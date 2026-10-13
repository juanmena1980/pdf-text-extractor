$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$runtimePython = Join-Path $PSScriptRoot "runtime\python\Scripts\python.exe"

if (Test-Path -LiteralPath $venvPython) {
    & $venvPython -m sintesis
    exit $LASTEXITCODE
}

if (Test-Path -LiteralPath $runtimePython) {
    & $runtimePython -m sintesis
    exit $LASTEXITCODE
}

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    & $pythonCmd.Source -m sintesis
    exit $LASTEXITCODE
}

Write-Error "No se encontro Python."
