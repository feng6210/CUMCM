<#
.SYNOPSIS
Create an Origin data plot from numeric CSV columns and verify OPJU/PDF reopenability.
.EXAMPLE
powershell -File origin_plot_from_csv.ps1 -CsvPath data.csv -XColumn x -YColumn y -OutputDirectory figures -BaseName fig_q1
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$CsvPath,
  [Parameter(Mandatory=$true)][string]$XColumn,
  [Parameter(Mandatory=$true)][string[]]$YColumn,
  [ValidateSet('line','scatter','line_symbol','column')][string]$PlotType = 'line',
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$BaseName,
  [string]$XLabel = '',
  [string]$YLabel = '',
  [string[]]$SeriesLabel = @(),
  [switch]$ShowDataLabels,
  [ValidateSet('cumcm-clean','cumcm-highlight','cumcm-vivid','legacy')][string]$StyleProfile = 'cumcm-clean',
  [ValidateRange(65,180)][double]$FinalWidthMm = 160,
  [string]$PythonExe = '',
  [switch]$PublicationTheme,
  [switch]$Visible
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$invariant = [System.Globalization.CultureInfo]::InvariantCulture
$numberStyles = [System.Globalization.NumberStyles]::Float -bor [System.Globalization.NumberStyles]::AllowThousands

function Resolve-MetadataPython([string]$Requested) {
  $candidates = @()
  if ($Requested) { $candidates += $Requested }
  if ($env:VIRTUAL_ENV) { $candidates += (Join-Path $env:VIRTUAL_ENV 'Scripts\python.exe') }
  $candidates += @(Get-Command python -All -ErrorAction SilentlyContinue | ForEach-Object { $_.Source })
  try {
    $candidates += @(& py -0p 2>$null | ForEach-Object {
      if ($_ -match '([A-Za-z]:\\.*python\.exe)\s*$') { $Matches[1] }
    })
  } catch {}
  foreach ($candidate in @($candidates | Where-Object { $_ } | Select-Object -Unique)) {
    if (-not (Test-Path -LiteralPath $candidate)) { continue }
    $savedErrorPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = 'Continue'
      & $candidate -c 'import pypdf' *> $null
      $probeExit = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $savedErrorPreference
    }
    if ($probeExit -eq 0) { return $candidate }
  }
  throw 'No Python interpreter with pypdf is available; pass -PythonExe explicitly.'
}
$report = [ordered]@{
  backend = 'Origin'
  status = 'FAILED'
  input_csv = $null
  input_sha256 = $null
  x_column = $XColumn
  y_columns = $YColumn
  row_count = 0
  plot_type = $PlotType
  style_profile = $StyleProfile
  put_worksheet = $false
  plot_created = $false
  project_saved = $false
  pdf_exported = $false
  project_reopened = $false
  opju = $null
  opju_sha256 = $null
  pdf = $null
  pdf_sha256 = $null
  metadata_sanitized = $false
  anonymous_check = $false
  pdf_reopened = $false
  identity_findings = @()
  final_width_mm = $FinalWidthMm
  pdf_page_width_pt = $null
  pdf_page_height_pt = $null
  effective_min_font_pt = $null
  font_family = 'Origin worksheet theme font'
  base_font_pt = 15.0
  line_width_pt = $(if ($StyleProfile -eq 'cumcm-vivid') { 1.4 } else { 1.2 })
  legend_strategy = 'top'
  generated_utc = [DateTime]::UtcNow.ToString('o')
  origin_version = $null
  effective_palette = @()
  series_color_mapping = [ordered]@{}
  decorative_effects = @('none')
  error = $null
}
$app = $null
$opju = $null

function Convert-ToLabTalkString([string]$Value) {
  return $Value.Replace('\', '/').Replace('"', '\"')
}

try {
  if ($PublicationTheme) { $StyleProfile = 'cumcm-clean'; $report.style_profile = $StyleProfile }
  $csv = (Resolve-Path -LiteralPath $CsvPath).Path
  $report.input_csv = [System.IO.Path]::GetFileName($csv)
  $report.input_sha256 = (Get-FileHash -LiteralPath $csv -Algorithm SHA256).Hash.ToLowerInvariant()
  $rows = @(Import-Csv -LiteralPath $csv)
  if ($rows.Count -eq 0) { throw 'CSV contains no data rows.' }
  $headers = @($rows[0].PSObject.Properties.Name)
  foreach ($name in @($XColumn) + @($YColumn)) {
    if ($headers -notcontains $name) { throw "CSV column not found: $name" }
  }

  $columnNames = @($XColumn) + @($YColumn)
  $data = New-Object 'double[,]' $rows.Count, $columnNames.Count
  for ($r = 0; $r -lt $rows.Count; $r++) {
    for ($c = 0; $c -lt $columnNames.Count; $c++) {
      $raw = [string]$rows[$r].($columnNames[$c])
      $value = 0.0
      if (-not [double]::TryParse($raw, $numberStyles, $invariant, [ref]$value)) {
        throw "Non-numeric value at data row $($r + 1), column '$($columnNames[$c])': $raw"
      }
      $data[$r, $c] = $value
    }
  }
  $report.row_count = $rows.Count

  $outDir = [System.IO.Path]::GetFullPath($OutputDirectory)
  [System.IO.Directory]::CreateDirectory($outDir) | Out-Null
  $opju = Join-Path $outDir "$BaseName.opju"
  $pdf = Join-Path $outDir "$BaseName.pdf"
  $report.opju = [System.IO.Path]::GetFileName($opju)
  $report.pdf = [System.IO.Path]::GetFileName($pdf)

  $app = New-Object -ComObject Origin.ApplicationSI
  try { $report.origin_version = [string]$app.Version } catch {}
  try { $app.Visible = [bool]$Visible } catch {}
  $null = $app.NewProject()
  if (-not $app.Execute('sec -poc 30;')) { throw 'Origin startup compile wait failed.' }
  if (-not $app.Execute('newbook name:=MMData;')) { throw 'Origin failed to create workbook.' }
  $report.put_worksheet = [bool]$app.PutWorksheet('[MMData]Sheet1', $data, 0, 0)
  if (-not $report.put_worksheet) { throw 'Origin PutWorksheet returned false.' }

  for ($i = 0; $i -lt $columnNames.Count; $i++) {
    $displayName = if ($i -gt 0 -and $SeriesLabel.Count -ge $i) { $SeriesLabel[$i - 1] } else { $columnNames[$i] }
    $longName = Convert-ToLabTalkString $displayName
    $colIndex = $i + 1
    $null = $app.Execute("wks.col$colIndex.lname`$=`"$longName`";")
  }
  $plotIds = @{ line = 200; scatter = 201; line_symbol = 202; column = 203 }
  $lastColumn = $columnNames.Count
  $plotCommand = if ($lastColumn -eq 2) {
    "plotxy iy:=(1,2) plot:=$($plotIds[$PlotType]);"
  } else {
    "plotxy iy:=(1,2:$lastColumn) plot:=$($plotIds[$PlotType]);"
  }
  $report.plot_created = [bool]$app.Execute($plotCommand)
  if (-not $report.plot_created) { throw "Origin plot command failed: $plotCommand" }

  if ($XLabel) {
    $escaped = Convert-ToLabTalkString $XLabel
    $null = $app.Execute("label -xb `"$escaped`";")
  }
  if ($YLabel) {
    $escaped = Convert-ToLabTalkString $YLabel
    $null = $app.Execute("label -yl `"$escaped`";")
  }

  if ($StyleProfile -ne 'legacy') {
    # Presentation only: never alter data, axis range, fitting, or aggregation.
    # PDF page is fitted by Origin and later scaled to FinalWidthMm in LaTeX.
    # Use larger source sizes so final tick/legend text remains at least 7 pt.
    $null = $app.Execute('xb.fsize=18; yl.fsize=18; layer.x.label.fsize=15; layer.y.label.fsize=15;')
    if ($PlotType -eq 'column') {
      if ($StyleProfile -eq 'cumcm-vivid') {
        $null = $app.Execute('int mmplot=0; doc -e D { mmplot++; if(mmplot==1) { set %C -pfbr color(42,157,143,2); set %C -pbcr color(42,157,143,2); set %C -pbw 0.3; } if(mmplot==2) { set %C -pfbr color(231,111,81,2); set %C -pbcr color(231,111,81,2); set %C -pbw 0.3; } if(mmplot>2) { set %C -pfbr color(233,196,106,2); set %C -pbcr color(233,196,106,2); set %C -pbw 0.3; } };')
      } elseif ($StyleProfile -eq 'cumcm-highlight') {
        $null = $app.Execute('int mmplot=0; doc -e D { mmplot++; if(mmplot==1) { set %C -pfbr color(170,180,189,2); set %C -pbcr color(170,180,189,2); set %C -pbw 0.3; } if(mmplot==2) { set %C -pfbr color(60,141,107,2); set %C -pbcr color(60,141,107,2); set %C -pbw 0.3; } if(mmplot>2) { set %C -pfbr color(217,130,43,2); set %C -pbcr color(217,130,43,2); set %C -pbw 0.3; } };')
      } else {
        $null = $app.Execute('int mmplot=0; doc -e D { mmplot++; if(mmplot==1) { set %C -pfbr color(47,93,124,2); set %C -pbcr color(47,93,124,2); set %C -pbw 0.3; } if(mmplot==2) { set %C -pfbr color(217,130,43,2); set %C -pbcr color(217,130,43,2); set %C -pbw 0.3; } if(mmplot>2) { set %C -pfbr color(76,149,108,2); set %C -pbcr color(76,149,108,2); set %C -pbw 0.3; } };')
      }
    } elseif ($StyleProfile -eq 'cumcm-vivid') {
      $null = $app.Execute('int mmplot=0; doc -e D { mmplot++; if(mmplot==1) { set %C -c color(42,157,143,2); set %C -w 1400; set %C -z 6; } if(mmplot==2) { set %C -c color(231,111,81,2); set %C -w 1400; set %C -z 6; } if(mmplot>2) { set %C -c color(233,196,106,2); set %C -w 1400; set %C -z 6; } };')
    } else {
      $null = $app.Execute('int mmplot=0; doc -e D { mmplot++; if(mmplot==1) { set %C -c color(47,93,124,2); set %C -w 1200; set %C -z 5; } if(mmplot==2) { set %C -c color(217,130,43,2); set %C -w 1200; set %C -z 5; } if(mmplot>2) { set %C -c color(76,149,108,2); set %C -w 1200; set %C -z 5; } };')
    }
    $null = $app.Execute('legend -r;')
    $null = $app.Execute('legend.fsize=15; legend.x=(layer.x.from+layer.x.to)/2; legend.y=layer.y.to+legend.dy/2+1;')
    $null = $app.Execute('page -FLS -u -c 3 -ml 0.03 -mr 0.03 -mt 0.03 -mb 0.03;')
  }
  $effectivePalette = if ($StyleProfile -eq 'cumcm-vivid') {
    @('#2A9D8F','#E76F51','#E9C46A','#457B9D','#9B5DE5','#F15BB5')
  } elseif ($StyleProfile -eq 'cumcm-highlight') {
    @('#AAB4BD','#3C8D6B','#D9822B','#2F5D7C','#8A6FB0','#C65D57')
  } else {
    @('#2F5D7C','#D9822B','#4C956C','#8A6FB0','#C65D57','#5F6B73')
  }
  $report.effective_palette = $effectivePalette
  for ($seriesIndex = 0; $seriesIndex -lt $YColumn.Count; $seriesIndex++) {
    $seriesName = if ($SeriesLabel.Count -gt $seriesIndex) { $SeriesLabel[$seriesIndex] } else { $YColumn[$seriesIndex] }
    $report.series_color_mapping[$seriesName] = $effectivePalette[$seriesIndex % $effectivePalette.Count]
  }
  if ($ShowDataLabels) {
    $null = $app.Execute('doc -e D { set %C -q 1; set %C -qm 2; set %C -qs 15; set %C -qp 4; };')
  }

  $report.project_saved = [bool]$app.Save($opju)
  if (-not $report.project_saved -or -not (Test-Path -LiteralPath $opju)) {
    throw 'Origin project save failed.'
  }
  $exportDir = Convert-ToLabTalkString $outDir
  $exportName = Convert-ToLabTalkString $BaseName
  $report.pdf_exported = [bool]$app.Execute("expGraph type:=pdf filename:=`"$exportName`" path:=`"$exportDir`";")
  if (-not $report.pdf_exported -or -not (Test-Path -LiteralPath $pdf)) {
    throw 'Origin PDF export failed.'
  }

  $null = $app.NewProject()
  $report.project_reopened = [bool]$app.Load($opju)
  if (-not $report.project_reopened) { throw 'Origin could not reopen the saved OPJU.' }
  $null = $app.NewProject()
  Start-Sleep -Milliseconds 250
  $pythonCommand = Resolve-MetadataPython $PythonExe
  $sanitizeScript = Join-Path $PSScriptRoot 'sanitize_office_metadata.py'
  $sanitizeOutput = & $pythonCommand $sanitizeScript --pdf $pdf
  if ($LASTEXITCODE -ne 0) { throw "PDF metadata sanitization failed: $($sanitizeOutput -join ' ')" }
  $sanitizeReport = ($sanitizeOutput -join [Environment]::NewLine) | ConvertFrom-Json
  $report.metadata_sanitized = [bool]$sanitizeReport.metadata_sanitized
  $report.anonymous_check = [bool]$sanitizeReport.anonymous_check
  $report.pdf_reopened = [bool]$sanitizeReport.pdf_reopened
  $report.identity_findings = @($sanitizeReport.identity_findings)
  $report.pdf_page_width_pt = [double]$sanitizeReport.pdf_page_width_pt
  $report.pdf_page_height_pt = [double]$sanitizeReport.pdf_page_height_pt
  $observedPalette = @($sanitizeReport.pdf_fill_palette)
  if ($observedPalette.Count -lt $YColumn.Count) { $observedPalette = @($sanitizeReport.pdf_stroke_palette) }
  if ($observedPalette.Count -lt $YColumn.Count) {
    throw 'Origin PDF colors could not be measured for every series.'
  }
  $report.effective_palette = @($observedPalette | Select-Object -First $YColumn.Count)
  $report.series_color_mapping = [ordered]@{}
  for ($seriesIndex = 0; $seriesIndex -lt $YColumn.Count; $seriesIndex++) {
    $seriesName = if ($SeriesLabel.Count -gt $seriesIndex) { $SeriesLabel[$seriesIndex] } else { $YColumn[$seriesIndex] }
    $report.series_color_mapping[$seriesName] = $report.effective_palette[$seriesIndex]
  }
  if (-not $report.metadata_sanitized -or -not $report.anonymous_check -or -not $report.pdf_reopened) {
    throw 'Origin PDF did not pass metadata anonymity and reopen checks.'
  }
  if ($report.pdf_page_width_pt -le 0) { throw 'Origin PDF page width could not be measured.' }
  $scaleAtFinalWidth = $FinalWidthMm / ($report.pdf_page_width_pt * 25.4 / 72.0)
  $report.effective_min_font_pt = [math]::Round(15.0 * $scaleAtFinalWidth, 2)
  if ($report.effective_min_font_pt -lt 7.0) {
    throw "Origin text would shrink below 7 pt at $FinalWidthMm mm (effective $($report.effective_min_font_pt) pt)."
  }
  $report.opju_sha256 = (Get-FileHash -LiteralPath $opju -Algorithm SHA256).Hash.ToLowerInvariant()
  $report.pdf_sha256 = [string]$sanitizeReport.pdf_sha256
  $report.status = 'PASSED'
} catch {
  $report.error = $_.Exception.Message
} finally {
  if ($null -ne $app) {
    try { $null = $app.Exit() } catch {}
    try { [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($app) } catch {}
  }
  $reportPath = if ($opju) {
    [System.IO.Path]::ChangeExtension([string]$opju, '.origin-report.json')
  } else {
    Join-Path ([System.IO.Path]::GetFullPath($OutputDirectory)) "$BaseName.origin-report.json"
  }
  [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($reportPath)) | Out-Null
  $json = $report | ConvertTo-Json -Depth 5
  [System.IO.File]::WriteAllText($reportPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
  Write-Output $json
}

if ($report.status -ne 'PASSED') { exit 1 }
