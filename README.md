# <img src="./assets/qpai_logo_web.png" height="60" alt="MIT QP-AI"> PixCell

**From any visual input - a drawing, a canvas sketch, a paper figure - create
a parametric GDS you can simulate and map to the PDK stack of your choice.**

📄 *From Pixels to PCells: A Neurosymbolic Approach to Photonic Component Creation* ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX))

## Install

```bash
npx plugins add QPG-MIT/PixCell
```

Single install for Claude Code, Codex, or Cursor users: skills,
subagents, and the 7 MCP servers land in your agent, and the Python engine
bootstraps itself on first use (no clone, no venv, no setup; the first run
takes a few minutes, later runs are instant). Claude Code native equivalent:
`claude plugin marketplace add QPG-MIT/PixCell && claude plugin install pixcell@pixcell`.

**No coding agent?** Run the studio in your browser from one line:

```bash
uvx --from 'pixcell[workbench] @ git+https://github.com/QPG-MIT/PixCell' pixcell studio
```

**Reproducing the paper, or developing?** Clone the repo; it carries the
locked environment, briefs, fixtures, benchmark record, and tests:

```bash
# no uv yet?  curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/QPG-MIT/PixCell && cd PixCell
uv sync                        # or ./setup.sh (macOS + Linux)
uv run pixcell doctor          # preflight: what can run here, what to add
```

Needs Python 3.11-3.13 (3.13 recommended). **The core loop uses no API key**
(recreation, verifier, gate, workbench, studio light table). Two optional
keys: `GEMINI_API_KEY`, used only when extracting from a paper figure (the
final black-and-white standardization step; drawn devices skip it entirely),
and `TIDY3D_API_KEY` for cloud FDTD. See [`.env.example`](.env.example).

## Use it

**1. Talk to your agent** (plugin install, or a coding agent opened in the
clone). It's natural language end to end:

> *"Here's a paper. Recreate the ring resonator in figure 3."*
> *"Hit an 8 nm FSR on 400 nm nitride."*
> *"Show me the device. I want to play with the knobs."*

Workers are dispatched, verified, and gated automatically; you get back a
GDS, its parametric source, and the fidelity score.

**2. The studio**, a chat conductor beside a live light table, in the browser:

```bash
pixcell studio
```

In a clone it opens onto a worked example
([`projects/example_mmi_splitter/`](projects/example_mmi_splitter/), a drawn
1×4 MMI recreated blind and gate-verified at IoU 0.995), so the knobs and
live fidelity are inspectable before you run anything.

**3. The CLI**, scriptable per-stage entry points (`homi` and `pixcell` are
the same command):

```bash
pixcell extract paper.pdf -o projects/my_device    # figure → silhouette + footprint
pixcell generate projects/my_device                # blind agent recreation + gate
pixcell retarget device.py --stack sin400.json --spec spec.json
pixcell explore  projects/my_device/output/best.py --launch   # per-device workbench
pixcell simulate projects/my_device/output/best.gds  # FDTD draft; a human presses Start
pixcell serve                                      # the 7 MCP servers · `pixcell api` for REST
```

## Going deeper

- Architecture, the conductor/gate protocol, and the package map: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and [`docs/agents/`](docs/agents/)
- The released measurement record (campaigns, benchmark, RL study): [`data/README.md`](data/README.md)
- Paper source and figure generators: [`paper/`](paper/)

## Tests

```bash
uv run pytest tests/ -q
```

## License

[MIT](LICENSE).
