"""Metrics-only W&B mirroring for immutable local attempt records."""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import re
import threading
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Literal

from .attempt_store import AttemptKey, AttemptStore, RunKey, StoredRecord


TRACKING_SCHEMA_VERSION = "pixcell-baseline-wandb-mirror-v1"
_METRIC_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9_./-]{0,127}$")
_WANDB_ENVIRONMENT_LOCK = threading.RLock()


class TrackingContractError(RuntimeError):
    """Tracking was requested without a valid saved record or metric set."""


@dataclass(frozen=True)
class TrackingResult:
    mirrored: bool
    wandb_run_id: str
    source_record_sha256: str
    tracking_error_relative_path: str | None = None


def deterministic_wandb_run_id(run_key: RunKey) -> str:
    """Return the stable W&B run ID used for create-or-resume."""

    canonical = json.dumps(
        {
            "schema_version": TRACKING_SCHEMA_VERSION,
            **run_key.as_dict(),
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "pxc-" + hashlib.sha256(canonical).hexdigest()[:28]


def validate_wandb_access(
    *,
    expected_entity: str | None,
    wandb_module: ModuleType | Any | None = None,
) -> dict[str, str | None]:
    """Verify the configured W&B identity before any paid sampling begins."""

    module = wandb_module or importlib.import_module("wandb")
    try:
        api = module.Api(timeout=20)
        viewer = api.viewer
        username = getattr(viewer, "username", None)
        entity = getattr(viewer, "entity", None) or getattr(
            api,
            "default_entity",
            None,
        )
    except Exception as exc:
        raise TrackingContractError("W&B credential preflight failed") from exc
    if not isinstance(username, str) or not username.strip():
        raise TrackingContractError("W&B credential resolved no authenticated user")
    if expected_entity is not None and entity != expected_entity:
        raise TrackingContractError(
            f"W&B entity mismatch: {entity!r} != {expected_entity!r}"
        )
    return {"username": username, "entity": entity}


def _metrics_payload(metrics: Mapping[str, int | float]) -> dict[str, int | float]:
    if not isinstance(metrics, Mapping) or not metrics:
        raise TrackingContractError("tracking metrics must be a non-empty mapping")
    result: dict[str, int | float] = {}
    for key, value in metrics.items():
        if not isinstance(key, str) or not _METRIC_NAME.fullmatch(key):
            raise TrackingContractError(f"invalid metric name: {key!r}")
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise TrackingContractError(
                f"metric {key!r} must be a finite integer or float"
            )
        result[key] = value
    return result


def _metrics_sha256(metrics: Mapping[str, int | float]) -> str:
    raw = json.dumps(
        metrics,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


@contextmanager
def _wandb_environment(wandb_dir: Path):
    names = ("WANDB_DIR", "WANDB_DISABLE_GIT", "WANDB_DISABLE_CODE", "WANDB_SAVE_CODE")
    previous = {name: os.environ.get(name) for name in names}
    os.environ.update(
        {
            "WANDB_DIR": str(wandb_dir),
            "WANDB_DISABLE_GIT": "true",
            "WANDB_DISABLE_CODE": "true",
            "WANDB_SAVE_CODE": "false",
        }
    )
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


class WandbMetricsMirror:
    """Mirror metrics only after their source attempt record is durable.

    W&B is deliberately an observability mirror, never the experiment record.
    Any W&B exception is converted into an immutable local tracking-error
    record while the sampling receipt/evaluation remains valid.
    """

    def __init__(
        self,
        *,
        store: AttemptStore,
        project: str,
        entity: str | None = None,
        group: str | None = None,
        wandb_dir: Path | None = None,
        wandb_module: ModuleType | Any | None = None,
    ) -> None:
        if not project.strip():
            raise TrackingContractError("W&B project must be non-empty")
        self.store = store
        self.project = project
        self.entity = entity
        self.group = group
        if self.group is not None and not self.group.strip():
            raise TrackingContractError("W&B group must be non-empty when provided")
        requested = (
            Path(wandb_dir).expanduser()
            if wandb_dir is not None
            else store.external_root / ".wandb"
        ).resolve(strict=False)
        if requested == store.repo_root or requested.is_relative_to(store.repo_root):
            raise TrackingContractError("WANDB_DIR must be outside the repository")
        requested.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.wandb_dir = requested.resolve(strict=True)
        if self.wandb_dir == store.repo_root or self.wandb_dir.is_relative_to(
            store.repo_root
        ):
            raise TrackingContractError("WANDB_DIR resolves inside the repository")
        self._wandb_module = wandb_module

    def mirror_saved_metrics(
        self,
        *,
        key: AttemptKey,
        source: Literal["sampling_receipt", "evaluation"],
        metrics: Mapping[str, int | float],
        step: int,
    ) -> TrackingResult:
        """Compatibility helper for one record and one short-lived session."""

        with self.session(key.run_key) as session:
            return session.mirror_saved_metrics(
                key=key,
                source=source,
                metrics=metrics,
                step=step,
            )

    def session(self, run_key: RunKey) -> WandbRunSession:
        """Create a lazy, persistent one-init-per-arm tracking session."""

        return WandbRunSession(mirror=self, run_key=run_key)

    def _load_saved_source(
        self,
        *,
        key: AttemptKey,
        source: Literal["sampling_receipt", "evaluation"],
    ) -> StoredRecord | None:
        if source == "sampling_receipt":
            return self.store.load_sampling_receipt(key)
        return self.store.load_evaluation(key)

    def _settings(self, module: Any) -> Any:
        return module.Settings(
            disable_code=True,
            disable_git=True,
            disable_job_creation=True,
            save_code=False,
            x_disable_machine_info=True,
            x_disable_stats=True,
            x_save_requirements=False,
        )

    def _init_kwargs(self, run_key: RunKey, run_id: str, module: Any) -> dict[str, Any]:
        result: dict[str, Any] = {
            "project": self.project,
            "id": run_id,
            "name": (
                f"{run_key.study_id}/{run_key.hypothesis_id}/{run_key.arm_id}"
            ),
            "resume": "allow",
            "dir": str(self.wandb_dir),
            "settings": self._settings(module),
        }
        if self.entity is not None:
            result["entity"] = self.entity
        if self.group is not None:
            result["group"] = self.group
        return result

    def _module(self) -> Any:
        if self._wandb_module is not None:
            return self._wandb_module
        return importlib.import_module("wandb")

    def _record_tracking_error(
        self,
        *,
        key: AttemptKey,
        saved: StoredRecord,
        source: Literal["sampling_receipt", "evaluation"],
        run_id: str,
        step: int,
        metrics_sha256: str,
        operation: Literal["init", "log", "finish"],
        error: Exception,
    ) -> StoredRecord:
        return self.store.write_tracking_error(
            key,
            {
                "schema_version": TRACKING_SCHEMA_VERSION,
                "source_record_type": source,
                "source_record_relative_path": str(saved.relative_path),
                "source_record_sha256": saved.record_sha256,
                "wandb_run_id": run_id,
                "wandb_step": step,
                "metrics_sha256": metrics_sha256,
                "operation": operation,
                "error_type": type(error).__name__,
                "error_message": str(error)[:4096],
            },
        )


class WandbRunSession:
    """One lazily initialized W&B run for one immutable PixCell arm."""

    def __init__(self, *, mirror: WandbMetricsMirror, run_key: RunKey) -> None:
        self.mirror = mirror
        self.run_key = run_key
        self.run_id = deterministic_wandb_run_id(run_key)
        self._run: Any | None = None
        self._closed = False
        self._last_context: tuple[
            AttemptKey,
            Literal["sampling_receipt", "evaluation"],
            StoredRecord,
            int,
            str,
        ] | None = None

    def __enter__(self) -> WandbRunSession:
        if self._closed:
            raise TrackingContractError("a closed W&B session cannot be reopened")
        # Initialization remains lazy so the first external tracking action
        # cannot precede its immutable local source record.
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def mirror_saved_metrics(
        self,
        *,
        key: AttemptKey,
        source: Literal["sampling_receipt", "evaluation"],
        metrics: Mapping[str, int | float],
        step: int,
    ) -> TrackingResult:
        if self._closed:
            raise TrackingContractError("W&B session is closed")
        if key.run_key != self.run_key:
            raise TrackingContractError(
                "attempt key belongs to a different W&B arm session"
            )
        if isinstance(step, bool) or not isinstance(step, int) or step < 0:
            raise TrackingContractError("W&B step must be a nonnegative integer")
        clean_metrics = _metrics_payload(metrics)
        saved = self.mirror._load_saved_source(key=key, source=source)
        if saved is None:
            raise TrackingContractError(
                f"cannot mirror {source} metrics before local state is saved"
            )
        metrics_sha = _metrics_sha256(clean_metrics)
        self._last_context = (key, source, saved, step, metrics_sha)
        try:
            if self._run is None:
                self._initialize()
        except Exception as exc:
            error = self.mirror._record_tracking_error(
                key=key,
                saved=saved,
                source=source,
                run_id=self.run_id,
                step=step,
                metrics_sha256=metrics_sha,
                operation="init",
                error=exc,
            )
            return TrackingResult(
                mirrored=False,
                wandb_run_id=self.run_id,
                source_record_sha256=saved.record_sha256,
                tracking_error_relative_path=str(error.relative_path),
            )

        try:
            with _WANDB_ENVIRONMENT_LOCK, _wandb_environment(
                self.mirror.wandb_dir
            ):
                # No task IDs, prompts, completions, programs, configs,
                # artifacts, tables, or source files cross this boundary.
                self._run.log(dict(clean_metrics), step=step, commit=True)
        except Exception as exc:
            error = self.mirror._record_tracking_error(
                key=key,
                saved=saved,
                source=source,
                run_id=self.run_id,
                step=step,
                metrics_sha256=metrics_sha,
                operation="log",
                error=exc,
            )
            return TrackingResult(
                mirrored=False,
                wandb_run_id=self.run_id,
                source_record_sha256=saved.record_sha256,
                tracking_error_relative_path=str(error.relative_path),
            )

        return TrackingResult(
            mirrored=True,
            wandb_run_id=self.run_id,
            source_record_sha256=saved.record_sha256,
        )

    def _initialize(self) -> None:
        module = self.mirror._module()
        init_kwargs = self.mirror._init_kwargs(self.run_key, self.run_id, module)
        # os.environ is process-global. Serialize this short section so
        # parallel samplers cannot restore WANDB_DIR beneath another init.
        with _WANDB_ENVIRONMENT_LOCK, _wandb_environment(self.mirror.wandb_dir):
            run = module.init(**init_kwargs)
        if run is None:
            raise RuntimeError("wandb.init returned no run")
        self._run = run

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._run is None:
            return
        try:
            with _WANDB_ENVIRONMENT_LOCK, _wandb_environment(
                self.mirror.wandb_dir
            ):
                self._run.finish()
        except Exception as exc:
            if self._last_context is None:
                raise
            key, source, saved, step, metrics_sha = self._last_context
            self.mirror._record_tracking_error(
                key=key,
                saved=saved,
                source=source,
                run_id=self.run_id,
                step=step,
                metrics_sha256=metrics_sha,
                operation="finish",
                error=exc,
            )
        finally:
            self._run = None
