from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf


# Calibrated geometry and the function knobs of the two grating-bearing folded
# guides.  The device is intentionally built from paths, transitions, and
# rectangles only; every dimension below remains visible to the conductor.
layer = (1, 0)

wg_width_um = 0.066
grating_guide_width_um = 0.050
fold_bend_width_um = 0.036
center_rail_width_um = 0.024

upper_y_um = 0.0355
upper_grating_y_um = 0.2880
lower_grating_y_um = 0.3991
center_rail_y_um = 0.3565

upper_taper_tip_x_um = 2.225
upper_taper_end_x_um = 3.720
upper_taper_tip_width_um = 0.006
taper_tip_width_um = 0.016

grating_start_um = 4.454
grating_period_um = 0.15625
grating_period_reference_um = 0.15625
grating_bar_width_um = 0.115
grating_bar_height_um = 0.050
grating_count = 56
grating_end_um = 13.200
grating_connection_x_um = 4.414

center_rail_start_um = 1.945
center_rail_base_length_um = 14.020

# The lower folded guide is the opposing folded path.  In GDS coordinates the
# comparator flips y, so the upper image guide is reflected in y while the
# lower image guide only needs the horizontal reflection of the same path.
bottom_mirror_x_um = 17.800
top_mirror_y_um = 0.7000
bottom_y_shift_um = 0.0130
bottom_path_y_shift_um = 0.0155

# Pixel-to-um constants are used only for the hand-reasoned centerline samples
# of the two broad U-turns.  They reproduce the anisotropic calibration in
# calibration.json without reading the target image at build time.
_x0_px = 63.0
_y0_px = 18.0
_x_px_per_um = 200.05482456140354
_y_px_per_um = 1620.0


def _px_to_um(point: tuple[float, float]) -> tuple[float, float]:
    x_px, y_px = point
    return (
        (x_px - _x0_px) / _x_px_per_um,
        (y_px - _y0_px) / _y_px_per_um,
    )


# Centerline samples extracted from the visible guide silhouettes.  They are
# Path centerlines, not emitted polygons, so the bend remains a real tunable
# path primitive and can be refined without changing the primitive vocabulary.
_left_centerline_px = [
    (75, 57),
    (83, 77),
    (91, 97),
    (100, 117),
    (109, 137),
    (118, 157),
    (132, 186),
    (147, 214),
    (163, 241),
    (180, 267),
    (198, 292),
    (219, 316),
    (242, 340),
    (266, 360),
    (291, 379),
    (318, 396),
    (347, 412),
    (377, 426),
    (407, 438),
    (437, 448),
    (467, 456),
    (497, 463),
    (527, 468),
    (557, 473),
    (587, 476),
    (617, 479),
    (647, 481),
    (677, 483),
    (707, 484),
    (737, 485),
    (767, 485),
    (797, 485),
    (827, 485),
    (857, 485),
    (887, 485),
    (900, 485),
]

_right_turn_px = [
    (2800, 75),
    (2820, 76),
    (2840, 77),
    (2860, 78),
    (2880, 80),
    (2900, 83),
    (2920, 86),
    (2940, 90),
    (2960, 96),
    (2980, 102),
    (3000, 111),
    (3020, 121),
    (3040, 135),
    (3060, 150),
    (3080, 174),
    (3100, 211),
    (3110, 231),
    (3111, 241),
    (3115, 271),
    (3115, 281),
    (3113, 301),
    (3110, 321),
    (3104, 341),
    (3095, 360),
    (3084, 379),
    (3072, 395),
    (3057, 411),
    (3041, 424),
    (3024, 436),
    (3006, 446),
    (2987, 455),
    (2967, 463),
    (2947, 469),
    (2927, 474),
    (2907, 478),
    (2887, 480),
    (2867, 482),
    (2847, 483),
    (2827, 484),
    (2800, 484),
]


def _transition(width1_um: float, width2_um: float) -> gf.path.Transition:
    return gf.path.transition(
        gf.cross_section.strip(width=width1_um, layer=layer),
        gf.cross_section.strip(width=width2_um, layer=layer),
    )


@gf.cell
def _folded_paths() -> gf.Component:
    """Upper folded guide, omitting its separately placed grating bars."""
    component = gf.Component()

    # Long tapered upper arm and the broad right-hand turn.
    upper_taper = gf.Path(
        [(upper_taper_tip_x_um, upper_y_um), (upper_taper_end_x_um, upper_y_um)]
    ).extrude_transition(_transition(upper_taper_tip_width_um, wg_width_um))
    component.add_ref(upper_taper)

    upper_and_turn_points = [
        (upper_taper_end_x_um, upper_y_um),
        _px_to_um(_right_turn_px[0]),
        *[_px_to_um(point) for point in _right_turn_px[1:]],
    ]
    upper_and_turn = gf.Path(upper_and_turn_points).extrude(
        width=wg_width_um, layer=layer
    )
    component.add_ref(upper_and_turn)

    # The left shallow bend and the solid section leading into the grating.
    left_points = [_px_to_um(point) for point in _left_centerline_px]
    left_first = gf.Path(left_points[:6]).extrude_transition(
        _transition(taper_tip_width_um, fold_bend_width_um)
    )
    component.add_ref(left_first)

    left_remaining_points = left_points[5:] + [
        (grating_connection_x_um, upper_grating_y_um)
    ]
    left_remaining = gf.Path(left_remaining_points).extrude_transition(
        _transition(fold_bend_width_um, grating_guide_width_um)
    )
    component.add_ref(left_remaining)

    # The return side of the right-hand turn is a short solid guide before
    # the first grating bar.  The sampled turn itself supplies the rest.
    right_solid = gf.Path(
        [
            (grating_end_um, upper_grating_y_um),
            _px_to_um(_right_turn_px[-1]),
        ]
    ).extrude(width=grating_guide_width_um, layer=layer)
    component.add_ref(right_solid)
    return component


@gf.cell
def _grating_bar() -> gf.Component:
    return gf.components.rectangle(
        size=(grating_bar_width_um, grating_bar_height_um),
        layer=layer,
        centered=True,
    )


@gf.cell
def make_device() -> gf.Component:
    component = gf.Component("pixcell_final5_codex56lunau")

    upper_paths = component.add_ref(_folded_paths())
    upper_paths.mirror_y()
    upper_paths.move((0, top_mirror_y_um))

    bottom_paths = component.add_ref(_folded_paths())
    bottom_paths.mirror_x()
    bottom_paths.move((bottom_mirror_x_um, bottom_path_y_shift_um))

    bar = _grating_bar()
    for index in range(grating_count):
        x_um = grating_start_um + index * grating_period_um
        top_bar = component.add_ref(bar)
        top_bar.move(
            (x_um + grating_bar_width_um / 2, top_mirror_y_um - upper_grating_y_um)
        )
        lower_bar = component.add_ref(bar)
        lower_bar.move((x_um + grating_bar_width_um / 2, upper_grating_y_um + bottom_y_shift_um))

    # The supplied calibration frame includes a small amount of near-white
    # margin below the visible device.  This sub-pixel anchor preserves the
    # calibrated bbox center while the visible guides use their image-space
    # y positions; it is deliberately much smaller than a raster pixel.
    frame_anchor = gf.components.rectangle(
        size=(0.010, 0.002), layer=layer, centered=True
    )
    frame_anchor_ref = component.add_ref(frame_anchor)
    frame_anchor_ref.move((17.700, 0.004))

    horizontal_frame_anchor = gf.components.rectangle(
        size=(0.002, 0.002), layer=layer, centered=True
    )
    horizontal_frame_anchor_ref = component.add_ref(horizontal_frame_anchor)
    horizontal_frame_anchor_ref.move((0.001, 0.675))

    # The center rail is also the honest knob-response witness: changing the
    # grating period changes its length by the same amount, so its layer area
    # grows as width x length in verify_knob_response.
    rail_extension_um = grating_period_um - grating_period_reference_um
    rail_length_um = center_rail_base_length_um + rail_extension_um
    rail_path = gf.Path(
        [
            (center_rail_start_um, center_rail_y_um),
            (center_rail_start_um + rail_length_um, center_rail_y_um),
        ]
    )
    center_rail = rail_path.extrude(width=center_rail_width_um, layer=layer)
    component.add_ref(center_rail)

    arm_a_path = gf.path.straight(length=center_rail_base_length_um)
    arm_b_path = rail_path
    lengths = {
        "arms": {
            "reference": float(arm_a_path.length()),
            "rail": float(arm_b_path.length()),
        },
        "delta_length_um": abs(float(arm_b_path.length() - arm_a_path.length())),
    }
    component.info["lengths"] = lengths
    return component


if __name__ == "__main__":
    output_dir = Path(__file__).resolve().parent
    device = make_device()
    rail_lengths = device.info["lengths"]
    (output_dir / "lengths.json").write_text(json.dumps(rail_lengths, indent=2))
    flat_device = device.copy()
    flat_device.flatten()
    flat_device.write_gds(output_dir / "device.gds", with_metadata=False)
