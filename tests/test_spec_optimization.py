"""
Tests for homi.spec_optimization — deterministic spec evaluator.

Covers: physics anchors (local mode solves), disk cache behavior, the sanity
guard, the FSR formula, the script measurement contract, and knob-response
verification. All tests run offline (the tidy3d ModeSolver plugin is local).
"""

import json
import textwrap
from pathlib import Path

import pytest

from homi import spec_optimization as so

REPO_ROOT = Path(__file__).parent.parent
import importlib.util as _ilu
_needs_tidy3d = pytest.mark.skipif(_ilu.find_spec("tidy3d") is None,
                                   reason="pixcell[simulate] extra not installed")
from homi.paths import stacks_dir as _stacks_dir
STACKS_DIR = _stacks_dir()  # checkout record if present, else the packaged assets

FAKE_STACK = {
    "label": "fake 220 nm SOI",
    "core_n": 3.476,
    "clad_n": 1.444,
    "thickness_um": 0.22,
    "single_mode_width_um": 0.5,
}

# Parametric fixture honoring the script contract: tunables as top-level
# `name = value` assignments, arm lengths computed from the script's OWN
# gf.Path objects (never hand-entered), lengths.json + GDS written beside it.
FIXTURE_SCRIPT = textwrap.dedent("""
    import json
    from pathlib import Path

    import gdsfactory as gf

    delta_length = 30.0
    width = 0.5
    base_length = 40.0

    out_dir = Path(__file__).parent

    short_path = gf.path.straight(length=base_length)
    long_path = gf.Path([(0.0, 10.0), (base_length + delta_length, 10.0)])

    c = gf.Component()
    c << gf.path.extrude(short_path, layer=(1, 0), width=width)
    c << gf.path.extrude(long_path, layer=(1, 0), width=width)

    arms = {"short": short_path.length(), "long": long_path.length()}
    lengths = {"arms": arms, "delta_length_um": arms["long"] - arms["short"]}

    c.write_gds(out_dir / "device.gds")
    (out_dir / "lengths.json").write_text(json.dumps(lengths, indent=2))
    """)


def load_stack(name: str) -> dict:
    return json.loads((STACKS_DIR / f"{name}.json").read_text())


def write_fixture(tmp_path: Path) -> Path:
    script = tmp_path / "mzi_fixture.py"
    script.write_text(FIXTURE_SCRIPT)
    return script


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_soi220_mode_anchor(tmp_path):
    result = so.solve_waveguide(load_stack("soi220"), cache_dir=tmp_path)
    assert 2.35 <= result.n_eff <= 2.50
    assert 3.95 <= result.n_g <= 4.25
    assert result.from_cache is False


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_sin400_mode_anchor(tmp_path):
    result = so.solve_waveguide(load_stack("sin400"), cache_dir=tmp_path)
    assert 1.90 <= result.n_g <= 2.15


def test_cache_second_call_skips_solver(tmp_path, monkeypatch):
    calls = []

    def fake_solver(core_n, clad_n, thickness_um, width_um, wavelength_um):
        calls.append(width_um)
        return 2.42, 4.08

    monkeypatch.setattr(so, "_run_mode_solver", fake_solver)

    first = so.solve_waveguide(FAKE_STACK, cache_dir=tmp_path)
    second = so.solve_waveguide(FAKE_STACK, cache_dir=tmp_path)
    assert first.from_cache is False
    assert second.from_cache is True
    assert (second.n_eff, second.n_g) == (first.n_eff, first.n_g)
    assert len(calls) == 1

    # A different width is a different cache key and must re-solve.
    third = so.solve_waveguide(FAKE_STACK, width_um=0.6, cache_dir=tmp_path)
    assert third.from_cache is False
    assert calls == [0.5, 0.6]


def test_sanity_guard_rejects_absurd_results(tmp_path, monkeypatch):
    # n_eff above core index is unphysical.
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (3.9, 4.0))
    with pytest.raises(ValueError):
        so.solve_waveguide(FAKE_STACK, cache_dir=tmp_path)

    # n_g outside [1, 6] is absurd. Same cache key as above: this also proves
    # the failed solve was NOT cached (a cache hit would bypass the raise).
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.4, 8.0))
    with pytest.raises(ValueError):
        so.solve_waveguide(FAKE_STACK, cache_dir=tmp_path)


def test_fsr_formula_synthetic():
    # FSR = lambda^2 / (n_g * dL): 1.55^2 / (4.0 * 75.0) um = 8.008333e-3 um.
    assert so.compute_fsr_nm(1.55, 4.0, 75.0) == pytest.approx(8.0083333, rel=1e-6)
    # dL = 75.078125 um makes it exactly 8.0 nm (4 * 75.078125 * 0.008 = 2.4025).
    assert so.compute_fsr_nm(1.55, 4.0, 75.078125) == pytest.approx(8.0, rel=1e-9)
    with pytest.raises(ValueError):
        so.compute_fsr_nm(1.55, 4.0, 0.0)


def test_measured_delta_length_runs_script_contract(tmp_path):
    script = write_fixture(tmp_path)
    measured = so.measured_delta_length(script)
    assert measured["delta_length_um"] == pytest.approx(30.0)
    assert measured["arms"]["short"] == pytest.approx(40.0)
    assert measured["arms"]["long"] == pytest.approx(70.0)
    assert (tmp_path / "device.gds").exists()


def test_measured_delta_length_rejects_missing_lengths_json(tmp_path):
    script = tmp_path / "no_contract.py"
    script.write_text("print('writes nothing')\n")
    with pytest.raises(RuntimeError, match="lengths.json"):
        so.measured_delta_length(script)


def test_verify_knob_response(tmp_path):
    script = write_fixture(tmp_path)
    report = so.verify_knob_response(script, param="delta_length", delta_um=5.0, width_um=0.5)
    assert report["passes"] is True
    assert report["delta_response_um"] == pytest.approx(5.0, rel=0.01)
    # Area must grow by ~ width * delta = 2.5 um^2 (within 25%).
    assert report["area_growth_um2"] == pytest.approx(2.5, rel=0.25)
    assert report["base_delta_length_um"] == pytest.approx(30.0)
    assert report["perturbed_delta_length_um"] == pytest.approx(35.0)


def test_verify_knob_response_rejects_missing_knob(tmp_path):
    script = tmp_path / "no_knob.py"
    script.write_text("x = 1.0\n")
    with pytest.raises(ValueError, match="delta_length"):
        so.verify_knob_response(script, width_um=0.5)


def test_evaluate_mzi_fsr_report(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_fixture(tmp_path)
    spec = {
        "target": {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02},
        "wavelength_um": 1.55,
    }

    report = so.evaluate_mzi_fsr(script, FAKE_STACK, spec, cache_dir=tmp_path)
    # dL = 30 um, n_g = 4.0 -> FSR = 1.55^2 / (4 * 30) * 1000 = 20.0208 nm.
    assert report.fsr_nm == pytest.approx(20.020833, rel=1e-6)
    assert report.target_nm == 8.0
    assert report.tolerance_rel == 0.02
    assert report.rel_error == pytest.approx((report.fsr_nm - 8.0) / 8.0, rel=1e-9)
    assert report.passes is False
    assert report.n_eff == 2.42
    assert report.n_g == 4.0
    assert report.delta_length_um == pytest.approx(30.0)
    assert report.wavelength_um == 1.55
    assert report.stack_label == FAKE_STACK["label"]
    assert report.from_cache is False

    as_dict = report.to_dict()
    assert as_dict["fsr_nm"] == report.fsr_nm
    assert as_dict["passes"] is False
    json.dumps(as_dict)  # must be JSON-serializable


def test_evaluate_mzi_fsr_passes_at_target(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = tmp_path / "mzi_on_spec.py"
    # 75.078 um sits on gdsfactory's 1 nm grid and puts FSR ~8.00001 nm at n_g=4.
    script.write_text(FIXTURE_SCRIPT.replace("delta_length = 30.0", "delta_length = 75.078"))
    spec = {
        "target": {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02},
        "wavelength_um": 1.55,
    }

    report = so.evaluate_mzi_fsr(script, FAKE_STACK, spec, cache_dir=tmp_path)
    assert report.fsr_nm == pytest.approx(so.compute_fsr_nm(1.55, 4.0, 75.078), rel=1e-9)
    assert report.passes is True


def test_cache_rejects_planted_absurd_values(tmp_path):
    """A writable cache entry must not smuggle unphysical n_g past the guard."""
    import hashlib

    stack = {"core_n": 3.476, "clad_n": 1.444, "thickness_um": 0.22, "single_mode_width_um": 0.5}
    key = f"core{3.476:.6f}_clad{1.444:.6f}_t{0.22:.6f}_w{0.5:.6f}_wl{1.55:.6f}"
    fname = f"mode_{hashlib.sha256(key.encode()).hexdigest()[:16]}.json"
    (tmp_path / fname).write_text(json.dumps({"n_eff": 2.4, "n_g": 42.0}))
    with pytest.raises(ValueError, match="n_g"):
        so.solve_waveguide(stack, 1.55, cache_dir=tmp_path)


def test_measured_delta_length_rejects_three_arms(tmp_path):
    """3+ arms must fail loudly, not bypass the delta consistency check."""
    script = tmp_path / "dev.py"
    script.write_text(
        "import json, pathlib\n"
        "here = pathlib.Path(__file__).parent\n"
        "(here / 'dev.gds').write_bytes(b'')\n"
        "payload = {'arms': {'a': 10.0, 'b': 20.0, 'c': 99.0}, 'delta_length_um': 10.0}\n"
        "(here / 'lengths.json').write_text(json.dumps(payload))\n"
    )
    with pytest.raises(RuntimeError, match="exactly 2 arms"):
        so.measured_delta_length(script)


def test_footprint_constraint_reported(tmp_path):
    """spec constraints.max_footprint_um gates passes on the measured bbox."""
    import textwrap

    script = tmp_path / "dev.py"
    script.write_text(textwrap.dedent("""
            import json, pathlib
            import gdsfactory as gf
            delta_length = 30.0
            c = gf.Component("fixture")
            p1 = gf.path.straight(length=40.0)
            p2 = gf.path.straight(length=40.0 + delta_length)
            xs = gf.cross_section.cross_section(width=0.5, layer=(1, 0))
            s1 = c << gf.path.extrude(p1, xs)
            s2 = c << gf.path.extrude(p2, xs)
            s2.dmovey(5.0)
            here = pathlib.Path(__file__).parent
            c.write_gds(here / "dev.gds")
            (here / "lengths.json").write_text(json.dumps(
                {"arms": {"a": p1.length(), "b": p2.length()},
                 "delta_length_um": p2.length() - p1.length()}))
            """))
    stack = {
        "core_n": 3.476,
        "clad_n": 1.444,
        "thickness_um": 0.22,
        "single_mode_width_um": 0.5,
        "label": "t",
    }
    base = {"target": {"value": 8.0, "tolerance_rel": 1000.0}, "wavelength_um": 1.55}
    tight = dict(base, constraints={"max_footprint_um": [10.0, 1.0]})
    loose = dict(base, constraints={"max_footprint_um": [200.0, 50.0]})
    r_tight = so.evaluate_mzi_fsr(script, stack, tight, cache_dir=tmp_path)
    r_loose = so.evaluate_mzi_fsr(script, stack, loose, cache_dir=tmp_path)
    assert r_tight.footprint_ok is False and r_tight.passes is False
    assert r_loose.footprint_ok is True and r_loose.passes is True
    assert r_loose.bbox_um[0] > 60.0


def test_analytic_transmission_fringe_spacing_matches_fsr():
    """Peak spacing of the analytic spectrum must reproduce lambda^2/(n_g*dL)."""
    n_eff0, n_g, dl, wl0 = 2.45, 4.06, 74.0, 1.55
    n = 40001
    span = 0.06  # um
    wls = [wl0 - span / 2 + i * span / (n - 1) for i in range(n)]
    t = so.analytic_transmission(wls, n_eff0, n_g, dl, wl0)
    peaks = [
        wls[i] for i in range(1, n - 1) if t[i] >= t[i - 1] and t[i] >= t[i + 1] and t[i] > 0.99
    ]
    assert len(peaks) >= 3
    spacings_nm = [(b - a) * 1000 for a, b in zip(peaks, peaks[1:])]
    expected = so.compute_fsr_nm(wl0, n_g, dl)
    mean_spacing = sum(spacings_nm) / len(spacings_nm)
    assert mean_spacing == pytest.approx(expected, rel=0.02)


# ---------------------------------------------------------------------------
# Schema v2: multi-metric specs, tiered evaluation, coupling-physics solves
# ---------------------------------------------------------------------------

V2_SPEC = {
    "device": "mzi",
    "wavelength_um": 1.55,
    "targets": [
        {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02, "tier": 0},
        {"metric": "extinction_ratio_db", "min": 20.0, "tier": 1},
        {"metric": "insertion_loss_db", "max": 1.0, "tier": 1},
    ],
}

OLD_SPEC = {
    "target": {"metric": "fsr_nm", "value": 8.0, "tolerance_rel": 0.02},
    "wavelength_um": 1.55,
}


def write_on_spec_fixture(tmp_path: Path) -> Path:
    """Fixture whose dL=75.078 um hits FSR ~8.0 nm at the faked n_g=4.0."""
    script = tmp_path / "mzi_on_spec.py"
    script.write_text(FIXTURE_SCRIPT.replace("delta_length = 30.0", "delta_length = 75.078"))
    return script


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_soi220_supermodes_anchor(tmp_path):
    stack = load_stack("soi220")
    result = so.solve_supermodes(stack, width_um=0.5, gap_um=0.2, cache_dir=tmp_path)
    assert result.n_even > result.n_odd
    assert stack["clad_n"] <= result.n_odd <= stack["core_n"]
    assert stack["clad_n"] <= result.n_even <= stack["core_n"]
    assert 3.0 <= result.coupling_length_um <= 60.0
    assert result.from_cache is False
    again = so.solve_supermodes(stack, width_um=0.5, gap_um=0.2, cache_dir=tmp_path)
    assert again.from_cache is True
    assert again.coupling_length_um == pytest.approx(result.coupling_length_um)


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_soi220_multimode_anchor(tmp_path):
    stack = load_stack("soi220")
    result = so.solve_multimode(stack, width_um=2.0, cache_dir=tmp_path)
    assert len(result.n_effs) == 2
    assert all(a > b for a, b in zip(result.n_effs, result.n_effs[1:]))
    assert 3.0 <= result.beat_length_um <= 60.0
    assert result.from_cache is False


def test_supermodes_cache_and_degeneracy_guard(tmp_path, monkeypatch):
    calls = []

    def fake_solver(core_n, clad_n, thickness_um, width_um, gap_um, wavelength_um):
        calls.append(gap_um)
        return 2.46, 2.43

    monkeypatch.setattr(so, "_run_supermode_solver", fake_solver)

    first = so.solve_supermodes(FAKE_STACK, width_um=0.5, gap_um=0.2, cache_dir=tmp_path)
    second = so.solve_supermodes(FAKE_STACK, width_um=0.5, gap_um=0.2, cache_dir=tmp_path)
    assert first.from_cache is False
    assert second.from_cache is True
    assert len(calls) == 1
    # Lc = wl / (2 dn) = 1.55 / (2 * 0.03).
    assert first.coupling_length_um == pytest.approx(1.55 / 0.06, rel=1e-9)
    assert second.coupling_length_um == pytest.approx(first.coupling_length_um)

    # A different gap is a different cache key and must re-solve.
    so.solve_supermodes(FAKE_STACK, width_um=0.5, gap_um=0.3, cache_dir=tmp_path)
    assert calls == [0.2, 0.3]

    # Degenerate supermodes (no splitting resolved) must raise, never divide.
    monkeypatch.setattr(so, "_run_supermode_solver", lambda *a: (2.45, 2.45))
    with pytest.raises(ValueError, match="[Dd]egenerate"):
        so.solve_supermodes(FAKE_STACK, width_um=0.5, gap_um=0.4, cache_dir=tmp_path)


def test_multimode_cache_and_mode_count_key(tmp_path, monkeypatch):
    calls = []

    def fake_solver(core_n, clad_n, thickness_um, width_um, n_modes, wavelength_um):
        calls.append(n_modes)
        return [2.7, 2.5, 2.2][:n_modes]

    monkeypatch.setattr(so, "_run_multimode_solver", fake_solver)

    first = so.solve_multimode(FAKE_STACK, width_um=2.0, cache_dir=tmp_path)
    second = so.solve_multimode(FAKE_STACK, width_um=2.0, cache_dir=tmp_path)
    assert first.from_cache is False
    assert second.from_cache is True
    assert len(calls) == 1
    # Beat length = wl / (2 * (n0 - n1)) = 1.55 / (2 * 0.2).
    assert first.beat_length_um == pytest.approx(1.55 / 0.4, rel=1e-9)
    assert second.n_effs == first.n_effs

    # n_modes is part of the cache key.
    third = so.solve_multimode(FAKE_STACK, width_um=2.0, n_modes=3, cache_dir=tmp_path)
    assert third.from_cache is False
    assert len(third.n_effs) == 3
    assert calls == [2, 3]


def test_extinction_helpers_round_trip():
    # Perfect 50/50 -> effectively infinite ER (reported at the cap).
    assert so.mzi_extinction_db(0.5) >= 60.0
    # 45/55 split -> 20 dB bar-port ER.
    assert so.mzi_extinction_db(0.45) == pytest.approx(20.0, abs=0.5)

    lo, hi = so.required_split_balance(20.0)
    assert lo == pytest.approx(0.45, abs=1e-9)
    assert hi == pytest.approx(0.55, abs=1e-9)

    # Round trip: the interval edges achieve exactly the requested ER.
    for er_db in (10.0, 25.0, 40.0):
        lo, hi = so.required_split_balance(er_db)
        assert so.mzi_extinction_db(lo) == pytest.approx(er_db, abs=1e-6)
        assert so.mzi_extinction_db(hi) == pytest.approx(er_db, abs=1e-6)

    with pytest.raises(ValueError):
        so.mzi_extinction_db(1.5)
    with pytest.raises(ValueError):
        so.required_split_balance(0.0)


def test_evaluate_v2_unmeasured_tier1_never_passes(tmp_path, monkeypatch):
    """Tier-1 targets without measurements must be 'unmeasured' and block passes."""
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_on_spec_fixture(tmp_path)

    report = so.evaluate(script, FAKE_STACK, V2_SPEC, cache_dir=tmp_path)
    by_metric = {v.metric: v for v in report.verdicts}
    assert by_metric["fsr_nm"].verdict == "pass"
    assert by_metric["extinction_ratio_db"].verdict == "unmeasured"
    assert by_metric["insertion_loss_db"].verdict == "unmeasured"
    assert set(report.unmeasured) == {"extinction_ratio_db", "insertion_loss_db"}
    assert report.passes is False
    assert "unmeasured" in report.reason
    json.dumps(report.to_dict())  # must be JSON-serializable


def test_evaluate_v2_with_measured_metrics_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_on_spec_fixture(tmp_path)

    report = so.evaluate(
        script,
        FAKE_STACK,
        V2_SPEC,
        measured_metrics={"extinction_ratio_db": 25.0, "insertion_loss_db": 0.6},
        cache_dir=tmp_path,
    )
    assert [v.verdict for v in report.verdicts] == ["pass", "pass", "pass"]
    assert report.unmeasured == ()
    assert report.passes is True
    assert report.reason == ""


def test_evaluate_v2_failing_measured_metric(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_on_spec_fixture(tmp_path)

    report = so.evaluate(
        script,
        FAKE_STACK,
        V2_SPEC,
        measured_metrics={"extinction_ratio_db": 15.0, "insertion_loss_db": 0.6},
        cache_dir=tmp_path,
    )
    by_metric = {v.metric: v for v in report.verdicts}
    assert by_metric["extinction_ratio_db"].verdict == "fail"
    assert by_metric["insertion_loss_db"].verdict == "pass"
    assert report.passes is False
    assert "extinction_ratio_db" in report.reason


def test_evaluate_v2_constraint_gates_even_when_measured(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_on_spec_fixture(tmp_path)

    spec = dict(V2_SPEC, constraints={"max_footprint_um": [10.0, 1.0]})
    report = so.evaluate(
        script,
        FAKE_STACK,
        spec,
        measured_metrics={"extinction_ratio_db": 25.0, "insertion_loss_db": 0.6},
        cache_dir=tmp_path,
    )
    assert report.footprint_ok is False
    assert report.passes is False


def test_evaluate_old_form_spec_regression(tmp_path, monkeypatch):
    """Old single-target specs evaluate identically through both entry points."""
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_on_spec_fixture(tmp_path)

    v2_report = so.evaluate(script, FAKE_STACK, OLD_SPEC, cache_dir=tmp_path)
    assert v2_report.unmeasured == ()
    assert v2_report.passes is True
    fsr = next(v for v in v2_report.verdicts if v.metric == "fsr_nm")

    legacy = so.evaluate_mzi_fsr(script, FAKE_STACK, OLD_SPEC, cache_dir=tmp_path)
    assert legacy.passes is True
    assert legacy.fsr_nm == pytest.approx(fsr.measured, rel=1e-12)
    assert legacy.target_nm == 8.0
    assert legacy.tolerance_rel == 0.02
    assert legacy.rel_error == pytest.approx(fsr.rel_error, rel=1e-12)


# ---------------------------------------------------------------------------
# Arbitrary multi-core cross-sections (adiabatic coupler / trident tier-0)
# ---------------------------------------------------------------------------


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_soi220_trident_cross_section_anchor(tmp_path):
    """A symmetric 3-core slice hybridizes: 3 guided modes, fundamental lifted."""
    stack = load_stack("soi220")
    trident = ((0.4, -0.55), (0.5, 0.0), (0.4, 0.55))
    result = so.solve_cross_section(stack, cores=trident, n_modes=3, cache_dir=tmp_path)
    assert len(result.n_effs) == 3
    assert all(a > b for a, b in zip(result.n_effs, result.n_effs[1:]))
    assert all(stack["clad_n"] <= n <= stack["core_n"] for n in result.n_effs)
    assert result.from_cache is False

    # Supermode hybridization with the wider center guide must push the
    # fundamental above the isolated 0.4 um single-guide n_eff.
    isolated = so.solve_waveguide(stack, width_um=0.4, cache_dir=tmp_path)
    assert result.n_effs[0] > isolated.n_eff


@pytest.mark.photonics_physics
@_needs_tidy3d
def test_two_core_cross_section_matches_solve_supermodes(tmp_path):
    """The generalized path must reproduce the dedicated 2-core solver."""
    stack = load_stack("soi220")
    width, gap = 0.5, 0.2
    pitch = width + gap
    dedicated = so.solve_supermodes(stack, width_um=width, gap_um=gap, cache_dir=tmp_path)
    pair = ((width, -pitch / 2), (width, pitch / 2))
    generalized = so.solve_cross_section(stack, cores=pair, cache_dir=tmp_path)
    assert generalized.n_effs[0] == pytest.approx(dedicated.n_even, abs=1e-6)
    assert generalized.n_effs[1] == pytest.approx(dedicated.n_odd, abs=1e-6)


def test_cross_section_cache_and_cores_key(tmp_path, monkeypatch):
    calls = []

    def fake_solver(core_n, clad_n, thickness_um, cores, n_modes, wavelength_um):
        calls.append(cores)
        return [2.5, 2.4, 2.3][:n_modes]

    monkeypatch.setattr(so, "_run_cross_section_solver", fake_solver)

    trident = ((0.4, -0.55), (0.5, 0.0), (0.4, 0.55))
    first = so.solve_cross_section(FAKE_STACK, cores=trident, n_modes=3, cache_dir=tmp_path)
    second = so.solve_cross_section(FAKE_STACK, cores=trident, n_modes=3, cache_dir=tmp_path)
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.n_effs == first.n_effs == (2.5, 2.4, 2.3)
    assert len(calls) == 1

    # Any change to the cores tuple is a different cache key and must re-solve.
    widened = ((0.45, -0.55), (0.5, 0.0), (0.4, 0.55))
    third = so.solve_cross_section(FAKE_STACK, cores=widened, n_modes=3, cache_dir=tmp_path)
    assert third.from_cache is False
    assert len(calls) == 2

    # A non-decreasing mode ladder must raise, never propagate.
    monkeypatch.setattr(so, "_run_cross_section_solver", lambda *a: [2.4, 2.4])
    with pytest.raises(ValueError, match="decreasing"):
        so.solve_cross_section(FAKE_STACK, cores=((0.5, -0.35), (0.5, 0.35)), cache_dir=tmp_path)


def test_cross_section_rejects_bad_cores():
    with pytest.raises(ValueError):
        so.solve_cross_section(FAKE_STACK, cores=())
    with pytest.raises(ValueError):
        so.solve_cross_section(FAKE_STACK, cores=((0.0, 0.0),))


def test_parse_cores_cli_format():
    assert so._parse_cores("0.4:-0.55,0.5:0,0.4:0.55") == (
        (0.4, -0.55),
        (0.5, 0.0),
        (0.4, 0.55),
    )
    with pytest.raises(ValueError):
        so._parse_cores("0.4")
    with pytest.raises(ValueError):
        so._parse_cores("")
