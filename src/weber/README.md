# Weber: GDSFactory Interactive Explorer Generator

Weber takes any GDSFactory Python script and automatically generates a full-featured interactive explorer with:

1. **Parameterization** - All numeric values exposed as sliders
2. **Decomposition** - Logical parts as swappable component slots
3. **Layer Assignment** - Configurable GDS layer assignments
4. **Tidy3D Integration** - Optional FDTD simulation upload

## Quick Start

```bash
# Setup
./setup.sh

# Activate environment
source venv/bin/activate

# Generate an explorer (with AI analysis)
python run.py scripts/your_device.py

# Generate an explorer (without AI, using smart defaults)
python run.py scripts/your_device.py --skip-agent

# Run the generated explorer
streamlit run output/your_device_explorer/app.py
```

## How It Works

Weber processes your GDSFactory script through three stages:

### Stage 1: Analyzer (Automated)
- Parses Python AST
- Extracts `gf.components.*` calls
- Identifies numeric parameters
- Detects layer assignments
- Builds component dependency graph

### Stage 2: Slot Agent (AI-powered or Smart Defaults)
- Groups components into logical "slots"
- Determines swappable alternatives
- Suggests layer groupings
- Identifies global parameters

### Stage 3: Generator (Automated)
- Generates `slot_definitions.py`
- Generates `device_builder.py` (parameterized)
- Generates `app.py` (Streamlit explorer)
- Copies required templates

## Usage

```bash
# Full AI-powered analysis (requires ANTHROPIC_API_KEY)
python run.py scripts/my_device.py

# Skip AI agent, use smart defaults (still has full functionality)
python run.py scripts/my_device.py --skip-agent

# Include Tidy3D simulation panel
python run.py scripts/my_device.py --tidy3d

# Custom output directory
python run.py scripts/my_device.py -o my_explorer/

# Provide API key directly
python run.py scripts/my_device.py --api-key sk-...

# Don't use cached agent responses
python run.py scripts/my_device.py --no-cache
```

## Configuration

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API key for slot agent |
| `TIDY3D_API_KEY` | Tidy3D API key for simulation upload |

### Swappable Component Types

Weber automatically detects and enables swapping between compatible types:

| Category | Swappable Types |
|----------|-----------------|
| Basic Shapes | `rectangle` ↔ `circle` ↔ `ellipse` ↔ `triangle` |
| Bends | `bend_circular` ↔ `bend_euler` ↔ `bend_s` |
| Waveguides | `straight` ↔ `taper` |

## Directory Structure

```
Weber/
├── run.py              # CLI entry point
├── core/
│   ├── analyzer.py     # AST parsing
│   ├── slot_agent.py   # Claude API agent
│   ├── default_slots.py # Smart defaults
│   ├── generator.py    # Explorer generation
│   └── config.py       # Configuration
├── templates/          # Reusable components
├── scripts/            # Place input scripts here
├── output/             # Generated explorers
└── examples/           # Example scripts
```

## Examples

See the `examples/` directory for sample GDSFactory scripts:

- `seed_1343_device.py` - Racetrack ring with internal MZI
- `seed_1337_device.py` - Heater structure variant
- `trident_mode_converter.py` - Trident taper/splitter

## Generated Explorer Features

Each generated explorer includes:

- **Parameter Sliders** - Adjust all geometric values in real-time
- **Component Swapping** - Switch between compatible component types
- **Layer Assignment** - Assign components to different GDS layers
- **Live Preview** - See changes immediately with polygon visualization
- **Size Comparison** - Compare against target footprint
- **GDS Export** - Download the configured design
- **Tidy3D Upload** (optional) - Upload to Tidy3D for FDTD simulation

## License

MIT License
