"""Resume the interrupted sweep pilot from the crash-safe task registry.

Uploads only grid points missing from tasks.json, applies the estimate gate
over the FULL batch (ceiling 3.0 FC), starts everything, polls, and writes
sweep_matrix.json. Idempotent: safe to rerun after further interruptions.
"""
import itertools
import json
import re
import time
from pathlib import Path

from homi.sweep_evaluation import (_make_simulation, _read_api_key, build_gds,
                                   patch_tunables)

PILOT = Path(__file__).resolve().parent
BUDGET_FC = 3.0
SWEEP = {"gap_um": [0.2, 0.3, 0.4, 0.5],
         "coupling_length": [12.0, 21.0, 30.0, 39.0]}
STACK = json.loads(Path("experiments/pdk_swap/stacks/sin400.json").read_text())
SRC = (PILOT / "device_base.py").read_text()

reg_p = PILOT / "tasks.json"
reg = json.loads(reg_p.read_text()) if reg_p.exists() else []
have = {tuple(sorted(t["params"].items())): t for t in reg}

names = list(SWEEP.keys())
cells = [dict(zip(names, combo)) for combo in itertools.product(*(SWEEP[n] for n in names))]

from Flex.core.cloud import (estimate_simulation_cost, get_task_status,
                             run_simulation, upload_simulation)

api_key = _read_api_key()
records = []
for params in cells:
    key = tuple(sorted(params.items()))
    if key in have:
        records.append(have[key])
        continue
    wd = PILOT / ("bpt_" + "_".join(f"{k}{v}" for k, v in params.items()).replace(".", "p"))
    wd.mkdir(exist_ok=True)
    try:
        gds = build_gds(patch_tunables(SRC, params), wd)
    except Exception as e:
        records.append({"params": params, "build_error": str(e)[:200]})
        continue
    sim = _make_simulation(gds, STACK, api_key)
    tag = "_".join(f"{k}{v}" for k, v in params.items())[:40]
    tid, _ = upload_simulation(sim, task_name=f"sweep_{tag}")
    rec = {"params": params, "task_id": tid,
           "estimate_fc": estimate_simulation_cost(tid)}
    records.append(rec)
    reg_p.write_text(json.dumps(records, indent=1))

total_est = sum(r.get("estimate_fc") or 0.0 for r in records)
print(f"uploads complete: {sum(1 for r in records if r.get('task_id'))} tasks, "
      f"est {total_est:.3f} FC")
if total_est > BUDGET_FC:
    print("STATUS: aborted_budget", total_est)
    raise SystemExit(0)

for r in records:
    if r.get("task_id"):
        run_simulation(r["task_id"])

deadline = time.time() + 3600
pending = {r["task_id"] for r in records if r.get("task_id")}
while pending and time.time() < deadline:
    for tid in list(pending):
        if get_task_status(tid) in ("success", "error", "diverged"):
            pending.discard(tid)
    if pending:
        time.sleep(12)

from tidy3d import web

for r in records:
    tid = r.get("task_id")
    if not tid:
        continue
    st = get_task_status(tid)
    r["task_status"] = st
    if st == "success":
        wd = PILOT / "results"
        wd.mkdir(exist_ok=True)
        data = web.load(tid, path=str(wd / f"{tid}.hdf5"))
        p_bar = float(abs(data["bar"].amps.sel(direction="+", mode_index=0).values[0]) ** 2)
        p_cross = float(abs(data["cross"].amps.sel(direction="+", mode_index=0).values[0]) ** 2)
        tot = p_bar + p_cross
        r["ratio"] = round(p_cross / tot, 4) if tot > 0 else None
        r["total_T"] = round(tot, 4)
    try:
        r["billed_fc"] = web.real_cost(tid)
    except Exception:
        r["billed_fc"] = r.get("estimate_fc")

matrix = {"axes": SWEEP, "fom": "coupling_ratio",
          "stack": "experiments/pdk_swap/stacks/sin400.json",
          "script": str(PILOT / "device_base.py"), "budget_fc": BUDGET_FC,
          "status": "complete", "total_estimate_fc": round(total_est, 3),
          "total_billed_fc": round(sum(r.get("billed_fc") or 0.0 for r in records), 3),
          "cells": records}
(PILOT / "sweep_matrix.json").write_text(json.dumps(matrix, indent=1))
print("STATUS: complete | billed:", matrix["total_billed_fc"])
