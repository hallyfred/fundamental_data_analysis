{{ config(materialized='view') }}

SELECT
    raw_data,
    year,
    month,
    day
FROM {{ source('bronze', 'ext_cash_flow') }}
