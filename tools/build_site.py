"""Assemble the static web app in ``site/`` for GitHub Pages.

Builds the package wheel into ``site/wheels/`` and writes
``site/wheel.json`` so the page knows which wheel to install into
Pyodide. The manifest also carries a build id (a hash of the wheel and app.js) that the
page appends to the ``app.js`` and wheel URLs, so browsers never pair a
cached script with a newer wheel or vice versa, and the page's own stamp
(``stamped_page``): a page that finds a different one in the manifest is
a stale copy from a cache, and loads itself afresh. Run it from the
repository root::

    python tools/build_site.py

The same script runs in the Pages workflow.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
WHEELS = SITE / "wheels"

PAGE_STAMP = re.compile(r'(<meta name="cgw-page" content=")([0-9a-f]*)(">)')
"""The page's stamp in ``index.html``: a meta tag the loader reads."""


def stamped_page(text: str) -> tuple[str, str]:
    """Return ``index.html``'s text with its stamp set, and the stamp.

    The stamp is a hash of the page with the stamp itself left empty, so
    it changes only when the page does (and a page stamped already comes
    back unchanged).

    Raises:
        SystemExit: For a page without the stamp's meta tag.
    """
    if not PAGE_STAMP.search(text):
        raise SystemExit('index.html has no <meta name="cgw-page" content="">')
    blank = PAGE_STAMP.sub(r"\g<1>\g<3>", text)
    stamp = hashlib.sha256(blank.encode("utf-8")).hexdigest()[:12]
    return PAGE_STAMP.sub(rf"\g<1>{stamp}\g<3>", text), stamp


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
    # Hash the wheel together with the page's own scripts, so a change to
    # app.js (or the app layout's desktop.js) alone also busts the cache.
    digest = hashlib.sha256(wheels[0].read_bytes())
    digest.update((SITE / "app.js").read_bytes())
    digest.update((SITE / "desktop.js").read_bytes())
    build_id = digest.hexdigest()[:12]
    page = SITE / "index.html"
    text = page.read_text(encoding="utf-8")
    stamped, stamp = stamped_page(text)
    if stamped != text:
        page.write_text(stamped, encoding="utf-8")
    manifest = {"wheel": wheels[0].name, "build": build_id, "page": stamp}
    (SITE / "wheel.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"Site ready: {SITE} (wheel {wheels[0].name}, build {build_id}, page {stamp})"
    )


if __name__ == "__main__":
    main()
