---
name: optimize
description: Fine-tune GDS parameters using JEE optimizer — SSE minimization to match target device geometry
argument-hint: "<project_dir or script_path> [method]"
allowed-tools: Read, Glob, Bash(ls *), mcp__homi-jee__*, mcp__homi-michaelangelo__get_generation_metrics
---

# HOMI Optimize: Parameter Fine-Tuning

You are running the JEE parameter optimization stage. Your goal: take a generated GDSFactory script and fine-tune its numeric parameters to minimize the geometric difference (SSE) between the generated layout and the target device image.

## Input

`$ARGUMENTS` — either:
- A project directory (containing `output/best.py` and `component/` with target image)
- A direct path to a GDSFactory script
- Optionally: optimization method (`nelder-mead` or `powell`)

## When to Use This

- After the `generate` skill when IoU is good (>0.80) but not excellent (<0.95)
- When the generated layout has the right topology but slightly wrong dimensions
- To close the gap between generated and target geometry

**Don't use this when:**
- IoU is below 0.50 — the script needs regeneration, not optimization
- The topology is wrong (e.g., missing ports, wrong connectivity) — optimization can't fix structural issues

## Workflow

### Step 1: Extract Tunable Parameters

```
mcp__homi-jee__extract_parameters(script_path)
```

This parses the GDSFactory script and identifies numeric parameters with suggested bounds. Review the output — some parameters matter more than others:

- **Critical**: coupling gap, waveguide width, coupling length, bend radius
- **Secondary**: taper length, offset, extension lengths
- **Usually fixed**: layer numbers, port widths at interfaces

### Step 2: Prepare Calibration

```
mcp__homi-jee__prepare_calibration(
  target_image="component/component.png",
  footprint_json="component/footprint.json",
  output_path="output/jee_calibration.json"
)
```

### Step 3: Choose Optimization Strategy

**Single optimization** (fast, good for fine-tuning):
```
mcp__homi-jee__run_optimization(
  script_path, target_image, calibration_file, output_dir, param_bounds,
  max_iterations=150,
  method="Nelder-Mead"
)
```

**Exploration** (thorough, good for finding global optimum):
```
mcp__homi-jee__run_exploration(
  script_path, target_image, calibration_file, output_dir,
  grid_points_per_param=5,
  top_n_for_optimization=3,
  max_iterations_per_method=100
)
```

Exploration does a grid search first, then runs both Powell and Nelder-Mead from the best grid points. Use this when you're not sure which parameter region is optimal.

### Step 4: Monitor Progress

```
mcp__homi-jee__poll_optimization(task_id)
# or
mcp__homi-jee__poll_exploration(task_id)
```

### Step 5: Get Results

```
mcp__homi-jee__get_optimization_result(task_id)
# or
mcp__homi-jee__get_exploration_result(task_id)
```

### Step 6: Apply Optimized Parameters

```
mcp__homi-jee__apply_parameters(script_path, optimized_params, output_dir)
```

This generates a new GDS file with the optimized parameters.

## Output

Report:
1. Which parameters changed and by how much
2. SSE improvement percentage
3. Before/after comparison
4. Whether the improvement is physically meaningful (e.g., "The gap narrowed from 0.25 to 0.21 um, matching the paper's 0.2 um specification")
5. File paths to the optimized script and GDS

## Parameter Sensitivity Guidance

For common photonic devices:

| Device | Most Sensitive Parameter | Typical Range |
|--------|------------------------|---------------|
| Directional coupler | coupling gap | 0.1-0.5 um |
| Ring resonator | ring radius, coupling gap | 5-50 um, 0.1-0.5 um |
| MMI | MMI width, MMI length | 2-10 um, 5-50 um |
| Y-branch | taper length, branch angle | 5-20 um, 1-10 deg |
| Grating coupler | period, fill factor | 0.5-1.0 um, 0.3-0.7 |
