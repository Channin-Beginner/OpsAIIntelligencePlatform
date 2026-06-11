import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "operator", "password": "OpsAI@2025"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    token = body["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
