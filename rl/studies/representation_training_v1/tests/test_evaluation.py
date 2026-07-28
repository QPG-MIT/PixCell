from __future__ import annotations

import asyncio
import hashlib
import io
from collections import Counter
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

from tinker_cookbook.renderers import (
    Message,
    ParseTermination,
    TextPart,
)

from rl.common.contracts import ModelObservation, VerifierReference
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.evaluation.tasks import EvaluationTask
from rl.studies.representation_training_v1 import evaluation as subject
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    load_protocol,
)
from rl.studies.representation_training_v1.store import (
    StageKey,
    TrainingStore,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_SHA = "a" * 40


def _image_bytes() -> bytes:
    image = Image.new("L", (8, 8), 255)
    for x in range(2, 6):
        for y in range(2, 6):
            image.putpixel((x, y), 0)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _task(task_id: str = "F1", *, level: str = "BENCHMARK") -> EvaluationTask:
    image = _image_bytes()
    digest = hashlib.sha256(image).hexdigest()
    return EvaluationTask(
        task_id=task_id,
        level=level,
        representation_id=f"representation-{task_id.lower()}",
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


class _FakeRenderer:
    def __init__(self, events: list[str]) -> None:
        self.events = events
        self.tokenizer = SimpleNamespace(decode=lambda tokens: "raw:" + repr(tokens))

    def build_generation_prompt(self, messages: list[Any]) -> Any:
        self.events.append("prompt")
        assert len(messages) == 1
        text = messages[0]["content"][1]["text"]
        assert "Phase-A Device Input" in text
        assert "target_image" not in text
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


class _FakeEvaluator:
    def __init__(
        self,
        events: list[str],
        *,
        result: EvaluationResult | None = None,
        broken_reference: bool = False,
    ) -> None:
        self.events = events
        self.result = result or EvaluationResult(
            status=EvaluationStatus.OK,
            attribution=Attribution.MODEL,
            iou=0.75,
            dice=0.8,
            metrics={
                "render_sha256": "1" * 64,
                "reference_sha256": "2" * 64,
            },
        )
        self.broken_reference = broken_reference
        self.execution_boundary = SimpleNamespace(
            runtime_path=Path("/usr/bin/false"),
            daemon_endpoint="unix:///private/fake.sock",
            image_ref="pixcell-evaluator@sha256:" + "3" * 64,
            image_id="sha256:" + "4" * 64,
            workspace_root=Path("/private/fake-workspace"),
        )

    def validate_reference(self, reference: VerifierReference) -> dict[str, Any]:
        self.events.append("reference")
        if self.broken_reference:
            raise ValueError("broken reference")
        return {
            "target_image_sha256": reference.target_image_sha256,
            "image_size_px": [8, 8],
            "bbox": [2, 2, 6, 6],
            "scale_px_per_um": [2.0, 2.0],
        }

    def evaluate_batch(
        self,
        requests: list[tuple[VerifierReference, str]],
    ) -> list[EvaluationResult]:
        self.events.append("evaluate")
        return [self.result for _ in requests]

    def close(self) -> None:
        self.events.append("close")


class _FakeSamplingClient:
    async def sample_async(self, **kwargs: Any) -> Any:
        assert kwargs["num_samples"] == 1
        parameters = kwargs["sampling_params"]
        assert parameters.max_tokens == subject.MAX_OUTPUT_TOKENS
        assert parameters.temperature == subject.TEMPERATURE
        assert parameters.top_p == subject.TOP_P
        return SimpleNamespace(
            sequences=[
                SimpleNamespace(
                    tokens=[1, 2, 3],
                    stop_reason="stop",
                )
            ]
        )


class _FakeService:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    def create_sampling_client(self, *, model_path: str) -> _FakeSamplingClient:
        self.events.append("sampling-client")
        assert model_path.startswith("tinker://")
        return _FakeSamplingClient()


def _training_receipt(
    tmp_path: Path,
    *,
    protocol: dict[str, Any],
    stage_id: str = "qwen-l0-sft",
    wave: str = "complete",
) -> tuple[Path, str]:
    external = tmp_path / "external"
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    key = StageKey(STUDY_ID, stage_id, "r0")
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            {
                "source_git_sha": SOURCE_SHA,
                "protocol_logical_sha256": protocol["logical_sha256"],
                "contract_version": protocol["contract_version"],
                "dataset": {
                    "logical_release_sha256": protocol["dataset"][
                        "logical_release_sha256"
                    ]
                },
                "stage": {
                    "stage_id": stage_id,
                    "model_key": protocol["stages"][stage_id]["model"],
                },
            },
        )
        stage = protocol["stages"][stage_id]
        max_steps = int(stage["waves"][wave]["max_steps"])
        entries = (
            [
                {
                    "name": f"{max_steps:06d}",
                    "batch": max_steps,
                    "epoch": None,
                    "final": True,
                    "state_path": f"tinker://fake/state-{max_steps:06d}",
                    "sampler_path": f"tinker://fake/sampler-{max_steps:06d}",
                    "role": "terminal",
                    "training_progress_fraction": 1.0,
                }
            ]
            if stage["kind"] == "rl"
            else [
                {
                    "name": "000003",
                    "batch": 3,
                    "epoch": None,
                    "final": False,
                    "state_path": "tinker://fake/state-000003",
                    "sampler_path": "tinker://fake/sampler-000003",
                    "role": "periodic",
                    "training_progress_fraction": 3 / 11,
                },
                {
                    "name": "final",
                    "batch": 11,
                    "epoch": 1,
                    "final": True,
                    "state_path": "tinker://fake/state",
                    "sampler_path": "tinker://fake/sampler",
                    "role": "terminal",
                    "training_progress_fraction": 1.0,
                },
            ]
        )
        terminal = {
            key: entries[-1][key]
            for key in (
                "name",
                "batch",
                "epoch",
                "final",
                "state_path",
                "sampler_path",
            )
        }
        receipt = store.write_wave_receipt(
            key,
            wave=wave,
            payload={
                "stage_id": stage_id,
                "wave": wave,
                "run_manifest_record_sha256": manifest.record_sha256,
                "checkpoint": terminal,
                "checkpoint_inventory": {
                    "count": len(entries),
                    "entries": entries,
                    "logical_sha256": subject._canonical_sha256(entries),
                },
            },
        )
    return external, receipt.record_sha256


def _dataset_binding(protocol: dict[str, Any]) -> dict[str, Any]:
    return {
        "logical_release_sha256": protocol["dataset"][
            "logical_release_sha256"
        ],
        "freeze_file_sha256": "5" * 64,
        "train_rows": protocol["dataset"]["train_rows"],
        "validation_rows": protocol["dataset"]["validation_rows"],
        "parquet_shards": {"depth-v1/data/validation-00000.parquet": "6" * 64},
        "reference_artifacts_sha256": "7" * 64,
        "reference_artifact_count": 1,
    }


def test_exact_panel_inventory_and_label_free_projection() -> None:
    protocol = load_protocol(REPO_ROOT)
    progress = subject.build_panel_tasks(
        repo_root=REPO_ROOT,
        protocol=protocol,
        panel=subject.PANEL_PROGRESS,
    )
    depth = subject.build_panel_tasks(
        repo_root=REPO_ROOT,
        protocol=protocol,
        panel=subject.PANEL_DEPTH_VALIDATION,
    )
    promotion = subject.build_panel_tasks(
        repo_root=REPO_ROOT,
        protocol=protocol,
        panel=subject.PANEL_INKLING_PROMOTION,
    )

    assert [task.task_id for task in progress] == [
        "F1",
        "F2",
        "F3",
        "F4",
        "F5",
        "F6",
        "F7",
        "F8",
    ]
    assert len(depth) == 1092
    assert len({task.representation_id for task in depth}) == 546
    assert len(promotion) == 68
    assert Counter(task.level for task in promotion) == {
        "BENCHMARK": 8,
        "L0": 6,
        "L1": 6,
        "L2": 6,
        "L3": 6,
        "L4": 36,
    }
    assert not any(hasattr(task, "label") or hasattr(task, "code") for task in depth)
    repeated = subject.build_panel_tasks(
        repo_root=REPO_ROOT,
        protocol=protocol,
        panel=subject.PANEL_INKLING_PROMOTION,
    )
    assert [task.task_id for task in repeated] == [
        task.task_id for task in promotion
    ]


def test_store_is_create_only_and_resumable(tmp_path: Path) -> None:
    stage = tmp_path / "stage"
    stage.mkdir()
    store = subject.CheckpointEvaluationStore(
        stage_path=stage,
        wave="complete",
        checkpoint_name="final",
        panel=subject.PANEL_PROGRESS,
    )
    payload = {"source_git_sha": SOURCE_SHA}
    first = store.create_or_verify_manifest(payload)
    second = store.create_or_verify_manifest(payload)

    assert first == second
    periodic = subject.CheckpointEvaluationStore(
        stage_path=stage,
        wave="complete",
        checkpoint_name="000003",
        panel=subject.PANEL_PROGRESS,
    )
    assert periodic.root != store.root
    assert periodic.create_or_verify_manifest(payload) == first
    with pytest.raises(subject.ImmutableEvaluationRecordError):
        store.create_or_verify_manifest({"source_git_sha": "b" * 40})


def test_checkpoint_can_only_load_from_the_exact_wave_receipt(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)

    binding = subject._load_checkpoint_binding(
        store=store,
        protocol=protocol,
        stage_id="qwen-l0-sft",
        wave="complete",
        checkpoint_name="000003",
        replicate_id="r0",
        expected_receipt_sha256=receipt_sha,
        source_git_sha=SOURCE_SHA,
    )
    assert binding.checkpoint_name == "000003"
    assert binding.sampler_path == "tinker://fake/sampler-000003"
    assert binding.checkpoint["training_progress_fraction"] == 3 / 11
    assert binding.wave_receipt.record_sha256 == receipt_sha
    final_binding = subject._load_checkpoint_binding(
        store=store,
        protocol=protocol,
        stage_id="qwen-l0-sft",
        wave="complete",
        checkpoint_name="final",
        replicate_id="r0",
        expected_receipt_sha256=receipt_sha,
        source_git_sha=SOURCE_SHA,
    )
    assert subject._sample_seed(
        protocol_sha256=protocol["logical_sha256"],
        binding=binding,
        panel=subject.PANEL_PROGRESS,
        task_id="F1",
    ) != subject._sample_seed(
        protocol_sha256=protocol["logical_sha256"],
        binding=final_binding,
        panel=subject.PANEL_PROGRESS,
        task_id="F1",
    )

    with pytest.raises(subject.CheckpointReceiptError):
        subject._load_checkpoint_binding(
            store=store,
            protocol=protocol,
            stage_id="qwen-l0-sft",
            wave="complete",
            checkpoint_name="000003",
            replicate_id="r0",
            expected_receipt_sha256="f" * 64,
            source_git_sha=SOURCE_SHA,
        )
    with pytest.raises(subject.CheckpointReceiptError):
        subject._load_checkpoint_binding(
            store=store,
            protocol=protocol,
            stage_id="qwen-l0-sft",
            wave="complete",
            checkpoint_name="user-supplied-uri-alias",
            replicate_id="r0",
            expected_receipt_sha256=receipt_sha,
            source_git_sha=SOURCE_SHA,
        )


def test_rl_wave_uses_its_unique_numeric_ceiling_checkpoint(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(
        tmp_path,
        protocol=protocol,
        stage_id="inkling-l4-rl",
        wave="smoke",
    )
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    binding = subject._load_checkpoint_binding(
        store=store,
        protocol=protocol,
        stage_id="inkling-l4-rl",
        wave="smoke",
        checkpoint_name="000001",
        replicate_id="r0",
        expected_receipt_sha256=receipt_sha,
        source_git_sha=SOURCE_SHA,
    )
    assert binding.checkpoint_name == "000001"
    assert binding.checkpoint["role"] == "terminal"
    assert binding.checkpoint["training_progress_fraction"] == 1.0

    with pytest.raises(subject.CheckpointReceiptError):
        subject._load_checkpoint_binding(
            store=store,
            protocol=protocol,
            stage_id="inkling-l4-rl",
            wave="smoke",
            checkpoint_name="final",
            replicate_id="r0",
            expected_receipt_sha256=receipt_sha,
            source_git_sha=SOURCE_SHA,
        )


def test_model_fault_is_zero_and_infrastructure_fault_aborts() -> None:
    task = _task()
    model_failure = EvaluationResult(
        status=EvaluationStatus.SYNTAX_ERROR,
        attribution=Attribution.MODEL,
        error="invalid syntax",
    )
    payload = subject._evaluation_payload(
        task=task,
        result=model_failure,
        sample_record_sha256="1" * 64,
        manifest_record_sha256="2" * 64,
    )
    assert payload["raw_absolute_scale_iou"] == 0.0
    assert payload["pure_executable"] is False

    for attribution, error_type in (
        (Attribution.REFERENCE, subject.ReferencePanelFault),
        (Attribution.EVALUATOR, subject.EvaluationInfrastructureFault),
    ):
        with pytest.raises(error_type):
            subject._evaluation_payload(
                task=task,
                result=EvaluationResult(
                    status=EvaluationStatus.WORKER_ERROR,
                    attribution=attribution,
                    error="fault",
                ),
                sample_record_sha256="1" * 64,
                manifest_record_sha256="2" * 64,
            )


def test_all_prompt_and_reference_checks_precede_service_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    evaluator = _FakeEvaluator(events)
    task = _task()

    monkeypatch.setattr(subject, "load_protocol", lambda *_args, **_kwargs: protocol)
    monkeypatch.setattr(subject, "validate_source_sha", lambda *_args: SOURCE_SHA)
    monkeypatch.setattr(
        subject,
        "_dataset_binding",
        lambda *_args: _dataset_binding(protocol),
    )
    monkeypatch.setattr(subject, "build_panel_tasks", lambda **_kwargs: [task])
    monkeypatch.setattr(subject, "_renderer", lambda *_args, **_kwargs: renderer)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")

    def service_factory() -> _FakeService:
        events.append("service")
        assert "prompt" in events
        assert "reference" in events
        return _FakeService(events)

    result = asyncio.run(
        subject.run_checkpoint_evaluation(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave="complete",
            checkpoint_name="final",
            replicate_id="r0",
            panel=subject.PANEL_PROGRESS,
            expected_source_sha=SOURCE_SHA,
            expected_wave_receipt_sha256=receipt_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            service_client_factory=service_factory,
            evaluator_factory=lambda: evaluator,
        )
    )

    assert result["status"] == "complete"
    assert events.index("prompt") < events.index("service")
    assert events.index("reference") < events.index("service")
    assert result["summary"]["mean_raw_absolute_scale_iou"] == 0.75
    assert "/complete/final/progress/report.json" in result["report"]
    report = subject.CheckpointEvaluationStore(
        stage_path=(
            TrainingStore(repo_root=REPO_ROOT, external_root=external).stage_path(
                StageKey(STUDY_ID, "qwen-l0-sft", "r0")
            )
        ),
        wave="complete",
        checkpoint_name="final",
        panel=subject.PANEL_PROGRESS,
    ).load_report()
    assert report is not None
    assert report["payload"]["checkpoint_name"] == "final"
    assert (
        report["payload"]["provenance"]["sampler"]["checkpoint"]
        ["training_progress_fraction"]
        == 1.0
    )
    assert set(report["payload"]["provenance"]["dataset"]) == {
        "repo_id",
        "revision",
        "configuration",
        "split",
        "logical_release_sha256",
        "freeze_file_sha256",
        "parquet_shards",
    }


def test_reference_failure_cannot_create_a_service_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    evaluator = _FakeEvaluator(events, broken_reference=True)

    monkeypatch.setattr(subject, "load_protocol", lambda *_args, **_kwargs: protocol)
    monkeypatch.setattr(subject, "validate_source_sha", lambda *_args: SOURCE_SHA)
    monkeypatch.setattr(
        subject,
        "_dataset_binding",
        lambda *_args: _dataset_binding(protocol),
    )
    monkeypatch.setattr(subject, "build_panel_tasks", lambda **_kwargs: [_task()])
    monkeypatch.setattr(subject, "_renderer", lambda *_args, **_kwargs: renderer)

    def forbidden_service() -> Any:
        raise AssertionError("ServiceClient was created before reference preflight")

    with pytest.raises(subject.ReferencePanelFault):
        asyncio.run(
            subject.run_checkpoint_evaluation(
                repo_root=REPO_ROOT,
                stage_id="qwen-l0-sft",
                wave="complete",
                checkpoint_name="final",
                replicate_id="r0",
                panel=subject.PANEL_PROGRESS,
                expected_source_sha=SOURCE_SHA,
                expected_wave_receipt_sha256=receipt_sha,
                external_root=external,
                confirmation=protocol["launch"]["confirmation_token"],
                service_client_factory=forbidden_service,
                evaluator_factory=lambda: evaluator,
            )
        )


def test_sample_survives_evaluator_fault_and_resume_does_not_resample(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    task = _task()
    events: list[str] = []
    renderer = _FakeRenderer(events)
    bad_evaluator = _FakeEvaluator(
        events,
        result=EvaluationResult(
            status=EvaluationStatus.WORKER_ERROR,
            attribution=Attribution.EVALUATOR,
            error="worker failed",
            retryable=True,
        ),
    )

    monkeypatch.setattr(subject, "load_protocol", lambda *_args, **_kwargs: protocol)
    monkeypatch.setattr(subject, "validate_source_sha", lambda *_args: SOURCE_SHA)
    monkeypatch.setattr(
        subject,
        "_dataset_binding",
        lambda *_args: _dataset_binding(protocol),
    )
    monkeypatch.setattr(subject, "build_panel_tasks", lambda **_kwargs: [task])
    monkeypatch.setattr(subject, "_renderer", lambda *_args, **_kwargs: renderer)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")

    with pytest.raises(subject.EvaluationInfrastructureFault):
        asyncio.run(
            subject.run_checkpoint_evaluation(
                repo_root=REPO_ROOT,
                stage_id="qwen-l0-sft",
                wave="complete",
                checkpoint_name="final",
                replicate_id="r0",
                panel=subject.PANEL_PROGRESS,
                expected_source_sha=SOURCE_SHA,
                expected_wave_receipt_sha256=receipt_sha,
                external_root=external,
                confirmation=protocol["launch"]["confirmation_token"],
                service_client_factory=lambda: _FakeService(events),
                evaluator_factory=lambda: bad_evaluator,
            )
        )

    training_store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
    record_store = subject.CheckpointEvaluationStore(
        stage_path=training_store.stage_path(key),
        wave="complete",
        checkpoint_name="final",
        panel=subject.PANEL_PROGRESS,
    )
    assert record_store.load_sample(task.task_id) is not None
    assert record_store.load_evaluation(task.task_id) is None

    good_evaluator = _FakeEvaluator(events)

    def forbidden_service() -> Any:
        raise AssertionError("resume attempted to resample an immutable completion")

    monkeypatch.delenv("TINKER_API_KEY")
    result = asyncio.run(
        subject.run_checkpoint_evaluation(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave="complete",
            checkpoint_name="final",
            replicate_id="r0",
            panel=subject.PANEL_PROGRESS,
            expected_source_sha=SOURCE_SHA,
            expected_wave_receipt_sha256=receipt_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            service_client_factory=forbidden_service,
            evaluator_factory=lambda: good_evaluator,
        )
    )
    assert result["status"] == "complete"
    assert record_store.load_evaluation(task.task_id) is not None
