$ErrorActionPreference = "Stop"

$appRoot = $PSScriptRoot
$app = Join-Path $appRoot "app.py"
Set-Location $appRoot

function Start-WithPython([string]$pythonExe) {
    Write-Host "Usando: $pythonExe"
    & $pythonExe $app
}

$portableExe = Join-Path $appRoot "PDFTextExtractor.exe"
$distExe = Join-Path $appRoot "dist\PDFTextExtractor.exe"
$runtimePython = Join-Path $appRoot "runtime\python\Scripts\python.exe"
$venvPython = Join-Path $appRoot ".venv\Scripts\python.exe"

if (Test-Path -LiteralPath $portableExe) {
    Start-Process -FilePath $portableExe
    exit 0
}

if (Test-Path -LiteralPath $distExe) {
    Start-Process -FilePath $distExe
    exit 0
}

if (Test-Path -LiteralPath $runtimePython) {
    Start-WithPython $runtimePython
    exit $LASTEXITCODE
}

if (Test-Path -LiteralPath $venvPython) {
    Start-WithPython $venvPython
    exit $LASTEXITCODE
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    Start-WithPython $pythonCmd.Source
    exit $LASTEXITCODE
}

Write-Error "No se encontro Python ni PDFTextExtractor.exe. Ejecuta setup_usb.ps1 o build_portable.ps1."
