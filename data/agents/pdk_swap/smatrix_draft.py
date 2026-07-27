"""Create a DRAFT Tidy3D FDTD task for the full S-matrix of an optimized design.

Policy (standing rule): this script uploads a draft and prints the cost
estimate + workbench link. It NEVER starts the run — the human presses Start.

Low-cost settings: coarse grid (min_steps_per_wvl=8 vs the 32 default), one
broadband mode source (FDTD yields the whole spectrum in a single run).

Run from repo root: .venv/bin/python data/agents/pdk_swap/smatrix_draft.py [gds]
"""
import re
import sys
from pathlib import Path

import gdsfactory as gf

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from Flex.core.cloud import estimate_simulation_cost, upload_simulation  # noqa: E402
from Flex.core.simulation import create_simulation_from_component  # noqa: E402

DEFAULT_GDS = "data/agents/pdk_swap/output/optimize/soi220/mzi_soi220.gds"


def read_tidy3d_key() -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    match = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text())
    if not match:
        raise SystemExit("no apikey in ~/.tidy3d/config")
    return match.group(1)


def main() -> None:
    gds = Path(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_GDS)
    component = gf.import_gds(gds)  # the generated GDS is the ONLY geometry
    api_key = read_tidy3d_key()

    sim = create_simulation_from_component(
        component=component,
        layers=[(1, 0)],
        material="Silicon (SOI)",
        thickness_nm=220,
        wavelength_um=1.55,
        api_key=api_key,
        config={"min_steps_per_wvl": 8},  # low-cost validation grid
    )
    task_name = f"pdk_swap_smatrix_{gds.stem}"
    task_id, task_url = upload_simulation(sim, task_name=task_name)
    cost = estimate_simulation_cost(task_id)
    print(f"DRAFT created (NOT started): {task_name}")
    print(f"  task_id: {task_id}")
    print(f"  estimated cost: {cost} FlexCredits")
    print(f"  workbench: {task_url}")
    print("  -> press Start in the workbench to run; fetch S21 afterwards.")


if __name__ == "__main__":
    main()
