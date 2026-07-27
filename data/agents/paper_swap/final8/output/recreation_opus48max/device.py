"""
Symmetric multi-waveguide SWG coupler (primitives-only, parametric).

Transverse cross-section (bottom -> top), mirror-symmetric about y = W/2:
    [5-rail SWG bundle][strip bar][5-rail SWG bundle][strip bar][5-rail SWG bundle]
The CENTER 5-rail bundle is the through waveguide (full length L). The two
flanking arms (each = 1 strip bar + 1 outer 5-rail bundle) run parallel to the
center over the coupling length couple_len, then the whole bundle bends up/down
to the transverse edges at both ends (the input/output fans).

Primitives only:
  - center rails: gf.Path straight + extrude
  - each arm: ONE gf.path.smooth() U-path extruded through a multi-Section
    CrossSection, so the bar + 5 rails bend together as a bundle.
No gf.components device stencils, no raw polygons. Layer (1, 0).

Note (gdsfactory 9.20.7): a Section's +offset lands at -y for a +x path, so
element offsets are computed as (centerline_y - element_y).
"""

import json
from pathlib import Path

import gdsfactory as gf

# ------------------------------- top-level tunables --------------------------
L = 120.0            # device length / through-guide length  [FUNCTION knob, verified]
W = 4.0              # transverse aperture (footprint width)
n_rail = 5           # rails per SWG bundle                   [FUNCTION knob, int]
rail_w = 0.068       # SWG rail width (um)                    [FUNCTION knob]
rail_pitch = 0.100   # SWG rail pitch (um)                    [FUNCTION knob]
bar_w = 0.470        # strip-bar width (um)                   [FUNCTION knob]
couple_len = 104.30  # coupling / transfer length (um)        [FUNCTION knob]
gap_cb = 0.033       # center-bundle -> bar slot / coupling gap (um)  [FUNCTION knob]
gap_br = 0.030       # bar -> outer-bundle slot (um)          [FUNCTION knob]
bundle_yc = 1.9933   # center-bundle transverse center (um)   [FUNCTION knob]
fan_radius = 3.6     # input/output fan bend radius (um)      [FUNCTION knob]
fan_top = 9.00       # fan stub reach toward the edge (um, clipped at W) [FUNCTION knob]

LAYER = (1, 0)


def _rail_offsets(n, pitch):
    return [(k - (n - 1) / 2.0) * pitch for k in range(n)]


def _arm_element_ys(y_mid, sign):
    """Absolute transverse y of the (bar, rail0..rail4) of one arm.

    sign = +1 -> top arm (toward y=W), -1 -> bottom arm (toward y=0).
    Positions derive from the coupling/slot knobs, symmetric about y_mid.
    """
    center_half = ((n_rail - 1) / 2.0) * rail_pitch + rail_w / 2.0   # center bundle half-height
    bar_off = center_half + gap_cb + bar_w / 2.0                      # bar center from y_mid
    outer_first = bar_off + bar_w / 2.0 + gap_br + rail_w / 2.0       # first outer rail from y_mid
    bar_y = y_mid + sign * bar_off
    rail_ys = [y_mid + sign * (outer_first + k * rail_pitch) for k in range(n_rail)]
    return bar_y, rail_ys


@gf.cell
def device() -> gf.Component:
    c = gf.Component()
    y_mid = W / 2.0
    straight_x0 = (L - couple_len) / 2.0
    straight_x1 = straight_x0 + couple_len

    # --- center through bundle: n_rail straight rails, full length ---
    for off in _rail_offsets(n_rail, rail_pitch):
        p = gf.Path([(0.0, bundle_yc + off), (L, bundle_yc + off)])
        c.add_ref(p.extrude(width=rail_w, layer=LAYER))

    # --- two coupled arms (bar + outer bundle), each a bent U-shaped bundle ---
    for sign in (+1, -1):                            # +1 top arm, -1 bottom arm
        bar_y, rail_ys = _arm_element_ys(y_mid, sign)
        elem_ys = [bar_y] + rail_ys                 # absolute y of each element
        centerline = (min(elem_ys) + max(elem_ys)) / 2.0   # bundle span center
        widths = [bar_w] + [rail_w] * n_rail
        # gdsfactory: +offset -> -y, so offset = centerline - element_y
        sections = tuple(
            gf.Section(width=w, offset=centerline - ey, layer=LAYER)
            for w, ey in zip(widths, elem_ys)
        )
        xs = gf.CrossSection(sections=sections)
        # U-path: stub at edge -> down to centerline -> straight -> up to edge
        cx0 = straight_x0 - fan_radius
        cx1 = straight_x1 + fan_radius
        y_edge = fan_top if sign > 0 else (W - fan_top)   # reach past the edge; render clips at [0,W]
        pts = [
            (cx0, y_edge),
            (cx0, centerline),
            (cx1, centerline),
            (cx1, y_edge),
        ]
        u = gf.path.smooth(points=pts, radius=fan_radius)
        c.add_ref(u.extrude(xs))

    return c


if __name__ == "__main__":
    c = device()
    here = Path(__file__).resolve().parent
    # Flatten before writing: gdsfactory/kfactory otherwise makes $$$CONTEXT_INFO$$$
    # the only top-level cell (referencing `device`), and the measurement contract's
    # _layer_area skips $$$ cells -> would read 0 area. Flattening puts the real
    # polygons in a top-level cell so gdstk area/bbox measurement works.
    flat = c.copy()
    flat.flatten()
    flat.write_gds(here / "device.gds")

    # Parametric measurement contract (spec_optimization.measured_delta_length):
    # two REAL straight guides -> through (center bundle, length L) and
    # coupled (arm coupling section, length couple_len). L is the verified knob
    # (delta = L - couple_len is +1 in L; couple_len < L keeps the sign clean).
    through_len = float(L)
    coupled_len = float(couple_len)
    (here / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {"through": through_len, "coupled": coupled_len},
                "delta_length_um": abs(through_len - coupled_len),
            },
            indent=2,
        )
    )
    print(f"wrote device.gds  through={through_len} coupled={coupled_len} delta={abs(through_len-coupled_len):.3f}")
