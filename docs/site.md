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
2. Asks `cncguitarwizard.webapp.parameter_schema()` for every field of
   `Prototype001Parameters` and `MachiningParameters` and draws a grouped
   form from it. Changed values are highlighted; tuple fields are edited as
   JSON. The few fields a builder normally touches (scale, fret count,
   bridge, body thickness, tool and feeds…) are shown up front; the rest of
   each group sits behind an *Advanced* fold, marked `advanced` in the
   schema (`_BASIC_FIELDS`, `_BASIC_BRIDGE_FIELDS` in `webapp.py`), with a
   page-wide checkbox to open them all. A field whose type is a union of
   kinded dataclasses — the bridge —
   becomes a dropdown of kinds with the chosen kind's own fields beneath
   it (`variant` in the schema).
3. On **Build** runs the build in stages — `start_build()`, then
   `advance_build()` once per stage of `workflows.Prototype001Build`
   (geometry, body, neck and fretboard toolpaths, G-code, FreeCAD script),
   then `finish_build()` — repainting a progress bar and a spinning Build
   button between stages, since Pyodide runs Python on the page's own
   thread. Everything lands in Pyodide's in-memory file system and comes
   back as text.
4. Shows the whole-instrument plan view, the three toolpath plots, download
   links for the FreeCAD script (`.py` and `.FCMacro`), the three `.nc`
   programs, the SVG plots and `build.json`, and a summary with stock size
   and time estimates.

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

`wheel.json` carries a build id (the wheel's hash). The page fetches it
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
| `site/app.js` | Pyodide bootstrap, form generation, build, downloads |
| `src/cncguitarwizard/webapp.py` | Schema and build glue called from the page |
| `src/cncguitarwizard/render/svg/plan_view.py` | The plan-view SVG |
| `tools/build_site.py` | Wheel build and manifest |
