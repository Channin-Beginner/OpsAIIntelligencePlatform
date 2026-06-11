$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

if (-not (Test-Path $Observability.AlertmanagerData)) {
    New-Item -ItemType Directory -Path $Observability.AlertmanagerData -Force | Out-Null
}

if (-not (Test-Path $Observability.AlertmanagerExe)) {
    throw "Alertmanager not found: $($Observability.AlertmanagerExe)"
}

Write-Host 'Starting Alertmanager on :9093'
Write-Host 'Webhook: http://127.0.0.1:8280/webhooks/alertmanager'

& $Observability.AlertmanagerExe `
    --config.file="$($Observability.AlertmanagerConfig)" `
    --web.listen-address=":9093" `
    --storage.path="$($Observability.AlertmanagerData)"
