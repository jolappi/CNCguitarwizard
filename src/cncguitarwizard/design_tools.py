"""Saved designs described, started, changed and checked from the command line.

The command line's ``settings``, ``new-design``, ``set`` and ``check``
commands, and the CNCguitarwizard skill that drives them (an AI assistant
such as Claude), work on the design files the web app's *Save design*
writes and its *Load design* reads (``webapp.DESIGN_FORMAT``). Every
change goes through the web app's own reading and checking: a setting
this version does not know, a value of the wrong type or a choice it
does not offer is refused, and a design is checked by building its
geometry, the editors' problems (``webapp.design_problems``) and its
parameter sheet. Nothing here computes a dimension of its own.

Lengths are millimetres; a length may be given in inches (``25.5in``,
25.4 mm an inch). Angles are degrees.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from .cam import MachiningParameters
from .exceptions import CNCGuitarWizardError
from .geometry.body.bridges import BRIDGE_KINDS, bridge_spec_from_dict
from .presets import Prototype001Parameters
from .presets.body_shapes import body_shape_from_dict
from .presets.prototype001 import INSTRUMENT_OVERRIDES
from .presets.styles import STYLES
from .setting_conditions import APPLIES_WHEN, applies
from .webapp import (
    DESIGN_FORMAT,
    LoadedDesign,
    design_problems,
    load_design,
    parameter_schema,
    style_design,
)
from .workflows import parameter_sheet
from .workflows.parameter_sheet import READY_FOR_REVIEW

MM_PER_INCH = 25.4
"""Millimetres in an inch, for a length given in inches."""

NOT_LENGTHS = (
    "angle",
    "fraction",
    "exponent",
    "perpendicular_fret",
    "speed",
    "rate",
    "dwell",
    "step_over",
)
"""Words in the names of number settings that are not lengths, which so
take no inches (angles, fractions, speeds and feeds...)."""

TRUE_WORDS = ("true", "yes", "on", "1")
FALSE_WORDS = ("false", "no", "off", "0")
"""How a yes/no setting may be given."""


class DesignFileError(CNCGuitarWizardError):
    """Raised when a design file cannot be read, made or changed."""


@dataclass(frozen=True, slots=True)
class SettingInfo:
    """One setting as the web app's form describes it.

    Args:
        name: The setting's name.
        part: ``"prototype"`` (the instrument) or ``"machining"``.
        group: The form's group it is in (``"Neck"``).
        field: The form's description of it (``parameter_schema``):
            ``type``, ``default``, ``help``, ``options``, ``variants``.
    """

    name: str
    part: str
    group: str
    field: dict[str, Any]


@cache
def setting_index() -> dict[str, SettingInfo]:
    """Return every setting of a design, by name (``parameter_schema``)."""
    schema = parameter_schema()
    return {
        field["name"]: SettingInfo(field["name"], part, group["title"], field)
        for part in ("prototype", "machining")
        for group in schema[part]
        for field in group["fields"]
    }


def read_design(path: Path) -> dict[str, Any]:
    """Return the design saved in ``path``.

    Raises:
        DesignFileError: If it cannot be read, or is not a design file.
    """
    try:
        design = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise DesignFileError(f"{path}: {error}") from error
    if not isinstance(design, dict) or design.get("format") != DESIGN_FORMAT:
        raise DesignFileError(f"{path} is not a CNCguitarwizard design file.")
    return design


def write_design(path: Path, design: dict[str, Any]) -> None:
    """Write ``design`` to ``path`` as the web app's *Save design* does."""
    path.write_text(json.dumps(design, indent=2) + "\n", encoding="utf-8")


def new_design(
    instrument: str, style: str | None = None, name: str = ""
) -> dict[str, Any]:
    """Return a new design: an instrument's defaults, or one of its styles.

    Args:
        instrument: An ``INSTRUMENT_OVERRIDES`` key (``electric_guitar``).
        style: A ``STYLES`` key offered for the instrument, or ``None``.
        name: The guitar's name.

    Returns:
        The design, as the web app saves one.

    Raises:
        DesignFileError: For an unknown instrument, or a style not offered
            for it.
    """
    if instrument not in INSTRUMENT_OVERRIDES:
        raise DesignFileError(
            f"Unknown instrument {instrument!r}; choose one of "
            f"{', '.join(INSTRUMENT_OVERRIDES)}."
        )
    if style is None:
        return {
            "format": DESIGN_FORMAT,
            "version": 1,
            "name": name,
            "instrument": instrument,
            "prototype": {},
            "machining": {},
        }
    design = style_design(instrument, style, name)
    if "error" in design:
        offered = [
            key for key, kind in STYLES.items() if instrument in kind.instruments
        ]
        raise DesignFileError(
            f"{design['error']} The styles for it: {', '.join(offered) or 'none'}."
        )
    return design


def describe_settings(
    design: dict[str, Any] | None = None,
    search: str = "",
    group: str = "",
    changed_only: bool = False,
) -> list[dict[str, Any]]:
    """Return the settings, each with its type, default and meaning.

    Args:
        design: A design, for each setting's value in it and whether it
            does anything there (``setting_conditions.applies``), the
            defaults its instrument's; ``None`` for the plain defaults.
        search: Words every setting listed has in its name or meaning
            (underscores read as spaces), as the web app's *Find a
            setting*.
        group: Only the settings of this form group (``"Neck"``,
            ``"Machining"``), any case.
        changed_only: Only those the design changed from its defaults.

    Returns:
        ``{"name", "group", "type", "default", "help"}`` for each, with
        ``options`` (a choice's), ``kinds`` (a bridge's or body shape's)
        and, for a design, ``value`` and ``applies``, with ``applies_when``
        for one that does nothing there.

    Raises:
        DesignFileError: If the design's values do not read.
    """
    if design is not None:
        values, defaults = _design_values(design)
    else:
        values = None
        defaults = _plain_values(Prototype001Parameters()) | _plain_values(
            MachiningParameters()
        )
    words = search.lower().replace("_", " ").split()
    described = []
    for info in setting_index().values():
        if group and info.group.lower() != group.lower():
            continue
        meaning = info.field.get("help", "")
        text = f"{info.name.replace('_', ' ')} {meaning}".lower()
        if not all(word in text for word in words):
            continue
        if changed_only and (
            values is None or values[info.name] == defaults[info.name]
        ):
            continue
        entry: dict[str, Any] = {
            "name": info.name,
            "group": info.group,
            "type": info.field["type"],
            "default": defaults[info.name],
        }
        if values is not None:
            entry["value"] = values[info.name]
            entry["applies"] = applies(info.name, values)
            if not entry["applies"]:
                entry["applies_when"] = applies_when(info.name)
        if "options" in info.field:
            entry["options"] = info.field["options"]
        if "variants" in info.field:
            entry["kinds"] = list(info.field["variants"])
        entry["help"] = meaning
        described.append(entry)
    return described


def check_design(design: dict[str, Any]) -> dict[str, Any]:
    """Return whether a design builds, and what is wrong with it if not.

    It is read as the web app loads it (``load_design``), its geometry
    built, the editors' problems found (``design_problems``) and its
    parameter sheet checked. The machining is planned only when it is
    built (``build-prototype001``).

    Args:
        design: The design.

    Returns:
        ``{"ok", "name", "instrument", "error", "problems", "skipped",
        "sheet", "changed"}``: ``ok`` when it builds with no problem and
        the sheet is ``READY FOR HUMAN REVIEW``; ``error`` why it does
        not build (``None`` when it does); ``problems`` what the editors
        would show in red; ``skipped`` the settings this version does not
        know; ``sheet`` the parameter sheet's status and checks;
        ``changed`` the settings it changed from its instrument's
        defaults, with their values.
    """
    result: dict[str, Any] = {
        "ok": False,
        "name": design.get("name", ""),
        "instrument": design.get("instrument"),
        "error": None,
        "problems": [],
        "skipped": [],
        "sheet": None,
        "changed": {},
    }
    try:
        loaded = load_design(design)
        geometry = loaded.parameters.build()
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        result["error"] = _reason(error)
        return result
    parameters = loaded.parameters
    values, defaults = _loaded_values(loaded)
    result["skipped"] = list(loaded.skipped)
    result["changed"] = {
        name: value for name, value in values.items() if value != defaults[name]
    }
    result["problems"] = design_problems({"prototype": _plain_values(parameters)})
    sheet = parameter_sheet(parameters, geometry)
    result["sheet"] = {
        "status": sheet.status,
        "checks": [check.as_dict() for check in sheet.checks],
    }
    result["ok"] = not result["problems"] and sheet.status == READY_FOR_REVIEW
    return result


def set_values(design: dict[str, Any], assignments: Sequence[str]) -> dict[str, Any]:
    """Return a design with settings changed, and whether to keep it.

    Each assignment is ``name=value``, or ``name.field=value`` for one
    field of a bridge or body shape (``body_bridge.string_count=7``);
    ``body_bridge=floyd_rose`` chooses another kind, written whole with
    its defaults.
    Values are read as the setting's type: a number (a length may be in
    inches, ``25.5in``), ``true``/``false``, one of a choice's options,
    ``none`` for an empty optional number, JSON for a list.

    Args:
        design: The design to change (not changed itself).
        assignments: The changes, in order.

    Returns:
        ``{"keep", "changes", "unchanged", "not_applied", "rejected",
        "check", "design"}``: ``changes`` each ``{"name", "from",
        "to"}``; ``unchanged`` the settings given the value they had;
        ``not_applied`` those given that do nothing beside the other
        settings (``setting_conditions.applies``), each ``{"name",
        "applies_when"}`` (``applies_when``); ``rejected`` each
        ``{"assignment", "reason"}``; ``check`` the changed design's
        ``check_design`` (``None`` when something was rejected);
        ``design`` the changed design. ``keep`` is true when nothing was
        rejected and the changed design is ``ok``, or no worse than an
        unfinished one it started from.

    Raises:
        DesignFileError: If the design's values do not read.
    """
    values, _ = _design_values(design)
    changed = copy.deepcopy(design)
    changes: list[dict[str, Any]] = []
    unchanged: list[str] = []
    rejected: list[dict[str, str]] = []
    for assignment in assignments:
        name, equals, text = assignment.partition("=")
        name = name.strip()
        try:
            if not equals:
                raise DesignFileError("Write it as name=value.")
            top, _, field_name = name.partition(".")
            new = _parsed(top, field_name, text, values)
        except DesignFileError as error:
            rejected.append({"assignment": assignment, "reason": str(error)})
            continue
        old = values[top]
        was, now = (old.get(field_name), new[field_name]) if field_name else (old, new)
        if was == now:
            unchanged.append(name)
            continue
        changes.append({"name": name, "from": was, "to": now})
        values[top] = new
        changed.setdefault(setting_index()[top].part, {})[top] = new
    # A setting given that does nothing beside the others' values (a neck
    # pickup's kind under a named layout): said, with what it needs, not
    # refused.
    given = {
        name.partition(".")[0] for name in [c["name"] for c in changes] + unchanged
    }
    not_applied = [
        {"name": name, "applies_when": applies_when(name)}
        for name in sorted(given)
        if not applies(name, values)
    ]
    result: dict[str, Any] = {
        "keep": False,
        "changes": changes,
        "unchanged": unchanged,
        "not_applied": not_applied,
        "rejected": rejected,
        "check": None,
        "design": changed,
    }
    if rejected:
        return result
    after = result["check"] = check_design(changed)
    result["keep"] = after["ok"]
    if not after["ok"]:
        # An unfinished design may be worked on: kept when no worse.
        start = check_design(design)
        result["keep"] = not start["ok"] and _faults(after) <= _faults(start)
    return result


def applies_when(name: str) -> list[dict[str, list[Any]]]:
    """Return the conditions under which setting ``name`` does anything,
    any one of them: the values other settings must have
    (``setting_conditions.APPLIES_WHEN``; empty for a setting that always
    does)."""
    return [
        {other: list(allowed) for other, allowed in condition.items()}
        for condition in APPLIES_WHEN.get(name, ())
    ]


def _parsed(top: str, field_name: str, text: str, values: dict[str, Any]) -> Any:
    """Return a setting's new value read from ``text``.

    For a bridge's or body shape's own field (``field_name``), the whole
    variant with that field changed.
    """
    if top == "instrument":
        raise DesignFileError(
            "The instrument decides every default: start a new design for "
            "another one (new-design --instrument)."
        )
    info = setting_index().get(top)
    if info is None:
        raise DesignFileError(f"There is no setting {top!r}; see the settings command.")
    field = info.field
    if field_name:
        if field["type"] != "variant":
            raise DesignFileError(f"{top} has no fields of its own.")
        current = dict(values[top])
        own = {
            entry["name"]: entry
            for entry in field["variants"][current["kind"]]["fields"]
        }
        if field_name not in own:
            raise DesignFileError(
                f"{top} {current['kind']!r} has no field {field_name!r}; it has "
                f"{', '.join(own)}."
            )
        current[field_name] = _read_value(field_name, own[field_name], text)
        return current
    if field["type"] == "variant":
        kind = text.strip()
        if kind not in field["variants"]:
            raise DesignFileError(
                f"{top} is one of {', '.join(field['variants'])}, not {kind!r}."
            )
        # Written whole, its defaults, as the web app saves a variant.
        spec = (
            bridge_spec_from_dict({"kind": kind})
            if kind in BRIDGE_KINDS
            else body_shape_from_dict({"kind": kind})
        )
        plain: dict[str, Any] = _plain(spec)
        return plain
    return _read_value(top, field, text)


def _read_value(name: str, field: dict[str, Any], text: str) -> Any:
    """Return ``text`` read as the setting ``field`` describes."""
    kind = field["type"]
    text = text.strip()
    if kind == "optional_float" and text.lower() in ("", "none", "null"):
        return None
    if kind in ("float", "optional_float"):
        return _number(name, text)
    if kind == "int":
        try:
            return int(text)
        except ValueError:
            raise DesignFileError(
                f"{name} takes a whole number, not {text!r}."
            ) from None
    if kind == "bool":
        if text.lower() in TRUE_WORDS:
            return True
        if text.lower() in FALSE_WORDS:
            return False
        raise DesignFileError(f"{name} is true or false, not {text!r}.")
    if kind == "choice":
        if text not in field["options"]:
            raise DesignFileError(
                f"{name} is one of {', '.join(field['options'])}, not {text!r}."
            )
        return text
    if kind == "json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            raise DesignFileError(f"{name} takes JSON (a list: [3, 5, 7]).") from None
    return text


def _number(name: str, text: str) -> float:
    """Return a number setting's value: a length in mm, or in inches."""
    plain = text.lower().replace(" ", "").replace(",", ".")
    factor = 1.0
    if plain.endswith("mm"):
        plain = plain[:-2]
    elif plain.endswith(("in", '"')):
        if any(word in name for word in NOT_LENGTHS):
            raise DesignFileError(f"{name} is no length; it takes no inches.")
        plain = plain.removesuffix("in").removesuffix('"')
        factor = MM_PER_INCH
    try:
        number = float(plain)
    except ValueError:
        raise DesignFileError(f"{name} takes a number, not {text!r}.") from None
    if not math.isfinite(number):
        raise DesignFileError(f"{name} takes a finite number, not {text!r}.")
    return round(number * factor, 4)


def _design_values(
    design: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a design's every setting and its instrument's defaults, as
    plain values (a bridge or body shape a dict with its ``kind``)."""
    try:
        loaded = load_design(design)
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        raise DesignFileError(f"The design does not read: {_reason(error)}") from error
    return _loaded_values(loaded)


def _loaded_values(loaded: LoadedDesign) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return a loaded design's every setting and its instrument's
    defaults, as plain values."""
    defaults = Prototype001Parameters.for_instrument(loaded.parameters.instrument)
    return (
        _plain_values(loaded.parameters) | _plain_values(loaded.machining),
        _plain_values(defaults) | _plain_values(MachiningParameters()),
    )


def _plain_values(parameters: Any) -> dict[str, Any]:
    """Return a parameter set's values as JSON-ready ones, by name."""
    return {
        field.name: _plain(getattr(parameters, field.name))
        for field in dataclasses.fields(parameters)
    }


def _plain(value: Any) -> Any:
    """Return ``value`` JSON-ready: tuples as lists, dataclasses as dicts."""
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _plain(dataclasses.asdict(value))
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    return value


def _faults(check: dict[str, Any]) -> int:
    """Return how much is wrong with a checked design: its error and
    problems, and a sheet that is not ready."""
    sheet_fault = (
        check["sheet"] is not None and check["sheet"]["status"] != READY_FOR_REVIEW
    )
    return int(check["error"] is not None) + len(check["problems"]) + int(sheet_fault)


def _reason(error: Exception) -> str:
    """Return an error as the web app shows it: its kind and message."""
    return f"{type(error).__name__}: {error}"
