"""阶段五：Grafana Webhook、KB、Postmortem、Dashboard 验收。"""

import uuid

WEBHOOK_SAMPLE = {
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "GrafanaHighErrorRate",
                "service": "ecom-api-portal",
                "severity": "high",
            },
            "annotations": {"summary": "Grafana unified alerting test"},
            "startsAt": "2025-11-11T10:00:00Z",
        }
    ],
}


def _webhook_payload(fingerprint: str) -> dict:
    return {
        **WEBHOOK_SAMPLE,
        "alerts": [{**WEBHOOK_SAMPLE["alerts"][0], "fingerprint": fingerprint}],
    }


def test_grafana_webhook_source_grafana(client, auth_headers):
    fingerprint = f"pytest-grafana-{uuid.uuid4().hex[:12]}"
    resp = client.post("/webhooks/grafana", json=_webhook_payload(fingerprint))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["incident_created"] is True

    alerts = client.get(
        "/api/v1/alerts",
        headers=auth_headers,
        params={"source": "grafana", "fingerprint": fingerprint},
    )
    assert alerts.status_code == 200
    items = alerts.json()["data"]["items"]
    assert any(item["source"] == "grafana" for item in items)


def test_dashboard_overview(client, auth_headers):
    resp = client.get("/api/v1/dashboard/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "core_kpi" in data
    assert "alert_curve_24h" in data
    assert "incident_funnel" in data
    assert "service_health_top" in data
    assert "rca_quality" in data
    assert "mttr_trend_30d" in data
    assert "top_root_causes" in data
    assert "runbook_success" in data
    assert "open_incidents" in data["core_kpi"]


def test_kb_publish_flow(client, auth_headers):
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "OpsAI@2025"},
    )
    assert admin_login.status_code == 200
    admin_headers = {
        "Authorization": f"Bearer {admin_login.json()['data']['access_token']}"
    }

    create = client.post(
        "/api/v1/kb/articles",
        headers=admin_headers,
        json={
            "title": f"pytest KB {uuid.uuid4().hex[:8]}",
            "summary": "阶段五测试",
            "content": "## 测试\n复盘正文",
            "tags_text": "pytest,postmortem",
            "service": "ecom-api-portal",
        },
    )
    assert create.status_code == 201
    article_id = create.json()["data"]["id"]
    assert create.json()["data"]["status"] == "draft"

    publish = client.post(
        f"/api/v1/kb/articles/{article_id}/publish",
        headers=admin_headers,
    )
    assert publish.status_code == 200
    assert publish.json()["data"]["status"] == "published"


def test_postmortem_on_resolve(client, auth_headers):
    fingerprint = f"pytest-pm-{uuid.uuid4().hex[:12]}"
    webhook = client.post("/webhooks/alertmanager", json=_webhook_payload(fingerprint))
    incident_id = webhook.json()["data"]["incident_id"]

    for action in ("acknowledge", "start_investigation", "mitigate", "resolve"):
        patch = client.patch(
            f"/api/v1/incidents/{incident_id}",
            headers=auth_headers,
            json={"action": action},
        )
        assert patch.status_code == 200

    kb_list = client.get(
        "/api/v1/kb/articles",
        headers=auth_headers,
        params={"source_incident_id": incident_id},
    )
    assert kb_list.status_code == 200
    items = kb_list.json()["data"]["items"]
    assert len(items) >= 1
    assert items[0]["status"] == "draft"
    assert items[0]["source_incident_id"] == incident_id
