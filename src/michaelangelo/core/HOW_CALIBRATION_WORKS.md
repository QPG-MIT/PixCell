# How Calibration Works in HOMI

This document explains the complete calibration system - how it works, why we do it this way, and how to validate it.

---

## Table of Contents

1. [Overview](#overview)
2. [What Calibration Does](#what-calibration-does)
3. [The Calculation](#the-calculation)
4. [How It's Used](#how-its-used)
5. [GDS Rasterization](#gds-rasterization)
6. [Comparison Metrics](#comparison-metrics)
7. [Validation](#validation)
8. [Why This Approach Works](#why-this-approach-works)
9. [Key Files](#key-files)

---

## Overview

Calibration maps between **physical coordinates** (micrometers) and **pixel coordinates** (image space).

**Inputs:**
- `device_bw.png` - Black/white device image
- `footprint.json` - Device dimensions in micrometers (from paper)

**Output:**
- `calibration.json` - Scale factors and offset for coordinate transformation

**The system is auto-generated** - you provide the inputs, calibration happens automatically before generation begins (in either mode).

---

## What Calibration Does

Calibration answers one question: **"How many pixels = 1 micrometer?"**

```
Device image:     1616 × 522 pixels (bounding box of black pixels)
Device physical:  40.0 × 1.7 micrometers (from paper)

Scale factors:
  X: 1616 ÷ 40.0 = 40.4 pixels per micrometer
  Y: 522 ÷ 1.7 = 307.06 pixels per micrometer
```

### calibration.json Structure

```json
{
  "bbox": [0, 62, 1616, 584],           // [x0, y0, x1, y1] bounding box in pixels
  "bbox_size_px": [1616, 522],          // [width, height] of bounding box
  "offset": [0, 62],                    // [x0, y0] top-left corner
  "scale_px_per_um": [40.4, 307.06],    // pixels per micrometer [x, y]
  "footprint_um": [40.0, 1.7],          // device size in micrometers [length, width]
  "image_size_px": [1616, 656],         // full image dimensions
  "white_threshold": 245                // threshold for white detection (grayscale)
}
```

---

## The Calculation

```python
# From michaelangelo/core/calibrate_boundary.py

def calculate_calibration(reference_image, footprint_length_um, footprint_width_um):
    img = load_image(reference_image)

    # Step 1: Find bounding box of non-white pixels (device extent)
    bbox = find_non_white_bbox(img, threshold=245)
    bbox_width_px = bbox[2] - bbox[0]
    bbox_height_px = bbox[3] - bbox[1]

    # Step 2: Calculate scale factors
    scale_x = bbox_width_px / footprint_length_um  # pixels per µm
    scale_y = bbox_height_px / footprint_width_um

    # Step 3: Return calibration data
    return {
        "bbox": bbox,
        "offset": [bbox[0], bbox[1]],
        "scale_px_per_um": [scale_x, scale_y],
        "footprint_um": [footprint_length_um, footprint_width_um],
        "image_size_px": [img.width, img.height],
        "white_threshold": 245
    }
```

**Key insight:** Calibration is pure math. It doesn't modify images - it just computes the mapping.

---

## How It's Used

### The HOMI Workflow

Calibration happens the same way in both generation modes. The **default**
is the agent recreation loop (`homi generate`): a dispatched coding agent
writes a primitives-only parametric script and iterates against
`compare_absolute`, with the conductor gate re-verifying every claim. The
diagram below shows the `--baseline` mode — the June-era multi-seed
pipeline, kept as the paper's measured baseline. Calibration is generated
at the same point in either mode.

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HOMI --baseline WORKFLOW                                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Step 1: Upload paper.pdf                                               │
│           ↓                                                              │
│  Step 2: Extract images → Score → Select device image                  │
│           ↓                                                              │
│  Step 3: Generate B&W variant → device_bw.png                           │
│           ↓                                                              │
│  Step 4: Enter footprint dimensions → footprint.json                    │
│           ↓                                                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  AUTO-CALIBRATION (happens silently)                              │  │
│  │  • Finds bbox of device_bw.png                                    │  │
│  │  • Computes scale_px_per_um = bbox_size ÷ footprint              │  │
│  │  • Saves calibration.json                                         │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│           ↓                                                              │
│  Phase 1: Generate 25 seeds × 2 turns                                   │
│           • Each seed: Generate GDS → Rasterize → Compare to device_bw  │
│           • Uses calibration to map GDS coords to pixels                │
│           • Compute IoU/Dice → Rank seeds                               │
│           ↓                                                              │
│  Phase 2: Extend best seeds with 3-8 more turns                         │
│           • Same comparison process                                      │
│           ↓                                                              │
│  Output: best.gds + best.py                                             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Where Auto-Generation Happens

| Location | When |
|----------|------|
| `michaelangelo/core/multiturn_seed_exploration.py` | Before Phase 1 if missing |
| `homi/gds_generation.py` | `run_calibration()` function |
| `homi/jee_integration.py` | `prepare_calibration()` function |

---

## GDS Rasterization

When a GDS is generated, it must be converted to pixels for comparison.

### The Transformation

```python
# From michaelangelo/core/compare_absolute.py

def render_gds_absolute(polygons, calib, supersample=4):
    """Render GDS at ABSOLUTE scale from calibration."""

    scale_x, scale_y = calib["scale_px_per_um"]
    x0, y0 = calib["offset"]
    footprint_h = calib["footprint_um"][1]

    for polygon in polygons:
        for x_um, y_um in polygon:
            # X-AXIS: LEFT-ALIGNED
            # GDS left edge aligns with target bbox left edge
            x_rel = x_um - gds_left_edge
            x_pixel = x0 + x_rel * scale_x

            # Y-AXIS: CENTERED
            # GDS is vertically centered in target bbox
            y_centered = y_um - gds_center_y + target_center_y
            y_pixel = y0 + (footprint_h - y_centered) * scale_y

            # Draw polygon on image
            draw.polygon(pixel_points, fill=0)  # black
```

### Key Properties

- **X-axis:** GDS left edge → target bbox left edge (left-aligned)
- **Y-axis:** GDS center → target bbox center (vertically centered)
- **Overflow:** If GDS exceeds footprint, it overflows and gets penalized
- **Underflow:** If GDS is smaller, empty space remains (low IoU)
- **Supersampling:** 4× rendering for anti-aliasing, then downsampled

---

## Comparison Metrics

### How Comparison Works

```python
def compute_metrics(raster, target, white_thresh=245):
    # Binarize both images
    r_mask = raster < 245  # True where black in generated
    t_mask = target < 245  # True where black in target

    # IoU = Intersection over Union (primary metric)
    intersection = (r_mask & t_mask).sum()
    union = (r_mask | t_mask).sum()
    IoU = intersection / union

    # Dice coefficient (alternative metric)
    Dice = 2 * intersection / (r_mask.sum() + t_mask.sum())

    # SSE = Sum of Squared Errors (pixel count of mismatches)
    diff = r_mask.astype(float) - t_mask.astype(float)
    SSE = (diff ** 2).sum()

    # Confusion matrix
    TP = intersection                  # Both black (correct)
    TN = (~r_mask & ~t_mask).sum()    # Both white (correct)
    FP = (r_mask & ~t_mask).sum()     # GDS has extra material
    FN = (~r_mask & t_mask).sum()     # GDS missing material
```

### Diff Image Visualization

```
Color coding:
- RED:   False Positive - GDS has material, target doesn't (extra)
- BLUE:  False Negative - Target has material, GDS doesn't (missing)
- WHITE: Correct match
```

The model sees this diff image between turns and adjusts accordingly.

### Example metrics.json

```json
{
  "IoU": 0.78,
  "Dice": 0.88,
  "SSE": 45000.0,
  "total_pixels": 1060096,
  "gds_size_um": [40.0, 1.7],
  "footprint_um": [40.0, 1.7],
  "size_match": [true, true]
}
```

---

## Validation

### The Footprint Verification Test

We can validate calibration by testing that a simple rectangle GDS perfectly overlaps a filled rectangle image.

**The test:**
1. Create filled rectangle image from calibration bbox
2. Create GDS rectangle with footprint dimensions
3. Render GDS using calibration
4. Compare → should get ~100% IoU

**Why this works:**
```
calibration.scale = bbox_size_px / footprint_um

When we render:
  gds_rectangle (footprint_um) × scale = footprint_um × (bbox_size_px / footprint_um)
                                       = bbox_size_px

The rendered GDS MUST equal the bbox size (mathematically guaranteed).
```

### Validation Results (January 2026)

Tested across multiple projects with different footprints:

```
==========================================================================================
Project      | Footprint          | IoU      |        SSE | Status
==========================================================================================
1x2_coupler  | 40.0 x 1.7 µm      | 1.0000   |        0.0 | PASS ✓
paper_2      | 24.3 x 5 µm        | 1.0000   |        0.0 | PASS ✓
paper_3      | 27.9 x 21.6 µm     | 1.0000   |        0.0 | PASS ✓
paper_4      | 240 x 4 µm         | 1.0000   |        0.0 | PASS ✓
70x6         | 70 x 6 µm          | 1.0000   |        0.0 | PASS ✓
==========================================================================================
```

### Bbox Detection Accuracy

The calibration bbox matches the actual device bbox to within ±1 pixel:

```
Project      | Calibration BBox             | Actual BBox                  | Match
==========================================================================================
1x2_coupler  | [0, 62, 1616, 584]           | [0, 62, 1615, 583]           | ±1px
paper_2      | [0, 0, 1024, 1024]           | [0, 0, 1023, 1023]           | ±1px
paper_3      | [0, 0, 1239, 392]            | [0, 0, 1238, 391]            | ±1px
paper_4      | [342, 97, 786, 923]          | [342, 97, 785, 922]          | ±1px
70x6         | [23, 24, 1586, 639]          | [23, 24, 1585, 638]          | ±1px
==========================================================================================
```

The ±1px difference is due to inclusive vs exclusive boundary handling.

### What Validation Proves

| Test | What it proves |
|------|----------------|
| IoU = 100% | Rasterization pipeline has no bugs |
| IoU = 100% | Scale factors are applied correctly |
| bbox ±1px | Bbox detection matches actual device pixels |

### What Validation Does NOT Prove

- Whether the footprint you entered is correct (you got that from the paper)
- Whether the B&W image accurately represents the device

### Running Validation (Optional)

```bash
python -c "
from homi.footprint_verification import verify_footprint
from pathlib import Path
result = verify_footprint(Path('projects/your_project/component'))
print(result)
"
```

---

## Why This Approach Works

### Alternative: Pixelation to Fill Footprint

A conceptual alternative approach:
1. Pixelate device_bw.png to fill the entire footprint (solid rectangle)
2. Create GDS matching this filled rectangle first
3. Then refine to match internal structure

**Why HOMI doesn't use this:**
1. **Calibration provides absolute positioning** - scale factors anchor the GDS correctly
2. **Multi-seed exploration** - 25+ seeds try different interpretations in parallel
3. **Visual feedback** - Models see detailed diff images showing exact errors
4. **Already works** - Benchmarks show good results without the extra step

The current approach uses **parallel search** (many seeds) rather than **hierarchical refinement** (footprint first, then details).

### Asymmetry of Verification

The system uses asymmetric verification:
- **Ground truth is fixed:** `device_bw.png` (never changes)
- **Generated GDS is variable:** Iteratively improved
- **One-way comparison:** GDS is always judged against ground truth

---

## Key Files

| File | Purpose |
|------|---------|
| `michaelangelo/core/calibrate_boundary.py` | Core calibration calculation (canonical, single owner) |
| `jee/core/__init__.py` | Re-exports `calculate_calibration` for the optimizer |
| `michaelangelo/core/compare_absolute.py` | Rasterize GDS and compute metrics |
| `jee/core/compute_sse.py` | Compute SSE between images |
| `jee/core/gds_raster_compare.py` | Alternative rasterization for JEE |
| `jee/core/compare_fixed.py` | Fixed calibration comparison |
| `jee/core/footprint_penalty.py` | Penalize GDS exceeding footprint |
| `homi/jee_integration.py` | `prepare_calibration()` wrapper |
| `homi/gds_generation.py` | `run_calibration()` wrapper |
| `homi/footprint_verification.py` | Optional validation tool |

---

## Project Structure

```
projects/{name}/
├── device_bw.png          # Target B&W image
├── footprint.json         # Device dimensions {"footprint_um": [length, width]}
├── output/
│   ├── recreation_<worker>/   # DEFAULT agent mode: device.py, component.png,
│   │                          #   calibration.json, raster.png, diff.png,
│   │                          #   metrics_abs.json, recreation_log.json
│   ├── best.gds           # Final GDS file (gate-verified in agent mode)
│   └── best.py            # Final GDSFactory script
└── component/             # --baseline mode only
    ├── component.png      # Copy of device_bw.png
    ├── calibration.json   # AUTO-GENERATED
    ├── multiturn_seeds/   # Phase 1 results
    │   └── seed_XXXX/
    │       └── turnN/
    │           ├── component.gds
    │           ├── raster.png
    │           ├── diff.png
    │           └── metrics.json
    └── extended_iteration/ # Phase 2 results
```

---

## Summary

1. **Calibration = coordinate mapping** (pixels ↔ micrometers)
2. **Auto-generated** from device image + footprint dimensions
3. **Used during rasterization** to render GDS at correct scale
4. **Validated** to work correctly across all tested footprint sizes
5. **No pixelation step needed** - parallel seed exploration handles variation
