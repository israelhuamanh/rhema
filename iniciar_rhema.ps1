# Script de arranque integral para Rhema (Motor Python + Aplicación Nativa Tauri v2)
$ErrorActionPreference = "Stop"

$cargoBin = Join-Path $env:USERPROFILE ".cargo\bin"
if ((Test-Path $cargoBin) -and ($env:Path -notlike "*$cargoBin*")) {
    $env:Path = "$cargoBin;$env:Path"
}

Write-Host "==========================================================" -ForegroundColor Yellow
Write-Host "  RHEMA - Iniciando Sistema de Proyeccion Biblica Local" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Yellow

$portInUse = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if (-not $portInUse) {
    Write-Host "[1/2] Iniciando rhema-engine (Python + Vosk + SQLite) en puerto 8765..." -ForegroundColor Green
    Start-Process -FilePath "j:\rhema\rhema-engine\venv\Scripts\python.exe" -ArgumentList "src\main.py" -WorkingDirectory "j:\rhema\rhema-engine" -WindowStyle Hidden
    Start-Sleep -Seconds 3
} else {
    Write-Host "[1/2] rhema-engine ya se encuentra activo en el puerto 8765." -ForegroundColor Yellow
}

$releaseExe = "j:\rhema\rhema-ui\src-tauri\target\release\rhema-ui.exe"
$debugExe = "j:\rhema\rhema-ui\src-tauri\target\debug\rhema-ui.exe"
$exePath = if (Test-Path $releaseExe) { $releaseExe } else { $debugExe }

if (Test-Path $exePath) {
    Write-Host "[2/2] Abriendo aplicacion nativa Tauri v2 (Rhema Studio + Rhema Live)..." -ForegroundColor Green
    Start-Process -FilePath $exePath -WorkingDirectory (Split-Path $exePath) -WindowStyle Normal
} else {
    Write-Host "[2/2] Compilando y abriendo Tauri v2..." -ForegroundColor Green
    Set-Location "j:\rhema\rhema-ui"
    npm run tauri dev
}
