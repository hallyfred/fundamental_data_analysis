from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pendulum
from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule
from cosmos import DbtTaskGroup, ExecutionConfig, ProfileConfig, ProjectConfig, RenderConfig
from cosmos.constants import LoadMode, TestBehavior

from src.orchestration.alerts import notify_pipeline_failure
from src.orchestration.alpha_vantage_quota_sensor import AlphaVantageQuotaSensor
from src.orchestration.round_robin import build_round_robin_plan

logger = logging.getLogger(__name__)

EXTRACTION_TASK_IDS = [
    "extract_overview",
    "extract_income_statement",
    "extract_balance_sheet",
    "extract_cash_flow",
    "extract_earnings",
]


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

    def store_batch_summary(summary):
        ti.xcom_push(key="batch_summary", value=summary)

    if extractor_name == "overview":
        from src.extract.overview import extract_overview

        return extract_overview(
            symbols=batch,
            run_id=run_id,
            allow_partial=True,
            summary_callback=store_batch_summary,
        )
    elif extractor_name == "income_statement":
        from src.extract.income_statement import extract_income_statement

        return extract_income_statement(
            symbols=batch,
            run_id=run_id,
            allow_partial=True,
            summary_callback=store_batch_summary,
        )
    elif extractor_name == "balance_sheet":
        from src.extract.balance_sheet import extract_balance_sheet

        return extract_balance_sheet(
            symbols=batch,
            run_id=run_id,
            allow_partial=True,
            summary_callback=store_batch_summary,
        )
    elif extractor_name == "cash_flow":
        from src.extract.cash_flow import extract_cash_flow

        return extract_cash_flow(
            symbols=batch,
            run_id=run_id,
            allow_partial=True,
            summary_callback=store_batch_summary,
        )
    elif extractor_name == "earnings":
        from src.extract.earning import extract_earning

        return extract_earning(
            symbols=batch,
            run_id=run_id,
            allow_partial=True,
            summary_callback=store_batch_summary,
        )
    else:
        raise ValueError(f"Unknown extractor: {extractor_name}")


def evaluate_extraction_status(**context):
    """Record extraction states without blocking dbt on incomplete batches.

    Rate limits still fail the extractor itself, which prevents the serial
    chain from issuing more API calls. This gate waits for all extractor task
    states and then allows dbt to rebuild from the last valid Bronze snapshot.
    """
    dag_run = context["dag_run"]
    ti = context["ti"]
    states = {}
    endpoint_summaries = {}
    plan = ti.xcom_pull(task_ids="select_batch", key="ticker_batch_plan") or {}
    aggregate_metrics = {
        "run_id": context.get("run_id"),
        "planned_requests": plan.get("planned_requests", 0),
        "actual_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "rate_limit_requests": 0,
        "retry_requests": 0,
        "watermark_skips": 0,
        "events": [],
    }
    for task_id in EXTRACTION_TASK_IDS:
        task_instance = dag_run.get_task_instance(task_id=task_id)
        states[task_id] = task_instance.state if task_instance else "missing"

        batch_summary = ti.xcom_pull(task_ids=task_id, key="batch_summary")
        if isinstance(batch_summary, dict):
            endpoint_summaries[task_id] = batch_summary
            aggregate_metrics["watermark_skips"] += batch_summary.get("watermark_skips", 0)
            metrics = batch_summary.get("request_metrics", {})
            for metric in (
                "actual_requests",
                "successful_requests",
                "failed_requests",
                "rate_limit_requests",
                "retry_requests",
            ):
                aggregate_metrics[metric] += metrics.get(metric, 0)
            aggregate_metrics["events"].extend(metrics.get("events", []))

    failed = {task_id: state for task_id, state in states.items() if state not in {"success", "skipped"}}
    partial_endpoints = {
        task_id
        for task_id, batch_summary in endpoint_summaries.items()
        if batch_summary.get("status") == "PARTIAL_SUCCESS"
    }
    status = "PARTIAL_SUCCESS" if failed or partial_endpoints else "SUCCESS"
    summary = {
        "status": status,
        "task_states": states,
        "failed_or_blocked_tasks": failed,
        "partial_endpoints": sorted(partial_endpoints),
        "endpoint_summaries": endpoint_summaries,
        "request_metrics": aggregate_metrics,
    }
    ti.xcom_push(key="extraction_status", value=summary)

    if failed:
        logger.warning("Extraction completed with warnings; dbt will use available Bronze data: %s", summary)
    else:
        logger.info("All extraction tasks completed successfully: %s", summary)
    return summary


with DAG(
    dag_id="financial_fundamental_pipeline",
    start_date=pendulum.datetime(2024, 1, 1, tz="America/Sao_Paulo"),
    schedule="0 9 * * 1-7",
    catchup=False,
    max_active_runs=1,
    default_args={"on_failure_callback": notify_pipeline_failure, "retries": 0},
    tags=["fundamental", "alpha_vantage", "dbt", "cosmos"],
    description="Financial pipeline with a weekly five-company round robin and dbt execution through Cosmos.",
) as dag:
    start = EmptyOperator(task_id="start_pipeline")
    wait_for_alpha_vantage_quota = AlphaVantageQuotaSensor(
        task_id="wait_for_alpha_vantage_quota",
        poke_interval=60,
    )
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

    evaluate_extraction = PythonOperator(
        task_id="evaluate_extraction_status",
        python_callable=evaluate_extraction_status,
        trigger_rule=TriggerRule.ALL_DONE,
    )

    # Shared Cosmos and dbt configuration
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

    # 1. Staging layer triggered by its corresponding endpoint
    dbt_stg_overview = make_dbt_group("dbt_stg_overview", "stg_overview")
    dbt_stg_income = make_dbt_group("dbt_stg_income", "stg_income_statement")
    dbt_stg_balance = make_dbt_group("dbt_stg_balance", "stg_balance_sheet")
    dbt_stg_cash_flow = make_dbt_group("dbt_stg_cash_flow", "stg_cash_flow")
    dbt_stg_earning = make_dbt_group("dbt_stg_earning", "stg_earning")

    # 2. Intermediate layer waits for the corresponding staging models
    dbt_int_overview = make_dbt_group("dbt_int_overview", "int_overview")
    dbt_int_income = make_dbt_group("dbt_int_income", "int_income_statement")
    dbt_int_balance = make_dbt_group("dbt_int_balance", "int_balance_sheet")
    dbt_int_cash_flow = make_dbt_group("dbt_int_cash_flow", "int_cash_flow")
    dbt_int_earning = make_dbt_group("dbt_int_earning", "int_earning")

    # 3. Gold / marts layer waits for every intermediate model
    dbt_gold = make_dbt_group("dbt_gold", "fct_fundamental_kpis")

    finish = EmptyOperator(task_id="finish_pipeline")

    # Orchestration:
    # 1. Run extraction tasks serially to enforce the API budget.
    start >> wait_for_alpha_vantage_quota >> select_batch
    select_batch >> extract_overview >> extract_income >> extract_balance >> extract_cash_flow >> extract_earnings

    # 2. Evaluate all extraction outcomes, including failed/upstream_failed
    # tasks, before allowing dbt to rebuild from available Bronze data.
    [extract_overview, extract_income, extract_balance, extract_cash_flow, extract_earnings] >> evaluate_extraction

    # 3. Run staging after the status gate. This decouples transformation from
    # a partial extraction while preserving the serial API request chain.
    evaluate_extraction >> dbt_stg_overview
    evaluate_extraction >> dbt_stg_income
    evaluate_extraction >> dbt_stg_balance
    evaluate_extraction >> dbt_stg_cash_flow
    evaluate_extraction >> dbt_stg_earning

    # 4. Preserve the staging > intermediate > Gold dependency chain.
    dbt_stg_overview >> dbt_int_overview
    dbt_stg_income >> dbt_int_income
    dbt_stg_balance >> dbt_int_balance
    dbt_stg_cash_flow >> dbt_int_cash_flow
    dbt_stg_earning >> dbt_int_earning

    [dbt_int_overview, dbt_int_income, dbt_int_balance, dbt_int_cash_flow, dbt_int_earning] >> dbt_gold
    # Cosmos AFTER_EACH tests must succeed before the pipeline finishes.
    dbt_gold >> finish
