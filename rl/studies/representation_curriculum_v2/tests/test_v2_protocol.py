from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.evaluation import tasks as task_loader
from rl.evaluation.protocol import jobs_for_wave, load_protocol
from rl.evaluation.tasks import (
    build_benchmark_task_manifest,
    load_task_manifest,
)
from rl.studies.representation_curriculum_v2 import (
    audit_context as context_auditor,
)
from rl.studies.representation_curriculum_v2 import (
    run_baseline as active_runner,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
STUDY_ROOT = REPO_ROOT / "rl/studies/representation_curriculum_v2"
PROTOCOL_FILE = STUDY_ROOT / "protocol.json"
TASK_MANIFEST_FILE = STUDY_ROOT / "task_manifest.json"


def _protocol() -> dict:
    return load_protocol(REPO_ROOT, protocol_file=PROTOCOL_FILE)


def _task_ids() -> list[str]:
    manifest = load_task_manifest(TASK_MANIFEST_FILE, repo_root=REPO_ROOT)
    return [entry["task_id"] for entry in manifest["task_sets"]["f1_f8"]]


def test_v2_is_only_two_direct_policy_zero_shot_baselines():
    protocol = _protocol()
    assert protocol["study_id"] == "representation-curriculum-v2"
    assert protocol["contract_version"] == "pixcell-direct-reconstruction-v2"
    assert protocol["purpose"] == {
        "kind": "direct-policy-zero-shot-baseline",
        "operating_point_selection": False,
        "training": False,
    }
    assert set(protocol["hypotheses"]) == {"RC-H05", "RC-H06"}
    assert "dataset" not in protocol
    assert protocol["hypotheses"]["RC-H05"]["arm_ids"] == ["qwen-on-60000"]
    assert protocol["hypotheses"]["RC-H06"]["arm_ids"] == [
        "inkling-e09-60000"
    ]
    assert "operating_point_selection" not in protocol
    assert "future_hypothesis_registry" not in protocol


def test_v2_model_and_sampling_bindings_are_exact():
    protocol = _protocol()
    assert protocol["arms"] == {
        "inkling-e09-60000": {
            "context_tokens": 65536,
            "max_image_long_edge": 1920,
            "max_output_tokens": 60000,
            "model": "thinkingmachines/Inkling",
            "provider": "tinker",
            "renderer": "tml_v0",
            "thinking": True,
            "thinking_effort": 0.9,
        },
        "qwen-on-60000": {
            "context_tokens": 65536,
            "max_image_long_edge": 1920,
            "max_output_tokens": 60000,
            "model": "Qwen/Qwen3.6-35B-A3B",
            "provider": "tinker",
            "renderer": "qwen3_5",
            "thinking": True,
            "thinking_effort": None,
        },
    }
    assert protocol["sampling"] == {
        "evaluator_workers": 8,
        "require_candidate_isolation": True,
        "sampling_concurrency": 8,
        "seed_namespace": (
            "pixcell-representation-curriculum-v2-direct-baselines"
        ),
        "temperature": 1.0,
        "top_p": 1.0,
    }
    assert protocol["launch"]["confirmation_token"] == "PIXCELL_BASELINE_V2"


def test_v2_uses_the_exact_frozen_f1_f8_tasks(
    monkeypatch: pytest.MonkeyPatch,
):
    active = json.loads(TASK_MANIFEST_FILE.read_text(encoding="utf-8"))
    canonical = build_benchmark_task_manifest(REPO_ROOT)
    assert active == canonical
    assert (
        active["logical_sha256"]
        == "05ca50526df05a3a79aa785504e36c7538106e5abdb72b64e86b20cc6f94a890"
    )

    def reject_depth_read(_root: Path) -> list[dict]:
        raise AssertionError("v2 benchmark manifest must not read depth rows")

    monkeypatch.setattr(
        task_loader,
        "_read_depth_validation_rows",
        reject_depth_read,
    )
    assert _task_ids() == [f"F{index}" for index in range(1, 9)]


@pytest.mark.parametrize("hypothesis_id", ("RC-H05", "RC-H06"))
def test_v2_smoke_is_attempt_one_and_complete_is_best_at_four(
    hypothesis_id: str,
):
    protocol = _protocol()
    task_ids = _task_ids()
    smoke = jobs_for_wave(
        protocol,
        hypothesis_id=hypothesis_id,
        wave_name="smoke",
        task_ids=task_ids,
    )
    complete = jobs_for_wave(
        protocol,
        hypothesis_id=hypothesis_id,
        wave_name="complete",
        task_ids=task_ids,
    )
    assert len(smoke) == 8
    assert {job.attempt_index for job in smoke} == {1}
    assert len(complete) == 32
    assert {job.attempt_index for job in complete} == {1, 2, 3, 4}
    assert set(smoke).issubset(set(complete))


def test_exact_renderer_contexts_fit_without_a_remote_client():
    pytest.importorskip("tinker")
    pytest.importorskip("tml_renderers")
    report = context_auditor.audit_context()
    assert report["remote_client_created"] is False
    assert report["summaries"] == {
        "inkling-e09-60000": {
            "task_count": 8,
            "max_prompt_tokens": 4159,
            "min_headroom_tokens": 1377,
        },
        "qwen-on-60000": {
            "task_count": 8,
            "max_prompt_tokens": 5357,
            "min_headroom_tokens": 179,
        },
    }


def test_context_audit_forces_offline_assets_and_restores_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.delenv("HF_HUB_OFFLINE", raising=False)
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "previous")
    with context_auditor._offline_model_assets():
        assert os.environ["HF_HUB_OFFLINE"] == "1"
        assert os.environ["TRANSFORMERS_OFFLINE"] == "1"
    assert "HF_HUB_OFFLINE" not in os.environ
    assert os.environ["TRANSFORMERS_OFFLINE"] == "previous"


def test_active_runner_binds_v2_and_accepts_no_selection(
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
                hypothesis="RC-H05",
                wave="smoke",
                expected_source_sha="a" * 40,
                confirm_spend="PIXCELL_BASELINE_V2",
                external_root=tmp_path,
            )

    monkeypatch.setattr(active_runner, "run_baseline", fake_run_baseline)
    monkeypatch.setattr(active_runner, "parser", FakeParser)
    active_runner.main()
    assert captured["protocol_file"] == PROTOCOL_FILE
    assert captured["hypothesis_id"] == "RC-H05"
    assert "selection_path" not in captured
    assert json.loads(capsys.readouterr().out) == {}
