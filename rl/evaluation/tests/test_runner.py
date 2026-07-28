from __future__ import annotations

import asyncio
import hashlib
import io
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from rl.common.contracts import ModelObservation, VerifierReference
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.evaluation import runner
from rl.evaluation.attempt_store import AttemptKey, AttemptStore, RunKey
from rl.evaluation.protocol import ArmSpec, JobSpec
from rl.evaluation.samplers import SampleResult
from rl.evaluation.tasks import EvaluationTask


def _image_bytes() -> bytes:
    image = Image.new("L", (4, 4), color=255)
    image.putpixel((1, 1), 0)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _task(task_id: str = "F1") -> EvaluationTask:
    image = _image_bytes()
    digest = hashlib.sha256(image).hexdigest()
    return EvaluationTask(
        task_id=task_id,
        level="BENCHMARK",
        representation_id=f"benchmark-{task_id.lower()}",
        observation=ModelObservation(
            image_bytes=image,
            footprint_um=(4.0, 4.0),
            image_sha256=digest,
        ),
        reference=VerifierReference(
            target_image_bytes=image,
            footprint_um=(4.0, 4.0),
            target_image_sha256=digest,
        ),
    )


def _arm(arm_id: str = "qwen-off-4096") -> ArmSpec:
    return ArmSpec(
        arm_id=arm_id,
        provider="tinker",
        model="Qwen/Qwen3.6-35B-A3B",
        renderer="qwen3_5_disable_thinking",
        thinking=False,
        thinking_effort=None,
        max_output_tokens=4096,
        context_tokens=65536,
        max_image_long_edge=1440,
    )


def _job(
    *,
    arm_id: str = "qwen-off-4096",
    task_id: str = "F1",
    attempt_index: int = 1,
) -> JobSpec:
    return JobSpec(
        hypothesis_id="RC-H01",
        arm_id=arm_id,
        task_id=task_id,
        attempt_index=attempt_index,
        seed=20260727,
    )


def _protocol() -> dict[str, Any]:
    return {
        "study_id": "representation-curriculum-v1",
        "launch": {"confirmation_token": "RUN_PHASE1_BASELINES"},
        "sampling": {
            "sampling_concurrency": 2,
            "evaluator_workers": 1,
            "temperature": 1.0,
            "top_p": 1.0,
        },
        "pricing": {
            "models": {
                "Qwen/Qwen3.6-35B-A3B": {
                    "prefill_cached": 0.108,
                    "prefill_uncached": 0.54,
                    "sample": 1.335,
                }
            }
        },
        "tracking": {
            "project": "pixcell-test",
            "entity": None,
        },
    }


def _store(tmp_path: Path) -> AttemptStore:
    repo = tmp_path / "repo"
    repo.mkdir()
    return AttemptStore(
        repo_root=repo,
        external_root=tmp_path / "external",
    )


def _sample_result(program: str = "print('sample')") -> SampleResult:
    return SampleResult(
        prompt_tokens=100,
        completion_tokens=10,
        stop_reason="stop",
        cap_hit=False,
        raw_text=program,
        completion_text=program,
        reasoning_text="",
        answer_text=program,
        reasoning_tokens_exact=0,
        answer_tokens_exact=10,
        reasoning_tokens_estimate=None,
        answer_tokens_estimate=None,
        channel_token_count_basis="test",
        channel_parse_complete=True,
    )


def _binding(
    *,
    protocol: dict[str, Any],
    arm: ArmSpec,
    hypothesis_id: str,
    source_sha: str = "a" * 40,
) -> dict[str, Any]:
    return {
        "hypothesis_id": hypothesis_id,
        "source_git_sha": source_sha,
        "protocol_sha256": "b" * 64,
        "task_set_sha256": "c" * 64,
        "prompt_sha256": "d" * 64,
        "arms": {
            arm.arm_id: {
                "model": arm.model,
                "renderer": arm.renderer,
                "thinking": arm.thinking,
                "thinking_effort": arm.thinking_effort,
                "max_output_tokens": arm.max_output_tokens,
                "context_tokens": arm.context_tokens,
                "max_image_long_edge": arm.max_image_long_edge,
            }
        },
        "sampling": protocol["sampling"],
        "runtime": {
            "python": "3.13.14",
            "packages": {"tinker": "0.22.7"},
            "tinker_cookbook_commit": "f" * 40,
        },
        "sandbox": {
            "image_ref": "sha256:" + "e" * 64,
            "image_id": "sha256:" + "e" * 64,
        },
    }


def _manifest_record(
    *,
    store: AttemptStore,
    protocol: dict[str, Any],
    arm: ArmSpec,
    hypothesis_id: str,
    binding: dict[str, Any],
) -> Any:
    run_key = RunKey(protocol["study_id"], hypothesis_id, arm.arm_id)
    with store.acquire_run_lock(run_key):
        return store.create_or_verify_run_manifest(
            run_key,
            runner._run_manifest(binding, arm.arm_id),
        )


def _receipt_payload(
    *,
    protocol: dict[str, Any],
    arm: ArmSpec,
    job: JobSpec,
    manifest_sha: str,
    prompt_tokens: int = 100,
) -> dict[str, Any]:
    sample = _sample_result().to_dict()
    sample["prompt_tokens"] = prompt_tokens
    return {
        "request": runner._expected_request(
            arm=arm,
            protocol=protocol,
            job=job,
        ),
        "sample": sample,
        "sampling_seconds": 0.1,
        "raw_completion_sha256": runner._sha256_text(sample["raw_text"]),
        "completion_sha256": runner._sha256_text(sample["completion_text"]),
        "run_manifest_record_sha256": manifest_sha,
        "cost_estimate_usd": runner._cost_estimate(
            protocol,
            arm,
            prompt_tokens=prompt_tokens,
            completion_tokens=sample["completion_tokens"],
        ),
    }


def _evaluation_payload(
    *,
    task: EvaluationTask,
    attribution: Attribution = Attribution.MODEL,
    status: EvaluationStatus = EvaluationStatus.SYNTAX_ERROR,
) -> dict[str, Any]:
    program = runner.extract_code(_sample_result().completion_text)
    return {
        "status": status.value,
        "attribution": attribution.value,
        "pure_executable": status is EvaluationStatus.OK,
        "measurement_available": False,
        "measured_iou": None,
        "measured_dice": None,
        "aggregation_iou": 0.0,
        "program": program,
        "program_sha256": runner._sha256_text(program),
        "reference_sha256": task.reference.target_image_sha256,
        "violations": [],
        "error": "expected test failure",
        "retryable": attribution is not Attribution.MODEL,
        "evaluation_seconds": 0.1,
        "diagnostics": {},
    }


class _CountingSampler:
    def __init__(self) -> None:
        self.calls = 0

    def build_prompt(self, _messages: list[Any]) -> SimpleNamespace:
        return SimpleNamespace(length=100)

    async def sample(
        self,
        _messages: list[Any],
        _request: Any,
    ) -> SampleResult:
        self.calls += 1
        return _sample_result()


class _SavedRecordTracker:
    def __init__(self, store: AttemptStore) -> None:
        self.store = store
        self.calls = 0

    def mirror_saved_metrics(
        self,
        *,
        key: AttemptKey,
        source: str,
        metrics: dict[str, int | float],
        step: int,
    ) -> SimpleNamespace:
        assert source == "evaluation"
        assert self.store.load_evaluation(key) is not None
        assert metrics["attempt/iou"] >= 0.0
        assert step >= 0
        self.calls += 1
        return SimpleNamespace(mirrored=True)


def test_reference_preflight_failure_happens_before_remote_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """A local reference failure must remain a zero-spend failure."""

    protocol = _protocol()
    task = _task()
    arm = _arm()
    job = JobSpec(
        hypothesis_id="RC-H02",
        arm_id=arm.arm_id,
        task_id=task.task_id,
        attempt_index=1,
        seed=20260727,
    )
    source_sha = "a" * 40
    client_calls = 0
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    binding = {
        "hypothesis_id": job.hypothesis_id,
        "source_git_sha": source_sha,
        "protocol_sha256": "b" * 64,
        "task_set_sha256": "c" * 64,
        "prompt_sha256": "d" * 64,
        "arms": {arm.arm_id: {"model": arm.model}},
        "sampling": protocol["sampling"],
        "runtime": {
            "python": "3.13.14",
            "packages": {"tinker": "0.22.7"},
            "tinker_cookbook_commit": "f" * 40,
        },
        "sandbox": {
            "image_ref": "sha256:" + "e" * 64,
            "image_id": "sha256:" + "e" * 64,
        },
    }

    class FakeSampler:
        def __init__(
            self,
            _target: Any,
            *,
            service_client_factory: Any,
        ) -> None:
            self.service_client_factory = service_client_factory

        def build_prompt(self, _messages: list[Any]) -> SimpleNamespace:
            return SimpleNamespace(length=100)

        async def sample(self, _messages: list[Any], _request: Any) -> Any:
            nonlocal client_calls
            client_calls += 1
            self.service_client_factory()
            raise AssertionError("sampling must not begin")

    class BadReferenceEvaluator:
        max_workers = 1

        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["require_isolation"] is True

        def __enter__(self) -> BadReferenceEvaluator:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def validate_reference(self, _reference: VerifierReference) -> dict[str, Any]:
            raise ValueError("broken local reference")

    monkeypatch.setattr(runner, "load_protocol", lambda _root, **_kwargs: protocol)
    monkeypatch.setattr(
        runner,
        "build_launch_binding",
        lambda **_kwargs: (binding, [task], [job]),
    )
    monkeypatch.setattr(runner, "validate_credentials", lambda _protocol: None)
    monkeypatch.setattr(
        runner,
        "validate_wandb_access",
        lambda **_kwargs: {"username": "test", "entity": None},
    )
    monkeypatch.setattr(
        runner,
        "resolved_arm_ids",
        lambda *_args, **_kwargs: [arm.arm_id],
    )
    monkeypatch.setattr(runner, "arm_spec", lambda *_args, **_kwargs: arm)
    monkeypatch.setattr(runner, "TinkerSampler", FakeSampler)
    monkeypatch.setattr(runner, "PixCellEvaluator", BadReferenceEvaluator)
    monkeypatch.setattr(runner, "_messages", lambda _task, _arm: [{"role": "user"}])

    with pytest.raises(ValueError, match="broken local reference"):
        asyncio.run(
            runner.run_baseline(
                repo_root=repo_root,
                hypothesis_id=job.hypothesis_id,
                wave_name="smoke",
                expected_source_sha=source_sha,
                external_root=tmp_path / "external",
                confirmation=protocol["launch"]["confirmation_token"],
            )
        )

    assert client_calls == 0
    assert list((tmp_path / "external").rglob("sampling_receipt.json")) == []


def test_receipt_precedes_evaluation_and_resume_never_resamples(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    task = _task()
    arm = _arm()
    job = _job()
    sampler = _CountingSampler()
    protocol = _protocol()
    key = runner._attempt_key(protocol["study_id"], job)
    messages = {(arm.arm_id, task.task_id): [{"role": "user"}]}

    asyncio.run(
        runner._sample_missing(
            store=store,
            study_id=protocol["study_id"],
            jobs=[job],
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm={arm.arm_id: "a" * 64},
        )
    )
    first = store.load_sampling_receipt(key)
    assert first is not None

    asyncio.run(
        runner._sample_missing(
            store=store,
            study_id=protocol["study_id"],
            jobs=[job],
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm={arm.arm_id: "a" * 64},
        )
    )
    assert sampler.calls == 1
    assert store.load_sampling_receipt(key) == first

    class ReceiptAwareEvaluator:
        max_workers = 1

        def evaluate_batch(
            self,
            requests: list[tuple[VerifierReference, str]],
        ) -> list[EvaluationResult]:
            assert store.load_sampling_receipt(key) == first
            assert len(requests) == 1
            return [
                EvaluationResult(
                    status=EvaluationStatus.OK,
                    attribution=Attribution.MODEL,
                    iou=0.75,
                    dice=0.8,
                    metrics={"render_sha256": "f" * 64},
                    latency_seconds=0.1,
                )
            ]

    tracker = _SavedRecordTracker(store)
    runner._evaluate_missing(
        store=store,
        study_id=protocol["study_id"],
        jobs=[job],
        tasks=[task],
        evaluator=ReceiptAwareEvaluator(),
        tracker_by_arm={arm.arm_id: tracker},
    )
    assert store.load_evaluation(key) is not None
    assert tracker.calls == 1


def test_smoke_expands_to_complete_without_duplicate_sampling(
    tmp_path: Path,
) -> None:
    """The complete wave must reuse its smoke subset and add only missing jobs."""

    store = _store(tmp_path)
    protocol = _protocol()
    tasks = [_task("F1"), _task("F2")]
    arms = {
        arm_id: _arm(arm_id)
        for arm_id in ("qwen-off-4096", "qwen-off-16384")
    }
    samplers = {arm_id: _CountingSampler() for arm_id in arms}
    messages = {
        (arm_id, task.task_id): [{"role": "user"}]
        for arm_id in arms
        for task in tasks
    }
    smoke = [
        _job(arm_id=arm_id, task_id="F1", attempt_index=1)
        for arm_id in arms
    ]
    complete = [
        _job(
            arm_id=arm_id,
            task_id=task.task_id,
            attempt_index=attempt_index,
        )
        for attempt_index in (1, 2)
        for task in tasks
        for arm_id in arms
    ]

    for jobs in (smoke, complete, complete):
        asyncio.run(
            runner._sample_missing(
                store=store,
                study_id=protocol["study_id"],
                jobs=jobs,
                tasks=tasks,
                arms=arms,
                protocol=protocol,
                samplers=samplers,
                messages=messages,
                run_manifest_record_sha256_by_arm={
                    arm_id: "a" * 64 for arm_id in arms
                },
            )
        )

    assert {arm_id: sampler.calls for arm_id, sampler in samplers.items()} == {
        "qwen-off-4096": 4,
        "qwen-off-16384": 4,
    }
    assert len(list(store.external_root.rglob("sampling_receipt.json"))) == 8


def test_sampling_wave_persists_siblings_before_raising_transport_failure(
    tmp_path: Path,
) -> None:
    """One failed request must not cancel paid sibling generations."""

    store = _store(tmp_path)
    protocol = _protocol()
    protocol["sampling"]["sampling_concurrency"] = 4
    task = _task()
    arm = _arm()
    jobs = [
        JobSpec(
            hypothesis_id="RC-H01",
            arm_id=arm.arm_id,
            task_id=task.task_id,
            attempt_index=index,
            seed=20260727 + index,
        )
        for index in range(1, 5)
    ]
    started: list[int] = []

    class OneFailureSampler(_CountingSampler):
        async def sample(
            self,
            _messages: list[Any],
            request: Any,
        ) -> SampleResult:
            self.calls += 1
            started.append(request.seed)
            await asyncio.sleep(0)
            if request.seed == jobs[0].seed:
                raise ConnectionError("simulated transport failure")
            return _sample_result()

    sampler = OneFailureSampler()
    with pytest.raises(RuntimeError, match="sibling requests settled"):
        asyncio.run(
            runner._sample_missing(
                store=store,
                study_id=protocol["study_id"],
                jobs=jobs,
                tasks=[task],
                arms={arm.arm_id: arm},
                protocol=protocol,
                samplers={arm.arm_id: sampler},
                messages={
                    (arm.arm_id, task.task_id): [{"role": "user"}]
                },
                run_manifest_record_sha256_by_arm={
                    arm.arm_id: "a" * 64
                },
            )
        )

    assert started == [job.seed for job in jobs]
    assert store.load_sampling_receipt(
        runner._attempt_key(protocol["study_id"], jobs[0])
    ) is None
    assert all(
        store.load_sampling_receipt(
            runner._attempt_key(protocol["study_id"], job)
        )
        is not None
        for job in jobs[1:]
    )


def test_resume_preflight_rejects_stale_request_before_new_sampling(
    tmp_path: Path,
) -> None:
    """An immutable receipt cannot be silently adopted by another job."""

    store = _store(tmp_path)
    protocol = _protocol()
    task = _task()
    arm = _arm()
    jobs = [_job(attempt_index=1), _job(attempt_index=2)]
    binding = _binding(
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
    )
    manifest = _manifest_record(
        store=store,
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        binding=binding,
    )
    stale = _receipt_payload(
        protocol=protocol,
        arm=arm,
        job=jobs[0],
        manifest_sha=manifest.record_sha256,
    )
    stale["request"]["seed"] += 1
    store.write_sampling_receipt(
        runner._attempt_key(protocol["study_id"], jobs[0]),
        stale,
    )
    sampler = _CountingSampler()
    messages = {(arm.arm_id, task.task_id): [{"role": "user"}]}

    with pytest.raises(ValueError, match="exact current job"):
        runner._validate_existing_attempts_before_sampling(
            store=store,
            study_id=protocol["study_id"],
            jobs=jobs,
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm={
                arm.arm_id: manifest.record_sha256
            },
        )

    assert sampler.calls == 0
    assert store.load_sampling_receipt(
        runner._attempt_key(protocol["study_id"], jobs[1])
    ) is None


def test_complete_resume_rejects_saved_verifier_failure_before_sampling(
    tmp_path: Path,
) -> None:
    """A bad smoke evaluation must stop a complete wave before attempts 2-4."""

    store = _store(tmp_path)
    protocol = _protocol()
    task = _task()
    arm = _arm()
    jobs = [_job(attempt_index=1), _job(attempt_index=2)]
    binding = _binding(
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
    )
    manifest = _manifest_record(
        store=store,
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        binding=binding,
    )
    key = runner._attempt_key(protocol["study_id"], jobs[0])
    store.write_sampling_receipt(
        key,
        _receipt_payload(
            protocol=protocol,
            arm=arm,
            job=jobs[0],
            manifest_sha=manifest.record_sha256,
        ),
    )
    store.write_evaluation(
        key,
        _evaluation_payload(
            task=task,
            attribution=Attribution.EVALUATOR,
            status=EvaluationStatus.WORKER_ERROR,
        ),
    )
    sampler = _CountingSampler()
    messages = {(arm.arm_id, task.task_id): [{"role": "user"}]}

    with pytest.raises(RuntimeError, match="refusing to buy more samples"):
        runner._validate_existing_attempts_before_sampling(
            store=store,
            study_id=protocol["study_id"],
            jobs=jobs,
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm={
                arm.arm_id: manifest.record_sha256
            },
        )

    assert sampler.calls == 0
    assert store.load_sampling_receipt(
        runner._attempt_key(protocol["study_id"], jobs[1])
    ) is None


def test_run_baseline_complete_fails_before_client_on_bad_smoke_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """The paid entrypoint applies the resume audit before sampling."""

    protocol = _protocol()
    task = _task()
    arm = _arm()
    jobs = [
        JobSpec(
            hypothesis_id="RC-H05",
            arm_id=arm.arm_id,
            task_id=task.task_id,
            attempt_index=index,
            seed=20260727 + index,
        )
        for index in (1, 2)
    ]
    source_sha = "a" * 40
    binding = _binding(
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        source_sha=source_sha,
    )
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    external_root = tmp_path / "external"
    store = AttemptStore(repo_root=repo_root, external_root=external_root)
    manifest = _manifest_record(
        store=store,
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        binding=binding,
    )
    key = runner._attempt_key(protocol["study_id"], jobs[0])
    store.write_sampling_receipt(
        key,
        _receipt_payload(
            protocol=protocol,
            arm=arm,
            job=jobs[0],
            manifest_sha=manifest.record_sha256,
        ),
    )
    store.write_evaluation(
        key,
        _evaluation_payload(
            task=task,
            attribution=Attribution.REFERENCE,
            status=EvaluationStatus.REFERENCE_ERROR,
        ),
    )
    client_calls = 0

    class FakeSampler:
        def __init__(
            self,
            _target: Any,
            *,
            service_client_factory: Any,
        ) -> None:
            self.service_client_factory = service_client_factory

        def build_prompt(self, _messages: list[Any]) -> SimpleNamespace:
            return SimpleNamespace(length=100)

        async def sample(self, _messages: list[Any], _request: Any) -> Any:
            nonlocal client_calls
            client_calls += 1
            self.service_client_factory()
            raise AssertionError("resume audit must stop before sampling")

    class ValidReferenceEvaluator:
        max_workers = 1

        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["require_isolation"] is True

        def __enter__(self) -> ValidReferenceEvaluator:
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def validate_reference(
            self,
            reference: VerifierReference,
        ) -> dict[str, Any]:
            return {"target_image_sha256": reference.target_image_sha256}

        def evaluate_batch(self, _requests: Any) -> Any:
            raise AssertionError("resume audit must stop before evaluation")

    monkeypatch.setattr(runner, "load_protocol", lambda _root, **_kwargs: protocol)
    monkeypatch.setattr(
        runner,
        "build_launch_binding",
        lambda **_kwargs: (binding, [task], jobs),
    )
    monkeypatch.setattr(runner, "validate_credentials", lambda _protocol: None)
    monkeypatch.setattr(
        runner,
        "validate_wandb_access",
        lambda **_kwargs: {"username": "test", "entity": None},
    )
    monkeypatch.setattr(
        runner,
        "resolved_arm_ids",
        lambda *_args, **_kwargs: [arm.arm_id],
    )
    monkeypatch.setattr(runner, "arm_spec", lambda *_args, **_kwargs: arm)
    monkeypatch.setattr(runner, "TinkerSampler", FakeSampler)
    monkeypatch.setattr(runner, "PixCellEvaluator", ValidReferenceEvaluator)
    monkeypatch.setattr(
        runner,
        "_messages",
        lambda _task, _arm: [{"role": "user"}],
    )

    with pytest.raises(RuntimeError, match="refusing to buy more samples"):
        asyncio.run(
            runner.run_baseline(
                repo_root=repo_root,
                hypothesis_id=jobs[0].hypothesis_id,
                wave_name="complete",
                expected_source_sha=source_sha,
                external_root=external_root,
                confirmation=protocol["launch"]["confirmation_token"],
            )
        )

    assert client_calls == 0
    assert store.load_sampling_receipt(
        runner._attempt_key(protocol["study_id"], jobs[1])
    ) is None


def test_complete_resume_reuses_valid_model_failure_and_samples_only_missing(
    tmp_path: Path,
) -> None:
    """A legitimate model failure remains evidence and does not poison resume."""

    store = _store(tmp_path)
    protocol = _protocol()
    task = _task()
    arm = _arm()
    jobs = [_job(attempt_index=1), _job(attempt_index=2)]
    binding = _binding(
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
    )
    manifest = _manifest_record(
        store=store,
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        binding=binding,
    )
    key = runner._attempt_key(protocol["study_id"], jobs[0])
    store.write_sampling_receipt(
        key,
        _receipt_payload(
            protocol=protocol,
            arm=arm,
            job=jobs[0],
            manifest_sha=manifest.record_sha256,
        ),
    )
    store.write_evaluation(key, _evaluation_payload(task=task))
    sampler = _CountingSampler()
    messages = {(arm.arm_id, task.task_id): [{"role": "user"}]}
    manifest_shas = {arm.arm_id: manifest.record_sha256}

    runner._validate_existing_attempts_before_sampling(
        store=store,
        study_id=protocol["study_id"],
        jobs=jobs,
        tasks=[task],
        arms={arm.arm_id: arm},
        protocol=protocol,
        samplers={arm.arm_id: sampler},
        messages=messages,
        run_manifest_record_sha256_by_arm=manifest_shas,
    )
    asyncio.run(
        runner._sample_missing(
            store=store,
            study_id=protocol["study_id"],
            jobs=jobs,
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm=manifest_shas,
        )
    )

    assert sampler.calls == 1
    assert len(list(store.external_root.rglob("sampling_receipt.json"))) == 2


def test_partial_receipt_is_evaluated_before_complete_wave_expands(
    tmp_path: Path,
) -> None:
    """A crash between sampling and scoring resumes without deadlock or spend."""

    store = _store(tmp_path)
    protocol = _protocol()
    task = _task()
    arm = _arm()
    jobs = [_job(attempt_index=1), _job(attempt_index=2)]
    binding = _binding(
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
    )
    manifest = _manifest_record(
        store=store,
        protocol=protocol,
        arm=arm,
        hypothesis_id=jobs[0].hypothesis_id,
        binding=binding,
    )
    first_key = runner._attempt_key(protocol["study_id"], jobs[0])
    store.write_sampling_receipt(
        first_key,
        _receipt_payload(
            protocol=protocol,
            arm=arm,
            job=jobs[0],
            manifest_sha=manifest.record_sha256,
        ),
    )
    sampler = _CountingSampler()
    messages = {(arm.arm_id, task.task_id): [{"role": "user"}]}
    manifest_shas = {arm.arm_id: manifest.record_sha256}

    runner._validate_existing_attempts_before_sampling(
        store=store,
        study_id=protocol["study_id"],
        jobs=jobs,
        tasks=[task],
        arms={arm.arm_id: arm},
        protocol=protocol,
        samplers={arm.arm_id: sampler},
        messages=messages,
        run_manifest_record_sha256_by_arm=manifest_shas,
        require_receipt_evaluations=False,
    )

    class ModelFailureEvaluator:
        max_workers = 1

        def evaluate_batch(
            self,
            requests: list[tuple[VerifierReference, str]],
        ) -> list[EvaluationResult]:
            assert len(requests) == 1
            return [
                EvaluationResult(
                    status=EvaluationStatus.SYNTAX_ERROR,
                    attribution=Attribution.MODEL,
                    error="invalid syntax",
                    latency_seconds=0.1,
                )
            ]

    runner._evaluate_missing(
        store=store,
        study_id=protocol["study_id"],
        jobs=[jobs[0]],
        tasks=[task],
        evaluator=ModelFailureEvaluator(),
        tracker_by_arm=None,
    )
    assert store.load_evaluation(first_key) is not None

    runner._validate_existing_attempts_before_sampling(
        store=store,
        study_id=protocol["study_id"],
        jobs=jobs,
        tasks=[task],
        arms={arm.arm_id: arm},
        protocol=protocol,
        samplers={arm.arm_id: sampler},
        messages=messages,
        run_manifest_record_sha256_by_arm=manifest_shas,
        require_receipt_evaluations=True,
    )
    asyncio.run(
        runner._sample_missing(
            store=store,
            study_id=protocol["study_id"],
            jobs=jobs,
            tasks=[task],
            arms={arm.arm_id: arm},
            protocol=protocol,
            samplers={arm.arm_id: sampler},
            messages=messages,
            run_manifest_record_sha256_by_arm=manifest_shas,
        )
    )
    assert sampler.calls == 1
    assert len(list(store.external_root.rglob("sampling_receipt.json"))) == 2


def test_saved_verifier_failure_is_diagnostic_and_receipt_can_be_re_evaluated(
    tmp_path: Path,
) -> None:
    """Infrastructure failure is preserved without poisoning the paid receipt."""

    store = _store(tmp_path)
    task = _task()
    arm = _arm()
    job = _job()
    protocol = _protocol()
    key = runner._attempt_key(protocol["study_id"], job)
    store.write_sampling_receipt(
        key,
        {
            "sample": _sample_result().to_dict(),
            "sampling_seconds": 0.1,
            "cost_estimate_usd": {
                "cached_prefill": 0.0,
                "uncached_prefill": 0.0,
            },
        },
    )

    class FailingEvaluator:
        max_workers = 1

        def evaluate_batch(
            self,
            _requests: list[tuple[VerifierReference, str]],
        ) -> list[EvaluationResult]:
            return [
                EvaluationResult(
                    status=EvaluationStatus.WORKER_ERROR,
                    attribution=Attribution.EVALUATOR,
                    error="worker crashed",
                    latency_seconds=0.1,
                    retryable=True,
                )
            ]

    tracker = _SavedRecordTracker(store)
    with pytest.raises(RuntimeError, match="verifier/reference failures"):
        runner._evaluate_missing(
            store=store,
            study_id=protocol["study_id"],
            jobs=[job],
            tasks=[task],
            evaluator=FailingEvaluator(),
            tracker_by_arm={arm.arm_id: tracker},
        )
    assert store.load_evaluation(key) is None
    assert len(store.list_evaluator_failures(key)) == 1
    assert tracker.calls == 0

    class RecoveredEvaluator:
        max_workers = 1

        def evaluate_batch(
            self,
            _requests: list[tuple[VerifierReference, str]],
        ) -> list[EvaluationResult]:
            return [
                EvaluationResult(
                    status=EvaluationStatus.SYNTAX_ERROR,
                    attribution=Attribution.MODEL,
                    error="model syntax error",
                    latency_seconds=0.1,
                )
            ]

    runner._evaluate_missing(
        store=store,
        study_id=protocol["study_id"],
        jobs=[job],
        tasks=[task],
        evaluator=RecoveredEvaluator(),
        tracker_by_arm={arm.arm_id: tracker},
    )
    assert store.load_evaluation(key) is not None
    assert len(store.list_evaluator_failures(key)) == 1
    assert tracker.calls == 1
