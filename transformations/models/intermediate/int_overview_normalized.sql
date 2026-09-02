{{ config(materialized='view') }}

WITH source AS (
    SELECT
        raw_data,
        year AS partition_year,
        month AS partition_month,
        day AS partition_day
    FROM {{ source('camada_bronze', 'ext_overview') }}
),
normalized AS (
    SELECT
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Symbol'), 'None') AS STRING) AS symbol,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AssetType'), 'None') AS STRING) AS asset_type,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Name'), 'None') AS STRING) AS company_name,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Description'), 'None') AS STRING) AS description,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.CIK'), 'None') AS STRING) AS cik,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Exchange'), 'None') AS STRING) AS exchange,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Currency'), 'None') AS STRING) AS currency,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Country'), 'None') AS STRING) AS country,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Sector'), 'None') AS STRING) AS sector,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Industry'), 'None') AS STRING) AS industry,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Address'), 'None') AS STRING) AS address,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.OfficialSite'), 'None') AS STRING) AS official_site,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.FiscalYearEnd'), 'None') AS STRING) AS fiscal_year_end,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.LatestQuarter'), 'None') AS STRING) AS latest_quarter,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.DividendDate'), 'None') AS STRING) AS dividend_date,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.ExDividendDate'), 'None') AS STRING) AS ex_dividend_date,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.MarketCapitalization'), 'None') AS INT64) AS market_capitalization,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.EBITDA'), 'None') AS INT64) AS ebitda,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.RevenueTTM'), 'None') AS INT64) AS revenue_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.GrossProfitTTM'), 'None') AS INT64) AS gross_profit_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.SharesOutstanding'), 'None') AS INT64) AS shares_outstanding,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.SharesFloat'), 'None') AS INT64) AS shares_float,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PERatio'), 'None') AS FLOAT64) AS pe_ratio,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PEGRatio'), 'None') AS FLOAT64) AS peg_ratio,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.BookValue'), 'None') AS FLOAT64) AS book_value,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.DividendPerShare'), 'None') AS FLOAT64) AS dividend_per_share,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.DividendYield'), 'None') AS FLOAT64) AS dividend_yield,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.EPS'), 'None') AS FLOAT64) AS eps,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.RevenuePerShareTTM'), 'None') AS FLOAT64) AS revenue_per_share_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.ProfitMargin'), 'None') AS FLOAT64) AS profit_margin,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.OperatingMarginTTM'), 'None') AS FLOAT64) AS operating_margin_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.ReturnOnAssetsTTM'), 'None') AS FLOAT64) AS return_on_assets_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.ReturnOnEquityTTM'), 'None') AS FLOAT64) AS return_on_equity_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.DilutedEPSTTM'), 'None') AS FLOAT64) AS diluted_eps_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.QuarterlyEarningsGrowthYOY'), 'None') AS FLOAT64) AS quarterly_earnings_growth_yoy,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.QuarterlyRevenueGrowthYOY'), 'None') AS FLOAT64) AS quarterly_revenue_growth_yoy,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystTargetPrice'), 'None') AS FLOAT64) AS analyst_target_price,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystRatingStrongBuy'), 'None') AS FLOAT64) AS analyst_rating_strong_buy,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystRatingBuy'), 'None') AS FLOAT64) AS analyst_rating_buy,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystRatingHold'), 'None') AS FLOAT64) AS analyst_rating_hold,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystRatingSell'), 'None') AS FLOAT64) AS analyst_rating_sell,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.AnalystRatingStrongSell'), 'None') AS FLOAT64) AS analyst_rating_strong_sell,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.TrailingPE'), 'None') AS FLOAT64) AS trailing_pe,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.ForwardPE'), 'None') AS FLOAT64) AS forward_pe,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PriceToSalesRatioTTM'), 'None') AS FLOAT64) AS price_to_sales_ratio_ttm,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PriceToBookRatio'), 'None') AS FLOAT64) AS price_to_book_ratio,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.EVToRevenue'), 'None') AS FLOAT64) AS ev_to_revenue,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.EVToEBITDA'), 'None') AS FLOAT64) AS ev_to_ebitda,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.Beta'), 'None') AS FLOAT64) AS beta,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PercentInsiders'), 'None') AS FLOAT64) AS percent_insiders,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.PercentInstitutions'), 'None') AS FLOAT64) AS percent_institutions,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.52WeekHigh'), 'None') AS FLOAT64) AS week_52_high,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.52WeekLow'), 'None') AS FLOAT64) AS week_52_low,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.50DayMovingAverage'), 'None') AS FLOAT64) AS day_50_moving_average,
        CAST(NULLIF(JSON_VALUE(raw_data, '$.200DayMovingAverage'), 'None') AS FLOAT64) AS day_200_moving_average,
        partition_year,
        partition_month,
        partition_day
    FROM source
)

SELECT *
FROM normalized
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY symbol, fiscal_year_end
    ORDER BY partition_year DESC, partition_month DESC, partition_day DESC
) = 1
