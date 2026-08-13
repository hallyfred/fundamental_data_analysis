## Pipeline Financial Fundamental Analysis

###  Objective
This project aims to consolidate fragmented accounting and financial data—such as Company Overview, Income Statements, Balance Sheets, Cash Flow, and Earnings—to monitor and analyze the financial health of publicly listed companies over time.

Rather than just mirroring the Alpha Vantage API endpoints, the goal is to build an analytical foundation that calculates key business metrics (e.g., ROE, Net Margin, Free Cash Flow, and YoY Growth) by joining disparate financial statements into a unified, business-ready dimensional model.

### What does the pipeline do?
This pipeline acts as a modern data engineering engine. It extracts raw data from the Alpha Vantage API, loads the original JSON payloads into Google Cloud Storage (Data Lake), and orchestrates the transformation process into BigQuery.

To ensure reliability and analytical value, the pipeline:

- Enforces Data Quality: Uses Data Contracts (via Pydantic) during ingestion and robust testing (via dbt) to prevent schema drift and null anomalies.

- Cleans and Consolidates: Transforms unstructured JSON data into standardized staging tables.

- Models for Business: Joins distinct financial reports (Balance, Income, Cash Flow) into dimensional Marts (Gold layer) to automatically calculate historical fundamentalist KPIs.

#### Core Metrics & KPIs 
The objective of the dimensional modeling (Gold Layer) is not merely to mirror the Alpha Vantage endpoints, but to act as a KPI calculation engine. We selected the most critical metrics used by financial analysts to evaluate a company's health. 

This requires joining historical data from Balance Sheets, Income Statements, and Cash Flows, as well as applying SQL Window Functions to calculate period-over-period growth.

| Business Pillar | Selected Metric | What does it answer? | Data Source (dbt Join) |
| :--- | :--- | :--- | :--- |
| **1. Profitability** | **ROE (Return on Equity)** | Does the company generate good returns on shareholders' equity? | `Net Income` (Income Statement) / `Total Equity` (Balance Sheet) |
| | **Net Margin** | How much of the total revenue translates into actual profit? | `Net Income` / `Total Revenue` (Income Statement) |
| | **EBITDA Margin** | What is the company's core operational efficiency? | `EBITDA` / `Total Revenue` (Income Statement) |
| **2. Health & Risk** | **Net Debt / EBITDA** | Can the company easily pay off its debts using its operational cash? | `(Total Debt - Cash)` (Balance Sheet) / `EBITDA` (Income Statement) |
| | **Current Ratio** | Does the company have enough liquid assets to cover short-term obligations? | `Current Assets` / `Current Liabilities` (Balance Sheet) |
| **3. Cash Generation**| **Free Cash Flow (FCF)** | How much actual cash is left after capital expenditures (CapEx)? | `Operating Cash Flow` - `CAPEX` (Cash Flow) |
| | **Quality of Earnings** | Is the reported net income backed by actual cash flow, or is it an accounting maneuver? | `Operating Cash Flow` (Cash Flow) / `Net Income` (Income Statement) |
| **4. Growth** | **Revenue YoY Growth** | Are the company's sales growing compared to the exact same period last year? | Calculated via SQL `LAG()` over `Total Revenue` |
| | **Earnings Surprise %** | Does the company consistently beat market expectations? | `EARNINGS` endpoint (Directly from API) |
| **5. Valuation** | **P/E Ratio & EV/EBITDA** | Is the company currently overvalued or undervalued by the market? | `OVERVIEW` endpoint (Current snapshot) |

### API Rate Limiting & Orchestration Strategy

The Alpha Vantage free tier restricts usage to **25 API requests per day**. Since our pipeline relies on 5 distinct endpoints (`OVERVIEW`, `INCOME_STATEMENT`, `BALANCE_SHEET`, `CASH_FLOW`, and `EARNINGS`), we can process a maximum of **5 companies (tickers) per day**.

However, because fundamental financial data (like balance sheets and income statements) is only updated quarterly, querying the same companies every day is highly inefficient.

To maximize our API usage, we implemented a **Round-Robin Rotation Strategy** orchestrated by Apache Airflow:

1. **Static Ticker Pool:** We maintain a curated list of 35 target companies (tickers) managed via Airflow Variables.
2. **Daily Batching:** The list is divided into 7 distinct batches (5 tickers per batch).
3. **Automated Rotation:** The Airflow DAG dynamically selects the batch to process based on the current day of the week (e.g., Batch 1 on Monday, Batch 2 on Tuesday).

This approach ensures that all 35 companies are fully refreshed every 7 days without ever exceeding the daily API rate limit, making the ingestion process both resilient and cost-effective.