# PAPERS REPORT

Repo scanned: `/Users/aadarwal/src/QPG-MIT/homi-anu-powered`

## Summary

- Source research PDFs are present under `papers/` for the numbered paper corpus.
- No `projects/*/paper.pdf` files were found for the requested devices.
- The requested legacy project directories `projects/1x2_coupler`, `projects/directional_couplers`, `projects/1x4PowerSplitter`, and `projects/designintended_adiabaticoupler` are not present in this checkout.
- The only structured device/paper map found is `paper/dataset_manifest.json`, which maps documented serials to `papers/*.pdf` and `projects/paper_<serial>` aliases. It does not map the requested legacy project names directly.
- `experiments/benchmark_inventory.json` maps `FINAL_1` and some legacy project IDs to device categories, but not to a source PDF.
- `presentation/emergence_report/index.html` was not present. The closest provenance footer found was `presentation/pdk_swap_proof/index.html`, which cites commits/transcripts, not source papers.

## Evidence Files

- `papers/documented.md`: human-readable paper serial catalog.
- `paper/dataset_manifest.json`: active numbered PDF mapping.
- `experiments/benchmark_inventory.json`: benchmark device inventory and legacy project IDs.
- `experiments/paper_swap/final1/output/PILOT_SUMMARY.json`: `FINAL_1` paper-swap provenance and explicit note that `FINAL_1 has no source-paper text`.
- `paper/model_matrix.json`: references old `projects/1x2_coupler` benchmark folders.
- `notebooks/paper_companion.py`: notebook gallery tying some extracted images to paper labels.

## Per-Device Findings

### 1. `projects/gemini_images_run/FINAL_1` — trident 1x2 coupler

- Requested path: `projects/gemini_images_run/FINAL_1`
- Path present: yes
- Local target image: `projects/gemini_images_run/FINAL_1/device_bw.png`
- Local footprint: `projects/gemini_images_run/FINAL_1/footprint.json`
- Footprint: `[40.0, 1.7]` um
- Source PDF present: no authoritative source PDF mapping found
- `projects/*/paper.pdf`: none found
- Structured serial mapping: none found
- Title: no source-paper title mapped to this device
- Primary DOI/identifier: none found for the source paper
- Best provenance breadcrumb:
  - `experiments/benchmark_inventory.json` lists `FINAL_1` as category `1x2_coupler` with description `1x2 optical coupler from paper`.
  - `experiments/paper_swap/final1/output/PILOT_SUMMARY.json` describes the experiment as `FINAL_1 trident 1x2 splitter - paper-figure input`.
  - The same file says: `FINAL_1 has no source-paper text`.
  - `projects/gemini_images_run/FINAL_1/device_bw.png` is byte-identical to `notebooks/assets/devices/1x2_coupler_bw.png`, `paper/figures/examples/trident.png`, `paper/to be included/figures/target_1x2_coupler.png`, `presentation/images/targets_new/1x2_coupler.png`, and `website/static/images/targets/1x2_coupler.png`.

Conclusion: paper present no, device-to-paper mapping no. The repo only provides a paper-figure provenance claim and the target image/footprint.

### 2. `projects/1x2_coupler`

- Requested path: `projects/1x2_coupler`
- Path present: no
- Source PDF present: no authoritative source PDF mapping found for this legacy project ID
- `projects/*/paper.pdf`: none found
- Structured serial mapping: none found
- Title: no source-paper title mapped directly to `projects/1x2_coupler`
- Primary DOI/identifier: none found for this legacy project ID
- Best provenance breadcrumb:
  - `experiments/benchmark_inventory.json` lists ID `1x2_coupler`, path `projects/1x2_coupler`, category `1x2_coupler`, footprint `[40.0, 1.7]`, and description `1x2 optical coupler benchmark reference`.
  - `paper/model_matrix.json` says its model matrix source is `projects/1x2_coupler (benchmark_* folders)`.
  - `notebooks/paper_companion.py` loads `1x2_coupler_bw.png` and uses it as the preferred image for `Paper 5: Adiabatic Coupler`, but this is a notebook/gallery breadcrumb rather than a canonical manifest mapping.
  - If that notebook breadcrumb is intentional, the candidate source is documented serial 5 / `papers/3.pdf`, title `Adiabatic Coupler With Design-Intended Splitting Ratio`, DOI `10.1109/JLT.2019.2946948`. This candidate is not directly asserted by `paper/dataset_manifest.json` for `projects/1x2_coupler`.

Conclusion: paper present only as a possible/candidate breadcrumb, not as an authoritative mapping. Device-to-paper mapping no.

### 3. `projects/directional_couplers`

- Requested path: `projects/directional_couplers`
- Path present: no
- Source PDF present: yes
- Structured serial mapping: yes, via `paper/dataset_manifest.json`
- Documented serial: 6
- Dataset key: `doc_06`
- Manifest project alias: `projects/paper_6`
- Source PDF path: `papers/4.pdf`
- Manifest title: `Fabrication-tolerant directional couplers on thin-film lithium niobate`
- Component type: `symmetric directional coupler on TFLN`
- Classification: `1.4 Couplers: Co-directional (directional) couplers`
- Primary DOI/identifier found:
  - DOI: `10.1364/OL.480131`
  - DOI URL found in PDF bytes: `https://doi.org/10.1364/OL.480131`
- Other PDF metadata/identifiers found:
  - Title metadata: `Fabrication-tolerant directional couplers on thin-film lithium niobate`
  - Author metadata: `P. Huang, K. Chen, L. Liu`
  - License/web-statement DOI-like URL: `https://doi.org/10.1364/OA_License_v2`
  - Crossmark URL includes DOI `10.1364/OL.480131`

Conclusion: paper present yes, mapped through documented serial 6 / `projects/paper_6`, not through the absent legacy path.

### 4. `projects/1x4PowerSplitter`

- Requested path: `projects/1x4PowerSplitter`
- Path present: no
- Source PDF present: yes
- Structured serial mapping: yes, via `paper/dataset_manifest.json`
- Documented serial: 2
- Dataset key: `doc_02`
- Manifest project alias: `projects/paper_2`
- Source PDF path: `papers/2.pdf`
- Manifest title: `A Photonic 1 x 4 Power Splitter Based on Multimode Interference in Silicon-Gallium-Nitride Slot Waveguide Structures`
- Component type: `1 x 4 MMI power splitter in slot waveguides`
- Classification: `1.3 Splitters/combiners: MMI splitters/combiners (1 x N)`
- Primary DOI/identifier found:
  - No DOI found in the local repo scan/PDF byte scan.
- Other PDF metadata/identifiers found:
  - macOS metadata title: `A Photonic 1  4 Power Splitter Based on Multimode Interference in Silicon-Gallium-Nitride Slot Waveguide Structures`
  - PDF metadata author field found by raw string scan: `Dror Malka, Yossef Danan, Yehonatan Ramon and Zeev Zalevsky`
  - PDF metadata keywords found by raw string scan: `optical splitter; slot waveguide; multimode interference (MMI)`

Conclusion: paper present yes, mapped through documented serial 2 / `projects/paper_2`, not through the absent legacy path. DOI absent from local evidence found.

### 5. `projects/designintended_adiabaticoupler`

- Requested path: `projects/designintended_adiabaticoupler`
- Path present: no
- Source PDF present: yes
- Structured serial mapping: yes, via `paper/dataset_manifest.json`
- Documented serial: 5
- Dataset key: `doc_05`
- Manifest project alias: `projects/paper_5`
- Source PDF path: `papers/3.pdf`
- Manifest title: `Adiabatic Coupler With Design-Intended Splitting Ratio`
- Component type: `adiabatic 2 x 2 coupler with set splitting ratio`
- Classification: `1.4 Couplers: Adiabatic couplers`
- Primary DOI/identifier found:
  - DOI: `10.1109/JLT.2019.2946948`
- Other PDF metadata/identifiers found:
  - Title metadata: `Adiabatic Coupler With Design-Intended Splitting Ratio`
  - Subject metadata: `Journal of Lightwave Technology;2019;37;24;10.1109/JLT.2019.2946948`
  - Publisher metadata: `IEEE`
  - Journal metadata: `Journal of Lightwave Technology`
  - Volume/issue/pages metadata: volume `37`, issue `24`, pages `6147-6155`
  - Cover date metadata: `15 Dec.15, 2019`

Conclusion: paper present yes, mapped through documented serial 5 / `projects/paper_5`, not through the absent legacy path.

## Adjacent Numbered-Paper Evidence

The following adjacent source paper is relevant because it is a 1x2/3-dB splitter and may be confused with `FINAL_1` or the old `1x2_coupler` fixture, but the repo does not map it to those requested paths.

### Documented serial 1 / `projects/paper_1`

- Source PDF path: `papers/1.pdf`
- Manifest title: `Low-Loss and Broadband Silicon Photonic 3-dB Power Splitter with Enhanced Coupling of Shallow-Etched Rib Waveguides`
- Component type: `3-dB power splitter (adiabatically tapered rib waveguide coupler)`
- Classification: `1.4 Couplers: Adiabatic 3 dB couplers`
- Primary DOI/identifier found:
  - DOI: `10.3390/app10134507`
  - DOI URL found in PDF bytes: `http://dx.doi.org/10.3390/app10134507`
  - MDPI URL found in PDF bytes: `https://www.mdpi.com/2076-3417/10/13/4507?type=check_update&version=3`
- Note: `papers/1.pdf` also contains many reference-section DOI links. Those were not treated as source-paper identifiers for the requested device list.

## Device-To-Paper Mapping Assessment

- Canonical numbered-paper mapping exists: `paper/dataset_manifest.json` maps documented serials to `papers/*.pdf` and `projects/paper_<serial>`.
- Canonical mapping for the requested legacy paths does not exist in the checked-out files.
- `FINAL_1` is especially under-specified: the repo preserves the target image, footprint, benchmark runs, and paper-figure claims, but no source paper title/DOI/PDF path.
- The legacy project IDs in `experiments/benchmark_inventory.json` appear to be inventory stubs or historical references; their directories are absent.
