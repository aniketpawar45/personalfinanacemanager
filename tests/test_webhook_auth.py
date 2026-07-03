import pytest
from fastapi.testclient import TestClient
from api.webhook import app

client = TestClient(app)


def test_webhook_rejects_unauthenticated_request(monkeypatch):
    """Asserts that the webhook gateway drops traffic lacking a valid secret token header."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super_secure_production_token")

    response = client.post(
        "/api/webhook",
        json={"message": {"text": "Coffee 120"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "invalid_spoofed_token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Inbound verification signature mismatch token check dropped."


def test_webhook_accepts_verified_request(monkeypatch, mocker):
    """Asserts that requests containing verified signatures bypass the security firewall."""
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "super_secure_production_token")

    # Mock underlying Telegram API and database engines to isolate routing logic
    mocker.patch("api.webhook.bot.send_message")
    mocker.patch("api.webhook.get_all_categories", return_cache=[])

    response = client.post(
        "/api/webhook",
        json={"callback_query": {"message": {"chat": {"id": 123}, "message_id": 456}, "from": {"id": 789},
                                 "data": "cancel_unk"}},
        headers={"X-Telegram-Bot-Api-Secret-Token": "super_secure_production_token"}
    )
    assert response.status_code == 200