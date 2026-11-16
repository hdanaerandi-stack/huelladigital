@echo off
setlocal
cd /d "%~dp0"
title Huella - Flask

echo ==============================================
echo          HUELLA - SERVIDOR FLASK
echo ==============================================
echo.

set "PYTHON_CMD="
where py >nul 2>nul
if %errorlevel%==0 set "PYTHON_CMD=py"
if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
    echo ERROR: No se encontro Python instalado.
    echo Instala Python y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] Creando entorno virtual .venv...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/3] Entorno virtual encontrado.
)

echo [2/3] Instalando/verificando dependencias...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] Iniciando Huella en http://127.0.0.1:5000
echo.
start "" "http://127.0.0.1:5000"
".venv\Scripts\python.exe" backend\app.py
exit /b

:error
echo.
echo No se pudo iniciar Huella. Revisa el mensaje de error de arriba.
pause
exit /b 1
