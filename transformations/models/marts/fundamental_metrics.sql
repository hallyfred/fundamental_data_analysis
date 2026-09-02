{{ config(
    materialized='table',
    partition_by={
        'field': 'fiscal_date_ending',
        'data_type': 'date'
    }
) }}

WITH overview AS (
    SELECT
        symbol,
        trailingpe AS pe_ratio,
        evtoebitda AS ev_to_ebitda
    FROM {{ ref('stg_overview') }}
),

final AS (
    SELECT
        i.symbol,
        i.fiscal_date_ending,
        i.roe,
        i.net_margin,
        i.ebitda_margin,
        i.net_debt_to_ebitda,
        i.current_ratio,
        i.free_cash_flow,
        i.quality_of_earnings,
        i.revenue_yoy_growth,
        i.earnings_surprise_pct,
        o.pe_ratio,
        o.ev_to_ebitda
    FROM {{ ref('int_financial_metrics') }} i
    LEFT JOIN overview o
        ON i.symbol = o.symbol
)

SELECT *
FROM final
