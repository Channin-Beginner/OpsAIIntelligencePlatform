"""阶段一 1.D 验收：Webhook → Incident → 状态机 → 去重。"""

import uuid

WEBHOOK_SAMPLE = {
    "status": "firing",
    "alerts": [
        {
            "status": "firing",
            "labels": {
                "alertname": "HighErrorRate",
                "service": "ecom-api-portal",
                "severity": "critical",
            },
            "annotations": {"summary": "portal 5xx > 5%"},
            "startsAt": "2025-11-11T10:00:00Z",
        }
    ],
}


def _webhook_payload(fingerprint: str) -> dict:
    payload = {**WEBHOOK_SAMPLE, "alerts": [{**WEBHOOK_SAMPLE["alerts"][0], "fingerprint": fingerprint}]}
    return payload


def test_health_contract(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["status"] in ("ok", "degraded")
    assert body["data"]["service"] == "ops-api"
    assert "version" in body["data"]


def test_webhook_creates_incident_and_dedup(client, auth_headers):
    fingerprint = f"pytest-accept-{uuid.uuid4().hex[:12]}"

    first = client.post("/webhooks/alertmanager", json=_webhook_payload(fingerprint))
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["code"] == 200
    assert first_body["data"]["incident_created"] is True
    assert first_body["data"]["incident_id"] is not None
    incident_id = first_body["data"]["incident_id"]

    second = client.post("/webhooks/alertmanager", json=_webhook_payload(fingerprint))
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["data"]["incident_created"] is False
    assert second_body["data"]["incident_id"] == incident_id

    list_resp = client.get("/api/v1/incidents", headers=auth_headers)
    assert list_resp.status_code == 200
    items = list_resp.json()["data"]["items"]
    matched = [item for item in items if item["id"] == incident_id]
    assert len(matched) == 1
    assert matched[0]["status"] == "open"


def test_state_machine_start_investigation(client, auth_headers):
    fingerprint = f"pytest-sm-{uuid.uuid4().hex[:12]}"
    webhook = client.post("/webhooks/alertmanager", json=_webhook_payload(fingerprint))
    incident_id = webhook.json()["data"]["incident_id"]

    patch = client.patch(
        f"/api/v1/incidents/{incident_id}",
        headers=auth_headers,
        json={"action": "start_investigation"},
    )
    assert patch.status_code == 200
    assert patch.json()["data"]["status"] == "investigating"

    timeline = client.get(f"/api/v1/incidents/{incident_id}/timeline", headers=auth_headers)
    assert timeline.status_code == 200
    events = timeline.json()["data"]["items"]
    status_events = [e for e in events if e["event_type"] == "status_change"]
    assert any("investigating" in e["content"] for e in status_events)
