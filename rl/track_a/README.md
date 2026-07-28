# PixCell Track A

Track A trains one self-hostable vision-language model
(`Qwen/Qwen3.6-35B-A3B`) to reconstruct a shown photonic geometry as a
primitive-only GDSFactory program. This directory is the training boundary
over the frozen PixCell Dataset. It does not contain private paper
benchmarks, historical rollouts, or model checkpoints.

## What the model receives

The `pixcell-direct-reconstruction-v3` contract is one blind user turn:

1. the row's maximum-visibility `image`;
2. its physical `footprint_um` as the historical footprint JSON, plus —
   when the image's aspect is distorted more than 1.6× relative to the
   footprint — an honest per-axis render-scale note computed from the
   image's own ink bounding box (half the training rows are distorted
   past that threshold; 78% of L4);
3. the exact PixCell GDSFactory extended primitive catalogue;
4. the direct Phase-A programming contract.

There is no system turn. The model never receives the dataset's stored
`instruction`, display calibration, `target_image`, row ID, class name,
representation metadata, ports, structural witnesses, or expected code.
The SFT user message is byte-identical to the RL sampling prompt — prompt
identity is what makes an SFT checkpoint resumable by RL.

## Reward

Three policies live in [`reward.py`](reward.py); the campaign uses
`shaped_v3b` (see [`../README.md`](../README.md) for the formula and its
rationale). `raw_iou` and `validity_floor` remain for the record. Fault
attribution is absolute: model failures are typed zeros, reference or
evaluator faults are `None` and abort the run rather than becoming biased
zeros.

## Files

| File | Role |
|------|------|
| [`reward.py`](reward.py) | The three reward policies + the shaped-component breakdown |
| [`tinker_data.py`](tinker_data.py) | Cookbook adapters: supervised dataset (level-filtered, exactly-once stratified pass, hierarchical loss mass), the single-turn Env, group builder, RL dataset (staged level + exact 80/20 replay + seed-7 validation canaries) |
| [`curriculum.py`](curriculum.py) | Level algebra and the deterministic schedules |
| [`train_sft.py`](train_sft.py) / [`train_rl.py`](train_rl.py) | Lean single-stage entry points (chz CLIs) |
| [`run.py`](run.py) | The four-run campaign runner: stage sequencing, checkpoint chaining, SFT sanity gate, fixed probe, provenance |
| [`probe_eval.py`](probe_eval.py) | The fixed 80-task cross-run probe |
| [`preflight.py`](preflight.py) | The zero-spend gate (digests, whitelists, token audit, ground-truth control, sandbox self-test) |
| [`launch.py`](launch.py) | Sandbox binding + preflight subprocess wrapper |

## Commands

```bash
python -m rl.track_a.run --smoke nothink --confirm-spend PIXCELL_RUNS_V2
python -m rl.track_a.run --run A --confirm-spend PIXCELL_RUNS_V2   # or B/C/D
```

Every launch requires `TINKER_API_KEY`, `WANDB_API_KEY`,
`PIXCELL_EVALUATOR_IMAGE` (the immutable sandbox), a clean worktree, and
passing preflight. Spend is confirmed explicitly; nothing launches without
`--confirm-spend PIXCELL_RUNS_V2`.
