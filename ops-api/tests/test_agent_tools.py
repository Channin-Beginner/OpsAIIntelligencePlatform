"""阶段三 3.B Agent 工具层单元测试。"""

from unittest.mock import MagicMock, patch

import pytest

from app.agent.rca.incident_rag import search_incident_context
from app.agent.rca.logs_tool import query_logs
from app.agent.rca.metrics_tool import query_metrics
from app.agent.rca.traces_tool import get_trace_by_id, search_traces
from app.models.incident import Incident
from app.models.kb_article import KbArticle


def test_metrics_tool_rejects_unknown_query_id():
    with pytest.raises(ValueError, match="不支持的 query_id"):
        query_metrics("drop_database")


@patch("app.agent.rca.metrics_tool.httpx.Client")
def test_metrics_tool_success(mock_client_cls):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "data": {
            "resultType": "vector",
            "result": [
                {
                    "metric": {"job": "ecom-api-portal"},
                    "value": [1710000000, "1"],
                }
            ],
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

    evidence = query_metrics("service_up", job="ecom-api-portal")
    assert evidence["type"] == "metric"
    assert evidence["source"] == "prometheus"
    assert "ecom-api-portal=1" in evidence["summary"]


@patch("app.agent.rca.logs_tool._query_loki")
def test_logs_tool_loki_path(mock_loki):
    mock_loki.return_value = {
        "status": "success",
        "data": {
            "result": [
                {
                    "stream": {"service": "ecom-api-portal"},
                    "values": [["1710000000000000000", "ERROR portal 500"]],
                }
            ]
        },
    }
    evidence = query_logs("error_logs", service="ecom-api-portal")
    assert evidence["type"] == "log"
    assert evidence["source"] == "loki"
    assert evidence["detail"]["backend"] == "loki"


@patch("app.agent.rca.traces_tool.httpx.Client")
def test_traces_tool_get_by_id(mock_client_cls):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"batches": [{"scopeSpans": [{"spans": []}]}]}
    mock_response.raise_for_status = MagicMock()
    mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

    evidence = get_trace_by_id("abc123def456")
    assert evidence["type"] == "trace"
    assert evidence["source"] == "tempo"
    assert "trace" in evidence["summary"].lower()


@patch("app.agent.rca.traces_tool.httpx.Client")
def test_traces_tool_search(mock_client_cls):
    mock_response = MagicMock()
    mock_response.json.return_value = {"traces": [{"traceID": "t1"}]}
    mock_response.raise_for_status = MagicMock()
    mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_response

    evidence = search_traces("ecom-api-portal")
    assert evidence["type"] == "trace"
    assert evidence["detail"]["service"] == "ecom-api-portal"


def test_incident_rag_keyword_search():
    db = MagicMock()
    incident = Incident(
        id=1,
        incident_no="INC-20251111-0001",
        title="portal HTTP 5xx 比例过高",
        description="HighErrorRate firing on portal",
        status="resolved",
        severity="critical",
        service="ecom-api-portal",
        root_cause_preview="chaos /chaos/error 路由返回 500",
    )
    article = KbArticle(
        id=1,
        title="Portal 5xx 激增",
        summary="检查 chaos flag",
        content="关闭 portal-500",
        tags_text="portal,5xx",
        service="ecom-api-portal",
        status="published",
    )

    def scalars_side_effect(stmt):
        stmt_str = str(stmt)
        if "kb_article" in stmt_str:
            return MagicMock(all=lambda: [article])
        return MagicMock(all=lambda: [incident])

    db.scalars.side_effect = scalars_side_effect

    evidence = search_incident_context(
        db,
        "portal 5xx chaos error",
        service="ecom-api-portal",
    )
    assert evidence["type"] == "kb"
    assert evidence["detail"]["incidents"]
    assert evidence["detail"]["kb_articles"]
