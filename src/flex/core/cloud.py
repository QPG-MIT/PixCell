"""
Flex Cloud Module

Tidy3D cloud upload, status tracking, and cost estimation.
"""

from typing import Tuple, Optional, Any

# Check if Tidy3D is available
try:
    import tidy3d as td
    from tidy3d import web
    TIDY3D_AVAILABLE = True
except ImportError:
    TIDY3D_AVAILABLE = False
    td = None
    web = None


# =============================================================================
# CONSTANTS
# =============================================================================

TIDY3D_WORKBENCH_URL = "https://tidy3d.simulation.cloud/workbench"


def is_available() -> bool:
    """Check if Tidy3D cloud is available."""
    return TIDY3D_AVAILABLE


def upload_simulation(
    sim: Any,
    task_name: str = "HOMI_Device"
) -> Tuple[str, str]:
    """
    Upload a simulation to Tidy3D cloud.

    Args:
        sim: td.Simulation object
        task_name: Name for the task (will be prefixed with "HOMI_")

    Returns:
        Tuple of (task_id, web_url)

    Raises:
        RuntimeError: If Tidy3D not available or upload fails
    """
    if not TIDY3D_AVAILABLE:
        raise RuntimeError("Tidy3D is not installed. Install with: pip install 'pixcell[simulate]'")

    # Clean task name (remove spaces, limit length)
    clean_name = task_name.replace(" ", "_")[:50]
    full_name = f"HOMI_{clean_name}"

    # Upload to cloud
    task_id = web.upload(sim, task_name=full_name)

    # Generate workbench URL
    web_url = f"{TIDY3D_WORKBENCH_URL}?taskId={task_id}"

    return task_id, web_url


def estimate_simulation_cost(task_id: str) -> Optional[float]:
    """
    Estimate the cost of a simulation in FlexCredits.

    Args:
        task_id: Task ID from upload

    Returns:
        Estimated cost in FlexCredits, or None if unavailable
    """
    if not TIDY3D_AVAILABLE:
        return None

    try:
        return web.estimate_cost(task_id)
    except Exception:
        return None


def get_task_status(task_id: str) -> Optional[str]:
    """
    Get the current status of a simulation task.

    Possible statuses:
    - "draft": Task created but not started
    - "queued": Waiting to run
    - "preprocess": Being preprocessed
    - "running": Simulation in progress
    - "postprocess": Processing results
    - "success": Completed successfully
    - "error": Failed with error

    Args:
        task_id: Task ID from upload

    Returns:
        Status string, or None if unavailable
    """
    if not TIDY3D_AVAILABLE:
        return None

    try:
        info = web.get_info(task_id)
        return info.status
    except Exception:
        return None


def run_simulation(task_id: str) -> bool:
    """
    Start running a simulation that has been uploaded.

    Args:
        task_id: Task ID from upload

    Returns:
        True if started successfully
    """
    if not TIDY3D_AVAILABLE:
        return False

    try:
        web.start(task_id)
        return True
    except Exception:
        return False


def get_task_info(task_id: str) -> Optional[dict]:
    """
    Get detailed information about a task.

    Args:
        task_id: Task ID

    Returns:
        Dict with task info, or None if unavailable
    """
    if not TIDY3D_AVAILABLE:
        return None

    try:
        info = web.get_info(task_id)
        return {
            "task_id": task_id,
            "status": info.status,
            "task_name": getattr(info, 'taskName', None),
            "created_at": getattr(info, 'createdAt', None),
        }
    except Exception:
        return None


def get_workbench_url(task_id: str) -> str:
    """
    Get the Tidy3D Workbench URL for a task.

    Args:
        task_id: Task ID

    Returns:
        Workbench URL string
    """
    return f"{TIDY3D_WORKBENCH_URL}?taskId={task_id}"


def validate_api_key(api_key: str) -> bool:
    """
    Validate a Tidy3D API key by attempting to list tasks.

    Args:
        api_key: API key to validate

    Returns:
        True if valid, False otherwise
    """
    if not TIDY3D_AVAILABLE:
        return False

    import os
    old_key = os.environ.get("SIMCLOUD_APIKEY")

    try:
        os.environ["SIMCLOUD_APIKEY"] = api_key
        # Try to get task list (will fail if key is invalid)
        web.get_tasks(num_tasks=1)
        return True
    except Exception:
        return False
    finally:
        # Restore old key
        if old_key:
            os.environ["SIMCLOUD_APIKEY"] = old_key
        elif "SIMCLOUD_APIKEY" in os.environ:
            del os.environ["SIMCLOUD_APIKEY"]
