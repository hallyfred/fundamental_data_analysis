{{ config(
    materialized='incremental',
    unique_key=['symbol', 'fiscal_date_ending'],
    incremental_strategy='merge',
    partition_by={
        'field': 'fiscal_date_ending',
        'data_type': 'date'
    }
) }}

WITH income AS (
    SELECT
        symbol,
        fiscaldateending AS fiscal_date_ending_income,
        totalrevenue,
        netincome,
        ebitda
    FROM {{ ref('stg_income_statement') }}
    WHERE report_type = 'annual'
      AND fiscaldateending IS NOT NULL
),

balance AS (
    SELECT
        symbol,
        fiscaldateending AS fiscal_date_ending_balance,
        totalcurrentassets,
        totalcurrentliabilities,
        totalshareholderequity,
        COALESCE(currentdebt, 0) + COALESCE(longtermdebt, 0) AS total_debt,
        COALESCE(cashandcashequivalentsatcarryingvalue, 0) AS cash_and_equivalents
    FROM {{ ref('stg_balance_sheet') }}
    WHERE report_type = 'annual'
      AND fiscaldateending IS NOT NULL
),

cash_flow AS (
    SELECT
        symbol,
        fiscaldateending AS fiscal_date_ending_cash_flow,
        operatingcashflow,
        capitalexpenditures
    FROM {{ ref('stg_cash_flow') }}
    WHERE report_type = 'annual'
      AND fiscaldateending IS NOT NULL
),

earnings AS (
    SELECT
        symbol,
        fiscaldateending AS fiscal_date_ending_earning,
        reportedeps,
        estimatedeps,
        surprisepercentage
    FROM {{ ref('stg_earning') }}
    WHERE report_type = 'annual'
      AND fiscaldateending IS NOT NULL
),

base AS (
    SELECT
        i.symbol,
        COALESCE(i.fiscal_date_ending_income, b.fiscal_date_ending_balance, c.fiscal_date_ending_cash_flow, e.fiscal_date_ending_earning) AS fiscal_date_ending,
        i.totalrevenue,
        i.netincome,
        i.ebitda,
        b.totalcurrentassets,
        b.totalcurrentliabilities,
        b.totalshareholderequity,
        b.total_debt,
        b.cash_and_equivalents,
        c.operatingcashflow,
        c.capitalexpenditures,
        e.reportedeps AS reported_eps,
        e.estimatedeps AS estimated_eps,
        e.surprisepercentage AS surprise_percentage
    FROM income i
    LEFT JOIN balance b
        ON i.symbol = b.symbol
       AND i.fiscal_date_ending_income = b.fiscal_date_ending_balance
    LEFT JOIN cash_flow c
        ON i.symbol = c.symbol
       AND i.fiscal_date_ending_income = c.fiscal_date_ending_cash_flow
    LEFT JOIN earnings e
        ON i.symbol = e.symbol
       AND i.fiscal_date_ending_income = e.fiscal_date_ending_earning
),

with_growth AS (
    SELECT
        base.symbol,
        base.fiscal_date_ending,
        base.totalrevenue,
        base.netincome,
        base.ebitda,
        base.totalcurrentassets,
        base.totalcurrentliabilities,
        base.totalshareholderequity,
        base.total_debt,
        base.cash_and_equivalents,
        base.operatingcashflow,
        base.capitalexpenditures,
        base.reported_eps,
        base.estimated_eps,
        base.surprise_percentage,
        LAG(base.totalrevenue) OVER (
            PARTITION BY base.symbol
            ORDER BY base.fiscal_date_ending
        ) AS previous_total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY base.symbol, base.fiscal_date_ending
            ORDER BY base.fiscal_date_ending DESC
        ) AS row_num
    FROM base
),

deduped AS (
    SELECT
        symbol,
        fiscal_date_ending,
        totalrevenue,
        netincome,
        ebitda,
        totalcurrentassets,
        totalcurrentliabilities,
        totalshareholderequity,
        total_debt,
        cash_and_equivalents,
        operatingcashflow,
        capitalexpenditures,
        reported_eps,
        estimated_eps,
        surprise_percentage,
        previous_total_revenue,
        ROW_NUMBER() OVER (
            PARTITION BY symbol
            ORDER BY fiscal_date_ending DESC
        ) AS latest_row
    FROM with_growth
    WHERE row_num = 1
)

SELECT
    symbol,
    fiscal_date_ending,
    totalrevenue,
    netincome,
    ebitda,
    totalcurrentassets,
    totalcurrentliabilities,
    totalshareholderequity,
    total_debt,
    cash_and_equivalents,
    operatingcashflow,
    capitalexpenditures,
    reported_eps,
    estimated_eps,
    surprise_percentage,
    ROUND(SAFE_DIVIDE(netincome, totalshareholderequity), 2) AS roe,
    ROUND(SAFE_DIVIDE(netincome, totalrevenue), 2) AS net_margin,
    ROUND(SAFE_DIVIDE(ebitda, totalrevenue), 2) AS ebitda_margin,
    ROUND(SAFE_DIVIDE((total_debt - cash_and_equivalents), ebitda), 2) AS net_debt_to_ebitda,
    ROUND(SAFE_DIVIDE(totalcurrentassets, totalcurrentliabilities), 2) AS current_ratio,
    CAST(ROUND(CAST((operatingcashflow - capitalexpenditures) AS FLOAT64), 2) AS FLOAT64) AS free_cash_flow,
    ROUND(SAFE_DIVIDE(operatingcashflow, netincome), 2) AS quality_of_earnings,
    ROUND(COALESCE(SAFE_DIVIDE((totalrevenue - previous_total_revenue), previous_total_revenue), 0), 2) AS revenue_yoy_growth,
    ROUND(COALESCE(SAFE_DIVIDE((reported_eps - estimated_eps), estimated_eps), 0), 2) AS earnings_surprise_pct
FROM deduped

{% if is_incremental() %}
WHERE fiscal_date_ending > (SELECT COALESCE(MAX(fiscal_date_ending), DATE '1900-01-01') FROM {{ this }})
{% endif %}
