# Topology reasoning — mzi_input.png (before coding)

Footprint: 91.1 um (L) x 50.75 um (W). Image 728x405 px, ~0.125 um/px.

## What the image shows (measured from black pixels, layer (1,0))
- A single waveguide enters from the far left at the vertical centerline
  (y ~= 22.7 um from top, i.e. slightly above image middle) and exits at the
  far right at the same centerline. Input line width ~= 0.5 um.
- Two solid black BARS: left bar ~x 10-16 um, right bar ~x 68-81 um, each
  ~2.5 um tall. These are the two 2x2 couplers of an MZI drawn schematically
  (splitter on the left, combiner on the right). The waveguides taper into them.
- Between the couplers the guide splits into TWO arms that each make a large
  rounded-rectangle (racetrack) detour: the TOP arm bends up, runs a vertical
  straight, rounds over a horizontal cap near y~=0, comes back down and rejoins;
  the BOTTOM arm mirrors this downward to y~=50.
  Racetrack vertical walls sit at x ~= 35 um (left) and x ~= 54 um (right);
  caps reach y ~= 0 (top) and y ~= 50 (bottom). Corner radius looks ~5 um.

## Interpretation
Classic unbalanced Mach-Zehnder interferometer:
  input -> coupler1 (splitter) -> {top arm, bottom arm} -> coupler2 (combiner) -> output
The two arms take large opposite detours; their path-length difference is the
`delta_length` that sets the FSR. The drawing is near-symmetric, so the nominal
delta is small (a few um), injected as extra length on one arm's cap.

## Primitives-only build plan
- couplers: `gf.components.rectangle` (basic shape) — the two solid bars.
- arms: `gf.Path` built by appending `gf.path.straight` + `gf.path.euler(90)`
  segments (lead -> up-bend -> vertical -> corner -> cap -> corner -> vertical
  -> bend -> lead). One helper builds both arms; the bottom arm's cap is longer
  by `delta_length`, so bottom.length() - top.length() == delta_length exactly.
- input/output: `gf.path.straight` extruded, centerline y=0.
- All extruded with a width=`wg_width` cross-section on layer (1,0). ends write_gds.
- ARM_LENGTHS computed from the Path objects at build time; lengths.json written
  next to the GDS: {arms:{top,bottom}, delta_length_um: bottom-top}.

No device stencils (no mzi*/coupler-as-device/ring*), no raw polygons.
