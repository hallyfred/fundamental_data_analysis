from __future__ import annotations

from datetime import datetime

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode

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

    # Configuração base compartilhada do Cosmos / dbt
    project_cfg = ProjectConfig(
        dbt_project_path="/opt/airflow/src/transformations",
        manifest_path="/opt/airflow/src/transformations/target/manifest.json",
    )
    profile_cfg = ProfileConfig(
        profile_name="transformations",
        target_name="dev",
        profiles_dir="/opt/airflow/src/transformations",
    )
    exec_cfg = ExecutionConfig(dbt_executable_path="dbt")

    def make_dbt_group(group_id: str, select_model: str) -> DbtTaskGroup:
        return DbtTaskGroup(
            group_id=group_id,
            project_config=project_cfg,
            profile_config=profile_cfg,
            execution_config=exec_cfg,
            render_config=RenderConfig(
                select=[select_model],
                load_mode=LoadMode.DBT_MANIFEST,
                emit_datasets=False,
            ),
        )

    # 1. Camada Staging (disparada pelo respectivo endpoint)
    dbt_stg_overview = make_dbt_group("dbt_stg_overview", "stg_overview")
    dbt_stg_income = make_dbt_group("dbt_stg_income", "stg_income_statement")
    dbt_stg_balance = make_dbt_group("dbt_stg_balance", "stg_balance_sheet")
    dbt_stg_cash_flow = make_dbt_group("dbt_stg_cash_flow", "stg_cash_flow")
    dbt_stg_earning = make_dbt_group("dbt_stg_earning", "stg_earning")

    # 2. Camada Intermediate (aguarda os stagings correspondentes)
    dbt_int_overview = make_dbt_group("dbt_int_overview", "int_overview_normalized")
    dbt_int_financial = make_dbt_group("dbt_int_financial", "int_financial_metrics")

    # 3. Camada Gold / Marts (aguarda os intermediates)
    dbt_gold = make_dbt_group("dbt_gold", "fundamental_metrics")

    validate_gold = EmptyOperator(task_id="validate_gold_data")
    finish = EmptyOperator(task_id="finish_pipeline")

    # Orquestração:
    # 1. Extrações em série estrita (sem paralelismo entre chamadas da API)
    start >> select_batch
    select_batch >> extract_overview >> extract_income >> extract_balance >> extract_cash_flow >> extract_earnings

    # 2. Cada modelo dbt roda logo após o seu respectivo endpoint de extração
    extract_overview >> dbt_stg_overview
    extract_income >> dbt_stg_income
    extract_balance >> dbt_stg_balance
    extract_cash_flow >> dbt_stg_cash_flow
    extract_earnings >> dbt_stg_earning

    # 3. Cada modelo dbt roda após a sua etapa anterior (stg > intermediate > gold)
    dbt_stg_overview >> dbt_int_overview
    [dbt_stg_balance, dbt_stg_income, dbt_stg_cash_flow] >> dbt_int_financial

    [dbt_int_overview, dbt_int_financial] >> dbt_gold
    [dbt_stg_earning, dbt_gold] >> validate_gold >> finish
