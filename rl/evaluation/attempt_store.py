"""Crash-safe, immutable storage for baseline sampling attempts.

The store deliberately lives outside the source repository.  A sampling
receipt is the durable boundary: once it exists, a resumed run evaluates that
receipt rather than asking the model for another completion.
"""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import math
import os
import re
import stat
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


RECORD_SCHEMA_VERSION = "pixcell-baseline-attempt-record-v1"
RUN_MANIFEST_SCHEMA_VERSION = "pixcell-baseline-run-manifest-v1"
MAX_RECORD_BYTES = 64 * 1024 * 1024

_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_IMMUTABLE_IMAGE = re.compile(
    r"^(?:sha256:[0-9a-f]{64}|[^\s@]+@sha256:[0-9a-f]{64})$"
)
_UNIT_INTERVAL_KEYS = {
    "dice",
    "executable_rate",
    "iou",
    "pure_executable_rate",
    "raw_absolute_scale_iou",
    "raw_iou",
    "reward",
    "score",
    "top_p",
}
_NONNEGATIVE_KEYS = {
    "cached_prefill",
    "completion_tokens",
    "evaluation_seconds",
    "input_tokens",
    "latency_seconds",
    "output_tokens",
    "prompt_tokens",
    "reasoning_tokens",
    "sampling_seconds",
    "total_tokens",
    "uncached_prefill",
}
_POSITIVE_INTEGER_KEYS = {
    "max_output_tokens",
    "max_tokens",
}
_RUN_MANIFEST_FIELDS = {
    "source_git_sha",
    "protocol_sha256",
    "task_set_sha256",
    "prompt_sha256",
    "sandbox_image_ref",
    "sandbox_image_id",
    "runtime",
    "model_binding",
}


class AttemptStoreError(RuntimeError):
    """Base class for attempt-ledger failures."""


class UnsafeStoreRootError(AttemptStoreError):
    """The requested result root overlaps the source repository."""


class InvalidRecordError(AttemptStoreError):
    """A record is not valid, canonical, or internally consistent."""


class ImmutableRecordError(AttemptStoreError):
    """A caller attempted to replace an existing immutable record."""


class ManifestDriftError(ImmutableRecordError):
    """A resumed arm no longer matches its frozen launch manifest."""


class RunLockedError(AttemptStoreError):
    """Another process already owns the nonblocking arm lock."""


class RunLockRequiredError(AttemptStoreError):
    """Sampling was requested without holding the arm lock."""


@dataclass(frozen=True, order=True)
class RunKey:
    study_id: str
    hypothesis_id: str
    arm_id: str

    def __post_init__(self) -> None:
        _validate_identifier(self.study_id, field="study_id")
        _validate_identifier(self.hypothesis_id, field="hypothesis_id")
        _validate_identifier(self.arm_id, field="arm_id")

    def as_dict(self) -> dict[str, str]:
        return {
            "study_id": self.study_id,
            "hypothesis_id": self.hypothesis_id,
            "arm_id": self.arm_id,
        }


@dataclass(frozen=True, order=True)
class AttemptKey:
    study_id: str
    hypothesis_id: str
    arm_id: str
    task_id: str
    attempt_index: int

    def __post_init__(self) -> None:
        RunKey(self.study_id, self.hypothesis_id, self.arm_id)
        _validate_identifier(self.task_id, field="task_id")
        if (
            isinstance(self.attempt_index, bool)
            or not isinstance(self.attempt_index, int)
            or not 1 <= self.attempt_index <= 1_000_000
        ):
            raise ValueError("attempt_index must be an integer in [1, 1000000]")

    @property
    def run_key(self) -> RunKey:
        return RunKey(self.study_id, self.hypothesis_id, self.arm_id)

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.run_key.as_dict(),
            "task_id": self.task_id,
            "attempt_index": self.attempt_index,
        }


@dataclass(frozen=True)
class StoredRecord:
    payload: dict[str, Any]
    payload_sha256: str
    record_sha256: str
    relative_path: PurePosixPath


@dataclass(frozen=True)
class ReceiptResolution:
    record: StoredRecord
    resumed: bool


def _validate_identifier(value: str, *, field: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(
            f"{field} must match {_IDENTIFIER.pattern!r}; got {value!r}"
        )


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
        raise InvalidRecordError("record is not finite JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_json(value: Any, *, path: str = "$", key: str | None = None) -> None:
    if value is None or isinstance(value, (str, bool)):
        pass
    elif isinstance(value, int):
        pass
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise InvalidRecordError(f"{path} must be finite")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json(item, path=f"{path}[{index}]")
    elif isinstance(value, Mapping):
        for child_key, item in value.items():
            if not isinstance(child_key, str):
                raise InvalidRecordError(f"{path} contains a non-string key")
            _validate_json(item, path=f"{path}.{child_key}", key=child_key)
    else:
        raise InvalidRecordError(
            f"{path} has non-JSON type {type(value).__name__}"
        )

    if key is None:
        return
    if key.endswith("_sha256") and value is not None:
        if not isinstance(value, str) or not _SHA256.fullmatch(value):
            raise InvalidRecordError(f"{path} must be a lowercase SHA-256")
    if value is not None and (
        key in _UNIT_INTERVAL_KEYS
        or key.endswith(("_dice", "_fraction", "_iou", "_rate"))
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0.0 <= float(value) <= 1.0
        ):
            raise InvalidRecordError(f"{path} must be in [0, 1]")
    if key == "temperature" and value is not None:
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not 0.0 <= float(value) <= 2.0
        ):
            raise InvalidRecordError(f"{path} must be in [0, 2]")
    if value is not None and (
        key in _NONNEGATIVE_KEYS or key.endswith("_seconds")
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or float(value) < 0.0
        ):
            raise InvalidRecordError(f"{path} must be nonnegative")
    if key in _POSITIVE_INTEGER_KEYS and value is not None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= 1_000_000
        ):
            raise InvalidRecordError(
                f"{path} must be an integer in [1, 1000000]"
            )


def _normalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        raise InvalidRecordError("record payload must be a JSON object")
    _validate_json(payload)
    # The canonical round trip also detaches the immutable record from mutable
    # mappings owned by a caller.
    normalized = json.loads(_canonical_bytes(payload))
    if not isinstance(normalized, dict):
        raise InvalidRecordError("record payload must be a JSON object")
    return normalized


def _json_object(raw: bytes, *, path: Path) -> dict[str, Any]:
    def reject_constant(value: str) -> Any:
        raise InvalidRecordError(f"{path} contains non-finite number {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise InvalidRecordError(f"{path} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw,
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidRecordError(f"{path} is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise InvalidRecordError(f"{path} must contain a JSON object")
    _validate_json(value)
    return value


def _record_document(
    *,
    record_type: str,
    key: Mapping[str, Any],
    payload: Mapping[str, Any],
    schema_version: str = RECORD_SCHEMA_VERSION,
) -> dict[str, Any]:
    normalized = _normalize_payload(payload)
    base: dict[str, Any] = {
        "schema_version": schema_version,
        "record_type": record_type,
        "key": dict(key),
        "payload": normalized,
        "payload_sha256": _sha256(normalized),
    }
    base["record_sha256"] = _sha256(base)
    return base


def _validate_record_document(
    document: Mapping[str, Any],
    *,
    expected_type: str,
    expected_key: Mapping[str, Any],
    expected_schema: str = RECORD_SCHEMA_VERSION,
) -> StoredRecord:
    required = {
        "schema_version",
        "record_type",
        "key",
        "payload",
        "payload_sha256",
        "record_sha256",
    }
    if set(document) != required:
        raise InvalidRecordError(
            f"{expected_type} record fields differ from the frozen schema"
        )
    if document["schema_version"] != expected_schema:
        raise InvalidRecordError(f"unexpected {expected_type} schema version")
    if document["record_type"] != expected_type:
        raise InvalidRecordError(f"expected {expected_type} record")
    if document["key"] != dict(expected_key):
        raise InvalidRecordError(f"{expected_type} key does not match its path")
    payload = document["payload"]
    if not isinstance(payload, dict):
        raise InvalidRecordError(f"{expected_type} payload must be an object")
    payload_sha = _sha256(payload)
    if document["payload_sha256"] != payload_sha:
        raise InvalidRecordError(f"{expected_type} payload hash mismatch")
    unsigned = dict(document)
    record_sha = unsigned.pop("record_sha256")
    if record_sha != _sha256(unsigned):
        raise InvalidRecordError(f"{expected_type} record hash mismatch")
    return StoredRecord(
        payload=dict(payload),
        payload_sha256=payload_sha,
        record_sha256=str(record_sha),
        relative_path=PurePosixPath("."),
    )


class _RunLock:
    def __init__(self, store: AttemptStore, run_key: RunKey, path: Path) -> None:
        self._store = store
        self._run_key = run_key
        self._path = path
        self._fd: int | None = None

    def __enter__(self) -> _RunLock:
        self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self._path, flags, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            if "fd" in locals():
                os.close(fd)
            raise RunLockedError(
                f"run {self._run_key} is already active"
            ) from exc
        except OSError:
            if "fd" in locals():
                os.close(fd)
            raise
        self._fd = fd
        try:
            self._store._mark_lock_held(self._run_key)
        except Exception:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            self._fd = None
            raise
        return self

    def __exit__(self, *_: object) -> None:
        if self._fd is None:
            return
        self._store._mark_lock_released(self._run_key)
        fcntl.flock(self._fd, fcntl.LOCK_UN)
        os.close(self._fd)
        self._fd = None


class AttemptStore:
    """External, create-only attempt ledger."""

    def __init__(self, *, repo_root: Path, external_root: Path) -> None:
        self.repo_root = Path(repo_root).resolve(strict=True)
        requested_root = Path(external_root).expanduser().resolve(strict=False)
        if (
            requested_root == self.repo_root
            or requested_root.is_relative_to(self.repo_root)
            or self.repo_root.is_relative_to(requested_root)
        ):
            raise UnsafeStoreRootError(
                "attempt output must not overlap the source repository"
            )
        requested_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.external_root = requested_root.resolve(strict=True)
        if (
            self.external_root == self.repo_root
            or self.external_root.is_relative_to(self.repo_root)
            or self.repo_root.is_relative_to(self.external_root)
        ):
            raise UnsafeStoreRootError(
                "attempt output resolves across the source repository"
            )
        self._held_locks: set[RunKey] = set()
        self._lock_state_guard = threading.Lock()

    @staticmethod
    def run_relative_path(run_key: RunKey) -> PurePosixPath:
        return PurePosixPath(
            "studies",
            run_key.study_id,
            "hypotheses",
            run_key.hypothesis_id,
            "arms",
            run_key.arm_id,
        )

    @classmethod
    def attempt_relative_path(cls, key: AttemptKey) -> PurePosixPath:
        return cls.run_relative_path(key.run_key) / PurePosixPath(
            "tasks",
            key.task_id,
            "attempts",
            f"{key.attempt_index:06d}",
        )

    @classmethod
    def run_manifest_relative_path(cls, run_key: RunKey) -> PurePosixPath:
        return cls.run_relative_path(run_key) / "run_manifest.json"

    @classmethod
    def sampling_receipt_relative_path(cls, key: AttemptKey) -> PurePosixPath:
        return cls.attempt_relative_path(key) / "sampling_receipt.json"

    @classmethod
    def evaluation_relative_path(cls, key: AttemptKey) -> PurePosixPath:
        return cls.attempt_relative_path(key) / "evaluation.json"

    def _path(self, relative: PurePosixPath) -> Path:
        path = self.external_root.joinpath(*relative.parts)
        resolved_parent = path.parent.resolve(strict=False)
        if resolved_parent != self.external_root and not resolved_parent.is_relative_to(
            self.external_root
        ):
            raise UnsafeStoreRootError("record path escaped the external root")
        return path

    def acquire_run_lock(self, run_key: RunKey) -> _RunLock:
        digest = hashlib.sha256(
            _canonical_bytes(run_key.as_dict())
        ).hexdigest()
        return _RunLock(
            self,
            run_key,
            self.external_root / ".locks" / f"{digest}.lock",
        )

    def _mark_lock_held(self, run_key: RunKey) -> None:
        with self._lock_state_guard:
            if run_key in self._held_locks:
                raise RunLockedError(f"run {run_key} is already locked here")
            self._held_locks.add(run_key)

    def _mark_lock_released(self, run_key: RunKey) -> None:
        with self._lock_state_guard:
            self._held_locks.discard(run_key)

    def _require_run_lock(self, run_key: RunKey) -> None:
        with self._lock_state_guard:
            if run_key not in self._held_locks:
                raise RunLockRequiredError(
                    "sampling requires the caller to hold the arm run lock"
                )

    def create_or_verify_run_manifest(
        self,
        run_key: RunKey,
        manifest: Mapping[str, Any],
    ) -> StoredRecord:
        normalized = _normalize_payload(manifest)
        missing = sorted(_RUN_MANIFEST_FIELDS - set(normalized))
        if missing:
            raise InvalidRecordError(
                f"run manifest is missing launch bindings: {missing}"
            )
        if not _GIT_SHA.fullmatch(str(normalized["source_git_sha"])):
            raise InvalidRecordError("source_git_sha must be a Git object SHA")
        for field in ("protocol_sha256", "task_set_sha256", "prompt_sha256"):
            if not _SHA256.fullmatch(str(normalized[field])):
                raise InvalidRecordError(f"{field} must be a lowercase SHA-256")
        if not _IMMUTABLE_IMAGE.fullmatch(
            str(normalized["sandbox_image_ref"])
        ):
            raise InvalidRecordError(
                "sandbox_image_ref must be an immutable image digest"
            )
        if not re.fullmatch(
            r"sha256:[0-9a-f]{64}", str(normalized["sandbox_image_id"])
        ):
            raise InvalidRecordError(
                "sandbox_image_id must be an immutable local image ID"
            )
        if (
            not isinstance(normalized["model_binding"], dict)
            or not normalized["model_binding"]
        ):
            raise InvalidRecordError("model_binding must be a non-empty object")
        runtime = normalized["runtime"]
        if (
            not isinstance(runtime, dict)
            or not isinstance(runtime.get("python"), str)
            or not runtime["python"]
            or not isinstance(runtime.get("packages"), dict)
            or not runtime["packages"]
            or not _GIT_SHA.fullmatch(
                str(runtime.get("tinker_cookbook_commit", ""))
            )
        ):
            raise InvalidRecordError("runtime must contain the pinned observed stack")

        expected = _record_document(
            record_type="run_manifest",
            key=run_key.as_dict(),
            payload=normalized,
            schema_version=RUN_MANIFEST_SCHEMA_VERSION,
        )
        relative = self.run_manifest_relative_path(run_key)
        try:
            return self._create_or_verify(
                relative=relative,
                expected=expected,
                record_type="run_manifest",
                key=run_key.as_dict(),
                schema_version=RUN_MANIFEST_SCHEMA_VERSION,
            )
        except ImmutableRecordError as exc:
            raise ManifestDriftError(
                "run manifest differs from the immutable arm binding"
            ) from exc

    def load_run_manifest(self, run_key: RunKey) -> StoredRecord | None:
        return self._load(
            relative=self.run_manifest_relative_path(run_key),
            record_type="run_manifest",
            key=run_key.as_dict(),
            schema_version=RUN_MANIFEST_SCHEMA_VERSION,
        )

    def write_sampling_receipt(
        self,
        key: AttemptKey,
        payload: Mapping[str, Any],
    ) -> StoredRecord:
        return self._write_attempt_record(
            key=key,
            payload=payload,
            record_type="sampling_receipt",
            relative=self.sampling_receipt_relative_path(key),
        )

    def load_sampling_receipt(self, key: AttemptKey) -> StoredRecord | None:
        return self._load(
            relative=self.sampling_receipt_relative_path(key),
            record_type="sampling_receipt",
            key=key.as_dict(),
        )

    def write_evaluation(
        self,
        key: AttemptKey,
        payload: Mapping[str, Any],
    ) -> StoredRecord:
        if self.load_sampling_receipt(key) is None:
            raise InvalidRecordError(
                "evaluation cannot precede its durable sampling receipt"
            )
        return self._write_attempt_record(
            key=key,
            payload=payload,
            record_type="evaluation",
            relative=self.evaluation_relative_path(key),
        )

    def load_evaluation(self, key: AttemptKey) -> StoredRecord | None:
        return self._load(
            relative=self.evaluation_relative_path(key),
            record_type="evaluation",
            key=key.as_dict(),
        )

    def write_evaluator_failure(
        self,
        key: AttemptKey,
        payload: Mapping[str, Any],
    ) -> StoredRecord:
        """Preserve a verifier diagnostic without poisoning canonical results."""

        if self.load_sampling_receipt(key) is None:
            raise InvalidRecordError(
                "evaluator failure cannot precede its sampling receipt"
            )
        normalized = _normalize_payload(payload)
        failure_id = _sha256(normalized)
        relative = (
            self.attempt_relative_path(key)
            / "evaluator_failures"
            / f"{failure_id}.json"
        )
        return self._write_attempt_record(
            key=key,
            payload=normalized,
            record_type="evaluator_failure",
            relative=relative,
        )

    def list_evaluator_failures(
        self,
        key: AttemptKey,
    ) -> tuple[StoredRecord, ...]:
        directory = self._path(
            self.attempt_relative_path(key) / "evaluator_failures"
        )
        if not directory.exists():
            return ()
        result: list[StoredRecord] = []
        for path in sorted(directory.glob("*.json")):
            relative = PurePosixPath(
                path.relative_to(self.external_root).as_posix()
            )
            record = self._load(
                relative=relative,
                record_type="evaluator_failure",
                key=key.as_dict(),
            )
            if record is not None:
                result.append(record)
        return tuple(result)

    def resume_or_sample(
        self,
        key: AttemptKey,
        sampler: Callable[[], Mapping[str, Any]],
    ) -> ReceiptResolution:
        existing = self.load_sampling_receipt(key)
        if existing is not None:
            return ReceiptResolution(record=existing, resumed=True)
        self._require_run_lock(key.run_key)
        if self.load_run_manifest(key.run_key) is None:
            raise InvalidRecordError(
                "sampling requires a frozen per-arm run manifest"
            )
        # Recheck after validating ownership and the launch binding.
        existing = self.load_sampling_receipt(key)
        if existing is not None:
            return ReceiptResolution(record=existing, resumed=True)
        sampled = sampler()
        record = self.write_sampling_receipt(key, sampled)
        return ReceiptResolution(record=record, resumed=False)

    def write_tracking_error(
        self,
        key: AttemptKey,
        payload: Mapping[str, Any],
    ) -> StoredRecord:
        normalized = _normalize_payload(payload)
        normalized.setdefault("occurred_at_unix_ns", time.time_ns())
        error_id = _sha256(normalized)
        relative = (
            self.attempt_relative_path(key)
            / "tracking_errors"
            / f"{error_id}.json"
        )
        return self._write_attempt_record(
            key=key,
            payload=normalized,
            record_type="tracking_error",
            relative=relative,
        )

    def list_tracking_errors(self, key: AttemptKey) -> tuple[StoredRecord, ...]:
        directory = self._path(
            self.attempt_relative_path(key) / "tracking_errors"
        )
        if not directory.exists():
            return ()
        result: list[StoredRecord] = []
        for path in sorted(directory.glob("*.json")):
            relative = PurePosixPath(path.relative_to(self.external_root).as_posix())
            record = self._load(
                relative=relative,
                record_type="tracking_error",
                key=key.as_dict(),
            )
            if record is not None:
                result.append(record)
        return tuple(result)

    def _write_attempt_record(
        self,
        *,
        key: AttemptKey,
        payload: Mapping[str, Any],
        record_type: str,
        relative: PurePosixPath,
    ) -> StoredRecord:
        expected = _record_document(
            record_type=record_type,
            key=key.as_dict(),
            payload=payload,
        )
        return self._create_or_verify(
            relative=relative,
            expected=expected,
            record_type=record_type,
            key=key.as_dict(),
        )

    def _create_or_verify(
        self,
        *,
        relative: PurePosixPath,
        expected: Mapping[str, Any],
        record_type: str,
        key: Mapping[str, Any],
        schema_version: str = RECORD_SCHEMA_VERSION,
    ) -> StoredRecord:
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = _canonical_bytes(expected) + b"\n"
        temporary = path.parent / (
            f".{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}"
        )
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
                self._fsync_directory(path.parent)
            except FileExistsError:
                observed = self._load(
                    relative=relative,
                    record_type=record_type,
                    key=key,
                    schema_version=schema_version,
                )
                if observed is None:
                    raise InvalidRecordError(
                        f"{path} disappeared while verifying immutability"
                    )
                if _canonical_bytes(expected) != _canonical_bytes(
                    self._read_document(path)
                ):
                    raise ImmutableRecordError(
                        f"{relative} already contains different data"
                    )
                return observed
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        record = _validate_record_document(
            expected,
            expected_type=record_type,
            expected_key=key,
            expected_schema=schema_version,
        )
        return StoredRecord(
            payload=record.payload,
            payload_sha256=record.payload_sha256,
            record_sha256=record.record_sha256,
            relative_path=relative,
        )

    def _load(
        self,
        *,
        relative: PurePosixPath,
        record_type: str,
        key: Mapping[str, Any],
        schema_version: str = RECORD_SCHEMA_VERSION,
    ) -> StoredRecord | None:
        path = self._path(relative)
        if not path.exists():
            return None
        document = self._read_document(path)
        record = _validate_record_document(
            document,
            expected_type=record_type,
            expected_key=key,
            expected_schema=schema_version,
        )
        return StoredRecord(
            payload=record.payload,
            payload_sha256=record.payload_sha256,
            record_sha256=record.record_sha256,
            relative_path=relative,
        )

    @staticmethod
    def _read_document(path: Path) -> dict[str, Any]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise InvalidRecordError(f"{path} must not be a symlink") from exc
            raise
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise InvalidRecordError(f"{path} is not a regular file")
            if metadata.st_size > MAX_RECORD_BYTES:
                raise InvalidRecordError(f"{path} exceeds the record size limit")
            chunks: list[bytes] = []
            remaining = MAX_RECORD_BYTES + 1
            while remaining > 0:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > MAX_RECORD_BYTES:
                raise InvalidRecordError(f"{path} exceeds the record size limit")
        finally:
            os.close(fd)
        return _json_object(raw, path=path)

    @staticmethod
    def _fsync_directory(path: Path) -> None:
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        fd = os.open(path, flags)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
