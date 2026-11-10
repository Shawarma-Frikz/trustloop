@echo off
setlocal

set "ROOT=%~dp0"

if not exist "%ROOT%.env" (
    echo TrustLoop .env file was not found at:
    echo   %ROOT%.env
    echo Create it from .env.example and add your local settings.
    pause
    exit /b 1
)

if not exist "%ROOT%scoring-service\.venv\Scripts\python.exe" (
    echo The scoring-service virtual environment was not found.
    echo Create scoring-service\.venv and install its requirements first.
    pause
    exit /b 1
)

where mvn >nul 2>nul
if errorlevel 1 (
    echo Maven was not found on PATH. Install Maven or add it to PATH, then retry.
    pause
    exit /b 1
)

for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%ROOT%.env") do (
    if not "%%A"=="" set "%%A=%%B"
)

 powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }" >nul 2>nul
if errorlevel 1 (
    echo Starting the scoring service in the background in this console...
    pushd "%ROOT%scoring-service"
    start "" /b cmd.exe /c ".venv\Scripts\python.exe -m app.main"
    popd
) else (
    echo A service is already listening on port 8000; reusing it.
)

echo Starting Spring Boot in this console. Press Ctrl+C to stop it.
cd /d "%ROOT%backend"
mvn spring-boot:run

echo The Chrome extension must already be loaded in Chrome.
endlocal
