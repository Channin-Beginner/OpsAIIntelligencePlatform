$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

foreach ($path in @($Observability.PrometheusData)) {
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Path $path -Force | Out-Null
    }
}

if (-not (Test-Path $Observability.PrometheusExe)) {
    throw "Prometheus not found: $($Observability.PrometheusExe)"
}

Write-Host 'Starting Prometheus on :9090'
Write-Host "Config: $($Observability.PrometheusConfig)"

& $Observability.PrometheusExe `
    --config.file="$($Observability.PrometheusConfig)" `
    --web.listen-address=":9090" `
    --storage.tsdb.path="$($Observability.PrometheusData)"
