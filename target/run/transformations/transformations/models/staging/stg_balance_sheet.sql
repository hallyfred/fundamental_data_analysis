

  create or replace view `projetodbt-479518`.`alphavantage`.`stg_balance_sheet`
  OPTIONS(
      description="""Flattened balance sheet reports from the Alpha Vantage BALANCE_SHEET endpoint."""
    )
  as 



WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM `projetodbt-479518`.`alphavantage`.`ext_balance_sheet`
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
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.fiscalDateEnding'), 'None'), '-'), 'N/A') AS DATE) AS fiscaldateending,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.reportedCurrency'), 'None'), '-'), 'N/A') AS STRING) AS reportedcurrency,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalAssets'), 'None'), '-'), 'N/A') AS INT64) AS totalassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalCurrentAssets'), 'None'), '-'), 'N/A') AS INT64) AS totalcurrentassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.cashAndCashEquivalentsAtCarryingValue'), 'None'), '-'), 'N/A') AS INT64) AS cashandcashequivalentsatcarryingvalue,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.cashAndShortTermInvestments'), 'None'), '-'), 'N/A') AS INT64) AS cashandshortterminvestments,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.inventory'), 'None'), '-'), 'N/A') AS INT64) AS inventory,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.currentNetReceivables'), 'None'), '-'), 'N/A') AS INT64) AS currentnetreceivables,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalNonCurrentAssets'), 'None'), '-'), 'N/A') AS INT64) AS totalnoncurrentassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.propertyPlantEquipment'), 'None'), '-'), 'N/A') AS INT64) AS propertyplantequipment,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.accumulatedDepreciationAmortizationPPE'), 'None'), '-'), 'N/A') AS INT64) AS accumulateddepreciationamortizationppe,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.intangibleAssets'), 'None'), '-'), 'N/A') AS INT64) AS intangibleassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.intangibleAssetsExcludingGoodwill'), 'None'), '-'), 'N/A') AS INT64) AS intangibleassetsexcludinggoodwill,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.goodwill'), 'None'), '-'), 'N/A') AS INT64) AS goodwill,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.investments'), 'None'), '-'), 'N/A') AS INT64) AS investments,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.longTermInvestments'), 'None'), '-'), 'N/A') AS INT64) AS longterminvestments,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.shortTermInvestments'), 'None'), '-'), 'N/A') AS INT64) AS shortterminvestments,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.otherCurrentAssets'), 'None'), '-'), 'N/A') AS INT64) AS othercurrentassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.otherNonCurrentAssets'), 'None'), '-'), 'N/A') AS INT64) AS othernoncurrentassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS totalliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalCurrentLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS totalcurrentliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.currentAccountsPayable'), 'None'), '-'), 'N/A') AS INT64) AS currentaccountspayable,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.deferredRevenue'), 'None'), '-'), 'N/A') AS INT64) AS deferredrevenue,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.currentDebt'), 'None'), '-'), 'N/A') AS INT64) AS currentdebt,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.shortTermDebt'), 'None'), '-'), 'N/A') AS INT64) AS shorttermdebt,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalNonCurrentLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS totalnoncurrentliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.capitalLeaseObligations'), 'None'), '-'), 'N/A') AS INT64) AS capitalleaseobligations,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.longTermDebt'), 'None'), '-'), 'N/A') AS INT64) AS longtermdebt,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.currentLongTermDebt'), 'None'), '-'), 'N/A') AS INT64) AS currentlongtermdebt,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.longTermDebtNoncurrent'), 'None'), '-'), 'N/A') AS INT64) AS longtermdebtnoncurrent,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.shortLongTermDebtTotal'), 'None'), '-'), 'N/A') AS INT64) AS shortlongtermdebttotal,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.otherCurrentLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS othercurrentliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.otherNonCurrentLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS othernoncurrentliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalShareholderEquity'), 'None'), '-'), 'N/A') AS INT64) AS totalshareholderequity,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.treasuryStock'), 'None'), '-'), 'N/A') AS INT64) AS treasurystock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.retainedEarnings'), 'None'), '-'), 'N/A') AS INT64) AS retainedearnings,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.commonStock'), 'None'), '-'), 'N/A') AS INT64) AS commonstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.commonStockSharesOutstanding'), 'None'), '-'), 'N/A') AS INT64) AS commonstocksharesoutstanding
    ,
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports;

