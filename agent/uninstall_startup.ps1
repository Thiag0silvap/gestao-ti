param(
    [string]$TaskName = "GestaoTI-InventoryAgent"
)

$ErrorActionPreference = "Stop"

if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "[Agent] Tarefa removida: $TaskName"
}
else {
    Write-Host "[Agent] Nenhuma tarefa encontrada com o nome $TaskName"
}
