"""Gate-and-promote — the single promotion path over a Phase-A workdir.

Every surface (CLI, REST, and therefore the web daemon's conductors) promotes
through this function, so the record's semantics cannot drift between fronts:

- the worker's canonical claim is ``submission.json`` ({claimed_iou,
  knob:{name, width_um}}); a missing or malformed submission renders the
  claim/knob checks "missing";
- ``verify_cell`` recomputes fidelity and audits source purity; the knob is
  perturbed when declared;
- STRICT mode (the default) refuses promotion unless the claim matched and
  the declared knob responded — the paper's full three-check gate. Protocol
  verification without a submission is recorded but does not promote.
- ``gate.json`` is persisted BEFORE the artifacts are promoted, and
  promotion itself is atomic (temp + ``os.replace``), so a watcher can never
  observe a promoted tree without its gate record, or a partial ``best.gds``.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from homi.conductor.gate import GateResult, verify_cell


@dataclass(frozen=True)
class PromotionOutcome:
    gate: GateResult
    claim_status: str        # ok | mismatch | missing
    knob_status: str         # ok | failed | missing
    promoted: bool
    reasons: list[str]       # human-readable refusal reasons (empty on promote)


def read_submission(workdir: Path) -> dict:
    try:
        raw = json.loads((workdir / "submission.json").read_text())
        return raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        return {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gate_and_promote(project_dir: Path, workdir: Path, *,
                     strict: bool = True) -> PromotionOutcome:
    project_dir = Path(project_dir)
    workdir = Path(workdir)
    gds_files = sorted(workdir.glob("*.gds"), key=lambda p: p.stat().st_mtime)
    script = workdir / "device.py"
    target = workdir / "component.png"
    calibration = workdir / "calibration.json"
    missing = [p.name for p in (script, target, calibration) if not p.exists()]
    if not gds_files or missing:
        raise FileNotFoundError(
            f"worker left no gateable cell (missing: {missing or ['gds']})")

    submission = read_submission(workdir)
    claimed_iou = submission.get("claimed_iou")
    if not isinstance(claimed_iou, (int, float)):
        claimed_iou = None
    knob_decl = submission.get("knob")
    knob_decl = knob_decl if isinstance(knob_decl, dict) else {}
    knob_name = knob_decl.get("name")
    width = knob_decl.get("width_um")
    knob = ((str(knob_name), width if isinstance(width, (int, float)) else None)
            if knob_name else None)

    gate = verify_cell(gds_files[-1], target, calibration, script,
                       claimed_iou=claimed_iou, knob=knob)
    claim_status = ("missing" if claimed_iou is None
                    else "ok" if gate.iou_matches_claim else "mismatch")
    knob_status = ("missing" if gate.knob is None
                   else "ok" if gate.knob.get("ok") else "failed")

    reasons: list[str] = []
    if gate.purity:
        reasons.append(f"source purity: {len(gate.purity)} violation(s)")
    if claim_status == "mismatch":
        reasons.append("claimed IoU disagrees with recomputation")
    if knob_status == "failed":
        reasons.append("declared knob did not move geometry")
    if strict:
        if claim_status == "missing":
            reasons.append("no submission.json claim (strict gate)")
        if knob_status == "missing":
            reasons.append("no declared knob to verify (strict gate)")
    promoted = gate.verified and not reasons

    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    accepted_gds = gds_files[-1]
    record = {
        "verified": gate.verified, "promoted": promoted,
        "iou": gate.iou, "metrics": gate.metrics,
        "claim": claim_status, "claimed_iou": claimed_iou,
        "purity": gate.purity, "knob": gate.knob, "knob_status": knob_status,
        "strict": strict, "reasons": reasons,
        # Bind the verdict to the exact four inputs it measured.  Consumers
        # may still read legacy records without this block, but a new record
        # can no longer be paired silently with a later script/GDS/target.
        "artifacts": {
            "script_sha256": _sha256(script),
            "gds_sha256": _sha256(accepted_gds),
            "target_sha256": _sha256(target),
            "calibration_sha256": _sha256(calibration),
        },
        "gated_at": datetime.now(timezone.utc).isoformat(),
    }
    tmp = output_dir / "gate.json.tmp"
    tmp.write_text(json.dumps(record, indent=1, default=str))
    os.replace(tmp, output_dir / "gate.json")

    if promoted:
        for src, dest in ((script, output_dir / "best.py"),
                          (accepted_gds, output_dir / "best.gds")):
            t = dest.with_suffix(dest.suffix + ".tmp")
            shutil.copy2(src, t)
            os.replace(t, dest)
    return PromotionOutcome(gate, claim_status, knob_status, promoted, reasons)
