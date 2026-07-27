# AGENTS.md — working in PixCell as a coding agent

The repository briefing for both vendors' CLIs: `CLAUDE.md` imports this file,
so Claude Code and Codex read the same instructions — the repo binds to
whichever coding agent you open in it, and the paper's measurements were made
with both. Skill playbooks in `.claude/skills/*/SKILL.md` are plain markdown;
read one directly when a task matches it.

## What is this repo?

**PixCell** (the paper: *From Pixels to PCells*) / **HOMI** (the Python package):
a neurosymbolic system in which multimodal coding agents convert a visually
presented photonic component (a paper figure, a drawing) into a **parametric
program** over a small catalog of geometric primitives, verified by a
deterministic visual metric (IoU at calibrated absolute scale), then retargeted
across foundry layer stacks through a measure-only tiered physics evaluator.

The governing invariant everywhere: **the agent is the optimizer; the Python
only measures — it never searches.** And its corollary: **no worker-reported
number enters the record** — acceptance is always the deterministic conductor
gate over artifacts (`homi.conductor.verify_cell`).

## Commands

```bash
uv sync                                                # or ./setup.sh
uv run pixcell doctor                                  # preflight: backend, keys, pins
uv run pixcell studio                                  # chat-first front door: conductor + light table
uv run pixcell extract paper.pdf -o projects/ring_resonator     # dispatches the extractor agent
uv run pixcell generate projects/ring_resonator                 # Phase-A agent recreate loop (default)
uv run pixcell generate projects/ring_resonator --baseline --preset balanced   # legacy multi-seed sweep
uv run pixcell retarget device.py --stack sin400.json --spec spec_sin400.json  # Phase B
uv run pixcell optimize projects/ring_resonator/output/best.py --method nelder-mead
uv run pixcell explore projects/ring_resonator/output/best.py --launch
uv run pixcell simulate projects/ring_resonator/output/best.gds
uv run pixcell benchmark --papers final_1 final_2 --families gemini claude
uv run pixcell serve                 # all 7 MCP servers · `pixcell api` = REST, localhost-only by default
uv run pixcell migrate device.gds --target-pdk generic_si220

uv run pytest tests/ rl/ release/ -q                   # the CI surface
uv run ruff check .
```

`pixcell` and `homi` are the same command; inside an activated environment,
drop the `uv run` prefix.

## Architecture — two planes

```
CONTROL PLANE (who runs the loop)                TOOL PLANE (what measures)
CLI / web / REST / chat-pane ──▶ homi.dispatch.dispatch_agent(stage, brief, workdir)
                                   │ backends: a tmux worker pane (Claude or
                                   │ Codex CLI), with headless claude -p /
                                   ▼ codex exec fallback
                        worker agent ◀────▶ MCP servers + python -m modules (measure-only)
                                   │
                                   ▼
                        homi.conductor gate over ARTIFACTS
                        (recompute IoU · primitives purity · knob response)
```

All packages live under `src/` (installed editable; import by top-level name):

| Package | Purpose |
|---------|---------|
| `src/homi/` | Integration hub — every surface (CLI `homi.cli`, REST `homi.api`, studio `homi.studio_app`, MCP) calls into here |
| `src/homi/briefs/` | **Worker prompts as package data — the single source.** `homi.briefs.render(name, **vars)`; `{{VAR}}` templating; phase briefs are hint-lint-clean by CI |
| `src/homi/dispatch.py` | The control plane: `dispatch_agent`, `STAGES`, `open_pane_session`; success = expected artifacts exist, never a send/exit status |
| `src/homi/conductor/` | The conductor protocol as code: `gate` (verify_cell), `hint_lint`, `readback` (anti silent model remap), `measure` (MEASURE handshake + CapLedger + service_loop), `tier1` (capped FDTD harness), `metrics` (campaign builders) |
| `src/gg/servers/` | 7 MCP servers (thin wrappers over homi integration modules) |
| `src/michaelangelo/core/` | The visual verifier (`compare_absolute`: IoU/Dice/SSE at calibrated absolute scale) + the legacy multi-seed engine (baseline) |
| `src/jee/core/` | Classical parameter optimization (SSE minimization) — the bilevel inner loop the agent drives |
| `src/weber/core/` | Parameter analysis for the workbench and optimizer |
| `src/flex/core/` | Tidy3D FDTD integration (tiered; cloud is human-gated) |
| `src/benchmarking/` | Chatbot-style benchmark harness (`homi-benchmark`) |

**Key principle**: business logic lives in `homi/`; MCP servers (`src/gg/servers/`)
and agent/skill definitions (`.claude/`) are thin binders. A brief is a payload
*sent to* a worker; a SKILL.md is instructions *for the running agent* — the
procedural text lives once, in `homi.briefs`.

### Pipeline stages (agent-first)

| Stage | Default behavior |
|-------|------------------|
| `extract` | Dispatched extractor agent, keyless perception (agent's own eyes + dumb render/crop tools); only surviving API call is B&W raster generation |
| `generate` | Dispatched Phase-A recreate worker (primitives-only parametric script, ≤6 IoU iterations) + conductor gate; `--baseline` = Michaelangelo multi-seed (the paper's measured chatbot-era baseline) |
| `retarget` | Dispatched Phase-B worker; tier-0 solves locally, tier-1 FDTD only through the conductor-serviced MEASURE loop under per-stack caps |
| `optimize` | JEE SSE minimization — classical inner-loop tool the agent drives |
| `simulate` | Tidy3D upload creates a DRAFT + workbench link; **the human presses Start** (never auto-start cloud spend) |
| `explore` / `migrate` | Deterministic tools (weber explorer generation; PDK layer mapping + DRC) |

### MCP Servers (7, registered in .mcp.json)

`homi-mj` (paper processing, keyless), `homi-michaelangelo`, `homi-raphael`
(orchestrator-driven GDS: execute / rasterize-and-compare / calibrate),
`homi-jee`, `homi-weber`, `homi-flex`, `homi-pdk`.
Run individually: `python -m gg.servers.mj_server`, or the console scripts
(`homi-mj`, `homi-michaelangelo`, …) that `.mcp.json` binds.

## Critical Gotchas

### Reference code by module, never by file path
`python -m michaelangelo.core.compare_absolute`, `Path(michaelangelo.__file__).parent`
(`homi.paths.michaelangelo_dir()`). File-path references (`michaelangelo/core/...`)
broke in the src/ move; module references survived. This rule is why.

### GDSFactory pinned to 9.20.7
Version 9.3x+ has breaking API changes requiring explicit PDK activation. AI models
cannot reliably handle this, causing generation failures. Do not upgrade.

### jee/weber `core` clash — resolved structurally, do not reintroduce
Both `jee/core/` and `weber/core/` exist; the historical bare-`core` import clash
was fixed by the src/ package layout + absolute imports (`from jee.core import`,
`from weber.core import`). The old `sys.modules` surgery is gone. Regression test:
`tests/test_core_import_order.py`. Never import a bare `core`.

### Python 3.11-3.13
`requires-python = ">=3.11,<3.14"` in pyproject.toml (3.13 recommended).

### Model name format
Pipeline VLM configs use `"provider/model-name"` (e.g. `"gemini/gemini-3-flash-preview"`).
Worker CLI configs are aliases + model ids (the shipped default is `--cli cdxx`, a full-auto Codex worker)
— and launch flags can silently remap models: trust only the status-line readback
(`homi.conductor.verify_readback`).

## Generation Presets (--baseline mode only)

| Preset | Seeds | Turns | Use Case |
|--------|-------|-------|----------|
| quick | 5 | 2 | Fast iteration |
| balanced | 13 | 3 | Default |
| thorough | 25 | 5 | Higher quality |
| maximum | 41 | 8 | Best results |

## Project Directory Structure

```
projects/{name}/
├── paper.pdf           # Source paper
├── device_bw.png       # Extracted B&W device image
├── footprint.json      # Device dimensions in μm
├── component/          # (--baseline) calibration + phase1/ + phase2/
└── output/
    ├── recreation_agent/   # Phase-A worker workdir (device.py, component.png, calibration.json, *.gds)
    ├── best.gds        # Final GDS (gate-verified in agent mode)
    └── best.py         # GDSFactory script
```

## Data layout (the released dataset + benchmark)

```
data/
├── agents/             # models as blind coding agents
│   ├── paper_swap/     # the 104-cell emergence matrix (RUNBOOK.md = experiment spine)
│   ├── catalog_swap/   # primitives-vs-stencil ladder
│   └── pdk_swap/       # MZI one-drawing→three-fabs proof
├── benchmark/          # the 8 device input fixtures + their source panels
└── chatbots/           # models as API chatbots: analysis, aggregates, trajectories
```

Narrative + file map: `docs/agent_integration.md` and `data/README.md` (the
card mapping every published number to its artifact). The protocol's living
pieces are code: briefs in `homi.briefs`, conductor tooling in
`homi.conductor`, skills in `plugins/pixcell/skills/` (symlinked into
`.claude/`, so a clone and a plugin install expose the same skills).

## Metrics

- **IoU / Dice**: `michaelangelo.core.compare_absolute` (the Phase-A verifier);
  recompute via `homi.conductor.recompute_metrics` — do not reimplement.
- **SSE**: overloaded across three modules (raw-pixel vs binarized differ ~65,025×);
  JEE's cost function is `jee.core.compute_sse`.
- **Tier-0 physics**: `python -m homi.spec_optimization` (eval / solve / supermodes /
  multimode / cross-section) — measure-only, never searches.

## Environment Variables

`.env` is optional — the core loop (recreation, verification, gating, the
workbench) is keyless. Keys unlock specific stages:
```
GEMINI_API_KEY=...        # Only to standardize an extracted paper figure + baseline mode
ANTHROPIC_API_KEY=...     # For Claude models (baseline/benchmark)
OPENAI_API_KEY=...        # For GPT models (baseline/benchmark)
OPENROUTER_API_KEY=...    # For Llama/Kimi/Qwen via OpenRouter
TIDY3D_API_KEY=...        # For FDTD simulation
```

## Test Markers

Defined in `pyproject.toml`:
- `reproducibility` — Reproducibility requirements
- `photonics_physics` — Physics validation
- `critic_generated` — Auto-generated by critic agents during code review
- `ml_methodology` — ML/AI methodology standards
- `deception` — Tests detecting mock/fake implementations
- `paper_code_consistency` — Paper claims match code

## Benchmarking

```bash
homi benchmark --papers final_1 final_2 --families gemini claude --phase1-seeds 15
homi benchmark --aggregate benchmark_results/2026-01-23_031555  # Aggregate only
```

Benchmark code: `src/benchmarking/` (cli, runner, reporter, aggregator,
per-provider modules; module name `benchmarking`).
Results land in `benchmark_results/{timestamp}/{component}/{provider}/`.

## Model Client Usage

```python
from homi.model_client import create_client, ModelConfig, VisionMessage

client, model_id = create_client("gemini/gemini-3-flash-preview")
response = client.generate(
    messages=[VisionMessage(role="user", text="Describe this device", images=[img_bytes])],
    config=ModelConfig(temperature=1.0, thinking_mode="high"),
    model_id=model_id
)
```

Backends are lazy-imported — only the SDK for the requested provider needs to be installed.

## The rest of the tree

`data/` is the measured record behind the paper (frozen — nothing writes into
it at runtime; `data/README.md` is the card), `arxiv/` the paper source,
`dataset/` the released image-to-code curriculum, `rl/` the training recipe
over it, `release/` the guarded Hugging Face publishing machinery, and
`plugins/pixcell/` the installable plugin.
