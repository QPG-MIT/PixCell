from __future__ import annotations

import pytest

from homi.conductor.source_policy import purity_violations, strict_purity_violations


def test_bezier_is_admitted():
    source = "import gdsfactory as gf\nc = gf.components.bezier()"
    assert strict_purity_violations(source) == []


def test_alias_and_dynamic_component_escape_hatches_are_rejected():
    alias = "import gdsfactory as x\nc = x.components.mzi()"
    dynamic = (
        "import gdsfactory as gf\n"
        "factory = getattr(gf.components, 'mzi')\n"
        "c = factory()\n"
    )
    assert any("non-catalog component" in item for item in strict_purity_violations(alias))
    assert any(
        "introspection" in item and "getattr" in item
        for item in strict_purity_violations(dynamic)
    )


def test_raw_polygon_image_read_and_dynamic_exec_are_rejected():
    assert "add_polygon" in strict_purity_violations("c.add_polygon([(0, 0), (1, 0)])")
    assert strict_purity_violations("from PIL import Image\nImage.open('target.png')")
    assert "dynamic execution: exec" in strict_purity_violations("exec('print(1)')")


def test_process_network_dynamic_imports_are_rejected():
    for module in (
        "builtins",
        "ctypes",
        "importlib",
        "multiprocessing",
        "os",
        "posix",
        "pty",
        "runpy",
        "signal",
        "socket",
        "subprocess",
        "sys",
    ):
        violations = strict_purity_violations(f"import {module}\n")
        assert f"forbidden import: {module}" in violations


def test_alternate_geometry_backends_are_rejected():
    for module in ("gdspy", "gdstk", "kfactory", "klayout", "phidl", "shapely"):
        violations = strict_purity_violations(f"import {module}\n")
        assert f"forbidden import: {module}" in violations
    violations = strict_purity_violations(
        "import gdsfactory as gf\np = gf.kdb.Polygon()\n"
    )
    assert any("alternate geometry backend" in item for item in violations)
    assert strict_purity_violations("from gdsfactory import kdb\n")
    assert strict_purity_violations("import gdsfactory.kcl as kcl\n")


def test_image_module_matching_does_not_reject_unrelated_prefixes():
    assert strict_purity_violations("import PILLOW\nimport cv20\nimport skimage_tools\n") == []


def test_dangerous_introspection_is_rejected():
    assert strict_purity_violations("f.__globals__['os'].system('x')") == [
        "forbidden introspection: __globals__"
    ]


@pytest.mark.parametrize(
    "source",
    [
        "import gdsfactory as gf\nvars(gf)['components'].mmi1x2()",
        "import gdsfactory as gf\nvars(gf)['kcl']",
        "import gdsfactory as gf\ng = globals()['gf']\ng.components.mmi1x2()",
        "import gdsfactory as gf\nlookup = getattr\nlookup(gf, 'kcl')",
    ],
)
def test_builtin_introspection_cannot_bypass_component_policy(source):
    assert any(
        "forbidden introspection call" in item
        for item in strict_purity_violations(source)
    )


def test_canonical_surface_matches_the_frozen_record_semantics():
    """The record-certifying rule must accept what recorded cells did:
    benign os/gdstk imports were within the campaign contract (strict-only
    bans), while raw-polygon, stencil, and gf.kdb backdoors reject on both
    surfaces. Pinned in full by tests/test_record_purity_sweep.py."""
    assert purity_violations("import os\nimport gdstk\n") == []
    assert "forbidden import: os" in strict_purity_violations("import os\n")
    assert purity_violations("import gdsfactory as gf\np = gf.kdb.Polygon()\n")
    assert purity_violations("c.add_polygon([(0, 0), (1, 0)])")
