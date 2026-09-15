"""Assemble the static web app in ``site/`` for GitHub Pages.

Builds the package wheel into ``site/wheels/`` and writes
``site/wheel.json`` so the page knows which wheel to install into
Pyodide. Run it from the repository root::

    python tools/build_site.py

The same script runs in the Pages workflow.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
WHEELS = SITE / "wheels"


def main() -> None:
    if WHEELS.exists():
        shutil.rmtree(WHEELS)
    WHEELS.mkdir(parents=True)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            str(ROOT),
            "--no-deps",
            "--wheel-dir",
            str(WHEELS),
            "--quiet",
        ],
        check=True,
    )
    wheels = sorted(WHEELS.glob("cncguitarwizard-*.whl"))
    if len(wheels) != 1:
        raise SystemExit(f"Expected exactly one wheel, found {len(wheels)}")
    (SITE / "wheel.json").write_text(
        json.dumps({"wheel": wheels[0].name}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Site ready: {SITE} (wheel {wheels[0].name})")


if __name__ == "__main__":
    main()
