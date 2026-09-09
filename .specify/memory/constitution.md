<!--
SYNC IMPACT REPORT
==================
Version change  : 0.0.0 → 1.0.0 (initial ratification — full document creation)
Modified        : n/a (new document)
Added sections  : Core Principles (I–V), Stack & Constraints, Development Workflow, Governance
Removed sections: n/a
Deferred TODOs  : none — all placeholders resolved from repo context
-->

# Financial Fundamental Analysis Pipeline Constitution

## Core Principles

### I. Separation of Concerns (NON-NEGOTIABLE)

Each pipeline layer MUST have a single, explicit responsibility and MUST NOT bleed into adjacent
layers:

- **Staging**: creates BigQuery external tables pointing to GCS Bronze JSONs. MUST expose only
  `raw_data STRING` and Hive partition columns (`year`, `month`, `day`). MUST NOT parse, cast,
  or transform any field.
- **Intermediate (Silver)**: MUST perform all JSON flattening (`JSON_VALUE`), type casting
  (`SAFE_CAST`), sentinel-value treatment, deduplication, and derived-field calculation. MUST NOT
  calculate business KPIs.
- **Marts (Gold)**: MUST perform cross-statement joins and calculate business KPIs only. MUST NOT
  re-parse JSON or re-apply type casting already done in intermediate.
- **Extraction (Python)**: MUST handle API interaction, Pydantic validation, GCS upload, and
  round-robin scheduling. MUST NOT write to BigQuery directly.

Rationale: boundary violations create untestable code, hidden data loss, and maintenance
debt that compounds with each new endpoint or KPI added.

---

### II. Explicit Grain Contract

Every dbt model MUST declare its grain — the minimal set of columns that uniquely identify a row
— as a comment at the top of the SQL file before any CTE.

- Intermediate models for financial statements: grain is `(symbol, fiscaldateending, report_type)`.
- Intermediate model for overview: grain is `(symbol)` — one row per company, most-recent snapshot.
- Mart `fct_fundamental_kpis`: grain is `(symbol, fiscaldateending, report_type)`.

Cross-statement joins in the mart MUST use LEFT JOIN anchored on the income statement so that
rows are never silently discarded when a balance sheet or cash flow record is absent for a given
period. Any join that could multiply rows MUST be preceded by a deduplication CTE or a documented
justification.

Rationale: financial statements have different semantic grains (period flow vs. point-in-time
snapshot). Undocumented grain assumptions cause silent fan-outs that corrupt KPI calculations.

---

### III. Safe-by-Default Data Handling

All type conversions and arithmetic MUST be safe — they MUST return `NULL` on failure rather than
raising an error or returning a misleading value:

- Use `SAFE_CAST(... AS INT64 / NUMERIC)` for all numeric coercions.
- Use `SAFE.PARSE_DATE('%Y-%m-%d', ...)` for all date coercions.
- Strip sentinel values (`'None'`, `'-'`, `'N/A'`, `''`) via `NULLIF` chains before casting.
- Use `SAFE_DIVIDE(numerator, denominator)` for all KPI divisions — never `/` directly.
- Preserve `fiscaldateending_raw STRING` alongside the cast `DATE` column in every intermediate
  model for auditability.

No model MUST discard a row solely because a field fails to cast. The row MUST be retained with
`NULL` in the affected column so anomalies surface through dbt tests rather than disappearing.

Rationale: the Alpha Vantage API returns HTTP 200 with sentinel strings for absent data.
Silent data loss at cast time is undetectable and corrupts downstream KPI calculations.

---

### IV. Catalog-First Documentation

Every dbt model MUST have a co-located `.yml` file that documents:

- A `description` for the model itself.
- `name`, `data_type`, and `description` for every column.
- All dbt tests applicable to that model (e.g., `not_null`, `accepted_values`,
  `dbt_utils.unique_combination_of_columns`).

`dbt docs generate` MUST produce a complete, navigable lineage graph with no undocumented nodes.
Models without a `.yml` file MUST be treated as incomplete and MUST NOT be merged to `main`.

Rationale: the dbt docs site is the project's data catalog. Undocumented models erode trust
and make the catalog useless as a governance artifact.

---

### V. Idempotent & Observable Operations

All pipeline operations — extraction, loading, and transformation — MUST be idempotent:

- Re-running the Airflow DAG for the same day MUST NOT produce duplicate records in BigQuery.
- Deduplication in intermediate models MUST use `ROW_NUMBER() OVER (PARTITION BY symbol,
  fiscaldateending, report_type ORDER BY ingest_date DESC, partition_day DESC, partition_month DESC)`
  and retain only `row_num = 1`.
- A GCS upload MUST be confirmed successful before the local temp file is deleted and before
  the blob path is appended to any output list.
- All extraction modules MUST use structured JSON logging (no bare `print()`), including:
  `run_id`, `endpoint`, `ticker`, `status`, `duration_ms`, `record_count`, `rejection_reason`.

Rationale: the round-robin strategy processes each ticker once every 7 days. A duplicate or
lost record cannot be corrected until the next weekly cycle, making idempotency critical.

---

## Stack & Constraints

**Technology stack** (MUST NOT be replaced without a constitution amendment):

| Layer | Technology | Constraint |
|---|---|---|
| Data Lake | Google Cloud Storage | Bronze JSONs partitioned `year=/month=/day=` (Hive) |
| Data Warehouse | BigQuery (`projetodbt-479518`, dataset `alphavantage`) | External tables via `dbt_external_tables` |
| Transformation | dbt (`src/transformations/`) | Profile `transformations`; project name `transformations` |
| Orchestration | Apache Airflow | DAGs in `dags/`; round-robin ticker rotation |
| Extraction | Python + Pydantic | 5 endpoints; 25 req/day free-tier limit; max 5 tickers/day |
| Containerization | Docker + Docker Compose | Full stack containerized including Airflow + dbt |
| CI/CD | GitHub Actions | Slim CI on PR: `pytest` + `dbt build --select state:modified+` |

**API Rate Limit policy**: Alpha Vantage free tier = 25 requests/day = 5 tickers × 5 endpoints.
The Airflow DAG MUST use `get_symbols_for_day()` to select only the daily batch — iterating all
35 tickers in a single run is a hard violation of this constitution.

**Secrets policy**: API keys, GCP credentials, and service account JSON MUST NEVER appear in
source code, dbt models, logs, test fixtures, or documentation. Use environment variables and
Docker secrets only.

---

## Development Workflow

**Branch strategy**: all changes MUST be developed on a feature branch. Direct pushes to `main`
are prohibited. PRs MUST pass CI (pytest + dbt slim CI) before merge.

**dbt execution order** (MUST be respected):

```
dbt run-operation dbt_external_tables.stage_external_sources   # recreate external tables
dbt run --select staging                                        # views only, no-op if unchanged
dbt run --select intermediate                                   # Silver: parse + deduplicate
dbt run --select marts                                          # Gold: join + KPIs
dbt test                                                        # all layers
```

**Model naming convention**:

- Staging: `stg_<endpoint>` (existing, unchanged)
- Intermediate: `int_<endpoint>`
- Marts: `fct_<subject>` (e.g., `fct_fundamental_kpis`)

**Test gate**: `dbt test` MUST pass for all models before a PR is mergeable. A failing
`not_null` or `unique_combination_of_columns` test on a key column is a blocking defect.
`NULL` values in KPI columns (from `SAFE_DIVIDE`) are valid data and MUST NOT be covered
by `not_null` tests.

**Adding a new KPI**: the KPI MUST be:
1. Defined in `requirements.md` with formula, units, and NULL-handling rule.
2. Derived-field components calculated in the appropriate intermediate model.
3. Final calculation placed in `fct_fundamental_kpis.sql` using `SAFE_DIVIDE`.
4. Documented in `fct_fundamental_kpis.yml` with formula and description.
5. Covered by a reconciliation check against a known sample value before merging.

---

## Governance

This constitution supersedes all other project conventions, README sections, and inline comments
where they conflict. In case of ambiguity, this document is the authoritative source.

**Amendment procedure**:
1. Open a PR with the proposed change to `.specify/memory/constitution.md`.
2. Increment `CONSTITUTION_VERSION` according to semantic versioning (MAJOR for principle
   removals or redefinitions, MINOR for new principles or sections, PATCH for clarifications).
3. Update `LAST_AMENDED_DATE` to the merge date.
4. PR description MUST explain the rationale and list affected downstream artifacts.

**Compliance review**: every PR that touches `src/transformations/models/` MUST be checked
against Principles I–V before approval. Reviewers MUST explicitly confirm compliance in the
PR comment.

**Versioning policy**:
- MAJOR: backward-incompatible governance change (principle removal, grain contract redefinition,
  layer responsibility reassignment).
- MINOR: new principle, new section, or materially expanded guidance.
- PATCH: clarifications, wording, typo fixes, non-semantic refinements.

**Version**: 1.0.0 | **Ratified**: 2026-09-07 | **Last Amended**: 2026-09-07
