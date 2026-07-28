from __future__ import annotations

import asyncio
import copy
import json
from collections.abc import Mapping
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
from rl.common.prompt import prompt_asset_hashes
from rl.studies.representation_training_v1 import renderer_diagnostic as subject
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    file_sha256,
    load_protocol,
    protocol_path,
    stage_spec,
)
from rl.studies.representation_training_v1.schedule import stage_tasks
from rl.studies.representation_training_v1.store import StageKey, TrainingStore

from .test_evaluation import (
    REPO_ROOT,
    _dataset_binding,
    _FakeEvaluator,
    _FakeRenderer,
    _task,
)


CURRENT_SOURCE_SHA = "c" * 40
EXPECTED_TEST_SEEDS = [
    580691976,
    582932630,
    447411723,
    1400409945,
    2147267335,
    1036237029,
    109803042,
    198943424,
    209601344,
    4208007,
    1771872124,
    1021084370,
    1432891407,
    1510509623,
    314385360,
    1742975857,
    1921349594,
    1042955959,
    286561693,
    142478594,
    1356546637,
    1516237462,
    1838024915,
    1030955817,
    1771488732,
    1591268683,
    1178371342,
    1648858767,
    1862439974,
    1103201425,
    316842612,
    314847471,
]


def _tasks() -> list[Any]:
    return [_task(f"F{index}") for index in range(1, 9)]


def _prefix_audit() -> dict[str, Any]:
    renderers = {}
    for renderer, compatible in (
        ("qwen3_5_disable_thinking", True),
        ("qwen3_5", False),
    ):
        renderers[renderer] = {
            "rows": 3468,
            "compatible_rows": 3468 if compatible else 0,
            "incompatible_rows": 0 if compatible else 3468,
            "compatible_with_sft_supervised_prefix": compatible,
            "expected_compatible_claim": compatible,
            "claim_verified": True,
            "comparison_scope": "through first positive-loss token",
            "diagnosis": renderer,
            "evidence_sha256": "8" * 64,
            "example": {"renderer": renderer},
        }
    return {
        "schema_version": "pixcell-qwen-sft-prefix-audit-v1",
        "rows": 3468,
        "training_renderer": "qwen3_5",
        "train_on_what": "LAST_ASSISTANT_MESSAGE",
        "target_policy": "program_and_end_token_only",
        "source_set_sha256": "9" * 64,
        "renderers": renderers,
    }


def _mixed_receipt(
    tmp_path: Path,
    *,
    protocol: dict[str, Any],
) -> tuple[Path, str]:
    external = tmp_path / "external"
    store = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    key = StageKey(
        STUDY_ID,
        subject.PRODUCER_STAGE_ID,
        subject.PRODUCER_REPLICATE_ID,
    )
    checkpoints = (
        ("000014", 14, False, "periodic", 14 / 55),
        ("000028", 28, False, "periodic", 28 / 55),
        ("000042", 42, False, "periodic", 42 / 55),
        ("final", 55, True, "terminal", 1.0),
    )
    entries = [
        {
            "name": name,
            "batch": batch,
            "epoch": 1 if final else 0,
            "final": final,
            "state_path": f"tinker://unit/state/{name}",
            "sampler_path": f"tinker://unit/sampler/{name}",
            "role": role,
            "training_progress_fraction": progress,
        }
        for name, batch, final, role, progress in checkpoints
    ]
    terminal = {
        field: entries[-1][field]
        for field in (
            "name",
            "batch",
            "epoch",
            "final",
            "state_path",
            "sampler_path",
        )
    }
    with store.acquire_stage_lock(key):
        manifest = store.create_or_verify_manifest(
            key,
            {
                "source_git_sha": subject.PRODUCER_SOURCE_GIT_SHA,
                "protocol_logical_sha256": protocol["logical_sha256"],
                "protocol_file_sha256": file_sha256(protocol_path(REPO_ROOT)),
                "contract_version": protocol["contract_version"],
                "prompt_assets": prompt_asset_hashes(),
                "dataset": {
                    "logical_release_sha256": protocol["dataset"]["logical_release_sha256"]
                },
                "runtime": {"pinned": True},
                "sandbox": {"image_id": "sha256:" + "4" * 64},
                "stage": {
                    "stage_id": subject.PRODUCER_STAGE_ID,
                    "kind": "sft",
                    "model_key": "qwen",
                    "recipe_key": "qwen_sft",
                },
                "model": protocol["models"]["qwen"],
                "recipe": protocol["recipes"]["qwen_sft"],
            },
        )
        receipt = store.write_wave_receipt(
            key,
            wave=subject.PRODUCER_WAVE,
            payload={
                "stage_id": subject.PRODUCER_STAGE_ID,
                "wave": subject.PRODUCER_WAVE,
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


class _Renderer(_FakeRenderer):
    def __init__(self, events: list[str], name: str) -> None:
        super().__init__(events)
        self.name = name

    def build_generation_prompt(self, messages: list[Any]) -> Any:
        self.events.append(f"prompt:{self.name}")
        assert len(messages) == 1
        return SimpleNamespace(length=102 if self.name == "qwen3_5_disable_thinking" else 100)


class _SharedSamplingState:
    def __init__(
        self,
        events: list[str],
        *,
        fail_on_call: int | None = None,
    ) -> None:
        self.events = events
        self.fail_on_call = fail_on_call
        self.calls = 0
        self.seeds: list[int] = []


class _SamplingClient:
    def __init__(self, state: _SharedSamplingState, path: str) -> None:
        self.state = state
        self.path = path

    async def sample_async(self, **kwargs: Any) -> Any:
        self.state.calls += 1
        if self.state.fail_on_call == self.state.calls:
            raise RuntimeError("synthetic transport fault")
        parameters = kwargs["sampling_params"]
        assert kwargs["num_samples"] == 1
        assert parameters.max_tokens == subject.MAX_OUTPUT_TOKENS
        assert parameters.temperature == subject.TEMPERATURE
        assert parameters.top_p == subject.TOP_P
        self.state.seeds.append(parameters.seed)
        self.state.events.append(f"sample:{self.path}:{parameters.seed}")
        return SimpleNamespace(sequences=[SimpleNamespace(tokens=[1, 2, 3], stop_reason="stop")])


class _Service:
    def __init__(self, state: _SharedSamplingState) -> None:
        self.state = state
        self.paths: list[str] = []

    def create_sampling_client(self, *, model_path: str) -> _SamplingClient:
        self.paths.append(model_path)
        self.state.events.append(f"client:{model_path}")
        return _SamplingClient(self.state, model_path)


def _patch_preflight(
    monkeypatch: pytest.MonkeyPatch,
    *,
    protocol: dict[str, Any],
    events: list[str],
) -> None:
    monkeypatch.setattr(
        subject,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )

    def source_check(_root: Path, expected: str) -> str:
        events.append(f"source:{expected}")
        assert expected == CURRENT_SOURCE_SHA
        return expected

    monkeypatch.setattr(subject, "validate_source_sha", source_check)
    monkeypatch.setattr(
        subject,
        "_source_provenance",
        lambda **_kwargs: {
            "producer_source_git_sha": subject.PRODUCER_SOURCE_GIT_SHA,
            "evaluator_source_git_sha": CURRENT_SOURCE_SHA,
            "git_relationship": {"ancestor_distance": 1},
            "task_contract_files": {},
            "task_contract_files_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        subject,
        "_dataset_binding",
        lambda *_args: _dataset_binding(protocol),
    )
    monkeypatch.setattr(
        subject,
        "_runtime_binding",
        lambda *_args: {"stack": "pinned"},
    )
    monkeypatch.setattr(
        subject.checkpoint_v1,
        "_benchmark_tasks",
        lambda **_kwargs: _tasks(),
    )
    monkeypatch.setattr(
        subject,
        "_sft_prefix_audit",
        lambda **_kwargs: events.append("prefix-audit") or _prefix_audit(),
    )
    renderers: dict[str, _Renderer] = {}

    def renderer(_model: str, name: str, **_kwargs: Any) -> _Renderer:
        return renderers.setdefault(name, _Renderer(events, name))

    monkeypatch.setattr(subject, "_renderer", renderer)


def _store(external: Path) -> subject.RendererDiagnosticStore:
    training = TrainingStore(repo_root=REPO_ROOT, external_root=external)
    key = StageKey(
        STUDY_ID,
        subject.PRODUCER_STAGE_ID,
        subject.PRODUCER_REPLICATE_ID,
    )
    return subject.RendererDiagnosticStore(stage_path=training.stage_path(key))


def _run(
    *,
    protocol: dict[str, Any],
    external: Path,
    receipt_sha: str,
    evaluator: _FakeEvaluator,
    service_factory: Any,
) -> dict[str, Any]:
    return asyncio.run(
        subject.run_renderer_diagnostic(
            repo_root=REPO_ROOT,
            evaluator_source_git_sha=CURRENT_SOURCE_SHA,
            producer_wave_receipt_record_sha256=receipt_sha,
            external_root=external,
            confirmation=protocol["launch"]["confirmation_token"],
            evaluator_factory=lambda: evaluator,
            service_client_factory=service_factory,
        )
    )


def _completed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _mixed_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    _patch_preflight(monkeypatch, protocol=protocol, events=events)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")
    evaluator = _FakeEvaluator(events)
    state = _SharedSamplingState(events)
    service = _Service(state)

    def service_factory() -> _Service:
        events.append("service")
        assert events.count(f"source:{CURRENT_SOURCE_SHA}") == 2
        assert "prefix-audit" in events
        assert events.count("reference") == 32
        return service

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
    return {
        "protocol": protocol,
        "external": external,
        "receipt_sha": receipt_sha,
        "events": events,
        "evaluator": evaluator,
        "state": state,
        "service": service,
        "result": result,
        "store": store,
        "manifest": manifest,
        "report": report,
    }


def _write_record(path: Path, value: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_matrix_and_cli_have_no_model_renderer_or_checkpoint_override() -> None:
    assert [spec.as_dict() for spec in subject.ARM_SPECS] == [
        {
            "arm_id": "final-no-thinking",
            "checkpoint_name": "final",
            "renderer": "qwen3_5_disable_thinking",
            "expected_sft_prefix_compatible": True,
        },
        {
            "arm_id": "step-14-thinking",
            "checkpoint_name": "000014",
            "renderer": "qwen3_5",
            "expected_sft_prefix_compatible": False,
        },
        {
            "arm_id": "step-28-thinking",
            "checkpoint_name": "000028",
            "renderer": "qwen3_5",
            "expected_sft_prefix_compatible": False,
        },
        {
            "arm_id": "step-42-thinking",
            "checkpoint_name": "000042",
            "renderer": "qwen3_5",
            "expected_sft_prefix_compatible": False,
        },
    ]
    assert subject.PRODUCER_SOURCE_GIT_SHA == ("bb80dbe666c7313f9a9f3bdb53765c35dfdeceab")
    actions = {action.dest for action in subject.parser()._actions if action.dest}
    assert not actions & {
        "model",
        "renderer",
        "checkpoint",
        "checkpoint_name",
        "stage",
        "wave",
        "replicate",
        "max_tokens",
        "temperature",
        "top_p",
    }


def test_real_renderer_prefix_audit_diagnoses_exact_mismatch() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, subject.PRODUCER_STAGE_ID)
    anchor = stage_tasks(REPO_ROOT / "dataset", stage)[0]
    audit = subject._sft_prefix_audit(
        dataset_root=REPO_ROOT / "dataset",
        protocol=protocol,
        tasks=[anchor],
    )

    disabled = audit["renderers"]["qwen3_5_disable_thinking"]
    canonical = audit["renderers"]["qwen3_5"]
    assert disabled["compatible_with_sft_supervised_prefix"] is True
    assert disabled["compatible_rows"] == 1
    assert disabled["example"]["prefix_equal"] is True
    assert disabled["example"]["through_first_positive_equal"] is True
    assert canonical["compatible_with_sft_supervised_prefix"] is False
    assert canonical["incompatible_rows"] == 1
    assert canonical["example"]["prefix_equal"] is False
    assert canonical["example"]["through_first_positive_equal"] is False
    assert "leaves <think> open" in canonical["diagnosis"]


def test_exact_matrix_records_full_provenance_and_is_non_promotable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    result = completed["result"]
    manifest = completed["manifest"]["payload"]
    report = completed["report"]["payload"]
    store = completed["store"]

    assert result["status"] == "complete"
    assert result["not_canonical_evidence"] is True
    assert "/diagnostics/" in result["report"]
    assert "/evaluations/" not in result["report"]
    assert completed["state"].calls == 32
    assert len(completed["state"].seeds) == 32
    assert len(set(completed["state"].seeds)) == 32
    assert completed["service"].paths == [
        "tinker://unit/sampler/final",
        "tinker://unit/sampler/000014",
        "tinker://unit/sampler/000028",
        "tinker://unit/sampler/000042",
    ]
    assert manifest["not_canonical_evidence"] is True
    assert manifest["promotion_eligibility"] == {
        "eligible": False,
        "policy": "diagnostic-only-never-promotion-evidence",
    }
    assert manifest["source"]["producer_source_git_sha"] == (subject.PRODUCER_SOURCE_GIT_SHA)
    assert manifest["source"]["evaluator_source_git_sha"] == CURRENT_SOURCE_SHA
    assert (
        manifest["producer_training"]["wave_receipt"]["record_sha256"] == completed["receipt_sha"]
    )
    assert list(
        manifest["producer_training"]["checkpoint_inventory"]["entries"][index]["name"]
        for index in range(4)
    ) == list(subject.EXPECTED_CHECKPOINT_NAMES)
    assert manifest["sampling"]["total_samples"] == 32
    assert len(manifest["sampling"]["seeds"]) == 32
    assert [row["seed"] for row in manifest["sampling"]["seeds"]] == EXPECTED_TEST_SEEDS
    assert report["not_canonical_evidence"] is True
    assert len(report["records"]) == 32
    assert set(report["summaries"]) == {spec.arm_id for spec in subject.ARM_SPECS}
    assert all(
        summary["mean_raw_absolute_scale_iou"] == 0.75 and summary["pure_executable"] == 8
        for summary in report["summaries"].values()
    )
    for spec in subject.ARM_SPECS:
        for task_id in subject.EXPECTED_TASK_IDS:
            sample = store.load_sample(spec.arm_id, task_id)
            evaluation = store.load_evaluation(spec.arm_id, task_id)
            assert sample is not None
            assert evaluation is not None
            response = sample["payload"]["response"]
            assert response["token_ids"] == [1, 2, 3]
            assert response["token_ids_sha256"] == subject._canonical_sha256([1, 2, 3])
            assert response["answer_text"] == "print('candidate')"
            assert response["reasoning_text"] == ""
            assert response["extracted_program"] == "print('candidate')"
            assert response["channel_parse_status"] == "clean"
            assert evaluation["payload"]["not_canonical_evidence"] is True
            assert (
                evaluation["payload"]["extracted_program_sha256"]
                == response["extracted_program_sha256"]
            )

    with pytest.raises(subject.checkpoint_v1.CheckpointEvaluationError):
        subject.checkpoint_v1._validate_record(
            completed["report"],
            record_type="checkpoint_report",
            key={},
        )


def test_already_complete_is_byte_stable_and_creates_no_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    store = completed["store"]
    before = {path: path.read_bytes() for path in store.root.rglob("*.json")}
    monkeypatch.delenv("TINKER_API_KEY")

    def forbidden_service() -> Any:
        raise AssertionError("already-complete diagnostic created a client")

    result = _run(
        protocol=completed["protocol"],
        external=completed["external"],
        receipt_sha=completed["receipt_sha"],
        evaluator=_FakeEvaluator(completed["events"]),
        service_factory=forbidden_service,
    )
    assert result["status"] == "already_complete"
    assert {path: path.read_bytes() for path in store.root.rglob("*.json")} == before


def test_partial_sampling_resume_only_fills_missing_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _mixed_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    _patch_preflight(monkeypatch, protocol=protocol, events=events)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")
    monkeypatch.setattr(subject, "SAMPLE_CONCURRENCY", 1)
    first_state = _SharedSamplingState(events, fail_on_call=7)

    with pytest.raises(subject.checkpoint_v1.SamplingInfrastructureFault):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events),
            service_factory=lambda: _Service(first_state),
        )

    store = _store(external)
    before = {path: path.read_bytes() for path in store.root.glob("arms/*/tasks/*/sample.json")}
    assert 0 < len(before) < 32
    assert not list(store.root.glob("arms/*/tasks/*/evaluation.json"))

    second_state = _SharedSamplingState(events)
    result = _run(
        protocol=protocol,
        external=external,
        receipt_sha=receipt_sha,
        evaluator=_FakeEvaluator(events),
        service_factory=lambda: _Service(second_state),
    )
    assert result["status"] == "complete"
    assert second_state.calls == 32 - len(before)
    assert len(list(store.root.glob("arms/*/tasks/*/sample.json"))) == 32
    assert all(path.read_bytes() == raw for path, raw in before.items())


@pytest.mark.parametrize("mutation", ("raw", "program", "foreign", "symlink"))
def test_tampering_and_foreign_inventory_fail_before_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    store = completed["store"]
    sample_path = store.root / "arms" / "final-no-thinking" / "tasks" / "F1" / "sample.json"
    if mutation in {"raw", "program"}:
        sample = json.loads(sample_path.read_text(encoding="utf-8"))
        field = "raw_text" if mutation == "raw" else "extracted_program"
        sample["payload"]["response"][field] = "tampered"
        _write_record(sample_path, sample)
    elif mutation == "foreign":
        foreign = store.root / "arms" / "final-no-thinking" / "tasks" / "F9" / "sample.json"
        foreign.parent.mkdir(parents=True)
        foreign.write_bytes(sample_path.read_bytes())
    else:
        link = store.root / "arms" / "final-no-thinking" / "tasks" / "F9"
        link.symlink_to(sample_path.parent, target_is_directory=True)

    def forbidden_service() -> Any:
        raise AssertionError("invalid resume created a client")

    with pytest.raises(subject.RendererDiagnosticError):
        _run(
            protocol=completed["protocol"],
            external=completed["external"],
            receipt_sha=completed["receipt_sha"],
            evaluator=_FakeEvaluator(completed["events"]),
            service_factory=forbidden_service,
        )


def test_wrong_receipt_and_second_source_check_precede_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    external, receipt_sha = _mixed_receipt(tmp_path, protocol=protocol)
    events: list[str] = []
    _patch_preflight(monkeypatch, protocol=protocol, events=events)
    monkeypatch.setenv("TINKER_API_KEY", "test-key")

    def forbidden_service() -> Any:
        raise AssertionError("failed preflight created a client")

    with pytest.raises(subject.checkpoint_v1.CheckpointReceiptError):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha="f" * 64,
            evaluator=_FakeEvaluator(events),
            service_factory=forbidden_service,
        )

    calls = 0

    def changing_source(_root: Path, expected: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("source changed after preflight")
        return expected

    monkeypatch.setattr(subject, "validate_source_sha", changing_source)
    with pytest.raises(ValueError, match="source changed"):
        _run(
            protocol=protocol,
            external=external,
            receipt_sha=receipt_sha,
            evaluator=_FakeEvaluator(events),
            service_factory=forbidden_service,
        )
    assert calls == 2


def test_model_failures_zero_and_infrastructure_failures_abort() -> None:
    arm = SimpleNamespace(
        spec=subject.ARM_SPECS[0],
        binding=None,
    )
    attempt = subject.PreparedAttempt(
        arm=arm,
        prepared=subject.checkpoint_v1.PreparedTask(
            task=_task(),
            prompt_tokens=100,
            prompt_text_sha256="1" * 64,
            reference_evidence={},
        ),
        seed=123,
    )
    model_failure = subject._evaluation_payload(
        attempt=attempt,
        result=EvaluationResult(
            status=EvaluationStatus.SYNTAX_ERROR,
            attribution=Attribution.MODEL,
            error="invalid syntax",
        ),
        sample_record_sha256="2" * 64,
        manifest_record_sha256="3" * 64,
        extracted_program_sha256="4" * 64,
    )
    assert model_failure["raw_absolute_scale_iou"] == 0.0
    assert model_failure["pure_executable"] is False

    for attribution, error_type in (
        (Attribution.REFERENCE, subject.checkpoint_v1.ReferencePanelFault),
        (
            Attribution.EVALUATOR,
            subject.checkpoint_v1.EvaluationInfrastructureFault,
        ),
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
                extracted_program_sha256="4" * 64,
            )


def test_resigned_report_marker_or_metrics_tampering_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    completed = _completed(tmp_path, monkeypatch)
    for mutation in ("marker", "summary"):
        payload = copy.deepcopy(completed["report"]["payload"])
        if mutation == "marker":
            payload["not_canonical_evidence"] = False
        else:
            payload["summaries"]["final-no-thinking"]["mean_raw_absolute_scale_iou"] = 0.99
        record = subject._record_document(
            record_type="renderer_diagnostic_report",
            key={},
            payload=payload,
        )
        with pytest.raises(subject.RendererDiagnosticError):
            subject._validate_report_rows(
                record,
                manifest_record=completed["manifest"],
                attempts=_attempt_context(completed),
            )


def _attempt_context(completed: Mapping[str, Any]) -> tuple[Any, ...]:
    protocol = completed["protocol"]
    training = TrainingStore(
        repo_root=REPO_ROOT,
        external_root=completed["external"],
    )
    bindings = subject._load_matrix_bindings(
        store=training,
        protocol=protocol,
        expected_wave_receipt_sha256=completed["receipt_sha"],
    )
    evaluator = _FakeEvaluator([])
    tasks = _tasks()
    panel = subject._task_panel(tasks)
    arms, attempts = subject._prepare_arms(
        protocol=protocol,
        model=protocol["models"]["qwen"],
        bindings=bindings,
        tasks=tasks,
        evaluator=evaluator,
        evaluator_source_git_sha=CURRENT_SOURCE_SHA,
        dataset_sha256=protocol["dataset"]["logical_release_sha256"],
        task_panel_sha256=panel["logical_sha256"],
    )
    assert len(arms) == 4
    evaluator.close()
    return attempts
