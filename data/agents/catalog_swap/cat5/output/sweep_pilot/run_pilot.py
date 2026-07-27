"""Authorized pilot: cat5 primitives coupler on sin400 — gap x length sweep, ceiling 3.0 FC."""
import json
from homi.sweep_evaluation import run_sweep

res = run_sweep(
    script_path="experiments/catalog_swap/cat5/output/sweep_pilot/device_base.py",
    stack_json_path="experiments/pdk_swap/stacks/sin400.json",
    sweep={"gap_um": [0.2, 0.3, 0.4, 0.5], "coupling_length": [12.0, 21.0, 30.0, 39.0]},
    fom="coupling_ratio",
    budget_fc=3.0,
    out_path="experiments/catalog_swap/cat5/output/sweep_pilot/sweep_matrix.json",
)
print("STATUS:", res["status"], "| est:", res.get("total_estimate_fc"), "| billed:", res.get("total_billed_fc"))
