# The 3D formats made in the browser (`backends.occt`)

The web app makes the finished model's other 3D formats itself, as files,
with no FreeCAD: *Other 3D formats* under *Downloads* gives STEP, STL, 3MF,
OBJ, GLB (glTF) or BREP, each a ZIP with every solid part a file of its own
(`Prototype001_Body.stl`, `Prototype001_NeckBack.stl`...) and the whole
guitar one more (`Prototype001.stl`), named as FreeCAD's export script names
them (`backends.freecad.formats`).

## The same model as FreeCAD's

The model is not made again some other way: the build's own FreeCAD script
(`Prototype001_freecad.py`) runs as it is, on OpenCascade, the geometry
kernel FreeCAD's `Part` workbench itself stands on, compiled for the web
(`replicad-opencascadejs` 1.1.0, from jsDelivr, about 23 MB, 7 MB as sent,
kept by the browser).

`freecad_api` is FreeCAD's `FreeCAD` and `Part` modules over it, as much of
them as the scripts use: vectors, rotations and placements (in plain
Python), polygons, faces, wires, line segments and arcs, B-spline surfaces
(the carved top), boxes, cylinders, cones (a ruled loft of their ends),
lofts, extrusions, cuts, fuses and commons (many tools at once, with a
fuzzy value), `removeSplitter`, fillets, 2D offsets, compounds (a cut
takes each of a compound's members as a tool of its own: this
OpenCascade takes a tool's parts as never overlapping, and an epoxy
tray's walls may, where FreeCAD's newer one copes), copies, a shape's
volume, box (its gap left out, as FreeCAD's), solids, faces, wires, edges and
vertices (each once: this OpenCascade has no shape map, so they are told
apart by their rounded boxes and `IsSame`), and a document of
`Part::Feature`s with labels, visibility and placements (a tilted neck's).
`connect` puts the two modules where the script's `import FreeCAD` and
`import Part` find them; there is no window (`FreeCAD.GuiUp` is false), and
the script's own `saveAs` and `Part.export` write nothing.

`model.build` runs the script and keeps its solid parts, each placed as it
is shown (once a script: the next format reuses them); `model.files` writes
one format: STEP with OpenCascade's STEP writer, BREP with `BRepTools`, the
meshes (`meshes`: binary STL, OBJ with an object a part, 3MF in mm, GLB in
metres with a colour a part) from OpenCascade's triangulation within
`MESH_LINEAR_DEFLECTION` (0.05 mm) of the surface, each face's triangles
turned to face outward. IGES is not offered: its writer is not in this
build of OpenCascade (FreeCAD's export script and the command line still
write it).

Built in the browser and in FreeCAD 1.1, the parts' volumes agree:

| Design | Parts (mm³) |
| --- | --- |
| Default bolt-on | body 3 176 647.8, neck 356 488.4, fretboard 127 436.4: the same |
| Engraved, lettered, bound | body 3 150 947.4, neck 356 488.4, fretboard 120 208.3, binding 7 440.9: the same |
| Neck-through, bevels, runes, carbon rods | block, wings, fretboard and rods the same; the neck 441 465.8 against 441 465.3 |
| Set neck, pointed volute, locking nut, scallops | body 3 048 226.3, neck 363 917.5, fretboard 122 553.9: the same |
| Stepped top (Alexi Hexed) | body 2 998 683.2, fretboard 128 581.9: the same; the neck 355 876.1 against 355 876.3 |
| Epoxy tray, flared round heel, vintage rod, nut jig | body 2 958 585.9, neck 349 726.9, fretboard 127 221.6, walnut strip 14 370.5, plug 1 358.5, jig 762.4: the same |

## In the page

`site/model_worker.js` is a module worker: Pyodide, the same wheel as the
page, and OpenCascade, loaded the first time a format is asked for. The page
(`exportModel`) sends it the last build's script, the format and the
guitar's name, shows its progress in the status line, and saves the ZIP it
returns; the page stays free meanwhile. One worker holds one model:
OpenCascade keeps everything it makes, so a new build's script gets a fresh
worker rather than a second model in the first (a few models in one would
crowd its memory). A first format takes the model's build: about a
minute for the default guitar, a few for a set neck or a neck-through,
and a quarter of an hour for a body bevelled round its edges (the
Mockingbird's: its edge finishes are one cut of some forty tools, 105 s
in FreeCAD, which uses every core, and over ten minutes here, on one).
The page shows the time spent meanwhile. The next formats only write,
in seconds (a STEP of the Mockingbird in 20 s).

## Tests

The writers are tested on small meshes (`tests/backends/occt/test_meshes.py`);
the scripts of every kind of design (bolt-on, set, neck-through, engraved,
stepped, carved, epoxy, a vintage rod, a locking nut) are read for every
name they use of FreeCAD's, each of which must be here
(`test_freecad_api.py`). OpenCascade itself runs only in the browser, where
the volumes above were compared.
