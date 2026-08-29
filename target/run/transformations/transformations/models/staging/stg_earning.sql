

  create or replace view `projetodbt-479518`.`alphavantage`.`stg_earning`
  OPTIONS(
      description="""Flattened annual and quarterly earnings reports from the Alpha Vantage EARNINGS endpoint."""
    )
  as 




WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM `projetodbt-479518`.`alphavantage`.`ext_earning`
), reports AS (
    SELECT raw_data, year, month, day, 'annual' AS report_type, report
    FROM raw_source, UNNEST(JSON_QUERY_ARRAY(raw_data, '$.annualEarnings')) AS report
    UNION ALL
    SELECT raw_data, year, month, day, 'quarterly' AS report_type, report
    FROM raw_source, UNNEST(JSON_QUERY_ARRAY(raw_data, '$.quarterlyEarnings')) AS report
)
SELECT
    JSON_VALUE(raw_data, '$.symbol') AS symbol,
    report_type,
    
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.fiscalDateEnding'), 'None'), '-'), 'N/A') AS DATE) AS fiscaldateending,
    
    
    
    CAST(NULL AS DATE) AS reporteddate,
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.reportedEPS'), 'None'), '-'), 'N/A') AS FLOAT64) AS reportedeps,
    
    
    CAST(NULL AS FLOAT64) AS estimatedeps,
    CAST(NULL AS FLOAT64) AS surprise,
    CAST(NULL AS FLOAT64) AS surprisepercentage,
    CAST(NULL AS STRING) AS reporttime,
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports
WHERE report_type = 'annual'

UNION ALL

SELECT
    JSON_VALUE(raw_data, '$.symbol') AS symbol,
    report_type,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.fiscalDateEnding'), 'None'), '-'), 'N/A') AS DATE) AS fiscaldateending,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.reportedDate'), 'None'), '-'), 'N/A') AS DATE) AS reporteddate,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.reportedEPS'), 'None'), '-'), 'N/A') AS FLOAT64) AS reportedeps,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.estimatedEPS'), 'None'), '-'), 'N/A') AS FLOAT64) AS estimatedeps,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.surprise'), 'None'), '-'), 'N/A') AS FLOAT64) AS surprise,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.surprisePercentage'), 'None'), '-'), 'N/A') AS FLOAT64) AS surprisepercentage,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.reportTime'), 'None'), '-'), 'N/A') AS STRING) AS reporttime
    ,
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports
WHERE report_type = 'quarterly';

