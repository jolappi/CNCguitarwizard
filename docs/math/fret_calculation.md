# Fret Calculation

## Formula

Remaining scale:

L_remaining = L / 2^(n/N)

Distance from nut:

L_distance = L - L_remaining

Where:

L = Scale length

n = Fret number

N = Frets per octave: 12 for semitones, as below; more for a microtonal
neck (`frets_per_octave`: 24 quarter tones, 19, 22, 31...). Fret N is
always the octave, at half the scale.

| Fret | Distance (609.6 mm scale) |
| ---: | ------------------------: |
|    1 |                 34.214 mm |
|    2 |                 66.507 mm |
|    3 |                 96.987 mm |
|  ... |                       ... |
|   12 |                304.800 mm |

With 24 frets per octave (quarter tones) every other fret is a semitone's:
fret 2 is at 34.214 mm, fret 24 at 304.800 mm.

## Markers on a microtonal neck

The marker frets (`inlay_single_marker_frets`, `inlay_double_marker_frets`)
are counted in semitones, each on the fret nearest that pitch
(`FretCalculator.nearest_fret`: `floor(s × N / 12 + 0.5)`): with 24 per
octave the 3rd fret's marker is on the 6th, the 12th's on the 24th; with
19, the 3rd's on the 5th and the 7th's on the 11th.
