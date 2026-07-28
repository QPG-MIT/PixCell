# Representation training v1

This study owns the first training campaign over the released PixCell
curriculum. It compares five Qwen learning paths and one bounded Inkling
policy-improvement path while keeping the model input, evaluator, dataset, and
F1–F8 benchmark fixed.

No command in this directory runs at import time. A paid launch requires the
committed protocol, an exact clean source commit, the pinned runtime, the
immutable candidate sandbox, valid Tinker and W&B identities, an external
ledger, and the explicit `PIXCELL_TRAINING_V1` confirmation.

## Branches

```text
Base Qwen
├── qwen-base-rl-l0 → l1 → l2 → l3 → l4
├── qwen-mixed-sft
│   └── qwen-mixed-rl-l{first unmastered ... L4}
└── qwen-l0-sft
    ├── qwen-sequential-sft-l1 → l2 → l3 → l4
    └── qwen-l0-rl-l1 → l2 → l3 → l4

Base Inkling
└── inkling-l4-rl
```

The pure-RL branch tests whether verifier-only learning can acquire the full
primitive-to-component curriculum directly from base Qwen. The L0 SFT
checkpoint is shared unchanged by the sequential-SFT and
composition-by-RL hypotheses. Mixed SFT supplies the checkpoint for the
strongest-open-model hypothesis. Each new SFT level loads its parent weights
with a fresh optimizer and restarts the linear schedule; that reset is part of
the sequential-SFT hypothesis. The fixed L0→RL path always enters at L1 after
its reviewed L0 checkpoint; it is not blocked by an invented mastery threshold.
The mixed-SFT path evaluates L0–L4 and enters RL at the first level below the
protocol-sealed thresholds of 0.80 mean raw IoU or 0.95 pure-executable rate.

Each Qwen RL level is one optimizer run with sealed ceilings at steps 1, 5, 10,
15, 20, 25, and 30. In the pure-RL branch, L0 begins directly from base Qwen.
Its step-1 smoke establishes rollout health, and an immutable rollout-health
receipt is required before step 5. Starting at step 5, progress is measured on
the same fixed held-out panel: realization slot 6, with exactly one row for
every representation at the current level. A report from that panel gates each
later ceiling. Entry into each pure-RL L1–L4 stage requires two reports from
the exact preceding-level terminal checkpoint: its prior-level slot-6 report
and its pre-update slot-6 baseline on the new level. Both reports are bound
into one approval and canonically recomputed at launch. F1–F8 remains a
periodic transfer report and never gates this curriculum.

The L0-SFT→RL branch uses the same rollout-health and fixed slot-6 cadence from
L1 onward. Its L1 entry is intentionally different: the L0-SFT checkpoint was
produced by an earlier frozen source, so smoke requires its exact parent
receipt plus a reviewed source transition. It does not require the obsolete
1,092-row depth report, F1–F8, or a fabricated same-source level-panel record.
L2–L4 entry requires the preceding completed level's slot-6 report.

In the pure-RL branch, each level first evaluates its actual parent policy on
that level's slot-6 panel, then reuses the identical tasks after steps 5, 10,
15, 20, 25, and 30. For L0, that pre-update parent is base Qwen and the panel
has 93 tasks. For L1 through L4, it is the preceding level's completed
checkpoint evaluated on the new level before its first update. This separates
learning from changes in sampled training-task difficulty. Final checkpoint
selection uses the separate 546-row slot-7 panel across L0–L4. Inkling uses
sealed ceilings at steps 1, 6, and 14. These are continuation waves, not
independently initialized runs.

The 21 exact stage definitions, parent edges, wave ceilings, models, recipes,
dataset release, and evaluation identities are in
[`protocol.json`](protocol.json).

## Policy input and objective

Every policy receives the established direct Phase-A interface:

1. the maximum-visibility component image;
2. the physical footprint;
3. black/white layer semantics;
4. the permitted extended primitive catalogue;
5. the direct one-shot programming contract.

The prompt is assembled by [`rl/common/prompt.py`](../../common/prompt.py).
The image transform is owned by
[`rl/common/preprocess.py`](../../common/preprocess.py). Calibration,
`target_image`, reference code, representation labels, split metadata, and IoU
remain verifier-only.

Qwen SFT places loss on exactly the Python program and the assistant end token.
Prompt tokens, image tokens, and the empty thinking header have zero weight.
RL receives no answer program and optimizes raw absolute-scale IoU. Model
failures receive zero; reference or evaluator failures abort rather than
becoming negative examples. Ports, counts, and structural witnesses remain
diagnostics.

## Frozen recipes

| Policy | Training | Important settings |
|---|---|---|
| Qwen | mixed or level SFT | Qwen3.6 35B A3B, thinking renderer, LoRA 32, batch 64, one physical pass, Adam `1e-4`, linear decay |
| Qwen | curriculum RL | G4, 8 groups per step, `1e-5`, importance sampling, KL 0, 20% earlier-level replay, 30 steps per level |
| Inkling | advanced L4 RL | native TMLv0, effort 0.9, G4, 8 groups per step, `1e-5`, importance sampling, KL 0 |

Qwen and Inkling both use a 1920-pixel longest edge, temperature 1, top-p 1,
and a 60,000-token output ceiling inside the 65,536-token context. The pinned
Cookbook exposes temperature but not top-p in its RL config; the pinned Tinker
SDK default of top-p 1 is asserted by a contract test. Every prompt is rendered
locally before launch and must retain positive context headroom.

SFT stages run continuously to their complete one-pass checkpoint. They are
not stopped after a one-step smoke because the pinned Cookbook finalizes the
SFT epoch state when `max_steps` is reached. Initial health is confirmed from
the first local/W&B telemetry while the same run continues.

RL has no built-in sampling validation. This prevents a one-step 60k smoke
from silently creating dozens of extra completions. F1–F8 and held-out depth
evaluation are explicit checkpoint jobs.

Tinker reuses the mutable alias `final` when a run continues. The study never
uses that alias as an RL promotion identity. Every wave receipt instead binds
the unique numeric checkpoint at that exact ceiling. SFT receipts inventory
the numeric quarter checkpoints and terminal `final`; all mixed-SFT inventory
checkpoints are evaluated on the full 1,092-row depth validation split. The
selected parent is the finite report with the highest representation-macro
mean IoU, then pure-executable rate, then later progress.

## Records and W&B

Set `PIXCELL_TRAINING_ROOT` to storage outside the repository. The external
ledger is authoritative:

```text
$PIXCELL_TRAINING_ROOT/
└── studies/representation-training-v1/
    └── stages/<stage>/runs/<replicate>/
        ├── run_manifest.json
        ├── invocations/
        ├── candidates/
        ├── waves/
        ├── tinker/
        └── wandb/
```

Each manifest binds the source commit, protocol, prompt assets, all frozen
dataset artifacts, runtime and Cookbook checkout, sandbox image, exact finite
task schedule, model, recipe, parent checkpoint, and tracking identity.
Candidate records retain the exact sampled token IDs, raw response, separated
reasoning/final channels, extracted program, stop state, and deterministic
measurement. A crash retry gets a new invocation ID, so it cannot overwrite
earlier paid samples.

`r0-retry1` is reserved for the L0-SFT→L1–L4 RL path after its original `r0`
smoke stopped before Tinker client creation. The original run has no samples,
checkpoints, metrics, or wave receipt and remains excluded from results. The
retry consumes the exact historical `qwen-l0-sft/r0` checkpoint; it is an
operational identity, not a second statistical replicate.

W&B is the live observability mirror:

- entity: `aadarwal-massachusetts-institute-of-technology`
- project: `pixcell-representation-training-v1`
- name: `representation-training-v1/<stage>/<replicate>@<source-sha>`
- group: `representation-training-v1/qwen-open` or
  `representation-training-v1/inkling`
- tags: stage, model, kind, replicate, and hypothesis IDs

The run ID is deterministic in source commit, protocol digest, stage, and
replicate. RL continuation uses `WANDB_RESUME=must`; a fresh stage uses
`WANDB_RESUME=never`. Git and source-code upload are disabled.
Checkpoint and fixed level-panel evaluations are authoritative external-ledger
jobs, not separate W&B training runs. W&B mirrors live optimizer runs; the
immutable evaluation records supply checkpoint-selection and promotion
evidence.

## Zero-spend gate

After this source is committed, run:

```bash
PIXCELL_EVALUATOR_IMAGE='<immutable image digest>' \
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.audit_phase0 \
  --expected-source-sha "$(git rev-parse HEAD)"
```

It checks all four initial roots:

- `qwen-mixed-sft` over all 3,468 depth training rows;
- `qwen-l0-sft` over all 642 L0 training rows;
- `qwen-base-rl-l0/smoke` over the 642 L0 training rows;
- `inkling-l4-rl/smoke` over the 648 L4 training rows.

The audit makes no model request. It hashes every frozen release artifact,
tokenizes every selected policy input, verifies every source and reference,
seals the exact task batches, checks the installed Cookbook source commit, and
executes a known-good program inside the immutable sandbox.

## Initial start order

The first paid starts are deliberately staggered:

1. evaluate base Qwen on `level-progress-l0` and seal its 93-row slot-6
   baseline before any pure-RL update;
2. start `qwen-mixed-sft/complete`, confirm its first metric and local
   checkpoint activity without stopping it;
3. start `qwen-l0-sft/complete`, confirm the same;
4. start `inkling-l4-rl/smoke`, which ends after one update;
5. start `qwen-base-rl-l0/smoke`, which is now authorized by the sealed base
   baseline and ends after one update;
6. evaluate the resulting checkpoints before approving any dependent stage.

The guarded launcher exposes no model, data, optimizer, token, schedule, or
W&B override:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.run_stage \
  --stage <sealed-stage> \
  --wave <sealed-wave> \
  --replicate r0 \
  --expected-source-sha "$(git rev-parse HEAD)" \
  --confirm-spend PIXCELL_TRAINING_V1
```

Dependent stages fail closed until their parent checkpoint and required
evaluation or promotion receipt exist. Repeating a completed command verifies
its immutable receipt and exits without touching Tinker or W&B.

## Evaluation and promotion

The progress panel is one attempt on each F1–F8 figure. The depth panel is the
full 1,092-row held-out-parameter split. The Inkling promotion panel contains
36 L4 anchors, six anchors from each earlier level, and F1–F8. Reference
rasters, calibration, labels, and target code never enter model messages.

Evaluate one checkpoint named in its wave receipt:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.evaluate_checkpoint \
  --repo-root "$(pwd)" \
  --stage <checkpoint-stage> \
  --wave <checkpoint-wave> \
  --checkpoint-name <exact-inventory-name> \
  --replicate r0 \
  --panel <progress|depth-validation|inkling-promotion|level-progress-l0..l4> \
  --source-git-sha "$(git rev-parse HEAD)" \
  --wave-receipt-record-sha256 <receipt-record-sha256> \
  --external-root "$PIXCELL_TRAINING_ROOT" \
  --confirm-spend PIXCELL_TRAINING_V1
```

The final F1–F8 benchmark is a separate, reporting-only v2 panel; it does not
change progress, depth, or promotion records. It makes four independently
seeded requests per figure (32 total), resumes only missing attempts, and
reports mean@1 plus per-figure and aggregate best@4. Its records live under
`evaluations/<wave>/<checkpoint>/final-benchmark-best4-v2/`:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.evaluate_final_benchmark \
  --repo-root "$(pwd)" \
  --stage <checkpoint-stage> \
  --wave <checkpoint-wave> \
  --checkpoint-name <terminal-inventory-name> \
  --replicate r0 \
  --source-git-sha "$(git rev-parse HEAD)" \
  --wave-receipt-record-sha256 <receipt-record-sha256> \
  --external-root "$PIXCELL_TRAINING_ROOT" \
  --confirm-spend PIXCELL_TRAINING_V1
```

The mixed-SFT renderer postmortem is a fixed, non-canonical diagnostic. It
samples only the final checkpoint with `qwen3_5_disable_thinking` and steps
14, 28, and 42 with `qwen3_5`, once each on F1–F8. Its 32 rows live under
`diagnostics/qwen-sft-renderer-diagnostic-v1/`, use a diagnostic-only schema,
and are explicitly ineligible for checkpoint promotion. Sampling the three
periodic checkpoints is a deliberate postmortem-only exception to the study's
terminal-checkpoint evaluation rule:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.evaluate_renderer_diagnostic \
  --repo-root "$(pwd)" \
  --evaluator-source-git-sha "$(git rev-parse HEAD)" \
  --producer-wave-receipt-record-sha256 <mixed-sft-receipt-record-sha256> \
  --external-root "$PIXCELL_TRAINING_ROOT" \
  --confirm-spend PIXCELL_TRAINING_V1
```

After reviewing that immutable report, bind it to exactly one dependent wave:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.record_approval \
  --stage <dependent-stage> \
  --wave <dependent-wave> \
  --replicate r0 \
  --evaluation-stage <checkpoint-stage> \
  --evaluation-wave <checkpoint-wave> \
  --evaluation-checkpoint <exact-inventory-name> \
  --evaluation-report-record-sha256 <report-record-sha256> \
  --expected-source-sha "$(git rev-parse HEAD)" \
  --confirm-approval PIXCELL_APPROVE_TRAINING_V1
```

Approvals bind the report, source commit, protocol digest, task panel,
checkpoint inventory, training receipt, and selection decision. They cannot be
reused for a different wave or checkpoint. The launcher treats the stored
approval as an index and canonically revalidates its bound report and metrics
before every paid continuation.

Pure-RL L1–L4 entry evaluates the same parent terminal checkpoint twice: once
on the preceding level's slot-6 panel and once on the new level's slot-6 panel.
Pass the preceding-level report as the primary evaluation above and the
new-level report as:

```bash
  --entry-baseline-report-record-sha256 <new-level-report-record-sha256>
```

The combined approval fails unless both reports resolve to the same parent
stage, wave, checkpoint, checkpoint inventory, run manifest, and wave receipt.

The L0-SFT→L1-RL smoke is the one receipt-only exception. It does not invent or
wait for an evaluation report. At the clean consumer commit, explicitly review
and enumerate every path changed since the source commit in the immutable
L0-SFT manifest:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.record_parent_transition \
  --replicate r0 \
  --expected-source-sha "$(git rev-parse HEAD)" \
  --approve-changed-path <first-exact-changed-path> \
  --approve-changed-path <second-exact-changed-path> \
  --confirm-approval PIXCELL_APPROVE_TRAINING_V1
```

This approval recomputes the parent manifest, terminal receipt, invocation,
checkpoint inventory, local artifact hashes, unchanged prompt, dataset, model,
SFT recipe and programming contract, plus the full ancestor-to-consumer Git
transition. The L1 smoke launcher revalidates all of it before W&B or Tinker.

An evaluation must always run from the same clean commit as its training
manifest. To adopt that already-reviewed evidence from a later descendant,
record a v2 approval at the clean consumer commit and explicitly enumerate the
complete reviewed Git path scope:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_training_v1.record_approval \
  --stage <one-dependent-stage> \
  --wave <one-dependent-wave> \
  --replicate r0 \
  --evaluation-stage <producer-checkpoint-stage> \
  --evaluation-wave <producer-checkpoint-wave> \
  --evaluation-checkpoint <exact-inventory-name> \
  --evaluation-report-record-sha256 <producer-report-record-sha256> \
  --evidence-source-sha <producer-commit> \
  --expected-source-sha "$(git rev-parse HEAD)" \
  --approve-changed-path <first-exact-changed-path> \
  --approve-changed-path <second-exact-changed-path> \
  --confirm-approval PIXCELL_APPROVE_TRAINING_V1
```

Every path from `git diff --name-status --no-renames <producer> HEAD` must
appear exactly once. The approval records both commit trees, ancestry, and a
plumbing-level inventory of every path, status, mode, and old/new object ID.
It also binds the producer report and evaluation manifest, training receipt
and checkpoint inventory, and all protocol, prompt, dataset, model/renderer,
sampling, and sandbox evidence. The dependent child manifest embeds that one
stage/wave/replicate transition. A same-source approval remains byte-for-byte
v1 and must omit both transition flags.

## Baseline completion

Attempts two through four of the zero-shot Qwen and Inkling F1–F8 baselines
remain the separate `representation-curriculum-v2` study. They are evaluation
only and do not block training. They may resume in the background with that
study's `complete` wave, but local Docker evaluation should not contend with a
live RL rollout unless a host-wide worker budget is in place.
