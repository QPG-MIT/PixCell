---
name: homi
description: Full paper-to-GDS pipeline — extracts photonic devices from research papers and generates fabrication-ready GDS files
argument-hint: <paper.pdf or image> [device description]
allowed-tools: Read, Glob, Grep, Bash(ls *), Bash(cat *footprint*), Bash(homi *), Bash(pixcell *), Bash(.venv/bin/homi *), Bash(.venv/bin/pixcell *), Bash(*pixcell-engine *), Bash(streamlit run *), mcp__homi-mj__*, mcp__homi-michaelangelo__*, mcp__homi-jee__*, mcp__homi-weber__*, mcp__homi-flex__*, mcp__homi-pdk__*, mcp__homi-raphael__*
---

# HOMI: Paper-to-GDS Pipeline

You are orchestrating the HOMI neurosymbolic pipeline. Your job is to convert a photonic device — from a research paper, hand-drawn sketch, or device image — into a fabrication-ready GDS file with parametric GDSFactory code.

**You are not a button-clicker.** At each stage, you reason about the results, make intelligent decisions, and explain your choices to the user. You are the intelligence layer between the raw tools and the designer.

**CLI invocation rule:** if the `homi` CLI is already on PATH (repo checkout or
installed package), use it directly. Otherwise invoke through the plugin's engine
resolver — `"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" homi <args>` — which finds or
bootstraps the PixCell Python engine (first run installs the gdsfactory stack; minutes).

## Input

The user provides `$ARGUMENTS` which can be:
- A path to a PDF research paper (most common)
- A path to a device image (PNG/JPEG)
- A path to an existing project directory (to resume)
- A device description to search for in a previously loaded paper

## Pipeline Overview

```
Extract → B&W → Footprint → Calibrate → Recreate (agent loop) → Gate → Optimize → Explore
```

Each stage feeds the next. You manage the project state in `projects/{name}/`.

**Generation default is the agent recreate loop** (the `generate` skill: you
write a primitives-only parametric script and iterate against the calibrated
IoU verifier via `mcp__homi-raphael__*`; acceptance is
`homi.conductor.verify_cell`, never your own reported score). The Michaelangelo
multi-seed Phase 1/2 pipeline described below is the **`--baseline` mode** —
the paper's measured chatbot-era baseline, kept for benchmarking and preset
sweeps. Spec retargeting across stacks is `homi retarget` (Phase-B protocol,
conductor-serviced measurements).

---

## Stage 1: Source Processing

### If the input is a PDF:

1. **See where the figures are.** Device schematics are often vector-drawn and invisible to embedded-image extraction, so start with the diagnostic:
   ```
   mcp__homi-mj__analyze_pdf_figures(pdf_path)
   ```
   Pages with high `vector_draw_ops` and 0 `embedded_images` are vector figures — the usual home of the device schematic. Use `recommend_render`.

2. **Render and LOOK.** *You* are the perception — there is no scoring tool; you use your own eyes:
   ```
   mcp__homi-mj__render_pdf_pages(pdf_path, output_dir, pages=recommend_render)
   ```
   `Read` each rendered page yourself and decide which holds the device schematic:
   - Is it a top-down layout/schematic with ports at the edges and dimension labels? (good — this is what we want)
   - Is it a cross-section? (useful for dimensions but not for GDS generation)
   - Is it a graph/plot/mode profile? (skip)
   - Is it a microscope/SEM image? (possible but harder to process)
   - If the user specified a device description (e.g., "ring resonator from Figure 3"), use that to narrow down.
   (Embedded rasters such as SEM photos can also be pulled with `mcp__homi-mj__extract_images_from_pdf` if useful.)

3. **Crop the device, then verify.** Read off a tight pixel bbox and cut it — you supply the box, the tool just crops:
   ```
   mcp__homi-mj__crop_region(page_image_path, bbox, output_path)
   ```
   `Read` the crop back; re-crop if a port is clipped or a neighboring panel/caption bleeds in. For a multi-panel figure, crop just the device panel.

4. **Generate B&W variants** — binary silhouettes of the device (Gemini generates; you judge with your own eyes):
   ```
   mcp__homi-mj__generate_bw_variants(cropped_image, output_dir, num_variants=5)
   ```

5. **Evaluate B&W quality.** Read each variant image and assess:
   - Are waveguides clearly defined with consistent width?
   - Are coupling regions preserved?
   - Is noise/background removed cleanly?
   - Are ports at the edges (not floating mid-image)?
   - If a variant needs refinement:
     ```
     mcp__homi-mj__refine_bw_image(source_image_path, output_dir, custom_instructions)
     ```

**Present your selection to the user** with reasoning: "I selected page3_img1 (score 8/10) — it shows a top-down schematic of the directional coupler with labeled ports and dimensions. The B&W variant 3 best preserves the coupling region geometry."

### If the input is an image:
Skip extraction. Go directly to B&W variant generation (step 5 above).

### If the input is a project directory:
Read `state.json` to determine where the pipeline left off, and resume from that point.

---

## Stage 2: Footprint Extraction

The footprint defines the physical dimensions of the device in micrometers.

1. **Read the footprint dimensions yourself** from the figure's dimension labels, the caption, and any parameter table (`Read` the relevant rendered pages) — then record them:
   ```
   mcp__homi-mj__create_footprint_json(length_um, width_um, output_path)
   ```

2. **Cross-reference with the paper text.** If you have access to the PDF:
   - Look for explicit dimension statements: "The device footprint is 200 x 50 um"
   - Check figure captions for scale bars
   - Look in the methods/fabrication section for waveguide widths and coupling lengths
   - If the paper says "coupling length = 12 um" but the extraction says 15 um, flag the discrepancy

3. **Create the footprint file**:
   ```
   mcp__homi-mj__create_footprint_json(length_um, width_um, output_path)
   ```

4. **Report to the user**: "Footprint extracted: 45.0 x 30.0 um. The paper mentions a 220nm SOI platform with 500nm waveguide width in Section 3. These dimensions are consistent with the figure scale bar."

**If dimensions can't be extracted automatically**, ask the user for the footprint dimensions. Provide guidance: "Common photonic device footprints range from 10-500 um. Ring resonators are typically 20-80 um diameter. Directional couplers are typically 50-300 um long."

---

## Stage 3: GDS Generation (--baseline multi-seed mode)

> Default generation is the agent recreate loop (see Pipeline Overview and the
> `generate` skill). This stage documents the baseline sweep.

### Setup

1. **Create the component directory**:
   ```
   mcp__homi-michaelangelo__setup_component_directory(image_path, output_dir, footprint)
   ```
   Where `footprint` is `{"length_um": L, "width_um": W}`.

2. **Run calibration** (maps physical dimensions to pixel coordinates):
   ```
   mcp__homi-michaelangelo__run_calibration(component_dir)
   ```

### Phase 1: Multi-Seed Exploration

3. **Start Phase 1** — explore many random seeds, each gets 2 turns (initial + refinement):
   ```
   mcp__homi-michaelangelo__start_phase1_exploration(
     component_dir,
     preset="balanced",    # or quick/thorough/maximum
     model="gemini/gemini-3-flash-preview"
   )
   ```

   **Preset guidance:**
   - `quick` (5 seeds, ~5 min) — fast prototyping, good for simple devices
   - `balanced` (13 seeds, ~10 min) — recommended default
   - `thorough` (25 seeds, ~20 min) — complex devices with fine features
   - `maximum` (41 seeds, ~40 min) — when quality is paramount

   Choose based on device complexity. A simple straight waveguide needs `quick`. A multi-mode interferometer needs `thorough` or `maximum`.

4. **Poll until complete**:
   ```
   mcp__homi-michaelangelo__poll_generation_status(task_id)
   ```

5. **Analyze Phase 1 results**:
   ```
   mcp__homi-michaelangelo__get_phase1_results(component_dir)
   ```

   **Reason about the results:**
   - What IoU range did the seeds achieve? (>0.85 is good, >0.90 is excellent)
   - Are the top seeds topologically correct? (right number of ports, correct connectivity)
   - Is there a pattern — do certain seed ranges work better?
   - Report: "Phase 1 complete. Best seed 1347 achieved IoU 0.91. Top 5 seeds range from 0.84-0.91. The geometry captures the ring coupling correctly but the bus waveguide taper needs refinement."

### Phase 2: Extended Iteration

6. **Start Phase 2** on the best seeds from Phase 1:
   ```
   mcp__homi-michaelangelo__start_phase2_iteration(
     component_dir,
     seeds=[top_seed_ids],
     additional_turns=3,
     model="gemini/gemini-3-flash-preview"
   )
   ```

7. **Poll and collect results**:
   ```
   mcp__homi-michaelangelo__get_phase2_results(component_dir)
   ```

8. **Report final metrics**:
   ```
   mcp__homi-michaelangelo__get_generation_metrics(component_dir)
   ```

---

## Stage 4: Parameter Optimization (Optional but Recommended)

If the user wants to fine-tune, use JEE optimizer:

1. **Extract tunable parameters** from the best script:
   ```
   mcp__homi-jee__extract_parameters(script_path)
   ```

2. **Prepare calibration** for the optimizer:
   ```
   mcp__homi-jee__prepare_calibration(target_image, footprint_json, output_path)
   ```

3. **Run optimization** — SSE minimization:
   ```
   mcp__homi-jee__run_optimization(
     script_path, target_image, calibration_file, output_dir, param_bounds,
     max_iterations=150, method="Nelder-Mead"
   )
   ```

4. **Apply optimized parameters**:
   ```
   mcp__homi-jee__apply_parameters(script_path, params, output_dir)
   ```

**Report**: "JEE optimization improved SSE by 47%. The coupling gap narrowed from 0.25 to 0.21 um, which better matches the paper's stated 0.2 um gap."

---

## Stage 5: Results and Next Steps

After generation (and optional optimization):

1. **Present the results** to the user:
   - Read the best GDS script and explain what it generates
   - Report IoU, Dice, and SSE metrics
   - Show the output file paths (best.gds, best.py)

2. **Offer next steps** based on what makes sense:

   **Interactive Workbench** — if the user wants to tune parameters: use the
   `explore` skill (the marimo workbench: the mask on a light table, live
   knobs, live IoU fidelity).

   **PDK Migration** — if the user wants to target a specific foundry:
   ```
   mcp__homi-pdk__analyze_paper_process(pdf_path=paper_path)
   mcp__homi-pdk__match_pdk(process_info)
   mcp__homi-pdk__convert_to_pdk(gds_path, pdk_name, output_path)
   mcp__homi-pdk__run_drc(gds_path, pdk_name)
   ```

   **Simulation** — if the user wants to verify optical performance:
   ```
   mcp__homi-flex__create_and_upload_simulation(gds_path, api_key, ...)
   ```

   **Optimization** — if the user wants better parameter fit:
   - Invoke the `optimize` skill or run JEE inline (Stage 4 above)

---

## Decision-Making Principles

1. **Always explain your reasoning.** Don't just call tools silently — tell the user what you're doing and why.
2. **Validate at each stage.** Check that the output makes physical sense before proceeding.
3. **Cross-reference the paper.** When you have the PDF, use information from the text to verify extracted dimensions, identify materials, and understand the device function.
4. **Suggest the right preset.** Simple devices (waveguides, bends) need `quick`. Complex devices (MMIs, ring arrays) need `thorough` or `maximum`.
5. **Know when to stop.** IoU > 0.90 is excellent. Don't optimize endlessly — tell the user when results are good enough.
6. **Handle failures gracefully.** If Phase 1 produces no seeds above IoU 0.5, the B&W image may need refinement. Go back and try a different variant or refine the existing one.
