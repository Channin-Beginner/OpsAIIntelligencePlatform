"""阶段四 Runbook 沙箱执行器与推荐测试。"""

from unittest.mock import MagicMock, patch

import pytest

from app.common.exceptions import BadRequestError
from app.runbook.recommend import match_runbook_ids
from app.runbook.runbook_executor import (
    execute_runbook_steps,
    execute_step,
    resolve_action_url,
)


def test_resolve_action_url_rejects_external_host():
    with pytest.raises(BadRequestError, match="不允许访问主机"):
        resolve_action_url("http://evil.example.com/admin/chaos/clear")


def test_resolve_action_url_rejects_non_chaos_path():
    with pytest.raises(BadRequestError, match="路径须以"):
        resolve_action_url("/admin/users/delete")


def test_resolve_action_url_allows_relative_chaos_path():
    with patch("app.runbook.runbook_executor.get_settings") as mock_settings:
        mock_settings.return_value = MagicMock(ecom_admin_base_url="http://127.0.0.1:8081")
        url = resolve_action_url("/admin/chaos/portal-500")
    assert url == "http://127.0.0.1:8081/admin/chaos/portal-500"


def test_execute_manual_step():
    result = execute_step(
        {
            "order": 1,
            "title": "人工确认",
            "action_type": "manual",
            "description": "检查 Grafana",
        }
    )
    assert result["status"] == "manual"


@patch("app.runbook.runbook_executor.execute_http_step")
def test_execute_runbook_steps_stops_on_http_failure(mock_http):
    mock_http.return_value = {
        "success": False,
        "status_code": 500,
        "error": "HTTP 500",
    }
    steps = [
        {
            "order": 1,
            "title": "fail",
            "action_type": "http",
            "action": {"method": "POST", "path": "/admin/chaos/portal-500"},
        },
        {"order": 2, "title": "skip", "action_type": "manual"},
    ]
    results, ok, err = execute_runbook_steps(steps)
    assert ok is False
    assert len(results) == 1
    assert err


def test_match_runbook_ids_by_service_and_alert():
    rb1 = MagicMock(id=1, service_tags=["ecom-api-portal"], alert_names=["HighErrorRate"])
    rb2 = MagicMock(id=2, service_tags=["ecom-api-admin"], alert_names=["HighP95Latency"])
    db = MagicMock()
    db.scalars.return_value.all.return_value = [rb1, rb2]

    ids = match_runbook_ids(
        db,
        service="ecom-api-portal",
        alertname="HighErrorRate",
    )
    assert ids == [1]
