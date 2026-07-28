from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

pytest.importorskip("chz", reason="Tinker is an optional RL dependency")
pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
pytest.importorskip(
    "tinker_cookbook",
    reason="Tinker Cookbook is an optional RL dependency",
)

from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.studies.representation_training_v1 import final_benchmark as subject
from rl.studies.representation_training_v1.protocol import STUDY_ID, load_protocol
from rl.studies.representation_training_v1.store import StageKey, TrainingStore

from .test_evaluation import (
    REPO_ROOT,
    SOURCE_SHA,
    _dataset_binding,
    _FakeEvaluator,
    _FakeRenderer,
    _task,
    _training_receipt,
)


class _SamplingClient:
    def __init__(
        self,
        events: list[str],
        *,
        fail_on_call: int | None = None,
    ) -> None:
        self.events = events
        self.fail_on_call = fail_on_call
        self.seeds: list[int] = []

    async def sample_async(self, **kwargs: Any) -> Any:
        assert kwargs["num_samples"] == 1
        parameters = kwargs["sampling_params"]
        seed = int(parameters.seed)
        self.seeds.append(seed)
        self.events.append(f"sample:{seed}")
        if self.fail_on_call == len(self.seeds):
            raise RuntimeError("synthetic sampling outage")
        assert parameters.max_tokens == subject.MAX_OUTPUT_TOKENS
        assert parameters.temperature == subject.TEMPERATURE
        assert parameters.top_p == subject.TOP_P
        return SimpleNamespace(
            sequences=[
                SimpleNamespace(
                    tokens=[1, 2, seed % 1000 + 3],
                    stop_reason="stop",
                )
            ]
        )


class _Service:
    def __init__(
        self,
        events: list[str],
        client: _SamplingClient,
    ) -> None:
        self.events = events
        self.client = client

    def create_sampling_client(self, *, model_path: str) -> _SamplingClient:
        self.events.append("sampling-client")
        assert model_path == "tinker://fake/sampler"
        return self.client


def _tasks() -> list[Any]:
    return [_task(task_id) for task_id in subject.EXPECTED_TASK_IDS]


def _patch_preflight(
    monkeypatch: pytest.MonkeyPatch,
    *,
    protocol: dict[str, Any],
    tasks: list[Any],
    renderer: _FakeRenderer,
) -> None:
    monkeypatch.setattr(subject, "load_protocol", lambda *_args, **_kwargs: protocol)
    monkeypatch.setattr(
        subject,
        "validate_source_sha",
        lambda *_args: SOURCE_SHA,
    )
    monkeypatch.setattr(
        subject,
        "_dataset_binding",
        lambda *_args: _dataset_binding(protocol),
    )
    monkeypatch.setattr(
        subject.checkpoint_v1,
        "_benchmark_tasks",
        lambda **_kwargs: tasks,
    )
    monkeypatch.setattr(subject, "_renderer", lambda *_args, **_kwargs: renderer)


def _run(
    *,
    protocol: dict[str, Any],
    external: Path,
    receipt_sha: str,
    evaluator: _FakeEvaluator,
    service_factory: Any,
    checkpoint_name: str = "final",
) -> dict[str, Any]:
    return asyncio.run(
        subject.run_final_benchmark(
            repo_root=REPO_ROOT,
            stage_id="qwen-l0-sft",
            wave="complete",
            checkpoint_name=checkpoint_name,
            replicate_id="r0",
            expected_source_sha=SOURCE_SHA,
            expected_wave_receipt_sha256=receipt_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            service_client_factory=service_factory,
            evaluator_factory=lambda: evaluator,
        )
    )


def _store(external: Path) -> subject.FinalBenchmarkStore:
    training = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    key = StageKey(STUDY_ID, "qwen-l0-sft", "r0")
    return subject.FinalBenchmarkStore(
        stage_path=training.stage_path(key),
        wave="complete",
        checkpoint_name="final",
    )


def _validation_context(
    *,
    protocol: dict[str, Any],
    external: Path,
    receipt_sha: str,
    tasks: list[Any],
    renderer: _FakeRenderer,
    evaluator: _FakeEvaluator,
) -> tuple[Any, list[subject.PreparedAttempt]]:
    training = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    binding = subject.checkpoint_v1._load_checkpoint_binding(
        store=training,
        protocol=protocol,
        stage_id="qwen-l0-sft",
        wave="complete",
        checkpoint_name="final",
        replicate_id="r0",
        expected_receipt_sha256=receipt_sha,
        source_git_sha=SOURCE_SHA,
    )
    prepared, _ = subject.checkpoint_v1._preflight_tasks(
        tasks=tasks,
        renderer=renderer,
        evaluator=evaluator,
        context_tokens=65_536,
    )
    panel = subject._task_panel(tasks)
    attempts = subject._attempts(
        prepared=prepared,
        source_git_sha=SOURCE_SHA,
        protocol_sha256=protocol["logical_sha256"],
        dataset_sha256=protocol["dataset"]["logical_release_sha256"],
        task_panel_sha256=panel["logical_sha256"],
        binding=binding,
    )
    return binding, attempts


def _completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    evaluator = _FakeEvaluator(events)
    tasks = _tasks()
    _patch_preflight(
        monkeypatch,
        protocol=protocol,
        tasks=tasks,
        renderer=renderer,
    )
    monkeypatch.setenv("TINKER_API_KEY", "test-key")
    client = _SamplingClient(events)

    def service_factory() -> _Service:
        events.append("service")
        assert events.count("reference") == 8
        return _Service(events, client)

    result = _run(
        protocol=protocol,
        external=external,
        receipt_sha=receipt_sha,
        evaluator=evaluator,
        service_factory=service_factory,
    )
    store = _store(external)
    manifest = store.load_manifest()
    report = store.load_report()
    assert manifest is not None
    assert report is not None
    binding, attempts = _validation_context(
        protocol=protocol,
        external=external,
        receipt_sha=receipt_sha,
        tasks=tasks,
        renderer=renderer,
        evaluator=evaluator,
    )
    return {
        "protocol": protocol,
        "external": external,
        "receipt_sha": receipt_sha,
        "events": events,
        "renderer": renderer,
        "evaluator": evaluator,
        "tasks": tasks,
        "client": client,
        "result": result,
        "store": store,
        "manifest": manifest,
        "report": report,
        "binding": binding,
        "attempts": attempts,
    }


def _write_record(path: Path, record: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _resigned_report(
    payload: dict[str, Any],
) -> dict[str, Any]:
    return subject._record_document(
        record_type="final_benchmark_report",
        key={},
        payload=payload,
    )


def test_v1_panel_and_record_namespaces_remain_unchanged() -> None:
    assert subject.checkpoint_v1.PANELS == (
        subject.checkpoint_v1.PANEL_PROGRESS,
        subject.checkpoint_v1.PANEL_DEPTH_VALIDATION,
        subject.checkpoint_v1.PANEL_INKLING_PROMOTION,
    )
    assert subject.PANEL_FINAL_BENCHMARK_V2 not in subject.checkpoint_v1.PANELS
    assert (
        subject.FINAL_BENCHMARK_RECORD_SCHEMA_VERSION
        != subject.checkpoint_v1.EVALUATION_RECORD_SCHEMA_VERSION
    )


def test_exact_best4_records_and_metrics_bind_full_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    result = completed["result"]
    store = completed["store"]
    manifest = completed["manifest"]["payload"]
    report = completed["report"]["payload"]
    client = completed["client"]
    events = completed["events"]

    assert result["status"] == "complete"
    assert subject.PANEL_FINAL_BENCHMARK_V2 in result["report"]
    assert len(client.seeds) == 32
    assert len(set(client.seeds)) == 32
    assert events[: events.index("service")].count("reference") == 8
    assert events.index("evaluate") > max(
        index for index, event in enumerate(events) if event.startswith("sample:")
    )

    assert len(report["records"]) == 32
    assert report["summary"] == {
        "figure_count": 8,
        "mean_at_1_raw_absolute_scale_iou": 0.75,
        "best_at_4_raw_absolute_scale_iou": 0.75,
        "attempt_count": 32,
        "pure_executable_count": 32,
        "pure_executable_rate": 1.0,
        "cap_hit_count": 0,
        "cap_hit_rate": 0.0,
        "channel_parse_complete_count": 32,
        "channel_parse_complete_rate": 1.0,
        "statuses": {"ok": 32},
        "stop_reasons": {"stop": 32},
        "completion_tokens": {
            "min": 3,
            "max": 3,
            "mean": 3.0,
            "total": 96,
        },
    }
    assert list(report["figures"]) == list(subject.EXPECTED_TASK_IDS)
    assert all(
        value["attempt_count"] == 4
        and value["best_at_4_raw_absolute_scale_iou"] == 0.75
        and value["pure_executable_rate"] == 1.0
        for value in report["figures"].values()
    )

    assert manifest["source_git_sha"] == SOURCE_SHA
    assert manifest["protocol"]["logical_sha256"] == completed["protocol"]["logical_sha256"]
    assert (
        manifest["dataset"]["logical_release_sha256"]
        == completed["protocol"]["dataset"]["logical_release_sha256"]
    )
    assert manifest["task_panel"]["task_ids"] == list(subject.EXPECTED_TASK_IDS)
    assert manifest["prompt"]["contract_version"] == completed["protocol"]["contract_version"]
    assert manifest["model"]["model"] == "Qwen/Qwen3.6-35B-A3B"
    assert manifest["model"]["renderer"] == "qwen3_5"
    assert manifest["sampler"]["checkpoint"]["final"] is True
    assert manifest["sampler"]["training_wave_receipt_record_sha256"] == completed["receipt_sha"]
    assert manifest["sandbox"]["image_id"] == "sha256:" + "4" * 64
    assert manifest["sampling"]["attempts_per_task"] == 4
    assert len(manifest["sampling"]["seeds"]) == 32

    for task_id in subject.EXPECTED_TASK_IDS:
        for attempt_index in range(1, 5):
            sample = store.load_sample(task_id, attempt_index)
            evaluation = store.load_evaluation(task_id, attempt_index)
            assert sample is not None
            assert evaluation is not None
            assert sample["payload"]["response"]["token_ids"]
            assert sample["payload"]["attempt_index"] == attempt_index
            assert evaluation["payload"]["attempt_index"] == attempt_index


def test_partial_sampling_resume_fills_only_missing_attempts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    evaluator = _FakeEvaluator(events)
    tasks = _tasks()
    _patch_preflight(
        monkeypatch,
        protocol=protocol,
        tasks=tasks,
        renderer=renderer,
    )
    monkeypatch.setattr(subject, "SAMPLE_CONCURRENCY", 1)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")
    first_client = _SamplingClient(events, fail_on_call=6)

    with pytest.raises(subject.checkpoint_v1.SamplingInfrastructureFault):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=evaluator,
            service_factory=lambda: _Service(events, first_client),
        )

    store = _store(external)
    samples_before = {
        path: path.read_bytes() for path in store.root.glob("attempts/*/*/sample.json")
    }
    assert 0 < len(samples_before) < 32
    assert not list(store.root.glob("attempts/*/*/evaluation.json"))

    second_client = _SamplingClient(events)
    result = _run(
        protocol=protocol,
        external=external,
        receipt_sha=receipt_sha,
        evaluator=_FakeEvaluator(events),
        service_factory=lambda: _Service(events, second_client),
    )

    assert result["status"] == "complete"
    assert len(second_client.seeds) == 32 - len(samples_before)
    assert len(list(store.root.glob("attempts/*/*/sample.json"))) == 32
    assert len(list(store.root.glob("attempts/*/*/evaluation.json"))) == 32
    assert all(path.read_bytes() == raw for path, raw in samples_before.items())


def test_undecodable_raw_tokens_are_persisted_and_never_executed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)

    def fail_decode(_tokens: list[int]) -> str:
        raise ValueError("synthetic tokenizer drift")

    renderer.tokenizer = SimpleNamespace(decode=fail_decode)
    tasks = _tasks()
    _patch_preflight(
        monkeypatch,
        protocol=protocol,
        tasks=tasks,
        renderer=renderer,
    )
    monkeypatch.setenv("TINKER_API_KEY", "test-key")
    client = _SamplingClient(events)

    with pytest.raises(subject.checkpoint_v1.SamplingInfrastructureFault):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events),
            service_factory=lambda: _Service(events, client),
        )

    store = _store(external)
    samples = list(store.root.glob("attempts/*/*/sample.json"))
    assert len(samples) == 32
    assert not list(store.root.glob("attempts/*/*/evaluation.json"))
    assert "evaluate" not in events
    for path in samples:
        payload = json.loads(path.read_text(encoding="utf-8"))["payload"]
        assert payload["response"]["token_ids"]
        assert payload["response"]["token_decode_complete"] is False
        assert "synthetic tokenizer drift" in payload["response"]["token_decode_error"]

    def forbidden_service() -> Any:
        raise AssertionError("undecodable persisted samples were resampled")

    with pytest.raises(subject.checkpoint_v1.SamplingInfrastructureFault):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events),
            service_factory=forbidden_service,
        )


def test_already_complete_never_touches_tinker_or_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    store = completed["store"]
    before = {path: path.read_bytes() for path in store.root.rglob("*.json")}
    monkeypatch.delenv("TINKER_API_KEY")

    def forbidden_service() -> Any:
        raise AssertionError("already-complete benchmark created a Tinker client")

    result = _run(
        protocol=completed["protocol"],
        external=completed["external"],
        receipt_sha=completed["receipt_sha"],
        evaluator=_FakeEvaluator(completed["events"]),
        service_factory=forbidden_service,
    )

    assert result["status"] == "already_complete"
    assert {path: path.read_bytes() for path in store.root.rglob("*.json")} == before


def test_tampered_raw_response_aborts_before_resume_sampling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    sample_path = completed["store"].root / "attempts" / "F1" / "000001" / "sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    sample["payload"]["response"]["raw_text"] = "tampered"
    _write_record(sample_path, sample)

    def forbidden_service() -> Any:
        raise AssertionError("tampered resume created a Tinker client")

    with pytest.raises(subject.FinalBenchmarkError):
        _run(
            protocol=completed["protocol"],
            external=completed["external"],
            receipt_sha=completed["receipt_sha"],
            evaluator=_FakeEvaluator(completed["events"]),
            service_factory=forbidden_service,
        )


def test_foreign_fifth_attempt_path_is_rejected_before_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    source = completed["store"].root / "attempts" / "F1" / "000001" / "sample.json"
    foreign = completed["store"].root / "attempts" / "F1" / "000005" / "sample.json"
    foreign.parent.mkdir(parents=True)
    foreign.write_bytes(source.read_bytes())

    def forbidden_service() -> Any:
        raise AssertionError("foreign attempt inventory created a Tinker client")

    with pytest.raises(subject.FinalBenchmarkError):
        _run(
            protocol=completed["protocol"],
            external=completed["external"],
            receipt_sha=completed["receipt_sha"],
            evaluator=_FakeEvaluator(completed["events"]),
            service_factory=forbidden_service,
        )


@pytest.mark.parametrize(
    "mutation",
    ("panel", "checkpoint", "source"),
)
def test_resigned_wrong_report_identity_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    payload = copy.deepcopy(completed["report"]["payload"])
    if mutation == "panel":
        payload["panel"] = "progress"
    elif mutation == "checkpoint":
        payload["checkpoint_name"] = "000003"
    else:
        payload["provenance"]["manifest"]["source_git_sha"] = "b" * 40
    tampered = _resigned_report(payload)

    with pytest.raises(subject.FinalBenchmarkError):
        subject.validate_final_benchmark_report(
            tampered,
            manifest_record=completed["manifest"],
            binding=completed["binding"],
            attempts=completed["attempts"],
        )


@pytest.mark.parametrize("mutation", ("incomplete", "duplicate"))
def test_resigned_incomplete_or_duplicate_attempt_rows_are_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    payload = copy.deepcopy(completed["report"]["payload"])
    if mutation == "incomplete":
        payload["records"].pop()
    else:
        payload["records"][-1] = copy.deepcopy(payload["records"][0])
    payload["attempt_records_sha256"] = subject.canonical_json_sha256(payload["records"])
    tampered = _resigned_report(payload)

    with pytest.raises(subject.FinalBenchmarkError):
        subject.validate_final_benchmark_report(
            tampered,
            manifest_record=completed["manifest"],
            binding=completed["binding"],
            attempts=completed["attempts"],
        )


def test_nonfinite_evaluator_metrics_abort_instead_of_becoming_zero() -> None:
    prepared = subject.checkpoint_v1.PreparedTask(
        task=_task(),
        prompt_tokens=100,
        prompt_text_sha256="1" * 64,
        reference_evidence={},
    )
    attempt = subject.PreparedAttempt(
        prepared=prepared,
        attempt_index=1,
        seed=123,
    )
    results = (
        EvaluationResult(
            status=EvaluationStatus.OK,
            attribution=Attribution.MODEL,
            iou=float("nan"),
        ),
        EvaluationResult(
            status=EvaluationStatus.OK,
            attribution=Attribution.MODEL,
            iou=0.5,
            dice=float("inf"),
        ),
        EvaluationResult(
            status=EvaluationStatus.OK,
            attribution=Attribution.MODEL,
            iou=0.5,
            metrics={"diagnostic": float("nan")},
        ),
    )
    for result in results:
        with pytest.raises(subject.checkpoint_v1.EvaluationInfrastructureFault):
            subject._evaluation_payload(
                attempt=attempt,
                result=result,
                sample_record_sha256="2" * 64,
                manifest_record_sha256="3" * 64,
            )


def test_reference_and_evaluator_attribution_are_never_model_zeros() -> None:
    prepared = subject.checkpoint_v1.PreparedTask(
        task=_task(),
        prompt_tokens=100,
        prompt_text_sha256="1" * 64,
        reference_evidence={},
    )
    attempt = subject.PreparedAttempt(prepared=prepared, attempt_index=1, seed=1)
    for attribution, error_type in (
        (Attribution.REFERENCE, subject.checkpoint_v1.ReferencePanelFault),
        (Attribution.EVALUATOR, subject.checkpoint_v1.EvaluationInfrastructureFault),
    ):
        with pytest.raises(error_type):
            subject._evaluation_payload(
                attempt=attempt,
                result=EvaluationResult(
                    status=EvaluationStatus.WORKER_ERROR,
                    attribution=attribution,
                    error="fault",
                ),
                sample_record_sha256="2" * 64,
                manifest_record_sha256="3" * 64,
            )


def test_periodic_checkpoint_cannot_be_called_final_benchmark(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    _patch_preflight(
        monkeypatch,
        protocol=protocol,
        tasks=_tasks(),
        renderer=renderer,
    )

    def forbidden_service() -> Any:
        raise AssertionError("periodic checkpoint created a Tinker client")

    with pytest.raises(subject.checkpoint_v1.CheckpointReceiptError):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events),
            service_factory=forbidden_service,
            checkpoint_name="000003",
        )


def test_reference_preflight_fault_precedes_tinker_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _training_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    renderer = _FakeRenderer(events)
    _patch_preflight(
        monkeypatch,
        protocol=protocol,
        tasks=_tasks(),
        renderer=renderer,
    )

    def forbidden_service() -> Any:
        raise AssertionError("reference fault created a Tinker client")

    with pytest.raises(subject.checkpoint_v1.ReferencePanelFault):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events, broken_reference=True),
            service_factory=forbidden_service,
        )
