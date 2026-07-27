"""Catalog tier-0 metrics: ring_fsr_nm, coupling_ratio, group_delay_ps,
bragg_wavelength_nm.

Same discipline as test_spec_optimization: stub scripts honoring the
lengths.json contract (per-metric shapes), solver monkeypatched, verdicts
from evaluate() schema v2. One pass + one fail + one contract-error case per
metric, plus a sanity-guard case for the bounded shapes.
"""

import json
import textwrap
from pathlib import Path

import pytest

import homi.spec_optimization as so

pytestmark = pytest.mark.photonics_physics

FAKE_STACK = {
    "label": "fake 220 nm SOI",
    "core_n": 3.476,
    "clad_n": 1.444,
    "thickness_um": 0.22,
    "single_mode_width_um": 0.5,
}

# Minimal script honoring the contract: real GDS written, lengths.json shape
# injected per test via the SHAPE placeholder (computed values, tiny geometry).
SHAPE_SCRIPT = textwrap.dedent("""
    import json
    from pathlib import Path

    import gdsfactory as gf

    out_dir = Path(__file__).parent
    c = gf.Component()
    c << gf.components.rectangle(size=(5.0, 0.5), layer=(1, 0))
    c.write_gds(out_dir / "device.gds")
    (out_dir / "lengths.json").write_text(json.dumps(SHAPE))
    """)


def write_shape_fixture(tmp_path: Path, shape: dict) -> Path:
    script = tmp_path / "device.py"
    script.write_text(SHAPE_SCRIPT.replace("SHAPE", json.dumps(shape)))
    return script


def spec_for(metric: str, **target) -> dict:
    return {"wavelength_um": 1.55, "targets": [{"metric": metric, **target}]}


def verdict(report, metric):
    return next(v for v in report.verdicts if v.metric == metric)


# ---------------------------------------------------------------- ring_fsr_nm


def test_ring_fsr_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    # FSR = 1.55^2 / (4.0 * 60.0625) * 1000 = 10.0 nm
    script = write_shape_fixture(tmp_path, {"ring": {"round_trip_um": 60.0625}})
    report = so.evaluate(
        script, FAKE_STACK, spec_for("ring_fsr_nm", value=10.0, tolerance_rel=0.02),
        cache_dir=tmp_path,
    )
    v = verdict(report, "ring_fsr_nm")
    assert v.verdict == "pass" and v.source == "local"
    assert v.measured == pytest.approx(10.0, rel=1e-6)
    assert report.passes is True
    assert report.delta_length_um is None  # no MZI arms involved


def test_ring_fsr_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"ring": {"round_trip_um": 60.0625}})
    report = so.evaluate(
        script, FAKE_STACK, spec_for("ring_fsr_nm", value=20.0, tolerance_rel=0.02),
        cache_dir=tmp_path,
    )
    assert verdict(report, "ring_fsr_nm").verdict == "fail"
    assert report.passes is False


def test_ring_fsr_missing_shape_is_contract_error(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"path": {"total_um": 100.0}})
    with pytest.raises(RuntimeError, match="'ring' shape"):
        so.evaluate(
            script, FAKE_STACK, spec_for("ring_fsr_nm", value=10.0, tolerance_rel=0.02),
            cache_dir=tmp_path,
        )


def test_ring_fsr_guard_rejects_absurd_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"ring": {"round_trip_um": 0.2}})
    with pytest.raises(ValueError, match="round_trip_um"):
        so.evaluate(
            script, FAKE_STACK, spec_for("ring_fsr_nm", value=10.0, tolerance_rel=0.02),
            cache_dir=tmp_path,
        )


# -------------------------------------------------------------- coupling_ratio


def test_coupling_ratio_pass_at_half(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    # dn = 0.02 -> L_x = 1.55 / 0.04 = 38.75 um; L = L_x/2 -> sin^2(pi/4) = 0.5
    monkeypatch.setattr(so, "_run_supermode_solver", lambda *a: (2.46, 2.44))
    script = write_shape_fixture(
        tmp_path, {"coupler": {"length_um": 19.375, "gap_um": 0.2}}
    )
    report = so.evaluate(
        script, FAKE_STACK, spec_for("coupling_ratio", value=0.5), cache_dir=tmp_path
    )
    v = verdict(report, "coupling_ratio")
    assert v.verdict == "pass"
    assert v.measured == pytest.approx(0.5, abs=1e-9)
    # default absolute window was injected by _normalize_spec
    assert v.target["tolerance_abs"] == pytest.approx(0.05)


def test_coupling_ratio_fail_at_full_transfer(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    monkeypatch.setattr(so, "_run_supermode_solver", lambda *a: (2.46, 2.44))
    script = write_shape_fixture(
        tmp_path, {"coupler": {"length_um": 38.75, "gap_um": 0.2}}
    )
    report = so.evaluate(
        script, FAKE_STACK, spec_for("coupling_ratio", value=0.5), cache_dir=tmp_path
    )
    v = verdict(report, "coupling_ratio")
    assert v.measured == pytest.approx(1.0, abs=1e-9)
    assert v.verdict == "fail"


def test_coupling_ratio_missing_gap_is_contract_error(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"coupler": {"length_um": 19.375}})
    with pytest.raises(RuntimeError, match="missing 'gap_um'"):
        so.evaluate(
            script, FAKE_STACK, spec_for("coupling_ratio", value=0.5), cache_dir=tmp_path
        )


# -------------------------------------------------------------- group_delay_ps


def test_group_delay_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    # 4.0 * 100 / 299.792458 = 1.33426 ps
    script = write_shape_fixture(tmp_path, {"path": {"total_um": 100.0}})
    report = so.evaluate(
        script, FAKE_STACK,
        spec_for("group_delay_ps", value=1.33426, tolerance_rel=0.01),
        cache_dir=tmp_path,
    )
    v = verdict(report, "group_delay_ps")
    assert v.verdict == "pass"
    assert v.measured == pytest.approx(4.0 * 100.0 / 299.792458, rel=1e-9)


def test_group_delay_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"path": {"total_um": 100.0}})
    report = so.evaluate(
        script, FAKE_STACK, spec_for("group_delay_ps", value=2.5, tolerance_rel=0.01),
        cache_dir=tmp_path,
    )
    assert verdict(report, "group_delay_ps").verdict == "fail"


def test_group_delay_missing_shape_is_contract_error(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(tmp_path, {"ring": {"round_trip_um": 60.0}})
    with pytest.raises(RuntimeError, match="'path' shape"):
        so.evaluate(
            script, FAKE_STACK, spec_for("group_delay_ps", value=1.0, tolerance_rel=0.01),
            cache_dir=tmp_path,
        )


# --------------------------------------------------------- bragg_wavelength_nm


def test_bragg_wavelength_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    # lambda_B = 2 * 2.42 * 0.3178 * 1000 = 1538.152 nm (same n_eff both widths)
    script = write_shape_fixture(
        tmp_path, {"grating": {"period_um": 0.3178, "w1_um": 0.475, "w2_um": 0.525}}
    )
    report = so.evaluate(
        script, FAKE_STACK,
        spec_for("bragg_wavelength_nm", value=1538.152, tolerance_rel=0.005),
        cache_dir=tmp_path,
    )
    v = verdict(report, "bragg_wavelength_nm")
    assert v.verdict == "pass"
    assert v.measured == pytest.approx(1538.152, rel=1e-9)


def test_bragg_wavelength_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(
        tmp_path, {"grating": {"period_um": 0.3178, "w1_um": 0.475, "w2_um": 0.525}}
    )
    report = so.evaluate(
        script, FAKE_STACK,
        spec_for("bragg_wavelength_nm", value=1600.0, tolerance_rel=0.005),
        cache_dir=tmp_path,
    )
    assert verdict(report, "bragg_wavelength_nm").verdict == "fail"


def test_bragg_missing_width_is_contract_error(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(
        tmp_path, {"grating": {"period_um": 0.3178, "w1_um": 0.475}}
    )
    with pytest.raises(RuntimeError, match="missing 'w2_um'"):
        so.evaluate(
            script, FAKE_STACK,
            spec_for("bragg_wavelength_nm", value=1538.0, tolerance_rel=0.005),
            cache_dir=tmp_path,
        )


def test_bragg_guard_rejects_out_of_band(tmp_path, monkeypatch):
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(
        tmp_path, {"grating": {"period_um": 1.5, "w1_um": 0.475, "w2_um": 0.525}}
    )
    with pytest.raises(ValueError, match="bragg_wavelength_nm"):
        so.evaluate(
            script, FAKE_STACK,
            spec_for("bragg_wavelength_nm", value=1550.0, tolerance_rel=0.005),
            cache_dir=tmp_path,
        )


# ------------------------------------------------- legacy coexistence guard


def test_arms_shape_still_validated_when_present(tmp_path, monkeypatch):
    """A payload carrying a malformed arms shape fails even for ring specs —
    the legacy contract is never silently skipped when the shape exists."""
    monkeypatch.setattr(so, "_run_mode_solver", lambda *a: (2.42, 4.0))
    script = write_shape_fixture(
        tmp_path,
        {"arms": {"a": 10.0, "b": 20.0, "c": 30.0}, "ring": {"round_trip_um": 60.0}},
    )
    with pytest.raises(RuntimeError, match="exactly 2 arms"):
        so.evaluate(
            script, FAKE_STACK, spec_for("ring_fsr_nm", value=10.0, tolerance_rel=0.05),
            cache_dir=tmp_path,
        )
