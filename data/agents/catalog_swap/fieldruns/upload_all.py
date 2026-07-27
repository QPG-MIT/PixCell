"""Upload the 5 authorized cloud runs: 2 coupler field maps (sin400) + 3 home specs (soi220).

Port strategy (uniform, honest): mode source on the designated input guide;
an 'input' flux monitor 0.6 um downstream of the source for normalization;
output power read from half-plane flux monitors split midway between output
guides (avoids overlapping mode planes on converged ports — armB's frozen
dx=0 geometry never fans out, so mode-monitor separation is impossible by
construction; the same flux method is applied to every run for fairness).
Field map (couplers only): single-freq z-cut FieldMonitor at core mid-plane.

Per-run hard ceiling 0.6 FC; abort any run whose estimate exceeds it.
Registry -> experiments/catalog_swap/fieldruns/tasks.json
"""
import json
import re
import sys
from pathlib import Path

import gdsfactory as gf
import gdstk

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

import tidy3d as td  # noqa: E402
from tidy3d.constants import C_0  # noqa: E402

from Flex.core.cloud import estimate_simulation_cost, run_simulation, upload_simulation  # noqa: E402
from Flex.core.simulation import create_simulation_from_component  # noqa: E402

FR = ROOT / "experiments/catalog_swap/fieldruns"
F0 = C_0 / 1.55
CEILING = 0.6


def read_key() -> str:
    cfg = Path.home() / ".tidy3d" / "config"
    m = re.search(r'apikey\s*=\s*"([^"]+)"', cfg.read_text())
    return m.group(1)


def cut_ys(gds, x):
    """Unique y-values where layer-1 material crosses vertical line x."""
    lib = gdstk.read_gds(str(gds))
    ys = set()
    for cell in lib.top_level():
        for poly in cell.get_polygons(depth=None, layer=1, datatype=0):
            for grp in gdstk.slice(poly, x, "x"):
                for piece in grp:
                    for px, py in piece.points:
                        if abs(px - x) <= 5e-3:
                            ys.add(round(float(py), 3))
    return sorted(ys)


def guides(gds, x):
    """Pair consecutive cut ys into (center, width) guide intervals."""
    ys = cut_ys(gds, x)
    out = []
    i = 0
    while i + 1 < len(ys):
        a, b = ys[i], ys[i + 1]
        if b - a > 0.05:
            out.append(((a + b) / 2, b - a))
            i += 2
        else:
            i += 1
    return out


def base_sim(gds_dir, core_n, clad_n, thickness_nm, material):
    comp = gf.import_gds(gds_dir / "device.gds")
    return comp, create_simulation_from_component(
        component=comp, layers=[(1, 0)], material=material,
        thickness_nm=thickness_nm, custom_core_n=core_n, custom_clad_n=clad_n,
        wavelength_um=1.55, api_key=read_key(), config={"min_steps_per_wvl": 12},
    )


def mode_source(x, y, zc, h=1.4, w=2.0):
    return td.ModeSource(
        center=(x, y, zc), size=(0, h, w),
        source_time=td.GaussianPulse(freq0=F0, fwidth=F0 / 10),
        direction="+", mode_spec=td.ModeSpec(num_modes=1), mode_index=0,
    )


def flux(name, x, y0, y1, zc, w=2.0):
    return td.FluxMonitor(center=(x, (y0 + y1) / 2, zc), size=(0, y1 - y0, w),
                          freqs=[F0], name=name)


REG = {}


def submit(name, sim, run_time, extra):
    sim = sim.updated_copy(run_time=run_time, **extra)
    task_id, url = upload_simulation(sim, task_name=f"catalog_{name}")
    est = estimate_simulation_cost(task_id)
    print(f"{name}: task {task_id} est {est} FC")
    if est is not None and est > CEILING:
        print(f"  ABORT {name}: estimate {est} > ceiling {CEILING}")
        REG[name] = {"task_id": task_id, "estimate": est, "started": False}
        return
    run_simulation(task_id)
    REG[name] = {"task_id": task_id, "estimate": est, "started": True, "url": url}


def coupler_run(arm):
    d = FR / f"cat5_{arm}_sin400"
    g = d / "device.gds"
    comp, sim = base_sim(d, 1.996, 1.444, 400, "Silicon (SOI)")
    zc = 0.2
    xin, xout = comp.xmin + 0.4, comp.xmax - 0.4
    gl = guides(g, xin + 0.1)
    gr = guides(g, xout - 0.1)
    top_in = max(gl, key=lambda t: t[0])[0]
    centers = sorted(c for c, _ in gr)
    split = sum(centers) / len(centers) if len(centers) >= 2 else centers[0]
    ylo, yhi = comp.ymin - 0.8, comp.ymax + 0.8
    src_x = xin + 0.2
    mons = [
        flux("input", src_x + 0.6, top_in - 0.9, top_in + 0.9, zc),
        flux("bar", xout, split, yhi, zc),
        flux("cross", xout, ylo, split, zc),
        td.FieldMonitor(center=(0, 0, zc), size=(td.inf, td.inf, 0),
                        freqs=[F0], name="field"),
    ]
    extra = {"sources": [mode_source(src_x, top_in, zc, h=1.2)], "monitors": mons}
    submit(f"cat5_{arm}_sin400", sim, 4e-12, extra)


def home_run(cid):
    d = FR / f"{cid}_home"
    g = d / "device.gds"
    comp, sim = base_sim(d, None, None, 220, "Silicon (SOI)")
    zc = 0.11
    xin, xout = comp.xmin + 0.4, comp.xmax - 0.4
    gl = guides(g, xin + 0.1)
    gr = guides(g, xout - 0.1)
    if cid == "cat4":
        src_y = max(gl, key=lambda t: t[0])[0]
    else:
        src_y = gl[0][0] if len(gl) == 1 else sorted(gl)[len(gl) // 2][0]
    src_x = xin + 0.2
    mons = [flux("input", src_x + 0.6, src_y - 0.9, src_y + 0.9, zc)]
    if cid in ("cat3", "cat4"):
        centers = sorted(c for c, _ in gr)
        split = sum(centers) / len(centers)
        ylo, yhi = comp.ymin - 0.8, comp.ymax + 0.8
        mons += [flux("out_top", xout, split, yhi, zc),
                 flux("out_bot", xout, ylo, split, zc)]
    else:  # cat6 crossing: through E, crosstalk N and S
        east_y = gr[0][0] if gr else 0.0
        xc = (comp.xmin + comp.xmax) / 2
        mons += [
            flux("through", xout, east_y - 1.2, east_y + 1.2, zc),
            td.FluxMonitor(center=(xc, comp.ymax - 0.4, zc), size=(2.4, 0, 2.0),
                           freqs=[F0], name="xtalk_n"),
            td.FluxMonitor(center=(xc, comp.ymin + 0.4, zc), size=(2.4, 0, 2.0),
                           freqs=[F0], name="xtalk_s"),
        ]
    extra = {"sources": [mode_source(src_x, src_y, zc, h=1.2)], "monitors": mons}
    submit(f"{cid}_home", sim, 3e-12, extra)


# couplers already submitted (see tasks.json)
for cid in ("cat3", "cat4", "cat6"):
    home_run(cid)

old = json.loads((FR / "tasks.json").read_text()) if (FR / "tasks.json").exists() else {}
old.update(REG)
(FR / "tasks.json").write_text(json.dumps(old, indent=1))
print("registry saved; total estimated:",
      sum(v["estimate"] or 0 for v in REG.values()))
