from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode, TestBehavior

from src.orchestration.alerts import notify_pipeline_failure
from src.orchestration.round_robin import build_round_robin_plan

logger = logging.getLogger(__name__)


def select_batch_for_run(**context):
    scheduled_for = context.get("data_interval_end") or context.get("logical_date")
    if scheduled_for is None:
        raise ValueError("Airflow run context has no data_interval_end or logical_date.")

    plan = build_round_robin_plan(scheduled_for, run_id=context.get("run_id"))
    batch = plan["symbols"]
    context["ti"].xcom_push(key="ticker_batch", value=batch)
    context["ti"].xcom_push(key="ticker_batch_plan", value=plan)
    logger.info("Round-robin plan: %s", json.dumps(plan))
    return batch


def run_extractor(extractor_name: str, **context):
    ti = context["ti"]
    batch = ti.xcom_pull(task_ids="select_batch", key="ticker_batch")
    run_id = context.get("run_id")

    if extractor_name == "overview":
        from src.extract.overview import extract_overview

        return extract_overview(symbols=batch, run_id=run_id)
    elif extractor_name == "income_statement":
        from src.extract.income_statement import extract_income_statement

        return extract_income_statement(symbols=batch, run_id=run_id)
    elif extractor_name == "balance_sheet":
        from src.extract.balance_sheet import extract_balance_sheet

        return extract_balance_sheet(symbols=batch, run_id=run_id)
    elif extractor_name == "cash_flow":
        from src.extract.cash_flow import extract_cash_flow

        return extract_cash_flow(symbols=batch, run_id=run_id)
    elif extractor_name == "earnings":
        from src.extract.earning import extract_earning

        return extract_earning(symbols=batch, run_id=run_id)
    else:
        raise ValueError(f"Extrator não reconhecido: {extractor_name}")


with DAG(
    dag_id="financial_fundamental_pipeline",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Sao_Paulo"),
    schedule="0 6 * * 1-7",
    catchup=False,
    max_active_runs=1,
    default_args={"on_failure_callback": notify_pipeline_failure, "retries": 0},
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
    dbt_project_path = Path(__file__).resolve().parents[1] / "src" / "transformations"
    project_cfg = ProjectConfig(
        dbt_project_path=dbt_project_path,
        manifest_path=dbt_project_path / "target" / "manifest.json",
    )
    profile_cfg = ProfileConfig(
        profile_name="transformations",
        target_name=os.getenv("DBT_TARGET", "prod"),
        profiles_yml_filepath=dbt_project_path / "profiles.yml",
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
                load_method=LoadMode.DBT_MANIFEST,
                emit_datasets=False,
                test_behavior=TestBehavior.AFTER_EACH,
            ),
        )

    # 1. Camada Staging (disparada pelo respectivo endpoint)
    dbt_stg_overview = make_dbt_group("dbt_stg_overview", "stg_overview")
    dbt_stg_income = make_dbt_group("dbt_stg_income", "stg_income_statement")
    dbt_stg_balance = make_dbt_group("dbt_stg_balance", "stg_balance_sheet")
    dbt_stg_cash_flow = make_dbt_group("dbt_stg_cash_flow", "stg_cash_flow")
    dbt_stg_earning = make_dbt_group("dbt_stg_earning", "stg_earning")

    # 2. Camada Intermediate (aguarda os stagings correspondentes)
    dbt_int_overview = make_dbt_group("dbt_int_overview", "int_overview")
    dbt_int_income = make_dbt_group("dbt_int_income", "int_income_statement")
    dbt_int_balance = make_dbt_group("dbt_int_balance", "int_balance_sheet")
    dbt_int_cash_flow = make_dbt_group("dbt_int_cash_flow", "int_cash_flow")
    dbt_int_earning = make_dbt_group("dbt_int_earning", "int_earning")

    # 3. Camada Gold / Marts (aguarda os intermediates)
    dbt_gold = make_dbt_group("dbt_gold", "fct_fundamental_kpis")

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
    dbt_stg_income >> dbt_int_income
    dbt_stg_balance >> dbt_int_balance
    dbt_stg_cash_flow >> dbt_int_cash_flow
    dbt_stg_earning >> dbt_int_earning

    [dbt_int_overview, dbt_int_income, dbt_int_balance, dbt_int_cash_flow, dbt_int_earning] >> dbt_gold
    # Cosmos AFTER_EACH tests must succeed before the pipeline finishes.
    dbt_gold >> finish
