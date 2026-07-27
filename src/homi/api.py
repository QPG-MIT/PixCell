"""
HOMI REST API - FastAPI interface to the pipeline.

Provides HTTP endpoints for:
- Paper extraction (PDF → device images)
- GDS generation (image → GDS)
- Parameter optimization (JEE)
- Explorer generation (Weber)
- Simulation (Tidy3D)
- PDK migration

Start with:
    uvicorn homi.api:app --host 0.0.0.0 --port 8000
    # or
    homi api
"""

from __future__ import annotations

import asyncio
import json
import shutil
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from homi.paths import projects_dir

app = FastAPI(
    title="HOMI API",
    description="Photonic Multimodal Intelligence — Paper to GDS Pipeline",
    version="1.0.0",
)

# Thread pool for CPU-bound tasks
executor = ThreadPoolExecutor(max_workers=4)

# In-memory task store (swap for Redis/DB in production)
_tasks: Dict[str, Dict[str, Any]] = {}

# Base directory for projects
PROJECTS_DIR = projects_dir()
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# Models
# =============================================================================


class ProjectInfo(BaseModel):
    name: str
    created_at: str
    step: int = 0
    has_pdf: bool = False
    has_device_bw: bool = False
    has_footprint: bool = False
    has_gds: bool = False


class FootprintInput(BaseModel):
    length_um: float
    width_um: float


class GenerateRequest(BaseModel):
    project: str
    # agent mode (default): blind Phase-A recreation worker + conductor gate
    cli: Optional[str] = None            # worker alias (pane) / backend hint
    worker_model: Optional[str] = None
    worker_effort: Optional[str] = None
    # baseline mode: the legacy multi-seed sweep (the paper's measured
    # chatbot-era baseline) — set baseline=true to use the fields below
    baseline: bool = False
    preset: str = "balanced"
    model: str = "gemini/gemini-3-flash-preview"
    base_seed: int = 1333
    phase1_only: bool = False


class OptimizeRequest(BaseModel):
    project: str
    script_path: Optional[str] = None
    method: str = "nelder-mead"
    max_iterations: int = 150
    explore: bool = False


class SimulateRequest(BaseModel):
    project: str
    gds_path: Optional[str] = None
    material: str = "Silicon (SOI)"
    thickness_nm: float = 220
    wavelength_um: float = 1.55


class MigrateRequest(BaseModel):
    project: str
    gds_path: Optional[str] = None
    target_pdk: str
    run_drc: bool = True


class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    progress: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


# =============================================================================
# Helpers
# =============================================================================


def _get_project_dir(name: str) -> Path:
    d = PROJECTS_DIR / name
    if not d.exists():
        raise HTTPException(404, f"Project '{name}' not found")
    return d


def _create_task(message: str) -> str:
    task_id = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    _tasks[task_id] = {
        "task_id": task_id,
        "status": "pending",
        "progress": 0.0,
        "message": message,
        "result": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }
    return task_id


def _update_task(task_id: str, **kwargs):
    if task_id in _tasks:
        _tasks[task_id].update(kwargs)
        _tasks[task_id]["updated_at"] = datetime.now().isoformat()


# =============================================================================
# Project management
# =============================================================================


@app.get("/projects", response_model=List[ProjectInfo])
def list_projects():
    """List all projects."""
    results = []
    for d in sorted(PROJECTS_DIR.iterdir()):
        if d.is_dir() and (d / "state.json").exists():
            state = json.loads((d / "state.json").read_text())
            results.append(ProjectInfo(
                name=d.name,
                created_at=state.get("created_at", ""),
                step=state.get("step", 0),
                has_pdf=(d / "paper.pdf").exists(),
                has_device_bw=(d / "device_bw.png").exists(),
                has_footprint=(d / "footprint.json").exists() or (d / "component" / "footprint.json").exists(),
                has_gds=(d / "output" / "best.gds").exists(),
            ))
    return results


@app.post("/projects/{name}")
def create_project(name: str):
    """Create a new project."""
    d = PROJECTS_DIR / name
    if d.exists():
        raise HTTPException(409, f"Project '{name}' already exists")
    d.mkdir(parents=True)
    state = {"name": name, "created_at": datetime.now().isoformat(), "step": 0}
    (d / "state.json").write_text(json.dumps(state, indent=2))
    return {"project": name, "path": str(d)}


@app.get("/projects/{name}")
def get_project(name: str):
    """Get project details."""
    d = _get_project_dir(name)
    state = json.loads((d / "state.json").read_text())
    return state


# =============================================================================
# Extract
# =============================================================================


@app.post("/projects/{name}/upload")
async def upload_paper(name: str, file: UploadFile = File(...)):
    """Upload a PDF or image to a project."""
    d = _get_project_dir(name)

    suffix = Path(file.filename).suffix.lower()
    if suffix == ".pdf":
        dest = d / "paper.pdf"
    else:
        dest = d / f"device_upload{suffix}"

    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    return {"uploaded": str(dest), "size_bytes": len(content)}


@app.post("/projects/{name}/extract", response_model=TaskStatus)
def extract_images(name: str, cli: Optional[str] = None):
    """Dispatch the extraction agent (agent-first perception; Gemini only for
    the B&W raster) — the same path as `homi extract`. Async; poll
    /tasks/{task_id}. Success is judged by artifacts on disk: the task pair
    (device_bw.png + footprint.json) exists, never a worker's claim."""
    from homi import dispatch

    d = _get_project_dir(name)
    pdf_path = d / "paper.pdf"
    if pdf_path.exists():
        input_path, input_kind = pdf_path, "pdf"
    else:
        imgs = [p for ext in ("*.png", "*.jpg", "*.jpeg") for p in d.glob(ext)
                if p.name != "device_bw.png"]
        if not imgs:
            raise HTTPException(400, "No paper.pdf or source image in project. Upload first.")
        input_path, input_kind = imgs[0], "image"

    task_id = _create_task(f"Extracting device from {name}")

    def _run():
        try:
            _update_task(task_id, status="running", progress=0.1,
                         message="extraction agent dispatched")
            result = dispatch.dispatch_extractor_agent(
                str(input_path), str(d), input_kind=input_kind, cli=cli
            )
            if result["status"] == "ok":
                _update_task(task_id, status="completed", progress=1.0, result={
                    "backend": result["backend"],
                    "artifacts": result.get("artifacts"),
                })
            else:
                _update_task(task_id, status="failed", error=(
                    result.get("error") or result.get("stderr_tail")
                    or (result.get("output_tail") or "")[-800:]
                ))
        except Exception as e:
            _update_task(task_id, status="failed", error=str(e))

    executor.submit(_run)
    return TaskStatus(**_tasks[task_id])


@app.post("/projects/{name}/footprint")
def set_footprint(name: str, footprint: FootprintInput):
    """Set device footprint dimensions."""
    d = _get_project_dir(name)
    fp_path = d / "footprint.json"
    data = {
        "footprint_um": [footprint.length_um, footprint.width_um],
        "length_um": footprint.length_um,
        "width_um": footprint.width_um,
    }
    fp_path.write_text(json.dumps(data, indent=2))
    return {"footprint": data, "path": str(fp_path)}


# =============================================================================
# Generate
# =============================================================================


@app.post("/projects/{name}/generate", response_model=TaskStatus)
def start_generation(name: str, req: GenerateRequest):
    """Start GDS generation (async). Returns task_id for polling.

    Default = the agent recreate loop: dispatch a blind Phase-A worker, then
    the conductor gate re-executes, re-scores, and checks parametricity —
    best.py/best.gds are promoted only if the gate passes (same path as
    `homi generate`). baseline=true runs the legacy multi-seed sweep."""
    d = _get_project_dir(name)
    task_id = _create_task(f"Generating GDS for {name}")

    if not req.baseline:

        def _run_agent():
            import shutil as _sh

            from homi import conductor, dispatch

            try:
                if not (d / "device_bw.png").exists() or not (d / "footprint.json").exists():
                    _update_task(task_id, status="failed",
                                 error="task pair missing: run /extract first "
                                       "(device_bw.png + footprint.json)")
                    return
                _update_task(task_id, status="running", progress=0.1,
                             message="Phase-A recreation worker dispatched "
                                     "(the agent is the optimizer)")
                workdir = d / "output" / "recreation_agent"
                workdir.mkdir(parents=True, exist_ok=True)
                result = dispatch.dispatch_agent(
                    "phase_a",
                    {"INPUT_DIR": str(d), "WORKDIR": str(workdir),
                     "GIT_RULE": "Do NOT run any git commands."},
                    workdir=str(workdir), cli=req.cli,
                    model=req.worker_model, effort=req.worker_effort,
                )
                if result["status"] != "ok":
                    _update_task(task_id, status="failed", error=(
                        result.get("error") or result.get("stderr_tail")
                        or (result.get("output_tail") or "")[-800:]
                    ))
                    return
                del _sh, conductor  # promotion is centralized
                from homi.conductor.promote import gate_and_promote

                _update_task(task_id, progress=0.8,
                             message="conductor gate: recompute IoU + claim + purity + knob response")
                try:
                    outcome = gate_and_promote(d, workdir)
                except FileNotFoundError as e:
                    _update_task(task_id, status="failed", error=str(e))
                    return
                if not outcome.promoted:
                    _update_task(task_id, status="failed",
                                 error=f"gate refused promotion (IoU={outcome.gate.iou:.4f}): "
                                       f"{'; '.join(outcome.reasons) or 'not verified'} — "
                                       f"worker artifacts kept in {workdir}")
                    return
                output_dir = d / "output"
                _update_task(task_id, status="completed", progress=1.0, result={
                    "verified": True,
                    "iou": outcome.gate.iou,
                    "best_py": str(output_dir / "best.py"),
                    "best_gds": str(output_dir / "best.gds"),
                })
            except Exception as e:
                _update_task(task_id, status="failed", error=str(e))

        executor.submit(_run_agent)
        return TaskStatus(**_tasks[task_id])

    from homi import gds_generation

    from homi.paths import michaelangelo_dir as _mdir

    michaelangelo_dir = _mdir()

    def _run():
        try:
            _update_task(task_id, status="running", progress=0.1)

            component_dir = d / "component"
            device_bw = d / "device_bw.png"
            footprint_json = d / "footprint.json"

            if not device_bw.exists():
                device_bw = component_dir / "component.png"
            if not device_bw.exists():
                _update_task(task_id, status="failed", error="No device image found")
                return

            # Setup if needed — signature: (component_dir: Path, device_bw_path: str, length, width)
            if not component_dir.exists():
                fp = json.loads(footprint_json.read_text())
                length = fp.get("footprint_um", [50])[0] if "footprint_um" in fp else fp.get("length_um", 50)
                width = fp.get("footprint_um", [0, 30])[1] if "footprint_um" in fp else fp.get("width_um", 30)
                gds_generation.setup_component_directory(
                    component_dir, str(device_bw), length, width
                )

            # Calibrate — signature: (component_dir: Path, michaelangelo_dir: Path)
            if not (component_dir / "calibration.json").exists():
                gds_generation.run_calibration(component_dir, michaelangelo_dir)

            _update_task(task_id, progress=0.2, message="Phase 1 starting")

            presets = {
                "quick": {"seed_range": 2, "additional_turns": 2, "num_parallel": 4},
                "balanced": {"seed_range": 6, "additional_turns": 3, "num_parallel": 8},
                "thorough": {"seed_range": 12, "additional_turns": 5, "num_parallel": 8},
                "maximum": {"seed_range": 20, "additional_turns": 8, "num_parallel": 12},
            }
            preset = presets[req.preset]

            # Phase 1 — signature: (component_dir: Path, michaelangelo_dir: Path, ...)
            gds_generation.run_phase1(
                component_dir, michaelangelo_dir,
                base_seed=req.base_seed,
                seed_range=preset["seed_range"],
                num_parallel=preset["num_parallel"],
                model=req.model,
            )
            _update_task(task_id, progress=0.6, message="Phase 1 complete")

            if not req.phase1_only:
                _update_task(task_id, progress=0.7, message="Phase 2 starting")
                gds_generation.run_phase2(
                    component_dir, michaelangelo_dir,
                    additional_turns=preset["additional_turns"],
                    num_parallel=preset["num_parallel"],
                    model=req.model,
                )
                _update_task(task_id, progress=0.9, message="Phase 2 complete")

            # Collect best — signature: (component_dir: Path, output_dir: Path)
            output_dir = d / "output"
            output_dir.mkdir(exist_ok=True)
            best = gds_generation.collect_best_output(component_dir, output_dir)

            _update_task(task_id, status="completed", progress=1.0, result=best)

        except Exception as e:
            _update_task(task_id, status="failed", error=str(e))

    executor.submit(_run)
    return TaskStatus(**_tasks[task_id])


# =============================================================================
# Task polling
# =============================================================================


@app.get("/tasks/{task_id}", response_model=TaskStatus)
def get_task(task_id: str):
    """Poll task status."""
    if task_id not in _tasks:
        raise HTTPException(404, f"Task '{task_id}' not found")
    return TaskStatus(**_tasks[task_id])


# =============================================================================
# Optimize
# =============================================================================


@app.post("/projects/{name}/optimize", response_model=TaskStatus)
def start_optimization(name: str, req: OptimizeRequest):
    """Start JEE parameter optimization (async)."""
    from homi import jee_integration

    d = _get_project_dir(name)
    task_id = _create_task(f"Optimizing {name}")

    script_path_str = req.script_path or str(d / "output" / "best.py")
    script_path = Path(script_path_str)
    if not script_path.exists():
        raise HTTPException(400, f"Script not found: {script_path}")

    def _run():
        try:
            _update_task(task_id, status="running", progress=0.1)

            target = d / "component" / "component.png"
            footprint = d / "component" / "footprint.json"
            cal_path = d / "output" / "jee_calibration.json"
            output_dir = d / "output" / "jee_output"
            output_dir.mkdir(exist_ok=True)

            # prepare_calibration signature: (target_image_path: Path, footprint_json_path: Path, output_path: Path)
            if footprint.exists() and target.exists():
                jee_integration.prepare_calibration(target, footprint, cal_path)

            config = jee_integration.get_jee_default_config()
            config["method"] = "Nelder-Mead" if req.method == "nelder-mead" else "Powell"
            config["max_iterations"] = req.max_iterations

            _update_task(task_id, progress=0.3, message="Optimization running")

            # All jee functions take Path objects
            if req.explore:
                result = jee_integration.run_jee_exploration(
                    script_path, target, cal_path, output_dir
                )
            else:
                result = jee_integration.run_jee_optimization(
                    script_path, target, cal_path, output_dir, config
                )

            _update_task(task_id, status="completed", progress=1.0, result=result)
        except Exception as e:
            _update_task(task_id, status="failed", error=str(e))

    executor.submit(_run)
    return TaskStatus(**_tasks[task_id])


# =============================================================================
# Simulate
# =============================================================================


@app.post("/projects/{name}/simulate", response_model=TaskStatus)
def start_simulation(name: str, req: SimulateRequest):
    """Upload GDS to Tidy3D for simulation."""
    from homi import flex_integration
    import os
    import gdsfactory as gf

    d = _get_project_dir(name)
    gds_path = req.gds_path or str(d / "output" / "best.gds")
    if not Path(gds_path).exists():
        raise HTTPException(400, f"GDS not found: {gds_path}")

    api_key = os.environ.get("TIDY3D_API_KEY")
    if not api_key:
        raise HTTPException(400, "TIDY3D_API_KEY not set")

    task_id = _create_task(f"Simulating {name}")

    def _run():
        try:
            _update_task(task_id, status="running", progress=0.3)

            # Load GDS into a gdsfactory Component
            component = gf.import_gds(gds_path)

            # create_and_upload_simulation signature: (component, config: Dict, api_key: str)
            config = {
                "material": req.material,
                "thickness_nm": req.thickness_nm,
                "wavelength_um": req.wavelength_um,
                "layers": [(1, 0)],
            }
            result = flex_integration.create_and_upload_simulation(component, config, api_key)
            _update_task(task_id, status="completed", progress=1.0, result=result)
        except Exception as e:
            _update_task(task_id, status="failed", error=str(e))

    executor.submit(_run)
    return TaskStatus(**_tasks[task_id])


# =============================================================================
# Migrate
# =============================================================================


def _unwrap_mcp(res):
    # @tool_handler returns MCP [TextContent(json)] — unwrap to the dict.
    if isinstance(res, list):
        return json.loads(res[0].text)
    return res


@app.post("/projects/{name}/migrate")
def migrate_to_pdk(name: str, req: MigrateRequest):
    """Migrate GDS to a target PDK — the same PDKServer handlers `homi
    migrate` and the homi-pdk MCP tools drive (there is no separate
    pdk_manager module)."""
    import asyncio

    from gg.servers.pdk_server import PDKServer

    d = _get_project_dir(name)
    gds_path = req.gds_path or str(d / "output" / "best.gds")
    if not Path(gds_path).exists():
        raise HTTPException(400, f"GDS not found: {gds_path}")

    output_path = d / "output" / f"best_{req.target_pdk}.gds"
    srv = PDKServer()
    result = _unwrap_mcp(asyncio.run(srv._convert_to_pdk({
        "gds_path": str(gds_path),
        "pdk_name": req.target_pdk,
        "output_path": str(output_path),
    })))
    if result.get("status") != "success":
        raise HTTPException(500, f"conversion failed: {result.get('error', result)}")

    response = {"converted": str(output_path), "pdk": req.target_pdk}

    if req.run_drc:
        drc = _unwrap_mcp(asyncio.run(srv._run_drc({
            "gds_path": str(output_path),
            "pdk_name": req.target_pdk,
        })))
        violations = drc.get("violations") or []
        response["drc_violations"] = violations
        response["drc_passed"] = not violations

    return response


# =============================================================================
# File downloads
# =============================================================================


@app.get("/projects/{name}/gds")
def download_gds(name: str):
    """Download the best GDS file."""
    d = _get_project_dir(name)
    gds_path = d / "output" / "best.gds"
    if not gds_path.exists():
        raise HTTPException(404, "No GDS file generated yet")
    return FileResponse(gds_path, filename=f"{name}.gds", media_type="application/octet-stream")


@app.get("/projects/{name}/script")
def download_script(name: str):
    """Download the best GDSFactory script."""
    d = _get_project_dir(name)
    script_path = d / "output" / "best.py"
    if not script_path.exists():
        raise HTTPException(404, "No script generated yet")
    return FileResponse(script_path, filename=f"{name}.py", media_type="text/x-python")


# =============================================================================
# PDK info
# =============================================================================


@app.get("/pdks")
def list_pdks():
    """List available PDKs (same PDKServer handler as the MCP tool)."""
    import asyncio

    from gg.servers.pdk_server import PDKServer

    return _unwrap_mcp(asyncio.run(PDKServer()._list_available_pdks({})))


@app.get("/models")
def get_models():
    """List available VLM models."""
    from homi.model_client import list_models
    return list_models()


@app.get("/presets")
def list_presets():
    """List generation presets."""
    return {
        "quick": {"seeds": 5, "turns": 2, "time_est": "~5 min"},
        "balanced": {"seeds": 13, "turns": 3, "time_est": "~10 min"},
        "thorough": {"seeds": 25, "turns": 5, "time_est": "~20 min"},
        "maximum": {"seeds": 41, "turns": 8, "time_est": "~40 min"},
    }


# =============================================================================
# Health
# =============================================================================


@app.get("/health")
def health():
    """Health check."""
    return {"status": "ok", "version": "1.0.0"}
