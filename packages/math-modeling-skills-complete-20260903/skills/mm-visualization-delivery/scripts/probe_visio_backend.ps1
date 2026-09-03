[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$path = $null
try { $path = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\VISIO.EXE' -ErrorAction Stop).'(default)' } catch {}
$comAvailable = $false
try { $null = [type]::GetTypeFromProgID('Visio.Application'); $comAvailable = $null -ne [type]::GetTypeFromProgID('Visio.Application') } catch { $comAvailable = $false }
[pscustomobject]@{
  backend = 'Visio'
  available = [bool]($path -or $comAvailable)
  executable_path = $path
  com_registered = $comAvailable
  fallback = 'FigureSpec/SVG or Mermaid'
  note = 'No VSDX is created when the native backend is unavailable.'
} | ConvertTo-Json -Depth 3
