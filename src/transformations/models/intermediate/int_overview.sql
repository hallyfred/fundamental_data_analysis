-- Grain: (symbol). Latest company snapshot; no fiscal-period grain.
-- Silver: parse, type, deduplicate and derive reusable components.

{{ config(materialized='view') }}

with source as (
    select raw_data, year as partition_year, month as partition_month,
        day as partition_day, date(year, month, day) as ingest_date
    from {{ ref('stg_overview') }}
),
parsed as (
    select
        partition_year,
        partition_month,
        partition_day,
        ingest_date,
        json_value(raw_data, '$.Symbol') as symbol,
        json_value(raw_data, '$.AssetType') as asset_type,
        json_value(raw_data, '$.Name') as name,
        json_value(raw_data, '$.Exchange') as exchange,
        json_value(raw_data, '$.Currency') as currency,
        json_value(raw_data, '$.Country') as country,
        json_value(raw_data, '$.Sector') as sector,
        json_value(raw_data, '$.Industry') as industry,
        json_value(raw_data, '$.FiscalYearEnd') as fiscal_year_end,
        json_value(raw_data, '$.LatestQuarter') as latest_quarter,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.MarketCapitalization'), 'None'), '-'), 'N/A'), '') as int64) as market_capitalization,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PERatio'), 'None'), '-'), 'N/A'), '') as numeric) as pe_ratio,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PEGRatio'), 'None'), '-'), 'N/A'), '') as numeric) as peg_ratio,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.BookValue'), 'None'), '-'), 'N/A'), '') as numeric) as book_value,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.DividendPerShare'), 'None'), '-'), 'N/A'), '') as numeric) as dividend_per_share,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.DividendYield'), 'None'), '-'), 'N/A'), '') as numeric) as dividend_yield,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.EPS'), 'None'), '-'), 'N/A'), '') as numeric) as eps,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.RevenuePerShareTTM'), 'None'), '-'), 'N/A'), '') as numeric) as revenue_per_share_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.ProfitMargin'), 'None'), '-'), 'N/A'), '') as numeric) as profit_margin,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.ReturnOnEquityTTM'), 'None'), '-'), 'N/A'), '') as numeric) as return_on_equity_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.EVToRevenue'), 'None'), '-'), 'N/A'), '') as numeric) as ev_to_revenue,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.EVToEBITDA'), 'None'), '-'), 'N/A'), '') as numeric) as ev_to_ebitda,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.Beta'), 'None'), '-'), 'N/A'), '') as numeric) as beta,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.TrailingPE'), 'None'), '-'), 'N/A'), '') as numeric) as trailing_pe,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.ForwardPE'), 'None'), '-'), 'N/A'), '') as numeric) as forward_pe,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PriceToSalesRatioTTM'), 'None'), '-'), 'N/A'), '') as numeric) as price_to_sales_ratio_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PriceToBookRatio'), 'None'), '-'), 'N/A'), '') as numeric) as price_to_book_ratio,
        json_value(raw_data, '$.Description') as description,
        json_value(raw_data, '$.CIK') as cik,
        json_value(raw_data, '$.Address') as address,
        json_value(raw_data, '$.OfficialSite') as official_site,
        json_value(raw_data, '$.DividendDate') as dividend_date,
        json_value(raw_data, '$.ExDividendDate') as ex_dividend_date,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.EBITDA'), 'None'), '-'), 'N/A'), '') as int64) as ebitda,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.RevenueTTM'), 'None'), '-'), 'N/A'), '') as int64) as revenue_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.GrossProfitTTM'), 'None'), '-'), 'N/A'), '') as int64) as gross_profit_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.SharesOutstanding'), 'None'), '-'), 'N/A'), '') as int64) as shares_outstanding,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.SharesFloat'), 'None'), '-'), 'N/A'), '') as int64) as shares_float,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.OperatingMarginTTM'), 'None'), '-'), 'N/A'), '') as numeric) as operating_margin_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.ReturnOnAssetsTTM'), 'None'), '-'), 'N/A'), '') as numeric) as return_on_assets_ttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.DilutedEPSTTM'), 'None'), '-'), 'N/A'), '') as numeric) as diluted_epsttm,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.QuarterlyEarningsGrowthYOY'), 'None'), '-'), 'N/A'), '') as numeric) as quarterly_earnings_growth_yoy,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.QuarterlyRevenueGrowthYOY'), 'None'), '-'), 'N/A'), '') as numeric) as quarterly_revenue_growth_yoy,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystTargetPrice'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_target_price,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystRatingStrongBuy'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_rating_strong_buy,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystRatingBuy'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_rating_buy,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystRatingHold'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_rating_hold,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystRatingSell'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_rating_sell,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.AnalystRatingStrongSell'), 'None'), '-'), 'N/A'), '') as numeric) as analyst_rating_strong_sell,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PercentInsiders'), 'None'), '-'), 'N/A'), '') as numeric) as percent_insiders,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.PercentInstitutions'), 'None'), '-'), 'N/A'), '') as numeric) as percent_institutions,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.52WeekHigh'), 'None'), '-'), 'N/A'), '') as numeric) as week_high_52,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.52WeekLow'), 'None'), '-'), 'N/A'), '') as numeric) as week_low_52,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.50DayMovingAverage'), 'None'), '-'), 'N/A'), '') as numeric) as moving_average_50,
        safe_cast(nullif(nullif(nullif(nullif(json_value(raw_data, '$.200DayMovingAverage'), 'None'), '-'), 'N/A'), '') as numeric) as moving_average_200
    from source
),
deduped as (
    select *
    from parsed
    qualify row_number() over (
        partition by symbol
        order by ingest_date desc, partition_day desc, partition_month desc
    ) = 1
)
select * from deduped
