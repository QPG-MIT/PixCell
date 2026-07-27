---
name: explore
description: Generate the device workbench — the marimo instrument over a verified parametric device (mask on a light table, live knobs, live IoU fidelity, provenance, handoffs).
argument-hint: "<project_dir or script_path> [--draw]"
allowed-tools: Read, Glob, Bash(ls *), Bash(homi *), Bash(pixcell *), Bash(.venv/bin/homi *), Bash(.venv/bin/pixcell *), Bash(marimo *), Bash(*pixcell-engine *)
---

# HOMI Explore: the Device Workbench

One designed surface; everything else is an integration. The workbench is a
self-contained marimo notebook generated per device: the mask on a backlit
light table (µm scale bar, die-boundary footprint frame, target ghost,
crosshair readout), knobs over the program's live DOF (function-defining
first), **live IoU against the target on every knob change** (the same
calibrated-raster math the conductor gate uses), the gate provenance, and
handoffs to the agent stages. Design spec (in the PixCell repo):
`docs/superpowers/specs/2026-07-06-device-workbench-design.md`.

## Generate

If the `homi` CLI is already on PATH (repo checkout or installed package), use it
directly; the engine resolver below is the fallback for plugin-only installs (it
finds or bootstraps the PixCell Python engine).
In a repo checkout without the venv activated, `.venv/bin/homi` works from
the repo root.

```
homi explore projects/<name>/output/best.py
# or, plugin-only install:
"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" homi explore projects/<name>/output/best.py
```

- `--draw` adds the Draw tab (local instrument only): sketch on the light
  table → `Dispatch recreation worker` → the sketch becomes a project and a
  Phase-A worker + conductor gate run through the normal control plane.
- `--launch` serves immediately; otherwise:

```
marimo run projects/<name>/output/workbench.py
# or, plugin-only install:
"${CLAUDE_PLUGIN_ROOT}/bin/pixcell-engine" marimo run projects/<name>/output/workbench.py
```

## What the workbench guarantees (anti-deception invariants)

- Every slider re-executes the device's own script (no UI-side geometry).
- The IoU readout is recomputed per rebuild; the die frame turns red when the
  bbox exceeds the footprint budget.
- Sliders carry the script's REAL defaults and analysis ranges; knobs the
  script never consumes are not shown.
- Cloud never auto-starts from the workbench — handoffs emit commands or
  dispatch agents whose spend gates are the usual ones.

## Embedding variant (no Draw tab)

To embed the same notebook in another surface that already has its own drawing
canvas, generate it without the Draw tab by calling
`homi.workbench.generate_workbench(script, artifact_dir, draw=False)` from the
engine's Python.
