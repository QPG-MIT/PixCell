from pathlib import Path

import gdsfactory as gf
import json
import numpy as np
from gdsfactory.cross_section import Section


layer = (1, 0)
arm_length_um = 2.35
top_stub_length_um = 0.0
center_width_um = 0.80
shoulder_width_um = 0.92
mid_width_um = 0.89
tip_width_um = 0.23

profile_t = np.array([0.0, 0.14, 0.30, 0.52, 0.74, 1.0], dtype=float)
profile_w = np.array(
    [center_width_um, shoulder_width_um, mid_width_um, 0.60, 0.32, tip_width_um],
    dtype=float,
)


def arm_width_function(t: np.ndarray) -> np.ndarray:
    t = np.asarray(t, dtype=float)
    return np.interp(t, profile_t, profile_w)


def build_arm(length_um: float) -> gf.Component:
    p = gf.path.straight(length_um, npoints=401)
    xs = gf.CrossSection(
        sections=(
            Section(
                width=center_width_um,
                layer=layer,
                width_function=arm_width_function,
                name="core",
            ),
        )
    )
    return p.extrude(cross_section=xs)


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()
    arm_lengths = {
        0: arm_length_um + top_stub_length_um,
        90: arm_length_um,
        180: arm_length_um,
        270: arm_length_um,
    }
    for angle in (0, 90, 180, 270):
        arm = build_arm(arm_lengths[angle])
        ref = c.add_ref(arm)
        ref.rotate(angle)
    return c


def main() -> Path:
    c = build_device().copy()
    c.flatten()
    out = Path(__file__).with_suffix(".gds")
    c.write_gds(out, with_metadata=False)
    lengths = {
        "arms": {
            "top": arm_length_um + top_stub_length_um,
            "bottom": arm_length_um,
        },
        "delta_length_um": top_stub_length_um,
    }
    out.with_name("lengths.json").write_text(json.dumps(lengths, indent=2))
    return out


if __name__ == "__main__":
    print(main())
