# Initial Engaging qualification — October 4, 2026

**Our own compute can perform image-conditioned training.** We verified this
with an actual Qwen LoRA optimizer step on one B200, including saving and
reloading the changed adapter. We also brought up a separate GLM-5.3-Flash
inference instance on two B200s using the existing platform's cached assets.
GLM visual training and the best learning signal remain unestablished.

Worktree: `/Users/aadarwal/src/QPG-MIT/contract-algos`, branch `contract-algos`,
created from `533752c1`. The literal `/contract-algos` location is on macOS's
read-only root filesystem. All source changes are in this worktree; the original
PixCell checkout remains clean. Existing production GLM/Inkling jobs and the
user's terminal seats were preserved.

## Measured results

| Check | Result | Evidence |
|---|---|---|
| Dedicated GLM service | Exact alias, text generation and image understanding passed on 2 B200s; current development instance has 16,384-token context | [W&B current readiness run](https://wandb.ai/aadarwal-massachusetts-institute-of-technology/visual_signal_algorithms/runs/d32hmde7) |
| Real own-GPU optimizer | Qwen3-VL-30B-A3B, 1 B200, one image-conditioned rank-4 attention LoRA step; nonzero gradients and changed adapters; exact reload logits | [W&B optimizer run](https://wandb.ai/aadarwal-massachusetts-institute-of-technology/visual_signal_algorithms/runs/stgr0pjx) |
| Training memory | 62,281,966,080 bytes peak allocated = 58.0 GiB; 114.2 s including loading | Same optimizer run, config and result artifacts |
| Canonical measurement controls | 20 controls over L0–L4 pass: five reference programs at 0.9941–0.9977 IoU, five rectangles, five syntax failures, five purity rejections | [W&B signal audit](https://wandb.ai/aadarwal-massachusetts-institute-of-technology/visual_signal_algorithms/runs/40mqpqph) |
| Initial GLM PixCell samples | Eight fresh attempts across two L0 tasks: four executed, three runtime errors, one truncated syntax failure; best IoU 0.87434 | [W&B grouped pilot](https://wandb.ai/aadarwal-massachusetts-institute-of-technology/visual_signal_algorithms/runs/ddkdevru); a plumbing sample, not a benchmark |
| Regression suite | 356 passed, 15 skipped, 20 expected failures; Ruff clean | `.contract-algos/pytest-full.log` |

The Qwen qualification used two synthetic color/shape images with completion
labels, frozen vision and MoE experts, and 1,671,168 trainable attention-adapter
parameters. It did **not** train on PixCell code labels, run GRPO, establish
convergence, or prove GLM trainability. The base already recognized the shapes;
the checks establish gradients, updates, image dependence and checkpoint
integrity, not newly learned visual competence.

## A measurement bug found before training

The original canonical extractor selected the cell with the most flattened
polygons from all cells. When a child and its parent tied, a child could win,
discarding the parent's rotation/reflection. A frozen, correct L1 program then
scored only **0.06825 IoU**. The fix selects genuine nonmetadata device roots
before applying the existing polygon-count selection. The same program now
scores **0.99773**, with a regression covering nested transforms and kfactory
metadata references.

The frozen dataset and historical records were not modified. The new audit
records measurement-source fingerprints. Historical aggregates must be
recomputed from their artifacts before direct comparison with this evaluator.
An earlier cold-start test also exposed wall-time contention; the final controls
used the same pinned Docker boundary as generated candidates, two workers and a
60-second execution timeout. Failed positive controls stop the audit.

The peer's final review flags possible historical impact through the conductor
and RL evaluator's shared extractor. The affected share and any changed
published aggregates remain unmeasured. Both final audit reports below already
record the corrected extractor's source hash; their rankings are post-fix. The
[peer reconciliation](PEER_DECISIONS.md) defines the provenance and paired
rescore requirements before using historical results as comparators.

## What the signal controls tell us

On these five tasks, the rectangle shortcut earns raw IoU up to 0.6603 but only
the 0.05 executable floor under `shaped_v3b`. That verifies the intended
anti-rectangle mechanism; it does not establish that this signal trains best.
`validity_floor` is an affine transformation of raw IoU among valid candidates,
so group-standardized advantages coincide in all-valid groups. Boundary
feedback can change candidate ordering; IoU and Dice alone are monotonically
related. Actual reward superiority needs matched training arms, multiple seeds,
held-out geometry groups and signal-independent metrics.

The frozen-policy pilot generated four attempts for each of two L0 training
tasks (9,460 completion tokens total). On one task, all four executed, with IoUs
0.8743, 0.8394, 0.7384 and 0.2466. All three policies ranked them identically;
the shaped reward changed relative spacing, and raw-IoU/validity-floor
standardized advantages were identical. On the second task, all four failed
execution or syntax, so **every signal was identically zero**. Changing the
geometric scalar reward alone cannot provide within-group learning credit for
that failed group. This motivates investigating API/format competence,
curriculum, or controlled error-feedback interventions before a broad signal
sweep. Two tasks are far too few to choose a winning signal.

One completion reached the server's 8192-token context ceiling: its prompt used
4987 tokens and output used the remaining 3205, despite requesting up to 4096.
The truncated attempt remains in the denominator. The replacement server has
now passed text and image checks with a 16,384-token context. A training
campaign still needs explicit prompt/output budgets; maximum context and
reasoning tokens are experimental variables, not incidental serving settings.

The immutable manifest has **3,068 train / 846 validation / 646 test rows**,
merging related leakage groups and identical image/target rasters. Existing
trained PixCell adapters may have seen this new holdout; start from a fresh
base checkpoint for the comparison. See [experiment design](DESIGN.md).

## Live services and reusable commands

Initial GLM job `24879182` completed its qualification and reached its 30-minute
limit at **October 4, 22:10:14 America/Chicago**. Slurm denied extending that
running allocation. We then explicitly submitted development job `24881211`
with a two-hour limit and 16384-token context, starting after the old allocation
ended. It runs on `node5501-c1`, private loopback port `18153`, served name
`contract-glm53-flash`, with a new private key. Its deadline is **October 5,
00:10:57 America/Chicago** (`2026-10-05T05:10:57Z`). This is a bounded development
session, not an automatically renewed service; check its evidence and Slurm
state before connecting. See the [infra instructions](infra/README.md).

The replacement passed exact model identity, text generation and image
understanding at `2026-10-05T03:15:14Z`, with 16384-token context confirmed in
its deployment metadata. Its fresh private key remains on the cluster; use
`runtime/24881211` with the prepared-request client. This is the current
development instance; `24879182` is the earlier completed test.

Qwen job `24879834` completed successfully and released its GPU. The adapter
is retained at
`/orcd/scratch/orcd/010/aadarwal/contract-algos/training/24879834/result/adapter/`.
The immutable base cache and shared training environment were not changed.

The [package README](README.md) covers manifest creation and rescore commands.
The generic `probe` CLI uses the canonical image prompt and requires both
server URL and deployment metadata. `infra/collect_prepared.py` runs prepared
requests within the Slurm allocation, reading its key locally. W&B uploads
include explicitly selected report files only; credentials are excluded.

## Tinker versus self-hosting

Tinker was supplying the optimizer/distributed runtime, sampler publication and
checkpoint management. Our private vLLM service supplies sampling. The Qwen
smoke proves a local optimizer and adapter save/reload; the existing July
self-hosted code is a useful implementation reference. A full RL loop still
needs task-specific masking/labels, per-step measurement controls, checkpoint
resume, sampler-adapter synchronization, and sampler/trainer log-probability
parity under the same image processing and precision.

| Capability | Status here |
|---|---|
| Dedicated GLM image/text sampling | Verified in the bounded two-B200 allocation |
| Artifact-derived PixCell rewards | Verified after the hierarchy fix, with isolated program execution |
| Local multimodal backward/update/checkpoint | Verified for Qwen's attention LoRA on synthetic images |
| Qwen PixCell-code training and complete GRPO loop | Next qualification; existing July implementation is a reference, not yet ported |
| GLM visual backward/update and refreshed rollout weights | Not qualified; requires supported distributed kernels and image handling |

The requested GLM model has 320B total parameters. Its successfully hosted FP8
weights do not imply compatible or similarly small backward-pass memory. The
inspected merged SkyRL path is language-only; the visual bridge and upstream
LoRA pieces are still evolving. Its B200 recipe warns that EP8 backward runs
out of memory and directs users to EP16. Do not submit a GLM training campaign
based only on the existing two-GPU serving success. See the source-linked
[model feasibility report](MODEL_FEASIBILITY.md).

The `%103` peer recommended keeping Tinker as the fastest route to comparison
with the paper's exact model lineage. That remains a useful fallback. Given the
user's own-compute objective and the successful local update, the practical next
step is a controlled self-hosted Qwen task-specific pilot, with GLM providing an
independent baseline or verifier-approved training candidates. These are
different model roles; signal comparisons must keep the trained model fixed.

Before a larger run, freeze the arm definitions, evaluator identity, seeds,
task schedule, token/GPU budget and decision rule. Add a validity-only format
control and a boundary-term ablation as separate hypotheses. Keep test groups
sealed until final evaluation. No additional credentials were needed for the
qualification completed here.
