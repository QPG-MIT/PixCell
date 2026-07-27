---
pretty_name: "PixCell Dataset: Representation-First Image-to-Code Curriculum"
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
  - 1K<n<10K
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
  - config_name: depth-v1
    data_files:
      - split: train
        path: depth-v1/data/train-*.parquet
      - split: validation
        path: depth-v1/data/validation-*.parquet
---

# PixCell Dataset

PixCell pairs high-visibility photonic component images and physical footprint
context with verified primitive-only GDSFactory programs. It is published in
two complementary configurations:

| Configuration | Rows | Representations | Splits |
|---|---:|---:|---|
| `core-v1` | 738 | 547 | `train`: 738 |
| `depth-v1` | 4,560 | 547 | `train`: 3,468 · `validation`: 1,092 |

[Core gallery](galleries/all.png) · [L0](galleries/l0.png) ·
[L1](galleries/l1.png) · [L2](galleries/l2.png) ·
[L3](galleries/l3.png) · [L4](galleries/l4.png) ·
[Depth overview](depth-v1/galleries/overview.png)

## Load from Hugging Face

```bash
pip install "datasets[vision]"
```

```python
from datasets import load_dataset

core = load_dataset(
    "qpaig-mit/pixcell",
    "core-v1",
    revision="core-v1",
    split="train",
)

depth = load_dataset(
    "qpaig-mit/pixcell",
    "depth-v1",
    revision="depth-v1",
)

row = core[0]
row["image"]          # exact model input
row["instruction"]    # footprint and display-scale context
row["code"]           # supervised program
row["target_image"]   # canonical physical-aspect raster
row["footprint_um"]   # physical width and height
```

No custom loader or `trust_remote_code` is required.

## Curriculum

The levels teach the permitted vocabulary before asking for complete photonic
components.

| Level | Rows | Representations | Contents |
|---|---:|---:|---|
| **L0 — primitives** | 177 | 93 | The 22-item PixCell primitive catalog, constructor modes, useful orientations, and scale calibration. |
| **L1 — operations** | 215 | 127 | Translation, rotation, reflection, alignment, spacing, connection, path construction, Booleans, repetition, arrays, and routing. |
| **L2 — compositions** | 118 | 99 | Small relational assemblies, connected chains, branches, repeated carriers, arrays, and radial banks. |
| **L3 — structures** | 120 | 120 | Authored multi-zone systems with routes, branches, defects, repeated media, and cyclic organization. |
| **L4 — components** | 108 | 108 | Couplers, MMIs, splitters, interferometers, resonators, crossings, gratings, cavities, converters, and free-propagation structures. |

`all` is the default configuration and currently contains the same rows as
`core-v1`. The `l0` through `l4` configurations expose individual levels.
Use both the `core-v1` configuration and `revision="core-v1"` to pin this
release.

`depth-v1` retains all 738 core rows. It adds seven controlled, model-visible
geometry realizations to 546 of the 547 approved representation anchors; one
anchor remains anchor-only because its sole exposed literal changes global
placement rather than visible shape. Its validation split holds out parameter
settings, not representation classes: every representation remains present in
training. Use the `depth-v1`
configuration and `revision="depth-v1"` together to pin it. The repository
revision selects the published release, while the configuration selects its
Parquet files.

## Row contract

| Purpose | Fields |
|---|---|
| Model input | `image`, `instruction` |
| Supervised target | `code` |
| Physical reference | `target_image`, `footprint_um` |
| Curriculum identity | `level`, `family`, `concept_id`, `representation_id`, `grammar_id`, `variation_role` |
| Split integrity | `leakage_group_id` |
| Construction metadata | `primitive_calls`, `prerequisite_ids`, `port_signature_json`, `parameters_json`, `topology_json` |
| Integrity and provenance | SHA-256 fields, `view_policy`, source digest, generator version |

`image` is a maximum-visibility view: thin gaps, rails, teeth, bends, and
defects are enlarged when needed to remain legible. It may not preserve
physical aspect ratio. The class-blind `instruction` supplies the footprint
and per-axis display magnification; `target_image` preserves the canonical
physical aspect.

The full schema and release inventory are in
[`metadata/catalog.json`](metadata/catalog.json).
The additional `depth-v1` lineage and controlled-variation fields are
documented in [`depth-v1/README.md`](depth-v1/README.md).

## Admission

Only admitted rows are published. Rejected proposals, quarantine candidates,
failed builds, private benchmark figures, and RL rollouts are excluded.

Admission checks compilation and execution, primitive-only source purity,
declared ports and connectivity, structural witnesses, calibrated geometry,
footprint agreement, and artifact hashes. The core policy is in
[`factory/admission_policy.json`](factory/admission_policy.json); the depth
release binds its accepted rows and evidence in
[`depth-v1/factory/accepted_manifest.json`](depth-v1/factory/accepted_manifest.json).

The frozen `core-v1` release reports five exact duplicate groups and 41
rotation/reflection-equivalent silhouette groups. They are retained as
declared API aliases, pose examples, or calibration cases and are bound by
`leakage_group_id`.

## Reproduce

The accepted-source capsule under `factory/core-v1/` makes the dataset
self-contained. From a clean PixCell checkout:

```bash
cd dataset
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt

python scripts/build_all.py
python scripts/validate_release.py --root . --execute-programs
python depth-v1/scripts/build.py --dataset-root . --output depth-v1
python depth-v1/scripts/validate.py \
  --release-root depth-v1 \
  --dataset-root . \
  --execute-programs
python -m unittest discover -s tests -v
python -m pytest depth-v1/tests -q
```

The rebuilds must reproduce these frozen logical release digests:

```text
core-v1   e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89
depth-v1  676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b
```

The capsule contains accepted programs, explicit grammar assignments, image
evidence, and admission sidecars. It excludes historical proposal generators,
rejected candidates, private benchmarks, and RL runs. See
[`factory/README.md`](factory/README.md) for the replay contract.

The rows contain executable Python. Core replay uses isolated temporary
working directories; depth replay executes verified rows in-process for
speed. Neither is a security sandbox. Inspect code from any untrusted revision
before executing it.

## Export

Convert a level to OpenAI-style multimodal `messages`:

```bash
python scripts/to_vlm_messages.py \
  --root . \
  --level l4 \
  --output /tmp/pixcell-l4.jsonl \
  --image-mode data-uri
```

## Scope

This release is a compact curriculum for image-to-code SFT, task sampling, and
representation studies. It is not a pretraining-scale corpus, a held-out
benchmark, an RL reward implementation, or an optical-performance dataset.

Images are synthetic, single-layer, black-and-white renders. Passing
admission establishes faithful geometry under the declared raster and
footprint; it does not establish electromagnetic performance or foundry
sign-off.

## License and citation

The dataset and release tools use the [MIT License](LICENSE). Dependency
notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md), and citation
metadata is in [CITATION.cff](CITATION.cff). The citation record will be
updated with the paper's arXiv identifier when available. Project source:
[QPG-MIT/PixCell](https://github.com/QPG-MIT/PixCell).
