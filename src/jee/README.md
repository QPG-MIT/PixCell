# JEE: GDS-to-Image Optimization Framework

A framework for optimizing GDSFactory parametric scripts to match target images using SSE (Sum of Squared Errors) minimization with `scipy.optimize.minimize` (Powell method).

## Quick Start

### 1. Run the Trident Example

```bash
cd jee/examples/trident_mode_converter
python optimize_trident.py
```

This will:
- Start from baseline SSE of ~89,854
- Optimize 10 device parameters
- Achieve ~32,000 SSE (64% improvement)
- Save results to `results/best_params.json`

### 2. Create Your Own Optimization

1. **Copy the example**:
   ```bash
   cp -r jee/examples/trident_mode_converter jee/examples/my_device
   cd jee/examples/my_device
   ```

2. **Replace `target.png`** with your device image

3. **Generate calibration**:
   ```bash
   python ../../core/calibrate_boundary.py \
     --reference-image target.png \
     --footprint-length-um 40.0 \
     --footprint-width-um 1.7 \
     --out calibration.json
   ```

4. **Edit `generated_component.py`** with your parametric device function

5. **Edit `optimize_trident.py`** (rename to `optimize_my_device.py`):
   - Update `BASELINE` dict with your initial parameters
   - Update `PARAM_BOUNDS` dict with parameter ranges
   - Update `make_*()` function to build your device

6. **Run optimization**:
   ```bash
   python optimize_my_device.py
   ```

## Directory Structure

```
jee/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── core/                     # Core scripts (called via subprocess)
│   ├── gds_raster_compare.py # GDS → image rasterization
│   ├── compute_sse.py        # SSE metric computation
│   ├── calibrate_boundary.py # Calibration generation
│   └── compare_fixed.py      # Fixed-calibration comparison
└── examples/
    └── trident_mode_converter/  # Working example (64% improvement achieved)
```

## Core Scripts

### `calibrate_boundary.py`
Generates calibration JSON from a target image and footprint dimensions.

```bash
python calibrate_boundary.py \
  --reference-image target.png \
  --footprint-length-um 40.0 \
  --footprint-width-um 1.7 \
  --out calibration.json
```

### `compute_sse.py`
Computes SSE metrics between target and rasterized GDS.

```bash
python compute_sse.py --target target.png --raster raster.png
```

### `compare_fixed.py`
Rasterizes GDS and compares to target using fixed calibration.

### `gds_raster_compare.py`
Core rasterization and comparison functions.

## Optimization Workflow

1. **GDS Generation**: Parametric function creates GDS from parameters
2. **Rasterization**: GDS polygons mapped to image space using calibration
3. **SSE Computation**: Binary pixel comparison (black = device, white = background)
4. **Powell Optimization**: scipy.optimize.minimize adjusts parameters to minimize SSE

## Key Concepts

### Calibration
Maps physical dimensions (microns) to pixel coordinates:
- `footprint_um`: Device size in microns
- `scale_px_per_um`: Pixels per micron (separate X/Y)
- `offset`: Top-left corner in pixels
- `bbox`: Bounding box of device region

### SSE (Sum of Squared Errors)
Pixel-level comparison metric:
- `both_black`: Correctly matched device pixels
- `both_white`: Correctly matched background
- `missing_black`: Device pixels missing from GDS (blue in diff)
- `extra_black`: Extra GDS pixels not in target (red in diff)

### Parameter Bounds
Define valid ranges for each parameter:
```python
PARAM_BOUNDS = {
    'length': (10.0, 22.0),
    'width': (0.15, 0.30),
    # ...
}
```

## Results

The trident example achieves:
- **Baseline SSE**: 89,854
- **Optimized SSE**: ~32,304
- **Improvement**: 64% reduction
- **Iterations**: ~200-300

## Dependencies

```
pip install -r requirements.txt
```

- gdsfactory>=7.0.0
- gdstk>=0.9.0
- numpy>=1.20.0
- scipy>=1.7.0
- Pillow>=9.0.0
