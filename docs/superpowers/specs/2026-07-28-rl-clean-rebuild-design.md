# RL clean rebuild — two Qwen runs on the sealed curriculum

**Date:** 2026-07-28 · **Branch:** `worktree-rl-clean-runs` (base `origin/main` @ `802110aff`)
**Goal:** delete the ceremony, restore the proven training signal, and run the paper's
two Qwen training arms on the released sealed dataset.

---

## 1. Diagnosis (what the study of both repos established)

### The old private library (`PixCell-running/rl`) learned; this tree cannot. Why:

**The old reward was `v3-b` shaped, anchored on `iou_n` — rectangle-baseline-normalized
excess IoU.** For every task, the IoU/Dice of a solid rectangle filling the calibrated
bounding box (`iou_rect`, `dice_rect`) is precomputed once, and the reward pays only for
structure *beyond* that degenerate answer:

```
iou_n      = max(0, (iou − iou_rect) / (1 − iou_rect))          # 0 = the rectangle hack, 1 = perfect
dice_n     = likewise
τ          = 0.05 · diag_um                                      # footprint diagonal sets the scale
t2b        = exp(−chamfer_boundary_um / τ)                       # boundary closeness
teacher_nb = max(0, t2b − t2b_rect) / max(1 − t2b_rect, 0.3)

crash / timeout / no-gds / bad-gds / syntax  →  0.0
purity violation (non-catalog geometry)      →  0.0              # old "ship mode"
executable + pure, iou_rect < 0.95           →  0.05 + 0.40·iou_n + 0.15·dice_n + 0.40·teacher_nb
executable + pure, iou_rect ≥ 0.95           →  0.05 + 0.40·iou  + 0.15·dice   + 0.40·t2b   # degenerate branch
```

Why each piece exists (all evidenced in the old repo):
- **Rectangle normalization** kills the measured degenerate attractor (the old policy
  *found* the bbox-fill hack: reward 0.975 on one task) and makes one reward scale mean
  the same thing on every task — which is what makes curricula, winner thresholds, and
  readable curves possible.
- **The 0.05 executable floor** separates "wrong geometry but a valid program" from
  "crash", restoring gradient exactly where early RL lives.
- **The boundary-chamfer teacher term** pays for count/boundary progress IoU cannot see
  (one more meander on a serpentine barely moves IoU).
- **The degenerate branch** scores rectangle-like targets raw, because normalizing
  against a rectangle that *is* the answer makes every program look identical.

With this reward, GRPO on Qwen3.6-35B-A3B (LoRA 32, G=8×B=8, lr 1e-5, 4096 tokens,
`qwen3_5_disable_thinking`) produced unambiguous learning: train `iou_n` 0.187→0.389
over the 95-step paper lineage; held-out `iou_n` 0.162→0.299 (+85% relative); the
no-SFT "pure" lineage took held-out L0 raw IoU **0.038→0.911** in three days.

**This tree replaced that signal with `reward = raw absolute IoU, else 0`**
(`representation_training_v1/launcher.py:917`, `"reward": "raw_absolute_scale_iou"`).
Consequences, all verified in code: no floor (valid-but-wrong ≡ crash ≡ 0), no
normalization (blob-filling pays; hard tasks pin near 0), Dice/chamfer discarded as
diagnostics, and — combined with `remove_constant_reward_groups=True` and group size
**4** — any task the model cannot already partially solve produces an all-zero group
that is deleted from the batch. Early RL on an unmastered level receives almost no
gradient. The two 6-step runs it managed before stalling show reward as pure noise.

### The old library's fatal weakness was the opposite one: **unsealed data.**
Eval pool grew 64→253 mid-campaign (curves incomparable across the boundary), the train
pool grew/shrank/killed a live run, pools were gitignored, and seed determinism broke on
any motif-registry edit. **This repo already fixed that completely**: the released
dataset is frozen under four layers of hashing, the loader re-verifies SHAs per row, and
model-visible vs verifier-only fields are separated by construction (`rl/common/contracts.py`).

### The ceremony this tree added is measurable and killed its own campaign.
~90% of 30,381 lines is scaffolding (two W&B integrations, two immutable-ledger systems,
two recipe-locking systems, wave/approval receipts, promotion gates at 0.80 IoU — a bar
the *old* runs show L2/L3 never reach). On launch night (Jul 28) the provenance
machinery itself caused three aborted launches in 100 minutes, then a 6-hour stall, then
the protocol's own baseline gate was relaxed to get anything running at all; ten
`training-live` worktrees exist only because runs were SHA-bound and every hotfix
required a fresh clean tree. The one useful negative result: 55-step **mixed-level SFT
produced ~0-IoU checkpoints** (renderer diagnostic: 1/8 executable), while **L0-only SFT
produced a usable checkpoint** (RL from it emitted executable programs at reward 0.2–0.5).

### What is genuinely good here and must be kept
`rl/common/` wholesale (contracts, hash-verified parquet loader, prompt contract
`pixcell-direct-reconstruction-v2`, preprocessing, batcher, per-candidate Docker
isolation with immutable image binding), the deterministic curriculum helpers
(exactly-once stratified SFT pass; 80/20 five-step replay cycle — both pinned by tests),
`tinker_data.py`'s clean Cookbook `Env`/`RLDataset` wrapper, and the essential parts of
preflight (dataset digest check against `freeze.json`, sandbox binding, clean-tree check).

---

## 2. What we will build (the decision)

**One training path, two runs, one reward.** Everything lives in `rl/track_a/` over
`rl/common/`; the studies apparatus is deleted.

### 2.1 Reward: port `v3-b` exactly — new policy `"shaped_v3b"`
- Constants identical to the old library (0.05 floor; 0.40/0.15/0.40 weights; τ = 0.05·diag;
  denominator floor 0.3; degenerate threshold `iou_rect ≥ 0.95`). These constants
  produced the curves; they are not re-tuned.
- Purity: the current evaluator rejects non-catalog programs *before* execution
  (`SOURCE_REJECTED → 0.0`). This matches the old ship-mode semantics (impure = 0.0,
  the Jul-21 stop-ship: a floor for impure programs trains the violation). Keep the
  current order.
- Per-task baselines (`iou_rect`, `dice_rect`, `chamfer_rect_boundary_um`, `diag_um`)
  are computed once per task from `target_image` + stored calibration, cached in-process
  keyed by `target_image_sha256`, and dumped to the run directory for provenance. The
  dataset is frozen, so these are constants of the release.
- The evaluator gains two candidate-side measurements it already half-computes: Dice
  (exists as diagnostic) and symmetric mean boundary-chamfer in µm (ported from the old
  `rl/reward/geometry.py`).
- `raw_iou` and `validity_floor` policies remain in the file for the record; the runs
  use `shaped_v3b`.
- Old shaping tests are ported and adapted (rect-equivalent ⇒ exactly 0.05; the
  (0.75, base 0.5) ⇒ 0.5 normalization case; purity ⇒ 0.0; crash ⇒ 0.0; degenerate
  branch exactness; denominator floor; ground-truth self-score ≈ 1.0).

### 2.2 Training recipe (both runs share it)
| Knob | Value | Source of truth |
|---|---|---|
| Model | `Qwen/Qwen3.6-35B-A3B` | paper + both repos |
| LoRA rank | 32 | old lineage + paper |
| Renderer | `qwen3_5_disable_thinking` | old winning lineage (60k-thinking is 10×+ decode cost; RC-H05 showed thinking@60k ≈ 0.218 zero-shot — not needed for the training result) |
| Max sampled tokens | 4096 | old lineage |
| Image | dataset-native, max edge 1440 | dataset is drawn at 1440 |
| GRPO | G=**8** rollouts × 8 groups/step, lr 1e-5, temp 1.0, top-p 1.0, `importance_sampling`, KL 0 | old lineage (this tree's G=4 halves the group signal) |
| Advantage | plain within-group mean-centering; constant-reward groups dropped | cookbook default = old paper lineage (PKPO/advantage-patch was an Inkling-era experiment; not ported) |
| Curriculum | staged L0→L4, **30 steps/level**, 80/20 current/replay via the existing deterministic five-step cycle | old stage budgets (30/35/30) + this tree's tested scheduler; no mastery gates, no approvals |
| Checkpoints | state every 5 steps; sampler checkpoint at each level boundary + final | enough to resume and to evaluate; nothing else |

### 2.3 The four runs — a 2×2: (±L0-SFT) × (no-think / think) [user-extended 2026-07-28]
The failed campaign's one useful measurement is RC-H05: zero-shot Qwen with thinking
at a 60k output ceiling scores **0.218 mean IoU@1** on F1–F8 under the corrected v2
prompt — already near the old post-training result (0.24). RL from that operating
point starts from a far higher launchpad, and the campaign's two 6-step runs sampled
with thinking@60k through this exact Env, so the path is execution-proven. Per the
user's direction, the ±SFT pair runs at both operating points, all four simultaneous:

| Run | Operating point | Arm |
|---|---|---|
| **A** `runA-l0sft-rl` | `qwen3_5_disable_thinking`, max_tokens 4096 | L0-SFT → RL L0→L4 (150 steps) |
| **B** `runB-base-rl` | `qwen3_5_disable_thinking`, max_tokens 4096 | base → RL L0→L4 (150 steps) |
| **C** `runC-think-base-rl` | `qwen3_5` (thinking), max_tokens 60000 | base → RL L0→L4 (150 steps) |
| **D** `runD-think-l0sft-rl` | `qwen3_5` (thinking), max_tokens 60000 | L0-SFT → RL L0→L4 (150 steps) |

Within each operating point the pair is a controlled ±L0-SFT comparison at matched RL
budget — the "controlled ablation" and "untouched training evaluations" the paper
defers (`arxiv/main.tex:879-881, :932-942`). Across operating points, A/B vs C/D
measures what the reasoning budget buys under identical reward, data, and schedule.

**Run D's SFT is gated.** The renderer diagnostic showed code-only SFT collapsing
checkpoints under the thinking renderer (0/8 executable) — but that was mixed-level
SFT, where L1–L4 labels plausibly truncated at `max_length`; L0-only SFT is the clean
test of the renderer hypothesis. D therefore runs its L0-SFT (code-only labels,
thinking renderer) and proceeds to RL **only if** the post-SFT sanity probe beats the
base-model thinking probe; otherwise D falls back to RL-from-base (C's config, second
seed) and the SFT collapse is reported as a finding. SFT for A stays as designed:
642 L0 `depth/train` rows, batch 64, lr 1e-4 linear, `LAST_ASSISTANT_MESSAGE`,
2 epochs ≈ 22 steps, prompt byte-identical to RL. Image stays 1440 for all four
(dataset-native; the protocol's 1920 was a no-op since no dataset image exceeds 1440).
Prompt-identity rule: each SFT and the RL that resumes it share one renderer.

**SFT hygiene (the mixed-SFT autopsy made this mandatory):**
1. decode-and-inspect rendered datums (text + train-mask) before spending;
2. token-length audit of all 642 labels — every label must fit `max_length` un-truncated
   (mixed-SFT's ~0-IoU collapse is consistent with long L2–L4 labels truncating at 6144;
   L0-only SFT dodges this, and we verify rather than assume);
3. post-SFT sanity eval before RL: 8 fixed L0 validation tasks, require ≥6/8 executable
   and mean IoU above the base-model probe, else stop and diagnose.

### 2.4 Evaluation (one instrument, no studies)
- **Probe set**: 80 tasks = 16/level from `depth/validation`, deterministically selected
  (sorted `opaque_id`, first 16 per level; recorded in the run dir). Eval@1 at T=1.0
  every 5 steps → per-level executable rate, raw IoU, and shaped reward. This is the
  training curve for the paper.
- **Step-0 probe = the base baseline.** No separate baselining studies, ever.
- **Final**: full `depth/validation` eval@1 for both final checkpoints, plus the F1–F8
  benchmark at k=8 through the same evaluator — the paper's headline protocol.
- Everything flows through the same Docker-isolated evaluator; every number is
  recomputed from artifacts (the conductor invariant survives; the receipts do not).

### 2.5 Provenance-lite (keep the invariant, drop the theater)
Commit before launch; preflight = dataset-digest check + sandbox-image binding +
renderer/tokenizer sanity + ground-truth positive control + clean-tree check; run dir
records resolved config + git SHA + baseline cache; Cookbook writes `metrics.jsonl`;
W&B project **`pixcell-rl`** (the old project — new curves land beside the ones that
worked), run names `runA-l0sft-rl-<date>` / `runB-base-rl-<date>`. No deterministic
run-id binding, no wave receipts, no approval tokens, no store locks, no SHA-suffixed
store roots. Run artifacts live outside the repo under the existing training volume
(`/Volumes/aadarwal_vx/QPG-MIT/PixCell-training/runs-v2/`, fallback `~/pixcell-training/`).

### 2.6 Launch mechanics (the 6-hour-stall lesson)
Runs launch in detached host tmux panes (not inside an agent session), logging to the
run dir; monitoring reads `metrics.jsonl` and rollout summaries. Keys are sourced from
the existing env file at launch, never printed. Smoke first: 2 GRPO steps at G=8×B=2 on
L0 **per operating point** (one no-think smoke, one think smoke — thinking decode is
~3–10× per rollout, so C/D cost must be measured, not assumed); the extrapolated cost
of all four full runs is reported before the full launches go out. Four simultaneous
runs share this machine's Docker evaluator: per-candidate containers are capped at
1 CPU and the batcher bounds in-flight evaluations per run, so evaluation queues
rather than thrashes; sampling, not evaluation, dominates step wall-clock.

### 2.7 Deletions (this branch)
- `rl/studies/` — all three studies + both extensions (the campaign ceremony, the
  superseded diagnostics, the mastery/promotion machinery).
- `rl/evaluation/` — the zero-shot baselining harness + its W&B mirror.
- `rl/track_b/` — the Inkling TML shim. Inkling is out of scope for the paper.
- `rl/track_c/` — an empty reservation.
- In `rl/track_a/`: the recipe-lock/approval surface (`recipe.py` ceremony,
  `evaluation_contract.py`, checkpoint promotion/selection) replaced by one lean runner;
  reward/tinker_data/curriculum/preflight-essentials/train entry points stay.
- Tests follow their code: the ~800 lines pinning the learning signal stay and grow
  (shaped-reward tests); ceremony tests leave with the ceremony.
- `rl/README.md` rewritten to describe exactly this design; `track_a/README.md` updated
  (reward table changes from `0.05 + 0.95·IoU` to the shaped contract).

### 2.8 Resolved by measurement: prompt contract v3 (anisotropy note) — TAKEN
Measured over `depth/train` (3,468 rows): **50% exceed 1.6× aspect distortion**
(p50 1.59, p90 5.0, max 31.6; by level: L0 29%, L1 42%, L2 49%, L3 53%, **L4 78%**).
The old library's honest scale note is therefore required, not optional: above 1.6×
the prompt states the per-axis render scale computed only from the attached image's
ink bbox and the stated footprint. Contract bumped `v2 → v3`; tests updated; below
the threshold the prompt is byte-identical to v2.

---

## 3. Alternatives considered

**A. Patch the existing study in place** (flip `reward_policy`, G4→G8, run its stages).
Least code motion, but keeps the machinery that demonstrably killed launch night (three
provenance aborts, SHA-bound relaunch worktrees, approval tokens, mastery gates), and
directly contradicts the directive to remove it. Rejected.

**B. Clean rebuild on `track_a` + `common`, port the proven reward.** Chosen — keeps
this repo's genuinely superior data/isolation layer and the old repo's proven signal;
one path, two runs, no studies. (This document.)

**C. Port the old library wholesale onto the new dataset.** The loop is byte-proven,
but it drags in the sample-dir pool machinery the parquet release replaced, loses the
sealed loader/contracts and Docker isolation, and reintroduces the unsealed-data class
of failure. Rejected.

---

## 4. Risks and mitigations
- **SFT collapse (mixed-SFT precedent)** → L0-only SFT + the three-step hygiene gate in §2.3.
- **Reward-port drift** → old tests ported verbatim; ground-truth positive control must
  self-score ≈ 1.0 through the full shaped path; constants pinned by test.
- **All-zero groups persisting early in Run B** → the floor guarantees executable
  variance pays; smoke run inspects `frac_mixed`/dropped-group counts at steps 1–2.
- **Sandbox image missing/stale on this machine** → preflight binds the image by
  spec-hash label; build script exists (`rl/common/sandbox/build.py`); smoke exercises it.
- **Session-tied runs** → detached tmux launch; resume = re-run the same command (state
  checkpoints every 5 steps; Cookbook resume).
- **Spend surprise** → smoke measures true per-step cost; both-run extrapolation is
  reported before full launch; runs are per-level resumable so they can be stopped at
  any stage boundary.

## 5. Test plan
- Ported shaping tests (constants, normalization, degenerate branch, purity, crash).
- Evaluator: Dice + boundary-chamfer surfaces exist and match hand-computed values on
  synthetic masks; ground-truth self-score ≈ 1.0 under `shaped_v3b`.
- Baseline computation: rectangle baseline on a known mask matches hand-computed
  `iou_rect`/`dice_rect`; cache keyed by `target_image_sha256`.
- Curriculum/schedule invariants keep their existing tests (exactly-once pass, 80/20 cycle).
- Prompt contract tests updated only if §2.8 measurement adds the scale note.
- `uv run pytest rl/ -q` green; `ruff` clean; CI surface (`tests/ rl/ release/`) green.

## 6. Explicit non-goals
No Inkling. No new zero-shot baseline studies. No dataset changes. No HF publishing.
No paper edits until both runs have results (then: the deferred-ablation paragraph, a
training-curve figure to re-fill the orphaned `fig_rl_training` slot, and Table III
companions — as a separate reviewed change with the user).
