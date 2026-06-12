$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

foreach ($path in @(
        $Observability.LokiData,
        "$($Observability.LokiData)\chunks",
        "$($Observability.LokiData)\rules",
        "$($Observability.LokiData)\index",
        "$($Observability.LokiData)\index_cache"
    )) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

if (-not (Test-Path $Observability.LokiExe)) {
    throw "Loki not found: $($Observability.LokiExe)"
}

Write-Host 'Starting Loki on :3100'
Write-Host "Config: $($Observability.LokiConfig)"

& $Observability.LokiExe "-config.file=$($Observability.LokiConfig)"
