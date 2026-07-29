"""Compose the benchmark gallery from agent-loop champions: per target, the
frozen input raster beside the champion program's render at target
calibration, with the difference map in the paper's convention (maroon
overlap, pink candidate-only, black target-only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

from michaelangelo.core.compare_absolute import extract_polygons, render_gds_absolute
from rl.common.evaluator import _prepare_reference
from rl.track_a.benchmark_eval import _fixture_tasks

OVERLAP = (128, 0, 0)
CANDIDATE_ONLY = (255, 146, 153)
TARGET_ONLY = (23, 25, 28)
BACKGROUND = (255, 255, 255)


def _render_champion(code: str, prepared) -> Image.Image | None:
    with tempfile.TemporaryDirectory() as workdir:
        script = Path(workdir) / "program.py"
        script.write_text(code, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=workdir,
            capture_output=True,
            timeout=60,
        )
        gds = Path(workdir) / "device.gds"
        if proc.returncode != 0 or not gds.exists():
            return None
        polygons = extract_polygons(gds)
        if not polygons:
            return None
        raster, _info = render_gds_absolute(polygons, prepared.calibration)
        return raster.convert("L")


def _diff(render: Image.Image, target: Image.Image) -> Image.Image:
    r = np.asarray(render) < 245
    t = np.asarray(target) < 245
    out = np.full((*t.shape, 3), BACKGROUND, dtype=np.uint8)
    out[r & t] = OVERLAP
    out[r & ~t] = CANDIDATE_ONLY
    out[~r & t] = TARGET_ONLY
    return Image.fromarray(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    repo = Path(__file__).resolve().parents[2]
    ap.add_argument("--benchmark-root", default=str(repo / "data" / "benchmark"))
    ap.add_argument("--champions", required=True, help="agent-loop summary JSON")
    ap.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    summary = json.loads(Path(args.champions).read_text(encoding="utf-8"))
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    tasks = {t.sampler.opaque_id: t for t in _fixture_tasks(Path(args.benchmark_root))}
    tiles = []
    manifest = {}
    for name, entry in summary["per_target"].items():
        task = tasks[name]
        prepared = _prepare_reference(task.reference)
        target = prepared.target
        render = _render_champion(entry["champion_code"], prepared)
        (out / f"{name}.program.py").write_text(
            entry["champion_code"], encoding="utf-8"
        )
        target.save(out / f"{name}.target.png")
        if render is not None:
            render.save(out / f"{name}.render.png")
            diff = _diff(render, target)
            diff.save(out / f"{name}.diff.png")
        manifest[name] = {
            "champion_iou": entry["champion_iou"],
            "rendered": render is not None,
        }
        row = [target.convert("RGB")]
        if render is not None:
            row.append(render.convert("RGB"))
            row.append(_diff(render, target))
        height = 220
        scaled = []
        for image in row:
            width = max(1, int(image.width * height / image.height))
            scaled.append(image.resize((width, height)))
        strip = Image.new(
            "RGB",
            (sum(i.width for i in scaled) + 8 * (len(scaled) - 1), height),
            BACKGROUND,
        )
        x = 0
        for image in scaled:
            strip.paste(image, (x, 0))
            x += image.width + 8
        tiles.append((name, entry["champion_iou"], strip))
    width = max(t[2].width for t in tiles) + 160
    total_height = sum(t[2].height + 16 for t in tiles)
    sheet = Image.new("RGB", (width, total_height), BACKGROUND)
    from PIL import ImageDraw

    draw = ImageDraw.Draw(sheet)
    y = 0
    for name, iou, strip in tiles:
        draw.text((4, y + 100), f"{name}\nIoU {iou:.3f}", fill=(23, 25, 28))
        sheet.paste(strip, (150, y))
        y += strip.height + 16
    sheet.save(out / "gallery.png")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    print(f"gallery written to {out}/gallery.png", flush=True)


if __name__ == "__main__":
    main()
