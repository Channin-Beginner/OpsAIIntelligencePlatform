# Launch Prometheus, Alertmanager, and Grafana in separate PowerShell windows.
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent

$scripts = @(
    @{ Name = 'Prometheus'; File = 'start-prometheus.ps1' },
    @{ Name = 'Alertmanager'; File = 'start-alertmanager.ps1' },
    @{ Name = 'Grafana'; File = 'start-grafana.ps1' }
)

foreach ($item in $scripts) {
    $path = Join-Path $PSScriptRoot $item.File
    Start-Process powershell -ArgumentList @(
        '-NoExit',
        '-ExecutionPolicy', 'Bypass',
        '-File', $path
    )
    Write-Host "Started $($item.Name) in a new window."
    Start-Sleep -Seconds 1
}

Write-Host ''
Write-Host 'Observability stack launch requested.'
Write-Host 'Prerequisites: ops-api :8280, ecom-api Admin :8081, Portal :8085'
Write-Host '  Prometheus   http://127.0.0.1:9090'
Write-Host '  Alertmanager http://127.0.0.1:9093'
Write-Host '  Grafana      http://127.0.0.1:3000'
Write-Host ''
Write-Host "Config directory: $root"
