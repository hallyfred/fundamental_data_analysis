{{ config(materialized='view') }}

{% set report_fields = [
    ("fiscalDateEnding", "DATE"), ("reportedCurrency", "STRING"),
    ("grossProfit", "INT64"), ("totalRevenue", "INT64"), ("costOfRevenue", "INT64"),
    ("costofGoodsAndServicesSold", "INT64"), ("operatingIncome", "INT64"),
    ("sellingGeneralAndAdministrative", "INT64"), ("researchAndDevelopment", "INT64"),
    ("operatingExpenses", "INT64"), ("investmentIncomeNet", "INT64"),
    ("netInterestIncome", "INT64"), ("interestIncome", "INT64"), ("interestExpense", "INT64"),
    ("nonInterestIncome", "INT64"), ("otherNonOperatingIncome", "INT64"),
    ("depreciation", "INT64"), ("depreciationAndAmortization", "INT64"),
    ("incomeBeforeTax", "INT64"), ("incomeTaxExpense", "INT64"),
    ("interestAndDebtExpense", "INT64"), ("netIncomeFromContinuingOperations", "INT64"),
    ("comprehensiveIncomeNetOfTax", "INT64"), ("ebit", "INT64"),
    ("ebitda", "INT64"), ("netIncome", "INT64")
] %}

WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM {{ source('camada_bronze', 'ext_income_statement') }}
), reports AS (
    SELECT raw_data, year, month, day, 'annual' AS report_type, report
    FROM raw_source, UNNEST(JSON_QUERY_ARRAY(raw_data, '$.annualReports')) AS report
    UNION ALL
    SELECT raw_data, year, month, day, 'quarterly' AS report_type, report
    FROM raw_source, UNNEST(JSON_QUERY_ARRAY(raw_data, '$.quarterlyReports')) AS report
)
SELECT
    JSON_VALUE(raw_data, '$.symbol') AS symbol,
    report_type,
    {% for field_name, field_type in report_fields %}
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.{{ field_name }}'), 'None'), '-'), 'N/A') AS {{ field_type }}) AS {{ field_name | lower }}{% if not loop.last %},{% endif %}
    {% endfor %},
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports
