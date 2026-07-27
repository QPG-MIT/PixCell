"""
Project Management Module

Manages HOMI project directories and state persistence.
"""

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


def get_projects_dir() -> Path:
    """Get the projects directory path."""
    # Default to projects/ in the HOMI root
    homi_root = Path(__file__).parent.parent
    projects_dir = homi_root / "projects"
    projects_dir.mkdir(exist_ok=True)
    return projects_dir


def create_project(name: str, pdf_path: Optional[str] = None) -> Path:
    """
    Create a new project directory.

    Args:
        name: Project name (will be sanitized)
        pdf_path: Optional path to PDF to copy into project

    Returns:
        Path to the created project directory
    """
    # Sanitize name
    safe_name = "".join(c for c in name if c.isalnum() or c in "._- ")
    safe_name = safe_name.strip().replace(" ", "_")

    if not safe_name:
        safe_name = f"project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    project_dir = get_projects_dir() / safe_name

    # Handle name collision
    if project_dir.exists():
        timestamp = datetime.now().strftime('%H%M%S')
        project_dir = get_projects_dir() / f"{safe_name}_{timestamp}"

    # Create directory structure
    project_dir.mkdir(parents=True)
    (project_dir / "extracted_images").mkdir()
    (project_dir / "bw_variants").mkdir()
    (project_dir / "component").mkdir()
    (project_dir / "output").mkdir()

    # Copy PDF if provided
    if pdf_path and os.path.exists(pdf_path):
        shutil.copy2(pdf_path, project_dir / "paper.pdf")

    # Initialize state
    state = {
        "name": safe_name,
        "created_at": datetime.now().isoformat(),
        "step": 1,
        "pdf_path": str(project_dir / "paper.pdf") if pdf_path else None
    }
    save_project_state(project_dir, state)

    return project_dir


def save_project_state(project_dir: Path, state: dict):
    """
    Save project state to JSON file.

    Args:
        project_dir: Path to project directory
        state: State dict to save
    """
    project_dir = Path(project_dir)
    state["updated_at"] = datetime.now().isoformat()

    state_path = project_dir / "state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)


def load_project_state(project_dir: Path) -> dict:
    """
    Load project state from JSON file.

    Args:
        project_dir: Path to project directory

    Returns:
        State dict (empty dict if not found)
    """
    project_dir = Path(project_dir)
    state_path = project_dir / "state.json"

    if state_path.exists():
        with open(state_path) as f:
            return json.load(f)

    return {}


def get_project_list() -> list[dict]:
    """
    Get list of all projects with their states.

    Returns:
        List of project info dicts, sorted by most recent first
    """
    projects_dir = get_projects_dir()
    projects = []

    for project_path in projects_dir.iterdir():
        if not project_path.is_dir():
            continue

        state = load_project_state(project_path)
        if state:
            state["path"] = str(project_path)
            projects.append(state)
        else:
            # Project without state - add minimal info
            projects.append({
                "name": project_path.name,
                "path": str(project_path),
                "step": 0,
                "created_at": None
            })

    # Sort by updated_at or created_at
    projects.sort(
        key=lambda p: p.get("updated_at") or p.get("created_at") or "",
        reverse=True
    )

    return projects


def delete_project(project_dir: Path) -> bool:
    """
    Delete a project directory.

    Args:
        project_dir: Path to project directory

    Returns:
        True if deleted successfully
    """
    project_dir = Path(project_dir)
    projects_dir = get_projects_dir()

    # Safety check - only delete if it's in the projects directory
    if not str(project_dir).startswith(str(projects_dir)):
        return False

    if project_dir.exists():
        shutil.rmtree(project_dir)
        return True

    return False


def get_project_summary(project_dir: Path) -> dict:
    """
    Get a summary of the project status.

    Args:
        project_dir: Path to project directory

    Returns:
        Summary dict with status of each step
    """
    project_dir = Path(project_dir)
    state = load_project_state(project_dir)

    summary = {
        "name": state.get("name", project_dir.name),
        "step": state.get("step", 0),
        "has_pdf": (project_dir / "paper.pdf").exists(),
        "has_selected_image": (project_dir / "selected_image.png").exists(),
        "has_bw_image": (project_dir / "device_bw.png").exists(),
        "has_footprint": (project_dir / "component" / "footprint.json").exists(),
        "phase1_complete": (project_dir / "component" / "phase1" / "exploration_summary.json").exists(),
        "phase2_complete": (project_dir / "component" / "phase2" / "extended_exploration_summary.json").exists(),
        "has_output": (project_dir / "output" / "best.gds").exists()
    }

    # Get best result if available
    if summary["has_output"]:
        output_summary = project_dir / "output" / "summary.json"
        if output_summary.exists():
            with open(output_summary) as f:
                result = json.load(f)
                summary["best_iou"] = result.get("iou")
                summary["best_seed"] = result.get("seed")
                summary["best_sse"] = result.get("sse")

    # Check for JEE optimization
    jee_result_path = project_dir / "output" / "jee_optimization_result.json"
    summary["jee_optimized"] = jee_result_path.exists()

    if summary["jee_optimized"]:
        with open(jee_result_path) as f:
            jee_result = json.load(f)
            summary["jee_improvement_pct"] = jee_result.get("improvement_pct", 0)
            summary["jee_best_sse"] = jee_result.get("best_sse")

    return summary


def update_project_step(project_dir: Path, step: int, extra_data: Optional[dict] = None):
    """
    Update project to a new step, optionally adding extra data.

    Args:
        project_dir: Path to project directory
        step: New step number
        extra_data: Optional additional data to merge into state
    """
    state = load_project_state(project_dir)
    state["step"] = step

    if extra_data:
        state.update(extra_data)

    save_project_state(project_dir, state)


def revert_to_step(project_dir: Path, target_step: int) -> dict:
    """
    Revert a project to a specific step, deleting all files/data from later steps.

    Args:
        project_dir: Path to project directory
        target_step: Step to revert to (1-8)

    Returns:
        Dict with:
            - success: bool
            - deleted_files: list of deleted paths
            - deleted_dirs: list of deleted directories
            - cleared_state_keys: list of state keys cleared
            - error: optional error message
    """
    project_dir = Path(project_dir)
    result = {
        "success": False,
        "deleted_files": [],
        "deleted_dirs": [],
        "cleared_state_keys": [],
        "error": None
    }

    try:
        # Load current state
        state = load_project_state(project_dir)
        current_step = state.get("step", 1)

        if target_step >= current_step:
            result["error"] = f"Cannot revert: target step {target_step} >= current step {current_step}"
            return result

        if target_step < 1:
            result["error"] = "Cannot revert below step 1"
            return result

        # Get cleanup actions
        cleanup_actions = _get_cleanup_actions(project_dir, target_step, current_step)

        # Execute file deletions
        for file_path in cleanup_actions["files"]:
            fp = Path(file_path)
            if fp.exists():
                fp.unlink()
                result["deleted_files"].append(str(file_path))

        # Execute directory deletions
        for dir_path in cleanup_actions["dirs"]:
            dp = Path(dir_path)
            if dp.exists():
                shutil.rmtree(dp)
                result["deleted_dirs"].append(str(dir_path))

        result["cleared_state_keys"] = cleanup_actions["state_keys"]

        # Update state.json - remove keys and set new step
        for key in cleanup_actions["state_keys"]:
            state.pop(key, None)

        state["step"] = target_step
        state["reverted_at"] = datetime.now().isoformat()
        state["reverted_from_step"] = current_step
        save_project_state(project_dir, state)

        result["success"] = True
        return result

    except Exception as e:
        result["error"] = str(e)
        return result


def _get_cleanup_actions(project_dir: Path, target_step: int, current_step: int) -> dict:
    """
    Determine what files, directories, and state keys to clean up when reverting.

    Args:
        project_dir: Path to project directory
        target_step: Step to revert to
        current_step: Current highest step

    Returns:
        Dict with keys: files, dirs, state_keys
    """
    files = []
    dirs = []
    state_keys = []

    # Revert from step N means delete data created transitioning TO step N
    # If we're reverting to step 2, we delete data from steps 3, 4, 5, etc.

    # Step 2→3 transition cleanup (if reverting to step 2 or lower)
    if target_step < 3 <= current_step:
        files.extend([
            project_dir / "selected_image.png",
            project_dir / "device_subfigure.png",
        ])
        dirs.append(project_dir / "bw_variants")
        state_keys.extend(["selected_image_idx", "bw_variants", "bw_refinement_history"])

    # Step 3→3.5 transition cleanup (if reverting to step 3 or lower)
    # This handles B&W selection → footprint extraction
    if target_step < 3.5 and current_step >= 3.5:
        files.append(project_dir / "device_bw.png")
        state_keys.extend(["selected_bw_idx"])

    # Step 3.5→4 (footprint extraction → confirmation)
    if target_step < 4 <= current_step:
        state_keys.extend(["footprint_extracted", "footprint"])

    # Step 4→5 transition cleanup (if reverting to step 4 or lower)
    if target_step < 5 <= current_step:
        files.extend([
            project_dir / "component" / "footprint.json",
            project_dir / "component" / "component.png",
            project_dir / "component" / "prompt.md",
            project_dir / "component" / "iteration_prompt.md",
            project_dir / "component" / "calibration.json",
        ])
        state_keys.append("component_dir")

    # Step 5→5.5 and beyond cleanup (if reverting to step 5 or lower)
    if target_step < 5.5 and current_step >= 5.5:
        # Standard single-component generation
        dirs.extend([
            project_dir / "component" / "phase1",
            project_dir / "component" / "phase2",
        ])
        # Output files
        files.extend([
            project_dir / "output" / "best.py",
            project_dir / "output" / "best.gds",
            project_dir / "output" / "best_raster.png",
            project_dir / "output" / "best_overlay.png",
            project_dir / "output" / "summary.json",
            project_dir / "output" / "calibration.json",
        ])
        state_keys.extend(["best_result", "generation_complete"])

    # Step 5.5→6 cleanup (JEE files - if reverting to step 5.5 or lower)
    if target_step < 6 <= current_step:
        files.extend([
            project_dir / "output" / "jee_optimization_result.json",
            project_dir / "output" / "best_pre_jee.gds",
            project_dir / "output" / "best_pre_jee.py",
        ])
        dirs.append(project_dir / "output" / "jee_results")
        state_keys.append("calibration_ready")

    # Note: Steps 7 and 8 are session-only, no persistent files to delete
    # Session state cleanup is handled separately in app.py

    return {"files": files, "dirs": dirs, "state_keys": state_keys}


def infer_project_step(project_dir: Path) -> float:
    """
    Infer project step from existing files.

    Used to repair projects missing state.json.

    Args:
        project_dir: Path to project directory

    Returns:
        Inferred step number (1-6)
    """
    project_dir = Path(project_dir)

    # Check for output (step 6)
    if (project_dir / "output" / "best.gds").exists():
        return 6

    # Check for phase1 results (step 5.5) - multiple architectures
    phase1_standard = project_dir / "component" / "phase1"
    phase1_benchmark = any(project_dir.glob("benchmark_*/phase1"))
    phase1_nested = any(project_dir.glob("*/benchmark_*/phase1"))  # FINAL_*/benchmark_*/phase1
    if phase1_standard.exists() or phase1_benchmark or phase1_nested:
        return 5.5

    # Check for calibration (step 5)
    if (project_dir / "component" / "calibration.json").exists():
        return 5

    # Check for footprint (step 4)
    if (project_dir / "component" / "footprint.json").exists():
        return 4

    # Check for B&W image (step 3)
    if (project_dir / "device_bw.png").exists():
        return 3

    # Check for extracted images (step 2)
    extracted = project_dir / "extracted_images"
    if extracted.exists() and any(extracted.iterdir()):
        return 2

    return 1


def repair_missing_state_files() -> dict:
    """
    Create state.json for projects missing it.

    Infers the step from existing files and creates a minimal state.json.

    Returns:
        Dict with keys: repaired (list of {name, step}), skipped (list of names), errors (list of {name, error})
    """
    results = {"repaired": [], "skipped": [], "errors": []}

    for project_path in get_projects_dir().iterdir():
        if not project_path.is_dir():
            continue

        state_path = project_path / "state.json"
        if state_path.exists():
            results["skipped"].append(project_path.name)
            continue

        try:
            step = infer_project_step(project_path)
            state = {
                "name": project_path.name,
                "created_at": None,  # Unknown
                "step": step,
                "repaired": True,
                "repaired_at": datetime.now().isoformat()
            }
            save_project_state(project_path, state)
            results["repaired"].append({"name": project_path.name, "step": step})
        except Exception as e:
            results["errors"].append({"name": project_path.name, "error": str(e)})

    return results


def get_session_keys_for_step(step: int) -> list:
    """
    Get session state keys that should be cleared when reverting to a step.

    Args:
        step: Target step to revert to

    Returns:
        List of session state keys to clear
    """
    keys_to_clear = []

    # Keys created by step 7 (explorer)
    if step < 7:
        keys_to_clear.extend([
            "explorer_script_source",
            "explorer_analysis",
            "explorer_slot_config",
            "explorer_params",
            "explorer_slider_values",
            "explorer_custom_primitives",
        ])

    # Keys created by step 8 (simulation)
    if step < 8:
        keys_to_clear.extend([
            "sim_component",
            "sim_api_key",
            "sim_api_key_valid",
            "sim_material",
            "sim_thickness_nm",
            "sim_wavelength_um",
            "sim_layers",
            "sim_custom_core_n",
            "sim_custom_clad_n",
            "sim_task_history",
            "sim_last_result",
        ])

    # JEE state keys (step 5.5→6)
    if step < 6:
        keys_to_clear.extend([
            "jee_running",
            "jee_complete",
            "jee_result",
        ])

    # Generation state keys (step 5)
    if step < 5:
        keys_to_clear.extend([
            "phase1_running",
            "phase2_running",
            "generation_complete",
        ])

    return keys_to_clear
