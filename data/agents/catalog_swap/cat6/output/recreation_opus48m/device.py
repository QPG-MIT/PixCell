"""Waveguide crossing (elliptical mode-expander crossing) — primitives-only, parametric.

Two orthogonal single-mode waveguides cross at the center. Each arm carries an
adiabatic elliptical mode-expander lobe that widens the mode before the
intersection (to suppress diffraction/crosstalk) and re-focuses it after. The
4-pointed-star silhouette is the boolean union of the two orthogonal lobes; the
four thin spikes are the single-mode access-waveguide tapers reaching the edge.

Layer (1,0). gdsfactory 9.20.7. Primitives only: gf.components.taper chain +
gf.boolean + @gf.cell assembly.
"""

import json
from pathlib import Path

import numpy as np
import gdsfactory as gf

# ---- top-level tunables (JEE-substitutable) --------------------------------
footprint = 8.0          # um, square die (tip-to-tip along each arm)
wg_width = 0.505         # um, single-mode access waveguide width at each port
neck_width = 0.74        # um, waveguide width at the lobe throat
lobe_width = 2.20        # um, full lobe width at the crossing center (mode expansion)
lobe_semi_major = 3.0    # um, half-length of the lens lobe along its arm (taper adiabaticity)
taper_length = 1.20      # um, access-taper length from die edge to lobe throat
n_seg = 80               # taper segments per arm (ellipse discretization)

LAYER = (1, 0)
_WMIN = 0.02             # um, floor so no zero-width taper


def _half_width(t: float) -> float:
    """Arm width (um) at position t (um) along the arm, t in [0, footprint]."""
    c = footprint / 2.0
    dy = abs(t - c)
    # access taper: wg_width at the edge (dy=c) -> neck_width at dy = c - taper_length
    if dy >= c - taper_length:
        neck = wg_width + (neck_width - wg_width) * (c - dy) / taper_length
    else:
        neck = neck_width
    # elliptical mode-expander lobe
    r2 = 1.0 - (dy / lobe_semi_major) ** 2
    ell = lobe_width * np.sqrt(r2) if r2 > 0.0 else 0.0
    w = max(neck, ell, _WMIN)
    return round(w / 0.002) * 0.002  # snap to 2 nm grid (kfactory port constraint)


def _arm() -> gf.Component:
    """One arm as a taper chain along x, centered at the origin (spans -c..+c)."""
    c = footprint / 2.0
    arm = gf.Component()
    ts = np.linspace(0.0, footprint, n_seg + 1)
    for i in range(n_seg):
        x0, x1 = float(ts[i]), float(ts[i + 1])
        seg = gf.components.taper(
            length=x1 - x0,
            width1=_half_width(x0),
            width2=_half_width(x1),
            layer=LAYER,
        )
        ref = arm.add_ref(seg)
        ref.move((x0 - c, 0.0))  # taper input port sits at x0-c
    return arm


@gf.cell
def crossing() -> gf.Component:
    arm_h = _arm()
    arm_v = gf.Component()
    vref = arm_v.add_ref(arm_h)
    vref.rotate(90.0)
    union = gf.boolean(arm_h, arm_v, "or", layer=LAYER)

    c = gf.Component()
    ref = c.add_ref(union)
    ref.move((footprint / 2.0, footprint / 2.0))  # place device in [0,footprint]^2
    return c


def _write_lengths(out_dir: Path) -> None:
    """Self-measured centerlines (measurement contract). Two orthogonal arms."""
    ph = gf.Path([(0.0, footprint / 2.0), (footprint, footprint / 2.0)])
    pv = gf.Path([(footprint / 2.0, 0.0), (footprint / 2.0, footprint)])
    lh, lv = float(ph.length()), float(pv.length())
    payload = {
        "arms": {"horizontal": lh, "vertical": lv},
        "delta_length_um": abs(lh - lv),
    }
    (out_dir / "lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    out_dir = Path(__file__).resolve().parent
    comp = gf.Component()          # fresh (unlocked) wrapper
    comp.add_ref(crossing())
    comp.flatten()                 # geometry as a single top-level cell (avoid $$$CONTEXT_INFO$$$ wrapping)
    comp.write_gds(out_dir / "device.gds")
    _write_lengths(out_dir)
    print("wrote", out_dir / "device.gds")
