# <img src="./assets/qpai_logo_web.png" height="60" alt="MIT QP-AI"> PixCell

*From Pixels to PCells: A Neurosymbolic Approach to Photonic Component Creation* ([arXiv:XXXX.XXXXX](https://arxiv.org/abs/XXXX.XXXXX))

https://github.com/user-attachments/assets/cfb10bed-8854-48a5-a326-6e8657b4e34a

## Install

```bash
# Claude Code, Codex, or Cursor
npx plugins add QPG-MIT/PixCell

# Claude Code, using its native plugin manager
claude plugin marketplace add QPG-MIT/PixCell && claude plugin install pixcell@pixcell

# Local browser Studio, without cloning the repository
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

Requires Python 3.11-3.13 (3.13 recommended). The core loop uses no API key:
recreation, verification, gating, the workbench, and the Studio light table
all run locally. `GEMINI_API_KEY` is used only to standardize an extracted
paper figure; drawn devices do not need it. `TIDY3D_API_KEY` is used only for
cloud FDTD. See [`.env.example`](.env.example).

## How to use

### Hosted Studio

[Try PixCell in your browser](https://pixcell.qpaig.com/new) with no local
installation. The hosted Studio is currently a trusted beta.

### Agent

Ask for a device and its constraints directly:

> *"Here's a paper. Recreate the ring resonator in figure 3."*
> *"Hit an 8 nm FSR on 400 nm nitride."*
> *"Show me the device. I want to play with the knobs."*

PixCell dispatches the workers and applies the deterministic gate. Successful
runs return the GDS, its parametric source, and the fidelity score.

### Local Studio

```bash
pixcell studio
```

The included [`projects/example_mmi_splitter/`](projects/example_mmi_splitter/)
example opens by default: a drawn 1×4 MMI recreated blind and gate-verified at
IoU 0.995.

### CLI

Each stage is available directly. `homi` and `pixcell` are aliases:

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
