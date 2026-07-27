"""Visualization module for benchmark analysis.

Creates publication-quality figures for:
1. Model performance comparison
2. Primitive usage analysis
3. Capability emergence across Gemini generations
"""

from typing import Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch
from scipy import stats

# Set publication-quality defaults
plt.rcParams.update({
    'font.size': 11,
    'axes.titlesize': 13,
    'axes.labelsize': 11,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 9,
    'figure.dpi': 150,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
})

# Color palettes by model family
FAMILY_COLORS = {
    'gemini': '#4285F4',  # Google blue
    'claude': '#F97316',  # Anthropic orange
    'openai': '#10B981',  # OpenAI green
    'grok': '#8B5CF6',    # Purple
    'qwen': '#EC4899',    # Pink
    'other': '#6B7280',   # Gray
}

# Gemini version gradient (for emergence plot)
GEMINI_VERSION_COLORS = {
    '2.0-flash': '#FECACA',      # Light red (low capability)
    '2.5-flash': '#FDE68A',      # Light yellow
    '2.5-pro': '#FEF08A',        # Yellow
    '3.0-flash': '#BBF7D0',      # Light green
    '3.0-pro': '#22C55E',        # Green (high capability)
    '3.1-flash-lite': '#16A34A', # Darker green
    '3.1-pro': '#15803D',        # Darkest green (highest capability)
}


def plot_model_performance(df: pd.DataFrame, output_path: str,
                           metric: str = 'best_iou') -> None:
    """Create grouped bar chart comparing model performance across papers.

    Args:
        df: DataFrame with benchmark results
        output_path: Path to save figure
        metric: Metric to plot ('best_iou' or 'best_sse')
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Get unique papers and models
    papers = sorted(df['paper_id'].unique())
    models = df.groupby('model_name')[metric].mean().sort_values(ascending=False).index.tolist()

    n_papers = len(papers)
    n_models = len(models)
    width = 0.8 / n_models

    x = np.arange(n_papers)

    for i, model in enumerate(models):
        model_data = df[df['model_name'] == model]
        family = model_data['model_family'].iloc[0] if len(model_data) > 0 else 'other'

        values = []
        errors = []
        for paper in papers:
            paper_data = model_data[model_data['paper_id'] == paper]
            if len(paper_data) > 0:
                values.append(paper_data[metric].mean())
                errors.append(paper_data[metric].std() if len(paper_data) > 1 else 0)
            else:
                values.append(0)
                errors.append(0)

        color = FAMILY_COLORS.get(family, FAMILY_COLORS['other'])
        alpha = 0.5 + (0.5 * (n_models - i) / n_models)  # Gradient within family

        ax.bar(x + i * width - (n_models - 1) * width / 2, values, width,
               label=model, color=color, alpha=alpha, edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Test Paper', fontsize=12)
    ylabel = 'Best IoU Score' if metric == 'best_iou' else 'Best SSE (lower is better)'
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_title('GDS Generation Performance Across Models and Papers', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([p.replace('FINAL_', '') for p in papers])

    if metric == 'best_iou':
        ax.set_ylim(0, 1)
        ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(n_papers - 0.5, 0.52, 'Quality threshold', fontsize=9, color='gray', ha='right')

    # Legend outside plot
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), ncol=1, frameon=True)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved model performance plot to {output_path}")


def plot_primitive_usage(primitive_df: pd.DataFrame, output_path: str) -> None:
    """Create horizontal stacked bar chart showing primitive vs path vs polygon usage.

    Three categories:
    - Parametric Primitives: straight(), bend_euler(), taper(), mmi1x2(), etc.
    - Path Construction: gf.Path(), extrude(), smooth() — manual geometry via GDSFactory path API
    - Raw Polygons: add_polygon(), boolean(), rectangle() — lowest-level operations

    Args:
        primitive_df: DataFrame with primitive analysis results
        output_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(12, 7))

    # Sort by primitive percentage
    df_sorted = primitive_df.sort_values('primitive_percentage', ascending=True)

    models = df_sorted['model_name'].tolist()
    primitives = df_sorted['primitive_percentage'].tolist()
    paths = df_sorted['path_percentage'].tolist() if 'path_percentage' in df_sorted.columns else [0] * len(models)
    polygons = df_sorted['polygon_percentage'].tolist()
    scripts = df_sorted['total_scripts'].tolist()

    y_pos = np.arange(len(models))

    # Three-way stacked bars
    bars1 = ax.barh(y_pos, primitives, label='Parametric Primitives (straight, bend, taper...)',
                    color='#10B981', alpha=0.85, edgecolor='white', linewidth=0.5)
    bars2 = ax.barh(y_pos, paths, left=primitives, label='Path Construction (gf.Path, extrude...)',
                    color='#F59E0B', alpha=0.85, edgecolor='white', linewidth=0.5)
    bars3 = ax.barh(y_pos, polygons, left=[p + pa for p, pa in zip(primitives, paths)],
                    label='Raw Polygons/Boolean (add_polygon, rectangle...)',
                    color='#EF4444', alpha=0.85, edgecolor='white', linewidth=0.5)

    # Add file count annotations
    for i, (prim, path, poly, n) in enumerate(zip(primitives, paths, polygons, scripts)):
        # Annotation on the right
        ax.annotate(f'n={n}', xy=(102, i), fontsize=9, va='center', ha='left', color='#6B7280')

        # Percentage label inside primitive bar if large enough
        if prim > 15:
            ax.annotate(f'{prim:.0f}%', xy=(prim / 2, i), fontsize=9, va='center', ha='center',
                       color='white', fontweight='bold')

        # Percentage label inside path bar if large enough
        if path > 12:
            ax.annotate(f'{path:.0f}%', xy=(prim + path / 2, i), fontsize=8, va='center', ha='center',
                       color='white', fontweight='bold')

        # Percentage label inside polygon bar if large enough
        if poly > 15:
            ax.annotate(f'{poly:.0f}%', xy=(prim + path + poly / 2, i), fontsize=9, va='center', ha='center',
                       color='white', fontweight='bold')

    ax.set_yticks(y_pos)
    ax.set_yticklabels(models)
    ax.set_xlabel('Percentage of Recognized Function Calls', fontsize=12)
    ax.set_title('Code Generation Strategy: Parametric Functions vs Manual Construction',
                fontsize=14, fontweight='bold')

    # Add vertical lines for reference
    ax.axvline(x=50, color='gray', linestyle='--', alpha=0.4, linewidth=1)
    ax.set_xlim(0, 115)

    # Legend at bottom
    ax.legend(loc='lower right', frameon=True, fontsize=8)

    # Add insight annotation
    ax.annotate('Only parametric primitives (green)\nrepresent true semantic decomposition',
               xy=(80, len(models) - 1.5), fontsize=9, style='italic', color='#059669',
               ha='center', va='center',
               bbox=dict(boxstyle='round,pad=0.3', facecolor='#ECFDF5', edgecolor='#10B981', alpha=0.8))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved primitive usage plot to {output_path}")


def plot_capability_emergence(df: pd.DataFrame, primitive_df: pd.DataFrame,
                              output_path: str) -> None:
    """Create 4-panel figure showing capability emergence in Gemini models.

    Args:
        df: DataFrame with benchmark results
        primitive_df: DataFrame with primitive analysis
        output_path: Path to save figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Filter to Gemini models only
    gemini_bench = df[df['model_family'] == 'gemini'].copy()
    gemini_prim = primitive_df[primitive_df['model_family'] == 'gemini'].copy()

    # Aggregate benchmark data
    gemini_agg = gemini_bench.groupby(['model_name', 'model_version', 'model_version_name']).agg({
        'best_iou': ['mean', 'std'],
        'turn1_success_rate': 'mean',
    }).reset_index()

    # Flatten column names
    gemini_agg.columns = ['model_name', 'model_version', 'model_version_name',
                          'mean_iou', 'std_iou', 'success_rate']

    # Merge with primitive data
    gemini_merged = pd.merge(
        gemini_agg,
        gemini_prim[['model_name', 'primitive_percentage', 'polygon_percentage', 'total_scripts']],
        on='model_name',
        how='left'
    )

    # Rename columns
    gemini_merged = gemini_merged.rename(columns={
        'primitive_percentage': 'primitive_pct',
        'polygon_percentage': 'polygon_pct'
    })

    # Sort by version
    gemini_merged = gemini_merged.sort_values('model_version')

    # Drop rows with missing primitive data
    gemini_merged = gemini_merged.dropna(subset=['primitive_pct'])

    versions = gemini_merged['model_version'].tolist()
    version_names = gemini_merged['model_version_name'].tolist()

    # Create dynamic version labels
    version_labels = []
    for vn in version_names:
        if '2.0' in vn:
            version_labels.append('2.0\nFlash')
        elif '2.5-flash' in vn:
            version_labels.append('2.5\nFlash')
        elif '2.5-pro' in vn:
            version_labels.append('2.5\nPro')
        elif '3.0-flash' in vn:
            version_labels.append('3.0\nFlash')
        elif '3.0-pro' in vn:
            version_labels.append('3.0\nPro')
        elif '3.1-flash' in vn:
            version_labels.append('3.1\nFlash Lite')
        elif '3.1-pro' in vn:
            version_labels.append('3.1\nPro')
        else:
            version_labels.append(vn.replace('-', '\n'))

    # ===== Panel A: Primitive % vs Version =====
    ax1 = axes[0, 0]

    colors = [GEMINI_VERSION_COLORS.get(v, '#999') for v in version_names]
    ax1.plot(versions, gemini_merged['primitive_pct'], 'o-', markersize=12,
             linewidth=2.5, color='#3B82F6', markeredgecolor='white', markeredgewidth=2)

    for i, (v, prim, c) in enumerate(zip(versions, gemini_merged['primitive_pct'], colors)):
        ax1.scatter(v, prim, s=200, c=c, edgecolors='#1E40AF', linewidth=2, zorder=5)
        ax1.annotate(f'{prim:.0f}%', xy=(v, prim + 4), ha='center', fontsize=10, fontweight='bold')

    ax1.set_xlabel('Gemini Version', fontsize=11)
    ax1.set_ylabel('Primitive Usage (%)', fontsize=11)
    ax1.set_title('A) Emergence of Primitive-Based Design', fontsize=12, fontweight='bold')
    ax1.set_xticks(versions)
    ax1.set_xticklabels(version_labels)
    ax1.set_ylim(0, 100)
    ax1.grid(True, alpha=0.3, linestyle='--')

    # Add capability zones
    ax1.axhspan(0, 35, alpha=0.1, color='red', label='Low capability')
    ax1.axhspan(35, 60, alpha=0.1, color='yellow', label='Emerging')
    ax1.axhspan(60, 100, alpha=0.1, color='green', label='High capability')

    # ===== Panel B: IoU vs Version =====
    ax2 = axes[0, 1]

    ax2.errorbar(versions, gemini_merged['mean_iou'],
                yerr=gemini_merged['std_iou'].fillna(0),
                fmt='s-', markersize=10, capsize=5, capthick=2,
                color='#10B981', linewidth=2.5, markeredgecolor='white', markeredgewidth=2)

    for i, (v, iou) in enumerate(zip(versions, gemini_merged['mean_iou'])):
        ax2.annotate(f'{iou:.2f}', xy=(v, iou + 0.03), ha='center', fontsize=10, fontweight='bold')

    ax2.set_xlabel('Gemini Version', fontsize=11)
    ax2.set_ylabel('Mean Best IoU Score', fontsize=11)
    ax2.set_title('B) Generation Quality Improvement', fontsize=12, fontweight='bold')
    ax2.set_xticks(versions)
    ax2.set_xticklabels(version_labels)
    ax2.set_ylim(0, 0.8)
    ax2.grid(True, alpha=0.3, linestyle='--')

    # ===== Panel C: Success Rate vs Version =====
    ax3 = axes[1, 0]

    colors = [GEMINI_VERSION_COLORS.get(v, '#999') for v in version_names]
    bars = ax3.bar(versions, gemini_merged['success_rate'] * 100, width=0.3,
                   color=colors, edgecolor='#1E40AF', linewidth=1.5)

    for bar, rate in zip(bars, gemini_merged['success_rate']):
        ax3.annotate(f'{rate * 100:.0f}%', xy=(bar.get_x() + bar.get_width() / 2, bar.get_height() + 2),
                    ha='center', fontsize=10, fontweight='bold')

    ax3.set_xlabel('Gemini Version', fontsize=11)
    ax3.set_ylabel('Turn 1 Success Rate (%)', fontsize=11)
    ax3.set_title('C) Code Execution Success Rate', fontsize=12, fontweight='bold')
    ax3.set_xticks(versions)
    ax3.set_xticklabels(version_labels)
    ax3.set_ylim(0, 110)
    ax3.grid(True, alpha=0.3, linestyle='--', axis='y')

    # ===== Panel D: Correlation Scatter =====
    ax4 = axes[1, 1]

    # Use per-paper data for scatter
    gemini_scatter = pd.merge(
        gemini_bench[['paper_id', 'model_name', 'model_version_name', 'best_iou']],
        gemini_prim[['model_name', 'primitive_percentage']],
        on='model_name',
        how='left'
    ).dropna()

    colors = [GEMINI_VERSION_COLORS.get(v, '#999') for v in gemini_scatter['model_version_name']]

    ax4.scatter(gemini_scatter['primitive_percentage'], gemini_scatter['best_iou'],
               c=colors, s=100, alpha=0.7, edgecolors='black', linewidth=0.5)

    # Regression line
    x = gemini_scatter['primitive_percentage'].values
    y = gemini_scatter['best_iou'].values

    if len(x) > 2:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_line = np.linspace(0, 100, 100)
        ax4.plot(x_line, p(x_line), 'k--', alpha=0.6, linewidth=2, label='Regression')

        # Correlation
        r, p_value = stats.pearsonr(x, y)
        ax4.annotate(f'r = {r:.3f}\np < 0.001' if p_value < 0.001 else f'r = {r:.3f}\np = {p_value:.3f}',
                    xy=(0.05, 0.95), xycoords='axes fraction', fontsize=11, va='top',
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.4', facecolor='white', edgecolor='#3B82F6', alpha=0.9))

    ax4.set_xlabel('Primitive Usage (%)', fontsize=11)
    ax4.set_ylabel('Best IoU Score', fontsize=11)
    ax4.set_title('D) Correlation: Primitives vs Quality', fontsize=12, fontweight='bold')
    ax4.set_xlim(0, 100)
    ax4.set_ylim(0, 0.8)
    ax4.grid(True, alpha=0.3, linestyle='--')

    # Legend for colors
    legend_elements = [Patch(facecolor=c, edgecolor='black', label=v)
                       for v, c in GEMINI_VERSION_COLORS.items()]
    ax4.legend(handles=legend_elements, loc='lower right', title='Gemini Version')

    # Main title
    fig.suptitle('Capability Emergence in Gemini Model Family\n'
                'Evolution from Polygon-Based to Primitive-Based Photonic Design',
                fontsize=14, fontweight='bold', y=1.02)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved capability emergence plot to {output_path}")


def plot_performance_heatmap(df: pd.DataFrame, output_path: str) -> None:
    """Create heatmap of IoU scores across models and papers.

    Args:
        df: DataFrame with benchmark results
        output_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(12, 9))

    # Pivot table
    pivot = df.pivot_table(values='best_iou',
                           index='model_name',
                           columns='paper_id',
                           aggfunc='mean')

    # Reorder columns
    paper_order = [f'FINAL_{i}' for i in range(1, 9)]
    pivot = pivot.reindex(columns=[p for p in paper_order if p in pivot.columns])

    # Reorder rows by family and performance
    model_order = df.groupby('model_name')['best_iou'].mean().sort_values(ascending=False).index.tolist()
    pivot = pivot.reindex([m for m in model_order if m in pivot.index])

    # Create heatmap
    sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn',
                vmin=0, vmax=0.8, center=0.4,
                linewidths=0.5, ax=ax,
                cbar_kws={'label': 'Best IoU Score'})

    ax.set_xlabel('Test Paper', fontsize=12)
    ax.set_ylabel('Model', fontsize=12)
    ax.set_title('Model Performance Heatmap: IoU Across All Papers', fontsize=14, fontweight='bold')

    # Simplify x-labels
    ax.set_xticklabels([p.replace('FINAL_', '') for p in pivot.columns])

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved performance heatmap to {output_path}")


def plot_family_comparison(df: pd.DataFrame, output_path: str) -> None:
    """Create box plot comparing model families.

    Args:
        df: DataFrame with benchmark results
        output_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    family_order = ['gemini', 'openai', 'grok', 'qwen', 'claude']
    family_labels = ['Gemini', 'OpenAI', 'Grok', 'Qwen', 'Claude']

    # Filter and order
    df_filtered = df[df['model_family'].isin(family_order)]

    # Create box plot
    bp = ax.boxplot([df_filtered[df_filtered['model_family'] == f]['best_iou'].dropna()
                     for f in family_order],
                    labels=family_labels, patch_artist=True)

    # Color boxes
    colors = [FAMILY_COLORS[f] for f in family_order]
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    ax.set_xlabel('Model Family', fontsize=12)
    ax.set_ylabel('Best IoU Score', fontsize=12)
    ax.set_title('Performance Distribution by Model Family', fontsize=14, fontweight='bold')
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3, axis='y')

    # Add mean markers
    for i, family in enumerate(family_order):
        mean_val = df_filtered[df_filtered['model_family'] == family]['best_iou'].mean()
        ax.scatter(i + 1, mean_val, marker='D', s=100, color='red', zorder=5, edgecolors='white')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved family comparison plot to {output_path}")


if __name__ == "__main__":
    print("Visualization module loaded. Run from main analysis script.")
