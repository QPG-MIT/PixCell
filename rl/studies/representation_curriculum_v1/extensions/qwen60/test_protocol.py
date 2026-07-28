from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.evaluation.protocol import (
    _require_protocol_at_head,
    deterministic_seed,
    jobs_for_wave,
    load_archived_protocol,
    load_protocol,
    task_manifest_path,
)
from rl.evaluation.tasks import load_task_manifest, load_task_set
from rl.studies.representation_curriculum_v1.extensions.qwen60 import (
    run_baseline as fixed_runner,
)


REPO_ROOT = Path(__file__).resolve().parents[5]
BASE_PROTOCOL = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/protocol.json"
)
QWEN32_PROTOCOL = (
    REPO_ROOT
    / "rl/studies/representation_curriculum_v1/extensions/qwen32/protocol.json"
)
EXTENSION_PROTOCOL = Path(__file__).with_name("protocol.json")
QWEN32_MERGE_SHA = "53de41ad43c0eeec36aa73bf4ae466f199711dfc"


def _benchmark_tasks():
    manifest = load_task_manifest(task_manifest_path(REPO_ROOT), repo_root=REPO_ROOT)
    return load_task_set(
        repo_root=REPO_ROOT,
        manifest=manifest,
        task_set="f1_f8",
    )


def test_extension_is_one_fixed_near_context_limit_arm():
    protocol = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    qwen32 = load_archived_protocol(
        REPO_ROOT,
        protocol_file=QWEN32_PROTOCOL,
    )
    assert protocol["study_id"] == "representation-curriculum-v1-qwen60"
    assert protocol["base_study"] == {
        "arm_id": "qwen-on-32768",
        "github_pull_request": 7,
        "hypothesis": "RC-H03",
        "merge_git_sha": QWEN32_MERGE_SHA,
        "protocol_sha256": qwen32["logical_sha256"],
        "source_git_sha": QWEN32_MERGE_SHA,
        "study_id": "representation-curriculum-v1-qwen32",
    }
    assert protocol["hypotheses"]["RC-H04"]["arm_ids"] == ["qwen-on-60000"]
    assert protocol["arms"]["qwen-on-60000"] == {
        "context_tokens": 65536,
        "max_image_long_edge": 1440,
        "max_output_tokens": 60000,
        "model": "Qwen/Qwen3.6-35B-A3B",
        "provider": "tinker",
        "renderer": "qwen3_5",
        "thinking": True,
        "thinking_effort": None,
    }
    for field in (
        "contract_version",
        "dataset",
        "launch",
        "pricing",
        "sampling",
        "task_manifest",
    ):
        assert protocol[field] == qwen32[field]
    qwen32_arm = dict(qwen32["arms"]["qwen-on-32768"])
    qwen32_arm["max_output_tokens"] = 60000
    assert protocol["arms"]["qwen-on-60000"] == qwen32_arm
    assert protocol["decision"]["trigger_evidence"] == {
        "arm_id": "qwen-on-32768",
        "attempts": 8,
        "cap_hit_rate": 0.125,
        "hypothesis_id": "RC-H03",
        "mean_iou": 0.02505331854632315,
        "pure_executable_rate": 0.125,
        "run_manifest_record_sha256": (
            "d6ed8fc91e5a18bcc364bbd6fb167b12188a9ac3c08a8886de10774405aa42d5"
        ),
        "source_git_sha": QWEN32_MERGE_SHA,
        "summary_logical_sha256": (
            "144769709b59150270487f72f5a9b84e95f5a4d8f6ec0cfcba4378190f79da95"
        ),
        "wave": "smoke",
    }


def test_qwen32_base_commit_contains_the_bound_protocol_and_pr_merge():
    relative = QWEN32_PROTOCOL.relative_to(REPO_ROOT).as_posix()
    committed = subprocess.check_output(
        ["git", "show", f"{QWEN32_MERGE_SHA}:{relative}"],
        cwd=REPO_ROOT,
    )
    assert json.loads(committed) == json.loads(QWEN32_PROTOCOL.read_bytes())
    subject = subprocess.check_output(
        ["git", "show", "-s", "--format=%s", QWEN32_MERGE_SHA],
        cwd=REPO_ROOT,
        text=True,
    ).strip()
    assert subject == "Merge pull request #7 from QPG-MIT/agent/qwen32-f1f8-baseline"


def test_extension_smoke_and_complete_are_exact_f1_f8_g4_jobs():
    protocol = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    task_ids = [task.task_id for task in _benchmark_tasks()]
    smoke = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H04",
        wave_name="smoke",
        task_ids=task_ids,
    )
    complete = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H04",
        wave_name="complete",
        task_ids=task_ids,
    )
    assert len(smoke) == 8
    assert len(complete) == 32
    assert {job.arm_id for job in complete} == {"qwen-on-60000"}
    assert {job.task_id for job in smoke} == set(task_ids)
    assert {job.attempt_index for job in complete} == {1, 2, 3, 4}


def test_extension_keeps_base_seed_pairing():
    base = load_archived_protocol(REPO_ROOT, protocol_file=BASE_PROTOCOL)
    extension = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    for task in _benchmark_tasks():
        for attempt_index in range(1, 5):
            assert deterministic_seed(
                extension,
                task_id=task.task_id,
                attempt_index=attempt_index,
            ) == deterministic_seed(
                base,
                task_id=task.task_id,
                attempt_index=attempt_index,
            )


def test_archived_60k_context_arithmetic_is_internally_consistent():
    protocol = load_archived_protocol(
        REPO_ROOT,
        protocol_file=EXTENSION_PROTOCOL,
    )
    arm = protocol["arms"]["qwen-on-60000"]
    context_fit = protocol["decision"]["context_fit"]
    largest_prompt = context_fit["largest_frozen_f1_f8_prompt_tokens"]
    context_tokens = arm["context_tokens"]
    max_output_tokens = arm["max_output_tokens"]
    minimum_reserve = context_tokens - largest_prompt - max_output_tokens
    assert context_tokens - largest_prompt == context_fit[
        "minimum_f1_f8_completion_capacity_tokens"
    ]
    assert minimum_reserve == context_fit["minimum_context_reserve_tokens"]
    assert minimum_reserve >= 0
    assert context_fit["selected_max_output_tokens"] == max_output_tokens
    assert largest_prompt + 64_000 > context_tokens
    assert largest_prompt + max_output_tokens <= context_tokens


def test_protocol_override_must_be_source_controlled(tmp_path: Path):
    outside = tmp_path / "protocol.json"
    outside.write_text(EXTENSION_PROTOCOL.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match="inside the source repository"):
        load_protocol(REPO_ROOT, protocol_file=outside)


def test_fixed_runner_forwards_the_extension_protocol_to_the_head_guard(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    captured: dict[str, object] = {}

    async def fake_run_baseline(**kwargs):
        captured.update(kwargs)
        return {"summaries": {}}

    class FakeParser:
        @staticmethod
        def parse_args():
            return SimpleNamespace(
                wave="smoke",
                expected_source_sha="a" * 40,
                confirm_spend="PIXCELL_PHASE1_BASELINE",
                external_root=tmp_path,
            )

    monkeypatch.setattr(fixed_runner, "run_baseline", fake_run_baseline)
    monkeypatch.setattr(fixed_runner, "parser", FakeParser)
    fixed_runner.main()
    assert captured["protocol_file"] == EXTENSION_PROTOCOL
    assert captured["hypothesis_id"] == "RC-H04"
    assert captured["wave_name"] == "smoke"
    assert json.loads(capsys.readouterr().out) == {}


def test_paid_protocol_guard_accepts_head_and_rejects_non_protocol_path():
    _require_protocol_at_head(REPO_ROOT, BASE_PROTOCOL)
    with pytest.raises(ValueError, match="tracked by the paid-launch commit"):
        _require_protocol_at_head(REPO_ROOT, REPO_ROOT / ".git")
