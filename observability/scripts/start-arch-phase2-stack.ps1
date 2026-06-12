# Launch architecture phase 2 stack: phase 1 + Loki / Promtail / Tempo / OTel Collector.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

$scripts = @(
    @{ Name = 'Loki'; File = 'start-loki.ps1' },
    @{ Name = 'Tempo'; File = 'start-tempo.ps1' },
    @{ Name = 'OTel Collector'; File = 'start-otel-collector.ps1' },
    @{ Name = 'Promtail'; File = 'start-promtail.ps1' },
    @{ Name = 'Prometheus'; File = 'start-prometheus.ps1' },
    @{ Name = 'Alertmanager'; File = 'start-alertmanager.ps1' },
    @{ Name = 'Grafana'; File = 'start-grafana.ps1' }
)

function Wait-LokiReady {
    param([int]$TimeoutSeconds = 90)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest 'http://127.0.0.1:3100/ready' -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Host 'Loki is ready (http://127.0.0.1:3100/ready).'
                return
            }
        }
        catch {
            # Loki still starting: connection refused or 503 empty ring are expected briefly.
        }
        Start-Sleep -Seconds 2
    }
    Write-Warning 'Loki did not become ready within timeout. Start OTel Collector after /ready returns 200.'
}

function Wait-TempoReady {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest 'http://127.0.0.1:3200/ready' -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                Write-Host 'Tempo is ready (http://127.0.0.1:3200/ready, OTLP gRPC :4319).'
                return
            }
        }
        catch {
            # Tempo still starting.
        }
        Start-Sleep -Seconds 2
    }
    Write-Warning 'Tempo did not become ready within timeout. Start OTel Collector after Tempo is listening on :4319.'
}

foreach ($item in $scripts) {
    $path = Join-Path $PSScriptRoot $item.File
    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-File', $path
    )
    Write-Host "Started $($item.Name) in a new window."
    if ($item.Name -eq 'Loki') {
        Write-Host 'Waiting for Loki /ready before continuing...'
        Wait-LokiReady
    }
    elseif ($item.Name -eq 'Tempo') {
        Write-Host 'Waiting for Tempo /ready before continuing...'
        Wait-TempoReady
    }
    else {
        Start-Sleep -Seconds 1
    }
}

Write-Host ''
Write-Host 'Architecture phase 2 stack launch requested.'
Write-Host 'Prerequisites:'
Write-Host '  ops-api :8280, ecom-api Admin :8081, Portal :8085'
Write-Host '  ecom-api OTEL_ENABLED=true (optional, for OTLP traces/metrics/logs)'
Write-Host ''
Write-Host '  Prometheus       http://127.0.0.1:9090'
Write-Host '  Alertmanager     http://127.0.0.1:9093'
Write-Host '  Grafana          http://127.0.0.1:3000'
Write-Host '  Loki             http://127.0.0.1:3100'
Write-Host '  Tempo            http://127.0.0.1:3200'
Write-Host '  OTel Collector   OTLP :4317 / :4318'
Write-Host '  Promtail         http://127.0.0.1:9080'
Write-Host ''
Write-Host "Config directory: $root"
