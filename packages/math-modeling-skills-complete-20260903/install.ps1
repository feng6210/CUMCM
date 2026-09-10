[CmdletBinding()]
param(
    [string]$Destination = (Join-Path $env:USERPROFILE ".codex\skills"),
    [switch]$ReplaceExisting,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$packageRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$sourceRoot = Join-Path $packageRoot "skills"

if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) {
    throw "Package skills directory is missing: $sourceRoot"
}

$skills = Get-ChildItem -LiteralPath $sourceRoot -Directory |
    Where-Object { $_.Name -eq "math-modeling-orchestrator" -or $_.Name -like "mm-*" } |
    Sort-Object Name

if ($skills.Count -ne 23) {
    throw "Expected 23 mathematical-modeling skills, found $($skills.Count)."
}

foreach ($skill in $skills) {
    if (-not (Test-Path -LiteralPath (Join-Path $skill.FullName "SKILL.md") -PathType Leaf)) {
        throw "Missing SKILL.md in $($skill.Name)."
    }
}

$existing = @($skills | Where-Object {
    Test-Path -LiteralPath (Join-Path $Destination $_.Name) -PathType Container
})

if ($existing.Count -gt 0 -and -not $ReplaceExisting) {
    $names = ($existing.Name -join ", ")
    throw "Existing skills detected: $names. Re-run with -ReplaceExisting to create a backup and replace them."
}

$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destinationParent = Split-Path -Parent $Destination
$stagingRoot = Join-Path $destinationParent ".mm-skills-install-$stamp"
$backupRoot = Join-Path $destinationParent "math-modeling-skills-backup-$stamp"

$plan = [ordered]@{
    source = $sourceRoot
    destination = $Destination
    skill_count = $skills.Count
    replace_existing = [bool]$ReplaceExisting
    existing_count = $existing.Count
    backup = if ($existing.Count -gt 0) { $backupRoot } else { $null }
    dry_run = [bool]$DryRun
}

if ($DryRun) {
    $plan | ConvertTo-Json -Depth 4
    exit 0
}

New-Item -ItemType Directory -Path $Destination -Force | Out-Null
New-Item -ItemType Directory -Path $stagingRoot -Force | Out-Null

try {
    foreach ($skill in $skills) {
        Copy-Item -LiteralPath $skill.FullName -Destination (Join-Path $stagingRoot $skill.Name) -Recurse
    }

    if ($existing.Count -gt 0) {
        New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null
        foreach ($skill in $existing) {
            $target = Join-Path $Destination $skill.Name
            Move-Item -LiteralPath $target -Destination (Join-Path $backupRoot $skill.Name)
        }
    }

    foreach ($skill in $skills) {
        Move-Item -LiteralPath (Join-Path $stagingRoot $skill.Name) -Destination (Join-Path $Destination $skill.Name)
    }

    $installed = Get-ChildItem -LiteralPath $Destination -Directory |
        Where-Object { $_.Name -eq "math-modeling-orchestrator" -or $_.Name -like "mm-*" }
    if ($installed.Count -lt 23) {
        throw "Post-install count check failed."
    }
}
catch {
    if (Test-Path -LiteralPath $backupRoot -PathType Container) {
        foreach ($backup in Get-ChildItem -LiteralPath $backupRoot -Directory) {
            $target = Join-Path $Destination $backup.Name
            if (-not (Test-Path -LiteralPath $target)) {
                Move-Item -LiteralPath $backup.FullName -Destination $target
            }
        }
    }
    throw
}
finally {
    if (Test-Path -LiteralPath $stagingRoot -PathType Container) {
        Remove-Item -LiteralPath $stagingRoot -Recurse -Force
    }
}

$plan.status = "INSTALLED"
$plan | ConvertTo-Json -Depth 4
