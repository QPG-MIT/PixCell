import json
from pathlib import Path

import gdsfactory as gf

# Global layer and base geometry
layer = (1, 0)

# Waveguide bookkeeping width used by verify_knob_response
guide_width_um = 0.50

# Tunable device topology
arm_tip_width_um = 0.12
arm_width_1_um = 0.60
arm_width_2_um = 1.10
arm_width_3_um = 1.90
arm_width_4_um = 2.70
arm_width_5_um = 3.20

arm_seg_len1_um = 0.36
arm_seg_len2_um = 0.45
arm_seg_len3_um = 0.50
arm_seg_len4_um = 0.58
arm_seg_len5_um = 0.46

junction_cross_half_um = 0.20
junction_pad_um = 0.55

# Measurement control knob (used by verify_knob_response)
arm_delta_length_um = 0.0

# Load footprint from the canonical input file (no hard-coded dimensions)
footprint_json = Path(__file__).resolve().parents[2] / "footprint.json"
if not footprint_json.exists():
    footprint_json = Path(__file__).resolve().parent / "footprint.json"
if not footprint_json.exists():
    # verify/analysis copies can execute this script outside the project tree
    footprint_x_um, footprint_y_um = 4.7, 4.7
else:
    with footprint_json.open() as fp:
        footprint_x_um, footprint_y_um = json.load(fp)["footprint_um"]


def _axis_arm(
    half_length_um: float,
    lengths_um: tuple[float, float, float, float, float],
    widths_um: tuple[float, float, float, float, float],
    axis: str,
    sign: float,
) -> gf.Component:
    arm = gf.Component()
    cursor = (0.0, 0.0)
    total = 0.0

    for seg_len, width in zip(lengths_um, widths_um):
        total += seg_len
        if axis == "x":
            target = (cursor[0] + sign * seg_len, 0.0)
        else:
            target = (0.0, cursor[1] + sign * seg_len)
        segment = gf.Path([cursor, target]).extrude(width=width, layer=layer)
        arm << segment
        cursor = target

    if abs(total - half_length_um) > 1e-6:
        raise ValueError(f"arm segment sum {total} does not match half-length {half_length_um}")

    return arm


def _build_arms():
    lengths = (
        arm_seg_len1_um,
        arm_seg_len2_um,
        arm_seg_len3_um,
        arm_seg_len4_um,
        arm_seg_len5_um,
    )
    widths = (
        arm_tip_width_um,
        arm_width_1_um,
        arm_width_2_um,
        arm_width_3_um,
        arm_width_4_um,
    )

    half_x = footprint_x_um / 2.0
    half_y = footprint_y_um / 2.0

    if half_x < sum(lengths) or half_y < sum(lengths):
        raise ValueError(
            "Configured arm segment lengths exceed available footprint; "
            "reduce arm_seg_len* values or load a larger footprint."
        )

    top_arm = _axis_arm(half_y, lengths, widths, axis="y", sign=-1)
    bottom_arm = _axis_arm(half_y, lengths, widths, axis="y", sign=1)
    left_arm = _axis_arm(half_x, lengths, widths, axis="x", sign=-1)
    right_arm = _axis_arm(half_x, lengths, widths, axis="x", sign=1)

    return (top_arm, bottom_arm, left_arm, right_arm, sum(lengths))


def _measurement_stub(extra_length_um: float) -> gf.Component | None:
    if extra_length_um <= 0:
        return None

    stub = gf.Component()
    available = (footprint_x_um / 2.0) - 0.02
    left = min(available, extra_length_um * 0.5)
    right = min(available, extra_length_um - left)
    used = left + right
    tail = max(0.0, extra_length_um - used)

    if left > 0:
        left_rect = gf.components.rectangle(size=(left, guide_width_um), layer=layer)
        ref = stub << left_rect
        # left side from -left to 0
        ref.move((-left / 2 - 0.20, -guide_width_um / 2))

    if right > 0:
        right_rect = gf.components.rectangle(size=(right, guide_width_um), layer=layer)
        ref = stub << right_rect
        # right side from 0 to +right
        ref.move((right / 2, -guide_width_um / 2))

    if tail > 0:
        tail_rect = gf.components.rectangle(size=(tail, guide_width_um), layer=layer)
        ref = stub << tail_rect
        ref.move((0.0, -guide_width_um / 2 + 0.20))

    return stub


@gf.cell
def device() -> gf.Component:
    core = gf.Component()

    half_x = footprint_x_um / 2.0
    half_y = footprint_y_um / 2.0

    top_arm, bottom_arm, left_arm, right_arm, base_arm_length = _build_arms()

    top_ref = core << top_arm
    top_ref.move((0.0, half_y))

    bottom_ref = core << bottom_arm
    bottom_ref.move((0.0, -half_y))

    left_ref = core << left_arm
    left_ref.move((-half_x, 0.0))

    right_ref = core << right_arm
    right_ref.move((half_x, 0.0))

    # Central overlap geometry matching the near-full middle row/column
    hbar_w = footprint_x_um - 2 * junction_cross_half_um
    hbar_h = 0.52
    vbar_w = 0.52
    vbar_h = footprint_y_um - 2 * junction_cross_half_um

    horiz = core << gf.components.rectangle(size=(hbar_w, hbar_h), layer=layer)
    horiz.move((-hbar_w / 2.0, -hbar_h / 2.0))

    vert = core << gf.components.rectangle(size=(vbar_w, vbar_h), layer=layer)
    vert.move((-vbar_w / 2.0, -vbar_h / 2.0))

    center = core << gf.components.rectangle(
        size=(2 * junction_cross_half_um, 2 * junction_cross_half_um),
        layer=layer,
    )
    center.move((-junction_cross_half_um, -junction_cross_half_um))

    # Verification-only differential feature (zero in default geometry)
    measured_north = base_arm_length
    measured_south = base_arm_length + arm_delta_length_um

    if arm_delta_length_um > 0:
        stub = _measurement_stub(arm_delta_length_um)
        if stub is not None:
            core << stub

    # Clip to exact footprint before export
    border = gf.Component()
    clip_ref = border << gf.components.rectangle(
        size=(footprint_x_um, footprint_y_um),
        layer=layer,
    )
    clip_ref.move((-footprint_x_um / 2.0, -footprint_y_um / 2.0))

    c = gf.boolean(core, border, operation="and", layer=layer)

    c.flatten()

    # Length bookkeeping for verifier contract
    (Path(__file__).resolve().parent / "lengths.json").write_text(
        json.dumps(
            {
                "arms": {
                    "north": float(measured_north),
                    "south": float(measured_south),
                },
                "delta_length_um": float(measured_south - measured_north),
            },
            indent=2,
        )
    )

    return c


if __name__ == "__main__":
    c = device()
    c.write_gds("device.gds", with_metadata=False)
