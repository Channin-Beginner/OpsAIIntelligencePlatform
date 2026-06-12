$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

if (-not (Test-Path $Observability.OtelCollectorExe)) {
    throw "OTel Collector not found: $($Observability.OtelCollectorExe)"
}

Write-Host 'Starting OTel Collector'
Write-Host "  OTLP gRPC :4317  HTTP :4318"
Write-Host "  Prometheus exporter :8889"
Write-Host "Config: $($Observability.OtelCollectorConfig)"

& $Observability.OtelCollectorExe --config="$($Observability.OtelCollectorConfig)"
