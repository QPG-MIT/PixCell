# Deliberation with the existing agent in `%103`

The pane was resolved through process ancestry and the native HOMI roster to
Claude session `06b7da1b-1a8f-4d7e-82b0-8a4b41e56485`, named `pixcell-8a`.
Communication used the installed HOMI native route; no terminal input/control
was used. Its substantive response is the [independent review](../../contract_algos_peer_review.md).
The review was read and challenged, rather than treated as execution authority.

## Adopted

- Separate serving, actual optimizer updates and complete RL qualification.
  A serving API alone cannot update model weights.
- Evaluate signal differences on identical candidate groups before spending on
  a learning comparison. A validity-only reward is a useful additional control
  for formatting versus geometric competence.
- Keep model, split, image preprocessing, task schedule and budgets fixed within
  the reward ablation. Use fresh base weights for the new holdout split.
- Add positive controls throughout a future training loop, not just at launch.
  The observed timeout issue and corrected hierarchy bug directly demonstrate
  why evaluator integrity comes first.
- Require sampler/trainer token and probability parity, adapter-version tracking
  and checkpoint resume before a self-hosted RL campaign.
- Keep raw artifacts authoritative; W&B makes them inspectable and comparable.
- Require a historical artifact audit before comparing new metrics with
  published aggregates. Preserve original records and write any verified
  corrections as a separate dated addendum with artifact-level differences.

## Qualified or not adopted

- The peer preferred Tinker for matching the published Qwen3.6 lineage. That is
  a legitimate comparability advantage, but the user's own-compute objective is
  now supported by a successful local Qwen3-VL optimizer test. No Tinker spending
  was authorized or initiated by peer suggestions.
- The peer's initial one-node, eight-B200 GLM backward proposal conflicts with
  the inspected SkyRL recipe warning about EP8 backward OOM on B200 and its
  EP16 guidance. We sent that evidence back and do not use the proposal as an
  actionable capacity guarantee. See [feasibility sources](MODEL_FEASIBILITY.md).
  The peer subsequently revised its report to incorporate EP16 and to qualify
  the throughput and visual-trainer claims below.
- Proposed cached vision-embedding injection is a research hypothesis, not a
  verified substitute for a full visual trainer. Parity must be established.
- Price totals, engineering timelines, comparative throughput multiples and
  statistical power in the independent review are planning estimates, not
  measured outcomes from this work. Our report uses measured GPU memory,
  allocation times and artifacts. Run seed variance must be measured before
  making a confident power claim.
- A two-sequence concurrency cap does not establish a measured two-times
  throughput ceiling relative to a single-stream observation. Per-sequence
  speed can change with batching, request lengths and configuration. The
  revised peer's remaining throughput bound is not adopted; benchmark the
  actual rollout configuration before sizing a campaign.
- EP16 is guidance from the inspected B200 recipe, not proof that every possible
  trainer requires 16 GPUs or that colocated execution is universally
  impossible. Separate sampler/trainer allocations are the proposed design
  for qualifying that recipe, not an already validated GLM visual training path.
- No blanket assertion that a GLM visual trainer does not exist is warranted.
  The inspected upstream paths did not establish a working, image-conditioned
  GLM training/rollout round trip for our configuration.
- Timeout retries should be specified and applied consistently to every arm.
  They must not turn genuinely nonterminating candidates into infrastructure
  exclusions or selectively give more compute to one signal. The current smoke
  uses explicit common limits and stops on failed reference controls; a future
  training loop needs a registered contention/retry policy.

## Historical-metric concern in the queued revision

The final queued reply and revised Section 2.7 were reviewed. The current
conductor and RL evaluator both call `extract_polygons`, so the identified
hierarchy defect has a credible path to historical measurements. That call
graph alone does **not** establish the verifier version used by every published
run, which stored artifacts are affected, or the size/direction of any change.
Nor does one affected ground truth demonstrate that a policy learned to avoid
hierarchy. Those are questions for a paired historical audit.

The final 20-control report and eight-candidate signal report already use the
fixed extractor; both record `michaelangelo.core.compare_absolute` SHA-256
`a597ff35c3337b25d2c97f68f56be64622d5aaea2c4be67941cd40bbe8fdc0f4`.
Their reported comparisons therefore do not depend on pre-fix rankings.

Before using an old score as a comparator, inventory retained GDS, targets,
calibrations, source programs and evaluator provenance; reproduce the original
score where possible, then measure the same artifacts with the corrected
extractor and otherwise identical settings. Report missing artifacts,
unreproduced original scores and execution failures separately from IoU
changes. Existing GDS should be rescored directly; any necessary source
re-execution needs its original dependency pins and the same isolation used
for generated candidates. Scope includes agent records, retained champion/Run B
artifacts, dataset references and training rollouts where available. Preserve
the sealed test split: historical-integrity findings must not become tuning
feedback for the new study.

A bounded read-only inventory found that
`data/training/qwen-rl-v2/agentloop/b-final.json` retains eight final champion
programs, but not all per-round candidates. They can support final-champion
remeasurement, not replay of the original selection process.
`data/training/qwen-rl-v2/bench/b-final.json` retains summary counts, means and
best scores without candidate programs; exact rescoring of its aggregates
requires recovering those candidates elsewhere. Audit only identified visual
measurements in the agent record, not unrelated physics experiments. A
hierarchy-stratified sample and the retained champions are a practical first
stage before expanding the audit.

Transformed sub-cells are not automatically affected: the historical selection
depends on polygon-count ties and cell order, while symmetry and renderer
translation normalization can leave the score unchanged. The single verified
failure therefore cannot establish either near-zero rewards for all such
programs or a learned preference for flat construction.

This review reconciliation did not run a historical rescore or establish an
erratum. The frozen `data/` record remains unchanged. The peer's revised file
is authoritative for the peer's own recommendations; this decision record
states which recommendations the experiment adopts and their evidence limits.

This captures decisions for the user; it does not overwrite the peer's authored
recommendations or imply agreement where the evidence differs.
