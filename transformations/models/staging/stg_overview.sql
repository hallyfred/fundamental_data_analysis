{{ config(materialized='view') }}

{% set overview_fields = [
    "Symbol", "AssetType", "Name", "Description", "Exchange", "Currency", 
    "Country", "Sector", "Industry", "MarketCapitalization", "EBITDA", 
    "PERatio", "DividendYield", "EPS", "52WeekHigh", "52WeekLow", 
    "50DayMovingAverage", "200DayMovingAverage", "SharesOutstanding"
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
    -- Loop Jinja para extrair e limpar o nome das colunas
    {% for field in overview_fields %}
        
        {% set clean_name = field | lower %}
        
        {% if clean_name[0] in ['0','1','2','3','4','5','6','7','8','9'] %}
            {% set clean_name = '_' ~ clean_name %}
        {% endif %}
        
        JSON_EXTRACT_SCALAR(raw_data, '$.{{ field }}') AS {{ clean_name }},
        
    {% endfor %}

    year as partition_year,
    month as partition_month,
    day as partition_day

FROM raw_source