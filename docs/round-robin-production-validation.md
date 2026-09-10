# Round-robin production validation

Use this checklist once the Alpha Vantage daily quota has reset. A previous controlled run reached the quota on 2026-09-10, so no additional API call may be made on that date.

## Entry conditions

- The release commit and `fundamental-airflow:2.9.3` image ID are recorded.
- `scripts/healthcheck_local.ps1` passes and the DAG is paused.
- The Alpha Vantage quota is confirmed available before 06:00 `America/Sao_Paulo`.
- No manual extractor or competing client will use the same API key during the observation window.

## Controlled run and seven-day cycle

Unpause `financial_pipeline` for the first scheduled run. Do not add manual retries on a failed or rate-limited day. For each run, record the Airflow logical date, the five expected tickers, the actual tickers, task result, logical API call count, GCS data objects created or skipped by the watermark, quarantine objects, dbt result, and incident reference.

| Cycle day | Logical date | Expected tickers | Actual tickers | Calls (max 25) | GCS result | dbt result | Status |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| 1 |  |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |  |
| 4 |  |  |  |  |  |  |  |
| 5 |  |  |  |  |  |  |  |
| 6 |  |  |  |  |  |  |  |
| 7 |  |  |  |  |  |  |  |

Accept the cycle only when all 35 configured tickers appear exactly once across the seven logical dates, each endpoint runs serially, no day exceeds 25 calls, every successful batch reaches the dbt tests, and no partial watermark is committed after failure.

## Day-eight idempotency check

Day eight naturally selects the same ticker batch as day one. Before that run, record the Gold row count and duplicate count at grain `(symbol, fiscaldateending, report_type)`. After the run and dbt completion, verify:

- unchanged fiscal data is skipped by each endpoint watermark rather than creating another GCS data object;
- endpoint metadata records the skip and reports no partial batch;
- the Gold grain still has zero duplicate keys;
- unchanged source data does not increase the Gold row count;
- the day-eight ticker set equals the day-one ticker set.

Attach the Airflow run IDs, GCS object listings or counts, dbt `run_results.json`, and BigQuery query results to the release record. Mark T042/T059 complete only after all evidence above is present.
