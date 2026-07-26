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

# PixCell Representation-First Image-to-Code Curriculum

PixCell is an accepted-only, synthetic image-to-code curriculum for teaching
multimodal models to reconstruct photonic geometry as parametric Python
programs. Each row pairs the exact high-visibility black-and-white image used
as the model input with a primitive-only GDSFactory program that recreates it.

The dataset is designed around a simple premise: useful volume comes from
different **representations**, not from thousands of small parameter changes
to the same shape. Discrete construction grammars are enumerated first.
Controlled realizations, calibration examples, and safe pose examples are
included only when they teach something explicit and are identified by their
`variation_role`.

## Curriculum

The five levels form one cumulative learning catalog:

| Level | What it teaches |
|---|---|
| **L0 — primitives** | The complete permitted component and path vocabulary, including primitive constructor modes, a bounded set of useful orientations, and physical-scale calibration cases. |
| **L1 — operations** | One operation or spatial relation at a time: translation, rotation, reflection, alignment, gaps, tangency, overlap, connection, path construction, Boolean operations, repetition, arrays, and routing. |
| **L2 — compositions** | Small representation graphs made from several already-legible primitives and L1 operations: relational assemblies, connected chains, local branches, repeated carriers, arrays, and graded or radial banks. |
| **L3 — hierarchical structures** | Coherent multi-zone systems with multiple bodies, routes, branches, defects, repeated media, and radial or cyclic organization. Each row is an independently authored semantic scene. |
| **L4 — photonic components** | Capstone component representations: couplers, MMIs and splitters, interferometers, resonators, crossings, gratings and repeated media, cavities, mode/edge converters, and free-propagation or fan structures. |

This ordering is pedagogical, not a statement that real photonic design always
proceeds linearly. Users may train on one level, accumulate levels, or filter
the complete `all` configuration by role or representation family.

## Accepted-only release

The public Parquet files contain only admitted examples. Rejected proposals,
quarantine candidates, failed intermediate builds, private benchmark figures,
and RL rollouts are not dataset rows.

Before admission, every example is subjected to deterministic checks
appropriate to its level:

1. the program parses, compiles, and executes in an isolated process;
2. source analysis enforces the public primitive catalog and rejects raw
   polygon dumps, prebuilt device stencils, target-image reads, and dynamic
   component lookup;
3. declared ports and broad connectivity are checked;
4. structural counts, repeated elements, and objective topology witnesses are
   checked where declared;
5. the generated GDS is rendered at calibrated absolute scale and compared
   with the target;
6. the exact model view, footprint, source, and evidence are hash-bound;
7. exact and rotation/reflection-equivalent duplicates are audited within and
   across curriculum levels under the declared alias policy.

Some semantic descriptions, such as the intended interpretation of a visual
hierarchy, are deliberately descriptive rather than brittle automated reward
terms. The machine gates measure executable facts; they do not pretend to
replace visual review.

## Configurations and splits

`all` is the default Hugging Face configuration. The `l0`, `l1`, `l2`, `l3`,
and `l4` configurations expose each stage separately without duplicating the
underlying files.

All released rows belong to a `train` split. PixCell does not relabel
curriculum stages as train/test partitions, and this release does not include
the paper's private evaluation figures. When constructing a downstream
validation set, group by `leakage_group_id` or `grammar_id` before splitting;
do not randomly separate pose or realization siblings.

The release manifest generated alongside the Parquet files is the
authoritative source for exact row counts, role counts, source-bank digests,
and the complete release digest.

## Row schema

The Parquet schema is flat and loader-free. Irregular nested source metadata is
stored as canonical JSON text so the schema remains stable across levels.

| Column | Type | Meaning |
|---|---|---|
| `schema_version` | string | Public row-schema version. |
| `id` | string | Globally unique example identifier. |
| `level` | string | One of `L0` through `L4`. |
| `curriculum_order` | integer | Stable order within the complete curriculum. |
| `image` | Image | Exact high-visibility image supplied to the model. |
| `target_image` | Image | Canonical high-resolution black-and-white target raster. |
| `code` | string | Complete ground-truth Python program. |
| `code_language` | string | `python`. |
| `instruction` | string | Image-to-code instruction paired with the example. |
| `label` | string | Reader-facing example label. |
| `family` | string | Representation or component family. |
| `concept_id` | string | Curriculum concept or component identity. |
| `representation_id` | string | Representation-level identity. |
| `grammar_id` | string | Program/visual grammar identity. |
| `leakage_group_id` | string | Group that must stay together in downstream splits. |
| `variation_role` | string | Semantic, realization, equivariance, or calibration role. |
| `primitive_calls` | list[string] | Primitive/API vocabulary observed in the program. |
| `prerequisite_ids` | list[string] | Earlier curriculum concepts used by the row when explicitly declared or mechanically derivable. |
| `port_signature_json` | string | Canonical JSON description of the port contract. |
| `footprint_um` | list[float] | Physical footprint in micrometres. |
| `parameters_json` | string | Canonical JSON of named top-level parameters. |
| `topology_json` | string | Canonical JSON of topology/structure metadata. |
| `metadata_json` | string | Canonical JSON retaining additional source metadata. |
| `image_sha256` | string | Integrity digest for the model image. |
| `target_image_sha256` | string | Integrity digest for the target raster. |
| `code_sha256` | string | Integrity digest for the program. |
| `normalized_d4_sha256` | string | Rotation/reflection-normalized silhouette digest. |
| `view_policy` | string | Deterministic policy used to select the model view. |
| `source_dataset_digest_sha256` | string | Digest of the audited source level. |
| `source_generator_version` | string | Version of the source generator. |

`image` is the supervision view, optimized so thin gaps, rails, teeth, bends,
and defects remain visible. It is not a replacement for physical dimensions.
Use `target_image`, `footprint_um`, and the JSON metadata when exact raster or
physical-scale information matters.

The canonical `instruction` is deliberately class-blind: it does not reveal
the row's `label`, `family`, or representation name. Those fields remain
available as metadata for analysis or an explicitly label-conditioned
training variant, while the default image-to-code task requires the model to
infer the construction from the geometry itself. The instruction does include
the physical footprint and the per-axis relative display magnification. This
is necessary task context: maximum-visibility views deliberately make thin
gaps and rails legible and therefore are not guaranteed to preserve physical
aspect ratio or absolute pixel scale.

## Loading with Hugging Face Datasets

After publication, load the complete curriculum or one level using the normal
Datasets API; no custom loading code or `trust_remote_code` is required:

```python
from datasets import load_dataset

catalog = load_dataset("<namespace>/<dataset-repository>", "all")
l4 = load_dataset("<namespace>/<dataset-repository>", "l4", split="train")

row = l4[0]
row["image"]          # PIL.Image.Image: the model input
row["target_image"]   # PIL.Image.Image: the canonical target
row["instruction"]    # user instruction
row["code"]           # supervised assistant answer
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

Rows can be filtered without losing their grouping metadata:

```python
semantic = catalog["train"].filter(
    lambda row: row["variation_role"] == "semantic"
)
```

## VLM and TRL adapter

The canonical Parquet remains flat so it is broadly usable. The included
adapter converts rows into OpenAI-style multimodal `messages`: a user message
with `[image_url, text]` content followed by an assistant message containing
the ground-truth program.

From this directory:

```bash
python scripts/to_vlm_messages.py \
  --root . \
  --level l4 \
  --output /tmp/l4_messages.jsonl \
  --image-mode data-uri
```

Use `--image-mode relative-path` when the trainer can resolve local image
paths. The resulting JSONL can be loaded directly:

```python
from datasets import load_dataset

messages = load_dataset(
    "json",
    data_files="/tmp/l4_messages.jsonl",
    split="train",
)
```

For TRL, supply this `messages` dataset to the VLM's chat template, processor,
and multimodal data collator:

```python
from trl import SFTConfig, SFTTrainer

trainer = SFTTrainer(
    model=model,
    args=SFTConfig(output_dir="pixcell-sft"),
    train_dataset=messages,
    processing_class=processor,
    data_collator=multimodal_data_collator,
)
```

`model`, `processor`, and `multimodal_data_collator` are intentionally
model-specific. Confirm that the selected TRL/model integration preserves the
image content instead of flattening the conversation to text. TRL is not
needed to consume or validate the dataset and is therefore not included in
the release lock.

## Validation and galleries

Install the pinned reference environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
```

Run the complete packaged-data validation from this directory:

```bash
python scripts/validate_release.py --root .
```

Regenerate the reader-facing L0–L4 galleries:

```bash
python scripts/render_galleries.py --root .
```

The validator checks the release inventory and checksums, Parquet schemas and
row counts, embedded-image and code hashes, code compilation, source purity,
identifiers and relative paths, the recorded cross-level collision report, and
the absence of private paths or obvious credentials.

To additionally execute every program in an isolated temporary directory and
require a nonempty GDS result, finite positive runtime ports, exact declared
port counts, full declared L3 port geometry, and the declared L4 boundary-side
port histogram with outward-facing orientations, use the pinned GDSFactory
stack and run:

```bash
python scripts/validate_release.py --root . --execute-programs
```

The exhaustive source-bank admission process also recomputes calibrated target
rasters, footprints, ports, structural witnesses, and source-to-target
agreement. Those evidence records and their digests are bound into the public
release; the default loader-only validation does not pretend to recompute them.

Maintainers can rebuild the package from the separately audited source banks:

```bash
python scripts/build_release.py \
  --source <audited-source-root> \
  --output .
python scripts/validate_release.py --root .
python scripts/render_galleries.py --root .
```

The published Parquet files and release manifest are canonical. The source
bank is needed only for a maintainer rebuild, not for loading or validating a
published checkout.

The Hugging Face dataset-card metadata can also be checked with:

```bash
python - <<'PY'
from huggingface_hub import DatasetCard

DatasetCard.load("README.md").validate(repo_type="dataset")
print("dataset card is valid")
PY
```

Card validation calls the Hugging Face validation service and therefore
requires network access.

## Limitations and intended use

- PixCell teaches visual representation and parametric construction. It is not
  a substitute for electromagnetic simulation, compact-model extraction,
  foundry design-rule checking, or fabrication sign-off.
- The images are idealized, single-layer black-and-white renders. Real
  micrographs, noisy screenshots, multilayer masks, and arbitrary paper styles
  are outside this release.
- The view policy prioritizes maximal visual legibility. Physical dimensions
  must be read from `footprint_um` and associated metadata rather than inferred
  from display pixels alone.
- A passing geometry gate establishes faithful construction under the declared
  raster and footprint; it does not establish optical performance.
- The catalog is intentionally curated. It covers many useful visual grammars
  but is not an exhaustive taxonomy of photonic devices.
- The programs target the pinned GDSFactory API. Later dependency versions may
  change geometry, port behavior, or rendered pixels.
- The examples are synthetic and accepted-only, so they should not be used to
  estimate performance on uncurated real-world figures without a separate
  evaluation set.

Appropriate uses include curriculum SFT, on-policy RL task sampling,
image-to-code representation learning, controlled ablations by curriculum
level, and evaluation of primitive-only parametric reconstruction.

## License and citation

The dataset and release tools are available under the [MIT License](LICENSE).
Dependency notices are listed in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Citation metadata is provided
in [CITATION.cff](CITATION.cff); no DOI or arXiv identifier is claimed here.
