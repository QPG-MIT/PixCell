"""Budgeted batched parameter sweeps measured by small full-wave simulations.

Measure-only: this module contains NO search logic and NO device knowledge.
It grids over the *declared* top-level tunables of a device script (the same
`name = value` convention as homi/spec_optimization and jee_integration),
builds each geometry, uploads one small FDTD task per grid point, and gates
every start behind a total-cost budget: all tasks are uploaded first, their
estimates summed, and if the sum exceeds the budget NOTHING is started.

Port placement is geometric: guide centers are found by slicing the written
GDS at an inset from each x-extreme (no reliance on component metadata).
The figure of merit "coupling_ratio" assumes a 2-in / 2-out geometry:
source into the top-left guide, monitors on both right guides
(bar = top-right, cross = bottom-right), ratio = P_cross / (P_bar + P_cross).

Results are returned and saved as a matrix JSON:
{axes: {name: [values]}, cells: [{params, ratio, total_T, task_id, billed}]}
"""

from __future__ import annotations

import itertools
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_TIMEOUT_S = 120
WL0_UM = 1.55
PORT_INSET_UM = 2.0
PLANE_YZ_UM = (1.4, 1.6)
RUN_TIME_S = 4e-12
MIN_STEPS_PER_WVL = 12
POLL_INTERVAL_S = 10
POLL_MAX_S = 3600


def patch_tunables(source: str, params: dict) -> str:
    """Replace top-level `name = value` assignments; error on missing names."""
    for name, value in params.items():
        new, n = re.subn(rf"^{re.escape(name)}\s*=.*$", f"{name} = {value!r}",
                         source, count=1, flags=re.M)
        if n == 0:
            raise ValueError(f"tunable {name!r} not found as a top-level assignment")
        source = new
    return source


def build_gds(script_source: str, workdir: Path) -> Path:
    """Run the patched script in workdir; it must write device.gds beside itself."""
    script = workdir / "device.py"
    script.write_text(script_source)
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=SCRIPT_TIMEOUT_S, cwd=str(workdir),
    )
    gds = workdir / "device.gds"
    if proc.returncode != 0 or not gds.exists():
        raise RuntimeError(f"script failed rc={proc.returncode}: {proc.stderr[-300:]}")
    return gds


def guide_centers(gds_path: Path, x: float, layer=(1, 0)) -> list[float]:
    """y-centers of disjoint material intervals crossing vertical line x, top first."""
    import gdstk

    lib = gdstk.read_gds(str(gds_path))
    ys: list[float] = []
    for cell in lib.top_level():
        if "$$$" in cell.name:
            continue
        for poly in cell.get_polygons(depth=None, layer=layer[0], datatype=layer[1]):
            pts = poly.points
            n = len(pts)
            for i in range(n):
                (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
                if (x0 - x) * (x1 - x) < 0:
                    t = (x - x0) / (x1 - x0)
                    ys.append(y0 + t * (y1 - y0))
    if len(ys) < 2:
        raise RuntimeError(f"no material crossing x={x}")
    ys.sort()
    # pair successive crossings into intervals, merge near-degenerate splits
    intervals = [(ys[i], ys[i + 1]) for i in range(0, len(ys) - 1, 2)]
    merged: list[list[float]] = []
    for lo, hi in intervals:
        if merged and lo - merged[-1][1] < 0.05:
            merged[-1][1] = hi
        else:
            merged.append([lo, hi])
    centers = [(lo + hi) / 2 for lo, hi in merged]
    centers.sort(reverse=True)
    return centers


def _make_simulation(gds_path: Path, stack: dict, api_key: str):
    """Small single-frequency simulation with geometric port placement."""
    import gdsfactory as gf
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d.constants import C_0

    from flex.core.simulation import create_simulation_from_component

    component = gf.import_gds(gds_path)
    sim = create_simulation_from_component(
        component=component,
        layers=[(1, 0)],
        material="Silicon (SOI)",
        thickness_nm=int(float(stack["thickness_um"]) * 1000),
        wavelength_um=WL0_UM,
        api_key=api_key,
        custom_core_n=float(stack["core_n"]),
        custom_clad_n=float(stack["clad_n"]),
        config={"min_steps_per_wvl": MIN_STEPS_PER_WVL},
    )
    xmin, xmax = component.xmin, component.xmax
    x_in, x_out = xmin + PORT_INSET_UM, xmax - PORT_INSET_UM
    in_centers = guide_centers(gds_path, x_in)
    out_centers = guide_centers(gds_path, x_out)
    z_mid = float(stack["thickness_um"]) / 2
    plane = (0, *PLANE_YZ_UM)
    f0 = C_0 / WL0_UM
    source = td.ModeSource(
        center=(x_in, in_centers[0], z_mid), size=plane,
        source_time=td.GaussianPulse(freq0=f0, fwidth=f0 / 10),
        direction="+", mode_spec=td.ModeSpec(num_modes=1), mode_index=0,
    )
    monitors = [
        td.ModeMonitor(center=(x_out, out_centers[0], z_mid), size=plane,
                       freqs=[f0], mode_spec=td.ModeSpec(num_modes=1), name="bar"),
        td.ModeMonitor(center=(x_out, out_centers[-1], z_mid), size=plane,
                       freqs=[f0], mode_spec=td.ModeSpec(num_modes=1), name="cross"),
    ]
    return sim.updated_copy(sources=[source], monitors=monitors, run_time=RUN_TIME_S)


def _read_api_key() -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    m = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text()) if cfg.exists() else None
    if not m:
        raise RuntimeError("no apikey in ~/.tidy3d/config")
    return m.group(1)


def run_sweep(script_path: str, stack_json_path: str, sweep: dict, fom: str,
              budget_fc: float, out_path: str | None = None, dry_run: bool = False) -> dict:
    """Grid-sweep declared tunables; upload all, gate on summed estimate, measure.

    sweep: {tunable_name: [values, ...], ...} — full cartesian grid.
    Returns the matrix dict; aborts (starting nothing) if estimates exceed budget_fc.
    """
    if fom != "coupling_ratio":
        raise ValueError(f"unsupported fom {fom!r}")
    source = Path(script_path).read_text()
    stack = json.loads(Path(stack_json_path).read_text())
    names = list(sweep.keys())
    grid = list(itertools.product(*(sweep[n] for n in names)))
    cells = [{"params": dict(zip(names, combo))} for combo in grid]

    result = {"axes": {n: list(sweep[n]) for n in names}, "fom": fom,
              "stack": stack_json_path, "script": script_path,
              "budget_fc": budget_fc, "status": "dry_run", "cells": cells}

    workdirs = []
    tmp_root = Path(tempfile.mkdtemp(prefix="sweep_"))
    for i, cell in enumerate(cells):
        wd = tmp_root / f"pt{i:03d}"
        wd.mkdir(parents=True)
        try:
            gds = build_gds(patch_tunables(source, cell["params"]), wd)
            cell["n_in_guides"] = len(guide_centers(gds, PORT_INSET_UM + _gds_xmin(gds)))
            workdirs.append((wd, gds))
        except Exception as e:  # one bad grid point must not kill the batch
            cell["build_error"] = str(e)[:200]
            workdirs.append((wd, None))
    if dry_run:
        return _finish(result, out_path)

    from flex.core.cloud import (estimate_simulation_cost, get_task_status,
                                 run_simulation, upload_simulation)
    api_key = _read_api_key()
    tasks = []
    for cell, (wd, gds) in zip(cells, workdirs):
        if gds is None:
            continue
        sim = _make_simulation(gds, stack, api_key)
        tag = "_".join(f"{k}{v}" for k, v in cell["params"].items())[:40]
        task_id, _url = upload_simulation(sim, task_name=f"sweep_{tag}")
        est = estimate_simulation_cost(task_id)
        cell["task_id"], cell["estimate_fc"] = task_id, est
        tasks.append(task_id)
        if out_path:  # crash-safe registry, updated per upload
            reg = Path(out_path).with_name("tasks.json")
            reg.write_text(json.dumps(
                [{"params": c["params"], "task_id": c.get("task_id"),
                  "estimate_fc": c.get("estimate_fc")} for c in cells
                 if c.get("task_id")], indent=1))
    total_est = sum(c["estimate_fc"] or 0.0 for c in cells)
    result["total_estimate_fc"] = round(total_est, 3)
    if total_est > budget_fc:
        result["status"] = "aborted_budget"
        return _finish(result, out_path)

    for tid in tasks:
        run_simulation(tid)
    deadline = time.time() + POLL_MAX_S
    pending = set(tasks)
    while pending and time.time() < deadline:
        for tid in list(pending):
            st = get_task_status(tid)
            if st in ("success", "error", "diverged"):
                pending.discard(tid)
        if pending:
            time.sleep(POLL_INTERVAL_S)

    from tidy3d import web
    for cell, (wd, _gds) in zip(cells, workdirs):
        tid = cell.get("task_id")
        if tid is None:
            continue
        st = get_task_status(tid)
        cell["task_status"] = st
        if st == "success":
            data = web.load(tid, path=str(wd / "data.hdf5"))
            p_bar = float(abs(data["bar"].amps.sel(direction="+", mode_index=0).values[0]) ** 2)
            p_cross = float(abs(data["cross"].amps.sel(direction="+", mode_index=0).values[0]) ** 2)
            total = p_bar + p_cross
            cell["ratio"] = round(p_cross / total, 4) if total > 0 else None
            cell["total_T"] = round(total, 4)
        try:
            cell["billed_fc"] = web.real_cost(tid)
        except Exception:
            cell["billed_fc"] = cell.get("estimate_fc")
    result["status"] = "complete"
    result["total_billed_fc"] = round(sum(c.get("billed_fc") or 0.0 for c in cells), 3)
    return _finish(result, out_path)


def _gds_xmin(gds_path: Path) -> float:
    import gdstk

    lib = gdstk.read_gds(str(gds_path))
    return min(cell.bounding_box()[0][0] for cell in lib.top_level()
               if "$$$" not in cell.name)


def _finish(result: dict, out_path: str | None) -> dict:
    if out_path:
        Path(out_path).write_text(json.dumps(result, indent=1))
    return result
