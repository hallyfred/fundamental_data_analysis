from unittest.mock import MagicMock, patch

from src.orchestration.alerts import notify_pipeline_failure


def test_failure_callback_does_not_call_network_without_webhook(monkeypatch):
    monkeypatch.delenv("ALERT_WEBHOOK_URL", raising=False)
    with patch("src.orchestration.alerts.requests.post") as post:
        notify_pipeline_failure(
            {
                "task_instance": MagicMock(dag_id="financial_fundamental_pipeline", task_id="extract_overview"),
                "run_id": "scheduled__test",
                "exception": RuntimeError("rate limit reached"),
            }
        )
    post.assert_not_called()


def test_failure_callback_posts_structured_rate_limit_alert(monkeypatch):
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://alerts.example.test/hook")
    response = MagicMock()
    with patch("src.orchestration.alerts.requests.post", return_value=response) as post:
        notify_pipeline_failure(
            {
                "task_instance": MagicMock(dag_id="financial_fundamental_pipeline", task_id="extract_overview"),
                "run_id": "scheduled__test",
                "exception": RuntimeError("API rate limit reached"),
            }
        )

    payload = post.call_args.kwargs["json"]
    assert payload["reason"] == "rate_limit"
    assert payload["run_id"] == "scheduled__test"
    post.assert_called_once_with("https://alerts.example.test/hook", json=payload, timeout=10)
    response.raise_for_status.assert_called_once_with()
