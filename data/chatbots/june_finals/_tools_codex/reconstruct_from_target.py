#!/usr/bin/env python3
"""Independent target-to-GDS reconstruction for HOMI examples.

This intentionally reads only the benchmark input image and footprint at the
example root. It does not inspect any existing run outputs.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image


WHITE_THRESHOLD = 245
EDGE_MARGIN_PX = 0.25
MIN_RUN_WIDTH_PX = 0.9


ATTEMPT_TEMPLATE = '''#!/usr/bin/env python3
"""GDS reconstruction generated from the example target image."""

from __future__ import annotations

import sys
from pathlib import Path

import gdstk

from rects_data import RECTANGLES


LAYER = 1
DATATYPE = 0


def build_library() -> gdstk.Library:
    lib = gdstk.Library(unit=1e-6, precision=1e-9)
    cell = lib.new_cell("codex_reconstruction")
    for xa, y_top, xb, y_bot in RECTANGLES:
        if xb <= xa or y_top <= y_bot:
            continue
        cell.add(gdstk.rectangle((xa, y_bot), (xb, y_top), layer=LAYER, datatype=DATATYPE))
    return lib


def main() -> None:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_suffix(".gds")
    out.parent.mkdir(parents=True, exist_ok=True)
    build_library().write_gds(str(out))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
'''


def load_footprint(example_dir: Path) -> tuple[float, float]:
    data = json.loads((example_dir / "footprint.json").read_text())
    if "footprint_um" in data:
        length, width = data["footprint_um"]
    else:
        length, width = data["length_um"], data["width_um"]
    return float(length), float(width)


def target_image_path(example_dir: Path) -> Path:
    for name in ("device_bw.png", "component.png"):
        candidate = example_dir / name
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"No target image found in {example_dir}")


def calculate_calibration(image_path: Path, footprint_um: tuple[float, float]) -> dict:
    img = Image.open(image_path).convert("L")
    arr = np.array(img)
    mask = arr < WHITE_THRESHOLD
    if not mask.any():
        x0, y0, x1, y1 = 0, 0, img.width, img.height
    else:
        ys, xs = np.where(mask)
        x0, y0, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1

    length_um, width_um = footprint_um
    bbox_w = x1 - x0
    bbox_h = y1 - y0
    return {
        "bbox": [x0, y0, x1, y1],
        "bbox_size_px": [bbox_w, bbox_h],
        "offset": [x0, y0],
        "scale_px_per_um": [bbox_w / length_um, bbox_h / width_um],
        "footprint_um": [length_um, width_um],
        "image_size_px": [img.width, img.height],
        "white_threshold": WHITE_THRESHOLD,
    }


def black_runs(row: np.ndarray) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start = None
    for index, value in enumerate(row):
        if value and start is None:
            start = index
        elif not value and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(row)))
    return runs


def trace_rectangles(
    image_path: Path,
    calibration: dict,
    edge_margin_px: float = EDGE_MARGIN_PX,
    min_run_width_px: float = MIN_RUN_WIDTH_PX,
    x_edge_margin_px: float | None = None,
    y_edge_margin_px: float | None = None,
) -> list[tuple[float, float, float, float]]:
    img = Image.open(image_path).convert("L")
    mask = np.array(img) < calibration["white_threshold"]
    x0, y0, _x1, y1 = calibration["bbox"]
    sx, sy = calibration["scale_px_per_um"]
    _length_um, width_um = calibration["footprint_um"]
    target_x_margin_px = edge_margin_px if x_edge_margin_px is None else x_edge_margin_px
    target_y_margin_px = edge_margin_px if y_edge_margin_px is None else y_edge_margin_px

    rectangles: list[tuple[float, float, float, float]] = []
    for row_index in range(y0, y1):
        for run_start, run_end in black_runs(mask[row_index]):
            run_width_px = run_end - run_start
            x_margin_px = min(target_x_margin_px, max(0.0, (run_width_px - min_run_width_px) / 2))
            xa = (run_start + x_margin_px - x0) / sx
            xb = (run_end - x_margin_px - x0) / sx
            y_top = width_um / 2 - (row_index + target_y_margin_px - y0) / sy
            y_bot = width_um / 2 - (row_index + 1 - target_y_margin_px - y0) / sy
            if xb <= xa or y_top <= y_bot:
                continue
            rectangles.append((round(xa, 7), round(y_top, 7), round(xb, 7), round(y_bot, 7)))
    return rectangles


def write_rectangles(path: Path, rectangles: list[tuple[float, float, float, float]]) -> None:
    with path.open("w") as f:
        f.write("RECTANGLES = [\n")
        for rect in rectangles:
            f.write(f"    {rect!r},\n")
        f.write("]\n")


def run_compare(repo_root: Path, run_dir: Path, target: Path) -> dict:
    compare_dir = run_dir / "compare1"
    compare_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        str(repo_root / "src/jee/core/compare_fixed.py"),
        "--gds",
        str(run_dir / "attempt1.gds"),
        "--layer",
        "1",
        "--datatype",
        "0",
        "--calibration",
        str(run_dir / "component/calibration.json"),
        "--like",
        str(target),
        "--flip-y",
        "--out",
        str(compare_dir / "raster.png"),
        "--compare-to",
        str(target),
        "--diff",
        str(compare_dir / "diff.png"),
        "--overlay",
        str(compare_dir / "overlay.png"),
        "--report",
        str(compare_dir / "metrics.json"),
    ]
    result = subprocess.run(command, cwd=repo_root, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        result.check_returncode()
    return json.loads((compare_dir / "metrics.json").read_text())


def reconstruct(
    example_dir: Path,
    run_name: str,
    repo_root: Path,
    edge_margin_px: float,
    min_run_width_px: float,
    x_edge_margin_px: float | None = None,
    y_edge_margin_px: float | None = None,
) -> dict:
    image_path = target_image_path(example_dir)
    footprint_um = load_footprint(example_dir)
    run_dir = example_dir / "runs" / run_name
    component_dir = run_dir / "component"
    component_dir.mkdir(parents=True, exist_ok=True)

    calibration = calculate_calibration(image_path, footprint_um)
    (component_dir / "calibration.json").write_text(json.dumps(calibration, indent=2))
    (component_dir / "footprint.json").write_text(json.dumps({"footprint_um": list(footprint_um)}, indent=2))
    shutil.copyfile(image_path, component_dir / "component.png")

    rectangles = trace_rectangles(
        image_path,
        calibration,
        edge_margin_px=edge_margin_px,
        min_run_width_px=min_run_width_px,
        x_edge_margin_px=x_edge_margin_px,
        y_edge_margin_px=y_edge_margin_px,
    )
    write_rectangles(run_dir / "rects_data.py", rectangles)
    attempt_path = run_dir / "attempt1.py"
    attempt_path.write_text(ATTEMPT_TEMPLATE)

    result = subprocess.run(
        [sys.executable, str(attempt_path), str(run_dir / "attempt1.gds")],
        cwd=run_dir,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        result.check_returncode()
    metrics = run_compare(repo_root, run_dir, image_path)

    summary = {
        "example": example_dir.name,
        "target": str(image_path.relative_to(repo_root)),
        "run_dir": str(run_dir.relative_to(repo_root)),
        "rectangles": len(rectangles),
        "edge_margin_px": edge_margin_px,
        "min_run_width_px": min_run_width_px,
        "x_edge_margin_px": x_edge_margin_px,
        "y_edge_margin_px": y_edge_margin_px,
        "metrics": metrics,
    }
    (run_dir / "metrics.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("examples", nargs="+", type=Path)
    parser.add_argument("--run-name", default="gpt-5-codex")
    parser.add_argument("--edge-margin-px", type=float, default=EDGE_MARGIN_PX)
    parser.add_argument("--min-run-width-px", type=float, default=MIN_RUN_WIDTH_PX)
    parser.add_argument("--x-edge-margin-px", type=float, default=None)
    parser.add_argument("--y-edge-margin-px", type=float, default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    summaries = []
    for example in args.examples:
        example_dir = example if example.is_absolute() else repo_root / example
        summaries.append(
            reconstruct(
                example_dir,
                args.run_name,
                repo_root,
                args.edge_margin_px,
                args.min_run_width_px,
                x_edge_margin_px=args.x_edge_margin_px,
                y_edge_margin_px=args.y_edge_margin_px,
            )
        )

    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
