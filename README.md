

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

The repository is structured to reflect this decoupled architecture, including our CI/CD workflows and containerization setup:

```text
fundamental_data_analysis/
├── .github/
│   └── workflows/    # CI/CD pipelines (GitHub Actions for Pytest & dbt)
├── src/
│   ├── extract/      # API connection logic and rate-limit handling
│   ├── transform/    # dbt project (models, macros, tests)
│   └── load/         # GCS to BigQuery loading routines
├── dags/             # Apache Airflow DAGs
├── tests/            # Pytest for Python modules
├── docker-compose.yml# Local infrastructure orchestration
├── Dockerfile        # Custom image build (Airflow + dbt)
└── requirements.txt  # Python dependencies

```

### Containerization & CI/CD Pipeline

To ensure reproducibility across environments and streamline deployments, this project heavily relies on Containerization and automated pipelines.

* **Containerization (Docker):** The entire stack—including Apache Airflow, Python extraction modules, and dbt—is fully containerized using Docker and Docker Compose. This ensures that the dependencies remain isolated.
* **Continuous Integration (CI):** On every Pull Request to the `main` branch, GitHub Actions triggers automatically. It runs `pytest` for the Python API connectors and performs a **dbt Slim CI** run (building and testing only modified models) to catch SQL errors before merging.
* **Continuous Deployment (CD):** Once the PR is approved, the CD pipeline automatically syncs the updated Airflow DAGs, Python scripts, and dbt models to the production environment.

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

1. **Static Ticker Pool:** We maintain a curated list of 35 target companies (tickers) managed via Airflow Variables.
2. **Daily Batching:** The list is divided into 7 distinct batches (5 tickers per batch).
3. **Automated Rotation:** The Airflow DAG dynamically selects the batch to process based on the current day of the week (e.g., Batch 1 on Monday, Batch 2 on Tuesday).

This approach ensures that all 35 companies are fully refreshed every 7 days without ever exceeding the daily API rate limit, making the ingestion process both resilient and cost-effective.

### Data Quality, Monitoring & Data Catalog

To maintain trust in the financial data without introducing the overhead of complex external governance tools, this pipeline relies on a lean, "code-first" governance approach:

* **Data Catalog & Documentation:** We leverage `dbt docs` as our centralized data catalog. It automatically parses our YAML files to generate a static, searchable website containing column-level descriptions, metric definitions, and data lineage graphs (DAGs) for the entire warehouse.
* **Pipeline Monitoring:** Apache Airflow acts as the control plane. We utilize Airflow's built-in SLA and callback mechanisms to send alerts (e.g., Slack/Email) upon task failures or if the Alpha Vantage API structure changes unexpectedly.
* **Data Quality Testing:** Over 40+ tests are executed dynamically via `dbt test` during the pipeline run. We enforce `not_null`, `unique`, and `accepted_values` tests on critical financial columns, ensuring that no corrupted API data propagates to the business layer.

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

The dbt project creates the BigQuery external tables automatically before each `dbt run`, using the external source definitions in `transformations/models/source.yml`. No manual table creation is required. The configured service account must have permission to create tables in the target dataset and read the GCS bucket.

To create or recreate only the external tables, run:

```bash
dbt run-operation dbt_external_tables.stage_external_sources --vars "ext_full_refresh: true"
```

