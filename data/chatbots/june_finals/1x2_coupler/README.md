# Example: 1×2 adiabatic coupler (trident splitter)

The canonical HOMI benchmark device: a 1×2 splitter with a center input taper that
terminates in a point, flanked by two arm tapers that S-bend out to a pair of output
waveguides. Extracted from `paper.pdf`; footprint **40.0 × 1.7 µm**.

```
component.png    # B&W target image (1616 × 656 px, calibrated 40.4 px/µm × 307.06 px/µm)
footprint.json   # {"footprint_um": [40.0, 1.7]}
paper.pdf        # source paper
runs/            # recorded recreation runs (scripts + metrics; .gds regenerable)
```

## Baseline: blind multi-seed VLM generation (Michaelangelo pipeline, Jan 2026)

Each model received the target image, footprint, and the GDSFactory catalog, then
generated scripts blind across seeds/turns (Phase 1) with diff-image feedback
refinement (Phase 2). IoU is computed by HOMI's calibrated rasterizer
(`rasterize_and_compare`, layer 1/0).

| Model | Seeds × turns | Best IoU |
|-------|--------------|----------|
| gemini/gemini-3-flash-preview | 15 × 2 + Phase 2 | **0.6153** |
| anthropic/claude-opus-4.5 | 1 + Phase 2 | 0.4976 |
| openai/gpt-5 | 1 | 0.3970 |
| anthropic/claude-3.7-sonnet | 1 + Phase 2 | 0.4083 |
| anthropic/claude-opus-4 | 1 + Phase 2 | 0.3357 |
| gemini/gemini-3-pro-preview | 15 × 2 | 0.2615 |
| anthropic/claude-sonnet-4 | 1 + Phase 2 | 0.2382 |
| gemini/gemini-2.5-flash | 15 × 2 | 0.2258 |
| anthropic/claude-sonnet-4.5 | 1 + Phase 2 | 0.1954 |
| gemini/gemini-2.0-flash | 15 × 2 | 0.1485 |
| qwen/qwen3-vl-235b-a22b-instruct | 1 | 0.1076 |

## Agentic run: Claude Fable 5 driving the HOMI MCP tools (`runs/claude-fable-5/`)

Same task, same scoring harness, same catalog — but run agentically through the
`homi-raphael` MCP server (`setup_component_directory` → `run_calibration` →
`get_gds_catalog` → `execute_gds_script` → `rasterize_and_compare`), with the agent
measuring the calibrated target image programmatically and reading the diff images
between attempts.

| Attempt | Change | IoU | SSE |
|---------|--------|-----|-----|
| 1 | parametric model from measured geometry (straight + tapers + bend_s) | 0.9545 | 10,870 |
| 2 | wider center tip, tilted arm tapers via path transitions | 0.9665 | 8,010 |
| (2a) | — grid-snap fix: port widths must be 2 nm multiples | — | — |
| 3 | bend_s replaced with measured-centerline waypoint paths | 0.9826 | 4,125 |
| 4 | pointed center tip, varying s-bend width, stub trim | **0.9839** | 3,808 |

**Result: IoU 0.9839 in 4 scripts (5 generations incl. one grid-snap retry), vs 0.6153
from the best blind pipeline run (~30+ generations).** The residual error is
single-pixel anti-aliasing noise along edges — at this calibration that is close to the
ceiling a polygon raster can reach against a grayscale-thresholded target.

Method notes, for fairness of comparison:

- Only catalog-listed GDSFactory constructs were used (straight, taper, bend_s,
  `gf.Path` + `extrude_transition` — the catalog's "core parametric system").
  No pixel-tracing of polygons.
- The agent measured the target image with numpy (column profiles → widths/centerlines
  in µm via the calibration). VLM baselines accessed the same image visually; agentic
  access to exact measurements is a structural advantage of the harness, and is part of
  what this run is meant to demonstrate.
- The S-bend centerlines in attempts 3–4 are measured waypoints, so those shapes are
  fit to this target rather than derived from a closed-form parametrization. Attempt 2
  (IoU 0.9665) is the best fully closed-form parametric version.

## Reproduce

```bash
# from the repo root, with .venv set up (./setup.sh)
.venv/bin/python examples/1x2_coupler/runs/claude-fable-5/attempt4.py
# then compare via the homi-raphael MCP tool rasterize_and_compare, or jee.core.gds_raster_compare
```
