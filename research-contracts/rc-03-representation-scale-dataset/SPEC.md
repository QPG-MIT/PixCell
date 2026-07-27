---
uuid: 111b4060-c967-42e4-80f0-600d3d7a29cd
slug: rc-03-representation-scale-dataset
version: 1.0.0
status: open
created: 2026-07-27
category: process
domain: photonics
source: https://pixcell.qpaig.com/#research-contracts
---

# RC-03: Representation and scale dataset

## Question

Should topology recognition, evidence-backed physical scale, and
executable reconstruction be learned jointly or as separately
supervised problems?

## Objective

A versioned, licensed corpus that separates the three learning problems
PixCell currently entangles, with protected splits and a matched-compute
comparison of joint and staged supervision. The paper's training study
could not isolate pixel-only perception because footprint is part of
the model input; this contract buys the corpus that makes such
questions separable.

## Definitions

- **Annotation layers**: (i) topology labels describing component
  structure and connectivity; (ii) scale evidence recording where
  physical size comes from (calibration source, scale bar, stated
  footprint), or an explicit no-scale-evidence flag; (iii) an
  executable program or verified reconstruction.
- **Protected splits**: in-family, held-out-topology, and
  held-out-paper splits published as salted membership hashes, so
  membership can be verified after the fact without revealing the
  split.
- **Abstention**: the scorer output for items with no scale evidence.
  Physical size is not identifiable from an unscaled silhouette, so
  abstention is the only correct behavior there and the benchmark must
  enforce it.

## Acceptance tests

All five are required. Settlement is all-or-nothing.

| ID | Requirement | Check |
|----|-------------|-------|
| T1 | Corpus integrity. | Versioned corpus with per-item sha256, source provenance (paper, page, crop), and a machine-checkable license manifest; zero items without a license entry. |
| T2 | Layer separation. | Every item carries the three separable annotation layers, all schema-validated. |
| T3 | Protected splits with leakage audit. | The three splits are published as salted membership hashes; a shipped near-duplicate and perceptual-hash audit shows zero crossover into protected splits. |
| T4 | Abstention enforced. | Items without scale evidence are marked abstain and the scorer counts abstention as the only correct behavior there. |
| T5 | Matched-compute comparison. | Joint and staged supervision compared at a logged, matched compute budget; baselines, raw scores, and an out-of-distribution error taxonomy ship; one rerun script reproduces the headline table from the shipped corpus. |

## Required evidence

| Key | Artifact |
|-----|----------|
| `source_manifest` | Every source with paper, page, and crop provenance |
| `license_manifest` | Machine-checkable license entry per item |
| `provenance_records` | Extraction tool, command, and time per item |
| `calibration_records` | Scale evidence or the explicit no-scale-evidence flag |
| `topology_annotations` | The topology label layer, schema-validated |
| `scale_evidence` | The scale evidence layer, schema-validated |
| `programs_or_reconstructions` | The executable layer, schema-validated |
| `split_hashes` | Salted membership hashes for the three splits |
| `leakage_audit` | Near-duplicate and perceptual-hash crossover report |
| `baselines` | Baseline scores under the declared protocol |
| `compute_log` | The logged compute budget for both curricula |
| `error_taxonomy` | Out-of-distribution error taxonomy |
| `rerun_script` | The one command that reproduces the headline table |

## Verdict procedure

Grading is by recomputation under the shared decision rule
(`research-contracts/rclib.py`): the issuer validates the schemas, reruns
the leakage audit, verifies split hashes, checks the license manifest
for full coverage, and reruns the headline table from the shipped
corpus. Claimant-reported scores never enter the verdict. The
executable form is `contract_definitions.py`; golden cases in
`eval.yml`.

## What success does not establish

Results are bounded to the released families and protected splits. The
corpus does not by itself settle the joint-versus-staged question
beyond the compared curricula and compute budget, and it does not
establish that any model trained on it generalizes past the audited
distribution.

## Claim and settlement

Claim through the [project page](https://pixcell.qpaig.com/#research-contracts)
or by opening a claim-request issue on this repository. The marketplace
record is `contract_3a48cb45d01f` on
[VVUQ4AI](https://vvuq.dirkenglund.org). Settlement is issuer-graded;
the marketplace's automated Lean verifier does not apply. The reward is
a term of the marketplace listing, mirrored in `registry.json`; the
deadline there is an advisory target date. Live claim state is always
the marketplace's answer, never this specification's.

## Amendment policy

Terms change only by amendment: a pull request against this directory
that states the previous version, the proposed change, and whether
existing claims survive it. Version bumps follow semver in the
frontmatter.
