{% docs __overview__ %}

# Fundamental Data Analysis Pipeline

This dbt project transforms validated Alpha Vantage financial data from the Bronze layer into analytics-ready Silver views and a Gold KPI mart in BigQuery.

## Architecture

| Layer | dbt resources | Purpose |
| --- | --- | --- |
| Bronze | Five external sources | Validated JSON payloads stored in date-partitioned Google Cloud Storage paths |
| Staging | Five views | Expose raw JSON and Hive ingestion partitions |
| Silver | Five intermediate views | Normalize types, remove API sentinel values, retain invalid dates for quality gates, and deduplicate the latest ingestion |
| Gold | `fct_fundamental_kpis` | Join financial statements and publish fundamental KPIs at `(symbol, fiscaldateending, report_type)` grain |

Silver remains materialized as views so it always reflects the current Bronze partitions without maintaining another stored copy. The Gold mart uses a full rebuild to recalculate window functions, late-arriving periods, and historical rows enriched by the latest overview snapshot. BigQuery partitions the Gold table by `fiscaldateending` and clusters it by `symbol` and `report_type`.

## Fundamental KPIs

The Gold mart publishes profitability, financial risk, liquidity, cash generation, earnings quality, growth, earnings surprise, and valuation metrics. Calculations use BigQuery safe arithmetic so zero denominators, missing statements, and numeric overflow produce `NULL` instead of incorrect values or failed builds.

## Round-robin ingestion

Apache Airflow selects one deterministic batch of five companies per business date. Five Alpha Vantage endpoints produce at most 25 requests per daily run. Watermarks prevent duplicate Bronze uploads, while incomplete batches, rate limits, quarantines, and extraction failures block downstream dbt execution.

## Quality and traceability

- Pydantic contracts validate source payloads before Bronze storage.
- Every scalar extraction-contract field is represented in Silver.
- Native dbt unit tests validate transformations with synthetic inputs.
- Data tests enforce keys, accepted report types, non-null business identifiers, and Gold grain uniqueness.
- GitHub Actions validates Python, Airflow, Docker, dbt, and data-quality behavior before release.

## Documentation scope

This site is the technical catalog for dbt sources, models, columns, tests, model SQL, and lineage. Live warehouse statistics and environment-specific relation metadata are intentionally excluded. Project setup and operating procedures remain in the repository:

- [Project README](https://github.com/hallyfred/fundamental_data_analysis#readme)
- [Local production runbook](https://github.com/hallyfred/fundamental_data_analysis/blob/main/docs/local-production-runbook.md)
- [Round-robin production validation](https://github.com/hallyfred/fundamental_data_analysis/blob/main/docs/round-robin-production-validation.md)
- [Silver and Gold specification](https://github.com/hallyfred/fundamental_data_analysis/tree/main/specs/silver-gold-layers)

{% enddocs %}
