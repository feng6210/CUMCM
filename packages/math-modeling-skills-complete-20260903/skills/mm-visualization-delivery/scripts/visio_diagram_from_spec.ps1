<#
.SYNOPSIS
Create a Visio diagram from local FigureSpec JSON and verify VSDX/PDF reopenability.
.EXAMPLE
powershell -File visio_diagram_from_spec.ps1 -SpecPath flow.json -OutputDirectory figures -BaseName fig_flow
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$SpecPath,
  [Parameter(Mandatory=$true)][string]$OutputDirectory,
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_.-]+$')][string]$BaseName,
  [double]$PixelsPerInch = 96,
  [ValidateRange(65,180)][double]$FinalWidthMm = 160,
  [ValidateRange(30,300)][int]$WorkerTimeoutSec = 120,
  [ValidateSet('cumcm-mechanism','legacy')][string]$StyleProfile = 'cumcm-mechanism',
  [string]$PythonExe = '',
  [switch]$Visible,
  [Parameter(DontShow=$true)][switch]$Worker
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

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

function Get-FileSha256([string]$Path) {
  $stream = [System.IO.File]::OpenRead($Path)
  $algorithm = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = $algorithm.ComputeHash($stream)
    return ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
  } finally {
    $algorithm.Dispose()
    $stream.Dispose()
  }
}

function Write-WorkerStage([string]$Path, [string]$Stage) {
  if (-not $Path) { return }
  $payload = [ordered]@{ stage = $Stage; updated_utc = [DateTime]::UtcNow.ToString('o') }
  [System.IO.File]::WriteAllText(
    $Path,
    (($payload | ConvertTo-Json -Compress) + [Environment]::NewLine),
    [System.Text.UTF8Encoding]::new($false)
  )
}

if (-not $Worker) {
  $outDir = [System.IO.Path]::GetFullPath($OutputDirectory)
  [System.IO.Directory]::CreateDirectory($outDir) | Out-Null
  $vsdxPath = Join-Path $outDir "$BaseName.vsdx"
  $reportPath = [System.IO.Path]::ChangeExtension($vsdxPath, '.visio-report.json')
  $workerArgs = @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath,
    '-Worker', '-SpecPath', $SpecPath, '-OutputDirectory', $outDir,
    '-BaseName', $BaseName, '-PixelsPerInch', ([string]$PixelsPerInch),
    '-StyleProfile', $StyleProfile, '-FinalWidthMm', ([string]$FinalWidthMm)
  )
  if ($Visible) { $workerArgs += '-Visible' }
  $workerStdout = Join-Path $outDir "$BaseName.worker.stdout.tmp"
  $workerStderr = Join-Path $outDir "$BaseName.worker.stderr.tmp"
  $workerProgressPath = Join-Path $outDir "$BaseName.visio-progress.json"
  $workerStartedUtc = [DateTime]::UtcNow
  $visioBefore = @([System.Diagnostics.Process]::GetProcessesByName('VISIO') | ForEach-Object { $_.Id })
  $workerProcess = Start-Process -FilePath 'powershell.exe' -ArgumentList $workerArgs `
    -PassThru -WindowStyle Hidden -RedirectStandardOutput $workerStdout -RedirectStandardError $workerStderr
  $workerCompleted = $workerProcess.WaitForExit($WorkerTimeoutSec * 1000)
  $timeoutCleanupPassed = $true
  $terminatedPids = @()
  if (-not $workerCompleted) {
    try {
      $treeKill = Start-Process -FilePath 'taskkill.exe' -ArgumentList @(
        '/PID', [string]$workerProcess.Id, '/T', '/F'
      ) -Wait -PassThru -WindowStyle Hidden
      $terminatedPids += $workerProcess.Id
      if ($treeKill.ExitCode -ne 0) { $timeoutCleanupPassed = $false }
    } catch {
      $timeoutCleanupPassed = $false
      try { $workerProcess.Kill(); $terminatedPids += $workerProcess.Id } catch {}
    }
    try { $workerProcess.WaitForExit(5000) | Out-Null } catch {}
    Start-Sleep -Milliseconds 500
    $newVisio = @([System.Diagnostics.Process]::GetProcessesByName('VISIO') | Where-Object {
      $_.Id -notin $visioBefore -and $_.StartTime.ToUniversalTime() -ge $workerStartedUtc.AddSeconds(-2)
    })
    if ($newVisio.Count -eq 1) {
      try {
        $newVisio[0].Kill(); $newVisio[0].WaitForExit(5000) | Out-Null
        $terminatedPids += $newVisio[0].Id
      } catch { $timeoutCleanupPassed = $false }
    } elseif ($newVisio.Count -gt 1) {
      # Ambiguous ownership: do not kill possibly user-created Visio processes.
      $timeoutCleanupPassed = $false
    }
    $workerStillAlive = @([System.Diagnostics.Process]::GetProcessesByName('powershell') | Where-Object {
      $_.Id -eq $workerProcess.Id
    }).Count -gt 0
    $ownedVisioStillAlive = @([System.Diagnostics.Process]::GetProcessesByName('VISIO') | Where-Object {
      $_.Id -notin $visioBefore -and $_.StartTime.ToUniversalTime() -ge $workerStartedUtc.AddSeconds(-2)
    }).Count -gt 0
    if ($workerStillAlive -or $ownedVisioStillAlive) { $timeoutCleanupPassed = $false }
  }
  $workerOutput = @()
  if (Test-Path -LiteralPath $workerStdout) {
    $workerOutput += @(Get-Content -LiteralPath $workerStdout -Encoding UTF8)
    Remove-Item -LiteralPath $workerStdout -Force
  }
  if (Test-Path -LiteralPath $workerStderr) {
    $workerOutput += @(Get-Content -LiteralPath $workerStderr -Encoding UTF8)
    Remove-Item -LiteralPath $workerStderr -Force
  }
  $workerExit = if ($workerCompleted) { $workerProcess.ExitCode } else { 124 }
  if (-not $workerCompleted) {
    $lastStage = $null
    if (Test-Path -LiteralPath $workerProgressPath) {
      try { $lastStage = (Get-Content -LiteralPath $workerProgressPath -Raw -Encoding UTF8 | ConvertFrom-Json).stage } catch {}
    }
    $timeoutReport = [ordered]@{
      backend = 'Visio'; status = 'FAILED'; stage = 'outer_worker_timeout'
      last_worker_stage = $lastStage
      worker_timeout_sec = $WorkerTimeoutSec
      timeout_cleanup_passed = $timeoutCleanupPassed
      terminated_pids = @($terminatedPids)
      input_spec = [System.IO.Path]::GetFileName($SpecPath)
      error = "Visio worker exceeded the bounded timeout of $WorkerTimeoutSec seconds."
    }
    [System.IO.File]::WriteAllText(
      $reportPath,
      (($timeoutReport | ConvertTo-Json -Depth 4) + [Environment]::NewLine),
      [System.Text.UTF8Encoding]::new($false)
    )
  }
  if (-not (Test-Path -LiteralPath $reportPath)) {
    $workerOutput | Write-Output
    exit 1
  }
  $finalReport = Get-Content -LiteralPath $reportPath -Raw -Encoding UTF8 | ConvertFrom-Json
  if ($finalReport.status -notin @('GENERATION_PASSED','PASSED')) {
    $workerOutput | Write-Output
    exit 1
  }
  if ($null -ne $workerExit -and $workerExit -ne 0) {
    $finalReport.warnings = @($finalReport.warnings) + @(
      "Worker process exit code was $workerExit after writing a complete generation report."
    )
  }
  $reopenReportPath = Join-Path $outDir "$BaseName.visio-reopen.json"
  $verifyScript = Join-Path $PSScriptRoot 'verify_visio_reopen.ps1'
  try {
    $pythonCommand = Resolve-MetadataPython $PythonExe
    $sanitizeScript = Join-Path $PSScriptRoot 'sanitize_office_metadata.py'
    $sanitizeOutput = @()
    $sanitizeExit = 1
    $sanitizeStdout = Join-Path $outDir "$BaseName.sanitize.stdout.tmp"
    $sanitizeStderr = Join-Path $outDir "$BaseName.sanitize.stderr.tmp"
    for ($attempt = 1; $attempt -le 3; $attempt++) {
      try {
        $process = Start-Process -FilePath $pythonCommand -ArgumentList @(
          $sanitizeScript, '--vsdx', $vsdxPath, '--pdf', (Join-Path $outDir "$BaseName.pdf")
        ) -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $sanitizeStdout -RedirectStandardError $sanitizeStderr
        $sanitizeExit = $process.ExitCode
        $sanitizeOutput = @()
        if (Test-Path -LiteralPath $sanitizeStdout) {
          $sanitizeOutput += @(Get-Content -LiteralPath $sanitizeStdout -Encoding UTF8)
        }
        if (Test-Path -LiteralPath $sanitizeStderr) {
          $sanitizeOutput += @(Get-Content -LiteralPath $sanitizeStderr -Encoding UTF8)
        }
      } finally {
        if (Test-Path -LiteralPath $sanitizeStdout) { Remove-Item -LiteralPath $sanitizeStdout -Force }
        if (Test-Path -LiteralPath $sanitizeStderr) { Remove-Item -LiteralPath $sanitizeStderr -Force }
      }
      if ($sanitizeExit -eq 0) { break }
      if ($attempt -lt 3) { Start-Sleep -Milliseconds 750 }
    }
    if ($sanitizeExit -ne 0) { throw "Metadata sanitization failed after 3 attempts: $($sanitizeOutput -join ' ')" }
    $sanitizeReport = ($sanitizeOutput -join [Environment]::NewLine) | ConvertFrom-Json
    $finalReport.metadata_sanitized = [bool]$sanitizeReport.metadata_sanitized
    $finalReport.anonymous_check = [bool]$sanitizeReport.anonymous_check
    $finalReport.pdf_reopened = [bool]$sanitizeReport.pdf_reopened
    $finalReport.pdf_fonts = @($sanitizeReport.pdf_fonts)
    $finalReport.effective_palette = @(
      @($sanitizeReport.pdf_fill_palette) + @($sanitizeReport.pdf_stroke_palette) |
        Select-Object -Unique
    )
    $finalReport.identity_findings = @($sanitizeReport.identity_findings)
    $finalReport.vsdx_sha256 = [string]$sanitizeReport.vsdx_sha256
    $finalReport.pdf_sha256 = [string]$sanitizeReport.pdf_sha256
    if (-not $finalReport.metadata_sanitized -or -not $finalReport.anonymous_check -or -not $finalReport.pdf_reopened) {
      throw 'Sanitized Visio outputs did not pass metadata anonymity and PDF reopen checks.'
    }
    $verifyOutput = & powershell -NoProfile -ExecutionPolicy Bypass -File $verifyScript -VsdxPath $vsdxPath -ReportPath $reopenReportPath
    $verifyExit = $LASTEXITCODE
    if ($verifyExit -ne 0 -or -not (Test-Path -LiteralPath $reopenReportPath)) {
      throw "Visio reopen worker failed: $($verifyOutput -join ' ')"
    }
    $reopenReport = Get-Content -LiteralPath $reopenReportPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $finalReport.reopened_shape_count = [int]$reopenReport.shape_count
    $finalReport.document_reopened = [bool]$reopenReport.reopened
    if (-not $finalReport.document_reopened) { throw [string]$reopenReport.error }
    $finalReport.status = 'PASSED'
    $finalReport.error = $null
  } catch {
    $finalReport.status = 'FAILED'
    $finalReport.error = $_.Exception.Message
  } finally {
    if (Test-Path -LiteralPath $reopenReportPath) { Remove-Item -LiteralPath $reopenReportPath -Force }
    if (Test-Path -LiteralPath $workerProgressPath) { Remove-Item -LiteralPath $workerProgressPath -Force }
  }
  $finalJson = $finalReport | ConvertTo-Json -Depth 6
  [System.IO.File]::WriteAllText($reportPath, $finalJson + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
  Write-Output $finalJson
  if ($finalReport.status -ne 'PASSED') { exit 1 }
  exit 0
}

$report = [ordered]@{
  backend = 'Visio'
  status = 'FAILED'
  input_spec = $null
  input_sha256 = $null
  node_count = 0
  edge_count = 0
  style_profile = $StyleProfile
  font_family = 'PDF_EMBEDDED_FONT'
  base_font_pt = $null
  effective_min_font_pt = $null
  source_page_width_mm = $null
  final_width_mm = $FinalWidthMm
  line_width_pt = $null
  legend_strategy = 'none'
  decorative_effects = @('none')
  effective_palette = @()
  pdf_fonts = @()
  unsupported_groups = 0
  document_saved = $false
  pdf_exported = $false
  document_reopened = $false
  reopened_shape_count = 0
  metadata_sanitized = $false
  anonymous_check = $false
  pdf_reopened = $false
  identity_findings = @()
  vsdx = $null
  vsdx_sha256 = $null
  pdf = $null
  pdf_sha256 = $null
  generated_utc = [DateTime]::UtcNow.ToString('o')
  visio_version = $null
  alerts_suppressed = $false
  save_method = 'SaveAsEx'
  warnings = @()
  error = $null
}
$app = $null
$doc = $null
$reopened = $null
$verifyApp = $null
$vsdx = $null
$progressPath = $null
$fontSizes = @()
$lineWidths = @()

function Convert-HexToRgbFormula([string]$Hex, [string]$Fallback) {
  $value = if ($Hex -match '^#[0-9A-Fa-f]{6}$') { $Hex } else { $Fallback }
  $r = [Convert]::ToInt32($value.Substring(1,2),16)
  $g = [Convert]::ToInt32($value.Substring(3,2),16)
  $b = [Convert]::ToInt32($value.Substring(5,2),16)
  return "RGB($r,$g,$b)"
}

function Get-NodeValue($Node, [string]$Name, $Default) {
  $property = $Node.PSObject.Properties[$Name]
  if ($null -eq $property -or $null -eq $property.Value) { return $Default }
  return $property.Value
}

function Get-BoundaryPoint($From, [double]$TargetX, [double]$TargetY) {
  $dx = $TargetX - [double]$From.x
  $dy = $TargetY - [double]$From.y
  if ([math]::Abs($dx) -lt 1e-12 -and [math]::Abs($dy) -lt 1e-12) {
    return [pscustomobject]@{ x = [double]$From.x; y = [double]$From.y }
  }
  $halfWidth = [math]::Max([double]$From.width / 2, 1e-6)
  $halfHeight = [math]::Max([double]$From.height / 2, 1e-6)
  if ([string]$From.shape -in @('circle','ellipse')) {
    $scale = 1 / [math]::Sqrt(($dx / $halfWidth) * ($dx / $halfWidth) + ($dy / $halfHeight) * ($dy / $halfHeight))
  } elseif ([string]$From.shape -eq 'diamond') {
    $scale = 1 / ([math]::Abs($dx) / $halfWidth + [math]::Abs($dy) / $halfHeight)
  } else {
    $sx = if ([math]::Abs($dx) -lt 1e-12) { [double]::PositiveInfinity } else { $halfWidth / [math]::Abs($dx) }
    $sy = if ([math]::Abs($dy) -lt 1e-12) { [double]::PositiveInfinity } else { $halfHeight / [math]::Abs($dy) }
    $scale = [math]::Min($sx, $sy)
  }
  return [pscustomobject]@{ x = [double]$From.x + $dx * $scale; y = [double]$From.y + $dy * $scale }
}

try {
  if ($PixelsPerInch -le 0) { throw 'PixelsPerInch must be positive.' }
  $specFile = (Resolve-Path -LiteralPath $SpecPath).Path
  $report.input_spec = [System.IO.Path]::GetFileName($specFile)
  $report.input_sha256 = Get-FileSha256 $specFile
  $spec = Get-Content -LiteralPath $specFile -Raw -Encoding UTF8 | ConvertFrom-Json
  $nodes = @($spec.nodes)
  $edges = @($spec.edges)
  if ($nodes.Count -eq 0) { throw 'FigureSpec contains no nodes.' }
  $report.node_count = $nodes.Count
  $report.edge_count = $edges.Count
  if ($null -ne $spec.PSObject.Properties['groups']) {
    $report.unsupported_groups = @($spec.groups).Count
    if ($report.unsupported_groups -gt 0) {
      throw 'Basic Visio exporter cannot render FigureSpec groups; use FigureSpec/SVG or remove groups before native export.'
    }
  }

  $canvasWidth = [double](Get-NodeValue $spec.canvas 'width' 800)
  $canvasHeight = [double](Get-NodeValue $spec.canvas 'height' 400)
  if ($canvasWidth -le 0 -or $canvasHeight -le 0) { throw 'Canvas width and height must be positive.' }
  $margin = [double](Get-NodeValue $spec.canvas 'margin_in' 0.15)
  $pageWidth = $canvasWidth / $PixelsPerInch + 2 * $margin
  $pageHeight = $canvasHeight / $PixelsPerInch + 2 * $margin
  $report.source_page_width_mm = [math]::Round($pageWidth * 25.4, 3)

  $outDir = [System.IO.Path]::GetFullPath($OutputDirectory)
  [System.IO.Directory]::CreateDirectory($outDir) | Out-Null
  $progressPath = Join-Path $outDir "$BaseName.visio-progress.json"
  Write-WorkerStage $progressPath 'spec_validated'
  $vsdx = Join-Path $outDir "$BaseName.vsdx"
  $pdf = Join-Path $outDir "$BaseName.pdf"
  $report.vsdx = [System.IO.Path]::GetFileName($vsdx)
  $report.pdf = [System.IO.Path]::GetFileName($pdf)

  Write-WorkerStage $progressPath 'starting_visio_com'
  $app = New-Object -ComObject Visio.Application
  Write-WorkerStage $progressPath 'visio_com_started'
  try { $report.visio_version = [string]$app.Version } catch {}
  # Native Visio may otherwise display a compatibility/save prompt in the
  # invisible worker and block indefinitely. IDOK (1) is the documented
  # response used for alert suppression; save flags 0 avoid asking Visio to
  # show the compatibility checker.
  $app.AlertResponse = 1
  $report.alerts_suppressed = ([int]$app.AlertResponse -eq 1)
  if (-not $report.alerts_suppressed) {
    throw 'Visio alert suppression could not be established.'
  }
  $app.Visible = [bool]$Visible
  $doc = $app.Documents.Add('')
  Write-WorkerStage $progressPath 'blank_document_created'
  $page = $app.ActivePage
  $page.PageSheet.CellsU('PageWidth').FormulaU = "$pageWidth in"
  $page.PageSheet.CellsU('PageHeight').FormulaU = "$pageHeight in"

  $nodeMap = @{}
  foreach ($node in $nodes) {
    $id = [string](Get-NodeValue $node 'id' '')
    if (-not $id) { throw 'Every node requires a non-empty id.' }
    if ($nodeMap.ContainsKey($id)) { throw "Duplicate node id: $id" }
    $x = $margin + [double](Get-NodeValue $node 'x' 0) / $PixelsPerInch
    $y = $pageHeight - $margin - [double](Get-NodeValue $node 'y' 0) / $PixelsPerInch
    $width = [double](Get-NodeValue $node 'width' 120) / $PixelsPerInch
    $height = [double](Get-NodeValue $node 'height' 50) / $PixelsPerInch
    $shapeType = [string](Get-NodeValue $node 'shape' 'rounded')
    $nodeMap[$id] = [pscustomobject]@{ x = $x; y = $y; width = $width; height = $height; shape = $shapeType; node = $node }
  }

  foreach ($edge in $edges) {
    $from = [string](Get-NodeValue $edge 'from' '')
    $to = [string](Get-NodeValue $edge 'to' '')
    if (-not $nodeMap.ContainsKey($from) -or -not $nodeMap.ContainsKey($to)) {
      throw "Edge references unknown node: $from -> $to"
    }
    $src = $nodeMap[$from]
    $dst = $nodeMap[$to]
    $start = Get-BoundaryPoint $src $dst.x $dst.y
    $end = Get-BoundaryPoint $dst $src.x $src.y
    $line = $page.DrawLine($start.x, $start.y, $end.x, $end.y)
    $line.CellsU('EndArrow').FormulaU = '13'
    $defaultEdge = if ($StyleProfile -eq 'cumcm-mechanism') { '#657786' } else { '#555555' }
    $line.CellsU('LineColor').FormulaU = Convert-HexToRgbFormula ([string](Get-NodeValue $edge 'color' $defaultEdge)) $defaultEdge
    $defaultEdgeWidth = if ($StyleProfile -eq 'cumcm-mechanism') { 1.0 } else { 1.5 }
    $lineWidth = [double](Get-NodeValue $edge 'line_width' $defaultEdgeWidth)
    $lineWidths += $lineWidth
    $line.CellsU('LineWeight').FormulaU = "$lineWidth pt"
    $style = [string](Get-NodeValue $edge 'style' 'solid')
    if ($style -eq 'dashed') { $line.CellsU('LinePattern').FormulaU = '2' }
    elseif ($style -eq 'dotted') { $line.CellsU('LinePattern').FormulaU = '3' }
    $edgeLabel = [string](Get-NodeValue $edge 'label' '')
    if ($edgeLabel) {
      $mx = ($start.x + $end.x) / 2
      $my = ($start.y + $end.y) / 2 + 0.10
      $labelShape = $page.DrawRectangle($mx - 0.45, $my - 0.12, $mx + 0.45, $my + 0.12)
      $labelShape.Text = $edgeLabel
      $labelShape.CellsU('LinePattern').FormulaU = '0'
      $labelShape.CellsU('FillPattern').FormulaU = '0'
      $defaultEdgeFont = if ($StyleProfile -eq 'cumcm-mechanism') { 8.0 } else { 13.0 }
      $labelFontSize = [double](Get-NodeValue $edge 'font_size' $defaultEdgeFont)
      $fontSizes += $labelFontSize
      $labelShape.CellsU('Char.Size').FormulaU = "$labelFontSize pt"
    }
  }

  foreach ($entry in $nodeMap.GetEnumerator()) {
    $node = $entry.Value.node
    $x = [double]$entry.Value.x
    $y = [double]$entry.Value.y
    $width = [double]$entry.Value.width
    $height = [double]$entry.Value.height
    $shapeType = [string]$entry.Value.shape
    $shape = if ($shapeType -in @('circle','ellipse')) {
      $page.DrawOval($x - $width/2, $y - $height/2, $x + $width/2, $y + $height/2)
    } else {
      $page.DrawRectangle($x - $width/2, $y - $height/2, $x + $width/2, $y + $height/2)
    }
    if ($shapeType -eq 'rounded') { $shape.CellsU('Rounding').FormulaU = '0.08 in' }
    if ($shapeType -eq 'diamond') { $shape.CellsU('Angle').FormulaU = '45 deg' }
    $shape.Text = [string](Get-NodeValue $node 'label' $entry.Key)
    $defaultFill = if ($StyleProfile -eq 'cumcm-mechanism') { '#F1F5F7' } else { '#E8F0FE' }
    $defaultStroke = if ($StyleProfile -eq 'cumcm-mechanism') { '#365A7A' } else { '#2563EB' }
    $shape.CellsU('FillForegnd').FormulaU = Convert-HexToRgbFormula ([string](Get-NodeValue $node 'fill' $defaultFill)) $defaultFill
    $shape.CellsU('LineColor').FormulaU = Convert-HexToRgbFormula ([string](Get-NodeValue $node 'stroke' $defaultStroke)) $defaultStroke
    $defaultNodeWidth = if ($StyleProfile -eq 'cumcm-mechanism') { 1.0 } else { 1.5 }
    $nodeLineWidth = [double](Get-NodeValue $node 'line_width' $defaultNodeWidth)
    $lineWidths += $nodeLineWidth
    $shape.CellsU('LineWeight').FormulaU = "$nodeLineWidth pt"
    $defaultNodeFont = if ($StyleProfile -eq 'cumcm-mechanism') { 9.0 } else { 10.0 }
    $fontSize = [double](Get-NodeValue $node 'font_size' $defaultNodeFont)
    $fontSizes += $fontSize
    $shape.CellsU('Char.Size').FormulaU = "$fontSize pt"
  }
  Write-WorkerStage $progressPath 'shapes_drawn'

  if ($fontSizes.Count -eq 0 -or $lineWidths.Count -eq 0) {
    throw 'Visio style metrics could not be measured.'
  }
  $scaleAtFinalWidth = $FinalWidthMm / [double]$report.source_page_width_mm
  $report.base_font_pt = [math]::Round([double](($fontSizes | Measure-Object -Minimum).Minimum), 3)
  $report.effective_min_font_pt = [math]::Round($report.base_font_pt * $scaleAtFinalWidth, 3)
  $report.line_width_pt = [math]::Round([double](($lineWidths | Measure-Object -Minimum).Minimum) * $scaleAtFinalWidth, 3)
  if ($report.effective_min_font_pt -lt 7.0) {
    throw "Visio text would shrink below 7 pt at $FinalWidthMm mm."
  }

  Write-Verbose 'Saving VSDX.'
  $null = $doc.SaveAsEx($vsdx, 0)
  Write-WorkerStage $progressPath 'document_saved'
  $report.document_saved = (Test-Path -LiteralPath $vsdx) -and ((Get-Item -LiteralPath $vsdx).Length -gt 0)
  if (-not $report.document_saved) { throw 'Visio document save failed.' }
  Write-Verbose 'Exporting PDF.'
  $null = $doc.ExportAsFixedFormat(1, $pdf, 1, 0)
  Write-WorkerStage $progressPath 'pdf_exported'
  $report.pdf_exported = (Test-Path -LiteralPath $pdf) -and ((Get-Item -LiteralPath $pdf).Length -gt 0)
  if (-not $report.pdf_exported) { throw 'Visio PDF export failed.' }

  $line = $null
  $labelShape = $null
  $shape = $null
  $page = $null
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
  Write-Verbose 'Closing generated document.'
  $null = $doc.Close()
  Write-WorkerStage $progressPath 'document_closed'
  $doc = $null
  Write-Verbose 'Quitting generation instance.'
  $null = $app.Quit()
  Write-WorkerStage $progressPath 'visio_quit'
  $app = $null
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
  Start-Sleep -Milliseconds 500
  $report.vsdx_sha256 = Get-FileSha256 $vsdx
  $report.pdf_sha256 = Get-FileSha256 $pdf
  $report.status = 'GENERATION_PASSED'
} catch {
  $report.error = $_.Exception.Message
} finally {
  if ($null -ne $reopened) {
    try { $null = $reopened.Close() } catch {}
    $reopened = $null
  }
  if ($null -ne $doc) {
    try { $null = $doc.Close() } catch {}
    $doc = $null
  }
  if ($null -ne $app) {
    try { $null = $app.Quit() } catch {}
    $app = $null
  }
  if ($null -ne $verifyApp) {
    try { $null = $verifyApp.Quit() } catch {}
    $verifyApp = $null
  }
  $reportPath = if ($vsdx) {
    [System.IO.Path]::ChangeExtension([string]$vsdx, '.visio-report.json')
  } else {
    Join-Path ([System.IO.Path]::GetFullPath($OutputDirectory)) "$BaseName.visio-report.json"
  }
  [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($reportPath)) | Out-Null
  $json = $report | ConvertTo-Json -Depth 6
  [System.IO.File]::WriteAllText($reportPath, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
  Write-Output $json
}

$workerExitCode = if ($report.status -in @('PASSED','GENERATION_PASSED')) { 0 } else { 1 }
if ($Worker) { [Environment]::Exit($workerExitCode) }
if ($workerExitCode -ne 0) { exit $workerExitCode }
