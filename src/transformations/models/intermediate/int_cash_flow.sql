-- Grain: (symbol, fiscaldateending, report_type). FLOW accumulated over the fiscal period.
-- Silver: parse, type, deduplicate and derive reusable components.

{{ config(materialized='view') }}

with source as (
    select raw_data, year as partition_year, month as partition_month,
        day as partition_day, date(year, month, day) as ingest_date
    from {{ ref('stg_cash_flow') }}
),
unnested as (
    select source.*, json_value(raw_data, '$.symbol') as symbol,
        'annual' as report_type, report
    from source, unnest(json_query_array(raw_data, '$.annualReports')) as report
    union all
    select source.*, json_value(raw_data, '$.symbol') as symbol,
        'quarterly' as report_type, report
    from source, unnest(json_query_array(raw_data, '$.quarterlyReports')) as report
),
parsed as (
    select
        partition_year,
        partition_month,
        partition_day,
        ingest_date,
        symbol,
        report_type,
        json_value(report, '$.fiscalDateEnding') as fiscaldateending_raw,
        safe.parse_date('%Y-%m-%d', json_value(report, '$.fiscalDateEnding')) as fiscaldateending,
        json_value(report, '$.reportedCurrency') as reportedcurrency,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.operatingCashflow'), 'None'), '-'), 'N/A'), '') as int64) as operating_cashflow,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.capitalExpenditures'), 'None'), '-'), 'N/A'), '') as int64) as capital_expenditures,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.depreciationDepletionAndAmortization'), 'None'), '-'), 'N/A'), '') as int64) as depreciation_depletion_and_amortization,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.dividendPayout'), 'None'), '-'), 'N/A'), '') as int64) as dividend_payout,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.stockBasedCompensation'), 'None'), '-'), 'N/A'), '') as int64) as stock_based_compensation,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.cashflowFromInvestment'), 'None'), '-'), 'N/A'), '') as int64) as cashflow_from_investment,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.cashflowFromFinancing'), 'None'), '-'), 'N/A'), '') as int64) as cashflow_from_financing,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.netIncome'), 'None'), '-'), 'N/A'), '') as int64) as net_income,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.paymentsForOperatingActivities'), 'None'), '-'), 'N/A'), '') as int64) as payments_for_operating_activities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromOperatingActivities'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_operating_activities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInOperatingLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as change_in_operating_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInOperatingAssets'), 'None'), '-'), 'N/A'), '') as int64) as change_in_operating_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInReceivables'), 'None'), '-'), 'N/A'), '') as int64) as change_in_receivables,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInInventory'), 'None'), '-'), 'N/A'), '') as int64) as change_in_inventory,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.profitLoss'), 'None'), '-'), 'N/A'), '') as int64) as profit_loss,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromRepaymentsOfShortTermDebt'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_repayments_of_short_term_debt,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.paymentsForRepurchaseOfCommonStock'), 'None'), '-'), 'N/A'), '') as int64) as payments_for_repurchase_of_common_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.paymentsForRepurchaseOfEquity'), 'None'), '-'), 'N/A'), '') as int64) as payments_for_repurchase_of_equity,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.paymentsForRepurchaseOfPreferredStock'), 'None'), '-'), 'N/A'), '') as int64) as payments_for_repurchase_of_preferred_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.dividendPayoutCommonStock'), 'None'), '-'), 'N/A'), '') as int64) as dividend_payout_common_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.dividendPayoutPreferredStock'), 'None'), '-'), 'N/A'), '') as int64) as dividend_payout_preferred_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromIssuanceOfCommonStock'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_issuance_of_common_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_issuance_of_long_term_debt_and_capital_securities_net,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromIssuanceOfPreferredStock'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_issuance_of_preferred_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromRepurchaseOfEquity'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_repurchase_of_equity,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.proceedsFromSaleOfTreasuryStock'), 'None'), '-'), 'N/A'), '') as int64) as proceeds_from_sale_of_treasury_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInCashAndCashEquivalents'), 'None'), '-'), 'N/A'), '') as int64) as change_in_cash_and_cash_equivalents,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.changeInExchangeRate'), 'None'), '-'), 'N/A'), '') as int64) as change_in_exchange_rate
    from unnested
),
deduped as (
    select *
    from parsed
    qualify row_number() over (
        partition by symbol, fiscaldateending, report_type
        order by ingest_date desc, partition_day desc, partition_month desc
    ) = 1
)
select *, safe_subtract(operating_cashflow, capital_expenditures) as free_cash_flow
from deduped
