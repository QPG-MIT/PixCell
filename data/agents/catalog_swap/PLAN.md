# Catalog experiment — gdsfactory components through Phase A/B (resume anchor)

Thesis test at catalog scale: primitives-from-understanding vs pre-parameterized
library cells, across soi220/sin400/tfln400. Protocol = verbatim paper_swap
lineage (same Phase A brief, same evaluator, same verification/audit).

## Matrix
- Components: cat1=mzi cat2=ring_single cat3=mmi1x2 cat4=mmi2x2 cat5=coupler
  cat6=crossing(zero-knob stencil!) cat7=spiral cat8=dbr(n=20)
  (identity ONLY here + stencils/; fixture dirs are neutral cat1..8)
- Models: opus48m (Air panes), codex55h (Mini panes). Frontier-only by design.
- Phase A: 16 panes, ONE wave split across machines (Air 8 claude / Mini 8 codex).
- Phase B v2.0 (free-form discovery): 32 panes (8 comp x 2 models x 2 arms
  {agent-script, stencil-wrapper}), each pane does 3 stacks sequentially.
  Air 16 claude / Mini 16 codex. Arm rule BOTH arms: retune exposed tunables
  only; restructuring forbidden. Briefs never state script provenance.
- Specs: stencil measured on soi220 home = target on all 3 stacks.
  Tier-0 free (FSR, L_c, beat length, delay, lambda_B). Tier-1 home
  measurements needed for cat3/cat4/cat6 IL (~1 FC, NEEDS USER AUTH).
- Then: transcript mining -> distilled portfolio optimizer -> v2.1 equipped
  rerun on held-out components (ring_double, mmi1x4-class).

## Status
- [x] fixtures cat1..8 (device_bw.png + footprint.json), neutral names
- [x] stencil wrappers (8/8 execute; cat6 has zero numeric knobs — ladder datum)
- [x] Phase A briefs x16 rendered; hint-lint PASS (16 benign template-example
      hits identical to the 104-cell protocol; substring FPs documented)
- [ ] LAUNCH — awaiting user go
- [ ] tier-1 home specs (cat3/4/6) — awaiting user cloud auth
