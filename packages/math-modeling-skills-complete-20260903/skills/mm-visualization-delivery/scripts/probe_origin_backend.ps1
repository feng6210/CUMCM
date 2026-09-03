[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$candidates = @(
  'D:\origin\Origin64.exe',
  'D:\origin\Origin.exe',
  'C:\Program Files\OriginLab\OriginPro\Origin.exe',
  'C:\Program Files\OriginLab\Origin\Origin.exe'
) | Where-Object { Test-Path -LiteralPath $_ }
$progIds = @('Origin.ApplicationSI', 'Origin.ApplicationCOMSI', 'Origin.Application')
$registeredProgIds = @()
foreach ($progId in $progIds) {
  try {
    if ([type]::GetTypeFromProgID($progId)) { $registeredProgIds += $progId }
  } catch {}
}
$pythonModule = $false
try { & python -c "import originpro" 2>$null; $pythonModule = $LASTEXITCODE -eq 0 } catch { $pythonModule = $false }
[pscustomobject]@{
  backend = 'Origin'
  available = [bool]($candidates.Count -gt 0 -or $pythonModule -or $registeredProgIds.Count -gt 0)
  executable_paths = $candidates
  com_registered = [bool]($registeredProgIds.Count -gt 0)
  com_prog_ids = $registeredProgIds
  originpro_python = $pythonModule
  fallback = 'Python/Matplotlib or SVG'
  note = 'No OPJU is created when the native backend is unavailable.'
} | ConvertTo-Json -Depth 3
