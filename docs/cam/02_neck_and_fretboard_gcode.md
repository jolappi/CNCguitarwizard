# Neck and fretboard G-code

The neck and the fretboard need 3D work — the lofted neck back and the
radiused playing surface — so `cncguitarwizard.cam` adds a small surfacing
layer on top of the 2.5D operations used for the body. It is still pure
Python: the surface is a height function `z(x, y)` in the machine frame,
`build_offset_grid` turns it into the *tool-tip surface* (the classic
drop-cutter: how low a flat or ball-nosed tool may go at each grid node
without any part of the tool cutting below the part), and the raster passes
sample that grid.

## Tools

| Tool | Used for | Defaults |
| --- | --- | --- |
| 6 mm flat end mill | index pins, truss-rod channel, headstock face, tuner marks, neck roughing, both outlines | as the body |
| 6 mm ball nose | neck back finish, fretboard radius | same feeds, `tool_tip="ball"` |
| 1 mm end mill | inlay pockets | 12 000 rpm, F300, plunge F100, 1 mm step-down |
| 0.6 mm fret-slot cutter | fret slots | 12 000 rpm, F300, plunge F100, 0.9 mm per pass |

Every program states its tool in the header. The machine has no tool
changer, so after each change the operator re-touches Z on the blank top;
X/Y zero stays at index pin 1 and every program still starts with the
pin 1 → pin 2 → pin 1 check.

## Neck (`NeckMachiningParameters`, five programs)

The blank is planed to `blank_thickness` (40 mm) with its top face the
fretboard glue plane. Two dowels sit in the waste beyond the headstock tip
and beyond the heel, on the centerline.

| Program | Setup | Contents |
| --- | --- | --- |
| `Neck_index_pins.nc` | glue face up | Both dowel holes through the blank |
| `Neck_top.nc` | glue face up, on dowels | Truss-rod channel; the 8° headstock face as Z-limited roughing plus a finishing raster with the flat tool; 0.5 mm centre marks for the six tuner holes |
| `Neck_back_rough.nc` | flipped about the centerline | Z-limited roughing of the neck back and headstock back, 3 mm layers, 60 % step-over |
| `Neck_back_finish.nc` | same, ball nose | Finishing raster along the neck, 0.75 mm step-over (≈ 0.023 mm scallop) |
| `Neck_back_outline.nc` | same, flat tool | Plan outline through the 2 mm skin, six tabs |

The back height function is the neck-back mesh where the neck exists, the
angled headstock back plane where the headstock exists (the deeper of the
two where both do), and a **skin** level everywhere else: the carve never
goes closer than `skin` (2 mm) to the glue plane, so the neck stays
attached to its waste frame, and the last 1–2 mm of the back curve at the
edges — where the D profile meets the fretboard side almost vertically — is
left for the outline cut and hand fairing. The outline pass then cuts just
the skin, lifting over the tabs.

Tuner holes are **not** drilled: they must be perpendicular to the angled
face, which a 3-axis machine cannot do with the blank flat. The program
leaves a 0.5 mm centre mark at each position on the milled face for a
drill press with an 8° wedge. Other simplifications: the nut shelf is a
straight 5 mm ledge (the model's U-shaped trim is not machined), the
headstock-root volute follows the mesh/plane union rather than the
FreeCAD fillets, and the spoke-wheel access pocket is not modelled.

## Fretboard (`FretboardMachiningParameters`, five programs)

The board is a flat blank `blank_thickness` (7 mm) thick, glue face down,
on two dowels beyond the nut and beyond the end. Everything is cut from
the top in one fixturing.

| Program | Tool | Contents |
| --- | --- | --- |
| `Fretboard_index_pins.nc` | flat | Both dowel holes |
| `Fretboard_radius.nc` | ball | 430 mm radius; the crown ends `blank − 6` mm below the blank top, the edges 0.9 mm lower |
| `Fretboard_inlays.nc` | 1 mm | Twelve barbed-wire pockets 2 mm below the crown; barbs narrower than the tool are left uncut |
| `Fretboard_slots.nc` | 0.6 mm | 24 slots that follow the radius across the board, 2.7 mm below the surface, three 0.9 mm passes, 1 mm past each edge |
| `Fretboard_outline.nc` | flat | Tapered outline with 8 mm nut corners and tabs |

## Checks

Tests verify that the ball finish never puts the tool below the sampled
neck-back mesh (within 0.1 mm at the steep edge zone), that roughing never
goes below the tip surface or the skin, that slots follow the radius, and
that pins lie in the waste. As with the body: run every file through a
simulator or air-cut it before the first blank, and expect to tune feeds.
