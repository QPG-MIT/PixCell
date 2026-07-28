"""External, immutable records for paid training stages."""

from __future__ import annotations

import errno
import fcntl
import hashlib
import json
import os
import re
import stat
import threading
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


RECORD_SCHEMA_VERSION = "pixcell-training-record-v1"
MAX_RECORD_BYTES = 16 * 1024 * 1024
_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class TrainingStoreError(RuntimeError):
    """Training record storage failed closed."""


class UnsafeTrainingRootError(TrainingStoreError):
    """Training output overlaps the source repository."""


class TrainingRunLockedError(TrainingStoreError):
    """Another process owns this exact stage and replicate."""


class ImmutableTrainingRecordError(TrainingStoreError):
    """An existing record differs from the proposed immutable value."""


@dataclass(frozen=True, order=True)
class StageKey:
    study_id: str
    stage_id: str
    replicate_id: str

    def __post_init__(self) -> None:
        for field, value in (
            ("study_id", self.study_id),
            ("stage_id", self.stage_id),
            ("replicate_id", self.replicate_id),
        ):
            if not _IDENTIFIER.fullmatch(value):
                raise ValueError(f"{field} has an invalid identifier: {value!r}")

    def as_dict(self) -> dict[str, str]:
        return {
            "study_id": self.study_id,
            "stage_id": self.stage_id,
            "replicate_id": self.replicate_id,
        }


@dataclass(frozen=True)
class TrainingRecord:
    payload: dict[str, Any]
    payload_sha256: str
    record_sha256: str
    relative_path: PurePosixPath


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TrainingStoreError("training record is not finite JSON") from exc


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _normalized_object(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TrainingStoreError("training record payload must be an object")
    result = json.loads(canonical_bytes(value))
    if not isinstance(result, dict):
        raise TrainingStoreError("training record payload must be an object")
    return result


def _document(
    *,
    record_type: str,
    key: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = _normalized_object(payload)
    base = {
        "schema_version": RECORD_SCHEMA_VERSION,
        "record_type": record_type,
        "key": dict(key),
        "payload": normalized,
        "payload_sha256": canonical_sha256(normalized),
    }
    base["record_sha256"] = canonical_sha256(base)
    return base


def _validate_document(
    value: Mapping[str, Any],
    *,
    record_type: str,
    key: Mapping[str, Any],
    relative_path: PurePosixPath,
) -> TrainingRecord:
    required = {
        "schema_version",
        "record_type",
        "key",
        "payload",
        "payload_sha256",
        "record_sha256",
    }
    if set(value) != required:
        raise TrainingStoreError("training record fields differ from the schema")
    if value["schema_version"] != RECORD_SCHEMA_VERSION:
        raise TrainingStoreError("training record has a foreign schema")
    if value["record_type"] != record_type or value["key"] != dict(key):
        raise TrainingStoreError("training record key or type differs from its path")
    payload = value["payload"]
    if not isinstance(payload, dict):
        raise TrainingStoreError("training record payload is not an object")
    payload_sha = canonical_sha256(payload)
    if payload_sha != value["payload_sha256"] or not _SHA256.fullmatch(payload_sha):
        raise TrainingStoreError("training record payload digest differs")
    unsigned = dict(value)
    record_sha = str(unsigned.pop("record_sha256"))
    if canonical_sha256(unsigned) != record_sha:
        raise TrainingStoreError("training record envelope digest differs")
    return TrainingRecord(
        payload=dict(payload),
        payload_sha256=payload_sha,
        record_sha256=record_sha,
        relative_path=relative_path,
    )


class _StageLock:
    def __init__(self, store: TrainingStore, key: StageKey, path: Path) -> None:
        self.store = store
        self.key = key
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> _StageLock:
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(self.path, flags, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            if "fd" in locals():
                os.close(fd)
            raise TrainingRunLockedError(f"{self.key} is already active") from exc
        try:
            self.store._mark_held(self.key)
        except Exception:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            raise
        self.fd = fd
        return self

    def __exit__(self, *_: object) -> None:
        if self.fd is None:
            return
        self.store._mark_released(self.key)
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)
        self.fd = None


class TrainingStore:
    """Create-only stage records and candidate evidence outside Git."""

    def __init__(self, *, repo_root: Path, external_root: Path) -> None:
        self.repo_root = repo_root.expanduser().resolve(strict=True)
        requested = external_root.expanduser().resolve(strict=False)
        if (
            requested == self.repo_root
            or requested.is_relative_to(self.repo_root)
            or self.repo_root.is_relative_to(requested)
        ):
            raise UnsafeTrainingRootError("training output overlaps the repository")
        requested.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.external_root = requested.resolve(strict=True)
        if (
            self.external_root == self.repo_root
            or self.external_root.is_relative_to(self.repo_root)
            or self.repo_root.is_relative_to(self.external_root)
        ):
            raise UnsafeTrainingRootError("training output resolves across the repository")
        self._held: set[StageKey] = set()
        self._guard = threading.Lock()

    @staticmethod
    def stage_relative_path(key: StageKey) -> PurePosixPath:
        return PurePosixPath(
            "studies",
            key.study_id,
            "stages",
            key.stage_id,
            "runs",
            key.replicate_id,
        )

    def stage_path(self, key: StageKey) -> Path:
        return self._path(self.stage_relative_path(key))

    def tinker_log_path(self, key: StageKey) -> Path:
        return self.stage_path(key) / "tinker"

    def candidate_root(self, key: StageKey) -> Path:
        return self.stage_path(key) / "candidates"

    def acquire_stage_lock(self, key: StageKey) -> _StageLock:
        digest = canonical_sha256(key.as_dict())
        return _StageLock(
            self,
            key,
            self.external_root / ".locks" / f"{digest}.lock",
        )

    def _mark_held(self, key: StageKey) -> None:
        with self._guard:
            if key in self._held:
                raise TrainingRunLockedError(f"{key} is already locked here")
            self._held.add(key)

    def _mark_released(self, key: StageKey) -> None:
        with self._guard:
            self._held.discard(key)

    def _require_lock(self, key: StageKey) -> None:
        with self._guard:
            if key not in self._held:
                raise TrainingStoreError("a stage lock is required before writing")

    def create_or_verify_manifest(
        self,
        key: StageKey,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        self._require_lock(key)
        return self._create_or_verify(
            self.stage_relative_path(key) / "run_manifest.json",
            record_type="run_manifest",
            key=key.as_dict(),
            payload=payload,
        )

    def load_manifest(self, key: StageKey) -> TrainingRecord | None:
        return self._load(
            self.stage_relative_path(key) / "run_manifest.json",
            record_type="run_manifest",
            key=key.as_dict(),
        )

    def write_wave_receipt(
        self,
        key: StageKey,
        *,
        wave: str,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        self._require_lock(key)
        if not _IDENTIFIER.fullmatch(wave):
            raise ValueError(f"invalid wave name: {wave!r}")
        if self.load_manifest(key) is None:
            raise TrainingStoreError("wave receipt cannot precede its run manifest")
        return self._create_or_verify(
            self.stage_relative_path(key) / "waves" / wave / "receipt.json",
            record_type="wave_receipt",
            key={**key.as_dict(), "wave": wave},
            payload=payload,
        )

    def load_wave_receipt(
        self,
        key: StageKey,
        *,
        wave: str,
    ) -> TrainingRecord | None:
        return self._load(
            self.stage_relative_path(key) / "waves" / wave / "receipt.json",
            record_type="wave_receipt",
            key={**key.as_dict(), "wave": wave},
        )

    def write_wave_approval(
        self,
        key: StageKey,
        *,
        wave: str,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        """Bind a non-initial paid wave to one immutable review decision."""

        self._require_lock(key)
        if not _IDENTIFIER.fullmatch(wave):
            raise ValueError(f"invalid wave name: {wave!r}")
        return self._create_or_verify(
            self.stage_relative_path(key) / "waves" / wave / "approval.json",
            record_type="wave_approval",
            key={**key.as_dict(), "wave": wave},
            payload=payload,
        )

    def load_wave_approval(
        self,
        key: StageKey,
        *,
        wave: str,
    ) -> TrainingRecord | None:
        return self._load(
            self.stage_relative_path(key) / "waves" / wave / "approval.json",
            record_type="wave_approval",
            key={**key.as_dict(), "wave": wave},
        )

    def write_candidate(
        self,
        key: StageKey,
        *,
        invocation_id: str,
        step: int,
        task_id: str,
        attempt: int,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        self._require_lock(key)
        if (
            not _IDENTIFIER.fullmatch(invocation_id)
            or step < 0
            or attempt < 1
            or not _IDENTIFIER.fullmatch(task_id)
        ):
            raise ValueError("invalid candidate key")
        return self._create_or_verify(
            self.stage_relative_path(key)
            / "candidates"
            / invocation_id
            / f"step-{step:06d}"
            / task_id
            / f"attempt-{attempt:02d}"
            / "evaluation.json",
            record_type="candidate_evaluation",
            key={
                **key.as_dict(),
                "invocation_id": invocation_id,
                "step": step,
                "task_id": task_id,
                "attempt": attempt,
            },
            payload=payload,
        )

    def write_candidate_sample(
        self,
        key: StageKey,
        *,
        invocation_id: str,
        step: int,
        task_id: str,
        attempt: int,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        """Persist paid model output before deterministic evaluation begins."""

        self._require_lock(key)
        if (
            not _IDENTIFIER.fullmatch(invocation_id)
            or step < 0
            or attempt < 1
            or not _IDENTIFIER.fullmatch(task_id)
        ):
            raise ValueError("invalid candidate key")
        return self._create_or_verify(
            self.stage_relative_path(key)
            / "candidates"
            / invocation_id
            / f"step-{step:06d}"
            / task_id
            / f"attempt-{attempt:02d}"
            / "sample.json",
            record_type="candidate_sample",
            key={
                **key.as_dict(),
                "invocation_id": invocation_id,
                "step": step,
                "task_id": task_id,
                "attempt": attempt,
            },
            payload=payload,
        )

    def load_candidate_sample(
        self,
        key: StageKey,
        *,
        invocation_id: str,
        step: int,
        task_id: str,
        attempt: int,
    ) -> TrainingRecord | None:
        return self._load(
            self.stage_relative_path(key)
            / "candidates"
            / invocation_id
            / f"step-{step:06d}"
            / task_id
            / f"attempt-{attempt:02d}"
            / "sample.json",
            record_type="candidate_sample",
            key={
                **key.as_dict(),
                "invocation_id": invocation_id,
                "step": step,
                "task_id": task_id,
                "attempt": attempt,
            },
        )

    def begin_invocation(
        self,
        key: StageKey,
        *,
        invocation_id: str,
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        """Record one process entry so stochastic crash retries never collide."""

        self._require_lock(key)
        if not _IDENTIFIER.fullmatch(invocation_id):
            raise ValueError(f"invalid invocation ID: {invocation_id!r}")
        if self.load_manifest(key) is None:
            raise TrainingStoreError("invocation cannot precede its run manifest")
        return self._create_or_verify(
            self.stage_relative_path(key)
            / "invocations"
            / invocation_id
            / "start.json",
            record_type="invocation",
            key={**key.as_dict(), "invocation_id": invocation_id},
            payload=payload,
        )

    def _path(self, relative: PurePosixPath) -> Path:
        path = self.external_root.joinpath(*relative.parts)
        parent = path.parent.resolve(strict=False)
        if parent != self.external_root and not parent.is_relative_to(self.external_root):
            raise UnsafeTrainingRootError("training record path escaped its root")
        return path

    def _create_or_verify(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> TrainingRecord:
        expected = _document(record_type=record_type, key=key, payload=payload)
        path = self._path(relative)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw = canonical_bytes(expected) + b"\n"
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
                observed = self._load(relative, record_type=record_type, key=key)
                if observed is None or canonical_bytes(expected) != canonical_bytes(
                    self._read(path)
                ):
                    raise ImmutableTrainingRecordError(
                        f"{relative} already contains different data"
                    )
                return observed
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        return _validate_document(
            expected,
            record_type=record_type,
            key=key,
            relative_path=relative,
        )

    def _load(
        self,
        relative: PurePosixPath,
        *,
        record_type: str,
        key: Mapping[str, Any],
    ) -> TrainingRecord | None:
        path = self._path(relative)
        if not path.exists():
            return None
        return _validate_document(
            self._read(path),
            record_type=record_type,
            key=key,
            relative_path=relative,
        )

    @staticmethod
    def _read(path: Path) -> dict[str, Any]:
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise TrainingStoreError(f"{path} must not be a symlink") from exc
            raise
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_RECORD_BYTES:
                raise TrainingStoreError(f"{path} is not a bounded regular file")
            chunks: list[bytes] = []
            remaining = MAX_RECORD_BYTES + 1
            while remaining:
                chunk = os.read(fd, min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            raw = b"".join(chunks)
            if len(raw) > MAX_RECORD_BYTES:
                raise TrainingStoreError(f"{path} exceeds the record limit")
        finally:
            os.close(fd)
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TrainingStoreError(f"{path} is not valid JSON") from exc
        if not isinstance(value, dict):
            raise TrainingStoreError(f"{path} must contain an object")
        return value
