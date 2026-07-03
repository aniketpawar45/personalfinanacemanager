import pytest
from fastapi.testclient import TestClient
import api.webhook
from api.webhook import app

client = TestClient(app)


def test_webhook_rejects_unauthenticated_request(monkeypatch):
    """Asserts that the webhook gateway drops traffic lacking a valid secret token header."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super_secure_production_token")
    # Re-read environment configurations to apply the secret token locally
    api.webhook.TELEGRAM_WEBHOOK_SECRET = "super_secure_production_token"

    response = client.post(
        "/api/webhook",
        json={
            "message": {
                "message_id": 999,
                "from": {"id": 12345},
                "chat": {"id": 54321},
                "text": "Coffee 120"
            }
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_spoofed_token"}
    )
    # The server gateway now cleanly intercepts the unauthorized webhook request
    assert response.status_code == 401


def test_webhook_accepts_verified_request(monkeypatch, mocker):
    """Asserts that requests containing verified signatures bypass the security firewall."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super_secure_production_token")
    api.webhook.TELEGRAM_WEBHOOK_SECRET = "super_secure_production_token"

    # FIX: Patch at the class level rather than the frozen object instance
    mock_send = mocker.patch("telegram.Bot.send_message", new_callable=mocker.AsyncMock)
    mocker.patch("api.webhook.get_all_categories", return_value=[])

    response = client.post(
        "/api/webhook",
        json={
            "message": {
                "message_id": 999,
                "from": {"id": 12345},
                "chat": {"id": 54321},
                "text": "/start"
            }
        },
        headers={"X-Telegram-Bot-Api-Secret-Token": "super_secure_production_token"}
    )
    assert response.status_code == 200
    assert mock_send.called