#!/bin/bash
PY=/Users/aadarwal/src/QPG-MIT/homi-anu-powered/.venv/bin/python
CMP=/Users/aadarwal/src/QPG-MIT/homi-anu-powered/michaelangelo/core/compare_absolute.py
$PY device.py 2>&1 | tail -2 || exit 1
$PY $CMP --gds device.gds --target component.png --calibration calibration.json \
  --out-raster raster.png --out-diff diff.png --out-overlay overlay.png --out-metrics metrics.json 2>&1 | grep -E '"IoU"|"Dice"|gds_size|size_match' 
