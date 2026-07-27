# PHASE-B PAPER FIGURES OF MERIT

Repo: `/Users/aadarwal/src/QPG-MIT/homi-anu-powered`

Scope: `papers/1.pdf`, `papers/2.pdf`, `papers/3.pdf`, `papers/4.pdf`.

Extraction method: text was extracted page-by-page with `.venv/bin/python` using `pdfminer.six` installed outside the repo under `/tmp/homi_pdfdeps`. Page references below are PDF page numbers from the extracted text. I only use source-paper FoMs, not later benchmark simulation results.

Schema convention:

- `transmission_total` is mapped to a linear total-throughput fraction where the paper gives a total/excess/insertion loss that can be interpreted that way. For splitters, I keep the original per-port dB or per-port percentage alongside the mapped aggregate efficiency.
- `split_balance` is the reported or intended output power split. Where the paper only states symmetry or ideal 3-dB behavior, it is marked as target/nominal rather than measured imbalance.
- `bandwidth_nm` is only assigned when the paper gives a bandwidth with a criterion or explicit wavelength interval.
- `max_footprint_um` uses the largest stated physical propagation dimension for the relevant device. If the paper does not give a complete bounding box, I state the component lengths used to derive the value.

## Paper 1: `papers/1.pdf`

- Documented serial: 1
- Manifest project alias: `projects/paper_1`
- Title: `Low-Loss and Broadband Silicon Photonic 3-dB Power Splitter with Enhanced Coupling of Shallow-Etched Rib Waveguides`
- Source identifier: DOI `10.3390/app10134507`; DOI URL `http://dx.doi.org/10.3390/app10134507`; MDPI URL `https://www.mdpi.com/2076-3417/10/13/4507?type=check_update&version=3`
- Device type: 1x2 / 3-dB adiabatic rib-waveguide power splitter

### HOME Stack as Stated

- Platform/material: silicon photonics, SOI rib waveguides; silicon refractive index `n = 3.476` at 1550 nm, BOX `n = 1.444` at 1550 nm (PDF p. 2).
- Film/layer stack: 8-inch SOI wafer with 220-nm silicon device layer and 2-um buried oxide; 70-nm TEOS hard mask deposited and later removed (PDF p. 4).
- Etch depth: 60-nm shallow etch in the silicon device layer for rib waveguides; strip waveguides also fabricated with silicon full etch for comparison/test structures (PDF pp. 2, 4).
- Cladding: 2-um BOX is explicitly stated. The paper says top oxide cladding could be added without significant performance change, but does not state it as part of the measured splitter stack after the hard mask removal (PDF p. 5).
- Waveguide width/gap: coupling comparison uses 220-nm-thick, 500-nm-wide waveguides (PDF p. 2). The splitter tapers from tip width `w1 = 200 nm` to waveguide width `w2 = 700 nm`; designed gap is 300 nm (PDF p. 3). Fabricated SEM dimensions were nominally 740-nm waveguide width and 340-nm gap, within 50 nm of design (PDF p. 4).
- Lithography/fabrication: DUV lithography in an 8-inch wafer-scale silicon process (PDF p. 4).

### Reported Figures of Merit

- Measured excess loss: `0.06 dB` at `1550 nm`, computed by the paper as `3.06 dB - 3 dB` after linear regression across cascaded splitters (PDF p. 4).
- Measured single-splitter transmission to one output: `-3.06 dB` at `1550 nm`; ideal split component is 3 dB, so this is 0.06 dB excess loss beyond ideal 3-dB splitting (PDF p. 4).
- Simulated transmission convergence: taper length 40 um gives transmission converged to `-3.03 dB` (PDF p. 3).
- Splitting ratio / balance: symmetric 3-dB power splitting is confirmed in simulation, but no measured imbalance number is reported (PDF p. 3). Cascaded outputs are treated as `P/2`, `P/4`, `P/8`, etc. for measurement (PDF p. 4).
- Measured operating bandwidth: `100 nm`, from `1470 nm` to `1570 nm` (PDF pp. 1, 4, 6).
- Simulated operating bandwidth: `200 nm` wavelength sweep, criterion stated as broad operation in FDTD spectral response, not the measured passband (PDF p. 3).
- Center wavelength / measurement wavelength: `1550 nm` for the loss measurement (PDF p. 4).
- Device length/footprint: taper length `LTaper = 40 um`; table lists this as the device dimension for this work (PDF p. 6). No full x-y bounding box is stated in the paper.
- Fabrication tolerance: excess loss remains below `0.07 dB` when waveguide width and gap are controlled within `+/-50 nm`; fabricated 740/340 nm width/gap is expected below 0.07 dB and measured at 0.06 dB (PDF p. 5).
- Tip-width tolerance: excess loss below `0.05 dB` as long as the tip width is below `300 nm` (PDF p. 5).
- Critical dimensions: relaxed CDs `>= 200 nm`; tip width 200 nm and gap spacing 300 nm (PDF pp. 1, 2).

### Schema Mapping

- `transmission_total`: `0.986` aggregate splitter efficiency excluding the ideal 3-dB split, from `10^(-0.06/10)`. Per-output measured transmission is `0.494` from `10^(-3.06/10)`.
- `split_balance`: `0.5 / 0.5` target/nominal. The paper reports symmetric 3-dB operation but does not report measured imbalance.
- `bandwidth_nm`: `100` measured, criterion/interval `1470-1570 nm`; `200` simulated sweep is secondary.
- `max_footprint_um`: `40` for the stated taper/device length. Full bbox not stated.

## Paper 2: `papers/2.pdf`

- Documented serial: 2
- Manifest project alias: `projects/paper_2`
- Title: `A Photonic 1 x 4 Power Splitter Based on Multimode Interference in Silicon-Gallium-Nitride Slot Waveguide Structures`
- Source identifier: DOI `10.3390/ma9070516`
- Device type: 1x4 MMI power splitter in Si-GaN slot waveguides

### HOME Stack as Stated

- Platform/material: Si-GaN slot waveguide; figures label green as Si, blue as GaN, and white as SiO2 (PDF p. 2).
- Indices at 1550 nm: `nSi = 3.48`, `nGaN = 2.305`, `nclad = 1.444` for SiO2 (PDF p. 2).
- Film/layer stack: optimized slot dimensions are `HSi = 300 nm`, `HGaN = 100 nm`, and `WS = 400 nm` layer width (PDF p. 2).
- Cladding: SiO2, with `nclad = 1.444` (PDF p. 2).
- Etch depth: no conventional etched-ridge depth is stated for the design. The preliminary process uses e-beam lithography, deposition, and lift-off rather than reporting an etch depth (PDF p. 6).
- Waveguide and MMI geometry: input/output taper lengths `2 um / 5 um`; input/output taper widths vary `0.4-0.6 um / 0.6-0.4 um`; segment waveguide width `0.4 um`, segment length `5 um`; output gap `0.7 um` (PDF pp. 2, 3). MMI width `WMMI = 5 um`; optimized MMI length `LMMI = 12.3 um` (PDF p. 4).
- Preliminary fabrication: PMMA A4 e-beam resist, high-resolution e-beam exposure, deposition of `50 nm` GaN over Si-silica, lift-off, then a second aligned exposure and deposition of `50 nm` intrinsic Si followed by lift-off (PDF p. 6). This preliminary sequence is separate from the optimized simulated stack dimensions above.

### Reported Figures of Merit

- Insertion loss: `0.07 dB` for all four output ports, using the paper's formula `Loss[dB] = -10 log10(N Pout / Pin)` with `N = 4` (PDF p. 5).
- Transmission/transfer energy: paper states transfer energy is almost `100%` from the input taper into all four output ports (PDF p. 5).
- Splitting ratio: each port receives exactly `24.6%` of total power at `1550 nm` in simulation (PDF p. 5). This corresponds to aggregate output power `98.4%`.
- Uniformity/imbalance: all four ports are reported at the same `24.6%`; no separate imbalance or port-to-port variation value is given (PDF p. 5).
- Bandwidth: FWHM `81 nm`, from `1510 nm` to `1591 nm`, where FWHM is defined at normalized power `P = 0.5` (PDF p. 6).
- C-band coverage: the 81-nm FWHM covers `1530-1565 nm` C-band (PDF pp. 2, 6, 7).
- Center/operating wavelength: around `1550 nm`; simulations and port powers are reported at 1550 nm (PDF pp. 2, 4, 5).
- Device length/footprint: MMI body `12.3 um x 5 um`; the field is split into four beams at propagation distance `z = 15 um`; conclusion says splitting occurs after a propagation length of about `15 um` (PDF pp. 4, 5, 7). Including explicitly listed input taper, MMI, segment, and output taper lengths gives a physical-length lower bound of `2 + 12.3 + 5 + 5 = 24.3 um`, but the paper does not state one full bounding box.
- Dimensional tolerance: for normalized slot power between 90% and 100%, tolerances are around `5/6 nm` for `HSi` and `4/5 nm` for `HGaN` (PDF p. 4).
- MMI tolerance: `LMMI` tolerance around `0.3/0.4 um`; `WMMI` tolerance around `65/85 nm` (PDF p. 4).

### Schema Mapping

- `transmission_total`: `0.984`, from `10^(-0.07/10)` using the paper's `N Pout / Pin` insertion-loss definition. Per-output power is `0.246`.
- `split_balance`: `[0.246, 0.246, 0.246, 0.246]` reported at 1550 nm; ideal 1x4 target is `0.25` per port. Uniformity is described as equal but not separately quantified.
- `bandwidth_nm`: `81`, criterion FWHM at normalized power `P = 0.5`, interval `1510-1591 nm`.
- `max_footprint_um`: `24.3` as a conservative physical-length lower bound from stated subcomponent lengths; the paper also reports active split propagation length about `15 um` and MMI body `12.3 um x 5 um`.

## Paper 3: `papers/3.pdf`

- Documented serial: 5
- Manifest project alias: `projects/paper_5`
- Title: `Adiabatic Coupler With Design-Intended Splitting Ratio`
- Source identifier: DOI `10.1109/JLT.2019.2946948`
- Device type: adiabatic 2x2 coupler with design-intended splitting ratio

### HOME Stack as Stated

- Platform/material: silicon-on-insulator (SOI) adiabatic couplers (PDF p. 1).
- Film/layer stack: fabricated on a `200 mm` SOI wafer with `220 nm` nominal top silicon thickness (PDF p. 6).
- Lithography/fabrication: `193 nm` optical lithography; several `Delta wout` variants fabricated on the same wafer (PDF p. 6).
- Etch depth: not stated in the extracted paper text.
- BOX/cladding: not stated in the extracted paper text.
- Waveguide widths/gaps: base width `w = 350 nm` chosen for single-mode operation; close coupled gap `g2 = 150 nm`; far-separated gap `g1 = 3 um` (PDF p. 4). Input S-bend widths selected as `w1 = 400 nm`, `w2 = 300 nm`, `Ls1 = 20 um` (PDF p. 4). Region III output uses `w3 = 350 nm`, `w4 = w3 - Delta wout` (PDF p. 5). `Delta wout` is swept in design/simulation and fabricated variants (PDF pp. 3, 6, 7).
- Access/taper geometry: `Lt = 5 um`; output S-bend length `Ls2 = 10 um`; central adiabatic region length `L = 200 um` (PDF pp. 4, 5, 6).

### Reported Figures of Merit

- Splitting-ratio range: experimental broadband ADCs with power SRs from `7%/93%` to `50%/50%` are fabricated/tested (PDF pp. 1, 8).
- Center wavelength: `1310 nm`; SR-vs-width-difference relationship is evaluated at 1310 nm (PDF pp. 1, 6, 7).
- Bandwidth: `100 nm`, from `1260 nm` to `1360 nm`, for fundamental TE mode (PDF pp. 1, 7, 8).
- Example split: for `Delta wout = 10 nm`, SR at 1310 nm is around `79%/21%` (PDF p. 6).
- Wavelength flatness of that example: largest SR deviation from the 1310-nm SR is `1.0292%` over `1260-1310 nm` and `0.6785%` over `1310-1360 nm` (PDF p. 6).
- Split-ratio fit accuracy: deviations from the experimental data curve fit at center wavelength are within `6.1%`, `2.8%`, and `6.5%` for semi-analytical representation, simulations, and experiment, respectively (PDF pp. 7, 8).
- Thermal tolerance/stability: for the 3-dB ADC, maximum SR variation across the O-band is `1.6%` in simulation for stage temperature `0 C` to `100 C`, and `1.3%` in experiment for `20 C` to `50 C` (PDF p. 8). Abstract also reports SR variances within `1.3%` for `20 C` to `50 C` (PDF p. 1).
- Insertion loss design criterion: each optimized region is expected to have IL below `0.1 dB`; if so, IL is treated as negligible during design (PDF p. 4).
- Measured insertion-loss caveat: grating couplers have approximately `10 dB` loss at 1310 nm; grating-coupler repeatability uncertainty is about `1 dB`, which the authors say is about an order of magnitude larger than the ADC device IL. The paper says device IL cannot be accurately characterized with those grating couplers (PDF pp. 6, 7).
- Qualitative measured IL: over `1260-1320 nm`, measured device/test-structure ILs are about `1 dB`, mostly attributed to grating-coupler uncertainty; beyond 1320 nm the grating-coupler uncertainty increases and actual device IL is unclear (PDF p. 7).
- Device length/footprint: selected lengths are `Lt = 5 um`, `Ls1 = 20 um`, central `L = 200 um`, `Ls2 = 10 um`, and output `Lt = 5 um`, giving an approximate propagation length of `240 um` for Regions I-V. The paper does not state a complete x-y bounding box and explicitly notes the device has a large footprint (PDF pp. 4, 5, 7).

### Schema Mapping

- `transmission_total`: `null` as a clean device metric. The paper's measured `~1 dB` IL over `1260-1320 nm` would be `0.794` linear, but the authors say it is mostly grating-coupler uncertainty and not an accurate ADC device IL. Design-stage per-region criterion is `<0.1 dB`.
- `split_balance`: variable by design. Reported range is `0.07/0.93` through `0.5/0.5`; for the 3-dB ADC, target/nominal is `0.5/0.5`. Example `Delta wout = 10 nm` gives `0.79/0.21` at 1310 nm.
- `bandwidth_nm`: `100`, criterion/interval `1260-1360 nm` TE operation with SR measurements.
- `max_footprint_um`: `240` approximate stated propagation length from the selected region lengths. Full bbox not stated.

## Paper 4: `papers/4.pdf`

- Documented serial: 6
- Manifest project alias: `projects/paper_6`
- Title: `Fabrication-tolerant directional couplers on thin-film lithium niobate`
- Source identifier: DOI `10.1364/OL.480131`; DOI URL `https://doi.org/10.1364/OL.480131`
- Device type: fabrication-tolerant symmetric directional coupler and DC-based 3-dB coupler on TFLN

### HOME Stack as Stated

- Platform/material: thin-film lithium niobate (TFLN), two x-cut and y-propagation TFLN ridge waveguides (PDF p. 1).
- Film/layer stack: main fabricated-profile model uses lithium-niobate slab height `H = 250 nm`, ridge height `h = 110 nm`, and sidewall angle `theta = 60 deg` (PDF p. 1).
- Etch depth: ridge height/etch depth in the gap is assumed the same as other areas; physical sputtering etch of TFLN is referenced (PDF p. 1). Fabrication uses Ar-plasma dry etching (PDF p. 3).
- Cladding: final chip covered with silicon oxide cladding by plasma-enhanced chemical vapor deposition (PDF p. 3).
- Optimized long-DC geometry: tolerant design at approximately `W = 0.8 um`, `g = 0.9 um` for the `H = 250 nm`, `h = 110 nm` stack (PDF pp. 1, 2).
- Alternate TFLN cross-section: the same principle is demonstrated for `H = 200 nm`, `h = 200 nm`, optimized `W = 0.6 um`, `g = 0.8 um` (PDF p. 2).
- 3-dB coupler geometry: after 3D FDTD optimization, TFLN waveguide width adjusted to `1.1 um`; `Ls = 40 um`, `L = 17.5 um`; gap in the S-bends increases gradually from `0.9 um` to `2.9 um` (PDF p. 3).

### Reported Figures of Merit

- Long-DC fabrication tolerance: abstract states tolerance greater than `+/-100 nm` for an optimized structure (PDF p. 1). Simulations show `Lpi` can remain nearly constant for `Delta w = +/-100 nm` with `W ~= 0.8 um`, `g = 0.9 um` (PDF p. 2).
- Long-DC transmission tolerance: for `W = 0.8 um`, `g = 0.9 um`, transmission curves at `1550 nm` nearly coincide for `Delta w` up to `+/-100 nm`; comparison design `W = 1.5 um`, `g = 0.4 um` shows large differences (PDF p. 2).
- Long-DC wavelength response: simulated wavelength responses are shown over `1.5-1.6 um` for coupling lengths `L = 1400 um` with tolerant design and `L = 1600 um` without tolerant design (PDF p. 2).
- Long-DC center/coupling dips: tolerant design simulated coupling dips remain around `1.55 um` for `Delta w` up to `+/-100 nm`; measured dips shift to about `1.54 um`, attributed to initial TFLN thickness deviation (PDF p. 2).
- 3-dB coupler condition: optimized for low overall insertion loss and ideal 3-dB power splitting at `1550 nm` in simulation (PDF p. 3). The paper does not give an absolute insertion-loss value.
- 3-dB simulated tolerance: transmission deviation is only `0.18 dB` for an `80 nm` width variation (`Delta w = +/-40 nm`) (PDF p. 3).
- 3-dB comparison tolerance: non-tolerant comparison design `W = 1.5 um`, `g = 0.4 um`, `L = 2 um` has `0.86 dB` transmission variation with `Delta w = +/-40 nm` (PDF p. 3).
- 3-dB measured tolerance: measured transmission deviation about `0.5 dB` for `Delta w` up to `+/-40 nm` (PDF p. 3).
- 3-dB measured split wavelength: ideal 3-dB splitting wavelengths are close to `1.565 um`, again attributed to TFLN thickness deviation of the initial wafer (PDF p. 3).
- Bandwidth: for the long DC, the paper reports a `1.5-1.6 um` wavelength-response sweep, but not a pass/fail bandwidth criterion. For the 3-dB coupler, it says bandwidth could be improved by applying the principle to bent DCs, but does not give a 3-dB-coupler operating bandwidth value (PDF pp. 2, 3).
- Device length/footprint: 3-dB coupler has `Ls = 40 um` and central coupling length `L = 17.5 um`; with S-bends on both sides, the stated propagation length is approximately `2*40 + 17.5 = 97.5 um` (PDF p. 3). Long-DC wavelength-response test uses `L = 1400 um` for tolerant design (PDF p. 2).
- Insertion/excess loss: no absolute measured insertion loss or excess loss value is reported for the 3-dB coupler. The paper motivates DCs as low insertion loss and low reflection but reports tolerance/relative transmission deviations rather than absolute loss (PDF pp. 1, 3).

### Schema Mapping

- `transmission_total`: `null` as an absolute device transmission. The reported `0.18 dB` simulated and `0.5 dB` measured values are transmission variation over fabrication offsets, not absolute insertion/excess loss. If treated only as variation factors, they correspond to `0.959` and `0.891`, respectively, but those are not total device efficiencies.
- `split_balance`: `0.5/0.5` target/nominal for the 3-dB coupler. Simulation target is ideal 3-dB at `1550 nm`; measured ideal split occurs near `1565 nm`. No numeric imbalance is reported.
- `bandwidth_nm`: `null` for the 3-dB coupler because no criterion bandwidth is stated. The long-DC response is evaluated over a `100 nm` sweep from `1500-1600 nm`, but this is not reported as a passband.
- `max_footprint_um`: `97.5` for the stated 3-dB coupler propagation length. Long-DC test length is `1400 um` and should be used only if the benchmark target is the long directional-coupler structure rather than the compact 3-dB coupler.

## Cross-Paper Schema Summary

| PDF | Serial | Device | transmission_total | split_balance | bandwidth_nm | max_footprint_um |
| --- | ---: | --- | --- | --- | ---: | ---: |
| `papers/1.pdf` | 1 | 1x2 3-dB adiabatic rib splitter | `0.986` aggregate from 0.06 dB excess loss; per-output `0.494` from -3.06 dB | `0.5/0.5` nominal, no measured imbalance | `100` measured (`1470-1570 nm`) | `40` |
| `papers/2.pdf` | 2 | 1x4 Si-GaN slot MMI splitter | `0.984` aggregate from 0.07 dB insertion loss; per-port `0.246` | `[0.246,0.246,0.246,0.246]` reported | `81` FWHM (`1510-1591 nm`) | `24.3` conservative physical-length lower bound; active split about `15` |
| `papers/3.pdf` | 5 | SOI design-intended adiabatic coupler | `null` clean metric; measured `~1 dB` is grating-limited and not accurate device IL | variable `0.07/0.93` to `0.5/0.5`; 3-dB target `0.5/0.5`; example `0.79/0.21` | `100` (`1260-1360 nm`) | `240` approximate propagation length |
| `papers/4.pdf` | 6 | TFLN fabrication-tolerant directional/3-dB coupler | `null` absolute metric; only transmission variation reported | `0.5/0.5` target for 3-dB coupler | `null` for 3-dB criterion; long-DC sweep spans `100` nm | `97.5` for 3-dB coupler; long DC `1400` |

