from __future__ import annotations

from pathlib import Path

import pytest

from rl.evaluation.protocol import (
    deterministic_seed,
    jobs_for_wave,
    load_protocol,
    resolved_arm_ids,
)
from rl.evaluation.tasks import load_task_manifest


REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_MANIFEST = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/task_manifest.json"
)


def _selection(selected: str, *, complete: bool = True) -> dict:
    protocol = load_protocol(REPO_ROOT)
    return {
        "schema_version": "pixcell-operating-point-selection-v1",
        "study_id": protocol["study_id"],
        "protocol_sha256": protocol["logical_sha256"],
        "source_hypothesis": "RC-H00",
        "selected_arm": selected,
        "rescue_required": False,
        "rescue_run": False,
        "complete": complete,
    }


def _task_ids(task_set: str) -> list[str]:
    manifest = load_task_manifest(TASK_MANIFEST, repo_root=REPO_ROOT)
    return [value["task_id"] for value in manifest["task_sets"][task_set]]


def test_protocol_freezes_baseline_and_forbids_unfrozen_training():
    protocol = load_protocol(REPO_ROOT)
    assert protocol["study_id"] == "representation-curriculum-v1"
    assert protocol["hypotheses"]["RC-H00"]["status"] == "frozen"
    assert protocol["hypotheses"]["RC-H01"]["status"] == "frozen"
    assert protocol["hypotheses"]["RC-H02"]["status"] == "frozen"
    assert all(
        value["status"] == "launch_forbidden_until_protocol_frozen"
        for value in protocol["future_hypothesis_registry"].values()
    )


def test_qwen_factorial_is_matched_and_seed_paired():
    protocol = load_protocol(REPO_ROOT)
    arms = [
        protocol["arms"][value]
        for value in protocol["hypotheses"]["RC-H00"]["arm_ids"]
    ]
    assert {(value["thinking"], value["max_output_tokens"]) for value in arms} == {
        (False, 4096),
        (False, 16384),
        (True, 4096),
        (True, 16384),
    }
    first = deterministic_seed(protocol, task_id="same", attempt_index=1)
    assert first == deterministic_seed(
        protocol,
        task_id="same",
        attempt_index=1,
    )
    assert first != deterministic_seed(
        protocol,
        task_id="same",
        attempt_index=2,
    )


def test_wave_job_counts_are_exact():
    protocol = load_protocol(REPO_ROOT)
    dev = _task_ids("qwen_operating_point")
    bench = _task_ids("f1_f8")
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00",
            wave_name="smoke",
            task_ids=dev,
        )
    ) == 4
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00",
            wave_name="complete",
            task_ids=dev,
        )
    ) == 320
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H02",
            wave_name="smoke",
            task_ids=bench,
        )
    ) == 8
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H02",
            wave_name="complete",
            task_ids=bench,
        )
    ) == 32


def test_qwen_baseline_keeps_incumbent_control_when_winner_differs():
    protocol = load_protocol(REPO_ROOT)
    assert resolved_arm_ids(
        protocol,
        "RC-H01",
        selection=_selection("qwen-off-4096"),
    ) == ["qwen-off-4096"]
    assert resolved_arm_ids(
        protocol,
        "RC-H01",
        selection=_selection("qwen-on-16384"),
    ) == ["qwen-off-4096", "qwen-on-16384"]


def test_conditional_rescue_is_fail_closed():
    protocol = load_protocol(REPO_ROOT)
    with pytest.raises(ValueError, match="forbidden"):
        resolved_arm_ids(
            protocol,
            "RC-H00R",
            selection=_selection("qwen-on-16384"),
        )
    triggered = _selection("qwen-on-16384", complete=False)
    triggered["rescue_required"] = True
    assert resolved_arm_ids(
        protocol,
        "RC-H00R",
        selection=triggered,
    ) == ["qwen-on-32768-confirmation"]
