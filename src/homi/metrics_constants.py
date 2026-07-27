"""
Shared constants for image metrics across all HOMI modules.

All binarization, IoU, SSE, and Dice computations must use these constants
to ensure consistent results between benchmark reporting and the pipeline.
"""

# Binarization threshold: pixels < this value are foreground (black).
# Value 245 matches the pipeline convention used by JEE, Michaelangelo,
# and the GDS raster comparison. Benchmark/metrics.py previously used 128,
# which was inconsistent. See GitHub issue #28.
BINARIZATION_THRESHOLD = 245
