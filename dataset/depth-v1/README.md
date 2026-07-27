# PixCell depth-v1

`depth-v1` is a separate, core-compatible release of controlled geometry
realizations around the 547 approved PixCell representations.

The immutable 738-row PixCell core is retained in full. Its 547 semantic rows
are the `r00` anchors; the other 191 core rows remain as `core-extra` records.
Exactly 546 anchors have seven additional, model-visible geometry states. One
L2 anchor remains anchor-only because its sole mutable literal is a global
translation erased by maximum-visibility normalization; synthesizing its
descendants would create repeated inputs with different code labels.

| Release split | Contents | Rows |
|---|---|---:|
| `train` | 738 core rows plus `r01`–`r05` descendants | 3,468 |
| `validation` | `r06`–`r07` descendants | 1,092 |
| **Total** | 546 complete eight-state groups, one anchor-only representation, and core extras | **4,560** |

This release does not alter `core-v1`. Every row binds its parent core example,
parent code hash, and frozen core digest.

## Row format

Rows preserve all 30 core columns, including the model image, physical-aspect
target, parametric Python program, footprint, topology, hashes, and curriculum
metadata. The appended depth fields record:

- parent and release provenance;
- geometry and realization identity;
- controlled transform axes and parameter deltas;
- dependency, pose, render, and split grouping;
- verification evidence (hashes and metrics) and generator version; and
- a deterministic logical-row digest.

Images remain embedded in Parquet, so the release loads without a custom
dataset script. The Hugging Face feature declaration is provided by
[`scripts/schema.py`](scripts/schema.py).

## Integrity

`scripts/schema.py` defines the stable column order, Hugging Face features,
logical row and release digests, deterministic Parquet shard names, the exact
frozen population contract, and manifest, freeze, and checksum helpers.

The logical digest hashes every non-payload field, including the stored hashes
of code and images, in ascending row-ID order. Freeze and checksum records bind
the generated release artifacts without changing any file in the parent core.
