from __future__ import annotations

import asyncio
import hashlib
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

pytest.importorskip("chz", reason="Tinker is an optional RL dependency")
pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
pytest.importorskip(
    "tinker_cookbook",
    reason="Tinker Cookbook is an optional RL dependency",
)

from tinker_cookbook.renderers import Message, ParseTermination, TextPart

from rl.common.contracts import ModelObservation, VerifierReference
from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
)
from rl.evaluation.tasks import EvaluationTask
from rl.studies.representation_training_v1 import evaluation, launcher, promotion
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    StageSpec,
    load_protocol,
    stage_spec,
)
from rl.studies.representation_training_v1.store import (
    StageKey,
    TrainingRecord,
    TrainingStore,
    canonical_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_SHA = "a" * 40


def _stage(level: str = "L0") -> StageSpec:
    index = int(level[1:])
    return StageSpec(
        stage_id=f"qwen-base-rl-{level.lower()}",
        kind="rl",
        model_key="qwen",
        recipe_key="qwen_rl",
        hypotheses=("h-qwen-base-curriculum-rl",),
        parent=("base:qwen" if index == 0 else f"qwen-base-rl-l{index - 1}:complete"),
        levels=(),
        current_level=level,
        replay_levels=tuple(f"L{value}" for value in range(index)),
        waves={
            "smoke": {"max_steps": 1, "approval": "initial"},
            "step-5": {
                "max_steps": 5,
                "approval": "rollout-health-receipt",
            },
            "step-10": {
                "max_steps": 10,
                "approval": "current-level-held-out-promotion-receipt",
            },
            "complete": {
                "max_steps": 30,
                "approval": "current-level-held-out-promotion-receipt",
            },
        },
    )


def _image_bytes() -> bytes:
    image = Image.new("L", (8, 8), 255)
    for x in range(2, 6):
        for y in range(2, 6):
            image.putpixel((x, y), 0)
    stream = io.BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _task(task_id: str = "l0-baseline") -> EvaluationTask:
    image = _image_bytes()
    digest = hashlib.sha256(image).hexdigest()
    return EvaluationTask(
        task_id=task_id,
        level="L0",
        representation_id="representation-l0",
        observation=ModelObservation(
            image_bytes=image,
            footprint_um=(2.0, 2.0),
            image_sha256=digest,
        ),
        reference=VerifierReference(
            target_image_bytes=image,
            footprint_um=(2.0, 2.0),
            target_image_sha256=digest,
        ),
    )


class _Renderer:
    tokenizer = SimpleNamespace(decode=lambda tokens: "decoded:" + repr(tokens))

    @staticmethod
    def build_generation_prompt(messages: list[Any]) -> Any:
        assert "Phase-A Device Input" in messages[0]["content"][1]["text"]
        return SimpleNamespace(length=100)

    @staticmethod
    def get_stop_sequences() -> list[int]:
        return [99]

    @staticmethod
    def parse_response(_tokens: list[int]) -> tuple[Message, ParseTermination]:
        return (
            Message(
                role="assistant",
                content=[TextPart(type="text", text="print('candidate')")],
            ),
            ParseTermination.STOP_SEQUENCE,
        )


class _Evaluator:
    execution_boundary = SimpleNamespace(
        runtime_path=Path("/usr/bin/false"),
        daemon_endpoint="unix:///private/fake.sock",
        image_ref="pixcell-evaluator@sha256:" + "3" * 64,
        image_id="sha256:" + "4" * 64,
        workspace_root=Path("/private/fake-workspace"),
    )

    @staticmethod
    def validate_reference(reference: VerifierReference) -> dict[str, Any]:
        return {
            "target_image_sha256": reference.target_image_sha256,
            "image_size_px": [8, 8],
            "bbox": [2, 2, 6, 6],
            "scale_px_per_um": [2.0, 2.0],
        }

    @staticmethod
    def evaluate_batch(
        requests: list[tuple[VerifierReference, str]],
    ) -> list[EvaluationResult]:
        return [
            EvaluationResult(
                status=EvaluationStatus.OK,
                attribution=Attribution.MODEL,
                iou=0.5,
                dice=2 / 3,
                metrics={
                    "render_sha256": "1" * 64,
                    "reference_sha256": "2" * 64,
                },
            )
            for _ in requests
        ]

    @staticmethod
    def close() -> None:
        return None


class _SamplingClient:
    @staticmethod
    async def sample_async(**kwargs: Any) -> Any:
        assert kwargs["num_samples"] == 1
        return SimpleNamespace(
            sequences=[SimpleNamespace(tokens=[1, 2, 3], stop_reason="stop")]
        )


class _BaseService:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def create_sampling_client(self, **kwargs: str) -> _SamplingClient:
        self.calls.append(dict(kwargs))
        return _SamplingClient()


def test_level_panels_are_exact_fixed_validation_slots(tmp_path: Path) -> None:
    protocol = load_protocol(REPO_ROOT)
    validation_rows = evaluation._depth_rows(REPO_ROOT / "dataset")
    assert evaluation.PANELS == (
        "progress",
        "depth-validation",
        "inkling-promotion",
    )
    expected_counts = {"L0": 93, "L1": 127, "L2": 98, "L3": 120, "L4": 108}
    for level, panel in evaluation.LEVEL_PROGRESS_PANELS.items():
        tasks = evaluation.build_panel_tasks(
            repo_root=REPO_ROOT,
            protocol=protocol,
            panel=panel,
        )
        assert len(tasks) == expected_counts[level]
        assert {task.level for task in tasks} == {level}
        assert len({task.representation_id for task in tasks}) == len(tasks)
        assert {task.task_id for task in tasks} == {
            evaluation._depth_task(row).task_id
            for row in validation_rows
            if str(row["level"]).upper() == level
            and row["realization_slot"] == 6
        }
    final = evaluation.build_panel_tasks(
        repo_root=REPO_ROOT,
        protocol=protocol,
        panel=evaluation.PANEL_DEPTH_FINAL_SELECTION,
    )
    assert len(final) == 546
    assert len({(task.level, task.representation_id) for task in final}) == 546
    assert {task.task_id for task in final} == {
        evaluation._depth_task(row).task_id
        for row in validation_rows
        if row["realization_slot"] == 7
    }

    stage_path = tmp_path / "stage"
    stage_path.mkdir()
    for panel in (
        *evaluation.LEVEL_PROGRESS_PANELS.values(),
        evaluation.PANEL_DEPTH_FINAL_SELECTION,
    ):
        store = evaluation.CheckpointEvaluationStore(
            stage_path=stage_path,
            wave="complete",
            checkpoint_name="final",
            panel=panel,
        )
        assert store.root.name == panel


def test_base_and_checkpoint_sampler_client_arguments_are_distinct() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = _stage()
    base = evaluation.BaseModelBinding(
        key=StageKey(STUDY_ID, stage.stage_id, "r0"),
        stage=stage,
        wave="base",
        checkpoint_name="base",
        checkpoint={"name": "base"},
        checkpoint_inventory_sha256="1" * 64,
        sampler_path=protocol["models"]["qwen"]["model"],
        binding_sha256="2" * 64,
    )
    record = TrainingRecord(
        payload={},
        payload_sha256="3" * 64,
        record_sha256="4" * 64,
        relative_path=Path("record.json"),
    )
    checkpoint = evaluation.CheckpointBinding(
        key=base.key,
        stage=stage,
        wave="smoke",
        checkpoint_name="000001",
        checkpoint={"name": "000001"},
        checkpoint_inventory_sha256="5" * 64,
        sampler_path="tinker://unit/sampler/000001",
        run_manifest=record,
        wave_receipt=record,
    )
    assert evaluation._sampling_client_kwargs(base) == {
        "base_model": protocol["models"]["qwen"]["model"]
    }
    assert evaluation._sampling_client_kwargs(checkpoint) == {
        "model_path": "tinker://unit/sampler/000001"
    }


def test_base_l0_panel_run_and_resume_has_no_fictitious_receipt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = _stage()
    service = _BaseService()
    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setattr(evaluation, "load_protocol", lambda *_a, **_k: protocol)
    monkeypatch.setattr(
        evaluation,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(evaluation, "stage_spec", lambda *_a, **_k: stage)
    monkeypatch.setattr(evaluation, "_renderer", lambda *_a, **_k: _Renderer())

    result = asyncio.run(
        evaluation.run_checkpoint_evaluation(
            repo_root=REPO_ROOT,
            stage_id=stage.stage_id,
            wave="base",
            checkpoint_name="base",
            replicate_id="r0",
            panel=evaluation.LEVEL_PROGRESS_PANELS["L0"],
            expected_source_sha=SOURCE_SHA,
            expected_wave_receipt_sha256="",
            external_root=tmp_path / "external",
            confirmation=protocol["launch"]["confirmation_token"],
            service_client_factory=lambda: service,
            evaluator_factory=_Evaluator,
            base_model=True,
        )
    )
    assert result["status"] == "complete"
    assert service.calls == [
        {"base_model": protocol["models"]["qwen"]["model"]}
    ]
    report = json.loads(Path(result["report"]).read_text(encoding="utf-8"))
    sampler = report["payload"]["provenance"]["sampler"]
    assert sampler["binding_kind"] == "base-model"
    assert not any("training_" in field for field in sampler)
    sample = next((tmp_path / "external").rglob("sample.json"))
    sample_payload = json.loads(sample.read_text(encoding="utf-8"))["payload"]
    assert "base_model_binding_sha256" in sample_payload
    assert "training_wave_receipt_record_sha256" not in sample_payload
    assert not list((tmp_path / "external").rglob("receipt.json"))
    assert not list((tmp_path / "external").rglob("run_manifest.json"))

    gated_stage = StageSpec(
        **{
            **stage.__dict__,
            "waves": {
                **stage.waves,
                "smoke": {
                    "max_steps": 1,
                    "approval": "base-level-held-out-baseline-receipt",
                },
            },
        }
    )
    training_store = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=tmp_path / "external",
    )
    with training_store.acquire_stage_lock(
        StageKey(STUDY_ID, stage.stage_id, "r0")
    ):
        base_approval = launcher._approval_record(
            repo_root=REPO_ROOT,
            store=training_store,
            key=StageKey(STUDY_ID, stage.stage_id, "r0"),
            stage=gated_stage,
            wave_name="smoke",
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    assert base_approval is not None
    assert (
        base_approval.payload["approval_gate"]
        == "base-level-held-out-baseline-receipt"
    )

    monkeypatch.delenv("TINKER_API_KEY")
    resumed = asyncio.run(
        evaluation.run_checkpoint_evaluation(
            repo_root=REPO_ROOT,
            stage_id=stage.stage_id,
            wave="base",
            checkpoint_name="base",
            replicate_id="r0",
            panel=evaluation.LEVEL_PROGRESS_PANELS["L0"],
            expected_source_sha=SOURCE_SHA,
            expected_wave_receipt_sha256="",
            external_root=tmp_path / "external",
            confirmation=protocol["launch"]["confirmation_token"],
            service_client_factory=lambda: pytest.fail("paid client on resume"),
            evaluator_factory=_Evaluator,
            base_model=True,
        )
    )
    assert resumed["status"] == "already_complete"


def test_base_panel_rechecks_source_after_preflight_before_paid_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = _stage()
    source_checks = 0

    def changing_source(_root: Path, expected: str) -> str:
        nonlocal source_checks
        source_checks += 1
        if source_checks == 2:
            raise ValueError("worktree changed")
        return expected

    monkeypatch.setenv("TINKER_API_KEY", "test-only")
    monkeypatch.setattr(evaluation, "load_protocol", lambda *_a, **_k: protocol)
    monkeypatch.setattr(evaluation, "validate_source_sha", changing_source)
    monkeypatch.setattr(evaluation, "stage_spec", lambda *_a, **_k: stage)
    monkeypatch.setattr(
        evaluation,
        "_dataset_binding",
        lambda *_a, **_k: {
            "logical_release_sha256": protocol["dataset"][
                "logical_release_sha256"
            ],
            "freeze_file_sha256": "1" * 64,
            "parquet_shards": {"depth.parquet": "2" * 64},
        },
    )
    monkeypatch.setattr(evaluation, "build_panel_tasks", lambda **_k: [_task()])
    monkeypatch.setattr(evaluation, "_renderer", lambda *_a, **_k: _Renderer())
    with pytest.raises(
        evaluation.CheckpointEvaluationError,
        match="source changed after evaluation preflight",
    ):
        asyncio.run(
            evaluation.run_checkpoint_evaluation(
                repo_root=REPO_ROOT,
                stage_id=stage.stage_id,
                wave="base",
                checkpoint_name="base",
                replicate_id="r0",
                panel=evaluation.LEVEL_PROGRESS_PANELS["L0"],
                expected_source_sha=SOURCE_SHA,
                expected_wave_receipt_sha256="",
                external_root=tmp_path / "external",
                confirmation=protocol["launch"]["confirmation_token"],
                service_client_factory=lambda: pytest.fail(
                    "paid client created after source mutation"
                ),
                evaluator_factory=_Evaluator,
                base_model=True,
            )
        )
    assert source_checks == 2


def _write_health_fixture(
    tmp_path: Path,
    *,
    fault: bool = False,
    all_constant: bool = False,
    all_failed: bool = False,
    unknown_status: bool = False,
    misattributed_infrastructure_status: bool = False,
    reward_mismatch: bool = False,
    failure_nonzero_reward: bool = False,
    failure_geometry: bool = False,
    sample_inventory_mismatch: bool = False,
) -> tuple[
    TrainingStore,
    StageKey,
    StageSpec,
    dict[str, Any],
    TrainingRecord,
]:
    protocol = load_protocol(REPO_ROOT)
    stage = _stage()
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    store = TrainingStore(repo_root=REPO_ROOT, external_root=tmp_path / "external")
    invocation_id = "smoke-unit"
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            {
                "source_git_sha": SOURCE_SHA,
                "protocol_logical_sha256": protocol["logical_sha256"],
            },
        )
        invocation = store.begin_invocation(
            key,
            invocation_id=invocation_id,
            payload={"wave": "smoke"},
        )
        for group in range(8):
            task_id = f"task-{group}"
            for attempt in range(1, 5):
                sample = store.write_candidate_sample(
                    key,
                    invocation_id=invocation_id,
                    step=0,
                    task_id=task_id,
                    attempt=attempt,
                    payload={"task": task_id, "attempt": attempt},
                )
                status = "runtime_error"
                if not all_failed and group == 0 and attempt == 2:
                    status = "ok"
                if unknown_status and group == 0 and attempt == 1:
                    status = "invented_status"
                if (
                    misattributed_infrastructure_status
                    and group == 0
                    and attempt == 1
                ):
                    status = "reference_error"
                reward = (
                    0.5
                    if status == "ok" and not all_constant
                    else 0.0
                )
                iou = reward if status == "ok" else None
                dice = (2.0 * iou / (1.0 + iou)) if iou is not None else None
                if reward_mismatch and status == "ok":
                    reward = 0.4
                if failure_nonzero_reward and group == 0 and attempt == 1:
                    reward = 0.25
                if failure_geometry and group == 0 and attempt == 1:
                    iou = 0.25
                    dice = 0.4
                store.write_candidate(
                    key,
                    invocation_id=invocation_id,
                    step=0,
                    task_id=task_id,
                    attempt=attempt,
                    payload={
                        "sample_record": {
                            "relative_path": str(sample.relative_path),
                            "payload_sha256": sample.payload_sha256,
                            "record_sha256": sample.record_sha256,
                        },
                        "evaluation": {
                            "status": status,
                            "attribution": (
                                "reference"
                                if fault and group == 0 and attempt == 1
                                else "model"
                            ),
                            "iou": iou,
                            "dice": dice,
                            "reward": reward,
                            "violations": [],
                            "error": None,
                            "latency_seconds": 0.1,
                            "metrics": {},
                        },
                    },
                )
        candidate_root = store.candidate_root(key) / invocation_id
        candidate_files = sorted(candidate_root.rglob("evaluation.json"))
        sample_files = sorted(candidate_root.rglob("sample.json"))
        candidate_inventory = [
            {
                "path": str(path.relative_to(store.stage_path(key))),
                "sha256": promotion.file_sha256(path),
            }
            for path in candidate_files
        ]
        sample_inventory = [
            {
                "path": str(path.relative_to(store.stage_path(key))),
                "sha256": promotion.file_sha256(path),
            }
            for path in sample_files
        ]
        receipt = store.write_wave_receipt(
            key,
            wave="smoke",
            payload={
                "stage_id": stage.stage_id,
                "wave": "smoke",
                "max_steps": 1,
                "run_manifest_record_sha256": manifest.record_sha256,
                "invocation_record_sha256": invocation.record_sha256,
                "invocation_id": invocation_id,
                "checkpoint": {
                    "name": "000001",
                    "batch": 1,
                    "epoch": None,
                    "final": True,
                    "state_path": "tinker://unit/state/000001",
                    "sampler_path": "tinker://unit/sampler/000001",
                },
                "candidate_inventory": {
                    "count": 32,
                    "expected_count": 32,
                    "logical_sha256": canonical_sha256(candidate_inventory),
                },
                "sample_inventory": {
                    "count": 32,
                    "expected_count": 32,
                    "logical_sha256": (
                        "f" * 64
                        if sample_inventory_mismatch
                        else canonical_sha256(sample_inventory)
                    ),
                },
            },
        )
    return store, key, stage, protocol, receipt


def test_rollout_health_gate_is_receipt_only_and_exact(tmp_path: Path) -> None:
    store, key, stage, protocol, receipt = _write_health_fixture(tmp_path)
    with store.acquire_stage_lock(key):
        approval = promotion.record_rollout_health_approval(
            store=store,
            key=key,
            stage=stage,
            wave_name="step-5",
            prior_wave="smoke",
            prior_receipt=receipt,
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    metrics = approval.payload["metrics"]
    assert metrics["candidates"] == 32
    assert metrics["groups"] == 8
    assert metrics["group_size"] == 4
    assert metrics["pure_executable"] == 1
    assert metrics["nonconstant_reward_groups"] == 1
    assert metrics["evaluator_or_reference_faults"] == 0
    assert store.load_wave_approval(key, wave="step-5") is None
    assert (
        store.load_rollout_health_approval(key, wave="step-5").record_sha256
        == approval.record_sha256
    )


def test_launcher_derives_rollout_health_before_step5(tmp_path: Path) -> None:
    store, key, stage, protocol, _receipt = _write_health_fixture(tmp_path)
    with store.acquire_stage_lock(key):
        approval = launcher._approval_record(
            repo_root=REPO_ROOT,
            store=store,
            key=key,
            stage=stage,
            wave_name="step-5",
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    assert approval is not None
    assert approval.payload["approval_gate"] == "rollout-health-receipt"
    health = store.load_rollout_health_approval(key, wave="step-5")
    assert health is not None
    assert health.payload["approval_gate"] == "rollout-health-receipt"
    assert store.load_wave_approval(key, wave="step-5") is None
    resolved = launcher._resolved_launch_binding(
        repo_root=REPO_ROOT,
        protocol=protocol,
        stage=stage,
        wave_name="step-5",
        store=store,
        key=key,
        parent=None,
        resume_batch=1,
    )
    assert resolved["wave_gate_evidence"] == {
        "approval_gate": "rollout-health-receipt",
        "relative_path": str(approval.relative_path),
        "payload_sha256": approval.payload_sha256,
        "record_sha256": approval.record_sha256,
    }


def test_l0_sft_rl_resolved_launch_binds_parent_transition(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = StageSpec(
        stage_id="qwen-l0-rl-l1",
        kind="rl",
        model_key="qwen",
        recipe_key="qwen_rl",
        hypotheses=("RT-H03",),
        parent="qwen-l0-sft:complete",
        levels=(),
        current_level="L1",
        replay_levels=("L0",),
        waves={
            "smoke": {
                "max_steps": 1,
                "approval": "parent-receipt-and-source-transition",
            },
        },
    )
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    store = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=tmp_path / "external",
    )
    with store.acquire_stage_lock(key):
        store.create_or_verify_manifest(
            key,
            {
                "source_git_sha": SOURCE_SHA,
                "protocol_logical_sha256": protocol["logical_sha256"],
            },
        )
        approval = store.write_wave_approval(
            key,
            wave="smoke",
            payload={
                "schema_version": (
                    promotion.PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
                ),
                "approval_gate": "parent-receipt-and-source-transition",
            },
        )
    resolved = launcher._resolved_launch_binding(
        repo_root=REPO_ROOT,
        protocol=protocol,
        stage=stage,
        wave_name="smoke",
        store=store,
        key=key,
        parent=None,
        resume_batch=None,
    )
    assert resolved["wave_gate_evidence"] == {
        "approval_gate": "parent-receipt-and-source-transition",
        "relative_path": str(approval.relative_path),
        "payload_sha256": approval.payload_sha256,
        "record_sha256": approval.record_sha256,
    }


@pytest.mark.parametrize("panel", ["level-progress-l0", "progress"])
def test_launcher_current_level_gate_binds_exact_level_panel(
    tmp_path: Path,
    panel: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, key, original, protocol, receipt = _write_health_fixture(tmp_path)
    stage = StageSpec(
        **{
            **original.__dict__,
            "waves": {
                "smoke": {"max_steps": 1, "approval": "initial"},
                "step-10": {
                    "max_steps": 10,
                    "approval": "current-level-held-out-promotion-receipt",
                },
            },
        }
    )
    checkpoint = receipt.payload["checkpoint"]
    # The fixture below is intentionally minimal because this test exercises
    # the launcher's downstream receipt/panel binding.  Canonical report
    # reconstruction is tested separately and must remain fail-closed.
    monkeypatch.setattr(
        launcher,
        "validate_same_source_wave_approval",
        lambda **_kwargs: None,
    )
    payload = {
        "schema_version": promotion.APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": "current-level-held-out-promotion-receipt",
        "stage_id": stage.stage_id,
        "wave": "step-10",
        "source_git_sha": SOURCE_SHA,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "prior_wave": "smoke",
        "prior_receipt_record_sha256": receipt.record_sha256,
        "evaluation": {
            "stage_id": stage.stage_id,
            "wave": "smoke",
            "panel": panel,
            "checkpoint": checkpoint,
            "report_record_sha256": "9" * 64,
            "training_wave_receipt_record_sha256": receipt.record_sha256,
        },
    }
    with store.acquire_stage_lock(key):
        store.write_wave_approval(key, wave="step-10", payload=payload)
        if panel == "level-progress-l0":
            observed = launcher._approval_record(
                repo_root=REPO_ROOT,
                store=store,
                key=key,
                stage=stage,
                wave_name="step-10",
                source_git_sha=SOURCE_SHA,
                protocol=protocol,
            )
            assert observed is not None
        else:
            with pytest.raises(
                launcher.TrainingLaunchError,
                match="held-out report",
            ):
                launcher._approval_record(
                    repo_root=REPO_ROOT,
                    store=store,
                    key=key,
                    stage=stage,
                    wave_name="step-10",
                    source_git_sha=SOURCE_SHA,
                    protocol=protocol,
                )


def test_launcher_next_level_gate_uses_current_dual_panel_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    store = TrainingStore(repo_root=REPO_ROOT, external_root=tmp_path / "external")
    parent_stage = stage_spec(protocol, "qwen-base-rl-l0")
    child_stage = stage_spec(protocol, "qwen-base-rl-l1")
    assert child_stage.wave("smoke")["approval"] == (
        "prior-and-current-level-held-out-transition-receipt"
    )
    parent_key = StageKey(STUDY_ID, parent_stage.stage_id, "r0")
    child_key = StageKey(STUDY_ID, child_stage.stage_id, "r0")
    checkpoint = {
        "name": "000030",
        "batch": 30,
        "epoch": None,
        "final": True,
        "state_path": "tinker://unit/state/000030",
        "sampler_path": "tinker://unit/sampler/000030",
    }
    inventory_entry = {
        **checkpoint,
        "role": "terminal",
        "training_progress_fraction": 1.0,
    }
    with store.acquire_stage_lock(parent_key):
        manifest = store.create_or_verify_manifest(
            parent_key,
            {
                "source_git_sha": SOURCE_SHA,
                "protocol_logical_sha256": protocol["logical_sha256"],
            },
        )
        receipt = store.write_wave_receipt(
            parent_key,
            wave="complete",
            payload={
                "stage_id": parent_stage.stage_id,
                "wave": "complete",
                "run_manifest_record_sha256": manifest.record_sha256,
                "checkpoint": checkpoint,
                "checkpoint_inventory": {
                    "count": 1,
                    "entries": [inventory_entry],
                    "logical_sha256": canonical_sha256([inventory_entry]),
                },
            },
        )
    approval_payload = {
        "schema_version": promotion.APPROVAL_SCHEMA_VERSION,
        "decision": "approve",
        "approval_gate": "prior-and-current-level-held-out-transition-receipt",
        "stage_id": child_stage.stage_id,
        "wave": "smoke",
        "source_git_sha": SOURCE_SHA,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "parent_stage_id": parent_stage.stage_id,
        "parent_wave": "complete",
        "parent_receipt_record_sha256": receipt.record_sha256,
        "selected_parent_checkpoint": checkpoint,
        "selected_parent_checkpoint_inventory_sha256": canonical_sha256(
            [inventory_entry]
        ),
        "evaluation": {
            "stage_id": parent_stage.stage_id,
            "wave": "complete",
            "panel": "level-progress-l0",
            "checkpoint": checkpoint,
            "report_record_sha256": "8" * 64,
            "training_wave_receipt_record_sha256": receipt.record_sha256,
        },
        "entry_baseline": {
            "stage_id": parent_stage.stage_id,
            "wave": "complete",
            "panel": "level-progress-l1",
            "checkpoint": checkpoint,
            "report_record_sha256": "9" * 64,
            "training_wave_receipt_record_sha256": receipt.record_sha256,
        },
    }
    validation_calls: list[dict[str, Any]] = []
    monkeypatch.setattr(
        launcher,
        "validate_same_source_wave_approval",
        lambda **kwargs: validation_calls.append(dict(kwargs)),
    )
    with store.acquire_stage_lock(child_key):
        store.write_wave_approval(
            child_key,
            wave="smoke",
            payload=approval_payload,
        )
        approval = launcher._approval_record(
            repo_root=REPO_ROOT,
            store=store,
            key=child_key,
            stage=child_stage,
            wave_name="smoke",
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    assert approval is not None
    assert approval.payload["evaluation"]["panel"] == "level-progress-l0"
    assert approval.payload["entry_baseline"]["panel"] == "level-progress-l1"
    assert len(validation_calls) == 1
    assert validation_calls[0]["approval"] is approval


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"fault": True}, "evaluator or reference fault"),
        ({"all_constant": True}, "no nonconstant G4 group"),
        ({"all_failed": True}, "no pure executable candidate"),
        ({"unknown_status": True}, "unknown evaluator status"),
        (
            {"misattributed_infrastructure_status": True},
            "evaluator or reference status mislabeled",
        ),
        ({"reward_mismatch": True}, "reward differs from raw IoU"),
        ({"failure_nonzero_reward": True}, "model failure has nonzero reward"),
        ({"failure_geometry": True}, "model failure contains geometry metrics"),
        ({"sample_inventory_mismatch": True}, "sample files differ"),
    ],
)
def test_rollout_health_gate_fails_closed(
    tmp_path: Path,
    kwargs: dict[str, bool],
    message: str,
) -> None:
    store, key, stage, protocol, receipt = _write_health_fixture(
        tmp_path,
        **kwargs,
    )
    with store.acquire_stage_lock(key), pytest.raises(
        promotion.PromotionError,
        match=message,
    ):
        promotion.record_rollout_health_approval(
            store=store,
            key=key,
            stage=stage,
            wave_name="step-5",
            prior_wave="smoke",
            prior_receipt=receipt,
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )


def test_model_status_allowlists_cannot_drift() -> None:
    assert promotion._MODEL_EVALUATION_STATUSES == (
        evaluation._MODEL_EVALUATION_STATUSES
    )


def test_level_gate_plans_never_use_f1_f8() -> None:
    l0 = _stage("L0")
    current = promotion.approval_plan(l0, "step-10")
    assert current.expected_panel == "level-progress-l0"
    assert current.allowed_evaluation_checkpoints == ((l0.stage_id, "step-5"),)

    l1 = _stage("L1")
    # The first wave has the prior-level approval in the sealed protocol;
    # represent it directly here without weakening StageSpec validation.
    l1 = StageSpec(
        **{
            **l1.__dict__,
            "waves": {
                **l1.waves,
                "smoke": {
                    "max_steps": 1,
                    "approval": (
                        "prior-and-current-level-held-out-transition-receipt"
                    ),
                },
            },
        }
    )
    prior = promotion.approval_plan(l1, "smoke")
    assert prior.expected_panel == "level-progress-l0"
    assert prior.allowed_evaluation_checkpoints == (
        ("qwen-base-rl-l0", "complete"),
    )
    assert prior.entry_baseline_panel == "level-progress-l1"
    assert current.expected_panel != promotion.PANEL_PROGRESS
    assert prior.expected_panel != promotion.PANEL_PROGRESS
