"""Durable resolved-turn presentation checkpoints and acknowledgement."""

from __future__ import annotations

import os
import sys
import uuid

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import campaign_service  # noqa: E402


@pytest.fixture(autouse=True)
def _database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "presentation.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


@pytest.fixture()
def client():
    with TestClient(app) as value:
        yield value


def _create_and_resolve(client: TestClient) -> tuple[str, dict]:
    campaign_id = client.post("/api/campaigns", json={"name": "Presentation Audit"}).json()["id"]
    current = client.get(f"/api/campaigns/{campaign_id}/current").json()
    advice_id = current["advice_options"][0]["id"]
    memo = client.post(
        f"/api/campaigns/{campaign_id}/memos",
        json={
            "creation_mode": "template",
            "advice_id": advice_id,
            "name": "Advice of record",
        },
    ).json()
    resolved = client.post(
        f"/api/campaigns/{campaign_id}/advice",
        json={
            "advice_id": advice_id,
            "expected_turn": 1,
            "idempotency_key": uuid.uuid4().hex,
            "memo_id": memo["id"],
            "memo_revision": memo["revision"],
        },
    )
    assert resolved.status_code == 200, resolved.text
    return campaign_id, current


def test_resolved_turn_checkpoint_survives_repository_restart(client):
    campaign_id, current_before = _create_and_resolve(client)

    authoritative_current = client.get(f"/api/campaigns/{campaign_id}/current").json()
    assert authoritative_current["summary"]["turn_number"] == 2
    assert len(authoritative_current["documents"]) > len(current_before["documents"])

    pending = client.get(f"/api/campaigns/{campaign_id}/presentation").json()
    assert pending["turn_number"] == 1
    assert pending["current_turn"] == current_before
    assert pending["result"]["turn_number"] == 1

    campaign_service.configure_repository()
    restarted = client.get(f"/api/campaigns/{campaign_id}/presentation").json()
    assert restarted == pending


def test_next_call_acknowledgement_is_explicit_and_idempotent(client):
    campaign_id, _ = _create_and_resolve(client)
    endpoint = f"/api/campaigns/{campaign_id}/presentation/acknowledge"

    first = client.post(endpoint, json={"turn_number": 1})
    second = client.post(endpoint, json={"turn_number": 1})
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {
        "campaign_id": campaign_id,
        "turn_number": 1,
        "acknowledged": True,
    }
    assert client.get(f"/api/campaigns/{campaign_id}/presentation").json() is None
    assert client.get(f"/api/campaigns/{campaign_id}/current").json()["summary"]["turn_number"] == 2


def test_multiple_unacknowledged_turns_are_presented_in_order(client):
    campaign_id, _ = _create_and_resolve(client)
    current = client.get(f"/api/campaigns/{campaign_id}/current").json()
    advice_id = current["advice_options"][0]["id"]
    memo = client.post(
        f"/api/campaigns/{campaign_id}/memos",
        json={
            "creation_mode": "template",
            "advice_id": advice_id,
            "name": "Second advice of record",
        },
    ).json()
    second = client.post(
        f"/api/campaigns/{campaign_id}/advice",
        json={
            "advice_id": advice_id,
            "expected_turn": 2,
            "idempotency_key": uuid.uuid4().hex,
            "memo_id": memo["id"],
            "memo_revision": memo["revision"],
        },
    )
    assert second.status_code == 200

    presentation_url = f"/api/campaigns/{campaign_id}/presentation"
    acknowledge_url = f"{presentation_url}/acknowledge"
    assert client.get(presentation_url).json()["turn_number"] == 1
    assert client.post(acknowledge_url, json={"turn_number": 2}).status_code == 409
    assert client.post(acknowledge_url, json={"turn_number": 1}).status_code == 200
    assert client.get(presentation_url).json()["turn_number"] == 2
    assert client.post(acknowledge_url, json={"turn_number": 2}).status_code == 200
    assert client.get(presentation_url).json() is None


@pytest.mark.parametrize(
    "payload",
    [
        {"turn_number": 0},
        {"turn_number": "one"},
        {"turn_number": 1, "unexpected": True},
    ],
)
def test_presentation_acknowledgement_request_is_strict(client, payload):
    campaign_id, _ = _create_and_resolve(client)
    response = client.post(
        f"/api/campaigns/{campaign_id}/presentation/acknowledge", json=payload
    )
    assert response.status_code == 422


def test_unknown_presentation_turn_is_a_stable_conflict(client):
    campaign_id, _ = _create_and_resolve(client)
    response = client.post(
        f"/api/campaigns/{campaign_id}/presentation/acknowledge",
        json={"turn_number": 2},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["error"] == "turn_presentation_not_found"
