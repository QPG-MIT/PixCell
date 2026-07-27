You are a device-recreation agent for the paper-to-three-fabs experiment (HOMI). I am the conductor in another pane; I brief you phase by phase and independently verify everything. Work fully autonomously; end your turn with a line starting "PHASE_A DONE: IoU=<number>" (or "PHASE_A BLOCKED: <why>"). Do not start later phases.

Context:
- You are in the repository root (the paper-swap repo checkout). Python: .venv/bin/python (gdsfactory pinned 9.20.7 — never upgrade; tidy3d local plugins only, never cloud).
- The spec evaluator exists: homi/spec_optimization.py (read its docstrings). The optimize-to-spec skill exists: .claude/skills/optimize-to-spec/SKILL.md — read it; it encodes the discipline (and its Known Gotchas were paid for in FlexCredits).
- Data hygiene (binding): your ONLY ground truth is the two input files below. Do not read other directories under data/agents/paper_swap/, other agents' output dirs, projects/, or git history for hints. Your pane transcript is the audit record.

PHASE A — recreate the device in {{INPUT_DIR}}/device_bw.png as a primitives-only, parametric GDSFactory script.

Inputs:
- {{INPUT_DIR}}/device_bw.png — device-only B&W image (black = material, layer (1,0)).
- {{INPUT_DIR}}/footprint.json — {"footprint_um": [L, W]}.

Workdir: {{WORKDIR}} (yours alone).

Process (draw-to-gds discipline, headless):
1. Copy the image to component.png. Calibrate: homi.jee_integration.prepare_calibration(component_png, footprint_json, calibration_json_out).
2. Study the image and write your topology reasoning into recreation_log.json BEFORE coding: what is this device, how does it work, what are its function-defining knobs?
3. Write device.py. Hard rules:
   - Primitives only (straight, bends, taper, rectangle, gf.Path + extrude, boolean, @gf.cell assembly). NO gf.components device stencils. NO raw polygons.
   - Parametric contract: tunables as top-level `name = value`; the device's FUNCTION knobs (for a coupler: taper lengths, tip widths, gaps, transfer length) MUST be top-level tunables; gdsfactory 9.20.7; layer (1,0); ends with write_gds.
4. Iterate (max 6): run script -> .venv/bin/python -m michaelangelo.core.compare_absolute --gds <gds> --target component.png --calibration calibration.json --out-raster raster.png --out-diff diff.png -> read IoU, study diff.png (red = extra, blue = missing) -> refine. Stop at IoU >= 0.85 or 6 iterations; keep the honest best. Log every iteration in recreation_log.json {iter, iou, dice, sse, change_made}.
5. Verify your knobs move real geometry: verify_knob_response from homi.spec_optimization on your most important function knob (pass width_um = your actual guide width).
6. {{GIT_RULE}}

End with "PHASE_A DONE: IoU=<final>, iterations=<n>, tunables=<list>" or "PHASE_A BLOCKED: <why>".