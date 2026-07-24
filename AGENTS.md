# CNCguitarwizard Development Guide

Welcome to the CNCguitarwizard project.

This document defines the engineering principles, coding standards and
architecture rules that every AI agent must follow when contributing to
this repository.

## Project Goal

CNCguitarwizard is an open source Python application for designing guitar
necks, fretboards and CNC-ready geometry.

The project values:

- readability
- correctness
- maintainability
- documentation
- small commits
- comprehensive tests

Performance is important but never at the expense of code quality.

## Python Version

Minimum supported version: Python 3.12.

Always use modern Python features.

## Project Layout

```text
src/
    cncguitarwizard/

tests/

docs/
```

Never create modules outside the src layout.

## Development Philosophy

Prefer simple over smart, explicit over implicit, and maintainable over
clever. The code should be understandable by a Python beginner.

## Coding Style

Use:

- dataclasses
- `slots=True`
- `frozen=True`
- type hints everywhere
- Google style docstrings

Avoid:

- unnecessary inheritance
- global state
- mutable geometry
- hidden side effects

## Geometry Rules

All geometry is immutable. Every geometric object represents a mathematical
fact. Never mutate `Point2D`, `Line2D`, `Vector2D`, or `Centerline`; create new
objects instead.

## Units

All dimensions are expressed in millimetres (mm). Never mix units.

## Public API

Keep public APIs intentionally small. Do not implement methods that are not
required. Follow YAGNI (You Aren't Gonna Need It).

## Exceptions

Never raise generic `Exception`. Use project-specific exceptions, such as
`GeometryException`, `ZeroLengthVectorError`, and `CalculationError`.

## Testing

Every feature requires tests. pytest is mandatory. Every bug fix requires a
regression test.

## Documentation

Every public class must contain:

- a docstring
- parameter documentation
- return documentation where appropriate

Every new package must have documentation inside `docs/`.

## Git

One commit equals one idea. Commit messages use Conventional Commits.

Examples:

```text
feat(geometry): add Point2D
fix(svg): correct line scaling
docs: update geometry documentation
test: improve primitive coverage
```

## Code Reviews

Always optimise for readability. Never optimise prematurely. Never sacrifice
clarity for fewer lines of code.

## Architecture

```text
CLI
↓
Configuration
↓
Calculation
↓
Geometry
↓
Rendering
↓
Export
```

Dependencies always point downward. Rendering must never know about CLI.
Geometry must never depend on rendering.

## Future Goals

```text
Geometry Engine
↓
Fretboard Generator
↓
Neck Generator
↓
SVG Export
↓
DXF Export
↓
FreeCAD
↓
CAM Integration
```

## Definition of Done

A task is complete only if:

- code compiles
- pytest passes
- Ruff passes
- mypy passes
- documentation is updated
- HISTORY is updated

## Final Principle

Write code that you would be proud to read again in five years.
