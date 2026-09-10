# Local Production Runbook

This project runs its production Airflow stack on the local Windows host through Docker Desktop. GitHub Actions validates changes; it does not deploy or control the local containers.

## Host prerequisites

- Configure Docker Desktop to start when Windows starts.
- Keep the host powered, connected to the internet, and awake before the 06:00 `America/Sao_Paulo` schedule.
- Keep `.env` and `gcp_key.json` only on the host. Never commit either file.
- Restrict access to the Windows account and enable disk encryption because the host contains production credentials.

On the validated host, Docker Desktop is registered to start with Windows and the active High Performance power plan has sleep disabled on AC and battery. Recheck these settings after Windows or Docker Desktop upgrades.

## Environment

Copy `.env.example` to `.env` and replace every placeholder. Generate an Airflow Fernet key with:

```powershell
docker run --rm apache/airflow:2.9.3-python3.11 python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Use `DBT_TARGET=prod` for the scheduled DAG. The `prod` target writes to `alphavantage`; local development commands default to `dev` and write to `alphavantage_dev`. CI explicitly uses `ci` and writes to `alphavantage_ci`.

`ALERT_WEBHOOK_URL` is optional. When configured, failed Airflow tasks send a structured HTTP POST. When empty, failures remain available in Airflow and structured logs without network notification.

## Release

Run from a clean `main` branch after the `dev -> main` pull request and GitHub Actions release validation pass:

```powershell
git checkout main
git pull --ff-only origin main
.\scripts\backup_airflow_db.ps1
docker compose build --pull
docker compose up -d --remove-orphans
.\scripts\healthcheck_local.ps1
```

Open Airflow only through `http://127.0.0.1:<AIRFLOW_WEBSERVER_PORT>` (8080 by default). Keep the DAG paused until the controlled quota and idempotency validation is complete. Record the deployed commit with `git rev-parse HEAD`.

## Daily checks

```powershell
.\scripts\healthcheck_local.ps1
docker compose logs --since 24h airflow-scheduler
```

Confirm that the expected five-ticker batch ran once, used at most 25 API calls, produced all five endpoint files, completed dbt tests, and did not report a rate limit. Docker uses bounded local log files; extraction audit logs continue to be uploaded to GCS.

Clean Airflow task logs older than 30 days on a weekly schedule. Preview before removal:

```powershell
.\scripts\cleanup_local_logs.ps1 -RetentionDays 30 -DryRun
.\scripts\cleanup_local_logs.ps1 -RetentionDays 30
```

After a reboot or Docker Desktop update, start and validate the stack with:

```powershell
.\scripts\start_local_stack.ps1
```

## Backup and restore

Create a compressed PostgreSQL dump before every release and periodically copy `backups/` to protected storage:

```powershell
.\scripts\backup_airflow_db.ps1
```

Restore only when the current metadata database is unusable. The restore script stops Airflow writers and requires an explicit flag:

```powershell
.\scripts\restore_airflow_db.ps1 -BackupFile .\backups\airflow_YYYYMMDD_HHMMSS.dump -Force
.\scripts\healthcheck_local.ps1
```

## Rollback

Save the failed commit and return to the previously recorded release commit:

```powershell
git status --short
git checkout <previous-release-commit>
docker compose build
docker compose up -d --remove-orphans
.\scripts\healthcheck_local.ps1
```

Restore the PostgreSQL dump only when the failed release changed metadata incompatibly. Ordinary application rollbacks should retain the current volume.

## Incident response

For a rate-limit alert, do not manually retry on the same calendar day. Preserve the Airflow run and GCS metadata logs, verify that no partial watermark was committed, and schedule one controlled run after the quota resets. For repeated container restarts, run `docker compose ps`, inspect the bounded Compose logs, and keep the DAG paused until the cause is resolved.
