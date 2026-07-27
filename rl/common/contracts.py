"""Shared projections that keep model, sampler, label, and verifier data apart."""

from __future__ import annotations

import hashlib
import io
import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from PIL import Image


def _image_bytes(value: Any, *, field: str) -> bytes:
    if isinstance(value, (bytes, bytearray, memoryview)):
        payload = bytes(value)
    elif isinstance(value, Mapping):
        embedded = value.get("bytes")
        if embedded is None:
            raise ValueError(f"{field} has no embedded bytes")
        payload = bytes(embedded)
    elif isinstance(value, Image.Image):
        buffer = io.BytesIO()
        value.save(buffer, format="PNG")
        payload = buffer.getvalue()
    else:
        raise TypeError(f"{field} must be embedded image bytes, not {type(value).__name__}")
    if not payload:
        raise ValueError(f"{field} is empty")
    return payload


def _footprint(value: Any) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("footprint_um must contain [length, width]")
    result = (float(value[0]), float(value[1]))
    if any(not math.isfinite(item) or item <= 0 for item in result):
        raise ValueError("footprint_um values must be finite and positive")
    return result


def _check_sha(payload: bytes, expected: Any, *, field: str) -> str:
    observed = hashlib.sha256(payload).hexdigest()
    if expected and str(expected) != observed:
        raise ValueError(f"{field} SHA-256 mismatch")
    return observed


@dataclass(frozen=True)
class ModelObservation:
    """The row projection from which the policy input is constructed.

    ``image_sha256`` is retained only for integrity checking; prompt builders
    serialize the image and footprint, never the digest. The projection has no
    row identifier, class label, calibration, target raster, representation
    metadata, or expected program.
    """

    image_bytes: bytes
    footprint_um: tuple[float, float]
    image_sha256: str


@dataclass(frozen=True)
class SupervisedExample:
    observation: ModelObservation
    code: str


@dataclass(frozen=True)
class VerifierReference:
    """Private reference state retained by the evaluator."""

    target_image_bytes: bytes
    footprint_um: tuple[float, float]
    target_image_sha256: str


@dataclass(frozen=True)
class SamplerMetadata:
    """Private curriculum/sampling fields; none are serialized into a prompt."""

    opaque_id: str
    level: str
    representation_id: str
    leakage_group_id: str
    realization_slot: int | None
    split_role: str


@dataclass(frozen=True)
class TaskRecord:
    observation: ModelObservation
    label: str
    reference: VerifierReference
    sampler: SamplerMetadata


def observation_from_row(row: Mapping[str, Any]) -> ModelObservation:
    """Project a dataset row using only the two policy-visible fields."""

    image = _image_bytes(row["image"], field="image")
    footprint = _footprint(row["footprint_um"])
    digest = _check_sha(image, row.get("image_sha256"), field="image")
    return ModelObservation(image, footprint, digest)


def supervised_from_row(row: Mapping[str, Any]) -> SupervisedExample:
    observation = observation_from_row(row)
    code = str(row["code"])
    if not code.strip():
        raise ValueError("code label is empty")
    return SupervisedExample(observation, code)


def reference_from_row(row: Mapping[str, Any]) -> VerifierReference:
    target = _image_bytes(row["target_image"], field="target_image")
    footprint = _footprint(row["footprint_um"])
    digest = _check_sha(
        target,
        row.get("target_image_sha256"),
        field="target_image",
    )
    return VerifierReference(target, footprint, digest)


def sampler_from_row(row: Mapping[str, Any]) -> SamplerMetadata:
    source_id = str(row["id"])
    opaque_id = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]
    slot = row.get("realization_slot")
    return SamplerMetadata(
        opaque_id=opaque_id,
        level=str(row.get("level", "")),
        representation_id=str(row.get("representation_id", "")),
        leakage_group_id=str(row.get("leakage_group_id", "")),
        realization_slot=int(slot) if slot is not None else None,
        split_role=str(row.get("split_role", "train")),
    )


def task_from_row(row: Mapping[str, Any]) -> TaskRecord:
    """Build all projections only after a row has been selected by the sampler."""

    supervised = supervised_from_row(row)
    return TaskRecord(
        observation=supervised.observation,
        label=supervised.code,
        reference=reference_from_row(row),
        sampler=sampler_from_row(row),
    )
