---
uuid: 92a1bfba-9df6-48f3-a13e-8f369799d0b1
slug: rc-02-process-faithful-retargeting
version: 1.0.0
status: open
created: 2026-07-27
category: physics
domain: photonics
source: https://pixcell.qpaig.com/#research-contracts
---

# RC-02: Process-faithful 2D-to-3D retargeting

## Question

Can one editable primitive program be retargeted across four process
models when its three-dimensional realization is explicit?

## Objective

One parametric program, four versioned layer-stack manifests, four
independently rerunnable Tidy3D artifact sets that meet preregistered
gates. The paper's retargeting study used simplified two-dimensional
stack models; this contract buys the three-dimensional version, where
each retarget emits the full layer-stack geometry and the simulation
inputs specify the structure completely.

## Definitions

- **Primitive program**: a parametric GDSFactory script restricted to
  the PixCell catalog, with function-relevant dimensions named and
  editable. Catalog purity rules are those of the conductor gate
  (`src/homi/conductor/source_policy.py`).
- **Stack manifest**: a versioned JSON description of one process
  model: materials, layer thicknesses, refractive indices, and any
  process parameters the simulation consumes. The repository ships
  reference manifests under `src/homi/assets/stacks/` (`soi220`,
  `sin400`, `tfln400`). Claimants may supply their own manifests in the
  same schema, including manifests derived from a foundry PDK; each
  must be versioned and hashed in the preregistration commit. Four
  distinct manifests are required in total.
- **Preregistration commit**: a single commit, made before any scored
  simulation runs, whose sha256-hashed contents fix the functional,
  footprint, process, and convergence gates and the four stack
  manifests.

## Acceptance tests

All five are required. Settlement is all-or-nothing.

| ID | Requirement | Check |
|----|-------------|-------|
| T1 | One program, four stacks, identical topology. | AST-level diff between per-stack variants shows only named-parameter value changes, no per-stack code forks; the program passes the catalog purity rules. |
| T2 | Explicit three-dimensional realization. | Each retarget emits the full 3D layer-stack geometry; simulation inputs fully specify the structure; geometry hashes are recorded per stack. |
| T3 | Preregistered gates met on all four stacks. | Gates were committed (sha256) before simulation; all four stacks' Tidy3D artifacts meet them; the issuer independently reruns at least one stack from shipped inputs and matches reported S-parameters within the stated tolerance. |
| T4 | Audits recomputed from shipped fields. | Mesh-refinement convergence study and energy-conservation checks per stack, recomputed by the issuer from shipped field data; solver-log numbers are not accepted. |
| T5 | Control and full reproduction. | A fixed-geometry cross-stack control isolates process-model effects from solver artifacts; one rerun script reproduces every reported number; task identifiers and compute cost are disclosed. |

## Required evidence

| Key | Artifact |
|-----|----------|
| `program_source` | The parametric program with named parameters |
| `named_parameters` | Per-stack parameter values, as data |
| `stack_manifests` | The four versioned, hashed stack manifests |
| `preregistration_commit` | Commit hash fixing gates and manifests before simulation |
| `generated_geometry` | Full 3D geometry per stack, with hashes |
| `simulation_inputs` | Complete Tidy3D inputs per stack |
| `field_records` | Field data sufficient to recompute the audits |
| `sparameter_results` | Reported S-parameters per stack, as data |
| `mesh_audit` | Mesh-refinement convergence study per stack |
| `conservation_audit` | Energy-conservation checks per stack |
| `control_results` | The fixed-geometry cross-stack control |
| `task_identifiers` | Tidy3D task ids for every scored run |
| `cost_ledger` | Compute cost of every scored run |
| `rerun_script` | The one command that reproduces every reported number |

## Verdict procedure

Grading is by recomputation under the shared decision rule
(`research-contracts/rclib.py`): the issuer reruns at least one stack from
`simulation_inputs`, recomputes both audits from `field_records`,
verifies the preregistration hashes, and re-applies the catalog purity
rules to `program_source`. Infrastructure failures (including cloud
solver outages) invalidate the grading run and are regraded; they are
never recorded against the submission. Claimant-reported S-parameters,
audit numbers, and solver-log values never enter the verdict. The
executable form is `contract_definitions.py`; golden cases in
`eval.yml`.

## What success does not establish

The result concerns simulation-backed retargeting on the four declared
process models. It is not foundry signoff, tape-out readiness, or
measured hardware performance. Claims are bounded by the fidelity of
the declared models and the stated tolerances.

## Claim and settlement

Claim through the [project page](https://pixcell.qpaig.com/#research-contracts)
or by opening a claim-request issue on this repository. The marketplace
record is `contract_f55f58150008` on
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
