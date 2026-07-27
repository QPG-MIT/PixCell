# JEE Core Library
# This package contains the core scripts for GDS-to-image optimization

from .gds_raster_compare import (
    load_top_cell,
    extract_polygons,
    polygons_bbox,
    rasterize,
    binarize,
    compute_metrics,
    make_diff,
    make_overlay,
)

from .compute_sse import compute_sse_metrics

from .calibrate_boundary import calculate_calibration

from .compare_fixed import (
    load_calibration,
    map_polygons_with_fixed_calibration,
)

from .footprint_penalty import (
    compute_gds_bbox_um,
    compute_footprint_penalty,
    compute_footprint_penalty_from_polygons,
)

from .optimizer import (
    GDSOptimizer,
    OptimizerConfig,
    OptimizationResult,
)

from .explorer import (
    GDSExplorer,
    ExplorerConfig,
    ExplorationResult,
    GridPoint,
    LocalOptResult,
)

from .visualize_exploration import (
    create_visualization_report,
    load_exploration_results,
    load_iteration_histories,
)

__all__ = [
    # gds_raster_compare
    "load_top_cell",
    "extract_polygons",
    "polygons_bbox",
    "rasterize",
    "binarize",
    "compute_metrics",
    "make_diff",
    "make_overlay",
    # compute_sse
    "compute_sse_metrics",
    # calibrate_boundary
    "calculate_calibration",
    # compare_fixed
    "load_calibration",
    "map_polygons_with_fixed_calibration",
    # footprint_penalty
    "compute_gds_bbox_um",
    "compute_footprint_penalty",
    "compute_footprint_penalty_from_polygons",
    # optimizer
    "GDSOptimizer",
    "OptimizerConfig",
    "OptimizationResult",
    # explorer
    "GDSExplorer",
    "ExplorerConfig",
    "ExplorationResult",
    "GridPoint",
    "LocalOptResult",
    # visualization
    "create_visualization_report",
    "load_exploration_results",
    "load_iteration_histories",
]
