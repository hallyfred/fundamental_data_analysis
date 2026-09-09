{{ config(materialized='view') }}

SELECT
    raw_data,
    year,
    month,
    day
FROM {{ source('camada_bronze', 'ext_income_statement') }}
