# Representation curriculum v1 record

This is a superseded diagnostic record, not a canonical baseline or paper
result. Its runs used the `pixcell-blind-phase-a-direct-v1` prompt contract,
which did not state the output-file requirement enforced by the evaluator.
The historical artifacts and protocol bindings are retained for provenance;
current paid launch code rejects that contract.

The frozen protocol and task manifest live in
[`rl/studies/representation_curriculum_v1/`](../../../rl/studies/representation_curriculum_v1/).

Phase 0 defines the record contract and contains no measured model result.
Phase 1 evaluates zero-shot Qwen and Inkling; it does not perform SFT or RL.
During that run, immutable candidate receipts and mutable working state live in
the external path named by `PIXCELL_STUDY_ROOT`. W&B mirrors saved metrics for
monitoring but does not certify or replace the local record.

Credentials, W&B working files, model caches, checkpoints, and unvalidated
partial exports do not belong here.
