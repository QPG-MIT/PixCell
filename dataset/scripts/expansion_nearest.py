"""Nearest-neighbor helpers for visual-only PixCell expansion proposals.

The proposal index deliberately contains only the 547 semantic ``core-v1``
anchors.  Pose, calibration, and realization descendants are excluded so they
cannot masquerade as independent representations during expansion review.

Raster similarity is review telemetry.  It can expose an accidental visual
alias, but it does not prove that a proposed construction grammar is novel.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
from PIL import Image
from scipy import ndimage
from skimage.transform import resize

from _shared import LEVELS, ReleaseError, normalized_d4_sha256, read_json


NORMALIZED_SIZE = 192
NORMALIZED_MARGIN = 6


@dataclass(frozen=True)
class CoreSemanticAnchor:
    """One canonical semantic representation from the frozen core."""

    example_id: str
    representation_id: str
    level: str
    family: str
    label: str
    d4_sha256: str
    mask: np.ndarray = field(repr=False, compare=False)
    dilated_mask: np.ndarray = field(repr=False, compare=False)
    image_bytes: bytes = field(repr=False, compare=False)


def _one_parquet(root: Path, level: str) -> Path:
    matches = sorted((root / "data" / level).glob("train-*.parquet"))
    if len(matches) != 1:
        raise ReleaseError(
            f"{level}: expected exactly one Parquet shard, found {len(matches)}"
        )
    return matches[0]


def _embedded_bytes(example_id: str, value: Any) -> bytes:
    payload = value.get("bytes") if isinstance(value, dict) else None
    if not payload:
        raise ReleaseError(f"{example_id}: semantic anchor image is not embedded")
    return bytes(payload)


def image_from_bytes(payload: bytes) -> Image.Image:
    """Decode image bytes into an independent grayscale PIL image."""

    try:
        with Image.open(io.BytesIO(payload)) as opened:
            return opened.convert("L")
    except OSError as exc:
        raise ReleaseError("could not decode proposal comparison image") from exc


def normalized_material_mask(
    image: Image.Image | np.ndarray,
    *,
    size: int = NORMALIZED_SIZE,
    margin: int = NORMALIZED_MARGIN,
    white_threshold: int = 245,
) -> np.ndarray:
    """Crop and uniformly fit a nonempty material mask into a square."""

    if size < 32 or margin < 0 or 2 * margin >= size:
        raise ReleaseError("invalid normalized expansion-raster dimensions")
    if isinstance(image, Image.Image):
        array = np.asarray(image.convert("L"))
    else:
        array = np.asarray(image)
        if array.ndim == 3:
            array = np.asarray(Image.fromarray(array.astype(np.uint8)).convert("L"))
    if array.ndim != 2 or not array.size:
        raise ReleaseError(f"proposal raster must be nonempty and 2-D: {array.shape}")
    mask = array < white_threshold
    if not mask.any():
        raise ReleaseError("proposal raster contains no material")
    ys, xs = np.nonzero(mask)
    cropped = mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]
    available = size - 2 * margin
    scale = min(available / cropped.shape[0], available / cropped.shape[1])
    height = max(1, min(available, int(round(cropped.shape[0] * scale))))
    width = max(1, min(available, int(round(cropped.shape[1] * scale))))
    fitted = (
        resize(
            cropped.astype(np.uint8),
            (height, width),
            order=0,
            mode="constant",
            preserve_range=True,
            anti_aliasing=False,
        )
        >= 0.5
    )
    canvas = np.zeros((size, size), dtype=bool)
    x0 = (size - width) // 2
    y0 = (size - height) // 2
    canvas[y0 : y0 + height, x0 : x0 + width] = fitted
    return canvas


def _binary_iou(left: np.ndarray, right: np.ndarray) -> float:
    union = int(np.logical_or(left, right).sum())
    return float(np.logical_and(left, right).sum() / union) if union else 1.0


def aligned_mask_similarity(
    left: Image.Image | np.ndarray,
    right: Image.Image | np.ndarray,
) -> dict[str, Any]:
    """Return bbox/scale/D4-aligned IoU as curator-facing telemetry."""

    left_mask = (
        left
        if isinstance(left, np.ndarray)
        and left.dtype == np.bool_
        and left.shape == (NORMALIZED_SIZE, NORMALIZED_SIZE)
        else normalized_material_mask(left)
    )
    right_mask = (
        right
        if isinstance(right, np.ndarray)
        and right.dtype == np.bool_
        and right.shape == (NORMALIZED_SIZE, NORMALIZED_SIZE)
        else normalized_material_mask(right)
    )
    left_dilated = ndimage.binary_dilation(left_mask, iterations=2)
    right_dilated = ndimage.binary_dilation(right_mask, iterations=2)
    return _aligned_prepared(
        left_mask,
        left_dilated,
        right_mask,
        right_dilated,
    )


def _aligned_prepared(
    left_mask: np.ndarray,
    left_dilated: np.ndarray,
    right_mask: np.ndarray,
    right_dilated: np.ndarray,
) -> dict[str, Any]:
    """Compare masks whose dilation has already been computed.

    Binary dilation commutes with every D4 transform, so semantic-anchor
    dilation is cached once instead of repeated for every proposal/transform.
    """

    candidates: list[tuple[float, float, int, bool]] = []
    for quarter_turn in range(4):
        rotated = np.rot90(right_mask, quarter_turn)
        rotated_dilated = np.rot90(right_dilated, quarter_turn)
        for mirrored in (False, True):
            transformed = np.fliplr(rotated) if mirrored else rotated
            transformed_dilated = (
                np.fliplr(rotated_dilated) if mirrored else rotated_dilated
            )
            raw_iou = _binary_iou(left_mask, transformed)
            dilated_iou = _binary_iou(left_dilated, transformed_dilated)
            candidates.append((dilated_iou, raw_iou, quarter_turn * 90, mirrored))
    dilated_iou, raw_iou, angle, mirrored = max(candidates)
    return {
        "aligned_raw_iou": round(raw_iou, 8),
        "aligned_dilated_iou": round(dilated_iou, 8),
        "right_transform_deg": angle,
        "right_mirrored": mirrored,
        "alignment": "bbox_centered_uniform_scale_plus_d4",
        "admission_role": "review_only",
    }


def load_core_semantic_anchors(dataset_root: Path) -> tuple[CoreSemanticAnchor, ...]:
    """Load exactly one anchor for every frozen representation."""

    root = dataset_root.expanduser().resolve()
    freeze = read_json(root / "factory" / "core-v1" / "freeze.json")
    expected_count = freeze.get("representation_count")
    if not isinstance(expected_count, int) or expected_count < 1:
        raise ReleaseError("core-v1 freeze has no representation count")

    anchors: list[CoreSemanticAnchor] = []
    for level in LEVELS:
        table = pq.read_table(
            _one_parquet(root, level),
            columns=[
                "id",
                "representation_id",
                "variation_role",
                "level",
                "family",
                "label",
                "image",
                "normalized_d4_sha256",
            ],
        )
        for row in table.to_pylist():
            if row["variation_role"] != "semantic":
                continue
            payload = _embedded_bytes(str(row["id"]), row["image"])
            image = image_from_bytes(payload)
            observed_d4 = normalized_d4_sha256(image)
            if observed_d4 != row["normalized_d4_sha256"]:
                raise ReleaseError(f"{row['id']}: frozen D4 witness drifted")
            anchors.append(
                CoreSemanticAnchor(
                    example_id=str(row["id"]),
                    representation_id=str(row["representation_id"]),
                    level=str(row["level"]),
                    family=str(row["family"]),
                    label=str(row["label"]),
                    d4_sha256=observed_d4,
                    mask=(mask := normalized_material_mask(image)),
                    dilated_mask=ndimage.binary_dilation(mask, iterations=2),
                    image_bytes=payload,
                )
            )

    if len(anchors) != expected_count:
        raise ReleaseError(
            f"semantic anchor count {len(anchors)} != frozen {expected_count}"
        )
    example_ids = [anchor.example_id for anchor in anchors]
    representation_ids = [anchor.representation_id for anchor in anchors]
    if len(example_ids) != len(set(example_ids)):
        raise ReleaseError("core semantic anchor IDs are not unique")
    if len(representation_ids) != len(set(representation_ids)):
        raise ReleaseError("core semantic representation IDs are not unique")
    return tuple(anchors)


def anchor_lookup(
    anchors: tuple[CoreSemanticAnchor, ...],
) -> dict[str, CoreSemanticAnchor]:
    """Index anchors by both public example ID and representation ID."""

    result: dict[str, CoreSemanticAnchor] = {}
    for anchor in anchors:
        for key in (anchor.example_id, anchor.representation_id):
            previous = result.setdefault(key, anchor)
            if previous is not anchor:
                raise ReleaseError(f"ambiguous semantic anchor identifier: {key}")
    return result


def nearest_semantic_anchors(
    image: Image.Image | np.ndarray,
    anchors: tuple[CoreSemanticAnchor, ...],
    *,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Rank frozen semantic anchors by aligned silhouette similarity."""

    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k < 1:
        raise ReleaseError("top_k must be a positive integer")
    candidate_mask = normalized_material_mask(image)
    candidate_dilated = ndimage.binary_dilation(candidate_mask, iterations=2)
    rows = []
    for anchor in anchors:
        rows.append(
            {
                "example_id": anchor.example_id,
                "representation_id": anchor.representation_id,
                "level": anchor.level,
                "family": anchor.family,
                "label": anchor.label,
                **_aligned_prepared(
                    candidate_mask,
                    candidate_dilated,
                    anchor.mask,
                    anchor.dilated_mask,
                ),
            }
        )
    rows.sort(
        key=lambda row: (
            -float(row["aligned_dilated_iou"]),
            -float(row["aligned_raw_iou"]),
            str(row["example_id"]),
        )
    )
    return rows[:top_k]


__all__ = [
    "CoreSemanticAnchor",
    "aligned_mask_similarity",
    "anchor_lookup",
    "image_from_bytes",
    "load_core_semantic_anchors",
    "nearest_semantic_anchors",
    "normalized_material_mask",
]
