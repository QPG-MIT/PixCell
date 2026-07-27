"""Sidewall-angle sweep (user-authorized): opus cat5 recreation AS-DRAWN on sin400.

Same mask, four fab realizations: sidewall 5/15/30/45 deg from vertical
(reference_plane='top' — mask defines ridge top; base flares outward).
Fixture matches the pilot (same grid/run_time/ports) + a z-cut field monitor.
Per-run ceiling 0.5 FC; registry written after every upload.
"""
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

import gdstk
import numpy as np

ROOT = Path("/Users/aadarwal/src/QPG-MIT/homi-anu-powered")
OUT = ROOT / "experiments/catalog_swap/cat5/output/sidewall_sweep"
SRC = ROOT / "experiments/catalog_swap/cat5/output/recreation_opus48m/device.py"
ANGLES_DEG = [5, 15, 30, 45]
CEILING_PER_RUN = 0.5

import os
cfg = (Path.home() / ".tidy3d" / "config").read_text()
os.environ["SIMCLOUD_APIKEY"] = re.search(r'apikey\s*=\s*"([^"]+)"', cfg).group(1)
import tidy3d as td
from tidy3d import web
from tidy3d.constants import C_0

# 1) build the as-recreated GDS once
work = Path(tempfile.mkdtemp())
(work / "device.py").write_text(SRC.read_text())
subprocess.run([str(ROOT / ".venv/bin/python"), "device.py"], cwd=work, check=True, timeout=300)
gds_path = next(work.glob("*.gds"))
lib = gdstk.read_gds(str(gds_path))
top = [c for c in lib.top_level() if "$$$" not in c.name][0]
polys = top.get_polygons(depth=None, layer=1, datatype=0)
pts_all = np.vstack([p.points for p in polys])
xmin, ymin = pts_all.min(0); xmax, ymax = pts_all.max(0)
print(f"GDS bbox: {xmax-xmin:.1f} x {ymax-ymin:.1f} um, {len(polys)} polys", flush=True)

def guide_centers(x_target):
    ys = []
    for p in polys:
        for piece in gdstk.slice(p, x_target, "x")[0] + gdstk.slice(p, x_target, "x")[1]:
            for x, y in piece.points:
                if abs(x - x_target) <= 1e-3:
                    ys.append(y)
    ys = sorted(ys)
    # cluster into guides
    guides, cur = [], [ys[0]]
    for y in ys[1:]:
        if y - cur[-1] > 0.3:
            guides.append((min(cur) + max(cur)) / 2); cur = [y]
        else:
            cur.append(y)
    guides.append((min(cur) + max(cur)) / 2)
    return guides

x_in, x_out = xmin + 1.0, xmax - 1.0
gin, gout = guide_centers(x_in), guide_centers(x_out)
print(f"in guides y={gin}, out guides y={gout}", flush=True)
y_src = max(gin)                      # top-left input
y_bar, y_cross = max(gout), min(gout) # bar = top-right, cross = bottom-right

T = 0.4  # core thickness um
n_core, n_clad = 1.996, 1.444
f0 = C_0 / 1.55
plane = (0, 1.4, 1.6)

registry_file = OUT / "tasks.json"
registry = []
for ang in ANGLES_DEG:
    slabs = td.PolySlab.from_gds(
        top, gds_layer=1, gds_dtype=0, axis=2, slab_bounds=(0.0, T),
        sidewall_angle=math.radians(ang), reference_plane="top")
    structs = [td.Structure(geometry=s, medium=td.Medium(permittivity=n_core**2)) for s in slabs]
    sim = td.Simulation(
        center=((xmin+xmax)/2, (ymin+ymax)/2, T/2),
        size=(xmax-xmin+3, ymax-ymin+3, T+3),
        structures=structs,
        medium=td.Medium(permittivity=n_clad**2),
        grid_spec=td.GridSpec.auto(min_steps_per_wvl=12, wavelength=1.55),
        run_time=4e-12,
        sources=[td.ModeSource(center=(x_in, y_src, T/2), size=plane,
                 source_time=td.GaussianPulse(freq0=f0, fwidth=f0/10),
                 direction="+", mode_spec=td.ModeSpec(num_modes=1), mode_index=0)],
        monitors=[
            td.ModeMonitor(center=(x_out, y_bar, T/2), size=plane, freqs=[f0],
                           mode_spec=td.ModeSpec(num_modes=1), name="bar"),
            td.ModeMonitor(center=(x_out, y_cross, T/2), size=plane, freqs=[f0],
                           mode_spec=td.ModeSpec(num_modes=1), name="cross"),
            td.FieldMonitor(center=(0, 0, T/2), size=(td.inf, td.inf, 0),
                            freqs=[f0], name="field"),
        ],
    )
    name = f"HOMI_cat5_sidewall_{ang}deg"
    tid = web.upload(sim, task_name=name, verbose=False)
    est = None
    try:
        est = web.estimate_cost(tid)
    except Exception as e:
        print(f"estimate err {ang}deg: {e}", flush=True)
    entry = {"angle_deg": ang, "task_id": tid, "estimate_fc": est}
    registry.append(entry)
    registry_file.write_text(json.dumps(registry, indent=1))
    print(f"uploaded {ang}deg -> {tid} est={est}", flush=True)
    if est is not None and est > CEILING_PER_RUN:
        print(f"SKIP START {ang}deg: estimate {est} > ceiling {CEILING_PER_RUN}", flush=True)
        entry["skipped"] = True
        registry_file.write_text(json.dumps(registry, indent=1))
        continue
    web.start(tid)
    entry["started"] = True
    registry_file.write_text(json.dumps(registry, indent=1))
    print(f"started {ang}deg", flush=True)
print("ALL UPLOADS/STARTS DONE", flush=True)
