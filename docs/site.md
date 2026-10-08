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
2. Offers the instrument first — electric guitar, 7- or 8-string guitar,
   bass, 5-string bass, headless guitar or headless bass — from the
   schema's `instruments` (`INSTRUMENT_OVERRIDES`); switching reloads the
   form with that instrument's defaults (after a confirmation when values
   were changed — every yes/no question is asked in the page's own
   dialog, `askConfirm`, not `window.confirm`, which some embedded
   browsers answer unseen) and sends it as `prototype.instrument`. Then asks
   `cncguitarwizard.webapp.parameter_schema()` for every field of
   `Prototype001Parameters` and `MachiningParameters` and draws a grouped
   form from it. Changed values are highlighted; tuple fields are edited as
   JSON. The few fields a builder normally touches (scale, fret count,
   bridge, body thickness, tool and feeds…) are shown up front; the rest of
   each group sits behind an *Advanced* fold, marked `advanced` in the
   schema (`_BASIC_FIELDS`, `_BASIC_VARIANT_FIELDS` in `webapp.py`), with a
   page-wide checkbox to open them all. Each group's title says how many
   of its settings are changed from their defaults (`countChanged`: *Body
   · 3 changed*, an editor pane's included). A variant's fields (a drawn body,
   a bridge) take the instrument's own variant as their default, so a
   design loaded with its values shows nothing changed. *Find a setting…* above them
   (`applyFormFilter`) shows only the fields whose name or meaning (its
   hover text) holds every word typed, underscores read as spaces — a
   field in an editor's pane too, its row in the form back while
   searching — opening their groups and folds and leaving out the rest;
   emptied, every fold is as open as it was. *Show only the settings
   changed from their defaults* keeps, of those, the ones marked changed
   (an editor pane's too), refreshed as a value is changed or set back;
   when none is left the form says so (`filter-empty`). Each field is labelled in
   words (`fieldLabel`: `body_pickup_frame_direction` reads *Pickup frame
   direction*, the body's own fields dropping their `body_`), its name in
   the code, the saved designs and the help in brackets at the end of its
   hover text. While a field is selected its meaning shows under it too
   (`fieldHint`, the same text: for a touch screen, and help too long to
   hover over), in the form or an editor's *Settings*, gone when the
   focus leaves the fields. Hovering a field's row shows what
   it means (its name is underlined dotted): `webapp._field_help` takes it
   from the code's own documentation — a dataclass's `Args:` entries, an
   attribute docstring, the comment block above the field (and the fields
   after it that the block names, `truss_rod_step_*` style wildcards
   included), else the first block in the class that names it, cut to the
   sentences that do — with `field_help.FIELD_HELP` first: plain words for
   the settings shown up front and those the code leaves unexplained.
   Every field has one. The settings that change an
   editor's drawing sit above it in that editor's own pane instead,
   folded under *Settings (N)* (`details.editor-settings`, closed until
   clicked; it reads *· changed* when one of them is) (`EDITOR_FIELDS`
   in `app.js`), but the instrument-wide ones that
   change every drawing (scale, string count, handedness, nut and heel
   widths), which stay at the head of the form, and the fine sizes
   behind each group's *Advanced* fold: in the body editor the neck's
   joint, the pickup layout, each position's pickup and place and
   whether they follow a fan, the bridge (its kind; its own sizes stay in
   the form) and whether it follows a fan, controls, pickup selector,
   jack, pickguard, humbucker frames, arm contour and belly cut, carved
   and stepped top, engraving, battery box and the neck bolts' side —
   in two columns on a wide screen (1200 px and up); in the headstock
   editor the tuner layout (`headstock_style`) and its bass side, the
   headstock's length, the tuner holes' size, the nut's style
   (`nut_style`: on the shelf, in a slot, behind a zero fret) and a
   locking nut, which it draws too, the lettering, and the truss rod's
   adjustment, spoke wheel and cover; in the inlay editor the markers'
   style, frets, sizes, depth and edge margin and the fretboard's
   binding. A list (the marker frets) is passed on once it reads as JSON.
   Each editor's long how-to sits folded under its *How to
   edit …* line (`details.editor-help`: the design, the headstock, the
   inlays), closed until clicked. Each is a copy of the
   form's field, whose row in the form is hidden while the pane is shown
   (a fitted or headless headstock has no editor, so its settings are back
   in the form); the field itself is
   what is saved, loaded and built. Choosing a locking nut wider
   than the neck (`locking_nut` "r3") widens `nut_width` to it, to the
   next half millimetre (`locking_nut_widths` in the schema). A field whose type is a union of
   kinded dataclasses — the bridge — becomes a dropdown of kinds with the
   chosen kind's own fields beneath it (`variant` in the schema). Kinds
   not made for the instrument's string count (`min_strings` /
   `max_strings`) are hidden, and a kind's own `string_count` (a
   hardtail's holes, a Floyd Rose's or Kahler's size, single-string
   bridges) follows the instrument's, also when the kind is changed. An
   optional number left empty shows *auto*: the value is worked out (a
   Floyd Rose's widths from its string count). The body
   shape offers only its drawn kind (`_FORM_KINDS`), so it has no dropdown
   (its row stays hidden) and its own fields fold away under
   *body_shape — Advanced*:
   the body is always drawn, starting from the Design by Jone template on
   a guitar and the Jazz Bass style one on a bass (a saved design that
   names the traced `design_by_jone` body loads as that template). A
   drawing panel above the results edits it (*Turn upright* shows it
   standing, the neck up, turned a quarter clockwise — a view only, the
   drawing's frame and every drag as before; *Turn sideways* lays it back
   down, the default; the choice is kept in the browser,
   `cncguitarwizard.bodyUpright`, and the headstock and inlay editors stay
   as they are): the outline's control points
   are handles to drag (click the outline to add one, Alt-click or
   right-click to remove one; *Start from* shows the template the drawing
   is ("Your own drawing" once its outline has been changed); choosing
   one replaces the drawing with that template at once (*Load* loads it
   again; declined, the choice goes back) — Design by Jone, Les Paul, Stratocaster, Jackson RR,
   ESP LTD Alexi Hexed, Mockingbird, Telecaster, SG, Explorer, Flying V or Jazz Bass style
   (mockups, not the original outlines) — and its cavity placements;
   a template's own other values, the Alexi Hexed's pickup, controls, Floyd Rose and stepped top
   (`values` in the layout's templates), are set too, the confirmation naming them; what the
   template loaded before (or the one the drawing is) set that way, and is
   still as it left it, goes back to its default, so an Alexi Hexed's
   stepped top is not left on a Les Paul, while a value changed since is
   kept), drawn
   over the neck, pocket, pickup and bridge routes and dashed rear
   cavities that `webapp.body_editor_layout()` lays out from the other
   settings. The control cavity (carrying its pots), each pot, the switch
   cavity, the battery box (when `body_battery_box` is on), each neck bolt
   (dashed: drilled from the back) and the jack (none with the jack on a
   Jazz Bass plate) can be dragged too, and the pickup routes slide
   along the neck. Shift-dragging the control cavity (with its cover and
   pots, or the Tele plate), the battery box, the jack or a pickup turns
   it about its centre (the jack about its socket, a pickup about its own
   centre on the centreline, from `pickups` in the layout) instead,
   changing `control_angle_degrees`, `battery_angle_degrees`,
   `jack_direction_degrees` or the pickup's `body_*_pickup_angle`; round
   cavities only move. A feature dropped wholly outside the outline asks whether to
   remove it: a pickup (the layout turns "custom" with that position
   empty, from `pickup_configurations` in the schema), the controls
   (`body_controls` "none"), the battery box, one of several pots or neck
   bolts; declined, it goes back. The switch cavity and the jack cannot go
   on their own and just move. With `body_pickguard` on, the guard is drawn
   over the features with square handles at its control points; dragging
   one writes `pickguard_points`, and *Auto pickguard* empties them again
   (the automatic guard's style, `body_pickguard_style`, is chosen beside
   it). Choosing the controls in the pickguard (`body_controls`
   "pickguard") ticks `body_pickguard`; a drawn guard that does not cover
   them gives way to the automatic one, and the status line says so.
   With `body_pickup_frame` set (ring, horns or hook, beside the editor
   with `body_pickup_frame_direction`), every humbucker's frame is drawn
   dark over it — its opening, screws and the holes over the height screws
   cut out — with small round yellow handles at its points (`frames` in
   the layout), drawn over everything else so they drag beside the neck
   and the body's edge too; a frame cut back to fit (`adjusted`) is named
   in the status line. Dragging one writes that pickup's own
   `body_<position>_frame_points` (the handle taken back into the frame's
   own frame with the layout's `origin`, `along`, `across` and `stretch`),
   a click on its edge adds a point and Alt/Option- or right-click
   removes one (four at least); choosing a style again empties all three
   fields. A frame that does not fit is outlined red and the status line
   gives its reason. With `body_arm_contour_depth` set (also beside the
   editor), the line where the arm contour starts is drawn in green with
   round handles: dragging one writes `arm_contour_points`, a click on the
   line adds one, Alt- or right-click removes one, and *Auto arm contour*
   empties them again. The belly cut's line works the same, in blue, with
   `body_belly_cut_depth`, `belly_cut_points` and *Auto belly cut*. With `body_engraving` on (beside the editor too, with
   `body_engraving_seed`) the decorative engraving is drawn in blue lines,
   and *New pattern* sets a new random seed (turning the engraving on);
   *Reroll* beside `body_engraving_seed` (in the form and the editor's
   *Settings*, `withReroll`) sets one too. Dragging the guard by its edge moves all its points together (a click
   without a drag still adds one), or onto *Create NC file* makes its
   programs: its screw spots in the body zeroed on the guard, and
   `Cover_pickguard`.
   A feature dropped on *Create NC file*
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
   to shape it with one — `headstock_tip_points`, dragged out for a round
   nose, in for a notch; a tip corner dragged within 3 mm of the other
   meets it in a sharp point (`HeadstockPlan.pointed`), which then drags as
   one, Shift-drag parting the corners again; edges and tip are rounded curves
   through their handles, so a Stratocaster or Schecter style outline
   can be drawn — Alt-click or right-click one to remove it), drawn over the fixed tuner holes of the
   chosen style with a keep-out circle `tuner_edge_offset` round each; the
   panel names any hole the edge comes too close to. Until a handle is
   moved, `headstock_bass_edge` / `headstock_treble_edge` stay empty and
   the drawing follows the fitted outline (a changed style or length
   redraws it); the first edit writes them, and *Start over* empties them
   again (`webapp.headstock_editor_layout()` supplies the holes and the
   fitted start edges). With the truss rod adjusted at the headstock its
   cover is drawn over the dashed trough (`truss_cover` in the layout:
   outline, screws, trough, size, corners and why it does not fit), its
   style, length and width in the editor's pane with `truss_rod_adjustment`:
   dragging a square corner handle writes a drawn cover
   (`truss_rod_cover_style` custom, `truss_rod_cover_points` and `_screws`,
   the size it was drawn at), a click on its edge adds a corner and an
   Alt/Option- or right-click removes one, and the round handles past its
   far end and beside its widest side write `truss_rod_cover_length` and
   `_width`; choosing a style goes back to its own shape and size. A
   drawing its tuners no longer fit (a changed
   scale or nut moves an in-line row's posts) still opens, the holes too
   close named in red, so it can be mended by dragging or *Start over*;
   so does one whose edges cross (a figure eight) or whose fitted outline
   would narrow to nothing, and *Start over* works even when no drawing
   could be laid out. A neck chosen in *Start from* loads at once (*Load*
   loads it again; declined, the choice goes back), and the tuner and tip
   settings it does not set go back to their defaults (`resets`:
   `NECK_TEMPLATE_RESETS`), so none is left from another neck. *Start from* → *Load* sets a whole neck from
   `neck_templates` in the schema (`NECK_TEMPLATES`): the Telecaster neck's
   slotted nut, flat six-in-line headstock, drawn Telecaster outline and
   heel-adjusted truss rod, or the Stratocaster, Gibson style, Flying V,
   Explorer or Mockingbird neck (mockups traced from product photos): its
   headstock style, angle, drawn outline, tuner stations and truss rod.
   Below it the **inlay editor** (*Inlay design*) draws the first fret
   marker's space on the board, nut to the left, with the style's marker
   in it (`webapp.inlay_editor_layout()`, `InlayLayout.editable_points()`)
   and the whole board below with every marker as it is cut. Dragging a
   corner, clicking a side to add one or Alt-clicking (right-clicking) one
   to remove it writes `inlay_points` and switches `inlay_style` to
   `custom`: every marker becomes that shape fitted to its own fret space.
   A dashed line shows where the corners fit every marker
   (`custom_limits()`: 1 mm from the frets in the shortest space and from
   the edges where the board is narrowest), and a drag stops at it; the
   panel says at which fret a shape does not fit. *Start over* empties
   `inlay_points` (a block). *Start from* lists every marker style but a
   drawn one (`inlay_style`'s options, by their labels): one chosen is
   loaded at once (*Load* loads it again), its style set and a drawn
   marker let go of (asked first), so the editor shows its marker to draw
   on from there. *Export SVG* and *Import SVG* take the marker to another
   drawing program and back (see [Outline templates](render/03_svg_templates.md)):
   its corners are read back, a curve as corners within 0.05 mm of it,
   each held inside the dashed line, and the import's note stays at the
   head of the status line until the next change. `inlay_style`, `inlay_depth` and
   `inlay_block_edge_margin` sit in its pane.
3. **Save design** downloads every setting as one JSON file on the user's
   own computer — the instrument, the guitar's name, all `prototype` and
   `machining` values, the drawn body's `control_points` and the drawn
   headstock edges included (`{"format": "cncguitarwizard-design",
   "version": 1, "name", "instrument", "prototype", "machining"}`), named
   for the guitar (*Guitar name*, beside the instrument) when it has one. **Load design** opens such a
   file — the file chooser straight from the click (a browser opens one
   only while handling the click itself; Safari not once a dialog has been
   answered), the question whether to replace changed values once a file
   is chosen: it brings an older design's values up to date
   (`webapp.upgrade_design`: a `headstock_outline` "fitted" with no edges
   drawn, the default before the headstock editor, loads as "drawn", the
   same outline with the editor open; an `index_pin_diameter` of 6, the
   default before the dowels followed the tool, loads empty), switches to
   the saved instrument, puts every value back into
   the form (variant kinds first, then their fields) and redraws the
   editors — the body editor from the loaded `control_points`, so a drag
   afterwards changes the loaded outline, not the start shape; settings
   this version does not know are skipped and listed,
   and a file that is not a design is refused. Nothing is stored on a
   server. The design is kept in the browser too (`localStorage`,
   `cncguitarwizard.lastDesign`: `designDocument()` saved after every
   settled change and a change of the guitar's name) and put back when
   the page is loaded again (`restoreLastDesign`, upgraded as a loaded
   design is; the status says so unless it is the defaults); *Reset*
   starts afresh, and a design that cannot be put back is passed over.
   **Undo** and **Redo** (beside *Reset* — on a wide screen the form
   column stays in view while the drawings and results scroll, so they
   are always at hand there; on a narrow one each editor's pane has them
   too — or Ctrl/Cmd+Z and Ctrl/Cmd+Shift+Z / Ctrl+Y) step back and forward
   through the design's changes: `undoHistory` in `app.js` keeps every
   form value (`collectValues()`, the instrument included) once a change
   has settled — a drag in an editor (kept when it ends), a template, a
   removal, a field changed in the form, a reset, an instrument switch or
   a loaded design — up to 100 steps, and puts back only the values that
   differ (another instrument's form drawn first), redrawing the editors.
   One history serves the whole page; a button's tooltip names the fields
   its step changes, and a new change clears the redo steps. In a text
   field the keys keep the browser's own undo of the typing.
   Every editor's drawing zooms (`enableZoom`): Ctrl/Cmd+wheel, or a
   trackpad's pinch, about the pointer, up to 20 times; zoomed in, a drag
   on the background moves it and a double-click there fits the whole
   drawing again; the zoom outlasts a redraw (`begin`), the plain wheel
   scrolls the page as ever, and every handle works as before.
   The editors' button rows keep to one line: their templates' four
   buttons sit in a *File ▾* menu (`details.menu`, closing once one is
   chosen or on a click elsewhere), and the body editor's *Auto
   pickguard*, *Auto arm contour*, *Auto steps* and *Auto belly cut*
   show only with a pickguard, an arm contour, a stepped top or a belly
   cut on, *New pattern* only with an engraving laid out at random (not
   a drawn one; `syncBodyButtons`).
   **Export SVG** and **Import SVG** in the body and headstock editors
   take an outline to another drawing program (Inkscape, Illustrator,
   Affinity Designer, a CAD program) and back; **Export DXF** and
   **Import DXF** in all three editors do the same for a CAD program
   (`webapp.outline_template(payload, part, "dxf")`,
   `<name>-<part>-outline.dxf`: the same layers by their ids, the outline
   on `cgwOutline` with a point on `cgwHandles` at every handle; any
   ASCII DXF is read, see [Outline templates](render/03_svg_templates.md#dxf-for-cad-programs)),
   the file chooser offering the kind asked for. Export downloads
   `webapp.outline_template()`'s template, `<name>-body-outline.svg` or
   `<name>-headstock-outline.svg`, drawn 1:1 in millimetres as the editor
   shows the design (mirrored for a left-handed build, a seven- or
   eight-string body widened): the layer *Outline* holds the outline as
   one path of Bézier curves with a node at every handle (the body's
   Catmull-Rom loop and the headstock's edges and tip convert exactly);
   the layer *Reference*, locked, what it is drawn round — the neck,
   pocket, routes, cavities, jack, centreline and bridge line, or the
   neck, nut, tuner holes (dashed, the edge's clearance round them),
   centreline, truss-rod cover and lettering — and three red registration
   marks; a body's and a headstock's template also have a layer *Pattern*
   with the engraving there is (none, the pattern's lines, or the lines
   drawn on the headstock face) to draw on.
   Import reads a file chosen from the click (`outline-file`) with
   `webapp.import_outline()`: `drawings.read_svg_shapes` reads any SVG
   (paths with every command, arcs included, rects, circles, ellipses,
   lines, polylines and polygons, in groups and layers with any
   transform, in any unit), the marks place the drawing to the
   millimetre whatever the program did to it (its page, its position, 72
   or 96 pixels to the inch — the message says by how much it was
   scaled), and the outline is the path still named `cgwOutline`, else the
   largest closed shape outside the reference layer (an outline drawn
   anew; its ends may be 3 mm apart). It becomes the editor's own handles,
   every one on the drawn line: the drawing's own nodes first, and more
   where the editor's curve strays more than 0.25 mm from it (a body span
   is halved, its neighbours too where they would be left over two and a
   half times as long; a headstock edge or tip gets a point where it
   strays most) — a polyline's nodes, closer than 8 mm on average, are no
   handles. A headstock's two edges end at one distance from the nut, the
   tip line, and its tip runs across from one edge's end to the other's;
   the tip line is the first that draws the outline within the tolerance
   of: a pair of nodes at one distance on the two sides (the template's
   own corners), where each side turns to run more across than along
   (45°), and back from the far end a millimetre at a time — or the
   closest; corners meeting make a pointed tip, and a tip that turns back
   across the headstock (a hook) is refused, as is a file without its
   marks or a closed outline. An outline exported and read back unchanged
   comes back exactly as it was. A body's pattern — its *Pattern* layer,
   any shape drawn beside the outline outside it, and any picture pasted
   in (a PNG kept in the file, its dark shapes traced into outlines) —
   where it was changed (read with every point and compared with the
   engraving there was), becomes the drawn engraving
   (`body_engraving_pattern` "drawn", `body_engraving_lines`, thinned to
   within 0.05 mm, `body_engraving` on), set in the form as if chosen
   there; emptied, it switches the engraving off; taken out of the file,
   or left as it was, it leaves the engraving alone; the message counts
   the shapes beside the outline and the pictures traced, and says why a
   picture was left out (a JPEG, a linked file). A headstock's is read
   the same way into the lines engraved on its face
   (`headstock_engraving_lines`, engraved with the lettering as deep as
   `headstock_engraving_depth`; emptied, none), and the headstock editor
   draws them in blue, saying when they run where the lettering may not.
   The import is one step to undo; the
   editor's status says how many handles it made, how close they keep,
   and then what does not fit (a feature outside the body, a tuner hole
   too near the edge) — the import's own note (`notice`) on a line of its
   own above it until the next change in the editor, and what does not
   fit in bold red (`showEditorStatus`, every editor's status).
4. On **Build 3D and CNC files** (or Ctrl/Cmd+Enter anywhere on the page,
   a field being typed in too) runs the build in stages — `start_build()`, then
   `advance_build()` once per stage of `workflows.Prototype001Build`
   (geometry, body, neck and fretboard toolpaths, cover plates, G-code,
   FreeCAD script),
   then `finish_build()` — repainting a progress bar and a spinning Build
   button between stages, since Pyodide runs Python on the page's own
   thread. Everything lands in Pyodide's in-memory file system and comes
   back as text.
5. Shows the result first, as soon as it is done (`#output`, the first
   thing in the right-hand column, above the editors; on a narrow screen
   straight under the build button and instrument choice, an error in
   the same place, and the page scrolls to either when it arrives out of
   view, `bringIntoView`; once the design changes after a build, a note
   above the result says its files are no longer the design's, with
   *Build again*: `builtFrom`, `markStale`, until the design is as built
   again): the summary with stock size
   (a fretboard blank's carrier on a row of its own, `fretboard_carrier_thickness`;
   the index pins' places only for a blank that has them) and the
   programs in one row — how many, about how long at the set feeds —
   first, each program's tool, time and cutting in the fold *Every
   program* below it (`#summary-programs`); then the download
   links for the FreeCAD script (`.py` and `.FCMacro`), every `.nc`
   program (body, electronics, neck, fretboard, the nut-slot jig and one per cover plate), the SVG plots, the DXF outlines
   (`Prototype001_plan.dxf`, `Prototype001_covers.dxf`; see [DXF](render/02_dxf.md)) and `build.json`;
   then the whole-instrument plan view (standing upright, headstock at
   the top, sized to fit the window; the nut drawn on its seat, bone white
   or dark for a locking nut, a board that runs on under it reaching on
   behind it) and the toolpath plots, one at a time, chosen from a list by part
   (each program by its step, the body's top first) or stepped through
   with the arrows beside it (`toolpath-choice`). The downloads come in one fold per part, closed
   until opened (its title says how many programs) — the
   model and report first, then body, neck, fretboard, the inlay pieces, the nut jig and covers — each
   program numbered in the order it is run (`build.json` gives it as the
   program's `step`), its toolpath plot a *Plot* link on its row. Each `.nc` row also has a *Simulate* button: it
   copies that program to the clipboard and opens
   [NC Viewer](https://ncviewer.com) in a panel below, where selecting all
   in its editor (Ctrl/Cmd+A), pasting (Ctrl/Cmd+V) and pressing *Plot*
   (or dropping the downloaded file) runs the simulation — the
   viewer has no URL or message API a page could feed directly.
   *Download all NC files (.zip)* gives every program in one ZIP named
   for the guitar (`<Guitar name>.zip`; `webapp.nc_archive` packs the last
   build's programs in Python): a folder named for the guitar, one folder
   a part inside it, each program numbered in running order
   (`Neck/02_Neck_top.nc`), and a `README.txt` listing them with their
   tools and run times. The name is made safe for a file name
   (`webapp.archive_name`: letters, digits, spaces, dots, dashes and
   underscores stay).

FreeCAD cannot run in a browser, so `.FCStd` and STEP are made locally:
download `Prototype001_freecad.py` and run
`freecadcmd Prototype001_freecad.py` (or open the `.FCMacro` in FreeCAD).
The script writes its outputs next to wherever it is executed. Or save
the design (*Save design*) and build it all locally from a clone with
`python -m cncguitarwizard build-prototype001 --design my_guitar.json
--output build/my_guitar`: the G-code, DXF, FCStd and STEP together.

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
| `site/index.html` | Layout and styling; the *Build* button on a row of its own, as wide as the column; the intro heads the left column and a build's result the right one, above the editors; on a narrow screen (≤ 900 px) the intro comes first, then the buttons and instrument choice, the build's result, the editors, and the form last |
| `site/app.js` | Pyodide bootstrap, form generation, build, downloads, NC Viewer simulator panel |
| `src/cncguitarwizard/webapp.py` | Schema and build glue called from the page |
| `src/cncguitarwizard/render/svg/plan_view.py` | The plan-view SVG |
| `tools/build_site.py` | Wheel build and manifest |
