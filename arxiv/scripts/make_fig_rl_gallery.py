"""Render Figure 13 and Table III from hash-locked benchmark evidence.

Each card pairs one frozen target with the highest-IoU executable program from
the fully re-scored best-of-eight draw. Difference maps use Figure 8's
publication convention: maroon for overlap, pink for candidate-only material,
and black for target-only material.

Run from the repository root:
    python arxiv/scripts/make_fig_rl_gallery.py
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle
from PIL import Image


REPO = Path(__file__).resolve().parents[2]
ASSET_DIR = Path(__file__).with_name("fig_rl_assets")
MANIFEST = ASSET_DIR / "manifest.json"
FIGURE_DIR = REPO / "arxiv" / "figures"
TABLE_PATH = REPO / "arxiv" / "table_rl.tex"

INK = "#17191c"
SOFT_INK = "#555a60"
RULE = "#17191c"
OVERLAP = "#800000"
CANDIDATE_ONLY = "#ff9299"
TARGET_ONLY = INK
ASPECT = 0.36

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


def _verified_path(manifest: dict, name: str) -> Path:
    path = ASSET_DIR / name
    expected = manifest["assets"][name]["sha256"]
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(
            f"Hash mismatch for {path}: expected {expected}, got {actual}."
        )
    return path


def _load_data() -> list[dict]:
    manifest = json.loads(MANIFEST.read_text())
    descriptor_path = _verified_path(manifest, "gallery.json")
    data = json.loads(descriptor_path.read_text())["devices"]
    if [row["device"] for row in data] != [f"F{index}" for index in range(1, 9)]:
        raise ValueError("Figure 13 requires ordered targets F1--F8.")
    for row in data:
        row["target_image"] = Image.open(
            _verified_path(manifest, row["target"])
        ).convert("L")
        row["render_image"] = Image.open(
            _verified_path(manifest, row["render"])
        ).convert("L")
        if row["target_image"].size != row["render_image"].size:
            raise ValueError(f"Target/render dimensions differ for {row['device']}.")
    return data


def _mask(image: Image.Image) -> np.ndarray:
    return np.asarray(image) < 128


def _rgb(color: str) -> np.ndarray:
    return np.rint(255 * np.asarray(to_rgb(color))).astype(np.uint8)


def _target_image(image: Image.Image) -> np.ndarray:
    mask = _mask(image)
    output = np.full((*mask.shape, 3), 255, dtype=np.uint8)
    output[mask] = _rgb(INK)
    return output


def _difference_image(target: Image.Image, render: Image.Image) -> np.ndarray:
    target_mask = _mask(target)
    render_mask = _mask(render)
    output = np.full((*target_mask.shape, 3), 255, dtype=np.uint8)
    output[target_mask & render_mask] = _rgb(OVERLAP)
    output[render_mask & ~target_mask] = _rgb(CANDIDATE_ONLY)
    output[target_mask & ~render_mask] = _rgb(TARGET_ONLY)
    return output


def _pad_to_aspect(image: np.ndarray, aspect: float = ASPECT) -> np.ndarray:
    height, width = image.shape[:2]
    if height / width < aspect:
        target_height, target_width = int(round(width * aspect)), width
    else:
        target_height, target_width = height, int(round(height / aspect))
    output = np.full((target_height, target_width, 3), 255, dtype=np.uint8)
    y0 = (target_height - height) // 2
    x0 = (target_width - width) // 2
    output[y0 : y0 + height, x0 : x0 + width] = image
    return output


def _image_axes(
    figure: plt.Figure,
    bounds: tuple[float, float, float, float],
    image: np.ndarray,
) -> None:
    axes = figure.add_axes(bounds)
    axes.imshow(_pad_to_aspect(image), interpolation="antialiased")
    axes.axis("off")


def _draw_card(
    figure: plt.Figure,
    *,
    bounds: tuple[float, float, float, float],
    row: dict,
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
        x + 0.012,
        y + height - 0.028,
        row["device"],
        ha="left",
        va="center",
        fontsize=9.2,
        color=INK,
    )
    figure.text(
        x + width - 0.012,
        y + height - 0.028,
        f"IoU {row['best_iou']:.3f}  ·  "
        f"{row['executable']}/{row['attempts']} executable",
        ha="right",
        va="center",
        fontsize=6.35,
        color=INK,
    )
    figure.add_artist(
        Line2D(
            [x + 0.010, x + width - 0.010],
            [y + height - 0.055, y + height - 0.055],
            transform=figure.transFigure,
            color=RULE,
            linewidth=0.52,
        )
    )
    figure.text(
        x + 0.012,
        y + height - 0.077,
        "Target",
        ha="left",
        va="center",
        fontsize=6.6,
        color=SOFT_INK,
    )
    figure.text(
        x + 0.012,
        y + 0.218,
        "Best of 8",
        ha="left",
        va="center",
        fontsize=6.6,
        color=SOFT_INK,
    )
    _image_axes(
        figure,
        (x + 0.012, y + 0.245, width - 0.024, 0.120),
        _target_image(row["target_image"]),
    )
    _image_axes(
        figure,
        (x + 0.012, y + 0.060, width - 0.024, 0.135),
        _difference_image(row["target_image"], row["render_image"]),
    )


def _render_figure(data: list[dict]) -> None:
    figure = plt.figure(figsize=(7.40, 4.02), facecolor="white")
    card_width = 0.230
    x_positions = (0.020, 0.263, 0.506, 0.749)
    for index, row in enumerate(data):
        block, column = divmod(index, 4)
        y = 0.520 if block == 0 else 0.035
        _draw_card(
            figure,
            bounds=(x_positions[column], y, card_width, 0.445),
            row=row,
        )

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = FIGURE_DIR / "fig_rl_gallery.pdf"
    png_path = FIGURE_DIR / "fig_rl_gallery.png"
    figure.savefig(pdf_path, dpi=600, facecolor="white", bbox_inches=None)
    figure.savefig(png_path, dpi=300, facecolor="white", bbox_inches=None)
    plt.close(figure)
    print(f"wrote {pdf_path}")
    print(f"wrote {png_path}")


def _render_table(data: list[dict]) -> None:
    executable_total = sum(row["executable"] for row in data)
    attempt_total = sum(row["attempts"] for row in data)
    eval_mean = float(np.mean([row["eval_at_1"] for row in data]))
    best_mean = float(np.mean([row["best_iou"] for row in data]))
    rows = [
        (
            f"{row['device']} & "
            f"{row['executable']}/{row['attempts']} & "
            f"{row['eval_at_1']:.3f} & "
            f"{row['best_iou']:.3f} \\\\"
        )
        for row in data
    ]
    table = "\n".join(
        [
            r"\begin{table}[t]",
            r"\caption{\textbf{Fully re-scored final-checkpoint evaluation.} "
            r"Eight attempts per target at temperature $1.0$. Executable counts "
            r"attempts that produced a scored GDS; eval@1 is mean IoU and best@8 "
            r"is the maximum over the eight attempts.}",
            r"\label{tab:rl}",
            r"\begingroup",
            r"\footnotesize",
            r"\setlength{\tabcolsep}{7.0pt}",
            r"\renewcommand{\arraystretch}{1.06}",
            r"\begin{ruledtabular}",
            r"\begin{tabular}{@{}lccc@{}}",
            r"Device & Executable & eval@1 & best@8 \\",
            r"\colrule",
            *rows,
            r"\colrule",
            (
                f"All / mean & {executable_total}/{attempt_total} & "
                f"{eval_mean:.3f} & {best_mean:.3f} \\\\"
            ),
            r"\end{tabular}",
            r"\end{ruledtabular}",
            r"\endgroup",
            r"\end{table}",
            "",
        ]
    )
    TABLE_PATH.write_text(table)
    print(f"wrote {TABLE_PATH}")


def main() -> None:
    data = _load_data()
    _render_figure(data)
    _render_table(data)


if __name__ == "__main__":
    main()
