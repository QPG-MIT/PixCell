# RL Clean Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the proven `v3-b` shaped reward (`iou_n`) in `rl/track_a`, delete the studies/ceremony apparatus, and produce a lean two-run launcher (Run A `l0sft-rl`, Run B `base-rl`) over the sealed depth-v1 dataset.

**Architecture:** `rl/common/` stays the measurement layer (gains `baselines.py` + a boundary-chamfer diagnostic in `evaluator.py`). `rl/track_a/` becomes the single training path: `reward.py` gains policy `shaped_v3b`; `tinker_data.py` keeps its Env/builders (baseline plumbed into the reward call); `train_sft.py`/`train_rl.py` are rewritten lean; a new `run.py` orchestrates stages, probe evals, and provenance. `rl/studies/`, `rl/evaluation/`, `rl/track_b/`, `rl/track_c/`, and track_a's recipe-lock/contract files are deleted.

**Tech Stack:** tinker 0.22.7 + tinker-cookbook ca232b0 (pinned), gdsfactory 9.20.7, scipy 1.18 (present), PIL/numpy, pytest, uv.

## Global Constraints

- Reward constants are the old library's, byte-for-byte: floor 0.05; weights 0.40/0.15/0.40; `TAU_FRAC = 0.05`; `TEACHER_DENOM_FLOOR = 0.3`; `DEGENERATE_IOU_RECT = 0.95`. Never re-tuned.
- Purity stays pre-execution: `SOURCE_REJECTED → 0.0` (old ship-mode semantics). No floor for impure programs.
- `None` reward (REFERENCE/EVALUATOR fault) keeps aborting the run — never becomes 0.
- Training defaults: `Qwen/Qwen3.6-35B-A3B`, renderer `qwen3_5_disable_thinking`, LoRA 32, G=8 rollouts × 8 groups, lr 1e-5 RL / 1e-4 SFT, max_tokens 4096, temp 1.0, image 1440, KL 0, `importance_sampling`, `remove_constant_reward_groups=True`, 30 steps/level, 80/20 replay.
- `rl/common` may not import `rl.track_a`, `tinker`, `tinker_cookbook`, or `chz` (pinned by `rl/common/tests/test_import_boundaries.py`).
- `_json_diagnostic` rejects non-finite floats: any chamfer that is `inf` must be recorded as `None`.
- No AI-attribution trailers in commits. Run `uv run pytest rl/ -q` before every commit; `uv run ruff check rl/` at task ends.

---

### Task 1: `rl/common/baselines.py` — per-task rectangle baseline

**Files:**
- Create: `rl/common/baselines.py`
- Test: `rl/common/tests/test_baselines.py`

**Interfaces:**
- Produces: `TaskBaseline` (frozen dataclass: `iou_rect: float`, `dice_rect: float`, `chamfer_rect_boundary_um: float | None`, `diag_um: float`), `rect_baseline(reference: VerifierReference) -> TaskBaseline` (pure), `cached_rect_baseline(reference) -> TaskBaseline` (module-level dict cache keyed by `reference.target_image_sha256`), `boundary_mask(mask)` and `chamfer_sym_um(mask_a, mask_b, um_per_px)` (ported verbatim from the old `rl/reward/geometry.py`).
- Consumes: `rl.common.contracts.VerifierReference`, `rl.common.evaluator._prepare_reference` (reuses the evaluator's own calibration so the baseline and the score share one geometry).

- [ ] Write `test_baselines.py` with two synthetic targets, `footprint_um=(30.0, 20.0)`:
  (a) a solid 60×40 black rectangle at (20,20) in a 100×80 PNG — its ink bbox equals the ink, so the rectangle fill IS the target: assert `iou_rect == 1.0` and `dice_rect == 1.0` (this is the degenerate case Task 3's branch keys on);
  (b) an L-shaped mask — hand-compute `iou_rect = ink_area / bbox_area`, `dice_rect = 2·ink/(ink + bbox)`; assert both, assert `chamfer_rect_boundary_um` is finite and > 0, and `diag_um == sqrt(30² + 20²)`; assert `cached_rect_baseline` returns the identical object for the same sha.
- [ ] Run: `uv run pytest rl/common/tests/test_baselines.py -q` — expect import failure.
- [ ] Implement. Core (port of old `compute_baselines.rect_baseline` over `_prepare_reference`):

```python
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import binary_erosion, distance_transform_edt
from rl.common.contracts import VerifierReference
from rl.common.evaluator import _prepare_reference

def boundary_mask(mask):
    return mask & ~binary_erosion(mask)

def chamfer_sym_um(mask_a, mask_b, um_per_px):
    if not mask_a.any() or not mask_b.any():
        inf = float("inf"); return inf, inf, inf
    dist_to_b = distance_transform_edt(~mask_b)
    dist_to_a = distance_transform_edt(~mask_a)
    a_to_b = float(dist_to_b[mask_a].mean()) * um_per_px
    b_to_a = float(dist_to_a[mask_b].mean()) * um_per_px
    return 0.5 * (a_to_b + b_to_a), a_to_b, b_to_a

@dataclass(frozen=True)
class TaskBaseline:
    iou_rect: float
    dice_rect: float
    chamfer_rect_boundary_um: float | None
    diag_um: float

def rect_baseline(reference: VerifierReference) -> TaskBaseline:
    prepared = _prepare_reference(reference)
    arr = np.asarray(prepared.target)          # already "L"
    thr = prepared.calibration["white_threshold"]
    x0, y0, x1, y1 = prepared.calibration["bbox"]
    tgt = arr < thr
    pred = np.zeros_like(tgt); pred[y0:y1, x0:x1] = True
    inter = float(np.logical_and(tgt, pred).sum())
    union = float(np.logical_or(tgt, pred).sum())
    denom = float(tgt.sum() + pred.sum())
    sx, sy = prepared.calibration["scale_px_per_um"]
    um_per_px = 2.0 / (sx + sy)
    chamfer_b, _, _ = chamfer_sym_um(boundary_mask(pred), boundary_mask(tgt), um_per_px)
    fw, fh = prepared.calibration["footprint_um"]
    return TaskBaseline(
        iou_rect=inter / union if union else 0.0,
        dice_rect=2.0 * inter / denom if denom else 0.0,
        chamfer_rect_boundary_um=None if chamfer_b == float("inf") else chamfer_b,
        diag_um=(fw * fw + fh * fh) ** 0.5,
    )

_CACHE: dict[str, TaskBaseline] = {}

def cached_rect_baseline(reference: VerifierReference) -> TaskBaseline:
    key = reference.target_image_sha256
    if key not in _CACHE:
        _CACHE[key] = rect_baseline(reference)
    return _CACHE[key]
```

- [ ] Tests pass; `git add` + commit `"Add rectangle-baseline computation to rl/common"`.

### Task 2: boundary chamfer in the evaluator

**Files:**
- Modify: `rl/common/evaluator.py` (the `compute_metrics` call site, ~line 797)
- Test: extend `rl/common/tests/test_evaluator.py`

**Interfaces:**
- Produces: `result.metrics["chamfer_boundary_um"]: float | None` on every `OK` result (µm, mean-axis scale; `None` when either mask is empty).
- Consumes: `boundary_mask`, `chamfer_sym_um` from `rl.common.baselines` — import them INSIDE the compare block (lazy) or top-level; **top-level import is fine** (`baselines` imports `evaluator` only for `_prepare_reference` — avoid the cycle by moving `_prepare_reference` usage in baselines to a function-local import, or import `baselines`' pure helpers from a `rl/common/geometry.py`). **Resolution: put `boundary_mask`/`chamfer_sym_um` in `rl/common/geometry.py` (no imports beyond numpy/scipy); `baselines.py` and `evaluator.py` both import from it. No cycle.**

- [ ] Move the two pure functions into `rl/common/geometry.py`; `baselines.py` imports them from there (adjust Task 1 file accordingly).
- [ ] Add test: craft a tiny GDS-producing program in the existing evaluator-test style (there is a ground-truth self-score test to copy from) and assert `result.metrics["chamfer_boundary_um"]` exists and is `< 0.5` for the self-scored ground truth; craft a shifted-square case via two synthetic masks through `chamfer_sym_um` directly with hand-computed value (1px shift over known um_per_px).
- [ ] Implement in `evaluator.py` right after `metrics = compute_metrics(...)`:

```python
r_mask = np.asarray(raster.convert("L")) < 245
t_mask = np.asarray(prepared.target) < 245
sx, sy = prepared.calibration["scale_px_per_um"]
chamfer_b, _, _ = chamfer_sym_um(
    boundary_mask(r_mask), boundary_mask(t_mask), 2.0 / (sx + sy)
)
metrics = {
    **metrics,
    "chamfer_boundary_um": None if chamfer_b == float("inf") else float(chamfer_b),
}
```

- [ ] `uv run pytest rl/common/tests/ -q` green; commit `"Measure boundary chamfer in the evaluator"`.

### Task 3: reward policy `shaped_v3b`

**Files:**
- Modify: `rl/track_a/reward.py`
- Test: extend `rl/track_a/tests/test_output_reward.py`

**Interfaces:**
- Produces: `REWARD_POLICIES = ("validity_floor", "raw_iou", "shaped_v3b")`; `reward_for_policy(result, *, policy, baseline: TaskBaseline | None = None) -> float | None`; `shaped_components(result, baseline) -> dict[str, float]` (the logging breakdown: `iou`, `dice`, `iou_n`, `dice_n`, `t2b`, `teacher_nb`, `degenerate`).
- Consumes: `TaskBaseline` from `rl.common.baselines`; `result.metrics["chamfer_boundary_um"]` from Task 2. Constants module-level: `SHAPED_FLOOR = 0.05`, `W_IOU3, W_DICE3, W_TEACHER = 0.40, 0.15, 0.40`, `TAU_FRAC = 0.05`, `TEACHER_DENOM_FLOOR = 0.3`, `DEGENERATE_IOU_RECT = 0.95`.

- [ ] Write the ported tests first (old `test_shaping.py`/`test_shaping_v3.py` semantics, expressed against `reward_for_policy` with a crafted `EvaluationResult(OK, MODEL, iou=…, dice=…, metrics={"chamfer_boundary_um": …})` and a crafted `TaskBaseline`):
  - non-degenerate normalization: `iou=0.75, baseline.iou_rect=0.5` with dice term and teacher zeroed ⇒ contribution `0.40 * 0.5`;
  - rect-equivalent program (`iou == iou_rect`, `dice == dice_rect`, chamfer == rect chamfer) ⇒ exactly `0.05`;
  - degenerate branch (`iou_rect = 0.96`): reward uses RAW iou/dice/t2b;
  - teacher denominator floor: `t2b=0.9, t2b_rect=0.8` ⇒ `0.1 / 0.3`;
  - crash (`RUNTIME_ERROR`, MODEL) ⇒ `0.0`; `SOURCE_REJECTED` ⇒ `0.0`; EVALUATOR fault ⇒ `None`;
  - missing chamfer (`None`) ⇒ `t2b = 0`, no crash; missing baseline ⇒ `ValueError` (shaped policy requires a baseline);
  - perfect program on non-degenerate target (`iou=dice=1.0`, chamfer 0, rect baseline 0.3/0.4/large-chamfer) ⇒ `0.05 + 0.40 + 0.15 + 0.40·(1 − t2b_rect)/max(1−t2b_rect, 0.3)` — assert `> 0.95` and `== pytest.approx(1.0)` when `t2b_rect ≤ 0.7`.
- [ ] Run tests, expect failures; implement:

```python
def _t2b(chamfer_um, tau: float) -> float:
    if chamfer_um is None or chamfer_um == float("inf"):
        return 0.0
    return math.exp(-float(chamfer_um) / tau)

def norm_excess(x: float, base: float) -> float:
    if base >= 1.0:
        return 0.0
    return max(0.0, (x - base) / (1.0 - base))

def _shaped_v3b(result: EvaluationResult, baseline: TaskBaseline) -> float:
    iou, dice = float(result.iou), float(result.dice)
    diag = baseline.diag_um if baseline.diag_um > 0 else 1e-9
    tau = max(TAU_FRAC * diag, 1e-9)
    chamfer = result.metrics.get("chamfer_boundary_um")
    chamfer_rect = baseline.chamfer_rect_boundary_um
    t2b = _t2b(chamfer, tau)
    t2b_rect = _t2b(chamfer_rect if chamfer_rect is not None else diag, tau)
    if baseline.iou_rect >= DEGENERATE_IOU_RECT:
        return SHAPED_FLOOR + W_IOU3 * iou + W_DICE3 * dice + W_TEACHER * t2b
    teacher_nb = max(0.0, t2b - t2b_rect) / max(1.0 - t2b_rect, TEACHER_DENOM_FLOOR)
    return (SHAPED_FLOOR
            + W_IOU3 * norm_excess(iou, baseline.iou_rect)
            + W_DICE3 * norm_excess(dice, baseline.dice_rect)
            + W_TEACHER * teacher_nb)
```

  In `reward_for_policy`: `policy == "shaped_v3b"` → OK ⇒ validate iou/dice finite in [0,1], require `baseline is not None`, return `_shaped_v3b`; MODEL failure ⇒ `0.0`; else `None`. Keep the existing two policies untouched.
- [ ] Tests green; commit `"Port the v3-b shaped reward (iou_n) as policy shaped_v3b"` with trailer `Honors:` referencing the design commitment commit.

### Task 4: plumb baseline + shaped metrics through the Env

**Files:**
- Modify: `rl/track_a/tinker_data.py` (`TrackAEnv.step` ~line 347, builder defaults), Test: `rl/track_a/tests/test_tinker_contract.py` additions

**Interfaces:**
- Consumes: `cached_rect_baseline` (Task 1), `reward_for_policy(..., baseline=...)` + `shaped_components` (Task 3).
- Produces: `TrackAEnv.step` computes `baseline = cached_rect_baseline(self.task.reference)` when `self.reward_policy == "shaped_v3b"`, passes it to `reward_for_policy`, and extends `StepResult.metrics` with `iou_n`, `teacher_nb`, `degenerate` from `shaped_components`. Builder defaults change: `TrackARLDatasetBuilder.group_size: int = 8`, `reward_policy: str = "shaped_v3b"`.

- [ ] Test: instantiate `TrackAEnv` with a stub renderer + a real L0 `TaskRecord` (existing contract tests show how) and a monkeypatched batcher returning a crafted OK result; assert reward equals the hand-computed shaped value and `metrics["iou_n"]` present.
- [ ] Implement; run `uv run pytest rl/track_a/tests/ -q`; commit `"Default Track A to the shaped reward at G=8"`.

### Task 5: the deletion sweep

**Files:**
- Delete: `rl/studies/`, `rl/evaluation/`, `rl/track_b/`, `rl/track_c/`, `rl/track_a/{recipe.py,evaluation_contract.py,checkpoint_metrics.py,checkpoint_selection.py,select_sft_checkpoint.py,evaluate_checkpoint.py,preflight.py→trim,tests/test_checkpoint_promotion.py,tests/test_launch_preflight.py}`
- Modify: `rl/track_a/curriculum.py` (absorb `LEVELS`, `normalize_level`, `normalize_replay_levels`, `expected_replay_levels` verbatim from `recipe.py`), `rl/track_a/tinker_data.py` (imports; delete the Inkling `_renderer` branch → `raise ValueError("Inkling is out of scope")`), `rl/track_a/launch.py` (keep `bind_execution_boundary`; drop recipe imports), `rl/stack.json` (drop `tml-renderers`), `rl/README.md` + `rl/track_a/README.md` (rewrite: three-policy reward table with `shaped_v3b` as the run policy, the two runs, no tracks B/C), `rl/conftest.py` (check for references)

**Steps:**
- [ ] `git rm -r rl/studies rl/evaluation rl/track_b rl/track_c` and the track_a ceremony files; move the four level helpers into `curriculum.py`; fix every import (`grep -rn "rl.studies\|rl\.evaluation\|rl\.track_b\|track_a\.recipe\|evaluation_contract\|checkpoint_selection\|checkpoint_metrics" rl/ src/ tests/ release/ plugins/ .claude/ pyproject.toml`).
- [ ] `preflight.py`: keep only `verify_frozen_dataset(repo_root, dataset_root)` (shard-hash check vs both freeze.json files), `require_clean_worktree(repo_root)`, and the tokenizer/prompt sanity check; delete the rest. `train_sft.py`/`train_rl.py` get stubbed imports fixed in Task 6 (temporarily mark them broken with a clear `raise SystemExit("rewritten in Task 6")` if needed to keep pytest green — better: do Task 5 and Task 6 in one commit if the seam is awkward).
- [ ] Full sweep green: `uv run pytest rl/ -q && uv run ruff check rl/`. Commit `"Remove the studies/ceremony apparatus from rl/"` (trailer `Honors:` design commitment; body lists what was deleted and why in two sentences).

### Task 6: lean entry points

**Files:**
- Rewrite: `rl/track_a/train_sft.py` (add `levels: str = "L0"`, `num_epochs: int = 2`, `learning_rate: float = 1e-4`, drop recipe gates, keep `TINKER_API_KEY` check + `verify_frozen_dataset` + `require_clean_worktree` + `bind_execution_boundary`), `rl/track_a/train_rl.py` (drop mastery report; args `current_level`, `replay_levels` (validated by `expected_replay_levels`), `load_checkpoint_path`, `group_size=8`, `reward_policy="shaped_v3b"`, `wandb_project="pixcell-rl"`, `wandb_name`)
- Test: `rl/track_a/tests/test_entry_points.py` — configs build without network (builder construction + arg validation paths; no Tinker client)

**Steps:**
- [ ] Verify in the pinned cookbook how `Config.load_checkpoint_path` loads (weights-only vs optimizer state) — `uv run python - <<'EOF'` inspecting `tinker_cookbook/rl/train.py` — and record the answer as a comment where `run.py` chains stages (old lineage chained on `/weights/final` sampler weights with a fresh optimizer per stage; match that).
- [ ] Write the two entry points (cookbook `Config` assembly copied from the current files minus ceremony; `wandb_project`/`wandb_name` passed through to the cookbook config's wandb fields — check exact field names in cookbook `train.Config`).
- [ ] Tests + `uv run pytest rl/ -q`; commit `"Lean SFT/RL entry points for the two-run campaign"`.

### Task 7: `rl/track_a/run.py` — the two-run orchestrator + probe eval

**Files:**
- Create: `rl/track_a/run.py`, `rl/track_a/probe_eval.py`
- Test: `rl/track_a/tests/test_run_plan.py` (stage plan construction, probe selection determinism — no network)

**Interfaces:**
- `probe_eval.select_probe_tasks(dataset_root, per_level=16) -> list[TaskRecord]`: depth/validation, per level sorted by `sampler.opaque_id`, first 16 — deterministic, no seed.
- `probe_eval.run_probe(checkpoint_or_base: str, tasks, *, out_path) -> dict`: samples 1 completion/task at T=1.0 max_tokens 4096 via `tinker.ServiceClient` sampling client (base model name or `tinker://` path), evaluates through `PixCellEvaluator(require_isolation=True)` batch, writes JSON `{per_level: {level: {executable_rate, mean_iou, mean_shaped}}, overall: …, checkpoint, timestamp}`.
- `run.py` CLI (chz): `--run {A,B}`, `--smoke`, `--confirm-spend PIXCELL_RUNS_V2`, `--runs-root` (default `/Volumes/aadarwal_vx/QPG-MIT/PixCell-training/runs-v2`, fallback `~/pixcell-training/runs-v2`), `--wandb-project pixcell-rl`. Stage plans:
  - Run A: `sft-l0` (levels=L0, 2 epochs) → sanity gate (probe on 8 L0 validation tasks: `executable ≥ 6/8` and `mean_iou > base_probe_l0_mean`, else abort) → `rl-l0 … rl-l4` (30 steps each, replay prefix, chained checkpoints).
  - Run B: `rl-l0 … rl-l4` from base.
  - Smoke: Run B's `rl-l0` only, `max_steps=2`, `groups_per_batch=2`, canaries 8, then print measured token counts + extrapolated full-campaign cost from the smoke `metrics.jsonl`.
  - Probe eval runs at campaign start (base model) and after every stage; results + resolved config + git SHA + `TaskBaseline` dump for all touched tasks written into `<runs-root>/<run-name>/provenance/`.
- [ ] Implement; stage-plan tests green; commit `"Two-run orchestrator with fixed cross-run probe eval"`.

### Task 8: SFT data audit + anisotropy measurement

**Files:**
- Create: `rl/track_a/data_audit.py` (invoked by `run.py` before SFT; also standalone)
- Possibly modify: `rl/common/prompt.py` (+ its tests) — only if measurement says so

**Steps:**
- [ ] `data_audit.py`: for the SFT levels, render every `(prompt, label)` through the real renderer; report max/percentile token lengths; **hard-fail if any label would truncate at `max_length`**; dump 3 decoded datums (text + weight mask summary) to the run dir for eyeball inspection.
- [ ] Anisotropy: one-off script over depth/train — per row, model-image ink bbox aspect vs `footprint_um` aspect; report the distribution of the ratio. If ≥ 10% of rows exceed 1.6×, add the old scale note to `build_prompt_text` (contract bump to `pixcell-direct-reconstruction-v3`, computed only from model-visible inputs: model image ink bbox + footprint), update `test_prompt_contract.py` accordingly; else record the measurement in the run provenance and leave the prompt at v2.
- [ ] Commit `"SFT data audit + anisotropy measurement"` (+ prompt v3 if taken, its own commit).

### Task 9: full-surface green + README + spec sync

- [ ] `uv run pytest tests/ rl/ release/ -q` (the CI surface) and `uv run ruff check .` — fix all fallout.
- [ ] `rl/README.md` and `rl/track_a/README.md` rewritten to describe exactly what exists now (the reward contract table must show `shaped_v3b` with the formula; the two runs; the probe protocol).
- [ ] Update the design spec's §2 if any decision changed during implementation (e.g., prompt v3 taken or not).
- [ ] Commit `"Document the clean training path"`.

---

## Self-review checklist (run after Task 9)
- Spec §2.1 ↔ Tasks 1–4; §2.2 ↔ Tasks 4/6; §2.3 ↔ Task 7 (+ SFT gate); §2.4 ↔ Task 7 probe; §2.5 ↔ Task 7 provenance + Task 6 preflight; §2.7 ↔ Task 5; §2.8 ↔ Task 8. Launch/monitoring are tracker tasks 9–12, not this plan.
- Grep the plan for TBD/TODO — none.
- Type consistency: `TaskBaseline` fields used in Task 3 match Task 1; `reward_for_policy(..., baseline=)` matches Task 4's call; probe JSON keys match Task 7.
