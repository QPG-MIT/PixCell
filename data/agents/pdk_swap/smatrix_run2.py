"""Broadband FDTD S-matrix of the SOI-optimized MZI — run 2, corrected ports.

Run 1 (fdve-3d2fac68) came back flat: Flex's create_simulation_from_component
centers the mode source/monitor on the bbox VERTICAL CENTER at the padded
domain edge — right for straight-through devices, wrong for this serpentine
MZI whose bus sits near the bbox top; the source injected into cladding.
(Flex improvement filed; here we correct placement surgically.)

This script keeps Flex's structures/domain/grid, then repositions source and
monitor onto the actual bus waveguide (y-interval measured from the GDS
polygons past the tapers) and sets an explicit run time covering the folded
optical path. Human-authorized re-run; hard cost ceiling 1.5 FlexCredits.

Run from repo root: .venv/bin/python data/agents/pdk_swap/smatrix_run2.py
"""
import re
import sys
from pathlib import Path

import gdsfactory as gf
import gdstk

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
INSET_UM = 6.0  # inject/collect past the edge tapers, on the full-width bus
RUN_TIME_S = 6e-12  # covers ~240 um folded path at n_g~4 plus ramp/decay
COST_CEILING = 1.5


def read_tidy3d_key() -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    match = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text())
    if not match:
        raise SystemExit("no apikey in ~/.tidy3d/config")
    return match.group(1)


def bus_y_center(gds_path: str, x_target: float) -> float:
    """y-center of the waveguide material crossing x_target (geometric slice)."""
    lib = gdstk.read_gds(gds_path)
    ys = []
    for cell in lib.top_level():
        if "$$$" in cell.name:
            continue
        for poly in cell.get_polygons(depth=None, layer=1, datatype=0):
            for piece in gdstk.slice(poly, x_target, "x")[0] + gdstk.slice(poly, x_target, "x")[1]:
                for x, y in piece.points:
                    if abs(x - x_target) <= 1e-3:
                        ys.append(y)
    if not ys:
        raise SystemExit(f"no material crossing x={x_target}")
    return (min(ys) + max(ys)) / 2


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
        config={"min_steps_per_wvl": 8},
    )

    xmin, ymin, xmax, ymax = (
        component.xmin, component.ymin, component.xmax, component.ymax
    )
    x_in, x_out = xmin + INSET_UM, xmax - INSET_UM
    y_in = bus_y_center(GDS, x_in)
    y_out = bus_y_center(GDS, x_out)
    thickness_um = 0.22

    freq0 = C_0 / 1.55
    freqs = [C_0 / (SPAN_UM[1] - i * (SPAN_UM[1] - SPAN_UM[0]) / (N_FREQS - 1))
             for i in range(N_FREQS)]
    plane = (0, 3.0, 2.5)  # tight local plane: only the bus crosses it here

    source = td.ModeSource(
        center=(x_in, y_in, thickness_um / 2),
        size=plane,
        source_time=td.GaussianPulse(freq0=freq0, fwidth=freq0 / 10),
        direction="+",
        mode_spec=td.ModeSpec(num_modes=1),
        mode_index=0,
    )
    monitor = td.ModeMonitor(
        center=(x_out, y_out, thickness_um / 2),
        size=plane,
        freqs=freqs,
        mode_spec=td.ModeSpec(num_modes=1),
        name="output_modes",
    )
    sim = sim.updated_copy(sources=[source], monitors=[monitor], run_time=RUN_TIME_S)

    print(f"ports: in=({x_in:.1f},{y_in:.2f})  out=({x_out:.1f},{y_out:.2f})  "
          f"run_time={RUN_TIME_S*1e12:.0f} ps")
    task_name = "pdk_swap_smatrix_mzi_soi220_bb_v2"
    task_id, task_url = upload_simulation(sim, task_name=task_name)
    cost = estimate_simulation_cost(task_id)
    print(f"task: {task_name}\n  id: {task_id}\n  estimated: {cost} FlexCredits")
    if cost is not None and cost > COST_CEILING:
        print(f"  cost exceeds ceiling {COST_CEILING} — NOT starting.")
        return
    started = run_simulation(task_id)
    print(f"  started: {started} (human-authorized re-run)\n  workbench: {task_url}")
    Path("data/agents/pdk_swap/output/smatrix_task.txt").write_text(task_id)


if __name__ == "__main__":
    main()
