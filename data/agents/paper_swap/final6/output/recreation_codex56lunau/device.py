import json
from pathlib import Path

import gdsfactory as gf
import numpy as np
from gdsfactory.cross_section import CrossSection, Section


# Function-defining dimensions (um).
layer = (1, 0)
wg_width = 0.24
lobe_width = 0.91
arm_length = 2.35
port_length = 0.56
peak_distance = 1.49
path_samples = 129
asymmetry_length = 0.0


def _smoothstep(x: np.ndarray) -> np.ndarray:
    return x * x * (3.0 - 2.0 * x)


def _base_arm_width(t: np.ndarray) -> np.ndarray:
    """Width along an arm, from its outer port (t=0) to the junction (t=1)."""
    t = np.asarray(t, dtype=float)
    port_t = port_length / arm_length
    peak_t = peak_distance / arm_length
    widths = np.full_like(t, wg_width)

    rising = (t > port_t) & (t < peak_t)
    x_rise = (t[rising] - port_t) / (peak_t - port_t)
    widths[rising] = wg_width + (lobe_width - wg_width) * _smoothstep(x_rise)

    falling = t >= peak_t
    x_fall = np.clip((t[falling] - peak_t) / (1.0 - peak_t), 0.0, 1.0)
    widths[falling] = lobe_width + (wg_width - lobe_width) * _smoothstep(x_fall)
    return widths


def _arm(extension: float = 0.0) -> tuple[gf.Component, gf.Path]:
    total_length = arm_length + extension
    x = np.linspace(-arm_length, 0.0, path_samples)
    if extension > 0.0:
        x = np.concatenate((np.array([-total_length]), x))
    path = gf.Path(np.column_stack((x, np.zeros_like(x))))

    def width_profile(t: np.ndarray) -> np.ndarray:
        t = np.asarray(t, dtype=float)
        if extension <= 0.0:
            return _base_arm_width(t)
        join_t = extension / total_length
        base_t = np.clip((t - join_t) / (1.0 - join_t), 0.0, 1.0)
        widths = _base_arm_width(base_t)
        widths[t < join_t] = wg_width
        return widths

    section = Section(
        width=wg_width,
        layer=layer,
        width_function=width_profile,
        port_names=("o1", "o2"),
    )
    cross_section = CrossSection(sections=(section,))
    return gf.path.extrude(path, cross_section=cross_section), path


@gf.cell
def crossing() -> gf.Component:
    component = gf.Component("four_port_crossing")
    arm, reference_path = _arm()
    top_arm, top_path = _arm(asymmetry_length)
    for angle in (0, 90, 180):
        reference = component.add_ref(arm)
        reference.rotate(angle, center=(0.0, 0.0))
    top_reference = component.add_ref(top_arm)
    top_reference.rotate(270, center=(0.0, 0.0))
    arm_lengths = {
        "reference": reference_path.length(),
        "function": top_path.length(),
    }
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(
            {
                "arms": arm_lengths,
                "delta_length_um": abs(arm_lengths["function"] - arm_lengths["reference"]),
            },
            indent=2,
        )
    )
    return component


if __name__ == "__main__":
    crossing().write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
