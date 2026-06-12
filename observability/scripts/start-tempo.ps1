$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

foreach ($path in @(
        "$($Observability.TempoData)\wal",
        "$($Observability.TempoData)\blocks",
        "$($Observability.TempoData)\generator",
        "$($Observability.TempoData)\generator\traces"
    )) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

if (-not (Test-Path $Observability.TempoExe)) {
    throw "Tempo not found: $($Observability.TempoExe)"
}

Write-Host 'Starting Tempo on :3200 (OTLP gRPC :4319, HTTP :4320, target=all)'
Write-Host "Config: $($Observability.TempoConfig)"

& $Observability.TempoExe "-target=all" "-config.file=$($Observability.TempoConfig)"
