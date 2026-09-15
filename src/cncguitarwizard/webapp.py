"""Glue for running the Prototype001 build inside a browser (Pyodide).

The static web page in ``site/`` loads the package as a wheel into
Pyodide and calls the two functions here: ``parameter_schema`` to draw
its form, and ``run_build`` to produce every FreeCAD-free artifact in
the browser's virtual file system. Both speak plain JSON-compatible
dictionaries so the JavaScript side needs no knowledge of the
dataclasses.
"""

from __future__ import annotations

import dataclasses
import json
import types
import typing
from pathlib import Path
from typing import Any

from .cam import MachiningParameters
from .exceptions import CNCGuitarWizardError
from .presets import Prototype001Parameters
from .render.svg import render_plan_view_svg
from .workflows import build_prototype001

_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Scale and fretboard",
        ("scale_length", "fret_count", "nut_width", "fret", "inlay"),
    ),
    ("Neck", ("final_fret", "first_fret", "twelfth", "neck", "nut_", "truss")),
    ("Heel", ("heel",)),
    ("Headstock and tuners", ("headstock", "tuner")),
    ("Body", ("body",)),
    ("Fillets and sampling", ("joint_fillet", "profile_sample", "segments")),
)


def parameter_schema() -> dict[str, Any]:
    """Describe both parameter sets for a generated form.

    Returns:
        ``{"prototype": [...groups...], "machining": [...groups...]}``
        where every group is ``{"title", "fields"}`` and every field is
        ``{"name", "type", "default"}`` with ``type`` one of ``float``,
        ``int``, ``bool``, ``optional_float`` or ``json`` (tuples).
    """
    return {
        "prototype": _group_fields(Prototype001Parameters),
        "machining": [
            {"title": "Machining", "fields": _describe_fields(MachiningParameters)}
        ],
    }


def run_build(
    payload: dict[str, Any], output_directory: str = "/build"
) -> dict[str, Any]:
    """Build every FreeCAD-free artifact from JSON parameter overrides.

    Args:
        payload: ``{"prototype": {...}, "machining": {...}}`` with values
            as produced by the form: numbers, booleans, ``None``, and
            lists for tuple fields.
        output_directory: Where to write, on whatever file system the
            interpreter has (Pyodide's in the browser).

    Returns:
        ``{"files": {name: text}, "report": {...}, "plan_view": svg}`` or
        ``{"error": message}`` when the parameters are rejected.
    """
    try:
        parameters = Prototype001Parameters(
            **_coerce(payload.get("prototype", {}))
        )
        machining = MachiningParameters(**_coerce(payload.get("machining", {})))
        geometry = parameters.build()
        result = build_prototype001(
            Path(output_directory),
            parameters,
            run_freecad=False,
            machining=machining,
        )
    except (CNCGuitarWizardError, TypeError, ValueError) as error:
        return {"error": f"{type(error).__name__}: {error}"}

    files: dict[str, str] = {}
    for path in (
        result.python_path,
        result.macro_path,
        result.report_path,
        *result.gcode_paths,
        *result.toolpath_preview_paths,
    ):
        files[path.name] = path.read_text(encoding="utf-8")
    report = json.loads(files[result.report_path.name])
    return {
        "files": files,
        "report": report,
        "plan_view": render_plan_view_svg(geometry),
    }


def _group_fields(cls: type) -> list[dict[str, Any]]:
    """Split a dataclass's fields into titled groups by name prefix."""
    described = _describe_fields(cls)
    groups: list[dict[str, Any]] = [
        {"title": title, "fields": []} for title, _ in _GROUPS
    ]
    other: list[dict[str, Any]] = []
    for field in described:
        for group, (_, prefixes) in zip(groups, _GROUPS, strict=True):
            if any(field["name"].startswith(prefix) for prefix in prefixes):
                group["fields"].append(field)
                break
        else:
            other.append(field)
    if other:
        groups.append({"title": "Other", "fields": other})
    return [group for group in groups if group["fields"]]


def _describe_fields(cls: type) -> list[dict[str, Any]]:
    """Return name, form type, and default for every init field."""
    hints = typing.get_type_hints(cls)
    described = []
    for field in dataclasses.fields(cls):
        if not field.init:
            continue
        default = (
            field.default
            if field.default is not dataclasses.MISSING
            else field.default_factory()  # type: ignore[misc]
        )
        described.append(
            {
                "name": field.name,
                "type": _form_type(hints[field.name]),
                "default": _jsonable(default),
            }
        )
    return described


def _form_type(annotation: Any) -> str:
    """Map a field annotation to the form control it needs."""
    origin = typing.get_origin(annotation)
    if origin in (types.UnionType, typing.Union):
        members = [arg for arg in typing.get_args(annotation) if arg is not type(None)]
        if len(members) == 1 and members[0] is float:
            return "optional_float"
        return "json"
    if annotation is bool:
        return "bool"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    return "json"


def _jsonable(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    return value


def _coerce(values: dict[str, Any]) -> dict[str, Any]:
    """Turn JSON lists back into the tuples the dataclasses expect."""
    return {name: _tuplify(value) for name, value in values.items()}


def _tuplify(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_tuplify(item) for item in value)
    return value
