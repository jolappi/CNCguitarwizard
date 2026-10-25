# The quick 3D model

The build's model is FreeCAD's (or OpenCascade's in the browser): exact,
every boolean cut, and slow — a Stratocaster's STEP takes twenty minutes
and more, if it is made at all. To try a change and see it, the quick model
draws the design's own surfaces as triangle meshes instead, in a second or
two (`render.preview3d`, `webapp.quick_model`).

It is a model to look at, not to build from: holes, the truss-rod
channel and the wiring are left out, and the hardware is in typical
sizes; the build's STEP and FreeCAD model are the exact ones.

## The parts

`preview_parts(geometry, neck_rows, spacing=PREVIEW_SPACING)` returns three
`PreviewPart`s, each a closed mesh (every edge met once each way), its
triangles turned outward (anticlockwise seen from outside), in millimetres
in the model's frame (X from the nut toward the tail, Z up from the glue
face):

| Part | Made from |
| --- | --- |
| `Body` | Its top and its back sampled on a grid `PREVIEW_SPACING` (2 mm) apart as heights: the top lowered by a carve or a stepped top, the contours on it, its roundover (by the distance to the edge) and the routes from the top (each to its depth); the back raised by its contours (a belly cut, a heel relief), its roundover (but where it stops short of a neck plate, `EdgeProfile.square`) and the routes from the back (pockets and cover recesses). The grid's points just outside the outline are moved onto it, so the edge is the outline's, not the grid's; walls join top and back round the edge and round every route cut through |
| `Neck` | The loft's own rows, headstock to heel end (`FreeCADScriptExporter.neck_loft_rows`: the back as FreeCAD lofts it, round into the heel and the headstock, the headstock's outline followed), closed across their top edges and at both ends |
| `Fretboard` | Its radiused surface's rows (`FretboardSurface.mesh`), run down at both edges to its flat underside and closed |
| `Top` | With a separate top (`BodySolid.cap_thickness`) only: the body's top from the cap's underside up, left out where a route goes clean through it; `Body` is then the core, up to the cap's underside, lower where a route reaches into it and where its own routes (wire channels, chambers) go down from there |

The neck and the fretboard are tilted back onto the body as the build
tilts them (`Prototype001Geometry.neck_tilt`: turned about the pocket
floor's heel end, the nut end going down).

## The details

`detail_parts(geometry, parameters, detail)` makes one detail set
(`DETAILS`), its parts closed meshes as the others, in typical sizes (the
design does not hold them):

| Detail | Parts |
| --- | --- |
| `neck` | `Frets`: a crown 2.6 mm wide and the frets' height along each slot, edge to edge on the board's radius (the zero fret's too). `Markers`: each inlay's outline, flush with the board (a hair proud, to show). `Nut`: across the board's end, as high as the strings sit (0.5 mm over the frets) |
| `headstock` | `Tuners`: on each tuner hole a bushing and a post standing along the face's normal, a gear housing under the back and a button out past the headstock's side (the hole's side) |
| `body` | `Pickguard`: each plate on the top, on its highest point. `Pickups`: the pickguard's pickup openings (else the pickup routes) 6 mm up over it (or the top). `Knobs`: one on each pot's shaft hole, a toggle on a switch's, a blade's tip up through its slot |
| `bridge` | `Strings`: from their posts (the bass side's from the nut out to the bass strings from the outside in, the treble side's likewise) over the nut to the saddles at the scale line, the nut's and the bridge's spacing, 3 mm over the frets' plane at the saddles, tilted with the neck. `Bridge`: a plate on the top beneath them and a saddle under each |

Built once the design is (its build kept), the sets take a tenth of a
second or two each.

`PreviewPart.float32()` and `uint32()` give the positions and triangles as
little-endian 32-bit floats and indices; `stl_bytes(parts)` writes them
all as one binary STL.

## In the page

*Preview › 3D model* (the application like UI's page; in the Classic UI the
*3D model* fold under the inlay editor) shows it, drawn when opened and
again a moment after each change while it is open and in sight — out of
sight it is only marked stale, as an editor is. `quick_worker.js` makes it
off the page's thread (Pyodide with the wheel only, no CAD kernel: the
answer's buffers handed over, not copied), and `quick3d.js` turns it in
three.js 0.160 (`OrbitControls`; creased normals past 35°, so a roundover
reads round and an edge sharp). The first model is framed whole (*Whole
guitar* frames it again); later ones keep the view, so a change is seen
from where it was looked at, and the wheel or a pinch zooms toward the
pointer, to a detail. *Save STL* saves what is drawn, 1:1 in
millimetres. A design with a separate top is built wired for it
(`_quick_built`), so the wire channels routed under the top are in the
core (seen with the top hidden); any other is built without its wiring,
the quicker. The detail sets are ticked by checkboxes (and in the
*Preview* menu), any or all of them, and are sent with the design
(`quick_model(payload, details)`): all four add about 70 000 triangles to
a Stratocaster's 128 000, and about 0.9 s to its drawing in the browser
(the body's set the most, 0.4 s); it turns about as quickly (a frame
1.25 ms where it took 1.05, on a desktop).

A Stratocaster is drawn again about 5 seconds after a change (on a
desktop; a phone takes longer): the design's own build most of it, the
meshes about a second; a design drawn before comes back in about 1.5 (its
build kept), and a detail set ticked in a fraction of one (the last few
designs' parts and sets kept). The first time takes a few more, loading
Python and three.js.
The page answers meanwhile: its longest pause is about 0.15 seconds.
