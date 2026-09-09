-- Grain: one raw OVERVIEW payload per ingestion record; duplicates preserved.
{{ config(materialized='view') }}

select raw_data, year, month, day
from {{ source('camada_bronze', 'ext_overview') }}
