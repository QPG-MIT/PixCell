# Visual signal experiments on our own compute

Start with [measured results and current service lifetime](RESULTS.md),
[experiment design](DESIGN.md), and [GLM training feasibility](MODEL_FEASIBILITY.md).

This package separates dataset/prompt integrity, model sampling, artifact
measurement, and eventual gradient updates. The offline audit performs **no
training and no model API calls**. It measures the same candidate programs
once, then applies the existing `raw_iou`, `validity_floor`, and `shaped_v3b`
policies. It imports no Tinker modules.

## Freeze a split before comparing signals

The released depth validation rows are new parameter realizations of families
also present in released training. They are useful interpolation checks, but
do not establish generalization to unseen representations. This experiment
view repartitions both released splits without changing any dataset files.

```bash
uv run python -m rl.contract_algos.splits \
  --out rl/contract_algos/runs/split-seed17.json
```

All rows with a common `leakage_group_id` stay together. Groups linked by
identical model-image or target-image bytes are merged transitively, even if
their footprints differ. Component hashes assign 70/15/15 train/validation/test
in expectation; actual counts by curriculum level are recorded. This prevents
declared group leakage and exact raster duplicates; it does not prove that all
semantic near-duplicates have been excluded. Review the level counts before
training and do not change seeds after looking at model scores.

The manifest binds frozen Parquet checksums, prompt asset hashes, individual
image/target/code hashes, and the assignment. Files are created exclusively;
rerunning into an existing path refuses to overwrite it. Use a fresh base
checkpoint: old PixCell adapters may have seen rows now assigned to holdout.
Choose reward variants on validation only and reserve test for final evaluation.

## Measure fixed controls

```bash
uv run python -m rl.contract_algos.audit \
  --manifest rl/contract_algos/runs/split-seed17.json \
  --controls --per-level 1 \
  --out rl/contract_algos/runs/controls-seed17.json
```

This runs one deterministically selected task per level through the canonical
evaluator with four controls: its frozen ground-truth program, a full-footprint
rectangle, a syntax failure, and rejected impure source. These trusted controls
use the evaluator's bounded subprocess path. The report includes programs,
render hashes, metric diagnostics, statuses, baselines, each reward component,
within-task ranks, reward spreads, and centered/standardized advantages. A
positive group variance means the candidate set offers a relative learning
signal; it does not establish a useful optimizer update. Controls reveal
reward behavior, not which reward will produce the best trained model.

Positive controls require successful execution and ground-truth IoU at least
0.97 (the existing preflight threshold). A failed control audit still writes
diagnostics and exits unsuccessfully. The default is two evaluator workers;
`--workers` and `--execution-timeout` are recorded in each artifact. Apply the
same execution bound to every model arm. Cold dependency imports can cause
timeouts on a busy machine; repair that measurement setup before interpretation.
Use `--controls-container` with `PIXCELL_EVALUATOR_IMAGE` set to run the same
trusted controls inside the model-program sandbox before live experiments.
The audit records the immutable sandbox image identity and measurement-source
hashes so environment or evaluator changes remain visible.

The rectangle receives only the executable floor under `shaped_v3b` on
non-rectangle targets; near-rectangle targets intentionally use raw components.
The boundary term can distinguish partially correct structure at similar IoU.
IoU and Dice are monotonically related and should not be interpreted as two
independent geometric observations.
On groups where every program executes, `validity_floor` is an affine transform
of `raw_iou`: standardizing each group yields the same relative advantages.
They differ in credit around failed programs. Pairwise policy comparisons in
the report expose changes to order and tied top choices.

## Rescore actual rollouts

An inference sampler writes one JSON object per line:

```json
{"task_id":"opaque_id_from_manifest","candidate_id":"sample-0","completion":"import gdsfactory as gf\n...","model":"exact-model-revision"}
```

The other sampler metadata is preserved. Each `(task_id, candidate_id)` must be
unique and every task must belong to the selected partition. Programs are
scored once and shared across the three policies, avoiding sampling differences
in the offline comparison.

```bash
uv run python -m rl.contract_algos.audit \
  --manifest rl/contract_algos/runs/split-seed17.json \
  --partition validation --candidates /path/to/rollouts.jsonl \
  --out rl/contract_algos/runs/validation-rescore.json
```

Imported model programs require the existing immutable Docker execution
boundary (`rl/common/sandbox/README.md`); they cannot opt into the trusted-control
subprocess path. The evaluator retries infrastructure faults once. Any remaining
reference/infrastructure fault aborts the audit rather than becoming a model
failure reward. Model syntax/runtime/purity failures are typed zeros. Final
accepted devices still require `homi.conductor.verify_cell` and relevant knob
response checks; the reward audit does not claim that extra verification.

## What establishes the best training signal

First compare all policies on identical base-model samples, checking executable
rate, constant-reward group fraction, top-candidate rank disagreement, and
rectangle preference. Then run equal-budget gradient-update arms from the same
fresh base checkpoint with fixed prompts, splits, task schedules, generation
budgets, and several seeds. Compare raw held-out IoU, executable/pure rate,
boundary distance, best-of-k, diversity, and GPU time/tokens—not training reward
alone. Keep input representation, SFT warmup, curriculum, KL regularization,
and reward policy as separate interventions. Only add structural or intermediate
credit signals after establishing these baselines and their failure modes.

Existing Tinker entrypoints own remote training and checkpoint management.
Serving an OpenAI-compatible model supplies rollouts; it does not supply
backpropagation, optimizer state, adapter updates, or checkpoint synchronization.
Those require a separate, verified local training backend for the chosen model.

## Collect and log new evidence

For a locally reachable dedicated server, use its deployment metadata and a
credential in `CONTRACT_ALGOS_API_KEY` (never a command-line argument):

```bash
uv run python -m rl.contract_algos.probe \
  --manifest rl/contract_algos/runs/split-seed17.json \
  --deployment-metadata /path/to/metadata.json \
  --base-url http://127.0.0.1:18153/v1 \
  --tasks 2 --attempts 4 --level L0 \
  --out rl/contract_algos/runs/glm-rollouts.jsonl
```

The actual private cluster route is a Slurm job step, documented in
[infra/README.md](infra/README.md). `infra/collect_prepared.py` accepts request
bodies created by `probe.request_body` and reads the per-job key on the node.
It stores the original response, checkpoint revision, image digest, token usage
and generation latency. The audit stores evaluation latency separately.

Upload only explicit report artifacts to the existing W&B project:

```bash
uv run --with wandb==0.28.0 python -m rl.contract_algos.telemetry \
  --kind signal-audit --name controls-seed17 \
  --report rl/contract_algos/runs/controls-seed17-container-fixed.json
```

An `optimizer-smoke` upload requires both its successful `result.json` and its
matching model/revision/script `config.json`. Never upload a whole remote
runtime directory: it also contains private server credentials.
