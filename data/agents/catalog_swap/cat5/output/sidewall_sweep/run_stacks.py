"""Sidewall x stack grid: same mask, 3 stacks x angles {0,5,15,30,45}deg.
sin400 5-45deg already done; this adds sin400@0 + soi220/tfln400 full ladders (11 sims).
Fixture identical to run_sidewall.py; z-cut field monitor at core mid per stack."""
import json, math, re, subprocess, tempfile, os
from pathlib import Path
import gdstk
import numpy as np

ROOT = Path("/Users/aadarwal/src/QPG-MIT/homi-anu-powered")
OUT = ROOT / "experiments/catalog_swap/cat5/output/sidewall_sweep"
SRC = ROOT / "experiments/catalog_swap/cat5/output/recreation_opus48m/device.py"
STACKS = {
    "soi220": {"n_core": 3.476, "n_clad": 1.444, "T": 0.22, "angles": [0, 5, 15, 30, 45]},
    "sin400": {"n_core": 1.996, "n_clad": 1.444, "T": 0.40, "angles": [0]},
    "tfln400": {"n_core": 2.138, "n_clad": 1.444, "T": 0.40, "angles": [0, 5, 15, 30, 45]},
}
CEILING = 0.5
cfg = (Path.home() / ".tidy3d" / "config").read_text()
os.environ["SIMCLOUD_APIKEY"] = re.search(r'apikey\s*=\s*"([^"]+)"', cfg).group(1)
import tidy3d as td
from tidy3d import web
from tidy3d.constants import C_0

work = Path(tempfile.mkdtemp())
(work / "device.py").write_text(SRC.read_text())
subprocess.run([str(ROOT / ".venv/bin/python"), "device.py"], cwd=work, check=True, timeout=300)
gds_path = next(work.glob("*.gds"))
lib = gdstk.read_gds(str(gds_path))
top = [c for c in lib.top_level() if "$$$" not in c.name][0]
polys = top.get_polygons(depth=None, layer=1, datatype=0)
pts_all = np.vstack([p.points for p in polys])
xmin, ymin = pts_all.min(0); xmax, ymax = pts_all.max(0)

def guide_centers(x_target):
    ys = []
    for p in polys:
        for piece in gdstk.slice(p, x_target, "x")[0] + gdstk.slice(p, x_target, "x")[1]:
            for x, y in piece.points:
                if abs(x - x_target) <= 1e-3:
                    ys.append(y)
    ys = sorted(ys)
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
y_src, y_bar, y_cross = max(gin), max(gout), min(gout)
f0 = C_0 / 1.55
plane = (0, 1.4, 1.6)
reg_file = OUT / "tasks_stacks.json"
registry = []
for stack, sc in STACKS.items():
    T = sc["T"]
    for ang in sc["angles"]:
        slabs = td.PolySlab.from_gds(top, gds_layer=1, gds_dtype=0, axis=2,
            slab_bounds=(0.0, T), sidewall_angle=math.radians(ang), reference_plane="top")
        structs = [td.Structure(geometry=s, medium=td.Medium(permittivity=sc["n_core"]**2)) for s in slabs]
        sim = td.Simulation(
            center=((xmin+xmax)/2, (ymin+ymax)/2, T/2),
            size=(xmax-xmin+3, ymax-ymin+3, T+3),
            structures=structs, medium=td.Medium(permittivity=sc["n_clad"]**2),
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
            ])
        tid = web.upload(sim, task_name=f"HOMI_cat5_sw_{stack}_{ang}deg", verbose=False)
        est = None
        try: est = web.estimate_cost(tid)
        except Exception as e: print(f"est err {stack}/{ang}: {e}", flush=True)
        entry = {"stack": stack, "angle_deg": ang, "task_id": tid, "estimate_fc": est}
        registry.append(entry); reg_file.write_text(json.dumps(registry, indent=1))
        if est is not None and est > CEILING:
            entry["skipped"] = True; reg_file.write_text(json.dumps(registry, indent=1))
            print(f"SKIP {stack}/{ang}: est {est}", flush=True); continue
        web.start(tid); entry["started"] = True
        reg_file.write_text(json.dumps(registry, indent=1))
        print(f"started {stack}/{ang}deg -> {tid} est={est}", flush=True)
print("ALL UPLOADS/STARTS DONE", flush=True)
