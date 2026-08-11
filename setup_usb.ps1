# Prepara la carpeta para usarla desde USB sin instalar nada en el PC destino.
# Requiere Python 3.10+ en la PC donde se ejecuta este script UNA vez.
# Resultado: runtime\python con PyMuPDF listo para copiar a la USB.

$ErrorActionPreference = "Stop"

$appRoot = $PSScriptRoot
$runtimeRoot = Join-Path $appRoot "runtime"
$pythonDir = Join-Path $runtimeRoot "python"
$requirements = Join-Path $appRoot "requirements.txt"

Write-Host "Preparando runtime portable en:"
Write-Host "  $pythonDir"
Write-Host ""

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Necesitas Python en PATH para preparar la USB. Luego el runtime viaja con la app."
}

$pyVersion = & $python.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python detectado: $pyVersion ($($python.Source))"

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null

if (Test-Path -LiteralPath $pythonDir) {
    Write-Host "Ya existe runtime\python. Reinstalando dependencias..."
} else {
    Write-Host "Creando entorno virtual portable..."
    & $python.Source -m venv --copies $pythonDir
}

$venvPython = Join-Path $pythonDir "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    throw "No se creo runtime\python\Scripts\python.exe"
}

Write-Host "Instalando dependencias..."
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirements

Write-Host ""
Write-Host "Listo. Copia TODA esta carpeta a la USB y abre Iniciar.bat"
Write-Host "Nota: el venv con --copies funciona mejor en la misma arquitectura Windows (64-bit)."
Write-Host ""
Write-Host "Para un .exe autonomo (recomendado entre PCs distintas), ejecuta:"
Write-Host "  powershell -ExecutionPolicy Bypass -File .\build_portable.ps1"
