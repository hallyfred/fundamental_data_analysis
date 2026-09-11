-- Grain: (symbol, fiscaldateending, report_type). Earnings per share for the fiscal period.
-- Silver: parse, type, deduplicate and derive reusable components.

{{ config(materialized='view') }}

with source as (
    select raw_data, year as partition_year, month as partition_month,
        day as partition_day, date(year, month, day) as ingest_date
    from {{ ref('stg_earning') }}
),
unnested as (
    select source.*, json_value(raw_data, '$.symbol') as symbol,
        'annual' as report_type, report
    from source, unnest(json_query_array(raw_data, '$.annualEarnings')) as report
    union all
    select source.*, json_value(raw_data, '$.symbol') as symbol,
        'quarterly' as report_type, report
    from source, unnest(json_query_array(raw_data, '$.quarterlyEarnings')) as report
),
parsed as (
    select
        partition_year,
        partition_month,
        partition_day,
        ingest_date,
        symbol,
        report_type,
        json_value(report, '$.fiscalDateEnding') as fiscaldateending_raw,
        safe.parse_date('%Y-%m-%d', json_value(report, '$.fiscalDateEnding')) as fiscaldateending,
        case when report_type = 'quarterly' then safe.parse_date('%Y-%m-%d', json_value(report, '$.reportedDate')) end as reported_date,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.reportedEPS'), 'None'), '-'), 'N/A'), '') as numeric) as reported_eps,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.estimatedEPS'), 'None'), '-'), 'N/A'), '') as numeric) as estimated_eps,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.surprise'), 'None'), '-'), 'N/A'), '') as numeric) as surprise,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.surprisePercentage'), 'None'), '-'), 'N/A'), '') as numeric) as surprise_percentage,
        case when report_type = 'quarterly' then json_value(report, '$.reportTime') end as report_time
    from unnested
),
deduped as (
    select *
    from parsed
    qualify row_number() over (
        partition by symbol, fiscaldateending, report_type
        order by ingest_date desc, partition_day desc, partition_month desc
    ) = 1
)
select * from deduped
