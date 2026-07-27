"""
HOMI Benchmark Statistics Module

Provides statistical functions and metric calculations for IoU/SSE benchmarks,
plus hypothesis testing for capability emergence analysis.
"""

import json
from typing import List, Tuple

import numpy as np
import pandas as pd


def calculate_iou(ground_truth: np.ndarray, prediction: np.ndarray) -> float:
    """
    Calculate Intersection over Union (IoU) between two binary masks.

    $$\\text{IoU} = \\frac{|G \\cap \\hat{G}|}{|G \\cup \\hat{G}|}$$

    Args:
        ground_truth: Binary mask of ground truth (numpy array)
        prediction: Binary mask of prediction (numpy array)

    Returns:
        IoU value in range [0, 1]
    """
    intersection = np.logical_and(ground_truth, prediction).sum()
    union = np.logical_or(ground_truth, prediction).sum()

    if union == 0:
        return 1.0 if intersection == 0 else 0.0

    return float(intersection / union)


def calculate_sse(ground_truth: np.ndarray, prediction: np.ndarray) -> float:
    """
    Calculate Sum of Squared Errors (SSE) between two arrays.

    $$\\text{SSE} = \\sum_{i,j} (I[i,j] - \\hat{I}(P)[i,j])^2$$

    Args:
        ground_truth: Ground truth values (numpy array)
        prediction: Predicted values (numpy array)

    Returns:
        SSE value (lower is better)
    """
    diff = ground_truth.astype(float) - prediction.astype(float)
    return float(np.sum(diff ** 2))


def calculate_dice(ground_truth: np.ndarray, prediction: np.ndarray) -> float:
    """
    Calculate Dice coefficient between two binary masks.

    $$\\text{Dice} = \\frac{2|G \\cap \\hat{G}|}{|G| + |\\hat{G}|}$$

    Args:
        ground_truth: Binary mask of ground truth
        prediction: Binary mask of prediction

    Returns:
        Dice coefficient in range [0, 1]
    """
    intersection = np.logical_and(ground_truth, prediction).sum()
    total = ground_truth.sum() + prediction.sum()

    if total == 0:
        return 1.0 if intersection == 0 else 0.0

    return float(2 * intersection / total)


def calculate_metrics(ground_truth: np.ndarray, prediction: np.ndarray) -> dict:
    """
    Calculate all metrics for a ground truth / prediction pair.

    Args:
        ground_truth: Ground truth array
        prediction: Predicted array

    Returns:
        Dict with 'iou', 'sse', 'dice' keys
    """
    return {
        'iou': calculate_iou(ground_truth, prediction),
        'sse': calculate_sse(ground_truth, prediction),
        'dice': calculate_dice(ground_truth, prediction),
    }


# IoU formula reference (for documentation purposes)
IOU_FORMULA = r"$\text{IoU} = \frac{|G \cap \hat{G}|}{|G \cup \hat{G}|}$"
SSE_FORMULA = r"$\text{SSE} = \sum_{i,j} (I[i,j] - \hat{I}(P)[i,j])^2$"
DICE_FORMULA = r"$\text{Dice} = \frac{2|G \cap \hat{G}|}{|G| + |\hat{G}|}$"


def test_emergence_hypothesis(benchmark_df: pd.DataFrame,
                               primitive_df: pd.DataFrame) -> dict:
    """Run statistical tests for capability emergence hypothesis.

    Tests whether newer model versions show increased primitive usage
    and whether primitive usage correlates with generation quality.
    """
    from scipy import stats as sp_stats

    results = {
        'hypothesis': (
            'Capability Emergence: Newer Gemini models learned to use '
            'GDSFactory primitives, correlating with better device '
            'generation quality.'
        ),
        'tests': {},
        'summary': {'key_findings': [], 'hypothesis_supported': False},
    }

    # Filter Gemini models
    gemini_prim = primitive_df[primitive_df['model_family'] == 'gemini'].copy()
    gemini_bench = benchmark_df[benchmark_df['model_family'] == 'gemini'].copy()

    # 1. Spearman: version vs primitive usage
    if len(gemini_prim) >= 3:
        rho, p = sp_stats.spearmanr(
            gemini_prim['model_version'], gemini_prim['primitive_percentage']
        )
        interp = ('Strong' if abs(rho) > 0.7 else
                  'Moderate' if abs(rho) > 0.4 else 'Weak')
        results['tests']['spearman_version_primitive'] = {
            'test': 'Spearman Correlation (Version vs Primitive Usage)',
            'rho': float(rho),
            'p_value': float(p),
            'significant': p < 0.05,
            'interpretation': f'{interp} {"positive" if rho > 0 else "negative"} correlation',
        }

    # 2. Mann-Whitney: 2.x vs 3.x on primitive_percentage
    v2_prim = gemini_prim[gemini_prim['model_version'] < 3]['primitive_percentage']
    v3_prim = gemini_prim[gemini_prim['model_version'] >= 3]['primitive_percentage']
    if len(v2_prim) > 0 and len(v3_prim) > 0:
        u, p = sp_stats.mannwhitneyu(v2_prim, v3_prim, alternative='less')
        results['tests']['mannwhitney_primitive'] = {
            'test': 'Mann-Whitney U (2.x vs 3.x on primitive_percentage)',
            'p_value': float(p),
            'significant': p < 0.05,
        }

    # 3. Mann-Whitney: 2.x vs 3.x on best_iou
    v2_iou = gemini_bench[gemini_bench['model_version'] < 3]['best_iou']
    v3_iou = gemini_bench[gemini_bench['model_version'] >= 3]['best_iou']
    if len(v2_iou) > 0 and len(v3_iou) > 0:
        u, p = sp_stats.mannwhitneyu(v2_iou, v3_iou, alternative='less')
        results['tests']['mannwhitney_iou'] = {
            'test': 'Mann-Whitney U (2.x vs 3.x on best_iou)',
            'p_value': float(p),
            'significant': p < 0.05,
        }

    # 4. Linear regression: primitive % -> IoU
    merged = pd.merge(
        benchmark_df[['model_name', 'best_iou']],
        primitive_df[['model_name', 'primitive_percentage']],
        on='model_name', how='inner'
    ).dropna()
    if len(merged) >= 5:
        slope, intercept, r, p, se = sp_stats.linregress(
            merged['primitive_percentage'], merged['best_iou']
        )
        results['tests']['linear_regression'] = {
            'test': 'Linear Regression (Primitives -> IoU)',
            'p_value': float(p),
            'significant': p < 0.05,
            'r_squared': float(r ** 2),
            'interpretation': (
                f'Each 10% increase in primitives -> {slope * 10:.3f} IoU increase'
            ),
        }

    # 5. ANOVA across families
    families = benchmark_df['model_family'].unique()
    groups = [
        benchmark_df[benchmark_df['model_family'] == f]['best_iou'].dropna()
        for f in families if len(benchmark_df[benchmark_df['model_family'] == f]) >= 2
    ]
    if len(groups) >= 2:
        f_stat, p = sp_stats.f_oneway(*groups)
        results['tests']['anova_families'] = {
            'test': 'One-way ANOVA (best_iou across families)',
            'p_value': float(p),
            'significant': p < 0.05,
        }

    # 6. Kruskal-Wallis
    if len(groups) >= 2:
        h_stat, p = sp_stats.kruskal(*groups)
        results['tests']['kruskal_families'] = {
            'test': 'Kruskal-Wallis H-test (best_iou across families)',
            'p_value': float(p),
            'significant': p < 0.05,
        }

    # Determine overall hypothesis support
    sig_count = sum(1 for t in results['tests'].values()
                    if isinstance(t, dict) and t.get('significant'))
    results['summary']['hypothesis_supported'] = sig_count >= 2

    return results


def save_results(results: dict, output_path: str) -> None:
    """Save statistical results to JSON."""
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"  - Saved statistical results to {output_path}")
