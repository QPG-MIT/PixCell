"""Tier-1 measurement harness: small capped FDTD of a fixture GDS.

The conductor runs this on a worker's ``MEASURE <stack>:`` request — workers
never run cloud jobs. Measures the achieved split fraction t, insertion loss,
and the implied extinction ratio ER = -20*log10|2t-1|, then writes
``measured.json`` for ``python -m homi.spec_optimization eval ... --measured``.

Hard cost ceiling gated BEFORE start (upload → estimate → refuse if over).

Run: ``.venv/bin/python -m homi.conductor.tier1 --dir <fixture dir> [...]``
(promoted from ``data/agents/pdk_swap/splitter_tier1.py``).
"""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

WL0 = 1.55
N_FREQS = 11  # small band: ratio + IL vs lambda glimpse
SPAN_UM = (1.53, 1.57)


def read_tidy3d_key(required: bool = True) -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    match = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text()) if cfg.exists() else None
    if match:
        return match.group(1)
    if not required:
        for env_name in ("SIMCLOUD_APIKEY", "TIDY3D_API_KEY"):
            if os.environ.get(env_name):
                return os.environ[env_name]
        return "dry-run"
    raise SystemExit("no apikey in ~/.tidy3d/config")


def output_port_names(port_positions: dict[str, list[float]], port_count: int) -> tuple[str, ...]:
    if port_count == 2:
        names = ("out_top", "out_bot")
        missing = [name for name in names if name not in port_positions]
        if missing:
            raise SystemExit(f"missing legacy port_positions entries for --ports 2: {missing}")
        return names

    names = tuple(f"out_{idx}" for idx in range(1, port_count + 1))
    missing = [name for name in names if name not in port_positions]
    if missing:
        raise SystemExit(f"missing port_positions entries for --ports {port_count}: {missing}")
    return names


def _parse_args(argv=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", required=True,
                    help="fixture directory holding the GDS + splitter_meta.json")
    ap.add_argument("--gds", default="fixture.gds")
    ap.add_argument("--task-name", default="homi_tier1_fixture")
    ap.add_argument("--material", default="Silicon (SOI)")
    ap.add_argument("--thickness-nm", type=int, default=220)
    ap.add_argument("--ceiling", type=float, default=0.45)
    ap.add_argument("--core-n", type=float, default=None)
    ap.add_argument("--clad-n", type=float, default=None)
    ap.add_argument("--ports", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.ports < 2:
        ap.error("--ports must be >= 2")
    return args


def main(argv=None) -> None:
    args = _parse_args(argv)

    # Heavy imports stay inside main so `--help` and module import are cheap.
    import gdsfactory as gf
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d import web
    from tidy3d.constants import C_0

    from flex.core.cloud import (
        estimate_simulation_cost,
        get_task_status,
        run_simulation,
        upload_simulation,
    )
    from flex.core.simulation import create_simulation_from_component

    fixture_dir = Path(args.dir).resolve()
    gds_path = fixture_dir / args.gds
    meta_path = fixture_dir / "splitter_meta.json"
    out_path = fixture_dir / "measured.json"
    cost_ceiling = args.ceiling

    meta = json.loads(meta_path.read_text())
    ports = meta["port_positions"]
    output_names = output_port_names(ports, args.ports)
    component = gf.import_gds(gds_path)  # the generated GDS is the ONLY geometry
    api_key = read_tidy3d_key(required=not args.dry_run)

    sim = create_simulation_from_component(
        component=component,
        layers=[(1, 0)],
        material=args.material,
        thickness_nm=args.thickness_nm,
        custom_core_n=args.core_n,
        custom_clad_n=args.clad_n,
        wavelength_um=WL0,
        api_key=api_key,
        config={"min_steps_per_wvl": 12},  # finer than tier-2: tiny domain, still cheap
    )

    freq0 = C_0 / WL0
    freqs = [C_0 / (SPAN_UM[1] - i * (SPAN_UM[1] - SPAN_UM[0]) / (N_FREQS - 1))
             for i in range(N_FREQS)]
    plane = (0, 1.6, 1.8)  # narrower than the fanned port separation
    thickness_um = args.thickness_nm / 1000.0

    source = td.ModeSource(
        center=(ports["in"][0], ports["in"][1], thickness_um / 2),
        size=plane,
        source_time=td.GaussianPulse(freq0=freq0, fwidth=freq0 / 10),
        direction="+",
        mode_spec=td.ModeSpec(num_modes=1),
        mode_index=0,
    )
    monitors = [
        td.ModeMonitor(
            center=(ports[name][0], ports[name][1], thickness_um / 2),
            size=plane,
            freqs=freqs,
            mode_spec=td.ModeSpec(num_modes=1),
            name=name,
        )
        for name in output_names
    ]
    sim = sim.updated_copy(sources=[source], monitors=monitors, run_time=3e-12)

    if args.dry_run:
        mode_monitor_count = sum(isinstance(monitor, td.ModeMonitor) for monitor in sim.monitors)
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "ports": args.ports,
                    "monitor_count": mode_monitor_count,
                    "monitor_names": [monitor.name for monitor in sim.monitors],
                    "source_count": len(sim.sources),
                },
                indent=2,
            )
        )
        return

    task_id, task_url = upload_simulation(sim, task_name=args.task_name)
    cost = estimate_simulation_cost(task_id)
    print(f"task {task_id} estimated {cost} FlexCredits")
    if cost is not None and cost > cost_ceiling:
        raise SystemExit(f"cost exceeds tier-1 ceiling {cost_ceiling} — not started")
    run_simulation(task_id)
    print(f"started (human-authorized tier-1): {task_url}")

    import time

    for _ in range(240):
        status = get_task_status(task_id)
        if status in ("success", "error", "diverged"):
            break
        time.sleep(10)
    if status != "success":
        raise SystemExit(f"task ended '{status}'")

    data = web.load(task_id, path=str(fixture_dir / "tier1_data.hdf5"))
    if args.ports > 2:
        import math

        powers = {
            name: abs(data[name].amps.sel(direction="+", mode_index=0).values) ** 2
            for name in output_names
        }
        total = sum(powers.values())
        mid = N_FREQS // 2
        total_mid = float(total[mid])
        fractions = {name: float(power[mid] / total_mid) for name, power in powers.items()}
        uniformity = max(fractions.values()) - min(fractions.values())
        splitter_il_db = -10 * math.log10(total_mid)
        measured = {
            "port_fractions": {name: round(value, 4) for name, value in fractions.items()},
            "total_transmission": round(total_mid, 4),
            "uniformity": round(uniformity, 4),
            "splitter_il_db": round(splitter_il_db, 3),
            "band_total_transmission_min_max": [
                round(float(min(total)), 4),
                round(float(max(total)), 4),
            ],
            "source": f"tier-1 FDTD {task_id}, grid 12 steps/wvl, mid-band {WL0} um",
        }
        out_path.write_text(json.dumps(measured, indent=2))
        print(json.dumps(measured, indent=2))
        return

    import math

    p_top = abs(data["out_top"].amps.sel(direction="+", mode_index=0).values) ** 2
    p_bot = abs(data["out_bot"].amps.sel(direction="+", mode_index=0).values) ** 2
    mid = N_FREQS // 2
    t = float(p_top[mid] / (p_top[mid] + p_bot[mid]))
    il_db = float(-10 * math.log10(p_top[mid] + p_bot[mid]))
    er_db = float(-20 * math.log10(abs(2 * t - 1))) if abs(2 * t - 1) > 1e-3 else 60.0

    measured = {
        "split_fraction_t": round(t, 4),
        "splitter_il_db": round(il_db, 3),
        "insertion_loss_db": round(2 * il_db, 3),  # an MZI traverses two such splitters
        "extinction_ratio_db": round(er_db, 2),
        "band_split_min_max": [round(float(min(p_top / (p_top + p_bot))), 4),
                               round(float(max(p_top / (p_top + p_bot))), 4)],
        "source": f"tier-1 FDTD {task_id}, grid 12 steps/wvl, mid-band {WL0} um",
    }
    out_path.write_text(json.dumps(measured, indent=2))
    print(json.dumps(measured, indent=2))


if __name__ == "__main__":
    main()
