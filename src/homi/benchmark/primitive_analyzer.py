"""Primitive usage analyzer for GDSFactory scripts.

Analyzes generated Python scripts to determine whether they use high-level
GDSFactory primitives (like straight, bend, taper) or low-level polygon operations.
"""

import ast
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


# High-level GDSFactory primitives - indicates semantic understanding
PRIMITIVE_FUNCTIONS = {
    # Waveguide components
    'straight',
    'bend_circular',
    'bend_euler',
    'bend_s',

    # Tapers and transitions
    'taper',
    'taper_strip_to_ridge',
    'taper_cross_section',
    'taper_adiabatic',

    # Couplers
    'coupler',
    'coupler_ring',
    'coupler_asymmetric',
    'coupler_straight',
    'coupler_full',
    'directional_coupler',

    # MMI components
    'mmi',
    'mmi1x2',
    'mmi2x2',
    'mmi_90',

    # Rings and resonators
    'ring',
    'ring_single',
    'ring_double',
    'ring_single_heater',
    'ring_double_heater',

    # Splitters
    'splitter_tree',
    'splitter_chain',

    # Interferometers
    'mzi',
    'mzi1x2',
    'mzi2x2',
    'mzi_arm',
    'mzi_arms',
    'mzi_phase_shifter',

    # Gratings
    'grating_coupler_elliptical',
    'grating_coupler_rectangular',
    'grating_coupler_te',
    'grating_coupler_tm',

    # Crossings
    'crossing',
    'crossing45',
    'crossing_etched',

    # Y-branches
    'y_branch',

    # Path-based components (indicates understanding of routing)
    'route_single',
    'route_bundle',
    'get_route',

    # Spiral
    'spiral',
    'spiral_external_io',
    'spiral_inner_io',
}

# Path-based construction (intermediate level - good understanding)
PATH_FUNCTIONS = {
    'path',
    'Path',
    'arc',
    'euler',
    'from_bezier_control_points',
    'extrude',
    'extrude_transition',
    'transition',
    'smooth',
}

# Low-level polygon operations - indicates lack of semantic decomposition
POLYGON_PATTERNS = {
    'rectangle',
    'ellipse',
    'Polygon',
    'polygon',
    'boolean',
    'add_polygon',
    # NOTE: add_ref removed — it's a standard GDSFactory operation for adding
    # component references, not a polygon operation. Including it inflated
    # polygon counts (e.g. 38% of Gemini 2.5 Pro's "polygon" counts were add_ref).
}

# Cross-section usage (indicates good understanding)
CROSS_SECTION_FUNCTIONS = {
    'cross_section',
    'CrossSection',
    'xs',
}


@dataclass
class ScriptAnalysis:
    """Result of analyzing a single GDSFactory script."""
    script_path: str
    primitive_count: int = 0
    path_count: int = 0
    polygon_count: int = 0
    cross_section_count: int = 0
    total_components: int = 0
    primitives_used: dict = field(default_factory=dict)
    paths_used: dict = field(default_factory=dict)
    polygons_used: dict = field(default_factory=dict)
    parse_error: Optional[str] = None

    @property
    def primitive_percentage(self) -> float:
        """Percentage of recognized calls that are parametric primitives.

        Only counts PRIMITIVE_FUNCTIONS (straight, bend_euler, taper, etc.)
        — the actual parametric component functions. Path-based construction
        (gf.Path, extrude) is reported separately.
        """
        total = self.primitive_count + self.path_count + self.polygon_count
        if total == 0:
            return 0.0
        return (self.primitive_count / total) * 100

    @property
    def path_percentage(self) -> float:
        """Percentage of recognized calls that are path-based construction."""
        total = self.primitive_count + self.path_count + self.polygon_count
        if total == 0:
            return 0.0
        return (self.path_count / total) * 100

    @property
    def polygon_percentage(self) -> float:
        """Percentage of recognized calls that are raw polygons."""
        total = self.primitive_count + self.path_count + self.polygon_count
        if total == 0:
            return 0.0
        return (self.polygon_count / total) * 100


def extract_function_name(node: ast.AST) -> Optional[str]:
    """Extract the function name from a Call AST node."""
    if isinstance(node, ast.Call):
        func = node.func

        # Simple call: func()
        if isinstance(func, ast.Name):
            return func.id

        # Attribute call: obj.func() or gf.components.func()
        if isinstance(func, ast.Attribute):
            return func.attr

    return None


def analyze_script(script_path: str) -> ScriptAnalysis:
    """Analyze a GDSFactory script for primitive vs polygon usage.

    Args:
        script_path: Path to the Python script

    Returns:
        ScriptAnalysis with counts and percentages
    """
    result = ScriptAnalysis(script_path=script_path)

    try:
        with open(script_path) as f:
            content = f.read()

        tree = ast.parse(content)
    except SyntaxError as e:
        result.parse_error = f"Syntax error: {e}"
        return result
    except Exception as e:
        result.parse_error = str(e)
        return result

    primitives_used = defaultdict(int)
    paths_used = defaultdict(int)
    polygons_used = defaultdict(int)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func_name = extract_function_name(node)

            if not func_name:
                continue

            if func_name in PRIMITIVE_FUNCTIONS:
                result.primitive_count += 1
                primitives_used[func_name] += 1

            elif func_name in PATH_FUNCTIONS:
                result.path_count += 1
                paths_used[func_name] += 1

            elif func_name in POLYGON_PATTERNS:
                result.polygon_count += 1
                polygons_used[func_name] += 1

            elif func_name in CROSS_SECTION_FUNCTIONS:
                result.cross_section_count += 1

    result.primitives_used = dict(primitives_used)
    result.paths_used = dict(paths_used)
    result.polygons_used = dict(polygons_used)
    result.total_components = result.primitive_count + result.path_count + result.polygon_count

    return result


def analyze_all_primitives(base_path: str) -> pd.DataFrame:
    """Analyze primitive usage across all generated scripts.

    Args:
        base_path: Path to gemini_images_run directory

    Returns:
        DataFrame with primitive analysis per model
    """
    base = Path(base_path)
    model_analyses = defaultdict(lambda: {
        'primitive_count': 0,
        'path_count': 0,
        'polygon_count': 0,
        'cross_section_count': 0,
        'total_scripts': 0,
        'successful_parses': 0,
        'primitives_used': defaultdict(int),
        'paths_used': defaultdict(int),
        'polygons_used': defaultdict(int),
    })

    # Find all generated component scripts
    script_paths = list(base.glob("**/generated_component.py"))

    print(f"Found {len(script_paths)} generated scripts to analyze...")

    for script_path in script_paths:
        # Extract model key from path
        model_key = None
        parts = script_path.parts

        for i, part in enumerate(parts):
            if part.startswith('benchmark_'):
                # Pattern: benchmark_{provider}_{model}
                match = re.match(r'benchmark_(\w+)_(.+)', part)
                if match:
                    provider = match.group(1)
                    model_name = match.group(2)
                    model_key = f"{provider}/{model_name}"
                break

        if not model_key:
            continue

        analysis = analyze_script(str(script_path))

        model_data = model_analyses[model_key]
        model_data['total_scripts'] += 1

        if analysis.parse_error is None:
            model_data['successful_parses'] += 1
            model_data['primitive_count'] += analysis.primitive_count
            model_data['path_count'] += analysis.path_count
            model_data['polygon_count'] += analysis.polygon_count
            model_data['cross_section_count'] += analysis.cross_section_count

            for prim, count in analysis.primitives_used.items():
                model_data['primitives_used'][prim] += count
            for path, count in analysis.paths_used.items():
                model_data['paths_used'][path] += count
            for poly, count in analysis.polygons_used.items():
                model_data['polygons_used'][poly] += count

    # Convert to DataFrame
    results = []
    for model_key, data in model_analyses.items():
        semantic = data['primitive_count'] + data['path_count']
        total = semantic + data['polygon_count']

        primitive_pct = (data['primitive_count'] / total * 100) if total > 0 else 0
        path_pct = (data['path_count'] / total * 100) if total > 0 else 0
        polygon_pct = (data['polygon_count'] / total * 100) if total > 0 else 0

        # Get display name
        from .data_aggregator import get_display_name, get_model_family, get_model_version

        model_name = get_display_name(model_key)
        model_family = get_model_family(model_key)
        model_version, version_name = get_model_version(model_key)

        results.append({
            'model_key': model_key,
            'model_name': model_name,
            'model_family': model_family,
            'model_version': model_version,
            'model_version_name': version_name,
            'total_scripts': data['total_scripts'],
            'successful_parses': data['successful_parses'],
            'primitive_count': data['primitive_count'],
            'path_count': data['path_count'],
            'polygon_count': data['polygon_count'],
            'cross_section_count': data['cross_section_count'],
            'primitive_percentage': primitive_pct,
            'path_percentage': path_pct,
            'polygon_percentage': polygon_pct,
            'top_primitives': dict(sorted(data['primitives_used'].items(), key=lambda x: -x[1])[:5]),
            'top_paths': dict(sorted(data['paths_used'].items(), key=lambda x: -x[1])[:5]),
            'top_polygons': dict(sorted(data['polygons_used'].items(), key=lambda x: -x[1])[:5]),
        })

    df = pd.DataFrame(results)
    df = df.sort_values('primitive_percentage', ascending=False)

    return df


# Pre-computed fallback data (primitives-only percentages, paths separated).
# These are approximate reference values — live analysis should be preferred.
USER_PRIMITIVE_DATA = pd.DataFrame([
    {'model_name': 'Gemini 3.0 Pro', 'total_scripts': 352, 'primitive_percentage': 66.8, 'path_percentage': 15.7, 'polygon_percentage': 17.4},
    {'model_name': 'Gemini 3.0 Flash', 'total_scripts': 323, 'primitive_percentage': 48.7, 'path_percentage': 24.6, 'polygon_percentage': 26.7},
    {'model_name': 'Gemini 2.5 Flash', 'total_scripts': 152, 'primitive_percentage': 38.7, 'path_percentage': 28.1, 'polygon_percentage': 33.1},
    {'model_name': 'Grok 4', 'total_scripts': 147, 'primitive_percentage': 40.0, 'path_percentage': 20.0, 'polygon_percentage': 40.0},
    {'model_name': 'Qwen3-VL Instruct', 'total_scripts': 164, 'primitive_percentage': 49.7, 'path_percentage': 38.5, 'polygon_percentage': 11.7},
    {'model_name': 'Gemini 2.0 Flash', 'total_scripts': 172, 'primitive_percentage': 48.8, 'path_percentage': 7.1, 'polygon_percentage': 44.1},
    {'model_name': 'Claude Opus 4.5', 'total_scripts': 48, 'primitive_percentage': 32.3, 'path_percentage': 26.7, 'polygon_percentage': 41.0},
    {'model_name': 'Claude Sonnet 4.5', 'total_scripts': 67, 'primitive_percentage': 13.1, 'path_percentage': 21.0, 'polygon_percentage': 65.9},
])


if __name__ == "__main__":
    # Test analysis
    from homi.paths import repo_root

    df = analyze_all_primitives(str((repo_root() or Path.cwd()) / "data" / "chatbots" / "trajectories"))
    print("\nPrimitive Analysis Results:")
    print(df[['model_name', 'total_scripts', 'primitive_percentage', 'polygon_percentage']].to_string())
