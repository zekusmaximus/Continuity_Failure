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
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import campaign_service  # noqa: E402
from app.ai.logging import get_run_store  # noqa: E402


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


@pytest.fixture(autouse=True)
def _clean_stores():
    """Isolate the module-level campaign + model-run stores between tests."""
    campaign_service.get_store().clear()
    get_run_store().clear()
    yield
    campaign_service.get_store().clear()
    get_run_store().clear()


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
    assert "not found" in res.json()["detail"].lower()


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
    res = client.post(
        f"/api/campaigns/{campaign}/advice", json={"advice_id": "controlled_disclosure"}
    )
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
    res = client.post(
        f"/api/campaigns/{campaign}/advice", json={"advice_id": "no_such_option"}
    )
    assert res.status_code == 400
    assert "unknown advice" in res.json()["detail"].lower()


@pytest.mark.parametrize(
    "payload",
    [
        {"advice_id": ""},
        {"advice_id": "x" * 65},
        {"advice_id": "NOT VALID"},
        {"advice_id": "mutual_aid", "unexpected": True},
    ],
)
def test_submit_advice_rejects_invalid_payloads(client, campaign, payload):
    res = client.post(f"/api/campaigns/{campaign}/advice", json=payload)
    assert res.status_code == 422


def test_submit_advice_unknown_campaign_returns_404(client):
    res = client.post("/api/campaigns/nope/advice", json={"advice_id": "controlled_disclosure"})
    assert res.status_code == 404


def test_advancing_terminal_campaign_returns_409(client, campaign):
    # Play to completion.
    for advice_id in SURVIVAL_SEQUENCE:
        res = client.post(f"/api/campaigns/{campaign}/advice", json={"advice_id": advice_id})
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            break
    # Further advice on a terminal campaign must 409.
    res = client.post(
        f"/api/campaigns/{campaign}/advice", json={"advice_id": "controlled_disclosure"}
    )
    assert res.status_code == 409


# ---------------------------------------------------------------------------
# Full campaign + turns + dossier
# ---------------------------------------------------------------------------

def test_full_campaign_completes_and_turns_recorded(client, campaign):
    last_status = "ACTIVE"
    for advice_id in SURVIVAL_SEQUENCE:
        res = client.post(f"/api/campaigns/{campaign}/advice", json={"advice_id": advice_id})
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
    client.post(f"/api/campaigns/{campaign}/advice", json={"advice_id": "controlled_disclosure"})
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
        res = client.post(f"/api/campaigns/{campaign}/advice", json={"advice_id": advice_id})
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            break
    res = client.post(
        f"/api/campaigns/{campaign}/memo", json={"advice_id": "controlled_disclosure"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "fallback"
