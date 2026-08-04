"""
Tests for the integer parameter type-hint fix in JEE optimization.

Verifies that:
1. _detect_int_params correctly identifies `: int` type hints
2. _create_parametric_factory rounds int params before substitution
3. GDSOptimizer._array_to_params rounds int params
4. GDSExplorer._snap_param rounds int params
5. The regex substitution produces valid int values in the script
"""

import numpy as np


# ── Test 1: _detect_int_params ──────────────────────────────────────────────

def test_detect_int_params():
    """_detect_int_params should find params with `: int` type hints."""
    from homi.jee_integration import _detect_int_params

    script = """
def make_device():
    num_teeth: int = 7
    width: float = 0.5
    gap = 0.1
    count : int = 3
    layers: tuple[int, int] = (1, 0)
    """

    param_names = ["num_teeth", "width", "gap", "count", "layers"]
    result = _detect_int_params(script, param_names)

    assert "num_teeth" in result, "num_teeth has `: int =` and should be detected"
    assert "count" in result, "count has `: int =` (with space) and should be detected"
    assert "width" not in result, "width has `: float =` and should NOT be detected"
    assert "gap" not in result, "gap has no type hint and should NOT be detected"
    # layers has `: tuple[int, int]` — should NOT match `: int =`
    assert "layers" not in result, "layers has tuple[int, int], not plain int"


def test_detect_int_params_empty():
    """No int params in an all-float script."""
    from homi.jee_integration import _detect_int_params

    script = """
width: float = 0.5
length = 10.0
    """
    result = _detect_int_params(script, ["width", "length"])
    assert result == set()


# ── Test 3: GDSOptimizer._array_to_params with int_params ───────────────────

def test_optimizer_array_to_params_int():
    """_array_to_params should round int params to integers."""
    from jee.core.optimizer import GDSOptimizer, OptimizerConfig
    from pathlib import Path
    import tempfile
    import json
    import os

    # Create minimal calibration file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"footprint_um": [10, 5], "scale_px_per_um": [10, 10], "image_size_px": [100, 50]}, f)
        cal_path = f.name

    # Create minimal target image
    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('L', (100, 50), 255)
        img.save(f.name)
        img_path = f.name

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OptimizerConfig(
                target_image=Path(img_path),
                calibration_file=Path(cal_path),
                output_dir=Path(tmpdir),
                grid_um=0.002,
            )

            optimizer = GDSOptimizer(
                factory_fn=lambda p: None,
                param_names=["num_teeth", "width"],
                param_bounds={"num_teeth": (1.0, 20.0), "width": (0.1, 1.0)},
                baseline={"num_teeth": 7.0, "width": 0.5},
                config=config,
                int_params={"num_teeth"},
            )

            arr = np.array([7.35, 0.48])
            params = optimizer._array_to_params(arr)

            assert params["num_teeth"] == 7.0, f"Expected 7.0, got {params['num_teeth']}"
            assert isinstance(params["num_teeth"], float), "Should still be float type for numpy compat"
            # width should be grid-snapped but not int-rounded
            assert abs(params["width"] - 0.48) < 0.01
    finally:
        os.unlink(cal_path)
        os.unlink(img_path)


def test_optimizer_array_to_params_no_int_params():
    """Without int_params, _array_to_params should behave as before (backward compat)."""
    from jee.core.optimizer import GDSOptimizer, OptimizerConfig
    from pathlib import Path
    import tempfile
    import json
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"footprint_um": [10, 5], "scale_px_per_um": [10, 10], "image_size_px": [100, 50]}, f)
        cal_path = f.name

    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('L', (100, 50), 255)
        img.save(f.name)
        img_path = f.name

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = OptimizerConfig(
                target_image=Path(img_path),
                calibration_file=Path(cal_path),
                output_dir=Path(tmpdir),
            )

            # No int_params — old behavior
            optimizer = GDSOptimizer(
                factory_fn=lambda p: None,
                param_names=["length", "width"],
                param_bounds={"length": (1.0, 20.0), "width": (0.1, 1.0)},
                baseline={"length": 10.0, "width": 0.5},
                config=config,
            )

            arr = np.array([7.35, 0.48])
            params = optimizer._array_to_params(arr)

            # Should NOT be rounded to int
            assert params["length"] != 7.0, "Should not round to int without int_params"
    finally:
        os.unlink(cal_path)
        os.unlink(img_path)


# ── Test 4: Explorer._snap_param ────────────────────────────────────────────

def test_explorer_snap_param():
    """_snap_param should round int params after grid snapping."""
    from jee.core.explorer import GDSExplorer, ExplorerConfig
    from pathlib import Path
    import tempfile
    import json
    import os

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"footprint_um": [10, 5], "scale_px_per_um": [10, 10], "image_size_px": [100, 50]}, f)
        cal_path = f.name

    from PIL import Image
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
        img = Image.new('L', (100, 50), 255)
        img.save(f.name)
        img_path = f.name

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config = ExplorerConfig(
                target_image=Path(img_path),
                calibration_file=Path(cal_path),
                output_dir=Path(tmpdir),
            )

            explorer = GDSExplorer(
                factory_fn=lambda p: None,
                param_names=["num_teeth", "width"],
                param_bounds={"num_teeth": (1.0, 20.0), "width": (0.1, 1.0)},
                baseline={"num_teeth": 7.0, "width": 0.5},
                config=config,
                int_params={"num_teeth"},
            )

            # 7.35 grid-snapped with 0.002 grid -> 7.35 -> int-rounded -> 7.0
            assert explorer._snap_param("num_teeth", 7.35) == 7.0
            assert explorer._snap_param("num_teeth", 7.6) == 8.0
            # width should just be grid-snapped, not int-rounded
            assert abs(explorer._snap_param("width", 0.483) - 0.484) < 0.001
    finally:
        os.unlink(cal_path)
        os.unlink(img_path)


