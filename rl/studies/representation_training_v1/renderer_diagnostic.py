"""Sealed, non-canonical diagnostic for the mixed-SFT Qwen renderer mismatch.

This module answers one narrow postmortem question: did the mixed-SFT adapter
learn a usable direct-code policy behind the closed-thinking prefix it saw
during teacher forcing, and when did canonical open-thinking generation
degrade?

It is intentionally not an evaluation panel.  Its records live below
``diagnostics/``, use a foreign record schema, carry an explicit
``not_canonical_evidence`` marker, and cannot satisfy any promotion gate.
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

from tinker_cookbook.renderers import Message, TextPart, TrainOnWhat

from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
    PixCellEvaluator,
)
from rl.common.output import extract_code
from rl.common.prompt import prompt_asset_hashes
from rl.common.runtime import validate_runtime_stack
from rl.evaluation.tasks import EvaluationTask, canonical_json_sha256
from rl.track_a.tinker_data import _message, _renderer

from . import evaluation as checkpoint_v1
from . import source_transition as source_transition_v2
from .preflight import (
    _cookbook_source_binding,
    _dataset_binding,
    _positive_target_text,
)
from .protocol import (
    STUDY_ID,
    file_sha256,
    load_protocol,
    protocol_path,
    stage_spec,
    validate_source_sha,
)
from .schedule import stage_tasks
from .store import TrainingStore


DIAGNOSTIC_ID = "qwen-sft-renderer-diagnostic-v1"
DIAGNOSTIC_SCHEMA_VERSION = "pixcell-qwen-sft-renderer-diagnostic-v1"
DIAGNOSTIC_RECORD_SCHEMA_VERSION = "pixcell-qwen-sft-renderer-diagnostic-record-v1"
TASK_PANEL_SCHEMA_VERSION = "pixcell-qwen-renderer-diagnostic-task-panel-v1"
PRODUCER_SOURCE_GIT_SHA = "bb80dbe666c7313f9a9f3bdb53765c35dfdeceab"
PRODUCER_STAGE_ID = "qwen-mixed-sft"
PRODUCER_WAVE = "complete"
PRODUCER_REPLICATE_ID = "r0"
EXPECTED_TASK_IDS = tuple(f"F{index}" for index in range(1, 9))
MAX_IMAGE_LONG_EDGE = 1920
MAX_OUTPUT_TOKENS = 60_000
TEMPERATURE = 1.0
TOP_P = 1.0
SAMPLE_CONCURRENCY = 8
EVALUATION_BATCH_SIZE = 32
EVALUATOR_WORKERS = 8
_SEED_DOMAIN = "pixcell-qwen-sft-renderer-diagnostic-seed-v1"
_PROMOTION_POLICY = "diagnostic-only-never-promotion-evidence"
_PROMPT_SOURCE_PATHS = (
    "rl/common/assets/phase_a_direct_v2.md",
    "src/michaelangelo/reference/gds_factory_function_catalogue_extended.md",
)


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    checkpoint_name: str
    renderer: str
    expected_sft_prefix_compatible: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "checkpoint_name": self.checkpoint_name,
            "renderer": self.renderer,
            "expected_sft_prefix_compatible": (self.expected_sft_prefix_compatible),
        }


ARM_SPECS = (
    ArmSpec(
        arm_id="final-no-thinking",
        checkpoint_name="final",
        renderer="qwen3_5_disable_thinking",
        expected_sft_prefix_compatible=True,
    ),
    ArmSpec(
        arm_id="step-14-thinking",
        checkpoint_name="000014",
        renderer="qwen3_5",
        expected_sft_prefix_compatible=False,
    ),
    ArmSpec(
        arm_id="step-28-thinking",
        checkpoint_name="000028",
        renderer="qwen3_5",
        expected_sft_prefix_compatible=False,
    ),
    ArmSpec(
        arm_id="step-42-thinking",
        checkpoint_name="000042",
        renderer="qwen3_5",
        expected_sft_prefix_compatible=False,
    ),
)
EXPECTED_CHECKPOINT_NAMES = ("000014", "000028", "000042", "final")
EXPECTED_SAMPLE_COUNT = len(ARM_SPECS) * len(EXPECTED_TASK_IDS)


class RendererDiagnosticError(checkpoint_v1.CheckpointEvaluationError):
    """The renderer diagnostic is unsafe, inconsistent, or incomplete."""


class ImmutableRendererDiagnosticError(checkpoint_v1.ImmutableEvaluationRecordError):
    """A create-only diagnostic record already differs."""


@dataclass(frozen=True)
class PreparedArm:
    spec: ArmSpec
    binding: checkpoint_v1.CheckpointBinding
    renderer: Any
    prepared: tuple[checkpoint_v1.PreparedTask, ...]
    preflight: dict[str, Any]


@dataclass(frozen=True)
class PreparedAttempt:
    arm: PreparedArm
    prepared: checkpoint_v1.PreparedTask
    seed: int

    @property
    def task(self) -> EvaluationTask:
        return self.prepared.task

    @property
    def key(self) -> tuple[str, str]:
        return (self.arm.spec.arm_id, self.task.task_id)


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
        raise RendererDiagnosticError("renderer diagnostic is not finite JSON") from exc


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
        "schema_version": DIAGNOSTIC_RECORD_SCHEMA_VERSION,
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
        raise RendererDiagnosticError("diagnostic record schema changed")
    if value["schema_version"] != DIAGNOSTIC_RECORD_SCHEMA_VERSION:
        raise RendererDiagnosticError("diagnostic record has a foreign schema")
    if value["record_type"] != record_type or value["key"] != dict(key):
        raise RendererDiagnosticError("diagnostic record key differs from its canonical path")
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise RendererDiagnosticError("diagnostic payload is not an object")
    if payload.get("not_canonical_evidence") is not True:
        raise RendererDiagnosticError("diagnostic record lost its non-canonical marker")
    if value["payload_sha256"] != _canonical_sha256(payload):
        raise RendererDiagnosticError("diagnostic payload digest mismatch")
    unsigned = dict(value)
    observed = unsigned.pop("record_sha256")
    if (
        not isinstance(observed, str)
        or not checkpoint_v1._SHA256.fullmatch(observed)
        or observed != _canonical_sha256(unsigned)
    ):
        raise RendererDiagnosticError("diagnostic envelope digest mismatch")
    return dict(value)


class RendererDiagnosticStore(checkpoint_v1.CheckpointEvaluationStore):
    """Create-only records in a namespace promotion code never reads."""

    def __init__(self, *, stage_path: Path) -> None:
        self.stage_path = stage_path.expanduser().resolve(strict=True)
        requested = self.stage_path / "diagnostics" / DIAGNOSTIC_ID
        requested.mkdir(parents=True, exist_ok=True, mode=0o700)
        resolved = requested.resolve(strict=True)
        if resolved != requested or not resolved.is_relative_to(self.stage_path):
            raise RendererDiagnosticError(
                "diagnostic root must be a real directory inside its stage"
            )
        if "evaluations" in resolved.relative_to(self.stage_path).parts:
            raise RendererDiagnosticError(
                "diagnostic records must not enter the evaluation namespace"
            )
        self.root = resolved

    @staticmethod
    def _arm_component(arm_id: str) -> str:
        expected = {spec.arm_id for spec in ARM_SPECS}
        if arm_id not in expected:
            raise ValueError(f"foreign diagnostic arm: {arm_id!r}")
        return arm_id

    @classmethod
    def _attempt_key(cls, arm_id: str, task_id: str) -> dict[str, str]:
        cls._arm_component(arm_id)
        cls._task_component(task_id)
        return {"arm_id": arm_id, "task_id": task_id}

    @classmethod
    def _attempt_path(
        cls,
        arm_id: str,
        task_id: str,
        filename: str,
    ) -> PurePosixPath:
        return PurePosixPath(
            "arms",
            cls._arm_component(arm_id),
            "tasks",
            cls._task_component(task_id),
            filename,
        )

    def load_manifest(self) -> dict[str, Any] | None:
        return self._load_diagnostic(
            PurePosixPath("manifest.json"),
            record_type="renderer_diagnostic_manifest",
            key={},
        )

    def create_or_verify_manifest(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_diagnostic(
            PurePosixPath("manifest.json"),
            record_type="renderer_diagnostic_manifest",
            key={},
            payload=payload,
        )

    def load_sample(
        self,
        arm_id: str,
        task_id: str,
    ) -> dict[str, Any] | None:
        return self._load_diagnostic(
            self._attempt_path(arm_id, task_id, "sample.json"),
            record_type="renderer_diagnostic_sample",
            key=self._attempt_key(arm_id, task_id),
        )

    def create_or_verify_sample(
        self,
        arm_id: str,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_diagnostic(
            self._attempt_path(arm_id, task_id, "sample.json"),
            record_type="renderer_diagnostic_sample",
            key=self._attempt_key(arm_id, task_id),
            payload=payload,
        )

    def load_evaluation(
        self,
        arm_id: str,
        task_id: str,
    ) -> dict[str, Any] | None:
        return self._load_diagnostic(
            self._attempt_path(arm_id, task_id, "evaluation.json"),
            record_type="renderer_diagnostic_evaluation",
            key=self._attempt_key(arm_id, task_id),
        )

    def create_or_verify_evaluation(
        self,
        arm_id: str,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_diagnostic(
            self._attempt_path(arm_id, task_id, "evaluation.json"),
            record_type="renderer_diagnostic_evaluation",
            key=self._attempt_key(arm_id, task_id),
            payload=payload,
        )

    def load_report(self) -> dict[str, Any] | None:
        return self._load_diagnostic(
            PurePosixPath("report.json"),
            record_type="renderer_diagnostic_report",
            key={},
        )

    def create_or_verify_report(
        self,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._create_or_verify_diagnostic(
            PurePosixPath("report.json"),
            record_type="renderer_diagnostic_report",
            key={},
            payload=payload,
        )

    def assert_attempt_inventory(
        self,
        attempts: Sequence[PreparedAttempt],
    ) -> None:
        arms_root = self.root / "arms"
        expected_files = {
            self._path(
                self._attempt_path(
                    attempt.arm.spec.arm_id,
                    attempt.task.task_id,
                    filename,
                )
            )
            for attempt in attempts
            for filename in ("sample.json", "evaluation.json")
        }
        expected_files.update(
            {
                self.root / ".lock",
                self.root / "manifest.json",
                self.root / "report.json",
            }
        )
        expected_directories = {self.root, arms_root}
        for path in expected_files:
            expected_directories.update(path.parents)
        for path in self.root.rglob("*"):
            if path.is_symlink():
                raise RendererDiagnosticError(
                    f"diagnostic record inventory contains a symlink: {path}"
                )
            if path.is_file() and path not in expected_files:
                raise RendererDiagnosticError(
                    f"diagnostic record inventory contains a foreign row: {path}"
                )
            if path.is_dir() and path not in expected_directories:
                raise RendererDiagnosticError(
                    f"diagnostic record inventory contains a foreign path: {path}"
                )

    def _create_or_verify_diagnostic(
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
                observed = self._load_diagnostic(
                    relative,
                    record_type=record_type,
                    key=key,
                )
                if observed is None or _canonical_bytes(observed) != _canonical_bytes(expected):
                    raise ImmutableRendererDiagnosticError(
                        f"{relative} already contains different data"
                    )
                return observed
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return expected

    def _load_diagnostic(
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


def _not_canonical() -> dict[str, Any]:
    return {
        "not_canonical_evidence": True,
        "promotion_eligibility": {
            "eligible": False,
            "policy": _PROMOTION_POLICY,
        },
    }


def _validate_fixed_protocol(protocol: Mapping[str, Any]) -> dict[str, Any]:
    stage = stage_spec(dict(protocol), PRODUCER_STAGE_ID)
    model = dict(protocol["models"][stage.model_key])
    recipe = dict(protocol["recipes"][stage.recipe_key])
    if (
        stage.kind != "sft"
        or stage.model_key != "qwen"
        or stage.recipe_key != "qwen_sft"
        or stage.wave(PRODUCER_WAVE)["max_steps"] != 55
    ):
        raise RendererDiagnosticError("producer SFT stage contract changed")
    expected_model = {
        "model": "Qwen/Qwen3.6-35B-A3B",
        "renderer": "qwen3_5",
        "thinking": True,
        "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "context_tokens": 65_536,
        "lora_rank": 32,
    }
    if model != expected_model:
        raise RendererDiagnosticError("Qwen model contract changed")
    if (
        recipe.get("target") != "program_and_end_token_only"
        or recipe.get("max_sequence_tokens") != 6144
    ):
        raise RendererDiagnosticError("SFT target contract changed")
    return {
        "stage": stage,
        "model": model,
        "recipe": recipe,
    }


def _source_provenance(
    *,
    repo_root: Path,
    evaluator_source_git_sha: str,
) -> dict[str, Any]:
    facts = source_transition_v2.source_transition_git_facts(
        repo_root=repo_root,
        producer_source_git_sha=PRODUCER_SOURCE_GIT_SHA,
        consumer_source_git_sha=evaluator_source_git_sha,
    )
    paths = (str(protocol_path(repo_root).relative_to(repo_root)), *_PROMPT_SOURCE_PATHS)
    bindings: dict[str, Any] = {}
    for relative in paths:
        producer_bytes = source_transition_v2._git(
            repo_root,
            "show",
            f"{PRODUCER_SOURCE_GIT_SHA}:{relative}",
        )
        current_path = (repo_root / relative).resolve(strict=True)
        if not current_path.is_relative_to(repo_root):
            raise RendererDiagnosticError("source binding escaped the repository")
        current_bytes = current_path.read_bytes()
        producer_sha = hashlib.sha256(producer_bytes).hexdigest()
        current_sha = hashlib.sha256(current_bytes).hexdigest()
        if producer_sha != current_sha:
            raise RendererDiagnosticError(
                f"producer and evaluator task contract differ: {relative}"
            )
        bindings[relative] = {
            "producer_sha256": producer_sha,
            "evaluator_sha256": current_sha,
            "byte_identical": True,
        }
    return {
        "producer_source_git_sha": PRODUCER_SOURCE_GIT_SHA,
        "evaluator_source_git_sha": evaluator_source_git_sha,
        "git_relationship": facts,
        "task_contract_files": bindings,
        "task_contract_files_sha256": _canonical_sha256(bindings),
    }


def _load_matrix_bindings(
    *,
    store: TrainingStore,
    protocol: dict[str, Any],
    expected_wave_receipt_sha256: str,
) -> tuple[checkpoint_v1.CheckpointBinding, ...]:
    bindings = tuple(
        checkpoint_v1._load_checkpoint_binding(
            store=store,
            protocol=protocol,
            stage_id=PRODUCER_STAGE_ID,
            wave=PRODUCER_WAVE,
            checkpoint_name=spec.checkpoint_name,
            replicate_id=PRODUCER_REPLICATE_ID,
            expected_receipt_sha256=expected_wave_receipt_sha256,
            source_git_sha=PRODUCER_SOURCE_GIT_SHA,
        )
        for spec in ARM_SPECS
    )
    receipts = {binding.wave_receipt.record_sha256 for binding in bindings}
    inventories = {binding.checkpoint_inventory_sha256 for binding in bindings}
    manifests = {binding.run_manifest.record_sha256 for binding in bindings}
    if len(receipts) != 1 or len(inventories) != 1 or len(manifests) != 1:
        raise RendererDiagnosticError("matrix checkpoints do not share one exact producer receipt")
    inventory = bindings[0].wave_receipt.payload["checkpoint_inventory"]
    entries = inventory["entries"]
    if tuple(str(entry["name"]) for entry in entries) != EXPECTED_CHECKPOINT_NAMES:
        raise RendererDiagnosticError(
            "producer checkpoint inventory differs from the sealed matrix"
        )
    expected_paths = {
        spec.checkpoint_name: binding.sampler_path
        for spec, binding in zip(ARM_SPECS, bindings, strict=True)
    }
    if len(set(expected_paths.values())) != len(ARM_SPECS):
        raise RendererDiagnosticError("producer checkpoint sampler paths are not unique")
    return bindings


def _producer_training_provenance(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    bindings: Sequence[checkpoint_v1.CheckpointBinding],
) -> dict[str, Any]:
    first = bindings[0]
    manifest = first.run_manifest
    receipt = first.wave_receipt
    payload = manifest.payload
    expected_manifest_fields = {
        "source_git_sha": PRODUCER_SOURCE_GIT_SHA,
        "protocol_logical_sha256": protocol["logical_sha256"],
        "protocol_file_sha256": file_sha256(protocol_path(repo_root)),
        "contract_version": protocol["contract_version"],
        "prompt_assets": prompt_asset_hashes(),
        "model": protocol["models"]["qwen"],
        "recipe": protocol["recipes"]["qwen_sft"],
    }
    for field, expected in expected_manifest_fields.items():
        if payload.get(field) != expected:
            raise RendererDiagnosticError(f"producer training manifest {field} changed")
    stage = payload.get("stage")
    dataset = payload.get("dataset")
    if (
        not isinstance(stage, Mapping)
        or stage.get("stage_id") != PRODUCER_STAGE_ID
        or stage.get("kind") != "sft"
        or stage.get("model_key") != "qwen"
        or stage.get("recipe_key") != "qwen_sft"
        or not isinstance(dataset, Mapping)
        or dataset.get("logical_release_sha256") != protocol["dataset"]["logical_release_sha256"]
    ):
        raise RendererDiagnosticError("producer training manifest stage or dataset changed")
    inventory = receipt.payload["checkpoint_inventory"]
    return {
        "stage_id": PRODUCER_STAGE_ID,
        "wave": PRODUCER_WAVE,
        "replicate_id": PRODUCER_REPLICATE_ID,
        "run_manifest": {
            "relative_path": str(manifest.relative_path),
            "payload_sha256": manifest.payload_sha256,
            "record_sha256": manifest.record_sha256,
        },
        "wave_receipt": {
            "relative_path": str(receipt.relative_path),
            "payload_sha256": receipt.payload_sha256,
            "record_sha256": receipt.record_sha256,
        },
        "checkpoint_inventory": inventory,
        "checkpoint_inventory_sha256": first.checkpoint_inventory_sha256,
        "samplers": {
            binding.checkpoint_name: {
                "checkpoint": binding.checkpoint,
                "sampler_path": binding.sampler_path,
            }
            for binding in bindings
        },
    }


def _normalized_segments(
    model_input: Any,
    *,
    stop_positions: int | None = None,
) -> list[dict[str, Any]]:
    """Normalize text chunk boundaries while preserving exact image identity."""

    total = int(model_input.length)
    stop = total if stop_positions is None else stop_positions
    if isinstance(stop, bool) or not isinstance(stop, int) or not 0 <= stop <= total:
        raise RendererDiagnosticError("invalid renderer-prefix slice")
    segments: list[dict[str, Any]] = []
    consumed = 0
    for chunk in model_input.chunks:
        if consumed >= stop:
            break
        length = int(chunk.length)
        take = min(length, stop - consumed)
        tokens = getattr(chunk, "tokens", None)
        if tokens is not None:
            selected = [int(token) for token in list(tokens)[:take]]
            if segments and segments[-1]["type"] == "tokens":
                segments[-1]["values"].extend(selected)
            else:
                segments.append({"type": "tokens", "values": selected})
        else:
            if take != length:
                raise RendererDiagnosticError("renderer prefix cuts through an image chunk")
            data = getattr(chunk, "data", None)
            if not isinstance(data, bytes):
                raise RendererDiagnosticError("renderer emitted an unhashable image chunk")
            segments.append(
                {
                    "type": "image",
                    "length": length,
                    "format": str(getattr(chunk, "format", "")),
                    "data_sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        consumed += take
    if consumed != stop:
        raise RendererDiagnosticError("renderer prefix length is inconsistent")
    return segments


def _append_token(
    segments: Sequence[Mapping[str, Any]],
    token: int,
) -> list[dict[str, Any]]:
    result = json.loads(_canonical_bytes(segments))
    if result and result[-1]["type"] == "tokens":
        result[-1]["values"].append(token)
    else:
        result.append({"type": "tokens", "values": [token]})
    return result


def _first_positive_offset(weights: Any, *, length: int) -> int:
    found = [index for index in range(length) if float(weights[index]) > 0.0]
    if not found:
        raise RendererDiagnosticError("SFT supervised target has no positive loss")
    first = found[0]
    if any(float(weights[index]) != 0.0 for index in range(first)):
        raise RendererDiagnosticError("SFT loss mask is not prefix-zero")
    return first


def _sft_prefix_audit(
    *,
    dataset_root: Path,
    protocol: Mapping[str, Any],
    tasks: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Prove the actual teacher-forced prefix against both inference renderers."""

    stage = stage_spec(dict(protocol), PRODUCER_STAGE_ID)
    model = dict(protocol["models"]["qwen"])
    source_tasks = list(tasks) if tasks is not None else stage_tasks(dataset_root, stage)
    if len(source_tasks) != (len(source_tasks) if tasks is not None else 3468):
        raise RendererDiagnosticError("SFT prefix audit has the wrong row count")
    training_renderer = _renderer(model["model"], model["renderer"])
    inference_renderers = {
        name: _renderer(model["model"], name) for name in ("qwen3_5_disable_thinking", "qwen3_5")
    }
    per_renderer: dict[str, dict[str, Any]] = {
        name: {
            "compatible_rows": 0,
            "incompatible_rows": 0,
            "evidence": [],
        }
        for name in inference_renderers
    }
    source_digest = hashlib.sha256()
    for task in source_tasks:
        messages = [_message(task, max_image=MAX_IMAGE_LONG_EDGE)]
        assistant = Message(
            role="assistant",
            content=[TextPart(type="text", text=task.label)],
        )
        supervised, weights = training_renderer.build_supervised_example(
            [*messages, assistant],
            train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
        )
        first = _first_positive_offset(weights, length=int(supervised.length))
        target_text = _positive_target_text(
            supervised,
            weights,
            training_renderer.tokenizer,
        )
        if target_text != task.label + "<|im_end|>":
            raise RendererDiagnosticError(
                f"{task.sampler.opaque_id} SFT target is not exact code plus end token"
            )
        before = _normalized_segments(supervised, stop_positions=first)
        through_first = _normalized_segments(
            supervised,
            stop_positions=first + 1,
        )
        first_token_segment = through_first[-1]
        if first_token_segment["type"] != "tokens":
            raise RendererDiagnosticError("first positive loss token is not text")
        first_token = int(first_token_segment["values"][-1])
        source_digest.update(task.sampler.opaque_id.encode("utf-8"))
        source_digest.update(bytes.fromhex(task.observation.image_sha256))
        source_digest.update(hashlib.sha256(task.label.encode("utf-8")).digest())
        for name, renderer in inference_renderers.items():
            generation = renderer.build_generation_prompt(messages)
            generation_segments = _normalized_segments(generation)
            prefix_equal = generation_segments == before
            through_equal = _append_token(generation_segments, first_token) == through_first
            compatible = prefix_equal and through_equal
            bucket = per_renderer[name]
            bucket["compatible_rows" if compatible else "incompatible_rows"] += 1
            evidence = {
                "task_id": task.sampler.opaque_id,
                "first_positive_loss_offset": first,
                "first_positive_token": first_token,
                "supervised_prefix_sha256": _canonical_sha256(before),
                "supervised_through_first_positive_sha256": (_canonical_sha256(through_first)),
                "generation_prefix_sha256": _canonical_sha256(generation_segments),
                "generation_plus_first_positive_sha256": _canonical_sha256(
                    _append_token(generation_segments, first_token)
                ),
                "prefix_equal": prefix_equal,
                "through_first_positive_equal": through_equal,
            }
            bucket["evidence"].append(evidence)
    results: dict[str, Any] = {}
    for name, bucket in per_renderer.items():
        expected = name == "qwen3_5_disable_thinking"
        compatible_rows = int(bucket["compatible_rows"])
        compatible = compatible_rows == len(source_tasks)
        if compatible is not expected:
            claim = "compatible" if expected else "incompatible"
            raise RendererDiagnosticError(f"{name} is not uniformly {claim} with the SFT prefix")
        evidence = bucket.pop("evidence")
        results[name] = {
            **bucket,
            "rows": len(source_tasks),
            "compatible_with_sft_supervised_prefix": compatible,
            "expected_compatible_claim": expected,
            "claim_verified": True,
            "comparison_scope": (
                "generation prefix plus first target token through the first positive-loss token"
            ),
            "diagnosis": (
                "The no-thinking generation prefix exactly matches the "
                "teacher-forced closed-thinking prefix."
                if expected
                else (
                    "The canonical renderer leaves <think> open, while code-only "
                    "SFT closes </think> before the first positive-loss code token; "
                    "a compatibility claim is rejected."
                )
            ),
            "evidence_sha256": canonical_json_sha256(evidence),
            "example": evidence[0],
        }
    return {
        "schema_version": "pixcell-qwen-sft-prefix-audit-v1",
        "rows": len(source_tasks),
        "training_renderer": model["renderer"],
        "train_on_what": "LAST_ASSISTANT_MESSAGE",
        "target_policy": "program_and_end_token_only",
        "source_set_sha256": source_digest.hexdigest(),
        "renderers": results,
    }


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
        raise checkpoint_v1.ReferencePanelFault("renderer diagnostic must be exact ordered F1-F8")
    return {
        "schema_version": TASK_PANEL_SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "task_count": len(entries),
        "task_ids": list(EXPECTED_TASK_IDS),
        "logical_sha256": canonical_json_sha256(entries),
    }


def _sample_seed(
    *,
    evaluator_source_git_sha: str,
    protocol_sha256: str,
    dataset_sha256: str,
    task_panel_sha256: str,
    arm: ArmSpec,
    binding: checkpoint_v1.CheckpointBinding,
    task_id: str,
) -> int:
    digest = hashlib.sha256(
        "\0".join(
            (
                _SEED_DOMAIN,
                PRODUCER_SOURCE_GIT_SHA,
                evaluator_source_git_sha,
                protocol_sha256,
                dataset_sha256,
                task_panel_sha256,
                binding.wave_receipt.record_sha256,
                binding.checkpoint_inventory_sha256,
                arm.arm_id,
                arm.checkpoint_name,
                arm.renderer,
                task_id,
                "1",
            )
        ).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _prepare_arms(
    *,
    protocol: Mapping[str, Any],
    model: Mapping[str, Any],
    bindings: Sequence[checkpoint_v1.CheckpointBinding],
    tasks: Sequence[EvaluationTask],
    evaluator: PixCellEvaluator,
    evaluator_source_git_sha: str,
    dataset_sha256: str,
    task_panel_sha256: str,
) -> tuple[tuple[PreparedArm, ...], tuple[PreparedAttempt, ...]]:
    arms: list[PreparedArm] = []
    attempts: list[PreparedAttempt] = []
    for spec, binding in zip(ARM_SPECS, bindings, strict=True):
        renderer = _renderer(model["model"], spec.renderer)
        prepared, preflight = checkpoint_v1._preflight_tasks(
            tasks=tasks,
            renderer=renderer,
            evaluator=evaluator,
            context_tokens=int(model["context_tokens"]),
        )
        arm = PreparedArm(
            spec=spec,
            binding=binding,
            renderer=renderer,
            prepared=tuple(prepared),
            preflight=preflight,
        )
        arms.append(arm)
        attempts.extend(
            PreparedAttempt(
                arm=arm,
                prepared=item,
                seed=_sample_seed(
                    evaluator_source_git_sha=evaluator_source_git_sha,
                    protocol_sha256=str(protocol["logical_sha256"]),
                    dataset_sha256=dataset_sha256,
                    task_panel_sha256=task_panel_sha256,
                    arm=spec,
                    binding=binding,
                    task_id=item.task.task_id,
                ),
            )
            for item in prepared
        )
    if len(attempts) != EXPECTED_SAMPLE_COUNT:
        raise RendererDiagnosticError(f"diagnostic resolved {len(attempts)} samples, expected 32")
    keys = [attempt.key for attempt in attempts]
    seeds = [attempt.seed for attempt in attempts]
    if len(set(keys)) != EXPECTED_SAMPLE_COUNT:
        raise RendererDiagnosticError("diagnostic attempt keys are not unique")
    if len(set(seeds)) != EXPECTED_SAMPLE_COUNT:
        raise RendererDiagnosticError("diagnostic deterministic seeds collided")
    return tuple(arms), tuple(attempts)


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
    channel_termination: str | None = None
    if token_decode_error is not None:
        answer_text = ""
        reasoning_text = ""
        channel_parse_complete = False
        channel_parse_status = "token_decode_error"
    else:
        try:
            message, termination = renderer.parse_response(tokens)
            answer_text = str(get_text_content(message))
            reasoning_text = checkpoint_v1._message_reasoning(message)
            channel_parse_complete = bool(termination.is_clean)
            channel_termination = str(termination)
            channel_parse_status = "clean" if channel_parse_complete else "unclean"
        except Exception as exc:
            answer_text = raw_text
            reasoning_text = ""
            channel_parse_complete = False
            channel_parse_status = "error"
            channel_parse_error = str(exc).replace("\x00", "")[-1200:]
    extracted_program = extract_code(answer_text)
    stop_reason = str(sequence.stop_reason)
    cap_hit = (
        len(tokens) >= MAX_OUTPUT_TOKENS
        or "length" in stop_reason.lower()
        or "max_token" in stop_reason.lower()
    )
    return {
        "token_ids": tokens,
        "token_ids_sha256": _canonical_sha256(tokens),
        "completion_tokens": len(tokens),
        "stop_reason": stop_reason,
        "cap_hit": cap_hit,
        "raw_text": raw_text,
        "raw_text_sha256": hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        "answer_text": answer_text,
        "answer_text_sha256": hashlib.sha256(answer_text.encode("utf-8")).hexdigest(),
        "reasoning_text": reasoning_text,
        "reasoning_text_sha256": hashlib.sha256(reasoning_text.encode("utf-8")).hexdigest(),
        "extracted_program": extracted_program,
        "extracted_program_sha256": hashlib.sha256(extracted_program.encode("utf-8")).hexdigest(),
        "token_decode_complete": token_decode_error is None,
        "token_decode_error": token_decode_error,
        "channel_parse_complete": channel_parse_complete,
        "channel_parse_status": channel_parse_status,
        "channel_parse_error": channel_parse_error,
        "channel_termination": channel_termination,
    }


_RESPONSE_FIELDS = {
    "token_ids",
    "token_ids_sha256",
    "completion_tokens",
    "stop_reason",
    "cap_hit",
    "raw_text",
    "raw_text_sha256",
    "answer_text",
    "answer_text_sha256",
    "reasoning_text",
    "reasoning_text_sha256",
    "extracted_program",
    "extracted_program_sha256",
    "token_decode_complete",
    "token_decode_error",
    "channel_parse_complete",
    "channel_parse_status",
    "channel_parse_error",
    "channel_termination",
}


def _validate_response(
    response: Any,
    *,
    attempt: PreparedAttempt,
) -> None:
    if not isinstance(response, Mapping) or set(response) != _RESPONSE_FIELDS:
        raise ImmutableRendererDiagnosticError(f"{attempt.key} raw response schema changed")
    tokens = response["token_ids"]
    if (
        not isinstance(tokens, list)
        or any(
            isinstance(token, bool) or not isinstance(token, int) or token < 0 for token in tokens
        )
        or response["completion_tokens"] != len(tokens)
        or response["token_ids_sha256"] != _canonical_sha256(tokens)
    ):
        raise ImmutableRendererDiagnosticError(f"{attempt.key} token inventory changed")
    for field in (
        "raw_text",
        "answer_text",
        "reasoning_text",
        "extracted_program",
    ):
        text = response[field]
        if (
            not isinstance(text, str)
            or response[f"{field}_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise ImmutableRendererDiagnosticError(f"{attempt.key} {field} digest changed")
    if response["extracted_program"] != extract_code(response["answer_text"]):
        raise ImmutableRendererDiagnosticError(
            f"{attempt.key} extracted program differs from the answer"
        )
    stop_reason = response["stop_reason"]
    expected_cap = len(tokens) >= MAX_OUTPUT_TOKENS or (
        isinstance(stop_reason, str)
        and ("length" in stop_reason.lower() or "max_token" in stop_reason.lower())
    )
    parse_status = response["channel_parse_status"]
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
        or parse_status not in {"clean", "unclean", "error", "token_decode_error"}
        or response["channel_parse_complete"] is not (parse_status == "clean")
        or (
            response["channel_parse_error"] is not None
            and not isinstance(response["channel_parse_error"], str)
        )
        or (
            response["channel_termination"] is not None
            and not isinstance(response["channel_termination"], str)
        )
        or (parse_status in {"clean", "unclean"} and response["channel_termination"] is None)
        or (
            parse_status not in {"clean", "unclean"} and response["channel_termination"] is not None
        )
        or (
            not response["token_decode_complete"]
            and (
                parse_status != "token_decode_error"
                or any(
                    response[field]
                    for field in (
                        "raw_text",
                        "answer_text",
                        "reasoning_text",
                        "extracted_program",
                    )
                )
            )
        )
    ):
        raise ImmutableRendererDiagnosticError(f"{attempt.key} response diagnostics changed")


def _sample_payload(
    *,
    attempt: PreparedAttempt,
    response: Mapping[str, Any],
    manifest_record_sha256: str,
) -> dict[str, Any]:
    binding = attempt.arm.binding
    return {
        **_not_canonical(),
        "diagnostic_manifest_record_sha256": manifest_record_sha256,
        "producer_wave_receipt_record_sha256": (binding.wave_receipt.record_sha256),
        "diagnostic_id": DIAGNOSTIC_ID,
        "arm": attempt.arm.spec.as_dict(),
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
        "checkpoint": binding.checkpoint,
        "task": {
            "task_id": attempt.task.task_id,
            "level": attempt.task.level,
            "representation_id": attempt.task.representation_id,
            "image_sha256": attempt.task.observation.image_sha256,
            "target_image_sha256": attempt.task.reference.target_image_sha256,
        },
        "request": {
            "num_samples": 1,
            "attempt_index": 1,
            "seed": attempt.seed,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "prompt_tokens": attempt.prepared.prompt_tokens,
            "prompt_text_sha256": attempt.prepared.prompt_text_sha256,
        },
        "response": dict(response),
    }


def _validate_sample_record(
    *,
    record: Mapping[str, Any],
    attempt: PreparedAttempt,
    manifest_record_sha256: str,
) -> None:
    payload = record["payload"]
    binding = attempt.arm.binding
    expected = {
        "diagnostic_manifest_record_sha256": manifest_record_sha256,
        "producer_wave_receipt_record_sha256": (binding.wave_receipt.record_sha256),
        "diagnostic_id": DIAGNOSTIC_ID,
        "arm": attempt.arm.spec.as_dict(),
        "checkpoint_inventory_sha256": binding.checkpoint_inventory_sha256,
        "checkpoint": binding.checkpoint,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ImmutableRendererDiagnosticError(
                f"{attempt.key} sample belongs to another diagnostic"
            )
    if payload.get("not_canonical_evidence") is not True:
        raise ImmutableRendererDiagnosticError(f"{attempt.key} sample lost non-canonical marker")
    expected_task = {
        "task_id": attempt.task.task_id,
        "level": attempt.task.level,
        "representation_id": attempt.task.representation_id,
        "image_sha256": attempt.task.observation.image_sha256,
        "target_image_sha256": attempt.task.reference.target_image_sha256,
    }
    expected_request = {
        "num_samples": 1,
        "attempt_index": 1,
        "seed": attempt.seed,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "prompt_tokens": attempt.prepared.prompt_tokens,
        "prompt_text_sha256": attempt.prepared.prompt_text_sha256,
    }
    if payload.get("task") != expected_task or payload.get("request") != expected_request:
        raise ImmutableRendererDiagnosticError(f"{attempt.key} sample request changed")
    _validate_response(payload.get("response"), attempt=attempt)


def _evaluation_payload(
    *,
    attempt: PreparedAttempt,
    result: EvaluationResult,
    sample_record_sha256: str,
    manifest_record_sha256: str,
    extracted_program_sha256: str,
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
    except RendererDiagnosticError as exc:
        raise checkpoint_v1.EvaluationInfrastructureFault(
            f"{attempt.key}: evaluator returned non-finite diagnostics"
        ) from exc
    normalized["diagnostic_manifest_record_sha256"] = normalized.pop(
        "evaluation_manifest_record_sha256"
    )
    normalized.update(
        {
            **_not_canonical(),
            "diagnostic_id": DIAGNOSTIC_ID,
            "arm_id": attempt.arm.spec.arm_id,
            "checkpoint_name": attempt.arm.spec.checkpoint_name,
            "renderer": attempt.arm.spec.renderer,
            "seed": attempt.seed,
            "extracted_program_sha256": extracted_program_sha256,
        }
    )
    return normalized


def _validate_evaluation_record(
    *,
    record: Mapping[str, Any],
    attempt: PreparedAttempt,
    sample_record_sha256: str,
    manifest_record_sha256: str,
    extracted_program_sha256: str,
) -> None:
    payload = record["payload"]
    expected = {
        "diagnostic_manifest_record_sha256": manifest_record_sha256,
        "sample_record_sha256": sample_record_sha256,
        "diagnostic_id": DIAGNOSTIC_ID,
        "arm_id": attempt.arm.spec.arm_id,
        "checkpoint_name": attempt.arm.spec.checkpoint_name,
        "renderer": attempt.arm.spec.renderer,
        "task_id": attempt.task.task_id,
        "level": attempt.task.level,
        "representation_id": attempt.task.representation_id,
        "seed": attempt.seed,
        "extracted_program_sha256": extracted_program_sha256,
        "attribution": Attribution.MODEL.value,
        "not_canonical_evidence": True,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ImmutableRendererDiagnosticError(f"{attempt.key} evaluation record changed")
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
        raise ImmutableRendererDiagnosticError(f"{attempt.key} has invalid stored metrics")
    status = payload.get("status")
    pure = payload.get("pure_executable")
    if (
        status not in {item.value for item in EvaluationStatus}
        or not isinstance(pure, bool)
        or pure is not (status == EvaluationStatus.OK.value)
        or (not pure and float(iou) != 0.0)
    ):
        raise ImmutableRendererDiagnosticError(f"{attempt.key} has inconsistent executable status")
    try:
        checkpoint_v1._safe_json(payload)
        _canonical_bytes(payload)
    except (
        checkpoint_v1.EvaluationInfrastructureFault,
        RendererDiagnosticError,
    ) as exc:
        raise ImmutableRendererDiagnosticError(f"{attempt.key} has non-finite diagnostics") from exc


async def _sample_missing(
    *,
    attempts: Sequence[PreparedAttempt],
    clients: Mapping[str, Any],
    store: RendererDiagnosticStore,
    manifest_record_sha256: str,
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
        prompt = attempt.arm.renderer.build_generation_prompt(messages)
        if int(prompt.length) != attempt.prepared.prompt_tokens:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} prompt changed after preflight"
            )
        async with semaphore:
            try:
                result = await clients[attempt.arm.spec.arm_id].sample_async(
                    prompt=prompt,
                    num_samples=1,
                    sampling_params=tinker.SamplingParams(
                        stop=attempt.arm.renderer.get_stop_sequences(),
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
        response = _decode_response(attempt.arm.renderer, sequences[0])
        store.create_or_verify_sample(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
            _sample_payload(
                attempt=attempt,
                response=response,
                manifest_record_sha256=manifest_record_sha256,
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
        raise faults[0]


def _score_missing(
    *,
    attempts: Sequence[PreparedAttempt],
    evaluator: PixCellEvaluator,
    store: RendererDiagnosticStore,
    manifest_record_sha256: str,
) -> None:
    pending: list[tuple[PreparedAttempt, dict[str, Any]]] = []
    for attempt in attempts:
        sample = store.load_sample(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        if sample is None:
            raise RendererDiagnosticError(f"{attempt.key} has no resumable sample")
        response = sample["payload"]["response"]
        if not response["token_decode_complete"]:
            raise checkpoint_v1.SamplingInfrastructureFault(
                f"{attempt.key} has undecodable persisted tokens"
            )
        existing = store.load_evaluation(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        if existing is not None:
            _validate_evaluation_record(
                record=existing,
                attempt=attempt,
                sample_record_sha256=str(sample["record_sha256"]),
                manifest_record_sha256=manifest_record_sha256,
                extracted_program_sha256=response["extracted_program_sha256"],
            )
            continue
        pending.append((attempt, sample))

    for offset in range(0, len(pending), EVALUATION_BATCH_SIZE):
        batch = pending[offset : offset + EVALUATION_BATCH_SIZE]
        requests = [
            (
                attempt.task.reference,
                str(sample["payload"]["response"]["extracted_program"]),
            )
            for attempt, sample in batch
        ]
        try:
            results = evaluator.evaluate_batch(requests)
        except Exception as exc:
            raise checkpoint_v1.EvaluationInfrastructureFault(
                f"isolated renderer-diagnostic batch failed: {exc}"
            ) from exc
        if len(results) != len(batch):
            raise checkpoint_v1.EvaluationInfrastructureFault(
                "isolated evaluator returned a different result count"
            )
        faults: list[checkpoint_v1.CheckpointEvaluationError] = []
        for (attempt, sample), result in zip(batch, results, strict=True):
            response = sample["payload"]["response"]
            try:
                payload = _evaluation_payload(
                    attempt=attempt,
                    result=result,
                    sample_record_sha256=str(sample["record_sha256"]),
                    manifest_record_sha256=manifest_record_sha256,
                    extracted_program_sha256=response["extracted_program_sha256"],
                )
            except (
                checkpoint_v1.ReferencePanelFault,
                checkpoint_v1.EvaluationInfrastructureFault,
            ) as exc:
                faults.append(exc)
                continue
            store.create_or_verify_evaluation(
                attempt.arm.spec.arm_id,
                attempt.task.task_id,
                payload,
            )
        if faults:
            raise faults[0]


def _validate_attempt_state(
    *,
    attempts: Sequence[PreparedAttempt],
    store: RendererDiagnosticStore,
    manifest_record_sha256: str,
) -> tuple[list[PreparedAttempt], list[PreparedAttempt]]:
    store.assert_attempt_inventory(attempts)
    missing_samples: list[PreparedAttempt] = []
    missing_evaluations: list[PreparedAttempt] = []
    for attempt in attempts:
        sample = store.load_sample(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        evaluation = store.load_evaluation(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        if sample is None:
            if evaluation is not None:
                raise ImmutableRendererDiagnosticError(
                    f"{attempt.key} has evaluation without raw sample"
                )
            missing_samples.append(attempt)
            missing_evaluations.append(attempt)
            continue
        _validate_sample_record(
            record=sample,
            attempt=attempt,
            manifest_record_sha256=manifest_record_sha256,
        )
        response = sample["payload"]["response"]
        if not response["token_decode_complete"] and evaluation is not None:
            raise ImmutableRendererDiagnosticError(f"{attempt.key} evaluates undecodable tokens")
        if evaluation is None:
            missing_evaluations.append(attempt)
            continue
        _validate_evaluation_record(
            record=evaluation,
            attempt=attempt,
            sample_record_sha256=str(sample["record_sha256"]),
            manifest_record_sha256=manifest_record_sha256,
            extracted_program_sha256=response["extracted_program_sha256"],
        )
    return missing_samples, missing_evaluations


def _arm_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(records) != len(EXPECTED_TASK_IDS):
        raise RendererDiagnosticError("diagnostic arm is not exact F1-F8")
    ious = [float(record["raw_absolute_scale_iou"]) for record in records]
    pure = [bool(record["pure_executable"]) for record in records]
    return {
        "tasks": len(records),
        "mean_raw_absolute_scale_iou": sum(ious) / len(ious),
        "pure_executable": sum(pure),
        "pure_executable_rate": sum(pure) / len(pure),
        "cap_hits": sum(bool(record["cap_hit"]) for record in records),
        "channel_parse_complete": sum(bool(record["channel_parse_complete"]) for record in records),
        "statuses": dict(sorted(Counter(str(record["status"]) for record in records).items())),
    }


def _report_payload(
    *,
    attempts: Sequence[PreparedAttempt],
    store: RendererDiagnosticStore,
    manifest_record: Mapping[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    by_arm: dict[str, list[dict[str, Any]]] = {spec.arm_id: [] for spec in ARM_SPECS}
    manifest_sha = str(manifest_record["record_sha256"])
    for attempt in attempts:
        sample = store.load_sample(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        evaluation = store.load_evaluation(
            attempt.arm.spec.arm_id,
            attempt.task.task_id,
        )
        if sample is None or evaluation is None:
            raise RendererDiagnosticError(f"{attempt.key} is incomplete")
        response = sample["payload"]["response"]
        measured = evaluation["payload"]
        _validate_sample_record(
            record=sample,
            attempt=attempt,
            manifest_record_sha256=manifest_sha,
        )
        _validate_evaluation_record(
            record=evaluation,
            attempt=attempt,
            sample_record_sha256=str(sample["record_sha256"]),
            manifest_record_sha256=manifest_sha,
            extracted_program_sha256=response["extracted_program_sha256"],
        )
        row = {
            "arm_id": attempt.arm.spec.arm_id,
            "checkpoint_name": attempt.arm.spec.checkpoint_name,
            "renderer": attempt.arm.spec.renderer,
            "task_id": attempt.task.task_id,
            "seed": attempt.seed,
            "status": measured["status"],
            "pure_executable": measured["pure_executable"],
            "raw_absolute_scale_iou": measured["raw_absolute_scale_iou"],
            "completion_tokens": response["completion_tokens"],
            "stop_reason": response["stop_reason"],
            "cap_hit": response["cap_hit"],
            "channel_parse_status": response["channel_parse_status"],
            "channel_parse_complete": response["channel_parse_complete"],
            "raw_text_sha256": response["raw_text_sha256"],
            "reasoning_text_sha256": response["reasoning_text_sha256"],
            "answer_text_sha256": response["answer_text_sha256"],
            "extracted_program_sha256": response["extracted_program_sha256"],
            "sample_record_sha256": sample["record_sha256"],
            "evaluation_record_sha256": evaluation["record_sha256"],
        }
        records.append(row)
        by_arm[attempt.arm.spec.arm_id].append(row)
    return {
        **_not_canonical(),
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "study_id": STUDY_ID,
        "producer_stage_id": PRODUCER_STAGE_ID,
        "producer_wave": PRODUCER_WAVE,
        "producer_replicate_id": PRODUCER_REPLICATE_ID,
        "matrix": [spec.as_dict() for spec in ARM_SPECS],
        "summaries": {arm_id: _arm_summary(values) for arm_id, values in by_arm.items()},
        "records": records,
        "record_set_sha256": canonical_json_sha256(records),
        "provenance": {
            "diagnostic_manifest_record_sha256": manifest_sha,
            "manifest": manifest_record["payload"],
        },
    }


def _manifest_payload(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    evaluator_source_git_sha: str,
    source_provenance: Mapping[str, Any],
    producer_training: Mapping[str, Any],
    dataset: Mapping[str, Any],
    task_panel: Mapping[str, Any],
    model: Mapping[str, Any],
    prefix_audit: Mapping[str, Any],
    runtime: Mapping[str, Any],
    sandbox: Mapping[str, Any],
    arms: Sequence[PreparedArm],
    attempts: Sequence[PreparedAttempt],
) -> dict[str, Any]:
    arm_preflights = {
        arm.spec.arm_id: {
            "spec": arm.spec.as_dict(),
            "checkpoint": arm.binding.checkpoint,
            "sampler_path": arm.binding.sampler_path,
            "prompt": arm.preflight,
            "prefix_compatibility": prefix_audit["renderers"][arm.spec.renderer],
        }
        for arm in arms
    }
    seed_inventory = [
        {
            "arm_id": attempt.arm.spec.arm_id,
            "checkpoint_name": attempt.arm.spec.checkpoint_name,
            "renderer": attempt.arm.spec.renderer,
            "task_id": attempt.task.task_id,
            "seed": attempt.seed,
        }
        for attempt in attempts
    ]
    return {
        **_not_canonical(),
        "schema_version": DIAGNOSTIC_SCHEMA_VERSION,
        "diagnostic_id": DIAGNOSTIC_ID,
        "study_id": STUDY_ID,
        "source": dict(source_provenance),
        "protocol": {
            "logical_sha256": protocol["logical_sha256"],
            "file_sha256": file_sha256(protocol_path(repo_root)),
            "contract_version": protocol["contract_version"],
            "preserved_unchanged": True,
        },
        "dataset": {
            "repo_id": protocol["dataset"]["repo_id"],
            "revision": protocol["dataset"]["revision"],
            "configuration": protocol["dataset"]["configuration"],
            "split": "fixed-f1-f8",
            **dict(dataset),
        },
        "producer_training": dict(producer_training),
        "task_panel": dict(task_panel),
        "prompt_assets": prompt_asset_hashes(),
        "model": {
            **dict(model),
            "producer_training_renderer": model["renderer"],
        },
        "sft_prefix_audit": dict(prefix_audit),
        "matrix": arm_preflights,
        "runtime": dict(runtime),
        "sandbox": dict(sandbox),
        "sampling": {
            "task_count": len(EXPECTED_TASK_IDS),
            "arms": len(ARM_SPECS),
            "total_samples": EXPECTED_SAMPLE_COUNT,
            "attempts_per_arm_task": 1,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_image_long_edge": MAX_IMAGE_LONG_EDGE,
            "sample_concurrency": SAMPLE_CONCURRENCY,
            "evaluation_batch_size": EVALUATION_BATCH_SIZE,
            "evaluator_workers": EVALUATOR_WORKERS,
            "seed_domain": _SEED_DOMAIN,
            "seed_algorithm": "sha256-bound deterministic 31-bit seed",
            "seeds": seed_inventory,
            "seeds_sha256": canonical_json_sha256(seed_inventory),
        },
        "evaluator_source_git_sha": evaluator_source_git_sha,
    }


def _runtime_binding(repo_root: Path) -> dict[str, Any]:
    runtime = validate_runtime_stack(repo_root)
    return {
        **runtime,
        "cookbook_source": _cookbook_source_binding(runtime),
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


async def run_renderer_diagnostic(
    *,
    repo_root: Path,
    evaluator_source_git_sha: str,
    producer_wave_receipt_record_sha256: str,
    external_root: Path,
    confirmation: str,
    service_client_factory: Callable[[], Any] = _default_service_client_factory,
    evaluator_factory: Callable[[], PixCellEvaluator] = _default_evaluator_factory,
) -> dict[str, Any]:
    """Run or resume the exact, diagnostic-only 32-sample matrix."""

    root = repo_root.expanduser().resolve(strict=True)
    protocol = load_protocol(root, require_committed=True)
    current_source = validate_source_sha(root, evaluator_source_git_sha)
    if confirmation != protocol["launch"]["confirmation_token"]:
        raise RendererDiagnosticError("explicit diagnostic spend confirmation is missing")
    fixed = _validate_fixed_protocol(protocol)
    training_store = TrainingStore(repo_root=root, external_root=external_root)
    bindings = _load_matrix_bindings(
        store=training_store,
        protocol=protocol,
        expected_wave_receipt_sha256=producer_wave_receipt_record_sha256,
    )
    source_provenance = _source_provenance(
        repo_root=root,
        evaluator_source_git_sha=current_source,
    )
    producer_training = _producer_training_provenance(
        repo_root=root,
        protocol=protocol,
        bindings=bindings,
    )
    dataset = _dataset_binding(root / "dataset", protocol)
    runtime = _runtime_binding(root)
    tasks = checkpoint_v1._benchmark_tasks(repo_root=root, protocol=protocol)
    task_panel = _task_panel(tasks)
    prefix_audit = _sft_prefix_audit(
        dataset_root=root / "dataset",
        protocol=protocol,
    )
    for spec in ARM_SPECS:
        observed = prefix_audit["renderers"][spec.renderer]["compatible_with_sft_supervised_prefix"]
        if observed is not spec.expected_sft_prefix_compatible:
            raise RendererDiagnosticError(f"{spec.arm_id} renderer compatibility claim changed")

    evaluator = evaluator_factory()
    try:
        sandbox = checkpoint_v1._sandbox_provenance(evaluator)
        arms, attempts = _prepare_arms(
            protocol=protocol,
            model=fixed["model"],
            bindings=bindings,
            tasks=tasks,
            evaluator=evaluator,
            evaluator_source_git_sha=current_source,
            dataset_sha256=str(dataset["logical_release_sha256"]),
            task_panel_sha256=str(task_panel["logical_sha256"]),
        )
        store = RendererDiagnosticStore(
            stage_path=training_store.stage_path(bindings[0].key),
        )
        with store.acquire_lock():
            manifest_payload = _manifest_payload(
                repo_root=root,
                protocol=protocol,
                evaluator_source_git_sha=current_source,
                source_provenance=source_provenance,
                producer_training=producer_training,
                dataset=dataset,
                task_panel=task_panel,
                model=fixed["model"],
                prefix_audit=prefix_audit,
                runtime=runtime,
                sandbox=sandbox,
                arms=arms,
                attempts=attempts,
            )
            manifest = store.create_or_verify_manifest(manifest_payload)
            missing_samples, missing_evaluations = _validate_attempt_state(
                attempts=attempts,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
            )
            existing_report = store.load_report()
            if existing_report is not None:
                if missing_samples or missing_evaluations:
                    raise RendererDiagnosticError(
                        "diagnostic report exists with incomplete matrix rows"
                    )
                expected = _report_payload(
                    attempts=attempts,
                    store=store,
                    manifest_record=manifest,
                )
                observed = store.create_or_verify_report(expected)
                _validate_report_rows(
                    observed,
                    manifest_record=manifest,
                    attempts=attempts,
                )
                return {
                    "status": "already_complete",
                    "diagnostic_id": DIAGNOSTIC_ID,
                    "not_canonical_evidence": True,
                    "report": str(store.root / "report.json"),
                    "report_record_sha256": observed["record_sha256"],
                    "summaries": observed["payload"]["summaries"],
                }

            if missing_samples:
                if not os.environ.get("TINKER_API_KEY"):
                    raise RendererDiagnosticError("TINKER_API_KEY is not present")
                # Revalidate the exact current source, explicit spend token,
                # producer receipt, existing rows, and matrix immediately
                # before the first paid-capable client exists.
                validate_source_sha(root, current_source)
                if confirmation != protocol["launch"]["confirmation_token"]:
                    raise RendererDiagnosticError(
                        "diagnostic spend confirmation changed before client"
                    )
                rebound = _load_matrix_bindings(
                    store=training_store,
                    protocol=protocol,
                    expected_wave_receipt_sha256=(producer_wave_receipt_record_sha256),
                )
                if [
                    (
                        binding.checkpoint,
                        binding.checkpoint_inventory_sha256,
                        binding.sampler_path,
                        binding.wave_receipt.record_sha256,
                    )
                    for binding in rebound
                ] != [
                    (
                        arm.binding.checkpoint,
                        arm.binding.checkpoint_inventory_sha256,
                        arm.binding.sampler_path,
                        arm.binding.wave_receipt.record_sha256,
                    )
                    for arm in arms
                ]:
                    raise RendererDiagnosticError("producer receipt changed before client creation")
                missing_samples, _ = _validate_attempt_state(
                    attempts=attempts,
                    store=store,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                )
                if not missing_samples:
                    raise RendererDiagnosticError(
                        "diagnostic resume state changed before client creation"
                    )
                service = service_client_factory()
                clients = {
                    arm.spec.arm_id: service.create_sampling_client(
                        model_path=arm.binding.sampler_path
                    )
                    for arm in arms
                    if any(
                        attempt.arm.spec.arm_id == arm.spec.arm_id for attempt in missing_samples
                    )
                }
                await _sample_missing(
                    attempts=missing_samples,
                    clients=clients,
                    store=store,
                    manifest_record_sha256=str(manifest["record_sha256"]),
                )

            missing_samples, _ = _validate_attempt_state(
                attempts=attempts,
                store=store,
                manifest_record_sha256=str(manifest["record_sha256"]),
            )
            if missing_samples:
                raise RendererDiagnosticError(
                    "diagnostic sampling did not persist all raw responses"
                )
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
            )
            if missing_samples or missing_evaluations:
                raise RendererDiagnosticError(
                    "diagnostic is incomplete after deterministic evaluation"
                )
            report_payload = _report_payload(
                attempts=attempts,
                store=store,
                manifest_record=manifest,
            )
            report = store.create_or_verify_report(report_payload)
            _validate_report_rows(
                report,
                manifest_record=manifest,
                attempts=attempts,
            )
            return {
                "status": "complete",
                "diagnostic_id": DIAGNOSTIC_ID,
                "not_canonical_evidence": True,
                "report": str(store.root / "report.json"),
                "report_record_sha256": report["record_sha256"],
                "summaries": report_payload["summaries"],
            }
    finally:
        evaluator.close()


def _validate_report_rows(
    record: Mapping[str, Any],
    *,
    manifest_record: Mapping[str, Any],
    attempts: Sequence[PreparedAttempt],
) -> dict[str, Any]:
    """Validate the report without granting it a canonical report interface."""

    validated = _validate_record(
        record,
        record_type="renderer_diagnostic_report",
        key={},
    )
    payload = validated["payload"]
    if (
        payload.get("schema_version") != DIAGNOSTIC_SCHEMA_VERSION
        or payload.get("diagnostic_id") != DIAGNOSTIC_ID
        or payload.get("not_canonical_evidence") is not True
        or payload.get("promotion_eligibility") != {"eligible": False, "policy": _PROMOTION_POLICY}
        or payload.get("matrix") != [spec.as_dict() for spec in ARM_SPECS]
    ):
        raise RendererDiagnosticError("diagnostic report identity changed")
    provenance = payload.get("provenance")
    records = payload.get("records")
    if (
        not isinstance(provenance, Mapping)
        or not isinstance(records, list)
        or provenance.get("diagnostic_manifest_record_sha256") != manifest_record["record_sha256"]
        or provenance.get("manifest") != manifest_record["payload"]
    ):
        raise RendererDiagnosticError("diagnostic report provenance changed")
    expected_keys = [attempt.key for attempt in attempts]
    observed_keys = [
        (str(row.get("arm_id")), str(row.get("task_id")))
        for row in records
        if isinstance(row, Mapping)
    ]
    if (
        len(records) != EXPECTED_SAMPLE_COUNT
        or observed_keys != expected_keys
        or len(set(observed_keys)) != EXPECTED_SAMPLE_COUNT
    ):
        raise RendererDiagnosticError("diagnostic report has an incomplete or reordered matrix")
    for row, attempt in zip(records, attempts, strict=True):
        if not isinstance(row, Mapping):
            raise RendererDiagnosticError("diagnostic report row is not an object")
        expected = {
            "arm_id": attempt.arm.spec.arm_id,
            "checkpoint_name": attempt.arm.spec.checkpoint_name,
            "renderer": attempt.arm.spec.renderer,
            "task_id": attempt.task.task_id,
            "seed": attempt.seed,
        }
        for field, value in expected.items():
            if row.get(field) != value:
                raise RendererDiagnosticError(f"{attempt.key} report identity changed")
        iou = row.get("raw_absolute_scale_iou")
        completion_tokens = row.get("completion_tokens")
        status = row.get("status")
        pure = row.get("pure_executable")
        cap_hit = row.get("cap_hit")
        stop_reason = row.get("stop_reason")
        parse_status = row.get("channel_parse_status")
        parse_complete = row.get("channel_parse_complete")
        expected_cap = (
            isinstance(completion_tokens, int)
            and not isinstance(completion_tokens, bool)
            and (
                completion_tokens >= MAX_OUTPUT_TOKENS
                or (
                    isinstance(stop_reason, str)
                    and ("length" in stop_reason.lower() or "max_token" in stop_reason.lower())
                )
            )
        )
        if (
            isinstance(iou, bool)
            or not isinstance(iou, (int, float))
            or not math.isfinite(float(iou))
            or not 0.0 <= float(iou) <= 1.0
            or status not in {item.value for item in EvaluationStatus}
            or not isinstance(pure, bool)
            or pure is not (status == EvaluationStatus.OK.value)
            or (not pure and float(iou) != 0.0)
            or isinstance(completion_tokens, bool)
            or not isinstance(completion_tokens, int)
            or completion_tokens < 0
            or not isinstance(stop_reason, str)
            or not isinstance(cap_hit, bool)
            or cap_hit is not expected_cap
            or parse_status not in {"clean", "unclean", "error", "token_decode_error"}
            or not isinstance(parse_complete, bool)
            or parse_complete is not (parse_status == "clean")
        ):
            raise RendererDiagnosticError(f"{attempt.key} report diagnostics are inconsistent")
        for field in (
            "raw_text_sha256",
            "reasoning_text_sha256",
            "answer_text_sha256",
            "extracted_program_sha256",
            "sample_record_sha256",
            "evaluation_record_sha256",
        ):
            if not checkpoint_v1._SHA256.fullmatch(str(row.get(field, ""))):
                raise RendererDiagnosticError(f"{attempt.key} report {field} is not a SHA-256")
    by_arm = {
        spec.arm_id: [row for row in records if row["arm_id"] == spec.arm_id] for spec in ARM_SPECS
    }
    recomputed = {arm_id: _arm_summary(rows) for arm_id, rows in by_arm.items()}
    if payload.get("summaries") != recomputed:
        raise RendererDiagnosticError("diagnostic claimed metrics differ from its rows")
    if payload.get("record_set_sha256") != canonical_json_sha256(records):
        raise RendererDiagnosticError("diagnostic row-set digest changed")
    return validated


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--repo-root", type=Path, required=True)
    result.add_argument("--evaluator-source-git-sha", required=True)
    result.add_argument(
        "--producer-wave-receipt-record-sha256",
        required=True,
    )
    result.add_argument("--external-root", type=Path, required=True)
    result.add_argument("--confirm-spend", default="")
    return result


def main() -> None:
    args = parser().parse_args()
    result = asyncio.run(
        run_renderer_diagnostic(
            repo_root=args.repo_root,
            evaluator_source_git_sha=args.evaluator_source_git_sha,
            producer_wave_receipt_record_sha256=(args.producer_wave_receipt_record_sha256),
            external_root=args.external_root,
            confirmation=args.confirm_spend,
        )
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
