@echo off
setlocal

cd /d "%~dp0"

echo [Agent] Removendo inicializacao automatica...
powershell -ExecutionPolicy Bypass -File "%~dp0uninstall_startup.ps1"

if errorlevel 1 (
  echo.
  echo [Agent] Falha ao remover o agente.
  pause
  exit /b 1
)

echo.
echo [Agent] Remocao concluida com sucesso.
pause
