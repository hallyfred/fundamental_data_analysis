

  create or replace view `projetodbt-479518`.`alphavantage`.`stg_overview`
  OPTIONS(
      description="""Silver layer model containing fundamental data, financial metrics, and corporate profiles for listed companies. Sourced from Alpha Vantage (OVERVIEW endpoint)."""
    )
  as 

-- JSON keys and BigQuery types aligned with OverviewSchema in contract.py


WITH raw_source AS (
    SELECT 
        raw_data,
        year,
        month,
        day
    FROM `projetodbt-479518`.`alphavantage`.`ext_overview`
)

SELECT
    -- Unpack the tuple into field_name and field_type variables
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Symbol'), 'None') 
            AS STRING
        ) AS symbol,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AssetType'), 'None') 
            AS STRING
        ) AS assettype,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Name'), 'None') 
            AS STRING
        ) AS name,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Description'), 'None') 
            AS STRING
        ) AS description,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.CIK'), 'None') 
            AS STRING
        ) AS cik,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Exchange'), 'None') 
            AS STRING
        ) AS exchange,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Currency'), 'None') 
            AS STRING
        ) AS currency,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Country'), 'None') 
            AS STRING
        ) AS country,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Sector'), 'None') 
            AS STRING
        ) AS sector,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Industry'), 'None') 
            AS STRING
        ) AS industry,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Address'), 'None') 
            AS STRING
        ) AS address,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.OfficialSite'), 'None') 
            AS STRING
        ) AS officialsite,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.FiscalYearEnd'), 'None') 
            AS STRING
        ) AS fiscalyearend,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.LatestQuarter'), 'None') 
            AS STRING
        ) AS latestquarter,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.DividendDate'), 'None') 
            AS STRING
        ) AS dividenddate,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.ExDividendDate'), 'None') 
            AS STRING
        ) AS exdividenddate,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.MarketCapitalization'), 'None') 
            AS INT64
        ) AS marketcapitalization,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.EBITDA'), 'None') 
            AS INT64
        ) AS ebitda,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.RevenueTTM'), 'None') 
            AS INT64
        ) AS revenuettm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.GrossProfitTTM'), 'None') 
            AS INT64
        ) AS grossprofitttm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.SharesOutstanding'), 'None') 
            AS INT64
        ) AS sharesoutstanding,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.SharesFloat'), 'None') 
            AS INT64
        ) AS sharesfloat,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PERatio'), 'None') 
            AS FLOAT64
        ) AS peratio,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PEGRatio'), 'None') 
            AS FLOAT64
        ) AS pegratio,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.BookValue'), 'None') 
            AS FLOAT64
        ) AS bookvalue,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.DividendPerShare'), 'None') 
            AS FLOAT64
        ) AS dividendpershare,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.DividendYield'), 'None') 
            AS FLOAT64
        ) AS dividendyield,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.EPS'), 'None') 
            AS FLOAT64
        ) AS eps,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.RevenuePerShareTTM'), 'None') 
            AS FLOAT64
        ) AS revenuepersharettm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.ProfitMargin'), 'None') 
            AS FLOAT64
        ) AS profitmargin,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.OperatingMarginTTM'), 'None') 
            AS FLOAT64
        ) AS operatingmarginttm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.ReturnOnAssetsTTM'), 'None') 
            AS FLOAT64
        ) AS returnonassetsttm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.ReturnOnEquityTTM'), 'None') 
            AS FLOAT64
        ) AS returnonequityttm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.DilutedEPSTTM'), 'None') 
            AS FLOAT64
        ) AS dilutedepsttm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.QuarterlyEarningsGrowthYOY'), 'None') 
            AS FLOAT64
        ) AS quarterlyearningsgrowthyoy,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.QuarterlyRevenueGrowthYOY'), 'None') 
            AS FLOAT64
        ) AS quarterlyrevenuegrowthyoy,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystTargetPrice'), 'None') 
            AS FLOAT64
        ) AS analysttargetprice,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystRatingStrongBuy'), 'None') 
            AS FLOAT64
        ) AS analystratingstrongbuy,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystRatingBuy'), 'None') 
            AS FLOAT64
        ) AS analystratingbuy,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystRatingHold'), 'None') 
            AS FLOAT64
        ) AS analystratinghold,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystRatingSell'), 'None') 
            AS FLOAT64
        ) AS analystratingsell,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.AnalystRatingStrongSell'), 'None') 
            AS FLOAT64
        ) AS analystratingstrongsell,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.TrailingPE'), 'None') 
            AS FLOAT64
        ) AS trailingpe,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.ForwardPE'), 'None') 
            AS FLOAT64
        ) AS forwardpe,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PriceToSalesRatioTTM'), 'None') 
            AS FLOAT64
        ) AS pricetosalesratiottm,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PriceToBookRatio'), 'None') 
            AS FLOAT64
        ) AS pricetobookratio,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.EVToRevenue'), 'None') 
            AS FLOAT64
        ) AS evtorevenue,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.EVToEBITDA'), 'None') 
            AS FLOAT64
        ) AS evtoebitda,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.Beta'), 'None') 
            AS FLOAT64
        ) AS beta,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PercentInsiders'), 'None') 
            AS FLOAT64
        ) AS percentinsiders,
        
    
        
        
        
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.PercentInstitutions'), 'None') 
            AS FLOAT64
        ) AS percentinstitutions,
        
    
        
        
        
        
            
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.52WeekHigh'), 'None') 
            AS FLOAT64
        ) AS _52weekhigh,
        
    
        
        
        
        
            
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.52WeekLow'), 'None') 
            AS FLOAT64
        ) AS _52weeklow,
        
    
        
        
        
        
            
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.50DayMovingAverage'), 'None') 
            AS FLOAT64
        ) AS _50daymovingaverage,
        
    
        
        
        
        
            
        
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.200DayMovingAverage'), 'None') 
            AS FLOAT64
        ) AS _200daymovingaverage,
        
    

    year as partition_year,
    month as partition_month,
    day as partition_day

FROM raw_source;

