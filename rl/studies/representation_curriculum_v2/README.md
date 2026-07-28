# Direct-policy zero-shot baselines v2

This study measures the untrained Qwen and Inkling policies on the fixed F1–F8
benchmark under the corrected `pixcell-direct-reconstruction-v2` contract. It
does not select an operating point and does not train a model.

## What the policy receives

Each attempt is one user turn, ordered as:

1. the benchmark's `device_bw.png`, decoded as RGB and downscaled only when
   needed with aspect ratio preserved and a 1920-pixel longest edge;
2. the image semantics: black is material on layer `(1, 0)`, white is
   background;
3. the benchmark's physical `[x-length, y-width]` footprint;
4. the exact extended primitive catalogue from
   `src/michaelangelo/reference/gds_factory_function_catalogue_extended.md`;
5. the direct programming requirements in
   `rl/common/assets/phase_a_direct_v2.md`.

There is no system message. For F1–F8, `device_bw.png` is both the visible
input and the silhouette against which the verifier later measures the
candidate; there is no separate hidden reference raster. The policy receives
the image once, in the user message. It never receives the verifier's
calibration, reference code, IoU, or answer-derived metadata.

The image and footprint are the normal Phase-A inputs defined by
`src/homi/briefs/phase_a_recreation.md`. The primitive catalogue is the
repository's permitted programming vocabulary. The direct programming
requirements retain the normal Phase-A source, parameterization, and output
rules while making the one-shot transport boundary explicit: the answer must
be a complete program that writes `device.gds`.
`rl/common/preprocess.py` is the authority for the deterministic image
transformation.

## Frozen arms

| Hypothesis | Policy | Reasoning | Output ceiling | Attempts |
|---|---|---|---:|---:|
| `RC-H05` | `Qwen/Qwen3.6-35B-A3B` | `qwen3_5`, thinking on | 60,000 | 4 per figure |
| `RC-H06` | `thinkingmachines/Inkling` | `tml_v0`, effort 0.9 | 60,000 | 4 per figure |

Both arms use a 65,536-token context, a 1920-pixel maximum image edge,
temperature 1.0, top-p 1.0, sampling concurrency 8, and the strict isolated
evaluator. A local renderer preflight measures every complete prompt and
rejects the launch if `prompt tokens + 60,000` exceeds the context.
The frozen 1920-pixel edge leaves positive context headroom for every Qwen and
Inkling F1–F8 input at the 60,000-token ceiling.

`smoke` means attempt index 1 for each of F1–F8: eight independent model
requests per arm. Those eight receipts are already the first quarter of the
declared best-at-4 baseline. After they execute and evaluate correctly,
`complete` resumes the same run and adds attempt indices 2–4; it does not
discard or repeat attempt 1.

## Before launch

The launch path is deliberately fail-closed. It requires a clean, exact source
commit; sealed protocol and task-manifest digests; the pinned runtime; the
immutable candidate-execution boundary; exact renderer context accounting;
valid references; credentials; an external attempt ledger; and the explicit
`PIXCELL_BASELINE_V2` spend confirmation. No Tinker service client exists until
those checks pass.

Inspect exact local renderer token accounting without making a remote request:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v2.audit_context
```

After committing the launch source, run the complete zero-spend audit with the
immutable evaluator image already selected:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v2.audit_phase0 \
  --expected-source-sha "$(git rev-parse HEAD)"
```

That audit needs no model or tracking credentials. It works offline, renders
all 16 arm/figure contexts, validates all eight references, executes one
fixed primitive-only probe against F1 inside the required sandbox, and
round-trips the run-manifest, sampling-receipt, and evaluation-record schemas.
A paid smoke launch is not ready unless this sealed audit passes.

Paid launch commands are intentionally not presented as casual copy-paste
examples. Use `run_baseline.py --help`, review the sealed commit, run `smoke`,
inspect all eight records, and only then resume `complete`.

## Freeze completed evidence

After both 32-attempt arms are complete, freeze the external ledger into the
small tracked record:

```bash
PYTHONPATH=src:. python -m \
  rl.studies.representation_curriculum_v2.freeze_phase1 \
  --external-root "$PIXCELL_STUDY_ROOT" \
  --expected-source-sha "$(git rev-parse HEAD)"
```

The command reproduces both summaries from immutable attempt receipts,
re-renders every prompt offline, and re-executes all 64 extracted programs in
the exact launch-bound sandbox before accepting their scores. It writes
`release_manifest.json`, `checksums.sha256`, `summaries.json`,
`attempts.jsonl`, and `programs.jsonl` under
`data/training/representation-curriculum-v2/phase1`. `programs.jsonl` contains
only programs that passed the source, execution, and geometry measurement
path, making every nonzero reported geometry independently re-evaluable.
Failed-output fallback text is not published. Raw completions, separate
reasoning and answer channels, mutable W&B state, and credentials remain
outside Git. Add `--validate` to prove that an existing tracked record matches
the authoritative ledger byte for byte.
