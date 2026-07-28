# Qwen 32k F1-F8 extension

> **Superseded diagnostic record.** This extension used the retired v1 prompt
> contract. Its measurements are not canonical baselines or paper results,
> and current paid launch code rejects the protocol. The files are retained
> for provenance.

This is the quality-first extension to the frozen Phase 1 baseline study. It
was registered after the `RC-H01` smoke wave showed that 7 of 8 Qwen
thinking-on/16k completions reached the output cap.

`RC-H03` keeps the original F1-F8 tasks, blind prompt, renderer, image policy,
temperature, seeds, evaluator, and four attempts per figure. Its only changed
model setting is the 32,768-token output cap. The extension uses its own study
ID, source commit, and external ledger. It does not rewrite the original
operating-point selection or `RC-H01` evidence.

The historical launch command was:

```bash
python -m rl.studies.representation_curriculum_v1.extensions.qwen32.run_baseline \
  --wave smoke \
  --external-root "$PIXCELL_STUDY_ROOT" \
  --expected-source-sha "$SOURCE_SHA" \
  --confirm-spend PIXCELL_PHASE1_BASELINE
```

After verifying all eight sampling and evaluation records, repeat with
`--wave complete`. The complete wave is resumable and contains 32 samples.
