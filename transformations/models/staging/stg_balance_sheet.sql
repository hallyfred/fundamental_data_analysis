{{ config(materialized='view') }}

{% set report_fields = [
    ("fiscalDateEnding", "DATE"), ("reportedCurrency", "STRING"),
    ("totalAssets", "INT64"), ("totalCurrentAssets", "INT64"),
    ("cashAndCashEquivalentsAtCarryingValue", "INT64"), ("cashAndShortTermInvestments", "INT64"),
    ("inventory", "INT64"), ("currentNetReceivables", "INT64"), ("totalNonCurrentAssets", "INT64"),
    ("propertyPlantEquipment", "INT64"), ("accumulatedDepreciationAmortizationPPE", "INT64"),
    ("intangibleAssets", "INT64"), ("intangibleAssetsExcludingGoodwill", "INT64"),
    ("goodwill", "INT64"), ("investments", "INT64"), ("longTermInvestments", "INT64"),
    ("shortTermInvestments", "INT64"), ("otherCurrentAssets", "INT64"),
    ("otherNonCurrentAssets", "INT64"), ("totalLiabilities", "INT64"),
    ("totalCurrentLiabilities", "INT64"), ("currentAccountsPayable", "INT64"),
    ("deferredRevenue", "INT64"), ("currentDebt", "INT64"), ("shortTermDebt", "INT64"),
    ("totalNonCurrentLiabilities", "INT64"), ("capitalLeaseObligations", "INT64"),
    ("longTermDebt", "INT64"), ("currentLongTermDebt", "INT64"),
    ("longTermDebtNoncurrent", "INT64"), ("shortLongTermDebtTotal", "INT64"),
    ("otherCurrentLiabilities", "INT64"), ("otherNonCurrentLiabilities", "INT64"),
    ("totalShareholderEquity", "INT64"), ("treasuryStock", "INT64"),
    ("retainedEarnings", "INT64"), ("commonStock", "INT64"),
    ("commonStockSharesOutstanding", "INT64")
] %}

WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM {{ source('camada_bronze', 'ext_balance_sheet') }}
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
