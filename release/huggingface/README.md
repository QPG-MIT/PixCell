# Hugging Face release

This directory builds and validates the generic public PixCell Dataset. It is
separate from `rl/` because dataset configurations describe data, while
training tracks describe ways to use that data.

The generated Hub tree contains:

| Configuration | Contents |
|---|---|
| `depth` | Default 4,560-row image, footprint, and code corpus |
| `core` | Exact 738-row curriculum subset |
| `references` | Separately keyed evaluator rasters and metadata |

The source releases under `dataset/` remain frozen. This tooling projects them
without modifying their files or release digests.

## Build and validate

```bash
PYTHONPATH=. python -m release.huggingface.build_release \
  --dataset-root dataset \
  --output release/huggingface/generated

PYTHONPATH=. python -m release.huggingface.validate_release \
  --dataset-root dataset \
  --release-root release/huggingface/generated
```

Build into an empty directory. A second build must match the first
byte-for-byte.

## Publish

Publication is dry-run by default and requires a clean, committed Git source.
The expected Hub `main` SHA is supplied explicitly:

```bash
PYTHONPATH=. python -m release.huggingface.publish_release \
  --package-root release/huggingface/generated \
  --dataset-root dataset \
  --expected-main-sha <full-remote-sha>
```

Adding `--apply` creates or verifies the pre-v2 safety tag, submits the complete
replacement as one Hub pull-request commit, validates the pull-request bytes,
merges it, validates `main`, and then creates `v2.0.0`. The immutable
`core-v1` and `depth-v1` tags are checked before and after publication.

No command in this directory launches model training.
