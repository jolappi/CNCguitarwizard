"""Tests for the web app's build and local server (``tools/``): a new
build must reach the browser, not a cached copy of the last."""

import importlib.util
import re
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


def test_the_app_layout_is_tried_beside_the_classic_page() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")
    build = (ROOT / "tools" / "build_site.py").read_text(encoding="utf-8")

    # Laid over the page once app.js runs, versioned with it.
    assert '"desktop.js?v=" + version' in page
    assert 'digest.update((SITE / "desktop.js").read_bytes())' in build
    # A new visitor gets the application like UI: only "classic", asked or
    # kept, chooses the Classic UI, and its View menu goes there.
    assert '(asked || stored(LAYOUT) || "desktop") === "classic"' in layout
    assert '"Classic UI"' in layout and '"Application like UI"' in layout
    # app.js shows the page what it scrolls to is on.
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    assert "window.cncgwLayout?.reveal(element)" in script


def test_the_app_ui_finds_a_setting_from_anywhere_with_its_pages() -> None:
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    # In the menu bar, "/" going to it before app.js sends it to the form.
    assert 'findBox.placeholder = "Find a setting… (/)"' in layout
    assert "bar.append(spacer, findBox, barBuild)" in layout
    assert "event.stopImmediatePropagation();" in layout
    # A setting's control set right there, and links to its pages.
    assert "setControlValue(original" in layout
    assert '"body-editor-options": ["body", "Design › Body"]' in layout
    assert "`Settings › ${group.dataset.title}`" in layout


def test_the_app_ui_has_pages_for_the_neck_and_the_fretboard() -> None:
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    assert '{ id: "neck", title: "Neck", parts: ["#desk-neck"] }' in layout
    assert '{ id: "fretboard", title: "Fretboard", parts: ["#desk-fretboard"] }' in (
        layout
    )
    # Their drawings from Python, their settings copies of the form's.
    assert "from cncguitarwizard.webapp import part_views" in layout
    assert "EDITOR_FIELDS[`${id}-page-options`]" in layout


def test_every_design_page_has_a_reset_of_its_own() -> None:
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    for page in ("design", "body", "neck", "headstock", "fretboard", "inlays"):
        assert f'["{page}", ' in layout[layout.index("const resetButtons") :]
    # As a group's Reset does: asking first, a variant's kind first.
    assert "await askConfirm(`Put ${which} of ${title} ${back}`)" in layout
    assert 'byId("reset").textContent = "Reset everything";' in layout


def test_a_tip_a_day_in_the_footer_or_the_status_bar() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    tips = script[
        script.index("const TIPS = [") : script.index("];", script.index("const TIPS"))
    ]
    # One sentence each, the builder's own among them.
    lines = re.findall(r'^  "(.*)",$', tips, re.MULTILINE)
    assert len(lines) >= 20 and all(line.endswith((".", "?")) for line in lines)
    assert "always use 24 V: two V23GA batteries in series." in tips
    assert "Oil your strings, at least where they cross the nut and the bridge." in tips
    # The same all day: picked by the date, not at random.
    assert "TIPS[(day * 7919) % TIPS.length]" in script
    # In the footer, before the thanks; the app layout's status bar.
    assert (
        '<span id="tip-of-the-day" class="tip" hidden></span>\n  <small class="thanks">'
        in page
    )
    assert (
        'statusBar.append(where, status, byId("tip-of-the-day"), progressBox);'
        in layout
    )


def stl_triangles(data: bytes) -> int:
    """Return how many triangles an STL file holds, checking it is whole."""
    if data.startswith(b"solid") and b"facet" in data[:400]:
        text = data.decode("ascii")
        assert text.rstrip().splitlines()[-1].startswith("endsolid")
        return text.count("endfacet")
    count = int.from_bytes(data[80:84], "little")
    assert len(data) == 84 + 50 * count
    return count


def test_the_bonus_offers_its_files_with_english_names() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")
    bonus = ROOT / "site" / "bonus"

    # Every file there is offered, and every link finds its file.
    links = re.findall(r'href="bonus/([^"]+)"', page)
    files = sorted(path.name for path in bonus.iterdir())
    assert sorted(links) == files
    # The dust shoe's three parts, the hose leaving forward or sideways.
    for part in ("collar", "housing", "brush_sleeve"):
        for way in ("hose_forward", "hose_sideways"):
            stl = bonus / f"dust_shoe_{part}_{way}.stl"
            assert stl_triangles(stl.read_bytes()) > 1000
    # The source in English too: its parts and messages.
    source = (bonus / "dust_shoe_makita_rt0702c_ttc_h40.scad").read_text("utf-8")
    assert 'part = "assembly"; // [assembly, collar, housing, sleeve]' in source
    for finnish in ("kaulus", "kotelo", "holkki", "kokoonpano", "sisaan"):
        assert finnish not in source and finnish not in " ".join(files)
    # In the application like UI, a page of its own under its own menu.
    assert '{ id: "bonus", title: "Bonus", parts: ["#bonus"] }' in layout
    assert '["Bonus", () => [' in layout
    assert '<a href="#bonus">Bonus</a>' in page


def test_dark_mode_is_the_default_set_before_the_page_paints_never_printed() -> None:
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")

    # Set in the head, before the styles, from what this browser kept.
    assert page.index('localStorage.getItem("cgw-theme")') < page.index("<style>")
    # Dark unless light is chosen.
    assert 'if (theme !== "light") document.documentElement' in page
    # The dark colours are the tokens', on screen only.
    assert '@media screen {\n    :root[data-theme="dark"] {' in page
    assert "--panel: #27231f;" in page and "color-scheme: dark;" in page
    # Its switch, in the Classic UI's header and the View menu.
    assert '"Dark mode"' in layout and "setDark(!isDark())" in layout


def test_a_build_says_its_steps_likely_times() -> None:
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")
    layout = (ROOT / "site" / "desktop.js").read_text(encoding="utf-8")
    workflow = (
        ROOT / "src" / "cncguitarwizard" / "workflows" / "prototype001.py"
    ).read_text(encoding="utf-8")

    # app.js names every step as the build starts.
    assert 'new CustomEvent("cgw-build-stages", { detail: stages })' in script
    # Every step of the build in the browser has a typical time (FreeCAD
    # runs only in a local build).
    typical = layout[layout.index("const TYPICAL_STEPS = {") :]
    typical = typical[: typical.index("};")]
    for label in re.findall(r'\(\s*"([^"]+)",\s*self\._', workflow):
        if label != "Running FreeCAD":
            assert f'"{label}":' in typical, label


def test_the_volute_is_drawn_in_the_headstock_editor() -> None:
    script = (ROOT / "site" / "app.js").read_text(encoding="utf-8")

    assert "if (layout.volute) this.drawVolute(layout.volute);" in script
    # Its three lines (crest and both ends), each into its own setting.
    assert 'headstock: "Where the volute ends in the headstock\'s back"' in script
    assert "[data-name='${this.layout.volute.lines[name].field}']" in script
    # Its ends stay on the centre line; the other half mirrors the drawn.
    assert "const ny = onCentre ? 0 : Math.max(0, y0 + y - start[1]);" in script
    editor = script[script.index('"headstock-editor-options": [') :]
    assert '"headstock_pointed_volute"' in editor[: editor.index("],")]
    # Seen from behind and above as it is drawn, a moment after the editor.
    assert "from cncguitarwizard.webapp import volute_view" in script
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert 'id="headstock-editor-volute" class="volute-view-box" hidden' in page
