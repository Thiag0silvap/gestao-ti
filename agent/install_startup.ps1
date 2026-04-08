param(
    [string]$TaskName = "GestaoTI-InventoryAgent",
    [switch]$UsePythonScript
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[Agent] $Message"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localExePath = Join-Path $scriptDir "InventoryAgent.exe"
$distExePath = Join-Path $scriptDir "dist\InventoryAgent.exe"
$distEnvPath = Join-Path $scriptDir "dist\.env"
$pythonPath = Join-Path $scriptDir ".venv\Scripts\python.exe"
$scriptPath = Join-Path $scriptDir "inventory_agent.py"
$envPath = Join-Path $scriptDir ".env"
$userId = "$env:USERDOMAIN\$env:USERNAME"

if (-not (Test-Path $envPath)) {
    throw "Arquivo .env nao encontrado em $envPath"
}

if ($UsePythonScript) {
    if (-not (Test-Path $pythonPath)) {
        throw "Python do ambiente virtual nao encontrado em $pythonPath"
    }

    $execute = $pythonPath
    $arguments = "`"$scriptPath`""
    Write-Step "Modo selecionado: script Python do .venv"
}
else {
    if (Test-Path $localExePath) {
        $exePath = $localExePath
    }
    elseif (Test-Path $distExePath) {
        $exePath = $distExePath
        Copy-Item -LiteralPath $envPath -Destination $distEnvPath -Force
    }
    else {
        throw "Executavel nao encontrado em $localExePath nem em $distExePath"
    }

    $execute = $exePath
    $arguments = ""
    Write-Step "Modo selecionado: executavel compilado"
}

$actionParams = @{
    Execute = $execute
}

if ($arguments) {
    $actionParams.Argument = $arguments
}

$action = New-ScheduledTaskAction @actionParams
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId $userId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew

$task = New-ScheduledTask `
    -Action $action `
    -Trigger @($triggerLogon, $triggerStartup) `
    -Principal $principal `
    -Settings $settings `
    -Description "Inicia o InventoryAgent automaticamente com o Windows."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Step "Tarefa agendada registrada com sucesso: $TaskName"
Write-Step "Use o Agendador de Tarefas do Windows para validar ou remover se necessario."
