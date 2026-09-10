

## Pipeline Financial Fundamental Analysis

### Objective
This project aims to consolidate fragmented accounting and financial data—such as Company Overview, Income Statements, Balance Sheets, Cash Flow, and Earnings—to monitor and analyze the financial health of publicly listed companies over time.

Rather than just mirroring the Alpha Vantage API endpoints, the goal is to build an analytical foundation that calculates key business metrics (e.g., ROE, Net Margin, Free Cash Flow, and YoY Growth) by joining disparate financial statements into a unified, business-ready dimensional model.

### What does the pipeline do?
This pipeline acts as a modern data engineering engine. It extracts raw data from the Alpha Vantage API, loads the original JSON payloads into Google Cloud Storage (Data Lake), and orchestrates the transformation process into BigQuery.

To ensure reliability and analytical value, the pipeline:

- **Enforces Data Quality:** Uses Data Contracts (via Pydantic) during ingestion and robust testing (via dbt) to prevent schema drift and null anomalies.
- **Cleans and Consolidates:** Transforms unstructured JSON data into standardized staging tables.
- **Models for Business:** Joins distinct financial reports (Balance, Income, Cash Flow) into dimensional Marts (Gold layer) to automatically calculate historical fundamentalist KPIs.

### System Architecture & Project Structure

The pipeline is built with a **Separation of Concerns** principle in mind, isolating the extraction logic from the transformation engine. The architecture follows a Medallion approach (Bronze -> Silver -> Gold), leveraging a Modern Data Stack:

*   **Extraction (Python):** Modular scripts interact with the Alpha Vantage API. Data contracts are enforced using Pydantic before the data hits the lake.
*   **Data Lake (GCS):** Stores the raw JSON payloads (Bronze Layer), ensuring we always have an immutable historical record to replay if needed.
*   **Data Warehouse (BigQuery):** Acts as the compute engine for analytics. 
*   **Transformation (dbt):** Handles all business logic, data cleansing (Silver Layer), and metric calculations (Gold Layer).
*   **Orchestration (Airflow):** Manages dependencies, scheduling, and the round-robin API strategy.

The repository is structured to reflect this architecture and its validation workflow:

```text
fundamental_data_analysis/
├── .github/
│   └── workflows/    # GitHub Actions validation (Ruff, Pytest, and dbt)
├── config/           # Environment-backed settings and the 35-ticker weekly pool
├── specs/            # Feature specifications and execution checklist
├── src/
│   ├── extract/          # API connection logic and rate-limit handling
│   ├── orchestration/    # Round-robin planning and business timezone rules
│   ├── transformations/  # dbt project (models, macros, tests)
│   └── load/             # GCS to BigQuery loading routines
├── dags/             # Apache Airflow DAGs
├── tests/            # Pytest for Python modules
├── docker-compose.yml# Local infrastructure orchestration
├── Dockerfile        # Custom image build (Airflow + dbt)
└── requirements.txt  # Python dependencies

```

### Containerization & CI/CD Pipeline

To ensure reproducibility across environments and streamline deployments, this project heavily relies on Containerization and automated pipelines.

* **Containerization (Docker):** The entire stack—including Apache Airflow, Python extraction modules, and dbt—is fully containerized using Docker and Docker Compose. This ensures that the dependencies remain isolated.
* **Continuous Integration (CI):** Pull requests to `main` and pushes to `main` or `dev` run Ruff, the complete mocked Python test suite, DAG integrity checks, all native Silver/Gold dbt unit tests, and a build with data-quality tests in `alphavantage_ci`.
* **Release validation:** A successful push to `main` records the validation result. Production deployment is not configured in this repository.

### Core Metrics & KPIs

The objective of the dimensional modeling (Gold Layer) is not merely to mirror the Alpha Vantage endpoints, but to act as a KPI calculation engine. We selected the most critical metrics used by financial analysts to evaluate a company's health.

This requires joining historical data from Balance Sheets, Income Statements, and Cash Flows, as well as applying SQL Window Functions to calculate period-over-period growth.

| Business Pillar | Selected Metric | What does it answer? | Data Source (dbt Join) |
| --- | --- | --- | --- |
| **1. Profitability** | **ROE (Return on Equity)** | Does the company generate good returns on shareholders' equity? | `Net Income` (Income Statement) / `Total Equity` (Balance Sheet) |
|  | **Net Margin** | How much of the total revenue translates into actual profit? | `Net Income` / `Total Revenue` (Income Statement) |
|  | **EBITDA Margin** | What is the company's core operational efficiency? | `EBITDA` / `Total Revenue` (Income Statement) |
| **2. Health & Risk** | **Net Debt / EBITDA** | Can the company easily pay off its debts using its operational cash? | `(Total Debt - Cash)` (Balance Sheet) / `EBITDA` (Income Statement) |
|  | **Current Ratio** | Does the company have enough liquid assets to cover short-term obligations? | `Current Assets` / `Current Liabilities` (Balance Sheet) |
| **3. Cash Generation** | **Free Cash Flow (FCF)** | How much actual cash is left after capital expenditures (CapEx)? | `Operating Cash Flow` - `CAPEX` (Cash Flow) |
|  | **Quality of Earnings** | Is the reported net income backed by actual cash flow, or is it an accounting maneuver? | `Operating Cash Flow` (Cash Flow) / `Net Income` (Income Statement) |
| **4. Growth** | **Revenue YoY Growth** | Are the company's sales growing compared to the exact same period last year? | Calculated via SQL `LAG()` over `Total Revenue` |
|  | **Earnings Surprise %** | Does the company consistently beat market expectations? | `EARNINGS` endpoint (Directly from API) |
| **5. Valuation** | **P/E Ratio & EV/EBITDA** | Is the company currently overvalued or undervalued by the market? | `OVERVIEW` endpoint (Current snapshot) |

### Data Modeling: The "One Big Table" (OBT) Approach

For the Gold Layer (presentation), we purposefully opted for a **One Big Table (OBT)** architecture rather than a traditional Star Schema. This architectural decision was driven by three main factors:

1. **Columnar Database Optimization:** Modern cloud data warehouses like BigQuery are highly optimized for scanning wide, denormalized tables rather than executing complex `JOIN` operations across multiple dimensions.
2. **Granularity Resolution:** Financial statements operate on different logical grains. A Balance Sheet is a snapshot in time, whereas an Income Statement covers a period. Calculating a metric like ROE (Net Income / Total Equity) requires cross-statement math. By resolving these grains within dbt and outputting a single OBT, we guarantee a "Single Source of Truth".
3. **Self-Service BI Simplicity:** An OBT abstracts the underlying complexity. End-users or financial analysts connecting via BI tools can simply drag and drop dimensions (Ticker, Quarter, Sector) and pre-calculated metrics without worrying about bi-directional filtering or join traps.

### API Rate Limiting & Orchestration Strategy

The Alpha Vantage free tier restricts usage to **25 API requests per day**. Since our pipeline relies on 5 distinct endpoints (`OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`, and `EARNINGS`), we can process a maximum of **5 companies (tickers) per day**.

However, because fundamental financial data (like balance sheets and income statements) is only updated quarterly, querying the same companies every day is highly inefficient.

To maximize our API usage, we implemented a **Round-Robin Rotation Strategy** orchestrated by Apache Airflow:

1. **Static Ticker Pool:** A curated list of 35 target companies is versioned in `config/config.py` as seven weekday groups.
2. **Daily Batching:** The list is divided into 7 distinct batches (5 tickers per batch).
3. **Automated Rotation:** The Airflow DAG selects the batch from `data_interval_end` in `America/Sao_Paulo`, making retries for the same interval deterministic.
4. **Strict Budget and Failure Gate:** The five endpoints run serially with one HTTP attempt each. A rate limit, quarantine, or partial batch fails the task and blocks dbt and all remaining API calls.

This approach ensures that all 35 companies are fully refreshed every 7 days without ever exceeding the daily API rate limit, making the ingestion process both resilient and cost-effective.

### Data Quality, Monitoring & Data Catalog

To maintain trust in the financial data without introducing the overhead of complex external governance tools, this pipeline relies on a lean, "code-first" governance approach:

* **Data Catalog & Documentation:** We leverage `dbt docs` as our centralized data catalog. It automatically parses our YAML files to generate a static, searchable website containing column-level descriptions, metric definitions, and data lineage graphs for the entire warehouse.
* **Pipeline Monitoring:** Apache Airflow exposes task state and dependency failures. Extraction logs record the run, endpoint, planned/completed/failed/pending tickers, planned calls, and interruption reason; metadata logs are uploaded to GCS.
* **Data Quality Testing:** The dbt project defines 30 unit tests and 27 data tests. Key columns use `not_null`, `unique`, `accepted_values`, and compound-grain tests so invalid data blocks the Gold completion gate.

### How to Run Locally

If you want to spin up this project on your local machine, follow the steps below.

#### Prerequisites

Before you begin, ensure you have the following installed and configured:

* **Docker** and **Docker Compose**.
* An **Alpha Vantage Free API Key** (Get it [here](https://www.alphavantage.co/support/#api-key)).
* A **Google Cloud Platform (GCP)** account with BigQuery and Google Cloud Storage enabled.
* A GCP **Service Account** with roles: `BigQuery Admin` and `Storage Admin`, with its JSON key downloaded.

#### Quickstart

**1. Clone the repository:**

```bash
git clone [https://github.com/yourusername/fundamental_data_analysis.git](https://github.com/yourusername/fundamental_data_analysis.git)
cd fundamental_data_analysis

```

**2. Configure Environment Variables:**
Create a `.env` file in the root directory. You can copy the provided `.env.example` file:

```bash
cp .env.example .env

```

Update the `.env` file with your specific credentials:

```env
ALPHA_VANTAGE_API_KEY=your_api_key_here
GCP_PROJECT_ID=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=/opt/airflow/config/gcp_credentials.json

```

**3. Provide GCP Credentials:**
Place your downloaded Service Account JSON key inside the `config/` directory and rename it to `gcp_credentials.json` (this folder is mapped into the Docker container).

**4. Build and Start the Infrastructure:**
Initialize the Airflow environment and spin up the containers:

```bash
docker-compose up -d --build

```

**5. Access the Orchestrator:**
Once the containers are healthy, open your browser and navigate to:

* **Airflow UI:** `http://localhost:8080` (Default login: `airflow` / `airflow`)

From the Airflow UI, you can unpause the DAGs, monitor the round-robin API ingestion, and watch the dbt transformations populate your BigQuery datasets.

#### External tables

The dbt project creates the BigQuery external tables automatically before each `dbt run`, using the external source definitions in `src/transformations/models/source.yml`. No manual table creation is required. The configured service account must have permission to create tables in the target dataset and read the GCS bucket.

To create or recreate only the external tables, run:

```bash
dbt run-operation dbt_external_tables.stage_external_sources --project-dir src/transformations --vars "ext_full_refresh: true"
```



### Silver models and validation

The five `intermediate` views parse the staging JSON payloads, normalize numeric
sentinels, preserve the original fiscal date, and retain the latest ingestion per
`(symbol, fiscaldateending, report_type)`. `int_overview` instead retains the latest
snapshot per `symbol`. Each SQL model has a co-located YAML column catalog, data
quality tests, and native dbt unit tests with synthetic JSON inputs.

Silver exposes every scalar field declared in `src/extract/contract.py`, including
all annual and quarterly report fields. Column metadata (`config.meta.source_field`)
records the original JSON key, including API aliases. The CI contract coverage
check detects missing fields, type mismatches, and missing full-payload test
assertions when an extraction contract changes.

Following `.specify/memory/constitution.md`, invalid fiscal dates remain `NULL`
and fail the `not_null` quality gate instead of disappearing. This takes precedence
over the older Kiro requirement to filter those records. Numeric conversion failures
remain `NULL`; derived sums and differences also return `NULL` on overflow.

```bash
dbt deps --project-dir src/transformations --profiles-dir src/transformations
dbt parse --project-dir src/transformations --profiles-dir src/transformations
dbt test --select "intermediate,test_type:unit" --project-dir src/transformations --profiles-dir src/transformations --target ci
dbt build --select +intermediate --exclude test_type:unit --project-dir src/transformations --profiles-dir src/transformations --target ci
```

The GitHub workflow runs these checks using the `ci` target (`alphavantage_ci`),
serializing dbt jobs that share that dataset. This target does not recreate production
external tables. Integration checks read the existing Bronze external tables in
`projetodbt-479518.alphavantage`; these must already exist. The CI service account
needs permission to run BigQuery jobs, create/update the CI dataset and views, and
read the Bronze external tables and their GCS objects. Configure `GCP_PROJECT_ID`
and `GCP_SA_KEY` in GitHub Actions; locally set `GOOGLE_APPLICATION_CREDENTIALS`.
The unit fixtures mock staging inputs, but executing native dbt Core unit tests still
requires a BigQuery connection. See the [dbt unit test documentation](https://docs.getdbt.com/docs/build/unit-tests).


### Gold mart: fundamental KPIs

`src/transformations/models/marts/fct_fundamental_kpis.sql` creates a table with
29 documented columns: statement keys, ingestion/snapshot metadata, the eight
financial inputs used by the KPIs, and eleven calculated or inherited metrics.
Income statement anchors LEFT JOINs on `(symbol, fiscaldateending, report_type)`;
overview joins on `symbol`. Missing statements leave NULL metrics while retaining
the income row. Periods found only in other statements are excluded.

ROE uses closing equity; EBITDA ratios use the reported period, without TTM or
annualization. Margins and YoY growth are fractions (0.10 means 10%); earnings
surprise follows the API percentage (6.25 means 6.25%). Overview valuation always
reflects the latest snapshot, identified by `overview_snapshot_date`, even for
historical periods. YoY uses LAG(4) quarterly and LAG(1) annual and assumes
contiguous reporting periods. No currency conversion is performed.

KPI arithmetic promotes integer inputs using `NUMERIC '1'` before safe division
and subtraction, preserving the NUMERIC output contract and avoiding integer
subtraction overflow. See [BigQuery safe arithmetic](https://docs.cloud.google.com/bigquery/docs/reference/standard-sql/mathematical_functions#safe_divide).

```bash
# Native dbt unit tests with synthetic inputs (requires BigQuery credentials):
dbt run-operation prepare_ci_schema --project-dir src/transformations --profiles-dir src/transformations --target ci
dbt test --select "marts,test_type:unit" --project-dir src/transformations --profiles-dir src/transformations --target ci
# Build ancestors, the Gold table and data quality tests in the CI dataset:
dbt build --select +marts --exclude test_type:unit --project-dir src/transformations --profiles-dir src/transformations --target ci
```

The GitHub workflow runs both Silver and Gold unit tests, followed by the full
`+marts` dependency graph and its data quality checks. The CI service account also
needs permission to create/update tables in `alphavantage_ci`. The guarded
`prepare_ci_schema` macro creates the CI dataset if needed before unit tests;
it refuses to run with a target other than `ci`.

The final BigQuery validation on 2026-09-10 built all five Silver views and the
Gold table and passed all 30 unit tests and 27 data tests. The Gold grain check
returned zero duplicate `(symbol, fiscaldateending, report_type)` groups.
