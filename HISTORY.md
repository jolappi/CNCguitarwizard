## Geometry Engine

Prototype001 now has a solid body. `cncguitarwizard.geometry.body` models a
flat 44 mm slab in the neck's own nut-origin frame, with a neck pocket,
pickup routes, a bridge mounting, rear control and switch cavities with
cover recesses, drilled shaft holes, and a jack bore, all cross-validated
against the outline and slab thickness. The Prototype001 body is digitised
from the user's own `omarunko.dxf`: its outline, trapezoidal neck pocket,
humbucker routes with mounting ears, Kahler 7300 baseplate cutout, almond
control cavity and round switch cavity are the drawing's own shapes. The
body frame is anchored on the drawing's pickup placement so the neck heel
lands in the drawing's pocket, which opens onto the horn gap. The instrument
is left-handed; the neck is symmetric.

The fretboard now carries 2 mm barbed-wire position markers. `InlayLayout`
places one marker between frets 3, 5, 7, 9, 15, 17, 19 and 21 and a pair at
12 and 24, and the FreeCAD backend cuts them as flat-bottomed pockets into
the radiused playing surface.

The neck-end inspection form now uses a U-shaped boundary instead of moving
or delaying individual D-profile rows. Both outer neck-end corners remain at
the original end line, while the centre retracts 12 mm toward the heel. The U is generated
as a FreeCAD cut after the unchanged neck loft, so the fixed 5 mm nut shelf
and every underlying D-profile section remain in their original positions.
The D-profile-to-U root now uses a 2 mm cylindrical fillet only on the two
vertical side walls of the U cylinder at the outer nut corners. The central U
arc is left untouched.

The fixed 5 mm nut shelf now keeps only its center flat at the nut line. The
two outer shoulders continue their longitudinal D-profile runout all the way
to the neck end before they meet the U-cylinder side blend.

Prototype001's default build workflow now exports the full joined neck again.
The headstock is no longer hidden in the standard `.FCStd` / `.step` output,
so the nut-end U transition is inspected in the real assembled context.
The default joined build now uses the true headstock-root transition loft
again. The outer D-profile shoulders continue farther into the headstock root
than the centre does, so the neck-back curve flows into the headstock without
an obvious seam or a post-fusion edge fillet.

The Stratocaster neck-only STEP reference confirmed that the reference neck
and fretboard are separate solids and that its heel and headstock roots are
continuous freeform surfaces. Prototype001 now exposes the corresponding
user-facing `headstock_root_length` and `heel_root_length` distances. The
headstock root controls only the smooth plan-view widening into the custom
3+3 headstock. The
heel root controls only the D-to-heel runout, preserving the complete flat
54 mm bolt-on mounting region.

The two roots now include separate lateral runout controls rather than only
longitudinal distances. `headstock_root_side_extension` forms a symmetric pair
of seam-free triangular shoulders in the headstock-to-neck surface, while
`heel_root_center_extension` creates the rounded center-leading heel root in
the same uninterrupted loft. The mounting block itself remains unaltered.

The headstock-to-neck blend is exposed as the dedicated
`headstock_volute_length` parameter. It controls the length of the shared
root transition, rather than adding a separate 3D feature.
The headstock now reaches its full shoulder width 10 mm from the nut and then
uses a long, smooth 140 mm taper toward the tip. This produces the intended
plan-view triangular runout while retaining a symmetrical, low-profile center.
The first two tuner pairs move 1 mm toward the centerline to preserve at least
8 mm of side-edge material within that longer taper.

The Prototype001 bolt-on mounting block now has an explicit,
user-configurable `heel_mounting_length`. Its default remains the verified
54 mm total (50 mm before fret 24 plus the 4 mm rear extension), and the
preset rejects anything shorter than the user-validated 40 mm mounting area.
Its D-profile-to-heel blend is now 45 mm long, giving the rounded heel entry a
slightly longer, more Strat-like taper while retaining the entire flat
mounting block.

Prototype001 now has a planar bolt-on heel underside. The neck joins it
through a multi-section, progressively flattened D-profile loft, while a
30 mm volute blends the angled headstock thickness into the first-fret neck.
Its fretboard now ends flush with the heel, and the neck wood includes a
6 mm horizontal nut shelf before the fretboard without moving the scale.
The playing-section back now uses a rounded exponent-2 elliptical profile
that begins directly at the fretboard sides instead of the flatter D shape.

Generated FreeCAD scripts can optionally save an editable `.FCStd` document
and export their solid as `.step` or `.stp`. Output suffixes are validated
before source generation.

The FreeCAD backend can now generate a single neck assembly document. The
neck back and fretboard remain separate solids, while an optional STEP export
contains both objects for fit inspection.

The assembly exporter can optionally subtract the validated rectangular
truss-rod channel from the neck solid. It rejects mismatched outlines and
channels that would consume the full neck depth.

The fretboard solid can now receive all 24 validated fret-slot cuts. Their
0.6 mm wide, 2.7 mm deep cutting geometry follows the sampled 430 mm playing
surface radius and preserves material beneath every slot.

The fretboard ends 4 mm after fret 24. The flat bolt-on heel begins 50 mm
toward the headstock from fret 24 and ends with the fretboard, making an exact
54 × 20 mm tapered mounting region that reaches 56 mm at its end. The shaped
transition and straight heel are now generated by one uninterrupted loft,
removing the former boolean boundary between them.
Both major joints are continuous laterally as well: the heel follows the
neck/fretboard taper, and the headstock shoulder uses a sampled curved outline.
The former separate rounded nose has been removed. A low 45 mm
tangent-controlled D-profile loft now widens, deepens, and progressively
flattens through superelliptical intermediate sections before entering the
straight heel inside the same loft. This replaces the straight
D-to-rectangle point interpolation that could form a visible triangular ramp.
Its centerline includes a configurable 1.5 mm inward scoop, reversing the
former outward hump without changing either end tangent.
The remaining transverse edge at the start of the heel's straight region now
receives the same adaptive 3 mm rounding strategy used for the headstock,
removing the visible sharp corner without adding a second heel solid.
The inward scoop is now constrained by the remaining depth to the heel plane,
so it cannot reach the final 20 mm depth early and create a longitudinal kink.
The 54 mm heel mounting region now remains in FreeCAD's consistent sampled
loft topology. Its central area is flat along the neck axis, while the outer
side edges retain the small rounded relief required for a valid, continuous
loft.
Headstock fusion now refines the combined BREP after the boolean operation,
preventing heel-nose split edges from invalidating the later complete solid.
Headstock fillet generation remains adaptive because OpenCASCADE may reject
individual BREP radii: smaller radii are attempted automatically and an
optional fillet failure no longer aborts the complete model build.

The tapered headstock now has backend-independent solid geometry with a
configurable, validated thickness from 14 to 16 mm. Prototype001 uses 16 mm,
and FreeCAD assemblies can export it as a separate angled solid.

FreeCAD headstock exports can now subtract the validated 3+3 tuner layout.
All six 10 mm bores pass completely through the solid along the normal of the
8-degree face.

Tuner holes now receive a configurable 45-degree face chamfer. Prototype001
uses the previously agreed 0.2 mm depth, while zero disables the feature.

The FreeCAD assembly exporter can optionally fuse the angled headstock into
the neck back for manufacturing output. Separate-object inspection remains
available, and incompatible nut widths are rejected before source generation.

The Prototype001 preset now provides one immutable parameter source for the
complete neck. It builds every current geometry component and feeds them to a
one-call FreeCAD export without coupling the core model to a CAD backend.

Prototype001 now has a one-command build workflow. It creates matching
FreeCAD macro and Python scripts plus a JSON report containing the complete
parameter set, version, timestamp, target files, and script checksum.

The normal build now executes FreeCAD and verifies that both `.FCStd` and
`.step` exist before reporting success. Script-only generation is explicit,
and failed or incomplete FreeCAD runs produce a build workflow error.

FreeCAD execution now always records its command, exit code, stdout, and
stderr in `freecad.log`. The JSON report persists `pending`, `failed`, or
`complete` state, so an interrupted build cannot resemble a successful one.

Neck loft sections no longer repeat their existing `Z = 0` edge points.
Removing those zero-length polygon edges fixes FreeCAD's initial `Null shape`
failure. Generated scripts now validate and identify every loft and boolean
result.

Radius-following fret slots now use one continuous cutter solid per fret.
This removes the internal coplanar seams that caused FreeCAD to report an
invalid shape during the first fret-slot boolean operation.

Fret-slot cutters now cross the playing surface and both fretboard edges with
small controlled overcuts. This avoids coincident OpenCASCADE boolean faces,
and diagnostics identify the exact fret number if a cut still fails.

Prototype001 now interprets the 17 mm and 19 mm neck dimensions correctly as
totals including the 6 mm fretboard. Its neck-wood depths are 11 mm and 13 mm,
while the heel remains the specified 20 mm of wood plus fretboard. Builds also
remove stale FCStd and STEP targets before FreeCAD execution.

Prototype001 tuner stations moved to 55, 85, and 115 mm with 16, 13, and
10 mm centerline offsets. This leaves at least 8.646 mm of wood between every
10 mm hole edge and the tapered headstock side.

The geometry package was introduced as the backend-independent foundation for
instrument geometry.

- Added immutable `Point2D`, `Vector2D`, and `Line2D` primitives.
- Introduced the guitar neck `Centerline` model.
- Added finite, positive scale-length validation for centerline geometry.
- Added `distance`, `midpoint`, and `interpolate` geometry utilities.
- Extended `Vector2D` with dot, cross, angle, and perpendicular operations.
- Added immutable point translation, rotation, and mirror transformations.
- Added equal-temperament fret positions and centerline-derived fret lines.
- Added tapered fretboard outlines from centerline and endpoint widths.
- Added symmetric R8 mm nut-corner rounding for rendered fretboard outlines.
- Applied the same R8 mm nut-corner fillets to FreeCAD fretboard solids.
- Added dependency-free SVG rendering with geometry snapshots.
- Added an immutable neck model and fluent neck builder.
- Added unit tests for primitive behavior, validation, and centerline geometry.

## Fretboard Generator

Fret positions were combined with the tapered fretboard outline for the first
time. The engine now produces bounded slot segments whose lengths follow the
fretboard taper, providing a backend-independent foundation for drawings and
future CAM operations.

The SVG backend was then extended to render the complete fretboard and its
bounded slots together. This created the first combined visual preview of the
fretboard geometry.

SVG previews now derive their view box from the rendered geometry. Models of
different dimensions fit the viewport automatically while retaining a
configurable model-space margin.

## Neck Generator

The first top-view neck outline was generated from the locked Prototype001
dimensions. It combines a 42 mm nut, a 56 mm width at fret 24, and a 63 mm
parallel bolt-on heel without manual CAD sketching.

The longitudinal wood profile followed next, introducing the 17 mm first-fret,
19 mm twelfth-fret, and 20 mm heel thickness references while keeping the
fretboard as a separate future geometry layer.

The separate fretboard geometry was then added with a 6 mm center thickness
and a true 430 mm circular cross-section. The model now exposes the calculated
surface sagitta and remaining edge thickness for manufacturing checks.

The modern 3+3 headstock reference followed with a 150 mm tapered plan and an
8-degree side angle. The shape widens through a 65 mm shoulder and narrows to
a 40 mm tip without copying a manufacturer-specific outline.

Six 10 mm tuner holes were added in a symmetric 3+3 layout. Automated checks
now protect the headstock edges, nut, tip, and neighboring holes before the
layout can proceed to a manufacturing backend.

The centered 440 × 6 × 9 mm double-action truss-rod channel was added with a
heel-side adjustment reference. Its fit is checked against the complete neck
outline before geometry is accepted.

Wizard-inspired D-profile cross-sections were introduced at frets 1 and 12.
The backend-independent superellipse keeps the shape symmetric and makes its
shoulder fullness adjustable for the future physical test block.

The cross-sections were then joined into the first backend-independent 3D neck
surface. A deterministic quad mesh now follows the nut, first-fret,
twelfth-fret, and final-fret thickness references and is ready for a future
FreeCAD loft backend.

The 430 mm fretboard radius was extended into a three-dimensional tapered
playing surface. Cross-section rows now coincide with the nut and every fret,
providing exact longitudinal references for CAD lofting and future fret-slot
operations.

## CAM

The first G-code comes from the project's own, dependency-free 2.5D planner
rather than an external CAM package. `cncguitarwizard.cam` answers one
question exactly — where can a disc of the tool's radius go inside a
polygon — per scanline for pocket rastering and along pruned normal
offsets for finishing contours and outside profiles, with arc samples on
the circumscribed polygon so chords never gouge. On top of that sit
pocket, drill (peck and helix) and profile-with-tabs operations, a GRBL
writer, and SVG toolpath plots. The body is machined from both faces on
two centerline index pins that share one work origin, so the flip is a
pure `Y -> -Y`; `build-prototype001` writes `Body_index_pins.nc`,
`Body_top.nc` and `Body_back.nc` alongside the FreeCAD outputs. Every
cutting move is checked to lie inside its own feature before the files
are trusted.

## FreeCAD Backend

The assembly export now builds the body as a fourth `Part::Feature`. Top
cavities are cut down from `Z = 0`, rear cavities and their cover recesses
up from the back face, drilled holes and pivot studs as vertical cylinders,
and the jack as a horizontal bore; the STEP file includes the body solid.
Inlay pockets are cut into the fretboard in the same script.

The first CAD backend was introduced without coupling FreeCAD to the geometry
engine. Deterministic standalone scripts can now loft the sampled neck-back
and fretboard sections into FreeCAD solids for visual inspection.

## Documentation

- Added public package reference with API tables, examples, and diagrams.
- Updated README, roadmap, and architecture documentation.

## Continuous Integration

- Added cached Python 3.12 GitHub Actions checks for pytest, Ruff, and mypy.
- Configured pytest warnings to fail the CI build.

## Step 2

The first core object was implemented.

Every future module will attach to the Project object,
forming the backbone of CNCguitarwizard.

2026-07-18 – Lift Off

The first runnable version of CNCguitarwizard was created. The project's architecture, philosophy and development principles were established before geometry generation began.
──────────────────────────────

History

Introduced:
v0.1.0

Related commits:

feat(geometry): add centerline

Related modules:

geometry/centerline.py

Tests:

tests/geometry/test_centerline.py

──────────────────────────────

## Internal Project Lore

The term "Digidust" was coined during the development of the first geometry modules.

Just like sawdust appears when wood is shaped,
Digidust appears when mathematics becomes geometry.

It reminds us that every tiny calculation is part of building a real instrument.
