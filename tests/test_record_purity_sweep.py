"""The frozen record certifies the canonical purity rule — permanently.

Every cell under data/agents/** carries a recorded verdict produced by the
campaign gate. The canonical rule (homi.conductor.source_policy
.purity_violations — what verify_cell runs) must reproduce those verdicts
forever: 119 recorded cells pass, 36 recorded rejections reject. Any policy
change that flips a frozen cell fails here instead of landing silently —
this check has caught exactly that twice in one day.

The strict surface (strict_purity_violations) is free to be harsher; it
screens execution, not the record.
"""

from pathlib import Path

from homi.conductor.source_policy import purity_violations, strict_purity_violations
from homi.paths import workspace_root

RECORD_SPLIT = (119, 36)  # (pass, reject) — the audited frozen-record verdicts

# Cells that exercise the exact canonical/strict boundary: recorded workers
# imported os/gdstk for benign post-processing (boolean merges, GDS IO) and
# the campaign gate accepted them. Strict-only bans must never leak into the
# canonical surface and flip these.
BOUNDARY_CELLS = (
    "data/agents/paper_swap/final1/output/recreation_codex54m/device.py",
    "data/agents/paper_swap/final2/output/recreation_codex55m/device.py",
    "data/agents/paper_swap/final3/output/recreation_opus48max/device.py",
    "data/agents/paper_swap/final5/output/recreation_codex55x/device.py",
    "data/agents/paper_swap/final6/output/recreation_codex55m/device.py",
)


def _record_files() -> list[Path]:
    root = workspace_root()
    files = set((root / "data" / "agents").rglob("device.py"))
    files |= set((root / "data" / "agents").rglob("best.py"))
    files.add(root / "projects" / "example_mmi_splitter" / "output" / "best.py")
    files.add(root / "src" / "homi" / "assets" / "example" / "best.py")
    return sorted(f for f in files if f.exists())


def test_canonical_rule_reproduces_every_frozen_verdict():
    files = _record_files()
    assert len(files) == sum(RECORD_SPLIT), (
        f"record inventory changed: {len(files)} files (data/ is frozen — "
        "update RECORD_SPLIT only with a record-curation commit)"
    )
    passed = sum(1 for f in files if not purity_violations(f.read_text()))
    assert (passed, len(files) - passed) == RECORD_SPLIT, (
        "canonical purity rule flips frozen record verdicts — the gate no "
        "longer certifies the published record"
    )


def test_strict_bans_stay_out_of_the_canonical_surface():
    root = workspace_root()
    for rel in BOUNDARY_CELLS:
        source = (root / rel).read_text()
        assert purity_violations(source) == [], f"canonical flip: {rel}"
        assert strict_purity_violations(source), f"strict should flag {rel}"
