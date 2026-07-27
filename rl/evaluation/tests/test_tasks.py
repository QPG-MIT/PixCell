from __future__ import annotations

from collections import Counter
from pathlib import Path

from rl.evaluation.tasks import (
    BENCHMARK_TASK_SET,
    OPERATING_POINT_TASK_SET,
    build_task_manifest,
    load_task_manifest,
    load_task_set,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/task_manifest.json"
)


def test_frozen_task_manifest_rebuilds_exactly():
    frozen = load_task_manifest(MANIFEST_PATH, repo_root=REPO_ROOT)
    assert frozen == build_task_manifest(REPO_ROOT)
    dev = frozen["task_sets"][OPERATING_POINT_TASK_SET]
    benchmark = frozen["task_sets"][BENCHMARK_TASK_SET]
    assert len(dev) == 40
    assert Counter(value["level"] for value in dev) == {
        "L0": 8,
        "L1": 8,
        "L2": 8,
        "L3": 8,
        "L4": 8,
    }
    assert len({value["representation_id"] for value in dev}) == 40
    assert [value["task_id"] for value in benchmark] == [
        f"F{index}" for index in range(1, 9)
    ]


def test_evaluation_loader_has_no_supervised_label():
    manifest = load_task_manifest(MANIFEST_PATH, repo_root=REPO_ROOT)
    for task_set, expected in (
        (OPERATING_POINT_TASK_SET, 40),
        (BENCHMARK_TASK_SET, 8),
    ):
        tasks = load_task_set(
            repo_root=REPO_ROOT,
            manifest=manifest,
            task_set=task_set,
        )
        assert len(tasks) == expected
        assert set(tasks[0].__dataclass_fields__) == {
            "task_id",
            "level",
            "representation_id",
            "observation",
            "reference",
        }
        assert not hasattr(tasks[0], "label")


def test_benchmark_model_and_reference_bytes_are_same_but_separate():
    manifest = load_task_manifest(MANIFEST_PATH, repo_root=REPO_ROOT)
    tasks = load_task_set(
        repo_root=REPO_ROOT,
        manifest=manifest,
        task_set=BENCHMARK_TASK_SET,
    )
    for task in tasks:
        assert task.observation.image_bytes == task.reference.target_image_bytes
        assert task.observation.image_sha256 == task.reference.target_image_sha256
        assert task.observation is not task.reference
