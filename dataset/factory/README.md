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

## Release boundary

`core-v1` never changes. Any future dataset version must be published
separately; `build_all.py` reproduces only the frozen 738 rows.
