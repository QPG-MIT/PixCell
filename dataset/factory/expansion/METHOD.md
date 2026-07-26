# Expansion method — approval draft

Status: **preview only**. This plan does not generate or admit any new dataset
rows. `core-v1` remains immutable.

## Identity model

Every proposed example has four independent identities:

```text
representation_id
  └── realization_id
        └── pose_id
              └── render_id
```

- `representation_id` changes only when the construction grammar or topology
  changes.
- `realization_id` changes for a deliberately selected physical parameter
  regime within the same grammar.
- `pose_id` changes for a useful rotation or reflection of the same physical
  construction.
- `render_id` changes only the input presentation. It never counts as new
  geometry or a new representation.

Every descendant of one representation belongs to the same leakage group.

## Four proposal lanes

### A. New representation grammars

Examples include a different coupling mechanism, branch graph, repetition
schedule, material transition, multi-zone hierarchy, or port topology. This is
the highest-value lane, especially for L3 and L4.

New grammars must state what visual/program structure is new relative to the
nearest `core-v1` row. A new component name alone is not enough.

### B. Controlled realizations

Each selected grammar receives only a few causal regimes, for example:

- compact, nominal, and elongated;
- weak, nominal, and strong gap;
- low, medium, and high repeated-element count;
- symmetric and intentionally asymmetric;
- ordinary and near-degenerate but still legible.

Small random width or length jitter is forbidden. A realization must make a
visible, explainable difference while preserving the representation grammar.

### C. Equivariance and pose

Rotations or reflections are proposed only when they exercise code, port, or
coordinate behavior that the base row does not already make trivial. Exhaustive
D4 multiplication is forbidden.

### D. Visual-domain rendering

The maximally visible black-and-white view remains the primary supervision
image. Optional companion renders may include true physical aspect, paper-like
layout, screenshots, crop/context, antialiasing, or later multilayer/color
views. These are separate render configurations, never new representations.

## Level-specific expansion

| Level | Primary expansion unit |
|---|---|
| L0 | Constructor modes, useful physical regimes, and non-trivial pose behavior for the 22 primitive APIs. |
| L1 | One explicit operation with different operand types, arity, signed direction, or causal regime. |
| L2 | Small operation graphs: chains, branches, arrays, morphology, repetition, and relational motifs. |
| L3 | New coherent multi-zone topology: bodies, routes, branches, repeated media, defects, radial/cyclic hierarchy. |
| L4 | New component mechanisms and under-covered visual grammars, balanced by family rather than name count. |

## Audit-driven first wave

The first wave contains exactly 100 proposed representation grammars and no
realization, pose, render, or repair descendants:

| Level | Proposed grammars | Evidence-backed purpose |
|---|---:|---|
| L1 | 12 | Close four missing L0→L1 primitive bridges and make terminal/port operations explicit. |
| L2 | 24 | Add port-aware split/rejoin, coupling, loop, crossing, body-terminal, and repeated-media motifs. |
| L3 | 32 | Build explicit photonic mechanism bridges rather than more generic hierarchy. |
| L4 | 32 | Add mux/demux, cascaded-filter, multiport repeated-media, interferometric, mode-mux, and interface mechanisms. |

The allocation comes from
[`core-v1-coverage.md`](core-v1-coverage.md). Crossings, plain 2×2 directional
couplers, single-ring variants, and parameter-only tooth changes are
deprioritized because `core-v1` already covers those forms or because they
belong in the realization lane.

Every proposed L4 grammar names an L3 prerequisite and a visible mechanism
bridge. The proposal compiler renders primitive-built silhouettes, checks exact
and D4 aliases against the 547 semantic core anchors, and records both an
author-declared semantic neighbor and computed visual neighbors. These are
review aids; none of the 100 proposals is a dataset row until separately
approved and admitted.

Controlled realizations, useful poses, render companions, and failure-derived
repair trajectories remain later, separate configurations. Their size will be
chosen only after the grammar wave is reviewed.

## Admission pipeline

```text
proposal specification
    → executable primitive-only program
    → isolated compile/runtime gate
    → ports/topology/structural witnesses
    → calibrated target + maximum-visibility view
    → geometry, footprint, legibility, and duplicate checks
    → review dossier and visual contact sheet
    → explicit human approval
    → new versioned configuration
```

The gates do not all become equal-weight RL rewards. Compilation and purity are
hard constraints. Geometry remains a continuous signal. Structural gates apply
only when a candidate declares that structure. Human review occurs before any
expansion is merged or trained on.

## Publication boundary

Possible future configurations are intentionally separate:

- `new-grammars-v1`
- `controlled-realizations-v1`
- `render-variants-v1`
- `repair-trajectories-v1`

The last track is produced only from real model failures and verifier feedback.
Rejected candidates and repair trajectories never enter accepted `core-v1`.
