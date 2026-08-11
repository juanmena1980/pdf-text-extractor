# Genera PDFTextExtractor.exe (PyInstaller) listo para copiar a una USB.
# Requiere Python con pip en la PC de build.

$ErrorActionPreference = "Stop"

$appRoot = $PSScriptRoot
Set-Location $appRoot

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    throw "Python no esta en PATH."
}

Write-Host "Instalando herramientas de build..."
& $python.Source -m pip install --upgrade pip
& $python.Source -m pip install -r (Join-Path $appRoot "requirements.txt")
& $python.Source -m pip install "pyinstaller>=6.0"

$distDir = Join-Path $appRoot "dist"
$workDir = Join-Path $appRoot "build"
$specPath = Join-Path $appRoot "PDFTextExtractor.spec"

$addData = "static;static"
if ($IsLinux -or $IsMacOS) {
    $addData = "static:static"
}

Write-Host "Compilando ejecutable..."
& $python.Source -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --name "PDFTextExtractor" `
    --add-data $addData `
    --hidden-import "extract_pdf_text" `
    --hidden-import "engines" `
    --hidden-import "engines.base" `
    --hidden-import "engines.registry" `
    --hidden-import "engines.periodismo" `
    --hidden-import "engines.nota_informativa" `
    --distpath $distDir `
    --workpath $workDir `
    --specpath $appRoot `
    (Join-Path $appRoot "app.py")

$exe = Join-Path $distDir "PDFTextExtractor.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    throw "No se genero el ejecutable esperado: $exe"
}

Copy-Item -Force $exe (Join-Path $appRoot "PDFTextExtractor.exe")

$portableDir = Join-Path $distDir "usb"
New-Item -ItemType Directory -Force -Path $portableDir | Out-Null
Copy-Item -Force $exe (Join-Path $portableDir "PDFTextExtractor.exe")
Copy-Item -Force (Join-Path $appRoot "Iniciar.bat") (Join-Path $portableDir "Iniciar.bat")
Copy-Item -Force (Join-Path $appRoot "README.md") (Join-Path $portableDir "README.md")

Write-Host ""
Write-Host "Listo."
Write-Host "  EXE:      $exe"
Write-Host "  Copia:    $(Join-Path $appRoot 'PDFTextExtractor.exe')"
Write-Host "  Paquete:  $portableDir"
Write-Host ""
Write-Host "Copia la carpeta dist\usb a tu USB y abre Iniciar.bat o PDFTextExtractor.exe"
if (Test-Path -LiteralPath $specPath) {
    Write-Host "(Se dejo tambien el .spec por si quieres personalizar el build.)"
}
