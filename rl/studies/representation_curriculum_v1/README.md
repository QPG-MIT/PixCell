# Representation curriculum v1

> **Superseded diagnostic record.** This study and its Qwen 32k/60k
> extensions used the `pixcell-blind-phase-a-direct-v1` prompt contract. That
> one-shot contract did not state the output-file requirement enforced by the
> evaluator, so its measurements are not canonical baselines or paper
> results. The protocol JSON and study files remain unchanged for provenance.
> Current paid launch code rejects this prompt contract.

This archived study recorded preliminary zero-shot measurements before any
curriculum training began. It had two merge boundaries:

1. Phase 0 freezes and validates the protocol, task manifest, prompt, sampling
   adapters, evaluator, result schema, and source SHA without creating a
   Tinker client.
2. Phase 1 samples and evaluates the frozen base models, then commits a
   validated evidence export in a separate PR.

The SFT and RL hypotheses reserved in [`protocol.json`](protocol.json) are not
launchable in either phase.

## Fixed model contract

Each model receives one maximum-visibility image, the physical footprint, the
PixCell primitive catalogue, and the existing blind Phase-A programming task.
It returns one Python program. Display calibration, the target raster,
representation labels, expected code, and verifier diagnostics are not
model-visible.

Every completion passes through the same strict source gate, isolated
execution boundary, GDS render, and absolute-scale IoU evaluator. A model
failure contributes zero IoU to aggregation. A reference or evaluator failure
aborts the wave instead of becoming a zero-scored model attempt.

## Frozen hypotheses

| ID | Purpose | Tasks and attempts |
|---|---|---|
| `RC-H00` | Select the Qwen inference operating point | 40 fixed `depth/validation` tasks, eight per level L0–L4 and one representation per task; thinking on/off × 4,096/16,384 output tokens; two paired attempts per task |
| `RC-H00R` | Resolve truncation at the largest registered Qwen thinking budget | Conditional 32,768-token confirmation only when `qwen-on-16384` has a cap-hit rate above 5% |
| `RC-H01` | Qwen zero-shot F1–F8 baseline | The incumbent `qwen-off-4096` and the selected `RC-H00` arm, omitting a duplicate arm; four attempts per figure |
| `RC-H02` | Inkling zero-shot F1–F8 baseline | Thinking effort 0.9, 20,000 output tokens; four attempts per figure |

The `RC-H00` arms use identical task-attempt seeds. Selection first maximizes
representation-macro mean raw IoU. Arms within 0.01 of the best are ordered by
pure executable rate, estimated uncached cost, median completion tokens, then
arm ID. The rule and all model, renderer, image, context, sampling, pricing,
task, and tracking settings are sealed in
[`protocol.json`](protocol.json). [`task_manifest.json`](task_manifest.json)
binds the exact tasks and source digests.

## Historical launch order

The commands below document how the superseded record was produced. They are
not runnable against the current prompt contract and must not be used to spend
or report a canonical baseline.

The launch must come from a clean checkout at the exact Phase 0 merge SHA.
Mutable output must be outside the repository. Build the committed evaluator
image and export the immutable image ID it prints:

```bash
python rl/common/sandbox/build.py
export PIXCELL_EVALUATOR_IMAGE=sha256:<printed-image-id>

export PIXCELL_STUDY_ROOT=/absolute/path/outside/PixCell
export TINKER_API_KEY=<credential>
export WANDB_API_KEY=<credential>
SOURCE_SHA="$(git rev-parse HEAD)"

PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v1.audit_phase0 \
  --expected-source-sha "$SOURCE_SHA"
```

The audit builds every frozen renderer/prompt combination without creating a
Tinker client, validates all 48 references, executes one accepted program in
the isolated evaluator, and round-trips the attempt-record schema. Only after
it passes, run the Qwen operating-point smoke and complete waves:

```bash
PYTHONPATH=src:. python -m rl.studies.representation_curriculum_v1.run_baseline \
  --hypothesis RC-H00 --wave smoke \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE

PYTHONPATH=src:. python -m rl.studies.representation_curriculum_v1.run_baseline \
  --hypothesis RC-H00 --wave complete \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE
```

The smoke wave records attempt 1 for the first fixed development task in each
of the four arms. The complete wave reuses those receipts and fills two
attempts for all 40 tasks. If its preliminary selection requires `RC-H00R`, run
the conditional confirmation before continuing:

```bash
PRELIMINARY="$PIXCELL_STUDY_ROOT/studies/representation-curriculum-v1/selections/operating_point.preliminary.json"

PYTHONPATH=src:. python -m rl.studies.representation_curriculum_v1.run_baseline \
  --hypothesis RC-H00R --wave complete --selection "$PRELIMINARY" \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE
```

Then start the Qwen and Inkling F1–F8 smoke waves concurrently. Each records
attempt 1 for all eight figures. Inspect and validate those 8-attempt results
per arm before starting the complete waves, which reuse attempt 1 and fill
attempts 2–4:

```bash
SELECTION="$PIXCELL_STUDY_ROOT/studies/representation-curriculum-v1/selections/operating_point.json"

PYTHONPATH=src:. python -m rl.studies.representation_curriculum_v1.run_baseline \
  --hypothesis RC-H01 --wave smoke --selection "$SELECTION" \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE

PYTHONPATH=src:. python -m rl.studies.representation_curriculum_v1.run_baseline \
  --hypothesis RC-H02 --wave smoke \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE
```

Use the same commands with `--wave complete` only after both smoke records pass.
The immutable local receipt is the sampling boundary: restarting a wave
evaluates an existing completion or fills a missing attempt; it does not
resample a saved attempt.

After every complete wave validates, freeze and revalidate the compact Phase 1
record:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v1.freeze_phase1 \
  --external-root "$PIXCELL_STUDY_ROOT" \
  --expected-source-sha "$SOURCE_SHA"

PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v1.freeze_phase1 \
  --external-root "$PIXCELL_STUDY_ROOT" \
  --expected-source-sha "$SOURCE_SHA" \
  --validate
```

The freezer accepts source changes only inside the fixed Phase 1 evidence
directory. The resulting files form the separate Phase 1 PR.

## Record ownership

The external attempt ledger is authoritative while the run is active. It
contains immutable sampling receipts, exact programs, evaluator evidence,
summaries, and the operating-point selection. W&B receives metrics only after
the corresponding local record is durable. A W&B outage is recorded locally
and cannot change an evaluation.

The Phase 1 PR freezes the validated release subset under
[`data/training/representation-curriculum-v1/`](../../../data/training/representation-curriculum-v1/).
Secrets, mutable W&B files, model caches, and checkpoints are never committed.
