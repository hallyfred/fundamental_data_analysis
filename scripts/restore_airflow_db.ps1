param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $Force) {
    throw "Restore replaces the Airflow metadata database. Re-run with -Force after checking the backup."
}

$resolvedBackup = (Resolve-Path -LiteralPath $BackupFile).Path
$containerFile = "/tmp/airflow_restore.dump"

try {
    & docker compose stop airflow-scheduler airflow-webserver
    if ($LASTEXITCODE -ne 0) { throw "Could not stop Airflow services" }

    & docker cp $resolvedBackup "fundamental_postgres:$containerFile"
    if ($LASTEXITCODE -ne 0) { throw "docker cp failed" }

    & docker exec fundamental_postgres pg_restore -U airflow -d airflow --clean --if-exists --no-owner $containerFile
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }
}
finally {
    & docker exec fundamental_postgres rm -f $containerFile 2>$null
    & docker compose up -d airflow-webserver airflow-scheduler
}

Write-Output "Airflow metadata restored from: $resolvedBackup"
