from __future__ import annotations

import pytest

from homi.conductor.source_policy import purity_violations


def test_bezier_is_admitted():
    source = "import gdsfactory as gf\nc = gf.components.bezier()"
    assert purity_violations(source) == []


def test_alias_and_dynamic_component_escape_hatches_are_rejected():
    alias = "import gdsfactory as x\nc = x.components.mzi()"
    dynamic = (
        "import gdsfactory as gf\n"
        "factory = getattr(gf.components, 'mzi')\n"
        "c = factory()\n"
    )
    assert any("non-catalog component" in item for item in purity_violations(alias))
    assert any(
        "introspection" in item and "getattr" in item
        for item in purity_violations(dynamic)
    )


def test_raw_polygon_image_read_and_dynamic_exec_are_rejected():
    assert "add_polygon" in purity_violations("c.add_polygon([(0, 0), (1, 0)])")
    assert purity_violations("from PIL import Image\nImage.open('target.png')")
    assert "dynamic execution: exec" in purity_violations("exec('print(1)')")


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
        violations = purity_violations(f"import {module}\n")
        assert f"forbidden import: {module}" in violations


def test_alternate_geometry_backends_are_rejected():
    for module in ("gdspy", "gdstk", "kfactory", "klayout", "phidl", "shapely"):
        violations = purity_violations(f"import {module}\n")
        assert f"forbidden import: {module}" in violations
    violations = purity_violations(
        "import gdsfactory as gf\np = gf.kdb.Polygon()\n"
    )
    assert any("alternate geometry backend" in item for item in violations)
    assert purity_violations("from gdsfactory import kdb\n")
    assert purity_violations("import gdsfactory.kcl as kcl\n")


def test_image_module_matching_does_not_reject_unrelated_prefixes():
    assert purity_violations("import PILLOW\nimport cv20\nimport skimage_tools\n") == []


def test_dangerous_introspection_is_rejected():
    assert purity_violations("f.__globals__['os'].system('x')") == [
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
        for item in purity_violations(source)
    )
