import logging

from fastapi.testclient import TestClient

from app.main import app
from app.proxy.correlation import CORRELATION_ID_HEADER

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_generated_correlation_id():
    response = client.get("/health")

    assert response.headers[CORRELATION_ID_HEADER].startswith("corr_")


def test_health_preserves_inbound_correlation_id_and_logs(caplog):
    caplog.set_level(logging.INFO, logger="app.main")

    response = client.get(
        "/health",
        headers={CORRELATION_ID_HEADER: "client-request-123"},
    )

    assert response.headers[CORRELATION_ID_HEADER] == "client-request-123"
    assert any(
        record.name == "app.main"
        and "request_completed method=GET path=/health status_code=200" in message
        and "correlation_id=client-request-123" in message
        for record in caplog.records
        for message in [record.getMessage()]
    )
