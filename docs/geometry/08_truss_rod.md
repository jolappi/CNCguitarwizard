# Truss-rod channel

Prototype001 uses a centered double-action truss rod, routed as a plain
channel that steps down twice at the adjusting end:

| Part | Width | Depth | Length |
| --- | ---: | ---: | ---: |
| Channel (`truss_rod_width`, `_depth`) | 6 mm | 7.5 mm | the rest of the route |
| Step (`truss_rod_step_*`) | 7.5 mm | 10.5 mm | 14 mm |
| Pocket (`truss_rod_pocket_*`) | 9 mm | 11 mm | 32 mm |
| Adjuster sleeve bore (`truss_rod_sleeve_*`, heel only) | Ø 9 mm | on the rod's axis | 12 mm |
| Adjuster head (`truss_rod_nut_*`, on the body side) | Ø 15 mm | | 6 mm |

## Rod length

Rods are sold by overall length, adjuster head included, in 20 mm steps
(420, 440, 460 mm…), and only the thin part grows from one to the next.
`Prototype001Parameters.truss_rod_fit(outline)` returns a `TrussRodFit`:

| Field | Meaning |
| --- | --- |
| `longest` | The longest rod the neck takes: the route from `truss_rod_start` (12 mm from the nut; at the headstock, the nut shelf) to the adjusting end, plus what lies outside it (`outside`: the head, and at the heel the 12 mm sleeve) |
| `recommended` | The longest of `truss_rod_stock_lengths` (300–600 mm every 20 mm, `TRUSS_ROD_STOCK_LENGTHS`) that fits |
| `rod_length` | The rod routed for: `truss_rod_rod_length`, or else `recommended` |
| `route_length` | The channel, step and pocket: `rod_length - outside` |

The adjusting end stays put, so a shorter rod moves the anchor end toward
it: at the heel the route still ends where the sleeve's bore starts, and
from the headstock it still starts under the nut. The default six-string
neck (24 frets, 25.5") takes up to 455 mm and gets a 440 mm rod; the
seven-string 480 mm, the bass 600 mm. A `truss_rod_rod_length` longer
than the neck takes is rejected, naming the longest stock rod that fits;
`truss_rod_length` sets the route by hand instead, from `truss_rod_start`.
The build report (`build.json`, `truss_rod`) and the web app's summary
give the rod, its route, the longest the neck takes and the recommended
stock length.

The rod's axis lies
`truss_rod_axis_depth` below the glue face: 7.5 mm, as measured on the
rod (0 puts it half the pocket's width above the pocket's floor); the
sleeve's bore and the head centre on it.

```python
from cncguitarwizard.geometry.neck import NeckOutline, TrussRodChannel

neck = NeckOutline(609.6, 24, 42.0, 56.0, 56.0, 63.0)
channel = TrussRodChannel(
    neck_outline=neck,
    start_position=12.0,
    length=437.2,
    width=6.0,
    depth=7.5,
    adjustment_side="heel",
    step_length=14.0,
    step_width=7.5,
    step_depth=10.5,
    pocket_length=32.0,
    pocket_width=9.0,
    pocket_depth=11.0,
    sleeve_length=12.0,
    sleeve_diameter=9.0,
    nut_diameter=15.0,
    nut_length=6.0,
    access_length=8.0,
    rod_axis_depth=7.5,
)
```

The channel validates its overall length and side clearance against the neck
outline.

## The adjusting end

- **Heel** (`truss_rod_adjustment="heel"`, the default): the route ends
  `truss_rod_sleeve_length` (12 mm) before the heel end — channel, then the
  step, then the pocket — and the adjuster's sleeve runs on to the heel end
  through a bore on the rod's axis (`TrussRodChannel.bore`). A router
  cannot cut a horizontal bore, so it is in the FreeCAD model for the fit
  and `Neck_top.nc`'s notes say where to drill it by hand. The adjuster's
  round head (Ø 15 × 6 mm) sits past the heel end on the body side, in a
  `Truss rod access` notch in the body (`BodySolid.truss_rod_access`) 1 mm
  clear of it all round, 15.5 mm deep (the axis plus the head's radius and
  0.5 mm), from 3 mm inside the neck pocket to `truss_rod_access_length`
  (the head's length + 2 mm) past its tail wall; its overlap with the
  neck pocket is allowed. An explicit rod length that ends short of the
  sleeve's bore is refused.
- **Headstock** (`truss_rod_adjustment="headstock"`): the route starts under
  the nut, at the back of the nut shelf, with the pocket and step there,
  and ends 12 mm before the heel end; the adjuster sits in a trough in the
  headstock face behind the shelf, up to 32 mm long and at least 3 mm from
  every tuner hole, as deep as at the heel. A Gibson-style truss-rod cover
  (`truss_rod_cover`, on by default) 6 mm larger than the trough, stopping
  0.5 mm short of the nut shelf, with three 3.2 mm screw holes, is cut
  from sheet as `Cover_truss_rod.nc` like the cavity covers. The route
  under the nut is open at the top (a router cannot cut a tunnel, and a
  bore drilled along the axis from the headstock would groove its angled
  face), so the nut seat is solid only either side of the 9 mm pocket;
  `Neck_top.nc`'s notes ask for a wooden filler over the fitted rod, flush
  with the seat, before the nut is glued (as Gibson fills its truss-rod
  channel). At the heel the route starts well past the nut and the seat is
  flat over the nut's whole width.

Both adjuster openings are on by default and can be left out:
`truss_rod_sleeve_bore=False` drops the heel sleeve's bore from the model
and the G-code notes (the body's notch for the head stays), and
`truss_rod_trough=False` leaves the headstock trough unrouted, and with it
its cover.

The neck G-code runs each part of the route a tool radius (3 mm) on over
its neighbour — the step over the channel's end, the pocket over the
step's, the channel's end over the step — and the pocket as far on toward
the adjuster (the sleeve's bore, or the trough). A round cutter leaves its
radius in every corner; this way no corner stands into the rod's square
step and block, at the cost of a few millimetres cut a little deeper than
the neighbour. Only the channel's anchor end is cut as drawn. The FreeCAD
model shows the route as designed.

The FreeCAD script cuts the step, pocket and trough as rows of boxes no
longer than 5 mm, which keeps FreeCAD's `check(True)` clean where their
walls cross the lofted neck top.
