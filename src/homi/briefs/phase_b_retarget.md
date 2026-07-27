PHASE B — retarget your recreated device to each layer stack against its function spec. You are the optimizer; the evaluator and the conductor's FDTD runs measure. Physics reasoning + prediction in writing BEFORE every move.

Stacks: {{STACKS}} — note per-stack single_mode_width_um and min_feature_um.
Specs: {{SPECS}} — the function FoM ONLY (read the spec files; they say WHAT must be met, never WHY) plus a per-stack footprint budget. Tier-1 metrics are measured by the CONDUCTOR (max {{TIER1_CAP}} FDTD calls per stack — budget is real; spend them wisely); you never run cloud jobs.

Per stack (workdir {{WORKDIR}}/<stack>/):
1. Adapt platform constants rule-based: waveguide widths to single_mode_width_um; respect min_feature_um everywhere. Then reason from YOUR OWN Phase-A understanding of what this device is and how it works (your recreation log already contains your classification): derive which geometric quantities must change when the platform physics changes, and WHY — write the derivation into your log BEFORE touching geometry. Ground every choice in tier-0 numbers: the evaluator provides local mode solves (see {{PYTHON}} -m homi.spec_optimization --help — solve / supermodes / multimode / cross-section); pick the solves relevant to YOUR device's physics and cite the numbers your decisions rest on. Do not guess scalings you can compute.
2. Write device_<stack>.py (same parametric contract; primitives only) + a MEASUREMENT FIXTURE fixture_<stack>.py -> fixture_<stack>.gds: the device verbatim, plus fan-out s-bends separating the two outputs to >= 5 um center-to-center and >= 3 um straight stubs, and splitter_meta.json {"port_positions": {"in": [x,y], "out_top": [x,y], "out_bot": [x,y]}} on the separated stubs (the fixture may exceed the device footprint budget; the DEVICE must not — evaluate the device GDS for bbox, the fixture GDS for transmission).
3. Tell the conductor you are ready for a measurement by ending your turn with "MEASURE <stack>: fixture=<path> predicted_T=<x>" — I will run the capped FDTD and reply with the measured transmission/balance. Iterate (reason from the measurement, adjust, request again) within the per-stack cap.
4. Log every iteration in optimization_log.json {iter, params, predicted_T, measured_T, reasoning}. Honest failure beats fudge: if a stack cannot reach the spec target within the cap, record why.
5. After your final stack, end with "PHASE_B DONE: <stack>=<result> for every stack".

{{GIT_RULE}}
