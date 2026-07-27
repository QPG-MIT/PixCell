# data/agents/ — the campaigns run with models as blind coding agents

Three campaigns, one protocol: blind workers recreate a device from a silhouette +
footprint; a deterministic conductor gate re-executes and re-scores everything; specs
retarget the verified programs across fabrication stacks through a measure-only,
cost-capped physics evaluator. **The claims→artifacts map for every reported number is
in `../README.md`.**

| Campaign | What ran | Spine documents |
|---|---|---|
| `paper_swap/` | the 104-cell emergence matrix (8 paper-figure devices × 13 agent configs, Phase A) + the final1 Phase-B pilot + the trident/sidewall study | `RUNBOOK.md` (protocol), `SWEEP_STATE.md` (per-cell verified state), `ACCESS_AUDIT_SWEEP.md` (blindness audit), `curation_manifest.json` (device provenance) |
| `catalog_swap/` | 8 library-catalog fixtures recreated by 2 configs (16 cells) + the two-arm primitives-vs-stencil Phase-B game (20 cells) + the sidewall/in-plane sweeps | `PLAN.md`, `catalog_verdicts.txt`, `briefs/` |
| `pdk_swap/` | the original MZI one-drawing→three-fabs proof, the vendor-stencil ladder, MMI craft transfer, tier-2 broadband validation | `output/run_metrics.json`, `output/validation_findings.md` |

Anatomy of a recreation cell (`<device>/output/recreation_<config>/`):

```
device.py             # the worker's primitives-only parametric program — the design record
recreation_log.json   # topology reading (pre-code), per-iteration IoU, knob verification
metrics*.json         # verifier output (IoU/Dice/SSE) — authoritative copy in ../sweep_results.json
component/diff/overlay/raster.png   # renders (local-only; regenerate by executing device.py)
```

Worker prompts are frozen in `*/briefs/`; per-session transcripts in `*/transcripts/`
(`.gz` + `INDEX.json` + `SHA256SUMS`). Cloud physics spend is ledgered per campaign in
`cloud_costs.json` (billed FlexCredits per task id). Raw FDTD `.hdf5` is local-only —
see `../BINARY_MANIFEST.json`.
