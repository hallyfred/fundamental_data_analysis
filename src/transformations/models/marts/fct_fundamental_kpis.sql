-- Grain: (symbol, fiscaldateending, report_type), anchored on income statement.
-- Flow statements cover a fiscal period; balance sheet is its closing snapshot.
-- Silver guarantees unique join keys and one latest overview snapshot per symbol.
-- Invalid fiscal dates remain visible and fail the not_null data quality gate.
-- A full rebuild preserves correctness for window functions, late-arriving periods,
-- and valuation fields sourced from the latest overview snapshot.
{{
    config(
        materialized='table',
        partition_by={
            'field': 'fiscaldateending',
            'data_type': 'date',
            'granularity': 'day'
        },
        cluster_by=['symbol', 'report_type']
    )
}}

with income_statement as (
    select symbol, fiscaldateending, report_type, reportedcurrency, ingest_date,
        total_revenue, net_income, ebitda_calc
    from {{ ref('int_income_statement') }}
),
balance_sheet as (
    select symbol, fiscaldateending, report_type, total_shareholder_equity,
        total_current_assets, total_current_liabilities, net_debt
    from {{ ref('int_balance_sheet') }}
),
cash_flow as (
    select symbol, fiscaldateending, report_type, operating_cashflow, free_cash_flow
    from {{ ref('int_cash_flow') }}
),
earning as (
    select symbol, fiscaldateending, report_type, surprise_percentage
    from {{ ref('int_earning') }}
),
overview as (
    select symbol, sector, industry, country, exchange, ingest_date, pe_ratio, ev_to_ebitda
    from {{ ref('int_overview') }}
),
revenue_with_lag as (
    select *,
        case
            when report_type = 'quarterly' then lag(total_revenue, 4) over (
                partition by symbol, report_type order by fiscaldateending
            )
            when report_type = 'annual' then lag(total_revenue, 1) over (
                partition by symbol, report_type order by fiscaldateending
            )
        end as prior_revenue
    from income_statement
),
joined as (
    select
        inc.symbol,
        inc.fiscaldateending,
        inc.report_type,
        inc.reportedcurrency,
        inc.ingest_date,
        ov.sector,
        ov.industry,
        ov.country,
        ov.exchange,
        ov.ingest_date as overview_snapshot_date,
        inc.total_revenue,
        inc.net_income,
        inc.ebitda_calc,
        bs.total_shareholder_equity,
        bs.total_current_assets,
        bs.total_current_liabilities,
        bs.net_debt,
        cf.operating_cashflow,
        cf.free_cash_flow,
        earn.surprise_percentage as earnings_surprise_pct,
        ov.pe_ratio,
        ov.ev_to_ebitda,
        inc.prior_revenue
    from revenue_with_lag as inc
    left join balance_sheet as bs
        on inc.symbol = bs.symbol
        and inc.fiscaldateending = bs.fiscaldateending
        and inc.report_type = bs.report_type
    left join cash_flow as cf
        on inc.symbol = cf.symbol
        and inc.fiscaldateending = cf.fiscaldateending
        and inc.report_type = cf.report_type
    left join earning as earn
        on inc.symbol = earn.symbol
        and inc.fiscaldateending = earn.fiscaldateending
        and inc.report_type = earn.report_type
    left join overview as ov on inc.symbol = ov.symbol
)
select
    symbol,
    fiscaldateending,
    report_type,
    reportedcurrency,
    ingest_date,
    sector,
    industry,
    country,
    exchange,
    overview_snapshot_date,
    total_revenue,
    net_income,
    ebitda_calc,
    total_shareholder_equity,
    total_current_assets,
    total_current_liabilities,
    net_debt,
    operating_cashflow,
    -- NUMERIC '1' promotes KPI arithmetic to exact NUMERIC. INT64/INT64 would
    -- return FLOAT64 in BigQuery. Source amounts stay INT64; no JSON re-parsing.
    safe_divide(safe_multiply(net_income, numeric '1'), total_shareholder_equity) as roe,
    safe_divide(safe_multiply(net_income, numeric '1'), total_revenue) as net_margin,
    safe_divide(safe_multiply(ebitda_calc, numeric '1'), total_revenue) as ebitda_margin,
    safe_divide(safe_multiply(net_debt, numeric '1'), ebitda_calc) as net_debt_to_ebitda,
    safe_divide(safe_multiply(total_current_assets, numeric '1'), total_current_liabilities) as current_ratio,
    free_cash_flow,
    safe_divide(safe_multiply(operating_cashflow, numeric '1'), net_income) as quality_of_earnings,
    safe_divide(
        safe_subtract(safe_multiply(total_revenue, numeric '1'), prior_revenue),
        prior_revenue
    ) as revenue_yoy_growth,
    earnings_surprise_pct,
    pe_ratio,
    ev_to_ebitda
from joined
