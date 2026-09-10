import sys
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Only Windows is unsupported; DAG import errors on Linux must fail CI.
if sys.platform != "win32":
    from dags.financial_pipeline_dag import dag, run_extractor, select_batch_for_run

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="Airflow requires POSIX/Linux")


def test_select_batch_for_run():
    mock_ti = MagicMock()
    batch = select_batch_for_run(
        data_interval_end=datetime(2026, 9, 7),
        run_id="scheduled__2026-09-07",
        ti=mock_ti,
    )
    assert isinstance(batch, list)
    assert mock_ti.xcom_push.call_count == 2
    mock_ti.xcom_push.assert_any_call(key="ticker_batch", value=batch)
    plan = mock_ti.xcom_push.call_args_list[1].kwargs["value"]
    assert plan["run_date"] == "2026-09-07"
    assert plan["planned_requests"] == 25


def test_manual_run_uses_logical_date_when_interval_end_is_absent():
    mock_ti = MagicMock()
    batch = select_batch_for_run(
        logical_date=datetime(2026, 9, 13),
        run_id="manual__2026-09-13",
        ti=mock_ti,
    )

    plan = mock_ti.xcom_push.call_args_list[1].kwargs["value"]
    assert plan["weekday"] == 6
    assert plan["symbols"] == batch


@patch("src.extract.overview.extract_overview", return_value=["f1.json"])
def test_run_extractor_overview(mock_extract):
    mock_ti = MagicMock()
    mock_ti.xcom_pull.return_value = ["AAPL"]
    assert run_extractor("overview", ti=mock_ti, run_id="scheduled__test") == ["f1.json"]
    mock_extract.assert_called_once_with(symbols=["AAPL"], run_id="scheduled__test")


def test_run_extractor_invalid_raises_error():
    with pytest.raises(ValueError):
        run_extractor("unknown_fn", ti=MagicMock())


def test_all_current_models_have_nonempty_task_groups():
    groups = dag.task_group.children
    expected = {
        "dbt_stg_overview": "stg_overview",
        "dbt_stg_income": "stg_income_statement",
        "dbt_stg_balance": "stg_balance_sheet",
        "dbt_stg_cash_flow": "stg_cash_flow",
        "dbt_stg_earning": "stg_earning",
        "dbt_int_overview": "int_overview",
        "dbt_int_income": "int_income_statement",
        "dbt_int_balance": "int_balance_sheet",
        "dbt_int_cash_flow": "int_cash_flow",
        "dbt_int_earning": "int_earning",
        "dbt_gold": "fct_fundamental_kpis",
    }
    for group_id, model in expected.items():
        tasks = list(groups[group_id])
        assert tasks, f"Empty task group: {group_id}"
        assert any(model in task.task_id for task in tasks), model
    assert any("test" in task.task_id for task in groups["dbt_gold"])


def test_gold_waits_for_all_silver_quality_gates():
    groups = dag.task_group.children
    for endpoint in ["overview", "income", "balance", "cash_flow", "earning"]:
        silver = groups[f"dbt_int_{endpoint}"]
        staging = groups[f"dbt_stg_{endpoint}"]
        staging_leaves = {task.task_id for task in staging.get_leaves()}
        for root in silver.get_roots():
            assert staging_leaves <= root.upstream_task_ids
        silver_leaves = {task.task_id for task in silver.get_leaves()}
        assert silver_leaves
        assert all("test" in task_id for task_id in silver_leaves)
        for root in groups["dbt_gold"].get_roots():
            assert silver_leaves <= root.upstream_task_ids
    gold_leaves = {task.task_id for task in groups["dbt_gold"].get_leaves()}
    assert gold_leaves <= dag.get_task("finish_pipeline").upstream_task_ids


def test_extraction_is_serial_and_runs_do_not_overlap():
    chain = [
        "select_batch",
        "extract_overview",
        "extract_income_statement",
        "extract_balance_sheet",
        "extract_cash_flow",
        "extract_earnings",
    ]
    for before, after in zip(chain, chain[1:], strict=False):
        assert before in dag.get_task(after).upstream_task_ids
        assert dag.get_task(after).trigger_rule == "all_success"
    assert dag.max_active_runs == 1
    assert dag.timezone.name == "America/Sao_Paulo"
