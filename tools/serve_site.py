"""Serve the web app in ``site/`` locally, never from the browser's cache.

Python's own ``http.server`` sends no ``Cache-Control``, so a browser
may keep the page for a while after a rebuild and show the old one. This
server tells it to check every file again each time (``no-cache``: an
unchanged file comes back as a short "not modified"). Run it from the
repository root, after ``tools/build_site.py``::

    python tools/serve_site.py 8765
"""

from __future__ import annotations

import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


class FreshHandler(SimpleHTTPRequestHandler):
    """A static file handler that asks the browser to revalidate everything."""

    def end_headers(self) -> None:
        """Add ``Cache-Control: no-cache`` to every response."""
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> None:
    """Serve ``site/`` on the port given (8765 by default)."""
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    handler = partial(FreshHandler, directory=str(SITE))
    with ThreadingHTTPServer(("", port), handler) as server:
        print(f"Serving {SITE} at http://localhost:{port}/ (no-cache)")
        server.serve_forever()


if __name__ == "__main__":
    main()
