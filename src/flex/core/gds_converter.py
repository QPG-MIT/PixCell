"""
Flex GDS Converter Module

Extracts polygons from GDSFactory components and converts them to Tidy3D structures.
"""

import os
import tempfile
from typing import List, Tuple, Any, Optional

# Check if dependencies are available
try:
    import gdstk
    GDSTK_AVAILABLE = True
except ImportError:
    GDSTK_AVAILABLE = False
    gdstk = None

try:
    import tidy3d as td
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None


def is_available() -> bool:
    """Check if required dependencies are available."""
    return GDSTK_AVAILABLE and TIDY3D_AVAILABLE


def extract_polygons_from_component(
    component: Any,
    included_layers: List[Tuple[int, int]],
    min_feature_size_um: float = 0.1,
    validate_fabricability: bool = True,
) -> List[List[Tuple[float, float]]]:
    """
    Extract 2D polygons from a GDSFactory component.

    Process:
    1. Export component to temporary GDS file
    2. Read with gdstk library
    3. Flatten cell hierarchy
    4. Filter polygons by layer
    5. Skip sub-fabrication polygons (area < min_area based on min_feature_size)

    Args:
        component: GDSFactory Component object
        included_layers: List of (layer, datatype) tuples to include
        min_feature_size_um: Minimum fabricable feature size in µm (default 0.1 = 100nm)
        validate_fabricability: If True, skip features smaller than min_feature_size

    Returns:
        List of polygons, where each polygon is a list of (x, y) vertices

    Raises:
        RuntimeError: If gdstk is not available
    """
    if not GDSTK_AVAILABLE:
        raise RuntimeError("gdstk is not installed. Install with: pip install gdstk")

    # Export to temporary GDS file
    gds_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.gds', delete=False) as tmp:
            gds_path = tmp.name

        component.write_gds(gds_path)

        # Read with gdstk
        lib = gdstk.read_gds(gds_path)

        # Find top cell
        top_cell = None
        for cell in lib.cells:
            # Skip context cells
            if "CONTEXT" in cell.name.upper():
                continue
            # Prefer cell matching component name
            if cell.name == component.name:
                top_cell = cell
                break
            # Otherwise use first non-context cell
            if top_cell is None:
                top_cell = cell

        if top_cell is None:
            return []

        # Flatten hierarchy
        cell_flat = top_cell.copy(f"{top_cell.name}_flat")
        cell_flat.flatten()

        # Extract polygons by layer
        polygons = []
        included_set = set(included_layers)

        for poly in cell_flat.polygons:
            layer_dt = (poly.layer, poly.datatype)

            if layer_dt not in included_set:
                continue

            # Skip sub-fabrication polygons (physics-based threshold)
            area = abs(poly.area())
            # Minimum area based on min_feature_size squared (e.g., 0.1um -> 0.01 um²)
            min_area_um2 = min_feature_size_um ** 2 if validate_fabricability else 0.001
            if area < min_area_um2:
                continue

            # Convert to list of (x, y) tuples
            vertices = [(float(p[0]), float(p[1])) for p in poly.points]
            polygons.append(vertices)

        return polygons

    finally:
        # Cleanup
        if gds_path and os.path.exists(gds_path):
            try:
                os.unlink(gds_path)
            except Exception:
                pass


def create_3d_structures(
    polygons: List[List[Tuple[float, float]]],
    thickness_um: float,
    core_medium: Any
) -> List[Any]:
    """
    Convert 2D polygons to 3D Tidy3D PolySlab structures.

    Args:
        polygons: List of 2D polygons (list of (x, y) vertices)
        thickness_um: Extrusion height in micrometers
        core_medium: Tidy3D Medium for the structures

    Returns:
        List of td.Structure objects
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    structures = []

    for poly_vertices in polygons:
        try:
            # Create PolySlab (extrude in Z direction)
            polyslab = td.PolySlab(
                vertices=poly_vertices,
                axis=2,  # Extrude in Z
                slab_bounds=(0, thickness_um)
            )

            # Create Structure with medium
            structure = td.Structure(
                geometry=polyslab,
                medium=core_medium
            )

            structures.append(structure)

        except Exception as e:
            # Skip invalid polygons (self-intersecting, etc.)
            continue

    return structures


def get_component_bounds(component: Any) -> Tuple[float, float, float, float]:
    """
    Get the bounding box of a GDSFactory component.

    Args:
        component: GDSFactory Component

    Returns:
        Tuple of (xmin, ymin, xmax, ymax) in micrometers
    """
    bbox = component.bbox()

    try:
        xmin, ymin = bbox[0]
        xmax, ymax = bbox[1]
    except TypeError:
        # Handle different bbox formats
        xmin, ymin = bbox.left, bbox.bottom
        xmax, ymax = bbox.right, bbox.top

    return float(xmin), float(ymin), float(xmax), float(ymax)


def convert_component_to_structures(
    component: Any,
    included_layers: List[Tuple[int, int]],
    thickness_um: float,
    core_medium: Any
) -> List[Any]:
    """
    Full conversion from GDSFactory component to Tidy3D structures.

    Args:
        component: GDSFactory Component
        included_layers: List of (layer, datatype) tuples to include
        thickness_um: Extrusion height in micrometers
        core_medium: Tidy3D Medium for the structures

    Returns:
        List of td.Structure objects

    Raises:
        ValueError: If no valid structures could be created
    """
    # Extract polygons
    polygons = extract_polygons_from_component(component, included_layers)

    if not polygons:
        raise ValueError(f"No polygons found on layers {included_layers}")

    # Create 3D structures
    structures = create_3d_structures(polygons, thickness_um, core_medium)

    if not structures:
        raise ValueError("Could not create any valid 3D structures from polygons")

    return structures
