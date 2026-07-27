"""Campaign results + run-metrics builders (conductor post-processing).

Promoted from ``data/agents/paper_swap/tools/{build_results,
metrics_extract}.py`` with the campaign directory as an argument instead of a
repo-depth anchor. The parsing formats are the sweep's own ledger/transcript
formats; ``PRE_LEDGER_CELLS`` are the cells verified before the ledger existed
(values from SWEEP_STATE.md) — campaign data, kept verbatim.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

#: Cells verified before sweep_verdicts.txt existed (July sweep, from SWEEP_STATE.md).
PRE_LEDGER_CELLS = [
    ("final2", "haiku45m", 0.4388, 0, "verified pre-ledger (first wave cell)"),
    ("final1", "opus48m", 0.9473, 0, "pilot"),
    ("final1", "codex55x", 0.9491, 0, "pilot"),
    ("final2", "codex55x", 0.9873, 0, ""),
    ("final2", "codex55m", 0.9601, 0, ""),
    ("final4", "codex55x", 0.9811, 0, ""),
    ("final5", "codex55x", 0.8458, 0, ""),
    ("final5", "codex55m", 0.9367, 0, ""),
    ("final6", "codex55x", 0.9393, 0, ""),
    ("final6", "codex55m", 0.8552, 0, ""),
    ("final7", "codex55x", 0.8632, 0, ""),
    ("final8", "codex55x", 0.9164, 0, ""),
]

_LEDGER_LINE = re.compile(
    r'^(final[1-8]) (\w+): (?:"IoU": ([0-9.]+) purity_hits=(\d+)'
    r"|IoU ([0-9.]+) PURITY-VIOLATION[^)]*\)|NO USABLE OUTPUT.*)"
)

# Cell identity appears in the brief as "<...>paper_swap/finalN/output/recreation_<cfg>/";
# prefix-agnostic so pre- and post-rename transcript paths both match.
_CELL_RE = re.compile(r"paper_swap/(final[1-8])/output/(recreation_[a-z0-9]+)/")


def build_results(campaign_dir: Path | str, write: bool = True) -> dict:
    """Parse the conductor's verdict ledger into the canonical results JSON.

    Reads ``<campaign>/sweep_verdicts.txt``; merges ``PRE_LEDGER_CELLS``;
    writes ``<campaign>/sweep_results.json`` unless ``write=False``.
    """
    campaign = Path(campaign_dir)
    cells: dict[tuple[str, str], dict] = {}
    for dev, cfg, iou, hits, note in PRE_LEDGER_CELLS:
        cells[(dev, cfg)] = {
            "device": dev, "config": cfg, "iou": iou,
            "purity_violation": hits > 0, "host": "mini", "notes": note,
        }
    for raw in (campaign / "sweep_verdicts.txt").read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        m = _LEDGER_LINE.match(raw)
        if not m:
            print("UNPARSED:", raw)
            continue
        dev, cfg = m.group(1), m.group(2)
        host = "air" if "[AIR]" in raw else "mini"
        note = "no-marker-recovered" if "no marker" in raw else ""
        if m.group(3):
            iou, viol = float(m.group(3)), int(m.group(4)) > 0
        elif m.group(5):
            iou, viol = float(m.group(5)), True
        else:
            iou, viol, note = None, False, "no usable output (hung)"
        cells[(dev, cfg)] = {
            "device": dev, "config": cfg, "iou": iou,
            "purity_violation": viol, "host": host, "notes": note,
        }
    out = sorted(cells.values(), key=lambda c: (c["config"], c["device"]))
    result = {"cells": out}
    if write:
        (campaign / "sweep_results.json").write_text(json.dumps(result, indent=1))
    return result


def _parse_ts(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def claude_session(path: Path, host: str) -> dict | None:
    """One Claude Code session jsonl -> cell metrics dict or None."""
    cell = None
    first_ts = last_ts = None
    out_tok = in_tok = cache_read = 0
    turns = 0
    model = None
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = _parse_ts(rec.get("timestamp", "")) if isinstance(rec.get("timestamp"), str) else None
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            msg = rec.get("message") or {}
            if cell is None:
                content = msg.get("content")
                text = json.dumps(content) if content else ""
                m = _CELL_RE.search(text)
                if m and rec.get("type") == "user":
                    cell = (m.group(1), m.group(2).replace("recreation_", ""))
            if rec.get("type") == "assistant":
                usage = msg.get("usage") or {}
                if usage:
                    turns += 1
                    out_tok += usage.get("output_tokens", 0) or 0
                    in_tok += usage.get("input_tokens", 0) or 0
                    cache_read += usage.get("cache_read_input_tokens", 0) or 0
                model = msg.get("model") or model
    if not cell or not first_ts:
        return None
    return {
        "device": cell[0], "config": cell[1], "host": host, "harness": "claude-code",
        "model_id": model, "session_file": path.name,
        "wall_minutes": round((last_ts - first_ts).total_seconds() / 60, 1),
        "assistant_turns": turns,
        "output_tokens": out_tok, "input_tokens_uncached": in_tok,
        "cache_read_tokens": cache_read,
    }


def codex_session(path: Path, host: str) -> dict | None:
    """One codex rollout jsonl -> cell metrics dict or None."""
    cell = None
    first_ts = last_ts = None
    model = None
    effort = None
    last_usage = None
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            ts = _parse_ts(rec.get("timestamp", "")) if isinstance(rec.get("timestamp"), str) else None
            if ts:
                first_ts = first_ts or ts
                last_ts = ts
            payload = rec.get("payload") or {}
            if cell is None:
                text = json.dumps(payload)[:20000]
                m = _CELL_RE.search(text)
                if m:
                    cell = (m.group(1), m.group(2).replace("recreation_", ""))
            if isinstance(payload, dict):
                model = payload.get("model") or model
                effort = payload.get("effort") or payload.get("model_reasoning_effort") or effort
                info = payload.get("info") or {}
                tu = (info.get("total_token_usage") if isinstance(info, dict) else None) or payload.get("total_token_usage")
                if isinstance(tu, dict):
                    last_usage = tu
    if not cell or not first_ts:
        return None
    rec = {
        "device": cell[0], "config": cell[1], "host": host, "harness": "codex-cli",
        "model_id": model, "effort": effort, "session_file": path.name,
        "wall_minutes": round((last_ts - first_ts).total_seconds() / 60, 1),
    }
    if last_usage:
        rec["output_tokens"] = last_usage.get("output_tokens")
        rec["input_tokens"] = last_usage.get("input_tokens")
        rec["cached_input_tokens"] = last_usage.get("cached_input_tokens")
        rec["reasoning_output_tokens"] = last_usage.get("reasoning_output_tokens")
        rec["total_tokens"] = last_usage.get("total_tokens")
    return rec


def extract_metrics(campaign_dir: Path | str, staging_dir: Path | str | None = None,
                    write: bool = True) -> dict:
    """Map each archived session transcript to its (device, config) cell and
    aggregate usage. Keeps the LAST session per cell (restarts supersede) and
    records the restart count."""
    campaign = Path(campaign_dir)
    staging = Path(staging_dir) if staging_dir else campaign / "transcripts_staging"
    cells = []
    for sub, host, parser in (
        ("mini_claude", "mini", claude_session),
        ("air_claude", "air", claude_session),
        ("mini_codex", "mini", codex_session),
    ):
        root = staging / sub
        if not root.is_dir():
            continue
        paths = root.rglob("*.jsonl") if sub == "mini_codex" else root.glob("*.jsonl")
        for path in sorted(paths):
            r = parser(path, host)
            if r:
                cells.append(r)
    by_cell: dict[tuple[str, str], list[dict]] = {}
    for r in cells:
        by_cell.setdefault((r["device"], r["config"]), []).append(r)
    final = []
    for _key, rs in sorted(by_cell.items()):
        rs.sort(key=lambda r: r["session_file"])
        best = max(rs, key=lambda r: r.get("wall_minutes") or 0)
        best["sessions_total"] = len(rs)
        best["wall_minutes_all_sessions"] = round(sum(r.get("wall_minutes") or 0 for r in rs), 1)
        final.append(best)
    result = {"cells": final}
    if write:
        (campaign / "sweep_metrics.json").write_text(json.dumps(result, indent=1))
    return result
