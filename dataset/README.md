---
pretty_name: "PixCell Dataset"
license: mit
language:
  - en
  - code
annotations_creators:
  - expert-generated
  - machine-generated
source_datasets:
  - original
task_categories:
  - image-text-to-text
tags:
  - image
  - text
  - code
  - python
  - code-generation
  - vision-language
  - photonics
  - gds
  - gdsfactory
  - image-to-code
  - multimodal
  - synthetic
  - curriculum-learning
  - datasets
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
dataset_info:
  - config_name: all
    splits:
      - name: train
        num_examples: 738
  - config_name: core-v1
    splits:
      - name: train
        num_examples: 738
  - config_name: l0
    splits:
      - name: train
        num_examples: 177
  - config_name: l1
    splits:
      - name: train
        num_examples: 215
  - config_name: l2
    splits:
      - name: train
        num_examples: 118
  - config_name: l3
    splits:
      - name: train
        num_examples: 120
  - config_name: l4
    splits:
      - name: train
        num_examples: 108
  - config_name: depth-v1
    splits:
      - name: train
        num_examples: 3468
      - name: validation
        num_examples: 1092
---

# PixCell Dataset

The PixCell Dataset is a verified image-to-code curriculum for photonic
geometry. Each row pairs a high-visibility component image and physical
footprint context with a complete primitive-only GDSFactory program.

## Choose a configuration

| Configuration | Best for | Rows | Splits |
|---|---|---:|---|
| `core-v1` | Curriculum training and compact task sampling | 738 | `train`: 738 |
| `depth-v1` | Image-to-code SFT and parameter recovery | 4,560 | `train`: 3,468, `validation`: 1,092 |
| `l0` through `l4` | Individual stages of the core curriculum | 108 to 215 | `train` |

`all` is the default compatibility alias for `core-v1`. Versioned work should
pass both the configuration and matching revision.

[Core gallery](galleries/all.png), [L0](galleries/l0.png),
[L1](galleries/l1.png), [L2](galleries/l2.png),
[L3](galleries/l3.png), [L4](galleries/l4.png),
[Depth overview](depth-v1/galleries/overview.png)

## Load

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

The Parquet files load directly through `datasets`.

## Curriculum

The five levels progress from the permitted primitive catalog to complete
photonic components.

| Level | Rows | Representations | Contents |
|---|---:|---:|---|
| **L0: primitives** | 177 | 93 | The 22-item primitive catalog, constructor modes, useful orientations, and scale calibration. |
| **L1: operations** | 215 | 127 | Translation, rotation, reflection, alignment, spacing, connection, path construction, Booleans, repetition, arrays, and routing. |
| **L2: compositions** | 118 | 99 | Small relational assemblies, connected chains, branches, repeated carriers, arrays, and radial banks. |
| **L3: structures** | 120 | 120 | Authored multi-zone systems with routes, branches, defects, repeated media, and cyclic organization. |
| **L4: components** | 108 | 108 | Couplers, MMIs, splitters, interferometers, resonators, crossings, gratings, cavities, converters, and free-propagation structures. |

`depth-v1` retains the complete core and adds seven controlled geometry
settings to 546 representation anchors.

## Split design

The split holds out parameter settings within known representations.

| Split | Contents | Rows |
|---|---|---:|
| `train` | All 738 core rows plus five new settings for each of 546 expanded representations | 3,468 |
| `validation` | Two further settings for each expanded representation | 1,092 |

```text
train      738 + (5 * 546) = 3,468
validation         2 * 546 = 1,092
```

Training receives the anchors and most controlled settings. Validation receives
a fixed parameter holdout for every expanded representation. This gives a
76/24 training-to-validation ratio and keeps all 547 representations available
during training.

Exact image-plus-instruction pairs and code hashes stay unique across the two
splits. `leakage_group_id` records related aliases and dependencies. Use that
field to construct a group-disjoint split for unseen-representation studies.

## Row contract

| Purpose | Fields |
|---|---|
| Model input | `image`, `instruction` |
| Supervised target | `code` |
| Physical reference | `target_image`, `footprint_um` |
| Curriculum identity | `level`, `family`, `concept_id`, `representation_id`, `grammar_id`, `variation_role` |
| Alias and dependency grouping | `leakage_group_id` |
| Construction metadata | `primitive_calls`, `prerequisite_ids`, `port_signature_json`, `parameters_json`, `topology_json` |
| Integrity and provenance | SHA-256 fields, `view_policy`, source digest, and generator version |

`image` is a maximum-visibility view: thin gaps, rails, teeth, bends, and
defects remain legible through declared per-axis display magnification. The
class-blind `instruction` supplies that display scale and the physical
footprint. `target_image` preserves the physical aspect ratio.

The full schema and release inventory are in
[`metadata/catalog.json`](metadata/catalog.json).
The additional `depth-v1` lineage and controlled-variation fields are
documented in [`depth-v1/README.md`](depth-v1/README.md).

## Construction and quality

Core examples enumerate primitives, operations, compositions, structures, and
photonic components. The depth builder identifies live geometry parameters and
emits a fixed schedule of controlled, visible settings.

Every row passes compilation and execution, primitive-only source checks,
declared port and connectivity checks, structural witnesses, calibrated
geometry comparison, footprint agreement, and artifact hashing. Release
manifests and verification evidence are stored under [`factory/`](factory/)
and [`depth-v1/factory/`](depth-v1/factory/).

The dataset targets executable geometric reconstruction at a declared raster
and physical footprint. Electromagnetic performance and foundry qualification
are evaluated in downstream device workflows.

All images, instructions, and programs are synthetic.

## Reproduce

The source capsule under `factory/core-v1/` and the depth release scripts
rebuild the published rows from a clean PixCell checkout.

<details>
<summary>Rebuild and verify both releases</summary>

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

The rebuilds reproduce these frozen logical release digests:

```text
core-v1   e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89
depth-v1  676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b
```

</details>

See [`factory/README.md`](factory/README.md) for the replay contract. Dataset
rows contain executable Python. Inspect code from untrusted revisions before
execution.

## Training export

Convert a level to OpenAI-style multimodal `messages`:

```bash
python scripts/to_vlm_messages.py \
  --root . \
  --level l4 \
  --output /tmp/pixcell-l4.jsonl \
  --image-mode data-uri
```

## Recommended use

Use `depth-v1` for image-to-code SFT and within-representation parameter
recovery. Use `core-v1` or the individual levels for staged training, task
sampling, and component-focused training. Use a representation-disjoint
benchmark for unseen-component evaluation.

## License and citation

The dataset and release tools use the [MIT License](LICENSE). Dependency
notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Citation
metadata is available in [CITATION.cff](CITATION.cff).

```bibtex
@misc{agarwal2026pixcelldataset,
  title        = {PixCell Dataset: Representation-First Image-to-Code Curriculum},
  author       = {Aadarsh Agarwal and Kenaish Al Qubaisi and Dirk Englund},
  year         = {2026},
  howpublished = {Hugging Face dataset},
  note         = {Version depth-v1},
  url          = {https://huggingface.co/datasets/qpaig-mit/pixcell}
}
```

The citation record will include the paper's arXiv identifier when available.
Project source: [QPG-MIT/PixCell](https://github.com/QPG-MIT/PixCell).
