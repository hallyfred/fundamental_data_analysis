



WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM `projetodbt-479518`.`alphavantage`.`ext_income_statement`
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
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.grossProfit'), 'None'), '-'), 'N/A') AS INT64) AS grossprofit,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.totalRevenue'), 'None'), '-'), 'N/A') AS INT64) AS totalrevenue,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.costOfRevenue'), 'None'), '-'), 'N/A') AS INT64) AS costofrevenue,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.costofGoodsAndServicesSold'), 'None'), '-'), 'N/A') AS INT64) AS costofgoodsandservicessold,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.operatingIncome'), 'None'), '-'), 'N/A') AS INT64) AS operatingincome,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.sellingGeneralAndAdministrative'), 'None'), '-'), 'N/A') AS INT64) AS sellinggeneralandadministrative,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.researchAndDevelopment'), 'None'), '-'), 'N/A') AS INT64) AS researchanddevelopment,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.operatingExpenses'), 'None'), '-'), 'N/A') AS INT64) AS operatingexpenses,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.investmentIncomeNet'), 'None'), '-'), 'N/A') AS INT64) AS investmentincomenet,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.netInterestIncome'), 'None'), '-'), 'N/A') AS INT64) AS netinterestincome,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.interestIncome'), 'None'), '-'), 'N/A') AS INT64) AS interestincome,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.interestExpense'), 'None'), '-'), 'N/A') AS INT64) AS interestexpense,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.nonInterestIncome'), 'None'), '-'), 'N/A') AS INT64) AS noninterestincome,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.otherNonOperatingIncome'), 'None'), '-'), 'N/A') AS INT64) AS othernonoperatingincome,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.depreciation'), 'None'), '-'), 'N/A') AS INT64) AS depreciation,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.depreciationAndAmortization'), 'None'), '-'), 'N/A') AS INT64) AS depreciationandamortization,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.incomeBeforeTax'), 'None'), '-'), 'N/A') AS INT64) AS incomebeforetax,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.incomeTaxExpense'), 'None'), '-'), 'N/A') AS INT64) AS incometaxexpense,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.interestAndDebtExpense'), 'None'), '-'), 'N/A') AS INT64) AS interestanddebtexpense,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.netIncomeFromContinuingOperations'), 'None'), '-'), 'N/A') AS INT64) AS netincomefromcontinuingoperations,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.comprehensiveIncomeNetOfTax'), 'None'), '-'), 'N/A') AS INT64) AS comprehensiveincomenetoftax,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.ebit'), 'None'), '-'), 'N/A') AS INT64) AS ebit,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.ebitda'), 'None'), '-'), 'N/A') AS INT64) AS ebitda,
    
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.netIncome'), 'None'), '-'), 'N/A') AS INT64) AS netincome
    ,
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports