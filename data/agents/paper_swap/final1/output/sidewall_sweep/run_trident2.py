"""Sidewall x stack sweep for the FINAL_1 trident 1x2 (symmetry-protection test).
Per stack: the pilot's Phase-B-verified fixture (fan-outs + recorded ports),
swept over sidewall angles {0,5,15,30,45}deg. Measures split balance (expect
symmetry-protected ~0.5) and total transmission/IL (expected to move)."""
import json, math, re, os
from pathlib import Path
import gdstk
import numpy as np

ROOT = Path("/Users/aadarwal/src/QPG-MIT/homi-anu-powered")
OUT = ROOT / "experiments/paper_swap/final1/output/sidewall_sweep"
BASE = ROOT / "experiments/paper_swap/final1/output/retarget_opus"
STACKS = {
    "soi220": {"n_core": 3.476, "n_clad": 1.444, "T": 0.22},
    "sin400": {"n_core": 1.996, "n_clad": 1.444, "T": 0.40},
    "tfln400": {"n_core": 2.138, "n_clad": 1.444, "T": 0.40},
}
ANGLES = [0, 5, 15, 30, 45]
CEILING = 0.65
cfg = (Path.home() / ".tidy3d" / "config").read_text()
os.environ["SIMCLOUD_APIKEY"] = re.search(r'apikey\s*=\s*"([^"]+)"', cfg).group(1)
import tidy3d as td
from tidy3d import web
from tidy3d.plugins.polyslab import ComplexPolySlab
from tidy3d.constants import C_0

f0 = C_0 / 1.55
plane = (0, 1.4, 1.6)
reg_file = OUT / "tasks_trident2.json"
registry = []
for stack, sc in STACKS.items():
    T = sc["T"]
    gds_path = BASE / stack / f"fixture_{stack}.gds"
    meta = json.loads((BASE / stack / "splitter_meta.json").read_text())
    ports = meta["port_positions"]
    lib = gdstk.read_gds(str(gds_path))
    top = [c for c in lib.top_level() if "$$$" not in c.name][0]
    pts_all = np.vstack([p.points for p in top.get_polygons(depth=None, layer=1, datatype=0)])
    xmin, ymin = pts_all.min(0); xmax, ymax = pts_all.max(0)
    for ang in ANGLES:
        slabs = ComplexPolySlab.from_gds(top, gds_layer=1, gds_dtype=0, axis=2,
            slab_bounds=(0.0, T), sidewall_angle=math.radians(ang), reference_plane="top")
        structs = [td.Structure(geometry=s, medium=td.Medium(permittivity=sc["n_core"]**2)) for s in slabs]
        sim = td.Simulation(
            center=((xmin+xmax)/2, (ymin+ymax)/2, T/2),
            size=(xmax-xmin+3, ymax-ymin+3, T+3),
            structures=structs, medium=td.Medium(permittivity=sc["n_clad"]**2),
            grid_spec=td.GridSpec.auto(min_steps_per_wvl=12, wavelength=1.55),
            run_time=4e-12,
            sources=[td.ModeSource(center=(ports["in"][0], ports["in"][1], T/2), size=plane,
                     source_time=td.GaussianPulse(freq0=f0, fwidth=f0/10),
                     direction="+", mode_spec=td.ModeSpec(num_modes=1), mode_index=0)],
            monitors=[
                td.ModeMonitor(center=(ports["out_top"][0], ports["out_top"][1], T/2), size=plane,
                               freqs=[f0], mode_spec=td.ModeSpec(num_modes=1), name="top"),
                td.ModeMonitor(center=(ports["out_bot"][0], ports["out_bot"][1], T/2), size=plane,
                               freqs=[f0], mode_spec=td.ModeSpec(num_modes=1), name="bot"),
                td.FieldMonitor(center=(0, 0, T/2), size=(td.inf, td.inf, 0), freqs=[f0], name="field"),
            ])
        tid = web.upload(sim, task_name=f"HOMI_f1_sw2_{stack}_{ang}deg", verbose=False)
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
        print(f"started {stack}/{ang}deg est={round(est,3) if est else '?'}", flush=True)
print("ALL UPLOADS/STARTS DONE", flush=True)
