---
uuid: 1d11329c-b901-4526-8186-7683c7871407
slug: rc-04-smallest-qualifying-open-model
version: 1.0.0
status: open
created: 2026-07-27
category: synthesis
domain: photonics
source: https://pixcell.qpaig.com/#research-contracts
---

# RC-04: Smallest qualifying open model

## Question

What is the smallest open-weight model, counted in active parameters,
that remains effective across the five PixCell task tiers and untouched
paper figures?

## Objective

Identify and release the smallest open-weight model in a frozen
candidate set that stays effective on the versioned tier suite under a
frozen protocol. The paper's training study established bounded
feasibility for verifier-derived training on one base model; this
contract buys the size frontier: how small a model can hold the
capability when the protocol cannot move after the fact.

## Definitions

- **Task tiers**: the five levels of the PixCell curriculum, from raw
  primitive reproduction to composite devices, as versioned in
  `dataset/` (admission policy: `dataset/factory/admission_policy.json`).
- **Untouched paper figures**: benchmark figures excluded from every
  training and development loop of the submission.
- **Active parameters**: parameters active in a forward pass. For dense
  models this equals total parameters; for mixture models it is the
  routed activation count. LoRA adapter size and quantized file size do
  not qualify.
- **Frozen candidate registry**: the dated, sha256-committed list of
  candidate models, per-tier floors, and inference and verifier
  budgets, fixed before any evaluation. Late additions void the run.

## Acceptance tests

All five are required. Settlement is all-or-nothing.

| ID | Requirement | Check |
|----|-------------|-------|
| T1 | Freeze first. | Candidate registry, per-tier floors, and identical inference and verifier budgets committed (sha256) before any evaluation; the preregistration commit predates every scored run. |
| T2 | Identical budgets, full raw record. | Every candidate evaluated on the versioned tier suite plus held-out untouched paper figures under the same budgets; all attempts, including failures, ship raw. |
| T3 | Recomputable bounds. | The issuer independently recomputes confidence bounds from shipped raw programs and scores using the shipped bootstrap script; the claimed qualifier meets the frozen per-tier floor. |
| T4 | No source violations. | Generated programs pass the PixCell conductor gate purity rules (catalog whitelist, no raster tracing, no coordinate dumps); the issuer reruns the gate on a sample. |
| T5 | Release and accounting. | The minimum qualifying model ships with weights, license, model and data cards, training lineage, total and active parameter accounting, inference recipe, latency, and compute; the performance-size frontier is reported. |

## Required evidence

| Key | Artifact |
|-----|----------|
| `candidate_registry` | The frozen, dated candidate list |
| `tier_floors` | The frozen per-tier score floors |
| `budget_manifest` | The identical inference and verifier budgets |
| `preregistration_commit` | Commit hash fixing registry, floors, and budgets |
| `raw_programs` | Every generated program, all candidates |
| `all_attempts` | Every attempt including failures, raw |
| `scores` | Per-attempt scores under the declared verifier |
| `bounds_script` | The bootstrap script that recomputes confidence bounds |
| `purity_gate_results` | Conductor-gate results on the sampled programs |
| `release_bundle` | Weights, license, model and data cards, lineage, recipe |
| `parameter_accounting` | Total and active parameter counts, with method |
| `runtime_accounting` | Latency and compute per candidate under the frozen budgets |
| `frontier_analysis` | The performance-size frontier across candidates |

## Verdict procedure

Grading is by recomputation under the shared decision rule
(`research-contracts/rclib.py`): the issuer verifies the preregistration
hashes and dates, recomputes bounds with `bounds_script` from
`raw_programs` and `scores`, and reruns the conductor purity gate on a
sample. Claimant-reported bounds and scores never enter the verdict.
The executable form is `contract_definitions.py`; golden cases in
`eval.yml`.

## What success does not establish

"Smallest" means the smallest qualifier among the dated entries of the
frozen registry under this protocol. It is not a global optimum over
all open models, and it is not a claim about LoRA parameter counts or
quantized file sizes. Effectiveness is bounded by the tier suite
version and the frozen budgets.

## Claim and settlement

Claim through the [project page](https://pixcell.qpaig.com/#research-contracts)
or by opening a claim-request issue on this repository. The marketplace
record is `contract_abb35955056a` on
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
