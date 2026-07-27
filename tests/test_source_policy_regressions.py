"""Differential pins for the canonical source policy.

The policy was extracted from the gate into homi.conductor.source_policy and
revised (AST analysis, alias closure, dynamic-call bans, catalog bezier). An
adversarial review of that extraction established the semantics pinned here —
most importantly that the textual raw-polygon belt keeps the policy at least
as strict as the pre-extraction textual gate, closing the string-literal
escape the AST walk cannot see.
"""

from homi.conductor.source_policy import purity_violations


def _rejects(source: str) -> bool:
    return bool(purity_violations(source))


def test_getattr_string_escape_is_closed():
    assert _rejects('getattr(c, "add_polygon")([(0, 0), (1, 0), (1, 1)])')


def test_textual_mention_keeps_old_gate_parity():
    assert _rejects("# add_polygon appears only in this comment")


def test_direct_raw_polygon_still_rejected():
    assert _rejects("c.add_polygon([(0, 0), (1, 0), (1, 1)])")


def test_bezier_is_catalog():
    src = "import gdsfactory as gf\nc = gf.components.bezier(control_points=pts)"
    assert not _rejects(src)


def test_stencils_rejected_through_alias():
    assert _rejects("import gdsfactory as g\nc = g.components.mzi()")


def test_dynamic_execution_rejected():
    assert _rejects('eval("1 + 1")')


def test_dynamic_component_resolution_rejected():
    assert _rejects('import gdsfactory as gf\ngetattr(gf.components, "mzi")()')


def test_image_prefix_is_segment_aware():
    assert _rejects("import PIL")
    assert _rejects("from PIL import Image")
    assert not _rejects("import PILLOW")


def test_clean_catalog_program_passes():
    src = (
        "import gdsfactory as gf\n"
        "W = 1.2\n"
        "c = gf.Component()\n"
        "c << gf.components.straight(length=10, width=W)\n"
        "c << gf.components.bend_euler(radius=5)\n"
    )
    assert not _rejects(src)
