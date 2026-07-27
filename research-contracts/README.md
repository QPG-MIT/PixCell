# Research Contracts

PixCell's next research directions are issued as research contracts: bounded
units of work whose objective, acceptance tests, required evidence,
and review procedure are fixed before any work begins, and which settle
only after the retained evidence is independently recomputed. This directory is
the canonical registry of those contracts. The paper motivates the form
in its closing section (Research Contracts, `arxiv/main.tex`); the project
page renders this registry at
[pixcell.qpaig.com](https://pixcell.qpaig.com/#research-contracts).

The discipline is the one the paper itself runs on. Throughout PixCell,
no worker-reported number enters the record: acceptance is a
deterministic gate recomputed over declared artifacts
(`src/homi/conductor/gate.py`). A research contract applies the same rule at
the scale of a research direction. The claimant never writes the
verdict.

## The five fixed elements

Every contract fixes, before work begins:

1. **A question** that evidence can settle.
2. **Acceptance tests** (`T1..T5`) that any submission must pass, each
   with a machine-checkable requirement.
3. **The evidence bundle** that must be retained, as a named artifact
   manifest.
4. **A verdict procedure**: a deterministic decision rule over
   issuer-recomputed results, with an explicit failure taxonomy.
5. **A claim boundary**: what success does not establish.

## The contracts

| ID | Slug | Question | Status |
|----|------|----------|--------|
| RC-01 | `rc-01-shape-aware-verification` | What deterministic metric reflects structural agreement without rewarding area-filling shortcuts? | open |
| RC-02 | `rc-02-process-faithful-retargeting` | Can one editable program be retargeted across four process models when its 3D realization is explicit? | open |
| RC-03 | `rc-03-representation-scale-dataset` | Should topology, physical scale, and executable reconstruction be learned jointly or separately? | open |
| RC-04 | `rc-04-smallest-qualifying-open-model` | What is the smallest open-weight model that stays effective across the PixCell task tiers? | open |

Each contract directory contains:

- `SPEC.md`: the human-readable contract. YAML frontmatter (uuid, slug,
  version, status, created, category) followed by the question,
  acceptance tests, required evidence, verdict procedure, and claim
  boundary.
- `config.yaml`: the machine-readable binding. Governing gates with
  status and evidence fields, claim boundaries, marketplace linkage,
  and the literal commands a reviewer re-runs.
- `contract_definitions.py`: the contract's data (gates, evidence keys)
  bound to the shared verdict engine. Pure and deterministic; this is
  the executable form of the verdict procedure.
- `eval.yml`: golden cases for the verdict logic, including every
  rejection path worth preserving.

`registry.json` is the machine-readable index of all four contracts.
`rclib.py` is the shared pure verdict engine. `validate.py` checks the
structural invariants of the whole tree; CI runs the same checks through
`tests/test_research_contracts.py`.

## Verdict procedure and failure taxonomy

Grading distinguishes submission failures from infrastructure failures.
A submission is graded by recomputation: the issuer re-runs the declared
checks from the retained evidence and never accepts claimant-reported
results. The decision rule, in order:

```
if any infrastructure failure occurred while grading
        (verifier crash, service outage, corrupt reference artifact,
         evaluator timeout, environment mismatch):
    verdict = NOT_SCORED        # the grading run is invalid; regrade.
                                # Never recorded against the submission.
elif any submission failure occurred
        (syntax error, purity violation, runtime failure,
         missing artifact, non-reproducible rerun):
    verdict = REJECTED          # with the failure codes
elif any required evidence key is missing, or any acceptance gate
        fails under issuer recomputation:
    verdict = REJECTED          # with the missing keys and failing gates
else:
    verdict = SETTLED           # every gate recomputed green
```

Measurement stays separate from the verdict: gates report pass or fail
from recomputation; the decision rule above is the only place a verdict
is formed. `rclib.py` implements it; each contract's `eval.yml` pins its
behavior with golden cases.

## Lifecycle

Contract status follows the research-contracts vocabulary: `draft`, `red`,
`open`, `in_progress`, `green`, `certified`, `deprecated`. All four
contracts are `open`: published and claimable. Gates start `red` and
turn `green` only when an accepted submission's evidence exists; green
gates must carry evidence. Red is honest: it means the evidence does not
yet exist, not that work failed. Terms change only by amendment through
a pull request that states the previous version, the change, and whether
existing claims survive it.

## Claiming and settlement

Contracts are published as funded bounties on the
[VVUQ4AI marketplace](https://vvuq.dirkenglund.org). The claim flow runs
through the [project page](https://pixcell.qpaig.com/#research-contracts);
a claim request can also be opened as an issue on this repository.
Settlement is issuer-graded with independent recomputation: the
marketplace's automated Lean verifier cannot check these deliverables,
so the issuer grades the evidence bundle against the acceptance tests
and pays by TFT transfer against the marketplace contract. Rewards live in `registry.json`
and on the marketplace record. Deadlines are advisory target dates
stated in the contract descriptions; the marketplace record carries no
enforced deadline field. Live claim state (who holds a claim, escrow,
open or claimed) is always the marketplace's answer, never this tree's.

Directions whose acceptance tests cannot yet be frozen are not
contracts. The paper names two, circuit-scale verification and program
recovery from legacy GDS archives; they will be issued here once their
gates can be written in the form above.
