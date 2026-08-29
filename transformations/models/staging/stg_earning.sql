{{ config(materialized='view') }}

{% set annual_fields = [
    ("fiscalDateEnding", "DATE"), ("reportedEPS", "FLOAT64")
] %}
{% set quarterly_fields = [
    ("fiscalDateEnding", "DATE"), ("reportedDate", "DATE"), ("reportedEPS", "FLOAT64"),
    ("estimatedEPS", "FLOAT64"), ("surprise", "FLOAT64"),
    ("surprisePercentage", "FLOAT64"), ("reportTime", "STRING")
] %}

WITH raw_source AS (
    SELECT raw_data, year, month, day
    FROM {{ source('camada_bronze', 'ext_earning') }}
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
    {% for field_name, field_type in annual_fields %}
    {% if field_name == 'fiscalDateEnding' %}
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.{{ field_name }}'), 'None'), '-'), 'N/A') AS {{ field_type }}) AS {{ field_name | lower }},
    {% else %}
    CAST(NULL AS DATE) AS reporteddate,
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.{{ field_name }}'), 'None'), '-'), 'N/A') AS {{ field_type }}) AS {{ field_name | lower }},
    {% endif %}
    {% endfor %}
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
    {% for field_name, field_type in quarterly_fields %}
    SAFE_CAST(NULLIF(NULLIF(NULLIF(JSON_VALUE(report, '$.{{ field_name }}'), 'None'), '-'), 'N/A') AS {{ field_type }}) AS {{ field_name | lower }}{% if not loop.last %},{% endif %}
    {% endfor %},
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM reports
WHERE report_type = 'quarterly'
