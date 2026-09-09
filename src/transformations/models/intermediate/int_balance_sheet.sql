-- Grain: (symbol, fiscaldateending, report_type). POSITION snapshot at fiscal period end.
-- Silver: parse, type, deduplicate and derive reusable components.

{{ config(materialized='view') }}

with source as (
    select raw_data, year as partition_year, month as partition_month,
        day as partition_day, date(year, month, day) as ingest_date
    from {{ ref('stg_balance_sheet') }}
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
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalAssets'), 'None'), '-'), 'N/A'), '') as int64) as total_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalCurrentAssets'), 'None'), '-'), 'N/A'), '') as int64) as total_current_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.cashAndCashEquivalentsAtCarryingValue'), 'None'), '-'), 'N/A'), '') as int64) as cash_and_cash_equivalents,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.cashAndShortTermInvestments'), 'None'), '-'), 'N/A'), '') as int64) as cash_and_short_term_investments,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.inventory'), 'None'), '-'), 'N/A'), '') as int64) as inventory,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.currentNetReceivables'), 'None'), '-'), 'N/A'), '') as int64) as current_net_receivables,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalNonCurrentAssets'), 'None'), '-'), 'N/A'), '') as int64) as total_non_current_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.propertyPlantEquipment'), 'None'), '-'), 'N/A'), '') as int64) as property_plant_equipment,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.intangibleAssets'), 'None'), '-'), 'N/A'), '') as int64) as intangible_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.goodwill'), 'None'), '-'), 'N/A'), '') as int64) as goodwill,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.longTermInvestments'), 'None'), '-'), 'N/A'), '') as int64) as long_term_investments,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.shortTermInvestments'), 'None'), '-'), 'N/A'), '') as int64) as short_term_investments,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as total_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalCurrentLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as total_current_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.currentAccountsPayable'), 'None'), '-'), 'N/A'), '') as int64) as current_accounts_payable,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.shortTermDebt'), 'None'), '-'), 'N/A'), '') as int64) as short_term_debt,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalNonCurrentLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as total_non_current_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.capitalLeaseObligations'), 'None'), '-'), 'N/A'), '') as int64) as capital_lease_obligations,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.longTermDebt'), 'None'), '-'), 'N/A'), '') as int64) as long_term_debt,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.currentLongTermDebt'), 'None'), '-'), 'N/A'), '') as int64) as current_long_term_debt,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.shortLongTermDebtTotal'), 'None'), '-'), 'N/A'), '') as int64) as short_long_term_debt_total,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.otherCurrentLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as other_current_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.totalShareholderEquity'), 'None'), '-'), 'N/A'), '') as int64) as total_shareholder_equity,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.retainedEarnings'), 'None'), '-'), 'N/A'), '') as int64) as retained_earnings,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.commonStock'), 'None'), '-'), 'N/A'), '') as int64) as common_stock,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.commonStockSharesOutstanding'), 'None'), '-'), 'N/A'), '') as int64) as common_stock_shares_outstanding,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.accumulatedDepreciationAmortizationPPE'), 'None'), '-'), 'N/A'), '') as int64) as accumulated_depreciation_amortization_ppe,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.intangibleAssetsExcludingGoodwill'), 'None'), '-'), 'N/A'), '') as int64) as intangible_assets_excluding_goodwill,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.investments'), 'None'), '-'), 'N/A'), '') as int64) as investments,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.otherCurrentAssets'), 'None'), '-'), 'N/A'), '') as int64) as other_current_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.otherNonCurrentAssets'), 'None'), '-'), 'N/A'), '') as int64) as other_non_current_assets,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.deferredRevenue'), 'None'), '-'), 'N/A'), '') as int64) as deferred_revenue,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.currentDebt'), 'None'), '-'), 'N/A'), '') as int64) as current_debt,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.longTermDebtNoncurrent'), 'None'), '-'), 'N/A'), '') as int64) as long_term_debt_noncurrent,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.otherNonCurrentLiabilities'), 'None'), '-'), 'N/A'), '') as int64) as other_non_current_liabilities,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.treasuryStock'), 'None'), '-'), 'N/A'), '') as int64) as treasury_stock
    from unnested
),
deduped as (
    select *
    from parsed
    qualify row_number() over (
        partition by symbol, fiscaldateending, report_type
        order by ingest_date desc, partition_day desc, partition_month desc
    ) = 1
),
derived as (
    select *, coalesce(short_long_term_debt_total, safe_add(long_term_debt, short_term_debt)) as total_debt
    from deduped
)
select *, safe_subtract(total_debt, cash_and_cash_equivalents) as net_debt
from derived
