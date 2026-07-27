---
name: simulate
description: Upload a GDS device to Tidy3D for FDTD optical simulation — configure materials, wavelength, and monitor results
argument-hint: "<project_dir or gds_path> [material]"
allowed-tools: Read, Glob, Bash(ls *), mcp__homi-flex__*, mcp__homi-pdk__get_layer_material_properties
---

# HOMI Simulate: Tidy3D FDTD Simulation

You are setting up an FDTD optical simulation of a photonic device using Tidy3D's cloud service.

## Input

`$ARGUMENTS` — either:
- A project directory (uses `output/best.gds`)
- A direct path to a GDS file
- Optionally: material platform name

## Prerequisites

- A valid Tidy3D API key (set as `TIDY3D_API_KEY` in `.env`)
- A GDS file to simulate

## Workflow

### Step 1: Verify Tidy3D Availability

```
mcp__homi-flex__is_tidy3d_available()
mcp__homi-flex__validate_api_key(api_key)
```

### Step 2: Choose Material Platform

```
mcp__homi-flex__get_material_presets()
```

Common platforms:
- **Silicon (SOI)**: 220nm Si on SiO2, n_core=3.48, n_clad=1.44 — most common
- **Silicon Nitride**: 400nm SiN on SiO2, n_core=2.0, n_clad=1.44 — low loss
- **TFLN**: Thin-film lithium niobate — electro-optic

If the paper specifies the platform, use that. Otherwise default to Silicon (SOI) at 1550nm.

If using a PDK, get exact material properties:
```
mcp__homi-pdk__get_layer_material_properties(pdk_name, layer_name)
```

### Step 3: Preview Simulation

```
mcp__homi-flex__get_simulation_info(
  gds_path,
  layers=[[1, 0]],
  thickness_nm=220,
  wavelength_um=1.55
)
```

Review the simulation bounds, grid resolution, and estimated runtime before uploading.

### Step 4: Create and Upload

```
mcp__homi-flex__create_and_upload_simulation(
  gds_path,
  api_key,
  material="Silicon (SOI)",
  thickness_nm=220,
  wavelength_um=1.55,
  task_name="HOMI_{device_name}"
)
```

**Standing rule: cloud simulations are NEVER auto-started.** Upload creates a
draft; you hand the human the workbench URL and THEY press Start. Spend
authority is human authority.

### Step 5: Monitor and Access Results

```
mcp__homi-flex__get_task_status(task_id)
mcp__homi-flex__get_workbench_url(task_id)
```

## Output

Report:
1. Simulation configuration (material, thickness, wavelength)
2. Task ID for tracking
3. Tidy3D Workbench URL for viewing results
4. Expected simulation time estimate
