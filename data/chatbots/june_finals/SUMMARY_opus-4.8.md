# Opus 4.8 agentic runs — results vs multi-seed VLM baselines

All driven through the HOMI `homi-raphael` MCP pipeline (setup -> calibrate -> get_catalog -> execute -> rasterize_and_compare).
4 attempts per device, two tiers: **parametric** (attempts 1-2, closed-form GDSFactory primitives) and **reconstruction** (attempts 3-4, horizontal strip-trace of the target bitmap). IoU from HOMI's calibrated rasterizer.

| Device | Type | Baseline best | Opus parametric | Opus reconstruction |
|---|---|---|---|---|
| FINAL_1 | 1x2 trident splitter | 0.685 | 0.952 | 0.983 |
| FINAL_2 | 1x4 MMI splitter | 0.629 | 0.937 | 0.997 |
| FINAL_3 | asymmetric directional coupler | 0.621 | 0.756 | 0.966 |
| FINAL_5 | contra-directional grating coupler | 0.409 | 0.761 | 0.729 |
| FINAL_7 | stadium ring + MZI with slotted bars | 0.425 | 0.689 | 0.987 |
| FINAL_8 | multi-stripe slab coupler (120x4) | 0.612 | 0.938 | 0.988 |

Mean: baseline 0.563 | parametric 0.839 | reconstruction 0.947 (best tier)
