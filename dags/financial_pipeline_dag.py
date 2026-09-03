from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig

from config.config import get_symbols_for_day


def select_batch_for_run(**context):
    execution_day = context["data_interval_start"].weekday()
    batch = get_symbols_for_day(execution_day)
    context["ti"].xcom_push(key="ticker_batch", value=batch)
    return batch


def run_extractor(extractor_name: str, **context):
    ti = context["ti"]
    batch = ti.xcom_pull(task_ids="select_batch", key="ticker_batch")

    if extractor_name == "overview":
        from src.extract.overview import extract_overview

        return extract_overview(symbols=batch)
    elif extractor_name == "income_statement":
        from src.extract.income_statement import extract_income_statement

        return extract_income_statement(symbols=batch)
    elif extractor_name == "balance_sheet":
        from src.extract.balance_sheet import extract_balance_sheet

        return extract_balance_sheet(symbols=batch)
    elif extractor_name == "cash_flow":
        from src.extract.cash_flow import extract_cash_flow

        return extract_cash_flow(symbols=batch)
    elif extractor_name == "earnings":
        from src.extract.earning import extract_earning

        return extract_earning(symbols=batch)
    else:
        raise ValueError(f"Extrator não reconhecido: {extractor_name}")


with DAG(
    dag_id="financial_fundamental_pipeline",
    start_date=datetime(2024, 1, 1),
    schedule="0 6 * * 1-7",
    catchup=False,
    tags=["fundamental", "alpha_vantage", "dbt", "cosmos"],
    description="Pipeline financeira com round-robin semanal de 5 empresas por dia e execução dbt via Cosmos.",
) as dag:
    start = EmptyOperator(task_id="start_pipeline")
    select_batch = PythonOperator(
        task_id="select_batch",
        python_callable=select_batch_for_run,
    )

    extract_overview = PythonOperator(
        task_id="extract_overview",
        python_callable=run_extractor,
        op_kwargs={"extractor_name": "overview"},
    )
    extract_income = PythonOperator(
        task_id="extract_income_statement",
        python_callable=run_extractor,
        op_kwargs={"extractor_name": "income_statement"},
    )
    extract_balance = PythonOperator(
        task_id="extract_balance_sheet",
        python_callable=run_extractor,
        op_kwargs={"extractor_name": "balance_sheet"},
    )
    extract_cash_flow = PythonOperator(
        task_id="extract_cash_flow",
        python_callable=run_extractor,
        op_kwargs={"extractor_name": "cash_flow"},
    )
    extract_earnings = PythonOperator(
        task_id="extract_earnings",
        python_callable=run_extractor,
        op_kwargs={"extractor_name": "earnings"},
    )
    load_bronze = EmptyOperator(task_id="load_bronze")

    dbt_tasks = DbtTaskGroup(
        group_id="dbt_daily_models",
        project_config=ProjectConfig(
            dbt_project_path="/opt/airflow/src/transformations",
            manifest_path="/opt/airflow/src/transformations/target/manifest.json",
        ),
        profile_config=ProfileConfig(
            profile_name="default",
            target_name="dev",
            profiles_dir="/opt/airflow/src/transformations",
        ),
        execution_config=ExecutionConfig(
            dbt_executable_path="dbt",
        ),
    )

    validate_gold = EmptyOperator(task_id="validate_gold_data")
    finish = EmptyOperator(task_id="finish_pipeline")

    start >> select_batch
    select_batch >> [
        extract_overview,
        extract_income,
        extract_balance,
        extract_cash_flow,
        extract_earnings,
    ]

    extract_overview >> load_bronze
    extract_income >> load_bronze
    extract_balance >> load_bronze
    extract_cash_flow >> load_bronze
    extract_earnings >> load_bronze

    load_bronze >> dbt_tasks >> validate_gold >> finish
