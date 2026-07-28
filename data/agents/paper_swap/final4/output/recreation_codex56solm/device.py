from pathlib import Path
import json

import gdsfactory as gf
import numpy as np


layer = (1, 0)
footprint_length = 18.0
footprint_width = 3.0
wg_width = 0.65
tip_width = 0.65
coupling_gap = 0.31
approach_offset = 0.695
approach_length = 9.0
taper_length = 9.0
transfer_length = 0.0
delta_length = 0.0
shape_power = 1.0
samples = 361


def smootherstep(t: np.ndarray) -> np.ndarray:
    t = np.clip(t, 0.0, 1.0)
    base = t * t * t * (t * (t * 6.0 - 15.0) + 10.0)
    return np.power(base, shape_power)


def coupling_envelope(x: np.ndarray) -> np.ndarray:
    center = footprint_length / 2.0
    half_transfer = transfer_length / 2.0
    effective_taper_length = (approach_length + taper_length) / 2.0
    distance_from_center = np.maximum(np.abs(x - center) - half_transfer, 0.0)
    normalized = 1.0 - distance_from_center / effective_taper_length
    return smootherstep(normalized)


@gf.cell
def adiabatic_directional_coupler() -> gf.Component:
    component = gf.Component()
    x = np.linspace(0.0, footprint_length, samples)
    envelope = coupling_envelope(x)

    closest_center = footprint_width / 2.0 - coupling_gap / 2.0 - wg_width / 2.0
    outer_center = closest_center - approach_offset
    offset = (closest_center - outer_center) * envelope
    top_y = outer_center + offset
    bottom_y = footprint_width - outer_center - offset

    top_points = np.column_stack((x, top_y))
    if delta_length > 0.0:
        top_points = np.vstack((top_points, [footprint_length + delta_length, top_y[-1]]))
    top_path = gf.Path(top_points)
    bottom_path = gf.Path(np.column_stack((x, bottom_y)))

    effective_width = (wg_width + tip_width) / 2.0
    cross_section = gf.CrossSection(
        sections=(gf.Section(width=effective_width, layer=layer),)
    )
    component.add_ref(gf.path.extrude(top_path, cross_section=cross_section))
    component.add_ref(gf.path.extrude(bottom_path, cross_section=cross_section))

    lengths = {
        "arms": {
            "top_um": float(top_path.length()),
            "bottom_um": float(bottom_path.length())
        },
        "delta_length_um": float(top_path.length() - bottom_path.length())
    }
    Path(__file__).with_name("lengths.json").write_text(
        json.dumps(lengths, indent=2) + "\n"
    )
    return component


if __name__ == "__main__":
    cell = adiabatic_directional_coupler()
    cell.write_gds(Path(__file__).with_name("device.gds"), with_metadata=False)
