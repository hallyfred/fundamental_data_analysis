$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspacePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
Set-Location -LiteralPath $workspacePath

$deadline = (Get-Date).AddMinutes(5)
do {
    & docker info *> $null
    if ($LASTEXITCODE -eq 0) { break }
    Start-Sleep -Seconds 10
} while ((Get-Date) -lt $deadline)

if ($LASTEXITCODE -ne 0) { throw "Docker Desktop did not become available within five minutes" }

& docker compose up -d
if ($LASTEXITCODE -ne 0) { throw "Docker Compose startup failed" }

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "healthcheck_local.ps1")
if ($LASTEXITCODE -ne 0) { throw "Local stack healthcheck failed" }
