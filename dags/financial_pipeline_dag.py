from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator

from config.config import get_symbols_for_day

from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig


def select_batch_for_run(**context):
    execution_day = context["data_interval_start"].weekday()
    batch = get_symbols_for_day(execution_day)
    context["ti"].xcom_push(key="ticker_batch", value=batch)
    return batch


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

    extract_overview = EmptyOperator(task_id="extract_overview")
    extract_income = EmptyOperator(task_id="extract_income_statement")
    extract_balance = EmptyOperator(task_id="extract_balance_sheet")
    extract_cash_flow = EmptyOperator(task_id="extract_cash_flow")
    extract_earnings = EmptyOperator(task_id="extract_earnings")
    load_bronze = EmptyOperator(task_id="load_bronze")

    dbt_tasks = DbtTaskGroup(
        group_id="dbt_daily_models",
        project_config=ProjectConfig(
            dbt_project_path="/opt/airflow/transformations",
            manifest_path="/opt/airflow/transformations/target/manifest.json",
        ),
        profile_config=ProfileConfig(
            profile_name="default",
            target_name="dev",
            profiles_dir="/opt/airflow/transformations",
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
