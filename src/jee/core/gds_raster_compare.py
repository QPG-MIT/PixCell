"""
Rasterize a GDS layout to match a reference image and compute comparison metrics.

Implements the pipeline described in howcompare.md:
- Reads GDS, extracts polygons on a (layer, datatype), including references.
- Gets the target image size and non-white bbox from a reference image.
- Preserves aspect ratio, centers into that bbox, and optionally flips Y.
- Supersamples, rasterizes polygons to a binary mask, then downsamples.
- Thresholds the reference to a binary mask and computes metrics.
- Produces raster, diff, overlay images, and a metrics JSON.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw

try:
    import gdstk  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("gdstk is required. Install with: pip install gdstk") from e


@dataclass
class ImageBBox:
    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return max(0, self.x1 - self.x0)

    @property
    def height(self) -> int:
        return max(0, self.y1 - self.y0)


def load_top_cell(gds_path: Path) -> "gdstk.Cell":
    lib = gdstk.read_gds(str(gds_path))
    top = lib.top_level()
    if not top:
        # fallback: any cell in library
        cells = list(lib.cells.values())
        if not cells:
            raise ValueError("No cells found in GDS library")
        return cells[-1]

    # Skip $$$CONTEXT_INFO$$$ (gdsfactory metadata cell)
    for cell in top:
        if cell.name != "$$$CONTEXT_INFO$$$":
            return cell

    # If only context info exists, return it anyway
    return top[0]


def extract_polygons(cell: "gdstk.Cell", layer: int, datatype: int) -> List[np.ndarray]:
    """Return polygon point arrays filtered by (layer, datatype).

    Compatible with gdstk 0.9.x which lacks by_spec keyword on get_polygons.
    We copy and flatten the cell to bring referenced geometry into the cell,
    then iterate over Polygon objects and filter by layer/datatype.
    """
    # Defensive copy so we don't mutate the user's library
    try:
        tmp = cell.copy("__TMP_FLAT__")
    except (TypeError, RuntimeError):
        # Fallback: create new cell and add a reference
        lib = gdstk.Library()
        tmp = lib.new_cell("__TMP_FLAT__")
        tmp.add(gdstk.Reference(cell))
    # Flatten recursively if available
    try:
        tmp.flatten(True)
    except TypeError:
        try:
            tmp.flatten()
        except (TypeError, RuntimeError):
            pass
    result: List[np.ndarray] = []
    # tmp.polygons returns Polygon objects (direct only after flatten)
    for poly in getattr(tmp, "polygons", []) or []:
        try:
            if int(poly.layer) == int(layer) and int(poly.datatype) == int(datatype):
                result.append(np.asarray(poly.points, dtype=float))
        except (AttributeError, TypeError, ValueError):
            # As a fallback, accept all polygons if metadata missing
            result.append(np.asarray(poly.points, dtype=float))
    if not result:
        # Last resort: get all polygons as raw points list
        try:
            pts_list = tmp.get_polygons(True)
            result = [np.asarray(p, dtype=float) for p in pts_list]
        except (TypeError, RuntimeError, AttributeError):
            pass
    return result


def polygons_bbox(polygons: Sequence[np.ndarray]) -> Tuple[float, float, float, float]:
    if not polygons:
        return 0.0, 0.0, 1.0, 1.0
    xs = np.concatenate([p[:, 0] for p in polygons])
    ys = np.concatenate([p[:, 1] for p in polygons])
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def nonwhite_bbox(img: Image.Image, white_threshold: int = 245) -> ImageBBox:
    g = img.convert("L")
    a = np.array(g)
    mask = a < white_threshold
    if not mask.any():
        # full image
        w, h = img.size
        return ImageBBox(0, 0, w, h)
    ys, xs = np.where(mask)
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    return ImageBBox(x0, y0, x1, y1)


def map_polygons_to_image(
    polygons: Sequence[np.ndarray],
    layout_bbox: Tuple[float, float, float, float],
    dest_bbox: ImageBBox,
    out_size: Tuple[int, int],
    preserve_aspect: bool,
    flip_y: bool,
    supersample: int,
) -> List[List[Tuple[int, int]]]:
    lx0, ly0, lx1, ly1 = layout_bbox
    lw = max(1e-9, lx1 - lx0)
    lh = max(1e-9, ly1 - ly0)
    W, H = out_size
    dx, dy = dest_bbox.x0, dest_bbox.y0
    dw, dh = dest_bbox.width, dest_bbox.height

    if preserve_aspect:
        s = min(dw / lw, dh / lh)
        pad_x = 0.5 * (dw - s * lw)
        pad_y = 0.5 * (dh - s * lh)
    else:
        sx = dw / lw
        sy = dh / lh
        s = None
        pad_x = pad_y = 0.0

    mapped: List[List[Tuple[int, int]]] = []
    for poly in polygons:
        if poly.size == 0:
            continue
        pts = []
        for x, y in poly:
            if preserve_aspect:
                x1 = (x - lx0) * s + dx + pad_x
                y1 = (y - ly0) * s
                if flip_y:
                    y1 = dy + dh - pad_y - y1
                else:
                    y1 = dy + pad_y + y1
            else:
                x1 = (x - lx0) * sx + dx
                y1 = (y - ly0) * sy
                if flip_y:
                    y1 = dy + dh - y1
                else:
                    y1 = dy + y1
            pts.append((int(round(x1 * supersample)), int(round(y1 * supersample))))
        mapped.append(pts)
    return mapped


def rasterize(polygons_px: Sequence[Sequence[Tuple[int, int]]], size: Tuple[int, int]) -> Image.Image:
    Wss, Hss = size
    img = Image.new("L", (Wss, Hss), 255)
    drw = ImageDraw.Draw(img)
    for poly in polygons_px:
        if len(poly) >= 3:
            drw.polygon(poly, fill=0)
    return img


def binarize(img: Image.Image, white_threshold: int) -> np.ndarray:
    a = np.array(img.convert("L"))
    return (a < white_threshold).astype(np.uint8)  # 1 = black/foreground


def compute_metrics(mask_g: np.ndarray, mask_t: np.ndarray) -> dict:
    g = mask_g.astype(bool)
    t = mask_t.astype(bool)
    inter = np.logical_and(g, t).sum()
    union = np.logical_or(g, t).sum()
    g_sum = g.sum()
    t_sum = t.sum()
    iou = (inter / union) if union > 0 else 1.0
    dice = (2 * inter / (g_sum + t_sum)) if (g_sum + t_sum) > 0 else 1.0
    acc = (np.logical_not(np.logical_xor(g, t)).sum()) / g.size
    prec = (inter / g_sum) if g_sum > 0 else 1.0
    rec = (inter / t_sum) if t_sum > 0 else 1.0

    def grid_energy(levels=(8, 16, 32)) -> float:
        H, W = mask_g.shape
        weights = np.array([1.0, 1.2, 1.4], dtype=float)[: len(levels)]
        weights /= weights.sum()
        diffs: List[float] = []
        for L, w in zip(levels, weights):
            # compute black fraction per cell
            h = H // L
            wcell = W // L
            if h == 0 or wcell == 0:
                continue
            diff_sum = 0.0
            cells = 0
            for i in range(L):
                for j in range(L):
                    gblk = mask_g[i * h : (i + 1) * h, j * wcell : (j + 1) * wcell]
                    tblk = mask_t[i * h : (i + 1) * h, j * wcell : (j + 1) * wcell]
                    pg = gblk.mean()  # since mask is 0/1, mean = fraction black
                    pt = tblk.mean()
                    diff_sum += abs(pg - pt)
                    cells += 1
            if cells:
                diffs.append(w * (diff_sum / cells))
        return float(np.sum(diffs)) if diffs else 0.0

    ge = grid_energy()
    energy = 0.7 * (1.0 - iou) + 0.3 * ge

    return dict(IoU=iou, Dice=dice, Accuracy=acc, Precision=prec, Recall=rec, GridEnergy=ge, Energy=energy)


def make_diff(mask_g: np.ndarray, mask_t: np.ndarray) -> Image.Image:
    H, W = mask_g.shape
    img = np.ones((H, W, 3), dtype=np.uint8) * 255
    # gds only (false positive): red
    fp = np.logical_and(mask_g == 1, mask_t == 0)
    img[fp] = (255, 0, 0)
    # target only (false negative): blue
    fn = np.logical_and(mask_g == 0, mask_t == 1)
    img[fn] = (0, 0, 255)
    return Image.fromarray(img, mode="RGB")


def make_overlay(original: Image.Image, mask_g: np.ndarray, alpha: float = 0.35) -> Image.Image:
    base = original.convert("RGB")
    overlay = np.array(base)
    red = np.array([255, 0, 0], dtype=np.uint8)
    sel = mask_g.astype(bool)
    overlay[sel] = (alpha * red + (1 - alpha) * overlay[sel]).astype(np.uint8)
    return Image.fromarray(overlay, mode="RGB")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--gds", required=True, type=Path)
    p.add_argument("--layer", required=True, type=int)
    p.add_argument("--datatype", required=True, type=int)
    p.add_argument("--like", required=True, type=Path, help="image whose size to use")
    p.add_argument(
        "--into-bbox-of",
        required=False,
        type=Path,
        help="use non-white bbox of this image as destination rectangle (defaults to --like)",
    )
    p.add_argument("--preserve-aspect", action="store_true")
    p.add_argument("--flip-y", action="store_true")
    p.add_argument("--white-threshold", type=int, default=245)
    p.add_argument("--supersample", type=int, default=4)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--compare-to", required=True, type=Path)
    p.add_argument("--diff", required=True, type=Path)
    p.add_argument("--overlay", required=True, type=Path)
    p.add_argument("--report", required=True, type=Path)
    args = p.parse_args()

    # 1) Load layout and polygons
    top = load_top_cell(args.gds)
    polys = extract_polygons(top, args.layer, args.datatype)
    if not polys:
        raise SystemExit("No polygons found for specified (layer, datatype)")
    lx0, ly0, lx1, ly1 = polygons_bbox(polys)

    # 2) Define mapping
    like_img = Image.open(args.like)
    W, H = like_img.size
    into_img_path = args.into_bbox_of if args.into_bbox_of else args.like
    into_img = Image.open(into_img_path)
    bbox = nonwhite_bbox(into_img, white_threshold=args.white_threshold)

    # 3) Rasterize to black/white
    mapped = map_polygons_to_image(
        polygons=polys,
        layout_bbox=(lx0, ly0, lx1, ly1),
        dest_bbox=bbox,
        out_size=(W, H),
        preserve_aspect=args.preserve_aspect,
        flip_y=args.flip_y,
        supersample=args.supersample,
    )

    Wss, Hss = W * args.supersample, H * args.supersample
    raster_ss = rasterize(mapped, (Wss, Hss))
    raster = raster_ss.resize((W, H), resample=Image.BOX)
    raster.save(args.out)

    # 4) Binarize target
    target = Image.open(args.compare_to)
    mask_g = binarize(raster, white_threshold=args.white_threshold)
    mask_t = binarize(target, white_threshold=args.white_threshold)

    # 5) Metrics
    metrics = compute_metrics(mask_g, mask_t)
    args.report.write_text(json.dumps(metrics, indent=2))

    # 6) Diagnostics
    diff_img = make_diff(mask_g, mask_t)
    diff_img.save(args.diff)
    overlay_img = make_overlay(target, mask_g)
    overlay_img.save(args.overlay)

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()


