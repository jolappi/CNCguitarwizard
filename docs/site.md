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
   page-wide checkbox to open them all. The settings that shape an
   editor's drawing sit in that editor's own pane instead
   (`EDITOR_FIELDS` in `app.js`): the pickup layout, controls, pickup
   selector and battery box in the body editor, the tuner layout
   (`headstock_style`) in the headstock editor. Each is a copy of the
   form's field, whose row in the form is hidden; the field itself is
   what is saved, loaded and built. Choosing a locking nut wider
   than the neck (`locking_nut` "r3") widens `nut_width` to it, to the
   next half millimetre (`locking_nut_widths` in the schema). A field whose type is a union of
   kinded dataclasses — the bridge — becomes a dropdown of kinds with the
   chosen kind's own fields beneath it (`variant` in the schema). The body
   shape offers only its drawn kind (`_FORM_KINDS`), so it has no dropdown:
   the body is always drawn, starting from the Design by Jone template on
   a guitar and the Jazz Bass style one on a bass (a saved design that
   names the traced `design_by_jone` body loads as that template). A
   drawing panel above the results edits it: the outline's control points
   are handles to drag (click the outline to add one, Alt-click or
   right-click to remove one; *Start from* shows the template the drawing
   is ("Your own drawing" once its outline has been changed); choosing
   one and *Load* replaces the drawing with that template — Design by Jone, Les Paul, Stratocaster or Jackson RR
   style or Jazz Bass style (mockups, not the original outlines) — and its cavity placements), drawn
   over the neck, pocket, pickup and bridge routes and dashed rear
   cavities that `webapp.body_editor_layout()` lays out from the other
   settings. The control cavity (carrying its pots), each pot, the switch
   cavity, the battery box (when `body_battery_box` is on), each neck bolt
   (dashed: drilled from the back) and the jack can be dragged too, and the pickup routes slide
   along the neck. Shift-dragging the control cavity (with its cover and
   pots, or the Tele plate), the battery box or the jack turns it about
   its centre (the jack about its socket) instead; round cavities only
   move. A feature dropped wholly outside the outline asks whether to
   remove it: a pickup (the layout turns "custom" with that position
   empty, from `pickup_configurations` in the schema), the controls
   (`body_controls` "none"), the battery box, one of several pots or neck
   bolts; declined, it goes back. The switch cavity and the jack cannot go
   on their own and just move. A feature dropped on *Create NC file*
   (above the drawing) stays put and gets its own NC programs instead,
   zeroed at its centre, its cover plates included
   (`webapp.feature_programs`), listed there as downloads, each with a
   *Simulate* button that opens the NC Viewer panel right under the list
   (no build needed). The square handles at the control cover's two ends stretch or
   shrink the cavity and its cover from that end (`control_stretch`; the
   centre and the pots move half the drag, so the other end stays), and
   those at its two sides widen or narrow it (`control_stretch_across`). A
   drop moves the fields that place them
   (`control_shift`, `control_angle_degrees`, `control_stretch`,
   `control_stretch_across`,
   `pot_offsets`, `switch_*`,
   `battery_*`, `neck_bolts`, `jack_*`,
   `body_*_pickup_offset`) and the layout is fetched again. The jack's
   bore starts wherever its line meets the drawn outline and runs into the
   control cavity; the panel warns when it misses the cavity. The neck, its
   pocket and the bridge follow the neck and scale and stay put. The
   panel reports the body's size
   and any feature left outside the outline, and writes the points into
   the shape's `control_points` field. Likewise, with
   `headstock_outline` "drawn" (the default) a headstock panel is open:
   both edges are handle chains from the shoulder to the tip (the tip
   handles set the length; click an edge to add a handle, click the tip
   to shape it with one — `headstock_tip_points`, dragged out for a point
   or a round end, in for a notch; edges and tip are rounded curves
   through their handles, so a Stratocaster or Schecter style outline
   can be drawn — Alt-click or right-click one to remove it), drawn over the fixed tuner holes of the
   chosen style with a keep-out circle `tuner_edge_offset` round each; the
   panel names any hole the edge comes too close to. Until a handle is
   moved, `headstock_bass_edge` / `headstock_treble_edge` stay empty and
   the drawing follows the fitted outline (a changed style or length
   redraws it); the first edit writes them, and *Start over* empties them
   again (`webapp.headstock_editor_layout()` supplies the holes and the
   fitted start edges).
3. **Save design** downloads every setting as one JSON file on the user's
   own computer — the instrument, all `prototype` and `machining` values,
   the drawn body's `control_points` and the drawn headstock edges
   included (`{"format": "cncguitarwizard-design", "version": 1,
   "instrument", "prototype", "machining"}`). **Load design** opens such a
   file: it switches to the saved instrument, puts every value back into
   the form (variant kinds first, then their fields) and redraws the
   editors — the body editor from the loaded `control_points`, so a drag
   afterwards changes the loaded outline, not the start shape; settings
   this version does not know are skipped and listed,
   and a file that is not a design is refused. Nothing is stored on a
   server.
4. On **Build** runs the build in stages — `start_build()`, then
   `advance_build()` once per stage of `workflows.Prototype001Build`
   (geometry, body, neck and fretboard toolpaths, cover plates, G-code,
   FreeCAD script),
   then `finish_build()` — repainting a progress bar and a spinning Build
   button between stages, since Pyodide runs Python on the page's own
   thread. Everything lands in Pyodide's in-memory file system and comes
   back as text.
5. Shows the whole-instrument plan view (standing upright, headstock at
   the top, sized to fit the window), the three toolpath plots, download
   links for the FreeCAD script (`.py` and `.FCMacro`), every `.nc`
   program (body, electronics, neck, fretboard and one per cover plate), the SVG plots and `build.json`, and a summary with stock size
   and time estimates. The downloads come in one list per part — the
   model and report first, then body, neck, fretboard and covers — each
   program numbered in the order it is run (`build.json` gives it as the
   program's `step`) with its toolpath plot beneath it. Each `.nc` row also has a *Simulate* button: it
   copies that program to the clipboard and opens
   [NC Viewer](https://ncviewer.com) in a panel below, where selecting all
   in its editor (Ctrl/Cmd+A), pasting (Ctrl/Cmd+V) and pressing *Plot*
   (or dropping the downloaded file) runs the simulation — the
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
| `site/index.html` | Layout and styling; the intro heads the left column, and on a narrow screen (≤ 900 px) the intro comes first, then the buttons and instrument choice, the editors and the results, and the form last |
| `site/app.js` | Pyodide bootstrap, form generation, build, downloads, NC Viewer simulator panel |
| `src/cncguitarwizard/webapp.py` | Schema and build glue called from the page |
| `src/cncguitarwizard/render/svg/plan_view.py` | The plan-view SVG |
| `tools/build_site.py` | Wheel build and manifest |
