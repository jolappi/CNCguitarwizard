"""Locked but configurable parameters for the first complete neck."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal, cast

from ..cam.planar import distance_to_boundary, offset_polygon, simplified
from ..geometry.body import (
    BRIDGE_MAX_STRINGS,
    BRIDGE_MIN_STRINGS,
    BodySolid,
    BridgeHardware,
    BridgeMounting,
    BridgeSpec,
    CarvedTop,
    Cavity,
    ContourCut,
    CoverPlate,
    DrilledHole,
    EdgeProfile,
    Engraving,
    FloydRoseSpec,
    HardtailSpec,
    HeadlessBridgeSpec,
    JackHole,
    KahlerBridgeSpec,
    RearCavity,
    SingleStringBridgeSpec,
    SteppedTop,
    TracedCavity,
    TracedOutline,
    TuneOMaticSpec,
    mirrored_hardware,
    neck_through,
    outlines_overlap,
    plateau_round,
    turned_hardware,
)
from ..geometry.body.neck_through import NeckThrough
from ..geometry.body.wiring import WireSpace, Wiring, plan_wiring
from ..geometry.exceptions import (
    BodyGeometryError,
    GeometryException,
    NeckGeometryError,
)
from ..geometry.fretboard import (
    Fretboard,
    FretboardSurface,
    FretLayout,
    FretSkew,
    InlayLayout,
    InlayStyle,
)
from ..geometry.lettering import FontName, text_lines
from ..geometry.neck import (
    LOCKING_NUT_SPECS,
    Centerline,
    HeadstockAngleReference,
    HeadstockPlan,
    HeadstockSolid,
    LockingNut,
    NeckBackSurface,
    NeckOutline,
    Side,
    TrussRodChannel,
    TunerHole,
    TunerLayout,
)
from ..geometry.neck.reinforcement import CLEARANCE as CARBON_ROD_CLEARANCE
from ..geometry.neck.reinforcement import CarbonRods
from ..geometry.primitives import (
    Point2D,
    Point3D,
    open_catmull_rom,
    point_in_polygon,
    rounded_polygon_points,
)
from .body_shapes import (
    BASS_BODY,
    BODY_WIDENING_PER_STRING,
    GUITAR_BODY,
    BodyShapeSpec,
    mirrored_shape,
    widened_shape,
)
from .controls import (
    GENERATED_REAR_LAYOUTS,
    SCREW_CLEARANCE,
    SCREW_SPOT_DEPTH,
    SCREW_SPOT_DIAMETER,
    ControlFeatures,
    ControlLayout,
    battery_features,
    control_features,
    rear_cover,
)
from .engraving import (
    EngravingArea,
    EngravingPattern,
    pattern_lines,
    pattern_pockets,
)
from .pickguard import (
    PICKGUARD_STYLES,
    SADDLE_REACH,
    Pickguard,
    PickguardStyleName,
    check_on_body,
    clear_of_bridge,
    clear_of_truss_rod,
    guard_outline,
    pickguard,
)
from .pickguard import automatic_points as automatic_pickguard_points
from .pickups import (
    PICKUP_CONFIGURATIONS,
    PickupConfiguration,
    PickupType,
    pickup_half_length,
    pickup_openings,
    pickup_route,
    pickup_screws,
)

HEADSTOCK_ENGRAVING_SETBACK = 20.0
"""How far behind the nut's seat the headstock lettering sits by default."""

HEADSTOCK_ENGRAVING_CLEARANCE = 2.0
"""Least gap between the headstock lettering and the face's edge, the
nut's seat, a tuner hole or the truss rod adjuster's trough, in mm."""

MIN_HEADLESS_LENGTH = 25.0
"""The shortest headless headpiece: the neck's nut-end blend needs it."""

MAX_FRETBOARD_BINDING = 3.0
"""The thickest fretboard binding accepted, in mm."""

ENGRAVING_WALL = 3.0
"""Least wood the engraving leaves over a cavity routed from the back, in
mm; a cavity reaching nearer the top is engraved round."""

CONTOUR_LINE_SAMPLES = 8
"""Samples per span of a drawn arm contour's line (``arm_contour_points``)."""

Instrument = Literal[
    "electric_guitar",
    "seven_string_guitar",
    "eight_string_guitar",
    "bass_guitar",
    "five_string_bass",
    "headless_guitar",
    "headless_bass",
]
"""Which instrument's defaults a parameter set starts from."""

MAX_FRET_SLANT_ANGLE = 10.0
"""The largest fret slant accepted, in degrees."""

NECK_FERRULE_BODY_WALL = 1.0
"""Least wood, in mm, between a neck-bolt ferrule and the body's edge, and
between two ferrules."""

SWITCH_SHAFT_HOLE_DIAMETERS: dict[str, float] = {
    "toggle": 12.7,
    "micro": 6.35,
}
"""The pickup selector's bushing hole, in mm: a 3-way toggle's 1/2 in, a
micro (mini) toggle's 1/4 in."""

FLAT_HEADSTOCK_FACE_DROP = 4.0
"""How far a flat headstock's face is set below the glue face, in mm: its
16 mm in the bottom of a 20 mm blank below the fretboard, so the strings
break over the nut toward the tuners."""

CONTROL_CLEARANCE_SHIFT = 20.0
"""How far, in mm, a generated control cavity may move out from the
centreline to clear a deep top route (see ``_placed_controls``)."""

JACK_DEFAULT_DEPTH = 55.0
"""The jack bore's length, in mm, when it aims at no control cavity."""

JACK_CAVITY_OVERRUN = 3.0
"""How far the jack bore runs on past the control cavity's wall, in mm."""

JACK_CUP_DIAMETER, JACK_CUP_DEPTH = 22.2, 25.0
"""A cup jack's or an Electrosocket's 7/8 in counterbore, 1 in deep, in mm."""

JACK_STRAT_DIAMETER, JACK_STRAT_DEPTH, JACK_STRAT_WALL = 25.4, 32.0, 4.0
"""A Stratocaster style jack's cavity under its top plate: a 1 in round
pocket this deep, this much wood from the body's edge, in mm."""

PICKUP_RING_REACH = 12.0
"""How far a pickup's mounting ring reaches past its route, in mm (a
humbucker's ring is about 92 x 45 mm over its 70 x 40 mm route, the ears
included): a carved top's plateau reaches that far round every pickup."""

PICKUP_RING_KEEP = 7.0
"""How far past its route a pickup's ring is held flat however near the
edge it comes, in mm: the ring itself, about 2.5 mm past a humbucker's
route at the sides and 3 to 5 at the ends, and a grid cell (2 mm) so it
reads flat right to its edge. (``PICKUP_RING_REACH``
is the plateau's generous margin; held that wide by a cutaway it left the
top a few mm to fall its whole height, a wall by the binding.)"""

CARVE_KEEP_MARGIN = 3.0
"""How far a carved top's plateau reaches round the neck pocket and the
truss-rod access, in mm."""

CARVE_MIN_FALL = 25.0
"""The shortest fall a carved top aims for from its plateau to its rim, in
mm: where the plateau comes nearer the edge, the rim narrows (down to its
``edge_rim``) to leave the fall that room."""

CARBON_ROD_SIZES: dict[str, tuple[float, float]] = {
    "3.2x6.35": (3.2, 6.35),
    "4x4": (4.0, 4.0),
    "3.2x9.5": (3.2, 9.5),
}
"""Carbon fibre bar sections by name: (width, height), in mm."""

CARBON_ROD_GAP = 3.0
"""Wood between a carbon rod's channel and the truss rod's route when the
rods' offset is automatic, in mm."""

CARBON_ROD_WALL = 2.0
"""The least wood between a carbon rod's channel and the truss rod's route
or the neck's side, in mm."""

CARBON_ROD_FLOOR = 2.0
"""The least wood under a carbon rod's channel, to the neck's back, in mm."""

NECK_THROUGH_MARGIN = 3.0
"""Wood a neck-through block keeps beside the pickup and bridge routes and
holes it carries, in mm (its automatic width)."""

NECK_THROUGH_BLOCK_FEATURES: tuple[str, ...] = (
    "Bridge",
    "Tailpiece",
    "String",
    "Floyd",
    "Kahler",
)
"""What a neck-through block carries besides the pickups: the bridge's
routes and holes, by name."""

NECK_THROUGH_EDGE_REACH = 12.0
"""How far past a neck-through glue line a part's edge finish (a
roundover, a binding) runs on into its waste, in mm."""

NECK_ANGLE_TUNE_O_MATIC = 2.0
"""A Tune-o-matic's neck angle on the flat top, in degrees (2-2.5 is usual;
a carved Les Paul top takes 3-5)."""

MAX_NECK_ANGLE = 6.0
"""The steepest neck angle accepted, in degrees."""

TRUSS_ROD_MIN_FLOOR = 1.0
"""Wood left under a headstock-adjusted standard rod's deepest pocket, in
mm: the neck is made this much thicker than the pocket's depth."""

STEP_EDGE_SLACK = 3.0
"""How near the body's edge drawn step lines may cross, in mm: where they
converge on the edge (the sliver between them is cut with the outer
band)."""

STEP_OUTLINE_TOLERANCE = 0.05
"""How far a stepped top's boundaries may stray from the outline's own
offset, in mm (the outline is simplified that much first)."""

PICKGUARD_CONTROL_LAP = 6.0
"""How far a pickguard reaches past the control cavity under it, at least,
in mm (pickguard-mounted controls are moved to leave it room)."""

PICKGUARD_CONTROL_GAP = 3.0
"""Wood kept between a pickguard control cavity and the other top routes."""

PICKGUARD_CONTROL_SHIFT = 40.0
"""How far pickguard-mounted controls may move to fit under a guard, in mm."""

PICKGUARD_CONTROL_TURNS = (0.0, 10.0, -10.0, 20.0, -20.0, 30.0, -30.0)
"""The turns (degrees) tried, in order, for controls that do not fit
under a guard square."""

MAX_MULTISCALE_RATIO = 1.15
"""The longest bass scale accepted, as a multiple of the treble scale."""

FLOYD_ROSE_NUTS: dict[int, Literal["r2", "r7", "r8"]] = {6: "r2", 7: "r7", 8: "r8"}
"""The locking nut ``locking_nut`` "auto" fits a Floyd Rose with, per
string count."""

HeadstockStyle = Literal[
    "3+3",
    "6_inline",
    "6_inline_reverse",
    "4+2",
    "2+4",
    "2+2",
    "4_inline",
    "4_inline_reverse",
    "4+1",
    "1+4",
    "3+2",
    "2+3",
    "5_inline",
    "5_inline_reverse",
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
    "4+1": (4, 1),
    "1+4": (1, 4),
    "3+2": (3, 2),
    "2+3": (2, 3),
    "5_inline": (5, 0),
    "5_inline_reverse": (0, 5),
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
    "4+1": ((40.0, 15.0), (45.0, 30.0)),
    "1+4": ((40.0, 15.0), (45.0, 30.0)),
    "3+2": ((40.0, 15.0), (45.0, 30.0)),
    "2+3": ((40.0, 15.0), (45.0, 30.0)),
    "5_inline": ((40.0, None), (45.0, 60.0)),
    "5_inline_reverse": ((40.0, None), (45.0, 60.0)),
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
    locking_nut: LockingNut | None = None
    """The top-mounted locking nut, or ``None`` for a plain nut."""
    fretboard_binding_width: float = 0.0
    """The binding strips' thickness along the board's long edges (0: none)."""
    headstock_engraving: Engraving | None = None
    """Lettering engraved into the headstock face, or ``None``."""
    neck_tilt: tuple[float, float, float] = (0.0, 0.0, 0.0)
    """The neck's back-tilt in degrees and the ``(x, z)`` it turns about."""
    neck_through: NeckThrough | None = None
    """A neck-through body's block and wings, or ``None`` for a bolt-on neck."""
    carbon_rods: CarbonRods | None = None
    """The carbon fibre bars beside the truss rod, or ``None``."""
    set_neck: bool = False
    """Whether the neck is glued into its pocket (no bolts)."""


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
        jack_hole: The output jack bore, or ``None`` with the jack on a
            control plate.
        control_cavity: The rear control cavity with its cover recess.
        switch_cavity: The rear switch cavity with its cover recess.
        extra_cavities: The bridge's top routes, and a Stratocaster style
            jack's cavity.
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
        pickguard: The pickguard, or ``None`` (its plate is also one of
            the ``controls``' covers).
        bridge_footprint: What the bridge itself covers on the top past
            its routes (a Kahler's plate), or empty.
        engraving: The decorative pattern engraved into the top, or
            ``None`` (see ``body_engraving``).
        carved_top: The arched top, or ``None`` (see ``body_carved_top``).
        stepped_top: The top in levels along the edge, or ``None`` (see
            ``body_stepped_top``).
    """

    heel_end: float
    outline: TracedOutline
    neck_pocket: TracedCavity
    bridge_pickup: TracedCavity | None
    neck_pickup: TracedCavity | None
    bridge_mounting: BridgeMounting
    jack_hole: JackHole | None
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
    pickguard: Pickguard | None = None
    bridge_footprint: tuple[Point2D, ...] = ()
    engraving: Engraving | None = None
    carved_top: CarvedTop | None = None
    stepped_top: SteppedTop | None = None
    wiring: Wiring = field(default_factory=Wiring)
    bridge_notes: tuple[str, ...] = ()


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
    # handedness: "right" builds the instrument as drawn (every body
    # template and the default neck are right-handed: seen from the front
    # with the headstock to the left, the bass side, the long horn and the
    # switch at -Y, the controls and jack at +Y); "left" builds its mirror
    # image: the body shape, its electronics and contours, the bass side
    # (pickups, bridge, frets, inlays, tuners), a Floyd Rose's arm side and
    # a drawn headstock tip all flip to the other side of the centerline.
    # Designs stay stored as drawn; text is set again, never mirrored.
    handedness: Literal["right", "left"] = "right"
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
    # a hardtail's holes when body_bridge_follows_fan is on, and
    # single-string bridges, each standing at its own string's scale.
    # body_pickups_follow_fan turns the pickups to the frets: "auto" turns
    # them except with a Tune-o-matic, "yes" and "no" always and never.
    bass_scale_length: float | None = None
    perpendicular_fret: float = 7.0
    nut_width: float = 42.0
    final_fret_width: float = 56.0
    heel_width: float = 56.0
    heel_mounting_length: float = 54.0
    # neck_joint: "bolt_on" screws the neck's heel into a pocket in the
    # body; "neck_through" runs the neck blank on through the body as a
    # centre block neck_through_width wide (empty: wide enough for the
    # pickup and bridge routes and holes, NECK_THROUGH_MARGIN each side),
    # the body's two wings cut from their own blanks and glued to its
    # sides. The neck's back then falls to the body's thickness over
    # neck_through_heel_ramp, reaching it where the body begins.
    # "one_piece" cuts the neck and the whole body from one blank, no
    # wings and no glue joints at all (as a neck-through whose block is the
    # whole body). "set" glues the heel into the pocket instead of bolting
    # it (Gibson style): no bolts, the pocket set_neck_glue_gap a side
    # round the heel for a tight glue joint; a neck angle is as for a
    # bolt-on neck.
    neck_joint: Literal["bolt_on", "set", "neck_through", "one_piece"] = "bolt_on"
    set_neck_glue_gap: float = 0.05
    neck_through_width: float | None = None
    neck_through_heel_ramp: float = 40.0
    heel_length: float = 4.0
    fretboard_end_extension: float = 4.0
    # Square nut-end corners: the board meets the nut with no rounding.
    fretboard_nut_corner_radius: float = 0.0
    first_fret_thickness: float = 17.0
    twelfth_fret_thickness: float = 19.0
    heel_thickness: float = 20.0
    fretboard_radius: float = 430.0
    fretboard_thickness: float = 6.0
    # Binding along the fretboard's long edges (0 = none): the board is
    # cut fretboard_binding_width narrower each side and strips that thick
    # are glued on, so board and binding together keep nut_width and
    # final_fret_width (and the neck under them its own). The fret slots
    # run out through the board's edges as usual; the frets' tangs are
    # nipped back over the binding.
    fretboard_binding_width: float = 0.0
    fret_slot_width: float = 0.6
    fret_slot_depth: float = 2.7
    # Position markers, cut as flat-bottomed pockets into the playing
    # surface: barbed wire (default) or round dots, two at 12 and 24 and
    # one at every other listed fret; or one shape per fret spanning the
    # board with its taper (inlay_block_length_fraction of the fret
    # spacing long, inlay_block_edge_margin from each edge): Gibson
    # blocks, Les Paul trapezoids, Jackson sharktooth, parallelograms,
    # diamonds or Gibson split blocks (see geometry.fretboard.inlay_layout);
    # or "custom", inlay_points' own shape: its corners as (along, across),
    # along 0 at the fret toward the nut and 1 at the marker's fret, across
    # the share of the board's half-width toward the bass edge (-1 the
    # treble edge, +1 the bass edge), drawn on the first marker in the web
    # app's inlay editor and fitted to every marker's fret space and the
    # board's taper (a block until drawn).
    inlay_depth: float = 2.0
    inlay_single_marker_frets: tuple[int, ...] = (3, 5, 7, 9, 15, 17, 19, 21)
    inlay_double_marker_frets: tuple[int, ...] = (12, 24)
    inlay_style: InlayStyle = "barbed_wire"
    inlay_dot_diameter: float = 6.0
    inlay_block_length_fraction: float = 0.6
    inlay_block_edge_margin: float = 5.0
    inlay_points: tuple[tuple[float, float], ...] = ()
    # Solid body (right-handed, as drawn): outline, pickup routes, bridge baseplate
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
    # neck_angle tilts the neck back (its headstock toward the player) by
    # this many degrees: the neck pocket's floor sinks toward its mouth,
    # body_neck_pocket_length x tan(angle) deeper there than at the heel
    # end, where it stays heel_thickness deep, and is cut in thin
    # terraces. The neck turns about the heel end of the pocket floor, so
    # the bridge moves to keep the strings' scale (and the 12th fret
    # halfway) along their tilted line. Empty: NECK_ANGLE_TUNE_O_MATIC
    # with a Tune-o-matic (it stands too tall for a flat neck on a flat
    # top), 0 otherwise.
    neck_angle: float | None = None
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
    # line, but moves further forward on its own when the chosen bridge
    # reaches closer (a recessed Floyd Rose, a hardtail's baseplate screws,
    # a Tune-o-matic's posts), keeping body_bridge_pickup_clearance of wood
    # between the route and the bridge's routes and holes, and never
    # reaches past the saddle line.
    body_bridge_pickup_offset: float = 21.73  # route centre before the bridge
    body_bridge_pickup_clearance: float = 3.0
    body_pickup_route_depth: float = 22.0
    # body_pickups picks a named layout (see PICKUP_CONFIGURATIONS): HH,
    # HSH, HSS, H, SSS, SS for a guitar, PJ, JJ, P, MM, RR for a bass. With
    # "custom" each position takes its own type from body_neck_pickup /
    # body_middle_pickup / body_bridge_pickup: the guitar humbucker or
    # single coil, a Jazz Bass single coil, a Precision Bass split coil,
    # a bass soapbar humbucker, a Rickenbacker style bass humbucker, or
    # none. The middle pickup sits
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
    # KahlerBridgeSpec (default, the DXF's flat-mount 7300 cutout; six to
    # eight strings), FloydRoseSpec (six to eight strings), TuneOMaticSpec,
    # HardtailSpec (string-through or top-loaded), HeadlessBridgeSpec or
    # SingleStringBridgeSpec (a unit per string, each at its own scale on
    # a multiscale). Each places its own routes, rear cavities and holes
    # relative to the scale line; one with a string_count must match the
    # instrument's. In the web form it is edited as JSON with a "kind"
    # entry.
    body_bridge: BridgeSpec = field(default_factory=KahlerBridgeSpec)
    # The body shape is a spec (see body_shapes): a drawn body
    # (YourDesignShape) — by default the Design by Jone template, the
    # user's own DXF outline resampled to control points (the bass gets
    # the Jazz Bass style one) — or the traced DXF itself
    # (DesignByJoneShape). Each carries its own outline and the placements
    # that belong to the silhouette - switch cavity, pot holes, jack -
    # measured from the heel end. The web form always edits a drawn body,
    # in the body editor.
    body_shape: BodyShapeSpec = field(default_factory=lambda: GUITAR_BODY)
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
    # rear cavity with 3 in a row, a superstrat rear cavity with 2 pots
    # and the 5-way blade switch in it, a single volume pot, an active
    # bass's 4 pots in a row, a Telecaster-style plate in the top, a Jazz
    # Bass style plate (3 pots, and the jack with body_jack "plate"), the
    # Stratocaster's controls in the pickguard, or none. Each cover plate
    # is cut from sheet in its own program.
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
    # body_battery_count 2 makes the box hold two batteries side by side
    # (18 V for some preamps), BATTERY_PITCH (28 mm) wider.
    # A pickguard (see presets.pickguard): body_pickguard puts one on, cut
    # from body_pickguard_thickness sheet in its own cover program. It
    # follows the outline body_pickguard_margin in, from the neck pocket to
    # the bridge (or the shape's pickguard_points), with openings over the
    # pickups and holes for the pots and selector under it, screwed round
    # its edge. body_controls "pickguard" mounts the controls in it,
    # Stratocaster style, over a cavity routed from the top: that layout
    # brings the guard with it, the automatic one if a drawn guard (a
    # template's) does not cover the controls.
    # body_pickguard_style draws the automatic guard as a Stratocaster's
    # ("stratocaster") or close round the pickups ("superstrat"); see
    # presets.pickguard.PICKGUARD_STYLES.
    body_pickguard: bool = False
    body_pickguard_thickness: float = 2.5
    body_pickguard_margin: float = 6.0
    body_pickguard_style: PickguardStyleName = "stratocaster"
    # A decorative pattern engraved into the top (see presets.engraving):
    # body_engraving puts it on, body_engraving_pattern picks it (Design by
    # Jone's scrolls, EVH stripes, flame, ripples, crackle, woodland camo or
    # a pinstripe round the edge), laid out at
    # random from body_engraving_seed (the same seed, the same pattern),
    # body_engraving_spacing setting its scale (the scroll copies about that
    # far apart, as in the drawing), cut
    # body_engraving_depth deep with a V-bit, body_engraving_margin in
    # from the edge and body_engraving_clearance clear of every top
    # cavity, hole, the bridge, the pickguard and the contours (the back's
    # cavities only when they leave less than ENGRAVING_WALL under it).
    # body_carved_top arches the top Les Paul style (geometry.body.carve)
    # on any body: it keeps its full body_thickness over a flat plateau
    # body_carve_margin round the pickups, the bridge and the neck pocket
    # (they always sit on the flat; its corners rounded, its ends round),
    # falls body_carve_depth toward the edge and lands on a flat rim
    # body_carve_rim wide. A Les Paul's 5/8
    # in maple cap over 1/4 in binding leaves a 3/8 in (9.5 mm) arch, its
    # body 2 1/4 in in the middle and 2 in at the edge. An arm contour
    # does not go with it.
    body_carved_top: bool = False
    body_carve_depth: float = 9.5
    body_carve_rim: float = 8.0
    body_carve_margin: float = 15.0
    # body_stepped_top lowers the top in bands that follow the edge, the
    # ESP LTD Alexi Hexed's graphic made into levels (geometry.body.steps):
    # inside the innermost of body_top_step_insets the top keeps its full
    # height, and each band nearer the edge lies body_top_step_height lower
    # than the one inside it — 12 and 40 mm in with 1.5 mm steps, the
    # middle band 1.5 mm down and the edge band 3 mm. The pickups and the
    # bridge stay on the top level; the back's cavities keep their top wall
    # under the bands. Not with a carved top, an arm contour or a pickguard.
    body_stepped_top: bool = False
    body_top_step_insets: tuple[float, ...] = (12.0, 40.0)
    body_top_step_height: float = 1.5
    body_engraving: bool = False
    body_engraving_pattern: EngravingPattern = "scroll"
    body_engraving_seed: int = 1
    body_engraving_depth: float = 2.0
    body_engraving_spacing: float = 50.0
    body_engraving_margin: float = 10.0
    body_engraving_clearance: float = 4.0
    body_battery_box: bool = False
    body_battery_count: int = 1
    body_battery_cavity_length: float = 56.0
    body_battery_cavity_width: float = 30.0
    body_battery_cavity_depth: float = 22.0
    body_battery_cover_margin: float = 7.0
    # Shaft holes through the top wall: the pickup selector's bushing at
    # the switch cavity's centre, and 3/8" pot bushings at the shape's pot
    # positions. body_switch picks the selector: a "toggle" (a 3-way
    # Switchcraft-style toggle, 1/2" bushing) or a "micro" (mini) toggle,
    # 1/4" bushing (SWITCH_SHAFT_HOLE_DIAMETERS); a
    # body_switch_shaft_hole_diameter overrides the hole.
    body_switch: Literal["toggle", "micro"] = "toggle"
    body_switch_shaft_hole_diameter: float | None = None
    body_pot_shaft_hole_diameter: float = 10.0
    # The output jack (body_jack): "side", a bore in from the body's edge
    # (a Les Paul style side plate or a barrel jack); "cup", that bore with
    # a 7/8 in counterbore at the edge for a Telecaster cup jack or an
    # Electrosocket (JACK_CUP_DIAMETER x JACK_CUP_DEPTH); "strat", a
    # Stratocaster style plate on the top: a round jack cavity routed from
    # the top just in from the edge (JACK_STRAT_DIAMETER x
    # JACK_STRAT_DEPTH), the bore running on from it. The bore starts where
    # the shape's jack line (jack_offset / jack_y along
    # jack_direction_degrees) meets the outline, whatever the body, and
    # runs on into the control cavity, JACK_CAVITY_OVERRUN past its wall;
    # body_jack_depth fixes its length instead (JACK_DEFAULT_DEPTH when it
    # aims at no control cavity). "plate" puts the jack on the Jazz Bass
    # style control plate (body_controls "jazz_bass"), behind its pots:
    # no bore from the edge.
    body_jack: Literal["side", "cup", "strat", "plate"] = "side"
    body_jack_diameter: float = 12.5
    body_jack_depth: float | None = None
    # The wire channels (see geometry.body.wiring): every pickup route and
    # a separate switch cavity wired to the controls, nearest first (a row
    # of pickups chains to them), a battery box's lead straight to them,
    # and the bridge's ground wire from the controls to its nearest cavity
    # or hole. Under a pickguard a channel is routed from the top
    # (WIRE_CHANNEL_WIDTH wide, at most WIRE_CHANNEL_DEPTH deep); every
    # other way is a straight hole drilled by hand (WIRE_HOLE_DIAMETER,
    # the ground GROUND_HOLE_DIAMETER), modelled and given in Body_top's
    # notes with its angle; a way no straight hole fits is left to the
    # builder in a note. False leaves the wiring to the builder.
    body_wire_channels: bool = True
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
    # A string-through bridge's ferrules (the hardtail, single-string
    # bridges): every hole the strings pass through the body by gets a
    # counterbore from the back body_string_ferrule_diameter wide and
    # body_string_ferrule_depth deep, drilled in Body_back (the ferrule
    # hides it); 5/16 in by default on a guitar, 3/8 in on a bass. A depth
    # of 0 leaves them to the builder.
    body_string_ferrule_diameter: float = 8.0
    body_string_ferrule_depth: float = 6.0
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
    # truss_rod_spoke_wheel: an adjuster with a spoke wheel ("auto": at the
    # heel yes, at the headstock no). At the heel the wheel turns past the
    # heel end (above); without it the route runs right to the heel end,
    # the adjuster nut at its end face (no bore, no notch in the body:
    # adjust with the neck off). At the headstock the wheel sits in an
    # open trough behind the nut (truss_rod_nut_length + 4 mm, no cover);
    # without it, behind a slotted (Fender) nut the key reaches the
    # adjuster through a notch truss_rod_key_hole_diameter wide
    # (truss_rod_nut_length + 2 mm long: the open start of its hole, all a
    # router can cut), and behind a shelf nut the covered trough is cut.
    truss_rod_spoke_wheel: Literal["auto", "yes", "no"] = "auto"
    truss_rod_key_hole_diameter: float = 8.0
    # truss_rod_profile: "standard" is the rod above, its adjusting end
    # stepping down to an 11 mm pocket; adjusted at the headstock that end
    # lies in the thin neck by the nut, so the neck is made thick enough at
    # the first fret to leave TRUSS_ROD_MIN_FLOOR under it (1 mm more than
    # the default 17 mm). "low_profile" is a low-profile two-way rod (as
    # StewMac's / Hosco's Hot Rod Low-profile: a straight 1/4 x 3/8 in
    # channel, 4 mm hex key): one straight channel
    # truss_rod_low_profile_width x truss_rod_low_profile_depth, no step
    # or pocket, which fits the thin neck as it is. "auto" spoke wheels
    # are for the standard rod only.
    truss_rod_profile: Literal["standard", "low_profile"] = "standard"
    truss_rod_low_profile_width: float = 6.35
    truss_rod_low_profile_depth: float = 9.5
    # truss_rod_sleeve_bore: model the adjuster sleeve's hand-drilled bore
    # at the heel (and note it in the neck's G-code); truss_rod_trough: rout
    # the adjuster's trough in the headstock face (and cut its cover). Turn
    # either off to leave that part to be made by hand, or not at all.
    truss_rod_sleeve_bore: bool = True
    truss_rod_trough: bool = True
    # Carbon fibre reinforcement (neck_carbon_rods): two bars glued into
    # channels in the neck's top, one each side of the truss rod, flush
    # under the fretboard, stiffening the neck against bending and twist.
    # neck_carbon_rod_size picks the bars' section from CARBON_ROD_SIZES
    # (width x height): 3.2 x 6.35 mm (1/8 x 1/4 in, the default), 4 x 4 mm,
    # or StewMac's 3.2 x 9.5 mm (1/8 x 3/8 in, which needs a thicker neck);
    # "custom" takes neck_carbon_rod_width wide and neck_carbon_rod_depth
    # tall. Each channel is CLEARANCE (0.1 mm) wider for the epoxy. They run
    # from neck_carbon_rod_start past the nut for neck_carbon_rod_length
    # (empty: to where the heel flattens, clear of the neck screws),
    # neck_carbon_rod_offset from the centerline (empty: beside the truss
    # rod's widest part along them, CARBON_ROD_GAP of wood between). Each
    # channel must leave CARBON_ROD_FLOOR of wood under it, out to its
    # edge, and CARBON_ROD_WALL to the truss rod's route and the neck's
    # sides.
    neck_carbon_rods: bool = False
    neck_carbon_rod_size: Literal["3.2x6.35", "4x4", "3.2x9.5", "custom"] = "3.2x6.35"
    neck_carbon_rod_width: float = 3.2
    neck_carbon_rod_depth: float = 6.35
    neck_carbon_rod_start: float = 20.0
    neck_carbon_rod_length: float | None = None
    neck_carbon_rod_offset: float | None = None
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
    # needs it. headstock_bass_side says where the low E is as drawn: -Y on
    # the right-handed Prototype001 body (the long-horn side; handedness
    # "left" mirrors it). The shoulder
    # and tip widths and shifts, when set, override the resolved ends
    # (shifts toward the bass side positive).
    headstock_style: HeadstockStyle = "3+3"
    headstock_bass_side: Literal["-y", "+y"] = "-y"
    headstock_length: float = 150.0
    headstock_root_length: float = 45.0
    # A headless neck (headless): no headstock and no tuners, the neck
    # ending headless_length behind the nut in a flat headpiece the
    # string anchor screws onto, as wide as the nut; the strings are tuned
    # at the bridge (a HeadlessBridgeSpec). headstock_style and the tuner
    # values are then not used.
    headless: bool = False
    headless_length: float = 35.0
    headstock_shoulder_width: float | None = None
    headstock_tip_width: float | None = None
    headstock_shoulder_shift: float | None = None
    headstock_tip_shift: float | None = None
    # "drawn" replaces the fitted outline with the edges drawn in the web
    # app's headstock editor: (distance from the nut, half-width) points
    # per side, each ending at the tip. The tuner holes still come from
    # headstock_style, and every hole must stay at least
    # tuner_edge_offset from the drawn edge. Empty edges fall back to
    # the fitted outline, so the default "drawn" with no edges drawn yet
    # is the fitted outline (and the web app's headstock editor is open).
    headstock_outline: Literal["fitted", "drawn"] = "drawn"
    headstock_bass_edge: tuple[tuple[float, float], ...] = ()
    headstock_treble_edge: tuple[tuple[float, float], ...] = ()
    # Points shaping a drawn headstock's tip, (how far past the tip line,
    # y), across the tip from -Y to +Y; empty, the tip is a straight cut.
    headstock_tip_points: tuple[tuple[float, float], ...] = ()
    # headstock_angle tilts the face back from the nut (0 for a flat,
    # Fender-style headstock). headstock_face_drop sets the face that far
    # below the glue face at the nut; empty, a flat headstock is set down
    # FLAT_HEADSTOCK_FACE_DROP (4 mm: its 16 mm in the bottom of a 20 mm
    # blank below the fretboard) so the strings still break over the nut,
    # and an angled one is not.
    headstock_angle: float = 8.0
    headstock_thickness: float = 16.0
    headstock_face_drop: float | None = None
    # Behind the nut's seat the top eases onto the headstock face over
    # headstock_face_transition, Stratocaster style (a smooth curve, level
    # at the seat and meeting the face at its slope); 0 for a sharp break.
    headstock_face_transition: float = 12.0
    tuner_hole_diameter: float = 10.0
    # Lettering engraved into the headstock face (a name or a logo's
    # words): headstock_engraving_text ("" for none) in
    # headstock_engraving_font (geometry.lettering's single-stroke "sans",
    # Hershey "script" or Hershey "gothic"), its capitals
    # headstock_engraving_height tall,
    # centred on headstock_engraving_x (from the nut, negative along the
    # headstock; None: HEADSTOCK_ENGRAVING_SETBACK behind the nut's seat)
    # and headstock_engraving_y, running along headstock_engraving_angle
    # degrees from +X (90: across the headstock, read with it pointing up),
    # cut headstock_engraving_depth deep with the engraving V-bit,
    # following the face. It must keep HEADSTOCK_ENGRAVING_CLEARANCE from
    # the face's edge, the nut's seat, the tuner holes and a truss rod
    # adjuster's trough.
    headstock_engraving_text: str = ""
    headstock_engraving_font: FontName = "sans"
    headstock_engraving_height: float = 6.0
    headstock_engraving_x: float | None = None
    headstock_engraving_y: float = 0.0
    headstock_engraving_angle: float = 90.0
    headstock_engraving_depth: float = 1.0
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
    # nut_style "shelf" stands the nut on the neck's flat seat
    # (nut_shelf_length) in front of the fretboard's end; "slot" is the
    # Fender (Telecaster) way: the fretboard runs on past the nut line, a
    # slot nut_thickness wide milled nut_slot_depth below its crown there,
    # and the nut is glued into that slot. Behind it the board carries on
    # at full height for nut_slot_lip, then slopes down to the glue face
    # over nut_slot_taper, where it ends. With "slot" a headstock-adjusted
    # truss rod is reached Fender style too, uncovered (see
    # truss_rod_spoke_wheel). "zero_fret" puts a fret on the nut line (the
    # scale starts there) and the nut, only a string guide now, a
    # zero_fret_gap behind it in a slot like "slot"'s: the board runs on
    # past the nut line to hold both. A locking nut takes the nut's place
    # whichever style is set.
    nut_style: Literal["shelf", "slot", "zero_fret"] = "shelf"
    zero_fret_gap: float = 3.0
    nut_thickness: float = 3.5
    nut_slot_depth: float = 3.0
    nut_slot_lip: float = 3.0
    nut_slot_taper: float = 3.0
    # A Floyd Rose locking nut screwed down from the top (see
    # geometry.neck.locking_nut): "auto" takes the Floyd Rose Original R2
    # with a Floyd Rose bridge (the 7- or 8-string nut on a seven- or
    # eight-string) and a plain nut otherwise; "none" is always a plain
    # nut; "r2" (41.3 mm), "r3" (42.85 mm), "r7" (47.6 mm, seven strings)
    # or "r8" (53.8 mm, eight strings; each needs nut_width at least that)
    # always a locking nut. Its seat on the neck runs the
    # nut's depth + 1 mm behind the nut line before the headstock face
    # starts. Its shelf sits from the frets' tops (fret_height above the
    # fretboard): the R2's on the fretboard, which runs on under the nut,
    # the R3's on the neck's seat on a shim. The two mounting screws get
    # locking_nut_screw_diameter pilot holes locking_nut_screw_depth below
    # the glue face, drilled by hand through the nut.
    locking_nut: Literal["auto", "none", "r2", "r3", "r7", "r8"] = "auto"
    fret_height: float = 1.2
    locking_nut_screw_diameter: float = 2.5
    locking_nut_screw_depth: float = 8.0
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
    def neck_runs_through(self) -> bool:
        """Whether the neck runs on into the body (neck-through or one piece)."""
        return self.neck_joint in ("neck_through", "one_piece")

    @property
    def left_handed(self) -> bool:
        """Return whether the instrument is built as its left-handed mirror."""
        return self.handedness == "left"

    @property
    def bass_sign(self) -> float:
        """Return +1.0 when the bass side is +Y, -1.0 when it is -Y.

        ``headstock_bass_side`` as drawn, the other side when left-handed.
        """
        drawn = -1.0 if self.headstock_bass_side == "-y" else 1.0
        return -drawn if self.left_handed else drawn

    @property
    def built_body_shape(self) -> BodyShapeSpec:
        """Return the body shape as built: ``body_shape``, mirrored when left-handed."""
        return mirrored_shape(self.body_shape) if self.left_handed else self.body_shape

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
        # A set neck's pocket is a tight glue joint.
        clearance = (
            self.set_neck_glue_gap
            if self.neck_joint == "set"
            else self.body_neck_pocket_clearance
        )
        if not math.isfinite(clearance) or clearance < 0.0:
            raise NeckGeometryError("The neck pocket's clearance must not be negative.")
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
        bass_sign = self.bass_sign
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
            elif points:
                # A lone tuner on this side (a 4+1's): the edge runs
                # straight past it, tuner_edge_offset out.
                ((_, edge),) = points
                shoulder_half = max(reserve_shoulder or 0.0, edge)
                tip_half = max(reserve_tip or 0.0, edge)
            else:
                shoulder_half = reserve_shoulder or 0.0
                tip_half = reserve_tip or 0.0

            # The posts follow converging strings, so a row's holes are not
            # quite in line and the fitted edge passes nearer the end ones;
            # past the 0.5 mm the clearance check allows, move it out.
            def edge_at(distance: float, shoulder: float, tip: float) -> float:
                fraction = (distance - root) / (length - root)
                return shoulder + (tip - shoulder) * fraction

            short = max(
                (
                    edge - edge_at(d, shoulder_half, tip_half)
                    for d, edge in points
                    if d > root
                ),
                default=0.0,
            )
            if short > 0.5:
                shoulder_half += short
                tip_half += short
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
        self._check_bridge_strings()
        # The steps are drawn wherever they fall; the build checks them.
        return self._body_layout(self.neck_outline(), check_steps=False)

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
        if self.headless:
            return self._headless_design()
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
            tip_points=self.built_tip_points() if drawn else (),
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

    def _headless_design(self) -> tuple[HeadstockPlan, TunerLayout]:
        """Return a headless neck's headpiece and its (empty) tuner layout.

        The headpiece runs ``headless_length`` behind the nut, as wide as
        the nut all along; it has no tuner holes.
        """
        plan = HeadstockPlan(
            self.headless_length,
            self.nut_width,
            min(self.headstock_root_length, self.headless_length / 2.0),
            self.nut_width,
            self.nut_width,
            bass_sign=self.bass_sign,
        )
        tuners = TunerLayout(
            plan,
            hole_diameter=self.tuner_hole_diameter,
            station_distances=(),
            side_offsets=(),
        )
        return plan, tuners

    def tuner_centres(self) -> tuple[tuple[str, float, float], ...]:
        """Return ``(side, x, y)`` of every tuner hole, without validating.

        The web app's headstock editor draws these fixed holes under the
        edges being drawn; a headless neck has none.
        """
        if self.headless:
            return ()
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
        if self.built_body_shape.neck_bolts:
            centres = [(heel_end + x, y) for x, y in self.built_body_shape.neck_bolts]
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

        body_outline = self.built_body_shape.outline_points(
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
    def switch_shaft_hole_diameter(self) -> float:
        """Return the selector's hole: ``body_switch_shaft_hole_diameter``,
        else the chosen ``body_switch``'s own (``SWITCH_SHAFT_HOLE_DIAMETERS``).
        """
        if self.body_switch_shaft_hole_diameter is not None:
            return self.body_switch_shaft_hole_diameter
        return SWITCH_SHAFT_HOLE_DIAMETERS[self.body_switch]

    @property
    def face_drop(self) -> float:
        """Return how far the headstock face lies below the glue face.

        ``headstock_face_drop``, or when empty ``FLAT_HEADSTOCK_FACE_DROP``
        for a flat (0 degree) headstock and nothing for an angled one.
        """
        if self.headstock_face_drop is not None:
            return self.headstock_face_drop
        return FLAT_HEADSTOCK_FACE_DROP if self.headstock_angle == 0.0 else 0.0

    @property
    def neck_angle_degrees(self) -> float:
        """Return the neck's back-tilt: ``neck_angle``, or the bridge's own.

        Raises:
            NeckGeometryError: For an angle outside 0..``MAX_NECK_ANGLE``.
        """
        angle = self.neck_angle
        if self.neck_runs_through:
            # The neck blank is the body's own centre: nothing to tilt.
            if angle not in (None, 0.0):
                raise NeckGeometryError(
                    "A neck-through or one-piece neck takes no neck_angle (it is "
                    "the body's own wood): leave it empty or 0."
                )
            return 0.0
        if angle is None:
            return (
                NECK_ANGLE_TUNE_O_MATIC
                if isinstance(self.body_bridge, TuneOMaticSpec)
                else 0.0
            )
        if not math.isfinite(angle) or not 0.0 <= angle <= MAX_NECK_ANGLE:
            raise NeckGeometryError(
                f"neck_angle must lie between 0 and {MAX_NECK_ANGLE:g} degrees."
            )
        return angle

    def neck_pivot(self) -> tuple[float, float]:
        """Return where the tilted neck turns: the pocket floor's heel end.

        ``(x, z)``: the heel end along the neck, ``heel_thickness`` below
        the top (the neck's glue face, z = 0).
        """
        outline = self.neck_outline()
        return outline.last_fret_position + outline.heel_length, -self.heel_thickness

    def neck_to_body(self, x: float, z: float) -> tuple[float, float]:
        """Return a point of the neck (x along it, z up from its glue face)
        where it lies on the body, the neck tilted by ``neck_angle``."""
        angle = math.radians(self.neck_angle_degrees)
        pivot_x, pivot_z = self.neck_pivot()
        dx, dz = x - pivot_x, z - pivot_z
        return (
            pivot_x + dx * math.cos(angle) - dz * math.sin(angle),
            pivot_z + dx * math.sin(angle) + dz * math.cos(angle),
        )

    def bridge_scale_line(self) -> float:
        """Return the X on the body where the saddles go.

        The scale line, moved for a tilted neck so the strings' scale (and
        the 12th fret halfway) is kept along their tilted line: the point
        a scale from the nut along the fret tops, carried with the neck.
        """
        scale = self.centre_scale
        if self.neck_angle_degrees == 0.0:
            return scale
        return self.neck_to_body(scale, self.fretboard_thickness + self.fret_height)[0]

    @property
    def centre_scale(self) -> float:
        """Return the scale on the centerline: the mean of a multiscale's two."""
        if self.bass_scale_length is None:
            return self.scale_length
        return (self.scale_length + self.bass_scale_length) / 2.0

    @property
    def fret_skew(self) -> FretSkew:
        """Return how the frets lean: slant and multiscale fan together."""
        bass_sign = self.bass_sign
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

    @property
    def truss_rod_spoke_wheel_fitted(self) -> bool:
        """Return whether the truss rod's adjuster has a spoke wheel.

        ``truss_rod_spoke_wheel``; ``"auto"`` fits one at the heel only,
        on a standard rod.
        """
        if self.truss_rod_spoke_wheel == "auto":
            return (
                self.truss_rod_adjustment == "heel"
                and self.truss_rod_profile == "standard"
            )
        return self.truss_rod_spoke_wheel == "yes"

    def _truss_rod_key_notch(self) -> bool:
        """Whether a headstock adjuster is reached through a key notch.

        Without a spoke wheel: only the open start of the key's hole is
        routed (a full trough for the adjuster's head would break through
        the headstock's root by the nut); behind a shelf nut it is covered.
        """
        return (
            self.truss_rod_adjustment == "headstock"
            and not self.truss_rod_spoke_wheel_fitted
        )

    def truss_rod(self, outline: NeckOutline) -> TrussRodChannel:
        """Return the truss-rod channel with its adjusting nut's pocket."""
        heel = self.truss_rod_adjustment == "heel"
        wheel = self.truss_rod_spoke_wheel_fitted
        key_notch = self._truss_rod_key_notch()
        shelf = self.nut_seat_length() + self.nut_shelf_reach()
        access = self.truss_rod_access_length
        if access is None:
            access = self.truss_rod_nut_length + 2.0
            if not heel and wheel:
                # The wheel in an open trough behind the nut, room to
                # turn it.
                access = self.truss_rod_nut_length + 4.0
            elif key_notch:
                # Only the open start of the key's hole.
                access = self.truss_rod_nut_length + 2.0
        if heel and not wheel:
            # The adjuster nut at the heel's end face: no notch past it.
            access = 0.0
        fit = self.truss_rod_fit(outline)
        start = self._truss_rod_start(heel, shelf)
        length = fit.route_length
        if heel and self.truss_rod_length is None:
            # The adjuster stays at the heel: a shorter rod starts later.
            start += fit.longest - fit.outside - length
        low = self.truss_rod_profile == "low_profile"
        channel = TrussRodChannel(
            outline,
            start,
            length,
            self.truss_rod_low_profile_width if low else self.truss_rod_width,
            self.truss_rod_low_profile_depth if low else self.truss_rod_depth,
            adjustment_side="heel" if heel else "nut",
            step_length=0.0 if low else self.truss_rod_step_length,
            step_width=self.truss_rod_step_width,
            step_depth=self.truss_rod_step_depth,
            pocket_length=0.0 if low else self.truss_rod_pocket_length,
            pocket_width=self.truss_rod_pocket_width,
            pocket_depth=self.truss_rod_pocket_depth,
            sleeve_length=self.truss_rod_sleeve_length if heel and wheel else 0.0,
            sleeve_diameter=(
                self.truss_rod_sleeve_diameter
                if self.truss_rod_sleeve_bore and wheel
                else 0.0
            ),
            nut_diameter=self.truss_rod_nut_diameter,
            nut_length=self.truss_rod_nut_length,
            access_length=access if heel or self.truss_rod_trough else 0.0,
            access_diameter=self.truss_rod_key_hole_diameter if key_notch else 0.0,
            shelf_length=shelf,
            # A low-profile rod's adjuster is centred in its channel.
            rod_axis_depth=(
                self.truss_rod_low_profile_depth / 2.0
                if low
                else self.truss_rod_axis_depth
            ),
        )
        if not heel and wheel and channel.adjuster_boundary:
            # The wheel's trough by the nut: an angled headstock's root is
            # only its thickness deep there, a flat one's set down too.
            wood = self.headstock_thickness + (
                self.face_drop if self.headstock_angle == 0.0 else 0.0
            )
            if channel.adjuster_depth + TRUSS_ROD_MIN_FLOOR > wood + 1e-9:
                raise NeckGeometryError(
                    f"A spoke wheel at the headstock needs a trough "
                    f"{channel.adjuster_depth:g} mm deep, which would break "
                    f"through the {wood:g} mm headstock root by the nut; use a "
                    "flat headstock, a thicker headstock_thickness, or no "
                    "spoke wheel (a key's notch)."
                )
        if not heel and channel.adjuster_boundary:
            trough = channel.adjuster_boundary
            trough_end = min(p.x for p in trough)
            front = max(p.x for p in trough)
            half = max(p.y for p in trough)
            _, tuners = self.headstock_design()
            for hole in tuners.holes:
                if _rectangle_gap(trough_end, front, half, hole) < 3.0:
                    raise NeckGeometryError(
                        f"The truss-rod trough reaches {-trough_end:.0f} mm into the "
                        f"headstock, too close to tuner {hole.side} {hole.index}; "
                        "shorten truss_rod_access_length or move the tuners"
                        + (
                            " (or leave the spoke wheel out: a key's notch is "
                            "narrower)."
                            if self.truss_rod_spoke_wheel_fitted
                            else "."
                        )
                    )
        return channel

    def _truss_rod_start(self, heel: bool, shelf: float) -> float:
        """Return where the truss rod's route starts, from the nut.

        At the heel ``truss_rod_start``; at the headstock the back of the
        nut's seat, the adjusting end's pocket under it.
        """
        return self.truss_rod_start if heel else -shelf

    def first_fret_thickness_needed(self) -> float:
        """Return the neck's thickness at the first fret, board included.

        ``first_fret_thickness``, made thick enough for a standard truss
        rod adjusted at the headstock: its deepest pocket or step, which
        lies in the neck by the nut, keeps ``TRUSS_ROD_MIN_FLOOR`` of wood
        under it.
        """
        if (
            self.truss_rod_adjustment != "headstock"
            or self.truss_rod_profile != "standard"
        ):
            return self.first_fret_thickness
        # The neck's back curves up toward its sides (the D profile), so
        # each part needs its floor at its edges, where the neck is
        # thinnest under it; the narrow neck by the nut is the worst.
        half_neck = self.nut_width / 2.0
        exponent = self.neck_profile_exponent
        needed = 0.0
        for length, width, depth in (
            (
                self.truss_rod_pocket_length,
                self.truss_rod_pocket_width,
                self.truss_rod_pocket_depth,
            ),
            (
                self.truss_rod_step_length,
                self.truss_rod_step_width,
                self.truss_rod_step_depth,
            ),
            (1.0, self.truss_rod_width, self.truss_rod_depth),
        ):
            if length <= 0.0:
                continue
            edge = min(width / 2.0 / half_neck, 0.99)
            share = (1.0 - edge**exponent) ** (1.0 / exponent)
            needed = max(needed, (depth + TRUSS_ROD_MIN_FLOOR) / share)
        return max(
            self.first_fret_thickness,
            math.ceil((self.fretboard_thickness + needed) * 10.0) / 10.0,
        )

    def truss_rod_fit(self, outline: NeckOutline) -> TrussRodFit:
        """Return the longest rod the neck takes and the one it is routed for.

        Raises:
            NeckGeometryError: When ``truss_rod_rod_length`` is longer than
                the neck takes, or no stock length fits.
        """
        heel = self.truss_rod_adjustment == "heel"
        wheel = self.truss_rod_spoke_wheel_fitted
        shelf = self.nut_seat_length() + self.nut_shelf_reach()
        heel_end = outline.last_fret_position + outline.heel_length
        start = self._truss_rod_start(heel, shelf)
        if heel and not wheel:
            # The adjuster nut ends at the heel's end face: the whole rod
            # lies in the route.
            end, outside = heel_end, 0.0
        else:
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
        and one at the far end hold it. A spoke wheel's trough, or a
        slotted (Fender style) nut's key notch, is left open.
        """
        nut = self.locking_nut_placed()
        if (
            not self.truss_rod_cover
            or (nut is not None and not nut.is_locking)
            or self.truss_rod_spoke_wheel_fitted
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

    def locking_nut_placed(self) -> LockingNut | None:
        """Return the nut placed on the fretboard, or ``None`` for a plain nut.

        A locking nut, or with ``nut_style`` "slot" a slotted Fender style
        nut (``LockingNut.slotted``), "zero_fret" one set back behind a zero
        fret; ``None`` for a nut on the neck's shelf.

        Raises:
            NeckGeometryError: When the nut does not fit the neck (see
                ``LockingNut``).
        """
        kind = self.locking_nut
        if kind == "auto":
            kind = (
                FLOYD_ROSE_NUTS.get(self.string_count, "r2")
                if isinstance(self.body_bridge, FloydRoseSpec)
                else "none"
            )
        if kind == "none":
            if self.nut_style not in ("shelf", "slot", "zero_fret"):
                raise NeckGeometryError(
                    'nut_style must be "shelf", "slot" or "zero_fret".'
                )
            if self.nut_style in ("slot", "zero_fret"):
                if not math.isfinite(self.nut_slot_depth) or self.nut_slot_depth <= 0:
                    raise NeckGeometryError(
                        "nut_slot_depth must be finite and positive."
                    )
                return LockingNut.slotted(
                    thickness=self.nut_thickness,
                    slot_depth=self.nut_slot_depth,
                    lean=self.fret_skew.at(0.0),
                    neck_width=self.nut_width,
                    fretboard_thickness=self.fretboard_thickness,
                    lip=self.nut_slot_lip,
                    taper=self.nut_slot_taper,
                    set_back=(
                        self.zero_fret_gap if self.nut_style == "zero_fret" else 0.0
                    ),
                )
            return None
        if not math.isfinite(self.fret_height) or self.fret_height < 0.0:
            raise NeckGeometryError("fret_height must be finite and non-negative.")
        # With nut_style "zero_fret" the locking nut goes behind the zero
        # fret, zero_fret_gap back.
        return LockingNut.placed(
            LOCKING_NUT_SPECS[kind],
            lean=self.fret_skew.at(0.0),
            neck_width=self.nut_width,
            fretboard_thickness=self.fretboard_thickness,
            fret_height=self.fret_height,
            screw_diameter=self.locking_nut_screw_diameter,
            screw_depth=self.locking_nut_screw_depth,
            set_back=self.zero_fret_gap if self.nut_style == "zero_fret" else 0.0,
        )

    def nut_seat_length(self) -> float:
        """Return the flat seat behind the nut line: longer for a locking nut."""
        nut = self.locking_nut_placed()
        return self.nut_shelf_length if nut is None else nut.seat_length

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
        bass_sign = self.bass_sign
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

    def _body_layout(
        self, outline: NeckOutline, *, check_steps: bool = True
    ) -> BodyLayout:
        heel_end = outline.last_fret_position + self.heel_length
        # Body features ride with the heel end, bridge features with the
        # scale length (see the body_* parameter comments).
        widening = self.body_widening_amount()
        shape = widened_shape(self.built_body_shape, widening)
        body_outline = TracedOutline(shape.outline_points(heel_end, widening))
        neck_pocket = TracedCavity(
            "Neck pocket",
            self._neck_pocket_outline(outline, heel_end),
            self.heel_thickness,
            floor_slope=math.tan(math.radians(self.neck_angle_degrees)),
        )
        # Only a bolt-on neck has bolts: a set neck is glued, and a
        # neck-through body has no pocket (its outline stays as where the
        # neck passes, for the keep-outs).
        neck_bolts = (
            self._neck_bolt_holes(outline, heel_end, neck_pocket)
            if self.neck_joint == "bolt_on"
            else ()
        )
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

        bass_sign = self.bass_sign

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

        # The saddles' line, moved with a tilted neck.
        saddles = self.bridge_scale_line()
        bridge_spec = self.body_bridge
        if isinstance(bridge_spec, FloydRoseSpec) and self.left_handed:
            # The tremolo arm (and the recess's wider side) go with the
            # treble strings.
            bridge_spec = replace(
                bridge_spec,
                treble_side="-y" if bridge_spec.treble_side == "+y" else "+y",
            )
        if isinstance(bridge_spec, SingleStringBridgeSpec):
            # Each unit stands at its own string's scale, square to it.
            bridge = bridge_spec.hardware(
                saddles, self.body_thickness, lean=fan.at(scale)
            )
        else:
            hardware = bridge_spec.hardware(saddles, self.body_thickness)
            if isinstance(self.body_bridge, TuneOMaticSpec) and bass_sign > 0.0:
                # Its bass post, set back, goes to the bass side.
                hardware = mirrored_hardware(hardware)
            bridge = turned_hardware(
                hardware,
                Point2D(saddles, 0.0),
                fan.at(scale) if self.bridge_follows_fan else 0.0,
                # A Tune-o-matic turns only where the strings rest; its
                # stop-bar studs stay square.
                (lambda name: name.startswith("Bridge post"))
                if isinstance(self.body_bridge, TuneOMaticSpec)
                else None,
            )
        bridge_mounting = bridge.mounting
        if bridge.footprint and not all(
            point_in_polygon(p, body_outline.points) for p in bridge.footprint
        ):
            raise BodyGeometryError(
                "The bridge's plate lies outside the body outline: lengthen the "
                "body behind the bridge or choose another bridge."
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
        own_offset = self.body_bridge_pickup_offset + turned_reach(
            bridge_type, bridge_angle - single_slant
        )
        needed_offset = self._bridge_pickup_clearance_offset(
            bridge, bridge_type, bridge_angle, bass_sign
        )
        bridge_pickup_x = scale - max(own_offset, needed_offset)
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
        # Moved forward to clear the bridge, the bridge pickup must still
        # leave the next pickup's route alone; if it cannot, say so here
        # rather than as a bare overlap when the body is built.
        neighbour = middle_pickup or neck_pickup
        if (
            bridge_pickup is not None
            and neighbour is not None
            and needed_offset > own_offset
            and outlines_overlap(bridge_pickup.outline, neighbour.outline)
        ):
            raise BodyGeometryError(
                f"The bridge pickup cannot clear the {self.body_bridge.kind} "
                f"bridge: moved to {scale - bridge_pickup_x:.1f} mm ahead of the "
                f"scale line, its route overlaps the {neighbour.name.lower()}. "
                "Choose another bridge or pickup layout, or move that pickup "
                "toward the neck."
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
                count=self.body_battery_count,
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
        # The bridge's own rear cavities (a Floyd Rose's spring cavity)
        # close with a six-screw sheet cover too.
        for rear in bridge.rear_cavities:
            controls = controls.with_covers(rear_cover(rear, 6))
        jack_hole, jack_cavity = self._jack(
            body_outline.points,
            Point2D(heel_end + shape.jack_offset, shape.jack_y),
            shape.jack_direction_degrees,
            controls,
        )
        holes: list[DrilledHole] = [*bridge.holes, *controls.holes]
        # A pickguard's square openings, one per pickup cover.
        pickup_holes: list[tuple[str, tuple[Point2D, ...]]] = []
        for label, kind, pickup_x, angle in (
            ("Neck", neck_type, neck_pickup_x, neck_angle),
            ("Middle", middle_type, middle_pickup_x, middle_angle),
            ("Bridge", bridge_type, bridge_pickup_x, bridge_angle),
        ):
            for index, opening in enumerate(
                pickup_openings(kind, pickup_x, bass_sign, angle, strings), start=1
            ):
                suffix = f" {index}" if kind == "precision_bass" else ""
                pickup_holes.append((f"{label} pickup opening{suffix}", opening))
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
        guard = self._pickguard(
            shape,
            heel_end,
            body_outline.points,
            [route for route in (neck_pickup, middle_pickup, bridge_pickup) if route],
            [
                *(route.outline for route in bridge.top_cavities),
                # The bridge's own plate, where it reaches past its routes.
                *((bridge.footprint,) if bridge.footprint else ()),
                *(route.outline for route in bridge.through_cavities),
                # A bridge with no route of its own (a string-through
                # hardtail, a Tune-o-matic) has its holes, and its saddles
                # reaching ahead of the scale line.
                *(
                    ((Point2D(scale - SADDLE_REACH, 0.0),),)
                    if not bridge.top_cavities
                    else ()
                ),
                *(
                    tuple(
                        Point2D(
                            hole.center_x + dx * hole.diameter / 2.0,
                            hole.center_y + dy * hole.diameter / 2.0,
                        )
                        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                    )
                    for hole in bridge.holes
                ),
            ],
            controls,
            neck_pocket.outline,
            pickup_holes,
            truss_rod_access.outline if truss_rod_access else (),
        )
        if guard is not None:
            controls = controls.with_covers(
                ControlFeatures(top_marks=guard.screw_spots, covers=(guard.plate,))
            )
        contours = self._contours(shape, body_outline.points, heel_end, bass_sign)
        carve_pickups = [
            p.outline for p in (neck_pickup, middle_pickup, bridge_pickup) if p
        ]
        carve_bridge = [
            *(c.outline for c in (*bridge.top_cavities, *bridge.through_cavities)),
            *((bridge.footprint,) if bridge.footprint else ()),
            *(
                tuple(
                    Point2D(
                        hole.center_x + dx * hole.diameter / 2.0,
                        hole.center_y + dy * hole.diameter / 2.0,
                    )
                    for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1))
                )
                for hole in bridge.holes
            ),
        ]
        carved_top = self._carved_top(
            body_outline.points,
            [
                neck_pocket.outline,
                *((truss_rod_access.outline,) if truss_rod_access else ()),
                *carve_pickups,
                *carve_bridge,
            ],
            carve_pickups,
            carve_bridge,
            contours,
        )

        stepped_top = self._stepped_top(
            shape,
            heel_end,
            body_outline.points,
            neck_pocket.outline,
            [*carve_pickups, *carve_bridge] if check_steps else [],
            contours,
            guard,
        )
        lowered = carved_top or stepped_top

        def carve_drop(route: Cavity) -> float:
            if lowered is None:
                return 0.0
            return max(lowered.drop_at(p.x, p.y) for p in route.outline)

        if lowered is not None:
            # The back's cavities keep their top wall under the arched or
            # stepped top.
            controls = replace(
                controls,
                control_cavity=self._under_carve(controls.control_cavity, carve_drop),
                switch_cavity=self._under_carve(controls.switch_cavity, carve_drop),
                battery_cavity=self._under_carve(controls.battery_cavity, carve_drop),
            )
            # A blade switch's slot still reaches its risen pocket.
            controls = _opened_into_controls(controls, self.body_thickness)
            bridge = replace(
                bridge,
                rear_cavities=tuple(
                    rear
                    for rear in (
                        self._under_carve(rear, carve_drop)
                        for rear in bridge.rear_cavities
                    )
                    if rear is not None
                ),
            )

        engraving = self._engraving(
            body_outline.points,
            [
                neck_pocket.outline,
                *((truss_rod_access.outline,) if truss_rod_access else ()),
                *(p.outline for p in (neck_pickup, middle_pickup, bridge_pickup) if p),
                *(c.outline for c in (*bridge.top_cavities, *bridge.through_cavities)),
                *((bridge.footprint,) if bridge.footprint else ()),
                *((jack_cavity.outline,) if jack_cavity else ()),
                *(c.outline for c in controls.top_cavities),
                *(c.outline for c in controls.through_cavities),
                # The back's cavities need not be dodged: only a route left
                # under too thin a top for the engraving.
                *(
                    route.outline
                    for rear in (
                        controls.control_cavity,
                        controls.switch_cavity,
                        controls.battery_cavity,
                        *bridge.rear_cavities,
                    )
                    if rear is not None
                    for route in (rear.cavity, *rear.steps)
                    if self.body_thickness - carve_drop(route) - route.depth
                    < self.body_engraving_depth + ENGRAVING_WALL
                ),
                *(c.outline for c in controls.covers if c.face == "top"),
                *(contour.region() for contour in contours),
            ],
            [
                *(
                    (hole.center, hole.diameter / 2.0)
                    for hole in (*holes, *controls.holes, *controls.top_marks)
                ),
                *(
                    (pivot, bridge_mounting.pivot_hole_diameter / 2.0)
                    for pivot in bridge_mounting.pivot_holes
                ),
            ],
            # A relief keeps to where the face is level.
            (lambda point: lowered.drop_at(point.x, point.y))
            if lowered is not None
            else None,
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
            (*bridge.top_cavities, *((jack_cavity,) if jack_cavity else ())),
            tuple(holes),
            (*bridge.through_cavities, *controls.through_cavities),
            bridge.rear_cavities,
            middle_pickup,
            (*neck_bolts, *self._string_ferrules(bridge.holes)),
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
            contours,
            truss_rod_access,
            guard,
            bridge.footprint,
            engraving,
            carved_top,
            stepped_top,
            # Built only (the body editor draws no wiring).
            self._wiring(
                body_outline.points,
                (
                    neck_pocket,
                    *((truss_rod_access,) if truss_rod_access else ()),
                    *((jack_cavity,) if jack_cavity else ()),
                ),
                [p for p in (neck_pickup, middle_pickup, bridge_pickup) if p],
                bridge,
                bridge_mounting,
                controls,
                (*holes, *controls.holes, *controls.top_marks),
                (*neck_bolts, *controls.back_marks),
                jack_hole,
                contours,
                lowered,
                guard,
            )
            if self.body_wire_channels and check_steps
            else Wiring(),
            bridge.notes,
        )

    def _string_ferrules(self, holes: tuple[DrilledHole, ...]) -> list[DrilledHole]:
        """Return the counterbores from the back for the strings' ferrules.

        One under every hole a string passes through the body by
        (``body_string_ferrule_diameter`` x ``_depth``); none with a depth
        of 0.

        Raises:
            BodyGeometryError: For a ferrule not wider than its string's
                hole, or a depth not leaving half the body.
        """
        depth = self.body_string_ferrule_depth
        diameter = self.body_string_ferrule_diameter
        through = [hole for hole in holes if "through hole" in hole.name]
        if not through or depth == 0.0:
            return []
        if not math.isfinite(depth) or not 0.0 < depth < self.body_thickness / 2.0:
            raise BodyGeometryError(
                "body_string_ferrule_depth must be 0 or positive and under half "
                "the body's thickness."
            )
        if not math.isfinite(diameter) or diameter <= max(h.diameter for h in through):
            raise BodyGeometryError(
                "body_string_ferrule_diameter must be wider than the string holes."
            )
        return [
            DrilledHole(
                hole.name.replace("through hole", "ferrule"),
                hole.center_x,
                hole.center_y,
                diameter,
                depth,
            )
            for hole in through
        ]

    def _wiring(
        self,
        outline: tuple[Point2D, ...],
        others: tuple[Cavity, ...],
        pickups: list[TracedCavity],
        bridge: BridgeHardware,
        mounting: BridgeMounting,
        controls: ControlFeatures,
        top_holes: tuple[DrilledHole, ...],
        back_holes: tuple[DrilledHole, ...],
        jack: JackHole | None,
        contours: tuple[ContourCut, ...],
        lowered: CarvedTop | SteppedTop | None,
        guard: Pickguard | None,
    ) -> Wiring:
        """Return the wire channels and holes (see ``body_wire_channels``).

        No controls, no wiring.
        """
        thickness = self.body_thickness

        def from_top(cavity: Cavity, face: bool = True) -> WireSpace:
            deepest = getattr(cavity, "deepest", cavity.depth)
            return WireSpace(
                cavity.name,
                cavity.outline,
                max(0.0, thickness - deepest),
                thickness,
                "top" if face else None,
            )

        def from_back(rear: RearCavity) -> WireSpace:
            return WireSpace(
                rear.name,
                rear.cavity.outline,
                0.0,
                rear.cavity.depth,
                "back",
                (rear.cover_recess.outline, *(step.outline for step in rear.steps)),
            )

        def drilled(hole: DrilledHole, back: bool = False) -> WireSpace:
            return WireSpace(
                hole.name,
                _circle_points(hole.center, hole.diameter / 2.0),
                0.0 if back else max(0.0, thickness - hole.depth),
                min(hole.depth, thickness) if back else thickness,
            )

        plate = [c for c in controls.top_cavities if c.name == "Control cavity"]
        if controls.control_cavity is not None:
            control = from_back(controls.control_cavity)
        elif plate:
            control = replace(
                from_top(plate[0]),
                parts=tuple(
                    c.outline for c in controls.top_cavities if c is not plate[0]
                ),
            )
        else:
            return Wiring()
        targets = [
            *(from_back(rear) for rear in bridge.rear_cavities),
            *(
                from_top(cavity)
                for cavity in (
                    *bridge.top_cavities,
                    *bridge.through_cavities,
                    *(
                        (mounting.sustain_block_cavity,)
                        if mounting.sustain_block_cavity is not None
                        else ()
                    ),
                )
            ),
            *(drilled(hole) for hole in bridge.holes),
            *(
                drilled(
                    DrilledHole(
                        "Pivot stud hole",
                        pivot.x,
                        pivot.y,
                        mounting.pivot_hole_diameter,
                        mounting.pivot_hole_depth,
                    )
                )
                for pivot in mounting.pivot_holes
            ),
        ]
        obstacles = [
            *(from_top(cavity, face=False) for cavity in others),
            *(from_top(cavity, face=False) for cavity in controls.top_cavities),
            *(from_top(cavity, face=False) for cavity in controls.through_cavities),
            *(drilled(hole) for hole in top_holes),
            *(drilled(hole, back=True) for hole in back_holes),
        ]
        if jack is not None:
            obstacles.append(_jack_space(jack, thickness))
        top_contours = [c for c in contours if c.face == "top"]
        back_contours = [c for c in contours if c.face == "back"]

        def top_at(point: Point2D) -> float:
            return (
                thickness
                - (lowered.drop_at(point.x, point.y) if lowered is not None else 0.0)
                - max((c.depth_at(point) for c in top_contours), default=0.0)
            )

        def back_at(point: Point2D) -> float:
            return max((c.depth_at(point) for c in back_contours), default=0.0)

        return plan_wiring(
            thickness,
            outline,
            control,
            [from_top(pickup) for pickup in pickups],
            targets,
            obstacles,
            switch=(
                from_back(controls.switch_cavity)
                if controls.switch_cavity is not None
                else None
            ),
            battery=(
                from_back(controls.battery_cavity)
                if controls.battery_cavity is not None
                else None
            ),
            covers=(guard.plate.outline,) if guard is not None else (),
            openings=(
                (
                    *(slot.outline for slot in guard.plate.slots),
                    *(
                        _circle_points(hole.center, hole.diameter / 2.0)
                        for hole in guard.plate.holes
                    ),
                )
                if guard is not None
                else ()
            ),
            top_at=top_at,
            back_at=back_at if back_contours else None,
        )

    def carbon_rods(
        self,
        outline: NeckOutline,
        surface: NeckBackSurface,
        channel: TrussRodChannel,
    ) -> CarbonRods | None:
        """Return the carbon fibre bars beside the truss rod, or ``None``.

        Raises:
            NeckGeometryError: For bars that would leave less than
                ``CARBON_ROD_FLOOR`` of wood under them, or come within
                ``CARBON_ROD_WALL`` of the truss rod's route or the neck's
                sides.
        """
        if not self.neck_carbon_rods:
            return None
        start = self.neck_carbon_rod_start
        if not math.isfinite(start) or start < 0.0:
            raise NeckGeometryError("neck_carbon_rod_start must not be negative.")
        # Empty: to where the heel flattens, clear of the neck screws.
        end = (
            start + self.neck_carbon_rod_length
            if self.neck_carbon_rod_length is not None
            else outline.last_fret_position - surface.heel_flat_start_offset
        )
        if self.neck_carbon_rod_size == "custom":
            bar = (self.neck_carbon_rod_width, self.neck_carbon_rod_depth)
        elif self.neck_carbon_rod_size in CARBON_ROD_SIZES:
            bar = CARBON_ROD_SIZES[self.neck_carbon_rod_size]
        else:
            raise NeckGeometryError(
                "neck_carbon_rod_size must be one of "
                f"{', '.join([*CARBON_ROD_SIZES, 'custom'])}."
            )
        width = bar[0] + CARBON_ROD_CLEARANCE
        beside = [
            half
            for front, back, half in channel.keep_clear()
            if front < end and back > start
        ]
        offset = self.neck_carbon_rod_offset
        if offset is None:
            offset = max(beside, default=0.0) + CARBON_ROD_GAP + width / 2.0
        rods = CarbonRods(start, end, offset, *bar)
        inner = offset - width / 2.0
        if beside and inner - max(beside) < CARBON_ROD_WALL - 1e-9:
            raise NeckGeometryError(
                f"The carbon rods' channels come within {inner - max(beside):.1f} "
                f"mm of the truss rod's route; keep {CARBON_ROD_WALL:g} mm "
                "between (a larger neck_carbon_rod_offset)."
            )
        outer = offset + width / 2.0
        rows = surface.mesh.rows
        steps = max(2, math.ceil((end - start) / 5.0))
        for index in range(steps + 1):
            x = start + (end - start) * index / steps
            half = self._neck_half_width_at(outline, x)
            if outer + CARBON_ROD_WALL > half + 1e-9:
                raise NeckGeometryError(
                    f"The carbon rods' channels come within "
                    f"{half - outer:.1f} mm of the neck's side {x:.0f} mm from "
                    f"the nut; keep {CARBON_ROD_WALL:g} mm (a smaller "
                    "neck_carbon_rod_offset or a later neck_carbon_rod_start)."
                )
            floor = -_back_z(rows, x, outer) - rods.depth
            if floor < CARBON_ROD_FLOOR - 1e-9:
                raise NeckGeometryError(
                    f"The carbon rods' channels leave {floor:.1f} mm of wood "
                    f"under them {x:.0f} mm from the nut; keep "
                    f"{CARBON_ROD_FLOOR:g} mm (shallower rods, a later "
                    "neck_carbon_rod_start or a thicker neck)."
                )
        return rods

    @staticmethod
    def _neck_half_width_at(outline: NeckOutline, x: float) -> float:
        """Return the neck's half width ``x`` from the nut."""
        if x >= outline.last_fret_position:
            return outline.heel_width / 2.0
        fraction = max(0.0, x) / outline.last_fret_position
        return (
            outline.nut_width + (outline.last_fret_width - outline.nut_width) * fraction
        ) / 2.0

    def neck_through_block_width(self, layout: BodyLayout) -> float:
        """Return a neck-through block's width.

        ``neck_through_width``, or wide enough for the pickup and bridge
        routes and holes (and the neck's heel) with ``NECK_THROUGH_MARGIN``
        of wood beside them.

        Raises:
            BodyGeometryError: For a width that is not positive.
        """
        if self.neck_through_width is not None:
            width = self.neck_through_width
            if not math.isfinite(width) or width <= 0.0:
                raise BodyGeometryError("neck_through_width must be positive.")
            return width
        outlines = [
            pickup.outline
            for pickup in (
                layout.neck_pickup,
                layout.middle_pickup,
                layout.bridge_pickup,
            )
            if pickup is not None
        ] + [
            cavity.outline
            for cavity in (*layout.extra_cavities, *layout.through_cavities)
            if cavity.name.startswith(NECK_THROUGH_BLOCK_FEATURES)
        ]
        reach = max(
            (abs(point.y) for points in outlines for point in points),
            default=0.0,
        )
        for hole in layout.holes:
            if hole.name.startswith(NECK_THROUGH_BLOCK_FEATURES) or (
                "pickup" in hole.name
            ):
                reach = max(reach, abs(hole.center_y) + hole.diameter / 2.0)
        reach = max(reach, self.heel_width / 2.0)
        return 2.0 * (reach + NECK_THROUGH_MARGIN)

    def neck_through_parts(
        self, outline: NeckOutline, plan: HeadstockPlan, layout: BodyLayout
    ) -> NeckThrough | None:
        """Return a neck-through body's block and wings, or ``None`` (bolt-on).

        A one-piece instrument's block is the whole body, with no wings.
        """
        if not self.neck_runs_through:
            return None
        neck = outline.boundary
        # The neck's plan from its +Y corner at the nut round the headstock
        # to its -Y corner, and its two sides from the nut on.
        head = (neck[0], *reversed(plan.boundary[2:]), neck[1])
        sides = (
            (neck[0], neck[7], neck[6], neck[5]),
            (neck[1], neck[2], neck[3], neck[4]),
        )
        return neck_through(
            layout.outline.points,
            (
                None
                if self.neck_joint == "one_piece"
                else self.neck_through_block_width(layout)
            ),
            head,
            sides,
            self.bass_sign,
            NECK_THROUGH_EDGE_REACH,
        )

    def headstock_solid(self, plan: HeadstockPlan) -> HeadstockSolid:
        """Return the headstock built on ``plan`` (see ``headstock_design``)."""
        return HeadstockSolid(
            plan,
            HeadstockAngleReference(plan.length, self.headstock_angle),
            self.headstock_thickness,
            self.face_drop,
            self.fret_skew.at(0.0),
            self.nut_seat_length(),
            self.headstock_face_transition,
        )

    def headstock_engraving_centre(self, headstock: HeadstockSolid) -> Point2D:
        """Return where the headstock lettering is centred (model frame)."""
        # Left-handed, it sits on the mirrored side.
        y = (
            -self.headstock_engraving_y
            if self.left_handed
            else self.headstock_engraving_y
        )
        if self.headstock_engraving_x is not None:
            return Point2D(self.headstock_engraving_x, y)
        seat_end = headstock.nut_seat_length + headstock.nut_reach
        return Point2D(-(seat_end + HEADSTOCK_ENGRAVING_SETBACK), y)

    def headstock_engraving_direction(self) -> float:
        """Return the direction the headstock lettering runs, in degrees.

        Left-handed, the mirror of ``headstock_engraving_angle`` read the
        other way (180 degrees less it): the text lies where the mirror
        image of the right-handed text would, its tops on the same side,
        but reads the right way round (set again, not mirrored).
        """
        if self.left_handed:
            return 180.0 - self.headstock_engraving_angle
        return self.headstock_engraving_angle

    def built_tip_points(self) -> tuple[tuple[float, float], ...]:
        """Return ``headstock_tip_points`` as built, mirrored when left-handed.

        Still ordered from -Y to +Y, as ``HeadstockPlan`` wants them.
        """
        if not self.left_handed:
            return self.headstock_tip_points
        return tuple((past, -y) for past, y in reversed(self.headstock_tip_points))

    def headstock_lettering(
        self,
        headstock: HeadstockSolid,
        tuner_layout: TunerLayout,
        truss_rod_channel: TrussRodChannel,
    ) -> Engraving | None:
        """Return the headstock face's lettering, or ``None`` without any.

        Raises:
            NeckGeometryError: For lettering the font cannot set, too deep,
                or running off the face, onto the nut's seat, into a
                tuner hole or the truss rod adjuster's trough.
        """
        text = self.headstock_engraving_text.strip()
        if not text:
            return None
        depth = self.headstock_engraving_depth
        if not math.isfinite(depth) or not 0.0 < depth < headstock.thickness / 2.0:
            raise NeckGeometryError(
                "headstock_engraving_depth must be positive and under half the "
                "headstock's thickness."
            )
        try:
            lines = text_lines(
                text,
                self.headstock_engraving_height,
                self.headstock_engraving_centre(headstock),
                self.headstock_engraving_direction(),
                self.headstock_engraving_font,
            )
        except GeometryException as error:
            raise NeckGeometryError(str(error)) from error
        clearance = HEADSTOCK_ENGRAVING_CLEARANCE
        face = offset_polygon(headstock.plan.boundary, clearance, inward=True)
        seat_end = -(headstock.nut_seat_length + headstock.nut_reach + clearance)
        trough = (
            offset_polygon(truss_rod_channel.adjuster_boundary, clearance, inward=False)
            if truss_rod_channel.adjuster_boundary
            and max(p.x for p in truss_rod_channel.adjuster_boundary) <= 0.0
            else ()
        )
        points = [p for line in lines for p in line]
        problem = (
            "runs off the face"
            if not all(point_in_polygon(p, face) for p in points)
            else "runs onto the nut's seat"
            if any(p.x > seat_end for p in points)
            else "runs into a tuner hole"
            if any(
                math.hypot(p.x - hole.center.x, p.y - hole.center.y)
                < hole.diameter / 2.0 + clearance
                for hole in tuner_layout.holes
                for p in points
            )
            else "runs into the truss rod adjuster's trough"
            if trough and any(point_in_polygon(p, trough) for p in points)
            else None
        )
        if problem is not None:
            raise NeckGeometryError(
                f"The headstock lettering {problem}: move it "
                "(headstock_engraving_x / _y), turn it or make it smaller."
            )
        return Engraving(lines, depth)

    def _under_carve(
        self, rear: RearCavity | None, drop: Callable[[Cavity], float]
    ) -> RearCavity | None:
        """Return ``rear`` made shallower to keep its top wall under a carve.

        It keeps ``body_rear_cavity_top_wall`` below the arched top
        wherever it lies (``drop`` gives how far the top falls over a
        route); its steps rise with it.
        """
        if rear is None:
            return None
        lowest = max(drop(part) for part in (rear.cavity, *rear.steps))
        limit = self.body_thickness - lowest - self.body_rear_cavity_top_wall
        shift = rear.cavity.depth - limit
        if shift <= 0.0:
            return rear
        return replace(
            rear,
            cavity=replace(rear.cavity, depth=rear.cavity.depth - shift),
            steps=tuple(replace(step, depth=step.depth - shift) for step in rear.steps),
        )

    def _stepped_top(
        self,
        shape: BodyShapeSpec,
        heel_end: float,
        outline: tuple[Point2D, ...],
        pocket: tuple[Point2D, ...],
        level: list[tuple[Point2D, ...]],
        contours: tuple[ContourCut, ...],
        guard: Pickguard | None,
    ) -> SteppedTop | None:
        """Return the top in levels, or ``None`` (see ``body_stepped_top``).

        The steps are the shape's drawn ``step_points``, or the outline
        taken in by ``body_top_step_insets``. ``level`` is what must sit on
        the top level: the pickups and the bridge's routes, plate and holes.

        Raises:
            BodyGeometryError: With a carved top, an arm contour or a
                pickguard, or steps that reach the pickups or the bridge.
        """
        if not self.body_stepped_top:
            return None
        if self.body_carved_top:
            raise BodyGeometryError(
                "A top is either carved or stepped: turn off body_carved_top or "
                "body_stepped_top."
            )
        if any(contour.face == "top" for contour in contours):
            raise BodyGeometryError(
                "A stepped top takes no arm contour: set body_arm_contour_depth to 0."
            )
        if guard is not None:
            raise BodyGeometryError(
                "A pickguard does not lie flat on a stepped top: turn off "
                "body_pickguard or body_stepped_top."
            )
        if shape.step_points:
            for index, polygon in enumerate(shape.step_points, start=1):
                if not all(
                    isinstance(point, (tuple, list))
                    and len(point) == 2
                    and all(
                        isinstance(v, (int, float)) and math.isfinite(v) for v in point
                    )
                    for point in polygon
                ):
                    raise BodyGeometryError(
                        f"The stepped top's step {index} has a point that is not "
                        "two numbers: redraw it, or use Auto steps."
                    )
            # Drawn: straight lines between the shape's points.
            boundaries = tuple(
                tuple(Point2D(heel_end + x, y) for x, y in polygon)
                for polygon in shape.step_points
            )
            where = "drawn"
        else:
            insets = tuple(float(inset) for inset in self.body_top_step_insets)
            if not all(math.isfinite(d) and d > 0.0 for d in insets) or any(
                inner <= outer for outer, inner in zip(insets, insets[1:], strict=False)
            ):
                raise BodyGeometryError(
                    "body_top_step_insets must be positive, the outermost first "
                    "and each further in than the last."
                )
            # The outline with the points it can do without left out
            # (within STEP_OUTLINE_TOLERANCE): the boundaries come out as
            # true and far quicker.
            edge = simplified(outline, STEP_OUTLINE_TOLERANCE)
            boundaries = tuple(
                tuple(offset_polygon(edge, inset, inward=True)) for inset in insets
            )
            where = f"{insets[-1]:g} mm in from the edge" if insets else ""
        steps = SteppedTop(boundaries, self.body_top_step_height)
        if shape.step_points:
            # Drawn lines may meet off the body, in the neck pocket or
            # within STEP_EDGE_SLACK of the edge (converging on it).
            steps.check_nested(
                lambda point: (
                    not point_in_polygon(point, outline)
                    or point_in_polygon(point, pocket)
                    or distance_to_boundary(point, outline) <= STEP_EDGE_SLACK
                )
            )
        innermost = steps.boundaries[-1]
        if any(
            not point_in_polygon(point, innermost)
            for feature in level
            for point in feature
        ):
            raise BodyGeometryError(
                f"The stepped top's innermost step ({where}) reaches the pickups "
                "or the bridge: make the last of body_top_step_insets smaller, "
                "or draw that step round them."
            )
        return steps

    def _carved_top(
        self,
        outline: tuple[Point2D, ...],
        flat: list[tuple[Point2D, ...]],
        pickups: list[tuple[Point2D, ...]],
        bridge: list[tuple[Point2D, ...]],
        contours: tuple[ContourCut, ...],
    ) -> CarvedTop | None:
        """Return the arched top, or ``None`` for a flat one.

        The plateau holds everything in ``flat`` (the neck pocket and the
        truss-rod access ``CARVE_KEEP_MARGIN`` round, the ``pickups``
        ``PICKUP_RING_REACH`` round, where their mounting rings rest, the
        ``bridge`` ``body_carve_margin`` round).

        Raises:
            BodyGeometryError: With an arm contour, which a carved top
                does not take.
        """
        if not self.body_carved_top:
            return None
        if any(contour.face == "top" for contour in contours):
            raise BodyGeometryError(
                "A carved top takes no arm contour: set body_arm_contour_depth to 0."
            )
        if not math.isfinite(self.body_carve_margin) or self.body_carve_margin < 0.0:
            raise BodyGeometryError("body_carve_margin must not be negative.")
        # The plateau, in straight lines and arcs: the neck pocket a little
        # round, each pickup its mounting ring round, the bridge the margin.
        margins = [
            (
                feature,
                PICKUP_RING_REACH
                if feature in pickups
                else self.body_carve_margin
                if feature in bridge
                else CARVE_KEEP_MARGIN,
            )
            for feature in flat
            if feature
        ]
        # The plateau keeps clear of the edge so the top has room to fall
        # (beside the neck pocket, along a cutaway); a pickup's ring and the
        # bridge stay flat however near it comes.
        keep = tuple(
            tuple(offset_polygon(pickup, PICKUP_RING_KEEP, inward=False))
            for pickup in pickups
            if pickup
        ) + tuple(tuple(feature) for feature in bridge if len(feature) >= 3)
        return CarvedTop(
            outline,
            plateau_round(margins),
            self.body_carve_depth,
            self.body_carve_rim,
            keep=keep,
            fall=CARVE_MIN_FALL,
            # Some rim is kept all round, a top binding's or roundover's
            # width and 1 mm more.
            edge_rim=max(self.body_top_binding_width, self.body_top_edge_radius) + 1.0,
        )

    def _engraving(
        self,
        outline: tuple[Point2D, ...],
        keep_out: list[tuple[Point2D, ...]],
        holes: list[tuple[Point2D, float]],
        level: Callable[[Point2D], float] | None = None,
    ) -> Engraving | None:
        """Return the top's decorative engraving, or ``None`` without one.

        The pattern (``presets.engraving``) is laid out from
        ``body_engraving_seed`` over the top ``body_engraving_margin`` in
        from the edge, clear of ``keep_out`` and ``holes``; a relief
        (camo) only where ``level``, the top's drop, is level.
        """
        if not self.body_engraving:
            return None
        area = EngravingArea(
            outline,
            self.body_engraving_margin,
            tuple(tuple(polygon) for polygon in keep_out),
            tuple(holes),
            self.body_engraving_clearance,
            level,
        )
        layout = (
            self.body_engraving_pattern,
            area,
            self.body_engraving_seed,
            self.body_engraving_spacing,
        )
        return Engraving(
            pattern_lines(*layout),
            self.body_engraving_depth,
            pattern_pockets(*layout, self.body_engraving_depth),
        )

    def _pickguard(
        self,
        shape: BodyShapeSpec,
        heel_end: float,
        outline: tuple[Point2D, ...],
        pickups: list[TracedCavity],
        bridge_areas: list[tuple[Point2D, ...]],
        controls: ControlFeatures,
        neck_pocket: tuple[Point2D, ...],
        openings: list[tuple[str, tuple[Point2D, ...]]],
        truss_rod_access: tuple[Point2D, ...] = (),
    ) -> Pickguard | None:
        """Return the pickguard, or ``None`` without one (see ``body_pickguard``).

        Controls mounted in the guard (``body_controls`` "pickguard") bring
        it with them, ``body_pickguard`` or not, and must be under it: a
        drawn guard that does not cover them — a template's, drawn for its
        own rear cavities — gives way to the automatic guard, which is made
        round them.

        Raises:
            BodyGeometryError: For a guard that does not fit the body.
        """
        in_guard = self.body_controls == "pickguard"
        # Controls mounted in the guard bring it with them.
        if not self.body_pickguard and not in_guard:
            return None
        cavities = [c for c in controls.top_cavities if c.name == "Control cavity"]

        def guard_from(points: Sequence[Point2D], automatic: bool) -> Pickguard:
            return pickguard(
                points,
                automatic=automatic,
                thickness=self.body_pickguard_thickness,
                pickup_openings=openings,
                holes=[*controls.holes, *controls.guard_holes],
                # A rear-mounted blade switch's slot, should the guard cover it.
                slots=(*controls.guard_slots, *controls.through_cavities),
                screw_clearance=SCREW_CLEARANCE,
                screw_spot_diameter=SCREW_SPOT_DIAMETER,
                screw_spot_depth=self.body_pickguard_thickness + SCREW_SPOT_DEPTH,
            )

        # Either way the truss rod's spoke wheel stays uncovered.
        if shape.pickguard_points:
            # Drawn for one bridge; stepped round whichever is fitted.
            drawn = clear_of_truss_rod(
                clear_of_bridge(
                    [Point2D(heel_end + x, y) for x, y in shape.pickguard_points],
                    bridge_areas,
                    [route.outline for route in pickups],
                ),
                truss_rod_access,
            )
            # Controls mounted in it must be under it; a guard drawn for
            # other controls (a template's) gives way to the automatic one,
            # made round them.
            if not in_guard:
                return guard_from(drawn, automatic=False)
            covering = guard_outline(drawn)
            if all(
                point_in_polygon(p, covering)
                for cavity in cavities
                for p in cavity.outline
            ):
                return guard_from(drawn, automatic=False)
        automatic = automatic_pickguard_points(
            outline,
            heel_end,
            self.body_pickguard_margin,
            bridge_areas,
            cavities[0].outline if in_guard and cavities else None,
            [route.outline for route in pickups],
            neck_pocket,
            self.bass_sign,
            PICKGUARD_STYLES[self.body_pickguard_style],
        )
        return guard_from(
            clear_of_truss_rod(automatic, truss_rod_access), automatic=True
        )

    def fretboard_surface(self) -> FretboardSurface:
        """Return the fretboard's playing surface, a bound board's narrower.

        Raises:
            NeckGeometryError: For a binding outside 0 to
                ``MAX_FRETBOARD_BINDING``.
        """
        # A bound board is cut narrower by its binding each side.
        binding = self.fretboard_binding_width
        if not math.isfinite(binding) or not 0.0 <= binding <= MAX_FRETBOARD_BINDING:
            raise NeckGeometryError(
                "fretboard_binding_width must lie between 0 and "
                f"{MAX_FRETBOARD_BINDING:g} mm."
            )
        return FretboardSurface(
            self.centre_scale,
            self.fret_count,
            self.nut_width - 2.0 * binding,
            self.final_fret_width - 2.0 * binding,
            self.fretboard_radius,
            self.fretboard_thickness,
            end_extension=self.fretboard_end_extension,
            profile_sample_count=self.profile_sample_count,
            skew=self.fret_skew,
        )

    def inlay_design(self, surface: FretboardSurface | None = None) -> InlayLayout:
        """Return the fret markers (cheap: the web app's inlay editor uses it).

        Markers listed beyond the last fret (the 24th-fret pair on a
        22-fret neck, say) are simply not cut.
        """
        return InlayLayout(
            surface or self.fretboard_surface(),
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
            bass_sign=self.bass_sign,
            # (Checked by the layout: a pair of numbers each.)
            custom_points=tuple(
                cast(tuple[float, float], tuple(point)) for point in self.inlay_points
            ),
        )

    def _check_bridge_strings(self) -> None:
        """Reject a bridge made for another number of strings.

        A bridge kind takes only the string counts it is made for
        (``BRIDGE_MIN_STRINGS`` / ``BRIDGE_MAX_STRINGS``), and a bridge
        with a string count of its own must carry the instrument's.

        Raises:
            BodyGeometryError: When the bridge does not fit the strings.
        """
        bridge = self.body_bridge
        kind, strings = bridge.kind, self.string_count
        most = BRIDGE_MAX_STRINGS.get(kind)
        least = BRIDGE_MIN_STRINGS.get(kind)
        if (most is not None and strings > most) or (
            least is not None and strings < least
        ):
            made = (
                f"{least} to {most}"
                if least is not None and most is not None and least != most
                else f"{most if most is not None else least}"
            )
            raise BodyGeometryError(
                f"The {kind} bridge is made for {made} strings; use the "
                f"hardtail or single-string bridges for {strings}."
            )
        own = getattr(bridge, "string_count", strings)
        if own != strings:
            what = {
                "hardtail": f"hardtail has {own} string holes",
                "headless": f"headless bridge has {own} strings",
                "single_string": f"single-string bridges are {own} units",
            }.get(kind, f"{kind} bridge is set for {own} strings")
            raise BodyGeometryError(
                f"The {what}, but the instrument has {strings} strings."
            )

    def _bridge_pickup_clearance_offset(
        self,
        bridge: BridgeHardware,
        kind: PickupType,
        angle: float,
        bass_sign: float,
    ) -> float:
        """Return the least bridge pickup offset that clears the bridge.

        The offset is the route centre's distance ahead of the scale line.
        The route keeps ``body_bridge_pickup_clearance`` of wood ahead of
        everything the bridge cuts into or sets on the top — its routes, its
        plate (``footprint``) and the edges of its holes (a hardtail's
        baseplate screws, a Tune-o-matic's posts) — and never reaches past
        the saddle line, where the strings
        leave the saddles (fanned on a multiscale).

        Args:
            bridge: The bridge's features, placed (and turned) on the body.
            kind: The bridge pickup's type.
            angle: The bridge pickup's slant in degrees.
            bass_sign: +1 when the bass side is +Y, -1 when it is -Y.

        Returns:
            The least offset in mm, or ``-inf`` without a bridge pickup.
        """
        # The route centred on the scale line's X = 0, so its points
        # measure how far it reaches toward the tail.
        route = pickup_route(
            kind,
            "Bridge pickup route",
            0.0,
            self.body_pickup_route_depth,
            bass_sign,
            angle,
            string_count=self.string_count,
        )
        if route is None:
            return -math.inf
        # Measured from the scale line, as the pickup is placed; a tilted
        # neck's bridge, moved off it, is measured where it stands.
        scale = self.centre_scale
        clearance = self.body_bridge_pickup_clearance
        # A route keeps its wood from the bridge's nearest route edge
        # wherever it is, as across the whole width.
        reach = max(point.x for point in route.outline)
        needed = [
            scale - cavity.min_x + reach + clearance
            for cavity in (*bridge.top_cavities, *bridge.through_cavities)
        ]
        # A plate on the top (a Kahler's, a headless unit's) is kept
        # clear of as its routes are.
        if bridge.footprint:
            front = min(point.x for point in bridge.footprint)
            needed.append(scale - front + reach + clearance)
        # A hole only meets the part of the route across from it: a
        # hardtail's screws, or a Tune-o-matic's posts turned with a fan,
        # are measured against the route between their own Ys.
        for hole in bridge.holes:
            keep_out = hole.diameter / 2.0 + clearance
            across = _reach_between(
                route.outline, hole.center_y - keep_out, hole.center_y + keep_out
            )
            needed.append(scale - (hole.center_x - keep_out) + across)
        # The saddle line leans with a fan (the strings' own bridge ends; a
        # slant alone leaves the bridge square), so each route point is
        # measured against the line at its own Y.
        lean = self.fret_skew.fan_only().at(scale)
        needed.append(max(point.x - lean * point.y for point in route.outline))
        return max(needed)

    def _jack(
        self,
        outline: tuple[Point2D, ...],
        aim: Point2D,
        direction_degrees: float,
        controls: ControlFeatures,
    ) -> tuple[JackHole | None, TracedCavity | None]:
        """Return the output jack's bore and a Strat style jack's cavity.

        Neither with the jack on the control plate (``body_jack`` "plate").

        The bore's line runs through ``aim`` along the shape's direction; it
        starts where that line enters the body (the crossing of the outline
        nearest ``aim``), so it sits on the edge of whatever body is drawn,
        and runs on into the control cavity (see ``body_jack``).

        Raises:
            BodyGeometryError: For an unknown ``body_jack``.
        """
        if self.body_jack not in ("side", "cup", "strat", "plate"):
            raise BodyGeometryError(
                f"Unknown jack {self.body_jack!r}: choose side, cup, strat or plate."
            )
        if self.body_jack == "plate":
            return None, None
        radians = math.radians(direction_degrees)
        ux, uy = math.cos(radians), math.sin(radians)

        def along(origin: Point2D, distance: float) -> Point2D:
            return Point2D(origin.x + ux * distance, origin.y + uy * distance)

        entries = [
            t
            for t in _line_crossings(aim, ux, uy, outline)
            if point_in_polygon(along(aim, t + 0.5), outline)
            and not point_in_polygon(along(aim, t - 0.5), outline)
        ]
        start = along(aim, min(entries, key=abs)) if entries else aim
        cavity: TracedCavity | None = None
        if self.body_jack == "strat":
            radius = JACK_STRAT_DIAMETER / 2.0
            centre = along(start, radius + JACK_STRAT_WALL)
            cavity = TracedCavity(
                "Jack cavity",
                tuple(
                    Point2D(
                        centre.x + radius * math.cos(2.0 * math.pi * k / 32),
                        centre.y + radius * math.sin(2.0 * math.pi * k / 32),
                    )
                    for k in range(32)
                ),
                JACK_STRAT_DEPTH,
            )
            start = centre
        depth = self.body_jack_depth
        if depth is None:
            depth = JACK_DEFAULT_DEPTH
            # The rear control cavity, or a Tele plate's cavity in the top.
            target = controls.control_cavity
            targets = (
                [target.cavity.outline]
                if target is not None
                else [
                    top.outline
                    for top in controls.top_cavities
                    if top.name == "Control cavity"
                ]
            )
            hits = [
                t
                for polygon in targets
                for t in _line_crossings(start, ux, uy, polygon)
                if t > 0.0
            ]
            if hits:
                depth = min(hits) + JACK_CAVITY_OVERRUN
        cup = self.body_jack == "cup"
        if cup:
            depth = max(depth, JACK_CUP_DEPTH + 5.0)
        return (
            JackHole(
                start.x,
                start.y,
                direction_degrees,
                diameter=self.body_jack_diameter,
                depth=depth,
                cup_diameter=JACK_CUP_DIAMETER if cup else 0.0,
                cup_depth=JACK_CUP_DEPTH if cup else 0.0,
            ),
            cavity,
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

        A generated rear cavity (``GENERATED_REAR_LAYOUTS``) sits where the
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

        def build(dx: float, dy: float, turn: float = 0.0) -> ControlFeatures:
            moved = shape
            if dx or dy or turn:
                moved = replace(
                    shape,
                    pot_offsets=tuple((x + dx, y + side * dy) for x, y in pots),
                    control_angle_degrees=shape.control_angle_degrees + turn,
                )
            return control_features(
                self.body_controls,
                moved,
                heel_end,
                thickness=self.body_thickness,
                top_wall=self.body_rear_cavity_top_wall,
                cover_depth=self.body_cover_recess_depth,
                pot_hole_diameter=self.body_pot_shaft_hole_diameter,
                switch_hole_diameter=self.switch_shaft_hole_diameter,
                # One pickup needs no selector beside a single volume pot.
                switch=sum(kind != "none" for kind in self.pickup_types()) > 1,
                plate_jack=self.body_jack == "plate",
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
        if self.body_controls == "pickguard":
            return self._guard_controls_placed(build, outline, top_cavities)
        if self.body_controls not in GENERATED_REAR_LAYOUTS or clear(controls):
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

    def _guard_controls_placed(
        self,
        build: Callable[[float, float, float], ControlFeatures],
        outline: tuple[Point2D, ...],
        top_cavities: tuple[Cavity, ...],
    ) -> ControlFeatures:
        """Return pickguard-mounted controls moved where a guard covers them.

        Their cavity, routed from the top, must lie
        ``body_pickguard_margin`` + ``PICKGUARD_CONTROL_LAP`` in from the
        edge, so the guard (that far in) covers it with a lap, and
        ``PICKGUARD_CONTROL_GAP`` clear of the neck pocket, the pickups and
        the bridge's routes. Where the shape's pots put it does not do, the
        controls move to the nearest place that does, along the neck and
        across it by up to ``PICKGUARD_CONTROL_SHIFT`` in 4 mm steps —
        turned by ``PICKGUARD_CONTROL_TURNS`` too where they do not fit
        square (along a Jackson RR's wing); if nothing does, they stay put
        and the body's own check reports it.
        """
        room = self.body_pickguard_margin + PICKGUARD_CONTROL_LAP
        gap = PICKGUARD_CONTROL_GAP
        # Each route's box, the gap wider all round (quick, and on the
        # safe side).
        routes = []
        for top in top_cavities:
            xs = [p.x for p in top.outline]
            ys = [p.y for p in top.outline]
            routes.append(
                (
                    Point2D(min(xs) - gap, min(ys) - gap),
                    Point2D(max(xs) + gap, min(ys) - gap),
                    Point2D(max(xs) + gap, max(ys) + gap),
                    Point2D(min(xs) - gap, max(ys) + gap),
                )
            )

        def fits(controls: ControlFeatures) -> bool:
            cavity = next(
                c for c in controls.top_cavities if c.name == "Control cavity"
            )
            points = cavity.outline
            cx = sum(p.x for p in points) / len(points)
            cy = sum(p.y for p in points) / len(points)
            # The ends first: they are the likeliest to stick out.
            ordered = sorted(points, key=lambda p: -math.hypot(p.x - cx, p.y - cy))
            return not any(outlines_overlap(points, r) for r in routes) and all(
                point_in_polygon(p, outline)
                and distance_to_boundary(p, outline) >= room
                for p in ordered
            )

        controls = build(0.0, 0.0, 0.0)
        if fits(controls):
            return controls
        reach = int(PICKGUARD_CONTROL_SHIFT)
        shifts = sorted(
            (
                (float(dx), float(dy))
                for dx in range(-reach, reach + 1, 4)
                for dy in range(-reach, reach + 1, 4)
                if math.hypot(dx, dy) <= reach
            ),
            key=lambda shift: math.hypot(*shift),
        )
        for turn in PICKGUARD_CONTROL_TURNS:
            for dx, dy in shifts:
                moved = build(dx, dy, turn)
                if fits(moved):
                    return moved
        return controls

    def _contours(
        self,
        shape: BodyShapeSpec,
        outline: tuple[Point2D, ...],
        heel_end: float,
        bass_sign: float,
    ) -> tuple[ContourCut, ...]:
        """Return the arm contour and belly cut that are switched on.

        Both sit on the bass side: the arm contour over the rear bout
        (from 120 mm behind the heel end), the belly cut over the upper
        bout (40 mm ahead of it to 120 mm behind). Each is deepest at the
        outline point furthest out on that side, or the one nearest
        ``body_*_position`` behind the heel end. The shape's
        ``arm_contour_points`` / ``belly_cut_points``, when drawn, are where
        the arm contour / belly cut starts instead (``ContourCut.along_line``).
        """
        contours: list[ContourCut] = []
        for name, face, depth, points in (
            (
                "Arm contour",
                "top",
                self.body_arm_contour_depth,
                shape.arm_contour_points,
            ),
            ("Belly cut", "back", self.body_belly_cut_depth, shape.belly_cut_points),
        ):
            if depth <= 0.0 or not points:
                continue
            line = open_catmull_rom(
                [Point2D(heel_end + x, y) for x, y in points], CONTOUR_LINE_SAMPLES
            )
            contours.append(
                ContourCut.along_line(name, face, outline, line, depth)  # type: ignore[arg-type]
            )
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
            if depth <= 0.0 or any(c.name == name for c in contours):
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
        self._check_bridge_strings()
        if self.neck_joint not in ("bolt_on", "set", "neck_through", "one_piece"):
            raise NeckGeometryError(
                'neck_joint must be "bolt_on", "set", "neck_through" or "one_piece".'
            )
        through = self.neck_runs_through
        if through and self.headless:
            raise NeckGeometryError(
                "A neck-through or one-piece neck needs a headstock: the "
                "headless neck is bolt-on only for now."
            )
        if (
            (through or self.neck_joint == "set")
            and self.truss_rod_adjustment == "heel"
            and not self.truss_rod_spoke_wheel_fitted
        ):
            raise NeckGeometryError(
                "A set, neck-through or one-piece neck buries a heel adjuster "
                "in the body (the neck never comes off): adjust the truss rod "
                "at the headstock, or fit a spoke wheel (truss_rod_spoke_wheel)."
            )
        if not through and (
            not math.isfinite(self.heel_mounting_length)
            or self.heel_mounting_length < 40.0
        ):
            raise NeckGeometryError(
                "Heel mounting length must be at least 40 mm for a secure neck joint."
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
        if self.headless and (
            not math.isfinite(self.headless_length)
            or not MIN_HEADLESS_LENGTH <= self.headless_length <= 80.0
        ):
            raise NeckGeometryError(
                f"headless_length must lie between {MIN_HEADLESS_LENGTH:g} and 80 mm."
            )
        head_length = self.headless_length if self.headless else self.headstock_length
        if (
            not math.isfinite(self.headstock_root_length)
            or not 5.0 <= self.headstock_root_length < head_length
        ):
            raise NeckGeometryError(
                "Headstock root length must be at least 5 mm and shorter "
                "than the headstock (or a headless neck's headpiece)."
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
        if not self.headless and (
            sum(HEADSTOCK_STYLES[self.headstock_style]) != self.string_count
        ):
            raise NeckGeometryError(
                f"Headstock style {self.headstock_style} holds "
                f"{sum(HEADSTOCK_STYLES[self.headstock_style])} tuners, but the "
                f"instrument has {self.string_count} strings."
            )
        bass_count, treble_count = HEADSTOCK_STYLES[self.headstock_style]
        if (
            not self.headless
            and bass_count == treble_count
            and len(self.tuner_station_distances) != bass_count
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
        if self.handedness not in ("right", "left"):
            raise NeckGeometryError('handedness must be "right" or "left".')
        string_values = (
            self.tuner_post_diameter,
            self.nut_string_spacing,
            self.bridge_string_spacing,
        )
        if not all(math.isfinite(value) and value > 0.0 for value in string_values):
            raise NeckGeometryError(
                "Tuner post diameter and string spacings must be positive."
            )
        if (
            not self.headless
            and self.tuner_inline_first_distance < self.headstock_root_length
        ):
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
        first_fret_wood_thickness = (
            self.first_fret_thickness_needed() - self.fretboard_thickness
        )
        twelfth_fret_wood_thickness = (
            self.twelfth_fret_thickness - self.fretboard_thickness
        )
        # The body first: a neck-through neck's back falls to the body's
        # thickness where the body begins.
        headstock_plan, tuner_layout = self.headstock_design()
        body_parts = self._body_layout(outline)
        through_parts = self.neck_through_parts(outline, headstock_plan, body_parts)
        heel_depth = self.heel_thickness
        heel_transition = self.heel_root_length
        if through_parts is not None:
            heel_depth = self.body_thickness
            ramp = self.neck_through_heel_ramp
            if not math.isfinite(ramp) or ramp <= 0.0:
                raise NeckGeometryError("neck_through_heel_ramp must be positive.")
            heel_transition = ramp
            heel_flat_start_offset = max(
                1.0, outline.last_fret_position - through_parts.front_x
            )
        neck_surface = NeckBackSurface(
            outline,
            first_fret_wood_thickness,
            twelfth_fret_wood_thickness,
            heel_depth,
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
            heel_transition_length=heel_transition,
            heel_flat_start_offset=heel_flat_start_offset,
            heel_scoop_depth=self.heel_scoop_depth,
            heel_root_center_extension=self.heel_root_center_extension,
            preserve_d_profile_at_heel=False,
            exponent=self.neck_profile_exponent,
            profile_sample_count=self.profile_sample_count,
            segments_per_region=self.segments_per_region,
        )
        fretboard_surface = self.fretboard_surface()
        board_nut_width = fretboard_surface.nut_width
        board_final_width = fretboard_surface.last_fret_width
        final_fret_fraction = 1.0 - 2.0 ** (-self.fret_count / 12.0)
        width_at_scale_end = (
            board_nut_width
            + (board_final_width - board_nut_width) / final_fret_fraction
        )
        locking_nut = self.locking_nut_placed()
        fretboard = Fretboard(
            self.centre_scale,
            board_nut_width,
            width_at_scale_end,
            Centerline(self.centre_scale),
            # A fretboard running on under a locking nut has no nut-end
            # corners to round.
            nut_corner_radius=(
                0.0
                if locking_nut is not None and locking_nut.on_fretboard
                else self.fretboard_nut_corner_radius
            ),
            skew=self.fret_skew,
        )
        fret_layout = FretLayout(
            fretboard,
            self.fret_count,
            self.fret_skew,
            zero_fret=locking_nut is not None and locking_nut.zero_fret,
        )
        inlay_layout = self.inlay_design(fretboard_surface)
        truss_rod_channel = self.truss_rod(outline)
        carbon_rods = self.carbon_rods(outline, neck_surface, truss_rod_channel)
        headstock = self.headstock_solid(headstock_plan)
        if body_parts.pickguard is not None:
            check_on_body(body_parts.pickguard, body_parts.outline.points)
        body = BodySolid(
            body_parts.outline,
            self.body_thickness,
            # A neck-through body has no pocket: the neck runs on through.
            None if through_parts is not None else body_parts.neck_pocket,
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
            engraving=body_parts.engraving,
            carved_top=body_parts.carved_top,
            stepped_top=body_parts.stepped_top,
            wire_channels=body_parts.wiring.channels,
            wire_holes=body_parts.wiring.holes,
            wire_notes=body_parts.wiring.by_hand,
            bridge_notes=body_parts.bridge_notes,
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
            locking_nut,
            self.fretboard_binding_width,
            self.headstock_lettering(headstock, tuner_layout, truss_rod_channel),
            (self.neck_angle_degrees, *self.neck_pivot()),
            through_parts,
            carbon_rods,
            self.neck_joint == "set",
        )


def _opened_into_controls(
    controls: ControlFeatures, thickness: float
) -> ControlFeatures:
    """Return ``controls``, each through route reaching into its cavity.

    A route (a blade switch's slot) reaches 1 mm into the deepest pocket
    of the control cavity under it — after the cavity rose under a carved
    top, too.
    """
    rear = controls.control_cavity
    if rear is None or not controls.through_cavities:
        return controls

    def opened(route: Cavity) -> Cavity:
        under = [
            pocket.depth
            for pocket in rear.pockets
            if outlines_overlap(pocket.outline, route.outline)
        ]
        if not under:
            return route
        return replace(route, depth=thickness - max(under) + 1.0)

    return replace(
        controls,
        through_cavities=tuple(opened(route) for route in controls.through_cavities),
    )


_BASS_OVERRIDES: dict[str, Any] = {
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
    # A bass's string ferrules, 3/8 in.
    "body_string_ferrule_diameter": 9.5,
    "body_string_ferrule_depth": 6.5,
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
    # The bass's long neck pocket takes its bolts further apart: the
    # pair at the pocket's mouth moves out near the body's edge, and
    # the rear pair 2 mm in from the pocket's end, so its ferrules lie
    # wholly over the pocket.
    "body_neck_bolt_spacing_x": 56.0,
    "body_neck_bolt_end_wall": 5.0,
}
"""The four-string bass's values (see ``INSTRUMENT_OVERRIDES``)."""

_HEADLESS_OVERRIDES: dict[str, Any] = {
    "headless": True,
    # A flat headpiece level with the glue face, the string anchor on it.
    "headstock_angle": 0.0,
    "headstock_face_drop": 0.0,
    "headstock_root_length": 15.0,
    "headstock_outline": "fitted",
}
"""What a headless guitar or bass changes (see ``headless``)."""

TELECASTER_NECK: dict[str, Any] = {
    "nut_style": "slot",
    "locking_nut": "none",
    "headstock_angle": 0.0,
    "headstock_style": "6_inline",
    "headstock_outline": "drawn",
    # A Telecaster outline round the default six-in-line row: the tuner
    # edge straight along the posts, flaring out from the nut; the other
    # edge nearly straight, sweeping out to the rounded treble point; the
    # end wrapping round the last tuner.
    "headstock_bass_edge": (
        (12.0, 26.0),
        (26.0, 35.0),
        (40.0, 39.5),
        (80.0, 29.4),
        (120.0, 19.4),
        (160.0, 9.3),
        (183.0, 2.8),
        (196.0, -5.0),
        (204.0, -20.0),
    ),
    "headstock_treble_edge": (
        (15.0, 23.0),
        (70.0, 24.5),
        (120.0, 26.5),
        (160.0, 30.0),
        (186.0, 36.0),
        (204.0, 39.0),
    ),
    "headstock_tip_points": ((3.5, 27.0), (4.5, 33.0)),
    "truss_rod_adjustment": "heel",
}
"""A Telecaster neck (see ``NECK_TEMPLATES``): a slotted nut, a flat
six-in-line headstock drawn as a Telecaster's, adjusted at the heel."""

NECK_TEMPLATES: dict[str, tuple[str, dict[str, Any]]] = {
    "telecaster": ("Telecaster neck", TELECASTER_NECK),
}
"""Neck and headstock starting points the headstock editor can load: each
a label and the values it sets (for a six-string guitar; the truss rod can
still be moved to the headstock afterwards)."""

BODY_TEMPLATE_VALUES: dict[str, dict[str, Any]] = {
    "alexi_hexed": {
        "body_pickups": "H",
        "body_controls": "volume_1",
        "body_bridge": FloydRoseSpec(),
        "body_stepped_top": True,
        "body_top_step_insets": (12.0, 40.0),
        "body_top_step_height": 1.5,
    },
}
"""Parameter values a body template (``YOUR_DESIGN_TEMPLATES``) sets
besides its shape when the body editor loads it: the ESP LTD Alexi Hexed
style one its look — a single bridge humbucker (an EMG HZ on the
original) under one volume pot (no selector), a Floyd Rose, and its
graphic as a stepped top (``body_stepped_top``, its two steps drawn in the
template's ``step_points``): the arrow round the pickup and the bridge at
full height, the band round it 1.5 mm lower, the rest out to the edge and
the wing tips 3 mm lower, where the original's pinstripes run. Its purple
fade and pinstripes (on the back and sides too) are the painter's; it is
neck-through (``neck_joint``) with sawtooth inlays (``inlay_style``
"sharktooth"), which the template leaves to choose."""

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
    "bass_guitar": _BASS_OVERRIDES,
    "five_string_bass": {
        **_BASS_OVERRIDES,
        # A Fender Jazz V-like five-string: a 47 mm nut, 18 mm at the
        # bridge (72 mm over the outer strings), a 77 mm heel, tuners 4+1.
        "string_count": 5,
        "nut_width": 47.0,
        "nut_string_spacing": 9.5,
        "bridge_string_spacing": 18.0,
        "final_fret_width": 77.0,
        "heel_width": 77.0,
        "headstock_style": "4+1",
        "headstock_length": 210.0,
        "body_bridge": HardtailSpec(
            string_count=5,
            string_spacing=18.0,
            string_hole_offset=30.0,
            screw_count=5,
            screw_spacing=18.0,
            screw_offset=-12.0,
        ),
    },
    "headless_guitar": {
        **_HEADLESS_OVERRIDES,
        "body_bridge": HeadlessBridgeSpec(),
        # The headless unit's plate reaches 12 mm ahead of the saddles:
        # the bridge humbucker moves up to leave 6 mm before it.
        "body_bridge_pickup_offset": 38.0,
    },
    "headless_bass": {
        **_BASS_OVERRIDES,
        **_HEADLESS_OVERRIDES,
        "body_bridge": HeadlessBridgeSpec(string_count=4, string_spacing=19.0),
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

The five-string bass takes the four-string's values with a 47 mm nut
(9.5 mm string spacing), 18 mm at the bridge, a 77 mm heel, a 4+1
headstock (a Fender Jazz V's) and a five-string hardtail; its Jazz Bass
pickup is the 4-1/8 in five-string route (see ``pickups.pickup_stretch``).

The bass values are labelled starting points for a common four-string
bass: 34-inch (863.6 mm) scale, 21 frets, a 38 mm nut and 62 mm heel, a
12-inch fretboard radius, 10 mm string spacing at the nut and 19 mm at
the bridge, Fender-style tuners in line (19 mm holes, 38 mm apart), a
Precision Bass pickup 150 mm and a Jazz Bass pickup 45 mm ahead of the
bridge, a string-through four-string hardtail, and neck bolts 56 mm
apart along the neck, the outer pair near the body's edge and the
rear pair's ferrules wholly over the neck pocket.
"""


def _rectangle_gap(front: float, back: float, half: float, hole: TunerHole) -> float:
    """Return the wood between a plan rectangle and a tuner hole's edge.

    The rectangle runs from ``front`` to ``back`` along the neck (either
    order) and ``half`` either side of the centerline.
    """
    low, high = min(front, back), max(front, back)
    dx = max(low - hole.center.x, 0.0, hole.center.x - high)
    dy = max(abs(hole.center.y) - half, 0.0)
    return math.hypot(dx, dy) - hole.diameter / 2.0


def _reach_between(outline: tuple[Point2D, ...], low: float, high: float) -> float:
    """Return the outline's largest X between two Ys, or ``-inf`` if none.

    Each edge is clipped to the band ``low <= y <= high``, so a long
    straight edge counts even where it has no vertex inside the band.
    """
    reach = -math.inf
    for start, end in zip(outline, (*outline[1:], outline[0]), strict=True):
        if max(start.y, end.y) < low or min(start.y, end.y) > high:
            continue
        if start.y == end.y:
            reach = max(reach, start.x, end.x)
            continue
        for y in (
            max(low, min(start.y, end.y)),
            min(high, max(start.y, end.y)),
        ):
            t = (y - start.y) / (end.y - start.y)
            reach = max(reach, start.x + t * (end.x - start.x))
    return reach


def _circle_points(centre: Point2D, radius: float) -> tuple[Point2D, ...]:
    """Return a round hole's outline, 16 points."""
    return tuple(
        Point2D(
            centre.x + radius * math.cos(math.pi * k / 8.0),
            centre.y + radius * math.sin(math.pi * k / 8.0),
        )
        for k in range(16)
    )


def _jack_space(jack: JackHole, thickness: float) -> WireSpace:
    """Return the jack's bore (and counterbore) as the wiring keeps clear of it.

    It runs level through the middle of the body's thickness.
    """
    radians = math.radians(jack.direction_degrees)
    ux, uy = math.cos(radians), math.sin(radians)

    def bar(length: float, width: float) -> tuple[Point2D, ...]:
        half = width / 2.0
        return tuple(
            Point2D(
                jack.start_x + ux * along - uy * across,
                jack.start_y + uy * along + ux * across,
            )
            for along, across in (
                (0.0, -half),
                (length, -half),
                (length, half),
                (0.0, half),
            )
        )

    widest = max(jack.diameter, jack.cup_diameter)
    return WireSpace(
        "Jack bore",
        bar(jack.depth, jack.diameter),
        thickness / 2.0 - widest / 2.0,
        thickness / 2.0 + widest / 2.0,
        parts=((bar(jack.cup_depth, jack.cup_diameter),) if jack.cup_diameter else ()),
    )


def _line_crossings(
    origin: Point2D, ux: float, uy: float, polygon: tuple[Point2D, ...]
) -> list[float]:
    """Return where the line ``origin + t (ux, uy)`` crosses ``polygon``'s sides."""
    crossings = []
    for a, b in zip(polygon, (*polygon[1:], polygon[0]), strict=True):
        ex, ey = b.x - a.x, b.y - a.y
        determinant = ex * uy - ux * ey
        if abs(determinant) < 1e-12:
            continue
        dx, dy = a.x - origin.x, a.y - origin.y
        t = (ex * dy - ey * dx) / determinant
        s = (ux * dy - uy * dx) / determinant
        if 0.0 <= s <= 1.0:
            crossings.append(t)
    return crossings


def distance_to_headstock_edge(plan: HeadstockPlan, point: Point2D) -> float:
    """Return how far ``point`` sits from the headstock's edges and tip.

    Measured as the fitted outline is laid out: across the neck to each
    side's edge at the point's own distance from the nut, and along the
    neck to the tip (straight to a shaped tip's outline); the smallest
    of the three. The nut is not an edge.
    """
    distance = -point.x
    return min(
        plan.edge_y(distance, 1.0) - point.y,
        point.y - plan.edge_y(distance, -1.0),
        plan.tip_clearance(point),
    )


def _back_z(rows: tuple[tuple[Point3D, ...], ...], x: float, y: float) -> float:
    """Return the neck back's height at ``(x, y)`` from its mesh rows.

    Linear between the two rows either side of ``x`` and across each row;
    0 (the glue face) beyond a row's sides.
    """

    def across(row: tuple[Point3D, ...]) -> float:
        for a, b in zip(row, row[1:], strict=False):
            if a.y <= y <= b.y:
                t = 0.0 if b.y == a.y else (y - a.y) / (b.y - a.y)
                return a.z + (b.z - a.z) * t
        return 0.0

    stations = [row[0].x for row in rows]
    if x <= stations[0]:
        return across(rows[0])
    for index in range(1, len(rows)):
        if x <= stations[index]:
            x0, x1 = stations[index - 1], stations[index]
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return (
                across(rows[index - 1])
                + (across(rows[index]) - across(rows[index - 1])) * t
            )
    return across(rows[-1])
