# PixCell standalone dataset factory

This directory makes the published PixCell curriculum reproducible without a
checkout of the private development or RL repository.

## `core-v1`

`core-v1` is the immutable 738-row curriculum released in this repository. Its
source bundle contains the minimum accepted-only material required to rebuild
the public Parquet:

- explicit grammar and factor assignments;
- one executable, primitive-only generator program per row;
- the exact model and target images;
- parameter, calibration, topology, and admission evidence consumed by the
  release gate; and
- the five accepted-only source manifests and audit reports.

Historical proposals, rejected candidates, cached GDS files, private benchmark
figures, and RL rollouts are deliberately absent.

The original candidate-bank builders are also deliberately absent. They were
development orchestration scripts coupled to historical proposal pools and an
RL environment; copying them would neither be compact nor reproduce their
source-bound hashes. In the frozen core, the executable per-row programs and
explicit factor assignments are the deterministic generators. No random
sampling is used.

The files are:

- `core-v1/freeze.json` — immutable release digest, counts, source checksums,
  and build commands;
- `core-v1/grammar_catalog.json` — inspectable grammar/factor map for all rows;
- `core-v1/source_manifest.json` — checksum inventory of every bundled source
  file; and
- `core-v1/source.tar.gz` — normalized deterministic source bundle.

## Rebuild

From the `dataset/` directory:

```bash
python scripts/build_all.py
python scripts/validate_release.py --execute-programs
```

`build_all.py` verifies the compressed source bundle, extracts it into a
temporary directory, rebuilds all five Parquet shards and galleries, and
refuses to succeed unless the logical release digest exactly matches the
frozen `core-v1` digest.

The second command independently executes all 738 emitted Python programs and
checks their runtime geometry and port contracts.

## Expansion boundary

`core-v1` never changes. Future generated examples must be published as
versioned companion configurations and must retain explicit IDs for four
different concepts:

1. representation grammar;
2. controlled physical realization;
3. pose/equivariance transform; and
4. visual-domain rendering.

This prevents parameter jitter or alternate image renders from being counted
as new representations. Expansion proposals are admitted only after the user
reviews the proposed grammar and visual examples; `build_all.py` never expands
the dataset.

The current approval draft is documented in
[`expansion/METHOD.md`](expansion/METHOD.md), with a
[visual method preview](expansion/preview.png). It is a planning artifact only:
the source capsule and published Parquet still contain exactly the frozen 738
rows.
