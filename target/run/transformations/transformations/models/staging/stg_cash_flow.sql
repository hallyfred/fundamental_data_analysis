

  create or replace view `projetodbt-479518`.`alphavantage`.`stg_cash_flow`
  OPTIONS(
      description="""Flattened cash flow reports from the Alpha Vantage CASH_FLOW endpoint."""
    )
  as 



WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM `projetodbt-479518`.`alphavantage`.`ext_cash_flow`
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
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.operatingCashflow'), 'None'), '-'), 'N/A') AS INT64) AS operatingcashflow,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.paymentsForOperatingActivities'), 'None'), '-'), 'N/A') AS INT64) AS paymentsforoperatingactivities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromOperatingActivities'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromoperatingactivities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInOperatingLiabilities'), 'None'), '-'), 'N/A') AS INT64) AS changeinoperatingliabilities,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInOperatingAssets'), 'None'), '-'), 'N/A') AS INT64) AS changeinoperatingassets,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.depreciationDepletionAndAmortization'), 'None'), '-'), 'N/A') AS INT64) AS depreciationdepletionandamortization,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.capitalExpenditures'), 'None'), '-'), 'N/A') AS INT64) AS capitalexpenditures,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInReceivables'), 'None'), '-'), 'N/A') AS INT64) AS changeinreceivables,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInInventory'), 'None'), '-'), 'N/A') AS INT64) AS changeininventory,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.profitLoss'), 'None'), '-'), 'N/A') AS INT64) AS profitloss,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.cashflowFromInvestment'), 'None'), '-'), 'N/A') AS INT64) AS cashflowfrominvestment,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.cashflowFromFinancing'), 'None'), '-'), 'N/A') AS INT64) AS cashflowfromfinancing,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromRepaymentsOfShortTermDebt'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromrepaymentsofshorttermdebt,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.paymentsForRepurchaseOfCommonStock'), 'None'), '-'), 'N/A') AS INT64) AS paymentsforrepurchaseofcommonstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.paymentsForRepurchaseOfEquity'), 'None'), '-'), 'N/A') AS INT64) AS paymentsforrepurchaseofequity,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.paymentsForRepurchaseOfPreferredStock'), 'None'), '-'), 'N/A') AS INT64) AS paymentsforrepurchaseofpreferredstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.dividendPayout'), 'None'), '-'), 'N/A') AS INT64) AS dividendpayout,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.dividendPayoutCommonStock'), 'None'), '-'), 'N/A') AS INT64) AS dividendpayoutcommonstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.dividendPayoutPreferredStock'), 'None'), '-'), 'N/A') AS INT64) AS dividendpayoutpreferredstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromIssuanceOfCommonStock'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromissuanceofcommonstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromIssuanceOfLongTermDebtAndCapitalSecuritiesNet'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromissuanceoflongtermdebtandcapitalsecuritiesnet,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromIssuanceOfPreferredStock'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromissuanceofpreferredstock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromRepurchaseOfEquity'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromrepurchaseofequity,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.proceedsFromSaleOfTreasuryStock'), 'None'), '-'), 'N/A') AS INT64) AS proceedsfromsaleoftreasurystock,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.stockBasedCompensation'), 'None'), '-'), 'N/A') AS INT64) AS stockbasedcompensation,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInCashAndCashEquivalents'), 'None'), '-'), 'N/A') AS INT64) AS changeincashandcashequivalents,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.changeInExchangeRate'), 'None'), '-'), 'N/A') AS INT64) AS changeinexchangerate,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.netIncome'), 'None'), '-'), 'N/A') AS INT64) AS netincome
    ,
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports;

