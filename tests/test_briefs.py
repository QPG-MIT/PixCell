"""homi.briefs — the single source for worker prompts (P1)."""

import pytest

from homi import briefs


def test_list_briefs_has_core_set():
    names = briefs.list_briefs()
    assert {"extract", "phase_a_recreation", "phase_b_retarget"} <= set(names)


def test_render_substitutes_and_rejects_unresolved():
    text = briefs.render(
        "phase_a_recreation", INPUT_DIR="/x", WORKDIR="/y", GIT_RULE="No git."
    )
    assert "/x/device_bw.png" in text
    assert "{{" not in text
    with pytest.raises(ValueError):
        briefs.render("phase_a_recreation", INPUT_DIR="/x")  # missing vars


def test_unknown_brief_raises():
    with pytest.raises(KeyError):
        briefs.render("nope")


def test_extract_brief_is_harness_neutral():
    """The extract brief must serve tool-less workers (codex) too: venv-python
    fallback for every tool it names, and a digit-anchored completion marker."""
    text = briefs.render(
        "extract", INPUT="/p.pdf", OUTPUT_DIR="/out", HINT_LINE="", INPUT_NOTE=""
    )
    assert "homi.paper_processing" in text
    assert "get_gemini_client" in text
    assert '{"footprint_um": [L, W]}' in text
    assert "EXTRACT DONE: files=" in text


def test_phase_b_renders():
    text = briefs.render(
        "phase_b_retarget",
        STACKS="/d/stacks/{soi220,sin400,tfln400}.json",
        SPECS="/d/spec_<stack>.json",
        TIER1_CAP="3",
        WORKDIR="/w",
        GIT_RULE="No git.",
    )
    assert "MEASURE <stack>:" in text
    assert "PHASE_B DONE" in text
