---
name: extract
description: Extract photonic device images from research papers — PDF processing, image scoring, B&W conversion, and footprint extraction
argument-hint: <paper.pdf> [device hint e.g. "ring resonator in Figure 3"]
allowed-tools: Read, Glob, Bash(ls *), Bash(homi *), Bash(pixcell *), Bash(.venv/bin/homi *), Bash(.venv/bin/pixcell *), Bash(*pixcell-engine *), mcp__homi-mj__analyze_pdf_figures, mcp__homi-mj__render_pdf_pages, mcp__homi-mj__extract_images_from_pdf, mcp__homi-mj__crop_region, mcp__homi-mj__generate_bw_variants, mcp__homi-mj__refine_bw_image, mcp__homi-mj__get_image_metadata, mcp__homi-mj__create_footprint_json
---

# HOMI Extract: Paper to Device Image

You are running the extraction stage of the HOMI pipeline: research paper PDF (or a
single device image) → clean B&W device image + footprint (physical dimensions in µm).

**This is agent-first.** *You* are the perception. You `Read` the rendered pages and
decide which figure is the device and where to crop. The tools are dumb (render, crop);
the judgment is yours. The only model call in this stage is the B&W *image generation* —
an image transform you cannot do yourself.

## Input

`$ARGUMENTS` — path to a PDF (or image), optionally followed by a device hint.

## Procedure — the brief is the single source

The procedure lives in ONE place, the packaged brief that dispatched workers get too.
Print it and follow it step by step:

```
"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" python -c "from homi import briefs; print(briefs.brief_path('extract').read_text())"
```

If the `homi` CLI is already on PATH (repo checkout or installed package), use its
Python directly (`python -c "from homi import briefs; …"`) — the engine resolver is
the fallback for plugin-only installs; on first use it bootstraps the PixCell engine.

Tool-name mapping: the brief uses bare tool names (`analyze_pdf_figures`, `crop_region`,
…); as a skill-driven agent you call them as `mcp__homi-mj__<name>`. The deliverables
are exactly `device_bw.png` + `footprint.json` in the output directory (default:
`projects/<paper-stem>/`).

## Judgment rubrics (yours, not an API's)

**Which figure is the device** (rubric formerly inside a Gemini scoring prompt):
- Top-down waveguide layout, ports at image edges, dimension labels → **the target**
- Cross-section (layer stack) → useful for dimensions, not for GDS
- Mode profile / spectra / graphs / logos → skip
- SEM / microscope photo → sometimes usable; prefer a clean schematic
- Multi-panel figure → crop the panel that is the top-down device; use the user's hint
  to disambiguate multi-device papers

**B&W variant quality** (Read every variant; pick with your own eyes):
- Pure black device on pure white background (no gray)
- Clean waveguide edges, consistent width; all ports visible at image edges
- No text, labels, arrows, dimension annotations, noise

If none is clean enough: `mcp__homi-mj__refine_bw_image(source, out,
custom_instructions="Remove the dimension labels and arrows. Preserve the coupling-region gap.")`

## Output

Report: (1) which page/figure was the device and why; (2) the crop + chosen B&W variant
with your quality assessment; (3) the footprint dimensions and where you read them;
(4) the output directory, ready for the generation stage.
