# Visual signal experiments on owned compute

This worktree separates three questions: does the chosen checkpoint serve image
requests, can its weights be trained here, and which feedback improves held-out
image-to-program performance? Passing one does not establish the next.

The initial model is `zai-org/GLM-5.3-Flash`. Its dedicated Engaging endpoint is
useful for baseline sampling, verifier-guided revision and candidate collection.
The image-conditioned optimizer path for this 320B MoE is a separate engineering
milestone. A cached Qwen3-VL-30B-A3B-Instruct can qualify our own GPU training
plumbing at much lower cost; results on Qwen are not GLM learning results.

## What we keep from Tinker

The trusted dataset projection, fixed image-and-footprint prompt, source purity
gate, calibrated evaluator, failure attribution and reward definitions remain
the same. Tinker currently supplies the remote training client, model kernels,
optimizer, distributed execution, sampler checkpoint publication and recovery.
A private vLLM endpoint replaces sampling only. Our own training stack must also
own backward passes, optimizer state, adapter/checkpoint identity, policy/sampler
version synchronization, queue recovery and training metrics.

Do not silently replace a Tinker-trained model with a similarly named checkpoint.
Model, revision, tokenizer/processor, prompt, image preprocessing, precision,
trainable modules, seed, context budget and weights lineage belong in every run.

## Experiment sequence

1. **Measurement controls.** Freeze a manifest; recompute ground-truth,
   bounding-box rectangle and invalid-program controls using the existing
   evaluator. Score identical candidates with every policy. This identifies
   flat rewards and shortcut attractors without training or sampling expense.
2. **Frozen-policy sampling.** Use the same starting checkpoint, tasks,
   temperature and token budgets for a candidate bank. Measure executable rate,
   within-task reward spread, ties, truncation and ranking disagreements. This
   diagnoses the signal available to the optimizer; it cannot establish which
   policy would learn best after the sampling distribution changes.
3. **Optimizer qualification.** On a supported smaller VLM, first use synthetic
   shape images and masked color/shape labels; obtain finite loss and nonzero trainable
   gradients, perform an optimizer step, save/reload an adapter and verify its
   tensors changed. Establish image-conditioned input handling and memory use.
   One successful update is an infrastructure result, not evidence of learning.
   Then repeat with canonical PixCell image prompts and assistant-code labels
   before claiming the complete task-specific training path has passed.
4. **Matched training pilot.** Compare reward arms from identical initialization
   and fixed grouped training tasks, initially short enough to inspect every
   rollout. Record optimizer steps, sampled tokens, accepted samples and GPU
   hours. Keep prompt, curriculum, KL, rollout-group size and LoRA targets fixed.
   Use multiple seeds before choosing an arm. No uncontrolled concurrent changes
   to SFT warm-start, reasoning budget and reward policy.
   Plan at least three seeds per arm, then use measured variance to assess
   uncertainty; three seeds alone do not guarantee sufficient statistical
   power. Freeze and hash the hypotheses, arm definitions, budgets, practical
   improvement margin and decision rule before launching the comparison.
5. **Held-out evaluation.** At fixed checkpoints, evaluate every arm on the same
   validation tasks; choose the configuration on validation, then evaluate once
   on the reserved test groups. Report pass@1, best-of-k at identical k, calibrated
   IoU, boundary error, source purity, crash/truncation rates and artifact-based
   parametric/knob acceptance. The conductor remains the final acceptance gate.
6. **Scale only after evidence.** Port the winning recipe to GLM only once a
   supported image-conditioned backward/checkpoint/sampler round trip has passed
   on the required hardware. A serving benchmark is not that round trip.

## Signal arms and what each tests

| Arm | Hypothesis or limitation |
|---|---|
| `raw_iou` | Direct sparse overlap reward; may prefer filled rectangles or fail to distinguish near misses. |
| `validity_floor` | Separates executable but poor geometry from syntax/runtime failures. Among all-valid candidates it is an affine transform of IoU. With per-group centered/standardized advantages, that alone may produce effectively the same update. |
| Planned: validity-only | Rewards successful execution without a geometry term; distinguishes improved formatting/API competence from improved geometric reconstruction. Not yet implemented in the three-policy audit. |
| `shaped_v3b` | Existing rectangle-normalized overlap plus boundary proximity gives credit for structure beyond area filling. Test the ranking and learning benefit rather than assuming it. |
| Later: normalized overlap without boundary term | Isolates the contribution of boundary feedback; keep reward range/advantage normalization comparable. |
| Later: feedback-conditioned revision | Tests richer information in the policy context, which is a separate intervention from changing a scalar reward. Hold interaction/token budget constant. |

Dice is a monotone function of IoU for binary masks on the same canvas; adding
both does not provide independent geometric evidence. Boundary measurements can
change candidate rankings, but they are not a topology guarantee. For ports,
connectivity and minimum-feature constraints, add deterministic diagnostics and
validate their fidelity before promoting them to rewards. Do not score a
model's own description of whether its geometry is correct.
Where retained references provide `topology_json` or `port_signature_json`,
qualify deterministic comparison to those targets as independent endpoints.
Report missing or unsupported annotations explicitly; do not equate source
primitive counts with connectivity correctness.

The previous SFT-seeded campaign lost policy diversity, while the base-to-RL arm
completed. That history motivates a controlled warm-start ablation; it does not
show that SFT is universally harmful. Track candidate diversity, entropy,
fraction of groups with nonzero advantage and rectangle-like failure modes.

## Leakage, failures and comparisons

The released depth validation set contains held-out realizations of training
representation families. It is useful for parameter generalization, but cannot
support a claim about unseen families. The new manifest groups leakage IDs and
duplicate image/target hashes before assigning partitions. It retains the
original release split in metadata and never modifies the release. A previously
trained checkpoint may have seen these data; use a base checkpoint for a new
training study and do not label this split as unseen to historical checkpoints.

Do not repeatedly tune on F1–F8. They are a tiny external check, already used in
the published work. Broader family holdouts and paired confidence intervals
across independent groups provide stronger evidence. Bootstrap groups rather
than treating correlated realizations as independent examples.

Reference corruption, evaluator crashes and infrastructure errors are masked or
abort the run. They never become zero-reward model examples. Store source and
render identities beside recomputed measurements; candidate-reported scores are
ignored. Truncated generations remain explicit and consume the same token
budget accounting as complete ones.

The corrected root-cell extraction changes evaluator identity. Every new arm
and baseline must use the same corrected verifier. Historical scores, including
Run B, need paired artifact rescoring and provenance checks before direct
comparison. Preserve the frozen record; document any verified changed published
numbers in a separate dated addendum. A shared call path establishes potential
exposure, not measured historical impact or a demonstrated training bias. The
final controls and eight-candidate signal audit already use the corrected
extractor; see [peer reconciliation](PEER_DECISIONS.md).

## Tracking and isolation

Project: [visual_signal_algorithms](https://forge.coreweave.com/wandb/aadarwal-massachusetts-institute-of-technology/visual_signal_algorithms).
The existing `api.wandb.ai` API credentials were verified against this exact
entity/project; the Forge page URL is not an SDK API base URL.

Use separate W&B job types for preflight, inference probes, signal audits and
actual training. Record `training_performed=false` for the first three. Keep
runtime outputs beneath `.contract-algos/` locally and the isolated
`/orcd/scratch/orcd/010/aadarwal/contract-algos` directory remotely. Never put
credentials, checkpoints or new results into the frozen `data/` tree.

The initial GLM job is private and bounded. Its port, identity and Slurm job ID
are independent of production GLM/Inkling services. Scheduler access is real;
idle nodes alone do not imply an allocation guarantee or a reservation. Long
campaigns need checkpoint/resume and a declared GPU-hour budget. Candidate
programs use the repository's existing purity/resource-limited evaluator; that
default subprocess is not equivalent to the optional Docker isolation tier.
