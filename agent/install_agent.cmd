@echo off
setlocal

cd /d "%~dp0"

if not exist ".env" (
  echo [Agent] Arquivo .env nao encontrado nesta pasta.
  pause
  exit /b 1
)

set "SECTOR_INPUT="
set /p SECTOR_INPUT=[Agent] Informe o setor desta maquina ^(ex: Financeiro, RH, Comercial, TI^): 

if not "%SECTOR_INPUT%"=="" (
  powershell -ExecutionPolicy Bypass -Command ^
    "$envFile = Join-Path '%~dp0' '.env';" ^
    "$content = Get-Content -LiteralPath $envFile;" ^
    "$updated = $content | ForEach-Object { if ($_ -match '^DEFAULT_SECTOR=') { 'DEFAULT_SECTOR=%SECTOR_INPUT%' } else { $_ } };" ^
    "Set-Content -LiteralPath $envFile -Value $updated -Encoding UTF8"

  if errorlevel 1 (
    echo.
    echo [Agent] Falha ao atualizar o setor no .env.
    pause
    exit /b 1
  )
)

echo [Agent] Registrando inicializacao automatica...
powershell -ExecutionPolicy Bypass -File "%~dp0install_startup.ps1"

if errorlevel 1 (
  echo.
  echo [Agent] Falha ao instalar o agente.
  pause
  exit /b 1
)

echo.
echo [Agent] Instalacao concluida com sucesso.
pause
