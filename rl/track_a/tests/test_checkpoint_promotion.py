from __future__ import annotations

import hashlib

import pytest

from rl.track_a.checkpoint_metrics import (
    behavioral_probe_summary,
    program_sha256,
)
from rl.track_a.checkpoint_selection import select_sft_checkpoint


def _attempt(
    opaque_id: str,
    program: str,
    render: str | None,
    reward: float,
) -> dict:
    return {
        "opaque_id": opaque_id,
        "program_sha256": program,
        "render_sha256": render,
        "pure_executable": render is not None,
        "reward": reward,
    }


def _geometry(sampler: str, iou: float, executable: float = 1.0) -> dict:
    return {
        "evaluation_role": "checkpoint-geometry",
        "sampler_path": sampler,
        "k": 1,
        "representation_macro_mean_iou": iou,
        "summary": {"pure_executable_rate": executable},
    }


def _behavior(sampler: str, probe: dict) -> dict:
    return {
        "evaluation_role": "behavioral-collapse-probe",
        "sampler_path": sampler,
        "k": 4,
        "behavioral_probe": probe,
    }


def _probe(*, collapsed: bool, nonconstant: float, program_mean: float) -> dict:
    return {
        "collapse_detected": collapsed,
        "nonconstant_reward_group_fraction": nonconstant,
        "mean_within_group_reward_std": nonconstant / 10,
        "mean_distinct_programs_per_prompt": program_mean,
        "mean_distinct_successful_renders_per_prompt": program_mean,
        "collapse_signals": {},
    }


def test_program_hash_ignores_fences_and_trailing_whitespace():
    plain = "import gdsfactory as gf\nprint('x')"
    fenced = "```python\nimport gdsfactory as gf  \nprint('x')\n```\n"
    assert program_sha256(plain) == program_sha256(fenced)
    assert program_sha256(plain) == hashlib.sha256(plain.encode()).hexdigest()


def test_behavioral_probe_reports_per_prompt_diversity_and_reward_variance():
    records = [
        _attempt("a", "p1", "r1", 0.1),
        _attempt("a", "p2", "r2", 0.2),
        _attempt("a", "p2", "r2", 0.2),
        _attempt("a", "p2", None, 0.0),
        _attempt("b", "p3", "r3", 0.5),
        _attempt("b", "p3", "r3", 0.5),
        _attempt("b", "p3", "r3", 0.5),
        _attempt("b", "p3", "r3", 0.5),
    ]
    summary = behavioral_probe_summary(records)
    assert summary["prompt_groups"] == 2
    assert summary["nonconstant_reward_group_fraction"] == 0.5
    assert summary["mean_distinct_programs_per_prompt"] == 1.5
    assert summary["mean_distinct_successful_renders_per_prompt"] == 1.5
    assert summary["mean_within_group_reward_std"] > 0
    assert not summary["collapse_detected"]
    assert summary["groups"][0]["distinct_program_sha256"] == ["p1", "p2"]
    assert summary["groups"][0]["distinct_successful_render_sha256"] == [
        "r1",
        "r2",
    ]


def test_behavioral_probe_detects_every_prompt_collapsing():
    records = [
        _attempt(prompt, f"p-{prompt}", f"r-{prompt}", 0.6)
        for prompt in ("a", "b")
        for _ in range(4)
    ]
    summary = behavioral_probe_summary(records)
    assert summary["collapse_detected"]
    assert summary["collapse_signals"]["identical_program_every_group"]
    assert summary["nonconstant_reward_group_fraction"] == 0


def test_selection_vetoes_collapsed_model_but_never_ranks_on_diversity():
    geometry = [
        ("high-k1.json", _geometry("sampler-high", 0.9)),
        ("middle-k1.json", _geometry("sampler-middle", 0.7)),
        ("low-k1.json", _geometry("sampler-low", 0.6)),
    ]
    behavior = [
        (
            "high-g4.json",
            _behavior(
                "sampler-high",
                _probe(
                    collapsed=True,
                    nonconstant=0.0,
                    program_mean=1.0,
                ),
            ),
        ),
        (
            "middle-g4.json",
            _behavior(
                "sampler-middle",
                _probe(
                    collapsed=False,
                    nonconstant=0.1,
                    program_mean=1.2,
                ),
            ),
        ),
        (
            "low-g4.json",
            _behavior(
                "sampler-low",
                _probe(
                    collapsed=False,
                    nonconstant=1.0,
                    program_mean=4.0,
                ),
            ),
        ),
    ]
    selected = select_sft_checkpoint(geometry, behavior)
    assert selected["selected"]["sampler_path"] == "sampler-middle"
    assert selected["ranking"][-1]["sampler_path"] == "sampler-high"
    assert not selected["behavioral_metrics_are_ranking_features"]


def test_selection_requires_one_behavior_report_per_geometry_report():
    with pytest.raises(ValueError, match="pairing mismatch"):
        select_sft_checkpoint(
            [("a.json", _geometry("sampler-a", 0.5))],
            [],
        )


def test_selection_fails_closed_on_missing_collapse_verdict():
    incomplete = _probe(collapsed=False, nonconstant=0.5, program_mean=2.0)
    incomplete.pop("collapse_detected")
    with pytest.raises(ValueError, match="boolean collapse_detected"):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", _behavior("sampler-a", incomplete))],
        )
