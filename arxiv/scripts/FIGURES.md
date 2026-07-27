# Figure provenance — main.tex

Every `\includegraphics` in `main.tex`, its generator, and the data it
reads. Generators live in `arxiv/scripts/` and write to `arxiv/figures/`
(PDF used by the paper + PNG preview). Standalone TikZ sources compile with tectonic.
The canonical binaries are the PDFs in `figures/` — **never delete them**, even
where the generator or its data is local-only.

| Figure (figures/) | Generator | Data source |
|---|---|---|
| fig_primitives.pdf, fig_composition.pdf | `build_fig_vocabulary_wolfram.py` (`export_fig_vocabulary_geometry.py` + `compose_fig_vocabulary.wls`) | final canonical opening figures; exact gate-whitelisted GDSFactory 9.20.7 x-y geometry, composed and typeset as vector artwork in Wolfram with shallow illustrative relief; the PixCell publication/front-door palette and type system are carried through the PDF, editable SVG, and PNG preview outputs |
| fig_targets.pdf | `make_fig_targets.py` | `fig_target_assets/manifest.json` + F1–F8 one-bit render assets derived at the archived threshold; source and asset hashes are recorded in the manifest |
| fig_extraction.pdf | `make_fig_extraction.py` | `fig_extraction_assets/manifest.json` + audited F5 panel-(c) crop and F2 schematic; frozen masks are reused directly from `fig_target_assets/` |
| fig_verification.pdf | `make_fig_verification.py` | `fig_verification_assets/manifest.json`: hash-locked F4 GPT-5.5 iteration rasters, metrics, and calibration; target shared with `fig_target_assets/F4.png` |
| fig_phases.pdf, fig_system.pdf (stacked as Fig. 6(a,b)) | `fig_phases_standalone.tex`, `fig_system_standalone.tex` | standalone TikZ |
| fig_channel.pdf | `fig_channel_standalone.tex` + `fig_channel_assets/` | standalone TikZ (from user sketch) |
| fig_june_seeds.pdf | `make_fig_june_seeds.py` | `data/chatbots/figure_panels/panels/` (paper_statistics.json + seed/turn tiles) |
| fig1_emergence.pdf | `make_fig1_tikz.py` (+ `make_figures.py::fig1`) | `benchmark_results/real_success_data.json` (tracked exception) + `data/agents/paper_swap/sweep_results.json` |
| fig2_agent_zoom.pdf | `make_figures.py::fig2` | `figures/agent_table.json` |
| fig3_heatmap.pdf | `make_figures.py::fig3` | `figures/agent_table.json` |
| fig4_effort_generation.pdf | `make_figures.py::fig4` | `figures/agent_table.json` |
| fig_progression.pdf | `make_fig_progression.py` | archived per-cell iteration logs (reconstructed 2026-07-09) |
| fig_pareto.pdf | `make_fig_pareto3d.py` | `figures/agent_table.json` + archived token/cost records |
| fig5_before_after.pdf (now anchored by an explicit prose reference in III.B — it was an unreferenced float, which let it drift pages away) | `make_fig5_before_after.py` | `projects/gemini_images_run/FINAL_{1,7,8}` rasters (tracked) + `data/agents/paper_swap/` |
| fig_spectra.pdf, fig_cross_matrix.pdf | `make_fig_pdk_swap.py` | `data/agents/pdk_swap/output/` (baseline_eval, optimize logs, cross_matrix) |
| fig_sweep_feasibility.pdf — REMOVED from the paper 2026-07-09 (near-uniform null heatmap; the numbers live in the prose) | `data/agents/catalog_swap/cat5/output/sweep_pilot/postprocess.py` | that dir's sweep matrices |
| fig_rl_training.pdf | `make_fig_rl_training.py` | `rl/reports/runs_ledger/` (tracked trunk / bridge-1 / bridge-2 metrics) + first draw `rl/reports/benchmark_eval_bridge2.json` |
| fig_rl_gallery.pdf | `make_fig_rl_gallery.py` | fully re-scored archived draw `rl/reports/benchmark_attempts_bridge2.jsonl` (matches `benchmark_eval_bridge2_g.json` and Table IV) + `database/bw/benchmark/` |
| fig_sidewall_stacks.pdf | `make_fig_sidewall_stacks.py` (generator reconstructed 2026-07-09) | `data/agents/catalog_swap/cat5/output/sidewall_sweep/` (tracked JSON matrices + `field_*.npz`) |
| fig_trident_sidewall.pdf | `make_fig_trident_sidewall.py` (generator reconstructed 2026-07-09; curves-only single-column since the same day — the field-map grid was redundant with fig_sidewall_stacks) | `data/agents/paper_swap/final1/output/sidewall_sweep/` (`trident_matrix.json`) |

## Orphans — canonical binary only (no in-repo generator)

Produced during the conductor-run sweep campaigns by session-local plotting;
the *data* survives, the plotting scripts were not retained.

| Figure | Data that backs it |
|---|---|
| fig_coupler_field.pdf — REMOVED from the paper 2026-07-09 (field-map imagery redundant with fig_sidewall_stacks; the audit numbers live in the prose) | tier-1 field records, `data/agents/catalog_swap/cat5/output/` (`field_*.npz`, local-only/gitignored); in-figure sentence titles redacted → panel tags (a)/(b) 2026-07-09 |
| fig_source_vs_ours.pdf | published panel (source paper, archived extraction record) + tier-2 field export; baked-in mis-attributed panel title redacted → panel tags 2026-07-09 (caption carries the correct Nguyen et al. credit) |

The local-only `.hdf5`/`.npz` bulk is listed in `RELEASING.md` for inclusion in
the artifact release.

Retired figures (no longer included in `main.tex`) live in `figures/old/`.
