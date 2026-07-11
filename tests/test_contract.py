"""Schema-contract tests: engine dataclass -> Pydantic model -> TS interface.

The API contract is duplicated by hand across three layers with no automatic
enforcement:

    engine/models.py            (plain dataclasses -- the source of truth)
      -> backend/app/schemas/api.py   (Pydantic v2 models; the service converts
         via ``dataclasses.asdict`` + ``model_validate``, so field names must
         match the dataclass *exactly*)
      -> frontend/src/api/client.ts   (hand-typed TS interfaces)

A field rename or type change in an engine dataclass that is exposed through the
API used to break the boundary *silently* (``asdict`` produces the new key,
Pydantic drops it into a default or ignores it). These tests fail on that drift.

Coverage:
  * Engine <-> Pydantic (the dangerous ``asdict`` leg): field-set parity **and**
    structural type compatibility for every entity that crosses the boundary.
  * Pydantic <-> TypeScript (the hand-typed leg): field-name parity, parsed out
    of ``client.ts`` with a dependency-free regex. Type checking on the TS side
    is left to ``tsc``; this only guards against a forgotten/renamed field.
"""

from __future__ import annotations

import dataclasses
import os
import re
import sys
import typing
from typing import get_args, get_origin

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_BACKEND = os.path.join(_ROOT, "backend")
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from pydantic import BaseModel  # noqa: E402

from engine import models as engine_models  # noqa: E402
from app.schemas import api as schemas  # noqa: E402


# ---------------------------------------------------------------------------
# The entities that cross the API boundary, paired dataclass -> Pydantic model.
#
# Entities in ``FULL_ASDICT_PAIRS`` are converted whole via ``asdict`` in the
# service layer (directly or nested inside another asdict'd entity), so the
# field sets must match *exactly* -- an extra Pydantic field would demand data
# the engine never emits; a missing one would silently drop an engine field.
# ---------------------------------------------------------------------------

FULL_ASDICT_PAIRS = [
    (engine_models.Faction, schemas.FactionModel),
    (engine_models.Crisis, schemas.CrisisModel),
    (engine_models.AdviceOption, schemas.AdviceOptionModel),
    (engine_models.ClientCall, schemas.ClientCallModel),
    (engine_models.Document, schemas.DocumentModel),
    (engine_models.ThreadCondition, schemas.ThreadConditionModel),
    (engine_models.OpenThread, schemas.OpenThreadModel),
    (engine_models.WorldState, schemas.WorldStateModel),
    (engine_models.AppliedDiff, schemas.AppliedDiffModel),
    (engine_models.NpcDecision, schemas.NpcDecisionModel),
    (engine_models.CanonEntry, schemas.CanonEntryModel),
    (engine_models.FactionReaction, schemas.FactionReactionModel),
    (engine_models.ConsequenceStack, schemas.ConsequenceStackModel),
    (engine_models.ConsequenceDelta, schemas.ConsequenceDeltaModel),
    (engine_models.AdviceMediation, schemas.AdviceMediationModel),
    (engine_models.VariableConsequence, schemas.VariableConsequenceModel),
    (engine_models.ConsequenceReport, schemas.ConsequenceReportModel),
    (engine_models.TurnResult, schemas.TurnResultModel),
]

# ``Campaign`` is *decomposed* into a summary in the service (not asdict'd
# whole), so only the summary's fields must exist on the dataclass.
SUBSET_PAIRS = [
    (engine_models.Campaign, schemas.CampaignSummaryModel),
]

_PAIR_IDS_FULL = [dc.__name__ for dc, _ in FULL_ASDICT_PAIRS]
_PAIR_IDS_SUBSET = [dc.__name__ for dc, _ in SUBSET_PAIRS]

# The set of engine dataclasses / Pydantic models that appear nested inside
# another entity. When a field's type resolves to one of these, we treat it as
# an opaque "object" so ``List[Faction]`` (dataclass) and ``List[FactionModel]``
# (Pydantic) compare equal -- the nested entity has its own row in the matrix.
_ENGINE_DATACLASSES = {
    dc for dc, _ in FULL_ASDICT_PAIRS + SUBSET_PAIRS
}


def _dataclass_hints(dc) -> dict:
    """Resolved type hints for a dataclass (``from __future__ import
    annotations`` stores raw strings; ``get_type_hints`` evaluates them)."""
    return typing.get_type_hints(dc)


def _normalize(tp) -> str:
    """Reduce a type to a canonical structural signature, collapsing any nested
    engine dataclass or Pydantic model to the marker ``<obj>`` so the two type
    systems can be compared field-for-field."""
    if tp is type(None):
        return "none"
    origin = get_origin(tp)
    if origin is None:
        # A concrete class.
        if isinstance(tp, type) and issubclass(tp, bool):
            return "bool"
        if isinstance(tp, type) and issubclass(tp, int):
            return "int"
        if tp is float:
            return "float"
        if tp is str:
            return "str"
        if dataclasses.is_dataclass(tp):
            return "<obj>"
        if isinstance(tp, type) and issubclass(tp, BaseModel):
            return "<obj>"
        # Fall back to the bare name so unexpected types still surface a diff.
        return getattr(tp, "__name__", str(tp))

    args = get_args(tp)
    if origin is typing.Union:
        non_none = [a for a in args if a is not type(None)]
        inner = "|".join(sorted(_normalize(a) for a in non_none))
        if type(None) in args:
            return f"Optional[{inner}]"
        return f"Union[{inner}]"
    if origin in (list, typing.List):
        return f"List[{_normalize(args[0]) if args else 'any'}]"
    if origin in (dict, typing.Dict):
        k = _normalize(args[0]) if args else "any"
        v = _normalize(args[1]) if len(args) > 1 else "any"
        return f"Dict[{k},{v}]"
    if origin in (tuple, typing.Tuple):
        return "Tuple[" + ",".join(_normalize(a) for a in args) + "]"
    return getattr(origin, "__name__", str(origin))


@pytest.mark.parametrize("dc,model", FULL_ASDICT_PAIRS, ids=_PAIR_IDS_FULL)
def test_pydantic_model_field_sets_match_dataclass(dc, model):
    """Every asdict'd entity must have exactly the same field set on both sides.

    A rename in the engine (``decider`` -> ``decider_name``) drops the old key
    off the dataclass side; a stale Pydantic field drops off the model side.
    Either way this equality fails.
    """
    dc_fields = {f.name for f in dataclasses.fields(dc)}
    model_fields = set(model.model_fields)
    missing_on_model = dc_fields - model_fields
    extra_on_model = model_fields - dc_fields
    assert not missing_on_model, (
        f"{dc.__name__} field(s) {sorted(missing_on_model)} are exposed by "
        f"asdict but missing from {model.__name__} -- the API would silently "
        f"drop them."
    )
    assert not extra_on_model, (
        f"{model.__name__} has field(s) {sorted(extra_on_model)} with no "
        f"corresponding field on {dc.__name__} -- the engine never emits them."
    )


@pytest.mark.parametrize("dc,model", FULL_ASDICT_PAIRS, ids=_PAIR_IDS_FULL)
def test_pydantic_model_field_types_match_dataclass(dc, model):
    """Every shared field must have a structurally compatible type.

    Nested entities collapse to ``<obj>`` (they get their own row), so this
    catches e.g. ``int`` -> ``str`` or ``List[str]`` -> ``str`` drift without
    tripping on ``Faction`` vs ``FactionModel``.
    """
    hints = _dataclass_hints(dc)
    mismatches = []
    for name, mfield in model.model_fields.items():
        if name not in hints:
            continue  # field-set test owns presence; skip here
        dc_sig = _normalize(hints[name])
        model_sig = _normalize(mfield.annotation)
        if dc_sig != model_sig:
            mismatches.append(f"{name}: dataclass={dc_sig} pydantic={model_sig}")
    assert not mismatches, (
        f"{dc.__name__} <-> {model.__name__} type drift: " + "; ".join(mismatches)
    )


@pytest.mark.parametrize("dc,model", SUBSET_PAIRS, ids=_PAIR_IDS_SUBSET)
def test_summary_model_fields_exist_on_dataclass(dc, model):
    """Decomposed entities: every summary field must name a real dataclass
    field (a rename of e.g. ``scenario_id`` breaks the summary projection)."""
    dc_fields = {f.name for f in dataclasses.fields(dc)}
    missing = set(model.model_fields) - dc_fields
    assert not missing, (
        f"{model.__name__} references field(s) {sorted(missing)} that do not "
        f"exist on {dc.__name__}."
    )
    # Where the field is shared, the types must still be compatible.
    hints = _dataclass_hints(dc)
    mismatches = []
    for name, mfield in model.model_fields.items():
        if name not in hints:
            continue
        dc_sig = _normalize(hints[name])
        model_sig = _normalize(mfield.annotation)
        if dc_sig != model_sig:
            mismatches.append(f"{name}: dataclass={dc_sig} pydantic={model_sig}")
    assert not mismatches, (
        f"{dc.__name__} <-> {model.__name__} type drift: " + "; ".join(mismatches)
    )


# ---------------------------------------------------------------------------
# Pydantic <-> TypeScript field-name parity.
# ---------------------------------------------------------------------------

# Maps a TS interface name in client.ts to its Pydantic model. Field *names*
# only -- ``tsc`` owns TS-internal type checking; this guards a forgotten field.
TS_INTERFACE_TO_MODEL = {
    "Faction": schemas.FactionModel,
    "Crisis": schemas.CrisisModel,
    "AdviceOption": schemas.AdviceOptionModel,
    "ClientCall": schemas.ClientCallModel,
    "DocumentRecord": schemas.DocumentModel,
    "ThreadCondition": schemas.ThreadConditionModel,
    "OpenThread": schemas.OpenThreadModel,
    "WorldState": schemas.WorldStateModel,
    "CampaignSummary": schemas.CampaignSummaryModel,
    "NpcDecision": schemas.NpcDecisionModel,
    "AppliedDiff": schemas.AppliedDiffModel,
    "CanonEntry": schemas.CanonEntryModel,
    "FactionReaction": schemas.FactionReactionModel,
    "ConsequenceStack": schemas.ConsequenceStackModel,
    "ConsequenceDelta": schemas.ConsequenceDeltaModel,
    "AdviceMediation": schemas.AdviceMediationModel,
    "VariableConsequence": schemas.VariableConsequenceModel,
    "ConsequenceReport": schemas.ConsequenceReportModel,
    "TurnResult": schemas.TurnResultModel,
    "SystemStatus": schemas.SystemStatusModel,
    "MemoContent": schemas.MemoContentModel,
    "MemoDraft": schemas.MemoDraftModel,
    "ModelRun": schemas.ModelRunModel,
}

_CLIENT_TS = os.path.join(_ROOT, "frontend", "src", "api", "client.ts")
_INTERFACE_RE = re.compile(
    r"export interface (\w+)\s*\{(.*?)\}", re.DOTALL
)
# A member line looks like ``  field_name: Type;`` or ``  field_name?: Type;``.
_MEMBER_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:", re.MULTILINE)


def _parse_ts_interfaces() -> dict:
    with open(_CLIENT_TS, "r", encoding="utf-8") as fh:
        source = fh.read()
    interfaces = {}
    for match in _INTERFACE_RE.finditer(source):
        name, body = match.group(1), match.group(2)
        interfaces[name] = {m.group(1) for m in _MEMBER_RE.finditer(body)}
    return interfaces


def test_client_ts_interfaces_are_parseable():
    """Guard the parser itself: every mapped interface must be found in
    client.ts (so a rename of the interface can't make a check vacuously pass)."""
    interfaces = _parse_ts_interfaces()
    missing = set(TS_INTERFACE_TO_MODEL) - set(interfaces)
    assert not missing, f"interfaces not found in client.ts: {sorted(missing)}"


@pytest.mark.parametrize(
    "iface_name", list(TS_INTERFACE_TO_MODEL), ids=list(TS_INTERFACE_TO_MODEL)
)
def test_ts_interface_field_names_match_pydantic(iface_name):
    interfaces = _parse_ts_interfaces()
    ts_fields = interfaces[iface_name]
    model = TS_INTERFACE_TO_MODEL[iface_name]
    py_fields = set(model.model_fields)
    missing_in_ts = py_fields - ts_fields
    extra_in_ts = ts_fields - py_fields
    assert not missing_in_ts, (
        f"TS interface {iface_name} is missing field(s) {sorted(missing_in_ts)} "
        f"present on {model.__name__}."
    )
    assert not extra_in_ts, (
        f"TS interface {iface_name} has field(s) {sorted(extra_in_ts)} not "
        f"present on {model.__name__}."
    )
