"""tidy3d is an optional extra ([simulate]); when it's absent, every surface
that needs it must say so with the exact install remedy — never a raw
ModuleNotFoundError from deep inside a solver.
"""

import sys

import pytest

REMEDY = r"pixcell\[simulate\]"


def test_flex_guard_names_the_simulate_extra(monkeypatch):
    import flex.core.materials as m

    monkeypatch.setattr(m, "TIDY3D_AVAILABLE", False)
    with pytest.raises(RuntimeError, match=REMEDY):
        m.get_material_medium(3.47)


def test_spec_optimization_solver_names_the_simulate_extra(monkeypatch):
    from homi import spec_optimization as so

    # None in sys.modules makes `import tidy3d` raise ImportError.
    monkeypatch.setitem(sys.modules, "tidy3d", None)
    with pytest.raises(RuntimeError, match=REMEDY):
        so._run_mode_solver(core_n=3.476, clad_n=1.444, thickness_um=0.22,
                            width_um=0.5, wavelength_um=1.55)


def test_sweep_evaluation_names_the_simulate_extra(monkeypatch, tmp_path):
    from homi import sweep_evaluation as se

    monkeypatch.setitem(sys.modules, "tidy3d", None)
    with pytest.raises(RuntimeError, match=REMEDY):
        se._make_simulation(tmp_path / "missing.gds", {}, api_key="")
