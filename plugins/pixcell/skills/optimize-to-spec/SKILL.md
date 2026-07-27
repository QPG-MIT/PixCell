---
name: optimize-to-spec
description: Retune a parametric HOMI device to hit a performance spec (e.g. MZI FSR) on a chosen layer stack — the agent reasons from physics and drives homi.spec_optimization, which measures but never searches. Use when a chat turn asks to "hit/meet a spec", "retarget to a PDK/stack", or "make it X nm FSR on SiN".
allowed-tools: Read, Write, Edit, Bash
---

# Optimize to Spec

Spec-driven retuning of a parametric device for a target layer stack. This is
the capability that makes HOMI a cross-PDK tool: the recreation step produced
*parametric primitives*, so meeting a spec on any stack is an optimization
problem — and **you are the optimizer**. The evaluator measures; you decide
every move and say why before measuring.

Requires: a device script satisfying the parametric contract (below), a spec
JSON, and a stack JSON. Never call Tidy3D cloud — the evaluator is local-only.

**Engine invocation.** If the `homi` CLI is already on PATH (repo checkout or
installed package), run the evaluator with that environment's `python` directly.
Otherwise invoke through the plugin's engine resolver, which finds or bootstraps
the PixCell Python engine: `"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -m homi.spec_optimization …`.

**Stacks.** Stack JSONs ship with the engine — list them from
`homi.paths.stacks_dir()` (e.g. `soi220.json`, `sin400.json`, `tfln400.json`):

```
"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -c "from homi import paths; [print(p) for p in sorted(paths.stacks_dir().glob('*.json'))]"
```

Use one of these, or a user-supplied stack JSON of the same shape.

## The division of labor (do not blur it)

| Problem | Owner | Tool |
|---|---|---|
| Topology / structure (what the device IS) | you, by reasoning | primitives, draw-to-gds |
| Continuous geometry fidelity vs an image | JEE | `homi.jee_integration` / `jee.core.GDSOptimizer` |
| Physics retargeting vs a spec | **you, reasoning from physics** | `homi.spec_optimization` (measure-only) |

Do NOT hand-roll grid sweeps for continuous polish — that is JEE's job and it
does it better (Nelder-Mead/CMA-ES, footprint penalty, bookkeeping). Your job
in THIS skill is the physics loop: derive the governing relation, predict,
measure, correct.

## Parametric contract (the script you operate on)

- Tunables are top-level `name = value` assignments (JEE-substitutable).
- The spec knob exists by name (for an MZI FSR spec: `delta_length`, µm).
- Arm centerlines are `gf.Path` objects; on every run the script writes
  `lengths.json` next to its GDS: `{"arms": {...}, "delta_length_um": ...}`,
  computed from the paths — never hand-entered.
- Verify once before optimizing:
  `"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -c "from homi.spec_optimization import verify_knob_response as v; print(v('<script>', width_um=<wg_width>))"`
  — pass `width_um` = the script's actual waveguide width, or the area check
  will misjudge (the expected growth is `width x delta`).

## The loop (max 6 evaluator calls per stack)

1. **Adapt the platform constants first, rule-based — not searched.** Set the
   waveguide width to the stack's `single_mode_width_um`; respect
   `min_feature_um`. These come from the stack JSON, not from optimization.
2. **Evaluate:**
   `"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -m homi.spec_optimization eval --script S --stack <stack.json> --spec spec.json`
   → FSR, n_eff, n_g, measured ΔL, verdict.
3. **Reason in writing BEFORE the next move.** For an MZI:
   `FSR = λ² / (n_g · ΔL)` → required `ΔL* = λ² / (n_g · FSR_target)`.
   State the ΔL you will set and the FSR you predict it produces.
4. **Move:** edit the top-level knob; reshape arm geometry with primitives if
   the new ΔL needs physical room (serpentines/detours are fine). The measured
   ΔL may differ from requested — that is WHY you iterate.
5. **Log every iteration** to `optimization_log.json`:
   `{iter, delta_length_requested_um, delta_length_measured_um, n_eff, n_g,
   fsr_nm, rel_error, reasoning, predicted_fsr_nm_next}` — honest, including
   misses.
6. **Stop** at `rel_error <= tolerance` or 6 calls. An honest failure beats a
   fudged pass. Expect convergence in 1–2 calls when the knob is clean
   (validated 2026-07-02: 1/1/1 and 2/2/2 across three stacks): solve the stack's
   modes FIRST and precompute `ΔL* = λ²/(n_g·FSR_target)` — the relation is
   exactly inverse-linear, so the first shot lands within grid-snap error, and
   one correction step (`ΔL_new = ΔL_old · FSR_measured / FSR_target`) covers
   any measured-vs-requested gap.
7. **Fidelity note:** after converging, re-rasterize against the original
   image calibration and record the IoU drop — geometry morphs to meet spec
   while topology persists. Report it; do not tune it back.

## Known gotchas (learned in the 2026-07-02 PDK-swap proof)

- `run_jee_optimization`'s parameter discovery reads function signatures
  (Weber analyzer) and returns "No tunable parameters" for module-level
  tunables. Drive `jee.core.GDSOptimizer` directly with explicit
  `param_names/bounds/baseline` + `homi.jee_integration._create_parametric_factory`.
- IoU rewards fattened waveguides (misalignment hedging). Trust SSE (JEE) for
  dimensional polish and your own pixel measurements for widths; do not let
  IoU pick `wg_width`.
- Mode solves are disk-cached by (indices, thickness, width, λ); the first
  solve per stack costs ~seconds, repeats are free. Never bypass the cache dir.
- n_g here is geometric dispersion only (constant-index materials — repo
  convention). Self-consistent for retuning; absolute values shift with
  material dispersion.
- Tier-1 characterization fixtures must FAN OUT the output guides before the
  monitor planes (>= 5 um separation, planes narrower than the separation).
  A plane spanning two guides projects onto their even supermode and corrupts
  per-port power — the telltale symptom is impossible physics (negative
  insertion loss, transmission > 1). Sanity-check every fixture's numbers
  against conservation before believing them.
- FDTD validation (cloud, human-authorized only): Flex's
  `create_simulation_from_component` places source/monitor at the bbox
  VERTICAL CENTER and records a SINGLE frequency — right for straight-through
  workbench devices, wrong for folded/asymmetric layouts and useless for
  fringe spectra. Reposition the ports onto the measured bus (take a geometric
  slice of the GDS) and set broadband monitor frequencies + an explicit
  run_time covering the folded optical path. A flat spectrum at ~10%
  transmission means the source missed the waveguide.

## Spec JSON shape

```json
{"device": "mzi",
 "target": {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02},
 "wavelength_um": 1.55, "mode": "TE0"}
```
