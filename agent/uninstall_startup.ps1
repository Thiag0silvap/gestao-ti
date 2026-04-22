param(
    [string]$TaskName = "GestaoTI-InventoryAgent"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command Get-ScheduledTask -ErrorAction SilentlyContinue)) {
    schtasks.exe /Query /TN $TaskName | Out-Null
    if ($LASTEXITCODE -eq 0) {
        schtasks.exe /Delete /TN $TaskName /F | Out-Null
        Write-Host "[Agent] Tarefa removida: $TaskName"
    }
    else {
        Write-Host "[Agent] Nenhuma tarefa encontrada com o nome $TaskName"
    }

    exit 0
}

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[Agent] Tarefa removida: $TaskName"
}
else {
    Write-Host "[Agent] Nenhuma tarefa encontrada com o nome $TaskName"
}
