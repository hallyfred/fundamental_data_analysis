{{ config(materialized='view') }}


WITH raw_source AS (
    SELECT
        raw_data,
        year,
        month,
        day
    FROM {{ source('camada_bronze', 'ext_overview') }}
)

SELECT
    year AS partition_year,
    month AS partition_month,
    day AS partition_day
FROM raw_source
