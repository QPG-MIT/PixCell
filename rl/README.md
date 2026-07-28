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
| [`track_b/`](track_b/) | Reserved for the established second training protocol; no implementation is implied yet |
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

The first diagnostic baseline protocol is
[`representation_curriculum_v1`](studies/representation_curriculum_v1/README.md).
It compared zero-shot Qwen operating points, then measured Qwen and Inkling on
F1–F8. Its v1 prompt contract is superseded, its measurements are not
canonical baselines, and the current paid loader rejects it. The files remain
available as an auditable historical record. It performed no SFT or RL.

Paid entry points require their explicit confirmation token and a successful
local preflight. Sample receipts and working state stay outside the repository.
W&B is an observability mirror, not the experiment record.
