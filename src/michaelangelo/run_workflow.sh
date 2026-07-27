#!/bin/bash
# run_workflow.sh - Run the full 2-phase component-to-GDS workflow
#
# Usage: ./run_workflow.sh COMPONENT_NAME [OPTIONS]
#
# Arguments:
#   COMPONENT_NAME    Name of the component folder in components/
#
# Options:
#   --phase1-only     Run only Phase 1 (multi-turn seed exploration)
#   --phase2-only     Run only Phase 2 (extended iteration)
#   --base-seed N     Base seed for exploration (default: 1333)
#   --seed-range N    Range around base seed (default: 12)
#   --num-parallel N  Number of parallel workers (default: 8)
#   --model MODEL     Gemini model to use (default: gemini-3-flash-preview)
#
# Example:
#   ./run_workflow.sh component8
#   ./run_workflow.sh component8 --phase1-only --base-seed 1500
#

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default values
COMPONENT=""
PHASE1_ONLY=false
PHASE2_ONLY=false
BASE_SEED=1333
SEED_RANGE=12
NUM_PARALLEL=8
MODEL="gemini-3-flash-preview"
IOU_THRESHOLD=0.0
ADDITIONAL_TURNS=3

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --phase1-only)
            PHASE1_ONLY=true
            shift
            ;;
        --phase2-only)
            PHASE2_ONLY=true
            shift
            ;;
        --base-seed)
            BASE_SEED="$2"
            shift 2
            ;;
        --seed-range)
            SEED_RANGE="$2"
            shift 2
            ;;
        --num-parallel)
            NUM_PARALLEL="$2"
            shift 2
            ;;
        --model)
            MODEL="$2"
            shift 2
            ;;
        --iou-threshold)
            IOU_THRESHOLD="$2"
            shift 2
            ;;
        --additional-turns)
            ADDITIONAL_TURNS="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            if [ -z "$COMPONENT" ]; then
                COMPONENT="$1"
            fi
            shift
            ;;
    esac
done

# Validate component name
if [ -z "$COMPONENT" ]; then
    echo "Usage: ./run_workflow.sh COMPONENT_NAME [OPTIONS]"
    echo ""
    echo "Available components:"
    ls -1 components/ 2>/dev/null || echo "  (none found)"
    echo ""
    echo "Options:"
    echo "  --phase1-only       Run only Phase 1"
    echo "  --phase2-only       Run only Phase 2"
    echo "  --base-seed N       Base seed (default: 1333)"
    echo "  --seed-range N      Seed range (default: 12)"
    echo "  --num-parallel N    Parallel workers (default: 8)"
    echo "  --model MODEL       Gemini model (default: gemini-3-flash-preview)"
    exit 1
fi

COMP_DIR="components/$COMPONENT"

if [ ! -d "$COMP_DIR" ]; then
    echo "ERROR: Component directory not found: $COMP_DIR"
    echo ""
    echo "Available components:"
    ls -1 components/ 2>/dev/null || echo "  (none found)"
    exit 1
fi

# Check for required files
if [ ! -f "$COMP_DIR/component.png" ] && [ ! -f "$COMP_DIR/component.jpeg" ]; then
    echo "ERROR: No component image found in $COMP_DIR"
    echo "Expected: component.png or component.jpeg"
    exit 1
fi

if [ ! -f "$COMP_DIR/footprint.json" ]; then
    echo "ERROR: footprint.json not found in $COMP_DIR"
    exit 1
fi

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    echo "ERROR: GEMINI_API_KEY environment variable not set"
    echo ""
    echo "Please set it with:"
    echo "  export GEMINI_API_KEY=your_api_key_here"
    exit 1
fi

# Activate virtual environment if not already active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -f ".venv/bin/activate" ]; then
        echo "Activating virtual environment..."
        source .venv/bin/activate
    else
        echo "ERROR: Virtual environment not found. Run ./setup.sh first."
        exit 1
    fi
fi

echo "=========================================="
echo "Michaelangelo Workflow"
echo "=========================================="
echo "Component: $COMPONENT"
echo "Model: $MODEL"
echo "Base Seed: $BASE_SEED"
echo "Seed Range: +/- $SEED_RANGE"
echo "Parallel Workers: $NUM_PARALLEL"
echo "=========================================="
echo ""

# Create results directory
mkdir -p "$COMP_DIR/results"

# Determine which target image to use
if [ -f "$COMP_DIR/component.png" ]; then
    TARGET_IMAGE="component.png"
else
    TARGET_IMAGE="component.jpeg"
fi

# ============================================
# PHASE 1: Multi-Turn Seed Exploration
# ============================================
if [ "$PHASE2_ONLY" = false ]; then
    echo ""
    echo "=========================================="
    echo "PHASE 1: Multi-Turn Seed Exploration"
    echo "=========================================="
    echo ""

    python core/gemini_multiturn_seed_exploration.py \
        --component-dir "$COMP_DIR" \
        --target-image "$TARGET_IMAGE" \
        --output-dir "results/multiturn_seeds" \
        --base-seed "$BASE_SEED" \
        --seed-range "$SEED_RANGE" \
        --num-parallel "$NUM_PARALLEL" \
        --model "$MODEL"

    echo ""
    echo "Phase 1 complete! Results saved to: $COMP_DIR/results/multiturn_seeds/"
fi

# ============================================
# PHASE 2: Extended Iteration
# ============================================
if [ "$PHASE1_ONLY" = false ]; then
    # Check if Phase 1 results exist
    PHASE1_SUMMARY="$COMP_DIR/results/multiturn_seeds/exploration_summary.json"
    if [ ! -f "$PHASE1_SUMMARY" ]; then
        echo ""
        echo "ERROR: Phase 1 results not found: $PHASE1_SUMMARY"
        echo "Run Phase 1 first or use --phase2-only with existing Phase 1 results."
        exit 1
    fi

    echo ""
    echo "=========================================="
    echo "PHASE 2: Extended Iteration"
    echo "=========================================="
    echo ""

    python core/gemini_extended_iteration.py \
        --component-dir "$COMP_DIR" \
        --phase1-dir "results/multiturn_seeds" \
        --output-dir "results/extended_iteration" \
        --target-image "$TARGET_IMAGE" \
        --iou-threshold "$IOU_THRESHOLD" \
        --additional-turns "$ADDITIONAL_TURNS" \
        --num-parallel "$NUM_PARALLEL" \
        --model "$MODEL"

    echo ""
    echo "Phase 2 complete! Results saved to: $COMP_DIR/results/extended_iteration/"
fi

echo ""
echo "=========================================="
echo "Workflow Complete!"
echo "=========================================="
echo ""
echo "Results location: $COMP_DIR/results/"
echo ""
echo "Key outputs:"
if [ "$PHASE2_ONLY" = false ]; then
    echo "  Phase 1 summary: $COMP_DIR/results/multiturn_seeds/exploration_summary.json"
fi
if [ "$PHASE1_ONLY" = false ]; then
    echo "  Phase 2 summary: $COMP_DIR/results/extended_iteration/extended_exploration_summary.json"
fi
echo ""
