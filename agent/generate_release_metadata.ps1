param(
    [string]$AgentScriptPath = "inventory_agent.py",
    [string]$ExecutablePath = "dist\InventoryAgent.exe"
)

$ErrorActionPreference = "Stop"

$resolvedAgentScriptPath = (Resolve-Path -LiteralPath $AgentScriptPath).Path
$resolvedExecutablePath = (Resolve-Path -LiteralPath $ExecutablePath).Path

if (-not $resolvedAgentScriptPath) {
    throw "Arquivo do agente nao encontrado: $AgentScriptPath"
}

if (-not $resolvedExecutablePath) {
    throw "Executavel nao encontrado para gerar metadata: $ExecutablePath"
}

$source = Get-Content -LiteralPath $resolvedAgentScriptPath -Raw
$versionMatch = [regex]::Match($source, 'APP_VERSION\s*=\s*"([^"]+)"')
if (-not $versionMatch.Success) {
    throw "Nao foi possivel identificar APP_VERSION em $resolvedAgentScriptPath"
}

$version = $versionMatch.Groups[1].Value
$sha256 = (Get-FileHash -LiteralPath $resolvedExecutablePath -Algorithm SHA256).Hash.ToLower()
$metadataPath = "$resolvedExecutablePath.version.json"
$metadata = [ordered]@{
    version = $version
    sha256 = $sha256
    generated_at = (Get-Date).ToString("s")
} | ConvertTo-Json

Set-Content -LiteralPath $metadataPath -Value $metadata -Encoding UTF8
Write-Host "[Agent] Metadata gerado em: $metadataPath"
