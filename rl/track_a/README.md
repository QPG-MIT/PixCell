# PixCell Track A

Track A trains one self-hostable vision-language model to reconstruct a shown
photonic geometry as a primitive-only GDSFactory program. This directory is the
training boundary over the frozen PixCell Dataset. It does not contain private
paper benchmarks, historical rollouts, or model checkpoints.

## What the model receives

The `pixcell-blind-phase-a-direct-v1` contract has one user turn:

1. the row's maximum-visibility `image`;
2. its physical `footprint_um`, formatted as the historical footprint JSON;
3. the existing PixCell GDSFactory primitive catalogue;
4. the existing Phase-A recreation task.

There is no system turn. The model does not receive the dataset's stored
`instruction`, display calibration, `target_image`, row ID, class name,
representation metadata, ports, structural witnesses, or expected code.

For SFT, the assistant label is the row's complete `code`. In other words, an
SFT example is still an image-and-code pair: the image and fixed task context
form the input, and the code is the supervised output.

## Dataset boundary

Track A pins `qpaig-mit/pixcell` at revision `v2.0.0`. The model-facing
configuration is `depth`; the separately keyed `references` configuration is
verifier-only.

The `depth` table supplies the maximum-visibility `image`, physical
`footprint_um`, supervised `code`, and private sampler metadata. It does not
supply a ready-made natural-language instruction. At runtime Track A constructs
the prompt from the image and footprint plus the versioned PixCell programming
contract described above. Sampler metadata selects and balances tasks but is
never serialized into the prompt.

The `references` table supplies the target raster and verification metadata,
joined by opaque row ID only after the model produces a program. It must never
be included in SFT messages, generation prompts, or model-visible tool output.
Local training uses the equivalent frozen Parquet files under `dataset/`; the
public repository and revision identify the portable release of the same
contract.

## What the verifier sees

Only after a completion exists, the evaluator receives the private
`target_image` and `footprint_um`. It:

1. compiles and applies the canonical AST source policy before execution;
2. executes the original complete program in a fresh, resource-limited child;
3. requires a non-empty `device.gds`;
4. renders layer `(1,0)` with Michaelangelo's absolute-scale, left-aligned and
   vertically centered mapping;
5. returns full-precision raw IoU and diagnostics.

Syntax, purity, runtime, missing-GDS, and invalid-GDS outcomes are model
failures. Broken references and evaluator faults are separate typed outcomes.
Evaluator faults are retried once and then drop the rollout group; they are
never silently converted into zero-quality programs.

The initial reward is intentionally small:

```text
model failure                     0
valid primitive-only program      0.05 + 0.95 * raw IoU
reference/evaluator failure       no policy reward
```

Dice, calibrated render information, and artifact hashes are recorded as
diagnostics. They do not create reward cliffs in the first pilot. Port, count,
and structural checks can be added later as diagnostics without changing the
initial reward contract.

## Training recipe

The committed Qwen recipe is
[`config.json`](config.json).

SFT visits every one of the 3,468 `depth/train` rows exactly once. Batches
interleave levels and representations. After assistant-token normalization,
the row loss is weighted so each level, then each representation within that
level, receives equal total loss mass. No row is omitted or duplicated. The
1,092 parameter-holdout rows are used only for validation.

RL resumes the selected SFT checkpoint. Each task is sampled four times (G4).
All four programs are independently measured; the cookbook centers advantages
within that group, so programs above their prompt's group mean are reinforced
and programs below it are suppressed. This is not best-of-four branch search
and the model is not shown which answer won.

Each paid RL stage is bounded to 30 steps, 8 prompt groups per step, and 4
rollouts per group, with checkpoints and executable evaluation every 5 steps.
The first stage begins at the first level the selected SFT checkpoint has not
already mastered, rather than assuming L0. After promotion, every five-step
cycle uses an exact 80/20 current-level to earlier-level replay schedule.

## Zero-spend preflight

Use the Python 3.13 environment from the dataset release and expose both source
roots:

```bash
PYTHONPATH=src:. python -m rl.track_a.preflight
PYTHONPATH=src:. pytest -q rl/common/tests rl/track_a/tests
```

The preflight checks every depth source and reference, catalogue/source-gate
parity, prompt leakage, frozen row counts, and representative ground-truth
self-scores. The paid-launch form also tokenizes all 3,468 SFT rows and proves
that none exceed 6,144 tokens. It does not create a Tinker client or spend
money.

Both launchers are spend-locked:

```bash
PYTHONPATH=src:. python -m rl.track_a.train_sft
PYTHONPATH=src:. python -m rl.track_a.train_rl
```

They exit before creating a client unless the matching explicit
`confirm_spend` value is supplied. RL additionally requires the selected SFT
checkpoint path.

At SFT steps 14, 28, and the final step 55, export the corresponding sampler
checkpoint and run two distinct measurements:

1. Run `evaluate_checkpoint.py` at `k=1` over all of
   `depth/validation`. This is the checkpoint quality report.
2. Run the same command with `--behavioral-probe --k 4 --rows 40` and
   `--levels` set to the first curriculum level not yet mastered. The
   deterministic balanced sampler spreads this small probe across
   representations in that level.

The G4 probe records, for every prompt, hashes and counts of distinct extracted
programs and successful calibrated renders. It also reports the fraction of
groups with nonconstant rewards and the mean within-group reward standard
deviation. It declares collapse only when every probed prompt returns the same
program, or when every prompt has at most one successful render and a constant
reward. These behavioral quantities are diagnostics and a conservative
collapse veto, never checkpoint-ranking features.

For example:

```bash
PYTHONPATH=src:. python -m rl.track_a.evaluate_checkpoint \
  --confirm-spend TRACK_A_EVAL \
  --sampler-path "$STEP14_SAMPLER" \
  --output rl/track_a/runs/step14-k1.json

PYTHONPATH=src:. python -m rl.track_a.evaluate_checkpoint \
  --confirm-spend TRACK_A_EVAL \
  --sampler-path "$STEP14_SAMPLER" \
  --behavioral-probe --k 4 --rows 40 --levels L2 \
  --output rl/track_a/runs/step14-g4.json
```

Pair all checkpoint reports by sampler path and select with:

```bash
PYTHONPATH=src:. python -m rl.track_a.select_sft_checkpoint \
  --geometry-reports rl/track_a/runs/step14-k1.json \
    rl/track_a/runs/step28-k1.json rl/track_a/runs/step55-k1.json \
  --behavioral-reports rl/track_a/runs/step14-g4.json \
    rl/track_a/runs/step28-g4.json rl/track_a/runs/step55-g4.json
```

After vetoing explicit sampling collapse, selection uses only the full `k=1`
representation-macro raw IoU, with pure-executable rate as a tie-breaker.
Validation NLL is logged but does not choose the checkpoint. The selected
checkpoint's **weights** path is then passed to `train_rl.py`; its sampler path
is only for evaluation.

The child process boundary is resource isolation, not a general security
sandbox. Run model-authored programs inside the deployment's normal container
or VM boundary.
