param(
    [string]$TaskName = "GestaoTI-InventoryAgent",
    [switch]$UsePythonScript
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "[Agent] $Message"
}

function Test-IsAdministrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$localExePath = Join-Path $scriptDir "InventoryAgent.exe"
$distExePath = Join-Path $scriptDir "dist\InventoryAgent.exe"
$distEnvPath = Join-Path $scriptDir "dist\.env"
$pythonPath = Join-Path $scriptDir ".venv\Scripts\python.exe"
$scriptPath = Join-Path $scriptDir "inventory_agent.py"
$envPath = Join-Path $scriptDir ".env"
$runAsUser = "SYSTEM"

if (-not (Test-Path $envPath)) {
    throw "Arquivo .env nao encontrado em $envPath"
}

if (-not (Test-IsAdministrator)) {
    throw "Execute este instalador como Administrador para registrar o agente como SYSTEM."
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

if (-not (Get-Command New-ScheduledTaskAction -ErrorAction SilentlyContinue)) {
    Write-Step "Cmdlets modernos de tarefa agendada nao encontrados. Usando modo compativel com Windows 7."

    $taskCommand = "`"$execute`""
    if ($arguments) {
        $taskCommand = "$taskCommand $arguments"
    }

    schtasks.exe /Create /TN $TaskName /TR $taskCommand /SC ONSTART /RU $runAsUser /RL HIGHEST /F | Out-Null

    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao registrar tarefa agendada pelo schtasks.exe"
    }

    Write-Step "Tarefa agendada registrada com sucesso: $TaskName"
    Write-Step "Modo Windows 7: tarefa criada para executar na inicializacao do Windows como SYSTEM."

    schtasks.exe /Run /TN $TaskName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Step "Tarefa iniciada imediatamente para validar o agente."
    }
    else {
        Write-Step "Tarefa registrada, mas nao foi possivel iniciar imediatamente. Ela iniciara no proximo boot."
    }

    exit 0
}

$actionParams.WorkingDirectory = $scriptDir
$action = New-ScheduledTaskAction @actionParams
$triggerLogon = New-ScheduledTaskTrigger -AtLogOn
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId $runAsUser -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

$task = New-ScheduledTask `
    -Action $action `
    -Trigger @($triggerLogon, $triggerStartup) `
    -Principal $principal `
    -Settings $settings `
    -Description "Inicia o InventoryAgent automaticamente com o Windows."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

Write-Step "Tarefa agendada registrada com sucesso: $TaskName"
Write-Step "Tarefa criada para executar na inicializacao do Windows como SYSTEM."

Start-ScheduledTask -TaskName $TaskName
Write-Step "Tarefa iniciada imediatamente para validar o agente."
Write-Step "Use o Agendador de Tarefas do Windows para validar ou remover se necessario."
