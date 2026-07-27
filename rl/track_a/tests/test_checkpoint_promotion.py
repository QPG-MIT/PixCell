from __future__ import annotations

import hashlib

import pytest

from rl.track_a.checkpoint_metrics import (
    behavioral_probe_summary,
    program_sha256,
)
from rl.track_a.checkpoint_selection import select_sft_checkpoint
from rl.track_a.evaluation_contract import (
    BEHAVIORAL_PROBE_ATTEMPTS,
    BEHAVIORAL_PROBE_K,
    BEHAVIORAL_PROBE_TASKS,
    CURRICULUM_LEVELS,
    FULL_GEOMETRY_REPRESENTATIONS,
    FULL_GEOMETRY_TASKS,
    REPORT_SCHEMA_VERSION,
    CheckpointSelectionContract,
    report_provenance,
    task_ids_sha256,
)


GEOMETRY_IDS = [f"geometry-{index:04d}" for index in range(FULL_GEOMETRY_TASKS)]
BEHAVIOR_IDS = {
    level: [
        f"behavior-{level.lower()}-{index:02d}"
        for index in range(BEHAVIORAL_PROBE_TASKS)
    ]
    for level in CURRICULUM_LEVELS
}
CONTRACT = CheckpointSelectionContract(
    source_git_sha="a" * 40,
    depth_logical_release_sha256="b" * 64,
    model="Qwen/example",
    renderer="qwen_renderer",
    temperature=1.0,
    top_p=1.0,
    max_tokens=4096,
    task_selection_seed=7,
    geometry_task_ids_sha256=task_ids_sha256(GEOMETRY_IDS),
    behavioral_task_ids_sha256_by_level={
        level: task_ids_sha256(values)
        for level, values in BEHAVIOR_IDS.items()
    },
)


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


def _summary(*, tasks: int, attempts: int, iou: float, executable: float) -> dict:
    return {
        "tasks": tasks,
        "attempts": attempts,
        "pure_executable_rate": executable,
        "mean_iou_at_1": iou,
        "mean_best_at_k_iou": iou,
    }


def _geometry(sampler: str, iou: float, executable: float = 1.0) -> dict:
    level_tasks = {
        "L0": 186,
        "L1": 254,
        "L2": 196,
        "L3": 240,
        "L4": 216,
    }
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evaluation_role": "checkpoint-geometry",
        "sampler_path": sampler,
        "model": CONTRACT.model,
        "renderer": CONTRACT.renderer,
        "split": "depth/validation",
        "levels": "all",
        "k": 1,
        "temperature": CONTRACT.temperature,
        "top_p": CONTRACT.top_p,
        "max_tokens": CONTRACT.max_tokens,
        "representation_macro_mean_iou": iou,
        "summary": _summary(
            tasks=FULL_GEOMETRY_TASKS,
            attempts=FULL_GEOMETRY_TASKS,
            iou=iou,
            executable=executable,
        ),
        "statuses": {"ok": FULL_GEOMETRY_TASKS},
        "levels_summary": {
            level: _summary(
                tasks=tasks,
                attempts=tasks,
                iou=iou,
                executable=executable,
            )
            for level, tasks in level_tasks.items()
        },
        "mean_completion_tokens": 100.0,
        "behavioral_probe": None,
        "records": None,
    }
    report["provenance"] = report_provenance(
        contract=CONTRACT,
        sampler_path=sampler,
        role="checkpoint-geometry",
        levels=CURRICULUM_LEVELS,
        task_ids=GEOMETRY_IDS,
        representation_count=FULL_GEOMETRY_REPRESENTATIONS,
        requested_rows=None,
        k=1,
        attempt_count=FULL_GEOMETRY_TASKS,
        sandbox_image_ref="sha256:" + "c" * 64,
        sandbox_image_id="sha256:" + "c" * 64,
    )
    return report


def _behavior(sampler: str, probe: dict, *, level: str = "L2") -> dict:
    report = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "evaluation_role": "behavioral-collapse-probe",
        "sampler_path": sampler,
        "model": CONTRACT.model,
        "renderer": CONTRACT.renderer,
        "split": "depth/validation",
        "levels": level,
        "k": BEHAVIORAL_PROBE_K,
        "temperature": CONTRACT.temperature,
        "top_p": CONTRACT.top_p,
        "max_tokens": CONTRACT.max_tokens,
        "representation_macro_mean_iou": 0.5,
        "summary": _summary(
            tasks=BEHAVIORAL_PROBE_TASKS,
            attempts=BEHAVIORAL_PROBE_ATTEMPTS,
            iou=0.5,
            executable=0.75,
        ),
        "statuses": {"ok": BEHAVIORAL_PROBE_ATTEMPTS},
        "levels_summary": {
            level: _summary(
                tasks=BEHAVIORAL_PROBE_TASKS,
                attempts=BEHAVIORAL_PROBE_ATTEMPTS,
                iou=0.5,
                executable=0.75,
            )
        },
        "mean_completion_tokens": 100.0,
        "behavioral_probe": probe,
        "records": None,
    }
    report["provenance"] = report_provenance(
        contract=CONTRACT,
        sampler_path=sampler,
        role="behavioral-collapse-probe",
        levels=[level],
        task_ids=BEHAVIOR_IDS[level],
        representation_count=BEHAVIORAL_PROBE_TASKS,
        requested_rows=BEHAVIORAL_PROBE_TASKS,
        k=BEHAVIORAL_PROBE_K,
        attempt_count=BEHAVIORAL_PROBE_ATTEMPTS,
        sandbox_image_ref="sha256:" + "c" * 64,
        sandbox_image_id="sha256:" + "c" * 64,
    )
    return report


def _probe(
    *,
    collapsed: bool,
    nonconstant: float,
    program_mean: float,
    level: str = "L2",
) -> dict:
    groups = []
    nonconstant_groups = round(nonconstant * BEHAVIORAL_PROBE_TASKS)
    extra_programs = round(
        (program_mean - 1.0) * BEHAVIORAL_PROBE_TASKS
    )
    program_counts = [1] * BEHAVIORAL_PROBE_TASKS
    for index in range(BEHAVIORAL_PROBE_TASKS):
        added = min(BEHAVIORAL_PROBE_K - 1, extra_programs)
        program_counts[index] += added
        extra_programs -= added
    assert extra_programs == 0
    for index, opaque_id in enumerate(BEHAVIOR_IDS[level]):
        is_nonconstant = index < nonconstant_groups
        distinct_count = program_counts[index]
        groups.append(
            {
                "opaque_id": opaque_id,
                "distinct_program_count": distinct_count,
                "successful_render_attempts": BEHAVIORAL_PROBE_K,
                "distinct_successful_render_count": distinct_count,
                "reward_std": 0.1 if is_nonconstant else 0.0,
                "reward_range": 0.2 if is_nonconstant else 0.0,
                "nonconstant_reward": is_nonconstant,
            }
        )
    identical_program_every_group = all(
        group["distinct_program_count"] == 1 for group in groups
    )
    constant_render_and_reward_every_group = all(
        group["distinct_successful_render_count"] <= 1
        and not group["nonconstant_reward"]
        for group in groups
    )
    assert collapsed == (
        identical_program_every_group
        or constant_render_and_reward_every_group
    )
    return {
        "probe_kind": "small-balanced-unmastered-g4",
        "group_size": BEHAVIORAL_PROBE_K,
        "prompt_groups": BEHAVIORAL_PROBE_TASKS,
        "collapse_detected": collapsed,
        "nonconstant_reward_group_fraction": nonconstant,
        "mean_within_group_reward_std": nonconstant / 10,
        "mean_distinct_programs_per_prompt": program_mean,
        "mean_distinct_successful_renders_per_prompt": program_mean,
        "collapse_signals": {
            "identical_program_every_group": identical_program_every_group,
            "constant_render_and_reward_every_group": (
                constant_render_and_reward_every_group
            ),
        },
        "groups": groups,
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
    selected = select_sft_checkpoint(
        geometry,
        behavior,
        contract=CONTRACT,
    )
    assert selected["selected"]["sampler_path"] == "sampler-middle"
    assert selected["ranking"][-1]["sampler_path"] == "sampler-high"
    assert not selected["behavioral_metrics_are_ranking_features"]


def test_selection_requires_one_behavior_report_per_geometry_report():
    with pytest.raises(ValueError, match="pairing mismatch"):
        select_sft_checkpoint(
            [("a.json", _geometry("sampler-a", 0.5))],
            [],
            contract=CONTRACT,
        )


def test_selection_fails_closed_on_missing_collapse_verdict():
    incomplete = _probe(collapsed=False, nonconstant=0.5, program_mean=2.0)
    incomplete.pop("collapse_detected")
    with pytest.raises(ValueError, match="collapse_detected must be boolean"):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", _behavior("sampler-a", incomplete))],
            contract=CONTRACT,
        )


@pytest.mark.parametrize(
    ("field_path", "value", "message"),
    [
        (
            ("representation_macro_mean_iou",),
            float("nan"),
            "representation_macro_mean_iou must be finite",
        ),
        (
            ("representation_macro_mean_iou",),
            float("inf"),
            "representation_macro_mean_iou must be finite",
        ),
        (
            ("summary", "pure_executable_rate"),
            1.01,
            r"summary\.pure_executable_rate must be in \[0, 1\]",
        ),
    ],
)
def test_selection_rejects_nonfinite_and_out_of_range_ranking_metrics(
    field_path: tuple[str, ...],
    value: float,
    message: str,
):
    geometry = _geometry("sampler-a", 0.5)
    target = geometry
    for field in field_path[:-1]:
        target = target[field]
    target[field_path[-1]] = value
    with pytest.raises(ValueError, match=message):
        select_sft_checkpoint(
            [("a-k1.json", geometry)],
            [
                (
                    "a-g4.json",
                    _behavior(
                        "sampler-a",
                        _probe(
                            collapsed=False,
                            nonconstant=0.5,
                            program_mean=2.0,
                        ),
                    ),
                )
            ],
            contract=CONTRACT,
        )


def test_selection_rejects_one_row_geometry_report_even_when_claimed_metric_is_high():
    geometry = _geometry("sampler-a", 0.99)
    geometry["summary"]["tasks"] = 1
    geometry["summary"]["attempts"] = 1
    geometry["provenance"]["task_count"] = 1
    geometry["provenance"]["attempt_count"] = 1
    with pytest.raises(ValueError, match="provenance.task_count=1"):
        select_sft_checkpoint(
            [("one-row.json", geometry)],
            [
                (
                    "a-g4.json",
                    _behavior(
                        "sampler-a",
                        _probe(
                            collapsed=False,
                            nonconstant=0.5,
                            program_mean=2.0,
                        ),
                    ),
                )
            ],
            contract=CONTRACT,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_git_sha", "c" * 40),
        ("depth_logical_release_sha256", "d" * 64),
        ("model", "Qwen/wrong"),
        ("renderer", "wrong_renderer"),
    ],
)
def test_selection_rejects_report_provenance_mismatch(field: str, value: str):
    geometry = _geometry("sampler-a", 0.5)
    geometry["provenance"][field] = value
    with pytest.raises(ValueError, match=rf"provenance\.{field}"):
        select_sft_checkpoint(
            [("a-k1.json", geometry)],
            [
                (
                    "a-g4.json",
                    _behavior(
                        "sampler-a",
                        _probe(
                            collapsed=False,
                            nonconstant=0.5,
                            program_mean=2.0,
                        ),
                    ),
                )
            ],
            contract=CONTRACT,
        )


def test_selection_rejects_behavioral_probe_outside_exact_40_by_4_contract():
    behavior = _behavior(
        "sampler-a",
        _probe(
            collapsed=False,
            nonconstant=0.5,
            program_mean=2.0,
        ),
    )
    behavior["provenance"]["task_count"] = 39
    behavior["provenance"]["attempt_count"] = 156
    with pytest.raises(ValueError, match="provenance.task_count=39"):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", behavior)],
            contract=CONTRACT,
        )


def test_selection_rejects_sampling_mismatch_between_report_and_recipe():
    behavior = _behavior(
        "sampler-a",
        _probe(
            collapsed=False,
            nonconstant=0.5,
            program_mean=2.0,
        ),
    )
    behavior["provenance"]["sampling"]["temperature"] = 0.7
    behavior["temperature"] = 0.7
    with pytest.raises(
        ValueError,
        match=r"provenance\.sampling\.temperature",
    ):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", behavior)],
            contract=CONTRACT,
        )


def test_selection_rejects_behavioral_task_set_not_bound_to_declared_level():
    behavior = _behavior(
        "sampler-a",
        _probe(
            collapsed=False,
            nonconstant=0.5,
            program_mean=2.0,
        ),
    )
    behavior["provenance"]["task_ids_sha256"] = "e" * 64
    with pytest.raises(ValueError, match="provenance.task_ids_sha256"):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", behavior)],
            contract=CONTRACT,
        )


def test_selection_recomputes_behavioral_collapse_verdict_from_groups():
    probe = _probe(
        collapsed=True,
        nonconstant=0.0,
        program_mean=1.0,
    )
    probe["collapse_detected"] = False
    with pytest.raises(
        ValueError,
        match="behavioral_probe.collapse_detected=False; expected True",
    ):
        select_sft_checkpoint(
            [("a-k1.json", _geometry("sampler-a", 0.5))],
            [("a-g4.json", _behavior("sampler-a", probe))],
            contract=CONTRACT,
        )
