# Paper-to-Three-Fabs Runbook

The sweepable protocol distilled from the 2026-07-02 MZI proof
(`data/agents/pdk_swap/`; figures regenerate via `paper/tools/make_fig_pdk_swap.py`).
One device image in → per-stack retargeted, verified designs out.
Designed so a conductor can run N devices in parallel windows overnight.

## Inputs (per device)

```
data/agents/paper_swap/<device>/
├── device_bw.png        # the paper figure, device-only B&W
├── footprint.json       # {"footprint_um": [L, W]}
├── stacks/*.json        # target platforms (core_n, clad_n, thickness_um,
│                        #   single_mode_width_um, min_feature_um, ...)
└── spec_<stack>.json    # schema-v2 spec per stack (see step 1)
```

## Step 1 — FoM selection (conductor, before any agent)

Classify the device from the figure and pick its FUNCTION-defining FoM —
the metric that makes the device the device. Then pick the cheapest valid
evaluation tier:

| Device class | Function FoM | Tier-0 reduction | In-loop tier |
|---|---|---|---|
| unbalanced MZI | FSR | λ²/(n_g·ΔL), mode solve | 0 (free, exact) |
| directional coupler | splitting vs length | L_c = λ/(2Δn_supermode) | 0 |
| MMI splitter | imaging length | L_π = λ/(2(n₀−n₁)) | 0 (+1 for IL) |
| ring/racetrack | FSR, coupling | perimeter·n_g; supermodes | 0 |
| adiabatic coupler / taper | transfer transmission | sliced supermode solves GUIDE only | 1 (cheap if device small) |

Rules learned the hard way:
- Quality metrics (ER, IL) are deliberate ADDITIONS, not defaults. The spec
  file controls everything: list only the function FoM first. Unmeasured
  tier-1 targets block passes — never fake them.
- Footprint budgets scale with confinement: what fits in X on SOI cannot
  physically fit at SiN/TFLN single-mode widths. Per-stack budgets, reasoning
  recorded in the spec.
- Tier-1-in-the-loop is legitimate ONLY when no tier-0 reduction exists AND
  the device is small (≲50 µm ⇒ ~0.1–0.3 FlexCredits/eval). Hard-cap calls
  per stack in the brief (default 3) and ceiling every run script.

## Step 2 — stand up the window (conductor)

One tmux window per device, two clean-record worker panes:
- Opus 4.8 medium (`claude --dangerously-skip-permissions --model claude-opus-4-8 --effort medium`) — the deployed live-agent default.
- codex gpt-5.5 xhigh fast (`codex --yolo -c mcp_servers={}`) — MCP disabled
  (a hanging personal MCP server blocks codex's first turn; workers are headless).
Launch the CLI, VERIFY the composer is up (`pane read`), then send the brief
(`pane send %id -f brief.md`). Never send into a booting shell.

## Step 3 — Phase A: blind recreation (both workers, parallel)

Brief template: `data/agents/paper_swap/briefs/phaseA_recreation.md`
(adapt paths; codex gets its own output dir + NO-git rule — shared worktree).
Non-negotiables in every brief:
- Inputs: image + footprint ONLY. No reading other arms' dirs / any ground truth.
- Primitives only (no gf.components device stencils, no raw polygons).
- Parametric contract: top-level `name = value` tunables; the device's
  function knobs MUST be tunables; lengths.json where the FoM needs measured
  path lengths (MZI-class); gdsfactory 9.20.7, layer (1,0).
- Loop ≤6 iterations vs `python -m michaelangelo.core.compare_absolute` IoU; honest
  best; per-iteration log; end marker "PHASE_A DONE: IoU=<x>" (digit-anchored
  markers — pollers must grep for `DONE: <field>=[0-9]`, never bare DONE, and
  exclude the brief's own template text).

Conductor gate: recompute IoU yourself; purity-grep the script
(`gf.components.(mzi|ring|coupler|mmi)|add_polygon`); knob-response check.

## Step 4 — Phase B: per-stack retarget (winner or both)

Brief: per stack, rule-set the platform constants (widths from stack JSON),
then reason–predict–measure on the function knobs against
`python -m homi.spec_optimization eval --script S --stack K --spec spec_<stack>.json`.
- Tier-0 FoM: expect 1–2 call convergence (precompute from the governing relation).
- Tier-1 FoM: agent derives geometry from tier-0 slice solves, conductor runs
  the capped FDTD evals and feeds results back via `--measured` (workers
  never run cloud jobs themselves).
- Per-iteration log with prediction-before-measurement. Honest failure > fudge.

Conductor gate: re-run every reported eval; cross-matrix if claiming
stack-specificity (evaluate each design on every stack).

## Step 5 — verification tiers (conductor only; all cloud spend)

- Every cloud script: cost estimate + hard ceiling + explicit human
  authorization for the session budget. Drafts never auto-start outside that.
- Tier-1 fixtures: fan outputs ≥5 µm apart before monitor planes (planes
  narrower than separation) — overlapping planes read impossible physics
  (negative IL = the telltale). Sanity-check conservation before believing.
- Full-device runs: place ports by geometric slice of the GDS, NOT the Flex
  builder's bbox-center default (misses folded/asymmetric layouts); broadband
  monitor (the builder's default is single-frequency); run_time covers the
  folded optical path; fringe/period claims via autocorrelation, not naive
  peak-picking.

## Step 6 — deliverables per device

`summary.json` (per stack: FoM measured, verdict, iterations, bbox),
cross-matrix where applicable, layout renders (before/after), honest-residual
notes. Feed into the device row of the sweep report.

## Sweep mode (overnight)

- One window per device; conductor loops: scaffold → briefs → pollers →
  verify → commit. Pollers are background greps with digit-anchored markers.
- Budget: tier-0 devices ≈ free; tier-1 devices ≈ (#stacks × cap × ~0.2cr) per
  agent. Set a session ceiling BEFORE starting the sweep; the conductor stops
  launching runs when spent.
- Commit per device with Commitment trailers; unsigned commits
  (`git -c commit.gpgsign=false`) when 1Password is locked overnight.
- Known worker-pane gotchas: pane_status misreads panes launched via compound
  commands (poll screen markers instead); codex needs `-c mcp_servers={}`;
  briefs with quotes/newlines go via `pane send -f file`.

## Step 7 — metrics capture (MANDATORY, per phase, per worker)

Time, context, and cost are analysis axes, not afterthoughts. The conductor
records, at every phase completion, into `<device>/output/metrics.json`:
- `duration_min`: from the CLI's own turn timer ("Worked for Xm Ys" /
  "<verb> for Xm Ys" in the pane) + wall-clock marker timestamps.
- `context`: status-line readback — claude panes show `ctx (Nk/1.0M)`, codex
  shows `Context N% used · NK`. Capture AFTER each phase; the same readback
  that validates the model/effort flag captures this for free.
- `cloud_cost`: after every cloud task, query `web.real_cost(task_id)` (billed,
  pro-rated — estimates overstate by 2-10x on early-shutoff runs). Keep a
  per-device task-id ledger; totals roll up to the sweep report.
- Workflow-mode stages get tokens for free: the runtime tracks per-agent token
  usage in the journal — harvest it into the same metrics.json.
Retro-reference: `data/agents/pdk_swap/output/run_metrics.json` +
`cloud_costs.json` (the MZI proof: ~5.7h wall, 4.366 FlexCredits billed).

## Step 8 — transcripts + anti-cheat audit (MANDATORY)

Transcripts are the primary data. Per run:
- Archive EVERY worker's session transcript (claude: ~/.claude/projects/<worktree>/<session>.jsonl,
  map to workers by grepping for their brief's distinctive strings; codex:
  ~/.codex/sessions/<date>/rollout-*.jsonl) as gzip into
  `experiments/<exp>/transcripts/` with an INDEX.json.
- Access audit (the appendix artifact): grep each transcript for forbidden-path
  patterns NOT present in its own brief — ground-truth dirs (fixture benchmark
  dirs, scaffold/baseline), the OTHER workers' output dirs. Zero content hits =
  clean; investigate every hit's context (incidental filename exposure via
  `git status` listings is distinct from content access — instruct workers to
  scope git status to their own paths, or have the conductor commit).
- Blindness leaks hide in inputs, not just briefs: spec files must not name the
  device class or its mechanism (the FoM says WHAT must be met, never WHY);
  briefs must not classify the device or hint the physics direction — the
  worker's own Phase-A log is its only classification source. Tool INVENTORY
  (the evaluator's --help) is fair; tool CHOICE is part of what's measured.

- Pre-dispatch hint-lint (conductor invariant): the conductor knows the device
  class from step 1 — before sending ANY brief/spec, grep the rendered worker
  inputs for the conductor's own classification vocabulary (device-class
  names, mechanism words, governing-relation formulas). Any hit blocks
  dispatch. Workers derive; conductors never teach.
- Spec provenance (mechanical): every target in a spec file labels its source —
  (1) the paper's own reported metrics, (2) the human intent-owner, or (3)
  conductor engineering default. Same spec for every worker: the comparison is
  the data. (Function-vs-quality classification is a judgment call, not
  mechanically decidable — DEFERRED; the step-1 rule stays as discipline.)
- Poller discipline for repeated-marker protocols (MEASURE loops): whole-screen
  greps re-match stale requests in scrollback. Use idle-debounce (state==idle
  x3) THEN grep only the fresh tail (last ~18 lines) for the marker.
- Fixture economy (measure-request protocol): the conductor's measurement
  service has a published per-call cost ceiling; oversized fixtures (long probe
  throws, wasted domain) are DECLINED without consuming the worker's call cap,
  with the envelope stated (probe x-extent, min separation). Workers design
  measurable fixtures; cost of measurement is part of the design constraint.
- Staleness gate (conductor, before EVERY measurement): verify the fixture GDS
  mtime is newer than its .py source and the device source it embeds. A stale
  fixture measures the previous geometry and returns confidently identical
  numbers — void data at full price. Void-by-staleness earns one flagged redo
  at conductor discretion; the redo and the ruling go in the log.
- Model-flag remapping (measured 2026-07-03): `claude --model claude-opus-4-1`
  SILENTLY REMAPS to Opus 4.8 (CLI warns only via /model). Headless -p probes
  answer "ok" under the remapped id — probes do NOT validate identity. The
  status-line readback gate is the ONLY reliable config check; it caught three
  mislabeled panes on its first sweep outing. Generation ladders must be built
  from readback-verified ids only.
