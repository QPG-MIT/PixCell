# Phase B v2.0 arm brief (catalog retune; rendered per cell: {CAT}, {ARM})

PHASE B RETUNE — your working directory is
data/agents/catalog_swap/{CAT}/output/retune_arm{ARM}/

It contains device.py — a parametric GDSFactory 9.20.7 script (layer (1,0)).
Retune it to meet a function specification on three fabrication stacks.

Specs (read them; they say WHAT must be met, never WHY):
  ../../spec_soi220.json  ../../spec_sin400.json  ../../spec_tfln400.json
Stack definitions (core/clad indices, thickness, single_mode_width_um, min_feature_um):
  data/agents/paper_swap/final1/stacks/{soi220,sin400,tfln400}.json

Evaluator (deterministic, local; run with the repo venv):
  .venv/bin/python -m homi.spec_optimization --help
  (subcommands: eval to judge device.py against a spec on a stack; solve /
  supermodes / multimode / cross-section for tier-0 mode data. Ground every
  geometric decision in numbers you computed, not guessed scalings.)

Task, one stack at a time (soi220, then sin400, then tfln400): adapt platform
constants rule-based (waveguide width to the stack's single_mode_width_um;
respect min_feature_um everywhere), reason from the physics of what this
device is to derive which exposed values must change and why, then evaluate.

HARD RULES
- Change ONLY the values of tunables already exposed in device.py.
  Restructuring is forbidden: no new primitives, no removed elements, no
  topology changes, no new parameters.
- Max 6 eval calls per stack. Predict before you measure: BEFORE every eval
  call append to optimization_log.json
  {stack, iter, changed_params, predicted_value, reasoning}; after the call
  record the measured value and rel_error.
- Per stack, when done (pass, or honestly out of budget), write
  result_<stack>.json: {"tunables": {..final values for that stack..},
  "evaluator_report": <full eval JSON>, "calls_used": N}.
- The device must fit the spec's max_footprint_um on every stack.
- Honest failure beats fudge. If a stack cannot pass using only the exposed
  tunables, set "infeasible_within_representation": true in result_<stack>.json
  with your reasoning.
- Do not run git commands. Do not modify anything outside your working
  directory. Do not open or edit any other directory under catalog_swap.
- End your final message with exactly:
  PHASE_B DONE: soi220=<pass|fail> sin400=<pass|fail> tfln400=<pass|fail>
