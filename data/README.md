# The PixCell dataset — evidence for every reported result

This tree is the released record behind *From Pixels to PCells* (`arxiv/main.tex`).
It is organized by the paper's two measurement modes plus the retargeting campaigns, and it
follows one rule inherited from the system itself: **no worker-reported number enters the
record** — every score here was recomputed by the deterministic conductor gate from the
stored artifacts, and you can recompute any of them yourself (below).

## Layout

| Path | Mode / campaign | What it holds |
|---|---|---|
| `chatbots/` | models as API chatbots | benchmark aggregates (`analysis/`, `aggregates/`), the frozen Sec III.A statistics + figure panels (`figure_panels/`), curated reference runs (`june_finals/`), raw trajectories (`trajectories/`), the paper-10 figure run (`paper_10/`), manifests, result decks |
| `agents/paper_swap/` | models as blind coding agents | the 104-cell matrix (8 devices × 13 configs), briefs, access audit, transcripts, per-cell records |
| `agents/catalog_swap/` | models as blind coding agents | the primitives-vs-stencil ladder: 16 recreation cells + the 20-cell two-arm Phase-B game |
| `agents/pdk_swap/` | models as blind coding agents | the MZI one-drawing→three-fabs proof + MMI craft transfer + tier-2 validation |
| `benchmark/` | — | the 8 device input fixtures (silhouette + footprint + calibration + meta), each `meta.json` naming its source panel in `benchmark/source_panels/` |
| `BINARY_MANIFEST.json` | — | sha256/size manifest for binary evidence kept out of git (raw FDTD hdf5, render PNGs) — the external artifact bundle |

The raw chatbot-benchmark trajectories live in `chatbots/trajectories/FINAL_1..8/`. The RL training
study's data lives in `rl/` (see `rl/README.md` and `rl/LINEAGE.md`; not yet in this
tree). The benchmark input fixtures (silhouette + footprint per device) are
`benchmark/`.

## Verify any cell yourself

Every Phase-A cell stores the worker's program (`device.py`) and the archived calibration.
The grade of record is a re-execution:

```bash
# From the tracked record alone (no external bundle needed): copy the cell out
# of the archive, re-execute its program, then run the full promotion gate
# (re-execute, re-rasterize, recompute IoU, purity check) against the target.
cp -r data/agents/paper_swap/<device>/output/recreation_<config> /tmp/cell
( cd /tmp/cell && python device.py )   # some cells write device.gds relative to
                                       # the CWD, others next to the script —
                                       # running inside the copy covers both
python - <<'PY'
from homi.conductor import verify_cell
r = verify_cell("/tmp/cell/device.gds",
                "data/agents/paper_swap/<device>/device_bw.png",   # target
                "/tmp/cell/calibration.json",                      # per-CELL calibration
                "/tmp/cell/device.py",
                claimed_iou=<iou from sweep_results.json>)
print(r.iou, r.iou_matches_claim, r.purity, r.verified)
PY

# If you have the external artifact bundle (which carries each cell's rendered
# component.png), the one-line raster re-score also works:
python -m michaelangelo.core.compare_absolute \
    <cell>/component.png <device>/device_bw.png <cell>/calibration.json
```

Note the calibration lives per cell (`<cell>/calibration.json`), not per device,
and `component.png` is bundle-only — the re-execution path above needs neither.
One archived cell (`final6/recreation_opus45m`) writes its GDS to a nested
`experiments/...` relative path rather than beside the script; use the path it
prints.

Campaign-level scores were conductor-recomputed at sweep time: `agents/paper_swap/sweep_verdicts.txt`
is that audit trail, and `agents/paper_swap/sweep_results.json` is the authoritative
per-cell record.

## Claims → artifacts

Every number in the paper's Results, mapped to its backing file.

### Sec III.A — models as API chatbots

| Claim | Artifact |
|---|---|
| 14 models × 8 devices matrix, per-model IoU/success | `chatbots/analysis/data/benchmark_results.csv` (+ `.parquet`) |
| usable-output fraction 30%→85%; best expected-usable U = 0.354 | `chatbots/aggregates/real_success_data.json` (`primitive_rate`, `expected_usable_iou`) |
| 63 multi-seed experiments, 640 trajectories; spread 0.246; first-seed-best 12.7%; largest spread 0.673; 84% ≥ 0.10 | `chatbots/figure_panels/panels/paper_statistics.json` → `seed_diversity` |
| 65.9% peaked after turn 1; best-of-2/3/5 gains +10/+16/+18.3%; paired t = 10.86; extended refinement 73% / +22.3% | same file → `turn_improvement` |
| primitive-usage / emergence statistics | `chatbots/analysis/data/primitive_analysis.csv`, `statistical_results.json` |
| raw scored trajectories (all 8 devices, per seed × turn: metrics, telemetry, generated program; failed attempts may lack individual files) | `chatbots/trajectories/FINAL_1..8/benchmark_*/{phase1,phase2,multiturn_seeds}/run_*/turn*/` |
| chatbot-benchmark per-device cost $0.03–$6 | order-of-magnitude estimate computed in `arxiv/scripts/make_fig_pareto3d.py` (no measured cost ledger exists for those runs) |

### Sec III.B–E — the agent matrix

| Claim | Artifact |
|---|---|
| 104 cells (13 configs × 8 devices), per-cell verified IoU + violation flags | `agents/paper_swap/sweep_results.json` |
| per-cell tokens / wall-clock (feeds Table `tab:cost`) | `agents/paper_swap/sweep_metrics.json`; USD conversion + bootstrap CIs computed in `arxiv/scripts/make_figures.py` → `arxiv/scripts/agent_table.json` |
| conductor re-verification of every cell | `agents/paper_swap/sweep_verdicts.txt`, `SWEEP_STATE.md` |
| access audit over staged sessions | `agents/paper_swap/ACCESS_AUDIT_SWEEP.md` + `transcripts/phaseA/INDEX.json` + `SHA256SUMS` |
| worker transcripts | `agents/paper_swap/transcripts/phaseA/*.gz` (180 archived; the audit froze at 167 — some cells produced two sessions) |
| worker briefs (hint-linted, verbatim) | `agents/paper_swap/briefs/` |
| per-cell record (program, topology log, iterations, knob check) | `agents/paper_swap/final<N>/output/recreation_<config>/{device.py, recreation_log.json, metrics*.json}` |
| device provenance (source papers, footprints, stacks) | `agents/paper_swap/curation_manifest.json`, `papers_report_codex.md`, `papers_fom_codex.md` |

### Sec IV — one drawing, three fabs (pdk_swap)

| Claim | Artifact |
|---|---|
| as-pictured misses: 640% / 1542% / 1331% | `agents/pdk_swap/output/baseline_eval.json` |
| retuned to FSR 8.0 nm, error <0.006%, 1–2 evaluator calls/stack | `agents/pdk_swap/output/optimize*/<stack>/optimization_log.json`, `run_metrics.json` |
| cross-stack transplant matrix | `agents/pdk_swap/output/optimize/cross_matrix.json` |
| vendor-stencil ladder (FSR 3/3, footprint 0/3) | `agents/pdk_swap/output/stencil/` |
| MMI craft transfer 1.08 / 3.06 / 1.09 dB | `agents/pdk_swap/output/optimize*/…/phase6*_log.json` |
| tier-2 broadband: FSR 7.77 nm, ER 12.24 dB, task id | `agents/pdk_swap/output/smatrix_result.json` (raw S-matrix: `smatrix_data.hdf5`, bundle) |
| FlexCredit ledger | `agents/pdk_swap/output/cloud_costs.json` |

### Sec V — the catalog head-to-head (catalog_swap)

| Claim | Artifact |
|---|---|
| 16 recreation cells, zero violations, means 0.94/0.92 | `agents/catalog_swap/catalog_verdicts.txt`, `cat<N>/output/recreation_*/` |
| the 20-cell two-arm game (win/tie/inversion/double-infeasibility) | `agents/catalog_swap/cat{1,2,5,7,8}/output/retune_arm{A..D}/result_<stack>.json` |
| vendor stencil sources | `agents/catalog_swap/stencils/cat<N>_stencil.py` |
| FlexCredit ledger (0.641 FC) | `agents/catalog_swap/cloud_costs.json` |

### Sec VI — the third dimension

| Claim | Artifact |
|---|---|
| in-plane sweep null (4×3 grid, max ratio 0.022) | `agents/catalog_swap/cat5/output/sweep_pilot/sweep_matrix.json` |
| sidewall sweeps, 34 cells across 2 devices × 3 platforms | `agents/catalog_swap/cat5/output/sidewall_sweep/` + `agents/paper_swap/final1/output/sidewall_sweep/` (matrices tracked; hdf5 in bundle, npz field maps tracked) |
| trident symmetry control: balance 0.500 ± 0.007, 15 cells | `agents/paper_swap/final1/output/sidewall_sweep/trident_matrix.json` |
| total billed < 13 FlexCredits | sum of the three `cloud_costs.json` ledgers (6.458 + 4.366 + 0.641 = 11.47 FC) + per-cell `billed_fc` in the sweep matrices |

### Sec VIII — the RL study

See `rl/README.md`: `rl/reports/benchmark_eval_bridge2_g.json` (the paper's k=8 table,
Table `tab:rl`: 0.254 / 0.466; the first draw `benchmark_eval_bridge2.json`, 0.2395 /
0.4433, is retained as the variance reference),
`benchmark_attempts_bridge2.jsonl` (per-attempt record), `rl/reports/runs_ledger/`
(training metrics behind fig_rl_training), `rl/LINEAGE.md` (checkpoint chain).

## Curation notes (read before reusing)

1. **`sweep_results.json` is the source of truth** for the 104 cells. Per-cell
   `metrics*.json` filenames vary across cells (the campaign evolved); do not assume a
   uniform per-cell schema.
2. **GDS files are not stored** — they regenerate deterministically from each cell's
   `device.py` (GDSFactory 9.20.7 pinned).
3. **Transcript count**: the paper's "167 staged sessions" is the count at the
   2026-07-03 audit freeze (`ACCESS_AUDIT_SWEEP.md`); 180 archives exist because some
   cells produced two sessions. `INDEX.json` enumerates the mapping.
4. **Known label artifact**: `sweep_metrics.json` tags `final1`/`codex` with
   `model_id: claude-fable-5`; the true configuration is GPT-5.5 (codex55x), IoU 0.9491
   per `final1/output/PILOT_SUMMARY.json`. The record is kept as-frozen; trust
   `sweep_results.json` + `PILOT_SUMMARY.json`. Likewise `final1/opus48m`
   corresponds to the directory `recreation_opus`.
5. **Three fixture-only devices** (`agents/paper_swap/{mmi_1x4_slot,
   adiabatic_coupler_design_ratio, tfln_directional_coupler}`) are curated task inputs
   that were never swept (`"fixture": "ABSENT"` in the manifest) — they have no `output/`.
6. **`chatbots/analysis/data/benchmark_results.csv`** contains two malformed legacy model
   keys (`gemini/geminim2p0mflash`, `gemini/geminim2p5mflash`) alongside the clean rows;
   the record is kept as-generated — filter on the clean `model_key` values.
7. **Phase B ran on `final1` only** within paper_swap ("PHASE B IS FROZEN" for 2–8);
   cross-stack evidence lives in `pdk_swap` and `catalog_swap`. The 104-cell matrix is a
   Phase-A (recreation) measurement.
8. **JEE-polish IoU (0.565→0.628)** in pdk_swap is reproducible from
   `output/jee_refine/` + `mode_cache/` but was not frozen as a standalone metrics JSON
   (`output/validation_findings.md` #6).

9. **Session transcripts are redacted for machine identity.** The 218
   archived worker sessions ship in full except for host-identity strings:
   tailnet addresses, DHCP/mDNS hostnames, and machine names are replaced by
   `[REDACTED-IP]` / `[REDACTED-HOST]` (119 of 218 archives carry at least one
   marker). Nothing else was altered — no reasoning, tool call, program, or
   result — and every `SHA256SUMS` was re-frozen over the redacted archives, so
   the shipped checksums verify against what you download. An independent sweep
   of the redacted set for credentials, tokens, and private keys returns clean.

## The external bundle

Binary evidence too heavy for the repo — raw FDTD `*.hdf5` (~480 MB, enumerated
per-file with sizes and sha256), campaign render PNGs and chatbot-benchmark trajectory rasters
(enumerated by class with file counts and byte totals) — is indexed in
`BINARY_MANIFEST.json` and will ship as a hosted artifact bundle at release.
The manifest is frozen as generated in the lab: its `png_classes` roots record
the lab layout (`projects/gemini_images_run/...`); in this tree those
trajectories live under `chatbots/trajectories/`.
