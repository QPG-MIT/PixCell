from __future__ import annotations

import json
from pathlib import Path

import gdsfactory as gf
import numpy as np

layer = (1, 0)

# Top-level tunables: keep them simple so JEE-style substitution can edit them.
delta_length = 11.93
center_length_um = 25.0
outer_taper_length_um = 21.7
center_taper_length_um = 25.0
center_body_length_um = 18.0
center_tip_length_um = 7.0
tip_width_um = 0.066
body_width_um = 0.24
center_tip_width_um = 0.072
center_body_width_um = 0.27
outer_start_x_um = 3.07
arm_pitch_um = 0.275
bend_shift_um = 0.45
center_y_um = 0.824
curve_samples = 80


def smoothstep(t: np.ndarray) -> np.ndarray:
    """Piecewise bend profile anchored to the observed outer-arm centerline."""
    xp = np.array([0.0, 0.18, 0.325, 0.65, 1.0])
    fp = np.array([0.0, 0.03, 0.29, 0.97, 1.0])
    return np.interp(t, xp, fp)


def make_bend_path(
    start_x: float,
    end_x: float,
    start_y: float,
    end_y: float,
    *,
    samples: int,
    profile_x: np.ndarray | None = None,
    profile_y: np.ndarray | None = None,
) -> gf.Path:
    xs = np.linspace(start_x, end_x, samples)
    t = (xs - start_x) / max(1e-9, end_x - start_x)
    if profile_x is None or profile_y is None:
        frac = smoothstep(t)
    else:
        frac = np.interp(t, profile_x, profile_y)
    ys = start_y + (end_y - start_y) * frac
    return gf.Path(np.column_stack([xs, ys]))


def make_arm(
    *,
    start_y: float,
    final_y: float,
    start_width: float,
    body_width: float,
    total_length: float,
    taper_length: float,
    samples: int,
) -> tuple[gf.Component, float]:
    c = gf.Component()
    taper = c << gf.components.taper(
        length=taper_length,
        width1=start_width,
        width2=body_width,
        layer=layer,
    )

    bend = make_bend_path(
        taper_length,
        total_length,
        start_y,
        final_y,
        samples=samples,
    ).extrude(width=body_width, layer=layer)
    bend_ref = c << bend
    bend_ref.dmove((0, 0))

    # Route the taper output into the bend start by matching the explicit geometry.
    taper.dmove((0, start_y))
    bend_ref.dmove((0, 0))

    return c, taper_length + make_bend_path(
        taper_length,
        total_length,
        start_y,
        final_y,
        samples=samples,
    ).length()


@gf.cell
def build_device() -> gf.Component:
    c = gf.Component()

    upper_length_um = outer_start_x_um + center_length_um + delta_length
    lower_length_um = outer_start_x_um + center_length_um + 11.93
    top_start_y = center_y_um - arm_pitch_um
    bottom_start_y = center_y_um + arm_pitch_um

    top_final_y = top_start_y - bend_shift_um
    bottom_final_y = bottom_start_y + bend_shift_um

    top_arm = make_bend_path(
        outer_start_x_um + outer_taper_length_um,
        upper_length_um,
        top_start_y,
        top_final_y,
        samples=curve_samples,
        profile_x=np.array([0.0, 0.12, 0.325, 0.65, 1.0]),
        profile_y=np.array([0.0, 0.02, 0.29, 0.97, 1.0]),
    )
    top_path = c << gf.components.taper(
        length=outer_taper_length_um,
        width1=tip_width_um,
        width2=body_width_um,
        layer=layer,
    )
    top_path.dmove((outer_start_x_um, top_start_y))
    top_sweep = c << top_arm.extrude(width=body_width_um, layer=layer)

    bottom_arm = make_bend_path(
        outer_start_x_um + outer_taper_length_um,
        lower_length_um,
        bottom_start_y,
        bottom_final_y,
        samples=curve_samples,
        profile_x=np.array([0.0, 0.12, 0.325, 0.65, 1.0]),
        profile_y=np.array([0.0, 0.01, 0.26, 0.95, 1.0]),
    )
    bottom_path = c << gf.components.taper(
        length=outer_taper_length_um,
        width1=tip_width_um,
        width2=body_width_um,
        layer=layer,
    )
    bottom_path.dmove((outer_start_x_um, bottom_start_y))
    bottom_sweep = c << bottom_arm.extrude(width=body_width_um, layer=layer)

    center_path = c << gf.components.taper(
        length=center_taper_length_um,
        width1=center_body_width_um,
        width2=center_tip_width_um,
        layer=layer,
    )
    center_path.dmove((0, center_y_um))

    # The upper and lower arms are mirror-symmetric; keep the layout explicit.
    top_sweep.dmove((0, 0))
    bottom_sweep.dmove((0, 0))

    lengths = {
        "arms": {
            "upper": float(top_arm.length() + outer_taper_length_um),
            "middle": float(center_taper_length_um),
        },
        "delta_length_um": float((top_arm.length() + outer_taper_length_um) - center_taper_length_um),
    }
    outdir = Path(__file__).resolve().parent
    (outdir / "lengths.json").write_text(json.dumps(lengths, indent=2))

    return c


def main() -> None:
    outdir = Path(__file__).resolve().parent
    c = build_device().copy()
    c.flatten()
    c.write_gds(outdir / "device.gds")


if __name__ == "__main__":
    main()
