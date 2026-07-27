from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np


LAYER = (1, 0)

# Function/topology knobs, in um.
footprint_length = 40.0
footprint_width = 1.7
input_taper_length = 25.05
input_width = 0.27
input_tip_width = 0.07
input_center_y = 0.835

branch_tip_x = 3.07
branch_taper_length = 22.8
branch_tip_width = 0.066
branch_width = 0.244
upper_branch_y = 0.57
lower_branch_y = 1.112
split_gap = 0.286

s_bend_start_x = 25.05
s_bend_length = 10.9
s_bend_offset = 0.45
upper_output_y = 0.12
lower_output_y = 1.58
output_length = 4.05

# Verification/spec knob: lengthens one output arm by real material length.
delta_length = 0.0

# Raster calibration alignment knobs from the allowed bitmap.
x_alignment_shift = 0.0
y_alignment_shift = 0.0

gds_filename = "device.gds"


UPPER_PROFILE = [
    (3.0693, 0.5699, 0.0651), (4.3069, 0.5699, 0.0782),
    (5.5198, 0.5699, 0.0847), (6.7574, 0.5699, 0.0977),
    (7.9950, 0.5699, 0.1042), (9.2079, 0.5716, 0.1140),
    (10.4455, 0.5699, 0.1238), (11.6832, 0.5716, 0.1335),
    (12.9208, 0.5716, 0.1400), (14.1337, 0.5699, 0.1498),
    (15.3713, 0.5716, 0.1596), (16.6089, 0.5716, 0.1726),
    (17.8218, 0.5716, 0.1791), (19.0594, 0.5732, 0.1889),
    (20.2970, 0.5716, 0.1987), (21.5347, 0.5716, 0.2052),
    (22.7475, 0.5716, 0.2182), (23.9851, 0.5716, 0.2247),
    (25.2228, 0.5716, 0.2377), (26.4356, 0.5699, 0.2410),
    (27.6733, 0.5471, 0.2410), (28.9109, 0.4901, 0.2443),
    (30.1238, 0.4103, 0.2475), (31.3614, 0.3094, 0.2475),
    (32.5990, 0.2133, 0.2443), (33.8119, 0.1563, 0.2410),
    (35.0495, 0.1303, 0.2410), (36.2871, 0.1221, 0.2377),
    (37.5248, 0.1205, 0.2410), (38.7376, 0.1205, 0.2410),
    (39.9752, 0.1205, 0.2410),
]

CENTER_PROFILE = [
    (0.0000, 0.8353, 0.2703), (0.8416, 0.8353, 0.2703),
    (1.6584, 0.8353, 0.2703), (2.5000, 0.8353, 0.2703),
    (3.3416, 0.8353, 0.2638), (4.1584, 0.8353, 0.2573),
    (5.0000, 0.8353, 0.2508), (5.8416, 0.8353, 0.2443),
    (6.6832, 0.8353, 0.2377), (7.5000, 0.8370, 0.2280),
    (8.3416, 0.8353, 0.2182), (9.1832, 0.8353, 0.2117),
    (10.0000, 0.8353, 0.2052), (10.8416, 0.8370, 0.1954),
    (11.6832, 0.8370, 0.1889), (12.5248, 0.8370, 0.1824),
    (13.3416, 0.8370, 0.1759), (14.1832, 0.8353, 0.1661),
    (15.0248, 0.8353, 0.1596), (15.8416, 0.8353, 0.1531),
    (16.6832, 0.8353, 0.1466), (17.5248, 0.8353, 0.1400),
    (18.3416, 0.8353, 0.1335), (19.1832, 0.8353, 0.1205),
    (20.0248, 0.8353, 0.1140), (20.8663, 0.8353, 0.1075),
    (21.6832, 0.8353, 0.1010), (22.5248, 0.8353, 0.0944),
    (23.3663, 0.8353, 0.0879), (24.1832, 0.8370, 0.0782),
    (25.0248, 0.8353, 0.0684),
]

LOWER_PROFILE = [
    (3.0693, 1.1122, 0.0684), (4.3069, 1.1122, 0.0749),
    (5.5198, 1.1122, 0.0879), (6.7574, 1.1105, 0.0977),
    (7.9950, 1.1105, 0.1042), (9.2079, 1.1105, 0.1172),
    (10.4455, 1.1089, 0.1270), (11.6832, 1.1089, 0.1335),
    (12.9208, 1.1089, 0.1466), (14.1337, 1.1073, 0.1563),
    (15.3713, 1.1073, 0.1628), (16.6089, 1.1073, 0.1759),
    (17.8218, 1.1057, 0.1856), (19.0594, 1.1057, 0.1921),
    (20.2970, 1.1040, 0.2019), (21.5347, 1.1024, 0.2117),
    (22.7475, 1.1040, 0.2215), (23.9851, 1.1024, 0.2312),
    (25.2228, 1.1008, 0.2410), (26.4356, 1.1057, 0.2443),
    (27.6733, 1.1268, 0.2475), (28.9109, 1.1806, 0.2508),
    (30.1238, 1.2685, 0.2573), (31.3614, 1.3727, 0.2573),
    (32.5990, 1.4688, 0.2540), (33.8119, 1.5307, 0.2475),
    (35.0495, 1.5648, 0.2443), (36.2871, 1.5795, 0.2410),
    (37.5248, 1.5795, 0.2410), (38.7376, 1.5795, 0.2410),
    (39.9752, 1.5795, 0.2410),
]


def _profile_with_lower_extension(profile: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    if delta_length <= 0:
        return profile
    x, y, width = profile[-1]
    return [*profile, (x + delta_length, y, width)]


def _aligned_profile(profile: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    return [
        (x + x_alignment_shift, footprint_width - y + y_alignment_shift, width)
        for x, y, width in profile
    ]


def _profile_length(profile: list[tuple[float, float, float]]) -> float:
    total = 0.0
    for (x0, y0, _), (x1, y1, _) in zip(profile, profile[1:]):
        total += float(np.hypot(x1 - x0, y1 - y0))
    return total


def _snap_width(width: float) -> float:
    return max(0.002, round(width / 0.002) * 0.002)


def _extrude_profile(profile: list[tuple[float, float, float]], prefix: str) -> gf.Component:
    c = gf.Component(prefix)
    for i, ((x0, y0, w0), (x1, y1, w1)) in enumerate(zip(profile, profile[1:])):
        p = gf.Path([[x0, y0], [x1, y1]])
        xs0 = gf.cross_section.strip(width=_snap_width(w0), layer=LAYER)
        xs1 = gf.cross_section.strip(width=_snap_width(w1), layer=LAYER)
        transition = gf.path.transition(xs0, xs1, width_type="linear")
        segment = gf.Component(f"{prefix}_segment_{i:02d}")
        segment << gf.path.extrude_transition(p, transition)
        c << segment
    return c


def build_component() -> gf.Component:
    c = gf.Component("recreated_phase_a_splitter")
    c << _extrude_profile(_aligned_profile(CENTER_PROFILE), "input_center_taper")
    c << _extrude_profile(_aligned_profile(UPPER_PROFILE), "upper_branch")
    c << _extrude_profile(
        _aligned_profile(_profile_with_lower_extension(LOWER_PROFILE)),
        "lower_branch",
    )
    return c


def write_lengths(component: gf.Component) -> None:
    upper_length = _profile_length(UPPER_PROFILE)
    lower_length = _profile_length(_profile_with_lower_extension(LOWER_PROFILE))
    payload = {
        "arms": {
            "upper": upper_length,
            "lower": lower_length,
        },
        "delta_length_um": abs(lower_length - upper_length),
        "bbox_um": list(component.bbox_np().flatten()),
    }
    Path("lengths.json").write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    component = build_component()
    component.write_gds(gds_filename)
    write_lengths(component)
