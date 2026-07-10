"""Durable SQLite repository and restart regression tests."""

from __future__ import annotations

import sqlite3
from dataclasses import asdict

import pytest

from engine import seed_data
from engine.models import Campaign, CampaignStatus, TurnResult
from engine.turn import advance_turn
from memory.persistence import (
    CorruptRecordError,
    ImmutableSnapshotError,
    SQLiteRepository,
)


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


def _resolve_and_save(repository: SQLiteRepository, campaign: Campaign, advice_id: str):
    result = advance_turn(campaign, advice_id)
    repository.put(campaign, snapshot_turn=result.turn_number)
    return result


def test_campaign_and_model_run_survive_new_repository_instance(tmp_path):
    database = tmp_path / "restart.sqlite3"
    first = SQLiteRepository(database)
    campaign = seed_data.create_northbridge_campaign("Restart Audit")
    first.put(campaign)
    _resolve_and_save(first, campaign, "controlled_disclosure")
    _resolve_and_save(first, campaign, "contractor_pressure")
    first.add_model_run(
        {
            "prompt_name": "memo_drafter",
            "prompt_version": "v1",
            "model_name": "disabled",
            "validation_status": "fallback",
            "input_summary": "turn 2",
            "raw_output": "",
            "parsed_output": {"recommendation": "retain as advisory only"},
            "retry_count": 0,
            "latency_ms": 0,
            "token_usage": None,
            "estimated_cost": None,
            "campaign_id": campaign.id,
            "turn_number": 2,
        }
    )

    restarted = SQLiteRepository(database)
    restored = restarted.get(campaign.id)

    assert isinstance(restored, Campaign)
    assert asdict(restored) == asdict(campaign)
    assert isinstance(restored.turn_history[0], TurnResult)
    assert restored.client_calls[1].turn == 1
    assert restored.canon == campaign.canon
    assert restored.open_threads == campaign.open_threads
    assert restarted.snapshot_json(campaign.id, 1)
    assert restarted.snapshot_json(campaign.id, 2)
    assert restarted.model_runs_for_campaign(campaign.id)[0]["parsed_output"] == {
        "recommendation": "retain as advisory only"
    }


def test_existing_turn_history_cannot_be_changed_by_resave(tmp_path):
    repository = SQLiteRepository(tmp_path / "immutable.sqlite3")
    campaign = seed_data.create_northbridge_campaign()
    repository.put(campaign)
    _resolve_and_save(repository, campaign, "controlled_disclosure")
    original_snapshot = repository.snapshot_json(campaign.id, 1)

    campaign.turn_history[0].aftermath_summary = "silently revised history"
    with pytest.raises(ImmutableSnapshotError):
        repository.put(campaign)

    restarted = SQLiteRepository(repository.path)
    assert restarted.snapshot_json(campaign.id, 1) == original_snapshot
    assert restarted.get(campaign.id).turn_history[0].aftermath_summary != (
        "silently revised history"
    )


def test_terminal_campaign_reopens_and_stays_terminal(tmp_path):
    database = tmp_path / "terminal.sqlite3"
    repository = SQLiteRepository(database)
    campaign = seed_data.create_northbridge_campaign()
    repository.put(campaign)
    for advice_id in SURVIVAL_SEQUENCE:
        result = _resolve_and_save(repository, campaign, advice_id)
        if result.status_after != CampaignStatus.ACTIVE:
            break

    restored = SQLiteRepository(database).get(campaign.id)
    assert restored.status == CampaignStatus.COMPLETED
    assert len(restored.turn_history) == 10
    with pytest.raises(RuntimeError, match="terminal"):
        advance_turn(restored, "controlled_disclosure")


def test_corrupt_campaign_payload_is_reported(tmp_path):
    repository = SQLiteRepository(tmp_path / "corrupt.sqlite3")
    campaign = seed_data.create_northbridge_campaign()
    repository.put(campaign)
    with sqlite3.connect(repository.path) as connection:
        connection.execute(
            "UPDATE campaigns SET payload_json = ? WHERE id = ?",
            ("{not-json", campaign.id),
        )

    with pytest.raises(CorruptRecordError, match="is corrupt"):
        SQLiteRepository(repository.path).get(campaign.id)


def test_schema_version_is_recorded(tmp_path):
    repository = SQLiteRepository(tmp_path / "versioned.sqlite3")
    with sqlite3.connect(repository.path) as connection:
        version = connection.execute(
            "SELECT MAX(version) FROM schema_migrations"
        ).fetchone()[0]
    assert version == 1
