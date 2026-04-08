@echo off
setlocal

cd /d "%~dp0"

set "PYINSTALLER_CMD=python -m PyInstaller"
set "EXTRA_ARGS="

if exist ".venv\Lib\site-packages" (
  set "EXTRA_ARGS=--paths .venv\Lib\site-packages --hidden-import psutil --hidden-import dotenv"
)

%PYINSTALLER_CMD% ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --noconsole ^
  --name InventoryAgent ^
  %EXTRA_ARGS% ^
  inventory_agent.py

if exist ".env.example" copy /Y ".env.example" "dist\.env.example" >nul
if exist ".env" copy /Y ".env" "dist\.env" >nul
if exist "install_startup.ps1" copy /Y "install_startup.ps1" "dist\install_startup.ps1" >nul
if exist "uninstall_startup.ps1" copy /Y "uninstall_startup.ps1" "dist\uninstall_startup.ps1" >nul
if exist "install_agent.cmd" copy /Y "install_agent.cmd" "dist\install_agent.cmd" >nul
if exist "uninstall_agent.cmd" copy /Y "uninstall_agent.cmd" "dist\uninstall_agent.cmd" >nul

echo.
echo Build finalizado.
echo Comando de build: %PYINSTALLER_CMD%
echo Executavel gerado em: %~dp0dist\InventoryAgent.exe
