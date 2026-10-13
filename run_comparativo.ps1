$ErrorActionPreference = "Stop"

$appRoot = $PSScriptRoot
Set-Location $appRoot

function Start-WithPython([string]$pythonExe) {
    Write-Host "Usando: $pythonExe"
    & $pythonExe -m comparativo
}

$runtimePython = Join-Path $appRoot "runtime\python\Scripts\python.exe"
$venvPython = Join-Path $appRoot ".venv\Scripts\python.exe"

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

Write-Error "No se encontro Python. Ejecuta: python -m pip install -r requirements.txt"
