# Qwen 60k F1-F8 extension

> **Superseded diagnostic record.** This extension used the retired v1 prompt
> contract. Its measurements are not canonical baselines or paper results,
> and current paid launch code rejects the protocol. The files are retained
> for provenance.

This is the near-context-limit extension to the frozen Phase 1 baseline study.
It follows the accepted Qwen 32k extension in pull request 7 and records the
user's quality-first decision to test the strongest practical setting for a
self-hostable model.

Qwen has a 65,536-token context window shared by the prompt and completion, so
a literal 65,536-token completion cannot be requested. Under the frozen
renderer, the largest F1-F8 prompt is 3,685 tokens. The 60,000-token cap
therefore fits every task and leaves at least 1,851 tokens of context reserve.

`RC-H04` keeps the original F1-F8 tasks, blind prompt, renderer, image policy,
temperature, seed namespace, evaluator, and four attempts per figure. Its only
changed model setting relative to `RC-H03` is the output cap. It has its own
study ID, W&B run identity, external ledger, and tracked evidence directory,
so it cannot overwrite the 16k or 32k records.

The historical launch command was:

```bash
python -m rl.studies.representation_curriculum_v1.extensions.qwen60.run_baseline \
  --wave smoke \
  --external-root "$PIXCELL_STUDY_ROOT" \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE
```

After verifying all eight sampling and evaluation records, repeat with
`--wave complete`. The complete wave is resumable and contains 32 samples.
