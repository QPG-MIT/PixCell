---
uuid: d341ffff-1e38-4d6e-a4e9-eff3b8325a74
slug: rc-01-shape-aware-verification
version: 1.0.0
status: open
created: 2026-07-27
category: infrastructure
domain: photonics
source: https://pixcell.qpaig.com/#research-contracts
---

# RC-01: Shape-aware visual verification

## Question

What deterministic metric reflects structural agreement between
calibrated photonic-device rasters without rewarding area-filling
shortcuts?

## Objective

A deterministic, reproducible shape-agreement metric for calibrated
device rasters that improves on IoU and on the current boundary
baseline. IoU is the acceptance metric throughout PixCell
(`michaelangelo.core.compare_absolute`); it is known to reward
area-filling: a candidate that pours material into the target's
bounding region scores well while destroying structure. The metric this
contract buys must order candidates by structural agreement and must
make area-filling a losing strategy.

## Definitions

- **Calibrated raster**: a binary foreground mask rendered at a fixed,
  stored pixels-per-micron scale, as produced by the PixCell verifier.
  Calibration is fixed per target from the stated physical footprint;
  candidates are never rescaled to fit.
- **Boundary baseline**: the strongest boundary-aware comparison
  currently in the repository, as declared and frozen in the evaluation
  suite at submission time.
- **Adversarial block construction**: a candidate raster built to
  maximize IoU while violating the target's structure, for example
  filled rectangles covering the target's extent.

## Acceptance tests

All five are required. Settlement is all-or-nothing.

| ID | Requirement | Check |
|----|-------------|-------|
| T1 | `metric(raster_a, raster_b) -> float` in `[0, 1]` is a pure deterministic function. | Same inputs give bit-identical output across two runs on independent machines; no randomness, no network, no learned weights that are not shipped and hashed. |
| T2 | A frozen evaluation suite covers calibrated perturbations (translation, rotation, scale), topology errors (merged and split features), port errors (missing and moved ports), and adversarial block constructions. | Suite manifest is versioned and hashed; every case class above is present; the hidden split manifest is committed before scores are reported. |
| T3 | On the declared corpus the metric strictly improves ordering over IoU and over the boundary baseline. | Rank correlation against blinded human judgments exceeds both baselines under the annotation protocol; a locked optimization comparison driven by the metric does not converge to degenerate area-filling. |
| T4 | Every adversarial block construction scores worse than its honest counterpart. | Pairwise check over all adversarial pairs in the suite; the suite must also exhibit at least one pair where IoU fails this ordering. |
| T5 | A single rerun script reproduces all raw scores from the shipped corpus and code. | Issuer runs one command from a clean environment; reproduced scores match shipped scores exactly. |

## Required evidence

The submission retains, and the manifest names, each of:

| Key | Artifact |
|-----|----------|
| `metric_code` | Implementation of the metric, pinned dependencies included |
| `metric_definition` | Mathematical definition matching the implementation |
| `calibrated_corpus` | The evaluation corpus with per-item hashes and calibration records |
| `perturbation_generator` | Code generating the perturbation and adversarial cases |
| `hidden_split_manifest` | Salted membership hashes for any held-out split |
| `annotation_protocol` | The blinded-judgment protocol and raw annotations |
| `baseline_analysis` | IoU and boundary-baseline scores on the same corpus |
| `raw_scores` | Every reported score, unaggregated |
| `failure_cases` | Cases where the metric misorders, with discussion |
| `rerun_script` | The one command that reproduces `raw_scores` |

## Verdict procedure

Grading is by recomputation. The issuer re-runs `rerun_script` from the
retained evidence, recomputes T1 through T5, and applies the shared
decision rule (`research-contracts/rclib.py`): infrastructure failures
invalidate the grading run and are never recorded against the
submission; submission failures, missing evidence keys, or a failing
gate reject; settlement requires every gate recomputed green. Claimant
reported scores never enter the verdict. The executable form of this
procedure is `contract_definitions.py` in this directory, with golden
cases in `eval.yml`.

## What success does not establish

Success establishes better ordering on the declared corpus. It does not
establish optical equivalence, fabrication validity, or a universal
perceptual metric. Scoring-threshold and corpus choices bind the claim
to the shipped suite.

## Claim and settlement

Claim through the [project page](https://pixcell.qpaig.com/#research-contracts)
or by opening a claim-request issue on this repository. The marketplace
record is `contract_71ec83b4b6e1` on
[VVUQ4AI](https://vvuq.dirkenglund.org). Settlement is issuer-graded:
the marketplace's automated Lean verifier cannot check this deliverable
and its verdict is ignored; the issuer grades the evidence bundle
against T1 through T5. The reward is a term of the marketplace listing,
mirrored in `registry.json`; the deadline there is an advisory target
date. Live claim state is always the marketplace's answer, never this
specification's.

## Amendment policy

Terms change only by amendment: a pull request against this directory
that states the previous version, the proposed change, and whether
existing claims survive it. Version bumps follow semver in the
frontmatter.
