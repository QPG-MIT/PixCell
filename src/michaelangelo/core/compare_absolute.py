"""
Compare GDS to target using ABSOLUTE scaling from calibration data.
No fit-to-box nonsense - if the component is too big, it overflows.
"""

import json
import numpy as np
from PIL import Image, ImageDraw

try:
    import gdstk
except ImportError:
    raise SystemExit("gdstk required: pip install gdstk")


def load_calibration(calib_path):
    """Load calibration data."""
    with open(calib_path) as f:
        return json.load(f)


def extract_polygons(gds_path, layer=1, datatype=0):
    """Extract polygons from GDS file."""
    lib = gdstk.read_gds(str(gds_path))

    # Find best cell (skip metadata)
    best_cell = None
    best_count = 0
    for cell in lib.cells:
        if "$$$" in cell.name:
            continue
        try:
            flat = cell.copy("__COUNT__")
            flat.flatten()
            count = sum(1 for p in flat.polygons
                       if p.layer == layer and p.datatype == datatype)
            if count > best_count:
                best_count = count
                best_cell = cell
        except (RuntimeError, TypeError, AttributeError):
            continue

    if best_cell is None:
        raise ValueError("No valid cell found")

    # Flatten and extract
    tmp = best_cell.copy("__FLAT__")
    tmp.flatten()

    polys = []
    for p in tmp.polygons:
        if p.layer == layer and p.datatype == datatype:
            polys.append(np.array(p.points))

    return polys


def gds_bbox(polygons):
    """Get bounding box of polygons."""
    if not polygons:
        return 0, 0, 1, 1
    all_pts = np.vstack(polygons)
    return (all_pts[:, 0].min(), all_pts[:, 1].min(),
            all_pts[:, 0].max(), all_pts[:, 1].max())


def gate_frame_offset(polygons, footprint_um):
    """Translation (dx, dy) mapping polygons into the gate's scoring frame.

    render_gds_absolute anchors a candidate by its own bounding box — left
    edge at the target bbox's left edge, vertically centered on the
    footprint — before scoring. Any surface that draws or scores polygons
    against the calibrated target must apply the same translation first,
    or its overlay (and any inlined IoU) diverges from the gate on scripts
    whose bbox is not anchored at the origin.
    """
    gx0, gy0, _gx1, gy1 = gds_bbox(polygons)
    dy = (footprint_um[1] / 2 - (gy0 + gy1) / 2) if footprint_um else -gy0
    return float(-gx0), float(dy)


def render_gds_absolute(polygons, calib, supersample=4):
    """
    Render GDS at ABSOLUTE scale from calibration.

    X-AXIS: LEFT-ALIGNED - GDS left edge aligns with target bbox left edge.
    Y-AXIS: CENTERED - GDS is vertically centered in the target bbox.

    If GDS is bigger than footprint, overflow is clipped.
    If GDS is smaller, there will be empty space.
    """
    # Target image size
    img_w, img_h = calib["image_size_px"]

    # Scale factors (px per um)
    scale_x, scale_y = calib["scale_px_per_um"]

    # Target bbox in image coordinates
    x0, y0, x1, y1 = calib["bbox"]

    # Footprint in um
    footprint_w_um, footprint_h_um = calib["footprint_um"]

    # Get GDS bounding box
    gx0, gy0, gx1, gy1 = gds_bbox(polygons)
    gds_w_um = gx1 - gx0
    gds_h_um = gy1 - gy0
    gds_cy = (gy0 + gy1) / 2  # GDS center Y for vertical centering

    # Target center in um (for Y-axis centering)
    target_cy_um = footprint_h_um / 2

    # Create supersampled image
    ss_w = img_w * supersample
    ss_h = img_h * supersample
    img = Image.new("L", (ss_w, ss_h), 255)
    draw = ImageDraw.Draw(img)

    # Map polygons to image coordinates
    for poly in polygons:
        pts = []
        for x, y in poly:
            # X-AXIS: LEFT-ALIGNED - relative to GDS left edge
            x_rel = x - gx0

            # Y-AXIS: CENTERED - relative to GDS center, then shift to footprint center
            y_centered = y - gds_cy + target_cy_um

            # Convert to pixels using absolute scale
            # GDS left edge (x_rel=0) → target bbox left edge (x0)
            px = x0 + x_rel * scale_x
            # Y-flip with centering
            py = y0 + (footprint_h_um - y_centered) * scale_y

            # Apply supersample
            pts.append((px * supersample, py * supersample))

        if len(pts) >= 3:
            draw.polygon(pts, fill=0)

    # Downsample
    raster = img.resize((img_w, img_h), Image.BOX)

    return raster, {
        "gds_size_um": (gds_w_um, gds_h_um),
        "footprint_um": (footprint_w_um, footprint_h_um),
        "size_match": (
            abs(gds_w_um - footprint_w_um) < 0.1,
            abs(gds_h_um - footprint_h_um) < 0.1
        )
    }


def compute_metrics(raster, target, white_thresh=245):
    """Compute comparison metrics including SSE."""
    r_arr = np.array(raster.convert("L"))
    t_arr = np.array(target.convert("L"))

    r_mask = r_arr < white_thresh
    t_mask = t_arr < white_thresh

    intersection = np.logical_and(r_mask, t_mask).sum()
    union = np.logical_or(r_mask, t_mask).sum()

    iou = intersection / union if union > 0 else 1.0
    dice = 2 * intersection / (r_mask.sum() + t_mask.sum()) if (r_mask.sum() + t_mask.sum()) > 0 else 1.0

    tp = intersection
    fp = np.logical_and(r_mask, ~t_mask).sum()
    fn = np.logical_and(~r_mask, t_mask).sum()
    tn = np.logical_and(~r_mask, ~t_mask).sum()

    accuracy = (tp + tn) / (tp + tn + fp + fn)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0

    # SSE computation (Sum of Squared Errors)
    # For binary masks, SSE = count of mismatched pixels
    diff = r_mask.astype(np.float32) - t_mask.astype(np.float32)
    sse = float(np.sum(diff ** 2))
    total_pixels = r_mask.size
    mse = sse / total_pixels

    return {
        "IoU": float(iou),
        "Dice": float(dice),
        "Accuracy": float(accuracy),
        "Precision": float(precision),
        "Recall": float(recall),
        # SSE metrics (primary scoring metric - lower is better)
        "SSE": float(sse),
        "MSE": float(mse),
        "total_pixels": int(total_pixels),
    }


def make_diff_image(raster, target, white_thresh=245):
    """Create diff image: red=FP, blue=FN, white=match."""
    r_arr = np.array(raster.convert("L"))
    t_arr = np.array(target.convert("L"))

    r_mask = r_arr < white_thresh
    t_mask = t_arr < white_thresh

    h, w = r_arr.shape
    diff = np.ones((h, w, 3), dtype=np.uint8) * 255

    # Red: GDS has material, target doesn't (false positive)
    fp = np.logical_and(r_mask, ~t_mask)
    diff[fp] = [255, 0, 0]

    # Blue: target has material, GDS doesn't (false negative)
    fn = np.logical_and(~r_mask, t_mask)
    diff[fn] = [0, 0, 255]

    return Image.fromarray(diff)


def make_overlay_image(raster, target, white_thresh=245, alpha=0.4):
    """Overlay GDS raster (red) on target image."""
    r_arr = np.array(raster.convert("L"))
    r_mask = r_arr < white_thresh

    overlay = np.array(target.convert("RGB"))
    red = np.array([255, 0, 0], dtype=np.uint8)
    overlay[r_mask] = (alpha * red + (1 - alpha) * overlay[r_mask]).astype(np.uint8)

    return Image.fromarray(overlay)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--gds", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--calibration", required=True)
    parser.add_argument("--out-raster", default="raster_abs.png")
    parser.add_argument("--out-diff", default="diff_abs.png")
    parser.add_argument("--out-overlay", default="overlay_abs.png")
    parser.add_argument("--out-metrics", default="metrics_abs.json")
    parser.add_argument("--layer", type=int, default=1)
    parser.add_argument("--datatype", type=int, default=0)
    args = parser.parse_args()

    # Load data
    calib = load_calibration(args.calibration)
    polygons = extract_polygons(args.gds, args.layer, args.datatype)
    target = Image.open(args.target)

    # Render at absolute scale
    raster, info = render_gds_absolute(polygons, calib)

    # Compute metrics
    metrics = compute_metrics(raster, target, calib.get("white_threshold", 245))
    metrics["gds_size_um"] = list(info["gds_size_um"])
    metrics["footprint_um"] = list(info["footprint_um"])
    metrics["size_match"] = [bool(x) for x in info["size_match"]]

    # Create diff and overlay
    diff = make_diff_image(raster, target, calib.get("white_threshold", 245))
    overlay = make_overlay_image(raster, target, calib.get("white_threshold", 245))

    # Save outputs
    raster.save(args.out_raster)
    diff.save(args.out_diff)
    overlay.save(args.out_overlay)
    with open(args.out_metrics, "w") as f:
        json.dump(metrics, f, indent=2)

    print(json.dumps(metrics, indent=2))
