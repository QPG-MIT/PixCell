"""
HOMI Configuration Module

Provides default configuration values and constants for the HOMI system.
"""

from typing import Dict, Any


# Timing Constants (from paper benchmarks)
GENERATION_TIME_SECONDS = 388
VERIFICATION_TIME_SECONDS = 0.18
ASYMMETRY_RATIO = 2156

# TTS Simulation Defaults
DEFAULT_NUM_SEEDS = 15
DEFAULT_NUM_TURNS = 5
DEFAULT_BASE_IOU = 0.25
DEFAULT_RANDOM_SEED = 42

# Slider Ranges
SLIDER_SEEDS_MIN = 1
SLIDER_SEEDS_MAX = 25
SLIDER_TURNS_MIN = 1
SLIDER_TURNS_MAX = 10
SLIDER_BASE_IOU_MIN = 0.1
SLIDER_BASE_IOU_MAX = 0.5
SLIDER_BASE_IOU_STEP = 0.05


def get_tts_defaults() -> Dict[str, Any]:
    """Get default TTS simulation parameters."""
    return {
        "num_seeds": DEFAULT_NUM_SEEDS,
        "num_turns": DEFAULT_NUM_TURNS,
        "base_iou": DEFAULT_BASE_IOU,
        "random_seed": DEFAULT_RANDOM_SEED,
    }


def get_slider_config() -> Dict[str, Dict[str, float]]:
    """Get slider configuration parameters."""
    return {
        "seeds": {
            "min": SLIDER_SEEDS_MIN,
            "max": SLIDER_SEEDS_MAX,
            "default": DEFAULT_NUM_SEEDS,
        },
        "turns": {
            "min": SLIDER_TURNS_MIN,
            "max": SLIDER_TURNS_MAX,
            "default": DEFAULT_NUM_TURNS,
        },
        "base_iou": {
            "min": SLIDER_BASE_IOU_MIN,
            "max": SLIDER_BASE_IOU_MAX,
            "step": SLIDER_BASE_IOU_STEP,
            "default": DEFAULT_BASE_IOU,
        },
    }


def create_slider(mo, slider_type: str, label: str = None):
    """
    Factory function to create sliders with consistent configuration.

    Args:
        mo: Marimo module
        slider_type: Type of slider ('seeds', 'turns', 'base_iou', 'scale', 'threshold')
        label: Optional custom label

    Returns:
        Configured mo.ui.slider instance
    """
    config = get_slider_config()

    # Additional slider configs for other use cases
    additional_configs = {
        "scale": {"min": 0.1, "max": 10.0, "step": 0.1, "default": 1.0},
        "threshold": {"min": 50, "max": 250, "step": 10, "default": 200},
    }

    all_configs = {**config, **additional_configs}

    if slider_type not in all_configs:
        raise ValueError(f"Unknown slider type: {slider_type}")

    cfg = all_configs[slider_type]

    default_labels = {
        "seeds": "Number of seeds",
        "turns": "Turns per seed",
        "base_iou": "Base IoU (Turn 1)",
        "scale": "Scale (μm/px)",
        "threshold": "Binary threshold",
    }

    return mo.ui.slider(
        start=cfg["min"],
        stop=cfg["max"],
        step=cfg.get("step", 1),
        value=cfg["default"],
        label=label or default_labels.get(slider_type, slider_type)
    )
