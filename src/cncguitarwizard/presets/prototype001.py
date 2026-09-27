"""Locked but configurable parameters for the first complete neck."""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Literal

from ..geometry.body import (
    BRIDGE_MAX_STRINGS,
    BodySolid,
    BridgeMounting,
    BridgeSpec,
    Cavity,
    ContourCut,
    CoverPlate,
    DrilledHole,
    EdgeProfile,
    HardtailSpec,
    JackHole,
    KahlerBridgeSpec,
    RearCavity,
    TracedCavity,
    TracedOutline,
    TuneOMaticSpec,
    outlines_overlap,
    turned_hardware,
)
from ..geometry.exceptions import BodyGeometryError, NeckGeometryError
from ..geometry.fretboard import (
    Fretboard,
    FretboardSurface,
    FretLayout,
    FretSkew,
    InlayLayout,
    InlayStyle,
)
from ..geometry.neck import (
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    NeckBackSurface,
    NeckOutline,
    Side,
    TrussRodChannel,
    TunerLayout,
)
from ..geometry.primitives import Point2D, point_in_polygon, rounded_polygon_points
from .body_shapes import (
    BASS_BODY,
    BODY_WIDENING_PER_STRING,
    BodyShapeSpec,
    DesignByJoneShape,
    widened_shape,
)
from .controls import (
    SCREW_CLEARANCE,
    ControlFeatures,
    ControlLayout,
    battery_features,
    control_features,
)
from .pickups import (
    PICKUP_CONFIGURATIONS,
    PickupConfiguration,
    PickupType,
    pickup_half_length,
    pickup_route,
    pickup_screws,
)

Instrument = Literal[
    "electric_guitar", "seven_string_guitar", "eight_string_guitar", "bass_guitar"
]
"""Which instrument's defaults a parameter set starts from."""

MAX_FRET_SLANT_ANGLE = 10.0
"""The largest fret slant accepted, in degrees."""

NECK_FERRULE_BODY_WALL = 1.0
"""Least wood, in mm, between a neck-bolt ferrule and the body's edge, and
between two ferrules."""

CONTROL_CLEARANCE_SHIFT = 20.0
"""How far, in mm, a generated control cavity may move out from the
centreline to clear a deep top route (see ``_placed_controls``)."""

MAX_MULTISCALE_RATIO = 1.15
"""The longest bass scale accepted, as a multiple of the treble scale."""

HeadstockStyle = Literal[
    "3+3",
    "6_inline",
    "6_inline_reverse",
    "4+2",
    "2+4",
    "2+2",
    "4_inline",
    "4_inline_reverse",
    "4+3",
    "3+4",
    "7_inline",
    "7_inline_reverse",
    "4+4",
    "8_inline",
    "8_inline_reverse",
]
"""Tuner arrangements: bass+treble counts; "reverse" puts the row on the treble side."""

HEADSTOCK_STYLES: dict[str, tuple[int, int]] = {
    "3+3": (3, 3),
    "6_inline": (6, 0),
    "6_inline_reverse": (0, 6),
    "4+2": (4, 2),
    "2+4": (2, 4),
    "2+2": (2, 2),
    "4_inline": (4, 0),
    "4_inline_reverse": (0, 4),
    "4+3": (4, 3),
    "3+4": (3, 4),
    "7_inline": (7, 0),
    "7_inline_reverse": (0, 7),
    "4+4": (4, 4),
    "8_inline": (8, 0),
    "8_inline_reverse": (0, 8),
}
"""Tuner counts on the (bass, treble) side for every headstock style."""

HEADSTOCK_RESERVES: dict[
    str, tuple[tuple[float | None, float | None], tuple[float | None, float | None]]
] = {
    "6_inline": ((36.0, None), (35.0, 60.0)),
    "6_inline_reverse": ((36.0, None), (35.0, 60.0)),
    "4+2": ((36.0, 15.0), (40.0, 30.0)),
    "2+4": ((36.0, 15.0), (40.0, 30.0)),
    "4_inline": ((40.0, None), (45.0, 60.0)),
    "4_inline_reverse": ((40.0, None), (45.0, 60.0)),
    "4+3": ((36.0, 15.0), (40.0, 30.0)),
    "3+4": ((36.0, 15.0), (40.0, 30.0)),
    "7_inline": ((36.0, None), (35.0, 60.0)),
    "7_inline_reverse": ((36.0, None), (35.0, 60.0)),
    "8_inline": ((36.0, None), (35.0, 60.0)),
    "8_inline_reverse": ((36.0, None), (35.0, 60.0)),
}
"""Least (shoulder, tip) half-widths kept on the row side and the other side.

``None`` leaves that end to the edge fitted through the holes.

Wood left in the blank so a traditional outline can still be carved from
it: a Strat headstock's treble lobe beside a six-in-line row (the row's
own edge follows its posts, which sit on the strings' lines and so run
diagonally across the centreline), a Music Man's root lobe and narrow tip
around 4+2. A 3+3 has no reserve; its edges follow the holes exactly.
"""


@dataclass(frozen=True, slots=True)
class Prototype001Geometry:
    """Contain every backend-independent component of Prototype001."""

    neck_outline: NeckOutline
    neck_surface: NeckBackSurface
    fretboard_surface: FretboardSurface
    fret_layout: FretLayout
    truss_rod_channel: TrussRodChannel
    headstock: HeadstockSolid
    tuner_layout: TunerLayout
    inlay_layout: InlayLayout
    body: BodySolid
    fret_slot_width: float
    fret_slot_depth: float
    tuner_chamfer_depth: float
    joint_fillet_radius: float
    headstock_root_swell: float
    nut_end_u_trim_depth: float
    nut_end_u_side_fillet_radius: float
    headstock_outer_d_profile_guide_extension: float
    heel_nose_radius: float
    heel_block_start_offset: float
    covers: tuple[CoverPlate, ...] = ()
    """Cavity covers and control plates, each cut from sheet."""


@dataclass(frozen=True, slots=True)
class BodyLayout:
    """A body's outline and every feature cut into it, not yet validated.

    Args:
        heel_end: X of the neck pocket's end; shape placements are
            measured from here.
        outline: The body silhouette.
        neck_pocket: The pocket the neck heel sits in.
        bridge_pickup: The bridge pickup route, or ``None``.
        neck_pickup: The neck pickup route, or ``None``.
        bridge_mounting: Bridge reference line and pivot studs.
        jack_hole: The output jack bore.
        control_cavity: The rear control cavity with its cover recess.
        switch_cavity: The rear switch cavity with its cover recess.
        extra_cavities: The bridge's top routes.
        holes: Drilled holes (switch, pots, pickup screws, bridge).
        through_cavities: Routes that open into a rear cavity.
        extra_rear_cavities: The bridge's rear cavities.
        middle_pickup: The middle pickup route, or ``None``.
        rear_holes: Holes drilled from the back (the neck-bolt ferrules
            and bolt holes).
        controls: The electronics layout's cavities, screw spots and
            cover plates (see ``controls.control_features``).
        top_edge: The top edge's roundover or binding channel.
        back_edge: The back edge's roundover or binding channel.
        contours: The arm contour and belly cut that are switched on.
        truss_rod_access: The notch past the neck pocket for a
            heel-adjusted truss rod's spoke wheel, or ``None``.
    """

    heel_end: float
    outline: TracedOutline
    neck_pocket: TracedCavity
    bridge_pickup: TracedCavity | None
    neck_pickup: TracedCavity | None
    bridge_mounting: BridgeMounting
    jack_hole: JackHole
    control_cavity: RearCavity | None
    switch_cavity: RearCavity | None
    extra_cavities: tuple[Cavity, ...]
    holes: tuple[DrilledHole, ...]
    through_cavities: tuple[Cavity, ...]
    extra_rear_cavities: tuple[RearCavity, ...]
    middle_pickup: TracedCavity | None = None
    rear_holes: tuple[DrilledHole, ...] = ()
    controls: ControlFeatures = field(default_factory=ControlFeatures)
    top_edge: EdgeProfile = field(default_factory=EdgeProfile)
    back_edge: EdgeProfile = field(default_factory=EdgeProfile)
    contours: tuple[ContourCut, ...] = ()
    truss_rod_access: TracedCavity | None = None


TRUSS_ROD_STOCK_LENGTHS: tuple[float, ...] = tuple(
    float(length) for length in range(300, 601, 20)
)
"""Truss rods as sold: 300 to 600 mm overall in 20 mm steps."""


@dataclass(frozen=True, slots=True)
class TrussRodFit:
    """How a truss rod fits the neck (see ``Prototype001Parameters.truss_rod_fit``).

    Args:
        longest: The longest rod, overall, the neck takes: its route from
            ``truss_rod_start`` (or the nut shelf) to the adjusting end.
        recommended: The longest stock length (``truss_rod_stock_lengths``)
            that fits, or ``None`` when none does.
        rod_length: The rod the neck is routed for: ``truss_rod_rod_length``,
            else ``recommended``; ``None`` when ``truss_rod_length`` sets
            the route directly.
        route_length: The routed channel, step and pocket together.
        outside: How much of the rod lies outside the route: the adjuster's
            head, and at the heel its sleeve in the hand-drilled bore.
    """

    longest: float
    recommended: float | None
    rod_length: float | None
    route_length: float
    outside: float


@dataclass(frozen=True, slots=True)
class _HeadstockLayout:
    """The resolved headstock plan settings and tuner stations of a style."""

    length: float
    shoulder_width: float
    shoulder_shift: float
    tip_width: float
    tip_shift: float
    bass_sign: float
    stations: tuple[float, ...]
    sides: tuple[Side, ...] | None
    offsets: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class Prototype001Parameters:
    """Define the complete first CNCguitarwizard neck in millimetres.

    First- and twelfth-fret thicknesses are total centerline dimensions from
    the playing surface to the neck back. Heel thickness describes neck wood
    below the separate fretboard, matching the specified 20 mm + fretboard.
    """

    # instrument names the defaults this set was made from (see
    # Prototype001Parameters.for_instrument); string_count is what the
    # tuner layout, bridge and pickups actually follow.
    instrument: Instrument = "electric_guitar"
    string_count: int = 6
    scale_length: float = 609.6
    fret_count: int = 24
    # fret_slant_angle tilts every fret, and the fretboard's nut and far
    # ends with them, about the centerline (degrees; positive moves each
    # fret's treble end toward the bridge). Fret spacing stays exact on
    # the centerline; the bridge and pickups are unchanged.
    fret_slant_angle: float = 0.0
    # Multiscale (fanned frets): with bass_scale_length set, scale_length
    # is the treble (outermost string's) scale and bass_scale_length the
    # bass one; perpendicular_fret is square to the neck (0 = the nut).
    # Each fret runs straight through its exact positions on the two
    # outer strings, the centerline gets the mean scale, and the pickups
    # turn with the frets. The bridge stays square on the centerline
    # scale, each saddle set to its string's scale — except a
    # Tune-o-matic's posts, as its saddles have too little travel, which
    # always turn to the fanned bridge line (its stop-bar studs stay),
    # and a hardtail's holes when body_bridge_follows_fan is on.
    # body_pickups_follow_fan turns the pickups to the frets: "auto" turns
    # them except with a Tune-o-matic, "yes" and "no" always and never.
    bass_scale_length: float | None = None
    perpendicular_fret: float = 7.0
    nut_width: float = 42.0
    final_fret_width: float = 56.0
    heel_width: float = 56.0
    heel_mounting_length: float = 54.0
    heel_length: float = 4.0
    fretboard_end_extension: float = 4.0
    # Square nut-end corners: the board meets the nut with no rounding.
    fretboard_nut_corner_radius: float = 0.0
    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0
    heel_thickness: float = 20.0
    fretboard_radius: float = 430.0
    fretboard_thickness: float = 6.0
    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
    # Position markers, cut as flat-bottomed pockets into the playing
    # surface: barbed wire (default), round dots, or Gibson-style blocks
    # that follow the taper. 12 and 24 get the traditional double layout
    # (blocks stay single); every other listed fret gets one marker.
    inlay_depth: float = 2.0
    inlay_single_marker_frets: tuple[int, ...] = (3, 5, 7, 9, 15, 17, 19, 21)
    inlay_double_marker_frets: tuple[int, ...] = (12, 24)
    inlay_style: InlayStyle = "barbed_wire"
    inlay_dot_diameter: float = 6.0
    inlay_block_length_fraction: float = 0.6
    inlay_block_edge_margin: float = 5.0
    # Solid body (left-handed): outline, pickup routes, bridge baseplate
    # cutout, and the rear control and switch cavities (each with its
    # cover recess) are all digitised directly from the user's own
    # assets/reference/omarunko.dxf (see _omarunko_outline.py) — the actual
    # shapes, not an approximation. The baseplate cutout depth remains a placeholder
    # (no Kahler 7300 manufacturer template was available).
    body_thickness: float = 44.0
    # The neck pocket is the neck's own tapered outline over the last
    # body_neck_pocket_length millimetres before the heel end, widened
    # by body_neck_pocket_clearance per side. It ends exactly where the
    # heel ends, opens onto the horn gap at its nut-ward end as in the
    # drawing, and follows any change of scale, fret count or neck
    # width by construction.
    body_neck_pocket_length: float = 79.48
    body_neck_pocket_clearance: float = 0.15
    # Longitudinal placements are offsets, not absolute positions. The
    # traced body — outline, neck pickup, control and switch cavities,
    # pots, jack — rides with the neck's heel end; the bridge features
    # — baseplate cutout, bridge pickup — ride with the scale length.
    # A different scale or fret count therefore keeps the neck in its
    # pocket and the bridge on the scale, and only the bridge's place
    # on the body changes. The defaults are the DXF's own distances.
    # Pickup routes use the drawing's own route shape
    # (OMARUNKO_PICKUP_ROUTE_LOCAL_POINTS, a humbucker with mounting-ear
    # tabs).
    body_neck_pickup_offset: float = 30.5  # route centre past the heel end
    # The bridge pickup sits body_bridge_pickup_offset ahead of the scale
    # line, but moves further forward on its own when the chosen bridge's
    # routes reach ahead of the scale line (a recessed Floyd Rose), keeping
    # body_bridge_pickup_clearance of wood between route and recess.
    body_bridge_pickup_offset: float = 21.73  # route centre before the bridge
    body_bridge_pickup_clearance: float = 3.0
    body_pickup_route_depth: float = 22.0
    # body_pickups picks a named layout (see PICKUP_CONFIGURATIONS): HH,
    # HSH, HSS, H, SSS, SS for a guitar, PJ, JJ, P, MM for a bass. With
    # "custom" each position takes its own type from body_neck_pickup /
    # body_middle_pickup / body_bridge_pickup: the guitar humbucker or
    # single coil, a Jazz Bass single coil, a Precision Bass split coil,
    # a bass soapbar humbucker, or none. The middle pickup sits
    # body_middle_pickup_offset past the heel end, or, left empty, in the
    # middle of the gap between the neck and bridge routes. A bridge
    # single coil slants body_bridge_single_coil_angle degrees, its treble
    # end toward the bridge, as on a Strat.
    body_pickups: PickupConfiguration = "HH"
    body_neck_pickup: PickupType = "humbucker"
    body_middle_pickup: PickupType = "none"
    body_bridge_pickup: PickupType = "humbucker"
    body_middle_pickup_offset: float | None = None
    body_bridge_single_coil_angle: float = 10.0
    # Clearance recesses for the pickup height-adjustment screw tips,
    # drilled on down from the route floor at the centre of each of the
    # route's two mounting-ear tabs (the DXF ears are centred 39.95 mm
    # either side of the string line).
    body_pickup_screw_spacing: float = 79.9
    body_pickup_screw_recess_diameter: float = 6.0
    body_pickup_screw_recess_extra_depth: float = 8.0
    # The bridge is an interchangeable spec (see geometry.body.bridges):
    # KahlerBridgeSpec (default, the DXF's flat-mount 7300 cutout),
    # FloydRoseSpec, TuneOMaticSpec or HardtailSpec. Each places its own
    # routes, rear cavities and holes relative to the scale line. In the
    # web form it is edited as JSON with a "kind" entry.
    body_bridge: BridgeSpec = field(default_factory=KahlerBridgeSpec)
    # The body shape is an interchangeable spec (see body_shapes): the
    # user's own Design by Jone outline traced from the DXF (default) or
    # a Stratocaster-inspired silhouette. Each carries its own outline
    # and the placements that belong to the silhouette - switch cavity,
    # pot holes, jack - measured from the heel end; the rear cavities
    # themselves keep the DXF's shapes. In the web form it is a dropdown
    # of kinds with the chosen kind's placements beneath it.
    body_shape: BodyShapeSpec = field(default_factory=DesignByJoneShape)
    body_bridge_follows_fan: bool = False
    body_pickups_follow_fan: Literal["auto", "yes", "no"] = "auto"
    # body_widening opens the body along its centreline for a wider neck:
    # each half, with its cavities, pots, switch and jack, moves out by
    # half of it. Left empty it is BODY_WIDENING_PER_STRING (12 mm) for
    # every string past six, so a seven- or eight-string heel and its
    # longer pickups fit a shape drawn for six strings.
    body_widening: float | None = None
    # Edge finishes, all optional (0 = off). body_top_edge_radius /
    # body_back_edge_radius round the edges over; instead of a roundover
    # an edge can take a binding channel body_*_binding_width wide and
    # body_*_binding_depth deep. body_arm_contour_depth bevels the top
    # over the bass-side rear bout (a Strat-style arm contour),
    # reaching body_arm_contour_width in from the edge and fading out
    # along body_arm_contour_length of it; body_belly_cut_* does the same
    # on the back of the bass-side upper bout (a belly cut). Each is
    # deepest at the bout's outermost point, or at body_*_position (X
    # from the heel end) when that is set.
    body_top_edge_radius: float = 0.0
    body_back_edge_radius: float = 0.0
    body_top_binding_width: float = 0.0
    body_top_binding_depth: float = 6.0
    body_back_binding_width: float = 0.0
    body_back_binding_depth: float = 6.0
    body_arm_contour_depth: float = 0.0
    body_arm_contour_width: float = 60.0
    body_arm_contour_length: float = 240.0
    body_arm_contour_position: float | None = None
    body_belly_cut_depth: float = 0.0
    body_belly_cut_width: float = 70.0
    body_belly_cut_length: float = 260.0
    body_belly_cut_position: float | None = None
    # Rear-routed electronics cavities are cut up from the back face to
    # within body_rear_cavity_top_wall of the top so the pot and switch
    # bushings can pass through, and closed by a cover plate seated in a
    # body_cover_recess_depth ledge (the drawing's own outer ring/circle
    # around each cavity).
    # body_controls picks the electronics layout (see controls.py): the
    # Design by Jone almond with 2 pots, a Gibson-style cavity with 4, a
    # rear cavity with 3 in a row, a Telecaster-style plate in the top, or
    # none. Each cover plate is cut from sheet in its own program.
    body_controls: ControlLayout = "almond_2"
    body_rear_cavity_top_wall: float = 8.0
    body_cover_recess_depth: float = 2.0
    # An optional 9 V battery box (for active pickups or a preamp) routed
    # from the back: body_battery_cavity_length x _width (a 9 V battery is
    # 48.5 x 26.5 x 17.5 mm; the room left is for its snap and wires),
    # body_battery_cavity_depth up from the back face, closed by a plate in
    # a recess body_battery_cover_margin wider all round and
    # body_cover_recess_depth deep, held by two screws at the box's ends.
    # The body shape's battery_offset, battery_y and battery_angle_degrees
    # place it. The wire to the control cavity is drilled by hand.
    body_battery_box: bool = False
    body_battery_cavity_length: float = 56.0
    body_battery_cavity_width: float = 30.0
    body_battery_cavity_depth: float = 22.0
    body_battery_cover_margin: float = 7.0
    # Shaft holes through the top wall: a 1/2" toggle bushing at the
    # switch cavity's centre, and 3/8" pot bushings at the shape's pot
    # positions.
    body_switch_shaft_hole_diameter: float = 12.7
    body_pot_shaft_hole_diameter: float = 10.0
    # Output jack bore, in from the edge at the shape's jack position.
    body_jack_diameter: float = 12.5
    body_jack_depth: float = 55.0
    # Bolt-on neck: the body shape's own neck_bolts, or else four bolts
    # in a rectangle centred across the neck, body_neck_bolt_spacing_x
    # along it and _y across it, the tail pair as close to the pocket's end
    # as the bolt hole allows (body_neck_bolt_end_wall of wood between the
    # hole and the neck's heel end; no bolt may come closer: the further
    # apart the bolts along the neck, the better they hold it) unless
    # body_neck_bolt_center_offset puts the pattern's centre that far
    # ahead of the heel end. With body_neck_bolts_outward (the default)
    # every bolt then moves out across the neck, as far from the truss rod
    # as it can go (3 mm of wood to the rod is the least): until
    # body_neck_bolt_edge_wall of wood is left beside its hole to the
    # neck's edge, or its ferrule keeps 1 mm of wood to the body's edge.
    # Each bolt gets a ferrule counterbore in the back of the body (it may
    # run past the neck pocket, never out of the body) and a bolt hole on
    # from its floor to the neck pocket.
    body_neck_bolt_spacing_x: float = 32.0
    body_neck_bolt_spacing_y: float = 40.0
    body_neck_bolt_center_offset: float | None = None
    body_neck_bolt_end_wall: float = 3.0
    body_neck_ferrule_diameter: float = 14.0
    body_neck_ferrule_depth: float = 5.0
    body_neck_bolt_hole_diameter: float = 5.0
    body_neck_bolt_edge_wall: float = 5.0
    body_neck_bolts_outward: bool = True
    # Truss rod: a plain channel truss_rod_width x truss_rod_depth, then,
    # at the adjusting end, a step (truss_rod_step_*) and a wider, deeper
    # pocket (truss_rod_pocket_*) for the rod's anchor and adjuster. The
    # rod's axis lies truss_rod_axis_depth below the neck's top (the
    # fretboard's glue face): the adjuster's sleeve bore and head centre
    # on it.
    # truss_rod_adjustment picks the adjusting end. "heel": the route ends
    # truss_rod_sleeve_length before the heel end, the adjuster's sleeve
    # runs on through a bore of truss_rod_sleeve_diameter (drilled by hand;
    # a router cannot cut it) and its round head, truss_rod_nut_diameter x
    # truss_rod_nut_length, sits past the heel end on the body side, in a
    # notch the body's neck pocket gets truss_rod_access_length past its
    # end. "headstock": the route starts under the nut, pockets first,
    # and the adjuster sits in a trough truss_rod_access_length long in
    # the headstock face, under a truss-rod cover cut from sheet
    # (truss_rod_cover). Empty access length: the head's length + 2 mm at
    # the heel, up to 32 mm (clear of the tuners) at the headstock. An
    # Rods are sold by overall length (adjuster head included) in steps of
    # 20 mm, only the thin part growing: truss_rod_rod_length is the rod
    # in hand, the route cut for it (the adjusting end stays put, the
    # anchor end moves). Empty, it is the longest of
    # truss_rod_stock_lengths that fits between truss_rod_start (at the
    # headstock, the nut shelf) and the adjusting end: at the heel the
    # route ends where the sleeve's bore starts, from the headstock 12 mm
    # before the heel end. truss_rod_length sets the route itself instead.
    truss_rod_start: float = 12.0
    truss_rod_rod_length: float | None = None
    truss_rod_stock_lengths: tuple[float, ...] = TRUSS_ROD_STOCK_LENGTHS
    truss_rod_length: float | None = None
    truss_rod_width: float = 6.0
    truss_rod_depth: float = 7.5
    truss_rod_step_length: float = 14.0
    truss_rod_step_width: float = 7.5
    truss_rod_step_depth: float = 10.5
    truss_rod_pocket_length: float = 32.0
    truss_rod_pocket_width: float = 9.0
    truss_rod_pocket_depth: float = 11.0
    truss_rod_sleeve_length: float = 12.0
    truss_rod_sleeve_diameter: float = 9.0
    truss_rod_axis_depth: float = 7.5
    truss_rod_adjustment: Literal["heel", "headstock"] = "heel"
    truss_rod_nut_diameter: float = 15.0
    truss_rod_nut_length: float = 6.0
    truss_rod_access_length: float | None = None
    truss_rod_cover: bool = True
    # truss_rod_sleeve_bore: model the adjuster sleeve's hand-drilled bore
    # at the heel (and note it in the neck's G-code); truss_rod_trough: rout
    # the adjuster's trough in the headstock face (and cut its cover). Turn
    # either off to leave that part to be made by hand, or not at all.
    truss_rod_sleeve_bore: bool = True
    truss_rod_trough: bool = True
    # Headstock style: "3+3" mirrors tuner_station_distances /
    # tuner_side_offsets onto both sides. The row styles (six in line on
    # the bass or, for "reverse", the treble edge; 4+2 with the pair at
    # the root) space tuner_inline_* stations along the row and put every
    # post on its own string's straight line past the nut
    # (nut_string_spacing / bridge_string_spacing, the post
    # tuner_post_diameter/2 outboard of the string), so no string bends
    # at the nut. Every edge with tuners follows them tuner_edge_offset
    # further out (a line fitted through the holes), but never inside
    # the style's wood reserve (HEADSTOCK_RESERVES): a six-in-line blank
    # keeps room for a Strat outline, a 4+2 blank for a Music Man one.
    # The headstock grows past headstock_length when the last tuner
    # needs it. headstock_bass_side says where the low E is: -Y on the
    # left-handed Prototype001 body (the long-horn side). The shoulder
    # and tip widths and shifts, when set, override the resolved ends
    # (shifts toward the bass side positive).
    headstock_style: HeadstockStyle = "3+3"
    headstock_bass_side: Literal["-y", "+y"] = "-y"
    headstock_length: float = 150.0
    headstock_root_length: float = 45.0
    headstock_shoulder_width: float | None = None
    headstock_tip_width: float | None = None
    headstock_shoulder_shift: float | None = None
    headstock_tip_shift: float | None = None
    # "drawn" replaces the fitted outline with the edges drawn in the web
    # app's headstock editor: (distance from the nut, half-width) points
    # per side, each ending at the tip. The tuner holes still come from
    # headstock_style, and every hole must stay at least
    # tuner_edge_offset from the drawn edge. Empty edges fall back to
    # the fitted outline.
    headstock_outline: Literal["fitted", "drawn"] = "fitted"
    headstock_bass_edge: tuple[tuple[float, float], ...] = ()
    headstock_treble_edge: tuple[tuple[float, float], ...] = ()
    headstock_angle: float = 8.0
    headstock_thickness: float = 16.0
    tuner_hole_diameter: float = 10.0
    tuner_station_distances: tuple[float, ...] = (55.0, 85.0, 110.0)
    tuner_side_offsets: tuple[float, ...] = (15.0, 12.0, 10.0)
    tuner_inline_first_distance: float = 50.0
    tuner_inline_spacing: float = 25.4
    tuner_edge_offset: float = 15.0
    tuner_tip_margin: float = 5.0
    tuner_post_diameter: float = 6.0
    nut_string_spacing: float = 7.0
    bridge_string_spacing: float = 10.5
    tuner_edge_clearance: float = 8.0
    tuner_hole_clearance: float = 10.0
    tuner_chamfer_depth: float = 0.2
    joint_fillet_radius: float = 3.0
    heel_nose_radius: float = 0.0
    heel_block_overlap: float = 0.0
    nut_shelf_length: float = 5.0
    # A real volute is compact and sits right behind the nut, not a long
    # gradual ramp that keeps the neck close to the raw headstock thickness
    # nearly out to fret 1 (which the previous 30 mm length did: fret 1
    # falls around X=34 mm). 12 mm keeps the whole taper well clear of the
    # fretted area while still being a smooth, tangent-continuous blend.
    headstock_volute_length: float = 12.0
    # Zero: any added swell here is, by definition, a local maximum that
    # must fall back down again to reconnect with its neighbours on both
    # sides — the depth rises toward the headstock, dips back down toward
    # the nut, rises a second time, then falls again into the neck. A
    # smooth monotonic taper (no added bump, using only the existing
    # smoothstep/smootherstep easing) still reads as a single round,
    # continuous curve from neck to headstock, it just never reverses.
    headstock_volute_depth: float = 0.0
    headstock_volute_peak_fraction: float = 0.25
    headstock_root_swell: float = 0.0
    # A real reference Stratocaster neck (measured from an actual STEP
    # model) has an instant depth step and a separately, gradually
    # tapering plan-view width. The depth step in our own model is now a
    # genuine boolean seam (see _headstock_transition_sections), not a
    # blend, so this length only controls how much room the width taper
    # gets — it no longer has to also fit a depth blend into the same
    # span. 15 mm keeps that narrowing visibly gradual rather than
    # cramming the headstock's whole plan width down to the nut width in
    # just a few mm.
    headstock_root_side_extension: float = 15.0
    nut_end_u_trim_depth: float = 12.0
    nut_end_u_side_fillet_radius: float = 2.0
    headstock_outer_d_profile_guide_extension: float = 0.0
    heel_root_length: float = 45.0
    heel_scoop_depth: float = 1.5
    heel_root_center_extension: float = 15.0
    neck_profile_exponent: float = 2.0
    profile_sample_count: int = 33
    segments_per_region: int = 12

    @classmethod
    def for_instrument(cls, instrument: Instrument) -> Prototype001Parameters:
        """Return the default parameters for an instrument.

        ``"electric_guitar"`` is the plain default; ``"bass_guitar"``
        applies ``INSTRUMENT_OVERRIDES["bass_guitar"]`` — a four-string,
        34-inch-scale bass with a wider, deeper neck, four in-line 19 mm
        tuner holes, a Precision Bass neck pickup and a Jazz Bass bridge
        pickup, a four-string hardtail and the Jazz Bass style body.

        Raises:
            NeckGeometryError: For an unknown instrument.
        """
        if instrument not in INSTRUMENT_OVERRIDES:
            raise NeckGeometryError(
                f"Unknown instrument {instrument!r}; choose one of "
                f"{', '.join(INSTRUMENT_OVERRIDES)}."
            )
        return cls(instrument=instrument, **INSTRUMENT_OVERRIDES[instrument])

    @property
    def heel_flat_start_offset(self) -> float:
        """Return the derived distance from fret 24 to the flat heel start.

        ``heel_mounting_length`` is the user-facing, total length of the
        bolt-on mounting block.  The small ``heel_length`` extension after
        fret 24 is part of that total, so the flat block begins this far
        before fret 24.
        """
        return self.heel_mounting_length - self.heel_length

    @property
    def headstock_shoulder_distance(self) -> float:
        """Return the plan-view distance used to form the headstock root.

        ``HeadstockPlan`` calls this a shoulder distance.  At the preset level
        it is deliberately named a root length: it controls how far the two
        sides run smoothly from the 42 mm neck into the full headstock width.
        It does not add a bulky volute below the player's thumb.
        """
        return self.headstock_root_length

    @property
    def heel_transition_length(self) -> float:
        """Return the longitudinal runout from playing neck into heel block.

        The separately configured ``heel_mounting_length`` remains fully flat
        for the bolt-on pocket.  This root length affects only the smooth
        lead-in immediately before that fixed mounting area.
        """
        return self.heel_root_length

    def _neck_pocket_outline(
        self, outline: NeckOutline, heel_end: float
    ) -> tuple[Point2D, ...]:
        """Return the pocket polygon: the neck's own outline plus clearance.

        The pocket runs from ``heel_end - body_neck_pocket_length`` to
        ``heel_end``; between those the neck is ``nut_width`` wide at
        the nut tapering to ``last_fret_width`` at the last fret, then
        ``heel_width`` to the heel end. Every wall sits
        ``body_neck_pocket_clearance`` outside the neck.
        """
        start = heel_end - self.body_neck_pocket_length
        if start < 0.0:
            raise NeckGeometryError("Neck pocket must not reach past the nut.")
        clearance = self.body_neck_pocket_clearance
        last_fret = outline.last_fret_position

        def taper_half_width(x: float) -> float:
            fraction = x / last_fret
            return (
                outline.nut_width
                + (outline.last_fret_width - outline.nut_width) * fraction
            ) / 2.0

        stations: list[tuple[float, float]] = []
        if start < last_fret:
            stations.append((start, taper_half_width(start)))
            stations.append((last_fret, outline.last_fret_width / 2.0))
            if outline.heel_width != outline.last_fret_width:
                stations.append((last_fret, outline.heel_width / 2.0))
        else:
            stations.append((start, outline.heel_width / 2.0))
        stations.append((heel_end, outline.heel_width / 2.0))
        lower = [Point2D(x, -(half + clearance)) for x, half in stations]
        upper = [Point2D(x, half + clearance) for x, half in reversed(stations)]
        return tuple(lower + upper)

    def _headstock_layout(self) -> _HeadstockLayout:
        """Resolve the headstock plan and tuner stations for the style.

        Stations: "3+3" mirrors ``tuner_station_distances`` onto both
        sides with ``tuner_side_offsets``. A row of tuners runs
        ``max(bass, treble)`` stations ``tuner_inline_spacing`` apart along
        the fuller side from ``tuner_inline_first_distance``; a 4+2 pair
        sits at the root on the other side, staggered half a station
        opposite the row's first two.

        Posts: in the row styles every post sits on its own string's
        straight continuation past the nut (the bridge-to-nut line from
        ``bridge_string_spacing`` and ``nut_string_spacing``), the post
        radius outboard of the string, so no string bends at the nut. The
        row takes its side's strings nearest first (low E to the first
        bass post) and the pair the other side's outermost strings, so a
        six-in-line row runs diagonally across the centreline and a 4+2
        row converges toward it. A 3+3 keeps its given offsets: with both
        rows at the same stations, straight strings would put the D and G
        posts too close together.

        Outline: each edge with tuners on it is the straight line fitted
        through those holes ``tuner_edge_offset`` further out, from the
        shoulder to the tip, so every hole sits the same distance from
        its edge — but never inside the style's ``HEADSTOCK_RESERVES``,
        the wood kept for carving a Strat or Music Man outline. An edge
        with no tuners is the reserve alone. Explicit
        ``headstock_shoulder_width`` / ``headstock_shoulder_shift`` /
        ``headstock_tip_width`` / ``headstock_tip_shift`` override the
        resolved ends. The headstock grows past ``headstock_length`` when
        the last tuner needs it.
        """
        bass_sign = -1.0 if self.headstock_bass_side == "-y" else 1.0
        bass_count, treble_count = HEADSTOCK_STYLES[self.headstock_style]
        hole_edge = self.tuner_hole_diameter / 2.0 + self.tuner_edge_clearance

        # Bass-positive lateral position of string n (1 = low E) at a
        # distance past the nut, continuing its bridge-to-nut line.
        def string_u(string: int, distance: float) -> float:
            spacing = (
                self.nut_string_spacing
                + (self.nut_string_spacing - self.bridge_string_spacing)
                * distance
                / self.centre_scale
            )
            return ((self.string_count + 1) / 2.0 - string) * spacing

        stations: list[tuple[float, Side, float]] = []  # distance, side, u
        sides: tuple[Side, ...] | None
        distances: tuple[float, ...]
        offsets: tuple[float, ...]
        if bass_count == treble_count:
            for distance, offset in zip(
                self.tuner_station_distances, self.tuner_side_offsets, strict=True
            ):
                stations.append((distance, "bass", offset))
                stations.append((distance, "treble", -offset))
            length = self.headstock_length
            sides = None
            distances = self.tuner_station_distances
            offsets = self.tuner_side_offsets
        else:
            row_side: Side
            pair_side: Side
            row_side, pair_side = (
                ("bass", "treble") if bass_count >= treble_count else ("treble", "bass")
            )
            row_count = max(bass_count, treble_count)
            pair_count = min(bass_count, treble_count)
            first, spacing = self.tuner_inline_first_distance, self.tuner_inline_spacing
            row_strings = (
                list(range(1, row_count + 1))
                if row_side == "bass"
                else list(range(self.string_count, self.string_count - row_count, -1))
            )
            pair_strings = (
                list(range(self.string_count, self.string_count - pair_count, -1))
                if pair_side == "treble"
                else list(range(1, pair_count + 1))
            )
            post_radius = self.tuner_post_diameter / 2.0
            row_sign = 1.0 if row_side == "bass" else -1.0
            pair_sign = -row_sign
            # Posts on both sides follow the strings, so the middle strings'
            # posts meet near the centreline; when they would crowd each
            # other (a 4+3), stretch the station spacing just enough.
            gap = self.tuner_hole_diameter + self.tuner_hole_clearance
            for _ in range(60):
                row_distances = [first + index * spacing for index in range(row_count)]
                stations = [
                    (
                        distance,
                        row_side,
                        string_u(string, distance) + row_sign * post_radius,
                    )
                    for distance, string in zip(row_distances, row_strings, strict=True)
                ]
                # The opposite side's tuners sit between the row's stations.
                stations += [
                    (
                        first + (step + 0.5) * spacing,
                        pair_side,
                        string_u(string, first + (step + 0.5) * spacing)
                        + pair_sign * post_radius,
                    )
                    for step, string in enumerate(pair_strings)
                ]
                crowded = any(
                    math.hypot(a[0] - b[0], a[2] - b[2]) < gap
                    for index, a in enumerate(stations)
                    for b in stations[index + 1 :]
                )
                if not crowded:
                    break
                spacing += 0.5
            length = max(
                self.headstock_length,
                max(row_distances) + hole_edge + self.tuner_tip_margin,
            )
            sides = tuple(side for _, side, _ in stations)
            distances = tuple(distance for distance, _, _ in stations)
            # Offsets are measured toward the hole's own side; a row post
            # past the centreline gets a negative one.
            offsets = tuple(u if side == "bass" else -u for _, side, u in stations)

        # Edges: fit each side's line through its holes, edge_offset out,
        # never inside the style's reserve; then, keeping the shoulder
        # end, push the tip end out until the line clears every hole (a
        # row that has crossed the centreline needs room on the far side
        # too) by tuner_edge_clearance.
        root = self.headstock_root_length
        reserve = HEADSTOCK_RESERVES.get(self.headstock_style)
        row_side_of_style: Side = "bass" if bass_count >= treble_count else "treble"
        halves: dict[Side, tuple[float, float]] = {}
        for side in ("bass", "treble"):
            sign = 1.0 if side == "bass" else -1.0
            reserve_shoulder, reserve_tip = (
                (None, None)
                if reserve is None
                else reserve[0 if side == row_side_of_style else 1]
            )
            points = [
                (distance, sign * u + self.tuner_edge_offset)
                for distance, hole_side, u in stations
                if hole_side == side
            ]
            if len(points) >= 2:
                mean_d = sum(d for d, _ in points) / len(points)
                mean_e = sum(e for _, e in points) / len(points)
                slope = sum((d - mean_d) * (e - mean_e) for d, e in points) / sum(
                    (d - mean_d) ** 2 for d, _ in points
                )
                shoulder_half = mean_e + slope * (root - mean_d)
                tip_half = mean_e + slope * (length - mean_d)
                if reserve_shoulder is not None:
                    shoulder_half = max(shoulder_half, reserve_shoulder)
                if reserve_tip is not None:
                    tip_half = max(tip_half, reserve_tip)
            else:
                shoulder_half = reserve_shoulder or 0.0
                tip_half = reserve_tip or 0.0
            for distance, _, u in stations:
                fraction = (distance - root) / (length - root)
                if fraction <= 0.0:
                    continue
                required = sign * u + hole_edge + 0.01
                tip_half = max(
                    tip_half, (required - shoulder_half * (1.0 - fraction)) / fraction
                )
            halves[side] = (shoulder_half, tip_half)
        shoulder_bass, tip_bass = halves["bass"]
        shoulder_treble, tip_treble = halves["treble"]
        shoulder_width = shoulder_bass + shoulder_treble
        shoulder_shift = (shoulder_bass - shoulder_treble) / 2.0
        tip_width_final = tip_bass + tip_treble
        tip_shift = (tip_bass - tip_treble) / 2.0
        if self.headstock_shoulder_width is not None:
            shoulder_width = self.headstock_shoulder_width
        if self.headstock_shoulder_shift is not None:
            shoulder_shift = self.headstock_shoulder_shift
        if self.headstock_tip_width is not None:
            tip_width_final = self.headstock_tip_width
        if self.headstock_tip_shift is not None:
            tip_shift = self.headstock_tip_shift
        return _HeadstockLayout(
            length,
            shoulder_width,
            shoulder_shift,
            tip_width_final,
            tip_shift,
            bass_sign,
            distances,
            sides,
            offsets,
        )

    def body_layout(self) -> BodyLayout:
        """Return the body's outline and every feature, without validating it.

        Cheap: only the neck's plan outline is built, not its surfaces.
        The web app's body editor draws these features over an outline the
        user is still drawing, so nothing here checks that they fit; the
        full ``build`` does that when it makes the ``BodySolid``.
        """
        return self._body_layout(self.neck_outline())

    def headstock_design(self) -> tuple[HeadstockPlan, TunerLayout]:
        """Return the headstock plan and its tuner holes, validated.

        Cheap: no solids are built. With ``headstock_outline == "drawn"``
        and both edges given, the plan uses the drawn edges and its length
        is theirs; every tuner hole must then sit at least
        ``tuner_edge_offset`` (less 0.5 mm) from the drawn outline.

        Raises:
            NeckGeometryError: If a hole comes too close to a drawn edge.
            HeadstockGeometryError: If the plan or holes are invalid.
        """
        layout = self._headstock_layout()
        drawn = (
            self.headstock_outline == "drawn"
            and bool(self.headstock_bass_edge)
            and bool(self.headstock_treble_edge)
        )
        plan = HeadstockPlan(
            self.headstock_bass_edge[-1][0] if drawn else layout.length,
            self.nut_width,
            self.headstock_root_length,
            layout.shoulder_width,
            layout.tip_width,
            shoulder_shift=layout.shoulder_shift,
            tip_shift=layout.tip_shift,
            bass_sign=layout.bass_sign,
            bass_edge=self.headstock_bass_edge if drawn else None,
            treble_edge=self.headstock_treble_edge if drawn else None,
        )
        tuners = TunerLayout(
            plan,
            hole_diameter=self.tuner_hole_diameter,
            station_distances=layout.stations,
            side_offsets=layout.offsets,
            minimum_edge_clearance=self.tuner_edge_clearance,
            minimum_hole_clearance=self.tuner_hole_clearance,
            sides=layout.sides,
        )
        if drawn:
            for hole in tuners.holes:
                gap = distance_to_headstock_edge(plan, hole.center)
                if gap < self.tuner_edge_offset - 0.5:
                    raise NeckGeometryError(
                        f"Tuner {hole.side} {hole.index} is {gap:.1f} mm from the "
                        f"drawn headstock edge; keep it at least "
                        f"{self.tuner_edge_offset:g} mm away."
                    )
        return plan, tuners

    def tuner_centres(self) -> tuple[tuple[str, float, float], ...]:
        """Return ``(side, x, y)`` of every tuner hole, without validating.

        The web app's headstock editor draws these fixed holes under the
        edges being drawn.
        """
        layout = self._headstock_layout()
        centres: list[tuple[str, float, float]] = []
        for index, (distance, offset) in enumerate(
            zip(layout.stations, layout.offsets, strict=True)
        ):
            sides: tuple[Side, ...] = (
                ("bass", "treble") if layout.sides is None else (layout.sides[index],)
            )
            for side in sides:
                sign = layout.bass_sign * (1.0 if side == "bass" else -1.0)
                centres.append((side, -distance, sign * offset))
        return tuple(centres)

    def _neck_bolt_holes(
        self, outline: NeckOutline, heel_end: float, pocket: TracedCavity
    ) -> tuple[DrilledHole, ...]:
        """Return the neck bolts' ferrule counterbores and bolt holes.

        Each bolt keeps its place along the neck (the body shape's
        ``neck_bolts`` or the default rectangle) and, with
        ``body_neck_bolts_outward``, moves out across the neck, on its own
        side, as far from the truss rod as it can: until
        ``body_neck_bolt_edge_wall`` of wood is left between its hole and
        the neck's edge, or — nearer the body's edge — until its ferrule
        keeps ``NECK_FERRULE_BODY_WALL`` of wood to it. A ferrule may run
        past the neck pocket, but must stay in the body.

        Raises:
            BodyGeometryError: If the sizes are not positive, the bolt hole
                is not narrower than its ferrule, a bolt leaves less than
                the edge wall to the neck's edge or less than 3 mm of wood to
                the truss-rod channel or its nut pocket, a ferrule leaves the
                body, or two ferrules overlap.
        """
        sizes = (
            self.body_neck_bolt_spacing_x,
            self.body_neck_bolt_spacing_y,
            self.body_neck_ferrule_diameter,
            self.body_neck_ferrule_depth,
            self.body_neck_bolt_hole_diameter,
            self.body_neck_bolt_edge_wall,
            self.body_neck_bolt_end_wall,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in sizes):
            raise BodyGeometryError("Neck-bolt sizes must be finite and positive.")
        if self.body_neck_bolt_hole_diameter >= self.body_neck_ferrule_diameter:
            raise BodyGeometryError(
                "The neck-bolt hole must be narrower than its ferrule."
            )
        if self.body_shape.neck_bolts:
            centres = [(heel_end + x, y) for x, y in self.body_shape.neck_bolts]
        else:
            offset = (
                self.body_neck_bolt_hole_diameter / 2.0
                + self.body_neck_bolt_end_wall
                + self.body_neck_bolt_spacing_x / 2.0
                if self.body_neck_bolt_center_offset is None
                else self.body_neck_bolt_center_offset
            )
            centre_x = heel_end - offset
            centres = [
                (
                    centre_x + sx * self.body_neck_bolt_spacing_x / 2.0,
                    sy * self.body_neck_bolt_spacing_y / 2.0,
                )
                for sx, sy in ((-1.0, -1.0), (1.0, -1.0), (-1.0, 1.0), (1.0, 1.0))
            ]
        radius = self.body_neck_bolt_hole_diameter / 2.0
        wall = self.body_neck_bolt_edge_wall
        ferrule_reach = self.body_neck_ferrule_diameter / 2.0 + NECK_FERRULE_BODY_WALL

        def neck_half_width(x: float) -> float:
            if x >= outline.last_fret_position:
                return outline.heel_width / 2.0
            fraction = x / outline.last_fret_position
            return (
                outline.nut_width
                + (outline.last_fret_width - outline.nut_width) * fraction
            ) / 2.0

        keep_clear = self.truss_rod(outline).keep_clear()

        def rod_gap(x: float, y: float) -> float:
            gaps = [
                abs(y) - radius - half
                for front, back, half in keep_clear
                if front - radius < x < back + radius
            ]
            return min(gaps, default=math.inf)

        body_outline = self.body_shape.outline_points(
            heel_end, self.body_widening_amount()
        )

        def ferrule_in_body(x: float, y: float) -> bool:
            return point_in_polygon(Point2D(x, y), body_outline) and all(
                point_in_polygon(
                    Point2D(
                        x + ferrule_reach * math.cos(math.pi * step / 18.0),
                        y + ferrule_reach * math.sin(math.pi * step / 18.0),
                    ),
                    body_outline,
                )
                for step in range(36)
            )

        placed: list[tuple[float, float]] = []
        for index, (x, y) in enumerate(centres, start=1):
            limit = neck_half_width(x) - wall - radius
            side = 1.0 if y > 0.0 else -1.0 if y < 0.0 else 1.0
            if self.body_neck_bolts_outward:
                # From the neck's edge in toward the rod, the first spot
                # whose ferrule keeps its wood to the body's edge.
                steps = int(max(0.0, limit) / 0.25)
                found = None
                for step in range(steps + 1):
                    candidate = side * (limit - 0.25 * step)
                    if rod_gap(x, candidate) < 3.0:
                        break
                    if ferrule_in_body(x, candidate):
                        found = candidate
                        break
                if found is None:
                    raise BodyGeometryError(
                        f"Neck bolt {index} at {x - heel_end:.1f} mm from the heel "
                        "end has no room: nowhere between the truss rod (3 mm of "
                        f"wood) and the neck's edge ({wall:g} mm) does its ferrule "
                        f"keep {NECK_FERRULE_BODY_WALL:g} mm of wood to the body's "
                        "edge; move it along the neck (drag it in the body editor)."
                    )
                y = found
            where = f"({x - heel_end:.1f}, {y:.1f}) from the heel end"
            end_wall = heel_end - (x + radius)
            if end_wall < self.body_neck_bolt_end_wall - 1e-6:
                raise BodyGeometryError(
                    f"Neck bolt {index} at {where} leaves {end_wall:.1f} mm of wood "
                    f"to the neck's heel end, under {self.body_neck_bolt_end_wall:g} "
                    "mm; move it toward the neck."
                )
            if abs(y) > limit + 1e-6:
                raise BodyGeometryError(
                    f"Neck bolt {index} at {where} leaves under {wall:g} mm of "
                    "wood to the neck's edge; move it in."
                )
            if rod_gap(x, y) < 3.0:
                raise BodyGeometryError(
                    f"Neck bolt {index} at {where} is within 3 mm of the truss "
                    "rod, and its ferrule has no room further out; move it along "
                    "the neck (drag it in the body editor)."
                )
            if not ferrule_in_body(x, y):
                raise BodyGeometryError(
                    f"Neck bolt {index} ferrule at {where} leaves under "
                    f"{NECK_FERRULE_BODY_WALL:g} mm of wood to the body's edge; move "
                    "it along the neck (drag it in the body editor)."
                )
            for other, (ox, oy) in enumerate(placed, start=1):
                if math.hypot(x - ox, y - oy) < (
                    self.body_neck_ferrule_diameter + NECK_FERRULE_BODY_WALL
                ):
                    raise BodyGeometryError(
                        f"Neck bolts {other} and {index} ferrules overlap; move "
                        "them further apart along the neck."
                    )
            placed.append((x, y))

        bolt_depth = self.body_thickness - pocket.depth
        holes: list[DrilledHole] = []
        for index, (x, y) in enumerate(placed, start=1):
            holes.append(
                DrilledHole(
                    f"Neck bolt {index} ferrule",
                    x,
                    y,
                    self.body_neck_ferrule_diameter,
                    self.body_neck_ferrule_depth,
                )
            )
            holes.append(
                DrilledHole(
                    f"Neck bolt {index} hole",
                    x,
                    y,
                    self.body_neck_bolt_hole_diameter,
                    bolt_depth,
                )
            )
        return tuple(holes)

    @property
    def centre_scale(self) -> float:
        """Return the scale on the centerline: the mean of a multiscale's two."""
        if self.bass_scale_length is None:
            return self.scale_length
        return (self.scale_length + self.bass_scale_length) / 2.0

    @property
    def fret_skew(self) -> FretSkew:
        """Return how the frets lean: slant and multiscale fan together."""
        bass_sign = -1.0 if self.headstock_bass_side == "-y" else 1.0
        outer = (self.string_count - 1) / 2.0
        fan = (
            0.0
            if self.bass_scale_length is None
            else self.bass_scale_length - self.scale_length
        )
        return FretSkew(
            self.fret_slant,
            fan,
            1.0 - 2.0 ** (-self.perpendicular_fret / 12.0),
            self.centre_scale,
            outer * self.nut_string_spacing,
            outer * self.bridge_string_spacing,
            bass_sign,
        )

    @property
    def bridge_follows_fan(self) -> bool:
        """Return whether the bridge turns to a multiscale's bridge line.

        Always for a Tune-o-matic (its saddles cannot travel far enough),
        for a hardtail when ``body_bridge_follows_fan`` is set, else never.
        """
        return isinstance(self.body_bridge, TuneOMaticSpec) or (
            self.body_bridge_follows_fan and isinstance(self.body_bridge, HardtailSpec)
        )

    @property
    def pickups_follow_fan(self) -> bool:
        """Return whether a multiscale's pickups turn to the frets.

        ``body_pickups_follow_fan`` decides: ``"auto"`` turns them unless
        the bridge is a Tune-o-matic.
        """
        if self.body_pickups_follow_fan == "auto":
            return not isinstance(self.body_bridge, TuneOMaticSpec)
        return self.body_pickups_follow_fan == "yes"

    def truss_rod(self, outline: NeckOutline) -> TrussRodChannel:
        """Return the truss-rod channel with its adjusting nut's pocket."""
        heel = self.truss_rod_adjustment == "heel"
        shelf = self.nut_shelf_length + self.nut_shelf_reach()
        access = self.truss_rod_access_length
        if access is None:
            access = self.truss_rod_nut_length + 2.0
            if not heel:
                # Up to 32 mm, shortened to keep 3 mm from the first tuner
                # hole (a fanned neck's longer shelf pushes the trough back).
                _, tuners = self.headstock_design()
                room = (
                    min(-(hole.center.x + hole.diameter / 2.0) for hole in tuners.holes)
                    - shelf
                    - 3.0
                )
                access = max(self.truss_rod_nut_length, min(32.0, room))
        fit = self.truss_rod_fit(outline)
        start = self.truss_rod_start if heel else -shelf
        length = fit.route_length
        if heel and self.truss_rod_length is None:
            # The adjuster stays at the heel: a shorter rod starts later.
            start += fit.longest - fit.outside - length
        channel = TrussRodChannel(
            outline,
            start,
            length,
            self.truss_rod_width,
            self.truss_rod_depth,
            adjustment_side="heel" if heel else "nut",
            step_length=self.truss_rod_step_length,
            step_width=self.truss_rod_step_width,
            step_depth=self.truss_rod_step_depth,
            pocket_length=self.truss_rod_pocket_length,
            pocket_width=self.truss_rod_pocket_width,
            pocket_depth=self.truss_rod_pocket_depth,
            sleeve_length=self.truss_rod_sleeve_length if heel else 0.0,
            sleeve_diameter=(
                self.truss_rod_sleeve_diameter if self.truss_rod_sleeve_bore else 0.0
            ),
            nut_diameter=self.truss_rod_nut_diameter,
            nut_length=self.truss_rod_nut_length,
            access_length=access if heel or self.truss_rod_trough else 0.0,
            shelf_length=shelf,
            rod_axis_depth=self.truss_rod_axis_depth,
        )
        if not heel and channel.adjuster_boundary:
            trough_end = min(p.x for p in channel.adjuster_boundary)
            _, tuners = self.headstock_design()
            for hole in tuners.holes:
                gap = trough_end - (hole.center.x + hole.diameter / 2.0)
                if gap < 3.0:
                    raise NeckGeometryError(
                        f"The truss-rod trough reaches {-trough_end:.0f} mm into the "
                        f"headstock, too close to tuner {hole.side} {hole.index}; "
                        "shorten truss_rod_access_length."
                    )
        return channel

    def truss_rod_fit(self, outline: NeckOutline) -> TrussRodFit:
        """Return the longest rod the neck takes and the one it is routed for.

        Raises:
            NeckGeometryError: When ``truss_rod_rod_length`` is longer than
                the neck takes, or no stock length fits.
        """
        heel = self.truss_rod_adjustment == "heel"
        shelf = self.nut_shelf_length + self.nut_shelf_reach()
        start = self.truss_rod_start if heel else -shelf
        heel_end = outline.last_fret_position + outline.heel_length
        end = heel_end - (self.truss_rod_sleeve_length if heel else 12.0)
        outside = self.truss_rod_nut_length + (
            self.truss_rod_sleeve_length if heel else 0.0
        )
        longest = end - start + outside
        fitting = [
            length
            for length in self.truss_rod_stock_lengths
            if length <= longest + 1e-6
        ]
        recommended = max(fitting) if fitting else None
        if self.truss_rod_length is not None:
            return TrussRodFit(
                longest, recommended, None, self.truss_rod_length, outside
            )
        rod = self.truss_rod_rod_length
        if rod is None:
            if recommended is None:
                raise NeckGeometryError(
                    f"No stock truss rod fits this neck: it takes at most "
                    f"{longest:.0f} mm; set truss_rod_rod_length."
                )
            rod = recommended
        elif rod > longest + 1e-6:
            advice = (
                f"; the longest stock rod that fits is {recommended:g} mm"
                if recommended is not None
                else ""
            )
            raise NeckGeometryError(
                f"A {rod:g} mm truss rod is {rod - longest:.1f} mm too long for "
                f"this neck, which takes at most {longest:.1f} mm{advice}."
            )
        return TrussRodFit(longest, recommended, rod, rod - outside, outside)

    def truss_rod_cover_plate(self, channel: TrussRodChannel) -> CoverPlate | None:
        """Return the cover over a headstock trough, or ``None``.

        It overlaps the trough by 6 mm all round except at the nut, where
        it stops 0.5 mm short of the nut shelf; two screws near the nut
        and one at the far end hold it.
        """
        if (
            not self.truss_rod_cover
            or channel.adjustment_side != "nut"
            or not channel.adjuster_boundary
        ):
            return None
        trough = channel.adjuster_boundary
        front = min(p.x for p in trough) - 6.0
        back = max(p.x for p in trough) - 0.5
        half = max(p.y for p in trough) + 6.0
        corners = [
            Point2D(front, -half),
            Point2D(back, -half),
            Point2D(back, half),
            Point2D(front, half),
        ]
        outline = rounded_polygon_points(
            corners, [half * 0.9, 2.0, 2.0, half * 0.9], samples_per_corner=8
        )
        screws = (
            (back - 3.5, -(half - 3.0)),
            (back - 3.5, half - 3.0),
            (front + 4.0, 0.0),
        )
        return CoverPlate(
            "Truss rod cover",
            "top",
            outline,
            self.body_cover_recess_depth,
            holes=tuple(
                DrilledHole(
                    f"Screw {index}",
                    x,
                    y,
                    SCREW_CLEARANCE,
                    self.body_cover_recess_depth,
                )
                for index, (x, y) in enumerate(screws, start=1)
            ),
        )

    def nut_shelf_reach(self) -> float:
        """Return how far a leaning nut end reaches back into the nut shelf.

        The neck's shelf is lengthened by this much, so the nut keeps its
        full ``nut_shelf_length`` where the nut end leans furthest back.
        """
        return abs(self.fret_skew.at(0.0)) * self.nut_width / 2.0

    @property
    def fret_slant(self) -> float:
        """Return the shear of slanted frets: X gained per mm of Y.

        Positive ``fret_slant_angle`` moves each fret's treble end, on the
        side away from ``headstock_bass_side``, toward the bridge.
        """
        bass_sign = -1.0 if self.headstock_bass_side == "-y" else 1.0
        return -bass_sign * math.tan(math.radians(self.fret_slant_angle))

    def body_widening_amount(self) -> float:
        """Return how much the body is opened along its centreline, in mm."""
        if self.body_widening is not None:
            return self.body_widening
        return max(0, self.string_count - 6) * BODY_WIDENING_PER_STRING

    def pickup_types(self) -> tuple[PickupType, PickupType, PickupType]:
        """Return the (neck, middle, bridge) pickup types in use.

        A named ``body_pickups`` layout decides; ``"custom"`` takes each
        position's own ``body_*_pickup`` parameter.

        Raises:
            BodyGeometryError: For an unknown layout name.
        """
        if self.body_pickups == "custom":
            return (
                self.body_neck_pickup,
                self.body_middle_pickup,
                self.body_bridge_pickup,
            )
        if self.body_pickups not in PICKUP_CONFIGURATIONS:
            raise BodyGeometryError(
                f"Unknown pickup layout {self.body_pickups!r}; choose one of "
                f"{', '.join(PICKUP_CONFIGURATIONS)} or custom."
            )
        return PICKUP_CONFIGURATIONS[self.body_pickups]

    def neck_outline(self) -> NeckOutline:
        """Return the neck's plan outline (cheap: no surfaces are built)."""
        return NeckOutline(
            self.centre_scale,
            self.fret_count,
            self.nut_width,
            self.final_fret_width,
            self.heel_width,
            self.heel_length,
        )

    def _body_layout(self, outline: NeckOutline) -> BodyLayout:
        heel_end = outline.last_fret_position + self.heel_length
        # Body features ride with the heel end, bridge features with the
        # scale length (see the body_* parameter comments).
        widening = self.body_widening_amount()
        shape = widened_shape(self.body_shape, widening)
        body_outline = TracedOutline(shape.outline_points(heel_end, widening))
        neck_pocket = TracedCavity(
            "Neck pocket",
            self._neck_pocket_outline(outline, heel_end),
            self.heel_thickness,
        )
        neck_bolts = self._neck_bolt_holes(outline, heel_end, neck_pocket)
        truss_rod = self.truss_rod(outline)
        truss_rod_access = (
            TracedCavity(
                "Truss rod access",
                # From 3 mm inside the pocket, so no wall is left between.
                tuple(
                    Point2D(heel_end - 3.0, p.y) if math.isclose(p.x, heel_end) else p
                    for p in truss_rod.access_boundary
                ),
                truss_rod.adjuster_depth,
            )
            if truss_rod.access_boundary
            else None
        )

        bass_sign = -1.0 if self.headstock_bass_side == "-y" else 1.0

        scale = self.centre_scale
        # A multiscale's pickups turn with the fanned frets (a slant alone
        # leaves them square). The bridge stays square with its saddles
        # set per string, but a Tune-o-matic's saddles have too little
        # travel, so it always turns with the fan (a hardtail on request).
        fan = self.fret_skew.fan_only()

        def fan_angle(x: float) -> float:
            if not fan.fan or not self.pickups_follow_fan:
                return 0.0
            return math.degrees(math.atan(-bass_sign * fan.at(x)))

        bridge = turned_hardware(
            self.body_bridge.hardware(scale, self.body_thickness),
            Point2D(scale, 0.0),
            fan.at(scale) if self.bridge_follows_fan else 0.0,
            # A Tune-o-matic turns only where the strings rest; its
            # stop-bar studs stay square.
            (lambda name: name.startswith("Bridge post"))
            if isinstance(self.body_bridge, TuneOMaticSpec)
            else None,
        )
        bridge_mounting = bridge.mounting
        if isinstance(self.body_bridge, HardtailSpec):
            if self.body_bridge.string_count != self.string_count:
                raise BodyGeometryError(
                    f"The hardtail has {self.body_bridge.string_count} string "
                    f"holes, but the instrument has {self.string_count} strings."
                )
        elif self.string_count > BRIDGE_MAX_STRINGS.get(
            self.body_bridge.kind, self.string_count
        ):
            raise BodyGeometryError(
                f"The {self.body_bridge.kind} bridge is drawn for "
                f"{BRIDGE_MAX_STRINGS[self.body_bridge.kind]} strings; use the "
                f"hardtail for {self.string_count}."
            )
        strings = self.string_count
        neck_type, middle_type, bridge_type = self.pickup_types()
        single_slant = (
            self.body_bridge_single_coil_angle if bridge_type == "single_coil" else 0.0
        )
        bridge_angle = single_slant + fan_angle(scale - self.body_bridge_pickup_offset)

        # A pickup turned with fanned frets reaches further along the neck;
        # it moves back by that much, so its near edge keeps the same gap
        # to the neck pocket (or the bridge).
        def turned_reach(kind: PickupType, angle: float) -> float:
            return pickup_half_length(
                kind, angle, bass_sign, strings
            ) - pickup_half_length(kind, 0.0, bass_sign, strings)

        neck_pickup_x = heel_end + self.body_neck_pickup_offset
        neck_pickup_x += turned_reach(neck_type, fan_angle(neck_pickup_x))
        neck_angle = fan_angle(neck_pickup_x)
        route_half_length = pickup_half_length(
            bridge_type, bridge_angle, bass_sign, strings
        )
        bridge_fronts = [
            cavity.min_x for cavity in (*bridge.top_cavities, *bridge.through_cavities)
        ]
        needed_offset = (
            scale
            - min(bridge_fronts)
            + route_half_length
            + self.body_bridge_pickup_clearance
            if bridge_fronts and bridge_type != "none"
            else -math.inf
        )
        bridge_pickup_x = scale - max(
            self.body_bridge_pickup_offset
            + turned_reach(bridge_type, bridge_angle - single_slant),
            needed_offset,
        )
        bridge_angle = single_slant + fan_angle(bridge_pickup_x)
        # Left empty, the middle pickup goes in the middle of the gap
        # between the neck and bridge routes' facing edges, so a single
        # coil between a single coil and a wide humbucker looks centred.
        middle_pickup_x = (
            (
                neck_pickup_x
                + pickup_half_length(neck_type, neck_angle, bass_sign, strings)
                + bridge_pickup_x
                - pickup_half_length(bridge_type, bridge_angle, bass_sign, strings)
            )
            / 2.0
            if self.body_middle_pickup_offset is None
            else heel_end + self.body_middle_pickup_offset
        )
        middle_angle = fan_angle(middle_pickup_x)
        neck_pickup = pickup_route(
            neck_type,
            "Neck pickup route",
            neck_pickup_x,
            self.body_pickup_route_depth,
            bass_sign,
            neck_angle,
            string_count=strings,
        )
        middle_pickup = pickup_route(
            middle_type,
            "Middle pickup route",
            middle_pickup_x,
            self.body_pickup_route_depth,
            bass_sign,
            middle_angle,
            string_count=strings,
        )
        bridge_pickup = pickup_route(
            bridge_type,
            "Bridge pickup route",
            bridge_pickup_x,
            self.body_pickup_route_depth,
            bass_sign,
            bridge_angle,
            string_count=strings,
        )
        battery: ControlFeatures | None = None
        if self.body_battery_box:
            room = self.body_thickness - self.body_rear_cavity_top_wall
            if not 0.0 < self.body_battery_cavity_depth <= room:
                raise BodyGeometryError(
                    f"Battery cavity depth must be positive and leave "
                    f"{self.body_rear_cavity_top_wall:g} mm of the top: at most "
                    f"{room:g} mm in this body."
                )
            battery = battery_features(
                shape,
                heel_end,
                length=self.body_battery_cavity_length,
                width=self.body_battery_cavity_width,
                depth=self.body_battery_cavity_depth,
                cover_margin=self.body_battery_cover_margin,
                cover_depth=self.body_cover_recess_depth,
            )
        controls = self._placed_controls(
            shape,
            heel_end,
            body_outline.points,
            (
                neck_pocket,
                *bridge.top_cavities,
                *(
                    route
                    for route in (neck_pickup, middle_pickup, bridge_pickup)
                    if route is not None
                ),
            ),
            tuple(
                rear.cover_recess.outline
                for rear in (
                    *bridge.rear_cavities,
                    *((battery.battery_cavity,) if battery is not None else ()),
                )
                if rear is not None
            ),
        )
        if battery is not None:
            controls = controls.with_battery(battery)
        jack_hole = JackHole(
            heel_end + shape.jack_offset,
            shape.jack_y,
            shape.jack_direction_degrees,
            diameter=self.body_jack_diameter,
            depth=self.body_jack_depth,
        )
        holes: list[DrilledHole] = [*bridge.holes, *controls.holes]
        for label, kind, pickup_x, angle in (
            ("Neck", neck_type, neck_pickup_x, neck_angle),
            ("Middle", middle_type, middle_pickup_x, middle_angle),
            ("Bridge", bridge_type, bridge_pickup_x, bridge_angle),
        ):
            for side, screw_x, screw_y in pickup_screws(
                kind,
                pickup_x,
                bass_sign,
                self.body_pickup_screw_spacing,
                angle,
                string_count=strings,
            ):
                holes.append(
                    DrilledHole(
                        f"{label} pickup {side} screw recess",
                        screw_x,
                        screw_y,
                        self.body_pickup_screw_recess_diameter,
                        self.body_pickup_route_depth
                        + self.body_pickup_screw_recess_extra_depth,
                    )
                )
        return BodyLayout(
            heel_end,
            body_outline,
            neck_pocket,
            bridge_pickup,
            neck_pickup,
            bridge_mounting,
            jack_hole,
            controls.control_cavity,
            controls.switch_cavity,
            bridge.top_cavities,
            tuple(holes),
            bridge.through_cavities,
            bridge.rear_cavities,
            middle_pickup,
            neck_bolts,
            controls,
            EdgeProfile(
                self.body_top_edge_radius,
                self.body_top_binding_width,
                self.body_top_binding_depth if self.body_top_binding_width else 0.0,
            ),
            EdgeProfile(
                self.body_back_edge_radius,
                self.body_back_binding_width,
                self.body_back_binding_depth if self.body_back_binding_width else 0.0,
            ),
            self._contours(body_outline.points, heel_end, bass_sign),
            truss_rod_access,
        )

    def _placed_controls(
        self,
        shape: BodyShapeSpec,
        heel_end: float,
        outline: tuple[Point2D, ...],
        top_cavities: tuple[Cavity, ...],
        other_covers: tuple[tuple[Point2D, ...], ...] = (),
    ) -> ControlFeatures:
        """Return the electronics layout, moved clear of the top routes.

        A generated rear cavity (``gibson_4``, ``rear_3``) sits where the
        shape's pots put it. Where it would rout into a deep top route over
        it (a Floyd Rose's fine-tuner recess, a pickup), leaving no wood
        between the two floors, the whole layout — cavity, cover and pots —
        moves to the nearest place, out from the centreline and along the
        neck by up to ``CONTROL_CLEARANCE_SHIFT`` in 1 mm steps, that clears
        them with its cover in the body and off ``other_covers`` (the
        bridge's spring-cavity cover, the battery box's). The drawn almond
        keeps its place;
        if nothing clears, the layout stays put and the body's own check
        reports it.
        """
        pots = shape.pot_offsets
        side = 1.0 if sum(y for _, y in pots) >= 0.0 else -1.0

        def build(dx: float, dy: float) -> ControlFeatures:
            moved = shape
            if dx or dy:
                moved = replace(
                    shape,
                    pot_offsets=tuple((x + dx, y + side * dy) for x, y in pots),
                )
            return control_features(
                self.body_controls,
                moved,
                heel_end,
                thickness=self.body_thickness,
                top_wall=self.body_rear_cavity_top_wall,
                cover_depth=self.body_cover_recess_depth,
                pot_hole_diameter=self.body_pot_shaft_hole_diameter,
                switch_hole_diameter=self.body_switch_shaft_hole_diameter,
            )

        def clear(controls: ControlFeatures) -> bool:
            rear = controls.control_cavity
            if rear is None:
                return True
            return not any(
                rear.cavity.depth + top.depth >= self.body_thickness
                and outlines_overlap(rear.cavity.outline, top.outline)
                for top in top_cavities
            ) and not any(
                outlines_overlap(rear.cover_recess.outline, cover)
                for cover in other_covers
            )

        controls = build(0.0, 0.0)
        if self.body_controls not in ("gibson_4", "rear_3") or clear(controls):
            return controls
        reach = int(CONTROL_CLEARANCE_SHIFT)
        shifts = sorted(
            (
                (float(dx), float(dy))
                for dx in range(-reach, reach + 1)
                for dy in range(reach + 1)
                if 0 < math.hypot(dx, dy) <= reach
            ),
            key=lambda shift: (math.hypot(*shift), -shift[1]),
        )
        for dx, dy in shifts:
            moved = build(dx, dy)
            rear = moved.control_cavity
            if (
                clear(moved)
                and rear is not None
                and all(point_in_polygon(p, outline) for p in rear.cover_recess.outline)
            ):
                return moved
        return controls

    def _contours(
        self, outline: tuple[Point2D, ...], heel_end: float, bass_sign: float
    ) -> tuple[ContourCut, ...]:
        """Return the arm contour and belly cut that are switched on.

        Both sit on the bass side: the arm contour over the rear bout
        (from 120 mm behind the heel end), the belly cut over the upper
        bout (40 mm ahead of it to 120 mm behind). Each is deepest at the
        outline point furthest out on that side, or the one nearest
        ``body_*_position`` behind the heel end.
        """
        contours: list[ContourCut] = []
        for name, face, depth, width, length, position, span in (
            (
                "Arm contour",
                "top",
                self.body_arm_contour_depth,
                self.body_arm_contour_width,
                self.body_arm_contour_length,
                self.body_arm_contour_position,
                (120.0, math.inf),
            ),
            (
                "Belly cut",
                "back",
                self.body_belly_cut_depth,
                self.body_belly_cut_width,
                self.body_belly_cut_length,
                self.body_belly_cut_position,
                (-40.0, 120.0),
            ),
        ):
            if depth <= 0.0:
                continue
            bass_side = [
                index
                for index, point in enumerate(outline)
                if point.y * bass_sign > 0.0
            ]
            if position is not None:
                apex = min(
                    bass_side, key=lambda i: abs(outline[i].x - heel_end - position)
                )
            else:
                in_span = [
                    index
                    for index in bass_side
                    if span[0] <= outline[index].x - heel_end <= span[1]
                ]
                if not in_span:
                    raise BodyGeometryError(
                        f"The body has no bass-side edge for the {name.lower()}."
                    )
                apex = max(in_span, key=lambda i: outline[i].y * bass_sign)
            contours.append(
                ContourCut.along_edge(
                    name,
                    face,  # type: ignore[arg-type]
                    outline,
                    apex,
                    length,
                    width,
                    depth,
                )
            )
        return tuple(contours)

    def build(self) -> Prototype001Geometry:
        """Build and validate all geometry from this parameter set.

        Returns:
            Complete backend-independent Prototype001 geometry.
        """
        heel_flat_start_offset = self.heel_flat_start_offset
        if (
            not math.isfinite(self.heel_mounting_length)
            or self.heel_mounting_length < 40.0
        ):
            raise NeckGeometryError(
                "Heel mounting length must be at least 40 mm for a secure "
                "bolt-on joint."
            )
        if heel_flat_start_offset <= 0.0:
            raise NeckGeometryError(
                "Heel mounting length must exceed the heel extension after fret 24."
            )
        if not math.isclose(self.nut_shelf_length, 5.0):
            raise NeckGeometryError(
                "Prototype001 fixes the nut shelf at 5 mm; the scarf-root "
                "runout must not change the nut seat."
            )
        if (
            not math.isfinite(self.headstock_volute_length)
            or not 5.0 <= self.headstock_volute_length <= 30.0
        ):
            raise NeckGeometryError(
                "Headstock volute length must be between 5 and 30 mm."
            )
        if (
            not math.isfinite(self.headstock_root_length)
            or not 5.0 <= self.headstock_root_length < self.headstock_length
        ):
            raise NeckGeometryError(
                "Headstock root length must be at least 5 mm and shorter "
                "than the headstock."
            )
        if self.headstock_style not in HEADSTOCK_STYLES:
            raise NeckGeometryError(
                f"Unknown headstock style {self.headstock_style!r}; choose one "
                f"of {', '.join(HEADSTOCK_STYLES)}."
            )
        if self.string_count < 1:
            raise NeckGeometryError("The instrument needs at least one string.")
        if (
            not math.isfinite(self.fret_slant_angle)
            or abs(self.fret_slant_angle) > MAX_FRET_SLANT_ANGLE
        ):
            raise NeckGeometryError(
                f"Fret slant must be within {MAX_FRET_SLANT_ANGLE:g} degrees."
            )
        if self.bass_scale_length is not None:
            if not math.isfinite(self.bass_scale_length) or not (
                self.scale_length
                < self.bass_scale_length
                <= self.scale_length * MAX_MULTISCALE_RATIO
            ):
                raise NeckGeometryError(
                    "The bass scale must be longer than the treble scale "
                    f"(scale_length) and at most {MAX_MULTISCALE_RATIO:g} times it."
                )
            if (
                not math.isfinite(self.perpendicular_fret)
                or not 0.0 <= self.perpendicular_fret <= self.fret_count
            ):
                raise NeckGeometryError(
                    f"The perpendicular fret must lie between the nut (0) and "
                    f"fret {self.fret_count}."
                )
            if self.body_bridge_follows_fan and not isinstance(
                self.body_bridge, HardtailSpec | TuneOMaticSpec
            ):
                raise NeckGeometryError(
                    "Only the hardtail and the Tune-o-matic turn to the fanned "
                    "bridge line; leave body_bridge_follows_fan off and set the "
                    "saddles instead."
                )
        if self.body_widening is not None and (
            not math.isfinite(self.body_widening) or self.body_widening < 0.0
        ):
            raise NeckGeometryError("Body widening must be zero or more.")
        if sum(HEADSTOCK_STYLES[self.headstock_style]) != self.string_count:
            raise NeckGeometryError(
                f"Headstock style {self.headstock_style} holds "
                f"{sum(HEADSTOCK_STYLES[self.headstock_style])} tuners, but the "
                f"instrument has {self.string_count} strings."
            )
        bass_count, treble_count = HEADSTOCK_STYLES[self.headstock_style]
        if bass_count == treble_count and len(self.tuner_station_distances) != (
            bass_count
        ):
            raise NeckGeometryError(
                f"A {self.headstock_style} headstock needs {bass_count} "
                "tuner_station_distances (and tuner_side_offsets)."
            )
        inline_values = (
            self.tuner_inline_first_distance,
            self.tuner_inline_spacing,
            self.tuner_edge_offset,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in inline_values):
            raise NeckGeometryError(
                "In-line tuner distance, spacing and edge offset must be positive."
            )
        if not math.isfinite(self.tuner_tip_margin) or (self.tuner_tip_margin < 0.0):
            raise NeckGeometryError("Tuner tip margin must not be negative.")
        if self.headstock_bass_side not in ("-y", "+y"):
            raise NeckGeometryError('headstock_bass_side must be "-y" or "+y".')
        string_values = (
            self.tuner_post_diameter,
            self.nut_string_spacing,
            self.bridge_string_spacing,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in string_values):
            raise NeckGeometryError(
                "Tuner post diameter and string spacings must be positive."
            )
        if self.tuner_inline_first_distance < self.headstock_root_length:
            raise NeckGeometryError(
                "The first in-line tuner must sit beyond the headstock root, "
                "on the straight tapered edge."
            )
        if (
            not math.isfinite(self.headstock_root_swell)
            or not 0.0 <= self.headstock_root_swell <= 3.0
        ):
            raise NeckGeometryError("Headstock root swell must be between 0 and 3 mm.")
        if (
            not math.isfinite(self.nut_end_u_trim_depth)
            or not 0.0 <= self.nut_end_u_trim_depth <= 30.0
        ):
            raise NeckGeometryError("Nut-end U trim depth must be between 0 and 30 mm.")
        if (
            not math.isfinite(self.nut_end_u_side_fillet_radius)
            or not 0.0 <= self.nut_end_u_side_fillet_radius <= 2.0
        ):
            raise NeckGeometryError(
                "Nut-end U side fillet radius must be between 0 and 2 mm."
            )
        if (
            not math.isfinite(self.headstock_outer_d_profile_guide_extension)
            or not 0.0 <= self.headstock_outer_d_profile_guide_extension <= 30.0
        ):
            raise NeckGeometryError(
                "Outer D-profile guide extension must be between 0 and 30 mm."
            )
        if not math.isfinite(self.heel_root_length) or self.heel_root_length <= 0.0:
            raise NeckGeometryError("Heel root length must be finite and positive.")
        outline = self.neck_outline()
        first_fret_wood_thickness = self.first_fret_thickness - self.fretboard_thickness
        twelfth_fret_wood_thickness = (
            self.twelfth_fret_thickness - self.fretboard_thickness
        )
        neck_surface = NeckBackSurface(
            outline,
            first_fret_wood_thickness,
            twelfth_fret_wood_thickness,
            self.heel_thickness,
            nut_transition_thickness=self.headstock_thickness,
            nut_shelf_length=self.nut_shelf_length + self.nut_shelf_reach(),
            nut_transition_length=self.headstock_volute_length,
            # Keep the underlying D-profile surface independent from the
            # inspection-only U-shaped end trim emitted by the FreeCAD
            # backend. That trim changes only the neck-end boundary.
            nut_volute_depth=max(
                self.headstock_volute_depth,
                self.headstock_root_swell,
            ),
            nut_volute_peak_fraction=self.headstock_volute_peak_fraction,
            nut_root_side_extension=self.headstock_root_side_extension,
            heel_transition_length=self.heel_root_length,
            heel_flat_start_offset=heel_flat_start_offset,
            heel_scoop_depth=self.heel_scoop_depth,
            heel_root_center_extension=self.heel_root_center_extension,
            preserve_d_profile_at_heel=False,
            exponent=self.neck_profile_exponent,
            profile_sample_count=self.profile_sample_count,
            segments_per_region=self.segments_per_region,
        )
        fretboard_surface = FretboardSurface(
            self.centre_scale,
            self.fret_count,
            self.nut_width,
            self.final_fret_width,
            self.fretboard_radius,
            self.fretboard_thickness,
            end_extension=self.fretboard_end_extension,
            profile_sample_count=self.profile_sample_count,
            skew=self.fret_skew,
        )
        final_fret_fraction = 1.0 - 2.0 ** (-self.fret_count / 12.0)
        width_at_scale_end = (
            self.nut_width
            + (self.final_fret_width - self.nut_width) / final_fret_fraction
        )
        fretboard = Fretboard(
            self.centre_scale,
            self.nut_width,
            width_at_scale_end,
            Centerline(self.centre_scale),
            nut_corner_radius=self.fretboard_nut_corner_radius,
            skew=self.fret_skew,
        )
        fret_layout = FretLayout(fretboard, self.fret_count, self.fret_skew)
        # Markers listed beyond the last fret (the 24th-fret pair on a
        # 22-fret neck, say) are simply not cut.
        inlay_layout = InlayLayout(
            fretboard_surface,
            self.inlay_depth,
            single_marker_frets=tuple(
                fret
                for fret in self.inlay_single_marker_frets
                if fret <= self.fret_count
            ),
            double_marker_frets=tuple(
                fret
                for fret in self.inlay_double_marker_frets
                if fret <= self.fret_count
            ),
            style=self.inlay_style,
            dot_diameter=self.inlay_dot_diameter,
            block_length_fraction=self.inlay_block_length_fraction,
            block_edge_margin=self.inlay_block_edge_margin,
        )
        truss_rod_channel = self.truss_rod(outline)
        headstock_plan, tuner_layout = self.headstock_design()
        headstock = HeadstockSolid(
            headstock_plan,
            HeadstockAngleReference(
                headstock_plan.length,
                self.headstock_angle,
            ),
            self.headstock_thickness,
        )
        body_parts = self._body_layout(outline)
        body = BodySolid(
            body_parts.outline,
            self.body_thickness,
            body_parts.neck_pocket,
            body_parts.bridge_pickup,
            body_parts.neck_pickup,
            body_parts.bridge_mounting,
            body_parts.jack_hole,
            control_cavity=body_parts.control_cavity,
            switch_cavity=body_parts.switch_cavity,
            battery_cavity=body_parts.controls.battery_cavity,
            extra_cavities=(
                *(
                    (body_parts.middle_pickup,)
                    if body_parts.middle_pickup is not None
                    else ()
                ),
                *body_parts.extra_cavities,
            ),
            holes=body_parts.holes,
            through_cavities=body_parts.through_cavities,
            extra_rear_cavities=body_parts.extra_rear_cavities,
            rear_holes=body_parts.rear_holes,
            control_top_cavities=body_parts.controls.top_cavities,
            control_back_marks=body_parts.controls.back_marks,
            control_top_marks=body_parts.controls.top_marks,
            top_edge=body_parts.top_edge,
            back_edge=body_parts.back_edge,
            contours=body_parts.contours,
            truss_rod_access=body_parts.truss_rod_access,
        )
        return Prototype001Geometry(
            outline,
            neck_surface,
            fretboard_surface,
            fret_layout,
            truss_rod_channel,
            headstock,
            tuner_layout,
            inlay_layout,
            body,
            self.fret_slot_width,
            self.fret_slot_depth,
            self.tuner_chamfer_depth,
            self.joint_fillet_radius,
            self.headstock_root_swell,
            self.nut_end_u_trim_depth,
            self.nut_end_u_side_fillet_radius,
            self.headstock_outer_d_profile_guide_extension,
            self.heel_nose_radius,
            heel_flat_start_offset + self.heel_block_overlap,
            (
                *body_parts.controls.covers,
                *(
                    (cover,)
                    if (cover := self.truss_rod_cover_plate(truss_rod_channel))
                    else ()
                ),
            ),
        )


INSTRUMENT_OVERRIDES: dict[str, dict[str, Any]] = {
    "electric_guitar": {},
    "seven_string_guitar": {
        "string_count": 7,
        "scale_length": 647.7,
        "nut_width": 48.0,
        "final_fret_width": 66.0,
        "heel_width": 66.0,
        "fretboard_radius": 400.0,
        "headstock_style": "7_inline",
        "body_bridge": HardtailSpec(string_count=7),
    },
    "eight_string_guitar": {
        "string_count": 8,
        "scale_length": 685.8,
        "nut_width": 55.0,
        "final_fret_width": 76.0,
        "heel_width": 76.0,
        "fretboard_radius": 400.0,
        "headstock_style": "8_inline",
        "tuner_station_distances": (50.0, 78.0, 106.0, 134.0),
        "tuner_side_offsets": (20.0, 17.0, 14.0, 11.0),
        "body_bridge": HardtailSpec(string_count=8, screw_count=6),
    },
    "bass_guitar": {
        "string_count": 4,
        "scale_length": 863.6,
        "fret_count": 21,
        "nut_width": 38.0,
        "final_fret_width": 62.0,
        "heel_width": 62.0,
        "first_fret_thickness": 21.0,
        "twelfth_fret_thickness": 23.0,
        "heel_thickness": 22.0,
        "fretboard_radius": 305.0,
        "nut_string_spacing": 10.0,
        "bridge_string_spacing": 19.0,
        "headstock_style": "4_inline",
        "headstock_length": 200.0,
        "tuner_hole_diameter": 19.0,
        "tuner_station_distances": (60.0, 110.0),
        "tuner_side_offsets": (20.0, 16.0),
        "tuner_inline_first_distance": 60.0,
        "tuner_inline_spacing": 38.0,
        "tuner_edge_offset": 20.0,
        "tuner_post_diameter": 12.0,
        "body_pickups": "PJ",
        "body_neck_pickup": "precision_bass",
        "body_bridge_pickup": "jazz_bass",
        "body_neck_pickup_offset": 102.7,
        "body_bridge_pickup_offset": 45.0,
        "body_bridge": HardtailSpec(
            string_count=4,
            string_spacing=19.0,
            string_hole_offset=30.0,
            screw_count=5,
            screw_spacing=15.0,
            screw_offset=-12.0,
        ),
        "body_shape": BASS_BODY,
    },
}
"""Parameter values that differ from the defaults, per instrument.

The seven- and eight-string values are labelled starting points for
extended-range guitars: 25.5-inch (647.7 mm) and 27-inch (685.8 mm)
scales, 48 / 55 mm nuts and 66 / 76 mm heels (one more 7 mm nut and
10.5 mm bridge string spacing per string), a flatter 400 mm fretboard
radius, tuners in line, stretched humbuckers (see
``pickups.pickup_stretch``) and a string-through hardtail with a hole per
string; an eight-string can also take a 4+4 headstock.

The bass values are labelled starting points for a common four-string
bass: 34-inch (863.6 mm) scale, 21 frets, a 38 mm nut and 62 mm heel, a
12-inch fretboard radius, 10 mm string spacing at the nut and 19 mm at
the bridge, Fender-style tuners in line (19 mm holes, 38 mm apart), a
Precision Bass pickup 150 mm and a Jazz Bass pickup 45 mm ahead of the
bridge, and a string-through four-string hardtail.
"""


def distance_to_headstock_edge(plan: HeadstockPlan, point: Point2D) -> float:
    """Return how far ``point`` sits from the headstock's edges and tip.

    Measured as the fitted outline is laid out: across the neck to each
    side's edge at the point's own distance from the nut, and along the
    neck to the tip; the smallest of the three. The nut is not an edge.
    """
    distance = -point.x
    return min(
        plan.edge_y(distance, 1.0) - point.y,
        point.y - plan.edge_y(distance, -1.0),
        plan.length - distance,
    )
