"""Persistent advice-memo workflow and authority-boundary regressions."""

from __future__ import annotations

import hashlib
import os
import sys
import uuid

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

from app.ai.logging import ModelRun, get_run_store  # noqa: E402
from app.ai.runner import AiArtifact, ArtifactStatus  # noqa: E402
from app.ai.schemas import MemoDraft  # noqa: E402
from app.main import app  # noqa: E402
from app.services import campaign_service  # noqa: E402


@pytest.fixture(autouse=True)
def _database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "memos.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


@pytest.fixture()
def client():
    with TestClient(app) as value:
        yield value


@pytest.fixture()
def campaign(client):
    return client.post("/api/campaigns", json={"name": "Memo Audit"}).json()["id"]


def _advice(client, campaign_id):
    return client.get(f"/api/campaigns/{campaign_id}/current").json()["advice_options"][0]["id"]


def _manual(client, campaign_id, advice_id, content="Original exact content"):
    response = client.post(
        f"/api/campaigns/{campaign_id}/memos",
        json={
            "creation_mode": "manual",
            "advice_id": advice_id,
            "name": "Water response memorandum",
            "content": content,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _send(client, campaign_id, advice_id, memo, key=None):
    return client.post(
        f"/api/campaigns/{campaign_id}/advice",
        json={
            "advice_id": advice_id,
            "expected_turn": 1,
            "idempotency_key": key or uuid.uuid4().hex,
            "memo_id": memo["id"],
            "memo_revision": memo["revision"],
        },
    )


def test_manual_create_edit_is_persistent_and_never_changes_world_state(client, campaign):
    advice_id = _advice(client, campaign)
    before = client.get(f"/api/campaigns/{campaign}/current").json()["world_state"]
    memo = _manual(client, campaign, advice_id)
    edited = client.patch(
        f"/api/campaigns/{campaign}/memos/{memo['id']}",
        json={
            "expected_revision": 1,
            "name": "Edited water response memorandum",
            "content": "Player-edited exact content",
        },
    )
    assert edited.status_code == 200
    body = edited.json()
    assert body["revision"] == 2
    assert [revision["source"] for revision in body["revisions"]] == ["player", "player"]
    assert body["revisions"][0]["content"] == "Original exact content"
    assert client.get(f"/api/campaigns/{campaign}/current").json()["world_state"] == before

    campaign_service.configure_repository()
    persisted = client.get(f"/api/campaigns/{campaign}/memos").json()
    assert persisted[0]["content"] == "Player-edited exact content"


def test_ai_assisted_memo_records_model_run_provenance(client, campaign, monkeypatch):
    advice_id = _advice(client, campaign)
    run = ModelRun(
        prompt_name="memo_drafter",
        prompt_version="v1",
        model_name="audit-model",
        provider="test-provider",
        validation_status="ok",
        campaign_id=campaign,
        turn_number=1,
    )
    draft = MemoDraft(
        recommendation="Issue a bounded notice.",
        rationale="The record supports immediate notice.",
        operational_steps=["Brief the hospital."],
        communications="State verified facts only.",
        likely_opposition=["Contractor review."],
        second_order_risks=["Short-term pressure."],
        fallback_plan="Preserve the written advice.",
    )

    def fake_run_artifact(**_kwargs):
        get_run_store().add(run)
        return AiArtifact(status=ArtifactStatus.OK, content=draft, run=run)

    monkeypatch.setattr(campaign_service, "run_artifact", fake_run_artifact)
    response = client.post(
        f"/api/campaigns/{campaign}/memos",
        json={"creation_mode": "ai", "advice_id": advice_id, "name": "Assisted memo"},
    )
    assert response.status_code == 201
    provenance = response.json()["provenance"]
    assert provenance == {
        "workflow": "ai_assisted",
        "model_run_id": run.id,
        "prompt_version": "v1",
        "model_name": "audit-model",
        "provider": "test-provider",
        "validation_status": "ok",
        "fallback_used": False,
    }
    assert client.get(f"/api/campaigns/{campaign}/model-runs").json()[0]["id"] == run.id


def test_ai_disabled_creation_uses_validated_deterministic_fallback(client, campaign):
    advice_id = _advice(client, campaign)
    response = client.post(
        f"/api/campaigns/{campaign}/memos",
        json={"creation_mode": "ai", "advice_id": advice_id, "name": "Fallback memo"},
    )
    assert response.status_code == 201
    memo = response.json()
    assert memo["provenance"]["workflow"] == "deterministic_fallback"
    assert memo["provenance"]["fallback_used"] is True
    assert "OPERATIONAL STEPS" in memo["content"]
    assert "_" not in memo["content"].split("LIKELY OPPOSITION", 1)[-1]


@pytest.mark.parametrize(
    "payload",
    [
        {"creation_mode": "manual", "advice_id": "controlled_disclosure", "name": "x"},
        {"creation_mode": "ai", "advice_id": "controlled_disclosure", "name": "x", "content": "no"},
        {"creation_mode": "manual", "advice_id": "controlled_disclosure", "name": "x", "content": " "},
        {"creation_mode": "manual", "advice_id": "controlled_disclosure", "name": "x", "content": "ok", "effects": {}},
        {"creation_mode": "manual", "advice_id": "BAD ID", "name": "x", "content": "ok"},
        {"creation_mode": "manual", "advice_id": "controlled_disclosure", "name": "x" * 121, "content": "ok"},
    ],
)
def test_memo_requests_are_strict_and_bounded(client, campaign, payload):
    assert client.post(f"/api/campaigns/{campaign}/memos", json=payload).status_code == 422


def test_send_seals_exact_content_links_decision_canon_and_dossier(client, campaign):
    advice_id = _advice(client, campaign)
    exact = "Line one\nLine two — preserve punctuation."
    memo = _manual(client, campaign, advice_id, exact)
    response = _send(client, campaign, advice_id, memo)
    assert response.status_code == 200
    result = response.json()
    sent = result["sent_memo"]
    assert sent["content"] == exact
    assert sent["content_digest"] == hashlib.sha256(exact.encode()).hexdigest()
    assert result["decision"]["memo_id"] == memo["id"]
    assert result["canon_entry"]["memo_id"] == memo["id"]

    archived = client.get(f"/api/campaigns/{campaign}/memos").json()[0]
    assert archived["status"] == "sent"
    assert archived["sent_snapshot"] == sent
    dossier = client.get(f"/api/campaigns/{campaign}/dossier").json()["markdown"]
    assert exact in dossier
    assert memo["id"] in dossier
    assert result["decision"]["decision_type"] in dossier


def test_idempotent_retry_replays_same_sent_artifact(client, campaign):
    advice_id = _advice(client, campaign)
    memo = _manual(client, campaign, advice_id)
    key = uuid.uuid4().hex
    first = _send(client, campaign, advice_id, memo, key)
    replay = _send(client, campaign, advice_id, memo, key)
    assert replay.status_code == 200
    assert replay.headers["Idempotent-Replay"] == "true"
    assert replay.json() == first.json()
    assert len(client.get(f"/api/campaigns/{campaign}/turns").json()["turns"]) == 1


def test_stale_revision_conflicts_and_sent_memo_is_immutable(client, campaign):
    advice_id = _advice(client, campaign)
    memo = _manual(client, campaign, advice_id)
    updated = client.patch(
        f"/api/campaigns/{campaign}/memos/{memo['id']}",
        json={"expected_revision": 1, "name": memo["name"], "content": "revision two"},
    ).json()
    stale = _send(client, campaign, advice_id, memo)
    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "stale_memo_revision"
    assert _send(client, campaign, advice_id, updated).status_code == 200
    immutable = client.patch(
        f"/api/campaigns/{campaign}/memos/{memo['id']}",
        json={"expected_revision": 2, "name": "rewrite", "content": "rewrite history"},
    )
    assert immutable.status_code == 409
    assert immutable.json()["detail"]["error"] == "memo_immutable"


def test_memo_ownership_is_enforced(client, campaign):
    advice_id = _advice(client, campaign)
    memo = _manual(client, campaign, advice_id)
    other = client.post("/api/campaigns", json={"name": "Other"}).json()["id"]
    other_advice = _advice(client, other)
    response = _send(client, other, other_advice, memo)
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "memo_not_found"
