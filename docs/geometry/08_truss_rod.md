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
  and ends 12 mm before the heel end; the adjuster is reached from the
  headstock face behind the shelf (see *Spoke wheel or not*), every
  trough at least 3 mm from every tuner hole in plan. Behind a shelf nut
  a Gibson-style truss-rod cover (`truss_rod_cover`, on by default) 6 mm
  larger than the trough, stopping 0.5 mm short of the nut shelf, with
  three 3.2 mm screw holes, is cut from sheet as `Cover_truss_rod.nc`
  like the cavity covers. The pocket and step then lie in the neck by the
  nut, which thins to the first fret's wood (11 mm on the default 17 mm
  neck): a standard rod's 11 mm pocket would break through its back, so
  the neck is made thick enough at the first fret to leave
  `TRUSS_ROD_MIN_FLOOR` (1 mm) under each part at its edges, where the D
  profile has curved up — 18.3 mm instead of 17 on the default neck
  (`first_fret_thickness_needed()`; a thicker `first_fret_thickness` is
  kept). A low-profile rod (below) needs no thicker neck. The route
  under the nut is open at the top (a router cannot cut a tunnel, and a
  bore drilled along the axis from the headstock would groove its angled
  face), so the nut seat is solid only either side of the 9 mm pocket;
  `Neck_top.nc`'s notes ask for a wooden filler over the fitted rod, flush
  with the seat, before the nut is glued (as Gibson fills its truss-rod
  channel). At the heel the route starts well past the nut and the seat is
  flat over the nut's whole width.

### Spoke wheel or not

`truss_rod_spoke_wheel` (`"auto"`, `"yes"`, `"no"`) says whether the
adjuster is a spoke wheel; `"auto"` fits one at the heel and none at the
headstock, on a standard rod only (`Prototype001Parameters.truss_rod_spoke_wheel_fitted`).

- **Heel, wheel**: as above — the sleeve's bore and the wheel past the
  heel end in the body's notch.
- **Heel, no wheel**: no bore can be routed there, so none is needed: the
  route runs right out through the heel's end, the rod's adjuster nut at
  the heel's end face (the whole rod lies in the route, `outside` 0), and
  the body gets no notch. It is turned with the neck off, as on a vintage
  Telecaster.
- **Headstock, wheel**: the wheel sits in an open trough behind the nut
  (seat), the head's length + 4 mm long and its width + 2 mm wide, 15.5
  mm deep, with no cover. The headstock's root by the nut must leave
  `TRUSS_ROD_MIN_FLOOR` under it: an angled headstock is only its
  thickness (16 mm) deep there, so a wheel needs a flat headstock (set
  down, 20 mm) or a thicker one; otherwise the build stops and says so.
- **Headstock, no wheel**: the key reaches the adjuster through a hole
  along the rod's axis, and a router can cut only its open start: a notch
  `truss_rod_key_hole_diameter` (8 mm) wide, the head's length + 2 mm
  long, down to the axis plus the key's radius (11.5 mm; `access_diameter`,
  `TrussRodChannel.adjuster_boundary`) — a trough for the head would
  break through an angled headstock's root. It is covered behind a shelf
  nut and open behind a slotted one; `Neck_top.nc`'s notes say to drill
  any longer hole on by hand.

### Low-profile rod

`truss_rod_profile="low_profile"` routes for a low-profile two-way rod,
as StewMac's and Hosco's Hot Rod Low-profile (a straight 1/4 × 3/8 in
channel measured from the fretboard's glue face, adjusted with a 4 mm hex
key; others, such as Next Gen's Low Pro at 6.25 × 9.25 mm, fit the same
channel): one straight channel `truss_rod_low_profile_width` ×
`truss_rod_low_profile_depth` (6.35 × 9.5 mm), with no step or pocket,
its adjuster centred in it (axis 4.75 mm down). It leaves 1.5 mm of wood
under it on the default 17 mm neck, so it needs no thicker neck at the
headstock. `"auto"` fits it no spoke wheel: at the heel its adjuster sits
at the heel's end face, at the headstock it is reached through the key's
notch.

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

## Carbon fibre reinforcement

`neck_carbon_rods` sets two carbon fibre bars into the neck's top, one
each side of the truss rod, glued flush under the fretboard: they
stiffen the neck against bending and twist (`geometry.neck.CarbonRods`).
`neck_carbon_rod_size` picks the bars' section (`CARBON_ROD_SIZES`): 3.2 ×
6.35 mm (1/8 × 1/4 in, the default), 4 × 4 mm or StewMac's 3.2 × 9.5 mm
(1/8 × 3/8 in); "custom" takes `neck_carbon_rod_width` ×
`neck_carbon_rod_depth`. Each channel is `CLEARANCE` (0.1 mm) wider for
the epoxy.
They run from `neck_carbon_rod_start` (20 mm) past the nut for
`neck_carbon_rod_length` — empty, to where the heel flattens, clear of a
bolt-on neck's screws (387 mm on the default guitar, 537 mm on the bass)
— `neck_carbon_rod_offset` from the centerline: empty, beside the truss
rod's widest part along them with `CARBON_ROD_GAP` (3 mm) of wood between
(8.4 mm; 9.15 mm with a headstock-adjusted rod's pocket). Each channel
must leave `CARBON_ROD_FLOOR` (2 mm) of wood under it out to its edge,
along its whole length, and `CARBON_ROD_WALL` (2 mm) to the truss rod's
route and the neck's sides: StewMac's 1/8 × 3/8 in bars are refused in
the default 17 mm neck (0.2 mm left under them at the start).

`Neck_carbon_rods.nc` cuts the channels after `Neck_top` on the same
fixture with a 3 mm end mill (`CARBON_ROD_TOOL`; the main tool is wider
than they are), no finishing allowance, in 1.5 mm passes; its notes give
the bars' length to cut. The FreeCAD model cuts the channels from the
neck and shows the bars as an object of their own (`CarbonRods`); the
plan view dashes them under the fretboard.
