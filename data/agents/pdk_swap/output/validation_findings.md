1. `homi/spec_optimization.py:108` trusts writable mode-cache JSON without re-solving or `_check_sane`; evidence path: `experiments/pdk_swap/output/mode_cache/` contains directly returned cached `n_eff`/`n_g`.

2. `homi/spec_optimization.py:150` trusts script-written `lengths.json` for `delta_length_um`; evidence path: `experiments/pdk_swap/output/optimize_codex/sin400/lengths.json` is consumed as the optical arm-length source, with no independent GDS connectivity measurement.

3. `homi/spec_optimization.py:157` only cross-checks `delta_length_um` when exactly two arms exist; evidence: `len(arms) == 2` gate means `lengths.json` with 3+ arm entries bypasses implied-DeltaL consistency validation.

4. `homi/spec_optimization.py:203` validates knob response using total layer-(1,0) polygon area growth; evidence: `_layer_area()` sums all top-cell polygons, so unrelated dummy geometry can satisfy `width_um * delta_um` without changing the MZI arm.

5. `presentation/pdk_swap_proof/index.html:68` reports baseline miss percentages, but no committed baseline eval JSON exists under `experiments/pdk_swap/output/`; evidence paths: values are reproducible from `experiments/pdk_swap/scaffold.py` + `experiments/pdk_swap/output/mode_cache/`, but no `baseline_eval*.json` artifact is present.

6. `presentation/pdk_swap_proof/index.html:90` claims Opus IoU `0.565 -> 0.628 after JEE polish`; evidence path: `experiments/pdk_swap/output/jee_refine/optimization_result.json` supports 20% SSE improvement, but no committed metrics JSON supports the exact post-polish IoU.

7. `presentation/pdk_swap_proof/index.html:44` overstates provenance with "every number below was re-measured"; evidence: the baseline percentages and JEE-polished IoU are not all present as committed JSON measurements under `experiments/pdk_swap/output/`.
