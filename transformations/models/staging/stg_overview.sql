{{ config(materialized='view') }}

-- JSON keys and BigQuery types aligned with OverviewSchema in contract.py
{% set overview_fields = [
    ("Symbol", "STRING"), ("AssetType", "STRING"), ("Name", "STRING"), ("Description", "STRING"),
    ("CIK", "STRING"), ("Exchange", "STRING"), ("Currency", "STRING"), ("Country", "STRING"),
    ("Sector", "STRING"), ("Industry", "STRING"), ("Address", "STRING"), ("OfficialSite", "STRING"),
    ("FiscalYearEnd", "STRING"), ("LatestQuarter", "STRING"), ("DividendDate", "STRING"),
    ("ExDividendDate", "STRING"), ("MarketCapitalization", "INT64"), ("EBITDA", "INT64"),
    ("RevenueTTM", "INT64"), ("GrossProfitTTM", "INT64"), ("SharesOutstanding", "INT64"),
    ("SharesFloat", "INT64"), ("PERatio", "FLOAT64"), ("PEGRatio", "FLOAT64"),
    ("BookValue", "FLOAT64"), ("DividendPerShare", "FLOAT64"), ("DividendYield", "FLOAT64"),
    ("EPS", "FLOAT64"), ("RevenuePerShareTTM", "FLOAT64"), ("ProfitMargin", "FLOAT64"),
    ("OperatingMarginTTM", "FLOAT64"), ("ReturnOnAssetsTTM", "FLOAT64"),
    ("ReturnOnEquityTTM", "FLOAT64"), ("DilutedEPSTTM", "FLOAT64"),
    ("QuarterlyEarningsGrowthYOY", "FLOAT64"), ("QuarterlyRevenueGrowthYOY", "FLOAT64"),
    ("AnalystTargetPrice", "FLOAT64"), ("AnalystRatingStrongBuy", "FLOAT64"),
    ("AnalystRatingBuy", "FLOAT64"), ("AnalystRatingHold", "FLOAT64"),
    ("AnalystRatingSell", "FLOAT64"), ("AnalystRatingStrongSell", "FLOAT64"),
    ("TrailingPE", "FLOAT64"), ("ForwardPE", "FLOAT64"), ("PriceToSalesRatioTTM", "FLOAT64"),
    ("PriceToBookRatio", "FLOAT64"), ("EVToRevenue", "FLOAT64"), ("EVToEBITDA", "FLOAT64"),
    ("Beta", "FLOAT64"), ("PercentInsiders", "FLOAT64"), ("PercentInstitutions", "FLOAT64"),
    ("52WeekHigh", "FLOAT64"), ("52WeekLow", "FLOAT64"), ("50DayMovingAverage", "FLOAT64"),
    ("200DayMovingAverage", "FLOAT64")
] %}

WITH raw_source AS (
    SELECT 
        raw_data,
        year,
        month,
        day
    FROM {{ source('camada_bronze', 'ext_overview') }}
)

SELECT
    -- Unpack the tuple into field_name and field_type variables
    {% for field_name, field_type in overview_fields %}
        
        {% set clean_name = field_name | lower %}
        
        {% if clean_name[0] in ['0','1','2','3','4','5','6','7','8','9'] %}
            {% set clean_name = '_' ~ clean_name %}
        {% endif %}
        
        -- Safely extract, handle 'None' strings, and cast to the strict type
        CAST(
            NULLIF(JSON_EXTRACT_SCALAR(raw_data, '$.{{ field_name }}'), 'None') 
            AS {{ field_type }}
        ) AS {{ clean_name }},
        
    {% endfor %}

    year as partition_year,
    month as partition_month,
    day as partition_day

FROM raw_source