# PixCell Track A

Track A trains one self-hostable vision-language model to reconstruct a shown
photonic geometry as a primitive-only GDSFactory program. This directory is the
training boundary over the frozen PixCell Dataset. It does not contain private
paper benchmarks, historical rollouts, or model checkpoints.

## What the model receives

The `pixcell-direct-reconstruction-v2` contract is a one-shot adaptation of
the blind Phase-A reconstruction task. It has one user turn:

1. the row's maximum-visibility `image`;
2. its physical `footprint_um`, formatted as the historical footprint JSON;
3. the exact PixCell GDSFactory extended primitive catalogue;
4. the direct Phase-A programming contract used by both training and
   evaluation.

There is no system turn. The model does not receive the dataset's stored
`instruction`, display calibration, `target_image`, row ID, class name,
representation metadata, ports, structural witnesses, or expected code.
The programming contract states the required construction and serialization
rules: GDSFactory 9.20.7, material on layer `(1,0)`, catalogue-only primitive
constructors, top-level live function tunables, an `@gf.cell` device, complete
executable Python, and the exact output file `device.gds`.

This is not the full tool-using HOMI Phase-A loop. That system lets an agent
derive calibration, inspect deterministic diffs, and revise its program. The
direct contract deliberately presents the same blind device inputs without
those tools or verifier feedback so it can be used consistently for SFT,
one-shot RL rollouts, and direct-policy evaluation.

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
2. executes the original complete program in a fresh, networkless,
   resource-limited container;
3. requires a non-empty `device.gds`;
4. renders layer `(1,0)` with Michaelangelo's absolute-scale, left-aligned and
   vertically centered mapping;
5. returns full-precision raw IoU and diagnostics.

Syntax, purity, runtime, missing-GDS, and invalid-GDS outcomes are model
failures. Broken references and evaluator faults are separate typed outcomes.
Evaluator faults are retried once and then abort the paid stage. Broken
references abort immediately. Neither can be converted into zero-quality
programs or silently dropped from a group.

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
PYTHONPATH=src:. python -m rl.track_a.preflight --audit-only
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
weights checkpoint and its full executable mastery report. RL and checkpoint
evaluation also require the immutable local candidate image:

```bash
python rl/common/sandbox/build.py
export PIXCELL_EVALUATOR_IMAGE=sha256:<printed-image-id>
```

At SFT steps 14, 28, and the final step 55, export the corresponding sampler
checkpoint and run two distinct measurements:

1. Run `evaluate_checkpoint.py` at `k=1` over all of
   `depth/validation`. Geometry reports reject `--rows` and `--levels`; this is
   always the complete 1,092-task, 546-representation checkpoint quality
   report.
2. Run the same command with `--behavioral-probe --k 4 --rows 40` and
   exactly one `--levels` value set to the first curriculum level not yet
   mastered. The
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
is only for evaluation. The guarded RL launch requires those paths to be the
`weights` and `sampler_weights` variants of the same Tinker checkpoint, binds
the weights path and the mastery-report SHA-256 into preflight, and revalidates
the report before creating a paid client. Evaluation similarly binds the exact
sampler path and a new JSON output below `rl/track_a/runs/`; it will not
overwrite an existing report.

Every executable report carries the frozen depth release digest, source Git
commit, model, renderer, split, exact level and task-set digest, task and
attempt counts, and sampling parameters. Selection recomputes that contract
from the current committed repository and rejects partial reports, stale or
mismatched report pairs, non-finite or out-of-range metrics, and behavioral
probes other than the exact 40-prompt G4 contract.

Track A refuses RL or checkpoint evaluation unless its per-candidate Docker
boundary is active. The launcher retains Tinker network access; each sampled
program receives no network, credentials, host filesystem, or mutable root
filesystem. The boundary is defense in depth around the canonical source
policy, not a claim that arbitrary Docker-hostile code is universally safe.
