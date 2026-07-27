# PixCell — coding-agent plugin

Turn a photonic device figure (a paper figure, a drawing) into a **verified
parametric GDS program**, inside your own coding agent, in any project.

Your agent recreates the device as a primitives-only parametric GDSFactory
script; a deterministic visual verifier (IoU at calibrated absolute scale)
gates the result; measure-only physics tools retarget it across foundry layer
stacks. The agent is the optimizer — the Python only measures.

PixCell is the system; `homi` is its engine.

## What installs

| Component | Contents |
|---|---|
| **Skills** (8) | `extract`, `generate`, `homi` (full pipeline), `optimize`, `migrate`, `simulate`, `explore` (marimo device workbench, incl. `--draw`), `optimize-to-spec` |
| **Agents** (4) | `extractor`, `synthesizer`, `optimizer`, `pdk-expert` |
| **MCP servers** (7) | `homi-mj` (paper processing), `homi-michaelangelo` (baseline sweep), `homi-raphael` (execute / rasterize-and-compare / calibrate), `homi-jee` (SSE optimization), `homi-weber` (explorer generation), `homi-flex` (Tidy3D FDTD), `homi-pdk` (layer mapping + DRC) |
| **Hooks** (3) | post-GDS metrics reminder, post-optimization DRC reminder, pre-Phase-2 viability check |
| **Engine resolver** | `bin/pixcell-engine` — finds or bootstraps the Python engine every server runs on |

## Install

```
# Claude Code, native marketplace flow (the supported path)
/plugin marketplace add QPG-MIT/PixCell
/plugin install pixcell@pixcell
```

Experimental, not yet release-tested end to end:

```
# Vendor-neutral npx-plugins hosts (Cursor and friends)
npx plugins add QPG-MIT/PixCell

# Codex marketplace flow
codex plugin marketplace add QPG-MIT/PixCell
codex plugin add pixcell@pixcell
```

## First run: the engine bootstrap

The plugin ships prompts and server declarations, not a 3 GB Python stack.
Every MCP server entry runs through `bin/pixcell-engine`, which resolves the
engine in order:

1. `$PIXCELL_PYTHON` (explicit interpreter override)
2. the nearest `.venv` above the working directory that can `import homi`
   (the PixCell repo-checkout case)
3. the cached engine at `${CLAUDE_PLUGIN_DATA:-~/.pixcell}/venv`
4. otherwise it **bootstraps** (3): `uv` if available, else `python3.13 -m venv`
   + pip, installing `pixcell` from GitHub.

The first MCP start on a machine with no engine takes **minutes** (the
gdsfactory stack is large); every later start is instant. Progress streams to
stderr; nothing touches stdout (that belongs to the MCP protocol).

## Environment keys

The core is **keyless**: the recreate loop, the IoU gate/verifier, tier-0
physics, DRC/PDK migration, and the marimo workbench need no API key.

| Key | Needed only for |
|---|---|
| `GEMINI_API_KEY` | `extract` — B&W raster generation (the one surviving API call) and the `--baseline` multi-seed sweep |
| `TIDY3D_API_KEY` | `simulate` — Tidy3D FDTD upload. Uploads create a **draft**; the human presses Start. Cloud spend never auto-starts. |

## Layout

```
plugins/pixcell/
├── .claude-plugin/plugin.json   # Claude Code manifest
├── .plugin/plugin.json          # Open Plugin Spec manifest (vendor-neutral)
├── skills/                      # the 8 product skills
├── agents/                      # the 4 specialist agents
├── .mcp.json                    # 7 servers, all via bin/pixcell-engine
└── bin/pixcell-engine           # engine resolver/bootstrapper (POSIX sh)
```

Source of truth: this directory. The repo's `.claude/skills/` entries for these
skills are symlinks into it, so opening the PixCell repo in a coding agent loads
the identical text.
