from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from homi.conductor.source_policy import strict_purity_violations
from rl.common.isolation import ExecutionBoundary
from rl.studies.representation_curriculum_v2 import audit_phase0


REPO_ROOT = Path(__file__).resolve().parents[4]


def _protocol() -> dict:
    return {
        "study_id": "representation-curriculum-v2",
        "logical_sha256": "1" * 64,
        "arms": {
            "inkling-e09-60000": {
                "model": "thinkingmachines/Inkling",
                "renderer": "tml_v0",
                "thinking": True,
                "thinking_effort": 0.9,
                "context_tokens": 65_536,
                "max_output_tokens": 60_000,
                "max_image_long_edge": 1920,
                "provider": "tinker",
            },
            "qwen-on-60000": {
                "model": "Qwen/Qwen3.6-35B-A3B",
                "renderer": "qwen3_5",
                "thinking": True,
                "thinking_effort": None,
                "context_tokens": 65_536,
                "max_output_tokens": 60_000,
                "max_image_long_edge": 1920,
                "provider": "tinker",
            },
        },
        "hypotheses": {
            "RC-H05": {"arm_ids": ["qwen-on-60000"]},
            "RC-H06": {"arm_ids": ["inkling-e09-60000"]},
        },
        "sampling": {"temperature": 1.0, "top_p": 1.0},
    }


def _boundary(tmp_path: Path) -> ExecutionBoundary:
    return ExecutionBoundary(
        runtime_path=Path("/usr/bin/docker"),
        daemon_endpoint="unix:///var/run/docker.sock",
        image_ref="sha256:" + "a" * 64,
        image_id="sha256:" + "a" * 64,
        workspace_root=tmp_path,
    )


def test_forbidden_prompt_fields_fail_closed() -> None:
    audit_phase0._assert_prompt_is_model_safe(
        "image, footprint, catalogue, and program",
        case_id="clean",
    )
    with pytest.raises(ValueError, match="verifier/answer-only"):
        audit_phase0._assert_prompt_is_model_safe(
            "Here is calibration.json and the target raster.",
            case_id="leak",
        )


def test_evaluator_probe_is_fixed_and_strictly_primitive_only() -> None:
    probe = audit_phase0._AUDIT_PROBE_PROGRAM
    assert strict_purity_violations(probe) == []
    assert 'write_gds("device.gds")' in probe
    assert "gf.components.rectangle" in probe
    assert "dataset" not in probe.casefold()


def test_renderer_audit_covers_exactly_sixteen_contexts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = _protocol()
    tasks = [
        SimpleNamespace(
            task_id=f"F{index}",
            observation=SimpleNamespace(footprint_um=(1.0, 1.0)),
        )
        for index in range(1, 9)
    ]

    class FakeSampler:
        def __init__(self, _target, *, service_client_factory):
            self.service_client_factory = service_client_factory

        @staticmethod
        def build_prompt(messages):
            return SimpleNamespace(length=messages)

    def fake_arm_spec(document, arm_id):
        return SimpleNamespace(
            **document["arms"][arm_id],
            arm_id=arm_id,
        )

    monkeypatch.setattr(audit_phase0, "TinkerSampler", FakeSampler)
    monkeypatch.setattr(audit_phase0, "arm_spec", fake_arm_spec)
    monkeypatch.setattr(audit_phase0, "_sampler_target", lambda arm: arm)
    monkeypatch.setattr(
        audit_phase0,
        "_messages",
        lambda task, _arm: 4000 + int(task.task_id[1:]),
    )
    monkeypatch.setattr(
        audit_phase0,
        "build_prompt_text",
        lambda _observation: "image, footprint, catalogue, and program",
    )

    report = audit_phase0._renderer_audit(
        protocol=protocol,
        tasks=tasks,
    )
    assert report["model_client_created"] is False
    assert report["prompt_cases"] == 16
    assert set(report["arms"]) == set(audit_phase0.EXPECTED_ARMS)
    for summary in report["arms"].values():
        assert summary == {
            "prompt_cases": 8,
            "prompt_tokens_min": 4001,
            "prompt_tokens_max": 4008,
            "minimum_headroom_tokens": 1528,
        }


def test_renderer_audit_rejects_negative_headroom(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = _protocol()
    tasks = [
        SimpleNamespace(
            task_id=f"F{index}",
            observation=SimpleNamespace(footprint_um=(1.0, 1.0)),
        )
        for index in range(1, 9)
    ]

    class OversizeSampler:
        def __init__(self, _target, *, service_client_factory):
            self.service_client_factory = service_client_factory

        @staticmethod
        def build_prompt(_messages):
            return SimpleNamespace(length=5537)

    monkeypatch.setattr(audit_phase0, "TinkerSampler", OversizeSampler)
    monkeypatch.setattr(
        audit_phase0,
        "arm_spec",
        lambda document, arm_id: SimpleNamespace(
            **document["arms"][arm_id],
            arm_id=arm_id,
        ),
    )
    monkeypatch.setattr(audit_phase0, "_sampler_target", lambda arm: arm)
    monkeypatch.setattr(audit_phase0, "_messages", lambda _task, _arm: [])
    monkeypatch.setattr(
        audit_phase0,
        "build_prompt_text",
        lambda _observation: "image, footprint, catalogue, and program",
    )
    with pytest.raises(ValueError, match="exceeds context"):
        audit_phase0._renderer_audit(protocol=protocol, tasks=tasks)


def test_schema_smoke_round_trips_both_arms(tmp_path: Path) -> None:
    protocol = _protocol()
    runtime = {
        "python": "3.13.5",
        "packages": {"gdsfactory": "9.20.7"},
        "tinker_cookbook_commit": "b" * 40,
    }
    report = audit_phase0._schema_smoke(
        repo_root=REPO_ROOT,
        protocol=protocol,
        source_git_sha="c" * 40,
        task_set_sha256="d" * 64,
        prompt_sha256="e" * 64,
        runtime=runtime,
        boundary=_boundary(tmp_path),
    )
    assert set(report) == set(audit_phase0.EXPECTED_ARMS)
    assert all(
        set(records)
        == {
            "run_manifest_record_sha256",
            "sampling_record_sha256",
            "evaluation_record_sha256",
        }
        for records in report.values()
    )


def test_sealed_audit_rejects_dirty_or_wrong_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        audit_phase0,
        "_git_state",
        lambda _root: ("a" * 40, False),
    )
    with pytest.raises(ValueError, match="source worktree must be clean"):
        audit_phase0.run_audit(
            repo_root=REPO_ROOT,
            expected_source_sha="a" * 40,
        )
    with pytest.raises(ValueError, match="source SHA mismatch"):
        audit_phase0.run_audit(
            repo_root=REPO_ROOT,
            expected_source_sha="b" * 40,
        )
