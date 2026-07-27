# Michaelangelo

A self-contained workflow for converting black & white component images to ranked GDS outputs using Gemini AI seed exploration and multi-turn iteration.

## Overview

Michaelangelo implements a **2-phase workflow** that:

1. **Phase 1 (Multi-Turn Seed Exploration)**: Explores multiple seeds in parallel, with each seed going through 2 turns of generation and improvement
2. **Phase 2 (Extended Iteration)**: Takes the best seeds from Phase 1 and continues iterating for 3 more turns

The workflow uses Gemini AI to analyze component images and generate GDSFactory Python scripts that recreate the device geometry.

## Prerequisites

- Python 3.11 or higher
- Gemini API key (get one at https://ai.google.dev/)

## Quick Start

### 1. Set up the environment

```bash
./setup.sh
```

This creates a local virtual environment and installs all dependencies.

### 2. Set your API key

```bash
export GEMINI_API_KEY=your_api_key_here
```

### 3. Run the workflow

```bash
# Run full workflow on the included example component
./run_workflow.sh component8

# Or run individual phases
./run_workflow.sh component8 --phase1-only
./run_workflow.sh component8 --phase2-only
```

## Adding a New Component

1. Create a folder in `components/`:
   ```bash
   mkdir components/my_component
   ```

2. Add your component image (PNG or JPEG):
   ```bash
   cp /path/to/your/image.png components/my_component/component.png
   ```

3. Create a `footprint.json` with the device dimensions in microns:
   ```json
   {
     "footprint_um": [10.0, 5.0]
   }
   ```

4. (Optional) Create custom prompts, or use the defaults from `templates/`:
   - `prompt.md` - Initial generation prompt
   - `iteration_prompt.md` - Iteration feedback prompt

5. Run the workflow:
   ```bash
   ./run_workflow.sh my_component
   ```

## Directory Structure

```
michaelangelo/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── setup.sh                 # Environment setup script
├── run_workflow.sh          # Workflow runner
│
├── core/                    # Core Python scripts
│   ├── calibrate_boundary.py              # Generate calibration from image
│   ├── compare_absolute.py                # Rasterize GDS and compute metrics
│   ├── gemini_multiturn_seed_exploration.py  # Phase 1
│   └── gemini_extended_iteration.py       # Phase 2
│
├── reference/               # GDSFactory function catalogue
│   └── gds_factory_function_catalogue_extended.md
│
├── templates/               # Default prompt templates
│   ├── prompt.md
│   ├── iteration_prompt.md
│   └── footprint_template.json
│
└── components/              # Component folders
    └── component8/          # Example component
        ├── component.png
        ├── footprint.json
        ├── prompt.md
        ├── iteration_prompt.md
        └── results/         # Generated outputs
            ├── multiturn_seeds/
            └── extended_iteration/
```

## Workflow Details

### Phase 1: Multi-Turn Seed Exploration

The first phase tests multiple random seeds (default: 25 seeds around base seed 1333) in parallel. For each seed:

1. **Turn 1**: Generate initial GDS from the target image
2. **Turn 2**: Show the rasterized output to the model, iterate to improve

Key metrics:
- **IoU (Intersection over Union)**: Measures overlap between generated and target
- **Dice coefficient**: Similar to IoU, emphasizes overlap

Output: `results/multiturn_seeds/exploration_summary.json`

### Phase 2: Extended Iteration

Takes seeds that passed the IoU threshold (default: 0%) and continues iterating:

- **Turns 3, 4, 5**: Continue feedback loop with rasterized output
- **Early stopping**: If IoU drops for 2 consecutive turns

Output: `results/extended_iteration/extended_exploration_summary.json`

## Command-Line Options

### run_workflow.sh

```bash
./run_workflow.sh COMPONENT_NAME [OPTIONS]

Options:
  --phase1-only         Run only Phase 1
  --phase2-only         Run only Phase 2
  --base-seed N         Base seed for exploration (default: 1333)
  --seed-range N        Range around base seed (default: 12)
  --num-parallel N      Number of parallel workers (default: 8)
  --model MODEL         Gemini model (default: gemini-3-flash-preview)
  --iou-threshold N     Min IoU for Phase 2 (default: 0.0)
  --additional-turns N  Extra turns in Phase 2 (default: 3)
```

### Running scripts directly

```bash
# Phase 1
python core/gemini_multiturn_seed_exploration.py \
  --component-dir components/my_component \
  --base-seed 1333 \
  --seed-range 12 \
  --num-parallel 8

# Phase 2
python core/gemini_extended_iteration.py \
  --component-dir components/my_component \
  --phase1-dir results/multiturn_seeds \
  --additional-turns 3
```

## Understanding Results

### Metrics

- **IoU (Intersection over Union)**: 0.0 = no overlap, 1.0 = perfect match
- **Dice coefficient**: Similar to IoU, often slightly higher

### Output Files

Each seed directory contains:
- `generated_component.py` - The Python script that generates the GDS
- `*.gds` - The generated GDS file
- `raster.png` - Rasterized version of the GDS
- `diff.png` - Difference visualization (red = false positive, blue = false negative)
- `overlay.png` - GDS overlaid on target
- `metrics.json` - IoU and Dice scores

### Best Results

Check `exploration_summary.json` for rankings:
- `ranked_by_iou` - Seeds ranked by IoU score
- `ranked_by_dice` - Seeds ranked by Dice score
- `best_seed_by_iou` - Single best seed by IoU

## Troubleshooting

### API Key Issues
```bash
# Verify API key is set
echo $GEMINI_API_KEY

# Set it if not
export GEMINI_API_KEY=your_key_here
```

### Missing Dependencies
```bash
# Re-run setup
./setup.sh

# Or manually install
source .venv/bin/activate
pip install -r requirements.txt
```

### No GDS Files Generated
- Check `log.txt` files in turn directories for error messages
- Verify the target image is clear and high-contrast
- Try different seeds with `--base-seed`

## License

This project is part of the Diffusion Photonics research initiative.
