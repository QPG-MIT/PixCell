"""Receipt-bound final-checkpoint F1--F8 best@4 evaluation.

This is deliberately a new, versioned path rather than an extension of the
v1 checkpoint panels.  The progress, depth, and promotion records therefore
keep their original one-attempt semantics and byte contracts.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
import uuid
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
    PixCellEvaluator,
)
from rl.common.prompt import prompt_asset_hashes
from rl.evaluation.tasks import EvaluationTask, canonical_json_sha256
from rl.track_a.tinker_data import _message, _renderer

from . import evaluation as checkpoint_v1
from .dataset_binding import _dataset_binding
from .protocol import (
    STUDY_ID,
    file_sha256,
    load_protocol,
    protocol_path,
    validate_source_sha,
)
from .store import TrainingStore


PANEL_FINAL_BENCHMARK_V2 = "final-benchmark-best4-v2"
FINAL_BENCHMARK_SCHEMA_VERSION = "pixcell-training-final-benchmark-v2"
FINAL_BENCHMARK_RECORD_SCHEMA_VERSION = "pixcell-training-final-benchmark-record-v2"
FINAL_BENCHMARK_TASK_PANEL_SCHEMA_VERSION = "pixcell-training-final-benchmark-task-panel-v2"
ATTEMPTS_PER_TASK = 4
EXPECTED_TASK_IDS = tuple(f"F{index}" for index in range(1, 9))
EXPECTED_ATTEMPTS = len(EXPECTED_TASK_IDS) * ATTEMPTS_PER_TASK
SAMPLE_CONCURRENCY = 8
EVALUATION_BATCH_SIZE = 32
EVALUATOR_WORKERS = 8
MAX_IMAGE_LONG_EDGE = checkpoint_v1.MAX_IMAGE_LONG_EDGE
MAX_OUTPUT_TOKENS = checkpoint_v1.MAX_OUTPUT_TOKENS
TEMPERATURE = checkpoint_v1.TEMPERATURE
TOP_P = checkpoint_v1.TOP_P
_SEED_DOMAIN = "pixcell-representation-training-final-benchmark-v2"
_RESPONSE_FIELDS = {
    "token_ids",
    "completion_tokens",
    "stop_reason",
    "cap_hit",
    "raw_text",
    "raw_text_sha256",
    "answer_text",
    "answer_text_sha256",
    "reasoning_text",
    "reasoning_text_sha256",
    "token_decode_complete",
    "token_decode_error",
    "channel_parse_complete",
    "channel_parse_error",
}
_SAMPLE_PAYLOAD_FIELDS = {
    "final_benchmark_manifest_record_sha256",
    "training_wave_receipt_record_sha256",
    "panel",
    "checkpoint_name",
    "checkpoint_inventory_sha256",
    "checkpoint",
    "task",
    "attempt_index",
    "request",
    "response",
}
_EVALUATION_PAYLOAD_FIELDS = {
    "final_benchmark_manifest_record_sha256",
    "sample_record_sha256",
    "panel",
    "task_id",
    "level",
    "representation_id",
    "attempt_index",
    "seed",
    "status",
    "attribution",
    "pure_executable",
    "raw_absolute_scale_iou",
    "dice",
    "render_sha256",
    "reference_sha256",
    "violations",
    "error",
    "latency_seconds",
    "diagnostics",
}
_REPORT_RECORD_FIELDS = {
    "task_id",
    "attempt_index",
    "seed",
    "status",
    "attribution",
    "pure_executable",
    "raw_absolute_scale_iou",
    "completion_tokens",
    "stop_reason",
    "cap_hit",
    "channel_parse_complete",
    "answer_text_sha256",
    "render_sha256",
    "reference_sha256",
    "violations",
    "error",
    "sample_record_sha256",
    "evaluation_record_sha256",
}
_REPORT_PAYLOAD_FIELDS = {
    "schema_version",
    "study_id",
    "stage_id",
    "wave",
    "checkpoint_name",
    "replicate_id",
    "panel",
    "summary",
    "figures",
    "records",
    "attempt_records_sha256",
    "provenance",
}


class FinalBenchmarkError(checkpoint_v1.CheckpointEvaluationError):
    """The requested final benchmark is unsafe, incomplete, or inconsistent."""


class ImmutableFinalBenchmarkRecordError(checkpoint_v1.ImmutableEvaluationRecordError):
    """A v2 final-benchmark record cannot be replaced or mixed."""


@dataclass(frozen=True)
class PreparedAttempt:
    prepared: checkpoint_v1.PreparedTask
    attempt_index: int
    seed: int

    @property
    def task(self) -> EvaluationTask:
        return self.prepared.task

    @property
    def key(self) -> tuple[str, int]:
        return (self.task.task_id, self.attempt_index)


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise FinalBenchmarkError("final-benchmark record is not finite JSON") from exc


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _record_document(
    *,
    record_type: str,
    key: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = json.loads(_canonical_bytes(payload))
    document = {
        "schema_version": FINAL_BENCHMARK_RECORD_SCHEMA_VERSION,
        "record_type": record_type,
        "key": dict(key),
        "payload": normalized,
        "payload_sha256": _canonical_sha256(normalized),
    }
    document["record_sha256"] = _canonical_sha256(document)
    return document


def _validate_record(
    value: Mapping[str, Any],
    *,
    record_type: str,
    key: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "record_type",
        "key",
        "payload",
        "payload_sha256",
        "record_sha256",
    }
    if set(value) != required:
        raise FinalBenchmarkError("final-benchmark record schema changed")
    if value["schema_version"] != FINAL_BENCHMARK_RECORD_SCHEMA_VERSION:
        raise FinalBenchmarkError("final-benchmark record has a foreign schema")
    if value["record_type"] != record_type or value["key"] != dict(key):
        raise FinalBenchmarkError("final-benchmark record key differs from its canonical path")
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise FinalBenchmarkError("final-benchmark payload is not an object")
    if value["payload_sha256"] != _canonical_sha256(payload):
        raise FinalBenchmarkError("final-benchmark payload digest mismatch")
    unsigned = dict(value)
    observed = unsigned.pop("record_sha256")
    if (
        not isinstance(observed, str)
        or not checkpoint_v1._SHA256.fullmatch(observed)
        or observed != _canonical_sha256(unsigned)
    ):
        raise FinalBenchmarkError("final-benchmark envelope digest mismatch")
    return dict(value)


class FinalBenchmarkStore(checkpoint_v1.CheckpointEvaluationStore):
    """Create-only v2 attempt records in a panel-isolated namespace."""

    def __init__(
        self,
        *,
        stage_path: Path,
        wave: str,
        checkpoint_name: str,
    ) -> None:
        if not checkpoint_v1._IDENTIFIER.fullmatch(wave) or not checkpoint_v1._IDENTIFIER.fullmatch(
            checkpoint_name
        ):
            raise ValueError("invalid final-benchmark identity")
        self.stage_path = stage_path.expanduser().resolve(strict=True)
        requested = (
            self.stage_path / "evaluations" / wave / checkpoint_name / PANEL_FINAL_BENCHMARK_V2
        )
        requested.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = requested.resolve(strict=True)
        if resolved != requested or not resolved.is_relative_to(self.stage_path):
            raise FinalBenchmarkError(
                "final-benchmark root must be a real directory inside its stage"
            )
        self.root = resolved

    @staticmethod
    def _attempt_component(attempt_index: int) -> str:
        if (
            isinstance(attempt_index, bool)
            or not isinstance(attempt_index, int)
            or not 1 <= attempt_index <= ATTEMPTS_PER_TASK
        ):
            raise ValueError(f"attempt index must be in [1, {ATTEMPTS_PER_TASK}]")
        return f"{attempt_index:06d}"

    @staticmethod
    def _attempt_key(task_id: str, attempt_index: int) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "attempt_index": attempt_index,
        }

    def _attempt_path(
        self,
        task_id: str,
        attempt_index: int,
        filename: str,
    ) -> PurePosixPath:
        task = self._task_component(task_id)
        attempt = self._attempt_component(attempt_index)
        return PurePosixPath("attempts", task, attempt, filename)

    def load_manifest(self) -> dict[str, Any] | None:
        return self._load_v2(
            PurePosixPath("manifest.json"),
            record_type="final_benchmark_manifest",
            key={},
        )

    def create_or_verify_manifest(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_v2(
            PurePosixPath("manifest.json"),
            record_type="final_benchmark_manifest",
            key={},
            payload=payload,
        )

    def load_sample(
        self,
        task_id: str,
        attempt_index: int,
    ) -> dict[str, Any] | None:
        return self._load_v2(
            self._attempt_path(task_id, attempt_index, "sample.json"),
            record_type="final_benchmark_sample",
            key=self._attempt_key(task_id, attempt_index),
        )

    def create_or_verify_sample(
        self,
        task_id: str,
        attempt_index: int,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_v2(
            self._attempt_path(task_id, attempt_index, "sample.json"),
            record_type="final_benchmark_sample",
            key=self._attempt_key(task_id, attempt_index),
            payload=payload,
        )

    def load_evaluation(
        self,
        task_id: str,
        attempt_index: int,
    ) -> dict[str, Any] | None:
        return self._load_v2(
            self._attempt_path(task_id, attempt_index, "evaluation.json"),
            record_type="final_benchmark_evaluation",
            key=self._attempt_key(task_id, attempt_index),
        )

    def create_or_verify_evaluation(
        self,
        task_id: str,
        attempt_index: int,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_v2(
            self._attempt_path(task_id, attempt_index, "evaluation.json"),
            record_type="final_benchmark_evaluation",
            key=self._attempt_key(task_id, attempt_index),
            payload=payload,
        )

    def load_report(self) -> dict[str, Any] | None:
        return self._load_v2(
            PurePosixPath("report.json"),
            record_type="final_benchmark_report",
            key={},
        )

    def create_or_verify_report(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_v2(
            PurePosixPath("report.json"),
            record_type="final_benchmark_report",
            key={},
            payload=payload,
        )

    def assert_attempt_inventory(
        self,
        attempts: Sequence[PreparedAttempt],
    ) -> None:
        """Reject foreign rows, alternate indices, and symlinks before resume."""

        attempts_root = self.root / "attempts"
        if not attempts_root.exists():
            return
        expected_files = {
            self._path(
                self._attempt_path(
                    attempt.task.task_id,
                    attempt.attempt_index,
                    filename,
                )
            )
            for attempt in attempts
            for filename in ("sample.json", "evaluation.json")
        }
        expected_directories = {attempts_root}
        for path in expected_files:
            expected_directories.update(path.parents)
        for path in attempts_root.rglob("*"):
            if path.is_symlink():
                raise FinalBenchmarkError(
                    f"final-benchmark attempt inventory contains a symlink: {path}"
                )
            if path.is_file() and path not in expected_files:
                raise FinalBenchmarkError(
                    f"final-benchmark attempt inventory contains a foreign row: {path}"
                )
            if path.is_dir() and path not in expected_directories:
                raise FinalBenchmarkError(
                    "final-benchmark attempt inventory contains an unexpected "
                    f"task or attempt: {path}"
                )

    def _create_or_verify_v2(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        expected = _record_document(
            record_type=record_type,
            key=key,
            payload=payload,
        )
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = _canonical_bytes(expected) + b"\n"
        temporary = path.parent / f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(temporary, flags, 0o600)
            try:
                with os.fdopen(fd, "wb", closefd=False) as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(fd)
            try:
                os.link(temporary, path)
                directory_fd = os.open(path.parent, os.O_RDONLY)
                try:
                    os.fsync(directory_fd)
                finally:
                    os.close(directory_fd)
            except FileExistsError:
                observed = self._load_v2(
                    relative,
                    record_type=record_type,
                    key=key,
                )
                if observed is None or _canonical_bytes(observed) != _canonical_bytes(expected):
                    raise ImmutableFinalBenchmarkRecordError(
                        f"{relative} already contains different data"
                    )
                return observed
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return expected

    def _load_v2(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        path = self._path(relative)
        if not path.exists():
            return None
        return _validate_record(
            self._read(path),
            record_type=record_type,
            key=key,
        )


def _final_checkpoint(
    binding: checkpoint_v1.CheckpointBinding,
) -> None:
    checkpoint = binding.checkpoint
    if (
        checkpoint.get("role") != "terminal"
        or checkpoint.get("final") is not True
        or checkpoint.get("training_progress_fraction") != 1.0
    ):
        raise checkpoint_v1.CheckpointReceiptError(
            "final benchmark requires the terminal checkpoint in its wave receipt"
        )


def _task_panel(tasks: Sequence[EvaluationTask]) -> dict[str, Any]:
    entries = [
        {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
            "image_sha256": task.observation.image_sha256,
            "target_image_sha256": task.reference.target_image_sha256,
            "footprint_um": list(task.observation.footprint_um),
        }
        for task in tasks
    ]
    if tuple(item["task_id"] for item in entries) != EXPECTED_TASK_IDS:
        raise checkpoint_v1.ReferencePanelFault("final benchmark must be exact ordered F1-F8")
    return {
        "schema_version": FINAL_BENCHMARK_TASK_PANEL_SCHEMA_VERSION,
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "task_count": len(entries),
        "task_ids": list(EXPECTED_TASK_IDS),
        "logical_sha256": canonical_json_sha256(entries),
    }


def _sample_seed(
    *,
    source_git_sha: str,
    protocol_sha256: str,
    dataset_sha256: str,
    task_panel_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
    task_id: str,
    attempt_index: int,
) -> int:
    digest = hashlib.sha256(
        "\0".join(
            (
                _SEED_DOMAIN,
                source_git_sha,
                protocol_sha256,
                dataset_sha256,
                task_panel_sha256,
                binding.stage.stage_id,
                binding.wave,
                binding.checkpoint_name,
                binding.checkpoint_inventory_sha256,
                binding.wave_receipt.record_sha256,
                binding.key.replicate_id,
                PANEL_FINAL_BENCHMARK_V2,
                task_id,
                str(attempt_index),
            )
        ).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _attempts(
    *,
    prepared: Sequence[checkpoint_v1.PreparedTask],
    source_git_sha: str,
    protocol_sha256: str,
    dataset_sha256: str,
    task_panel_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
) -> list[PreparedAttempt]:
    attempts = [
        PreparedAttempt(
            prepared=item,
            attempt_index=attempt_index,
            seed=_sample_seed(
                source_git_sha=source_git_sha,
                protocol_sha256=protocol_sha256,
                dataset_sha256=dataset_sha256,
                task_panel_sha256=task_panel_sha256,
                binding=binding,
                task_id=item.task.task_id,
                attempt_index=attempt_index,
            ),
        )
        for item in prepared
        for attempt_index in range(1, ATTEMPTS_PER_TASK + 1)
    ]
    if len(attempts) != EXPECTED_ATTEMPTS:
        raise FinalBenchmarkError(
            f"final benchmark resolved {len(attempts)} attempts, expected {EXPECTED_ATTEMPTS}"
        )
    keys = [attempt.key for attempt in attempts]
    seeds = [attempt.seed for attempt in attempts]
    if len(set(keys)) != EXPECTED_ATTEMPTS:
        raise FinalBenchmarkError("final benchmark resolved duplicate attempt keys")
    if len(set(seeds)) != EXPECTED_ATTEMPTS:
        raise FinalBenchmarkError("final benchmark deterministic seeds collided")
    return attempts


def _seed_inventory(attempts: Sequence[PreparedAttempt]) -> list[dict[str, Any]]:
    return [
        {
            "task_id": attempt.task.task_id,
            "attempt_index": attempt.attempt_index,
            "seed": attempt.seed,
        }
        for attempt in attempts
    ]


def _decode_response(renderer: Any, sequence: Any) -> dict[str, Any]:
    from tinker_cookbook.renderers import get_text_content

    tokens = [int(token) for token in sequence.tokens]
    token_decode_error: str | None = None
    try:
        raw_text = str(renderer.tokenizer.decode(tokens))
    except Exception as exc:
        raw_text = ""
        token_decode_error = str(exc).replace("\x00", "")[-1200:]
    channel_parse_error: str | None = None
    if token_decode_error is not None:
        answer_text = ""
        reasoning_text = ""
        channel_parse_complete = False
    else:
        try:
            message, termination = renderer.parse_response(tokens)
            answer_text = str(get_text_content(message))
            reasoning_text = checkpoint_v1._message_reasoning(message)
            channel_parse_complete = bool(termination.is_clean)
        except Exception as exc:
            # Malformed channel structure is model output.  Keep the exact raw
            # response and let the deterministic evaluator score extracted code.
            answer_text = raw_text
            reasoning_text = ""
            channel_parse_complete = False
            channel_parse_error = str(exc).replace("\x00", "")[-1200:]
    stop_reason = str(sequence.stop_reason)
    cap_hit = (
        len(tokens) >= MAX_OUTPUT_TOKENS
        or "length" in stop_reason.lower()
        or "max_token" in stop_reason.lower()
    )
    return {
        "token_ids": tokens,
        "completion_tokens": len(tokens),
        "stop_reason": stop_reason,
        "cap_hit": cap_hit,
        "raw_text": raw_text,
        "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "answer_text": answer_text,
        "answer_text_sha256": hashlib.sha256(answer_text.encode("utf-8")).hexdigest(),
        "reasoning_text": reasoning_text,
        "reasoning_text_sha256": hashlib.sha256(reasoning_text.encode("utf-8")).hexdigest(),
        "token_decode_complete": token_decode_error is None,
        "token_decode_error": token_decode_error,
        "channel_parse_complete": channel_parse_complete,
        "channel_parse_error": channel_parse_error,
    }


def _sample_payload(
    *,
    attempt: PreparedAttempt,
    response: Mapping[str, Any],
    manifest_record_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
) -> dict[str, Any]:
    prepared = attempt.prepared
    return {
        "final_benchmark_manifest_record_sha256": manifest_record_sha256,
        "training_wave_receipt_record_sha256": (binding.wave_receipt.record_sha256),
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "checkpoint_name": binding.checkpoint_name,
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
        "checkpoint": binding.checkpoint,
        "task": {
            "task_id": prepared.task.task_id,
            "level": prepared.task.level,
            "representation_id": prepared.task.representation_id,
            "image_sha256": prepared.task.observation.image_sha256,
            "target_image_sha256": prepared.task.reference.target_image_sha256,
        },
        "attempt_index": attempt.attempt_index,
        "request": {
            "num_samples": 1,
            "independent_request": True,
            "seed": attempt.seed,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "prompt_tokens": prepared.prompt_tokens,
            "prompt_text_sha256": prepared.prompt_text_sha256,
        },
        "response": dict(response),
    }


def _validate_response(response: Any, *, attempt: PreparedAttempt) -> None:
    if not isinstance(response, Mapping) or set(response) != _RESPONSE_FIELDS:
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} raw response is incomplete")
    tokens = response["token_ids"]
    if (
        not isinstance(tokens, list)
        or any(
            isinstance(token, bool) or not isinstance(token, int) or token < 0 for token in tokens
        )
        or response["completion_tokens"] != len(tokens)
    ):
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} token inventory changed")
    for field in ("raw_text", "answer_text", "reasoning_text"):
        text = response[field]
        if (
            not isinstance(text, str)
            or response[f"{field}_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} {field} digest changed")
    stop_reason = response["stop_reason"]
    expected_cap = len(tokens) >= MAX_OUTPUT_TOKENS or (
        isinstance(stop_reason, str)
        and ("length" in stop_reason.lower() or "max_token" in stop_reason.lower())
    )
    if (
        not isinstance(stop_reason, str)
        or not isinstance(response["cap_hit"], bool)
        or response["cap_hit"] is not expected_cap
        or not isinstance(response["token_decode_complete"], bool)
        or response["token_decode_complete"] is not (response["token_decode_error"] is None)
        or (
            response["token_decode_error"] is not None
            and not isinstance(response["token_decode_error"], str)
        )
        or not isinstance(response["channel_parse_complete"], bool)
        or (
            response["channel_parse_error"] is not None
            and not isinstance(response["channel_parse_error"], str)
        )
        or (response["channel_parse_complete"] and response["channel_parse_error"] is not None)
        or (
            not response["token_decode_complete"]
            and (
                response["channel_parse_complete"]
                or any(response[field] for field in ("raw_text", "answer_text", "reasoning_text"))
            )
        )
    ):
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} response diagnostics changed")


def _validate_sample_record(
    *,
    record: Mapping[str, Any],
    attempt: PreparedAttempt,
    manifest_record_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
) -> None:
    payload = record["payload"]
    if set(payload) != _SAMPLE_PAYLOAD_FIELDS:
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} sample payload schema changed")
    expected_top = {
        "final_benchmark_manifest_record_sha256": manifest_record_sha256,
        "training_wave_receipt_record_sha256": (binding.wave_receipt.record_sha256),
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "checkpoint_name": binding.checkpoint_name,
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
        "checkpoint": binding.checkpoint,
        "attempt_index": attempt.attempt_index,
    }
    for field, expected in expected_top.items():
        if payload.get(field) != expected:
            raise ImmutableFinalBenchmarkRecordError(
                f"{attempt.key} sample belongs to another final benchmark"
            )
    expected_task = {
        "task_id": attempt.task.task_id,
        "level": attempt.task.level,
        "representation_id": attempt.task.representation_id,
        "image_sha256": attempt.task.observation.image_sha256,
        "target_image_sha256": attempt.task.reference.target_image_sha256,
    }
    expected_request = {
        "num_samples": 1,
        "independent_request": True,
        "seed": attempt.seed,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "prompt_tokens": attempt.prepared.prompt_tokens,
        "prompt_text_sha256": attempt.prepared.prompt_text_sha256,
    }
    if payload.get("task") != expected_task or payload.get("request") != expected_request:
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} sample request changed")
    _validate_response(payload.get("response"), attempt=attempt)


def _evaluation_payload(
    *,
    attempt: PreparedAttempt,
    result: EvaluationResult,
    sample_record_sha256: str,
    manifest_record_sha256: str,
) -> dict[str, Any]:
    payload = checkpoint_v1._evaluation_payload(
        task=attempt.task,
        result=result,
        sample_record_sha256=sample_record_sha256,
        manifest_record_sha256=manifest_record_sha256,
    )
    if result.status is not EvaluationStatus.OK:
        payload["raw_absolute_scale_iou"] = 0.0
        payload["dice"] = None
        payload["pure_executable"] = False
    try:
        normalized = json.loads(_canonical_bytes(payload))
    except FinalBenchmarkError as exc:
        raise checkpoint_v1.EvaluationInfrastructureFault(
            f"{attempt.key}: evaluator returned non-finite diagnostics"
        ) from exc
    latency = normalized.get("latency_seconds")
    dice = normalized.get("dice")
    if (
        isinstance(latency, bool)
        or not isinstance(latency, (int, float))
        or not math.isfinite(float(latency))
        or float(latency) < 0.0
        or (
            dice is not None
            and (
                isinstance(dice, bool)
                or not isinstance(dice, (int, float))
                or not math.isfinite(float(dice))
                or not 0.0 <= float(dice) <= 1.0
            )
        )
    ):
        raise checkpoint_v1.EvaluationInfrastructureFault(
            f"{attempt.key}: evaluator returned invalid finite metrics"
        )
    normalized["final_benchmark_manifest_record_sha256"] = normalized.pop(
        "evaluation_manifest_record_sha256"
    )
    normalized["panel"] = PANEL_FINAL_BENCHMARK_V2
    normalized["attempt_index"] = attempt.attempt_index
    normalized["seed"] = attempt.seed
    return normalized


def _validate_evaluation_record(
    *,
    record: Mapping[str, Any],
    attempt: PreparedAttempt,
    sample_record_sha256: str,
    manifest_record_sha256: str,
) -> None:
    payload = record["payload"]
    if set(payload) != _EVALUATION_PAYLOAD_FIELDS:
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} evaluation payload schema changed")
    expected = {
        "final_benchmark_manifest_record_sha256": manifest_record_sha256,
        "sample_record_sha256": sample_record_sha256,
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "task_id": attempt.task.task_id,
        "level": attempt.task.level,
        "representation_id": attempt.task.representation_id,
        "attempt_index": attempt.attempt_index,
        "seed": attempt.seed,
        "attribution": Attribution.MODEL.value,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} evaluation record changed")
    iou = payload.get("raw_absolute_scale_iou")
    latency = payload.get("latency_seconds")
    if (
        isinstance(iou, bool)
        or not isinstance(iou, (int, float))
        or not math.isfinite(float(iou))
        or not 0.0 <= float(iou) <= 1.0
        or isinstance(latency, bool)
        or not isinstance(latency, (int, float))
        or not math.isfinite(float(latency))
        or float(latency) < 0.0
    ):
        raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} has invalid stored metrics")
    status = payload.get("status")
    pure = payload.get("pure_executable")
    if (
        status not in {item.value for item in EvaluationStatus}
        or not isinstance(pure, bool)
        or pure is not (status == EvaluationStatus.OK.value)
        or (not pure and float(iou) != 0.0)
    ):
        raise ImmutableFinalBenchmarkRecordError(
            f"{attempt.key} has inconsistent executable status"
        )
    dice = payload.get("dice")
    violations = payload.get("violations")
    error = payload.get("error")
    diagnostics = payload.get("diagnostics")
    if (
        (
            dice is not None
            and (
                isinstance(dice, bool)
                or not isinstance(dice, (int, float))
                or not math.isfinite(float(dice))
                or not 0.0 <= float(dice) <= 1.0
            )
        )
        or not isinstance(violations, list)
        or any(not isinstance(value, str) for value in violations)
        or (error is not None and not isinstance(error, str))
        or not isinstance(diagnostics, Mapping)
    ):
        raise ImmutableFinalBenchmarkRecordError(
            f"{attempt.key} has malformed evaluator diagnostics"
        )
    for field in ("render_sha256", "reference_sha256"):
        value = payload.get(field)
        if value is not None and not checkpoint_v1._SHA256.fullmatch(str(value)):
            raise ImmutableFinalBenchmarkRecordError(f"{attempt.key} has an invalid {field}")
    # Re-run strict finite normalization over every nested diagnostic.
    try:
        checkpoint_v1._safe_json(payload)
        _canonical_bytes(payload)
    except (
        checkpoint_v1.EvaluationInfrastructureFault,
        FinalBenchmarkError,
    ) as exc:
        raise ImmutableFinalBenchmarkRecordError(
            f"{attempt.key} has non-finite diagnostics"
        ) from exc


async def _sample_missing(
    *,
    attempts: Sequence[PreparedAttempt],
    renderer: Any,
    sampling_client: Any,
    store: FinalBenchmarkStore,
    manifest_record_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
) -> None:
    import tinker

    semaphore = asyncio.Semaphore(SAMPLE_CONCURRENCY)

    async def sample_one(attempt: PreparedAttempt) -> None:
        messages = [_message(attempt.task, max_image=MAX_IMAGE_LONG_EDGE)]
        prompt_text = str(messages[0]["content"][1]["text"])
        if (
            hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
            != attempt.prepared.prompt_text_sha256
        ):
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} prompt text changed after preflight"
            )
        prompt = renderer.build_generation_prompt(messages)
        if int(prompt.length) != attempt.prepared.prompt_tokens:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} prompt changed after preflight"
            )
        async with semaphore:
            try:
                result = await sampling_client.sample_async(
                    prompt=prompt,
                    num_samples=1,
                    sampling_params=tinker.SamplingParams(
                        stop=renderer.get_stop_sequences(),
                        max_tokens=MAX_OUTPUT_TOKENS,
                        temperature=TEMPERATURE,
                        top_p=TOP_P,
                        seed=attempt.seed,
                    ),
                )
            except Exception as exc:
                raise checkpoint_v1.SamplingInfrastructureFault(
                    f"{attempt.key} sampling failed: {exc}"
                ) from exc
        sequences = list(result.sequences)
        if len(sequences) != 1:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} returned {len(sequences)} samples, expected 1"
            )
        response = _decode_response(renderer, sequences[0])
        # This durable record is the boundary before any candidate execution.
        store.create_or_verify_sample(
            attempt.task.task_id,
            attempt.attempt_index,
            _sample_payload(
                attempt=attempt,
                response=response,
                manifest_record_sha256=manifest_record_sha256,
                binding=binding,
            ),
        )
        if not response["token_decode_complete"]:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} raw token IDs were persisted but could not be "
                f"decoded: {response['token_decode_error']}"
            )

    tasks = [asyncio.create_task(sample_one(attempt)) for attempt in attempts]
    try:
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    except BaseException:
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    faults = [outcome for outcome in outcomes if isinstance(outcome, BaseException)]
    if faults:
        # All sibling requests have settled and every successful raw response
        # is durable before the run releases its lock or reports the fault.
        raise faults[0]


def _score_missing(
    *,
    attempts: Sequence[PreparedAttempt],
    evaluator: PixCellEvaluator,
    store: FinalBenchmarkStore,
    manifest_record_sha256: str,
) -> None:
    pending: list[tuple[PreparedAttempt, dict[str, Any]]] = []
    for attempt in attempts:
        sample = store.load_sample(attempt.task.task_id, attempt.attempt_index)
        if sample is None:
            raise FinalBenchmarkError(f"{attempt.key} has no resumable sample")
        response = sample["payload"]["response"]
        if not response["token_decode_complete"]:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} has persisted raw token IDs that the renderer "
                f"could not decode: {response['token_decode_error']}"
            )
        existing = store.load_evaluation(
            attempt.task.task_id,
            attempt.attempt_index,
        )
        if existing is not None:
            _validate_evaluation_record(
                record=existing,
                attempt=attempt,
                sample_record_sha256=str(sample["record_sha256"]),
                manifest_record_sha256=manifest_record_sha256,
            )
            continue
        pending.append((attempt, sample))

    for offset in range(0, len(pending), EVALUATION_BATCH_SIZE):
        batch = pending[offset : offset + EVALUATION_BATCH_SIZE]
        requests = [
            (
                attempt.task.reference,
                str(sample["payload"]["response"]["answer_text"]),
            )
            for attempt, sample in batch
        ]
        try:
            results = evaluator.evaluate_batch(requests)
        except Exception as exc:
            raise checkpoint_v1.EvaluationInfrastructureFault(
                f"isolated final-benchmark batch failed: {exc}"
            ) from exc
        if len(results) != len(batch):
            raise checkpoint_v1.EvaluationInfrastructureFault(
                "isolated evaluator returned a different result count"
            )
        faults: list[checkpoint_v1.CheckpointEvaluationError] = []
        for (attempt, sample), result in zip(batch, results, strict=True):
            try:
                payload = _evaluation_payload(
                    attempt=attempt,
                    result=result,
                    sample_record_sha256=str(sample["record_sha256"]),
                    manifest_record_sha256=manifest_record_sha256,
                )
            except (
                checkpoint_v1.ReferencePanelFault,
                checkpoint_v1.EvaluationInfrastructureFault,
            ) as exc:
                faults.append(exc)
                continue
            store.create_or_verify_evaluation(
                attempt.task.task_id,
                attempt.attempt_index,
                payload,
            )
        if faults:
            raise faults[0]


def _validate_attempt_state(
    *,
    attempts: Sequence[PreparedAttempt],
    store: FinalBenchmarkStore,
    manifest_record_sha256: str,
    binding: checkpoint_v1.CheckpointBinding,
) -> tuple[list[PreparedAttempt], list[PreparedAttempt]]:
    store.assert_attempt_inventory(attempts)
    missing_samples: list[PreparedAttempt] = []
    missing_evaluations: list[PreparedAttempt] = []
    for attempt in attempts:
        sample = store.load_sample(attempt.task.task_id, attempt.attempt_index)
        evaluation = store.load_evaluation(
            attempt.task.task_id,
            attempt.attempt_index,
        )
        if sample is None:
            if evaluation is not None:
                raise ImmutableFinalBenchmarkRecordError(
                    f"{attempt.key} has an evaluation without its raw sample"
                )
            missing_samples.append(attempt)
            missing_evaluations.append(attempt)
            continue
        _validate_sample_record(
            record=sample,
            attempt=attempt,
            manifest_record_sha256=manifest_record_sha256,
            binding=binding,
        )
        response = sample["payload"]["response"]
        if not response["token_decode_complete"] and evaluation is not None:
            raise ImmutableFinalBenchmarkRecordError(
                f"{attempt.key} has an evaluation for an undecodable response"
            )
        if evaluation is None:
            missing_evaluations.append(attempt)
            continue
        _validate_evaluation_record(
            record=evaluation,
            attempt=attempt,
            sample_record_sha256=str(sample["record_sha256"]),
            manifest_record_sha256=manifest_record_sha256,
        )
    return missing_samples, missing_evaluations


def _diagnostics(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not records:
        raise FinalBenchmarkError("cannot summarize an empty attempt set")
    count = len(records)
    completions = [int(record["completion_tokens"]) for record in records]
    pure = sum(bool(record["pure_executable"]) for record in records)
    cap_hits = sum(bool(record["cap_hit"]) for record in records)
    parse_complete = sum(bool(record["channel_parse_complete"]) for record in records)
    return {
        "attempt_count": count,
        "pure_executable_count": pure,
        "pure_executable_rate": pure / count,
        "cap_hit_count": cap_hits,
        "cap_hit_rate": cap_hits / count,
        "channel_parse_complete_count": parse_complete,
        "channel_parse_complete_rate": parse_complete / count,
        "statuses": dict(sorted(Counter(str(record["status"]) for record in records).items())),
        "stop_reasons": dict(
            sorted(Counter(str(record["stop_reason"]) for record in records).items())
        ),
        "completion_tokens": {
            "min": min(completions),
            "max": max(completions),
            "mean": sum(completions) / count,
            "total": sum(completions),
        },
    }


def _summaries(
    records: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    if len(records) != EXPECTED_ATTEMPTS:
        raise FinalBenchmarkError(
            f"final report has {len(records)} attempts, expected {EXPECTED_ATTEMPTS}"
        )
    expected_keys = [
        (task_id, attempt_index)
        for task_id in EXPECTED_TASK_IDS
        for attempt_index in range(1, ATTEMPTS_PER_TASK + 1)
    ]
    observed_keys = [
        (str(record.get("task_id")), record.get("attempt_index")) for record in records
    ]
    if observed_keys != expected_keys or len(set(observed_keys)) != len(observed_keys):
        raise FinalBenchmarkError(
            "final report attempt inventory is incomplete, duplicated, or reordered"
        )
    figures: dict[str, Any] = {}
    best_scores: list[float] = []
    all_scores: list[float] = []
    for task_id in EXPECTED_TASK_IDS:
        figure_records = [record for record in records if record["task_id"] == task_id]
        scores = [
            _unit_metric(
                record["raw_absolute_scale_iou"],
                field=f"{task_id} raw_absolute_scale_iou",
            )
            for record in figure_records
        ]
        all_scores.extend(scores)
        best_scores.append(max(scores))
        figures[task_id] = {
            "mean_at_1_raw_absolute_scale_iou": sum(scores) / len(scores),
            "best_at_4_raw_absolute_scale_iou": max(scores),
            **_diagnostics(figure_records),
        }
    summary = {
        "figure_count": len(EXPECTED_TASK_IDS),
        "mean_at_1_raw_absolute_scale_iou": sum(all_scores) / len(all_scores),
        "best_at_4_raw_absolute_scale_iou": (sum(best_scores) / len(best_scores)),
        **_diagnostics(records),
    }
    return summary, figures


def _unit_metric(value: Any, *, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise FinalBenchmarkError(f"{field} must be finite and in [0, 1]")
    return float(value)


def _report_payload(
    *,
    attempts: Sequence[PreparedAttempt],
    store: FinalBenchmarkStore,
    manifest_record: Mapping[str, Any],
    binding: checkpoint_v1.CheckpointBinding,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    manifest_sha = str(manifest_record["record_sha256"])
    for attempt in attempts:
        sample = store.load_sample(attempt.task.task_id, attempt.attempt_index)
        evaluation = store.load_evaluation(
            attempt.task.task_id,
            attempt.attempt_index,
        )
        if sample is None or evaluation is None:
            raise FinalBenchmarkError(f"{attempt.key} is incomplete")
        _validate_sample_record(
            record=sample,
            attempt=attempt,
            manifest_record_sha256=manifest_sha,
            binding=binding,
        )
        _validate_evaluation_record(
            record=evaluation,
            attempt=attempt,
            sample_record_sha256=str(sample["record_sha256"]),
            manifest_record_sha256=manifest_sha,
        )
        response = sample["payload"]["response"]
        measured = evaluation["payload"]
        records.append(
            {
                "task_id": attempt.task.task_id,
                "attempt_index": attempt.attempt_index,
                "seed": attempt.seed,
                "status": measured["status"],
                "attribution": measured["attribution"],
                "pure_executable": measured["pure_executable"],
                "raw_absolute_scale_iou": measured["raw_absolute_scale_iou"],
                "completion_tokens": response["completion_tokens"],
                "stop_reason": response["stop_reason"],
                "cap_hit": response["cap_hit"],
                "channel_parse_complete": response["channel_parse_complete"],
                "answer_text_sha256": response["answer_text_sha256"],
                "render_sha256": measured["render_sha256"],
                "reference_sha256": measured["reference_sha256"],
                "violations": measured["violations"],
                "error": measured["error"],
                "sample_record_sha256": sample["record_sha256"],
                "evaluation_record_sha256": evaluation["record_sha256"],
            }
        )
    summary, figures = _summaries(records)
    return {
        "schema_version": FINAL_BENCHMARK_SCHEMA_VERSION,
        "study_id": STUDY_ID,
        "stage_id": binding.stage.stage_id,
        "wave": binding.wave,
        "checkpoint_name": binding.checkpoint_name,
        "replicate_id": binding.key.replicate_id,
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "summary": summary,
        "figures": figures,
        "records": records,
        "attempt_records_sha256": canonical_json_sha256(records),
        "provenance": {
            "final_benchmark_manifest_record_sha256": manifest_sha,
            "manifest": manifest_record["payload"],
        },
    }


def validate_final_benchmark_report(
    record: Mapping[str, Any],
    *,
    manifest_record: Mapping[str, Any],
    binding: checkpoint_v1.CheckpointBinding,
    attempts: Sequence[PreparedAttempt],
) -> dict[str, Any]:
    """Validate a complete best@4 report without trusting claimed aggregates."""

    validated = _validate_record(
        record,
        record_type="final_benchmark_report",
        key={},
    )
    payload = validated["payload"]
    if set(payload) != _REPORT_PAYLOAD_FIELDS:
        raise FinalBenchmarkError("final-benchmark report payload schema changed")
    expected_identity = {
        "schema_version": FINAL_BENCHMARK_SCHEMA_VERSION,
        "study_id": STUDY_ID,
        "stage_id": binding.stage.stage_id,
        "wave": binding.wave,
        "checkpoint_name": binding.checkpoint_name,
        "replicate_id": binding.key.replicate_id,
        "panel": PANEL_FINAL_BENCHMARK_V2,
    }
    for field, expected in expected_identity.items():
        if payload.get(field) != expected:
            raise FinalBenchmarkError(f"final-benchmark report {field} differs from its request")
    records = payload.get("records")
    provenance = payload.get("provenance")
    if not isinstance(records, list) or not isinstance(provenance, Mapping):
        raise FinalBenchmarkError("final-benchmark report is incomplete")
    if (
        provenance.get("final_benchmark_manifest_record_sha256") != manifest_record["record_sha256"]
        or provenance.get("manifest") != manifest_record["payload"]
    ):
        raise FinalBenchmarkError("final-benchmark report provenance differs from its manifest")
    if len(attempts) != EXPECTED_ATTEMPTS:
        raise FinalBenchmarkError("validator did not receive the sealed 32 attempts")
    expected_keys = [attempt.key for attempt in attempts]
    observed_keys: list[tuple[str, int]] = []
    for row, attempt in zip(records, attempts, strict=False):
        if not isinstance(row, Mapping) or set(row) != _REPORT_RECORD_FIELDS:
            raise FinalBenchmarkError("final-benchmark attempt row is incomplete")
        key = (str(row.get("task_id")), row.get("attempt_index"))
        observed_keys.append(key)
        if key != attempt.key or row.get("seed") != attempt.seed:
            raise FinalBenchmarkError(
                "final-benchmark attempt row has the wrong task, index, or seed"
            )
        _unit_metric(
            row.get("raw_absolute_scale_iou"),
            field=f"{attempt.key} raw_absolute_scale_iou",
        )
        if (
            row.get("attribution") != Attribution.MODEL.value
            or row.get("status") not in {item.value for item in EvaluationStatus}
            or not isinstance(row.get("pure_executable"), bool)
            or not isinstance(row.get("cap_hit"), bool)
            or not isinstance(row.get("channel_parse_complete"), bool)
            or isinstance(row.get("completion_tokens"), bool)
            or not isinstance(row.get("completion_tokens"), int)
            or row["completion_tokens"] < 0
        ):
            raise FinalBenchmarkError(f"{attempt.key} attempt diagnostics are invalid")
        expected_cap = (
            row["completion_tokens"] >= MAX_OUTPUT_TOKENS
            or "length" in str(row["stop_reason"]).lower()
            or "max_token" in str(row["stop_reason"]).lower()
        )
        if (
            row["pure_executable"] is not (row["status"] == EvaluationStatus.OK.value)
            or (not row["pure_executable"] and float(row["raw_absolute_scale_iou"]) != 0.0)
            or not isinstance(row.get("stop_reason"), str)
            or row["cap_hit"] is not expected_cap
            or not isinstance(row.get("violations"), list)
            or any(not isinstance(value, str) for value in row["violations"])
            or (row.get("error") is not None and not isinstance(row["error"], str))
        ):
            raise FinalBenchmarkError(f"{attempt.key} attempt status is internally inconsistent")
        for field in (
            "answer_text_sha256",
            "sample_record_sha256",
            "evaluation_record_sha256",
        ):
            if not checkpoint_v1._SHA256.fullmatch(str(row.get(field, ""))):
                raise FinalBenchmarkError(f"{attempt.key} {field} is not a SHA-256")
        for field in ("render_sha256", "reference_sha256"):
            value = row.get(field)
            if value is not None and not checkpoint_v1._SHA256.fullmatch(str(value)):
                raise FinalBenchmarkError(f"{attempt.key} {field} is not a SHA-256")
    if (
        len(records) != EXPECTED_ATTEMPTS
        or observed_keys != expected_keys
        or len(set(observed_keys)) != EXPECTED_ATTEMPTS
    ):
        raise FinalBenchmarkError("final-benchmark report has incomplete or duplicate attempt rows")
    summary, figures = _summaries(records)
    if payload.get("summary") != summary or payload.get("figures") != figures:
        raise FinalBenchmarkError("final-benchmark claimed metrics differ from its 32 attempts")
    if payload.get("attempt_records_sha256") != canonical_json_sha256(records):
        raise FinalBenchmarkError("final-benchmark attempt-set digest changed")
    return validated


def _manifest_payload(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    source_git_sha: str,
    dataset: Mapping[str, Any],
    task_panel: Mapping[str, Any],
    model: Mapping[str, Any],
    preflight: Mapping[str, Any],
    sandbox: Mapping[str, Any],
    binding: checkpoint_v1.CheckpointBinding,
    attempts: Sequence[PreparedAttempt],
) -> dict[str, Any]:
    seeds = _seed_inventory(attempts)
    return {
        "schema_version": FINAL_BENCHMARK_SCHEMA_VERSION,
        "study_id": STUDY_ID,
        "stage_id": binding.stage.stage_id,
        "wave": binding.wave,
        "checkpoint_name": binding.checkpoint_name,
        "replicate_id": binding.key.replicate_id,
        "panel": PANEL_FINAL_BENCHMARK_V2,
        "source_git_sha": source_git_sha,
        "protocol": {
            "logical_sha256": protocol["logical_sha256"],
            "file_sha256": file_sha256(protocol_path(repo_root)),
            "contract_version": protocol["contract_version"],
        },
        "dataset": {
            "repo_id": protocol["dataset"]["repo_id"],
            "revision": protocol["dataset"]["revision"],
            "configuration": protocol["dataset"]["configuration"],
            "split": "fixed-f1-f8",
            **dict(dataset),
        },
        "task_panel": dict(task_panel),
        "prompt": {
            "contract_version": protocol["contract_version"],
            "assets": prompt_asset_hashes(),
            "prompt_set_sha256": preflight["prompt_set_sha256"],
            "prompt_tokens": preflight["prompt_tokens"],
            "minimum_context_headroom": preflight["minimum_context_headroom"],
        },
        "model": {
            "model_key": binding.stage.model_key,
            **dict(model),
        },
        "sampler": {
            "sampler_path": binding.sampler_path,
            "checkpoint_name": binding.checkpoint_name,
            "checkpoint": binding.checkpoint,
            "checkpoint_inventory_sha256": (binding.checkpoint_inventory_sha256),
            "training_run_manifest_record_sha256": (binding.run_manifest.record_sha256),
            "training_wave_receipt_record_sha256": (binding.wave_receipt.record_sha256),
            "training_wave_receipt_relative_path": str(binding.wave_receipt.relative_path),
        },
        "sandbox": dict(sandbox),
        "reference_set_sha256": preflight["reference_set_sha256"],
        "sampling": {
            "attempts_per_task": ATTEMPTS_PER_TASK,
            "task_count": len(EXPECTED_TASK_IDS),
            "total_attempts": EXPECTED_ATTEMPTS,
            "independent_requests": True,
            "num_samples_per_request": 1,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
            "sample_concurrency": SAMPLE_CONCURRENCY,
            "evaluation_batch_size": EVALUATION_BATCH_SIZE,
            "evaluator_workers": EVALUATOR_WORKERS,
            "seed_algorithm": ("sha256-bound deterministic 31-bit seed with attempt index"),
            "seed_domain": _SEED_DOMAIN,
            "seeds": seeds,
            "seeds_sha256": canonical_json_sha256(seeds),
        },
    }


def _default_evaluator_factory() -> PixCellEvaluator:
    return PixCellEvaluator(
        max_workers=EVALUATOR_WORKERS,
        evaluator_retries=1,
        require_isolation=True,
    )


def _default_service_client_factory() -> Any:
    import tinker

    return tinker.ServiceClient()


async def run_final_benchmark(
    *,
    repo_root: Path,
    stage_id: str,
    wave: str,
    checkpoint_name: str,
    replicate_id: str,
    expected_source_sha: str,
    expected_wave_receipt_sha256: str,
    external_root: Path,
    confirmation: str,
    service_client_factory: Callable[[], Any] = _default_service_client_factory,
    evaluator_factory: Callable[[], PixCellEvaluator] = _default_evaluator_factory,
) -> dict[str, Any]:
    """Run or resume the exact 32-attempt final-checkpoint best@4 panel."""

    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    source_git_sha = validate_source_sha(root, expected_source_sha)
    if confirmation != protocol["launch"]["confirmation_token"]:
        raise FinalBenchmarkError("explicit paid-evaluation confirmation is missing")
    if replicate_id not in protocol["launch"]["replicates"]:
        raise FinalBenchmarkError("replicate is not declared in the protocol")
    if protocol["evaluation"].get("final_benchmark_attempts") != ATTEMPTS_PER_TASK:
        raise FinalBenchmarkError("protocol no longer seals four final-benchmark attempts")

    training_store = TrainingStore(
        repo_root=root,
        external_root=external_root,
    )
    binding = checkpoint_v1._load_checkpoint_binding(
        store=training_store,
        protocol=protocol,
        stage_id=stage_id,
        wave=wave,
        checkpoint_name=checkpoint_name,
        replicate_id=replicate_id,
        expected_receipt_sha256=expected_wave_receipt_sha256,
        source_git_sha=source_git_sha,
    )
    _final_checkpoint(binding)
    model = checkpoint_v1._model_binding(protocol, binding.stage)
    dataset = _dataset_binding(root / "dataset", protocol)
    tasks = checkpoint_v1._benchmark_tasks(repo_root=root, protocol=protocol)
    task_panel = _task_panel(tasks)
    renderer = _renderer(
        model["model"],
        model["renderer"],
        effort=model.get("effort"),
    )
    evaluator = evaluator_factory()
    try:
        prepared, preflight = checkpoint_v1._preflight_tasks(
            tasks=tasks,
            renderer=renderer,
            evaluator=evaluator,
            context_tokens=int(model["context_tokens"]),
        )
        sandbox = checkpoint_v1._sandbox_provenance(evaluator)
        attempts = _attempts(
            prepared=prepared,
            source_git_sha=source_git_sha,
            protocol_sha256=str(protocol["logical_sha256"]),
            dataset_sha256=str(dataset["logical_release_sha256"]),
            task_panel_sha256=str(task_panel["logical_sha256"]),
            binding=binding,
        )
        store = FinalBenchmarkStore(
            stage_path=training_store.stage_path(binding.key),
            wave=wave,
            checkpoint_name=binding.checkpoint_name,
        )
        with store.acquire_lock():
            manifest_payload = _manifest_payload(
                repo_root=root,
                protocol=protocol,
                source_git_sha=source_git_sha,
                dataset=dataset,
                task_panel=task_panel,
                model=model,
                preflight=preflight,
                sandbox=sandbox,
                binding=binding,
                attempts=attempts,
            )
            manifest = store.create_or_verify_manifest(manifest_payload)
            missing_samples, missing_evaluations = _validate_attempt_state(
                attempts=attempts,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
                binding=binding,
            )
            existing_report = store.load_report()
            if existing_report is not None:
                if missing_samples or missing_evaluations:
                    raise FinalBenchmarkError(
                        "final-benchmark report exists with incomplete attempt rows"
                    )
                expected_payload = _report_payload(
                    attempts=attempts,
                    store=store,
                    manifest_record=manifest,
                    binding=binding,
                )
                observed = store.create_or_verify_report(expected_payload)
                validate_final_benchmark_report(
                    observed,
                    manifest_record=manifest,
                    binding=binding,
                    attempts=attempts,
                )
                return {
                    "status": "already_complete",
                    "stage_id": binding.stage.stage_id,
                    "wave": binding.wave,
                    "checkpoint_name": binding.checkpoint_name,
                    "panel": PANEL_FINAL_BENCHMARK_V2,
                    "report": str(store.root / "report.json"),
                    "report_record_sha256": observed["record_sha256"],
                    "summary": observed["payload"]["summary"],
                }

            if missing_samples:
                if not os.environ.get("TINKER_API_KEY"):
                    raise FinalBenchmarkError("TINKER_API_KEY is not present")
                # Every prompt, reference, existing record, receipt, sandbox,
                # seed, and manifest has passed before this paid-capable object.
                service = service_client_factory()
                sampling_client = service.create_sampling_client(model_path=binding.sampler_path)
                await _sample_missing(
                    attempts=missing_samples,
                    renderer=renderer,
                    sampling_client=sampling_client,
                    store=store,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                    binding=binding,
                )

            missing_samples, _ = _validate_attempt_state(
                attempts=attempts,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
                binding=binding,
            )
            if missing_samples:
                raise FinalBenchmarkError("sampling did not persist all 32 raw responses")
            _score_missing(
                attempts=attempts,
                evaluator=evaluator,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
            )
            missing_samples, missing_evaluations = _validate_attempt_state(
                attempts=attempts,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
                binding=binding,
            )
            if missing_samples or missing_evaluations:
                raise FinalBenchmarkError(
                    "final benchmark is incomplete after deterministic evaluation"
                )
            report_payload = _report_payload(
                attempts=attempts,
                store=store,
                manifest_record=manifest,
                binding=binding,
            )
            report = store.create_or_verify_report(report_payload)
            validate_final_benchmark_report(
                report,
                manifest_record=manifest,
                binding=binding,
                attempts=attempts,
            )
            return {
                "status": "complete",
                "stage_id": binding.stage.stage_id,
                "wave": binding.wave,
                "checkpoint_name": binding.checkpoint_name,
                "panel": PANEL_FINAL_BENCHMARK_V2,
                "report": str(store.root / "report.json"),
                "report_record_sha256": report["record_sha256"],
                "summary": report_payload["summary"],
            }
    finally:
        evaluator.close()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--stage", required=True)
    result.add_argument("--wave", required=True)
    result.add_argument("--checkpoint-name", required=True)
    result.add_argument("--replicate", default="r0")
    result.add_argument("--source-git-sha", required=True)
    result.add_argument("--wave-receipt-record-sha256", required=True)
    result.add_argument("--external-root", type=Path, required=True)
    result.add_argument("--confirm-spend", default="")
    return result


def main() -> None:
    args = parser().parse_args()
    report = asyncio.run(
        run_final_benchmark(
            repo_root=args.repo_root,
            stage_id=args.stage,
            wave=args.wave,
            checkpoint_name=args.checkpoint_name,
            replicate_id=args.replicate,
            expected_source_sha=args.source_git_sha,
            expected_wave_receipt_sha256=args.wave_receipt_record_sha256,
            external_root=args.external_root,
            confirmation=args.confirm_spend,
        )
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
