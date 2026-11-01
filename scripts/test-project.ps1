$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$scoringDir = Join-Path $repoRoot "scoring-service"
$python = Join-Path $scoringDir ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Scoring virtual environment is missing. Create it and install scoring-service/requirements.txt plus contracts/requirements.txt first."
}
if (-not (Test-Path -LiteralPath (Join-Path $repoRoot "extension\node_modules"))) {
    throw "Extension dependencies are missing. Run 'npm ci' in extension first."
}

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory = $true)][string]$WorkingDirectory,
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    Write-Host "`n> $Executable $($Arguments -join ' ')" -ForegroundColor Cyan
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

Invoke-CheckedCommand $scoringDir $python @("-m", "app.data_pipeline")
Invoke-CheckedCommand $scoringDir $python @("-m", "app.train_baseline")
Invoke-CheckedCommand $scoringDir $python @("-m", "pytest", "-q")
Invoke-CheckedCommand (Join-Path $repoRoot "contracts") $python @("-m", "pytest", "-q")
Invoke-CheckedCommand (Join-Path $repoRoot "backend") "mvn" @("-B", "verify")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("run", "typecheck")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("run", "build")
Invoke-CheckedCommand (Join-Path $repoRoot "extension") "npm" @("test")

Write-Host "`nAll TrustLoop checks passed." -ForegroundColor Green
