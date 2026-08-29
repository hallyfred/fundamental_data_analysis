{{ config(materialized='view') }}

{% set report_fields = [
    ("fiscalDateEnding", "DATE"), ("reportedCurrency", "STRING"),
    ("operatingCashflow", "INT64"), ("paymentsForOperatingActivities", "INT64"),
    ("proceedsFromOperatingActivities", "INT64"), ("changeInOperatingLiabilities", "INT64"),
    ("changeInOperatingAssets", "INT64"), ("depreciationDepletionAndAmortization", "INT64"),
    ("capitalExpenditures", "INT64"), ("changeInReceivables", "INT64"),
    ("changeInInventory", "INT64"), ("profitLoss", "INT64"),
    ("cashflowFromInvestment", "INT64"), ("cashflowFromFinancing", "INT64"),
    ("proceedsFromRepaymentsOfShortTermDebt", "INT64"),
    ("paymentsForRepurchaseOfCommonStock", "INT64"),
    ("paymentsForRepurchaseOfEquity", "INT64"),
    ("paymentsForRepurchaseOfPreferredStock", "INT64"), ("dividendPayout", "INT64"),
    ("dividendPayoutCommonStock", "INT64"), ("dividendPayoutPreferredStock", "INT64"),
    ("proceedsFromIssuanceOfCommonStock", "INT64"),
    ("proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet", "INT64"),
    ("proceedsFromIssuanceOfPreferredStock", "INT64"),
    ("proceedsFromRepurchaseOfEquity", "INT64"), ("proceedsFromSaleOfTreasuryStock", "INT64"),
    ("stockBasedCompensation", "INT64"), ("changeInCashAndCashEquivalents", "INT64"),
    ("changeInExchangeRate", "INT64"), ("netIncome", "INT64")
] %}

WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM {{ source('camada_bronze', 'ext_cash_flow') }}
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
