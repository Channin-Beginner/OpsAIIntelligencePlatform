"""阶段三 3.C DeepSeek RCA 编排测试。"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.agent.rca.rca_agent import analyze_incident, gather_evidence
from app.models.alert_event import AlertEvent
from app.models.incident import Incident


def _sample_incident() -> Incident:
    return Incident(
        id=10,
        incident_no="INC-20251111-0099",
        title="portal HTTP 5xx 比例过高",
        description="HighErrorRate firing",
        status="investigating",
        severity="critical",
        service="ecom-api-portal",
    )


def _sample_alert() -> AlertEvent:
    return AlertEvent(
        id=1,
        fingerprint="fp-portal-500",
        source="alertmanager",
        status="firing",
        severity="critical",
        alertname="HighErrorRate",
        service="ecom-api-portal",
        title="portal 5xx > 5%",
        summary="HTTP 5xx error rate exceeds threshold",
    )


@patch("app.agent.rca.rca_agent.search_incident_context")
@patch("app.agent.rca.rca_agent.search_traces")
@patch("app.agent.rca.rca_agent.query_logs")
@patch("app.agent.rca.rca_agent.query_metrics")
def test_gather_evidence_includes_four_pillars(
    mock_metrics,
    mock_logs,
    mock_traces,
    mock_rag,
):
    mock_metrics.return_value = {"type": "metric", "source": "prometheus", "summary": "up=1"}
    mock_logs.return_value = {"type": "log", "source": "loki", "summary": "ERROR 500"}
    mock_traces.return_value = {"type": "trace", "source": "tempo", "summary": "2 traces"}
    mock_rag.return_value = {"type": "kb", "source": "incident_rag", "summary": "1 KB"}

    db = MagicMock()
    incident = _sample_incident()
    evidence = gather_evidence(db, incident, primary_alert=_sample_alert())

    assert len(evidence) >= 4
    types = {e["type"] for e in evidence}
    assert types >= {"metric", "log", "trace", "kb"}
    assert mock_metrics.call_count >= 1


@patch("app.agent.rca.rca_agent.match_runbook_ids")
@patch("app.agent.rca.rca_agent.runbooks_for_llm_context")
@patch("app.agent.rca.rca_agent.chat_json")
@patch("app.agent.rca.rca_agent.gather_evidence")
@patch("app.agent.rca.rca_agent.get_settings")
def test_analyze_incident_with_llm(
    mock_settings, mock_gather, mock_chat, mock_runbooks_ctx, mock_match
):
    settings = MagicMock()
    settings.llm_api_key = "test-key"
    mock_settings.return_value = settings
    mock_runbooks_ctx.return_value = [{"id": 1, "title": "Portal 500"}]
    mock_match.return_value = [1]

    mock_gather.return_value = [
        {"type": "metric", "source": "prometheus", "summary": "error high"},
    ]
    mock_chat.return_value = (
        {
            "hypothesis": "chaos 路由返回 500",
            "confidence": 0.88,
            "suggested_actions": ["关闭 portal-500 flag"],
            "suggested_runbook_ids": [],
            "evidence_refs": [{"index": 0, "reason": "错误率升高"}],
        },
        "deepseek-chat",
    )

    result = analyze_incident(MagicMock(), _sample_incident())
    assert result["hypothesis"] == "chaos 路由返回 500"
    assert result["confidence"] == 0.88
    assert result["model_name"] == "deepseek-chat"
    assert result["evidence"]


@patch("app.agent.rca.rca_agent.match_runbook_ids")
@patch("app.agent.rca.rca_agent.runbooks_for_llm_context")
@patch("app.agent.rca.rca_agent.gather_evidence")
@patch("app.agent.rca.rca_agent.get_settings")
def test_analyze_incident_fallback_without_api_key(
    mock_settings, mock_gather, mock_runbooks_ctx, mock_match
):
    settings = MagicMock()
    settings.llm_api_key = ""
    mock_settings.return_value = settings
    mock_runbooks_ctx.return_value = []
    mock_match.return_value = [1]

    mock_gather.return_value = [
        {"type": "kb", "source": "incident_rag", "summary": "2 条相似历史 Incident"},
        {"type": "log", "source": "loki", "summary": "ERROR portal 500"},
    ]

    result = analyze_incident(MagicMock(), _sample_incident())
    assert result["model_name"] == "rule-based-fallback"
    assert result["hypothesis"]
    assert 0 < result["confidence"] <= 0.85


@patch("app.agent.rca.service._release_rca_lock")
@patch("app.agent.rca.service._acquire_rca_lock")
@patch("app.agent.rca.service.analyze_incident")
def test_trigger_rca_persists_result(mock_analyze, mock_lock, mock_unlock):
    from app.agent.rca.service import trigger_rca
    from app.schemas.common import RcaTriggerRequest

    mock_lock.return_value = True
    mock_analyze.return_value = {
        "hypothesis": "测试根因",
        "confidence": 0.77,
        "evidence": [{"type": "metric", "source": "prometheus", "summary": "ok"}],
        "suggested_actions": ["检查服务"],
        "suggested_runbook_ids": [],
        "model_name": "deepseek-chat",
    }

    db = MagicMock()
    incident = _sample_incident()
    db.scalar.return_value = None
    db.get.return_value = incident

    def flush_side_effect():
        row = db.add.call_args[0][0]
        row.id = 99

    db.flush.side_effect = flush_side_effect

    with patch("app.agent.rca.service._get_incident_or_404", return_value=incident):
        with patch("app.agent.rca.service._get_primary_alert", return_value=None):
            with patch("app.agent.rca.service._add_timeline"):
                result = trigger_rca(db, 10, RcaTriggerRequest(), actor_id=1)

    assert result.hypothesis == "测试根因"
    assert result.confidence == pytest.approx(0.77)
    mock_unlock.assert_called_once()


@patch("app.agent.rca.service._acquire_rca_lock")
def test_trigger_rca_conflict_when_locked(mock_lock):
    from app.agent.rca.service import trigger_rca
    from app.common.exceptions import ConflictError
    from app.schemas.common import RcaTriggerRequest

    mock_lock.return_value = False
    db = MagicMock()
    incident = _sample_incident()
    db.scalar.return_value = None

    with patch("app.agent.rca.service._get_incident_or_404", return_value=incident):
        with pytest.raises(ConflictError):
            trigger_rca(db, 10, RcaTriggerRequest(), actor_id=1)
