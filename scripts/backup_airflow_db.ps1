param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "..\backups")
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Force -Path $outputPath | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupFile = Join-Path $outputPath "airflow_$timestamp.dump"
$containerFile = "/tmp/airflow_$timestamp.dump"

try {
    & docker exec fundamental_postgres pg_dump -U airflow -d airflow -Fc -f $containerFile
    if ($LASTEXITCODE -ne 0) { throw "pg_dump failed" }

    & docker cp "fundamental_postgres:$containerFile" $backupFile
    if ($LASTEXITCODE -ne 0) { throw "docker cp failed" }

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $backupFile).Hash
    Set-Content -LiteralPath "$backupFile.sha256" -Value "$hash  $([System.IO.Path]::GetFileName($backupFile))"
    Write-Output "Backup created: $backupFile"
}
finally {
    & docker exec fundamental_postgres rm -f $containerFile 2>$null
}
