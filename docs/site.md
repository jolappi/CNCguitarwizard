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
   browsers answer unseen) and sends it as `prototype.instrument`. Under
   it, *Style* offers the styles made for that instrument (the schema's
   `styles`, `presets.styles.STYLES`; hidden where there are none): a
   whole instrument in one choice, the quick way in among the many
   settings — Design by Jone, a Fender Stratocaster or Telecaster, a
   Gibson Les Paul, SG, Flying V or Explorer, a Jackson RR, an ESP LTD
   Alexi Hexed, a B.C. Rich Mockingbird, a Music Man Axis or a Fender
   Jazz Bass style. The
   Fender, Gibson and Jackson ones place their controls, jack and pickups
   as on the original (measured from photos and the user's Stratocaster
   drawing; see [Body shapes](geometry/12_body.md#body-shapes)): a '52
   Telecaster's plate and side jack and its bridge pickup slanted 16°, a
   vintage Stratocaster's guard, controls and jack plate, a Les Paul's
   staggered pots, an SG's jack in the top, an Explorer's row of pots and
   a Rhoads' toggle among its pots. The Jackson RR and Alexi Hexed styles
   have their pointed headstocks (the `jackson` and `alexi` neck
   templates, on six strings), with the laminated neck blank they need on
   a neck run through the body (the style's machining,
   `InstrumentStyle.machining_values`, in the design's `machining`). The
   SG and Mockingbird styles bevel their edges all round
   (`body_top_bevel_width`, `body_back_bevel_width`), rounding over 5 mm
   the stretches their templates' `top_round_points` /
   `back_round_points` mark: the SG's tail (and on the back its control
   cavity's lower bout), the Mockingbird's neck end and tail. The SG style
   has its small guard (`body_pickguard_style` "sg_small", or the
   batwing) and its humbuckers in rings; a guard meets the humbucker
   frames with no wood between them, and the body editor draws it as cut.
   Choosing one (asked first when values were changed) loads
   `webapp.style_design(instrument, style, name)` as a saved design is
   loaded (`applyDesign`, then `repairDesign`): every setting back to the
   instrument's defaults, then the style's own, the guitar's name kept; a
   new form (another instrument, *Reset*, a design loaded) shows none
   chosen (`showStyles`, `loadStyle`). *Easy mode* under it hides the long
   settings form, the editors' *Settings* and the *Settings* jump link
   (`body.easy`, `setEasyMode`): the instrument, its style, the guitar's
   name, the scale length (a copy of the form's field, `easy-options` in
   `EDITOR_FIELDS`, shown only in easy mode), the drawings, *Build* and the
   result stay — choose a style and build. It is kept in the browser (`cncguitarwizard.easyMode`), off
   until chosen, and `/` (Find a setting) leaves it. Its *Neck-through*
   tick (`easy-neck-through`) sets `neck_joint` to `neck_through` with what
   such a neck cannot keep (`webapp.neck_through_changes`: a round heel
   end made square, a neck plate made ferrules, a rod adjusted at the heel
   with no spoke wheel adjusted at the headstock), so any style builds
   neck-through; cleared, it puts them back (or the joint to its default),
   and it follows the form's joint. Then asks
   `cncguitarwizard.webapp.parameter_schema()` for every field of
   `Prototype001Parameters` and `MachiningParameters` and draws a grouped
   form from it. Changed values are highlighted; tuple fields are edited as
   JSON. A value that cannot be read (not a number, broken JSON) is marked
   red once it is given — Enter, or leaving the field — not while it is
   still being typed, the reason in its hint (`valueProblem`), and the mark
   goes as soon as it reads again; an editor's copy passes only a value
   that reads on to its form field, and Build names the field it stops
   at (*Thickness (body_thickness): Needs a number*), marks it, and
   offers *Go to Thickness* (`FieldError`, `goToField`: its group and
   folds opened, a search that leaves it out cleared, or its copy in an
   editor's *Settings* while that editor is shown; then selected). The few fields a builder normally touches (scale, fret count,
   bridge, body thickness, tool and feeds…) are shown up front; the rest of
   each group sits behind an *Advanced* fold, marked `advanced` in the
   schema (`_BASIC_FIELDS`, `_BASIC_VARIANT_FIELDS` in `webapp.py`), with a
   page-wide checkbox to open them all. An open group's title stays in
   sight at the top while its fields scroll by (sticky, in the form's own
   column on a wide screen). Each group's title says how many
   of its settings are changed from their defaults (`countChanged`: *Body
   · 3 changed*, an editor pane's included), and *Show only the settings
   changed* how many there are in all (`changed-total`). A group with
   changes has *Reset 3 to defaults* at its top (`resetGroup`): after
   asking, its changed settings go back to their defaults — a variant's
   kind first, its own fields with it — as one Undo step, and the
   editors redraw as after an undo (`redrawEditors`). The groups opened by hand
   are kept in the browser (`cncguitarwizard.openGroups`; not those a
   search opens), so a reload, another instrument or a loaded design
   opens the same ones; with none kept, *Body* and *Machining* open. A variant's fields (a drawn body,
   a bridge) take the instrument's own variant as their default, so a
   design loaded with its values shows nothing changed. *Find a setting…* above them
   (`applyFormFilter`) shows only the fields whose name or meaning (its
   hover text) holds every word typed, underscores read as spaces — a
   field in an editor's pane too, its row in the form back while
   searching — opening their groups and folds and leaving out the rest,
   the words found marked in the fields' names (`markWords`); emptied,
   every fold is as open as it was. `/` anywhere but a field
   goes to it (its text selected); Enter in it goes to the
   first setting found (its value selected, ready to be typed over), and
   Escape empties it. *Show only the settings
   changed from their defaults* keeps, of those, the ones marked changed
   (an editor pane's too), refreshed as a value is changed or set back;
   when none is left the form says so (`filter-empty`). Each field is labelled in
   words (`fieldLabel`: `body_pickup_frame_direction` reads *Pickup frame
   direction*, the body's own fields dropping their `body_`), its name in
   the code, the saved designs and the help in brackets at the end of its
   hover text. While a field is selected its meaning shows under it too
   (`fieldHint`, the same text: for a touch screen, and help too long to
   hover over), in the form or an editor's *Settings*, gone when the
   focus leaves the fields; a field changed from its default shows the
   default there too, with *Reset to default* (`defaultLine`; an
   editor's copy passes the reset on to its form field as any change, so
   Undo takes it back). The wheel over a selected number field scrolls
   the page (or the column it is in) and leaves its value alone
   (`scrollPastNumber`), where the browser would step it unseen; its
   arrow keys step by 1 as ever, by 10 with Shift and by 0.1 with
   Alt/Option (a whole-number field by 1). Hovering a field's row shows what
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
   and stepped top, engraving, battery box, the neck bolts' side and the
   strap guide —
   in two columns on a wide screen (1200 px and up); in the headstock
   editor the tuner layout (`headstock_style`) and its bass side, the
   headstock's length, the tuner holes' size, the nut's style
   (`nut_style`: on the shelf, in a slot, behind a zero fret) and a
   locking nut, which it draws too, the lettering, and the truss rod's
   adjustment, spoke wheel and cover; in the inlay editor the markers'
   style, frets, sizes, depth and edge margin and the fretboard's
   binding and blind fret slots. A list (the marker frets) is passed on once it reads as JSON.
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
   ESP LTD Alexi Hexed, Music Man Axis, Mockingbird, Telecaster, SG, Explorer, Flying V or Jazz Bass style
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
   cavity, the battery box (when `body_battery_box` is on), the strap
   guide (when `body_strap_guide` is on: its plate and screw pilots,
   dashed), each neck bolt
   (dashed: drilled from the back) and the jack (none with the jack on a
   Jazz Bass plate) can be dragged too, and the pickup routes slide
   along the neck. Shift-dragging the control cavity (with its cover and
   pots, or the Tele plate), the battery box, the jack, the strap guide or
   a pickup turns
   it about its centre (the jack about its socket, a pickup about its own
   centre on the centreline, from `pickups` in the layout) instead,
   changing `control_angle_degrees`, `battery_angle_degrees`,
   `jack_direction_degrees` or the pickup's `body_*_pickup_angle`; the
   strap guide's drag or turn sets all three of `strap_guide_offset`,
   `strap_guide_y` and `strap_guide_angle_degrees` from where the layout
   draws it (`strap_guide`), since they may be empty; round
   cavities only move. A feature dropped wholly outside the outline asks whether to
   remove it: a pickup (the layout turns "custom" with that position
   empty, from `pickup_configurations` in the schema), the controls
   (`body_controls` "none"), the battery box, the strap guide, one of
   several pots or neck
   bolts; declined, it goes back. The switch cavity and the jack cannot go
   on their own and just move. With `body_pickguard` on, the guard is drawn
   over the features with square handles at its control points; dragging
   one writes `pickguard_points`, and *Auto pickguard* empties them again
   (the automatic guard's style, `body_pickguard_style`, is chosen beside
   it). Choosing the controls in the pickguard (`body_controls`
   "pickguard") ticks `body_pickguard`; a drawn guard that does not cover
   them gives way to the automatic one, and the status line says so.
   Neck bolts with no room where they are asked to go (one dragged past
   the cutaway, or a saved design's) are drawn there anyway, not moved
   out, and the status line says why in red (`problems` from
   `body_editor_layout`), so they can be dragged where they fit; the
   build refuses them meanwhile. An epoxy tray (`body_epoxy_tray_depth`,
   beside the editor) is drawn amber under the features, its walls round
   the openings in wood.
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
   `body_belly_cut_depth`, `belly_cut_points` and *Auto belly cut*, the leg
   contour's in teal with `body_leg_contour_depth`, `leg_contour_points`
   and *Auto leg contour*, and the
   heel relief's on the back where the neck joins, in plum, with
   `body_heel_relief` (a contour or a notch, beside the editor with its
   depth and `body_heel_relief_line`), `heel_relief_points` and *Auto
   heel relief* (a U round the heel, or with `pocket` the pocket's outline
   offset by the reach, either taking in the whole heel to the pocket's
   bass wall; or with `corner` a straight line
   slanting across the heel's treble corner, clear of a neck plate; where
   a plate leaves no corner beyond it the U is drawn and the status line
   says why); the relief reaches out past the heel on the treble side
   only: round the heel, by the pocket or drawn it takes in the whole heel
   to the pocket's bass wall, across the corner it stops at the centreline
   (a plate tilted on a bevel takes it across the neck to just past the
   plate). A line moved by hand stays as drawn whatever relief is
   chosen, and the status line says so; choosing `body_heel_relief_line`
   by hand (not a loaded design or an undo) goes back to that automatic
   line, as *Auto heel relief* does. An automatic line is drawn as it is
   cut (the layout's `line`), its handles spread evenly along it; moved,
   the line runs through the handles. The stretches of the edge a bevel
   all round leaves to the roundover (the shape's `top_round_points` /
   `back_round_points`, the layout's `round_points`) are drawn along the
   outline, the top's in orange and the back's dashed purple a little
   inside it, with square handles at their ends set in from the edge
   (clear of the outline's own handles) that slide along it; *Round top
   edge* / *Round back edge* (shown with that bevel) add one 60 mm long at
   the tail, and Alt-click or right-click on a handle takes its stretch
   away. With
   `body_neck_plate` (beside the editor: ferrules, a Fender style plate or
   an asymmetric one) the plate is drawn on the back in steel grey and its
   bolts stay at its holes, not dragged; on a `"bevel"` heel relief it
   tilts with it (a Tilt Joint): along the neck, or with `corner` toward
   the treble corner. With `body_engraving` on (beside the editor too, with
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
   can be drawn — Alt-click or right-click one to remove it), drawn over the tuner holes of the
   chosen style with a keep-out circle `tuner_edge_offset` round each; the
   panel names any hole the edge comes too close to, or two holes with
   less than `tuner_hole_clearance` of wood between them. A dragged hole
   slides along its edge, kept as far in from it as it was, so the
   tuner's key stays out past the edge (Shift-drag puts it anywhere
   across), and along the neck between its side's neighbours
   (`startHoleDrag`); a dragged edge takes its holes along, each kept as
   far in from its edge as it was (`holeInsets`, `followEdges`). Either
   writes every hole's place to `tuner_hole_points` (see
   [Tuner layout](geometry/07_tuner_layout.md)). Changing the style, the
   string count or the style's tuner settings by hand (in the form or the
   pane) empties it, so the style lays the holes out again; *Start over*
   and a neck template do too, while a loaded design or an undo keeps what
   it sets. Until a handle is
   moved, `headstock_bass_edge` / `headstock_treble_edge` stay empty and
   the drawing follows the fitted outline (a changed style or length
   redraws it); the first edit writes them, and *Start over* empties them
   again (`webapp.headstock_editor_layout()` supplies the holes, the least
   wood between them and the fitted start edges). With the truss rod adjusted at the headstock its
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
   Explorer, Mockingbird or Music Man neck (mockups traced from product
   photos): its
   headstock style, angle, drawn outline, tuner stations and truss rod —
   the Stratocaster's with a round heel end (`neck_heel_end`), the others
   square.
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
   `inlay_block_edge_margin` sit in its pane. With the `runes` style each
   marker fret gets its own choice of rune above the drawing (`showRunes`,
   from the schema's `runes` and the layout's), each named with its glyph
   and what it stands for; a change writes them all to `inlay_runes`.
   *Random runes* picks one for every fret at random, no two the same
   (24 runes to choose from), and writes them there too.
   In every editor a drawn line can be made straight and a sharp drawing
   round. The curved lines — the body's outline, the pickguard, the
   humbucker frames, the arm contour, belly cut and heel relief lines and
   the headstock's edges and tip — round through their handles: a
   double-click on a handle makes it a sharp corner (drawn dark; again,
   round again), and a Shift-click on the line makes the span nearest the
   click straight, both its ends corners (again, curved again). A corner
   is stored as its point with a third item, `[x, y, "corner"]`
   (`spline.CORNER`): the curve leaves it toward the next point and comes
   in from the one before, so it runs straight between two
   (`closedCatmullRom`, `openCatmullRom` and `smoothCurve` as Python's
   `closed_catmull_rom`, `open_catmull_rom` and `SmoothCurve`). A tip
   corner is the edge's last handle, so a corner there makes the tip
   leave its edge sharp. The polygons — a stepped top's lines, a drawn
   truss-rod cover and a drawn inlay marker — are the other way round,
   straight between their corners: a double-click on a corner rounds the
   line through it (`[x, y, "round"]`, `spline.ROUND`: drawn as a circle,
   or filled pale), and a Shift-click on a side curves it, both its ends
   round (again, straight again; `drawnPolygon` as Python's
   `drawn_polygon`). A drag keeps a point's mark, and a press that does
   not move commits nothing (`stirred`), so a double-click lands on the
   handle it was made on.
3. **Save design** downloads every setting as one JSON file on the user's
   own computer — the instrument, the guitar's name, all `prototype` and
   `machining` values, the drawn body's `control_points` and the drawn
   headstock edges included (`{"format": "cncguitarwizard-design",
   "version": 1, "name", "instrument", "prototype", "machining"}`), named
   for the guitar (*Guitar name*, beside the instrument) when it has one
   (Ctrl/Cmd+S too, in place of the browser's saving the page). The
   button is marked (*Save design •*, `markUnsaved`) while the design
   differs from the one last saved or loaded in this browser (kept there,
   `cncguitarwizard.savedDesign`, so a reload still knows it); with none
   saved or loaded yet, once a setting is changed or the guitar named.
   *Recent ▾* beside it lists the last six designs saved or loaded in
   this browser, newest first by file name (one saved again takes its old
   place; `cncguitarwizard.recentDesigns`, `rememberDesign`): one chosen
   is loaded as its file would be (`putDesign`), asked first when
   settings are changed. **Load
   design** (or Ctrl/Cmd+O, or the file dropped anywhere on the page: a
   banner at the top says so while it is dragged, `drop-banner`; an SVG
   or DXF dropped on an editor's drawing is read as its outline, or the
   inlay marker, as its *Import* does, the drawing outlined meanwhile,
   `dropEditor`; any other file dropped is refused rather than opened in
   the page's place) opens such a
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
   A design put back or loaded never stays in error (`repairDesign`):
   whatever would make an editor show red — an error, a problem its
   layout reports (a neck bolt with no room, a frame or lettering that
   does not fit, a strap guide off the flat back or on a cover), a
   feature outside the outline (`webapp.design_problems`)
   — is put back to its default. A field whose value does not read goes
   first; then `webapp.repair_design` tries the settings changed from
   their defaults (those the commonest problems come from first,
   `REPAIR_FIRST`, a strap guide's place among them, so a guide in the
   way goes back to its automatic spot before what it is in the way of
   is put back): one at a time, keeping each that leaves fewer
   problems, then more together until none are left, and last gives back
   the design's own value where its default was not needed. The status
   line names what was put back, and Undo takes it back.
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
   its step changes as the form labels them (*Undo: Thickness*, *Undo:
   Bridge · Baseplate length*), and a new change clears the redo steps. In a text
   field the keys keep the browser's own undo of the typing.
   While a handle or a feature is dragged, a label by the pointer says
   how far it has moved or where it is (`showReadout`): a body handle or
   feature its move along the neck and across it (*+20.2 mm along ·
   −10.1 mm across*, a pickup along only), a turn its angle and a
   stretch its change; a headstock edge handle its distance from the nut
   and the centreline, a tuner hole its distance from the nut and the
   edge. A handle pressed — the body's outline handles and features, the
   headstock's edge handles and tuner holes — is picked and marked
   (`pickHandle`; a feature moves as if dropped there, `nudgeFeature`, a
   pickup along the neck only):
   the arrow keys then move it 0.5 mm across the screen (Shift: 5 mm,
   turned into the drawing's frame, so upright or mirrored too), each
   move committed as a drag is (quick moves one Undo step) and said by it
   for a moment; a tuner hole keeps its distance from its edge along the
   neck, as dragged, and moves off it or nearer across. Escape, or a
   press on the background, lets it go.
   Every editor's drawing zooms (`enableZoom`): Ctrl/Cmd+wheel, or a
   trackpad's pinch, about the pointer, up to 20 times; zoomed in, a drag
   on the background moves it and a double-click there fits the whole
   drawing again, as does the chip in its corner that says how far it is
   zoomed (*2.7× · Fit*, `showZoom`: a touch screen's way back; a plot's
   too). On a touch screen two fingers on the background pinch it about
   their middle and move it with them, the point under their middle kept
   under it (a finger on a handle or feature is left to it; a plot keeps
   one-finger scrolling of the page, `touch-action: pan-x pan-y`).
   The chips sit in a strip of their own above the drawing, so none
   covers its top (a toolpath plot's title).
   *Full window*, beside *Measure* in each drawing's other top corner,
   shows the drawing over the whole page as big as the window lets it,
   every handle working as before (`zoom-frame.full`); an editor keeps
   its status line there, at the foot (copied in as it changes:
   `full-status`), and *Undo* and *Redo* beside *Close*; *Close* or
   Escape puts it back.
   *Measure*, in each drawing's other top corner (the result's plots
   too, all drawn in millimetres), lays a ruler across the middle of
   what is in view (`enableRuler`): drag either end — it snaps to the
   middle of a handle or hole within 8 px, Alt-drag not, and Shift keeps
   it level or upright — or its line to move it whole; its length and
   how far it runs across and up the screen are written at its middle
   (*30.1 mm · ↔ 30.0 · ↕ 3.0*), sized for the zoom, and it stays on top
   through every redraw until *Measure* takes it off. The
   zoom outlasts a redraw (`begin`), the plain wheel
   scrolls the page as ever, and every handle works as before.
   The editors' button rows keep to one line: their templates' four
   buttons sit in a *File ▾* menu (`details.menu`, closing once one is
   chosen, on a click elsewhere or on Escape), and the body editor's *Auto
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
   a field being typed in too, or *Build* floating in the corner while
   the page's own is out of sight — scrolled past on a narrow screen, in
   the form's column on a wide one — and showing *Building…* as it does,
   `build-float`) runs the build in stages — `start_build()`, then
   `advance_build()` once per stage of `workflows.Prototype001Build`
   (geometry, body, neck and fretboard toolpaths, cover plates, G-code,
   FreeCAD script),
   then `finish_build()` — repainting a progress bar and a spinning Build
   button between stages, since Pyodide runs Python on the page's own
   thread. Everything lands in Pyodide's in-memory file system and comes
   back as text. The tab's title is the guitar's name (`syncTitle`),
   *Building…* in front of it meanwhile; a build that ends while another
   tab is in front puts *✓ Built* or *✗ Build failed* there until the
   page is seen again (`noteInTitle`).
5. Quick links at the top of the right-hand column, kept in view while it
   scrolls (`#jump`), go to the result (once there is one), the body,
   headstock and inlay editors (while they show) and, on a narrow screen
   where they come last, the settings.
   Shows the result first, as soon as it is done (`#output`, the first
   thing in the right-hand column, above the editors; on a narrow screen
   straight under the build button and instrument choice, an error in
   the same place, and the page scrolls to either when it arrives out of
   view, `bringIntoView`; once the design changes after a build, a note
   above the result says its files are no longer the design's, with
   *Build again*: `builtFrom`, `markStale`, until the design is as built
   again): the summary with stock size
   (a fretboard blank's carrier on a row of its own, `fretboard_carrier_thickness`;
   the index pins' places only for a blank that has them, along the
   machine's Y for a blank turned to fit its travel, and a warning for
   one too big for it either way) and the
   programs in one row — how many, about how long at the set feeds —
   first, each program's tool, time and cutting in the fold *Every
   program* below it (`#summary-programs`), each row's *Plot* showing its
   toolpath plot below and bringing it into sight; then the download
   links for the FreeCAD script (`.py` and `.FCMacro`), every `.nc`
   program (body, electronics, neck, fretboard, the nut-slot jig and one per cover plate), the SVG plots, the DXF outlines
   (`Prototype001_plan.dxf`, `Prototype001_covers.dxf`; see [DXF](render/02_dxf.md)) and `build.json`;
   then the whole-instrument plan view (standing upright, headstock at
   the top, sized to fit the window; each part named under the pointer,
   `<title>` from `render_plan_view_svg`: *Neck pocket*, *Tuner hole,
   bass 1*, *Control cavity (back)*; the nut drawn on its seat, bone white
   or dark for a locking nut, a board that runs on under it reaching on
   behind it) and the toolpath plots, one at a time, chosen from a list by part
   (each program by its step, the body's top first) or stepped through
   with the arrows beside it (`toolpath-choice`; the shown program's
   tool, time, cutting and operations under them, and *Simulate* for it,
   opening NC Viewer under the plot; each says how deep its
   colours cut in a bar under the part, and which toolpath a cut is under
   the pointer, `cam.preview`); both zoom as an
   editor's drawing does (`zoomablePlot`, `enableZoom`). *Print*, beside
   the summary's title (or the browser's own printing once there is a
   result), prints a sheet for the workshop: the guitar's name,
   instrument and the day at its head, the summary, every program
   unfolded and the plan view, the stale-result note if the design has
   changed since; the form, editors, downloads and toolpaths are left
   out (`print-result`, set on `beforeprint`, and the page's print CSS). The downloads come in one fold per part, closed
   until opened (its title says how many programs) — the
   model and report first, then body, neck, fretboard, the inlay pieces, the nut jig and covers — each
   program numbered in the order it is run (`build.json` gives it as the
   program's `step`), its toolpath plot a *Plot* link on its row; on a
   narrow screen a row's links wrap, its name breaks after an underscore
   and a table still too wide scrolls on its own, so nothing runs past the
   results' clipped edge. Each `.nc` row also has a *Simulate* button: it
   copies that program to the clipboard and opens
   [NC Viewer](https://ncviewer.com) in a panel below, where selecting all
   in its editor (Ctrl/Cmd+A), pasting (Ctrl/Cmd+V) and pressing *Plot*
   (or dropping the downloaded file) runs the simulation — the
   viewer has no URL or message API a page could feed directly.
   *Download all NC files (.zip)* gives every program in one ZIP named
   for the guitar (`<Guitar name>.zip`; `webapp.nc_archive` packs the last
   build's programs in Python): a folder named for the guitar, one folder
   a part inside it, each program numbered in running order
   (`Neck/02_Neck_top_6mm_flathead.nc`, a program named for its tool), and
   a `README.txt` listing them with their
   tools and run times. The name is made safe for a file name
   (`webapp.archive_name`: letters, digits, spaces, dots, dashes and
   underscores stay).
6. **Shortcuts**, at the right of the header (or `?` anywhere but a
   field), lists the page's keys and mouse moves in a dialog
   (`keys-dialog`): building, undo and redo, zooming and moving a
   drawing, Escape; each editor's own handles stay in its *How to edit*.
7. **Tour**, beside it, walks the basic path in five steps — the
   instrument and its name, the body, the headstock (while it has an
   editor), the settings, and Build (`startTour`, `TOUR_STEPS`). Each
   step lights its part up and dims the rest (`tour-spot`), with a card
   beside it (*Next*, *Skip tour*, Escape). In the body and headstock
   steps a pointer shows what to do (`demoBody`, `demoHeadstock`): it
   pulls a handle of the outline out and back, or slides a pickup along
   the neck and back, now and then at random — drawn only, through the
   editors' own uncommitted drawing (`showPoint`, `showEdges`) and put
   back exactly, so nothing in the design or its Undo changes, and a
   press of the user's own in the drawing stops it first. The last step
   asks for Build to be pressed, and building ends the tour. It runs by
   itself once, on the first visit (`cncguitarwizard.toured`).

FreeCAD cannot run in a browser, so `.FCStd` and STEP are made locally:
download `Prototype001_freecad.py` and run
`freecadcmd Prototype001_freecad.py` (or open the `.FCMacro` in FreeCAD).
The script writes its outputs next to wherever it is executed. Or save
the design (*Save design*) and build it all locally from a clone with
`python -m cncguitarwizard build-prototype001 --design my_guitar.json
--output build/my_guitar`: the G-code, DXF, FCStd and STEP together.

## Classic UI and application like UI (a trial), dark mode

A new visitor gets the page as a desktop application, the application
like UI (`site/desktop.js`), in dark mode; *View → Classic UI* goes to
the Classic UI, the long single page, whose header's *Application like
UI* comes back. The choice is kept in the browser, so the next visit
opens the same (`?layout=desktop` or `?layout=classic` in the address
chooses too). A menu bar runs along the top — *File* (new, open, recent
designs, save, print the result), *Edit* (undo, redo, find a setting),
*Design* (the instrument and style, the body, the neck, the headstock,
the fretboard, the inlays), *Settings* (each group of the form), *Build* (build, then the
result's summary, downloads, plan view and toolpaths), *View* (easy
mode, dark mode, the Classic UI), *Bonus* (files to print for the
machine) and *Help* (the tour, the shortcuts, what the
page does, the source) — with *Build* at its right, and a status bar
along the bottom says which page is shown, the status line and a build's
progress. One page shows at a time: the instrument (with the intro and
the design file's buttons), each editor, the settings (the groups in a
list beside them, one group shown, all that match while finding a
setting) or the result (its summary, downloads, plan view and toolpaths
as tabs).

Build opens the result page at once, a panel at its head saying what
the build is doing: *Building …* with a turning ring, a bar and the time
so far and about how long is left, the step running (*Step 3 of 8:
Planning the neck toolpaths — about 29 s*), each step passed with its
time and each to come with its likely time; the menu bar's *Build* says
*Building… 25%* and goes back to it. A step's likely time is this
browser's own from its builds so far (kept, the mean of each build's and
the last), else a typical build's (`TYPICAL_STEPS`), and once a step is
done all are scaled by how quick this build has been so far: after the
first the rest are about known. The bar goes by those times, so the
long steps (the neck's back) count for more. A finished build turns the panel
green (*… is built*, how long it took, the summary under it); one that
stops turns it red, saying at which step, the error itself above it. It
follows app.js's own progress (its label and bar) and its Build button
(`busy` while it runs).

Dark mode, the default, is a choice of its own, in either UI: *View →
Dark mode* in the application like UI, *Light mode* (*Dark mode* to go
back) in the Classic UI's header, kept in the browser (`?theme=light`
or `?theme=dark` in the address chooses too). The page's colours are
tokens on `:root` (`--ink`, `--bg`, `--panel`, `--line`, `--accent`,
`--tint` and the rest) that `:root[data-theme="dark"]` sets afresh, on
screen only, so a print stays light; a script at the head of the page
sets the theme before it paints, so it never flashes light first. The
drawings (the editors, the plan view, the toolpath plots) stay on light
paper (`--paper`), their colours being a drawing's.

*Design › Neck* and *Design › Fretboard* are pages of their own there:
a drawing of the part (`webapp.part_views`, `render.svg.neck_views`)
with its settings beside it (under it on a narrow screen), copies of the
form's as an editor's Settings hold them. The neck from above — the
headstock and its tuner holes, the board, frets, markers and nut — from
the side (its height stretched three times: the neck's depth under the
board, the heel) and in section at the first and twelfth frets, its
width and depth said; the fretboard from above — its slots as cut
(blind ones short of the edges), markers, fret numbers and, scalloped,
its scallops shaded between their lands — from the side along its middle
(the scallops hollowed in it, the slots down into it) and in section at
the twelfth fret, its radius said. Both are drawn afresh a moment after
a setting changes while either page shows (not during a build); a design
that does not build says why there instead. The fretboard's binding and
blind slots move there from the inlay editor's Settings.

Every page under *Design* has a Reset of its own (*Reset Body (4)*, the
number its settings changed from their defaults, off when there are
none): it puts back, after asking, the settings of its groups in the
form and those it shows (its Settings' copies; the body's drawing,
`body_shape`, with the body's) — the instrument's page the instrument's
own (handedness, strings, scale and *Other*), the neck's the *Neck*,
*Heel* and *Fillets* groups, the fretboard's and the inlays' their halves
of *Scale and fretboard* — a variant's kind first, as a group's Reset
does; Undo takes them back as one step. The instrument's page keeps the
Reset of everything, there called *Reset everything*.

The menu bar's own search (*Find a setting… (/)*, `/` from anywhere)
finds settings from any page, as the form's search does (every word in
a setting's name, field name or meaning), the likeliest first (the
words in its name, the shortest such name first; then in its field
name; then in its meaning, said soonest first). Each comes with its own
control, set right there — a copy, as an editor's Settings holds one,
passing its value to the form's — and a link to each page it is on: its
editor's Settings (*Design › Body*, *Design › Headstock*, *Design ›
Inlays*) when one shows it there, else its group (*Settings › Body*);
the link opens the page and its fold and selects the setting, Enter the
first one's. Searching *flame* finds the strap guide's tick box, linked
to *Design › Body*.

Nothing is built twice: the Classic UI's own parts are shown page by
page and the menus press its own buttons, so `app.js` runs as ever. It
shows the page an element is on before it scrolls to it or selects it
(`reveal`, which the app layout answers as `window.cncgwLayout`): a
finished build opens the result, a setting found or gone to its group,
the tour's next stop its page.

## Tip of the day

One sentence a day from `TIPS` in `site/app.js` — the builder's own
(EMG actives on 24 V from two V23GA batteries; oil the strings at the nut
and the bridge), wiring, setup, the workshop and the page's own keys —
in the Classic UI's footer and at the right of the application like UI's
status bar (in full on hovering it; not while a build shows its
progress, nor on a screen narrower than 700 px). It is the same all day
and another tomorrow: each day steps 7919, a prime, along the list
(`tipOfTheDay`), so the order looks random and every tip comes round
once before any comes back. Add one by adding a line to `TIPS`.

## Bonus: a dust shoe to print

Under the whole page (the Classic UI's *Bonus* link; the application
like UI's *Bonus* menu, a page of its own) the page offers files to
print for the machine rather than for the guitar, served from
`site/bonus/`: a dust shoe for a Makita RT0702C router on a TwoTrees
TTC-H40, for a 60 mm vacuum hose. Three parts, each printing without
supports as it lies in its file:

- the *collar*, clamped round the router's 65 mm body with an M4 bolt
  (its nut in a hex pocket), carrying the hose's port;
- the *housing* round the bit, bolted under the collar with four M4
  bolts, its back straight to turn toward the machine's frame (16 mm
  from the router's body on the TTC-H40);
- the *brush sleeve* over the housing, sliding 50 mm up and down on
  three M4 screws in the housing's bosses, so its brushes (a strip with
  a 3 mm U-channel back, 8 mm tall, snapped into its groove) stay down
  on the work as the cut goes deeper, and the chips go up the hose.

Each comes in two sets: the hose leaving forward (`*_hose_forward.stl`,
out of the gantry's way along X) or to one side
(`*_hose_sideways.stl`). `dust_shoe_makita_rt0702c_ttc_h40.scad` is
their OpenSCAD source, every size a setting at its top (the router's
diameter, the hose and how it fits the port, the room to the frame, the
hose's direction as `port_angle`: 90 forward, 0 to the side, the
travel): choose the `part` (`collar`, `housing` or `sleeve`; `assembly`
shows them together), render it and export it as STL.

## Building and previewing locally

```bash
python tools/build_site.py
python tools/serve_site.py 8765
```

Then open <http://localhost:8765>. `tools/build_site.py` builds the wheel
into `site/wheels/` and writes `site/wheel.json`, both git-ignored. The
page needs to be served over HTTP (not opened as a file) because Pyodide
fetches the wheel. `tools/serve_site.py` is Python's `http.server` with
`Cache-Control: no-cache` on every response, so the browser checks each
file again every time (an unchanged one comes back as a short "not
modified"); plain `python -m http.server` sends no such header, and a
browser may then keep the page itself for a while. Served by Apache
instead (MAMP), `site/.htaccess` sets the same header for the page, the
script and the manifest.

`wheel.json` carries a build id (a hash of the wheel, `app.js` and
`desktop.js`) and the
page's stamp. The page fetches it past every cache — `cache: "no-store"`
and a URL of its own each time (`wheel.json?t=…`), so not even a CDN's
copy (GitHub Pages keeps files 10 minutes) is used — and appends the id
to the `app.js` and wheel URLs, so after a rebuild a plain reload always
gets the matching script and wheel — no hard refresh needed. The page
itself (its markup, styles and help) is stamped by `tools/build_site.py`
with a hash of itself (`<meta name="cgw-page">`, `stamped_page`; it
changes only when the page does). A page whose stamp is not the
manifest's is a stale copy from a cache: before loading anything it
loads itself again at `?page=<stamp>`, a URL no cache holds, once (a page
edited but not rebuilt keeps going). The status line shows the build id
that is running.

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
| `site/desktop.js` | The application like UI, a trial: a menu bar and one page at a time over the Classic UI; the dark mode switch |
| `site/bonus/` | The bonus: the dust shoe's STL files and their OpenSCAD source |
| `src/cncguitarwizard/webapp.py` | Schema and build glue called from the page |
| `src/cncguitarwizard/render/svg/plan_view.py` | The plan-view SVG |
| `tools/build_site.py` | Wheel build, manifest and the page's stamp |
| `tools/serve_site.py` | Local server that keeps the browser from caching the site |
| `site/.htaccess` | The same `no-cache` header under Apache (MAMP) |
