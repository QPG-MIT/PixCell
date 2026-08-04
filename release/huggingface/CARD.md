---
pretty_name: "PixCell Dataset"
license: mit
language:
  - en
task_categories:
  - image-text-to-text
tags:
  - image-to-code
  - code-generation
  - vision-language
  - photonics
  - gds
  - gdsfactory
  - synthetic
  - curriculum-learning
size_categories:
  - 1K<n<10K
configs:
  - config_name: depth
    default: true
    data_files:
      - split: train
        path: depth/data/train-*.parquet
      - split: validation
        path: depth/data/validation-*.parquet
  - config_name: core
    data_files:
      - split: train
        path: core/data/train-*.parquet
  - config_name: references
    data_files:
      - split: train
        path: references/data/train-*.parquet
      - split: validation
        path: references/data/validation-*.parquet
dataset_info:
  - config_name: depth
    splits:
      - name: train
        num_examples: 3468
      - name: validation
        num_examples: 1092
  - config_name: core
    splits:
      - name: train
        num_examples: 738
  - config_name: references
    splits:
      - name: train
        num_examples: 3468
      - name: validation
        num_examples: 1092
---

# PixCell Dataset

PixCell is a verified image-to-code curriculum for reconstructing photonic
geometry as primitive-only GDSFactory Python programs. Each model row contains
a high-visibility component image, its physical footprint, and an audited
program.

[Core curriculum gallery](assets/core.png) |
[Depth representation overview](assets/depth.png)

## Configurations

| Configuration | Rows | Purpose |
|---|---:|---|
| `depth` | 4,560 | Default corpus for supervised training and parameter recovery |
| `core` | 738 | Compact L0 to L4 curriculum with 547 anchors and 191 supporting rows |
| `references` | 4,560 | Target rasters, calibration, lineage, and verifier metadata |

`core` is an exact subset of `depth/train`. `references` follows the same
train and validation split as `depth` and joins through `opaque_id`.

## Load

```python
from datasets import load_dataset

depth = load_dataset(
    "qpaig-mit/pixcell",
    "depth",
    revision="v2.0.0",
)

core = load_dataset(
    "qpaig-mit/pixcell",
    "core",
    revision="v2.0.0",
    split="train",
)

references = load_dataset(
    "qpaig-mit/pixcell",
    "references",
    revision="v2.0.0",
)
```

## Training contract

| Role | Fields |
|---|---|
| Model observation | `image`, `footprint_um` |
| Supervised target | `code` |
| Sampling and curriculum | `level`, `curriculum_order`, `representation_id`, `leakage_group_id`, `variation_role`, `realization_slot`, `is_core` |
| Evaluator reference | the matching row from `references` |

The dataset stores no per-row prompt. Training code combines the image and
footprint with its selected programming contract. Sampling fields organize
batches and are model-visible only if a training pipeline explicitly includes
them.

The maximum-visibility image preserves topology and within-axis proportions.
The footprint supplies the physical width and height. The `references`
configuration supplies the canonical physical-aspect raster and calibration
used by geometry evaluators. Keep `references` out of model prompts.
Stored calibration uses the renderer's analytic bounding box. A bbox inferred
from thresholded antialiased pixels can differ by at most one pixel.

`opaque_id` is a stable join key derived from the v1 source ID. It is not an
anonymization mechanism.

## Split design

| Split | Construction | Rows |
|---|---|---:|
| `train` | 738 core rows plus five additional settings for 546 representations | 3,468 |
| `validation` | Two held-out settings for each expanded representation | 1,092 |

Validation measures parameter recovery within known representations. Every
representation is present in training.

## Curriculum

| Level | Rows | Representations | Contents |
|---|---:|---:|---|
| L0 | 177 | 93 | Primitive catalog, constructor modes, orientation, and scale |
| L1 | 215 | 127 | Placement, transforms, alignment, connection, repetition, and routing |
| L2 | 118 | 99 | Relational assemblies, chains, branches, arrays, and radial banks |
| L3 | 120 | 120 | Multi-zone structures, repeated media, defects, and cyclic organization |
| L4 | 108 | 108 | Couplers, MMIs, interferometers, resonators, crossings, gratings, cavities, and converters |

## Verification

Published rows pass deterministic compilation and execution, the
primitive-only source policy, structural checks, calibrated geometry
comparison, footprint agreement, and artifact hashing.

The dataset targets geometric reconstruction of single-layer photonic layouts.
Optical performance and foundry qualification are handled by downstream device
evaluation.

The release manifest binds every shard to the frozen source digests:

```text
core   e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89
depth  676c49134d4d044c7d84426cf8eeecf09302e74ca4aa548956f14b7631a4d80b
```

Source, release tools, and training recipes are available in the
[PixCell v2.0.0 source release](https://github.com/QPG-MIT/PixCell/tree/dataset-v2.0.0).

## Versions

Use configuration `depth` with revision `v2.0.0` to pin this release. The
original `core-v1` and `depth-v1` releases remain available at their matching
Hugging Face revisions.

Version 2.0.0 is a breaking schema release. It makes `depth` the default,
removes the duplicated per-row instruction, and moves target rasters and
calibration into `references`. Pin revision `core-v1` or `depth-v1` for the
original row schema.

## Citation

For the PixCell method and benchmark:

```bibtex
@misc{agarwal2026pixcell,
  title         = {From Pixels to {PCells}: A Neurosymbolic Approach to Photonic Component Creation},
  author        = {Aadarsh Agarwal and Kenaish Al Qubaisi and Dirk Englund},
  year          = {2026},
  eprint        = {2608.00084},
  archivePrefix = {arXiv},
  primaryClass  = {cs.CV},
  doi           = {10.48550/arXiv.2608.00084},
  url           = {https://arxiv.org/abs/2608.00084}
}
```

For the versioned dataset release:

```bibtex
@dataset{agarwal2026pixcell_dataset,
  title   = {PixCell Dataset: Representation-First Image-to-Code Curriculum},
  author  = {Aadarsh Agarwal and Kenaish Al Qubaisi and Dirk Englund},
  year    = {2026},
  version = {2.0.0},
  url     = {https://huggingface.co/datasets/qpaig-mit/pixcell}
}
```
