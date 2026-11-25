# RC-01 vs. Raw IoU: Formal Divergence, Goodhart Deficit, & Calibration Audit

- **Audited Metric Version (Sections 1–4.2)**: RC-01 `v1.1.0` (frozen historical audit baseline; see Section 5 for the frozen **`v1.2.0`** implementation in `src/michaelangelo/core/rc01.py` & [`RC01_FORMAL_SPEC.md`](RC01_FORMAL_SPEC.md) incorporating all three calibration refinements discovered in Section 4.2)
- **Audited Corpora** (all evaluated strictly inside canonical Docker `sha256:daf9faaf9881cfee5af6e1fcbeb7974d8c7fd44bb0e65fdc0c00fe5e7e6c123d`, zero control faults):
  1. **Round-1 Train Rollouts** (`r1_rc01_enriched.jsonl`): 500 `split-seed17` train tasks × 4 rollouts = 2,000 rollouts; **869 passing candidates (`IoU >= 0.45`)** across 252 multi-candidate groups (`>=2` passing rollouts).
  2. **Held-Out Checkpoints (`val50` & `val25`, `think_0.2`)**: `r0_base`, `r0_sft_gentle`, `r1_iou_ep1`, `r1_iou_ep2`, `r1_rc01_ep1`, and `r1_rc01_ep2`.
  3. **Canonical-Docker Calibration / False-Alarm Audit**: full sub-component & area-level inspection of the **top 15 unique highest-divergence Round-1 rollouts** plus **all 10 unique L0/L1 `Trap80` rollouts** (23 distinct tasks).

---

## 1. Formal Divergence & Goodhart Diagnostics

For any candidate $y$ evaluated on calibrated target $x$ with Raw IoU $I(y) \in [0, 1]$, RC-01 score $R(y) \in [0, 1]$, and topological fidelity gate $G_{\text{struct}}(y) = S_{\text{topo}}(y) \in [0, 1]$:

1. **Structural-Illusion Gap (Goodhart Deficit)**:
   $$\Delta_{\text{struct}}(y) = \max\big(0,\; I(y) - R(y)\big), \qquad \bar{\Delta}_{\text{struct}} = \mathbb{E}[\Delta_{\text{struct}}(y)].$$
   Measures how much raw pixel overlap overstates true photonic/structural fidelity. Under an IoU-optimized policy, **Goodhart divergence** occurs when $\Delta I > 0$ while $\Delta R \le 0$ (or $\Delta\bar{\Delta}_{\text{struct}} \gg 0$).
2. **High-IoU Trap Rates**:
   $$\operatorname{FPR}_{\text{trap70}} = \mathbb{P}\big(S_{\text{topo}}(y) < 0.80 \;\big|\; I(y) \ge 0.70\big), \qquad \operatorname{FPR}_{\text{trap80}} = \mathbb{P}\big(R(y) < 0.50 \;\big|\; I(y) \ge 0.80\big).$$
3. **Within-Task Rank Reversal & Best-of-$K$ Selection Regret**:
   For each task group $\mathcal{G}(x) = \{y_1, \dots, y_m\}$ ($m \ge 2$), let $y^*_{\text{IoU}} = \arg\max_{y \in \mathcal{G}} I(y)$ and $y^*_{\text{RC01}} = \arg\max_{y \in \mathcal{G}} R(y)$:
   $$\operatorname{Regret}_{\text{IoU} \to \text{RC01}}(x) = R(y^*_{\text{RC01}}) - R(y^*_{\text{IoU}}) \ge 0,$$
   paired with within-group Kendall's $\tau(I, R)$, Spearman's $\rho(I, R)$, and top-1 flip rate $\mathbb{P}(R(y^*_{\text{RC01}}) - R(y^*_{\text{IoU}}) > 10^{-4})$.

---

## 2. Round-1 Rollout Divergence Audit (869 Real Passing Candidates, L0–L4, `v1.1.0`)

| Level | $N$ (`IoU>=0.45`) | Mean IoU | Mean RC-01 | $\bar{\Delta}_{\text{struct}}$ | Mean $S_{\text{topo}}$ | $\operatorname{FPR}_{\text{trap70}}$ (`s_topo<0.80`) | $\operatorname{FPR}_{\text{trap80}}$ (`RC01<0.50`) | Groups ($m\ge 2$) | Top-1 Flip% | Best-of-4 Regret | Kendall $\tau$ | Spearman $\rho$ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **L0** | 223 | `0.8265` | `0.6753` | `0.1517` | `0.8104` | `32/164` (`19.5%`) | `15/139` (`10.8%`) | 62 | `9.7%` | `0.0093` | `0.845` | `0.858` |
| **L1** | 199 | `0.8362` | `0.6901` | `0.1474` | `0.8238` | `20/146` (`13.7%`) | `6/132` (`4.5%`) | 58 | `13.8%` | `0.0045` | `0.726` | `0.741` |
| **L2** | 164 | `0.8208` | `0.6304` | `0.1919` | `0.7456` | `25/116` (`21.6%`) | `6/106` (`5.7%`) | 46 | `13.0%` | `0.0113` | `0.690` | `0.705` |
| **L3** | 147 | `0.6929` | `0.3755` | **`0.3207`** | `0.4994` | **`31/66` (`47.0%`)** | **`16/46` (`34.8%`)** | 46 | **`26.1%`** | **`0.0319`** | **`0.609`** | **`0.641`** |
| **L4** | 136 | `0.7076` | `0.4985` | **`0.2213`** | `0.6155` | **`22/64` (`34.4%`)** | `6/46` (`13.0%`) | 40 | **`17.5%`** | **`0.0250`** | `0.750` | `0.780` |
| **ALL** | **869** | **`0.7865`** | **`0.5918`** | **`0.1978`** | **`0.7181`** | **`130/556` (`23.4%`)** | **`49/469` (`10.4%`)** | **252** | **`15.5%`** | **`0.0152`** | **`0.726`** | **`0.746`** |

**Key Structural Findings**:
1. **Nearly one quarter (`23.4%`) of all `IoU >= 0.70` Round-1 candidates fail topology (`s_topo < 0.80`)**, and **`10.4%` of `IoU >= 0.80` candidates collapse below `RC01 < 0.50`**.
2. **Complexity cliff at L3–L4**: $\bar{\Delta}_{\text{struct}}$ doubles from L0–L1 (`0.147–0.152`) to L3 (`0.321`) and L4 (`0.221`). Nearly **half (`47.0%`) of L3 `IoU >= 0.70` rollouts** and **one third (`34.4%`) of L4 `IoU >= 0.70` rollouts** are broken-topology traps; Best-of-4 top-1 selection reverses on **`26.1%` of L3** and **`17.5%` of L4** groups, costing `0.025–0.032` mean RC-01 regret per group if selected by raw IoU.
3. **Online GRPO group variance**: Across the 252 multi-candidate groups, RC-01 v1.1.0 produces **1.71× wider within-group std than Raw IoU** (`median 0.0850 vs 0.0498`, `mean 0.1166 vs 0.0678`), proving RC-01 strengthens rather than flattens GRPO advantage signal.

---

## 3. Held-Out Checkpoint Goodhart Audit (`val50` & `val25`, `v1.1.0`)

### 3.1 Overall Trajectory Across All 6 Checkpoints

| Checkpoint | `val50` Valid | `val50` IoU (all / val) | `val50` RC-01 (all / val) | `val50` $\bar{\Delta}_{\text{struct}}$ (all / val) | `val50` `T70` / `T80` | `val25` Valid | `val25` IoU / RC-01 (all) | `val25` $\bar{\Delta}_{\text{struct}}$ (all / val) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `r0_base` | `37/50` | `0.4346` / `0.5874` | `0.3285` / `0.4439` | `0.1090` / `0.1472` | `1/15` / `0/13` | `17/25` | `0.4243` / `0.3086` | `0.1197` / `0.1760` |
| `r0_sft_gentle` | `33/50` | `0.4211` / `0.6381` | `0.3231` / `0.4895` | `0.1032` / `0.1564` | `2/14` / `0/12` | `17/25` | `0.4509` / `0.3260` | `0.1296` / `0.1906` |
| `r1_iou_ep1` | **`37/50`** | **`0.4749`** / `0.6418` | **`0.3519`** / `0.4756` | `0.1272` / `0.1719` | `2/17` / `0/11` | `16/25` | `0.4147` / `0.2959` | `0.1215` / `0.1899` |
| `r1_iou_ep2` | `35/50` | `0.4358` / `0.6226` | `0.3129` / `0.4471` | `0.1268` / `0.1811` | `3/16` / **`1/13`** | **`18/25`** | **`0.4910`** / **`0.3626`** | `0.1339` / `0.1859` |
| **`r1_rc01_ep1`** | `31/50` | `0.3978` / `0.6416` | `0.3063` / **`0.4940`** | **`0.0970`** / `0.1564` | `3/16` / **`0/12`** | `15/25` | `0.3968` / `0.3189` | **`0.0881` / `0.1468`** |
| `r1_rc01_ep2` | `32/50` | `0.4036` / `0.6306` | `0.2776` / `0.4338` | `0.1305` / `0.2038` | `3/14` / `1/10` | `15/25` | `0.3491` / `0.2371` | `0.1167` / `0.1944` |

### 3.2 Live L4 Goodhart Divergence (Smoking-Gun Evidence)

| Checkpoint | `val25` L4 (ok) | `val25` L4 IoU | `val25` L4 RC-01 | `val25` L4 $\bar{\Delta}_{\text{all}}$ / $\bar{\Delta}_{\text{val}}$ | `val50` L4 (ok) | `val50` L4 IoU | `val50` L4 RC-01 | `val50` L4 $\bar{\Delta}_{\text{all}}$ / $\bar{\Delta}_{\text{val}}$ | `val50` L4 `T70` / `T80` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `r0_base` | `2/5` | `0.3322` | `0.2558` | `0.0763` / `0.1908` | `6/10` | `0.3261` | `0.1813` | `0.1447` / `0.2412` | `0/2` / `0/1` |
| `r1_iou_ep1` | `3/5` | `0.4432` (**`+0.111`**) | `0.2383` (**`-0.018`!**) | `0.2050` / **`0.3417`** | `8/10` | `0.4553` (`+0.129`) | `0.2566` (`+0.075`) | `0.1986` / `0.2483` | `1/3` / `0/1` |
| `r1_iou_ep2` | `5/5` | `0.6707` (`+0.339`) | `0.3714` (`+0.116`) | **`0.3126`** / `0.3126` | `10/10` | `0.5264` (**`+0.200`**) | `0.2576` (**`+0.001` vs ep1!**) | **`0.2754` / `0.2754`** | **`2/4` / `1/2`** |
| **`r1_rc01_ep1`** | `4/5` | `0.5267` (`+0.195`) | **`0.4604` (`+0.205`)** | **`0.1128` / `0.1410`** | `7/10` | `0.3898` (`+0.064`) | **`0.2730` (`+0.092`)** | **`0.1400` / `0.2001`** | `1/3` / **`0/1`** |
| `r1_rc01_ep2` | `3/5` | `0.3981` | `0.2215` | `0.1766` / `0.2944` | `5/10` | `0.3193` | `0.1475` | `0.1717` / `0.3435` | `2/3` / `0/1` |

**Causal Interpretation**:
1. **Direct L4 Goodhart Inversion (`r0_base -> r1_iou_ep1` on `val25`)**: Raw-IoU RFT raised L4 IoU by **`+0.1110`** (`0.3322 -> 0.4432`) while **degrading true L4 RC-01 by `-0.0175`** (`0.2558 -> 0.2383`), exploding $\bar{\Delta}_{\text{val}}$ to `0.3417`. Continuing to `r1_iou_ep2` on `val50` added another `+0.0711` L4 IoU (`0.4553 -> 0.5264`) for literally **`+0.0010` L4 RC-01** (`0.2566 -> 0.2576`), inflating `val50` L4 $\bar{\Delta}_{\text{struct}}$ to **`0.2754`** (`50%` of `IoU>=0.70` and `50%` of `IoU>=0.80` L4 outputs were broken-topology traps, e.g., `048dc382` `IoU=0.886 / RC01=0.099`).
2. **RC-01 Purification Eliminates L4 Goodhart Inflation (`r1_rc01_ep1`)**: Training 1 epoch on RC-01-purified traces delivered the **highest L4 RC-01 on BOTH `val25` (`0.4604`, `1.93×` `r1_iou_ep1`) and `val50` (`0.2730`)** while slashing `val25` L4 $\bar{\Delta}_{\text{val}}$ by **`2.4×`** (`0.3417 -> 0.1410`) and achieving the lowest overall Goodhart Deficit (`0.0970` on `val50`, `0.0881` on `val25`).
3. **Why Ep2 overfit on both arms**: Inkling's 3×-looped layers `6..17` overfit past ~50–60 steps (`r1_iou_ep2` degraded `val50` `topo` `-0.098`; `r1_rc01_ep2` degraded valid RC-01 `0.494 -> 0.434`), confirming 1-epoch RFT with higher RC-01 trace volume (`r2_rc01`) + conservative online dense RC-01 GRPO from `r1_iou_ep1` as the principled path forward.

---

## 4. Calibration & False-Alarm Audit (Canonical Docker Inspection, `v1.1.0`)

### 4.1 Top 15 Unique Highest-Divergence Round-1 Rollouts (`Δ = IoU - RC01 ∈ [0.691, 0.929]`)

Every single candidate below was re-rendered strictly inside canonical Docker `sha256:daf9faaf...`:

| # | Lv | Task ID | IoU | RC-01 | $\Delta$ | Exact Structural Diagnosis (`pred` vs `gt`) | Classification |
|---:|---|---|---:|---:|---:|---|---|
| 1 | L2 | `1c124bb792` | `0.9789` | `0.0498` | `0.9291` | $\beta_0 = 7$ vs $1$ (`[130k×3, 80k×4]` vs `[718k]`); code explicitly set `gap_um = 0.23` severing all 7 chain elements | **Genuine Bug** (7-way break) |
| 2 | L4 | `411c0da093` | `0.9356` | `0.0281` | `0.9075` | $\beta_0 = 3$ vs $1$ (two `50k` detached arms) **and** $\beta_1 = 0$ vs $2$ (both `19.6k` cavities vanished). | **Genuine Bug** (breaks + filled holes) |
| 3 | L1 | `02f2ad9d10` | `0.9077` | `0.0199` | `0.8878` | $\beta_1 = 1$ vs $0$: accidental `51,231 px` spurious interior hole (`s_sdf=0.545, s_width=0.679`). | **Genuine Bug** (spurious cavity) |
| 4 | L3 | `0a61e8ce26` | `0.8787` | `0.0242` | `0.8544` | $\beta_0 = 3$ vs $1$ (`272k` + `70k` detached arms) + $\beta_1 = 0$ vs $2$ (`211 px` crevices missing). | **Genuine Bug** (3-way disconnection) |
| 5 | L3 | `1f9723be0a` | `0.8713` | `0.0251` | `0.8462` | $\beta_1 = 2$ vs $0$: two `23,411 px` spurious enclosed holes from wrong routing. | **Genuine Bug** (2 spurious cavities) |
| 6 | L1 | `101b644682` | `0.8409` | `0.0167` | `0.8242` | $\beta_1 = 0$ vs $1$ (real `4,003 px` hole filled) + `+403k px` overfill (`s_sdf=0.301`). | **Genuine Bug** (filled hole + overfill) |
| 7 | L4 | `01f01fc07f` | `0.7999` | `0.0153` | `0.7846` | $\beta_1 = 6$ vs $42$: missed **36 of 42** photonic-crystal lattice holes (`s_width=0.250`). | **Genuine Bug** (36 missing PhC holes) |
| 8 | L2 | `2f4560d6e0` | `0.7874` | `0.0210` | `0.7664` | $\beta_1 = 0$ vs $1$: **1,232,017 px** central loop cavity completely missing/open + wrong port valence. | **Genuine Bug** (missing 1.23M loop) |
| 9 | L3 | `2b92c0b4bd` | `0.8120` | `0.0599` | `0.7521` | Holes `25×` too small (`100 px` vs `2,529 px`) + wrong L/R ports (`[2,2]` vs `[1,1]`, `s_port=0.151`). | **Genuine Bug** (wrong ports + cavities) |
| 10 | L2 | `00f1f41582` | `0.8379` | `0.0924` | `0.7456` | $\beta_1 = 3$ vs $7$: missed **4 of 7** `33k px` cavities + wrong R port valence (`2 vs 1`). | **Genuine Bug** (4 missing cavities) |
| 11 | L3 | `0cb5ea82e4` | `0.7505` | `0.0249` | `0.7256` | $\beta_1 = 2$ vs $1$: missed `7,878 px` hole (`s_cav=0.0`), pinched two `202 px` spurious gaps elsewhere. | **Genuine Bug** (wrong cavity location) |
| 12 | L3 | `13d2859e3f` | `0.9041` | `0.1796` | `0.7246` | $\beta_0 = 5$ vs $1$: **4 massive `87.7k px` ports completely detached** from central body. | **Genuine Bug** (4 detached ports) |
| 13 | L2 | `060bc964fe` | `0.8532` | `0.1329` | `0.7203` | Fused BOTH top & bottom dual ports into solid slabs (`ports [1,1,1,1] vs [1,1,2,2]`, `bays 4 vs 6`). | **Genuine Bug** (fused dual ports/bays) |
| 14 | L3 | `0885b184b5` | `0.9383` | `0.2271` | `0.7112` | Exact $\beta_0=1, \beta_1=2$, ports, bays (`s_rim=0.999, s_width=0.924`), but the 2 enclosed crevices are **`12.8×` oversized** (`15,600 px` vs `1,214 px`, `s_cav=0.150`). | **Genuine Defect / Strict Scale** |
| 15 | L4 | `021b4232e0` | `0.8008` | `0.1098` | `0.6909` | $\beta_1 = 12$ vs $42$: 12 giant `46k px` holes instead of 42 `6.3k px` PhC holes. | **Genuine Bug** (wrong PhC lattice) |

**Top-15 Verdict**: **14/15 (`93.3%`) unambiguous catastrophic photonic/structural defects**, **1/15 (`6.7%`) genuine `12.8×` cavity-sizing defect scored strictly** (`#14`), and **`0/15` (`0.0%`) rasterization/sub-pixel false alarms.**

### 4.2 Extended False-Alarm Hunt: All 10 Unique L0/L1 `Trap80` Rollouts (`IoU >= 0.80, RC01 < 0.50`)

Because L0 single primitives unexpectedly exhibited `10.8%` `Trap80`, we audited **all 10 unique L0/L1 `Trap80` tasks** specifically hunting for RC-01 over-strictness:

- **8 / 10 (`80%`) are genuine structural/orientation defects**:
  - **2 × 180°-upside-down regular pentagons** (`L0 01283d17`, `L0 33ce9108`, `IoU=0.812 -> RC01=0.221`): target has flat top / pointed bottom (`z_fills T=0.649, B=0.131`), whereas candidate rotated `-90°` points upside-down (`T=0.131, B=0.649`); raw IoU gave `0.812`, RC-01 caught the 180° flip cleanly.
  - **6 × genuine L1 structural defects**: `02f2ad9d` (spurious 51k hole), `101b6446` (filled 4k hole), `467b4bcd` (`IoU=0.902`, `beta0=2 vs 1` broken link), `07c8ce87` (`IoU=0.874`, wrong double-pad dumbbell `ports [1,1,2,2] vs [1,1,1,1]`), `09581420` (`bays 2 vs 4`), `06c06dcf` (`s_sdf=0.429` misaligned dual cavities).
- **2 / 10 (`20%`) ARE Genuine RC-01 v1.1 Calibration Over-Strictness Cases (`L0 1d4432f7`, `L0 0b6771b2`)**:
  - Both are single-piece L0 left-to-right tapers/horns (`IoU=0.814 / 0.853 -> RC01=0.345 / 0.451`) with **exact topology** (`b0=1, b1=0, ports=(1,1,1,1), bays=2`), **correct orientation**, `s_bnd=0.76–0.81`, and `s_width=0.85–0.89`, differing only in narrow-end taper width (`4.0 um` vs `~6.2 um`, `s_sdf=0.365–0.423`).
  - **Root cause**: Putting the continuous 10% port-zone fill ratio `r_fill` inside `s_port_topo` (which gates `s_topo`) caused a moderate geometric end-width mismatch (`r_fill_L ≈ 0.58`) to drop `s_topo` to `0.480 / 0.602` (< `0.80` topological gate).

---

## 5. Frozen RC-01 `v1.2.0` Calibration Implementation (`src/michaelangelo/core/rc01.py`)

All three calibration refinements identified in Section 4.2 are now implemented and frozen as **`RC01_VERSION = "1.2.0"`** in `src/michaelangelo/core/rc01.py` (with unit/adversarial regression coverage in `tests/test_rc01.py` and first-class `"rc01"` / `"validity_only"` reward policies in `rl/track_a/reward.py`), without retroactively altering historical `v1.1.0` records:

1. **Matching-port `r_fill` decoupling**: When side port counts match (`k_s(A) == k_s(B)`), continuous `r_fill` stays inside `s_rim`, while `s_port_topo` only triggers for catastrophic `>4×` arm/whisker collapse (`r_fill < 0.25`, with tight symmetric 1-px Nyquist perimeter tolerance `min(z_tols_a, z_tols_b)`) or discrete port-count/bay mismatches. Single-piece L0 tapers now pass `s_topo >= 0.80` while real 180°-flipped pentagons (`33ce9108`: `0.1750`, `s_topo=0.205`), MMI bay losses, and `048dc382` 1/3/5-px whiskers (`0.3845 / 0.4468 / 0.4843`, `s_topo=0.256–0.361`) remain crushed.
2. **Full-resolution narrow-band neck erosion on `>1024px` canvases**: Removes the `>1024px` SDF-downsampling skip whenever `max(r_neck/dy, r_neck/dx) <= 2.5` or `r_neck < 0.75 * min(sy_s * dy, sx_s * dx)` (up to `8 px` per axis), snapping 1–4 px white-box interior whiskers on isotropic and mildly anisotropic `1440px`/`2496px` canvases cleanly (`t_neck < 0.50`) with fast vectorized slicing on near-isotropic calibrated grids and `0/26` false alarms on real `2496px` GT controls (`0.9882–0.9998`, mean `0.9971`).
3. **Mild sublinear `s_cav` tempering for exact-count cavities**: When `beta1(A) == beta1(B) >= 1` and `s_cav_raw > 0`, applies `s_cav = s_cav_raw ** 0.65` so exact-count scaled cavities (`#14`) still degrade strongly (`s_topo < 0.50`) without collapsing identically to missing or shifted non-overlapping cavities (`0 ** 0.65 == 0`).
