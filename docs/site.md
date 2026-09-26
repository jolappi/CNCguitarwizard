# Web app on GitHub Pages

The `site/` directory is a static web page that runs the real
`cncguitarwizard` package in the browser through
[Pyodide](https://pyodide.org) (CPython compiled to WebAssembly). Nothing
runs on a server, so it can be hosted on GitHub Pages as-is, and no code
had to be rewritten for it: the core package is pure, dependency-free
Python.

## What it does

1. Loads Pyodide from the jsDelivr CDN and installs the project wheel from
   `site/wheels/` with micropip.
2. Offers the instrument first — electric guitar or bass guitar — from the
   schema's `instruments` (`INSTRUMENT_OVERRIDES`); switching reloads the
   form with that instrument's defaults (after a confirmation when values
   were changed) and sends it as `prototype.instrument`. Then asks
   `cncguitarwizard.webapp.parameter_schema()` for every field of
   `Prototype001Parameters` and `MachiningParameters` and draws a grouped
   form from it. Changed values are highlighted; tuple fields are edited as
   JSON. The few fields a builder normally touches (scale, fret count,
   bridge, body thickness, tool and feeds…) are shown up front; the rest of
   each group sits behind an *Advanced* fold, marked `advanced` in the
   schema (`_BASIC_FIELDS`, `_BASIC_VARIANT_FIELDS` in `webapp.py`), with a
   page-wide checkbox to open them all. A field whose type is a union of
   kinded dataclasses — the bridge, the body shape —
   becomes a dropdown of kinds with the chosen kind's own fields beneath
   it (`variant` in the schema). Choosing the body shape "Your design"
   opens a drawing panel above the results: the outline's control points
   are handles to drag (double-click the outline to add one, Alt-click or
   right-click to remove one; *Start from* + *Load* replaces the drawing
   with a template — Design by Jone, Les Paul, Stratocaster or Jackson RR
   style — and its cavity placements), drawn
   over the neck, pocket, pickup and bridge routes and dashed rear
   cavities that `webapp.body_editor_layout()` lays out from the other
   settings. The control cavity (carrying its pots), each pot, the switch
   cavity, each neck bolt (dashed: drilled from the back) and the jack can
   be dragged too, and the pickup routes slide
   along the neck; a drop moves the fields that place them
   (`control_shift`, `pot_offsets`, `switch_*`, `neck_bolts`, `jack_*`,
   `body_*_pickup_offset`) and the layout is fetched again. The neck, its
   pocket and the bridge follow the neck and scale and stay put. The
   panel reports the body's size
   and any feature left outside the outline, and writes the points into
   the shape's `control_points` field. Likewise, choosing
   `headstock_outline` "drawn" opens a headstock panel: both edges are
   handle chains from the shoulder to the tip (the tip handles set the
   length), drawn over the fixed tuner holes of the chosen style with a
   keep-out circle `tuner_edge_offset` round each; the panel names any hole
   the edge comes too close to, and writes `headstock_bass_edge` /
   `headstock_treble_edge` (`webapp.headstock_editor_layout()` supplies
   the holes and the fitted start edges).
3. On **Build** runs the build in stages — `start_build()`, then
   `advance_build()` once per stage of `workflows.Prototype001Build`
   (geometry, body, neck and fretboard toolpaths, cover plates, G-code,
   FreeCAD script),
   then `finish_build()` — repainting a progress bar and a spinning Build
   button between stages, since Pyodide runs Python on the page's own
   thread. Everything lands in Pyodide's in-memory file system and comes
   back as text.
4. Shows the whole-instrument plan view, the three toolpath plots, download
   links for the FreeCAD script (`.py` and `.FCMacro`), every `.nc`
   program (body, electronics, neck, fretboard and one per cover plate), the SVG plots and `build.json`, and a summary with stock size
   and time estimates. Each `.nc` row also has a *Simulate* button: it
   copies that program to the clipboard and opens
   [NC Viewer](https://ncviewer.com) in a panel below, where pasting into
   the editor (or dropping the downloaded file) runs the simulation — the
   viewer has no URL or message API a page could feed directly.

FreeCAD cannot run in a browser, so `.FCStd` and STEP are made locally:
download `Prototype001_freecad.py` and run
`freecadcmd Prototype001_freecad.py` (or open the `.FCMacro` in FreeCAD).
The script writes its outputs next to wherever it is executed.

## Building and previewing locally

```bash
python tools/build_site.py
python -m http.server 8765 --directory site
```

Then open <http://localhost:8765>. `tools/build_site.py` builds the wheel
into `site/wheels/` and writes `site/wheel.json`, both git-ignored. The
page needs to be served over HTTP (not opened as a file) because Pyodide
fetches the wheel.

`wheel.json` carries a build id (a hash of the wheel and `app.js`). The page fetches it
uncached and appends the id to the `app.js` and wheel URLs, so after a
rebuild a plain reload always gets the matching script and wheel — no
hard refresh needed. The status line shows the build id that is running.

## Deployment

`.github/workflows/pages.yml` builds the wheel and publishes `site/` on
every push to `main`. Enable Pages once in the repository settings
(*Settings → Pages → Source: GitHub Actions*); the workflow's `deploy`
job prints the page URL.

## Files

| File | Purpose |
| --- | --- |
| `site/index.html` | Layout and styling |
| `site/app.js` | Pyodide bootstrap, form generation, build, downloads, NC Viewer simulator panel |
| `src/cncguitarwizard/webapp.py` | Schema and build glue called from the page |
| `src/cncguitarwizard/render/svg/plan_view.py` | The plan-view SVG |
| `tools/build_site.py` | Wheel build and manifest |
