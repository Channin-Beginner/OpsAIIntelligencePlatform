$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\paths.ps1"

if (-not (Test-Path $Observability.PromtailData)) {
    New-Item -ItemType Directory -Path $Observability.PromtailData -Force | Out-Null
}

if (-not (Test-Path $Observability.PromtailExe)) {
    throw "Promtail not found: $($Observability.PromtailExe)"
}

if (-not (Test-Path $Observability.EcomApiLogDir)) {
    Write-Warning "EcomAI log directory not found yet: $($Observability.EcomApiLogDir)"
    Write-Warning 'Start ecom-api with LOG_FILE_ENABLED=true to create admin.log / portal.log'
}

Write-Host 'Starting Promtail on :9080'
Write-Host "Log dir: $($Observability.EcomApiLogDir)"
Write-Host "Config: $($Observability.PromtailConfig)"

& $Observability.PromtailExe "-config.file=$($Observability.PromtailConfig)"
