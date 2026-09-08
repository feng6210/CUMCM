[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

function Test-CommandAvailable {
    param([Parameter(Mandatory = $true)][string]$Name)
    return $null -ne (Get-Command -Name $Name -ErrorAction SilentlyContinue)
}

function Test-ComProgId {
    param([Parameter(Mandatory = $true)][string[]]$ProgIds)
    foreach ($progId in $ProgIds) {
        try {
            if ($null -ne [type]::GetTypeFromProgID($progId, $false)) {
                return $progId
            }
        }
        catch {
            continue
        }
    }
    return $null
}

$python = Get-Command -Name py -ErrorAction SilentlyContinue
if ($null -eq $python) {
    $python = Get-Command -Name python -ErrorAction SilentlyContinue
}

$pythonPackages = [ordered]@{}
$pythonOk = $false
if ($null -ne $python) {
    $launcherArgs = @()
    if ($python.Name -eq 'py.exe' -or $python.Name -eq 'py') {
        $launcherArgs += '-3'
    }
    $probe = 'import importlib.util,json; names=["yaml","jsonschema","numpy","pandas","matplotlib","PIL","pypdfium2","scipy","sklearn","networkx","openpyxl"]; print(json.dumps({n:(importlib.util.find_spec(n) is not None) for n in names}))'
    $json = & $python.Source @launcherArgs -c $probe
    if ($LASTEXITCODE -eq 0) {
        $parsed = $json | ConvertFrom-Json
        foreach ($name in @('yaml', 'jsonschema', 'numpy', 'pandas', 'matplotlib', 'PIL', 'pypdfium2', 'scipy', 'sklearn', 'networkx', 'openpyxl')) {
            $pythonPackages[$name] = [bool]$parsed.$name
        }
        $pythonOk = -not ($pythonPackages.Values -contains $false)
    }
}

$originProgId = Test-ComProgId -ProgIds @('Origin.ApplicationSI', 'Origin.Application')
$visioProgId = Test-ComProgId -ProgIds @('Visio.Application')

$report = [ordered]@{
    checked_at = (Get-Date).ToUniversalTime().ToString('o')
    python = [ordered]@{
        executable = if ($null -ne $python) { $python.Source } else { $null }
        packages = $pythonPackages
        required_ready = $pythonOk
    }
    latex = [ordered]@{
        xelatex = Test-CommandAvailable -Name 'xelatex'
        latexmk = Test-CommandAvailable -Name 'latexmk'
        bibtex = Test-CommandAvailable -Name 'bibtex'
        pdftoppm = Test-CommandAvailable -Name 'pdftoppm'
    }
    optional_native_backends = [ordered]@{
        origin_progid = $originProgId
        visio_progid = $visioProgId
        note = 'Origin/Visio are optional licensed applications; the package includes deterministic fallbacks.'
    }
}

$report | ConvertTo-Json -Depth 6

if (-not $pythonOk) {
    Write-Error 'Python or one or more required Python packages are missing. Run: py -m pip install -r requirements.txt'
}
