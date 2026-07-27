# Canonical Benchmark Results

This directory contains the reference benchmark results for reproducibility validation.

## Contents

- `real_success_data.json` - Actual benchmark results from 9 VLM models on 352 devices

## Version History

| Date | Description |
|------|-------------|
| 2026-01-28 | Initial canonical results from benchmark runs |

## Validation

To validate your reproduction against these canonical results:

```bash
python -m pytest tests/test_reproducibility.py -v
```

Results are considered reproducible if they fall within the variance bounds
documented in `expected_results/variance_statistics.json`.
