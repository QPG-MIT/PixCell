"""Resumable, candidate-level baseline sampling and deterministic evaluation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import statistics
import time
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.output import extract_code
from rl.common.preprocess import model_image
from rl.common.prompt import build_prompt_text
from rl.evaluation.attempt_store import (
    AttemptKey,
    AttemptStore,
    RunKey,
)
from rl.evaluation.protocol import (
    ArmSpec,
    JobSpec,
    arm_spec,
    build_launch_binding,
    jobs_for_wave,
    load_protocol,
    resolved_arm_ids,
    task_manifest_path,
    validate_credentials,
)
from rl.evaluation.samplers import (
    SamplerTarget,
    SamplingRequest,
    TinkerSampler,
)
from rl.evaluation.summarize import (
    atomic_write_json,
    choose_operating_point,
    summarize_arm,
)
from rl.evaluation.tasks import (
    EvaluationTask,
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)
from rl.evaluation.tracking import (
    WandbMetricsMirror,
    WandbRunSession,
    validate_wandb_access,
)


_FORBIDDEN_PROMPT_FRAGMENTS = (
    "DISPLAY NOTE",
    "magnification x:y",
    "px/um",
    "target_image",
    "calibration.json",
)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _messages(task: EvaluationTask, arm: ArmSpec) -> list[Any]:
    from tinker_cookbook.renderers import ImagePart, Message, TextPart

    text = build_prompt_text(task.observation)
    leaked = [value for value in _FORBIDDEN_PROMPT_FRAGMENTS if value in text]
    if leaked:
        raise ValueError(f"model prompt leaked forbidden fields: {leaked}")
    return [
        Message(
            role="user",
            content=[
                ImagePart(
                    type="image",
                    image=model_image(
                        task.observation,
                        max_long_edge=arm.max_image_long_edge,
                    ),
                ),
                TextPart(type="text", text=text),
            ],
        )
    ]


def _sampler_target(arm: ArmSpec) -> SamplerTarget:
    return SamplerTarget(
        model_name=arm.model,
        renderer_name=arm.renderer,
        base_model=arm.model,
        effort=arm.thinking_effort,
    )


def _safe_json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _safe_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_json(item) for item in value]
    if hasattr(value, "item"):
        return _safe_json(value.item())
    return str(value)


def _attempt_key(study_id: str, job: JobSpec) -> AttemptKey:
    return AttemptKey(
        study_id=study_id,
        hypothesis_id=job.hypothesis_id,
        arm_id=job.arm_id,
        task_id=job.task_id,
        attempt_index=job.attempt_index,
    )


def _run_manifest(binding: dict[str, Any], arm_id: str) -> dict[str, Any]:
    return {
        "source_git_sha": binding["source_git_sha"],
        "protocol_sha256": binding["protocol_sha256"],
        "task_set_sha256": binding["task_set_sha256"],
        "prompt_sha256": binding["prompt_sha256"],
        "sandbox_image_ref": binding["sandbox"]["image_ref"],
        "sandbox_image_id": binding["sandbox"]["image_id"],
        "runtime": binding["runtime"],
        "model_binding": {
            "arm_id": arm_id,
            **binding["arms"][arm_id],
            "temperature": binding["sampling"]["temperature"],
            "top_p": binding["sampling"]["top_p"],
        },
    }


def _selection_document(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    value = json.loads(path.expanduser().resolve(strict=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("selection receipt must contain a JSON object")
    claimed = value.get("logical_sha256")
    unsigned = {key: item for key, item in value.items() if key != "logical_sha256"}
    if claimed != canonical_json_sha256(unsigned):
        raise ValueError("selection receipt logical SHA-256 mismatch")
    return value


def _canonical_selection_path(
    *,
    external_root: Path,
    study_id: str,
    hypothesis_id: str,
) -> Path | None:
    root = (
        external_root.expanduser().resolve()
        / "studies"
        / study_id
        / "selections"
    )
    if hypothesis_id == "RC-H00R":
        return root / "operating_point.preliminary.json"
    if hypothesis_id == "RC-H01":
        return root / "operating_point.json"
    return None


def _cost_estimate(
    protocol: dict[str, Any],
    arm: ArmSpec,
    *,
    prompt_tokens: int,
    completion_tokens: int,
) -> dict[str, float]:
    rates = protocol["pricing"]["models"][arm.model]
    sample = completion_tokens * float(rates["sample"]) / 1_000_000
    return {
        "cached_prefill": (
            prompt_tokens * float(rates["prefill_cached"]) / 1_000_000 + sample
        ),
        "uncached_prefill": (
            prompt_tokens * float(rates["prefill_uncached"]) / 1_000_000 + sample
        ),
    }


def _tracking_step(
    job: JobSpec,
    *,
    tasks: list[EvaluationTask],
) -> int:
    task_index = {task.task_id: index for index, task in enumerate(tasks)}
    return (job.attempt_index - 1) * len(tasks) + task_index[job.task_id]


def _summary_path(store: AttemptStore, run_key: RunKey) -> Path:
    relative = store.run_relative_path(run_key) / "summary.json"
    return store.external_root.joinpath(*relative.parts)


def _selection_paths(store: AttemptStore, study_id: str) -> tuple[Path, Path]:
    root = store.external_root / "studies" / study_id / "selections"
    return (
        root / "operating_point.preliminary.json",
        root / "operating_point.json",
    )


def _preflight_renderers(
    *,
    tasks: list[EvaluationTask],
    arms: dict[str, ArmSpec],
    samplers: dict[str, TinkerSampler],
) -> dict[tuple[str, str], list[Any]]:
    messages: dict[tuple[str, str], list[Any]] = {}
    for arm_id, arm in arms.items():
        sampler = samplers[arm_id]
        for task in tasks:
            rendered_messages = _messages(task, arm)
            prompt = sampler.build_prompt(rendered_messages)
            if int(prompt.length) + arm.max_output_tokens > arm.context_tokens:
                raise ValueError(
                    f"{arm_id}/{task.task_id} exceeds its context window: "
                    f"{prompt.length}+{arm.max_output_tokens}>{arm.context_tokens}"
                )
            messages[(arm_id, task.task_id)] = rendered_messages
    return messages


def _preflight_references(tasks: list[EvaluationTask], evaluator: PixCellEvaluator) -> None:
    for task in tasks:
        evidence = evaluator.validate_reference(task.reference)
        if evidence["target_image_sha256"] != task.reference.target_image_sha256:
            raise ValueError(f"{task.task_id} reference validation changed its digest")


async def _sample_missing(
    *,
    store: AttemptStore,
    study_id: str,
    jobs: list[JobSpec],
    tasks: list[EvaluationTask],
    arms: dict[str, ArmSpec],
    protocol: dict[str, Any],
    samplers: dict[str, TinkerSampler],
    messages: dict[tuple[str, str], list[Any]],
) -> None:
    semaphore = asyncio.Semaphore(int(protocol["sampling"]["sampling_concurrency"]))

    async def sample_one(job: JobSpec) -> None:
        key = _attempt_key(study_id, job)
        if store.load_sampling_receipt(key) is not None:
            return
        arm = arms[job.arm_id]
        request = SamplingRequest(
            max_tokens=arm.max_output_tokens,
            temperature=float(protocol["sampling"]["temperature"]),
            top_p=float(protocol["sampling"]["top_p"]),
            seed=job.seed,
        )
        started = time.monotonic()
        async with semaphore:
            sample = await samplers[job.arm_id].sample(
                messages[(job.arm_id, job.task_id)],
                request,
            )
        elapsed = time.monotonic() - started
        sample_payload = sample.to_dict()
        payload = {
            "request": {
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "top_p": request.top_p,
                "seed": request.seed,
            },
            "sample": sample_payload,
            "sampling_seconds": elapsed,
            "raw_completion_sha256": _sha256_text(sample.raw_text),
            "completion_sha256": _sha256_text(sample.completion_text),
            "cost_estimate_usd": _cost_estimate(
                protocol,
                arm,
                prompt_tokens=sample.prompt_tokens,
                completion_tokens=sample.completion_tokens,
            ),
        }
        store.write_sampling_receipt(key, payload)

    await asyncio.gather(*(sample_one(job) for job in jobs))


def _evaluate_missing(
    *,
    store: AttemptStore,
    study_id: str,
    jobs: list[JobSpec],
    tasks: list[EvaluationTask],
    evaluator: PixCellEvaluator,
    tracker_by_arm: dict[str, WandbRunSession],
) -> None:
    task_by_id = {task.task_id: task for task in tasks}
    pending: list[tuple[JobSpec, AttemptKey, dict[str, Any]]] = []
    for job in jobs:
        key = _attempt_key(study_id, job)
        if store.load_evaluation(key) is not None:
            continue
        receipt = store.load_sampling_receipt(key)
        if receipt is None:
            raise RuntimeError(f"missing sampling receipt for {key}")
        pending.append((job, key, receipt.payload))

    failures: list[str] = []
    for job in jobs:
        key = _attempt_key(study_id, job)
        existing = store.load_evaluation(key)
        if (
            existing is not None
            and existing.payload.get("attribution") != Attribution.MODEL.value
        ):
            failures.append(
                f"{key}: {existing.payload.get('attribution')}/"
                f"{existing.payload.get('status')}; "
                f"record={existing.relative_path}"
            )
    batch_size = evaluator.max_workers * 4
    for start in range(0, len(pending), batch_size):
        batch = pending[start : start + batch_size]
        requests = [
            (
                task_by_id[job.task_id].reference,
                receipt["sample"]["completion_text"],
            )
            for job, _key, receipt in batch
        ]
        results = evaluator.evaluate_batch(requests)
        for (job, key, receipt), result in zip(batch, results, strict=True):
            completion = str(receipt["sample"]["completion_text"])
            program = extract_code(completion)
            measured_iou = float(result.iou) if result.iou is not None else None
            measured_dice = float(result.dice) if result.dice is not None else None
            aggregation_iou = (
                measured_iou
                if result.attribution is Attribution.MODEL and measured_iou is not None
                else 0.0
            )
            pure = result.status is EvaluationStatus.OK
            payload: dict[str, Any] = {
                "status": result.status.value,
                "attribution": result.attribution.value,
                "pure_executable": pure,
                "measurement_available": result.iou is not None,
                "measured_iou": measured_iou,
                "measured_dice": measured_dice,
                "aggregation_iou": aggregation_iou,
                "program": program,
                "program_sha256": _sha256_text(program),
                "reference_sha256": task_by_id[
                    job.task_id
                ].reference.target_image_sha256,
                "violations": list(result.violations),
                "error": result.error,
                "retryable": bool(result.retryable),
                "evaluation_seconds": float(result.latency_seconds),
                "diagnostics": _safe_json(result.metrics),
            }
            render_sha256 = result.metrics.get("render_sha256")
            if render_sha256 is not None:
                payload["render_sha256"] = render_sha256
            saved = store.write_evaluation(key, payload)
            tracking_metrics = {
                "attempt/iou": aggregation_iou,
                "attempt/pure_executable": int(pure),
                "attempt/cap_hit": int(receipt["sample"]["cap_hit"]),
                "attempt/prompt_tokens": int(receipt["sample"]["prompt_tokens"]),
                "attempt/completion_tokens": int(
                    receipt["sample"]["completion_tokens"]
                ),
                "attempt/sampling_seconds": float(receipt["sampling_seconds"]),
                "attempt/evaluation_seconds": float(result.latency_seconds),
                "attempt/estimated_uncached_cost_usd": float(
                    receipt["cost_estimate_usd"]["uncached_prefill"]
                ),
            }
            tracker_by_arm[job.arm_id].mirror_saved_metrics(
                key=key,
                source="evaluation",
                metrics=tracking_metrics,
                step=_tracking_step(job, tasks=tasks),
            )
            if result.attribution is not Attribution.MODEL:
                failures.append(
                    f"{key}: {result.attribution.value}/{result.status.value}; "
                    f"record={saved.relative_path}"
                )
    if failures:
        raise RuntimeError(
            "baseline evaluation aborted on verifier/reference failures:\n"
            + "\n".join(failures)
        )


def _validate_selection_provenance(
    *,
    repo_root: Path,
    external_root: Path,
    expected_source_sha: str,
    protocol: dict[str, Any],
    hypothesis_id: str,
    selection: dict[str, Any] | None,
) -> None:
    """Recompute a canonical operating-point receipt from immutable attempts."""

    if hypothesis_id not in {"RC-H00R", "RC-H01"}:
        if selection is not None:
            raise ValueError(f"{hypothesis_id} must not receive a selection receipt")
        return
    if selection is None:
        raise ValueError(f"{hypothesis_id} requires a selection receipt")
    if selection.get("source_git_sha") != expected_source_sha:
        raise ValueError("operating-point selection source SHA differs from launch SHA")

    store = AttemptStore(repo_root=repo_root, external_root=external_root)
    manifest = load_task_manifest(task_manifest_path(repo_root), repo_root=repo_root)
    tasks = load_task_set(
        repo_root=repo_root,
        manifest=manifest,
        task_set=protocol["hypotheses"]["RC-H00"]["task_set"],
    )
    task_ids = [task.task_id for task in tasks]
    h00_jobs = jobs_for_wave(
        protocol,
        hypothesis_id="RC-H00",
        wave_name="complete",
        task_ids=task_ids,
    )
    h00_binding, _bound_tasks, _bound_jobs = build_launch_binding(
        repo_root=repo_root,
        hypothesis_id="RC-H00",
        wave_name="complete",
        expected_source_sha=expected_source_sha,
        external_root=external_root,
    )
    summaries: dict[str, dict[str, Any]] = {}
    for arm_id in protocol["hypotheses"]["RC-H00"]["arm_ids"]:
        run_key = RunKey(protocol["study_id"], "RC-H00", arm_id)
        run_manifest = store.load_run_manifest(run_key)
        if run_manifest is None or run_manifest.payload != _run_manifest(
            h00_binding,
            arm_id,
        ):
            raise ValueError(f"RC-H00/{arm_id} run manifest is missing or stale")
        summaries[arm_id] = summarize_arm(
            store=store,
            study_id=protocol["study_id"],
            hypothesis_id="RC-H00",
            arm_id=arm_id,
            jobs=h00_jobs,
            tasks=tasks,
        )

    rescue_summary = None
    if selection.get("rescue_run"):
        rescue_arm = str(protocol["hypotheses"]["RC-H00R"]["arm_ids"][0])
        h00r_jobs = jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00R",
            wave_name="complete",
            task_ids=task_ids,
            selection=selection,
        )
        h00r_binding, _bound_tasks, _bound_jobs = build_launch_binding(
            repo_root=repo_root,
            hypothesis_id="RC-H00R",
            wave_name="complete",
            expected_source_sha=expected_source_sha,
            external_root=external_root,
            selection=selection,
        )
        run_key = RunKey(protocol["study_id"], "RC-H00R", rescue_arm)
        run_manifest = store.load_run_manifest(run_key)
        if run_manifest is None or run_manifest.payload != _run_manifest(
            h00r_binding,
            rescue_arm,
        ):
            raise ValueError("RC-H00R run manifest is missing or stale")
        rescue_summary = summarize_arm(
            store=store,
            study_id=protocol["study_id"],
            hypothesis_id="RC-H00R",
            arm_id=rescue_arm,
            jobs=h00r_jobs,
            tasks=tasks,
        )

    expected = choose_operating_point(
        protocol=protocol,
        source_git_sha=expected_source_sha,
        source_summaries=summaries,
        rescue_summary=rescue_summary,
    )
    if selection != expected:
        raise ValueError(
            "operating-point selection does not reproduce from immutable attempts"
        )
    if hypothesis_id == "RC-H00R" and (
        not expected["rescue_required"] or expected["rescue_run"]
    ):
        raise ValueError("RC-H00R requires the incomplete triggered preliminary receipt")
    if hypothesis_id == "RC-H01" and not expected["complete"]:
        raise ValueError("RC-H01 requires a complete operating-point selection")


def _write_summaries_and_selection(
    *,
    store: AttemptStore,
    protocol: dict[str, Any],
    binding: dict[str, Any],
    jobs: list[JobSpec],
    tasks: list[EvaluationTask],
) -> dict[str, dict[str, Any]]:
    hypothesis_id = str(binding["hypothesis_id"])
    summaries: dict[str, dict[str, Any]] = {}
    for arm_id in binding["arms"]:
        run_key = RunKey(protocol["study_id"], hypothesis_id, arm_id)
        summary = summarize_arm(
            store=store,
            study_id=protocol["study_id"],
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            jobs=jobs,
            tasks=tasks,
        )
        atomic_write_json(_summary_path(store, run_key), summary)
        summaries[arm_id] = summary

    if binding["wave"] != "complete":
        return summaries
    preliminary_path, final_path = _selection_paths(store, protocol["study_id"])
    if hypothesis_id == "RC-H00":
        selection = choose_operating_point(
            protocol=protocol,
            source_git_sha=binding["source_git_sha"],
            source_summaries=summaries,
        )
        atomic_write_json(preliminary_path, selection)
        if selection["complete"]:
            atomic_write_json(final_path, selection)
    elif hypothesis_id == "RC-H00R":
        manifest = json.loads(preliminary_path.read_text(encoding="utf-8"))
        original = {
            arm_id: value
            for arm_id, value in manifest["arm_summaries"].items()
            if arm_id in protocol["hypotheses"]["RC-H00"]["arm_ids"]
        }
        if len(summaries) != 1:
            raise ValueError("RC-H00R must contain exactly one rescue arm")
        selection = choose_operating_point(
            protocol=protocol,
            source_git_sha=binding["source_git_sha"],
            source_summaries=original,
            rescue_summary=next(iter(summaries.values())),
        )
        atomic_write_json(final_path, selection)
    return summaries


async def run_baseline(
    *,
    repo_root: Path,
    hypothesis_id: str,
    wave_name: str,
    expected_source_sha: str,
    external_root: Path,
    confirmation: str,
    selection_path: Path | None = None,
) -> dict[str, Any]:
    """Run one frozen wave. No training client is ever constructed."""

    root = repo_root.expanduser().resolve()
    protocol = load_protocol(root)
    canonical_selection = _canonical_selection_path(
        external_root=external_root,
        study_id=protocol["study_id"],
        hypothesis_id=hypothesis_id,
    )
    if canonical_selection is None:
        if selection_path is not None:
            raise ValueError(f"{hypothesis_id} does not accept a selection receipt")
    else:
        if selection_path is None:
            raise ValueError(
                f"{hypothesis_id} requires --selection {canonical_selection}"
            )
        observed_selection = selection_path.expanduser().resolve(strict=True)
        if observed_selection != canonical_selection:
            raise ValueError(
                "selection receipt must be the canonical file under the study root"
            )
    expected_confirmation = protocol["launch"]["confirmation_token"]
    if confirmation != expected_confirmation:
        raise ValueError(
            f"paid baseline launch requires --confirm-spend {expected_confirmation}"
        )
    selection = _selection_document(selection_path)
    binding, tasks, jobs = build_launch_binding(
        repo_root=root,
        hypothesis_id=hypothesis_id,
        wave_name=wave_name,
        expected_source_sha=expected_source_sha,
        external_root=external_root,
        selection=selection,
    )
    _validate_selection_provenance(
        repo_root=root,
        external_root=external_root,
        expected_source_sha=expected_source_sha,
        protocol=protocol,
        hypothesis_id=hypothesis_id,
        selection=selection,
    )
    validate_credentials(protocol)
    validate_wandb_access(expected_entity=protocol["tracking"].get("entity"))
    arms = {
        arm_id: arm_spec(protocol, arm_id)
        for arm_id in resolved_arm_ids(
            protocol,
            hypothesis_id,
            selection=selection,
        )
    }
    store = AttemptStore(repo_root=root, external_root=external_root)
    shared_service: dict[str, Any] = {}

    def service_factory() -> Any:
        if "client" not in shared_service:
            import tinker

            shared_service["client"] = tinker.ServiceClient(
                user_metadata={
                    "study": protocol["study_id"],
                    "hypothesis": hypothesis_id,
                    "source_sha": expected_source_sha,
                }
            )
        return shared_service["client"]

    samplers = {
        arm_id: TinkerSampler(
            _sampler_target(arm),
            service_client_factory=service_factory,
        )
        for arm_id, arm in arms.items()
    }
    # Renderer/tokenizer construction, complete context accounting, reference
    # validation, launch manifests, and locks all precede the first ServiceClient.
    messages = _preflight_renderers(
        tasks=tasks,
        arms=arms,
        samplers=samplers,
    )
    with PixCellEvaluator(
        max_workers=int(protocol["sampling"]["evaluator_workers"]),
        evaluator_retries=1,
        require_isolation=True,
    ) as evaluator:
        _preflight_references(tasks, evaluator)
        with ExitStack() as stack:
            for arm_id in arms:
                run_key = RunKey(protocol["study_id"], hypothesis_id, arm_id)
                stack.enter_context(store.acquire_run_lock(run_key))
                store.create_or_verify_run_manifest(
                    run_key,
                    _run_manifest(binding, arm_id),
                )
            await _sample_missing(
                store=store,
                study_id=protocol["study_id"],
                jobs=jobs,
                tasks=tasks,
                arms=arms,
                protocol=protocol,
                samplers=samplers,
                messages=messages,
            )
            mirrors = {
                arm_id: WandbMetricsMirror(
                    store=store,
                    project=protocol["tracking"]["project"],
                    entity=protocol["tracking"].get("entity"),
                    group=protocol["tracking"].get("group"),
                )
                for arm_id in arms
            }
            trackers = {
                arm_id: stack.enter_context(
                    mirror.session(
                        RunKey(protocol["study_id"], hypothesis_id, arm_id)
                    )
                )
                for arm_id, mirror in mirrors.items()
            }
            _evaluate_missing(
                store=store,
                study_id=protocol["study_id"],
                jobs=jobs,
                tasks=tasks,
                evaluator=evaluator,
                tracker_by_arm=trackers,
            )
            summaries = _write_summaries_and_selection(
                store=store,
                protocol=protocol,
                binding=binding,
                jobs=jobs,
                tasks=tasks,
            )
    return {
        "binding": binding,
        "summaries": summaries,
        "mean_arm_iou": (
            statistics.fmean(
                value["mean_iou_at_1"] for value in summaries.values()
            )
            if summaries
            else 0.0
        ),
    }
