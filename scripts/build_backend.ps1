# Build AllSafe FastAPI backend as a Windows sidecar executable for Tauri bundling.
param(
    [string]$Python = "python",
    [string]$OutputName = "allsafe-api"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$BinDir = Join-Path $Root "src-tauri\bin"

Write-Host "Installing PyInstaller if needed..."
& $Python -m pip install pyinstaller --quiet

Write-Host "Building backend sidecar from $Backend ..."
Push-Location $Backend
try {
    & $Python -m PyInstaller `
        --noconfirm `
        --onefile `
        --name $OutputName `
        --hidden-import=uvicorn.logging `
        --hidden-import=uvicorn.loops `
        --hidden-import=uvicorn.loops.auto `
        --hidden-import=uvicorn.protocols `
        --hidden-import=uvicorn.protocols.http `
        --hidden-import=uvicorn.protocols.http.auto `
        --hidden-import=uvicorn.protocols.websockets `
        --hidden-import=uvicorn.protocols.websockets.auto `
        --hidden-import=uvicorn.lifespan `
        --hidden-import=uvicorn.lifespan.on `
        --collect-all=fastapi `
        --collect-all=pydantic `
        run_server.py
} finally {
    Pop-Location
}

New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
$Built = Join-Path $Backend "dist\$OutputName.exe"
if (-not (Test-Path $Built)) {
    throw "Build failed: $Built not found"
}

Copy-Item -Force $Built (Join-Path $BinDir "$OutputName-x86_64-pc-windows-msvc.exe")
Write-Host "Sidecar copied to src-tauri/bin/"
Write-Host "Run: npm run tauri:build"
