#!/usr/bin/env python3
"""Compile a visual-only PixCell grammar proposal wave for human review.

This command is intentionally separate from ``build_all.py``.  It reads the
frozen release, a curator-authored ``specs.json``, and the central
``scripts/proposal_scenes.py`` module, then writes only:

``factory/expansion/<wave>/generated/``

No Parquet row is created or admitted.  The command snapshots every hash-bound
``core-v1`` artifact before rendering and fails if any of them changes.

Scene-module interface
----------------------
``scripts/proposal_scenes.py`` must expose:

``build_proposal(candidate: Mapping[str, Any]) -> gf.Component``

The compiler owns maximum-visibility rasterization, nearest-core comparison,
manifests, and review galleries.  Scene code only constructs proposal geometry.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

from _shared import (
    SAFE_PUBLIC_ID,
    ReleaseError,
    canonical_sha256,
    normalized_d4_sha256,
    read_json,
    scan_value_strings,
    sha256_file,
    write_json,
)
from expansion_nearest import (
    CoreSemanticAnchor,
    aligned_mask_similarity,
    anchor_lookup,
    image_from_bytes,
    load_core_semantic_anchors,
    nearest_semantic_anchors,
)


SPEC_SCHEMA_VERSION = "pixcell-expansion-wave-spec-1"
OUTPUT_SCHEMA_VERSION = "pixcell-expansion-grammar-render-v1"
DEFAULT_WAVE = "wave-1"
GENERATED_NAME = "generated"
ALLOWED_LEVELS = frozenset({"L1", "L2", "L3", "L4"})
LEVEL_ORDER = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4}
PROPOSAL_ONLY_STATUS = "proposal_only_requires_human_approval"
PORT_SIGNATURE = re.compile(r"^\d+x\d+$")
MODEL_VIEW_SIZE_PX = (1440, 1093)
RASTER_MARGIN_PX = 36
NEAREST_TOP_K = 5
PROPOSAL_VOID_LAYER = (2, 0)


@dataclass(frozen=True)
class FrozenCoreSnapshot:
    """Hashes that an expansion preview is forbidden to change."""

    core_name: str
    release_digest_sha256: str
    row_count: int
    representation_count: int
    file_sha256: Mapping[str, str]
    core_prerequisite_levels: Mapping[str, str]
    core_anchor_aliases: Mapping[str, str]


@dataclass(frozen=True)
class RenderedProposal:
    """Generated review evidence for one proposal."""

    candidate: Mapping[str, Any]
    image_path: Path
    image: Image.Image
    footprint_um: tuple[float, float]
    calibration: Mapping[str, Any]
    observed_ports: tuple[Mapping[str, Any], ...]
    nearest: tuple[Mapping[str, Any], ...]
    declared_nearest: tuple[Mapping[str, Any], ...]


def _release_path(root: Path, relative: object, *, label: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ReleaseError(f"{label} must be a nonempty release-relative path")
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise ReleaseError(f"{label} is not release-relative: {relative!r}")
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ReleaseError(f"{label} escapes the dataset package") from exc
    if not candidate.is_file():
        raise ReleaseError(f"{label} is missing: {relative}")
    return candidate


def snapshot_frozen_core(dataset_root: Path) -> FrozenCoreSnapshot:
    """Verify and capture the immutable core boundary."""

    root = dataset_root.expanduser().resolve()
    freeze_path = root / "factory" / "core-v1" / "freeze.json"
    freeze = read_json(freeze_path)
    if freeze.get("core_name") != "core-v1":
        raise ReleaseError("expansion requires the frozen core-v1 release")

    files: dict[str, str] = {
        freeze_path.relative_to(root).as_posix(): sha256_file(freeze_path)
    }

    def add_frozen(
        relative: object,
        *,
        label: str,
        expected_sha256: object | None = None,
    ) -> Path:
        path = _release_path(root, relative, label=label)
        digest = sha256_file(path)
        if expected_sha256 is not None and digest != expected_sha256:
            raise ReleaseError(f"{label} differs from core-v1 freeze")
        files[path.relative_to(root).as_posix()] = digest
        return path

    source = freeze.get("source_bundle")
    if not isinstance(source, dict):
        raise ReleaseError("core-v1 freeze has no source bundle")
    add_frozen(
        source.get("path"),
        label="core source archive",
        expected_sha256=source.get("sha256"),
    )
    add_frozen(
        source.get("inventory_path"),
        label="core source inventory",
    )

    grammar_catalog_path: Path | None = None
    for key, label in (
        ("grammar_catalog", "core grammar catalog"),
        ("admission_policy", "core admission policy"),
        ("reproducibility_report", "core reproducibility report"),
    ):
        record = freeze.get(key)
        if not isinstance(record, dict):
            raise ReleaseError(f"core-v1 freeze has no {key}")
        frozen_path = add_frozen(
            record.get("path"),
            label=label,
            expected_sha256=record.get("sha256"),
        )
        if key == "grammar_catalog":
            grammar_catalog_path = frozen_path

    reference = freeze.get("reference_artifacts")
    if not isinstance(reference, dict) or not reference:
        raise ReleaseError("core-v1 freeze has no reference artifacts")
    for relative, digest in sorted(reference.items()):
        add_frozen(
            relative,
            label=f"core reference artifact {relative}",
            expected_sha256=digest,
        )

    release_digest = freeze.get("release_digest_sha256")
    row_count = freeze.get("row_count")
    representation_count = freeze.get("representation_count")
    if (
        not isinstance(release_digest, str)
        or not isinstance(row_count, int)
        or not isinstance(representation_count, int)
    ):
        raise ReleaseError("core-v1 freeze counts or digest are malformed")
    if grammar_catalog_path is None:
        raise ReleaseError("core-v1 freeze has no grammar catalog path")
    grammar_catalog = read_json(grammar_catalog_path)
    catalog_rows = grammar_catalog.get("rows")
    if not isinstance(catalog_rows, list) or not catalog_rows:
        raise ReleaseError("core-v1 grammar catalog has no rows")
    core_prerequisite_levels: dict[str, str] = {}
    core_anchor_aliases: dict[str, str] = {}
    for row in catalog_rows:
        if not isinstance(row, dict):
            raise ReleaseError("core-v1 grammar catalog contains a malformed row")
        level = row.get("level")
        if level not in LEVEL_ORDER:
            raise ReleaseError("core-v1 grammar catalog contains an invalid level")
        for key in ("concept_id", "id", "grammar_id"):
            identifier = row.get(key)
            if not isinstance(identifier, str) or not identifier:
                raise ReleaseError(
                    f"core-v1 grammar catalog row has no valid {key}"
                )
            previous = core_prerequisite_levels.setdefault(identifier, level)
            if previous != level:
                raise ReleaseError(
                    f"core prerequisite ID {identifier!r} spans multiple levels"
                )
        example_id = str(row["id"])
        representation_id = str(row["grammar_id"])
        previous_alias = core_anchor_aliases.setdefault(
            example_id,
            representation_id,
        )
        if previous_alias != representation_id:
            raise ReleaseError(
                f"core example ID {example_id!r} spans multiple representations"
            )
    return FrozenCoreSnapshot(
        core_name="core-v1",
        release_digest_sha256=release_digest,
        row_count=row_count,
        representation_count=representation_count,
        file_sha256=dict(sorted(files.items())),
        core_prerequisite_levels=dict(sorted(core_prerequisite_levels.items())),
        core_anchor_aliases=dict(sorted(core_anchor_aliases.items())),
    )


def assert_frozen_core_unchanged(
    before: FrozenCoreSnapshot,
    dataset_root: Path,
) -> None:
    """Fail if proposal work changed any frozen path or digest."""

    after = snapshot_frozen_core(dataset_root)
    if after != before:
        changed = sorted(
            path
            for path in set(before.file_sha256) | set(after.file_sha256)
            if before.file_sha256.get(path) != after.file_sha256.get(path)
        )
        raise ReleaseError(f"proposal build changed frozen core files: {changed}")


def safe_generated_output(
    dataset_root: Path,
    wave_id: str,
    requested: Path | None = None,
) -> Path:
    """Resolve the one directory a proposal compiler may replace."""

    if SAFE_PUBLIC_ID.fullmatch(wave_id) is None:
        raise ReleaseError(f"unsafe expansion wave ID: {wave_id!r}")
    root = dataset_root.expanduser().resolve()
    expected = (root / "factory" / "expansion" / wave_id / GENERATED_NAME).resolve()
    output = expected if requested is None else requested.expanduser().resolve()
    if output != expected:
        raise ReleaseError(
            "proposal output must be exactly "
            f"factory/expansion/{wave_id}/{GENERATED_NAME}"
        )
    return output


def _nonempty_string(candidate_id: str, value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseError(f"{candidate_id}: {field} must be a nonempty string")
    return value.strip()


def validate_proposal_specs(
    payload: Any,
    *,
    wave_id: str,
    core: FrozenCoreSnapshot,
    anchors: tuple[CoreSemanticAnchor, ...],
) -> list[dict[str, Any]]:
    """Validate the curator-authored proposal registry."""

    if not isinstance(payload, dict):
        raise ReleaseError("expansion specs must contain a JSON object")
    if payload.get("schema_version") != SPEC_SCHEMA_VERSION:
        raise ReleaseError(f"expansion spec schema must be {SPEC_SCHEMA_VERSION!r}")
    if payload.get("wave_id") != wave_id:
        raise ReleaseError("expansion spec wave_id differs from the requested wave")
    if payload.get("core_release_digest_sha256") != core.release_digest_sha256:
        raise ReleaseError("expansion specs are not bound to frozen core-v1")
    if payload.get("status") != PROPOSAL_ONLY_STATUS:
        raise ReleaseError(
            f"expansion spec status must be {PROPOSAL_ONLY_STATUS!r}"
        )
    if payload.get("mutates_core") is not False:
        raise ReleaseError("expansion specs must declare mutates_core=false")
    admission_keys = sorted(
        key
        for key in payload
        if isinstance(key, str)
        and (key.startswith("admission") or key.startswith("admitted"))
    )
    if admission_keys:
        raise ReleaseError(
            "approval-only expansion specs cannot contain admission fields: "
            f"{admission_keys}"
        )
    hits = scan_value_strings("expansion specs", payload)
    if hits:
        raise ReleaseError("; ".join(hits))

    raw_candidates = payload.get("candidates")
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise ReleaseError("expansion specs have no candidates")
    declared_count = payload.get("candidate_count")
    if isinstance(declared_count, bool) or not isinstance(declared_count, int):
        raise ReleaseError("expansion candidate_count must be an integer")
    if declared_count != len(raw_candidates):
        raise ReleaseError("expansion candidate_count differs from candidates")
    declared_level_counts = payload.get("level_counts")
    if not isinstance(declared_level_counts, dict) or not declared_level_counts:
        raise ReleaseError("expansion level_counts must be a nonempty object")
    if any(
        level not in ALLOWED_LEVELS
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 1
        for level, count in declared_level_counts.items()
    ):
        raise ReleaseError("expansion level_counts are malformed")

    core_by_id = anchor_lookup(anchors)
    candidate_ids: set[str] = set()
    representation_ids: set[str] = set()
    validated: list[dict[str, Any]] = []
    for raw in raw_candidates:
        if not isinstance(raw, dict):
            raise ReleaseError("every expansion candidate must be a JSON object")
        candidate_admission_keys = sorted(
            key
            for key in raw
            if isinstance(key, str)
            and (key.startswith("admission") or key.startswith("admitted"))
        )
        if candidate_admission_keys:
            raise ReleaseError(
                "approval-only expansion candidates cannot contain admission "
                f"fields: {candidate_admission_keys}"
            )
        candidate_id = _nonempty_string(
            "<candidate>",
            raw.get("candidate_id"),
            field="candidate_id",
        )
        if SAFE_PUBLIC_ID.fullmatch(candidate_id) is None:
            raise ReleaseError(f"unsafe expansion candidate ID: {candidate_id!r}")
        if candidate_id in candidate_ids:
            raise ReleaseError(f"duplicate expansion candidate ID: {candidate_id}")
        candidate_ids.add(candidate_id)

        representation_id = _nonempty_string(
            candidate_id,
            raw.get("representation_id"),
            field="representation_id",
        )
        if SAFE_PUBLIC_ID.fullmatch(representation_id) is None:
            raise ReleaseError(
                f"{candidate_id}: unsafe representation_id {representation_id!r}"
            )
        if representation_id in representation_ids:
            raise ReleaseError(
                f"duplicate expansion representation ID: {representation_id}"
            )
        representation_ids.add(representation_id)

        for field in (
            "label",
            "family_id",
            "family_label",
            "mechanism",
            "path_grammar",
            "scene_id",
        ):
            _nonempty_string(candidate_id, raw.get(field), field=field)
        level = _nonempty_string(
            candidate_id,
            raw.get("level"),
            field="level",
        ).upper()
        if level not in ALLOWED_LEVELS:
            raise ReleaseError(
                f"{candidate_id}: proposal level must be one of "
                f"{sorted(ALLOWED_LEVELS)}"
            )
        if raw.get("level") != level:
            raise ReleaseError(f"{candidate_id}: level must use canonical uppercase")

        signature = _nonempty_string(
            candidate_id,
            raw.get("port_signature"),
            field="port_signature",
        )
        if PORT_SIGNATURE.fullmatch(signature) is None:
            raise ReleaseError(
                f"{candidate_id}: non-canonical port signature {signature!r}"
            )

        roles = raw.get("roles")
        if not isinstance(roles, list) or not roles:
            raise ReleaseError(f"{candidate_id}: roles must be a nonempty array")
        role_names: set[str] = set()
        for role in roles:
            if not isinstance(role, dict) or set(role) != {"role", "count"}:
                raise ReleaseError(
                    f"{candidate_id}: each role must contain role and count"
                )
            name = _nonempty_string(candidate_id, role["role"], field="role")
            count = role["count"]
            if (
                name in role_names
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count < 1
            ):
                raise ReleaseError(f"{candidate_id}: malformed or duplicate role")
            role_names.add(name)

        witnesses = raw.get("structural_witnesses")
        if not isinstance(witnesses, dict) or not witnesses:
            raise ReleaseError(
                f"{candidate_id}: structural_witnesses must be a nonempty object"
            )
        parameters = raw.get("scene_parameters")
        if not isinstance(parameters, dict):
            raise ReleaseError(f"{candidate_id}: scene_parameters must be an object")
        scene = raw.get("scene")
        if not isinstance(scene, dict) or set(scene) != {"archetype", "variant"}:
            raise ReleaseError(
                f"{candidate_id}: scene must contain exactly archetype and variant"
            )
        _nonempty_string(
            candidate_id,
            scene.get("archetype"),
            field="scene.archetype",
        )
        variant = scene.get("variant")
        if isinstance(variant, bool) or not isinstance(variant, int) or variant < 0:
            raise ReleaseError(
                f"{candidate_id}: scene.variant must be a nonnegative integer"
            )

        deltas = raw.get("representation_deltas")
        if (
            not isinstance(deltas, list)
            or not deltas
            or any(not isinstance(value, str) or not value.strip() for value in deltas)
        ):
            raise ReleaseError(
                f"{candidate_id}: representation_deltas must be nonempty strings"
            )

        prerequisites = raw.get("prerequisite_ids")
        if (
            not isinstance(prerequisites, list)
            or not prerequisites
            or any(
                not isinstance(value, str) or not value.strip()
                for value in prerequisites
            )
            or len(prerequisites) != len(set(prerequisites))
        ):
            raise ReleaseError(
                f"{candidate_id}: prerequisite_ids must be unique nonempty strings"
            )

        nearest_ids = raw.get("nearest_core_ids")
        if (
            not isinstance(nearest_ids, list)
            or not nearest_ids
            or any(not isinstance(value, str) or not value for value in nearest_ids)
        ):
            raise ReleaseError(
                f"{candidate_id}: nearest_core_ids must be a nonempty array"
            )
        resolved = []
        for nearest_id in nearest_ids:
            anchor = core_by_id.get(nearest_id)
            if anchor is None:
                representation_id = core.core_anchor_aliases.get(nearest_id)
                if representation_id is not None:
                    anchor = core_by_id.get(representation_id)
            if anchor is None:
                raise ReleaseError(
                    f"{candidate_id}: dangling nearest core ID {nearest_id!r}"
                )
            if anchor.example_id in resolved:
                raise ReleaseError(
                    f"{candidate_id}: repeated nearest semantic anchor "
                    f"{anchor.example_id!r}"
                )
            resolved.append(anchor.example_id)
        normalized = dict(raw)
        normalized["nearest_core_ids"] = resolved
        validated.append(normalized)

    actual_level_counts = dict(
        sorted(Counter(candidate["level"] for candidate in validated).items())
    )
    if dict(sorted(declared_level_counts.items())) != actual_level_counts:
        raise ReleaseError(
            "expansion level_counts differ from candidates: "
            f"declared={dict(sorted(declared_level_counts.items()))}, "
            f"actual={actual_level_counts}"
        )

    candidate_order = {
        str(candidate["candidate_id"]): index
        for index, candidate in enumerate(validated)
    }
    candidate_levels = {
        str(candidate["candidate_id"]): str(candidate["level"])
        for candidate in validated
    }
    core_prerequisite_levels = dict(core.core_prerequisite_levels)
    for anchor in anchors:
        core_prerequisite_levels.setdefault(anchor.example_id, anchor.level)
        core_prerequisite_levels.setdefault(anchor.representation_id, anchor.level)
    for index, candidate in enumerate(validated):
        candidate_id = str(candidate["candidate_id"])
        level = str(candidate["level"])
        prerequisite_levels: list[str] = []
        for prerequisite_id in candidate["prerequisite_ids"]:
            wave_index = candidate_order.get(prerequisite_id)
            if wave_index is not None:
                if wave_index >= index:
                    raise ReleaseError(
                        f"{candidate_id}: wave prerequisite {prerequisite_id!r} "
                        "must appear earlier in the registry"
                    )
                prerequisite_level = candidate_levels[prerequisite_id]
                if LEVEL_ORDER[prerequisite_level] > LEVEL_ORDER[level]:
                    raise ReleaseError(
                        f"{candidate_id}: wave prerequisite {prerequisite_id!r} "
                        "comes from a later curriculum level"
                    )
            else:
                prerequisite_level = core_prerequisite_levels.get(prerequisite_id)
                if prerequisite_level is None:
                    raise ReleaseError(
                        f"{candidate_id}: dangling prerequisite ID "
                        f"{prerequisite_id!r}"
                    )
                if LEVEL_ORDER[prerequisite_level] > LEVEL_ORDER[level]:
                    raise ReleaseError(
                        f"{candidate_id}: core prerequisite {prerequisite_id!r} "
                        "comes from a later curriculum level"
                    )
            prerequisite_levels.append(prerequisite_level)
        if level == "L4" and "L3" not in prerequisite_levels:
            raise ReleaseError(
                f"{candidate_id}: every L4 proposal must bridge from L3"
            )
    return validated


def _load_scene_module(
    path: Path,
) -> tuple[ModuleType, Callable[[Mapping[str, Any]], Any]]:
    if not path.is_file():
        raise ReleaseError(
            f"proposal scene module is missing: {path.name}; "
            "it must expose build_proposal(candidate)"
        )
    spec = importlib.util.spec_from_file_location(
        "_pixcell_expansion_proposal_scenes",
        path,
    )
    if spec is None or spec.loader is None:
        raise ReleaseError(f"could not load proposal scene module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(spec.name, None)
        raise
    builder = getattr(module, "build_proposal", None)
    if not callable(builder):
        raise ReleaseError(
            "proposal_scenes.py must expose callable build_proposal(candidate)"
        )
    return module, builder


def _component_polygons(
    component: Any,
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    getter = getattr(component, "get_polygons_points", None)
    if not callable(getter):
        raise ReleaseError(
            "build_proposal(candidate) must return a GDSFactory Component"
        )
    raw = getter(by="tuple")
    if not isinstance(raw, Mapping):
        raise ReleaseError("proposal component returned malformed polygon data")
    polygons: list[np.ndarray] = []
    voids: list[np.ndarray] = []
    for layer, values in raw.items():
        for value in values:
            points = np.asarray(value, dtype=float)
            if (
                points.ndim != 2
                or points.shape[0] < 3
                or points.shape[1] != 2
                or not np.isfinite(points).all()
            ):
                raise ReleaseError("proposal component contains a malformed polygon")
            target = voids if tuple(layer) == PROPOSAL_VOID_LAYER else polygons
            target.append(points)
    if not polygons:
        raise ReleaseError("proposal component contains no polygons")
    return polygons, voids


def render_component_max_visible(
    component: Any,
) -> tuple[Image.Image, tuple[float, float], dict[str, Any]]:
    """Render a component with independent-axis maximum visibility.

    Physical aspect is preserved in calibration metadata.  The review raster
    deliberately expands both axes into the same model-visible frame so thin
    rails, gaps, arm banks, and repeated media remain legible.
    """

    polygons, voids = _component_polygons(component)
    stacked = np.concatenate(polygons, axis=0)
    x0, y0 = np.min(stacked, axis=0)
    x1, y1 = np.max(stacked, axis=0)
    width_um = float(x1 - x0)
    height_um = float(y1 - y0)
    if not (
        math.isfinite(width_um)
        and math.isfinite(height_um)
        and 0.05 <= width_um <= 7000
        and 0.05 <= height_um <= 7000
    ):
        raise ReleaseError(
            f"proposal has invalid physical footprint {width_um}x{height_um} um"
        )

    image_width, image_height = MODEL_VIEW_SIZE_PX
    bbox_width = image_width - 2 * RASTER_MARGIN_PX
    bbox_height = image_height - 2 * RASTER_MARGIN_PX
    scale_x = bbox_width / width_um
    scale_y = bbox_height / height_um
    image = Image.new("L", MODEL_VIEW_SIZE_PX, 255)
    draw = ImageDraw.Draw(image)
    for polygon in polygons:
        fitted = [
            (
                RASTER_MARGIN_PX + (float(x) - x0) * scale_x,
                RASTER_MARGIN_PX + bbox_height - (float(y) - y0) * scale_y,
            )
            for x, y in polygon
        ]
        draw.polygon(fitted, fill=0)
    for polygon in voids:
        fitted = [
            (
                RASTER_MARGIN_PX + (float(x) - x0) * scale_x,
                RASTER_MARGIN_PX + bbox_height - (float(y) - y0) * scale_y,
            )
            for x, y in polygon
        ]
        draw.polygon(fitted, fill=255)
    calibration = {
        "bbox": [
            RASTER_MARGIN_PX,
            RASTER_MARGIN_PX,
            RASTER_MARGIN_PX + bbox_width,
            RASTER_MARGIN_PX + bbox_height,
        ],
        "bbox_size_px": [bbox_width, bbox_height],
        "footprint_um": [width_um, height_um],
        "image_size_px": list(image.size),
        "physical_aspect_ratio": width_um / height_um,
        "display_bbox_aspect_ratio": bbox_width / bbox_height,
        "scale_px_per_um": [scale_x, scale_y],
        "view_policy": "maximum_visibility_independent_axes_proposal_v1",
        "void_layer": list(PROPOSAL_VOID_LAYER),
        "white_threshold": 245,
    }
    return image, (width_um, height_um), calibration


def _runtime_ports(component: Any) -> tuple[dict[str, Any], ...]:
    raw_ports = getattr(component, "ports", ())
    records = []
    for port in raw_ports:
        center = [float(value) for value in port.dcenter]
        record = {
            "name": str(port.name),
            "center": center,
            "width": float(port.dwidth),
            "orientation": float(port.orientation) % 360.0,
            "port_type": str(port.port_type),
        }
        if (
            len(center) != 2
            or not all(math.isfinite(value) for value in center)
            or not math.isfinite(record["width"])
            or record["width"] <= 0
            or not math.isfinite(record["orientation"])
        ):
            raise ReleaseError("proposal component contains an invalid runtime port")
        records.append(record)
    names = [record["name"] for record in records]
    if len(names) != len(set(names)):
        raise ReleaseError("proposal component runtime port names are not unique")
    return tuple(records)


def _expected_port_count(signature: str) -> int:
    inputs, outputs = signature.split("x", 1)
    return int(inputs) + int(outputs)


def _save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", compress_level=6, optimize=False)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        try:
            return ImageFont.load_default(size=size)
        except TypeError:
            return ImageFont.load_default()


def _display_text(value: object) -> str:
    """Normalize punctuation for small raster labels."""

    return str(value).translate(
        str.maketrans(
            {
                "–": "-",
                "—": "-",
                "→": "->",
                "×": "x",
                "·": "|",
            }
        )
    )


def _fit(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    fitted = ImageOps.contain(image.convert("RGB"), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    canvas.paste(
        fitted,
        ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2),
    )
    return canvas


def _ellipsize(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    width: int,
) -> str:
    if draw.textbbox((0, 0), text, font=font)[2] <= width:
        return text
    candidate = text
    while candidate and draw.textbbox((0, 0), candidate + "...", font=font)[2] > width:
        candidate = candidate[:-1]
    return candidate.rstrip() + "..."


def render_overview(
    proposals: list[RenderedProposal],
    output: Path,
    *,
    columns: int = 4,
) -> None:
    """Render one compact atlas of every proposal image."""

    tile_width, tile_height = 390, 270
    image_size = (350, 178)
    gap, margin, header = 16, 24, 82
    rows = math.ceil(len(proposals) / columns)
    sheet = Image.new(
        "RGB",
        (
            2 * margin + columns * tile_width + (columns - 1) * gap,
            2 * margin + header + rows * tile_height + max(0, rows - 1) * gap,
        ),
        "#f3f4f6",
    )
    draw = ImageDraw.Draw(sheet)
    draw.text(
        (margin, margin),
        "PixCell expansion grammar review | wave 1",
        fill="#111318",
        font=_font(27),
    )
    draw.text(
        (margin, margin + 39),
        f"{len(proposals)} visual grammar proposals | no dataset rows admitted",
        fill="#5c6470",
        font=_font(14),
    )
    for index, proposal in enumerate(proposals):
        row, column = divmod(index, columns)
        x0 = margin + column * (tile_width + gap)
        y0 = margin + header + row * (tile_height + gap)
        draw.rounded_rectangle(
            (x0, y0, x0 + tile_width, y0 + tile_height),
            radius=8,
            fill="white",
            outline="#c8ccd2",
        )
        fitted = _fit(proposal.image, image_size)
        image_x = x0 + 20
        image_y = y0 + 13
        sheet.paste(fitted, (image_x, image_y))
        draw.rectangle(
            (
                image_x,
                image_y,
                image_x + image_size[0],
                image_y + image_size[1],
            ),
            outline="#e1e3e7",
        )
        candidate = proposal.candidate
        label = _ellipsize(
            draw,
            _display_text(candidate["label"]),
            _font(14),
            tile_width - 40,
        )
        identifier = _ellipsize(
            draw,
            str(candidate["candidate_id"]),
            _font(11),
            tile_width - 40,
        )
        draw.text((x0 + 20, y0 + 204), label, fill="#111318", font=_font(14))
        draw.text((x0 + 20, y0 + 228), identifier, fill="#5c6470", font=_font(11))
        draw.text(
            (x0 + 20, y0 + 248),
            f"{candidate['level']} | {_display_text(candidate['family_label'])}",
            fill="#5c6470",
            font=_font(10),
        )
    _save_png(sheet, output)


def _wrapped_lines(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.ImageFont,
    width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=font)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def render_review_pages(
    proposals: list[RenderedProposal],
    output_dir: Path,
) -> list[Path]:
    """Render detailed candidate-versus-nearest pages, four proposals per page."""

    output_dir.mkdir(parents=True, exist_ok=True)
    page_paths = []
    card_width, card_height = 820, 520
    margin, gap, header = 24, 18, 72
    for page_index, start in enumerate(range(0, len(proposals), 4), start=1):
        page = Image.new(
            "RGB",
            (
                2 * margin + 2 * card_width + gap,
                2 * margin + header + 2 * card_height + gap,
            ),
            "#f3f4f6",
        )
        draw = ImageDraw.Draw(page)
        draw.text(
            (margin, margin),
            f"Expansion grammar review | page {page_index}",
            fill="#111318",
            font=_font(24),
        )
        for local_index, proposal in enumerate(proposals[start : start + 4]):
            row, column = divmod(local_index, 2)
            x0 = margin + column * (card_width + gap)
            y0 = margin + header + row * (card_height + gap)
            draw.rounded_rectangle(
                (x0, y0, x0 + card_width, y0 + card_height),
                radius=8,
                fill="white",
                outline="#c8ccd2",
            )
            nearest_anchor = proposal.declared_nearest[0]
            left = _fit(proposal.image, (375, 190))
            right = _fit(
                image_from_bytes(nearest_anchor["image_bytes"]),
                (375, 190),
            )
            page.paste(left, (x0 + 18, y0 + 48))
            page.paste(right, (x0 + 427, y0 + 48))
            draw.text(
                (x0 + 18, y0 + 17),
                "PROPOSAL",
                fill="#2f67d8",
                font=_font(13),
            )
            draw.text(
                (x0 + 427, y0 + 17),
                "DECLARED NEAREST CORE",
                fill="#5c6470",
                font=_font(13),
            )
            candidate = proposal.candidate
            draw.text(
                (x0 + 18, y0 + 252),
                _ellipsize(
                    draw,
                    _display_text(candidate["label"]),
                    _font(15),
                    card_width - 36,
                ),
                fill="#111318",
                font=_font(15),
            )
            draw.text(
                (x0 + 18, y0 + 278),
                f"{candidate['level']} | "
                f"{_display_text(candidate['family_label'])} | "
                f"ports {candidate['port_signature']}",
                fill="#5c6470",
                font=_font(11),
            )
            draw.text(
                (x0 + 18, y0 + 303),
                f"Nearest: {nearest_anchor['example_id']} "
                f"(aligned IoU {nearest_anchor['aligned_dilated_iou']:.3f})",
                fill="#5c6470",
                font=_font(11),
            )
            text_y = y0 + 330
            body_font = _font(11)
            for heading, text in (
                (
                    "New",
                    _display_text("; ".join(candidate["representation_deltas"])),
                ),
                (
                    "Witnesses",
                    json.dumps(
                        candidate["structural_witnesses"],
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            ):
                lines = _wrapped_lines(
                    draw,
                    f"{heading}: {text}",
                    font=body_font,
                    width=card_width - 36,
                )
                for line in lines[:4]:
                    draw.text(
                        (x0 + 18, text_y),
                        line,
                        fill="#30343a",
                        font=body_font,
                    )
                    text_y += 19
        page_path = output_dir / f"page-{page_index:02d}.png"
        _save_png(page, page_path)
        page_paths.append(page_path)
    return page_paths


def _markdown_cell(value: object) -> str:
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def write_grammar_index(
    proposals: list[RenderedProposal],
    output: Path,
) -> None:
    """Write the compact, human-readable registry behind the visual dossier."""

    counts = Counter(str(proposal.candidate["level"]) for proposal in proposals)
    lines = [
        "# PixCell expansion grammar proposals · wave 1",
        "",
        (
            "Approval-only registry: these are proposed visual grammars, not "
            "admitted dataset rows. `core-v1` remains unchanged."
        ),
        "",
        (
            f"Total: **{len(proposals)}** · "
            + " · ".join(f"{level}: **{counts[level]}**" for level in sorted(counts))
        ),
        "",
    ]
    for level in sorted(counts):
        lines.extend(
            [
                f"## {level}",
                "",
                "| ID | Grammar | Family | Ports | Builds from | Representation delta |",
                "|---|---|---|---:|---|---|",
            ]
        )
        for proposal in proposals:
            candidate = proposal.candidate
            if candidate["level"] != level:
                continue
            prerequisites = "<br>".join(
                f"`{_markdown_cell(identifier)}`"
                for identifier in candidate["prerequisite_ids"]
            )
            deltas = "<br>".join(
                _markdown_cell(delta)
                for delta in candidate["representation_deltas"]
            )
            lines.append(
                "| "
                + " | ".join(
                    (
                        f"`{_markdown_cell(candidate['candidate_id'])}`",
                        _markdown_cell(candidate["label"]),
                        _markdown_cell(candidate["family_label"]),
                        f"`{_markdown_cell(candidate['port_signature'])}`",
                        prerequisites,
                        deltas,
                    )
                )
                + " |"
            )
        lines.append("")
    output.write_text("\n".join(lines), encoding="utf-8")


def _declared_nearest_records(
    candidate: Mapping[str, Any],
    image: Image.Image,
    lookup: Mapping[str, CoreSemanticAnchor],
) -> tuple[dict[str, Any], ...]:
    records = []
    for example_id in candidate["nearest_core_ids"]:
        anchor = lookup[example_id]
        records.append(
            {
                "example_id": anchor.example_id,
                "representation_id": anchor.representation_id,
                "level": anchor.level,
                "family": anchor.family,
                "label": anchor.label,
                "image_bytes": anchor.image_bytes,
                **aligned_mask_similarity(image, anchor.mask),
            }
        )
    return tuple(records)


def _manifest_nearest(record: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if key != "image_bytes"}


def _promote_generated(stage: Path, output: Path) -> None:
    """Atomically replace only the exact generated proposal directory."""

    output.parent.mkdir(parents=True, exist_ok=True)
    backup = output.parent / f".{output.name}.backup"
    if backup.exists():
        raise ReleaseError(f"stale proposal backup exists: {backup}")
    moved_old = False
    moved_new = False
    try:
        if output.exists():
            if not output.is_dir():
                raise ReleaseError(f"proposal output is not a directory: {output}")
            os.replace(output, backup)
            moved_old = True
        os.replace(stage, output)
        moved_new = True
    except Exception:
        if moved_new and output.is_dir():
            shutil.rmtree(output)
        if moved_old:
            os.replace(backup, output)
        raise
    else:
        if moved_old:
            shutil.rmtree(backup)


def build_expansion_proposals(
    dataset_root: Path,
    *,
    wave_id: str = DEFAULT_WAVE,
    output: Path | None = None,
) -> dict[str, Any]:
    """Compile one visual proposal wave without admitting dataset rows."""

    root = dataset_root.expanduser().resolve()
    generated = safe_generated_output(root, wave_id, output)
    wave_root = generated.parent
    specs_path = wave_root / "specs.json"
    scenes_path = Path(__file__).resolve().with_name("proposal_scenes.py")
    if not specs_path.is_file():
        raise ReleaseError(f"proposal specs are missing: {specs_path}")

    before = snapshot_frozen_core(root)
    anchors = load_core_semantic_anchors(root)
    if len(anchors) != before.representation_count:
        raise ReleaseError("semantic nearest index differs from frozen core count")
    candidates = validate_proposal_specs(
        read_json(specs_path),
        wave_id=wave_id,
        core=before,
        anchors=anchors,
    )
    _module, build_proposal = _load_scene_module(scenes_path)
    core_lookup = anchor_lookup(anchors)
    core_d4: dict[str, list[str]] = {}
    for anchor in anchors:
        core_d4.setdefault(anchor.d4_sha256, []).append(anchor.example_id)

    stage = Path(
        tempfile.mkdtemp(
            prefix=f".{GENERATED_NAME}.stage.",
            dir=wave_root,
        )
    )
    rendered: list[RenderedProposal] = []
    candidate_d4: dict[str, str] = {}
    try:
        for candidate in candidates:
            candidate_id = str(candidate["candidate_id"])
            try:
                component = build_proposal(candidate)
            except Exception as exc:
                raise ReleaseError(
                    f"{candidate_id}: proposal scene construction failed: {exc}"
                ) from exc
            image, footprint, calibration = render_component_max_visible(component)
            d4_sha = normalized_d4_sha256(image)
            if d4_sha in core_d4:
                raise ReleaseError(
                    f"{candidate_id}: D4-equivalent to core anchors {core_d4[d4_sha]}"
                )
            if d4_sha in candidate_d4:
                raise ReleaseError(
                    f"{candidate_id}: D4-equivalent to proposal {candidate_d4[d4_sha]}"
                )
            candidate_d4[d4_sha] = candidate_id
            image_path = stage / "images" / f"{candidate_id}.png"
            _save_png(image, image_path)
            observed_ports = _runtime_ports(component)
            expected_ports = _expected_port_count(str(candidate["port_signature"]))
            if len(observed_ports) != expected_ports:
                raise ReleaseError(
                    f"{candidate_id}: runtime port count {len(observed_ports)} "
                    f"!= declared {expected_ports}"
                )
            nearest = tuple(
                nearest_semantic_anchors(
                    image,
                    anchors,
                    top_k=NEAREST_TOP_K,
                )
            )
            declared = _declared_nearest_records(candidate, image, core_lookup)
            rendered.append(
                RenderedProposal(
                    candidate=candidate,
                    image_path=image_path,
                    image=image,
                    footprint_um=footprint,
                    calibration=calibration,
                    observed_ports=observed_ports,
                    nearest=nearest,
                    declared_nearest=declared,
                )
            )

        render_overview(rendered, stage / "overview.png")
        page_paths = render_review_pages(rendered, stage / "pages")
        grammar_index_path = stage / "GRAMMARS.md"
        write_grammar_index(rendered, grammar_index_path)
        manifest_candidates = []
        for proposal in rendered:
            relative_image = proposal.image_path.relative_to(stage).as_posix()
            manifest_candidates.append(
                {
                    **proposal.candidate,
                    "image": {
                        "path": relative_image,
                        "sha256": sha256_file(proposal.image_path),
                        "size_px": list(proposal.image.size),
                    },
                    "footprint_um": list(proposal.footprint_um),
                    "calibration": proposal.calibration,
                    "observed_ports": list(proposal.observed_ports),
                    "normalized_d4_sha256": normalized_d4_sha256(proposal.image),
                    "declared_nearest_core": [
                        _manifest_nearest(record)
                        for record in proposal.declared_nearest
                    ],
                    "computed_visual_nearest": list(proposal.nearest),
                }
            )
        manifest = {
            "schema_version": OUTPUT_SCHEMA_VERSION,
            "wave_id": wave_id,
            "scope": "visual_approval_only",
            "admission": {
                "status": "not_admitted",
                "dataset_rows_created": 0,
                "requires_human_approval": True,
            },
            "core_name": before.core_name,
            "core_release_digest_sha256": before.release_digest_sha256,
            "core_semantic_anchor_count": len(anchors),
            "specs_sha256": sha256_file(specs_path),
            "scene_module_sha256": sha256_file(scenes_path),
            "candidate_count": len(manifest_candidates),
            "level_counts": dict(
                sorted(Counter(row["level"] for row in manifest_candidates).items())
            ),
            "candidate_digest_sha256": canonical_sha256(manifest_candidates),
            "overview": {
                "path": "overview.png",
                "sha256": sha256_file(stage / "overview.png"),
            },
            "grammar_index": {
                "path": grammar_index_path.relative_to(stage).as_posix(),
                "sha256": sha256_file(grammar_index_path),
            },
            "review_pages": [
                {
                    "path": path.relative_to(stage).as_posix(),
                    "sha256": sha256_file(path),
                }
                for path in page_paths
            ],
            "candidates": manifest_candidates,
        }
        write_json(stage / "manifest.json", manifest)
        assert_frozen_core_unchanged(before, root)
        _promote_generated(stage, generated)
        assert_frozen_core_unchanged(before, root)
        return manifest
    except Exception:
        if stage.is_dir():
            shutil.rmtree(stage)
        raise


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    parser.add_argument("--wave", default=DEFAULT_WAVE)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Safety-checked output override; must equal "
            "factory/expansion/<wave>/generated."
        ),
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    manifest = build_expansion_proposals(
        args.root,
        wave_id=args.wave,
        output=args.output,
    )
    print(
        json.dumps(
            {
                "wave_id": manifest["wave_id"],
                "scope": manifest["scope"],
                "candidate_count": manifest["candidate_count"],
                "candidate_digest_sha256": manifest["candidate_digest_sha256"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
