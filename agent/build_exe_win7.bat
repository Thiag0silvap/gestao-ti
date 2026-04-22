@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD=py -3.8"
set "VENV_DIR=.venv-win7"

%PYTHON_CMD% --version >nul 2>&1
if errorlevel 1 (
  echo [Agent] Python 3.8 nao encontrado.
  echo [Agent] Instale o Python 3.8.10 para gerar build compativel com Windows 7.
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [Agent] Criando ambiente virtual legado em %VENV_DIR%...
  %PYTHON_CMD% -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 1
)

"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade "pip<24"
if errorlevel 1 exit /b 1

"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements-win7.txt
if errorlevel 1 exit /b 1

"%VENV_DIR%\Scripts\python.exe" -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --noconsole ^
  --name InventoryAgent ^
  --paths "%VENV_DIR%\Lib\site-packages" ^
  --hidden-import psutil ^
  --hidden-import dotenv ^
  inventory_agent.py

if errorlevel 1 exit /b 1

if exist ".env.example" copy /Y ".env.example" "dist\.env.example" >nul
if exist ".env" copy /Y ".env" "dist\.env" >nul
if exist "install_startup.ps1" copy /Y "install_startup.ps1" "dist\install_startup.ps1" >nul
if exist "uninstall_startup.ps1" copy /Y "uninstall_startup.ps1" "dist\uninstall_startup.ps1" >nul
if exist "install_agent.cmd" copy /Y "install_agent.cmd" "dist\install_agent.cmd" >nul
if exist "uninstall_agent.cmd" copy /Y "uninstall_agent.cmd" "dist\uninstall_agent.cmd" >nul

echo.
echo [Agent] Build Windows 7 finalizado.
echo [Agent] Executavel gerado em: %~dp0dist\InventoryAgent.exe
