# rl/ — training the blind reconstructor

Two packages, one training path:

| Package | Purpose |
|---------|---------|
| [`common/`](common/) | The measurement layer: hash-verified dataset projection ([`dataset_io.py`](common/dataset_io.py), [`contracts.py`](common/contracts.py)), the versioned blind prompt ([`prompt.py`](common/prompt.py), contract `pixcell-direct-reconstruction-v3`), per-candidate Docker-isolated execution and absolute-scale scoring ([`evaluator.py`](common/evaluator.py), [`isolation.py`](common/isolation.py), [`sandbox/`](common/sandbox/)), and the rectangle baselines behind the shaped reward ([`baselines.py`](common/baselines.py), [`geometry.py`](common/geometry.py)) |
| [`track_a/`](track_a/) | The Qwen training path: reward policies, Tinker Cookbook adapters, deterministic curriculum, lean SFT/RL entry points, and the four-run campaign runner |

The governing invariant is unchanged from the rest of the repository: **the
Python measures; it never searches.** Every reward is recomputed from
artifacts by the deterministic evaluator; no model-reported number enters
the record.

## The reward — `shaped_v3b`

The campaign reward is the private library's proven v3-b signal (the reward
behind the recorded learning runs), constants byte-identical:

```
iou_n  = max(0, (iou − iou_rect) / (1 − iou_rect))       # rectangle-normalized excess IoU
dice_n = likewise
τ      = 0.05 · footprint_diagonal_um
t2b    = exp(−boundary_chamfer_um / τ)
teacher = max(0, t2b − t2b_rect) / max(1 − t2b_rect, 0.3)

crash / timeout / no-gds / syntax           → 0.0
source-rejected (non-catalog geometry)      → 0.0
executable + pure, iou_rect < 0.95          → 0.05 + 0.40·iou_n + 0.15·dice_n + 0.40·teacher
executable + pure, iou_rect ≥ 0.95          → 0.05 + 0.40·iou + 0.15·dice + 0.40·t2b
```

`iou_rect`/`dice_rect` are what a solid rectangle filling the target's
calibrated ink bounding box scores — precomputed once per task
(`common/baselines.py`) and cached; the dataset is frozen, so they are
constants of the release. Normalizing against the rectangle kills the
area-fill attractor and puts every task on one scale; the 0.05 floor keeps
"valid but wrong" distinguishable from "crashed"; the boundary-chamfer
teacher pays for count/boundary progress IoU cannot see; rectangle-like
targets score raw because normalizing against a rectangle that *is* the
answer would make every program identical.

## The four runs

One recipe (Qwen3.6-35B-A3B, LoRA 32, GRPO 8 rollouts × 8 groups/step,
lr 1e-5, temp 1.0, KL 0, importance sampling, 30 steps per level L0→L4 with
the exact 80/20 replay cycle), crossed over ±L0-SFT and thinking budget:

| Run | Operating point | Arm |
|-----|-----------------|-----|
| A `runA-l0sft-rl` | no-think @ 4096 tokens | L0-SFT → RL L0→L4 |
| B `runB-base-rl` | no-think @ 4096 tokens | base → RL L0→L4 |
| C `runC-think-base-rl` | thinking @ 60000 tokens | base → RL L0→L4 |
| D `runD-think-l0sft-rl` | thinking @ 60000 tokens | L0-SFT → RL L0→L4 (gated) |

```bash
# price an operating point first (2 GRPO steps, 2 groups):
python -m rl.track_a.run --smoke nothink --confirm-spend PIXCELL_RUNS_V2
python -m rl.track_a.run --smoke think   --confirm-spend PIXCELL_RUNS_V2

# then each full campaign, one detached pane each:
python -m rl.track_a.run --run A --confirm-spend PIXCELL_RUNS_V2
```

Each stage is a subprocess over [`track_a/train_sft.py`](track_a/train_sft.py)
/ [`track_a/train_rl.py`](track_a/train_rl.py), chained on the previous
stage's final sampler weights; re-running the command resumes the campaign.
A fixed 80-task probe (16 per level from `depth/validation`, sorted opaque
ids) is evaluated at campaign start — the base-model baseline — and after
every stage, so every point on the curve is comparable. SFT arms must beat
the base probe on L0 before RL spends anything.

Requirements: `TINKER_API_KEY` and `WANDB_API_KEY`. Candidate programs
execute behind an AST source gate in a resource-limited subprocess by
default; set `PIXCELL_REQUIRE_ISOLATION=1` to demand the Docker tier
(image named by `PIXCELL_EVALUATOR_IMAGE`, built by
[`common/sandbox/build.py`](common/sandbox/build.py)). Run artifacts land
outside the repository (default `~/pixcell-training/runs-v2/`, override with
`--runs-root`); W&B project `pixcell-rl`. The pinned environment is
[`requirements-lock.txt`](requirements-lock.txt) / [`stack.json`](stack.json).

## Result — the released model

Run B ran to completion (150 GRPO steps, L0→L4) and is the released model:
[`qpaig-mit/pixcell`](https://huggingface.co/qpaig-mit/pixcell). On the
held-out F1–F8 benchmark (8 attempts at T=1.0) it scores mean IoU 0.228 and
best-of-8 0.467, from a base model that produced 0 executable attempts in 64.
Deployed as intended — inside the attempt–measure–revise loop
([`track_a/agent_loop.py`](track_a/agent_loop.py): 8 attempts, then 3 rounds
of 4 champion revisions under number-free verifier feedback) — it reaches
**mean champion IoU 0.491**. The validated evidence (benchmark records, loop
trajectories, champion programs, render gallery) is versioned in
[`data/training/qwen-rl-v2/`](../data/training/qwen-rl-v2/).

The SFT-seeded arms (Run A and every fork from its checkpoints) entered RL
with low policy entropy and collapsed terminally within ~50–60 RL steps; the
thinking pair (C/D) was still mid-campaign at release time and is not part
of this record.

## Preflight

[`track_a/preflight.py`](track_a/preflight.py) is the zero-spend gate the
runner executes before any Tinker client exists: frozen-release digests for
both dataset layers, clean-worktree check, catalog/dataset/conductor
whitelist identity, per-row reference and source validation, prompt-leak
check, SFT token audit (hard-fails on any truncating label), ground-truth
positive control scored through `shaped_v3b`, and the Docker sandbox
self-test.
