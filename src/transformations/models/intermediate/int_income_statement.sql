-- =============================================================================
-- Model  : int_income_statement
-- Grain  : (symbol, fiscaldateending, report_type)
--          One row per company, fiscal period end date, and report frequency.
--          Semantic: income statement covers a FLOW period (revenue, expenses,
--          profit accumulated over the period ending on fiscaldateending).
-- Source : stg_income_statement → raw_data STRING (Alpha Vantage JSON payload)
-- Layer  : Intermediate (Silver) — parse, type-cast, deduplicate, derive fields.
--          No KPI calculations here (those belong in marts).
-- =============================================================================

{{ config(materialized='view') }}

-- ---------------------------------------------------------------------------
-- CTE 1: attach ingest_date from Hive partitions
-- ---------------------------------------------------------------------------
with source as (

    select
        raw_data,
        year                                          as partition_year,
        month                                         as partition_month,
        day                                           as partition_day,
        date(year, month, day)                        as ingest_date
    from {{ ref('stg_income_statement') }}

),

-- ---------------------------------------------------------------------------
-- CTE 2: unnest annualReports and quarterlyReports arrays into individual rows
-- Each element in the array becomes one row tagged with its report_type.
-- ---------------------------------------------------------------------------
unnested as (

    select
        source.partition_year,
        source.partition_month,
        source.partition_day,
        source.ingest_date,
        'annual'                                      as report_type,
        json_value(source.raw_data, '$.symbol')       as symbol,
        report
    from source,
    unnest(json_extract_array(source.raw_data, '$.annualReports')) as report

    union all

    select
        source.partition_year,
        source.partition_month,
        source.partition_day,
        source.ingest_date,
        'quarterly'                                   as report_type,
        json_value(source.raw_data, '$.symbol')       as symbol,
        report
    from source,
    unnest(json_extract_array(source.raw_data, '$.quarterlyReports')) as report

),

-- ---------------------------------------------------------------------------
-- CTE 3: parse all fields — SAFE_CAST + NULLIF sentinel chain
-- Sentinel values ('None', '-', 'N/A', '') are converted to NULL before cast.
-- fiscaldateending_raw preserves the original string for audit purposes.
-- ---------------------------------------------------------------------------
parsed as (

    select
        symbol,
        report_type,
        partition_year,
        partition_month,
        partition_day,
        ingest_date,

        -- Date fields
        json_value(report, '$.fiscalDateEnding')      as fiscaldateending_raw,
        safe.parse_date(
            '%Y-%m-%d',
            nullif(json_value(report, '$.fiscalDateEnding'), '')
        )                                             as fiscaldateending,

        -- String fields
        json_value(report, '$.reportedCurrency')      as reportedcurrency,

        -- Numeric fields (INT64) — sentinel chain before cast
        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.grossProfit'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as gross_profit,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.totalRevenue'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as total_revenue,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.costOfRevenue'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as cost_of_revenue,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.operatingIncome'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as operating_income,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.sellingGeneralAndAdministrative'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as selling_general_and_administrative,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.researchAndDevelopment'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as research_and_development,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.operatingExpenses'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as operating_expenses,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.netInterestIncome'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as net_interest_income,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.interestIncome'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as interest_income,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.interestExpense'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as interest_expense,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.depreciationAndAmortization'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as depreciation_and_amortization,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.incomeBeforeTax'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as income_before_tax,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.incomeTaxExpense'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as income_tax_expense,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.netIncomeFromContinuingOperations'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as net_income_from_continuing_operations,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.ebit'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as ebit,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.ebitda'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as ebitda,

        safe_cast(
            nullif(nullif(nullif(nullif(
                json_value(report, '$.netIncome'),
            'None'), '-'), 'N/A'), '') as int64
        )                                             as net_income,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.costofGoodsAndServicesSold'), 'None'), '-'), 'N/A'), '') as int64) as cost_of_goods_and_services_sold,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.investmentIncomeNet'), 'None'), '-'), 'N/A'), '') as int64) as investment_income_net,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.nonInterestIncome'), 'None'), '-'), 'N/A'), '') as int64) as non_interest_income,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.otherNonOperatingIncome'), 'None'), '-'), 'N/A'), '') as int64) as other_non_operating_income,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.depreciation'), 'None'), '-'), 'N/A'), '') as int64) as depreciation,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.interestAndDebtExpense'), 'None'), '-'), 'N/A'), '') as int64) as interest_and_debt_expense,
        safe_cast(nullif(nullif(nullif(nullif(json_value(report, '$.comprehensiveIncomeNetOfTax'), 'None'), '-'), 'N/A'), '') as int64) as comprehensive_income_net_of_tax
    from unnested

),

-- ---------------------------------------------------------------------------
-- CTE 4: deduplicate — keep the most recent ingest per (symbol, fiscaldateending, report_type)
-- Tiebreak: partition_day DESC, then partition_month DESC
-- ---------------------------------------------------------------------------
deduped as (

    select
        *,
        row_number() over (
            partition by symbol, fiscaldateending, report_type
            order by ingest_date desc, partition_day desc, partition_month desc
        ) as rn
    from parsed

),

-- ---------------------------------------------------------------------------
-- CTE 5: filter — remove rows with unparseable dates and deduplicate residue
-- ---------------------------------------------------------------------------
filtered as (

    select * from deduped
    where rn = 1

)

-- ---------------------------------------------------------------------------
-- Final SELECT — add derived field ebitda_calc
-- ---------------------------------------------------------------------------
select
    symbol,
    report_type,
    fiscaldateending,
    fiscaldateending_raw,
    reportedcurrency,
    gross_profit,
    total_revenue,
    cost_of_revenue,
    operating_income,
    selling_general_and_administrative,
    research_and_development,
    operating_expenses,
    net_interest_income,
    interest_income,
    interest_expense,
    depreciation_and_amortization,
    income_before_tax,
    income_tax_expense,
    net_income_from_continuing_operations,
    ebit,
    ebitda,
    net_income,

    -- Derived: use direct ebitda when available, fall back to ebit + D&A
    coalesce(
        ebitda,
        case
            when ebit is not null and depreciation_and_amortization is not null
                then safe_add(ebit, depreciation_and_amortization)
            else null
        end
    )                                                 as ebitda_calc,

    ingest_date,
    partition_year,
    partition_month,
    partition_day,
    cost_of_goods_and_services_sold,
    investment_income_net,
    non_interest_income,
    other_non_operating_income,
    depreciation,
    interest_and_debt_expense,
    comprehensive_income_net_of_tax
from filtered
