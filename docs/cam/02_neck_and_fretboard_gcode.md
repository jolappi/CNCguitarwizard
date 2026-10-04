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

## Neck (`NeckMachiningParameters`, five programs, or eight laminated)

The blank's top face is the fretboard glue plane, and it is as thick as the
neck and headstock need — their deepest point below that plane — unless
`blank_thickness` asks for more. The neck itself needs 20 mm (the heel), so
a flat headstock (set down to end 20 mm below the fretboard) comes from a
plain 20 mm plank. An angled one needs more (8 degrees: 36.6 mm; a 197 mm
six-in-line at 8 degrees: 42.9 mm), and the blank is chosen with
`blank` (the web form's machining `neck_blank`):

1. `"solid"` (the default): one plank that thick, cut by the five programs
   below.
2. `"laminated"`: the neck is cut from its own 20 mm plank first, and a
   block is glued under the headstock end afterwards
   (`NeckMachiningPlan.headstock_block`: from where the headstock's back
   first falls below the plank to just past the tip, short of the tip's
   dowel; the headstock's width plus room for the outline cut; as thick
   as the plank — usually cut from the same wood — or thicker when the
   headstock needs it). The headstock then gets programs of its own:

   | Order | Program | Setup | Contents |
   | --- | --- | --- | --- |
   | 1 | `Neck_index_pins.nc` | glue face up | Both dowel holes through the plank |
   | 2 | `Neck_top.nc` | glue face up | The truss-rod route only |
   | 3–4 | `Neck_back_rough.nc`, `Neck_back_finish.nc` | flipped, Z zero on the plank's back | The neck's back from the block's start to the heel |
   | — | glue the block on | | |
   | 5 | `Headstock_top.nc` | glue face up, the neck end on a spacer as thick as the block, long dowels | The headstock face and tuner marks |
   | 6–7 | `Headstock_back_rough.nc`, `Headstock_back_finish.nc` | flipped, Z zero on the block's underside | The headstock's back and root through the full thickness |
   | 8 | `Neck_back_outline.nc` | same | The whole outline, through both layers |

The index-pin program's notes, `build.json` (`stock.Neck.blank`,
`stock.Neck.laminated`) and the web app's summary give the blank; a solid
blank's notes also offer the laminated way. Two dowels sit in the waste
beyond the headstock tip and beyond the heel, on the centerline.

| Program | Setup | Contents |
| --- | --- | --- |
| `Neck_index_pins.nc` | glue face up | Both dowel holes through the blank |
| `Neck_top.nc` | glue face up, on dowels | Truss-rod channel; the 8° headstock face as Z-limited roughing plus a finishing raster with the flat tool; the truss rod's step and pocket at its adjusting end, each run 3 mm on over its neighbour so no round corner is left for the rod's square blocks (and a headstock-adjusted rod's access trough, unless `truss_rod_trough` is off in the headstock face; the heel adjuster's sleeve bore is drilled by hand, as the notes say); 0.5 mm centre marks for the six tuner holes |
| `Headstock_engraving.nc` | same fixture and zero as `Neck_top` (with a laminated blank: right after `Headstock_top`), V-bit | The headstock lettering (`headstock_engraving_text`), each line in 1 mm passes to `headstock_engraving_depth` below the finished face, following its angle; only with lettering |
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

### Neck-through

A neck-through blank (`geometry.neck_through`) runs from the headstock tip
to the body's tail and is exactly as thick as the body (a headstock
needing more is refused: glue a block under it, `blank="laminated"`).
Its outline is the neck and the body's centre block joined
(`NeckThrough.plan`); the dowels go beyond the headstock tip and beyond
the block's tail. The back is carved only across the neck and headstock
and only up to where the body begins (the block's back is the blank's);
`Neck_back_outline` then cuts the whole outline full depth, the waste
beside the block too, with tabs. The block's own features — pickup and
bridge routes and holes, a heel-adjusted truss rod's access notch, its
share of a carve, its edges and any rear cavity reaching it — are cut by
the body's programs (`plan_body_machining` with the neck's `fixture`, no
outline cut) on the same dowels: `Neck_block_top` and the like with the
top face up, `Neck_block_back...` after the neck's back. The wings get
the body's programs each on its own blank (`Wing_bass_...`,
`Wing_treble_...`), their dowels on a line along each wing's middle.

## Fretboard (`FretboardMachiningParameters`, five programs and the inlay pieces)

The board is a flat blank `blank_thickness` (7 mm) thick, glue face down,
on two dowels beyond the nut and beyond the end. Everything is cut from
the top in one fixturing.

| Program | Tool | Contents |
| --- | --- | --- |
| `Fretboard_index_pins.nc` | flat | Both dowel holes |
| `Fretboard_radius.nc` | ball | 430 mm radius; the crown ends `blank − 6` mm below the blank top, the edges 0.9 mm lower |
| `Fretboard_inlays.nc` | 1 mm | Twelve barbed-wire pockets 2 mm below the crown, each the marker rounded to the tool (see below); barbs narrower than the tool are left out |
| `Fretboard_slots.nc` | 0.6 mm | 24 slots that follow the radius across the board, 2.7 mm below the surface, three 0.9 mm passes, 1 mm past each edge |
| `Fretboard_outline.nc` | flat | A locking nut's shelf first, when the board runs on under it; then the tapered outline with square nut corners (`fretboard_nut_corner_radius`, 0 by default) and tabs |

Under an R2 locking nut (see [Headstock](../geometry/06_headstock.md#locking-nut))
the outline runs 16 mm on past the nut line and a pocket mills that end
down to the nut's shelf, reaching past the board's sides and end so only
the wall at the nut line is left. `Neck_top.nc`'s notes say how to fit the
nut and drill its screws. A slotted Fender style nut (`nut_style` "slot")
gets its slot in `Fretboard_inlays.nc` (`Nut slot`, `nut_thickness` 3.5 mm
wide, `nut_slot_depth` 3 mm below the crown, closed behind by the board's
full-height lip, so the 1 mm inlay end mill cuts it); the outline runs on
`nut_thickness + nut_slot_lip + nut_slot_taper` (9.5 mm) past the nut
line, and `Fretboard_outline.nc` first steps the slope behind the lip
down to the glue face in 0.5 mm terraces (`SLOPE_STEP`) with the flat end
mill, to be sanded into one slope. The nut is glued in. With a zero fret
(`nut_style` "zero_fret") the slot sits `zero_fret_gap` (3 mm) behind
the nut line, the outline runs on 12.5 mm, and `Fretboard_slots.nc` cuts
the zero fret's slot on the nut line first (`Zero fret slot`).

## Inlay pieces (`Fretboard_inlay_pieces.nc`)

Barbed-wire and block markers get a sheet program of their own
(`plan_inlay_machining`, part `Inlays`); round dots do not, as they are
bought ready-made or cut from rod. Every marker becomes a piece, nested
in fret order, left to right in rows of up to 150 mm
(`INLAY_ROW_LENGTH`), each row behind the last, 3 mm apart beyond the
tool. The sheet is as thick as the pockets are deep (`inlay_depth`, 2 mm),
taped down on double-sided tape (the pieces have no tabs), show face up:
the pieces lie as on the board seen from above. The work zero is the
centre of the nested pieces, Z at the sheet top, and each piece is cut
through with the same 1 mm inlay end mill as the pockets.

Neither the pocket nor the piece can be sharper than that end mill: the
pocket keeps a tool-radius round in every corner the tool turns inside,
the piece in every corner cut into it. So both follow the marker outline
rounded both ways by the tool radius (`inlay_fit_outline`: grown and
shrunk back, then shrunk and grown back): the pocket's inner corners are
cut round where the piece's would stay full, and the piece is
`INLAY_FIT_CLEARANCE` (0.1 mm) smaller all round, so each piece drops
into its pocket. Glue the pieces in and level them with the radius.

With slanted or fanned frets (`fret_slant_angle`, `bass_scale_length`)
each slot runs along its own line, still following the radius, and the
outline's nut end and far end lean with the first and last frets.

## Checks

Tests verify that the ball finish never puts the tool below the sampled
neck-back mesh (within 0.1 mm at the steep edge zone), that roughing never
goes below the tip surface or the skin, that slots follow the radius, and
that pins lie in the waste. As with the body: run every file through a
simulator or air-cut it before the first blank, and expect to tune feeds.
