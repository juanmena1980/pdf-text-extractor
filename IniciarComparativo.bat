@echo off
setlocal
cd /d "%~dp0"

title Comparativo de transcripciones
echo.
echo  Comparativo de transcripciones
echo  ------------------------------
echo.

if exist "%~dp0runtime\python\Scripts\python.exe" (
    echo Usando Python portable en runtime\python ...
    "%~dp0runtime\python\Scripts\python.exe" -m comparativo
    goto :eof
)

if exist "%~dp0.venv\Scripts\python.exe" (
    echo Usando .venv local ...
    "%~dp0.venv\Scripts\python.exe" -m comparativo
    goto :eof
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Usando Python del sistema ...
    python -m comparativo
    goto :eof
)

echo.
echo No se encontro Python.
echo Instala Python y ejecuta: python -m pip install -r requirements.txt
echo.
pause
endlocal
