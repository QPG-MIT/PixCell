"""Footprint verification: validate calibration before Phase 1.

This module implements Step 0 - a calibration validation step that:
1. Creates a filled rectangle image from the device bounding box
2. Generates a GDS rectangle matching the footprint dimensions
3. Compares them to verify calibration accuracy

If IoU >= 99%, calibration is valid and Phase 1 can proceed.
Reference: diffusionphotonics/runs_v3_0731_04112025 achieved 99.59% IoU.
"""

from pathlib import Path
from PIL import Image, ImageDraw
import json
import logging

logger = logging.getLogger(__name__)


def create_filled_footprint_image(calibration_path: Path, output_path: Path) -> Path:
    """Create a solid black rectangle matching the device bounding box.

    This represents what a "perfect" GDS rectangle should look like
    when rendered at the calibration scale.

    Args:
        calibration_path: Path to calibration.json
        output_path: Path to save the filled rectangle image

    Returns:
        Path to the saved image
    """
    with open(calibration_path) as f:
        calib = json.load(f)

    # Create white image matching original image size
    w, h = calib["image_size_px"]
    img = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(img)

    # Fill the bbox with black (this is the footprint area)
    x0, y0, x1, y1 = calib["bbox"]
    draw.rectangle([x0, y0, x1, y1], fill=0)

    img.save(output_path)
    logger.info(f"Created filled footprint image: {output_path}")
    return output_path


def generate_footprint_gds(calibration_path: Path, output_path: Path) -> Path:
    """Generate a simple rectangle GDS matching the footprint dimensions.

    This creates the simplest possible GDS - just a rectangle with
    the exact footprint dimensions. When rendered with the calibration,
    it should perfectly overlap the filled footprint image.

    Args:
        calibration_path: Path to calibration.json
        output_path: Path to save the GDS file

    Returns:
        Path to the saved GDS file
    """
    import gdsfactory as gf
    import uuid

    with open(calibration_path) as f:
        calib = json.load(f)

    length_um, width_um = calib["footprint_um"]

    # Use unique cell name to avoid collisions
    unique_name = f"footprint_rect_{uuid.uuid4().hex[:8]}"
    c = gf.Component(unique_name)
    rect = gf.components.rectangle(size=(length_um, width_um), layer=(1, 0))
    c << rect
    c.write_gds(str(output_path))

    logger.info(f"Generated footprint GDS ({length_um}µm × {width_um}µm): {output_path}")
    return output_path


def verify_footprint(component_dir: Path, threshold: float = 0.99) -> dict:
    """Run footprint verification (Step 0).

    This is the main entry point for calibration validation. It:
    1. Creates a filled rectangle image from the bbox
    2. Generates a GDS rectangle with footprint dimensions
    3. Renders the GDS using calibration
    4. Compares rendered GDS to filled rectangle
    5. Returns success if IoU >= threshold

    Args:
        component_dir: Directory containing calibration.json
        threshold: Minimum IoU required (default 0.99 = 99%)

    Returns:
        dict with keys:
            - success: bool - whether IoU >= threshold
            - iou: float - Intersection over Union score
            - sse: float - Sum of Squared Errors
            - precision: float - how much of generated is correct
            - recall: float - how much of target is covered
            - message: str - human-readable result
    """
    from michaelangelo.core.compare_absolute import (
        extract_polygons, render_gds_absolute,
        compute_metrics, load_calibration
    )

    component_dir = Path(component_dir)
    calib_path = component_dir / "calibration.json"

    if not calib_path.exists():
        return {
            "success": False,
            "iou": 0.0,
            "sse": float("inf"),
            "precision": 0.0,
            "recall": 0.0,
            "message": f"Calibration file not found: {calib_path}"
        }

    # 1. Create filled footprint image (the "target")
    footprint_img_path = component_dir / "footprint_filled.png"
    create_filled_footprint_image(calib_path, footprint_img_path)

    # 2. Generate footprint GDS (the "test")
    footprint_gds_path = component_dir / "footprint_rectangle.gds"
    generate_footprint_gds(calib_path, footprint_gds_path)

    # 3. Load calibration and render GDS
    calib = load_calibration(calib_path)
    polygons = extract_polygons(footprint_gds_path, layer=1, datatype=0)
    raster, info = render_gds_absolute(polygons, calib)

    # 4. Compare rendered GDS to filled rectangle
    target = Image.open(footprint_img_path)
    metrics = compute_metrics(raster, target, calib.get("white_threshold", 245))

    # 5. Save rendered GDS for visual inspection
    raster.save(component_dir / "footprint_raster.png")

    # 6. Create diff image for debugging
    from michaelangelo.core.compare_absolute import make_diff_image
    diff = make_diff_image(raster, target, calib.get("white_threshold", 245))
    diff.save(component_dir / "footprint_diff.png")

    # 7. Check threshold
    iou = metrics["IoU"]
    success = iou >= threshold

    result = {
        "success": success,
        "iou": float(iou),
        "sse": float(metrics["SSE"]),
        "precision": float(metrics["Precision"]),
        "recall": float(metrics["Recall"]),
        "gds_size_um": info.get("gds_size_um", []),
        "footprint_um": list(calib["footprint_um"]),
        "message": f"Calibration {'VALID' if success else 'INVALID'}: IoU = {iou:.4f} (threshold: {threshold})"
    }

    # Save verification result
    with open(component_dir / "footprint_verification.json", "w") as f:
        json.dump(result, f, indent=2)

    if success:
        logger.info(f"✓ Step 0 PASSED: {result['message']}")
    else:
        logger.warning(f"✗ Step 0 FAILED: {result['message']}")

    return result


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m homi.footprint_verification <component_dir>")
        sys.exit(1)

    component_dir = Path(sys.argv[1])
    result = verify_footprint(component_dir)
    print(json.dumps(result, indent=2))
