---
name: migrate
description: Migrate a GDS design to a target foundry PDK — layer mapping, conversion, and DRC validation
argument-hint: <project_dir or gds_path> [target_pdk]
allowed-tools: Read, Glob, Bash(ls *), mcp__homi-pdk__*, mcp__homi-mj__create_footprint_json
---

# HOMI Migrate: Cross-PDK Synthesis

You are performing cross-PDK migration — taking a photonic device and converting it to a target foundry's process design kit. This is the practical application of the neurosymbolic approach: the Geometric Intent Representation (GIR) enables device portability across fabrication platforms.

## Input

`$ARGUMENTS` — either:
- A project directory (uses the generated GDS)
- A direct path to a GDS file
- Optionally: target PDK name

## Workflow

### Step 1: Analyze Source Process

If a paper PDF is available:
```
mcp__homi-pdk__analyze_paper_process(pdf_path=paper_path)
```

This extracts fabrication parameters from the paper: waveguide thickness, material platform, wavelength, foundry hints.

### Step 2: List Available PDKs

```
mcp__homi-pdk__list_available_pdks()
```

Available targets include:
- Generic Si 220nm (default SOI platform)
- AIM Photonics (220nm SOI with custom layers)
- AMF Singapore (220nm SOI)
- Silicon Nitride (400nm SiN)

### Step 3: Match or Select PDK

If the user specified a target, use that. Otherwise, find the best match:
```
mcp__homi-pdk__match_pdk(process_info)
```

This returns ranked PDK matches with confidence scores.

### Step 4: Understand Layer Mapping

```
mcp__homi-pdk__get_pdk_layer_mapping(pdk_name)
mcp__homi-pdk__list_pdk_layers_full(pdk_name)
mcp__homi-pdk__get_pdk_cross_sections(pdk_name)
```

Explain to the user how generic layers map to the target PDK. For example:
- Layer (1,0) → WGCORE (waveguide core)
- Layer (2,0) → SLAB (partial etch slab)

### Step 5: Convert

```
mcp__homi-pdk__convert_to_pdk(gds_path, pdk_name, output_path)
```

### Step 6: Validate with DRC

```
mcp__homi-pdk__run_drc(converted_gds_path, pdk_name)
```

If DRC violations are found:
```
mcp__homi-pdk__suggest_drc_fixes(violations)
```

**Common DRC issues:**
- Minimum feature width violation → waveguides too narrow for the target process
- Minimum spacing violation → coupling gaps too small
- Minimum bend radius → bends too tight for the target platform

Report violations clearly and suggest whether they can be fixed by parameter adjustment or require redesign.

## Output

Report:
1. Source platform analysis
2. Target PDK and why it was selected
3. Layer mapping applied
4. DRC results — pass/fail with details
5. File path to the converted GDS
6. Any design rule violations that need attention

## Cross-PDK Considerations

When migrating between platforms, key differences to flag:
- **Waveguide width**: 500nm (Si) vs 800nm (SiN) vs 1000nm+ (TFLN)
- **Minimum bend radius**: 5um (Si) vs 50um (SiN)
- **Coupling gaps**: Process-dependent minimum spacing
- **Layer count**: Some PDKs have partial etch, heaters, metal routing
- **Etch depth**: Full etch vs partial etch affects mode confinement
