# Representation curriculum v1 record

This directory receives the validated evidence release for the
`representation-curriculum-v1` study. The frozen protocol and task manifest
live in
[`rl/studies/representation_curriculum_v1/`](../../../rl/studies/representation_curriculum_v1/).

Phase 0 defines the record contract and contains no measured model result.
Phase 1 evaluates zero-shot Qwen and Inkling; it does not perform SFT or RL.
During that run, immutable candidate receipts and mutable working state live in
the external path named by `PIXCELL_STUDY_ROOT`. W&B mirrors saved metrics for
monitoring but does not certify or replace the local record.

The Phase 1 PR will add only the validated evidence needed to reproduce the
reported baseline: bound source, protocol and task digests; attempt and
evaluator records; aggregate summaries; the Qwen operating-point selection;
and release checksums. Credentials, W&B working files, model caches,
checkpoints, and unvalidated partial exports do not belong here.
