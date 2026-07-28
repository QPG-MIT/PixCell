"""Metamaterial-clad multi-strip directional coupler section (primitives only).

Central 5-strip sub-wavelength bundle (the bus), flanked above and below by a
wide rail at a small coupling gap; each rail carries a 5-strip sub-wavelength
cladding on its outer side (staggered ends). Rails end in curved facets and
bend away as thick exit bars; the strip bundles merge into their own bent
exits. Slightly asymmetric top/bottom gaps, as measured. Boolean-clipped to
the L_total x H_total frame.
"""

import gdsfactory as gf

# ---------------- tunables (um) ----------------
L_total = 120.0            # device length
H_total = 4.0              # device height (frame clip)
y_mid = 1.9939             # central-bundle midline

# central sub-wavelength bundle (the bus core)
n_core = 5
core_center_offsets = (-0.2015, -0.0994, 0.0, 0.1021, 0.2014)  # vs y_mid
core_strip_heights = (0.0692, 0.0614, 0.0591, 0.0670, 0.0692)  # bottom->top
core_margin_l = 0.03       # bundle end clearance, left
core_margin_r = 0.09       # bundle end clearance, right
core_dy = -0.0017          # fine vertical trim of the bundle only

# coupling section (function knobs); *_b = bottom half (measured asymmetry)
coupling_gap = 0.0369      # top rail <-> bundle gap
coupling_gap_b = 0.0267
rail_w = 0.4688            # top rail width
rail_w_b = 0.4666
coupling_len = 106.20      # rail (interaction) length, centered on the device
rail_len_delta = 0.0       # top-rail length excess over bottom (arm imbalance)
rail_x0 = (L_total - coupling_len) / 2   # rail outer-edge start x
rail_x1 = (L_total + coupling_len) / 2   # rail outer-edge end x
# rail end facet: inner-edge setback vs fraction t (0 = outer edge, 1 = inner)
facet_profile = ((0.0, 0.0), (0.25, 0.40), (0.5, 0.92), (0.73, 1.52),
                 (0.91, 2.22), (1.0, 2.85))
facet_steps = 14

# outer sub-wavelength cladding strips on each rail
n_strips = 5
strip_w = 0.0658
strip_pitch = 0.1002
strip_pitch_b = 0.1003
outer_gap = 0.0324         # top rail <-> first outer strip gap
outer_gap_b = 0.0357
strip_margins = (7.82, 8.08, 8.42, 9.70, 10.05)  # end margin, outermost->rail

# bent exits: top-left control points (x, y, width-after-this-vertex);
# widths taper toward the frame edge, matching the measured curve
rail_exit_pts = ((9.20, 2.500, 0.52), (7.744, 2.828, 0.54),
                 (7.078, 2.996, 0.57), (6.456, 3.219, 0.60),
                 (5.906, 3.442, 0.63), (5.443, 3.665, 0.66),
                 (5.052, 3.888, 0.70), (4.67, 4.10, 0.66))
strip_exit_pts = ((9.80, 3.000, 0.50), (8.121, 3.442, 0.56),
                  (7.658, 3.665, 0.62), (7.281, 3.888, 0.68),
                  (6.92, 4.10, 0.67))

LAYER = (1, 0)


def _interp(table, t):
    for (t0, v0), (t1, v1) in zip(table, table[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return table[-1][1]


@gf.cell
def device() -> gf.Component:
    raw = gf.Component()

    def rect(comp, x0, y0, x1, y1):
        if x1 <= x0 or y1 <= y0:
            return
        r = comp << gf.components.rectangle(size=(x1 - x0, y1 - y0), layer=LAYER)
        r.move((x0, y0))

    # ---- central bundle
    for off, h in zip(core_center_offsets, core_strip_heights):
        yc = y_mid + off + core_dy
        rect(raw, core_margin_l, yc - h / 2, L_total - core_margin_r, yc + h / 2)

    bundle_top = y_mid + core_center_offsets[-1] + core_strip_heights[-1] / 2
    bundle_bot = y_mid + core_center_offsets[0] - core_strip_heights[0] / 2

    def exit_bars(pts, sign):
        """Bent exit at both x-ends of one half; pts given for the top-left.

        Extruded segment-by-segment with per-segment widths (union overlaps).
        """
        for mirror_x in (False, True):
            p = [
                ((L_total - px if mirror_x else px), y_mid + sign * (py - y_mid))
                for px, py, _ in pts
            ]
            for (x0, y0), (x1, y1), (_, _, w) in zip(p, p[1:], pts[1:]):
                # extend each segment slightly so joints overlap (no notches)
                dx, dy = x1 - x0, y1 - y0
                n = (dx * dx + dy * dy) ** 0.5
                ex, ey = 0.04 * dx / n, 0.04 * dy / n
                raw << gf.path.extrude(
                    gf.Path([(x0 - ex, y0 - ey), (x1 + ex, y1 + ey)]),
                    width=w, layer=LAYER,
                )

    rail_bands = []
    rail_spans: dict[str, tuple[float, float]] = {}

    def half_side(sign, gap, r_w, o_gap, s_pitch):
        """One rail + outer strips + bent exits; sign=+1 top, -1 bottom."""
        edge = bundle_top if sign > 0 else bundle_bot
        r_in = edge + sign * gap                # rail inner edge y
        r_out = r_in + sign * r_w               # rail outer edge y
        lo, hi = sorted((r_in, r_out))
        x_end = rail_x1 + (rail_len_delta if sign > 0 else 0.0)
        rect(raw, rail_x0, lo, x_end, hi)
        rail_bands.append((r_in, r_out))
        rail_spans["rail_top" if sign > 0 else "rail_bot"] = (rail_x0, x_end)

        s_edge = r_out + sign * o_gap           # first strip inner edge
        for i in range(n_strips):
            j = n_strips - 1 - i                # j=0 nearest rail
            yc = s_edge + sign * (j * s_pitch + strip_w / 2)
            m = strip_margins[i]
            lo, hi = sorted((yc - strip_w / 2, yc + strip_w / 2))
            rect(raw, m, lo, L_total - m, hi)

        exit_bars(rail_exit_pts, sign)
        exit_bars(strip_exit_pts, sign)

    half_side(+1, coupling_gap, rail_w, outer_gap, strip_pitch)
    half_side(-1, coupling_gap_b, rail_w_b, outer_gap_b, strip_pitch_b)

    # ---- curved rail end facets: staircase cut following facet_profile
    cuts = gf.Component()
    for r_in, r_out in rail_bands:
        for k in range(facet_steps):
            t0, t1 = k / facet_steps, (k + 1) / facet_steps
            setback = _interp(facet_profile, (t0 + t1) / 2)
            ys = sorted((r_out + (r_in - r_out) * t0, r_out + (r_in - r_out) * t1))
            rect(cuts, rail_x0 - 0.05, ys[0], rail_x0 + setback, ys[1])
            rect(cuts, rail_x1 - setback, ys[0], rail_x1 + 0.05, ys[1])

    clipped = gf.boolean(raw, cuts, operation="not", layer=LAYER)

    # ---- clip everything to the frame
    frame = gf.Component()
    rect(frame, 0.0, 0.0, L_total, H_total)
    final = gf.boolean(clipped, frame, operation="and", layer=LAYER)

    c = gf.Component()
    c << final
    for name, (xa, xb) in rail_spans.items():
        c.info[name + "_len_um"] = abs(xb - xa)
    return c


if __name__ == "__main__":
    import json
    from pathlib import Path

    comp = device()
    here = Path(__file__).resolve().parent
    out = here / "device.gds"
    comp.write_gds(str(out), with_metadata=False)
    arms = {
        "rail_top": float(comp.info["rail_top_len_um"]),
        "rail_bot": float(comp.info["rail_bot_len_um"]),
    }
    (here / "lengths.json").write_text(
        json.dumps({
            "arms": arms,
            "delta_length_um": abs(arms["rail_top"] - arms["rail_bot"]),
            "coupling_len_um": coupling_len,
        }, indent=2)
    )
    print("wrote", out, "; bbox:", comp.bbox_np())
