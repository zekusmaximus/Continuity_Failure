"""Turn resolution must be atomic, retry-safe, and diagnosable.

Guarantees under test:

* one submission resolves at most one turn;
* an exact retry replays the original response and advances nothing;
* a reused key with a changed payload is a conflict, never a silent replay;
* a stale or competing submission never overwrites newer state;
* a failure anywhere before the commit leaves no authoritative change —
  campaign state, turn number, and immutable snapshots are all untouched;
* every request carries a request id and emits one structured log line whose
  fields are an allow-list that cannot contain memo prose or model output.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
import threading
import uuid

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.observability import IdempotencyOutcome, bind_log_fields  # noqa: E402
from app.services import campaign_service, errors  # noqa: E402
from memory import persistence  # noqa: E402

REQUEST_LOGGER = "continuity_failure.request"
ADVICE_ROUTE = "/api/campaigns/{campaign_id}/advice"

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


@pytest.fixture(autouse=True)
def _isolated_database(tmp_path, monkeypatch):
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "atomic.sqlite3"))
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
    return client.post("/api/campaigns", json={"name": "Atomicity Audit"}).json()["id"]


def _key(label: str = "") -> str:
    return f"{label}{uuid.uuid4().hex}"[:64] if label else uuid.uuid4().hex


def _post(client, campaign_id, advice_id, expected_turn, key, headers=None):
    memo = _MEMOS_BY_KEY.get((campaign_id, key))
    if memo is None:
        created = client.post(
            f"/api/campaigns/{campaign_id}/memos",
            json={
                "creation_mode": "manual",
                "advice_id": advice_id,
                "name": "Atomic advice of record",
                "content": "Exact advisory content for the atomicity test.",
            },
        )
        if created.status_code == 201:
            memo = created.json()
            _MEMOS_BY_KEY[(campaign_id, key)] = memo
        else:
            memo = {"id": "memo_" + "0" * 32, "revision": 1}
    return client.post(
        f"/api/campaigns/{campaign_id}/advice",
        json={
            "advice_id": advice_id,
            "expected_turn": expected_turn,
            "idempotency_key": key,
            "memo_id": memo["id"],
            "memo_revision": memo["revision"],
        },
        headers=headers or {},
    )


def _turn_number(client, campaign_id) -> int:
    return client.get(f"/api/campaigns/{campaign_id}/current").json()["summary"][
        "turn_number"
    ]


def _idempotency_rows(campaign_id) -> list:
    path = campaign_service.get_repository().path
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT idempotency_key, resulting_turn FROM turn_idempotency "
            "WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchall()


def _play_to_terminal(client, campaign_id) -> str:
    for advice_id in SURVIVAL_SEQUENCE:
        res = _post(client, campaign_id, advice_id, _turn_number(client, campaign_id), _key())
        assert res.status_code == 200
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            return res.json()["status_after"]
    raise AssertionError("campaign did not reach a terminal status")


# ---------------------------------------------------------------------------
# Successful resolution
# ---------------------------------------------------------------------------

def test_successful_resolution_advances_once_and_records_the_key(client, campaign):
    key = _key()
    res = _post(client, campaign, "controlled_disclosure", 1, key)

    assert res.status_code == 200
    assert res.headers["idempotent-replay"] == "false"
    assert res.json()["turn_number"] == 1
    assert _turn_number(client, campaign) == 2
    assert _idempotency_rows(campaign) == [(key, 1)]


# ---------------------------------------------------------------------------
# Exact retry
# ---------------------------------------------------------------------------

def test_exact_retry_returns_the_original_response_without_advancing(client, campaign):
    key = _key()
    first = _post(client, campaign, "controlled_disclosure", 1, key)
    assert first.status_code == 200

    retry = _post(client, campaign, "controlled_disclosure", 1, key)

    assert retry.status_code == 200
    assert retry.headers["idempotent-replay"] == "true"
    # Byte-for-byte the original resolved turn, not a re-resolution.
    assert retry.json() == first.json()
    assert _turn_number(client, campaign) == 2
    assert len(client.get(f"/api/campaigns/{campaign}/turns").json()["turns"]) == 1
    assert _idempotency_rows(campaign) == [(key, 1)]


def test_many_retries_of_one_key_never_create_a_second_turn(client, campaign):
    key = _key()
    responses = [_post(client, campaign, "mutual_aid", 1, key) for _ in range(5)]

    assert all(res.status_code == 200 for res in responses)
    assert all(res.json() == responses[0].json() for res in responses)
    assert _turn_number(client, campaign) == 2
    assert len(_idempotency_rows(campaign)) == 1


# ---------------------------------------------------------------------------
# Key reuse with a changed payload
# ---------------------------------------------------------------------------

def test_key_reuse_with_changed_advice_is_a_conflict(client, campaign):
    key = _key()
    assert _post(client, campaign, "controlled_disclosure", 1, key).status_code == 200

    res = _post(client, campaign, "mutual_aid", 1, key)

    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "idempotency_key_conflict"
    assert _turn_number(client, campaign) == 2
    # The original record stands; nothing was overwritten.
    assert _idempotency_rows(campaign) == [(key, 1)]
    turns = client.get(f"/api/campaigns/{campaign}/turns").json()["turns"]
    assert [t["advice_id"] for t in turns] == ["controlled_disclosure"]


def test_key_reuse_with_changed_expected_turn_is_a_conflict(client, campaign):
    key = _key()
    assert _post(client, campaign, "controlled_disclosure", 1, key).status_code == 200

    res = _post(client, campaign, "controlled_disclosure", 2, key)

    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "idempotency_key_conflict"
    assert _turn_number(client, campaign) == 2


# ---------------------------------------------------------------------------
# Stale revision
# ---------------------------------------------------------------------------

def test_stale_expected_turn_is_a_conflict_and_changes_nothing(client, campaign):
    assert _post(client, campaign, "controlled_disclosure", 1, _key()).status_code == 200
    before = client.get(f"/api/campaigns/{campaign}/current").json()

    res = _post(client, campaign, "mutual_aid", 1, _key())

    assert res.status_code == 409
    detail = res.json()["detail"]
    assert detail["error"] == "stale_turn"
    assert detail["expected_turn"] == 1
    assert detail["current_turn"] == 2
    assert detail["campaign_id"] == campaign
    assert client.get(f"/api/campaigns/{campaign}/current").json() == before
    assert len(_idempotency_rows(campaign)) == 1


def test_expected_turn_ahead_of_the_campaign_is_also_a_conflict(client, campaign):
    res = _post(client, campaign, "mutual_aid", 7, _key())
    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "stale_turn"
    assert _turn_number(client, campaign) == 1


# ---------------------------------------------------------------------------
# Terminal campaigns
# ---------------------------------------------------------------------------

def test_terminal_campaign_rejects_a_new_submission(client, campaign):
    status_after = _play_to_terminal(client, campaign)
    turns_before = client.get(f"/api/campaigns/{campaign}/turns").json()

    res = _post(client, campaign, "controlled_disclosure", _turn_number(client, campaign), _key())

    assert res.status_code == 409
    assert res.json()["detail"]["error"] == "campaign_terminal"
    assert status_after.lower() in res.json()["detail"]["message"].lower()
    assert client.get(f"/api/campaigns/{campaign}/turns").json() == turns_before


def test_retrying_the_turn_that_ended_the_campaign_still_replays(client, campaign):
    """The final turn's key must replay, not trip the terminal guard."""
    key = None
    for advice_id in SURVIVAL_SEQUENCE:
        key = _key()
        res = _post(client, campaign, advice_id, _turn_number(client, campaign), key)
        if res.json()["status_after"] in ("COMPLETED", "FAILED"):
            break
    final = res.json()

    replay = _post(client, campaign, advice_id, final["turn_number"], key)

    assert replay.status_code == 200
    assert replay.headers["idempotent-replay"] == "true"
    assert replay.json() == final


# ---------------------------------------------------------------------------
# Competing submissions
# ---------------------------------------------------------------------------

def test_two_simultaneous_submissions_advance_exactly_one_turn(tmp_path, monkeypatch):
    """Distinct keys, same revision, real threads: one resolves, one is stale."""
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "race.sqlite3"))
    campaign_service.configure_repository()
    campaign_id = campaign_service.create_campaign("Race").id
    campaign_service.get_repository()  # materialize the shared singleton up front

    start = threading.Barrier(2)
    outcomes: list = []
    lock = threading.Lock()

    def worker(index: int) -> None:
        start.wait()
        try:
            resolved = campaign_service.submit_advice(
                campaign_id,
                "controlled_disclosure",
                expected_turn=1,
                idempotency_key=f"racekey{index:04d}" + uuid.uuid4().hex,
            )
            record = ("resolved", resolved.result.turn_number, resolved.replayed)
        except errors.TurnResolutionError as exc:
            record = ("rejected", exc.code, None)
        with lock:
            outcomes.append(record)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
    assert not any(thread.is_alive() for thread in threads)

    resolved = [o for o in outcomes if o[0] == "resolved"]
    rejected = [o for o in outcomes if o[0] == "rejected"]
    assert len(resolved) == 1, outcomes
    assert resolved[0] == ("resolved", 1, False)
    assert len(rejected) == 1, outcomes
    assert rejected[0][1] == "stale_turn"

    campaign = campaign_service.get_repository().get(campaign_id)
    assert campaign.turn_number == 2
    assert len(campaign.turn_history) == 1
    with sqlite3.connect(campaign_service.get_repository().path) as connection:
        rows = connection.execute(
            "SELECT COUNT(*) FROM turn_snapshots WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()[0]
    assert rows == 1


def test_two_simultaneous_retries_of_one_key_resolve_one_turn(tmp_path, monkeypatch):
    """The same key raced against itself: one resolves, the other replays it."""
    monkeypatch.setenv("CF_DATABASE_PATH", str(tmp_path / "race_key.sqlite3"))
    campaign_service.configure_repository()
    campaign_id = campaign_service.create_campaign("Retry Race").id
    campaign_service.get_repository()

    key = "sharedkey" + uuid.uuid4().hex
    start = threading.Barrier(2)
    outcomes: list = []
    lock = threading.Lock()

    def worker() -> None:
        start.wait()
        resolved = campaign_service.submit_advice(
            campaign_id,
            "controlled_disclosure",
            expected_turn=1,
            idempotency_key=key,
        )
        with lock:
            outcomes.append(resolved.replayed)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert sorted(outcomes) == [False, True]
    assert campaign_service.get_repository().get(campaign_id).turn_number == 2


# ---------------------------------------------------------------------------
# Rollback: failure after deterministic resolution, before commit
# ---------------------------------------------------------------------------

def _snapshot_state(campaign_id) -> dict:
    repository = campaign_service.get_repository()
    campaign = repository.get(campaign_id)
    with sqlite3.connect(repository.path) as connection:
        snapshots = connection.execute(
            "SELECT turn_number FROM turn_snapshots WHERE campaign_id = ? "
            "ORDER BY turn_number",
            (campaign_id,),
        ).fetchall()
        keys = connection.execute(
            "SELECT COUNT(*) FROM turn_idempotency WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()[0]
    return {
        "turn_number": campaign.turn_number,
        "status": campaign.status,
        "variables": dict(campaign.world_state.variables),
        "turn_history": len(campaign.turn_history),
        "canon": len(campaign.canon),
        "snapshots": snapshots,
        "idempotency_rows": keys,
    }


def test_failure_after_resolution_before_commit_leaves_no_authoritative_change(
    client, campaign
):
    """Inject a failure between the writes and the commit; prove nothing landed."""
    assert _post(client, campaign, "controlled_disclosure", 1, _key()).status_code == 200
    before = _snapshot_state(campaign)
    assert before["turn_number"] == 2

    class Injected(RuntimeError):
        pass

    def explode(self, **kwargs):
        raise Injected("simulated crash after resolution, before commit")

    # A scoped patch: the shared ``monkeypatch`` fixture would also undo the
    # autouse database isolation, silently pointing these assertions at the
    # developer database.
    with pytest.MonkeyPatch.context() as patch:
        # The last write in the unit of work. By the time it runs, the campaign
        # row and the turn snapshot are already written inside the transaction.
        patch.setattr(
            persistence.RepositoryTransaction, "save_idempotency_record", explode
        )
        with pytest.raises(Injected):
            campaign_service.submit_advice(
                campaign,
                "mutual_aid",
                expected_turn=2,
                idempotency_key=_key(),
            )

    after = _snapshot_state(campaign)
    assert after == before
    assert after["turn_number"] == 2
    assert after["snapshots"] == [(1,)]
    assert after["idempotency_rows"] == 1

    # The campaign is still usable: the same turn resolves cleanly afterwards.
    recovered = _post(client, campaign, "mutual_aid", 2, _key())
    assert recovered.status_code == 200
    assert recovered.json()["turn_number"] == 2


def test_failure_immediately_after_deterministic_resolution_persists_nothing(
    client, campaign
):
    """The engine mutates its campaign in memory; that must never reach SQLite."""
    before = _snapshot_state(campaign)
    real_advance = campaign_service.turn_engine.advance_turn

    class Injected(RuntimeError):
        pass

    def resolve_then_fail(campaign_obj, advice_id):
        real_advance(campaign_obj, advice_id)  # fully mutates the in-memory campaign
        raise Injected("simulated crash after deterministic resolution")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(campaign_service.turn_engine, "advance_turn", resolve_then_fail)
        with pytest.raises(Injected):
            campaign_service.submit_advice(
                campaign,
                "controlled_disclosure",
                expected_turn=1,
                idempotency_key=_key(),
            )

    assert _snapshot_state(campaign) == before
    assert before["turn_number"] == 1
    assert before["turn_history"] == 0
    assert before["snapshots"] == []
    assert before["idempotency_rows"] == 0


def test_write_lock_timeout_is_a_clean_retriable_503(client, campaign):
    """Contention must not surface as a 500, and must not half-apply a turn."""
    repository = campaign_service.get_repository()

    def impatient_connect():
        connection = sqlite3.connect(str(repository.path), timeout=0.05)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    blocker = sqlite3.connect(str(repository.path), timeout=0.05)
    blocker.execute("BEGIN IMMEDIATE")  # hold the write lock from "another process"
    try:
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(repository, "_connect", impatient_connect)
            res = _post(client, campaign, "controlled_disclosure", 1, _key())
    finally:
        blocker.rollback()
        blocker.close()

    assert res.status_code == 503
    assert res.json()["detail"]["error"] == "repository_busy"
    assert res.headers["retry-after"] == "1"
    assert res.headers["x-request-id"]
    # Nothing was applied, so the identical retry is safe and succeeds.
    assert _turn_number(client, campaign) == 1
    assert _idempotency_rows(campaign) == []


def test_rejected_submission_leaves_no_idempotency_record(client, campaign):
    """A failed request must not burn its key, or an honest retry could never win."""
    key = _key()
    assert _post(client, campaign, "no_such_option", 1, key).status_code == 400
    assert _idempotency_rows(campaign) == []

    res = _post(client, campaign, "controlled_disclosure", 1, key)
    assert res.status_code == 200
    assert res.json()["turn_number"] == 1


# ---------------------------------------------------------------------------
# Request id propagation
# ---------------------------------------------------------------------------

def test_every_response_carries_a_request_id(client, campaign):
    for res in (
        client.get("/health"),
        client.get(f"/api/campaigns/{campaign}/current"),
        _post(client, campaign, "controlled_disclosure", 1, _key()),
        client.get("/api/campaigns/nope/current"),
    ):
        assert res.headers.get("x-request-id")


def test_valid_inbound_request_id_is_adopted(client, campaign):
    inbound = "trace-Northbridge_2026.07.10-0001"
    res = _post(
        client, campaign, "controlled_disclosure", 1, _key(),
        headers={"X-Request-ID": inbound},
    )
    assert res.status_code == 200
    assert res.headers["x-request-id"] == inbound


@pytest.mark.parametrize("inbound", ["short", "has spaces", "bad;id;injection", "x" * 129, ""])
def test_invalid_inbound_request_id_is_replaced(client, campaign, inbound):
    res = client.get(
        f"/api/campaigns/{campaign}/current", headers={"X-Request-ID": inbound}
    )
    generated = res.headers["x-request-id"]
    assert generated != inbound
    assert len(generated) == 32 and generated.isalnum()


def test_request_ids_are_unique_per_request(client, campaign):
    seen = {
        client.get(f"/api/campaigns/{campaign}/current").headers["x-request-id"]
        for _ in range(5)
    }
    assert len(seen) == 5


def test_error_bodies_carry_the_request_id(client, campaign):
    res = _post(client, campaign, "mutual_aid", 9, _key())
    assert res.status_code == 409
    assert res.json()["detail"]["request_id"] == res.headers["x-request-id"]


# ---------------------------------------------------------------------------
# Structured logs
# ---------------------------------------------------------------------------

REQUIRED_LOG_FIELDS = {
    "event",
    "request_id",
    "method",
    "route",
    "status",
    "duration_ms",
    "campaign_id",
    "turn_number",
    "expected_turn",
    "idempotency",
}


def _records(caplog):
    return [r for r in caplog.records if r.name == REQUEST_LOGGER]


def _advice_record(caplog):
    matches = [r for r in _records(caplog) if r.structured["route"] == ADVICE_ROUTE]
    assert matches, "no structured log line for the advice route"
    return matches[-1].structured


def test_structured_log_has_every_required_field(client, campaign, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    res = _post(client, campaign, "controlled_disclosure", 1, _key())
    assert res.status_code == 200

    record = _advice_record(caplog)
    assert set(record) == REQUIRED_LOG_FIELDS
    assert record["event"] == "http_request"
    assert record["request_id"] == res.headers["x-request-id"]
    assert record["method"] == "POST"
    assert record["route"] == ADVICE_ROUTE
    assert record["status"] == 200
    assert isinstance(record["duration_ms"], float) and record["duration_ms"] >= 0
    assert record["campaign_id"] == campaign
    assert record["turn_number"] == 1
    assert record["expected_turn"] == 1
    assert record["idempotency"] == IdempotencyOutcome.RESOLVED
    # The line is emitted as parseable JSON, not free prose.
    assert json.loads(_records(caplog)[-1].getMessage())


@pytest.mark.parametrize(
    "scenario,expected",
    [
        ("replay", IdempotencyOutcome.REPLAYED),
        ("key_conflict", IdempotencyOutcome.KEY_CONFLICT),
        ("stale", IdempotencyOutcome.STALE_TURN),
        ("terminal", IdempotencyOutcome.TERMINAL),
        ("unknown_advice", IdempotencyOutcome.REJECTED),
    ],
)
def test_idempotency_outcome_is_logged(client, campaign, caplog, scenario, expected):
    key = _key()
    if scenario == "terminal":
        _play_to_terminal(client, campaign)
    elif scenario != "unknown_advice":
        assert _post(client, campaign, "controlled_disclosure", 1, key).status_code == 200

    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    if scenario == "replay":
        _post(client, campaign, "controlled_disclosure", 1, key)
    elif scenario == "key_conflict":
        _post(client, campaign, "mutual_aid", 1, key)
    elif scenario == "stale":
        _post(client, campaign, "mutual_aid", 1, _key())
    elif scenario == "terminal":
        _post(client, campaign, "mutual_aid", _turn_number(client, campaign), _key())
    else:
        _post(client, campaign, "no_such_option", 1, key)

    assert _advice_record(caplog)["idempotency"] == expected


def test_schema_rejected_request_still_logs_route_and_campaign(client, campaign, caplog):
    """A 422 never reaches a handler; it must stay attributable anyway."""
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    res = client.post(
        f"/api/campaigns/{campaign}/advice",
        json={"advice_id": "mutual_aid", "expected_turn": 1, "idempotency_key": "bad key!"},
    )
    assert res.status_code == 422

    record = _advice_record(caplog)
    assert record["status"] == 422
    assert record["campaign_id"] == campaign
    assert record["route"] == ADVICE_ROUTE
    assert record["request_id"] == res.headers["x-request-id"]
    # The rejected key must not appear anywhere in the log line.
    assert "bad key!" not in json.dumps(record)


def test_non_turn_routes_log_not_applicable(client, campaign, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)
    client.get(f"/api/campaigns/{campaign}/current")
    record = _records(caplog)[-1].structured
    assert record["idempotency"] == IdempotencyOutcome.NOT_APPLICABLE
    assert record["route"] == "/api/campaigns/{campaign_id}/current"


def test_logs_never_contain_memo_text_or_model_output(client, campaign, caplog):
    caplog.set_level(logging.INFO)
    memo = client.post(
        f"/api/campaigns/{campaign}/memo", json={"advice_id": "controlled_disclosure"}
    ).json()
    _post(client, campaign, "controlled_disclosure", 1, _key())

    prose = [
        memo["draft"]["recommendation"],
        memo["draft"]["rationale"],
        memo["draft"]["communications"],
        memo["draft"]["fallback_plan"],
    ]
    assert all(text for text in prose)

    # No logger anywhere may carry memo prose, not just the request logger.
    emitted = "\n".join(record.getMessage() for record in caplog.records)
    for text in prose:
        assert text not in emitted
    assert "advice_id" not in emitted and "idempotency_key" not in emitted
    for record in _records(caplog):
        assert set(record.structured) == REQUIRED_LOG_FIELDS


def test_bind_log_fields_ignores_unknown_keys(client, campaign, caplog):
    caplog.set_level(logging.INFO, logger=REQUEST_LOGGER)

    original = campaign_service.submit_advice

    def leaky(*args, **kwargs):
        bind_log_fields(memo_text="CONFIDENTIAL DRAFT", api_key="sk-secret")
        return original(*args, **kwargs)

    from app.api import campaigns as campaigns_api

    campaigns_api.campaign_service.submit_advice = leaky
    try:
        _post(client, campaign, "controlled_disclosure", 1, _key())
    finally:
        campaigns_api.campaign_service.submit_advice = original

    record = _advice_record(caplog)
    assert set(record) == REQUIRED_LOG_FIELDS
    assert "CONFIDENTIAL DRAFT" not in json.dumps(record)
    assert "sk-secret" not in json.dumps(record)
