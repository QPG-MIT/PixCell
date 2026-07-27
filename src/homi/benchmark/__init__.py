"""
HOMI Benchmark Module

Provides benchmark data and aggregation utilities for the HOMI paper.
"""

from .data import (
    MODELS_MAIN,
    TURN1_IOU,
    BEST_IOU,
    BEST_TURN,
    MODELS_GALLERY,
    PRIMITIVE_RATES,
    MEAN_IOUS,
    get_expected_usable,
    get_benchmark_data,
    get_gallery_data,
    simulate_tts_trajectories,
)
from .statistics import (
    calculate_iou,
    calculate_sse,
    calculate_dice,
    calculate_metrics,
    IOU_FORMULA,
    SSE_FORMULA,
    DICE_FORMULA,
)

__all__ = [
    "MODELS_MAIN",
    "TURN1_IOU",
    "BEST_IOU",
    "BEST_TURN",
    "MODELS_GALLERY",
    "PRIMITIVE_RATES",
    "MEAN_IOUS",
    "get_expected_usable",
    "get_benchmark_data",
    "get_gallery_data",
    "simulate_tts_trajectories",
    "calculate_iou",
    "calculate_sse",
    "calculate_dice",
    "calculate_metrics",
    "IOU_FORMULA",
    "SSE_FORMULA",
    "DICE_FORMULA",
]
