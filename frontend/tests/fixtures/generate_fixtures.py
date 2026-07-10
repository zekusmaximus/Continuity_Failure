"""Regenerate the frontend's API fixtures from the real backend.

The component tests run against a fake fetch, but the *payloads* that fake
serves are captured from a genuine Northbridge campaign resolved by the real
engine and the real Pydantic schemas. That way a backend response-shape change
breaks the frontend tests instead of silently passing against a stale hand-typed
object.

    npm run test:fixtures        (from frontend/)

The campaign id is normalised so the fixtures are byte-stable across runs.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

FIXTURES = pathlib.Path(__file__).resolve().parent
REPO_ROOT = FIXTURES.parents[2]

sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

# An isolated database: regenerating fixtures must never touch a real save.
os.environ["CF_DATABASE_PATH"] = str(
    pathlib.Path(tempfile.mkdtemp(prefix="cf-fixtures-")) / "fixtures.sqlite3"
)
os.environ["CF_AI_ENABLED"] = "false"

from app.services import campaign_service as cs  # noqa: E402

CAMPAIGN_ID = "test-campaign"
ADVICE_ID = "full_disclosure"


def write(name: str, payload) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
    text = text.replace(real_id, CAMPAIGN_ID)
    (FIXTURES / name).write_text(text + "\n", encoding="utf-8")
    print(f"  wrote {name}")


def dump(model) -> dict:
    return json.loads(model.model_dump_json())


created = cs.create_campaign(name="")
real_id = created.id

print(f"Generating fixtures from campaign {real_id}...")

write("turns-0.json", dump(cs.get_turns(real_id)))
write("dossier.json", dump(cs.get_dossier(real_id)))

for turn in (1, 2, 3):
    current = cs.get_current(real_id)
    write(f"current-turn-{turn}.json", dump(current))
    if turn == 3:
        break
    resolved = cs.submit_advice(
        real_id,
        ADVICE_ID,
        expected_turn=current.summary.turn_number,
        idempotency_key=f"fixture-{turn}",
    )
    write(f"advice-turn-{turn}.json", dump(resolved.result))
    write(f"turns-{turn}.json", dump(cs.get_turns(real_id)))

print("Done.")
