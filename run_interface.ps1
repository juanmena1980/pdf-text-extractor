$ErrorActionPreference = "Stop"

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$bundledPython = Join-Path $env:USERPROFILE ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
$app = Join-Path $PSScriptRoot "app.py"

Set-Location $projectRoot

if (Test-Path -LiteralPath $bundledPython) {
    & $bundledPython $app
} else {
    python $app
}
