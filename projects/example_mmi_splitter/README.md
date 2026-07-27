# example_mmi_splitter — a complete, gate-verified project

A worked example of the channel described in the paper (Sec. VII and
App. B): a hand-drawn 1×4 MMI splitter, blindly recreated by a coding-agent
worker as a primitives-only parametric program, and promoted through the
deterministic conductor gate at IoU 0.995.

This project ships so the studio and workbench open onto a real device on
first run — and so every artifact of the channel has one inspectable
instance:

| File | Role |
|---|---|
| `device_bw.png` | the input silhouette (dark = material) — here, from a drawing |
| `footprint.json` | the stated physical size in µm — the other half of the task pair |
| `output/best.py` | the design record: the gate-verified parametric program |
| `output/best.gds` | its executed geometry |
| `output/recreation_codex/` | the blind worker's private dir, kept as provenance |
| — `calibration.json` | pixel↔µm mapping, fixed once from the target |
| — `component.png` | the target as the worker saw it |
| — `raster.png`, `diff.png` | the verifier's render + signed diff of the final round |
| — `overlay_abs.png` | candidate-on-target overlay |
| — `metrics_abs.json` | independently recomputed IoU/Dice/SSE |
| — `recreation_log.json` | the worker's topology reading, logged before coding |

Try it:

```bash
homi studio                                              # it's on the light table
homi explore projects/example_mmi_splitter/output/best.py --launch   # the workbench
homi optimize projects/example_mmi_splitter/output/best.py --method nelder-mead
```

No API key is needed for any of the above.
