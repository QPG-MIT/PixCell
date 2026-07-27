"""
Spec Optimization Evaluator for HOMI

Deterministic measurement layer for spec-driven cross-PDK optimization:
- solve_waveguide: local tidy3d mode solve (n_eff, n_g) for a layer stack,
  disk-cached so repeat solves never re-invoke the solver.
- solve_supermodes / solve_multimode: tier-0 coupling physics (directional
  coupler supermode splitting, MMI beat length), same cache/guard discipline.
- measured_delta_length / verify_knob_response: the parametric-script
  measurement contract (script writes lengths.json from its own path objects)
  plus proof that the declared knob changes real geometry.
- evaluate: schema-v2 multi-metric specs as functionals of S with tiered
  evaluation — tier-0 metrics (fsr_nm) computed locally; tier>=1 metrics
  (extinction_ratio_db, insertion_loss_db) come from full-wave results fed in
  via measured_metrics, else are reported "unmeasured" and NEVER count as a
  pass. evaluate_mzi_fsr remains as the legacy single-target wrapper.

This module contains NO search or optimization logic — the agent is the
optimizer; the evaluator only measures. It NEVER imports tidy3d.web or any
cloud API: mode solving is strictly the local ModeSolver plugin.

Trust boundary (stated, not hidden): delta_length comes from the script's own
lengths.json (derived from its gf.Path objects), and verify_knob_response
checks that the declared knob moves total layer area as width*delta predicts.
A deliberately deceptive script could fake both (lie in lengths.json, or tie
dummy geometry to the knob). These checks defend against honest mistakes, not
an adversarial script author — the audit record for that is the generating
agent's transcript plus independent re-measurement (and, when it matters,
centerline extraction from the GDS, which is future work).
"""

import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import gdstk

from homi.paths import workspace_root

# Writable solver cache lives OUTSIDE the frozen record; the solve results
# recorded during the retargeting campaign stay readable as a seed.  data/ is
# a frozen record — nothing may write into it at runtime.
DEFAULT_CACHE_DIR = workspace_root() / ".cache" / "mode_cache"
SEED_CACHE_DIR = workspace_root() / "data" / "agents" / "pdk_swap" / "output" / "mode_cache"


def _cache_hit(cache_file: Path, include_seed: bool = True) -> Path | None:
    """The readable copy of a cache entry: the writable cache first, then —
    only for the default cache — the frozen campaign seed.  An explicit
    cache_dir means exactly that cache: no global fallthrough."""
    if cache_file.exists():
        return cache_file
    if include_seed:
        seed = SEED_CACHE_DIR / cache_file.name
        if seed.exists():
            return seed
    return None

# Mode-plane cross-section (um): large enough for weakly-confined SiN/TFLN modes.
PLANE_SIZE_UM = 5.0
MIN_STEPS_PER_WVL = 20
N_G_BOUNDS = (1.0, 6.0)

# Script runs are plain gdsfactory builds; minutes means something is wrong.
SCRIPT_TIMEOUT_S = 300

# Same top-level `name = value` convention as jee_integration._create_parametric_factory.
_ASSIGNMENT_PATTERN = r"(\b{name}\s*(?::\s*[^=]+)?\s*=\s*)(-?\d+\.?\d*)"

# Metrics the evaluator can compute locally from geometry + mode physics
# (tier 0). Anything else needs a supplied full-wave measurement.
# Each local metric reads its own lengths.json shape (see measured_lengths):
#   fsr_nm              -> {"arms": {a: L, b: L}, "delta_length_um": dL}
#   ring_fsr_nm         -> {"ring": {"round_trip_um": L}}
#   coupling_ratio      -> {"coupler": {"length_um": L, "gap_um": g[, "width_um": w]}}
#   group_delay_ps      -> {"path": {"total_um": L}}
#   bragg_wavelength_nm -> {"grating": {"period_um": P, "w1_um": a, "w2_um": b}}
LOCAL_METRICS = (
    "fsr_nm",
    "ring_fsr_nm",
    "coupling_ratio",
    "group_delay_ps",
    "bragg_wavelength_nm",
)

# Speed of light expressed as um traveled per ps (group_delay_ps = n_g * L / this).
_UM_PER_PS_LIGHT = 299.792458

# Physical sanity windows for lengths.json-supplied geometry (contract guards).
_RING_ROUND_TRIP_BOUNDS_UM = (1.0, 10000.0)
_PATH_TOTAL_BOUNDS_UM = (1.0, 100000.0)
_BRAGG_WAVELENGTH_BOUNDS_NM = (1000.0, 2000.0)

# Reported ER at/above this means "effectively infinite" (perfect 50/50 split).
ER_CAP_DB = 60.0

# Below this supermode splitting the coupling length is numerically meaningless.
MIN_SUPERMODE_SPLIT = 1e-6


@dataclass(frozen=True)
class ModeResult:
    """Result of a single-mode waveguide solve."""

    n_eff: float
    n_g: float
    from_cache: bool


@dataclass(frozen=True)
class SupermodeResult:
    """Even/odd supermodes of two identical coupled cores (directional coupler)."""

    n_even: float
    n_odd: float
    coupling_length_um: float
    from_cache: bool


@dataclass(frozen=True)
class MultimodeResult:
    """Leading modes of a single wide core (an MMI body cross-section)."""

    n_effs: tuple[float, ...]
    beat_length_um: float
    from_cache: bool


@dataclass(frozen=True)
class CrossSectionModes:
    """Leading supermodes of an arbitrary multi-core cross-section slice."""

    n_effs: tuple[float, ...]
    from_cache: bool


@dataclass(frozen=True)
class TargetVerdict:
    """Per-target verdict: 'pass' / 'fail' / 'unmeasured' — never conflated."""

    metric: str
    tier: int
    verdict: str
    target: dict
    measured: float | None = None
    rel_error: float | None = None
    source: str | None = None  # "local" (evaluator physics) or "supplied"


@dataclass(frozen=True)
class MultiSpecReport:
    """Schema-v2 verdict: per-target results plus the overall gate.

    passes is True only when EVERY target is measured and passing and no
    constraint is violated; unmeasured targets block it (an unmeasured metric
    is not a pass) and are listed in `unmeasured` with the reason echoed.
    """

    passes: bool
    verdicts: tuple[TargetVerdict, ...]
    unmeasured: tuple[str, ...]
    reason: str
    n_eff: float
    n_g: float
    delta_length_um: float | None
    wavelength_um: float
    stack_label: str
    from_cache: bool
    bbox_um: tuple[float, float] | None = None
    max_footprint_um: tuple[float, float] | None = None
    footprint_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SpecReport:
    """Verdict of one device script against one FSR spec on one stack."""

    fsr_nm: float
    target_nm: float
    tolerance_rel: float
    rel_error: float
    passes: bool
    n_eff: float
    n_g: float
    delta_length_um: float
    wavelength_um: float
    stack_label: str
    from_cache: bool
    bbox_um: tuple[float, float] | None = None
    max_footprint_um: tuple[float, float] | None = None
    footprint_ok: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_fsr_nm(wavelength_um: float, n_g: float, delta_length_um: float) -> float:
    """FSR of an unbalanced MZI: lambda^2 / (n_g * delta_L), returned in nm."""
    if n_g <= 0:
        raise ValueError(f"n_g must be positive, got {n_g}")
    if delta_length_um <= 0:
        raise ValueError(f"delta_length_um must be positive, got {delta_length_um}")
    return wavelength_um**2 / (n_g * delta_length_um) * 1000.0


def mzi_extinction_db(split_fraction: float) -> float:
    """
    Bar-port extinction ratio (dB) of an MZI whose identical lossless 1x2
    splitter and combiner send power fraction t to one arm:
    ER = -20*log10(|2t - 1|). A perfect 50/50 split nulls the bar port, so
    values at/above ER_CAP_DB mean "effectively infinite".
    """
    if not 0.0 <= split_fraction <= 1.0:
        raise ValueError(f"split_fraction must be in [0, 1], got {split_fraction}")
    imbalance = abs(2.0 * split_fraction - 1.0)
    if imbalance == 0.0:
        return ER_CAP_DB
    return min(-20.0 * math.log10(imbalance), ER_CAP_DB)


def required_split_balance(er_db: float) -> tuple[float, float]:
    """Split-fraction interval [t_lo, t_hi] achieving at least er_db of MZI ER."""
    if er_db <= 0.0:
        raise ValueError(f"er_db must be positive, got {er_db}")
    half_width = 10.0 ** (-er_db / 20.0) / 2.0
    return (0.5 - half_width, 0.5 + half_width)


def solve_waveguide(
    stack: dict,
    wavelength_um: float = 1.55,
    *,
    width_um: float | None = None,
    cache_dir: Path | None = None,
) -> ModeResult:
    """
    Solve the fundamental TE mode of a strip waveguide defined by a stack dict.

    Stack fields used: core_n, clad_n, thickness_um, single_mode_width_um
    (width_um overrides the stack width). Solves are disk-cached by
    (core_n, clad_n, thickness_um, width_um, wavelength_um); a cache hit never
    invokes the solver.
    """
    core_n = float(stack["core_n"])
    clad_n = float(stack["clad_n"])
    thickness_um = float(stack["thickness_um"])
    width = float(width_um if width_um is not None else stack["single_mode_width_um"])

    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_file = cache_root / _cache_filename(core_n, clad_n, thickness_um, width, wavelength_um)

    cache_hit = _cache_hit(cache_file, include_seed=cache_dir is None)
    if cache_hit is not None:
        payload = json.loads(cache_hit.read_text())
        n_eff, n_g = float(payload["n_eff"]), float(payload["n_g"])
        # The cache is a writable file: re-apply the sanity guard so a corrupt
        # or planted entry cannot smuggle absurd physics past the evaluator.
        _check_sane(n_eff, n_g, core_n=core_n, clad_n=clad_n)
        return ModeResult(n_eff=n_eff, n_g=n_g, from_cache=True)

    n_eff, n_g = _run_mode_solver(core_n, clad_n, thickness_um, width, wavelength_um)
    _check_sane(n_eff, n_g, core_n=core_n, clad_n=clad_n)

    cache_file.write_text(
        json.dumps(
            {
                "core_n": core_n,
                "clad_n": clad_n,
                "thickness_um": thickness_um,
                "width_um": width,
                "wavelength_um": wavelength_um,
                "n_eff": n_eff,
                "n_g": n_g,
            },
            indent=2,
        )
    )
    return ModeResult(n_eff=n_eff, n_g=n_g, from_cache=False)


def solve_supermodes(
    stack: dict,
    wavelength_um: float = 1.55,
    *,
    width_um: float,
    gap_um: float,
    cache_dir: Path | None = None,
) -> SupermodeResult:
    """
    Solve the even/odd supermodes of TWO identical cores separated by gap_um.

    Directional-coupler physics: coupling_length_um = wavelength / (2 * dn)
    where dn = n_even - n_odd. Disk-cached by (core_n, clad_n, thickness_um,
    width_um, gap_um, wavelength_um); cached and fresh results alike pass the
    sanity guards (n_eff in [clad, core], splitting above MIN_SUPERMODE_SPLIT).
    """
    core_n = float(stack["core_n"])
    clad_n = float(stack["clad_n"])
    thickness_um = float(stack["thickness_um"])
    width = float(width_um)
    gap = float(gap_um)

    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    key = (
        f"core{core_n:.6f}_clad{clad_n:.6f}_t{thickness_um:.6f}"
        f"_w{width:.6f}_g{gap:.6f}_wl{wavelength_um:.6f}"
    )
    cache_file = cache_root / f"supermodes_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"

    cache_hit = _cache_hit(cache_file, include_seed=cache_dir is None)
    if cache_hit is not None:
        payload = json.loads(cache_hit.read_text())
        n_even, n_odd = float(payload["n_even"]), float(payload["n_odd"])
        coupling = _coupling_length(n_even, n_odd, core_n, clad_n, wavelength_um)
        return SupermodeResult(
            n_even=n_even, n_odd=n_odd, coupling_length_um=coupling, from_cache=True
        )

    n_even, n_odd = _run_supermode_solver(core_n, clad_n, thickness_um, width, gap, wavelength_um)
    coupling = _coupling_length(n_even, n_odd, core_n, clad_n, wavelength_um)

    cache_file.write_text(
        json.dumps(
            {
                "core_n": core_n,
                "clad_n": clad_n,
                "thickness_um": thickness_um,
                "width_um": width,
                "gap_um": gap,
                "wavelength_um": wavelength_um,
                "n_even": n_even,
                "n_odd": n_odd,
                "coupling_length_um": coupling,
            },
            indent=2,
        )
    )
    return SupermodeResult(
        n_even=n_even, n_odd=n_odd, coupling_length_um=coupling, from_cache=False
    )


def solve_multimode(
    stack: dict,
    wavelength_um: float = 1.55,
    *,
    width_um: float,
    n_modes: int = 2,
    cache_dir: Path | None = None,
) -> MultimodeResult:
    """
    Solve the leading n_modes of a single wide core (an MMI body cross-section).

    beat_length_um = wavelength / (2 * (n_effs[0] - n_effs[1])). Disk-cached by
    (core_n, clad_n, thickness_um, width_um, n_modes, wavelength_um); cached and
    fresh results alike pass the sanity guards (each n_eff in [clad, core],
    strictly decreasing order).
    """
    core_n = float(stack["core_n"])
    clad_n = float(stack["clad_n"])
    thickness_um = float(stack["thickness_um"])
    width = float(width_um)
    if n_modes < 2:
        raise ValueError(f"n_modes must be >= 2 for a beat length, got {n_modes}")

    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    key = (
        f"core{core_n:.6f}_clad{clad_n:.6f}_t{thickness_um:.6f}"
        f"_w{width:.6f}_m{n_modes}_wl{wavelength_um:.6f}"
    )
    cache_file = cache_root / f"multimode_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"

    cache_hit = _cache_hit(cache_file, include_seed=cache_dir is None)
    if cache_hit is not None:
        payload = json.loads(cache_hit.read_text())
        n_effs = tuple(float(n) for n in payload["n_effs"])
        beat = _beat_length(n_effs, core_n, clad_n, wavelength_um)
        return MultimodeResult(n_effs=n_effs, beat_length_um=beat, from_cache=True)

    n_effs = tuple(
        float(n)
        for n in _run_multimode_solver(core_n, clad_n, thickness_um, width, n_modes, wavelength_um)
    )
    beat = _beat_length(n_effs, core_n, clad_n, wavelength_um)

    cache_file.write_text(
        json.dumps(
            {
                "core_n": core_n,
                "clad_n": clad_n,
                "thickness_um": thickness_um,
                "width_um": width,
                "n_modes": n_modes,
                "wavelength_um": wavelength_um,
                "n_effs": list(n_effs),
                "beat_length_um": beat,
            },
            indent=2,
        )
    )
    return MultimodeResult(n_effs=n_effs, beat_length_um=beat, from_cache=False)


def solve_cross_section(
    stack: dict,
    wavelength_um: float = 1.55,
    *,
    cores: tuple[tuple[float, float], ...],
    n_modes: int = 2,
    cache_dir: Path | None = None,
) -> CrossSectionModes:
    """
    Solve the leading modes of an arbitrary multi-core cross-section slice.

    cores is a tuple of (width_um, y_offset_um) pairs — e.g. a trident slice is
    ((w_outer, -d), (w_center, 0.0), (w_outer, +d)). All cores share the
    stack's thickness and materials. Disk-cached by (core_n, clad_n,
    thickness_um, the full cores tuple, n_modes, wavelength_um); cached and
    fresh results alike pass the sanity guards (each n_eff in [clad, core],
    strictly decreasing order).
    """
    core_n = float(stack["core_n"])
    clad_n = float(stack["clad_n"])
    thickness_um = float(stack["thickness_um"])
    cores_norm = tuple((float(w), float(y)) for w, y in cores)
    if not cores_norm:
        raise ValueError("cores must contain at least one (width_um, y_offset_um) pair")
    if any(w <= 0 for w, _ in cores_norm):
        raise ValueError(f"Every core width must be positive, got {cores_norm}")
    if n_modes < 1:
        raise ValueError(f"n_modes must be >= 1, got {n_modes}")

    cache_root = Path(cache_dir) if cache_dir is not None else DEFAULT_CACHE_DIR
    cache_root.mkdir(parents=True, exist_ok=True)
    cores_key = ";".join(f"{w:.6f}:{y:.6f}" for w, y in cores_norm)
    key = (
        f"core{core_n:.6f}_clad{clad_n:.6f}_t{thickness_um:.6f}"
        f"_cores[{cores_key}]_m{n_modes}_wl{wavelength_um:.6f}"
    )
    cache_file = cache_root / f"xsection_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"

    cache_hit = _cache_hit(cache_file, include_seed=cache_dir is None)
    if cache_hit is not None:
        payload = json.loads(cache_hit.read_text())
        n_effs = tuple(float(n) for n in payload["n_effs"])
        _check_mode_ladder(n_effs, core_n=core_n, clad_n=clad_n)
        return CrossSectionModes(n_effs=n_effs, from_cache=True)

    n_effs = tuple(
        float(n)
        for n in _run_cross_section_solver(
            core_n, clad_n, thickness_um, cores_norm, n_modes, wavelength_um
        )
    )
    _check_mode_ladder(n_effs, core_n=core_n, clad_n=clad_n)

    cache_file.write_text(
        json.dumps(
            {
                "core_n": core_n,
                "clad_n": clad_n,
                "thickness_um": thickness_um,
                "cores": [list(pair) for pair in cores_norm],
                "n_modes": n_modes,
                "wavelength_um": wavelength_um,
                "n_effs": list(n_effs),
            },
            indent=2,
        )
    )
    return CrossSectionModes(n_effs=n_effs, from_cache=False)


def measured_lengths(script_path: Path | str) -> dict[str, Any]:
    """
    Run a parametric device script and return its raw lengths.json payload.

    Script contract: the script writes lengths.json next to its GDS, computed
    from its OWN gf.Path/component objects at build time, never hand-entered.
    Shape validation is per-metric (see _validate_arms and the _require_shape
    callers in evaluate) so a ring script is not forced to invent MZI arms.
    """
    script = Path(script_path).resolve()
    _run_script(script)

    lengths_file = script.parent / "lengths.json"
    if not lengths_file.exists():
        raise RuntimeError(
            f"Script {script.name} did not write lengths.json next to its GDS "
            "(required by the measurement contract)"
        )
    return json.loads(lengths_file.read_text())


def _validate_arms(payload: dict) -> dict[str, Any]:
    """Validate the two-arm MZI shape of lengths.json (fsr_nm contract)."""
    arms = payload.get("arms")
    if not isinstance(arms, dict) or len(arms) != 2:
        raise RuntimeError(
            f"lengths.json must contain an 'arms' dict with exactly 2 arms "
            f"(an MZI has two), got {arms} — 3+ arms would silently bypass the "
            "delta consistency check"
        )
    arms = {name: float(length) for name, length in arms.items()}

    delta = float(payload["delta_length_um"])
    lengths = list(arms.values())
    implied = abs(lengths[0] - lengths[1])
    if abs(delta - implied) > 1e-3:
        raise RuntimeError(
            f"lengths.json is inconsistent: delta_length_um={delta} but arm "
            f"lengths imply {implied}"
        )

    return {"arms": arms, "delta_length_um": delta}


def measured_delta_length(script_path: Path | str) -> dict[str, Any]:
    """
    Run a parametric device script and return its self-measured arm lengths.

    Script contract: the script writes lengths.json next to its GDS —
    {"arms": {name: L_um, ...}, "delta_length_um": float} — computed from its
    OWN gf.Path/component objects at build time, never hand-entered.
    """
    return _validate_arms(measured_lengths(script_path))


def _require_shape(payload: dict, key: str, fields: tuple[str, ...], metric: str) -> dict:
    """Extract lengths.json shape `key`, demanding numeric `fields` (contract)."""
    shape = payload.get(key)
    if not isinstance(shape, dict):
        raise RuntimeError(
            f"lengths.json is missing the '{key}' shape required by the "
            f"{metric} metric (measurement contract)"
        )
    out = {}
    for field in fields:
        if field not in shape:
            raise RuntimeError(
                f"lengths.json '{key}' shape is missing '{field}' "
                f"(required by the {metric} metric)"
            )
        out[field] = float(shape[field])
    for field, value in shape.items():
        if field not in out:
            out[field] = float(value)
    return out


def _bounded(value: float, bounds: tuple[float, float], label: str) -> float:
    lo, hi = bounds
    if not (lo <= value <= hi):
        raise ValueError(f"{label}={value} outside sane bounds [{lo}, {hi}]")
    return value


def verify_knob_response(
    script_path: Path | str,
    param: str = "delta_length",
    delta_um: float = 5.0,
    *,
    width_um: float,
) -> dict[str, Any]:
    """
    Prove the declared knob changes real geometry, not just reported numbers.

    Copies the script, perturbs its top-level `<param> = <number>` assignment
    by delta_um, rebuilds, and checks that (a) lengths.json delta_length_um
    moves by delta_um within 1% and (b) layer-(1,0) polygon area grows by
    ~ width_um * delta_um within 25% (measured with gdstk from the written GDS).
    """
    script = Path(script_path).resolve()
    source = script.read_text()

    pattern = _ASSIGNMENT_PATTERN.format(name=re.escape(param))
    match = re.search(pattern, source)
    if match is None:
        raise ValueError(f"No top-level '{param} = <number>' assignment found in {script.name}")
    base_value = float(match.group(2))
    perturbed_source = re.sub(pattern, rf"\g<1>{base_value + delta_um}", source)

    with tempfile.TemporaryDirectory(prefix="knob_response_") as tmp:
        base_delta, base_area = _build_and_measure(Path(tmp) / "base", script.name, source)
        pert_delta, pert_area = _build_and_measure(
            Path(tmp) / "perturbed", script.name, perturbed_source
        )

    delta_response = pert_delta - base_delta
    delta_length_ok = abs(delta_response - delta_um) <= 0.01 * abs(delta_um)

    area_growth = pert_area - base_area
    expected_area_growth = width_um * delta_um
    area_ok = abs(area_growth - expected_area_growth) <= 0.25 * abs(expected_area_growth)

    return {
        "param": param,
        "delta_um": delta_um,
        "width_um": width_um,
        "base_value": base_value,
        "base_delta_length_um": base_delta,
        "perturbed_delta_length_um": pert_delta,
        "delta_response_um": delta_response,
        "delta_length_ok": delta_length_ok,
        "base_area_um2": base_area,
        "perturbed_area_um2": pert_area,
        "area_growth_um2": area_growth,
        "expected_area_growth_um2": expected_area_growth,
        "area_ok": area_ok,
        "passes": delta_length_ok and area_ok,
    }


def evaluate(
    script_path: Path | str,
    stack: dict,
    spec: dict,
    *,
    measured_metrics: dict | None = None,
    cache_dir: Path | None = None,
) -> MultiSpecReport:
    """
    Judge a device script against a (possibly multi-metric) spec on a stack.

    Accepts both spec forms: v1 {"target": {...}} and v2 {"targets": [...]}.
    Tier-0 metrics (fsr_nm) are computed here from the measured delta_length
    and a local mode solve — a supplied value never overrides the evaluator's
    own physics. Tier>=1 metrics (extinction_ratio_db, insertion_loss_db, ...)
    are not computable locally from geometry: they judge only when a value is
    fed in via measured_metrics (full-wave results), else the verdict is
    "unmeasured". Overall passes requires every target measured AND passing
    AND no constraint violated — unmeasured is never counted as a pass.
    """
    wavelength_um, targets, constraints = _normalize_spec(spec)
    supplied = dict(measured_metrics or {})
    requested = {target["metric"] for target in targets}

    payload = measured_lengths(script_path)
    mode = solve_waveguide(stack, wavelength_um, cache_dir=cache_dir)

    # Per-metric local physics, each from its own lengths.json shape. The
    # legacy two-arm contract is validated whenever the shape is present OR
    # fsr_nm is requested (missing/malformed arms must still fail loudly).
    local_values: dict[str, float] = {}
    delta_length_um = None
    if "arms" in payload or "fsr_nm" in requested:
        arm_data = _validate_arms(payload)
        delta_length_um = arm_data["delta_length_um"]
        local_values["fsr_nm"] = compute_fsr_nm(wavelength_um, mode.n_g, delta_length_um)
    if "ring_fsr_nm" in requested:
        ring = _require_shape(payload, "ring", ("round_trip_um",), "ring_fsr_nm")
        round_trip = _bounded(
            ring["round_trip_um"], _RING_ROUND_TRIP_BOUNDS_UM, "ring round_trip_um"
        )
        local_values["ring_fsr_nm"] = wavelength_um**2 / (mode.n_g * round_trip) * 1000.0
    if "group_delay_ps" in requested:
        path_shape = _require_shape(payload, "path", ("total_um",), "group_delay_ps")
        total = _bounded(path_shape["total_um"], _PATH_TOTAL_BOUNDS_UM, "path total_um")
        local_values["group_delay_ps"] = mode.n_g * total / _UM_PER_PS_LIGHT
    if "coupling_ratio" in requested:
        coupler = _require_shape(payload, "coupler", ("length_um", "gap_um"), "coupling_ratio")
        width = coupler.get("width_um", float(stack["single_mode_width_um"]))
        super_result = solve_supermodes(
            stack,
            wavelength_um,
            width_um=width,
            gap_um=coupler["gap_um"],
            cache_dir=cache_dir,
        )
        argument = math.pi * coupler["length_um"] / (2.0 * super_result.coupling_length_um)
        local_values["coupling_ratio"] = math.sin(argument) ** 2
    if "bragg_wavelength_nm" in requested:
        grating = _require_shape(
            payload, "grating", ("period_um", "w1_um", "w2_um"), "bragg_wavelength_nm"
        )
        n1 = solve_waveguide(
            stack, wavelength_um, width_um=grating["w1_um"], cache_dir=cache_dir
        ).n_eff
        n2 = solve_waveguide(
            stack, wavelength_um, width_um=grating["w2_um"], cache_dir=cache_dir
        ).n_eff
        bragg_nm = 2.0 * ((n1 + n2) / 2.0) * grating["period_um"] * 1000.0
        local_values["bragg_wavelength_nm"] = _bounded(
            bragg_nm, _BRAGG_WAVELENGTH_BOUNDS_NM, "bragg_wavelength_nm"
        )

    verdicts = []
    for target in targets:
        metric = target["metric"]
        tier = int(target["tier"])
        if metric in local_values:
            value, source = local_values[metric], "local"
        elif metric in supplied:
            value, source = float(supplied[metric]), "supplied"
        else:
            verdicts.append(
                TargetVerdict(metric=metric, tier=tier, verdict="unmeasured", target=dict(target))
            )
            continue
        passed, rel_error = _judge_target(target, value)
        verdicts.append(
            TargetVerdict(
                metric=metric,
                tier=tier,
                verdict="pass" if passed else "fail",
                target=dict(target),
                measured=value,
                rel_error=rel_error,
                source=source,
            )
        )

    # Optional footprint constraint: constraints["max_footprint_um"] = [L, W].
    # The bbox is measured from the written GDS, not declared.
    bbox_um = None
    max_footprint = None
    footprint_ok = None
    constraint = constraints.get("max_footprint_um")
    if constraint is not None:
        max_footprint = (float(constraint[0]), float(constraint[1]))
        bbox_um = _layer_bbox(_find_gds(Path(script_path).resolve().parent))
        footprint_ok = bbox_um[0] <= max_footprint[0] and bbox_um[1] <= max_footprint[1]

    failed = tuple(v.metric for v in verdicts if v.verdict == "fail")
    unmeasured = tuple(v.metric for v in verdicts if v.verdict == "unmeasured")
    issues = []
    if failed:
        issues.append("failed targets: " + ", ".join(failed))
    if unmeasured:
        issues.append("unmeasured targets: " + ", ".join(unmeasured))
    if footprint_ok is False:
        issues.append("footprint exceeds max_footprint_um")

    return MultiSpecReport(
        passes=not issues,
        verdicts=tuple(verdicts),
        unmeasured=unmeasured,
        reason="; ".join(issues),
        n_eff=mode.n_eff,
        n_g=mode.n_g,
        delta_length_um=delta_length_um,
        wavelength_um=wavelength_um,
        stack_label=str(stack.get("label", "unlabeled stack")),
        from_cache=mode.from_cache,
        bbox_um=bbox_um,
        max_footprint_um=max_footprint,
        footprint_ok=footprint_ok,
    )


def evaluate_mzi_fsr(
    script_path: Path | str,
    stack: dict,
    spec: dict,
    cache_dir: Path | None = None,
) -> SpecReport:
    """Legacy single-target FSR entry point — a thin wrapper over evaluate()."""
    report = evaluate(script_path, stack, spec, cache_dir=cache_dir)
    fsr = next(v for v in report.verdicts if v.metric == "fsr_nm")
    return SpecReport(
        fsr_nm=fsr.measured,
        target_nm=float(fsr.target["value"]),
        tolerance_rel=float(fsr.target["tolerance_rel"]),
        rel_error=fsr.rel_error,
        passes=report.passes,
        n_eff=report.n_eff,
        n_g=report.n_g,
        delta_length_um=report.delta_length_um,
        wavelength_um=report.wavelength_um,
        stack_label=report.stack_label,
        from_cache=report.from_cache,
        bbox_um=report.bbox_um,
        max_footprint_um=report.max_footprint_um,
        footprint_ok=report.footprint_ok,
    )


def analytic_transmission(
    wavelengths_um: "list[float]",
    n_eff0: float,
    n_g: float,
    delta_length_um: float,
    wavelength0_um: float = 1.55,
) -> "list[float]":
    """
    Idealized MZI bar-port transmission |S21|^2 from mode-solved dispersion.

    T(lambda) = cos^2(pi * dL * n_eff(lambda) / lambda) with first-order
    dispersion n_eff(lambda) = n_eff0 + (n_eff0 - n_g)/lambda0 * (lambda - lambda0)
    (so that the fringe spacing reproduces FSR = lambda0^2 / (n_g * dL)).
    Assumes ideal 50/50 splitters, lossless single-mode arms — the spacing is
    exact under those assumptions; depth/level are not. This is the analytic
    tier; the full S-matrix tier is a Tidy3D FDTD of the layout (cloud,
    draft-only by policy).
    """
    dn_dl = (n_eff0 - n_g) / wavelength0_um
    out = []
    for wl in wavelengths_um:
        n_eff = n_eff0 + dn_dl * (wl - wavelength0_um)
        phase = math.pi * delta_length_um * n_eff / wl
        out.append(math.cos(phase) ** 2)
    return out


def spectrum(
    script_path: Path | str,
    stack: dict,
    *,
    center_um: float = 1.55,
    span_nm: float = 40.0,
    points: int = 4001,
    cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Analytic T(lambda) of a device script on a stack, from real mode solves."""
    measured = measured_delta_length(script_path)
    mode = solve_waveguide(stack, center_um, cache_dir=cache_dir)
    half = span_nm / 2000.0  # nm -> um
    wavelengths = [center_um - half + i * (2 * half) / (points - 1) for i in range(points)]
    t = analytic_transmission(
        wavelengths, mode.n_eff, mode.n_g, measured["delta_length_um"], center_um
    )
    return {
        "wavelength_um": wavelengths,
        "transmission": t,
        "n_eff": mode.n_eff,
        "n_g": mode.n_g,
        "delta_length_um": measured["delta_length_um"],
        "fsr_nm": compute_fsr_nm(center_um, mode.n_g, measured["delta_length_um"]),
        "model": "analytic two-beam interference (ideal 50/50, lossless); "
        "dispersion first-order from local mode solve",
    }


def _normalize_spec(spec: dict) -> tuple[float, list[dict], dict]:
    """Normalize v1 ({"target": ...}) and v2 ({"targets": [...]}) spec forms."""
    wavelength_um = float(spec.get("wavelength_um", 1.55))
    if "targets" in spec:
        targets = [dict(t) for t in spec["targets"]]
    elif "target" in spec:
        targets = [dict(spec["target"])]
    else:
        raise ValueError("Spec needs 'targets' (schema v2) or 'target' (v1)")
    if not targets:
        raise ValueError("Spec 'targets' must not be empty")
    for target in targets:
        target.setdefault("metric", "fsr_nm")
        target.setdefault("tier", 0 if target["metric"] in LOCAL_METRICS else 1)
        if not ({"value", "min", "max"} & target.keys()):
            raise ValueError(f"Target {target['metric']} needs 'value', 'min', or 'max'")
        # A ratio near 0.5 makes relative tolerance misleading; coupling_ratio
        # defaults to an absolute window unless the spec says otherwise.
        if (
            target["metric"] == "coupling_ratio"
            and "value" in target
            and "tolerance_abs" not in target
            and "tolerance_rel" not in target
        ):
            target["tolerance_abs"] = 0.05
    return wavelength_um, targets, spec.get("constraints") or {}


def _judge_target(target: dict, value: float) -> tuple[bool, float | None]:
    """Judge a measured value against one target; returns (passed, rel_error)."""
    if "value" in target:
        reference = float(target["value"])
        rel_error = abs(value - reference) / reference if reference != 0 else None
        if "tolerance_abs" in target:
            return abs(value - reference) <= float(target["tolerance_abs"]), rel_error
        tolerance_rel = float(target.get("tolerance_rel", 0.0))
        if rel_error is None:
            raise ValueError("tolerance_rel cannot judge a zero-valued target")
        return rel_error <= tolerance_rel, rel_error
    passed = True
    if "min" in target:
        passed = passed and value >= float(target["min"])
    if "max" in target:
        passed = passed and value <= float(target["max"])
    return passed, None


def _coupling_length(
    n_even: float, n_odd: float, core_n: float, clad_n: float, wavelength_um: float
) -> float:
    """Guarded directional-coupler coupling length from supermode splitting."""
    _check_n_eff(n_even, core_n=core_n, clad_n=clad_n, label="n_even")
    _check_n_eff(n_odd, core_n=core_n, clad_n=clad_n, label="n_odd")
    split = n_even - n_odd
    if split <= MIN_SUPERMODE_SPLIT:
        raise ValueError(
            f"Degenerate supermodes: n_even={n_even:.6f}, n_odd={n_odd:.6f} — "
            f"splitting {split:.2e} is below {MIN_SUPERMODE_SPLIT} (or mis-ordered)"
        )
    return wavelength_um / (2.0 * split)


def _check_mode_ladder(n_effs: tuple[float, ...], *, core_n: float, clad_n: float) -> None:
    """Guard a mode ladder: every n_eff physical, strictly decreasing order."""
    for i, n_eff in enumerate(n_effs):
        _check_n_eff(n_eff, core_n=core_n, clad_n=clad_n, label=f"n_effs[{i}]")
    if any(a <= b for a, b in zip(n_effs, n_effs[1:])):
        raise ValueError(f"Mode indices must be strictly decreasing, got {n_effs}")


def _beat_length(
    n_effs: tuple[float, ...], core_n: float, clad_n: float, wavelength_um: float
) -> float:
    """Guarded MMI beat length from the two leading modes."""
    _check_mode_ladder(n_effs, core_n=core_n, clad_n=clad_n)
    split = n_effs[0] - n_effs[1]
    if split <= MIN_SUPERMODE_SPLIT:
        raise ValueError(f"Degenerate leading modes: splitting {split:.2e} gives no beat length")
    return wavelength_um / (2.0 * split)


def _cache_filename(
    core_n: float,
    clad_n: float,
    thickness_um: float,
    width_um: float,
    wavelength_um: float,
) -> str:
    key = (
        f"core{core_n:.6f}_clad{clad_n:.6f}_t{thickness_um:.6f}"
        f"_w{width_um:.6f}_wl{wavelength_um:.6f}"
    )
    return f"mode_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"


def _run_mode_solver(
    core_n: float,
    clad_n: float,
    thickness_um: float,
    width_um: float,
    wavelength_um: float,
) -> tuple[float, float]:
    """
    Local tidy3d mode solve of a strip waveguide; returns (n_eff, n_g).

    Strictly the local ModeSolver plugin — tidy3d.web / cloud must never be
    imported or called from this module.
    """
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d.constants import C_0
    from tidy3d.plugins.mode import ModeSolver

    simulation = td.Simulation(
        size=(wavelength_um, PLANE_SIZE_UM, PLANE_SIZE_UM),
        grid_spec=td.GridSpec.auto(wavelength=wavelength_um, min_steps_per_wvl=MIN_STEPS_PER_WVL),
        structures=[
            td.Structure(
                geometry=td.Box(center=(0, 0, 0), size=(td.inf, width_um, thickness_um)),
                medium=td.Medium(permittivity=core_n**2),
            )
        ],
        medium=td.Medium(permittivity=clad_n**2),
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.Periodic()),
        run_time=1e-12,
    )
    solver = ModeSolver(
        simulation=simulation,
        plane=td.Box(center=(0, 0, 0), size=(0, PLANE_SIZE_UM, PLANE_SIZE_UM)),
        mode_spec=td.ModeSpec(num_modes=1, group_index_step=True),
        freqs=[C_0 / wavelength_um],
    )
    data = solver.solve()
    n_eff = float(data.n_eff.isel(f=0, mode_index=0).values.real)
    n_g = float(data.n_group.isel(f=0, mode_index=0).values.real)
    return n_eff, n_g


def _run_supermode_solver(
    core_n: float,
    clad_n: float,
    thickness_um: float,
    width_um: float,
    gap_um: float,
    wavelength_um: float,
) -> tuple[float, float]:
    """
    Local tidy3d solve of two identical coupled cores; returns (n_even, n_odd).

    Strictly the local ModeSolver plugin — tidy3d.web / cloud must never be
    imported or called from this module.
    """
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d.constants import C_0
    from tidy3d.plugins.mode import ModeSolver

    pitch = width_um + gap_um  # center-to-center separation
    plane_w = max(PLANE_SIZE_UM, 2 * width_um + gap_um + 4.0)
    core_medium = td.Medium(permittivity=core_n**2)
    simulation = td.Simulation(
        size=(wavelength_um, plane_w, PLANE_SIZE_UM),
        grid_spec=td.GridSpec.auto(wavelength=wavelength_um, min_steps_per_wvl=MIN_STEPS_PER_WVL),
        structures=[
            td.Structure(
                geometry=td.Box(
                    center=(0, sign * pitch / 2, 0), size=(td.inf, width_um, thickness_um)
                ),
                medium=core_medium,
            )
            for sign in (-1, 1)
        ],
        medium=td.Medium(permittivity=clad_n**2),
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.Periodic()),
        run_time=1e-12,
    )
    solver = ModeSolver(
        simulation=simulation,
        plane=td.Box(center=(0, 0, 0), size=(0, plane_w, PLANE_SIZE_UM)),
        mode_spec=td.ModeSpec(num_modes=2),
        freqs=[C_0 / wavelength_um],
    )
    data = solver.solve()
    n_effs = [float(data.n_eff.isel(f=0, mode_index=i).values.real) for i in range(2)]
    return max(n_effs), min(n_effs)


def _run_multimode_solver(
    core_n: float,
    clad_n: float,
    thickness_um: float,
    width_um: float,
    n_modes: int,
    wavelength_um: float,
) -> list[float]:
    """
    Local tidy3d solve of a single wide core; returns n_modes effective indices.

    Strictly the local ModeSolver plugin — tidy3d.web / cloud must never be
    imported or called from this module.
    """
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d.constants import C_0
    from tidy3d.plugins.mode import ModeSolver

    plane_w = max(PLANE_SIZE_UM, width_um + 4.0)
    simulation = td.Simulation(
        size=(wavelength_um, plane_w, PLANE_SIZE_UM),
        grid_spec=td.GridSpec.auto(wavelength=wavelength_um, min_steps_per_wvl=MIN_STEPS_PER_WVL),
        structures=[
            td.Structure(
                geometry=td.Box(center=(0, 0, 0), size=(td.inf, width_um, thickness_um)),
                medium=td.Medium(permittivity=core_n**2),
            )
        ],
        medium=td.Medium(permittivity=clad_n**2),
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.Periodic()),
        run_time=1e-12,
    )
    solver = ModeSolver(
        simulation=simulation,
        plane=td.Box(center=(0, 0, 0), size=(0, plane_w, PLANE_SIZE_UM)),
        mode_spec=td.ModeSpec(num_modes=n_modes),
        freqs=[C_0 / wavelength_um],
    )
    data = solver.solve()
    return [float(data.n_eff.isel(f=0, mode_index=i).values.real) for i in range(n_modes)]


def _run_cross_section_solver(
    core_n: float,
    clad_n: float,
    thickness_um: float,
    cores: tuple[tuple[float, float], ...],
    n_modes: int,
    wavelength_um: float,
) -> list[float]:
    """
    Local tidy3d solve of an arbitrary multi-core slice; returns n_modes indices.

    Strictly the local ModeSolver plugin — tidy3d.web / cloud must never be
    imported or called from this module.
    """
    from homi.optional_deps import require_tidy3d

    td = require_tidy3d()
    from tidy3d.constants import C_0
    from tidy3d.plugins.mode import ModeSolver

    # span + 4 um of clad margin; reduces to the solve_supermodes plane
    # (2w + gap + 4) for a symmetric pair, so the two paths share a grid.
    span = max(y + w / 2 for w, y in cores) - min(y - w / 2 for w, y in cores)
    plane_w = max(PLANE_SIZE_UM, span + 4.0)
    core_medium = td.Medium(permittivity=core_n**2)
    simulation = td.Simulation(
        size=(wavelength_um, plane_w, PLANE_SIZE_UM),
        grid_spec=td.GridSpec.auto(wavelength=wavelength_um, min_steps_per_wvl=MIN_STEPS_PER_WVL),
        structures=[
            td.Structure(
                geometry=td.Box(center=(0, y, 0), size=(td.inf, w, thickness_um)),
                medium=core_medium,
            )
            for w, y in cores
        ],
        medium=td.Medium(permittivity=clad_n**2),
        boundary_spec=td.BoundarySpec.all_sides(boundary=td.Periodic()),
        run_time=1e-12,
    )
    solver = ModeSolver(
        simulation=simulation,
        plane=td.Box(center=(0, 0, 0), size=(0, plane_w, PLANE_SIZE_UM)),
        mode_spec=td.ModeSpec(num_modes=n_modes),
        freqs=[C_0 / wavelength_um],
    )
    data = solver.solve()
    return [float(data.n_eff.isel(f=0, mode_index=i).values.real) for i in range(n_modes)]


def _check_n_eff(n_eff: float, *, core_n: float, clad_n: float, label: str = "n_eff") -> None:
    if not clad_n <= n_eff <= core_n:
        raise ValueError(
            f"Unphysical {label}={n_eff:.4f}: must lie in [clad_n={clad_n}, core_n={core_n}]"
        )


def _check_sane(n_eff: float, n_g: float, *, core_n: float, clad_n: float) -> None:
    """Refuse absurd solver output rather than propagating it — never fudge."""
    _check_n_eff(n_eff, core_n=core_n, clad_n=clad_n)
    lo, hi = N_G_BOUNDS
    if not lo <= n_g <= hi:
        raise ValueError(f"Absurd n_g={n_g:.4f}: must lie in [{lo}, {hi}]")


def _python_executable() -> str:
    # The interpreter running this process has the whole stack installed —
    # never a checkout-relative .venv path (breaks installed/uvx runs).
    return sys.executable


def _run_script(script: Path) -> None:
    proc = subprocess.run(
        [_python_executable(), script.name],
        cwd=script.parent,
        capture_output=True,
        text=True,
        timeout=SCRIPT_TIMEOUT_S,
    )
    if proc.returncode != 0:
        tail = proc.stderr.strip().splitlines()[-15:]
        raise RuntimeError(
            f"Script {script.name} failed (exit {proc.returncode}):\n" + "\n".join(tail)
        )


def _build_and_measure(run_dir: Path, script_name: str, source: str) -> tuple[float, float]:
    """Run one script variant in an isolated dir; return (delta_length_um, layer-(1,0) area)."""
    run_dir.mkdir(parents=True)
    script = run_dir / script_name
    script.write_text(source)
    measured = measured_delta_length(script)
    return measured["delta_length_um"], _layer_area(_find_gds(run_dir))


def _find_gds(directory: Path) -> Path:
    gds_files = sorted(directory.glob("*.gds"), key=lambda p: p.stat().st_mtime)
    if not gds_files:
        raise RuntimeError(f"Script did not write a GDS file in {directory}")
    return gds_files[-1]


def _layer_bbox(gds_path: Path, layer: tuple[int, int] = (1, 0)) -> tuple[float, float]:
    """(length, width) of the layer's bounding box in um, from the written GDS."""
    library = gdstk.read_gds(str(gds_path))
    lo_x = lo_y = float("inf")
    hi_x = hi_y = float("-inf")
    for cell in library.top_level():
        if "$$$" in cell.name:
            continue
        for polygon in cell.get_polygons(depth=None, layer=layer[0], datatype=layer[1]):
            (bx0, by0), (bx1, by1) = polygon.bounding_box()
            lo_x, lo_y = min(lo_x, bx0), min(lo_y, by0)
            hi_x, hi_y = max(hi_x, bx1), max(hi_y, by1)
    if lo_x == float("inf"):
        raise RuntimeError(f"No layer-{layer} polygons in {gds_path}")
    return (round(hi_x - lo_x, 3), round(hi_y - lo_y, 3))


def _layer_area(gds_path: Path, layer: tuple[int, int] = (1, 0)) -> float:
    """Total polygon area on a layer, from top cells (gdsfactory metadata cells excluded)."""
    library = gdstk.read_gds(str(gds_path))
    total = 0.0
    for cell in library.top_level():
        if "$$$" in cell.name:  # kfactory writes a $$$CONTEXT_INFO$$$ metadata cell
            continue
        for polygon in cell.get_polygons(depth=None, layer=layer[0], datatype=layer[1]):
            total += polygon.area()
    return total


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def _parse_cores(text: str) -> tuple[tuple[float, float], ...]:
    """Parse the CLI cores format "w:y,w:y,..." into ((w, y), ...)."""
    cores = []
    for token in text.split(","):
        parts = token.split(":")
        if len(parts) != 2:
            raise ValueError(f"Bad core '{token}': expected 'width_um:y_offset_um'")
        cores.append((float(parts[0]), float(parts[1])))
    return tuple(cores)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m homi.spec_optimization",
        description="Deterministic spec evaluator: local mode solve + MZI FSR vs spec.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    eval_p = sub.add_parser("eval", help="Evaluate a device script against a spec")
    eval_p.add_argument("--script", required=True, help="Parametric device script")
    eval_p.add_argument("--stack", required=True, help="Layer stack JSON")
    eval_p.add_argument("--spec", required=True, help="Spec JSON (v1 'target' or v2 'targets')")
    eval_p.add_argument(
        "--measured", help="JSON dict of full-wave results for tier>=1 metrics, e.g. measured.json"
    )
    eval_p.add_argument("--json", dest="json_out", help="Write the full report JSON here")
    eval_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    solve_p = sub.add_parser("solve", help="Mode-solve a stack's strip waveguide")
    solve_p.add_argument("--stack", required=True, help="Layer stack JSON")
    solve_p.add_argument("--width", type=float, help="Override waveguide width (um)")
    solve_p.add_argument("--wavelength", type=float, default=1.55, help="Wavelength (um)")
    solve_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    super_p = sub.add_parser("supermodes", help="Even/odd supermodes of two coupled cores")
    super_p.add_argument("--stack", required=True, help="Layer stack JSON")
    super_p.add_argument("--width", type=float, required=True, help="Core width (um)")
    super_p.add_argument("--gap", type=float, required=True, help="Edge-to-edge gap (um)")
    super_p.add_argument("--wavelength", type=float, default=1.55, help="Wavelength (um)")
    super_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    multi_p = sub.add_parser("multimode", help="Leading modes of a wide core (MMI body)")
    multi_p.add_argument("--stack", required=True, help="Layer stack JSON")
    multi_p.add_argument("--width", type=float, required=True, help="Core width (um)")
    multi_p.add_argument("--modes", type=int, default=2, help="Number of modes (default 2)")
    multi_p.add_argument("--wavelength", type=float, default=1.55, help="Wavelength (um)")
    multi_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    xsec_p = sub.add_parser("cross-section", help="Supermodes of an arbitrary multi-core slice")
    xsec_p.add_argument("--stack", required=True, help="Layer stack JSON")
    xsec_p.add_argument(
        "--cores",
        required=True,
        help="Cores as 'w:y,w:y,...' (um), e.g. '0.4:-0.55,0.5:0,0.4:0.55'",
    )
    xsec_p.add_argument("--modes", type=int, default=2, help="Number of modes (default 2)")
    xsec_p.add_argument("--wavelength", type=float, default=1.55, help="Wavelength (um)")
    xsec_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    spec_p = sub.add_parser("spectrum", help="Analytic T(lambda) of a device script on a stack")
    spec_p.add_argument("--script", required=True, help="Parametric device script")
    spec_p.add_argument("--stack", required=True, help="Layer stack JSON")
    spec_p.add_argument("--span-nm", type=float, default=40.0)
    spec_p.add_argument("--json", dest="json_out", help="Write spectrum JSON here")
    spec_p.add_argument("--cache-dir", help="Mode-solve cache dir (default: experiment output)")

    args = parser.parse_args(argv)
    cache_dir = Path(args.cache_dir) if args.cache_dir else None

    if args.command == "spectrum":
        stack = _load_json(args.stack)
        result = spectrum(args.script, stack, span_nm=args.span_nm, cache_dir=cache_dir)
        print(
            f"[{stack.get('label', args.stack)}] analytic FSR={result['fsr_nm']:.4f} nm "
            f"(n_g={result['n_g']:.4f}, dL={result['delta_length_um']:.3f} um, "
            f"{len(result['wavelength_um'])} pts over {args.span_nm} nm)"
        )
        if args.json_out:
            Path(args.json_out).write_text(json.dumps(result, indent=1))
        return 0

    if args.command == "solve":
        stack = _load_json(args.stack)
        result = solve_waveguide(stack, args.wavelength, width_um=args.width, cache_dir=cache_dir)
        width = args.width if args.width is not None else stack["single_mode_width_um"]
        print(
            f"[{stack.get('label', args.stack)}] n_eff={result.n_eff:.4f} "
            f"n_g={result.n_g:.4f} @ {args.wavelength} um, width={width} um"
            f"{' (cached)' if result.from_cache else ''}"
        )
        return 0

    if args.command == "supermodes":
        stack = _load_json(args.stack)
        result = solve_supermodes(
            stack, args.wavelength, width_um=args.width, gap_um=args.gap, cache_dir=cache_dir
        )
        print(
            f"[{stack.get('label', args.stack)}] n_even={result.n_even:.6f} "
            f"n_odd={result.n_odd:.6f} dn={result.n_even - result.n_odd:.6f} -> "
            f"Lc={result.coupling_length_um:.2f} um @ {args.wavelength} um "
            f"(w={args.width}, gap={args.gap}){' (cached)' if result.from_cache else ''}"
        )
        return 0

    if args.command == "multimode":
        stack = _load_json(args.stack)
        result = solve_multimode(
            stack, args.wavelength, width_um=args.width, n_modes=args.modes, cache_dir=cache_dir
        )
        n_effs = ", ".join(f"{n:.6f}" for n in result.n_effs)
        print(
            f"[{stack.get('label', args.stack)}] n_effs=[{n_effs}] -> "
            f"beat={result.beat_length_um:.2f} um @ {args.wavelength} um "
            f"(w={args.width}, {args.modes} modes){' (cached)' if result.from_cache else ''}"
        )
        return 0

    if args.command == "cross-section":
        stack = _load_json(args.stack)
        cores = _parse_cores(args.cores)
        result = solve_cross_section(
            stack, args.wavelength, cores=cores, n_modes=args.modes, cache_dir=cache_dir
        )
        n_effs = ", ".join(f"{n:.6f}" for n in result.n_effs)
        cores_str = ", ".join(f"{w}@{y:+}" for w, y in cores)
        print(
            f"[{stack.get('label', args.stack)}] n_effs=[{n_effs}] @ {args.wavelength} um "
            f"({len(cores)} cores: {cores_str}){' (cached)' if result.from_cache else ''}"
        )
        return 0

    measured_metrics = _load_json(args.measured) if args.measured else None
    report = evaluate(
        args.script,
        _load_json(args.stack),
        _load_json(args.spec),
        measured_metrics=measured_metrics,
        cache_dir=cache_dir,
    )
    parts = []
    for v in report.verdicts:
        if v.verdict == "unmeasured":
            parts.append(f"{v.metric}=? UNMEASURED")
        elif v.rel_error is not None:
            parts.append(f"{v.metric}={v.measured:.4f} ({v.rel_error:.2%} off) {v.verdict.upper()}")
        else:
            parts.append(f"{v.metric}={v.measured:.4f} {v.verdict.upper()}")
    footprint = ""
    if report.footprint_ok is not None:
        footprint = (
            f" | bbox={report.bbox_um[0]:.1f}x{report.bbox_um[1]:.1f} um vs "
            f"budget {report.max_footprint_um[0]:.1f}x{report.max_footprint_um[1]:.1f} -> "
            f"{'fits' if report.footprint_ok else 'EXCEEDS'}"
        )
    overall = "PASS" if report.passes else ("INCOMPLETE" if report.unmeasured else "MISS")
    delta_part = (
        f"dL={report.delta_length_um:.3f} um"
        if report.delta_length_um is not None
        else "dL=n/a"
    )
    print(
        f"[{report.stack_label}] " + " | ".join(parts) + footprint + f" => {overall}"
        f"{f' ({report.reason})' if report.reason else ''} "
        f"[n_eff={report.n_eff:.4f}, n_g={report.n_g:.4f}, "
        f"{delta_part}{', cached' if report.from_cache else ''}]"
    )
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report.to_dict(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
