# paper-tools — figure generators and provenance for the PixCell paper

The paper itself lives in [`../arxiv/`](../arxiv/), which is **literally the arXiv
submission tree**: what you upload is exactly

```bash
tar -C arxiv -czf pixcell-submission.tar.gz .
```

(`arxiv/` carries `main.bbl` — arXiv does not run BibTeX — plus `emergence.bib`
so local rebuilds work too; arXiv ignores the `.bib` when a `.bbl` is present.
`apsrev4-2.bst` is vendored from the REVTeX 4.2 distribution (APS) so the
bibliography renders identically locally and on arXiv.)

## Rebuild the paper

```bash
cd arxiv && tectonic main.tex        # or latexmk -pdf main.tex
```

Build artifacts (`main.pdf`, `*.aux`, `*.log`, `*.out`, `*.blg`, `mainNotes.bib`)
are gitignored; `main.bbl` is tracked deliberately (arXiv requires it).
The rendered PDF is committed at [`../assets/pixcell-paper.pdf`](../assets/pixcell-paper.pdf).

## Regenerate figures

`FIGURES.md` maps every figure to its generator. Two kinds:

- **Standalone** (run anywhere): the TikZ/TeX sources `fig_system_standalone.tex`,
  `fig_phases_standalone.tex`, `fig_channel_standalone.tex` (+ `fig_channel_assets/`),
  `fig1_emergence.tex`, and the Wolfram vocabulary-figure pair
  (`compose_fig_vocabulary.wls`, `build_fig_vocabulary_wolfram.py`).
- **Record-driven** (`make_fig*.py`, `make_figures.py`): these read the released
  measurement record (`data/`, `projects/gemini_images_run/`, `rl/reports/`).
  They become runnable here once the record lands in this repository; until then
  they are provenance — the exact code that produced the published figures.

Generator output paths were retargeted for this repository's layout
(`paper/figures` → `arxiv/figures`, `paper/tools` → `paper-tools`); everything
else is verbatim from the lab source at commit `9acdba42a`.

`agent_table.json` is the frozen output of `make_figures.py` (per-cell tokens /
wall-clock → USD + bootstrap CIs) that feeds the paper's cost table.
