---
pretty_name: PixCell Representation-First Image-to-Code Curriculum
license: mit
language:
  - en
task_categories:
  - image-to-text
tags:
  - image
  - code
  - python
  - photonics
  - gds
  - gdsfactory
  - image-to-code
  - multimodal
  - synthetic
  - curriculum-learning
size_categories:
  - n<1K
configs:
  - config_name: all
    default: true
    data_files:
      - split: train
        path:
          - data/l0/train-*.parquet
          - data/l1/train-*.parquet
          - data/l2/train-*.parquet
          - data/l3/train-*.parquet
          - data/l4/train-*.parquet
  - config_name: core-v1
    data_files:
      - split: train
        path:
          - data/l0/train-*.parquet
          - data/l1/train-*.parquet
          - data/l2/train-*.parquet
          - data/l3/train-*.parquet
          - data/l4/train-*.parquet
  - config_name: l0
    data_files:
      - split: train
        path: data/l0/train-*.parquet
  - config_name: l1
    data_files:
      - split: train
        path: data/l1/train-*.parquet
  - config_name: l2
    data_files:
      - split: train
        path: data/l2/train-*.parquet
  - config_name: l3
    data_files:
      - split: train
        path: data/l3/train-*.parquet
  - config_name: l4
    data_files:
      - split: train
        path: data/l4/train-*.parquet
---

# PixCell

PixCell is an accepted-only, synthetic curriculum for teaching multimodal
models to reconstruct photonic geometry as parametric Python. A model receives
a high-visibility component image plus physical footprint and display-scale
context, then produces a complete program using the permitted PixCell
primitive catalog and GDSFactory.

The frozen `core-v1` release prioritizes distinct construction
representations over large collections of near-identical parameter changes.

| Release fact | Value |
|---|---|
| Examples | 738 image-program pairs |
| Representations | 547 |
| Curriculum | L0–L4 |
| Split | `train` only |
| Format | Parquet with embedded PNG images |
| Reference environment | Python 3.13.14, GDSFactory 9.20.7 |
| License | MIT |

[View the complete gallery](galleries/all.png), or browse
[L0](galleries/l0.png), [L1](galleries/l1.png),
[L2](galleries/l2.png), [L3](galleries/l3.png), and
[L4](galleries/l4.png) separately. Every gallery shows the exact `image`
field presented to a model.

## Quick start

No custom loader or `trust_remote_code` is required:

```python
from datasets import load_dataset

core = load_dataset(
    "qpaig-mit/pixcell",
    "core-v1",
    revision="core-v1",
    split="train",
)
l4 = load_dataset(
    "qpaig-mit/pixcell",
    "l4",
    revision="core-v1",
    split="train",
)

row = l4[0]
row["image"]          # PIL.Image.Image: model input
row["instruction"]    # class-blind reconstruction prompt
row["code"]           # complete supervised answer
row["target_image"]   # canonical physical-aspect target raster
row["footprint_um"]   # physical width and height
```

From a local checkout of this directory:

```python
from datasets import load_dataset

l2 = load_dataset(
    "parquet",
    data_files={"train": "data/l2/train-*.parquet"},
    split="train",
)
```

## Curriculum

The stages are cumulative: primitives, operations, compositions, hierarchical
systems, then complete photonic components.

| Level | Rows | Representations | Focus |
|---|---:|---:|---|
| **L0 — primitives** | 177 | 93 | The complete 22-item PixCell primitive vocabulary, useful constructor modes, orientations, and scale calibration. |
| **L1 — operations** | 215 | 127 | Translation, rotation, reflection, alignment, spacing, tangency, overlap, connection, path construction, Boolean operations, repetition, arrays, and routing. |
| **L2 — compositions** | 118 | 99 | Small relational assemblies, connected chains, branches, repeated carriers, arrays, and radial banks. |
| **L3 — hierarchical structures** | 120 | 120 | Independently authored multi-zone systems with routes, branches, defects, repeated media, and cyclic organization. |
| **L4 — photonic components** | 108 | 108 | Couplers, MMIs, splitters, interferometers, resonators, crossings, gratings, cavities, converters, and free-propagation structures. |
| **Total** | **738** | **547** | |

`all` is the default configuration. It and `core-v1` currently contain the
same 738 rows. Use the `core-v1` configuration together with
`revision="core-v1"` to pin the immutable Hub snapshot. The `l0` through `l4`
configurations expose individual stages without duplicating files.

All configurations have a `train` split. Curriculum levels are not disguised
train/test partitions, and the paper's private evaluation figures are not
included. PixCell is therefore not a ready-made held-out benchmark.

## Task and rendering contract

The canonical `instruction` is class-blind: it does not reveal the component
label, family, or representation name. Those fields remain available as
metadata for analysis or explicitly label-conditioned training.

`image` is the maximum-visibility supervision view. Thin gaps, rails, teeth,
bends, and defects are enlarged when necessary so their shapes remain
legible. It may not preserve physical aspect ratio. The instruction records
the physical footprint and per-axis display magnification so the model is not
asked to infer hidden scale from pixels.

Use:

- `image` for the visual model input;
- `instruction` for footprint and display-scale context;
- `target_image` for the canonical physical-aspect raster; and
- `footprint_um` and the JSON metadata for exact physical information.

## Admission and grouping

Only admitted examples appear in the public Parquet. Rejected proposals,
quarantined candidates, failed builds, private benchmarks, and RL rollouts are
excluded.

Admission verifies that each program:

1. compiles, executes, and emits nonempty geometry;
2. passes the primitive-only source-purity gate;
3. matches declared port and broad connectivity contracts;
4. satisfies declared structural and repeated-element witnesses;
5. agrees with calibrated geometry and footprint evidence; and
6. is hash-bound to its source, images, and admission record.

The complete policy is in
[`factory/admission_policy.json`](factory/admission_policy.json). Runtime
validation uses a fresh temporary working directory; it is an integrity check,
not a security sandbox for untrusted code.

The release reports five exact duplicate groups and 41
rotation/reflection-equivalent silhouette groups. These are retained only for
declared API aliases, pose examples, or calibration roles. When making a
downstream validation split, group on `leakage_group_id` (or, more
conservatively, `grammar_id`) so related rows never cross the split boundary.

`variation_role` distinguishes representation-changing semantic examples from
controlled realization, equivariance, and calibration examples.

## Row schema

The schema is flat and loader-free. Irregular metadata is stored as canonical
JSON text for stability across levels.

| Field group | Columns |
|---|---|
| Supervision | `image`, `target_image`, `instruction`, `code`, `code_language` |
| Ordering and labels | `id`, `level`, `curriculum_order`, `label`, `family` |
| Representation identity | `concept_id`, `representation_id`, `grammar_id`, `leakage_group_id`, `variation_role` |
| Construction context | `primitive_calls`, `prerequisite_ids`, `port_signature_json`, `footprint_um`, `parameters_json`, `topology_json`, `metadata_json` |
| Integrity | `image_sha256`, `target_image_sha256`, `code_sha256`, `normalized_d4_sha256` |
| Provenance | `schema_version`, `view_policy`, `source_dataset_digest_sha256`, `source_generator_version` |

The authoritative schema, counts, role totals, and duplicate report are in
[`metadata/catalog.json`](metadata/catalog.json).

## VLM message adapter

The included adapter converts flat rows into OpenAI-style multimodal
`messages`: a user message containing the image and instruction, followed by
an assistant message containing the ground-truth program.

From this directory:

```bash
python scripts/to_vlm_messages.py \
  --root . \
  --level l4 \
  --output /tmp/pixcell-l4.jsonl \
  --image-mode data-uri
```

Use `--image-mode relative-path` when the training stack can resolve local
images. Processor, chat-template, and multimodal-collator setup remains
model-specific.

## Reproduce and validate

The dataset directory is self-contained. Its accepted-source capsule can
rebuild the five Parquet shards, metadata, and galleries without access to the
historical development or RL repository.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt

python scripts/build_all.py
python scripts/validate_release.py --root . --execute-programs
python -m unittest discover -s tests -v
```

`build_all.py` verifies the source capsule and refuses to succeed unless the
logical release digest is exactly:

```text
e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89
```

The executable source capsule contains accepted programs, explicit
grammar/factor assignments, exact image evidence, and admission sidecars. It
does not contain historical candidate banks, rejected proposals, or the
original proposal-generation orchestration, and it is not a general-purpose
expansion engine. See [`factory/README.md`](factory/README.md) for the precise
replay contract.

For a faster package-integrity check that does not execute all 738 programs:

```bash
python scripts/validate_release.py --root .
```

## Intended use and limitations

PixCell is suitable for:

- curriculum SFT and image-to-code representation learning;
- task sampling for on-policy RL paired with an external deterministic
  evaluator;
- controlled studies by level, family, grammar, or variation role; and
- evaluation of primitive-only parametric reconstruction on separately
  constructed held-out tasks.

It is a compact, high-density curriculum—not a pretraining-scale corpus, an
RL reward environment, or a standalone benchmark. It also does not replace
electromagnetic simulation, compact-model extraction, foundry design-rule
checking, or fabrication sign-off.

Images are idealized single-layer black-and-white renders. Real micrographs,
noisy paper figures, multilayer masks, and arbitrary visual styles are outside
`core-v1`. Geometry admission establishes faithful construction under the
declared raster and footprint, not optical performance. Programs target the
pinned GDSFactory API; later dependency versions may change geometry or port
behavior.

## License and citation

The dataset and release tools use the [MIT License](LICENSE). Dependency
notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and citation
metadata is provided in [CITATION.cff](CITATION.cff). The citation record will
be updated with the paper's arXiv identifier when it becomes available.
