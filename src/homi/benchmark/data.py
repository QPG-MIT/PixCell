"""
HOMI Benchmark Data

Contains benchmark data from the HOMI paper for visualization and analysis.
"""

from typing import List, Dict, Any
import numpy as np

# Main benchmark data (Table 1 in paper)
MODELS_MAIN: List[str] = [
    'Gemini 3\nFlash',
    'GPT-5.2\nPro',
    'Gemini 2.5\nFlash',
    'GPT-5.2',
    'GPT-5',
    'Claude\nOpus 4.5'
]

TURN1_IOU: List[float] = [0.33, 0.28, 0.52, 0.56, 0.36, 0.36]
BEST_IOU: List[float] = [0.62, 0.56, 0.54, 0.56, 0.50, 0.50]
BEST_TURN: List[int] = [2, 5, 4, 1, 4, 3]

# Gallery benchmark data (Figure X in paper)
MODELS_GALLERY: List[str] = [
    'Gemini-3\nPro',
    'Gemini-3\nFlash',
    'Grok-4',
    'Gemini-2.5\nFlash',
    'Gemini-2.5\nPro',
    'Qwen-VL',
    'Claude\nOpus 4.5',
    'Gemini-2.0\nFlash'
]

PRIMITIVE_RATES: List[float] = [85.2, 67.2, 55.1, 55.9, 54.5, 48.8, 27.1, 30.2]
MEAN_IOUS: List[float] = [0.415, 0.411, 0.337, 0.305, 0.194, 0.167, 0.258, 0.208]


def get_expected_usable(
    primitive_rates: List[float] = None,
    mean_ious: List[float] = None
) -> List[float]:
    """
    Calculate expected usable IoU from primitive rates and mean IoUs.
    
    Args:
        primitive_rates: List of primitive detection rates (%)
        mean_ious: List of mean IoU values
        
    Returns:
        List of expected usable IoU values
    """
    if primitive_rates is None:
        primitive_rates = PRIMITIVE_RATES
    if mean_ious is None:
        mean_ious = MEAN_IOUS
    
    return [r * i / 100 for r, i in zip(primitive_rates, mean_ious)]


def get_benchmark_data() -> Dict[str, Any]:
    """
    Get main benchmark data as a dictionary.
    
    Returns:
        Dict with models, turn1_iou, best_iou, best_turn
    """
    return {
        "models": MODELS_MAIN,
        "turn1_iou": TURN1_IOU,
        "best_iou": BEST_IOU,
        "best_turn": BEST_TURN,
    }


def get_gallery_data() -> Dict[str, Any]:
    """
    Get gallery benchmark data as a dictionary.

    Returns:
        Dict with models, primitive_rates, mean_ious, expected_usable
    """
    return {
        "models": MODELS_GALLERY,
        "primitive_rates": PRIMITIVE_RATES,
        "mean_ious": MEAN_IOUS,
        "expected_usable": get_expected_usable(),
    }


def simulate_tts_trajectories(
    num_seeds: int = 15,
    num_turns: int = 5,
    base_iou: float = 0.25,
    seed: int = 42
) -> Dict[str, Any]:
    """
    Simulate test-time scaling IoU trajectories.

    Args:
        num_seeds: Number of seeds to simulate
        num_turns: Number of turns per seed
        base_iou: Base IoU at turn 1
        seed: Random seed for reproducibility

    Returns:
        Dict with trajectories, best_at_t, mean_at_t, final_ious
    """
    np.random.seed(seed)
    trajectories = []

    for _ in range(num_seeds):
        trajectory = [base_iou + np.random.normal(0, 0.08)]
        for _ in range(1, num_turns):
            improvement = np.random.exponential(0.03)
            noise = np.random.normal(0, 0.02)
            new_iou = min(0.85, trajectory[-1] + improvement + noise)
            trajectory.append(max(trajectory[-1], new_iou))
        trajectories.append(trajectory)

    trajectories_arr = np.array(trajectories)

    return {
        "trajectories": trajectories_arr,
        "best_at_t": np.max(trajectories_arr, axis=0),
        "mean_at_t": np.mean(trajectories_arr, axis=0),
        "final_ious": trajectories_arr[:, -1],
        "num_seeds": num_seeds,
        "num_turns": num_turns,
    }
