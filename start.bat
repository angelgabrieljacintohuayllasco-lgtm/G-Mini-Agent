@echo off
REM G-Mini Agent — Inicio rápido (Windows)
REM Un solo click: instala todo y arranca backend + frontend unificados

echo ========================================
echo   G-Mini Agent — Starting...
echo ========================================
echo.

cd /d "%~dp0"

REM Verificar Python
python --version 2>nul || (
    echo [ERROR] Python no encontrado. Instala Python 3.11+ desde python.org
    pause
    exit /b 1
)

REM Verificar Node.js
node --version 2>nul || (
    echo [ERROR] Node.js no encontrado. Instala Node.js 20+ desde nodejs.org
    pause
    exit /b 1
)

REM Crear venv si no existe
if not exist "venv" (
    echo [1/3] Creando entorno virtual Python...
    python -m venv venv
)

REM Instalar deps Python (rápido si ya están)
echo [1/3] Verificando dependencias Python...
call venv\Scripts\activate.bat
pip install -r backend\requirements.txt --quiet 2>nul

REM Instalar deps Node (rápido si ya están)
echo [2/3] Verificando dependencias Node.js...
cd electron
call npm install --silent 2>nul
cd ..

echo [3/3] Iniciando G-Mini Agent...
echo.
echo   Backend + Frontend se lanzan juntos.
echo   Alt+G = mostrar/ocultar  |  Ctrl+Shift+Q = salir
echo.

REM Electron lanza el backend automáticamente como proceso hijo
cd electron
call npx electron .
cd ..

echo.
echo G-Mini Agent cerrado.
pause
