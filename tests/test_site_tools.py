"""Tests for the web app's build and local server (``tools/``): a new
build must reach the browser, not a cached copy of the last."""

import importlib.util
import threading
import urllib.request
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parent.parent


def tool(name: str) -> ModuleType:
    """Load ``tools/<name>.py`` (a script, not a package module)."""
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PAGE = '<head><meta name="cgw-page" content=""></head><body>{}</body>'


def test_the_page_is_stamped_with_a_hash_of_itself() -> None:
    stamped_page = tool("build_site").stamped_page

    text, stamp = stamped_page(PAGE.format("one"))
    assert f'content="{stamp}"' in text and len(stamp) == 12
    # Stamped again it is the same page; changed, it gets a new stamp.
    assert stamped_page(text) == (text, stamp)
    assert stamped_page(PAGE.format("two"))[1] != stamp
    with pytest.raises(SystemExit, match="cgw-page"):
        stamped_page("<head></head>")


def test_the_site_page_carries_its_stamp_and_checks_it() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    assert tool("build_site").PAGE_STAMP.search(page)
    # The loader reads the manifest past every cache and compares stamps.
    assert 'fetch("wheel.json?t=" + Date.now()' in page
    assert "manifest.page !== stamp" in page


def test_the_local_server_asks_for_every_file_to_be_checked_again(
    tmp_path: Path,
) -> None:
    (tmp_path / "index.html").write_text("<p>hello</p>", encoding="utf-8")
    handler = partial(tool("serve_site").FreshHandler, directory=str(tmp_path))
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/index.html"
            with urllib.request.urlopen(url) as response:
                assert response.headers["Cache-Control"] == "no-cache"
                assert response.read() == b"<p>hello</p>"
        finally:
            server.shutdown()


def test_the_page_offers_a_style_and_an_easy_mode() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    # A style under the instrument, loaded as a design.
    assert '<select id="style"' in page
    assert "style_design(*json.loads(style_args))" in script
    # Easy mode hides the settings form, the editors' and the link to them,
    # and is kept in the browser.
    assert 'id="easy-mode"' in page
    assert (
        "body.easy .aside-form, body.easy .editor-settings, "
        "body.easy #jump .jump-settings { display: none; }"
    ) in page
    assert '"cncguitarwizard.easyMode"' in script
    # With the scale length under the style, a copy of the form's field.
    assert 'id="easy-options"' in page
    assert '"easy-options": ["scale_length"]' in script
    # And a Neck-through tick, with what such a neck cannot keep.
    assert 'id="easy-neck-through"' in page
    assert "neck_through_changes(json.loads(easy_values))" in script


def test_the_results_fit_a_phone_screen() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    # A file's links wrap and its name breaks after an underscore, so
    # Simulate stays in view in the results, which clip what runs past.
    narrow = page[page.index("@media (max-width: 900px)") :]
    assert "#files td.links { white-space: normal; }" in narrow
    assert "#files details.file-part > table { display: block; overflow-x: auto; }" in (
        narrow
    )
    assert 'name.replaceAll("_", "_<wbr>")' in script


def test_the_editor_draws_an_automatic_contour_as_it_is_cut() -> None:
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    assert "this.openPath(data.line || openCatmullRom(line.points, 8))" in script


def test_a_body_template_leaves_an_optional_value_empty_not_null() -> None:
    # Start from writes each of the template's shape fields into the form;
    # one it leaves out (jack_inset None) was written as the text "null",
    # which no field reads ("Not a number"), so no other body could load.
    import typing

    from cncguitarwizard.presets.body_shapes import (
        YOUR_DESIGN_TEMPLATES,
        YourDesignShape,
    )
    from cncguitarwizard.webapp import _form_type

    hints = typing.get_type_hints(YourDesignShape)
    assert _form_type(hints["jack_inset"]) == "optional_float"
    assert any(shape.jack_inset is None for _, shape in YOUR_DESIGN_TEMPLATES.values())
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert (
        'else if (type === "optional_float" && value === null) input.value = "";'
        in script
    )


def test_the_credit_links_to_ls_guitars() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    # In the header and the footer, at the right host over https.
    assert page.count('href="https://jounilappi.hopto.org/lsguitars/"') == 2
    assert "jouni.lappi.hopto.org" not in page


def test_the_footer_ends_with_the_thanks_in_small_print() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    footer = page[page.index("<footer>") : page.index("</footer>")]

    # The last thing in the footer, small.
    last = footer.rstrip().rsplit("\n", 1)[-1].strip()
    assert last.startswith('<small class="thanks">Special thanks to Kai Rankio')
    assert "Claude and GPT for providing the code" in last
    assert "footer .thanks { flex-basis: 100%; font-size: 11px; }" in page
