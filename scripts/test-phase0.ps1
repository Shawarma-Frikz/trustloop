$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "Command failed ($LASTEXITCODE): $Executable $($Arguments -join ' ')"
        }
    }
    finally {
        Pop-Location
    }
}

Invoke-CheckedCommand (Join-Path $repoRoot "backend") "mvn" @("-B", "verify")
Invoke-CheckedCommand (Join-Path $repoRoot "scoring-service") "python" @("-m", "pytest", "-q")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("run", "typecheck")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("run", "build")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("test")
Invoke-CheckedCommand (Join-Path $repoRoot "contracts") "python" @("-m", "pip", "install", "-r", "requirements.txt")
Invoke-CheckedCommand (Join-Path $repoRoot "contracts") "python" @("-m", "pytest", "-q")

Write-Host "All Phase 0 harness commands passed."
