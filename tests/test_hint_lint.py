"""conductor.hint_lint — workers derive; conductors never teach (P2)."""

from homi import briefs
from homi.conductor import hint_lint


def test_lint_flags_device_class_vocabulary():
    assert hint_lint.lint("set the ring radius to 5") == ["ring"]
    assert hint_lint.lint("This MZI has an 8 nm FSR") == ["mzi", "fsr"]


def test_lint_passes_neutral_geometry_text():
    assert hint_lint.lint("straight and bend only; taper lengths as tunables") == []


def test_lint_matches_whole_words_only():
    # splitter_meta.json is a fixture filename, not a leaked classification
    assert hint_lint.lint("write splitter_meta.json with port positions") == []


def test_packaged_phase_briefs_are_hint_clean():
    """The blind-protocol briefs must never leak device class or mechanism.

    (The extract brief is exempt: extraction is not blind — it carries a
    user-supplied device hint by design.)
    """
    phase_a = briefs.render(
        "phase_a_recreation", INPUT_DIR="/in", WORKDIR="/w", GIT_RULE="No git."
    )
    phase_b = briefs.render(
        "phase_b_retarget",
        STACKS="/in/stacks/*.json",
        SPECS="/in/spec_<stack>.json",
        TIER1_CAP="3",
        WORKDIR="/w",
        GIT_RULE="No git.",
    )
    assert hint_lint.lint(phase_a) == []
    assert hint_lint.lint(phase_b) == []
