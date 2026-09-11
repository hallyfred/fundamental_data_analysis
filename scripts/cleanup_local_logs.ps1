param(
    [ValidateRange(1, 3650)]
    [int]$RetentionDays = 30,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$workspacePath = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$logPath = [System.IO.Path]::GetFullPath((Join-Path $workspacePath "logs"))
if (-not $logPath.StartsWith($workspacePath, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Resolved log path is outside the workspace: $logPath"
}
if (-not (Test-Path -LiteralPath $logPath)) {
    Write-Output "No local log directory found: $logPath"
    exit 0
}

$cutoff = (Get-Date).AddDays(-$RetentionDays)
$expired = @(Get-ChildItem -LiteralPath $logPath -File -Recurse | Where-Object { $_.LastWriteTime -lt $cutoff })
if (-not $DryRun) {
    foreach ($file in $expired) {
        Remove-Item -LiteralPath $file.FullName -Force
    }
}

Write-Output "Expired log files: $($expired.Count); retention_days=$RetentionDays; dry_run=$DryRun"
