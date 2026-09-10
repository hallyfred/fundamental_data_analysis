$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$services = @(& docker compose ps --format json | ForEach-Object { $_ | ConvertFrom-Json })
if ($LASTEXITCODE -ne 0) { throw "Could not inspect Docker Compose services" }

$required = @("airflow-webserver", "airflow-scheduler", "postgres")
foreach ($serviceName in $required) {
    $service = $services | Where-Object { $_.Service -eq $serviceName }
    if (-not $service -or $service.State -ne "running") {
        throw "Service is not running: $serviceName"
    }
    if ($service.Health -and $service.Health -ne "healthy") {
        throw "Service is not healthy: $serviceName ($($service.Health))"
    }
}

$webserverPort = 8080
$envFile = Join-Path $PSScriptRoot "..\.env"
if (Test-Path -LiteralPath $envFile) {
    $portEntry = Get-Content -LiteralPath $envFile | Where-Object { $_ -match "^AIRFLOW_WEBSERVER_PORT=" } | Select-Object -Last 1
    if ($portEntry) { $webserverPort = [int](($portEntry -split "=", 2)[1]) }
}
Invoke-RestMethod -Uri "http://127.0.0.1:$webserverPort/health" -TimeoutSec 15 | Out-Null
& docker exec fundamental_airflow_webserver airflow db check
if ($LASTEXITCODE -ne 0) { throw "Airflow database check failed" }
& docker exec fundamental_airflow_webserver airflow dags list-import-errors
if ($LASTEXITCODE -ne 0) { throw "Airflow DAG import check failed" }

Write-Output "Local Airflow stack is healthy."
