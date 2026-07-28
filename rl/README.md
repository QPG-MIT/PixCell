# PixCell training

This directory separates measurement shared by every training approach from
the policy choices of each approach. The frozen training data remains under
[`dataset/`](../dataset/); private paper benchmarks, historical rollouts, and
model checkpoints are not part of this tree.

## Layout

| Path | Responsibility |
|---|---|
| [`common/`](common/) | Dataset projection, candidate execution, source checking, absolute-scale IoU measurement, output extraction, and bounded evaluation batching |
| [`evaluation/`](evaluation/) | Model-neutral task loading, sampling adapters, immutable attempt records, aggregation, and metrics-only experiment tracking |
| [`studies/`](studies/) | Versioned study protocols, task manifests, and launch entry points |
| [`track_a/`](track_a/) | Self-hostable open model trained by direct SFT, then curriculum G4 RL |
| [`track_b/`](track_b/) | Inkling-specific native TML runtime bridge used by the advanced L4 policy study |
| [`track_c/`](track_c/) | Reserved for the established third training protocol; no implementation is implied yet |
| [`requirements-lock.txt`](requirements-lock.txt) | Shared pinned Python environment |
| [`stack.json`](stack.json) | Shared runtime version evidence |

The dependency direction is one way:

```text
PixCell source policy -> rl.common -> rl.evaluation -> rl.studies
                                  \-> rl.track_a
```

`rl.common` measures a program and returns typed evidence. It does not know
which model is being trained, how examples are scheduled, how measurements
become rewards, or how checkpoints are selected. Those decisions belong to
the track or frozen study that owns them. `rl.evaluation` is shared by base
models and trained checkpoints; it does not create training clients or define
policy rewards.

Track A is the only implemented training path. Its exact model-visible
contract, dataset inputs, SFT schedule, RL recipe, spend locks, and commands
are documented in [`track_a/README.md`](track_a/README.md).

The active direct-policy baseline protocol is
[`representation_curriculum_v2`](studies/representation_curriculum_v2/README.md).
It measures Qwen and Inkling on F1–F8 under the corrected prompt contract and
performs no training or operating-point selection.

The active training campaign is
[`representation_training_v1`](studies/representation_training_v1/README.md).
It freezes the shared Qwen L0 checkpoint, mixed and sequential SFT branches,
Qwen curriculum-RL branches, and the bounded Inkling L4 policy-improvement
branch. All training state and sampled programs remain in an immutable
external ledger.

[`representation_curriculum_v1`](studies/representation_curriculum_v1/README.md)
is a superseded diagnostic record. It compared zero-shot Qwen operating
points, then measured Qwen and Inkling on F1–F8. Its measurements are not
canonical baselines, and the current paid loader rejects every v1 protocol
file. The archived files remain available for audit provenance.

Paid entry points require their explicit confirmation token and a successful
local preflight. Sample receipts and working state stay outside the repository.
W&B is an observability mirror, not the experiment record.
