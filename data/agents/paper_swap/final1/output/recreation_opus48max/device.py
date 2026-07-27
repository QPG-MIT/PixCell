"""
Adiabatic 1x2 power splitter (three-waveguide mode-evolution coupler).

Recreation of experiments/paper_swap/final1/device_bw.png (40 x 1.7 um).

A central input waveguide is adiabatically tapered DOWN to a tip while two
symmetric outer waveguides are tapered UP from tips, at a constant sub-wavelength
gap. The central fundamental mode evolves into the symmetric supermode of the two
outer guides (50/50 power transfer), which are then routed apart by S-bends to
two output ports.

Primitives only: straight, taper, gf.Path->extrude, @gf.cell assembly. Layer (1,0).
"""
from pathlib import Path
import json
import numpy as np
import gdsfactory as gf

# ---------------------------------------------------------------------------
# Top-level tunables (the device's function knobs)
# ---------------------------------------------------------------------------
w_in = 0.27           # central input waveguide width (um)
w_center_tip = 0.076  # central taper mid/tip width where the sharp point begins (um)
w_center_point = 0.02 # final central point width (adiabatic donor endpoint, um)
w_outer_tip = 0.064   # outer waveguide tip width (acceptor start, um)
w_wg = 0.242          # single-mode outer/output guide width (um)
gap_um = 0.105        # coupling gap, edge-to-edge -> coupling strength (um)
L_in = 3.1            # central input straight length before coupler (um)
L_couple = 22.9       # adiabatic coupling / outer-taper length (um) -- critical knob
L_center_taper = 21.9 # central down-taper length to w_center_tip (um)
L_center_point = 0.5  # final sharp point taper (w_center_tip -> w_center_point, um)
L_sbend = 10.0        # S-bend (output routing) length (um)
L_out = 4.0           # output straight length (um)
out_offset = 0.728    # output waveguide center offset from device center (um)
y_offset_coupler = 0.0125  # coupler-section vertical offset vs symmetric outputs (um)
delta_length = 0.0    # output-arm length imbalance (routing/phase knob; 0 = symmetric)

LAYER = (1, 0)


def _sbend_path(length: float, dy: float, npoints: int = 121) -> gf.Path:
    """Smooth cosine S-bend centerline from (0,0) to (length, dy)."""
    x = np.linspace(0.0, length, npoints)
    y = dy * (1.0 - np.cos(np.pi * x / length)) / 2.0
    return gf.Path(np.column_stack([x, y]))


@gf.cell
def adiabatic_splitter(
    w_in: float = w_in,
    w_center_tip: float = w_center_tip,
    w_center_point: float = w_center_point,
    w_outer_tip: float = w_outer_tip,
    w_wg: float = w_wg,
    gap_um: float = gap_um,
    L_in: float = L_in,
    L_couple: float = L_couple,
    L_center_taper: float = L_center_taper,
    L_center_point: float = L_center_point,
    L_sbend: float = L_sbend,
    L_out: float = L_out,
    out_offset: float = out_offset,
    y_offset_coupler: float = y_offset_coupler,
    delta_length: float = delta_length,
) -> gf.Component:
    c = gf.Component()
    xs_wg = gf.cross_section.cross_section(width=w_wg, layer=LAYER)
    xs_in = gf.cross_section.cross_section(width=w_in, layer=LAYER)

    # Coupler-region outer-arm half-offset, set by the coupling gap.
    # Because the central and outer widths taper complementarily, using the
    # average widths keeps the edge-to-edge gap ~= gap_um across the coupler.
    y_couple = gap_um + (w_in + w_center_tip) / 4.0 + (w_outer_tip + w_wg) / 4.0
    # The coupler section sits slightly above the (symmetric) output center.
    ys = y_offset_coupler

    x_coupler_end = L_in + L_couple
    x_sbend_end = x_coupler_end + L_sbend

    # ---- Central waveguide: input straight + down-taper + sharp point ----
    s_in = c << gf.components.straight(length=L_in, cross_section=xs_in)
    s_in.move((0.0, 0.0), (0.0, ys))  # o1 at (0, ys)
    t_c = c << gf.components.taper(
        length=L_center_taper, width1=w_in, width2=w_center_tip, layer=LAYER
    )
    t_c.move((0.0, 0.0), (L_in, ys))  # o1 at coupler start
    # final sharp point so the donor closes to a tip (no blunt end face)
    t_cp = c << gf.components.taper(
        length=L_center_point, width1=w_center_tip, width2=w_center_point, layer=LAYER
    )
    t_cp.move((0.0, 0.0), (L_in + L_center_taper, ys))

    # ---- Outer arms (x2): up-taper + S-bend + output straight ----
    arm_len = {}
    for name, sign in (("top", +1.0), ("bottom", -1.0)):
        yc = sign * y_couple + ys           # coupler-region arm center (shifted)
        yo = sign * out_offset              # output center (symmetric)

        t_o = c << gf.components.taper(
            length=L_couple, width1=w_outer_tip, width2=w_wg, layer=LAYER
        )
        t_o.move((0.0, 0.0), (L_in, yc))  # o1 at coupler start, offset yc

        sbend_len = _sbend_path(L_sbend, yo - yc).length()
        sb = c << gf.path.extrude(_sbend_path(L_sbend, yo - yc), xs_wg)
        sb.move((0.0, 0.0), (x_coupler_end, yc))  # start at coupler end

        this_out = L_out + (delta_length if name == "top" else 0.0)
        s_o = c << gf.components.straight(length=this_out, cross_section=xs_wg)
        s_o.move((0.0, 0.0), (x_sbend_end, yo))

        # Arm centerline length (from real segment geometry)
        arm_len[name] = L_couple + sbend_len + this_out

    # ---- Measurement contract: lengths.json next to the GDS ----
    out_dir = Path(__file__).resolve().parent
    delta = abs(arm_len["top"] - arm_len["bottom"])
    (out_dir / "lengths.json").write_text(
        json.dumps(
            {"arms": arm_len, "delta_length_um": delta},
            indent=2,
        )
    )
    return c


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    comp = adiabatic_splitter()
    # with_metadata=False keeps the device cell top-level (no $$$CONTEXT_INFO$$$
    # wrapper), so gdstk-based area/bbox measurement sees the real polygons.
    comp.write_gds(out_dir / "device.gds", with_metadata=False)
    print("bbox_um:", comp.bbox_np().flatten().tolist() if hasattr(comp, "bbox_np") else comp.bbox())
    print("wrote", out_dir / "device.gds")
