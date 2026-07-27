# HOMI Phase-A / Phase-B ("paper-swap") — Full Breakdown

> **Provenance (2026-07-06).** Historical breakdown of the agent campaigns,
> written pre-consolidation; paths in the body reflect the layout AT RUN TIME.
> Current locations: `agents/experiments/*` and bare `experiments/*` →
> `data/agents/*` · `homi/*.py` → `src/homi/*.py` · `michaelangelo/core/*` →
> `src/michaelangelo/core/*` (run as `python -m michaelangelo.core.compare_absolute`)
> · `gg/servers/*` → `src/gg/servers/*` · `benchmark/` → `src/benchmarking/` ·
> `presentation/*` → consolidated into the paper (`arxiv/`) ·
> `gemini_images_run*` → `data/chatbots/trajectories` · `benchmark_results/` →
> `data/chatbots/aggregates` · worker briefs → the `homi.briefs`
> package (single source) · conductor tooling (gate / hint-lint / readback /
> MEASURE service / tier-1 harness / metrics builders) → `homi.conductor` ·
> `.claude/workflows/paper-swap-phase-a.js` → retired into `homi.conductor.gate`.
> The measurements, numbers, and protocol description below are the record —
> unchanged. File line-counts and `:NNN` anchors cite the run-time revision
> and may sit a few lines off in the current tree.

## 0. The one-paragraph mental model

The runs are the **paper-swap protocol** — *not* the classic 3-phase MJ→Michaelangelo→JEE pipeline in the slide deck. A **conductor** (a Claude session driven by a skill) spawns **worker agent panes** (Claude + Codex CLIs as tmux panes in anu), briefs each by file, and independently re-verifies everything. **Phase A** = *blind* recreation of a device from its paper figure into a primitives-only parametric GDSFactory script, scored by IoU. **Phase B** = *de-hinted* retargeting of that device to hit a physics spec (e.g. MZI FSR, splitter transmission) on each foundry layer stack. The governing design principle everywhere: **the agent is the optimizer; the Python only measures — it never searches.** It ran as **three campaigns** (paper_swap, catalog_swap, pdk_swap) plus a chatbot-style baseline for contrast.

---

## 1. WHERE THE PROCESS IS DEFINED

Two layers: thin **skills** (anu binders) that delegate to a **spine** (a runbook + two brief templates).

### 1a. The spine (authoritative, read first)
| File | Role |
|---|---|
| `experiments/paper_swap/RUNBOOK.md` (182 lines) | **The protocol.** 8 steps + sweep-mode + metrics/transcript/anti-cheat appendices. Both skills say "the RUNBOOK IS the spine — follow it exactly." |
| `experiments/paper_swap/briefs/phaseA_recreation.md` (26 lines) | **Phase A worker prompt** (templated `{{INPUT_DIR}}`/`{{WORKDIR}}`/`{{GIT_RULE}}`). |
| `experiments/paper_swap/briefs/phaseB_retarget.md` (13 lines) | **Phase B worker prompt** (`{{TIER1_CAP}}` + the `MEASURE <stack>:` handshake). |
| `experiments/paper_swap/SWEEP_STATE.md` (45 lines) | Resume anchor: ≤8 panes/wave, 1 wave = 1 window = 1 model config, the 13-config wave queue W1–W12. |

### 1b. The skills (`.claude/`)
| Skill | Path | Mode |
|---|---|---|
| `paper-swap` | `.claude/skills/paper-swap/SKILL.md` | Interactive, **one** device, human watching |
| `paper-swap-sweep` | `.claude/skills/paper-swap-sweep/SKILL.md` | Unattended, **N** devices overnight |
| `paper-swap-phase-a` | `.claude/workflows/paper-swap-phase-a.js` (68 lines) | **A Workflow, not a SKILL.md** — the executable Claude-native recreate→verify pipeline |
| `optimize-to-spec` | `.claude/skills/optimize-to-spec/SKILL.md` | Phase-B physics-retargeting discipline |
| `sweep-feasibility` | `.claude/skills/sweep-feasibility/SKILL.md` | Phase-B reachability probing |

Of these, only `optimize-to-spec` ships in this repository (as
`plugins/pixcell/skills/optimize-to-spec/`). The paper-swap binders, the
Workflow, and `sweep-feasibility` are campaign-era conductor tooling: their
protocol content is preserved verbatim in `data/agents/paper_swap/RUNBOOK.md`
and the gate they drove is code at `homi.conductor`.

### 1c. Phase A and Phase B, precisely
**Phase A — "blind" (`phaseA_recreation.md`, RUNBOOK step 3).** The worker's *only* inputs are `device_bw.png` (black = material, layer (1,0)) + `footprint.json` (`{"footprint_um":[L,W]}`). Data-hygiene binding (brief line 6): *"Do not read other directories … other agents' output dirs … or git history for hints. Your pane transcript is the audit record."* The worker is **not told the device class** — it must classify the device itself. Process: calibrate → write topology reasoning to `recreation_log.json` *before* coding → write `device.py` (**primitives only**: straight/bend/taper/rectangle/`gf.Path`+extrude/boolean/`@gf.cell`; **no `gf.components` device stencils, no raw polygons**; function knobs as top-level tunables) → iterate ≤6× against `compare_absolute.py` IoU, stop at **IoU ≥ 0.85** → `verify_knob_response` → end with the digit-anchored marker `PHASE_A DONE: IoU=<x>, iterations=<n>, tunables=<list>`.

**Phase B — "de-hinted" (`phaseB_retarget.md`, RUNBOOK step 4).** The worker retargets to each stack driven only by spec files that say **WHAT** must be met, **never WHY** (mechanism/physics withheld). It must reason from *its own Phase-A classification*. Per stack: rule-set platform constants (widths → `single_mode_width_um`, respect `min_feature_um`) → derive which geometry must change and why, grounded in tier-0 mode solves → write `device_<stack>.py` + a measurement fixture `fixture_<stack>.py` → emit `MEASURE <stack>: fixture=<path> predicted_T=<x>` and block → conductor runs capped FDTD, replies → iterate → `PHASE_B DONE: soi220=T<x>/fits=<y> …`.

Both phases are guarded by a **conductor adversarial gate**: (1) recompute IoU independently, (2) purity-grep `gf.components.(mzi|ring|coupler|mmi)|add_polygon`, (3) `verify_knob_response` on the main knob. In the workflow, a cell is `VERIFIED` only if recomputed IoU matches the claim within **0.005** AND purity is clean AND the knob moves.

A **pre-dispatch hint-lint** (RUNBOOK 153–157) greps every rendered worker input for the conductor's own device-class/mechanism/formula vocabulary — any hit **blocks dispatch**. *"Workers derive; conductors never teach."*

---

## 2. HOW THE AGENT PANES WERE COORDINATED

No monolithic driver script exists — the orchestration lives in the RUNBOOK + skills and is executed turn-by-turn by the conductor pane.

### 2a. Spawn + boot (RUNBOOK step 2, lines 44–51)
- **Claude worker:** `claude --dangerously-skip-permissions --model claude-opus-4-8 --effort medium`
- **Codex worker:** `codex --yolo -c mcp_servers={}` (MCP disabled — a hanging personal MCP server blocks codex's first turn)
- Sequence: launch CLI → `pane read` to **verify the composer is up** → `pane send %id -f brief.md`. *"Never send into a booting shell."* Briefs with quotes/newlines must go via `-f file`.

### 2b. The anti-silent-fallback readback gate (RUNBOOK 176–181)
`claude --model claude-opus-4-1` **silently remaps to Opus 4.8**, and headless `-p` probes answer "ok" under the remapped id. So the **status-line readback** is the *only* reliable config check — it "caught three mislabeled panes on its first sweep outing." Model/effort is verified from the pane's status line before any brief is sent, and that same readback captures context usage for free.

### 2c. Polling + verification
Workers end turns with **digit-anchored markers**; pollers are background greps for `DONE: <field>=[0-9]` (never bare `DONE`, and excluding the brief's own template text). `pane_status` misreads panes launched via compound commands, so the protocol polls **screen markers** instead. On every completed cell the conductor runs the 3-part adversarial gate and appends a line to `sweep_verdicts.txt`. Watchdog: per-completion wake + 35-min wave timeout kills hung panes, records `HUNG`, retries once; aborts at <12% free memory.

### 2d. Phase-B measurement service (the "conductor-serviced measurement loop")
Workers **never run cloud jobs**. On `MEASURE <stack>:` the conductor:
- **Staleness gate** before every run — fixture GDS mtime must be newer than its `.py` and embedded device source (stale = "confidently identical numbers, void data at full price"; one flagged redo).
- **Fixture-economy decline** — oversized fixtures declined *without consuming* the worker's call cap.
- Runs capped FDTD via `experiments/pdk_swap/splitter_tier1.py` (`--material/--thickness-nm/--core-n/--clad-n/--ceiling`), **concurrent dispatch** when requests queue.
- **Conservation sanity** on every result (negative IL / T>1 = overlapping monitor planes = impossible physics).
- Replies with measured transmission/balance; per-stack cap default 3.

### 2e. Two substrates (paper-swap-sweep SKILL 20–28)
- **Claude-family cells** *can* run through the **Workflow tool** (`paper-swap-phase-a.js`, a `pipeline(cells, recreate, verify)` with schema-validated returns and per-agent token tracking).
- **Codex/other-vendor cells must be anu panes** (workflows can't spawn other vendors). In practice the 104-cell sweep ran as pane waves (metrics show 57 Claude-Code + 47 Codex-CLI sessions).

### 2f. Budget
Interactive mode: conductor may escalate ceilings *with justification*. Sweep mode: total FlexCredit + per-call + calls-per-stack ceilings set **at launch**; conductor **never escalates mid-sweep**; over-ceiling → cells close as "unmeasured — budget," never failures.

---

## 3. THE CODE — WHERE IT IS & WHAT IT DOES

**Design principle, stated in the source:** `homi/spec_optimization.py:18` — *"This module contains NO search or optimization logic — the agent is the optimizer; the evaluator only measures."* `homi/sweep_evaluation.py:3` — *"Measure-only … NO search logic and NO device knowledge."*

### 3a. Phase-A engine ("raphael" write→verify→refine)
There is **no single `homi/raphael_integration.py`** — the engine is three thin pieces:
1. **Calibration** — `homi/jee_integration.py:60` `prepare_calibration(target_png, footprint_json, out)` → writes `calibration.json` (µm↔px scale via JEE's `calculate_calibration`).
2. **Execute** — run the agent's `device.py` as a subprocess, capture newest `.gds` (`gg/servers/raphael_server.py:320`).
3. **Rasterize + compare** — **`michaelangelo/core/compare_absolute.py`** (273 lines) is the actual metric engine:
   - `extract_polygons` (:23) → `render_gds_absolute` (:68, renders at **absolute physical scale** from calibration, no fit-to-box) → `compute_metrics` (:141).
   - **IoU** `:152`, **Dice** `:153`, **SSE** `:167` (mismatched-pixel count on binary masks), plus accuracy/precision/recall; writes `diff.png` (red=extra, blue=missing).
- MCP surface: `gg/servers/raphael_server.py` (`homi-raphael` — `setup_component_directory`, `run_calibration`, `execute_gds_script`, `rasterize_and_compare`, `get_gds_catalog`, `get_target_image`). Workers in the protocol call the Python directly for determinism.

### 3b. Phase-B evaluator — `homi/spec_optimization.py` (1367 lines, measure-only)
- Physics: `compute_fsr_nm(λ, n_g, ΔL)` (:191) = `λ²/(n_g·ΔL)·1000` (the relation the agent inverts to precompute ΔL*).
- Mode solvers (disk-cached, **local tidy3d `ModeSolver` only — never `tidy3d.web`**): `solve_waveguide` (:223, → n_eff/n_g), `solve_supermodes` (:275, coupling length), `solve_multimode` (:337, MMI beat length), `solve_cross_section` (:398, arbitrary multi-core).
- Measurement contract: `measured_lengths`/`measured_delta_length` (:467/:511) read `lengths.json` the script writes *from its own `gf.Path` objects* — geometry comes from the script, not the agent.
- Verdict engine: **`evaluate(script, stack, spec)`** (:607) — tier-0 metrics (`fsr_nm, ring_fsr_nm, coupling_ratio, group_delay_ps, bragg_wavelength_nm`) computed from measured geometry + local solve; tier-1 (ER, IL) only get a verdict if fed a `--measured` value from FDTD, else `"unmeasured"` (never a pass). Footprint bbox measured from the written GDS, never declared.
- Anti-fake check: **`verify_knob_response`** (:551) perturbs the top-level knob and asserts layer-(1,0) area grew by ≈ `width·Δ` within 25%.
- **CLI** (`python -m homi.spec_optimization`): `eval / solve / supermodes / multimode / cross-section / spectrum`. This is the Phase-B worker's actual interface.

### 3c. Feasibility engine — `homi/sweep_evaluation.py` (255 lines)
`run_sweep(script, stack_json, sweep, fom, budget_fc, out_path, dry_run)` (:148) — cartesian grid over declared tunables, **uploads all FDTD points first, sums estimates, and starts nothing if `total_est > budget_fc`** (:201, status `aborted_budget`). FoM (coupling ratio) computed at :228–231. Crash-safe `tasks.json` registry.

### 3d. Metric libraries (two in this tree, deliberately redundant — flag: "SSE" is overloaded)
- `benchmark/metrics.py` — campaign-era raw-pixel metrics (`compute_iou`/`compute_dice`/`compute_raw_sse`, raw uint8, max 255²/px) — not in this release; its statistical successors live in `src/homi/benchmark/`.
- `jee/core/compute_sse.py` — `compute_sse_metrics` (binarized masks, JEE's cost function).
- `michaelangelo/core/compare_absolute.py` — the one actually used in the Phase-A loop.
- ⚠️ raw-pixel SSE vs binarized SSE differ **by up to ~65,025×** (documented, issue #29).

### 3e. Conductor tools & analysis scripts
| Script | What it does |
|---|---|
| `experiments/paper_swap/tools/build_results.py` (79 ln, campaign-era — not in this release) | Parses `sweep_verdicts.txt` + hardcoded pre-ledger cells → **`sweep_results.json`**; prints per-config mean IoU + violation counts. |
| `experiments/paper_swap/tools/metrics_extract.py` (156 ln, campaign-era — not in this release) | Maps each transcript to its `(device,config)` cell by the workdir signature in the brief → **`sweep_metrics.json`** (tokens/turns/wall-time). |
| `analyze_primitives.py` (209 ln, campaign-era — superseded by `src/homi/benchmark/primitive_analyzer.py`) | Static purity analyzer: classifies scripts into primitives / basic-shapes / raw-polygons; per-model purity %. |
| `experiments/pdk_swap/splitter_tier1.py` (217 ln, campaign-era — the shipped harness is `python -m homi.conductor.tier1`) | The **tier-1 FDTD measurement harness** the conductor ran on `MEASURE`. |
| `experiments/cross_pdk_synthesis.py` (1135 ln, campaign-era — not in this release) | The **older, batch** cross-PDK path — uses the *search-based* Michaelangelo multi-seed sweep, **not** the measure-only protocol. Don't conflate. |

---

## 4. THE SCRIPTS THAT ACTUALLY RAN (concrete command surface)

- **Phase-A worker inner loop:** `.venv/bin/python device.py` → `.venv/bin/python michaelangelo/core/compare_absolute.py --gds <gds> --target component.png --calibration calibration.json --out-raster raster.png --out-diff diff.png` → repeat ≤6×; then `verify_knob_response` from `homi.spec_optimization`.
- **Phase-B worker:** `python -m homi.spec_optimization eval --script S --stack stacks/X.json --spec spec_<stack>.json` (tier-0) + fixture build → `MEASURE` handshake (tier-1).
- **Conductor measurement:** `experiments/pdk_swap/splitter_tier1.py --material … --thickness-nm … --ceiling …`.
- **Conductor post-processing:** `tools/build_results.py`, `tools/metrics_extract.py`, `analyze_primitives.py`.
- **Pane driving:** `pane spawn / read / send %id -f brief.md / status`; background greps for `DONE: <field>=[0-9]`.

---

## 5. THE DATA THAT WAS PRODUCED

Three campaigns + two writeups + the chatbot baseline:

| # | Campaign | What it produced | Root |
|---|---|---|---|
| 1 | **paper_swap** (the "emergence matrix") | 8 devices × 13 agent configs = **104-cell Phase-A IoU grid** (103 verified); Phase B on the pilot only | `data/agents/paper_swap/` |
| 2 | **catalog_swap** | 8 gdsfactory catalog primitives × 2 frontier agents; primitives-vs-stencil ladder, Phase A+B | `data/agents/catalog_swap/` |
| 3 | **pdk_swap** | The MZI "one drawing → three fabs" FSR-to-spec proof + FDTD validation | `data/agents/pdk_swap/` |
| — | **emergence_paper** | The headline LaTeX paper | `arxiv/` |
| — | **emergence_report** | HTML writeup of the chatbot baseline | consolidated into `arxiv/` |
| — | **pdk_swap_proof** | HTML + LaTeX writeup of campaign 3 | consolidated into `arxiv/` |
| — | **Chatbot baseline** | Source images + analysis scripts + figures ("before") | `data/chatbots/{trajectories,aggregates}` (in this tree) |

### 5a. The 8 devices (FINAL_1–8)
| Dir | Footprint µm | Device |
|---|---|---|
| final1 | 40 × 1.7 | Trident / adiabatic 1×2 splitter (the pilot) |
| final2 | 25 × 10 | 1×4 MMI splitter |
| final3 | 120 × 4 | Directional coupler (long) |
| final4 | 18 × 3 | Compact directional coupler |
| final5 | 18.2 × 0.7 | Grating-assisted (Bragg) coupler |
| final6 | 4.7 × 4.7 | Waveguide crossing (4-port) |
| final7 | 3.0 × 5.5 | Ring/racetrack + balanced MZI |
| final8 | 120 × 4 | Sub-wavelength-grating coupler |

Each `finalN/output/` holds 13 `recreation_<config>/` dirs (`device.py`, `.gds`, `component.png`, `diff.png`, `overlay.png`, `metrics.json`, `recreation_log.json`, `calibration.json`, `knob_response.json`). Three more device dirs (`mmi_1x4_slot`, `adiabatic_coupler_design_ratio`, `tfln_directional_coupler`) were **curated but never swept** (`output/` empty; provenance in each `provenance.json`).

### 5b. The full 104-cell Phase-A IoU matrix
Source of truth: `experiments/paper_swap/sweep_results.json` (+ `sweep_verdicts.txt` for purity, `sweep_metrics.json` for cost/time). `*` = purity violation.

| Config (mean/usable IoU, viol.) | F1 | F2 | F3 | F4 | F5 | F6 | F7 | F8 |
|---|---|---|---|---|---|---|---|---|
| **codex55x** GPT-5.5 xhigh (.912/.912, 0) | .949 | .987 | .817 | .981 | .846 | .939 | .863 | .916 |
| **opus48m** Opus 4.8 med (.910/.910, 0) | .947 | .972 | .851 | .965 | .786 | .982 | .873 | .900 |
| **codex55h** GPT-5.5 high (.910/.910, 0) | .940 | .976 | .967 | .977 | .753 | .921 | .809 | .934 |
| **opus48max** Opus 4.8 max (.909/.909, 0) | .961 | .994 | .741 | .972 | .840 | .967 | .874 | .919 |
| **codex55m** GPT-5.5 med (.897/.897, 0) | .987 | .960 | .641 | .921 | .937 | .855 | .958 | .918 |
| **codex54m** GPT-5.4 (.802/.802, 0) | .853 | .987 | .704 | .891 | .437 | .943 | .700 | .903 |
| **sonnet5m** Sonnet 5 (.797/.797, 0) | .887 | .973 | .655 | .971 | .563 | .909 | .556 | .866 |
| **codexspark** GPT-5.3 spark (.749/.749, 0) | .528 | .641 | .728 | .855 | .637 | .641 | .978 | .981 |
| **codex54mini** GPT-5.4-mini (.645/.645, 0) | .855 | .576 | .546 | .916 | .298 | .856 | .507 | .604 |
| **opus45m** Opus 4.5 (.506/**.341**, 2) | .365 | .454* | .464 | .650 | .309 | .868* | .588 | .349 |
| **haiku45h** Haiku 4.5 high (.386/**.189**, 4) | .186 | .382* | .274 | .593* | .143* | .458* | .557 | .499 |
| **sonnet45m** Sonnet 4.5 (.361/**.148**, 3) | .242 | .519* | .019 | .477* | .284 | .709* | .197 | .444 |
| **haiku45m** Haiku 4.5 med (.334/**.062**, 6) | .291* | .439 | .231* | .503* | .292* | .604* | .254* | .058 |

Highest cell: final2/opus48max **0.994**. Hardest devices (discriminators): **F3, F5**. Grid is 8×13=104; paper cites **103 verified** (final1/haiku45m first produced no usable GDS, later redone to 0.291).

### 5c. Phase-B results
**paper_swap pilot (final1 only)** — `final1/output/{retarget_opus,retarget_codex}/summary.json`, `PILOT_SUMMARY.json`; spec = T≥0.95 & balance 0.5±0.02:
| Stack | Opus 4.8 med | codex GPT-5.5 xhigh |
|---|---|---|
| soi220 | partial T=0.928 | partial T=0.976, balance fail |
| sin400 | **PASS** T=0.967 (2 calls) | **PASS** T=0.974 (1 call) |
| tfln400 | T-floor 0.93 | T-floor 0.92 |

Split balance was structurally exact (0.500–0.5075) on **all** stacks; transmission was the fight; TFLN has a ~0.93 within-budget floor. Cloud billed **6.458 FlexCredits** (`final1/output/cloud_costs.json`).

**pdk_swap MZI proof** — device = unbalanced MZI, spec **FSR = 8.0 nm ±2% @1550 TE0**. Baseline flat-GDS misses everywhere (`baseline_eval.json`: soi220 640%, sin400 1542%, tfln400 1331% off). Both agents hit **8.000 nm on all three diagonal stacks in 1–2 calls**; off-diagonal transplants miss. Full-wave FDTD (`output/smatrix_result.json`): **FSR_fdtd 7.77 nm vs analytic 8.00 (3.3% agreement)**.

**catalog_swap** — cat1–8 (mzi, ring_single, mmi1x2, mmi2x2, coupler, crossing, spiral, dbr) × {opus48m, codex55h}. Phase A all purity-clean (e.g. cat8 codex55h 0.994). Phase B ran 4 arms (armA/C = agent-primitives, armB/D = stencil-wrapper) × 3 stacks → the **DOF-coverage law**: primitives clear knob ceilings the stencils hit (e.g. cat1 armD infeasible on sin400 where armC passes). Verdicts in `catalog_verdicts.txt`; 0.641 FC total.

### 5d. Where the headline numbers live
- **"103-cell agent matrix"** → `sweep_results.json` + `arxiv/scripts/agent_table.json`; paper `arxiv/main.tex`.
- **"Gemini 30→85% emergence"** → `data/chatbots/aggregates/real_success_data.json` (the emergence-report writeup was consolidated into the paper). **This is the chatbot baseline, not the agent run** (Mann–Whitney p=0.0001).
- **"5× same-weights harness jump"** → the *same weights* scored 0.07/0.03 as chatbots vs **0.341/0.148 as agents**: Opus-4.5 0.070→0.341, Sonnet-4.5 0.031→0.148. Frontier jump 0.35→0.91. Chatbot side in `real_success_data.json`, agent side in `agent_table.json`.
- **"MZI on 3 stacks in 1–2 calls"** → `data/agents/pdk_swap/output/` (writeup consolidated into the paper).

### 5e. Navigation map
```
data/agents/paper_swap/
  sweep_results.json        ← PRIMARY 104-cell IoU grid
  sweep_metrics.json / sweep_verdicts.txt / ACCESS_AUDIT_SWEEP.md
  curation_manifest.json / papers_fom_codex.md / papers_report_codex.md
  RUNBOOK.md / SWEEP_STATE.md
  briefs/{phaseA_recreation,phaseB_retarget}.md
  transcripts/phaseA/       ← gz transcripts + INDEX.json + SHA256SUMS (redacted for machine identity)
  final1/  device_bw.png footprint.json stacks/ spec_*.json
     output/recreation_<13 configs>/  PILOT_SUMMARY.json  retarget_{opus,codex}/  sidewall_sweep/
  final2..8/  device_bw.png footprint.json output/recreation_<13 configs>/
  {mmi_1x4_slot,adiabatic_coupler_design_ratio,tfln_directional_coupler}/  (curated, not run)
data/agents/catalog_swap/   briefs/ cat1..8/output/
data/agents/pdk_swap/       spec*.json stacks/ output/{baseline_eval,smatrix_result}.json scaffold.py smatrix_*.py
arxiv/                      main.tex (the paper) + scripts/agent_table.json + figures/
data/chatbots/              trajectories/ (baseline inputs) + aggregates/real_success_data.json
src/homi/{spec_optimization,sweep_evaluation,jee_integration}.py
src/michaelangelo/core/compare_absolute.py    (IoU/Dice/SSE engine)
```

---

## 6. Caveats worth knowing

1. **Only `final1` ran Phase B** in paper_swap; final2–8 are Phase-A-only ("PHASE B IS FROZEN"). Full cross-stack Phase-B evidence lives in **pdk_swap** (MZI) and **catalog_swap**.
2. **`paper-swap-phase-a` is a `.js` Workflow, not a SKILL.md/agent.md.** Only file: `.claude/workflows/paper-swap-phase-a.js`.
3. **"SSE" is overloaded** across the metric modules (~65,025× scale difference; issue #29). IoU/Dice are consistent.
4. **Two cross-PDK paths coexist:** the measure-only agent-as-optimizer protocol (this write-up) vs the older search-based `experiments/cross_pdk_synthesis.py` (Michaelangelo multi-seed). Don't conflate.
5. **Metrics labeling glitch:** `sweep_metrics.json` tags final1/config=`codex` as `claude-fable-5` — a mapping artifact; the authoritative identity (codex55x, IoU 0.9491) is in `PILOT_SUMMARY.json`. No model literally named "Fable 5" ran the matrix.
6. **Historical paths** inside transcripts/reports reference the old checkout name `homi-anu-powered` / `projects/gemini_images_run/` — this repo was renamed to PixCell-running; those paths are historical.
