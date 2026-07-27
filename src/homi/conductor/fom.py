"""FoM selection — the conductor's first judgment, as code.

Codifies the RUNBOOK step-1 table (device class → function FoM → cheapest
tier that measures it → fixture kind → spec template) plus the three-source
resolution: the human's stated intent in chat, the paper's own words
(harvested into ``function.json`` at extract time), and the silhouette
classification. Precedence human > paper > visual; disagreement between
sources is SURFACED, never silently resolved.

Everything here is conductor knowledge. The firewall is unchanged: workers
derive the device class themselves from the picture; hint-lint gates every
worker-bound byte; spec files state WHAT must be met, never WHY.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class FomPlan:
    device_class: str
    fom: str
    description: str
    tier0: str | None          # the analytic reduction, or None if physics needs FDTD
    in_loop_tier: int          # 0 = free local loop; 1 = capped FDTD via MEASURE
    fixture: str | None        # tier-1 fixture kind, when in_loop_tier == 1
    spec_template: dict        # WHAT-only skeleton for spec_<stack>.json
    source: str                # "human" | "paper" | "visual"
    source_text: str           # the classified evidence, verbatim
    conflicts: list[str] = field(default_factory=list)


#: RUNBOOK step-1 rule table. Quality metrics (ER/IL) are additions, not
#: defaults; tier-1-in-loop only when no tier-0 reduction exists.
DEVICE_FOMS: dict[str, dict] = {
    # spec templates use the EVALUATOR's schema (homi.spec_optimization
    # _normalize_spec): {"target": {...}} or {"targets": [...]}, metric names
    # from LOCAL_METRICS for tier-0, MEASURE-loop names for tier-1.
    "mzi": {
        "fom": "fsr_nm",
        "description": "free spectral range at the design wavelength",
        "tier0": "FSR = lambda^2 / (n_g * delta_L): measured arm imbalance + local n_g solve",
        "in_loop_tier": 0,
        "fixture": None,
        "spec_template": {"target": {"metric": "fsr_nm", "value": None,
                                     "tolerance_rel": 0.02},
                          "wavelength_um": 1.55, "mode": "TE0"},
    },
    "ring": {
        "fom": "ring_fsr_nm",
        "description": "resonator free spectral range from circumference",
        "tier0": "FSR = lambda^2 / (n_g * L_round): measured circumference + local n_g solve",
        "in_loop_tier": 0,
        "fixture": None,
        "spec_template": {"target": {"metric": "ring_fsr_nm", "value": None,
                                     "tolerance_rel": 0.02},
                          "wavelength_um": 1.55, "mode": "TE0"},
    },
    "bragg": {
        "fom": "bragg_wavelength_nm",
        "description": "Bragg wavelength from grating period",
        "tier0": "lambda_B = 2 * n_eff * period: measured period + local n_eff solve",
        "in_loop_tier": 0,
        "fixture": None,
        "spec_template": {"target": {"metric": "bragg_wavelength_nm", "value": None,
                                     "tolerance_rel": 0.01},
                          "wavelength_um": 1.55, "mode": "TE0"},
    },
    "directional_coupler": {
        "fom": "coupling_ratio",
        "description": "power coupling ratio at the design wavelength",
        "tier0": "coupling length from supermode splitting (solve_supermodes) + measured gap/length",
        "in_loop_tier": 0,
        "fixture": "splitter_1x2",
        "spec_template": {"target": {"metric": "coupling_ratio", "value": None,
                                     "tolerance_abs": 0.05},
                          "wavelength_um": 1.55, "mode": "TE0"},
    },
    "splitter": {
        "fom": "transmission_balance",
        "description": "total transmission and output balance",
        "tier0": None,
        "in_loop_tier": 1,
        "fixture": "splitter_1xN",
        "spec_template": {"targets": [
            {"metric": "transmission", "min": 0.95},
            {"metric": "balance", "value": 0.5, "tolerance_abs": 0.02},
        ], "wavelength_um": 1.55},
    },
    "mmi": {
        "fom": "transmission_uniformity",
        "description": "total transmission and per-port uniformity",
        "tier0": "MMI beat length from solve_multimode grounds L_MMI; transmission needs FDTD",
        "in_loop_tier": 1,
        "fixture": "splitter_1xN",
        "spec_template": {"targets": [
            {"metric": "transmission", "min": 0.9},
            {"metric": "uniformity", "max": 0.05},
        ], "wavelength_um": 1.55},
    },
    "crossing": {
        "fom": "transmission_crosstalk",
        "description": "through transmission and crosstalk",
        "tier0": None,
        "in_loop_tier": 1,
        "fixture": "crossing_4port",
        "spec_template": {"targets": [
            {"metric": "transmission", "min": 0.95},
            {"metric": "crosstalk_db", "max": -30.0},
        ], "wavelength_um": 1.55},
    },
    "grating_coupler": {
        "fom": "coupling_efficiency",
        "description": "fiber-chip coupling efficiency at the design wavelength",
        "tier0": None,
        "in_loop_tier": 1,
        "fixture": None,
        "spec_template": {"targets": [
            {"metric": "coupling_efficiency", "min": 0.3},
        ], "wavelength_um": 1.55},
    },
}

#: Longest-match-first keyword classification. Order matters: specific
#: phrases before generic words ("grating coupler" before "grating"/"coupler").
_CLASS_KEYWORDS: list[tuple[str, str]] = [
    ("grating coupler", "grating_coupler"),
    ("fiber coupler", "grating_coupler"),
    ("mach-zehnder", "mzi"),
    ("mach zehnder", "mzi"),
    ("interferometer", "mzi"),
    ("mzi", "mzi"),
    ("racetrack", "ring"),
    ("microring", "ring"),
    ("resonator", "ring"),
    ("ring", "ring"),
    ("bragg", "bragg"),
    ("directional coupler", "directional_coupler"),
    ("crossing", "crossing"),
    ("multimode interference", "mmi"),
    ("multimode splitter", "mmi"),
    ("mmi", "mmi"),
    ("star coupler", "mmi"),
    ("star-coupler", "mmi"),
    ("power splitter", "splitter"),
    ("power divider", "splitter"),
    ("splitter", "splitter"),
    ("y-branch", "splitter"),
    ("y branch", "splitter"),
    ("coupler", "directional_coupler"),
    ("grating", "bragg"),
]


def classify_text(text: str | None) -> str | None:
    """Map free text (human words, paper words, a worker's blind
    classification) to a canonical device class, or None."""
    if not text:
        return None
    low = text.lower()
    for keyword, device_class in _CLASS_KEYWORDS:
        if keyword in low:
            return device_class
    return None


def resolve_fom(
    human: str | None = None,
    paper: str | None = None,
    visual: str | None = None,
    targets: dict | None = None,
) -> FomPlan | None:
    """Resolve the FoM plan from the three evidence sources.

    Precedence human > paper > visual. Sources that classify differently are
    recorded as conflicts for the conductor to surface — never silently
    resolved. ``targets`` (e.g. the paper's reported numbers) fill matching
    keys of the spec template.
    """
    classified = [
        (source, text, classify_text(text))
        for source, text in (("human", human), ("paper", paper), ("visual", visual))
        if text
    ]
    resolved = [(s, t, c) for s, t, c in classified if c]
    if not resolved:
        return None

    source, source_text, device_class = resolved[0]
    # same measurement family (e.g. splitter vs mmi) is agreement, not conflict
    _family = {"splitter": "split", "mmi": "split"}

    def _fam(c):
        return _family.get(c, c)

    conflicts = [
        f"{s} reads as {c}, {source} reads as {device_class}"
        for s, _t, c in resolved[1:]
        if _fam(c) != _fam(device_class)
    ]

    entry = DEVICE_FOMS[device_class]
    import copy

    template = copy.deepcopy(entry["spec_template"])
    # fill target values by metric name (e.g. the paper's reported FSR)
    _target_list = template.get("targets") or (
        [template["target"]] if "target" in template else []
    )
    for t in _target_list:
        claimed = (targets or {}).get(t.get("metric"))
        if claimed is not None:
            t["value"] = claimed

    return FomPlan(
        device_class=device_class,
        fom=entry["fom"],
        description=entry["description"],
        tier0=entry["tier0"],
        in_loop_tier=entry["in_loop_tier"],
        fixture=entry["fixture"],
        spec_template=template,
        source=source,
        source_text=source_text[:200],
        conflicts=conflicts,
    )
