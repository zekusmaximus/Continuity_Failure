"""Applied-diff construction.

Every world-state mutation is expressed as one or more ``AppliedDiff`` records
so the UI can always show *why* something changed (design rule #3).
"""

from __future__ import annotations

from typing import Dict, List

from engine.models import AppliedDiff
from engine.state import clamp


def apply_diffs(
    variables: Dict[str, int],
    deltas: Dict[str, int],
    reason: str,
    source_type: str,
) -> List[AppliedDiff]:
    """Apply ``deltas`` to ``variables`` in place and return the diff records.

    Only variables that already exist in ``variables`` are touched. The
    recorded ``delta`` reflects the *effective* change after clamping, so a
    value pinned at a bound reports a delta of the amount actually moved.
    """
    diffs: List[AppliedDiff] = []
    for variable, delta in deltas.items():
        if variable not in variables:
            continue
        if delta == 0:
            continue
        old_value = variables[variable]
        new_value = clamp(old_value + delta)
        effective = new_value - old_value
        variables[variable] = new_value
        diffs.append(
            AppliedDiff(
                variable=variable,
                old_value=old_value,
                new_value=new_value,
                delta=effective,
                reason=reason,
                source_type=source_type,
            )
        )
    return diffs
