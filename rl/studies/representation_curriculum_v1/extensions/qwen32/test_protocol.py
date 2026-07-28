from __future__ import annotations

from pathlib import Path

import pytest

from rl.evaluation.protocol import (
    _require_protocol_at_head,
    deterministic_seed,
    jobs_for_wave,
    load_archived_protocol,
    load_protocol,
)
from rl.evaluation.tasks import load_task_manifest


REPO_ROOT = Path(__file__).resolve().parents[5]
BASE_PROTOCOL = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/protocol.json"
)
EXTENSION_PROTOCOL = Path(__file__).with_name("protocol.json")
TASK_MANIFEST = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/task_manifest.json"
)


def _benchmark_task_ids() -> list[str]:
    manifest = load_task_manifest(TASK_MANIFEST, repo_root=REPO_ROOT)
    return [value["task_id"] for value in manifest["task_sets"]["f1_f8"]]


def test_extension_is_one_fixed_quality_first_arm():
    protocol = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    assert protocol["study_id"] == "representation-curriculum-v1-qwen32"
    assert protocol["base_study"]["protocol_sha256"] == load_archived_protocol(
        REPO_ROOT,
        protocol_file=BASE_PROTOCOL,
    )["logical_sha256"]
    assert protocol["hypotheses"]["RC-H03"]["arm_ids"] == ["qwen-on-32768"]
    assert protocol["arms"]["qwen-on-32768"] == {
        "context_tokens": 65536,
        "max_image_long_edge": 1440,
        "max_output_tokens": 32768,
        "model": "Qwen/Qwen3.6-35B-A3B",
        "provider": "tinker",
        "renderer": "qwen3_5",
        "thinking": True,
        "thinking_effort": None,
    }


def test_extension_smoke_and_complete_are_exact_f1_f8_g4_jobs():
    protocol = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    task_ids = _benchmark_task_ids()
    smoke = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H03",
        wave_name="smoke",
        task_ids=task_ids,
    )
    complete = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H03",
        wave_name="complete",
        task_ids=task_ids,
    )
    assert len(smoke) == 8
    assert len(complete) == 32
    assert {job.arm_id for job in complete} == {"qwen-on-32768"}
    assert {job.task_id for job in smoke} == set(task_ids)
    assert {job.attempt_index for job in complete} == {1, 2, 3, 4}


def test_extension_keeps_base_seed_pairing():
    base = load_archived_protocol(REPO_ROOT, protocol_file=BASE_PROTOCOL)
    extension = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    for task_id in _benchmark_task_ids():
        for attempt_index in range(1, 5):
            assert deterministic_seed(
                extension,
                task_id=task_id,
                attempt_index=attempt_index,
            ) == deterministic_seed(
                base,
                task_id=task_id,
                attempt_index=attempt_index,
            )


def test_protocol_override_must_be_source_controlled(tmp_path: Path):
    outside = tmp_path / "protocol.json"
    outside.write_text(EXTENSION_PROTOCOL.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="inside the source repository"):
        load_protocol(REPO_ROOT, protocol_file=outside)


def test_paid_protocol_must_be_tracked_by_head():
    _require_protocol_at_head(REPO_ROOT, BASE_PROTOCOL)
    with pytest.raises(ValueError, match="tracked by the paid-launch commit"):
        _require_protocol_at_head(REPO_ROOT, REPO_ROOT / ".git")
