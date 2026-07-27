"""
Flex Integration Module for HOMI

Provides Tidy3D FDTD simulation functionality for Step 8.
Wraps the Flex module for easy integration with the main app.
"""

from typing import Dict, Any, List, Tuple, Optional


def is_tidy3d_available() -> bool:
    """
    Check if Tidy3D and required dependencies are available.

    Returns:
        True if Tidy3D can be used
    """
    try:
        from flex.core import materials, cloud
        return materials.is_available() and cloud.is_available()
    except ImportError:
        return False


def get_material_presets() -> Dict[str, Dict[str, Any]]:
    """
    Get available material presets.

    Returns:
        Dict mapping preset name to preset info
    """
    try:
        from flex.core.materials import MATERIAL_PRESETS
        return MATERIAL_PRESETS.copy()
    except ImportError:
        return {}


def get_simulation_info(
    component: Any,
    layers: List[Tuple[int, int]],
    thickness_nm: int,
    wavelength_um: float
) -> Dict[str, Any]:
    """
    Get information about simulation that would be created.

    Args:
        component: GDSFactory Component
        layers: Layers to include
        thickness_nm: Thickness in nm
        wavelength_um: Wavelength in um

    Returns:
        Dict with simulation parameters
    """
    try:
        from flex.core.simulation import get_simulation_info as _get_info
        return _get_info(component, layers, thickness_nm, wavelength_um)
    except ImportError:
        return {}


def create_and_upload_simulation(
    component: Any,
    config: Dict[str, Any],
    api_key: str
) -> Dict[str, Any]:
    """
    Create simulation and upload to Tidy3D cloud.

    Args:
        component: GDSFactory Component
        config: Simulation configuration with keys:
            - material: Material preset name
            - thickness_nm: Device thickness in nm
            - wavelength_um: Simulation wavelength in um
            - layers: List of (layer, datatype) tuples
            - custom_core_n: Optional custom core index
            - custom_clad_n: Optional custom cladding index
            - task_name: Optional task name
        api_key: Tidy3D API key

    Returns:
        Dict with:
            - task_id: Task ID string
            - web_url: Tidy3D Workbench URL
            - estimated_cost: Cost in FlexCredits (or None)
            - simulation_info: Dict with simulation parameters

    Raises:
        RuntimeError: If Tidy3D not available
        ValueError: If simulation cannot be created
    """
    if not is_tidy3d_available():
        raise RuntimeError("Tidy3D is not available. Please install with: pip install 'pixcell[simulate]'")

    from flex.core.simulation import create_simulation_from_component
    from flex.core.cloud import upload_simulation, estimate_simulation_cost

    # Extract config
    material = config.get("material", "Silicon (SOI)")
    thickness_nm = config.get("thickness_nm", 220)
    wavelength_um = config.get("wavelength_um", 1.55)
    layers = config.get("layers", [(1, 0)])
    custom_core_n = config.get("custom_core_n")
    custom_clad_n = config.get("custom_clad_n")
    task_name = config.get("task_name", "Device")

    # Create simulation
    sim = create_simulation_from_component(
        component=component,
        layers=layers,
        material=material,
        thickness_nm=thickness_nm,
        wavelength_um=wavelength_um,
        api_key=api_key,
        custom_core_n=custom_core_n,
        custom_clad_n=custom_clad_n
    )

    # Upload to cloud
    task_id, web_url = upload_simulation(sim, task_name=task_name)

    # Estimate cost
    estimated_cost = estimate_simulation_cost(task_id)

    # Get simulation info
    sim_info = get_simulation_info(component, layers, thickness_nm, wavelength_um)

    return {
        "task_id": task_id,
        "web_url": web_url,
        "estimated_cost": estimated_cost,
        "simulation_info": sim_info
    }


def get_task_status(task_id: str) -> Optional[str]:
    """
    Get current status of a simulation task.

    Args:
        task_id: Task ID

    Returns:
        Status string or None
    """
    try:
        from flex.core.cloud import get_task_status as _get_status
        return _get_status(task_id)
    except ImportError:
        return None


def get_workbench_url(task_id: str) -> str:
    """
    Get Tidy3D Workbench URL for a task.

    Args:
        task_id: Task ID

    Returns:
        URL string
    """
    try:
        from flex.core.cloud import get_workbench_url as _get_url
        return _get_url(task_id)
    except ImportError:
        return f"https://tidy3d.simulation.cloud/workbench?taskId={task_id}"


def validate_api_key(api_key: str) -> bool:
    """
    Validate a Tidy3D API key.

    Args:
        api_key: API key to validate

    Returns:
        True if valid
    """
    try:
        from flex.core.cloud import validate_api_key as _validate
        return _validate(api_key)
    except ImportError:
        return False
