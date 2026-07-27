# Trident Mode Converter Optimization Example

This example demonstrates optimizing a trident (Y-splitter) mode converter to match a target image.

## Device Description

The trident mode converter consists of:
- **Center arm**: A tapered waveguide
- **Top/Bottom arms**: Tapered straights + S-bends

Target footprint: 40.0 x 1.7 microns

## Results

| Metric | Baseline | Optimized | Improvement |
|--------|----------|-----------|-------------|
| SSE    | 89,854   | 32,304    | **64%**     |

## Files

- `target.png` - Target device image (40.0 x 1.7 µm)
- `calibration.json` - Calibration data (scale, offset, bbox)
- `generated_component.py` - Parametric GDSFactory component
- `optimize_trident.py` - Powell optimizer script
- `results/best_params.json` - Best optimization results
- `visualizations/` - Diff, overlay, and raster images

## Running the Optimization

```bash
python optimize_trident.py
```

The optimizer will:
1. Start with baseline parameters (SSE ~89,854)
2. Run Powell optimization (~200 iterations)
3. Print progress with SSE values
4. Save best parameters to `results/`

## Parameters Being Optimized

| Parameter | Description | Bounds |
|-----------|-------------|--------|
| `mid_length` | Center arm length | 10.0 - 22.0 µm |
| `mid_width_in` | Center input width | 0.15 - 0.30 µm |
| `mid_width_out` | Center output width | 0.06 - 0.15 µm |
| `outer_length` | Outer arm length | 22.0 - 28.0 µm |
| `outer_width_in` | Outer input width | 0.06 - 0.15 µm |
| `outer_width_out` | Outer output width | 0.10 - 0.20 µm |
| `gap_start` | Gap between arms | 0.03 - 0.10 µm |
| `bend_length` | S-bend length | 12.0 - 18.0 µm |
| `bend_height` | S-bend height | 0.35 - 0.65 µm |
| `bend_width_end` | S-bend end width | 0.18 - 0.35 µm |

## Visualizations

- **diff.png**: Red = extra geometry, Blue = missing geometry
- **overlay.png**: GDS (red tint) overlaid on target
- **raster.png**: Binary GDS rasterization

## Adapting for Your Device

1. Copy this entire directory
2. Replace `target.png` with your device image
3. Run calibration (see main README)
4. Modify `generated_component.py` with your device function
5. Update `optimize_trident.py` with your parameters and bounds
