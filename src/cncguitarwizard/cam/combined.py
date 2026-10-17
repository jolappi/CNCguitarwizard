"""Programs cut one after another with the same tool, joined into one.

Each part's setups are planned one program each, so the operator can run
them apart (a cavity left out, a program run again). Where several in a
row keep the same fixture, tool and work zero, nothing is done at the
machine between them: ``combined_setups`` joins them into one program,
cut in the same order, so they are loaded and started once.
"""

from __future__ import annotations

from collections.abc import Sequence

from .gcode import Setup
from .parameters import MachiningParameters


def runs_together(first: Setup, second: Setup, parameters: MachiningParameters) -> bool:
    """Return whether ``second`` can be cut straight after ``first``.

    Both need the same fixture (not ``None``), the same tool
    (``Setup.tool``, else ``parameters``), the same work zero and the
    same dowels to check.

    Args:
        first: The program cut first.
        second: The program cut next.
        parameters: The tool of a setup that names none.

    Returns:
        ``True`` when one program can cut both.
    """
    return (
        first.fixture is not None
        and first.fixture == second.fixture
        and (first.tool or parameters) == (second.tool or parameters)
        and first.work_zero == second.work_zero
        and first.reference_points == second.reference_points
    )


def setup_runs(
    setups: Sequence[Setup], parameters: MachiningParameters
) -> tuple[tuple[int, ...], ...]:
    """Return the setups' indices grouped into the programs that cut them.

    Args:
        setups: One part's setups, in running order.
        parameters: The tool of a setup that names none.

    Returns:
        One group per program, in running order: the setups each cuts,
        a single one where the next needs anything done first.
    """
    runs: list[list[int]] = []
    for index, setup in enumerate(setups):
        if runs and runs_together(setups[runs[-1][-1]], setup, parameters):
            runs[-1].append(index)
        else:
            runs.append([index])
    return tuple(tuple(run) for run in runs)


def combined_setup(setups: Sequence[Setup]) -> Setup:
    """Return setups that run together as one program.

    It is named after the first, then each later one by the words its
    name does not share with the first's: ``Body_back`` and
    ``Body_back_controls`` make ``Body_back_and_controls``. Its notes are
    the first's, then each later one's under its own name.

    Args:
        setups: Setups that ``runs_together`` in turn, at least one.

    Returns:
        The one program; a single setup unchanged.
    """
    first, *later = setups
    if not later:
        return first
    return Setup(
        "_and_".join([first.name, *(_own_words(first.name, s.name) for s in later)]),
        "; then ".join(setup.description for setup in setups),
        tuple(path for setup in setups for path in setup.toolpaths),
        (
            *first.notes,
            *(
                note
                for setup in later
                for note in (
                    f"Then {setup.name}: {setup.description}.",
                    *(f"{setup.name}: {text}" for text in setup.notes),
                )
            ),
        ),
        first.reference_points,
        first.tool,
        first.work_zero,
        first.fixture,
    )


def combined_setups(
    setups: Sequence[Setup], parameters: MachiningParameters
) -> tuple[Setup, ...]:
    """Return one part's setups with those that run together joined.

    Args:
        setups: One part's setups, in running order.
        parameters: The tool of a setup that names none.

    Returns:
        The programs in running order (``setup_runs``).
    """
    return tuple(
        combined_setup([setups[index] for index in run])
        for run in setup_runs(setups, parameters)
    )


def _own_words(first: str, name: str) -> str:
    """Return the words of ``name`` after those it shares with ``first``.

    At least its last word stays: ``Body_top`` after ``Body_top_steps``
    is ``top``.
    """
    words = name.split("_")
    shared = 0
    for mine, theirs in zip(words, first.split("_"), strict=False):
        if mine != theirs:
            break
        shared += 1
    return "_".join(words[min(shared, len(words) - 1) :])
