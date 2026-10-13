@echo off
setlocal
cd /d "%~dp0"
title Mesa de sintesis
echo.
echo  Mesa de sintesis
echo  ----------------
echo.

if exist "%~dp0.venv\Scripts\python.exe" (
    echo Usando .venv local ...
    "%~dp0.venv\Scripts\python.exe" -m sintesis
    goto :eof
)

if exist "%~dp0runtime\python\Scripts\python.exe" (
    echo Usando Python portable ...
    "%~dp0runtime\python\Scripts\python.exe" -m sintesis
    goto :eof
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    echo Usando Python del sistema ...
    python -m sintesis
    goto :eof
)

echo No se encontro Python.
pause
endlocal
