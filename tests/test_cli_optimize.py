"""Regression tests for materializing and promoting JEE optimization results."""

from argparse import Namespace

import pytest

import homi.cli as cli
from homi import jee_integration


def test_apply_parameter_values_preserves_contract_and_rounds_integers():
    source = """\
width_um: float = 1.5  # physical width
periods : int = 3  # discrete geometry

def build():
    width_um = 99.0  # a local with the same name must not move
    return width_um
"""

    rewritten = jee_integration.apply_parameter_values(
        source,
        {"width_um": 2.75, "periods": 4.6},
        int_params={"periods"},
    )

    assert "width_um: float = 2.75  # physical width" in rewritten
    assert "periods : int = 5  # discrete geometry" in rewritten
    assert "    width_um = 99.0  # a local with the same name must not move" in rewritten


def test_apply_parameter_values_fails_closed_for_missing_assignment():
    with pytest.raises(
        ValueError,
        match="optimized parameters are not top-level numeric assignments: missing_um",
    ):
        jee_integration.apply_parameter_values(
            "width_um = 1.5\n",
            {"missing_um": 2.0},
        )


def _optimize_args(script_path, *, promote):
    return Namespace(
        script_path=script_path,
        target=None,
        method="nelder-mead",
        max_iterations=8,
        explore=False,
        promote=promote,
    )


def _stub_optimize_inputs(tmp_path, monkeypatch):
    script = tmp_path / "best.py"
    script.write_text("width_um = 1.5\n")
    target = tmp_path / "device_bw.png"
    target.write_bytes(b"png")
    calibration = tmp_path / "calibration.json"
    calibration.write_text("{}")

    monkeypatch.setattr(
        cli,
        "_discover_optimize_inputs",
        lambda *_args, **_kwargs: (target, calibration, None),
    )
    monkeypatch.setattr(
        jee_integration,
        "extract_factory_and_params",
        lambda _path: (
            object(),
            ["width_um"],
            {"width_um": (1.0, 2.0)},
            {"width_um": 1.5},
            set(),
        ),
    )
    monkeypatch.setattr(jee_integration, "get_jee_default_config", lambda: {})
    return script


def test_cmd_optimize_returns_failure_on_optimizer_error(tmp_path, monkeypatch):
    script = _stub_optimize_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        jee_integration,
        "run_jee_optimization",
        lambda *_args, **_kwargs: {"error": "optimizer diverged"},
    )
    promotion_calls = []
    monkeypatch.setattr(
        cli,
        "_promote_polished_candidate",
        lambda **kwargs: promotion_calls.append(kwargs),
    )

    assert cli.cmd_optimize(_optimize_args(script, promote=True)) == 1
    assert promotion_calls == []


@pytest.mark.parametrize("promote", [False, True])
def test_cmd_optimize_promotes_only_when_requested(tmp_path, monkeypatch, promote):
    script = _stub_optimize_inputs(tmp_path, monkeypatch)
    monkeypatch.setattr(
        jee_integration,
        "run_jee_optimization",
        lambda *_args, **_kwargs: {
            "improvement_pct": 12.5,
            "best_sse": 0.25,
            "best_params": {"width_um": 1.625},
        },
    )
    promotion_calls = []

    def fake_promote(**kwargs):
        promotion_calls.append(kwargs)
        return True, "promoted test revision"

    monkeypatch.setattr(cli, "_promote_polished_candidate", fake_promote)

    assert cli.cmd_optimize(_optimize_args(script, promote=promote)) == 0
    assert len(promotion_calls) == int(promote)
    if promote:
        assert promotion_calls[0]["result"]["method"] == "nelder-mead"
        assert promotion_calls[0]["int_params"] == set()
