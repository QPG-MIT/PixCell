#!/usr/bin/env python3
"""Build the complete per-cell compilation for the paper-swap matrix.

One row per (device, configuration): the gate-recomputed score, source
purity, knob-response tier, iteration count, wall time, the full token
breakdown as each harness reports it, and an API-list-price-equivalent
cost computed with the vendor-correct formula from rate_card.json.

Nothing here is estimated. A configuration whose model has no published
per-token price carries cost = null. A field a harness does not report is
null, never zero.

Run from the repository root:
    .venv/bin/python data/agents/paper_swap/build_compilation.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import median

CAMP = Path(__file__).resolve().parent
CARD = json.loads((CAMP / "rate_card.json").read_text())
RATES = CARD["models"]
CFG2MODEL = CARD["config_to_model"]

NEW_PREFIXES = ("codex56", "opus5", "fable5")
# Waves resumed after a provider session limit: wall-clock includes the frozen
# interval and is not comparable to uninterrupted waves. Tokens, iterations and
# IoU are unaffected.
WALL_UNRELIABLE = {"opus5max", "fable5max"}


def _cost(metrics: dict, model: str) -> tuple[float | None, str]:
    rate = RATES.get(model)
    if not rate or rate.get("input") is None:
        return None, "no published per-token price"
    if rate["vendor"] == "anthropic":
        need = ("input_tokens_uncached", "cache_read_tokens", "output_tokens")
        if not all(k in metrics for k in need):
            return None, "harness did not report the required token buckets"
        # cache_creation_tokens was added to the parser late; treat a missing
        # value as unknown rather than zero, since zero understates cost.
        if "cache_creation_tokens" not in metrics:
            return None, "cache-write tokens not captured for this cell"
        usd = (
            metrics["input_tokens_uncached"] * rate["input"]
            + metrics["cache_read_tokens"] * rate["cache_read"]
            + metrics["cache_creation_tokens"] * rate["cache_write_1h"]
            + metrics["output_tokens"] * rate["output"]
        ) / 1e6
        return round(usd, 4), "anthropic 4-bucket (writes at 1h TTL)"
    need = ("input_tokens", "cached_input_tokens", "output_tokens")
    if not all(k in metrics for k in need):
        return None, "harness did not report the required token buckets"
    uncached = metrics["input_tokens"] - metrics["cached_input_tokens"]
    usd = (
        uncached * rate["input"]
        + metrics["cached_input_tokens"] * rate["cached_input"]
        + metrics["output_tokens"] * rate["output"]
    ) / 1e6
    return round(usd, 4), "openai 3-bucket (cached is a subset of input)"


def _iterations(cell_dir: Path) -> int | None:
    log = cell_dir / "recreation_log.json"
    if not log.exists() or log.stat().st_size < 3:
        return None
    try:
        payload = json.loads(log.read_text())
    except ValueError:
        return None
    for candidate in (payload, payload.get("iterations") if isinstance(payload, dict) else None,
                      payload.get("iters") if isinstance(payload, dict) else None):
        if isinstance(candidate, list) and candidate:
            entries = [e for e in candidate if isinstance(e, dict) and ("iou" in e or "iter" in e)]
            if entries:
                return len(entries)
    if isinstance(payload, dict):
        for key in ("iteration_count", "n_iterations", "iterations_used"):
            if isinstance(payload.get(key), int):
                return payload[key]
    return None


def main() -> None:
    results = {(c["device"], c["config"]): c
               for c in json.loads((CAMP / "sweep_results.json").read_text())["cells"]}
    metrics = {(c["device"], c["config"]): c
               for c in json.loads((CAMP / "sweep_metrics.json").read_text())["cells"]
               if c.get("device")}
    knob_path = CAMP / "knob_retrofit.json"
    knob = {}
    if knob_path.exists():
        for key, value in json.loads(knob_path.read_text())["cells"].items():
            device, config = key.split("/")
            knob[(device, config)] = value

    rows = []
    for (device, config), cell in sorted(results.items()):
        cell_dir = CAMP / device / "output" / f"recreation_{config}"
        met = metrics.get((device, config), {})
        model = CFG2MODEL.get(config)
        cost, basis = _cost(met, model) if model else (None, "configuration not in rate card")
        kb = knob.get((device, config), {})
        wall = met.get("wall_minutes")
        rows.append({
            "device": device,
            "config": config,
            "generation": "extension" if config.startswith(NEW_PREFIXES) else "original",
            "model": model,
            "model_id_readback": met.get("model_id"),
            "effort": met.get("effort"),
            "vendor": RATES.get(model, {}).get("vendor"),
            "harness": met.get("harness"),
            "host": met.get("host"),
            "iou": cell.get("iou"),
            "purity_violation": cell.get("purity_violation"),
            "knob_tier": kb.get("tier"),
            "knob_param": kb.get("knob"),
            "knob_area_growth_um2": kb.get("area_growth_um2"),
            "iterations": _iterations(cell_dir),
            "wall_minutes": wall,
            "wall_minutes_comparable": None if wall is None else config not in WALL_UNRELIABLE,
            "output_tokens": met.get("output_tokens"),
            "reasoning_output_tokens": met.get("reasoning_output_tokens"),
            "input_tokens_total": met.get("input_tokens"),
            "input_tokens_uncached": met.get("input_tokens_uncached"),
            "cached_input_tokens": met.get("cached_input_tokens"),
            "cache_read_tokens": met.get("cache_read_tokens"),
            "cache_creation_tokens": met.get("cache_creation_tokens"),
            "total_tokens": met.get("total_tokens"),
            "cost_usd": cost,
            "cost_basis": basis,
        })

    by_config: dict[str, list[dict]] = {}
    for row in rows:
        by_config.setdefault(row["config"], []).append(row)

    summary = []
    for config, cells in by_config.items():
        ious = [c["iou"] for c in cells if c["iou"] is not None]
        costs = [c["cost_usd"] for c in cells if c["cost_usd"] is not None]
        walls = [c["wall_minutes"] for c in cells if c["wall_minutes"] is not None]
        iters = [c["iterations"] for c in cells if c["iterations"] is not None]
        outs = [c["output_tokens"] for c in cells if c["output_tokens"] is not None]
        usable = [0.0 if c["purity_violation"] or c["iou"] is None else c["iou"] for c in cells]
        summary.append({
            "config": config,
            "generation": cells[0]["generation"],
            "model": cells[0]["model"],
            "vendor": cells[0]["vendor"],
            "n_cells": len(cells),
            "mean_iou": round(sum(ious) / len(ious), 4) if ious else None,
            "usable_iou": round(sum(usable) / len(cells), 4) if cells else None,
            "violations": sum(1 for c in cells if c["purity_violation"]),
            "median_iterations": median(iters) if iters else None,
            "median_wall_min": median(walls) if walls else None,
            "wall_comparable": all(c["wall_minutes_comparable"] is not False for c in cells),
            "median_output_tokens": median(outs) if outs else None,
            "total_cost_usd": round(sum(costs), 2) if costs else None,
            "median_cost_usd": round(median(costs), 3) if costs else None,
            "cost_cells_priced": f"{len(costs)}/{len(cells)}",
            "knob_declared_pass": sum(1 for c in cells if c["knob_tier"] == "declared-knob-pass"),
            "knob_alternate_pass": sum(1 for c in cells if c["knob_tier"] == "alternate-knob-pass"),
            "knob_unresolved": sum(1 for c in cells if c["knob_tier"] == "unresolved"),
        })
    summary.sort(key=lambda r: (r["mean_iou"] is None, -(r["mean_iou"] or 0)))

    out = {
        "_purpose": "Complete per-cell compilation of the paper-swap matrix: score, "
                    "purity, knob response, iterations, wall time, token breakdown, "
                    "and API-list-price-equivalent cost.",
        "_rate_card": "rate_card.json (sources and formulas therein)",
        "_caveats": [
            "cost_usd is an API-list-price EQUIVALENT: these runs executed on "
            "subscription plans, so no per-token invoice exists. It converts measured "
            "tokens at published list rates.",
            "wall_minutes_comparable is false for waves resumed after a provider "
            "session limit; their wall clock includes frozen intervals.",
            "A null is a genuine absence, never a zero.",
        ],
        "cells": rows,
        "by_configuration": summary,
    }
    (CAMP / "compilation.json").write_text(json.dumps(out, indent=1))

    print(f"{'config':16s} {'gen':10s} {'IoU':>6s} {'use':>6s} {'it':>3s} "
          f"{'wall':>6s} {'out tok':>9s} {'$/cell':>8s}  priced")
    for r in summary:
        mi = f"{r['mean_iou']:.3f}" if r["mean_iou"] is not None else "  -  "
        ui = f"{r['usable_iou']:.3f}" if r["usable_iou"] is not None else "  -  "
        it = f"{r['median_iterations']:.0f}" if r["median_iterations"] is not None else " - "
        wl = f"{r['median_wall_min']:.1f}" if r["median_wall_min"] is not None else "  -  "
        ot = f"{r['median_output_tokens']:,.0f}" if r["median_output_tokens"] is not None else "   -   "
        cs = f"${r['median_cost_usd']:.2f}" if r["median_cost_usd"] is not None else "   -   "
        flag = "" if r["wall_comparable"] else " *"
        print(f"{r['config']:16s} {r['generation']:10s} {mi:>6s} {ui:>6s} {it:>3s} "
              f"{wl:>6s}{flag:2s} {ot:>9s} {cs:>8s}  {r['cost_cells_priced']}")
    print("\n* wall clock includes a provider-limit freeze; not comparable")
    print(f"wrote {CAMP / 'compilation.json'}")


if __name__ == "__main__":
    main()
