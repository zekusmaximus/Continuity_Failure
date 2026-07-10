"""First AI tool end-to-end (Week 3, commit 3): the memo drafter.

Exercised through the service layer (not the FastAPI TestClient) so these tests
don't import `fastapi` and thus don't disturb `test_engine_does_not_import_fastapi`.
The HTTP endpoints are smoke-tested separately. AI is off by default, so every
assertion here runs against the deterministic fallback path.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

import pytest  # noqa: E402

from app.ai import fallbacks  # noqa: E402
from app.ai.logging import ValidationStatus  # noqa: E402
from app.ai.schemas import MemoDraft  # noqa: E402
from app.services import campaign_service  # noqa: E402
from engine.turn import UnknownAdviceOption  # noqa: E402


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "memo.sqlite3"))
    campaign_service.configure_repository()
    yield
    campaign_service.configure_repository()


def _new_campaign_with_advice():
    created = campaign_service.create_campaign()
    current = campaign_service.get_current(created.id)
    advice_id = current.advice_options[0].id
    return created.id, advice_id


# ---------------------------------------------------------------------------
# Fallback validity
# ---------------------------------------------------------------------------

def test_memo_fallback_is_a_valid_memo():
    payload = {
        "advice_title": "Full disclosure",
        "recommendation": "Disclose the preliminary result now.",
        "rationale": "Transparency limits later legal exposure.",
        "expected_benefits": ["Preserves public trust"],
        "expected_harms": ["Short-term panic risk"],
        "operational_steps": [
            "Brief the hospital before release.",
            "Publish the verification deadline.",
        ],
        "affected_factions": ["Town Council", "Northbridge Hospital"],
    }
    memo = fallbacks.memo_fallback(payload)
    assert isinstance(memo, MemoDraft)
    assert memo.recommendation
    assert memo.operational_steps == payload["operational_steps"]
    assert memo.second_order_risks == ["Short-term panic risk"]
    assert any("Town Council" in line for line in memo.likely_opposition)


# ---------------------------------------------------------------------------
# Service path with AI off (deterministic fallback)
# ---------------------------------------------------------------------------

def test_draft_memo_returns_fallback_and_logs_a_run():
    campaign_id, advice_id = _new_campaign_with_advice()

    result = campaign_service.draft_memo(campaign_id, advice_id)
    assert result is not None
    assert result.status == "fallback"
    assert result.source == "system"
    assert result.draft.recommendation
    assert result.draft.fallback_plan
    assert result.draft.operational_steps
    assert not any("_" in line for line in result.draft.likely_opposition)

    runs = campaign_service.get_model_runs(campaign_id)
    assert len(runs) == 1
    assert runs[0].prompt_name == "memo_drafter"
    assert runs[0].validation_status == ValidationStatus.FALLBACK
    assert runs[0].model_name == "disabled"


def test_draft_memo_does_not_change_world_state():
    campaign_id, advice_id = _new_campaign_with_advice()

    before = dict(campaign_service.get_current(campaign_id).world_state.variables)
    campaign_service.draft_memo(campaign_id, advice_id)
    after = dict(campaign_service.get_current(campaign_id).world_state.variables)

    assert before == after  # advisory only — the engine owns state


def test_draft_memo_unknown_advice_raises():
    campaign_id, _ = _new_campaign_with_advice()
    with pytest.raises(UnknownAdviceOption):
        campaign_service.draft_memo(campaign_id, "no_such_option")


def test_draft_memo_missing_campaign_returns_none():
    assert campaign_service.draft_memo("nonexistent", "whatever") is None
    assert campaign_service.get_model_runs("nonexistent") is None
