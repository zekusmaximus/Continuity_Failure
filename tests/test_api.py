"""HTTP/route-level tests for the FastAPI backend.

Covers every endpoint through ``TestClient``: the deterministic campaign loop
(create → current → advice → turns → dossier), the AI-assist seam (/memo and
/model-runs), and the error paths (404 for unknown campaigns, 400 for unknown
advice, 409 for advancing a terminal campaign). These run against the live
FastAPI app but AI is off by default, so the memo drafter returns a
deterministic fallback and makes no network call.

Lives in its own file so the engine-independence AST scan in
``test_engine_turns.py`` is unaffected by importing the web stack here.
"""

from __future__ import annotations

import os
import sqlite3
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


SURVIVAL_SEQUENCE = [
    "controlled_disclosure",
    "contractor_pressure",
    "mutual_aid",
    "controlled_disclosure",
    "state_support",
    "controlled_disclosure",
    "mutual_aid",
    "contractor_pressure",
    "controlled_disclosure",
    "mutual_aid",
]
_MEMOS_BY_KEY = {}


def _submit(client, campaign_id, advice_id, *, expected_turn=None, key=None,
            cited_document_ids=None):
    """Submit advice against the live revision with a fresh idempotency key.

    Mirrors an honest client: one new key per deliberate submission, and the
    turn number the client currently believes is authoritative.
    """
    if expected_turn is None:
        current = client.get(f"/api/campaigns/{campaign_id}/current")
        expected_turn = (
            current.json()["summary"]["turn_number"]
            if current.status_code == 200
            else 1
        )
    submission_key = key or uuid.uuid4().hex
    memo = _MEMOS_BY_KEY.get((campaign_id, submission_key))
    if memo is None:
        created = client.post(
            f"/api/campaigns/{campaign_id}/memos",
            json={
                "creation_mode": "manual",
                "advice_id": advice_id,
                "name": "API advice of record",
                "content": "Exact advisory content for the API test.",
            },
        )
        if created.status_code == 201:
            memo = created.json()
            _MEMOS_BY_KEY[(campaign_id, submission_key)] = memo
        else:
            memo = {"id": "memo_" + "0" * 32, "revision": 1}
    return client.post(
        f"/api/campaigns/{campaign_id}/advice",
        json={
            "advice_id": advice_id,
            "expected_turn": expected_turn,
            "idempotency_key": submission_key,
            "memo_id": memo["id"],
            "memo_revision": memo["revision"],
            **(
                {"cited_document_ids": cited_document_ids}
                if cited_document_ids is not None
                else {}
            ),
        },
    )


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    """Every API test gets a fresh SQLite file, never the developer database."""
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "api.sqlite3"))
    campaign_service.configure_repository()
    _MEMOS_BY_KEY.clear()
    yield
    campaign_service.configure_repository()


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def campaign(client):
    """Create a fresh campaign and return its id."""
    res = client.post("/api/campaigns", json={})
    assert res.status_code == 201
    return res.json()["id"]


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["scenario"] == "northbridge_water_failure"


# ---------------------------------------------------------------------------
# Campaign lifecycle
# ---------------------------------------------------------------------------

def test_create_campaign_defaults(client):
    res = client.post("/api/campaigns", json={})
    assert res.status_code == 201
    body = res.json()
    assert body["status"] == "ACTIVE"
    assert body["turn_number"] == 1
    assert body["max_turns"] == 10
    assert body["id"]


def test_create_campaign_with_name(client):
    res = client.post("/api/campaigns", json={"name": "Custom Engagement"})
    assert res.status_code == 201
    assert res.json()["name"] == "Custom Engagement"


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "x" * 81},
        {"name": "   "},
        {"name": "Valid", "unexpected": True},
    ],
)
def test_create_campaign_rejects_invalid_payloads(client, payload):
    res = client.post("/api/campaigns", json=payload)
    assert res.status_code == 422


def test_get_campaign(client, campaign):
    res = client.get(f"/api/campaigns/{campaign}")
    assert res.status_code == 200
    body = res.json()
    assert body["summary"]["id"] == campaign
    assert body["world_state"]["variables"]["water_security"] >= 0
    assert body["world_state"]["factions"]  # 10 factions


def test_get_campaign_unknown_returns_404(client):
    res = client.get("/api/campaigns/does-not-exist")
    assert res.status_code == 404
    assert res.json()["detail"]["error"] == "campaign_not_found"
    assert "not found" in res.json()["detail"]["message"].lower()


def test_recent_campaigns_expose_resume_metadata_only(client):
    first = client.post("/api/campaigns", json={"name": "Earlier"}).json()
    second = client.post("/api/campaigns", json={"name": "Most Recent"}).json()
    res = client.get("/api/campaigns?limit=2")
    assert res.status_code == 200
    body = res.json()
    assert [row["id"] for row in body] == [second["id"], first["id"]]
    assert set(body[0]) == {
        "id",
        "name",
        "scenario_id",
        "status",
        "turn_number",
        "max_turns",
        "failure_reason",
        "created_at",
        "updated_at",
    }


def test_campaign_resumes_after_service_repository_reconstruction(client, campaign):
    _submit(client, campaign, "controlled_disclosure")
    before = client.get(f"/api/campaigns/{campaign}/turns").json()
    campaign_service.configure_repository()
    after = client.get(f"/api/campaigns/{campaign}/turns")
    assert after.status_code == 200
    assert after.json() == before


def test_corrupt_saved_campaign_returns_clear_error(client, campaign):
    repository = campaign_service.get_repository()
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            "UPDATE campaigns SET payload_json = ? WHERE id = ?",
            ("{broken", campaign),
        )
    res = client.get(f"/api/campaigns/{campaign}/current")
    assert res.status_code == 500
    detail = res.json()["detail"]
    assert detail["error"] == "corrupt_record"
    assert detail["request_id"]
    # The player-facing message must not leak table names or record paths.
    assert "payload_json" not in detail["message"]
    assert "campaigns" not in detail["message"]


def test_get_current_has_turn_package(client, campaign):
    res = client.get(f"/api/campaigns/{campaign}/current")
    assert res.status_code == 200
    body = res.json()
    assert body["client_call"]["turn"] == 1
    assert body["advice_options"]  # 6 options
    assert body["documents"]
    assert body["system_status"]
    assert body["system_status"]["ai_available"] is False
    assert "off by default" in body["system_status"]["model_status"].lower()


def test_current_unknown_campaign_returns_404(client):
    res = client.get("/api/campaigns/nope/current")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# Advice submission + error paths
# ---------------------------------------------------------------------------

def test_submit_advice_advances_turn(client, campaign):
    res = _submit(client, campaign, "controlled_disclosure")
    assert res.status_code == 200
    body = res.json()
    assert body["turn_number"] == 1
    assert body["decision"]["decision_type"]
    assert body["diffs"]
    assert body["status_after"] == "ACTIVE"
    assert body["consequence_stack"]["immediate"]
    # The campaign advanced.
    assert client.get(f"/api/campaigns/{campaign}/current").json()["summary"]["turn_number"] == 2


def test_submit_unknown_advice_returns_400(client, campaign):
    res = _submit(client, campaign, "no_such_option")
    assert res.status_code == 400
    assert res.json()["detail"]["error"] == "unknown_advice_option"
    # A rejected option must not consume the turn.
    assert client.get(f"/api/campaigns/{campaign}/current").json()["summary"][
        "turn_number"
    ] == 1


_VALID_KEY = "a" * 32


@pytest.mark.parametrize(
    "payload",
    [
        {"advice_id": "", "expected_turn": 1, "idempotency_key": _VALID_KEY},
        {"advice_id": "x" * 65, "expected_turn": 1, "idempotency_key": _VALID_KEY},
        {"advice_id": "NOT VALID", "expected_turn": 1, "idempotency_key": _VALID_KEY},
        {"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": _VALID_KEY, "unexpected": True},
        # Missing revision / key.
        {"advice_id": "mutual_aid"},
        {"advice_id": "mutual_aid", "expected_turn": 1},
        {"advice_id": "mutual_aid", "idempotency_key": _VALID_KEY},
        # Out-of-bounds revision.
        {"advice_id": "mutual_aid", "expected_turn": 0, "idempotency_key": _VALID_KEY},
        {"advice_id": "mutual_aid", "expected_turn": 100000, "idempotency_key": _VALID_KEY},
        {"advice_id": "mutual_aid", "expected_turn": "one", "idempotency_key": _VALID_KEY},
        # Out-of-bounds / malformed idempotency keys.
        {"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": "short"},
        {"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": "k" * 65},
        {"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": "has spaces!"},
        {"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": ""},
    ],
)
def test_submit_advice_rejects_invalid_payloads(client, campaign, payload):
    res = client.post(f"/api/campaigns/{campaign}/advice", json=payload)
    assert res.status_code == 422


def test_submit_advice_unknown_campaign_returns_404(client):
    res = _submit(client, "nope", "controlled_disclosure", expected_turn=1)
    assert res.status_code == 404


def test_advancing_terminal_campaign_returns_409(client, campaign):
    # Play to completion.
    for advice_id in SURVIVAL_SEQUENCE:
        res = _submit(client, campaign, advice_id)
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            break
    # Further advice on a terminal campaign must 409.
    res = _submit(client, campaign, "controlled_disclosure")
    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "campaign_terminal"


# ---------------------------------------------------------------------------
# Full campaign + turns + dossier
# ---------------------------------------------------------------------------

def test_full_campaign_completes_and_turns_recorded(client, campaign):
    last_status = "ACTIVE"
    for advice_id in SURVIVAL_SEQUENCE:
        res = _submit(client, campaign, advice_id)
        assert res.status_code == 200
        last_status = res.json()["status_after"]
        if last_status in ("COMPLETED", "FAILED"):
            break
    assert last_status == "COMPLETED"

    turns = client.get(f"/api/campaigns/{campaign}/turns").json()
    assert len(turns["turns"]) == 10
    assert turns["canon"]
    assert turns["summary"]["status"] == "COMPLETED"


def test_dossier_endpoint_returns_markdown(client, campaign):
    # Resolve one turn so the dossier has a timeline.
    _submit(client, campaign, "controlled_disclosure")
    res = client.get(f"/api/campaigns/{campaign}/dossier")
    assert res.status_code == 200
    body = res.json()
    assert body["campaign_id"] == campaign
    assert body["markdown"].startswith("# Campaign Dossier")
    assert "Turn-by-Turn Timeline" in body["markdown"]
    assert body["filename"].endswith(".md")


def test_dossier_unknown_campaign_returns_404(client):
    res = client.get("/api/campaigns/nope/dossier")
    assert res.status_code == 404


def test_turns_unknown_campaign_returns_404(client):
    res = client.get("/api/campaigns/nope/turns")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# AI-assist seam: /memo and /model-runs
# ---------------------------------------------------------------------------

def test_draft_memo_returns_system_fallback(client, campaign):
    res = client.post(
        f"/api/campaigns/{campaign}/memo", json={"advice_id": "controlled_disclosure"}
    )
    assert res.status_code == 200
    body = res.json()
    # AI off by default -> deterministic fallback, honestly labeled.
    assert body["status"] == "fallback"
    assert body["source"] == "system"
    assert body["draft"]["recommendation"]
    assert body["draft"]["fallback_plan"]


def test_draft_memo_does_not_advance_turn(client, campaign):
    before = client.get(f"/api/campaigns/{campaign}/current").json()
    client.post(f"/api/campaigns/{campaign}/memo", json={"advice_id": "full_disclosure"})
    after = client.get(f"/api/campaigns/{campaign}/current").json()
    assert before["summary"]["turn_number"] == after["summary"]["turn_number"]
    assert before["world_state"]["variables"] == after["world_state"]["variables"]


def test_draft_memo_logs_a_model_run(client, campaign):
    client.post(f"/api/campaigns/{campaign}/memo", json={"advice_id": "mutual_aid"})
    runs = client.get(f"/api/campaigns/{campaign}/model-runs").json()
    assert len(runs) == 1
    assert runs[0]["prompt_name"] == "memo_drafter"
    assert runs[0]["validation_status"] == "fallback"
    assert runs[0]["model_name"] == "disabled"


def test_model_run_survives_service_repository_reconstruction(client, campaign):
    client.post(
        f"/api/campaigns/{campaign}/memo", json={"advice_id": "mutual_aid"}
    )
    campaign_service.configure_repository()
    runs = client.get(f"/api/campaigns/{campaign}/model-runs")
    assert runs.status_code == 200
    assert len(runs.json()) == 1
    assert runs.json()[0]["validation_status"] == "fallback"


def test_draft_memo_unknown_advice_returns_400(client, campaign):
    res = client.post(f"/api/campaigns/{campaign}/memo", json={"advice_id": "nope"})
    assert res.status_code == 400


def test_draft_memo_unknown_campaign_returns_404(client):
    res = client.post("/api/campaigns/nope/memo", json={"advice_id": "controlled_disclosure"})
    assert res.status_code == 404


def test_model_runs_unknown_campaign_returns_404(client):
    res = client.get("/api/campaigns/nope/model-runs")
    assert res.status_code == 404


def test_model_runs_empty_for_new_campaign(client, campaign):
    res = client.get(f"/api/campaigns/{campaign}/model-runs")
    assert res.status_code == 200
    assert res.json() == []


def test_draft_memo_works_on_terminal_campaign(client, campaign):
    """Drafting a memo must not require an active turn (advisory, no state change)."""
    for advice_id in SURVIVAL_SEQUENCE:
        res = _submit(client, campaign, advice_id)
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            break
    res = client.post(
        f"/api/campaigns/{campaign}/memo", json={"advice_id": "controlled_disclosure"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "fallback"


# ---------------------------------------------------------------------------
# Evidence citation over the API
# ---------------------------------------------------------------------------

def test_citing_available_documents_resolves_and_records_them(client, campaign):
    res = _submit(
        client, campaign, "controlled_disclosure",
        cited_document_ids=["doc_town_manager_transcript"],
    )
    assert res.status_code == 200
    assert res.json()["decision"]["cited_document_ids"] == [
        "doc_town_manager_transcript"
    ]


def test_citing_an_unknown_document_is_a_typed_400(client, campaign):
    res = _submit(
        client, campaign, "controlled_disclosure",
        cited_document_ids=["doc_that_does_not_exist"],
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error"] == "unknown_document"


def test_citing_a_future_turn_document_is_a_typed_400(client, campaign):
    res = _submit(
        client, campaign, "controlled_disclosure",
        cited_document_ids=["doc_school_closure_request"],  # turn 2 document
    )
    assert res.status_code == 400
    assert res.json()["detail"]["error"] == "unknown_document"


def test_more_than_three_citations_is_rejected_by_validation(client, campaign):
    res = _submit(
        client, campaign, "controlled_disclosure",
        cited_document_ids=[
            "doc_preliminary_lab_report", "doc_town_manager_transcript",
            "doc_council_session_excerpt", "doc_school_closure_request",
        ],
    )
    assert res.status_code == 422


def test_same_key_with_different_citations_is_an_idempotency_conflict(client, campaign):
    key = uuid.uuid4().hex
    first = _submit(
        client, campaign, "controlled_disclosure", key=key,
        cited_document_ids=["doc_town_manager_transcript"],
    )
    assert first.status_code == 200

    retry = _submit(
        client, campaign, "controlled_disclosure", key=key, expected_turn=1,
        cited_document_ids=["doc_preliminary_lab_report"],
    )
    assert retry.status_code == 409
    assert retry.json()["detail"]["error"] == "idempotency_key_conflict"
