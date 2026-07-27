"""Render Figure 11 from hash-locked reconstruction and simulation evidence.

Panels A--C present the published reference field, the blind target and
executed reconstruction, and the SOI full-wave realization. The displayed
simulation quantity is positive forward Poynting-flux density at the
z-mid-plane. Panel D compares fabrication-angle sensitivity for a fixed
directional-coupler mask with a mirror-symmetric splitter control.

Run from the repository root:
    python arxiv/scripts/make_fig_sidewall_stacks.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_sidewall_assets")
MANIFEST_PATH = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
GRID = "#e2e4e6"
STACKS = (
    ("soi220", "220 nm SOI", "#315e9f", "o"),
    ("sin400", "400 nm SiN", "#a31f34", "s"),
    ("tfln400", "400 nm TFLN", "#267c5a", "^"),
)
CONTROL_ANGLES = (0.0, 5.0, 15.0, 30.0, 45.0)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": [
            "Iowan Old Style",
            "STIX Two Text",
            "STIXGeneral",
            "Times New Roman",
        ],
        "mathtext.fontset": "stix",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "savefig.facecolor": "white",
        "savefig.bbox": None,
    }
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verified_path(manifest: dict, key: str) -> Path:
    specification = manifest["assets"][key]
    path = ASSET_DIR / specification["asset"]
    actual = _sha256(path)
    expected = specification["sha256"]
    if actual != expected:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected}, got {actual}."
        )
    return path


def _verified_json(manifest: dict, key: str) -> dict:
    return json.loads(_verified_path(manifest, key).read_text())


def _first_crossing(values: dict[float, float]) -> float | None:
    angles = sorted(values)
    for low, high in zip(angles, angles[1:]):
        low_value = values[low]
        high_value = values[high]
        if (low_value - 0.5) * (high_value - 0.5) < 0:
            return low + (high - low) * (0.5 - low_value) / (
                high_value - low_value
            )
    return None


def _load_inputs() -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text())
    contract = manifest["display_contract"]

    published_field = np.asarray(
        Image.open(_verified_path(manifest, "published_field")).convert("RGB")
    )
    target = np.asarray(
        Image.open(_verified_path(manifest, "target")).convert("L")
    )
    reconstruction = np.asarray(
        Image.open(_verified_path(manifest, "reconstruction")).convert("L")
    )
    metrics = _verified_json(manifest, "reconstruction_metrics")

    with np.load(_verified_path(manifest, "forward_power_density")) as field:
        field_x = np.asarray(field["x"], dtype=float)
        field_y = np.asarray(field["y"], dtype=float)
        forward_sx = np.asarray(field["Sx"], dtype=float)

    if target.shape != reconstruction.shape:
        raise ValueError("Target and reconstruction raster shapes differ.")
    target_mask = target < 245
    reconstruction_mask = reconstruction < 245
    intersection = np.logical_and(target_mask, reconstruction_mask).sum()
    union = np.logical_or(target_mask, reconstruction_mask).sum()
    measured_iou = float(intersection / union)
    expected_iou = float(contract["expected_reconstruction_iou"])
    if not np.isclose(measured_iou, expected_iou, atol=1e-12):
        raise ValueError(
            f"Recomputed IoU {measured_iou} does not match {expected_iou}."
        )
    if not np.isclose(float(metrics["IoU"]), measured_iou, atol=1e-12):
        raise ValueError("Archived and recomputed reconstruction IoUs disagree.")

    if forward_sx.shape != (len(field_x), len(field_y)):
        raise ValueError("Forward-flux field dimensions do not match x/y axes.")
    reference_low, reference_high = contract["input_reference_window_um"]
    reference_mask = (field_x >= reference_low) & (field_x <= reference_high)
    reference_peak = float(forward_sx[reference_mask].max())
    if reference_peak <= 0:
        raise ValueError("The upstream forward-flux reference is not positive.")
    display_low, display_high = contract["field_x_range_um"]
    display_mask = (field_x >= display_low) & (field_x <= display_high)
    displayed_flux = np.maximum(forward_sx[display_mask], 0.0) / reference_peak
    if displayed_flux.max() > 1.000001 or displayed_flux.max() < 0.99:
        raise ValueError(
            "Displayed forward flux does not honor the declared input reference."
        )

    ratio = {stack_id: {} for stack_id, _, _, _ in STACKS}
    for cell in _verified_json(manifest, "coupler_stacks")["cells"]:
        if cell["status"] != "success":
            raise ValueError("The coupler stack matrix contains a failed cell.")
        ratio[cell["stack"]][float(cell["angle_deg"])] = float(cell["ratio"])
    for cell in _verified_json(manifest, "coupler_soi_dense")["cells"]:
        if cell["status"] != "success":
            raise ValueError("The dense SOI matrix contains a failed cell.")
        ratio["soi220"][float(cell["angle_deg"])] = float(cell["ratio"])
    for cell in _verified_json(manifest, "coupler_sin")["cells"]:
        if cell["status"] != "success":
            raise ValueError("The SiN matrix contains a failed cell.")
        ratio["sin400"][float(cell["angle_deg"])] = float(cell["ratio"])

    expected_angles = {
        "soi220": {0.0, 2.5, 5.0, 7.5, 10.0, 12.5, 15.0, 30.0, 45.0},
        "sin400": set(CONTROL_ANGLES),
        "tfln400": set(CONTROL_ANGLES),
    }
    if any(set(ratio[stack_id]) != angles for stack_id, angles in expected_angles.items()):
        raise ValueError("Directional-coupler angle coverage is incomplete.")
    sin_crossing = _first_crossing(ratio["sin400"])
    tfln_crossing = _first_crossing(ratio["tfln400"])
    if not np.isclose(
        sin_crossing,
        float(contract["expected_sin_first_crossing_deg"]),
        atol=1e-12,
    ):
        raise ValueError("The SiN 50/50 crossing does not reconcile.")
    if not np.isclose(
        tfln_crossing,
        float(contract["expected_tfln_first_crossing_deg"]),
        atol=1e-12,
    ):
        raise ValueError("The TFLN 50/50 crossing does not reconcile.")

    control_cells = _verified_json(manifest, "splitter_control")["cells"]
    control = {}
    for cell in control_cells:
        if cell["status"] != "success":
            raise ValueError("The symmetric-control matrix contains a failed cell.")
        key = (cell["stack"], float(cell["angle_deg"]))
        control[key] = {
            "balance": float(cell["balance"]),
            "total_T": float(cell["total_T"]),
        }
    expected_control_keys = {
        (stack_id, angle)
        for stack_id, _, _, _ in STACKS
        for angle in CONTROL_ANGLES
    }
    if set(control) != expected_control_keys:
        raise ValueError("Symmetric-control angle coverage is incomplete.")
    max_deviation = max(
        abs(values["balance"] - 0.5) for values in control.values()
    )
    if not np.isclose(
        max_deviation,
        float(contract["expected_control_max_balance_deviation"]),
        atol=1e-12,
    ):
        raise ValueError("The symmetric-control balance range does not reconcile.")

    soi_vertical = control[("soi220", 0.0)]
    balance = soi_vertical["balance"]
    total_transmission = soi_vertical["total_T"]
    if not np.isclose(
        balance,
        float(contract["expected_soi_vertical_balance"]),
        atol=1e-12,
    ):
        raise ValueError("The retained SOI field balance does not reconcile.")
    if not np.isclose(
        total_transmission,
        float(contract["expected_soi_vertical_total_transmission"]),
        atol=1e-12,
    ):
        raise ValueError("The retained SOI transmission does not reconcile.")
    top_power = total_transmission * balance
    bottom_power = total_transmission * (1.0 - balance)

    negative_magnitude = float(np.abs(forward_sx[forward_sx < 0]).sum())
    absolute_magnitude = float(np.abs(forward_sx).sum())

    return {
        "published_field": published_field,
        "target": target,
        "reconstruction": reconstruction,
        "target_mask": target_mask,
        "reconstruction_mask": reconstruction_mask,
        "iou": measured_iou,
        "field_x": field_x[display_mask],
        "field_y": field_y,
        "forward_flux": displayed_flux,
        "field_reference": (float(reference_low), float(reference_high)),
        "negative_flux_fraction": negative_magnitude / absolute_magnitude,
        "ratio": ratio,
        "control": control,
        "max_deviation": max_deviation,
        "balance": balance,
        "total_transmission": total_transmission,
        "top_power": top_power,
        "bottom_power": bottom_power,
    }


def _shared_vertical_crop(target_mask: np.ndarray, reconstruction_mask: np.ndarray) -> slice:
    combined = np.logical_or(target_mask, reconstruction_mask)
    rows = np.flatnonzero(combined.any(axis=1))
    if not len(rows):
        raise ValueError("The reconstruction pair contains no foreground.")
    padding = 18
    low = max(0, int(rows[0]) - padding)
    high = min(combined.shape[0], int(rows[-1]) + padding + 1)
    return slice(low, high)


def _tint_mask(mask: np.ndarray, color: str) -> np.ndarray:
    rgb = np.asarray(matplotlib.colors.to_rgb(color))
    image = np.ones((*mask.shape, 3), dtype=float)
    image[mask] = rgb
    return image


def _panel_heading(
    figure: plt.Figure,
    *,
    x: float,
    letter: str,
    title: str,
    y: float,
    rule_y: float,
    rule_end: float,
) -> None:
    figure.text(
        x,
        y,
        letter,
        ha="left",
        va="center",
        fontsize=10.5,
        color=INK,
    )
    figure.text(
        x + 0.035,
        y,
        title,
        ha="left",
        va="center",
        fontsize=10.5,
        color=INK,
    )
    figure.add_artist(
        Line2D(
            [x, rule_end],
            [rule_y, rule_y],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.68,
        )
    )


def _style_plot(axes: plt.Axes) -> None:
    axes.spines["top"].set_visible(False)
    axes.spines["right"].set_visible(False)
    axes.spines["left"].set_linewidth(0.68)
    axes.spines["bottom"].set_linewidth(0.68)
    axes.tick_params(axis="both", labelsize=7.2, width=0.6, length=3.0, pad=2.5)
    axes.grid(axis="y", color=GRID, linewidth=0.52, zorder=0)
    axes.set_axisbelow(True)


def _plain_image_axis(
    axes: plt.Axes,
    image: np.ndarray,
    *,
    title: str | None = None,
) -> None:
    axes.imshow(image, interpolation="antialiased", aspect="auto")
    axes.axis("off")
    if title:
        axes.set_title(
            title,
            fontsize=7.7,
            color=INK,
            pad=2.5,
            fontweight="normal",
        )


def _boxed_image(
    figure: plt.Figure,
    *,
    bounds: tuple[float, float, float, float],
    image: np.ndarray,
    title: str,
) -> None:
    x, y, width, height = bounds
    figure.add_artist(
        Rectangle(
            (x, y),
            width,
            height,
            transform=figure.transFigure,
            facecolor="none",
            edgecolor=INK,
            linewidth=0.68,
            zorder=0,
        )
    )
    figure.text(
        x + 0.010,
        y + height - 0.020,
        title,
        ha="left",
        va="center",
        fontsize=7.7,
        color=INK,
    )
    image_axes = figure.add_axes(
        (x + 0.010, y + 0.015, width - 0.020, height - 0.050)
    )
    image_axes.imshow(image, interpolation="antialiased")
    image_axes.axis("off")


def _render(data: dict) -> None:
    figure = plt.figure(figsize=(7.40, 4.58), facecolor="white")

    _panel_heading(
        figure,
        x=0.020,
        letter="A",
        title="Published reference field",
        y=0.965,
        rule_y=0.925,
        rule_end=0.325,
    )
    _panel_heading(
        figure,
        x=0.345,
        letter="B",
        title="Agent reconstruction",
        y=0.965,
        rule_y=0.925,
        rule_end=0.650,
    )
    _panel_heading(
        figure,
        x=0.670,
        letter="C",
        title="Full-wave realization",
        y=0.965,
        rule_y=0.925,
        rule_end=0.980,
    )
    _panel_heading(
        figure,
        x=0.020,
        letter="D",
        title="Fabrication sensitivity",
        y=0.515,
        rule_y=0.478,
        rule_end=0.980,
    )

    source_axes = figure.add_axes((0.025, 0.640, 0.290, 0.200))
    field_axes = figure.add_axes((0.680, 0.640, 0.250, 0.200))
    colorbar_axes = figure.add_axes((0.940, 0.640, 0.010, 0.200))

    _plain_image_axis(source_axes, data["published_field"])
    vertical_crop = _shared_vertical_crop(
        data["target_mask"],
        data["reconstruction_mask"],
    )
    _boxed_image(
        figure,
        bounds=(0.355, 0.742, 0.250, 0.135),
        image=_tint_mask(data["target_mask"][vertical_crop], INK),
        title="Target",
    )
    _boxed_image(
        figure,
        bounds=(0.355, 0.575, 0.250, 0.135),
        image=_tint_mask(data["reconstruction_mask"][vertical_crop], STACKS[0][2]),
        title=f"Reconstruction  ·  IoU {data['iou']:.3f}",
    )

    field_image = field_axes.imshow(
        data["forward_flux"].T,
        origin="lower",
        aspect="auto",
        cmap="jet",
        vmin=0.0,
        vmax=1.0,
        extent=[
            data["field_x"].min(),
            data["field_x"].max(),
            data["field_y"].min(),
            data["field_y"].max(),
        ],
        interpolation="bilinear",
    )
    field_axes.set_xlabel(r"$x$ ($\mu$m)", fontsize=7.4, labelpad=2.0)
    field_axes.set_ylabel(r"$y$ ($\mu$m)", fontsize=7.4, labelpad=2.0)
    field_axes.tick_params(
        axis="both",
        labelsize=6.5,
        width=0.55,
        length=2.5,
        pad=2.0,
    )
    for spine in field_axes.spines.values():
        spine.set_linewidth(0.65)

    colorbar = figure.colorbar(
        field_image,
        cax=colorbar_axes,
        ticks=(0.0, 0.5, 1.0),
    )
    colorbar.ax.tick_params(labelsize=6.3, length=2.5, width=0.55, pad=1.5)
    colorbar.set_label(
        "Normalized forward flux",
        fontsize=6.5,
        labelpad=1.5,
    )
    colorbar.outline.set_linewidth(0.55)

    coupler_axes = figure.add_axes((0.075, 0.090, 0.520, 0.300))
    balance_axes = figure.add_axes((0.680, 0.250, 0.290, 0.140))
    transmission_axes = figure.add_axes((0.680, 0.090, 0.290, 0.120))

    coupler_axes.axhline(
        0.5,
        color=SOFT_INK,
        linewidth=0.72,
        linestyle=(0, (3.5, 2.5)),
        zorder=1,
    )
    coupler_axes.text(
        44.5,
        0.525,
        "50/50",
        fontsize=6.8,
        color=SOFT_INK,
        ha="right",
        va="bottom",
    )
    for stack_id, _, color, marker in STACKS:
        angles = sorted(data["ratio"][stack_id])
        values = [data["ratio"][stack_id][angle] for angle in angles]
        coupler_axes.plot(
            angles,
            values,
            color=color,
            marker=marker,
            linewidth=1.25,
            markersize=3.5,
            markeredgewidth=0.55,
            zorder=3,
        )
    coupler_axes.set_xlim(-0.8, 45.8)
    coupler_axes.set_ylim(0.0, 1.04)
    coupler_axes.set_xticks((0, 5, 15, 30, 45))
    coupler_axes.set_yticks((0.0, 0.25, 0.5, 0.75, 1.0))
    coupler_axes.set_xlabel(
        "Sidewall angle from vertical (deg)",
        fontsize=8.0,
        labelpad=3.5,
    )
    coupler_axes.set_ylabel("Coupling ratio", fontsize=8.0, labelpad=3.5)
    coupler_axes.set_title(
        "Fixed directional-coupler mask",
        fontsize=8.4,
        pad=5.0,
        fontweight="normal",
    )
    _style_plot(coupler_axes)

    balance_axes.axhline(
        0.5,
        color=SOFT_INK,
        linewidth=0.68,
        linestyle=(0, (3.5, 2.5)),
        zorder=1,
    )
    for stack_id, _, color, marker in STACKS:
        balances = [
            data["control"][(stack_id, angle)]["balance"]
            for angle in CONTROL_ANGLES
        ]
        balance_axes.plot(
            CONTROL_ANGLES,
            balances,
            color=color,
            marker=marker,
            linewidth=1.10,
            markersize=3.0,
            markeredgewidth=0.50,
            zorder=3,
        )
    balance_axes.set_xlim(-0.8, 45.8)
    balance_axes.set_ylim(0.49, 0.51)
    balance_axes.set_xticks((0, 5, 15, 30, 45))
    balance_axes.set_yticks((0.49, 0.50, 0.51))
    balance_axes.tick_params(labelbottom=False)
    balance_axes.set_ylabel(r"Split balance $b$", fontsize=7.7, labelpad=3.0)
    balance_axes.set_title(
        "Symmetric splitter control",
        fontsize=8.4,
        pad=5.0,
        fontweight="normal",
    )
    _style_plot(balance_axes)

    for stack_id, _, color, marker in STACKS:
        transmissions = [
            data["control"][(stack_id, angle)]["total_T"]
            for angle in CONTROL_ANGLES
        ]
        transmission_axes.plot(
            CONTROL_ANGLES,
            transmissions,
            color=color,
            marker=marker,
            linewidth=1.10,
            markersize=3.0,
            markeredgewidth=0.50,
            zorder=3,
        )
    transmission_axes.set_xlim(-0.8, 45.8)
    transmission_axes.set_ylim(0.4, 1.02)
    transmission_axes.set_xticks((0, 5, 15, 30, 45))
    transmission_axes.set_yticks((0.4, 0.6, 0.8, 1.0))
    transmission_axes.set_xlabel("Sidewall angle (deg)", fontsize=7.7, labelpad=3.0)
    transmission_axes.set_ylabel("Transmission", fontsize=7.7, labelpad=3.0)
    _style_plot(transmission_axes)

    handles = [
        Line2D(
            [],
            [],
            color=color,
            marker=marker,
            linewidth=1.15,
            markersize=3.5,
            label=label,
        )
        for _, label, color, marker in STACKS
    ]
    legend = figure.legend(
        handles=handles,
        loc="center right",
        bbox_to_anchor=(0.972, 0.440),
        ncol=3,
        frameon=False,
        fontsize=7.7,
        handlelength=1.5,
        handletextpad=0.45,
        columnspacing=1.2,
        borderaxespad=0.0,
    )
    for text in legend.get_texts():
        text.set_color(INK)

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FIGURE_DIR / "fig_sidewall_stacks.pdf"
    png_path = FIGURE_DIR / "fig_sidewall_stacks.png"
    figure.savefig(pdf_path, dpi=600, facecolor="white", bbox_inches=None)
    figure.savefig(png_path, dpi=300, facecolor="white", bbox_inches=None)
    plt.close(figure)

    print(
        f"F1 IoU={data['iou']:.6f}; "
        f"Ptop={data['top_power']:.6f}; "
        f"Pbot={data['bottom_power']:.6f}; "
        f"T={data['total_transmission']:.6f}; "
        f"balance={data['balance']:.6f}"
    )
    print(
        "Negative forward-flux magnitude clipped for display: "
        f"{100 * data['negative_flux_fraction']:.3f}% of total |Sx|."
    )
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


def main() -> None:
    _render(_load_inputs())


if __name__ == "__main__":
    main()
