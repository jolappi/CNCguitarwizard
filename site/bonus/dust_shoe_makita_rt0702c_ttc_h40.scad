// Dust shoe: Makita RT0702C on a TwoTrees TTC-H40
// The back wall (-Y) is straight and is turned toward the CNC's frame.
// Three parts: the collar (clamp + hose port), the housing and the sliding brush sleeve.
// Each prints without supports in the position it is exported in.

part = "assembly"; // [assembly, collar, housing, sleeve]
sleeve_raised = false; // the assembly view: the sleeve in its upper or lower position

/* [Router] */
router_d     = 65;    // the Makita's body diameter where it is clamped
router_clear = 0.4;
clamp_h      = 25;    // the clamp ring's height
clamp_wall   = 6;
clamp_gap    = 3;
bolt_d       = 4.5;   // M4

/* [Extraction hose] */
hose_d   = 60;
// "inside" = the port goes inside the hose (the hose's INSIDE diameter = hose_d)
// "over"   = the hose goes inside the port (the hose's OUTSIDE diameter = hose_d)
hose_fit = "inside"; // [inside, over]
hose_wall = 4;       // the hose's wall (the sleeve's clearance past the hose)
port_len  = 40;
port_wall = 2.5;

/* [Room on the frame's side] */
frame_gap    = 16;  // from the router body's surface to the CNC's frame (mm)
frame_margin = 2;   // the gap left to the frame

/* [Housing] */
hood_r      = 55;
port_offset = 82;
port_angle  = 90;   // the hose's direction: 90 = forward (X travel free), 0 = to the side
hood_h      = 35;   // set so the housing's bottom is about level with the collet nut
wall        = 3;
plate_t     = 4;
flange_t    = 4;

/* [Brush sleeve] */
travel      = 50;   // how far it slides
sleeve_wall = 3.5;
sleeve_clear= 0.5;
brush_w     = 3.2;  // the brush strip's back (its U channel) thickness + 0.2 mm
hook        = 0.4;  // the hook's inset per side at the groove's mouth
hook_h      = 1.6;  // the hook's height (its chamfer included)
brush_depth = 8;   // the brush strip's back height (the hook snaps in under its lower edge)
pin_h       = 16;   // the pin screws' height from the housing's bottom
pin_d       = 3.3;  // the pilot hole for an M4 screw
slot_w      = 4.6;

$fn = 96;

// ---- derived sizes ----
port_od = hose_fit == "inside" ? hose_d - 0.3 : hose_d + 0.5 + 2*port_wall;
port_id = port_od - 2*port_wall;
hose_od = hose_fit == "inside" ? hose_d + 2*hose_wall : port_od;
port_r  = max(port_od/2 + wall, hose_od/2 + 1.5);
R_in    = router_d/2 + router_clear;
R_cl    = R_in + clamp_wall;
s0      = pin_h;                         // the slots' lower end in the sleeve
sleeve_h= s0 + travel + slot_w/2 + 6;

function dir(a) = [cos(a), sin(a)];
port_c = port_offset * dir(port_angle);
// the pins: at the hose's end and the sides, never toward the frame (-Y)
pins = concat([[ (port_offset + port_r) * dir(port_angle), port_angle ]],
    [ for (a = [port_angle+90, port_angle+180, port_angle+270])
        let(b = (a % 360 + 360) % 360) if (abs(b - 270) > 30) [ hood_r * dir(b), b ] ]);
bolts = port_angle == 90 ? [ [32, 45], [-32, 45], [40, -25], [-40, -25] ]
                         : [ [45, 32], [45, -30], [-20, 42], [-30, -30] ];
lip_out  = sleeve_clear + brush_w + 3;           // the sleeve's lip width past the housing's outside
back_lim = router_d/2 + frame_gap - frame_margin - lip_out; // the housing's back edge (-Y = the frame)
echo(str("The housing's back edge ", back_lim, " mm, the sleeve's back edge ", back_lim+lip_out, " mm from the router's centre"));
assert(back_lim > R_in + clamp_wall, "The clamp ring does not fit on the frame's side");

module footprint() intersection() {
    hull() { circle(hood_r); translate(port_c) circle(port_r); }
    translate([-300, -back_lim]) square(600);   // a straight back wall on the frame's side
}

// ---------- COLLAR ----------
module collar() translate([0,0,hood_h]) difference() {
    union() {
        linear_extrude(flange_t) footprint();
        cylinder(r=R_cl, h=flange_t+clamp_h);
        for (s=[1,-1]) translate([-(R_cl+13), s>0 ? clamp_gap/2 : -clamp_gap/2-10, 0])
            cube([15, 10, flange_t+clamp_h]);
        translate([port_c[0],port_c[1],0]) cylinder(d=port_od, h=flange_t+port_len);
    }
    translate([0,0,-1]) cylinder(r=R_in, h=100);
    translate([port_c[0],port_c[1],-1]) cylinder(d=port_id, h=100);
    translate([-100, -clamp_gap/2, -1]) cube([100 - R_in + 1, clamp_gap, 100]);
    translate([-(R_cl+6), 0, flange_t+clamp_h/2]) rotate([90,0,0]) {
        cylinder(d=bolt_d, h=40, center=true);
        translate([0,0,clamp_gap/2+10-3.5]) cylinder(d=8.1, h=10, $fn=6);
    }
    for (b=bolts) translate([b[0],b[1],-1]) cylinder(d=bolt_d, h=flange_t+2);
}

// ---------- HOUSING ----------
module housing() difference() {
    union() {
        difference() {
            linear_extrude(hood_h) footprint();
            translate([0,0,-1]) linear_extrude(hood_h-plate_t+1) offset(r=-wall) footprint();
        }
        // bosses for the pin screws
        for (q=pins) translate(q[0]) rotate([0,0,q[1]]) translate([-wall-2,0,pin_h])
            rotate([0,90,0]) cylinder(d=10, h=wall+2);
    }
    translate([0,0,-1]) cylinder(r=router_d/2+1.5, h=hood_h+2);
    translate([port_c[0],port_c[1],-1]) cylinder(d=port_id, h=hood_h+2);
    for (q=pins) translate(q[0]) rotate([0,0,q[1]]) translate([0,0,pin_h])
        rotate([0,90,0]) cylinder(d=pin_d, h=30, center=true);
    for (b=bolts) translate([b[0],b[1],-1]) cylinder(d=bolt_d, h=hood_h+2);
}

module groove2d(g0, ins) difference() {
    offset(r=g0 + brush_w - ins) footprint();
    offset(r=g0 + ins) footprint();
}

// ---------- SLEEVE (in its lowest position) ----------
module sleeve() translate([0,0,-travel]) difference() {
    union() {
        linear_extrude(sleeve_h) offset(r=sleeve_clear+sleeve_wall) footprint();
        linear_extrude(hook_h+brush_depth+3) offset(r=lip_out) footprint();
    }
    translate([0,0,-1]) linear_extrude(sleeve_h+2) offset(r=sleeve_clear) footprint();
    // the brush groove: a chamfer at its mouth + a sharp hook, the full width above
    g0 = sleeve_clear + 1.5;
    translate([0,0,-1]) linear_extrude(1 + hook_h/2) groove2d(g0, hook/2);   // the chamfer
    translate([0,0,hook_h/2-0.01]) linear_extrude(hook_h/2+0.02) groove2d(g0, hook); // the hook
    translate([0,0,hook_h]) linear_extrude(brush_depth) groove2d(g0, 0);       // the strip's back
    // upright slots for the pin screws
    for (q=pins) translate(q[0]) rotate([0,0,q[1]]) hull()
        for (z=[s0, s0+travel]) translate([0,0,z])
            rotate([0,90,0]) cylinder(d=slot_w, h=30, center=true);
}

// ---------- the choice ----------
if (part == "assembly") {
    color("orange") collar();
    color("steelblue") housing();
    color("gray") translate([0,0, sleeve_raised ? travel : 0]) sleeve();
} else if (part == "collar") translate([0,0,-hood_h]) collar();
else if (part == "housing") rotate([180,0,0]) translate([0,0,-hood_h]) housing();
else if (part == "sleeve") translate([0,0,travel]) sleeve();
