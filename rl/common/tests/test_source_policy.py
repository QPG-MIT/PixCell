from __future__ import annotations

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
    assert "dynamic component resolution" in purity_violations(dynamic)


def test_raw_polygon_image_read_and_dynamic_exec_are_rejected():
    assert "add_polygon" in purity_violations("c.add_polygon([(0, 0), (1, 0)])")
    assert purity_violations("from PIL import Image\nImage.open('target.png')")
    assert "dynamic execution: exec" in purity_violations("exec('print(1)')")
