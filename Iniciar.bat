@echo off
setlocal
cd /d "%~dp0"

title Extractor de texto PDF
echo.
echo  Extractor de texto PDF
echo  ----------------------
echo.

REM 1) Ejecutable portable ya construido (ideal para USB)
if exist "%~dp0PDFTextExtractor.exe" (
    echo Iniciando PDFTextExtractor.exe ...
    start "" "%~dp0PDFTextExtractor.exe"
    goto :eof
)

if exist "%~dp0dist\PDFTextExtractor.exe" (
    echo Iniciando dist\PDFTextExtractor.exe ...
    start "" "%~dp0dist\PDFTextExtractor.exe"
    goto :eof
)

REM 2) Python portable embebido en la USB (creado por setup_usb.ps1)
if exist "%~dp0runtime\python\Scripts\python.exe" (
    echo Usando Python portable en runtime\python ...
    "%~dp0runtime\python\Scripts\python.exe" "%~dp0app.py"
    goto :eof
)

REM 3) Entorno virtual local
if exist "%~dp0.venv\Scripts\python.exe" (
    echo Usando .venv local ...
    "%~dp0.venv\Scripts\python.exe" "%~dp0app.py"
    goto :eof
)

REM 4) Python del sistema
where python >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Usando Python del sistema ...
    python "%~dp0app.py"
    goto :eof
)

echo.
echo No se encontro un runtime.
echo.
echo Opciones:
echo   A^) Copia PDFTextExtractor.exe a esta carpeta ^(tras build_portable.ps1^)
echo   B^) Ejecuta setup_usb.ps1 una vez en una PC con Python
echo.
pause
endlocal
