# Research: Silver & Gold Layers — Financial Fundamental Pipeline

## Decision 1: JSON flattening strategy in BigQuery

**Decision**: Use `JSON_VALUE(raw_data, '$.field')` + `JSON_QUERY` for arrays, with `SAFE_CAST` and `NULLIF` sentinel stripping in intermediate models.

**Rationale**: The Bronze layer stores each Alpha Vantage response as a single JSON string in `raw_data STRING`. BigQuery's `JSON_VALUE` is the standard scalar extractor; `JSON_QUERY_ARRAY` / `UNNEST(JSON_EXTRACT_ARRAY(...))` handles the `annualReports` / `quarterlyReports` arrays. `SAFE_CAST` prevents query failure on malformed values. `NULLIF` chains strip sentinel strings (`'None'`, `'-'`, `'N/A'`, `''`) before casting.

**Alternatives considered**: Loading JSON into BigQuery native JSON type — rejected because the external table uses `STRING` format (CSV with `\x01` delimiter) and changing the source schema would break existing staging models.

---

## Decision 2: Deduplication approach

**Decision**: `ROW_NUMBER() OVER (PARTITION BY symbol, fiscaldateending, report_type ORDER BY ingest_date DESC, partition_day DESC, partition_month DESC)` with `WHERE rn = 1` in a final CTE, followed by `WHERE fiscaldateending IS NOT NULL`.

**Rationale**: The round-robin ingestion can re-ingest the same ticker multiple times across days (e.g., restatements or pipeline reruns). The most recent `ingest_date` represents the most up-to-date data. `partition_day/month` break ties deterministically. Filtering `fiscaldateending IS NOT NULL` after deduplication protects the grain without discarding valid quarterly records.

**Alternatives considered**: `QUALIFY ROW_NUMBER() = 1` (BigQuery supports this) — valid alternative, but the explicit CTE pattern is more readable and debuggable.

---

## Decision 3: YoY Revenue Growth window

**Decision**: `LAG(total_revenue, 4) OVER (PARTITION BY symbol, report_type ORDER BY fiscaldateending)` for quarterly; `LAG(total_revenue, 1)` for annual.

**Rationale**: Confirmed by `/speckit.clarify` Q1. `LAG(4)` for quarterly compares Q1-2025 with Q1-2024 (true YoY), not Q4-2024 (sequential). `LAG(1)` for annual is correct since periods are already 12 months apart.

**Alternatives considered**: `LAG(1)` for both — rejected (gives quarter-over-quarter, not year-over-year for quarterly data).

---

## Decision 4: Mart join anchor

**Decision**: `int_income_statement` as the driving (LEFT) table. All other intermediates (`int_balance_sheet`, `int_cash_flow`, `int_earning`, `int_overview`) are LEFT JOINed on `(symbol, fiscaldateending, report_type)` (overview joins only on `symbol`).

**Rationale**: Confirmed by `/speckit.clarify` Q4. Income statement is the most complete and consistently populated source — it is the primary source for profitability KPIs. Anchoring on it ensures every row in the mart has at minimum the revenue and net income fields needed for core KPIs.

**Alternatives considered**: FULL OUTER JOIN — rejected (produces rows with all KPIs NULL, pollutes the mart with unusable rows).

---

## Decision 5: Mart column scope

**Decision**: Mart includes only the columns needed to calculate the defined KPIs plus dimension/metadata columns. No raw column pass-through with `inc_*` / `bs_*` / `cf_*` prefixes.

**Rationale**: Confirmed by `/speckit.clarify` Q5. Keeps `fct_fundamental_kpis` focused and query-efficient. Analysts needing raw financials should query intermediate models directly.

**Columns in mart**:
- Dimensions: `symbol`, `fiscaldateending`, `report_type`, `reportedcurrency`, `ingest_date`
- From income statement: `total_revenue`, `net_income`, `ebitda_calc`, `ebit`
- From balance sheet: `total_shareholder_equity`, `total_current_assets`, `total_current_liabilities`, `net_debt`
- From cash flow: `operating_cashflow`, `free_cash_flow`
- From earning: `surprise_percentage` (as `earnings_surprise_pct`)
- From overview: `pe_ratio`, `ev_to_ebitda`, `sector`, `industry`, `country`, `exchange`, `overview_snapshot_date`
- KPIs: `roe`, `net_margin`, `ebitda_margin`, `net_debt_to_ebitda`, `current_ratio`, `quality_of_earnings`, `revenue_yoy_growth`

---

## Decision 6: dbt materialization

**Decision**: Intermediate = `view`; Mart = `table`.

**Rationale**: Intermediate models are transformations over external tables (already reading from GCS). Materializing as views avoids storage cost for intermediate results. The mart `fct_fundamental_kpis` must be a table for BI tool performance (no on-the-fly JSON parsing for every query).

---

## Decision 7: Overview join strategy in mart

**Decision**: `int_overview` is deduplicated to one row per `symbol` (most recent `ingest_date`) in the intermediate layer. The mart joins on `symbol` only (not on `fiscaldateending`), since overview is a point-in-time snapshot without a fiscal period dimension.

**Rationale**: The Alpha Vantage OVERVIEW endpoint returns current market data (P/E, EV/EBITDA), not historical per-period data. Joining on `symbol` alone correctly enriches all historical periods with the latest available market snapshot.
