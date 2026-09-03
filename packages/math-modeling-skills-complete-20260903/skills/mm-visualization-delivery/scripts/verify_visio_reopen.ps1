<#
.SYNOPSIS
Reopen a VSDX in an isolated Visio automation process and record the shape count.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory=$true)][string]$VsdxPath,
  [Parameter(Mandatory=$true)][string]$ReportPath
)

$ErrorActionPreference = 'Stop'
$result = [ordered]@{ reopened = $false; shape_count = 0; error = $null }
$app = $null
$doc = $null
try {
  $resolved = (Resolve-Path -LiteralPath $VsdxPath).Path
  $app = New-Object -ComObject Visio.InvisibleApp
  $doc = $app.Documents.Open($resolved)
  $result.shape_count = $doc.Pages.Item(1).Shapes.Count
  $result.reopened = $result.shape_count -gt 0
  if (-not $result.reopened) { throw 'Visio reopened the VSDX but found no shapes.' }
} catch {
  $result.error = $_.Exception.Message
} finally {
  if ($null -ne $doc) { try { $null = $doc.Close() } catch {} }
  if ($null -ne $app) { try { $null = $app.Quit() } catch {} }
  $json = $result | ConvertTo-Json -Depth 3
  $absoluteReport = [System.IO.Path]::GetFullPath($ReportPath)
  [System.IO.Directory]::CreateDirectory([System.IO.Path]::GetDirectoryName($absoluteReport)) | Out-Null
  [System.IO.File]::WriteAllText($absoluteReport, $json + [Environment]::NewLine, [System.Text.UTF8Encoding]::new($false))
}

$code = if ($result.reopened) { 0 } else { 1 }
[Environment]::Exit($code)
