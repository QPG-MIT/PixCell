"""Broadband FDTD S-matrix run of the SOI-optimized MZI — HUMAN-AUTHORIZED.

The human explicitly authorized starting this run (2026-07-02, ~0.76
FlexCredits estimate). This script rebuilds the draft with a BROADBAND mode
monitor (the Flex default records a single frequency, which cannot show
fringes), re-estimates, prints the cost, and starts the task.

Run from repo root: .venv/bin/python data/agents/pdk_swap/smatrix_run.py
"""
import re
import sys
from pathlib import Path

import gdsfactory as gf

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

import tidy3d as td  # noqa: E402
from tidy3d.constants import C_0  # noqa: E402

from Flex.core.cloud import (  # noqa: E402
    estimate_simulation_cost,
    run_simulation,
    upload_simulation,
)
from Flex.core.simulation import create_simulation_from_component  # noqa: E402

GDS = "data/agents/pdk_swap/output/optimize/soi220/mzi_soi220.gds"
SPAN_UM = (1.53, 1.57)
N_FREQS = 201


def read_tidy3d_key() -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    match = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text())
    if not match:
        raise SystemExit("no apikey in ~/.tidy3d/config")
    return match.group(1)


def main() -> None:
    component = gf.import_gds(Path(GDS))  # the generated GDS is the ONLY geometry
    api_key = read_tidy3d_key()

    sim = create_simulation_from_component(
        component=component,
        layers=[(1, 0)],
        material="Silicon (SOI)",
        thickness_nm=220,
        wavelength_um=1.55,
        api_key=api_key,
        config={"min_steps_per_wvl": 8},  # coarse validation grid
    )

    freqs = [C_0 / (SPAN_UM[1] - i * (SPAN_UM[1] - SPAN_UM[0]) / (N_FREQS - 1))
             for i in range(N_FREQS)]
    monitors = []
    for monitor in sim.monitors:
        if isinstance(monitor, td.ModeMonitor):
            monitors.append(monitor.updated_copy(freqs=freqs))
        else:
            monitors.append(monitor)  # field snapshot stays single-frequency
    sim = sim.updated_copy(monitors=monitors)

    task_name = "pdk_swap_smatrix_mzi_soi220_broadband"
    task_id, task_url = upload_simulation(sim, task_name=task_name)
    cost = estimate_simulation_cost(task_id)
    print(f"task: {task_name}\n  id: {task_id}\n  estimated: {cost} FlexCredits")
    if cost is not None and cost > 1.5:
        print("  cost exceeds authorized band (~0.76, ceiling 1.5) — NOT starting.")
        return
    started = run_simulation(task_id)
    print(f"  started: {started} (human-authorized)\n  workbench: {task_url}")
    Path("data/agents/pdk_swap/output/smatrix_task.txt").write_text(task_id)


if __name__ == "__main__":
    main()
