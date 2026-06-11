$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

if (-not (Test-Path $Observability.GrafanaExe)) {
    throw "Grafana not found: $($Observability.GrafanaExe)"
}

$env:GF_PATHS_HOME = $Observability.GrafanaHome
$env:GF_PATHS_PROVISIONING = $Observability.ProvisioningDir
$env:GF_SERVER_HTTP_PORT = '3000'

Write-Host 'Starting Grafana on :3000'
Write-Host "Provisioning: $($Observability.ProvisioningDir)"
Write-Host 'Default login: admin / admin (change password on first login)'

Set-Location $Observability.GrafanaHome
& $Observability.GrafanaExe
