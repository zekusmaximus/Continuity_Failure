"""Developer command: validate scenario content.

Usage::

    python -m engine.content validate [scenario_id ...]

With no scenario id, validates every scenario directory shipped in
``engine/content/scenarios/``. Exits non-zero and prints file/field-anchored
errors if any scenario is invalid, so it can gate CI or a pre-commit hook.
"""

from __future__ import annotations

import os
import sys
from typing import List

from engine.content import loader
from engine.content.loader import IncompatibleSchemaVersion
from engine.content.validator import ContentValidationError


def _all_scenarios() -> List[str]:
    root = loader._CONTENT_ROOT
    if not os.path.isdir(root):
        return []
    return sorted(
        name for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name))
    )


def _validate_one(scenario_id: str) -> bool:
    try:
        loader.validate_scenario(scenario_id)
    except ContentValidationError as exc:
        print(f"FAIL  {scenario_id}: {len(exc.errors)} error(s)")
        for err in exc.errors:
            print(f"        {err}")
        return False
    except IncompatibleSchemaVersion as exc:
        print(f"FAIL  {scenario_id}: {exc}")
        return False
    print(f"OK    {scenario_id}")
    return True


def main(argv: List[str]) -> int:
    if not argv or argv[0] != "validate":
        print(__doc__)
        return 2
    scenarios = argv[1:] or _all_scenarios()
    if not scenarios:
        print("no scenarios found under engine/content/scenarios/")
        return 1
    ok = all(_validate_one(s) for s in scenarios)
    if ok:
        print(f"\nAll {len(scenarios)} scenario(s) valid.")
        return 0
    print("\nContent validation failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
