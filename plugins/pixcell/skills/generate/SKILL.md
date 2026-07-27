---
name: generate
description: Generate GDS from a device image — the Phase-A agent recreate loop (write→verify→refine against calibrated IoU) by default; Michaelangelo multi-seed exploration behind --baseline
argument-hint: "<project_dir or image_path> [preset]"
allowed-tools: Read, Glob, Bash(ls *), Bash(homi *), Bash(pixcell *), Bash(.venv/bin/homi *), Bash(.venv/bin/pixcell *), Bash(*pixcell-engine *), mcp__homi-michaelangelo__*, mcp__homi-raphael__*
---

# HOMI Generate: Device Image to GDS

You are running the GDS generation stage of the HOMI pipeline. Your goal: take a B&W device image with a footprint and produce a fabrication-ready GDS file with parametric GDSFactory code.

## Two modes — the agent loop is the default

**Default (agent recreate loop).** YOU are the generator: run the Phase-A
recreation discipline yourself — the procedure is the packaged brief, printed via

```
"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -c "from homi import briefs; print(briefs.brief_path('phase_a_recreation').read_text())"
```

(if the `homi` CLI is already on PATH — repo checkout or installed package — use its
Python directly; the engine resolver is the fallback for plugin-only installs),
with the `mcp__homi-raphael__*` tools (`execute_gds_script`,
`rasterize_and_compare`, `run_calibration`) as your loop. Primitives only, knobs
as top-level tunables, iterate ≤6× against IoU, honest best. This is what
`homi generate <project>` dispatches a worker to do; as the skill-driven agent
you ARE that worker. Acceptance is the conductor gate
(`homi.conductor.verify_cell`) — never your own reported IoU.

**`--baseline` (multi-seed sweep).** The legacy Michaelangelo Phase 1/2
pipeline below — kept as the paper's measured baseline and for benchmarking.
Use it only when the user asks for the baseline or a preset sweep.

## Input

`$ARGUMENTS` — either:
- A project directory (containing `device_bw.png` and `footprint.json` or a `component/` subdirectory)
- A path to a B&W device image (you'll need to ask for footprint dimensions)
- Optionally, a preset name: `quick`, `balanced`, `thorough`, `maximum`

## Prerequisites

Before generation can start, you need:
1. A B&W device image (pure black on white, clean edges)
2. A footprint (length and width in micrometers)
3. Both placed in a component directory with calibration

If these don't exist yet, tell the user to run the `extract` skill first.

## Workflow

### Step 1: Setup Component Directory

```
mcp__homi-michaelangelo__setup_component_directory(
  image_path="path/to/device_bw.png",
  output_dir="projects/{name}/component",
  footprint={"length_um": 45.0, "width_um": 30.0}
)
```

### Step 2: Run Calibration

```
mcp__homi-michaelangelo__run_calibration(component_dir)
```

This maps physical dimensions to pixel coordinates. Must complete before generation.

### Step 3: Choose Preset

If the user didn't specify, choose based on device complexity:

| Device Type | Recommended Preset | Why |
|------------|-------------------|-----|
| Straight waveguide, taper | `quick` (5 seeds, ~5 min) | Simple geometry |
| Bend, Y-branch | `balanced` (13 seeds, ~10 min) | Moderate complexity |
| Ring resonator, directional coupler | `thorough` (25 seeds, ~20 min) | Fine coupling features |
| MMI, arrayed waveguide | `maximum` (41 seeds, ~40 min) | Complex multi-port geometry |

### Step 4: Phase 1 — Multi-Seed Exploration

```
mcp__homi-michaelangelo__start_phase1_exploration(
  component_dir,
  preset="balanced",
  model="gemini/gemini-3-flash-preview"
)
```

Poll until complete:
```
mcp__homi-michaelangelo__poll_generation_status(task_id)
```

### Step 5: Analyze Phase 1 Results

```
mcp__homi-michaelangelo__get_phase1_results(component_dir)
```

**Interpret the results intelligently:**
- IoU > 0.90 = excellent match, topology is correct
- IoU 0.75-0.90 = good shape but details need refinement
- IoU 0.50-0.75 = rough match, may have structural issues
- IoU < 0.50 = poor match, consider refining the B&W image

If all seeds score below 0.5, the input image may be problematic. Suggest going back to the `extract` skill to refine the B&W variant.

### Step 6: Phase 2 — Extended Iteration

Select the top seeds (typically top 3-5) and run extended iteration:

```
mcp__homi-michaelangelo__start_phase2_iteration(
  component_dir,
  seeds=[top_seed_ids],
  additional_turns=3,
  model="gemini/gemini-3-flash-preview"
)
```

### Step 7: Collect Final Results

```
mcp__homi-michaelangelo__get_phase2_results(component_dir)
mcp__homi-michaelangelo__get_generation_metrics(component_dir)
```

## Output

Report to the user:
1. Best IoU/Dice/SSE achieved
2. Which seed produced the best result
3. File paths: `output/best.gds`, `output/best.py`
4. Assessment of the result quality
5. Suggested next steps: optimize (if IoU < 0.95), explore (for parameter tuning), simulate, or PDK migration

## Alternative: Raphael (Orchestrator-Driven)

For simple devices or when you want direct control over the GDSFactory code, use Raphael instead of Michaelangelo:

```
mcp__homi-raphael__get_gds_catalog()           # See available components
mcp__homi-raphael__execute_gds_script(script)  # Run your own script
mcp__homi-raphael__rasterize_and_compare(...)  # Check IoU
```

This is useful when you can write the GDSFactory code yourself based on the device description, without needing multi-seed exploration.
