"""Repair the degenerate calibration produced by the briefed calibration call.

homi.jee_integration.prepare_calibration -> jee.core.calculate_calibration takes
the pixel<->um mapping from the bbox of every pixel with luminance < 245.
device_bw.png carries 2485 faint background speckles (luminance 158-244) at the
image edges, so that bbox becomes the WHOLE image and the mapping is wrong by
1.28x in x and 1.34x in y, with a 193 px anchoring error.

This script re-derives the bbox from the largest connected component of the SAME
sub-threshold mask (the device silhouette, 99.94% of the sub-threshold pixels)
and leaves every other field, including white_threshold, untouched -- so the
scored target mask is bit-identical to the briefed one and only the geometry
mapping is fixed.

Writes:
  calibration_prescribed.json  -- prepare_calibration output, verbatim
  calibration.json             -- the repaired mapping (used for scoring)
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

from homi.jee_integration import prepare_calibration

HERE = Path(__file__).resolve().parent
TARGET = HERE / "component.png"
FOOTPRINT = HERE / "footprint.json"


def device_bbox(image_path: Path, white_threshold: int) -> tuple[list[int], dict]:
    """Bbox of the largest connected component of the sub-threshold mask."""
    gray = np.array(Image.open(image_path).convert("L"))
    mask = gray < white_threshold
    labels, count = ndimage.label(mask)
    sizes = ndimage.sum(mask, labels, range(1, count + 1))
    largest = int(np.argmax(sizes)) + 1
    component = labels == largest
    ys, xs = np.where(component)
    bbox = [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]

    speckle = mask & ~component
    sy, sx = np.where(speckle)
    stats = {
        "device_px": int(component.sum()),
        "speckle_px": int(speckle.sum()),
        "speckle_components": int(count - 1),
        "speckle_luminance_range": [int(gray[speckle].min()), int(gray[speckle].max())],
        "speckle_bbox": [int(sx.min()), int(sy.min()), int(sx.max()) + 1, int(sy.max()) + 1],
        "device_share_of_mask": float(component.sum() / mask.sum()),
    }
    return bbox, stats


def main() -> None:
    prescribed_path = HERE / "calibration_prescribed.json"
    prepare_calibration(TARGET, FOOTPRINT, prescribed_path)
    cal = json.loads(prescribed_path.read_text())

    threshold = cal["white_threshold"]
    bbox, stats = device_bbox(TARGET, threshold)
    x0, y0, x1, y1 = bbox
    length_um, width_um = cal["footprint_um"]

    repaired = dict(cal)
    repaired["bbox"] = bbox
    repaired["bbox_size_px"] = [x1 - x0, y1 - y0]
    repaired["offset"] = [x0, y0]
    repaired["scale_px_per_um"] = [(x1 - x0) / length_um, (y1 - y0) / width_um]
    repaired["bbox_source"] = (
        f"largest connected component of the luminance < {threshold} mask "
        f"({stats['device_share_of_mask']:.4f} of all sub-threshold pixels). "
        f"The raw bbox of that mask, used by jee.core.calculate_calibration, is "
        f"{cal['bbox']} -- the whole image -- because {stats['speckle_px']} "
        f"background pixels in {stats['speckle_components']} disconnected "
        f"speckles (luminance {stats['speckle_luminance_range'][0]}-"
        f"{stats['speckle_luminance_range'][1]}) span {stats['speckle_bbox']}."
    )
    repaired["repair_stats"] = stats
    repaired["prescribed"] = {
        "bbox": cal["bbox"],
        "scale_px_per_um": cal["scale_px_per_um"],
    }

    (HERE / "calibration.json").write_text(json.dumps(repaired, indent=2))
    print("prescribed:", json.dumps(cal["bbox"]), cal["scale_px_per_um"])
    print("repaired:  ", json.dumps(repaired["bbox"]), repaired["scale_px_per_um"])
    print("speckle:   ", stats["speckle_px"], "px in", stats["speckle_components"],
          "components spanning", stats["speckle_bbox"])


if __name__ == "__main__":
    main()
