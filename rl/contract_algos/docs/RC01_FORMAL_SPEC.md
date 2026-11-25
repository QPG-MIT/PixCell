# RC-01: Formal Mathematical Specification & Learning Dynamics of Shape-Aware Visual Verification for PixCell

- **Specification Version**: `1.2.0` (frozen, zero learned weights, pure deterministic function; supersedes `1.1.0` with three documented calibration refinements below)
- **Contract Reference**: `research-contracts/rc-01-shape-aware-verification/SPEC.md` (UUID `d341ffff-1e38-4d6e-a4e9-eff3b8325a74`, marketplace `contract_71ec83b4b6e1`)
- **Reference Implementation**: `src/michaelangelo/core/rc01.py` (`RC01_VERSION = "1.2.0"`), wired into `rl/common/evaluator.py` (passing `gds_size_um` from `michaelangelo.core.compare_absolute.render_gds_absolute`) and exposed as first-class reward policy `"rc01"` (alongside `"validity_only"`) in `rl/track_a/reward.py`
- **Verification & Audit Surface**: `tests/test_rc01.py` (21 deterministic, adversarial, symmetry, anisotropy, overflow, and v1.2.0 calibration regression tests), `rl/track_a/tests/test_output_reward.py`, and [`RC01_DIVERGENCE_AUDIT.md`](RC01_DIVERGENCE_AUDIT.md) (869-rollout Round-1 Goodhart & calibration audit on v1.1.0)
- **Canonical Execution Boundary**: Immutable Docker image `sha256:daf9faaf9881cfee5af6e1fcbeb7974d8c7fd44bb0e65fdc0c00fe5e7e6c123d` (and opt-in Apptainer SIF boundary in `rl/common/isolation.py`). `michaelangelo.core.rc01` depends solely on stdlib, `numpy`, and `scipy`.

---

## 1. Domain Audit: PixCell Verification Architecture & Baselines

### 1.1 Calibrated Raster Geometry in PixCell (`depth-v1`, `split-seed17.json`, & `data/benchmark/final_1..final_8`)

In PixCell (`rl/common/evaluator.py`, `michaelangelo.core.compare_absolute`), candidate GDSFactory Python programs execute inside the immutable candidate sandbox (Python 3.12, `gdsfactory==9.20.7`, `gdstk==0.9.0`, `numpy==2.4.6`, `scipy==1.18.0`, `scikit-image==0.26.0`, `shapely==2.1.2`, `klayout==0.30.6`) to produce `device.gds`. Flattened layer `(1, 0)` polygons are rasterized via `render_gds_absolute` (4× supersampled box downsampling, left-aligned on $x$, centered on $y$, thresholded at grayscale `< 245`) onto the exact calibrated canvas of the target PNG (`VerifierReference.target_image_bytes`):

- **Model observation** (`image` in `depth-v1`): maximum-visibility aspect (long edge $1440\text{ px}$).
- **Verifier target raster** (`target_image` in `depth-v1`): isotropic `physical_aspect` (long edge $2496\text{ px}$, bbox span $\approx 2369\text{--}2401\text{ px}$, up to $6.23\times 10^6$ pixels).
- **Severe physical anisotropy in `data/benchmark/final_1..final_8`**: 7 of 8 benchmark targets exhibit anisotropic pixel scales `scale_px_per_um = [scale_x, scale_y]` up to **25.94× (`final_8`: `[34.54, 896.0]`)**, **11.68× (`final_3`: `[15.82, 184.75]`)**, **8.10× (`final_5`: `[200.05, 1620.0]`)**, and **7.60× (`final_1`: `[40.4, 307.06]`)**. Unweighted pixel distances distort physical errors by $>75\%$ and rotate pixel-space skeletons by $90^\circ$; RC-01 explicitly supports physical pixel spacing `(dy, dx) = (1/scale_y, 1/scale_x)` across EDT, KD-tree distances, rim strips, neck erosion, and boundary arc-length weights.
- **Scale & structural diversity across the 25 held-out validation tasks (`split-seed17.json`, 5/level L0–L4)**:
  - Calibrated pixel pitch spans $18.23\text{ px}/\mu\text{m}$ (`L3 0aa80f9f`, $130\times 47\,\mu\text{m}$) to $133.39\text{ px}/\mu\text{m}$ (`L0 0409041c`, $18\times 18\,\mu\text{m}$).
  - Intrinsic stroke widths span $28\text{ px}$ (`L4 0641192a`, directional coupler) to $534\text{ px}$ (`L0 0409041c`), with single-device width dynamic ranges up to $8.7\times$ (`L4 03a18410` `butterfly_mmi_coupler_2x2`).
  - Connected component counts range from $\beta_0 = 1$ to $\beta_0 = 12$ (`L2 05c462f6`), and bounded interior cavity counts range from $\beta_1 = 0$ to $\beta_1 = 25$ (`L4 048dc382`).
  - Bounding-box fill fraction (`iou_rect`) spans $0.121$ (`L4 037badff`) to $0.872$ (`L1 06b88ff9`).

### 1.2 Empirical Audit of Ground-Truth Residuals, Existing Baselines, & Frame Clipping

Running all 25 held-out validation GT controls plus the L4 training control-fault task (`01e3679661feed4b668f`, `slot_arm_mzi_1x1`, raw GT IoU $0.9675 < 0.97$) inside the canonical Docker sandbox revealed four foundational facts:

1. **Nyquist GT rasterization jitter floor**: Across all 25 validation tasks, re-rendering frozen GT code agrees with `target_image` to mean boundary distance $0.029\text{--}0.707\text{ px}$, 95th-percentile distance $\le \sqrt{2}\approx 1.414\text{ px}$ (1 diagonal pixel), and exact unfiltered topology on $25/25$ tasks. On small real cavities (`L4 037badff` $59\times 59\text{ px}$ slot hole $= 3{,}481\text{ px}$; `L4 048dc382` 25 grating holes $\approx 3{,}612\text{ px}$), 1-px inward rasterization bias reduces raw hole IoU to $57^2/59^2 = 0.9334$.
2. **Subpixel pinhole aliasing on `01e3679661feed4b668f`**: Raw 4-connected background labeling reports $6$ holes on `target_image` and $10$ holes on the GT re-render—of which $4$ and $8$, respectively, are **1-pixel aliasing pinholes**. Self-relative persistence filtering ($a_{\min}(M)$) snaps BOTH rasters to the exact vector ground truth $(\beta_0=1, \beta_1=2)$ with areas $[38{,}255;\; 1{,}166{,}048]$ vs $[35{,}981;\; 1{,}163{,}163]$.
3. **Two defects in `shaped_v3b` (`rl/track_a/reward.py`)**:
   - **GT positive-control failure**: On `L1 06b88ff94174bb341235` (`iou_rect = 0.872 < 0.95`), perfect GT (`IoU = 0.9973`) scores only **`shaped_v3b = 0.7510`** (failing the $\ge 0.97$ positive-control contract).
   - **Flat zero-gradient clamping plateau**: Every valid candidate below `iou_rect` and `t2b_rect` collapses to constant `0.0500`.
4. **Silent Canvas Overflow Clipping in `compare_absolute.py`**: `render_gds_absolute` left-aligns X at `bbox[0]` and vertically centers Y at `(bbox[1] + bbox[3]) / 2`, silently clipping any GDS polygon extending beyond the canvas frame (`image_size_px`). A pure raster-only metric cannot see clipped geometry outside the frame; RC-01 exposes an explicit overflow guard (`gds_size_um`, `footprint_um`, `canvas_size_um`) and `evaluate_rc01_calibrated(...)` helper, wired directly to `render_info["gds_size_um"]` in `rl/common/evaluator.py`.

---

## 2. Formal Characterization of Geometric & Topological Failure Modes

Let $\Omega = \{0, \dots, H-1\} \times \{0, \dots, W-1\} \subset \mathbb{Z}^2$ be the calibrated pixel lattice with physical pixel spacing $(d_y, d_x) = (1/\text{scale}_y, 1/\text{scale}_x)$ (default $(1, 1)$ when isotropic), and let $A, B \subseteq \Omega$ be candidate and reference binary foreground masks.

### Proposition 2.1 (Topological Blindness of IoU and Additive Boundary Chamfer)
1. **Waveguide break ($\Delta\beta_0 = +1$)**: Removing a $\delta$-px transverse cut from an $L \times w$ waveguide severs optical transmission ($\beta_0: 1 \to 2$), yet $1 - \operatorname{IoU} = \delta / L = O(\delta w / |B|) \to 0$ and $\operatorname{Chamfer}_\partial = O(\delta w / L) \to 0$. (*Historical v1.1.0 empirical*: 1-px cut on `L2 026447e3`: `IoU = 0.9997`, `v3b = 0.9962`, RC-01 = **`0.2758`**.)
2. **Directional-coupler bridge ($\Delta\beta_0 = -1$)**: Bridging a coupling gap $g$ with a $\delta$-px short yields $1 - \operatorname{IoU} = O(\delta g / |B|) \to 0$. (*Historical v1.1.0 empirical*: 1-px bridge on `L4 059a4672`: `IoU = 0.9999`, `v3b = 0.9999`, RC-01 = **`0.2492`**.)
3. **Cavity filling ($\Delta\beta_1 < 0$)**: Filling a resonant hole of area $a_h$ shifts IoU by only $a_h / (|B| + a_h)$. (*Historical v1.1.0 empirical*: filling the slot hole of `L4 037badff`: `IoU = 0.9949`, `v3b = 0.9960`, RC-01 = **`0.0299`**.)
4. **Euler-characteristic ($\chi = \beta_0 - \beta_1$) cancellation**: Simultaneously cutting a waveguide ($\beta_0 \mapsto \beta_0 + 1$) and punching an extra hole ($\beta_1 \mapsto \beta_1 + 1$) leaves $\Delta\chi = 0$. Any metric pooling $(\beta_0, \beta_1)$ into $\chi$ or normalizing $\Delta\beta_0$ by $\beta_0 + \beta_1$ is blind to cuts on multi-hole photonic-crystal nanobeams. RC-01 keeps $H_0$ and $H_1$ strictly separate and independently normalized by $\max(\tilde{\beta}_0(A), \tilde{\beta}_0(B), 1)$ vs $\max(\tilde{\beta}_1(A), \tilde{\beta}_1(B), 1)$.

### Proposition 2.2 (Thin-Feature Area Dominance, Whisker Exploits, & Parallel-Walled Contractible Bays)
1. **Port deletion**: Let $B = B_{\text{bulk}} \cup B_{\text{port}}$ with $|B_{\text{port}}| / |B_{\text{bulk}}| = \rho \ll 1$. Deleting all access ports preserves $(\beta_0, \beta_1)$ while $\operatorname{IoU} = (1+\rho)^{-1} = 1 - \rho + O(\rho^2)$ (`L4 048dc382`: `IoU = 0.9703`, v1.1.0 RC-01 = **`0.4439`**).
2. **Whisker + end-cap & white-box interior whisker exploits**: Deleting $95\%$ of an input waveguide while leaving an end-cap on the bbox rim and a thin connecting whisker fools both raw IoU (`0.964–0.983`) and naive rim-only checks (`s_rim = 1.0`). RC-01 v1.2.0 crushes outer port-arm whiskers via the catastrophic `r_fill < 0.25` trigger in `s_port_topo` (real `L4 048dc382` 1/3/5-px whiskers: **`0.3662 / 0.4386 / 0.4770`**, `s_topo = 0.240–0.355`) AND closes white-box thin interior whiskers on `>1024px` canvases via full-resolution narrow-band neck erosion (`t_neck < 0.50`).
3. **Parallel-walled contractible bays (`1x4 MMI` 5-port vs 3-port / 2-port / fused-slab)**: All four variants are contractible $(\beta_0=1, \beta_1=0)$ with high bulk IoU (`0.826–0.884`). Deleting middle output prongs or fusing all 4 prongs destroys both 4-side rim port-component valence ($k_R: 4 \to 2$ or $1$) and tight-bbox contractible void bays $\beta_0(\operatorname{BBox}(M) \setminus M)$.

### Proposition 2.3 (Zero-Overlap Cliff & Vanishing Reward Gradient)
For a thin waveguide of width $w$ translated by $\Delta > w$, $\operatorname{IoU}(T_\Delta(B), B) = 0$ and $\partial_\Delta \operatorname{IoU} = 0$. Under `shaped_v3b`, the flat plateau expands to every candidate below `iou_rect` (`0.0500`), and global-diagonal $\tau = 0.05 D$ smears sub-micron features by $15\times$.

### Proposition 2.4 (Area-Filling Shortcuts, Deletion-Bonus Paradox, Hollow-Slit-Frame, & Existence-Side Persistence)
1. **Bounding-box & Convex-hull fill**: Average `IoU = 0.3559` / `0.4622` across 25 val tasks (`v3b` up to `0.6099`).
2. **Deletion-bonus paradox (`fdel3dyc` thin ring vs solid disk)**: At matched $\operatorname{IoU} \approx 0.52\text{--}0.55$, raw IoU, Dice, symmetric boundary Chamfer, NSD, `shaped_v3b`, and naive $1/\tau_{\text{pred}}$-weighted FP metrics accidentally prefer a solid disk over a slightly shifted thin ring. Dual-target-thickness FP weighting + $S_{\text{width}}$ + $S_{\text{topo}}$ make shifted thin rings score $>10\times$ higher than solid disks.
3. **Hollow-slit-frame attack**: A 1-px or 3-px wireframe of a `1x4 MMI` with a 1-px slit is contractible `(1, 0)` and achieves near-perfect boundary alignment (`S_bnd = 0.95–1.00`), defeating pure boundary metrics. Interior thickness spectrum $S_{\text{width}}$ + SDF recall + $\operatorname{IoU}_{1:1}$ crush it below `0.12`.
4. **Why raw SEDT total persistence $(d - b)$ fails vs area/existence-side persistence**: In signed-distance sublevel filtrations, punching a tiny $2\times 2$ pinhole inside a solid disk creates an $H_1$ pair with death $d \approx 1\text{ px}$ (existence side) and huge negative birth $b = -R_{\text{disk}}$ (interior wall thickness), giving deceptive total persistence $d - b \approx R_{\text{disk}}$. Symmetrically, adding a tiny detached $2\times 2$ speck next to a merged coupler creates an $H_0$ pair with tiny existence radius $|b| \approx 1\text{ px}$ and huge death $d$. RC-01 filters sub-threshold specks/pinholes directly on their **existence-side area support** $a_{\min}(M)$, while $S_{\text{mass},0}$, $S_{\text{bij},0}$, $R_{\text{vol}}$, and overlap-gated $S_{\text{cav}}$ crush larger spoofs.

---

## 3. Formal Mathematical Derivation of RC-01 (`v1.2.0`)

Let $A, B \in \{0, 1\}^{H \times W}$ be calibrated binary masks normalized symmetrically via `mask_mode ∈ {"auto", "bool", "grayscale"}` (in `"auto"` mode, if either input is a PIL Image or numeric array with $\max > 1$, both numeric arrays decode via `< white_threshold`, guaranteeing all-black `uint8(0)` vs all-white `uint8(255)` returns `0.0`). Let physical pixel spacing be $(d_y, d_x) = (1/\text{scale}_y, 1/\text{scale}_x)$ (default $(1, 1)$), $h_{\min} = \min(d_y, d_x)$, and physical Nyquist tolerance:
$$\varepsilon_{\text{nyq}} = \frac{1.5}{\sqrt{2}}\sqrt{d_y^2 + d_x^2} \quad (= 1.5\text{ px when } d_y = d_x = 1).$$
- **Boundary cases**: $A = B = \emptyset \implies \operatorname{RC01} = \phi_{\text{ov}}$; exactly one empty $\implies 0$; $A = B \neq \emptyset \implies \phi_{\text{ov}}$ (where $\phi_{\text{ov}} \in (0, 1]$ is the optional canvas-overflow factor, identically $1.0$ on pure raster calls).
- **Lossless union crop**: For $A, B \neq \emptyset, A \neq B$, crop to the tight union bbox padded by a 1-px `False` border with physical diagonal $D_\cup = \sqrt{(H_\cup d_y)^2 + (W_\cup d_x)^2}$.

### Pillar 1 & Pillar 3: Exact Uncapped Filtered 2D Homology, Overlap-Gated Tempered Cavities, Full-Res Neck & Port-Bay Topology ($S_{\text{topo}}$)

At **full native pixel resolution** with dual connectivity **(8-connected foreground, 4-connected background)**:

1. **Self-relative persistence filter**: $a_{\min}(M) = \min(\max(9, \lfloor 10^{-4}|M|\rfloor), \max(1, \lfloor 10^{-2}|M|\rfloor))$. Retain ALL filtered foreground components $\{C_i^M\}_{i=1}^{\tilde{\beta}_0(M)}$ and ALL bounded holes $\{H_k^M\}_{k=1}^{\tilde{\beta}_1(M)}$ **without truncation** for exact $\tilde{\beta}_0, \tilde{\beta}_1, T_0, T_1, S_{\text{mass},0}, S_{\text{mass},1}, R_{\text{vol}}$; cap only the $O(K^3)$ Hungarian matching matrices at top $K = 256$ by descending area. Let $A_{\text{clean}}, B_{\text{clean}}$ denote the persistence-filtered foreground masks.
2. **1-to-1 Component-Matched IoU & Bijection Purity**:
   $$\operatorname{IoU}_{1:1}(A, B) = \frac{M_{\text{fg}}}{|A \cup B|}, \qquad P_{\text{fg}} = \frac{M_{\text{fg}}}{|A \cap B|}, \qquad \omega = \min(1,\; 5\,\operatorname{IoU}_{\text{raw}}), \qquad S_{\text{bij},0} = 1 - \omega(1 - P_{\text{fg}}).$$
3. **Separate Betti Factors ($T_0, T_1$) & Uncapped Mass Similarity ($S_{\text{mass},0}$)**:
   $$T_k = \mathbb{1}[\tilde{\beta}_k(A)=\tilde{\beta}_k(B)] + \mathbb{1}[\tilde{\beta}_k(A)\neq\tilde{\beta}_k(B)]\exp\!\left(-\big(0.15 + 1.20\tfrac{|\tilde{\beta}_k(A)-\tilde{\beta}_k(B)|}{\max(\tilde{\beta}_k(A),\tilde{\beta}_k(B),1)}\big)\right),$$
   $$S_{\text{mass},0} = 1 - \tfrac{1}{2}\|\tilde{m}(A) - \tilde{m}(B)\|_1.$$
4. **Overlap-Gated Nyquist-Tolerant Cavity Fidelity ($S_{\text{cav}}$, v1.2.0 Refinement (c))**:
   If $\tilde{\beta}_1(A) = \tilde{\beta}_1(B) = 0$, $S_{\text{cav}} = 1$. Otherwise let $S_{\text{hole}} \in [0, 1]$ be the symmetric 1-to-1 matched 1-px Nyquist-dilated hole F1 (normalized over total uncapped hole areas) and let:
   $$S_{\text{cav}}^{\text{raw}}(A, B) = (1 - \omega)\, R_{\text{vol}}\, S_{\text{mass},1} \;+\; \omega\, S_{\text{hole}},$$
   $$S_{\text{cav}}(A, B) = \begin{cases} \big(S_{\text{cav}}^{\text{raw}}(A, B)\big)^{0.65} & \text{if } \tilde{\beta}_1(A) = \tilde{\beta}_1(B) \ge 1 \text{ and } S_{\text{cav}}^{\text{raw}} > 0, \\ S_{\text{cav}}^{\text{raw}}(A, B) & \text{otherwise.} \end{cases}$$
   Exact-count cavities with scale mismatch (e.g., `12.8×` oversized crevices with overlapping support) still degrade strongly ($0.15^{0.65} = 0.291 \ll 0.80$) without collapsing identically to missing cavities, while shifted non-overlapping fake holes (`V7`, $S_{\text{hole}} = 0$) still give $0^{0.65} = 0 \implies \operatorname{RC01} \le 0.030$, and translated hollow rings at $\omega = 0$ keep $S_{\text{cav}} = 1.0$.
5. **Full-Res Narrow-Band Structural Neck Connectivity ($T_{\text{neck}}$, v1.2.0 Refinement (b))**:
   Let $r_{\text{neck}} = \min(0.12 w^*, 2.0 \max(d_y, d_x))$ and $h_{\text{sdf}} = \min(s_y d_y, s_x d_x)$.
   - Whenever $\max(r_{\text{neck}}/d_y, r_{\text{neck}}/d_x) \le 2.5$ **or** ($r_{\text{neck}} < 0.75\, h_{\text{sdf}}$ and $\max(r_{\text{neck}}/d_y, r_{\text{neck}}/d_x) \le 8.0$)—covering **all** isotropic canvases of arbitrary size ($1440\text{ px}$, $2496\text{ px}$) AND eliminating the mild-to-moderate anisotropy dead zone (`1.25:1–1.87:1` on `2496px` canvases)—run exact **full-resolution** narrow-band Euclidean disk erosion directly on $A_{\text{clean}}, B_{\text{clean}}$ (dispatching exact lattice matches for $d^2 \le 1, 2, 4$ to fast vectorized slicing even under small integer-bbox calibration rounding $d_x \ne d_y$), then compare persistence-filtered 8-connected component counts via $T_{\text{neck}} = T(\beta_{0,\text{neck}}(A), \beta_{0,\text{neck}}(B))$.
   - Under severe physical anisotropy ($\max(r_{\text{neck}}/d_y, r_{\text{neck}}/d_x) > 2.5$ with $r_{\text{neck}} \ge 0.75\, h_{\text{sdf}}$), run neck erosion on the physical-sampling SDF working grid.
6. **Intrinsic 4-Side Port-Zone & Contractible-Bay Topology ($S_{\text{port-topo}}$, v1.2.0 Refinement (a))**:
   - On each mask's persistence-cleaned tight bounding box (`sub`), extract the 4 outer $10\%$ port zones ($Z_{\text{L}}, Z_{\text{R}}, Z_{\text{T}}, Z_{\text{B}}$): compute per-side 1D rim port-component count $k_s$ (after closing $\le 2$-px aliasing notches), port-width mass similarity $m_{p,s}$, and 1-px Nyquist-tolerated symmetric zone fill ratio:
     $$\delta_{\text{fill},s} = \min\!\left(\frac{|\partial Z_s(A)|}{|Z_s(A)|},\; \frac{|\partial Z_s(B)|}{|Z_s(B)|}\right), \qquad r_{\text{fill},s} = \frac{\min(\max(f_A, f_B),\; \min(f_A, f_B) + \delta_{\text{fill},s})}{\max(f_A, f_B)}.$$
   - Keep continuous $r_{\text{fill},s}$ unconditionally inside Pillar 5 ($S_{\text{rim}}$) via $p_{\text{rim},s} = T(k_s(A), k_s(B)) \cdot m_{p,s}^{1/2} \cdot r_{\text{fill},s}$.
   - Decouple moderate geometric $r_{\text{fill},s}$ from discrete topological $S_{\text{port-topo}}$ when side port counts match ($k_s(A) = k_s(B)$), triggering $S_{\text{topo}}$ only for catastrophic $>4\times$ arm/whisker collapse ($r_{\text{fill},s} < 0.25$) or discrete port-count / bay mismatches:
     $$p_{\text{topo},s} = \begin{cases} m_{p,s}^{1/2} \cdot \big(1 \text{ if } r_{\text{fill},s} \ge 0.25 \text{ else } r_{\text{fill},s}\big) & \text{if } k_s(A) = k_s(B), \\ T(k_s(A), k_s(B)) \cdot m_{p,s}^{1/2} \cdot r_{\text{fill},s} & \text{if } k_s(A) \neq k_s(B). \end{cases}$$
   - Compute 2D tight-bbox contractible bay count $b_{\text{bay}}(M)$ as filtered 4-connected components of $\operatorname{open}_4(\neg \text{sub}_s)$ on the SDF grid, giving $T_{\text{bay}} = T(b_{\text{bay}}(A), b_{\text{bay}}(B))$ and:
     $$S_{\text{port-topo}} = \left(\prod_{s \in \{\text{L,R,T,B}\}} p_{\text{topo},s}\right)^{1/2} \cdot T_{\text{bay}}^{1/2}.$$
   - All port-zone and bay signatures remain **strictly translation-invariant, symmetry-preserving, and anisotropy-invariant**.
7. **Combined Topological Fidelity Factor**:
   $$S_{\text{topo}}(A, B) = T_0 \cdot S_{\text{mass},0} \cdot S_{\text{bij},0} \cdot T_1 \cdot S_{\text{cav}} \cdot T_{\text{neck}} \cdot S_{\text{port-topo}} \in [0, 1].$$

### Pillar 4: Anisotropic Physical Continuous SDF ($S_{\text{sdf}}$) with Dual-Target-Thickness FP Weighting & Tight Thickness Spectrum ($S_{\text{width}}$)

With independent per-axis strides $s_y = \max(1, \lceil H_\cup / 512 \rceil)$, $s_x = \max(1, \lceil W_\cup / 512 \rceil)$ on $A_{\text{clean}}, B_{\text{clean}}$, we compute exact physical EDT via `distance_transform_edt(..., sampling=(s_y d_y, s_x d_x))` with 1-cell `False` border padding, preserving isolated sub-stride thin filaments (`(density > 0) & ~dilate(ds_core)`):
- Characteristic functional width $w(M) = \max(h_{\min}, 4\, q_{0.35}(R_{\text{in}}))$, $w^* = \min(w(A), w(B))$.
- Tightened tolerances ($s_{\text{eff}} = \sqrt{(s_y d_y)^2 + (s_x d_x)^2}/\sqrt{2}$):
  $$\varepsilon_{\text{sdf}} = \max(\varepsilon_{\text{nyq}},\; 0.75\, s_{\text{eff}}), \qquad \varepsilon_w = \max(2\varepsilon_{\text{nyq}},\; 1.0\, s_{\text{eff}}).$$
- **Dual-Target-Thickness FP Weighting**: For directed alignment $X \to Y$, let $w_{\text{lo}} = \max(\sigma_{\min}, 0.25 w^*)$ and $w_{\text{hi}} = \max(w_{\text{lo}}, 0.75 w^*)$. At each $x \in X_s$:
  $$r_{\text{eff}}(x) = \begin{cases} \min(R_X(x), R_Y(x)) & R_Y(x) > 0 \text{ (TP)}, \\ \min(|\phi_Y(x)|, 0.5 w^*) & R_Y(x) = 0 \text{ (FP)}, \end{cases} \qquad \psi_{X \to Y}(x) = \frac{1}{\operatorname{clip}(r_{\text{eff}}(x), w_{\text{lo}}, w_{\text{hi}})}.$$
- **Thickness spectrum $S_{\text{width}}$**: Geometric mean of Nyquist-tolerated ($\varepsilon_w$) quantile ratios across $2\, q_{\{25, 50, 75, 90\}}(R_{\text{in}})$.

### Pillar 2: Physical Arc-Length-Weighted Full-Resolution Boundary F1 ($S_{\text{bnd}}$) & Far-Field Proximity ($S_{\text{far}}$)

On full-resolution 1-px inner boundary pixels $(y_i, x_i) \in \partial M$, physical coordinates are $(y_i d_y, x_i d_x)$ and exact physical arc-length weight is $w_{\text{arc}, i} = \sqrt{(n_{\text{tb}, i}\, d_x)^2 + (n_{\text{lr}, i}\, d_y)^2}$. Using `cKDTree` (DoS-capped at $32{,}000$ points) with $\tau_{\text{loc}} = \max(2.5 h_{\min}, 0.50 w^*)$, $\tau_{\text{far}} = \max(8 h_{\min}, 0.12 D_\cup)$, and $d_\varepsilon = \max(0, d - \varepsilon_{\text{nyq}})$, compute arc-length-weighted harmonic means $S_{\text{bnd}}$ and $S_{\text{far}}$.

### Pillar 5: Persistence-Cleaned Four-Side Rim Exposure ($S_{\text{rim}}$)

Running strictly on the persistence-filtered masks $A_{\text{clean}}, B_{\text{clean}}$ with anisotropy-matched physical rim strips, each side $s \in \{\text{L}, \text{R}, \text{T}, \text{B}\}$ combines spatial rim F1 $d_s$ and full continuous port-zone score $p_{\text{rim},s}^{1/2}$, aggregated as $S_{\text{rim}} = (\prod_s d_s\, p_{\text{rim},s}^{1/2})^{1/4}$.

### Coupled Dual-Regime Aggregation, Overflow Guard, & RL Reward Policy (`rl/track_a/reward.py`)

$$S_{\text{geom}} = \operatorname{IoU}_{1:1}^{0.30}\; S_{\text{bnd}}^{0.25}\; S_{\text{sdf}}^{0.30}\; S_{\text{rim}}^{0.15}, \qquad G_{\text{topo}} = S_{\text{topo}}^{0.75},$$
$$S_{\text{core}} = \phi_{\text{ov}} \cdot G_{\text{topo}} \cdot S_{\text{width}} \cdot S_{\text{geom}},$$
$$S_{\text{shape-far}} = \phi_{\text{ov}} \cdot \big(0.20 + 0.80\, G_{\text{topo}}^{1/2}\big)\cdot S_{\text{width}}^{1/2} \cdot \left(0.5\, S_{\text{far}} + 0.5\,(S_{\text{bnd}}\, S_{\text{sdf}}\, S_{\text{rim}})^{1/3}\right),$$
$$\boxed{\operatorname{RC01}(A, B) = (1 - \eta)\, S_{\text{core}}(A, B) \;+\; \eta\, S_{\text{shape-far}}(A, B), \qquad \eta = 0.15,}$$
where $\phi_{\text{ov}} = \min\!\big(1, \frac{W_{\text{avail}}}{W_{\text{gds}}}\big)\cdot \min\!\big(1, \frac{H_{\text{avail}}}{H_{\text{gds}}}\big)$ when `gds_size_um` exceeds available canvas dimensions beyond $1\%$ tolerance (and $\phi_{\text{ov}} \equiv 1$ on pure raster comparisons).

In `rl/track_a/reward.py`, the first-class `"rc01"` reward policy maps an `EvaluationResult` (populated by `PixCellEvaluator` with `gds_size_um` from `compare_absolute.render_gds_absolute`) to:
$$r_{\text{rc01}} = \begin{cases} 0.05\,\phi_{\text{ov}} + 0.95\,\operatorname{RC01} & \text{if } \text{status} = \text{OK} \text{ and candidate raster is non-empty}, \\ 0.0 & \text{if } (\text{status} = \text{OK and empty raster}) \text{ or MODEL failure}, \\ \text{None} & \text{if EVALUATOR or REFERENCE fault (masked / abort)}. \end{cases}$$
The companion `"validity_only"` control policy maps `OK -> 1.0`, MODEL failures `-> 0.0`, and EVALUATOR / REFERENCE faults `-> None`.

---

## 4. Formal Metric Properties & Theorems

### Theorem 4.1 (Boundedness, Exact Identity, Symmetry & Determinism — Gate T1)
For all $A, B \in \{0, 1\}^{H \times W}$ with $\phi_{\text{ov}} = 1$: $\operatorname{RC01}(A, B) \in [0, 1]$, $\operatorname{RC01}(A, B) = 1 \iff A = B$, and $\operatorname{RC01}(A, B) = \operatorname{RC01}(B, A)$ bit-identically across runs.

### Theorem 4.2 (1-Lipschitz GT Rasterization Stability)
Under subpixel Nyquist jitter ($d_H(\partial A, \partial B) \le \sqrt{2}\text{ px}$) preserving filtered homology, port counts, full-res neck connectivity, and opened bbox bays, $|\phi_A - \phi_B| \le \varepsilon_{\text{nyq}}$ and $\operatorname{RC01}(A, B) \ge 0.85\,\operatorname{IoU}^{0.30} + 0.15 \ge 0.992 \gg 0.97$. *Empirical v1.2.0 check*: **26/26** real PixCell GT controls (all 25 val tasks + L4 train fault `01e36796` where raw IoU failed at `0.9675`) achieve **`0.9882–0.9998`** (mean **`0.9971`**, min `s_topo = 0.9961`).

### Theorem 4.3 (Anti-Goodhart Upper Bounds on Topological Defects)
1. **Balanced (50/50) waveguide break or coupler bridge ($\Delta\beta_0 = \pm 1$)**: $\delta_0 = 0.5$, $T_0 = e^{-0.75} = 0.472$, $S_{\text{mass},0} \le 0.55$, $S_{\text{bij},0} \approx 0.50 \implies S_{\text{topo}} \le 0.130$, $\operatorname{IoU}_{1:1} \le 0.50$, yielding $\operatorname{RC01} \le \mathbf{0.235}$ even at $\operatorname{IoU} = 0.9999$.
2. **Filled cavity or shifted non-overlapping fake hole (`V7`, $\operatorname{IoU} \ge 0.20$)**: $S_{\text{cav}} = 0 \implies S_{\text{core}} = 0 \implies \operatorname{RC01} \le 0.20\,\eta = \mathbf{0.030}$ regardless of raw IoU.
3. **White-box thin interior whisker on `>1024px` canvases**: Full-res narrow-band neck erosion snaps 1–4 px interior whiskers bridging severed bodies, driving $T_{\text{neck}} \le 0.472 \implies S_{\text{topo}} \le 0.472 \ll 0.80$.
4. **Parallel-walled contractible-bay destruction (`1x4 MMI`) & catastrophic `>4×` port collapse**: Discrete count/bay mismatches ($k_R: 4 \to 2/1$, bays $7 \to 5/4/0$) and catastrophic port-zone collapse ($r_{\text{fill}} < 0.25$) still drive $S_{\text{topo}} < 0.50$, while single-piece L0 tapers with matching port counts and moderate end-width ratios ($r_{\text{fill}} \ge 0.25$) pass $S_{\text{topo}} \ge 0.80$ with continuous credit inside $S_{\text{rim}}$.

### Theorem 4.4 (First-Order Stochastic Dominance Suppression of Area-Filling Shortcuts)
If $A \supseteq B$ fills concavities of width $c \gg w(B)$, $R_{\text{in}}(A)$ stochastically dominates $R_{\text{in}}(B)$, driving $S_{\text{width}} \ll 1$, dual-weighted $S_{\text{sdf}} \ll 1$, and $S_{\text{port-topo}} \ll 1$ while leaving rigid motions unpenalized ($S_{\text{width}}(T_\Delta(B), B) = 1$).

### Theorem 4.5 (Non-Vanishing Dense Shaping Gradient at Zero Overlap & Zero-Hole Regimes)
For any rigid translation $\Delta > w$ ($\operatorname{IoU} = 0, S_{\text{core}} = 0$), $\operatorname{RC01}(T_\Delta(B), B) \ge \frac{\eta}{2}(0.20 + 0.80 G_{\text{topo}}^{1/2}) S_{\text{far}}(\Delta) > 0$ with $\partial_\Delta \operatorname{RC01} < 0\;\forall\Delta > \varepsilon_{\text{nyq}}$, and even hole-less candidates retain monotone spatial gradient in $(0, 0.030]$.

---

## 5. Formal Analysis of Learning & Training Dynamics

### 5.1 Selection / Rejection-Sampled Fine-Tuning (RFT / STaR)

In iterative Thinking-RFT (STaR), selecting winners by raw IoU harvests high-IoU structural-bug traces $\mathcal{C}_{\text{bug}}$ into supervised distillation. **Recommended RFT / STaR Trace Gate**: Select rollouts with `bd.score >= 0.65` (L0–L2) / `>= 0.55` (L3–L4) **and** `bd.s_topo >= 0.80`, ranking `best_of_k` by `bd.score`.

### 5.2 Online GRPO / PPO RL Dynamics

In grouped policy-gradient training, groups with zero reward variance ($\sigma \le 10^{-12}$) are skipped. Under Raw IoU, $P_{\text{dead}}(\text{IoU}) = (1 - p_{\text{exec}} p_{\text{hit}})^G$. By **Theorem 4.5**, RC-01 gives every non-empty executable layout a distinct strictly positive gradient, collapsing dead groups toward $P_{\text{dead}}(\text{RC-01}) \approx (1 - p_{\text{exec}})^G$, while Theorems 4.3–4.4 prevent GRPO Goodhart reward hacking.

### 5.3 Label-Free Curriculum Dynamics Across L0–L4

RC-01 uses zero level labels yet cleanly separates every failure mode from L0 primitives through L1 arrays (`IoU_1to1`) and stepped bars (padded EDT fixing `v3b`'s `0.7510` failure), L2 connected routes (`T_0, S_bij0`), L3 scaffolds (`T_1, S_cav`), and L4 multi-port couplers/MMIs/25-hole gratings (`S_port_topo, S_rim, w*`).

---

## 6. Empirical Validation Summary (`v1.2.0` Direct Checks & Historical `v1.1.0` Campaign Record)

### 6.1 Direct RC-01 `v1.2.0` Verification (Current Code)

- **Unit, adversarial, & v1.2.0 calibration suite (`tests/test_rc01.py`)**: **21/21 passed**, covering identity, bit-identical determinism, exact symmetry, empty/shape edge cases, grayscale/`uint8` decoding, uncapped Betti counts $>256$, exterior dust-speck immunity, 1-px waveguide cuts, 1-px coupler bridges + dust-speck spoofs, filled rings + 2-px pinholes + off-center & centered Swiss-cheese + `V7` shifted fake holes, deletion-bonus paradox, hollow-slit-frames, `1x4 MMI` bay destruction + whisker exploits + ECT cancellation, `10:1` & `25:1` physical anisotropy equivalence, canvas overflow guard (+ `NaN`/non-positive fail-closed bounds), zero-overlap monotone RL shaping, stick-figure & checkerboard attacks, edge-touching bars, plus explicit v1.2.0 regressions (L0 single-piece tapers passing `s_topo >= 0.80` while upside-down pentagons & whiskers fail; `1600×1600` & mildly anisotropic `2496×2496` white-box 1/2/4-px interior whiskers snapped by full-res `t_neck < 0.50`; exact-`beta1` cavity scaling tempered cleanly while missing cavities still collapse `< 0.05`).
- **26 real PixCell GT controls (`2496px` rasters: 25 held-out val L0–L4 + L4 train fault `01e36796`)**: **26/26 pass `>= 0.97`** (`0.9882–0.9998`, mean **`0.9971`**, min `s_topo = 0.9961`, zero full-res neck erosion false alarms).
- **25 held-out val shortcut & Gate T4 audit (`v1.2.0`)**: BBox fill mean **`0.0351`**; Convex-hull fill mean **`0.1230`**; Gate T4 (`0.35w` vertical shift vs shortcuts): BBox vs Honest **`24/25`** (only near-convex `L1 06b88ff9` at `0.4524` vs `0.4365`), Convex Hull vs Honest **`23/25`** (same two near-convex L1 bars as `v1.1.0`).
- **Real `2496px` adversarial checks (`v1.2.0`)**: `cut_1px` (`L2 026447e3`) **`0.1812`** (`t_neck=0.472`); `bridge_1px` (`L4 059a4672` / `0641192a`) **`0.2134 / 0.1970`**; `delete_ports` (`L4 03a18410`) **`0.2209`** (`s_topo=0.245`); `move_port_80px` (`L4 03a18410`) **`0.1756`**; `L4 048dc382` V4 whisker + 5-px end-cap attacks (`IoU = 0.988`) `1px / 3px / 5px`: **`0.3845 / 0.4468 / 0.4843`** (`s_topo = 0.256–0.361`); real `L0 33ce9108` 180°-upside-down regular pentagon: **`0.1750`** (`s_topo = 0.205`). *(Trade-off note: on single-port `L4 048dc382`, full left-port deletion produces `r_fill = 0.360 >= 0.25` with matching port counts `(1,1,1,1)` and bays `27=27`, so `s_rim` still drops to `0.102` and overall RC-01 drops from `IoU=0.970` to `0.697`, though `s_topo = 1.000` under the explicit `r_fill < 0.25` decoupling threshold.)*

### 6.2 Historical `v1.1.0` Validation & Audit Record (Not Re-Run Under `v1.2.0`)

The following published audit summaries were measured under frozen `v1.1.0` prior to the `v1.2.0` calibration refinements (see [`RC01_DIVERGENCE_AUDIT.md`](RC01_DIVERGENCE_AUDIT.md) for full tables; do not compare `v1.1.0` and `v1.2.0` scores without paired rescoring):

- **Positive/negative controls (`v1.1.0`, 25 val tasks)**: GT controls `0.9898–0.9998` (mean `0.9974`, vs `shaped_v3b` min `0.7510` FAIL); BBox fill mean `0.0263`; Convex-hull fill mean `0.1107`; Gate T4 BBox vs Honest `25/25`, Convex Hull vs Honest `23/25`; wrong-task `2496×2496` mean `0.0104`.
- **Real Inkling-2-Mini re-ranking (`v1.1.0`, 59 Docker-rendered predictions)**: Flipped candidate rankings on 4 tasks (5 pairwise flips), purging broken 4-hole crosses (`L3 05b0064b`, `IoU=0.8907 -> RC01=0.1397`) and 5-piece disconnected outputs (`L4 03a18410`, `IoU=0.6285 -> RC01=0.0323`) in favor of topologically exact predictions.
- **Round-1 869-rollout Goodhart & Calibration Audit (`v1.1.0`)**: `23.4%` (`130/556`) of `IoU >= 0.70` rollouts failed `s_topo < 0.80` (`47.0%` on L3, `34.4%` on L4); top-15 divergence audit found `14/15` (`93.3%`) catastrophic photonic defects, `1/15` (`#14`, `12.8×` oversized cavities) strict scaling, and `0/15` rasterization false alarms; the 10-task L0/L1 `Trap80` audit found 8 genuine bugs and the 2 L0 single-piece taper false-strictness cases (`1d4432f7`, `0b6771b2`) directly resolved in `v1.2.0`.

---

## 7. Failure Cases, Limitations & Claim Boundaries

1. **Near-convex L1 primitives under large honest shift (Gate T4)**: On `L1 06b88ff9` (`Hull_IoU = 0.933`) and `L1 020c61bd` (`Hull_IoU = 0.890`), a $0.35w$ vertical translation moves the shape by $30\%$ of its own height, genuinely worse than a $93\%$ convex-hull approximation.
2. **Raster-level tangency**: Mathematical single-point tangencies (`L1 020c61bd`) rasterize as $\beta_0 = 1$; distinguishing exact tangency from 1-px overlap requires direct GDS polygon inspection.
3. **Electromagnetic & DRC claims**: High RC-01 establishes calibrated geometric, topological, thickness, and port-bay fidelity; it does **not** establish optical S-parameter equivalence or foundry DRC compliance (RC-02).
4. **Vector-hybrid extension**: `evaluate_rc01_calibrated` already bridges `calibration.json` anisotropy and `gds_size_um` overflow; future work can optionally pair this pure raster metric with exact `gdstk`/`shapely` minimum-gap DRC and port-signature checks inside the canonical sandbox.
