#!/usr/bin/env python3
"""Create the deterministic, minimal PixCell core-v1 source bundle.

This maintainer-only command is the one-time bridge from the original audited
source banks to the standalone public factory.  The produced bundle contains
only files consumed by ``build_release.py``:

* accepted-only manifests and audit reports;
* executable per-card generator programs;
* exact model and target images;
* explicit factor/parameter specifications; and
* calibration, topology, and admission evidence used by the release gate.

Historical proposals, rejected candidates, GDS intermediates, caches, and
private benchmark material are intentionally excluded.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

from _shared import LEVELS, ReleaseError, read_json, sha256_file, write_json


CORE_NAME = "core-v1"
EXPECTED_RELEASE_DIGEST = (
    "e1c509dca337ce485efcb2b35101a052e06b12331b63a2f21a36c93b3682ea89"
)
SOURCE_COMMIT = "2ab0e551fc75c2ad7087ef88ecad2b5de279704b"
BANK_NAMES = {
    "l0": "pool_v8_l0_bank",
    "l1": "pool_v8_l1_bank",
    "l2": "pool_v8_l2_bank",
    "l3": "pool_v8_l3_full120",
    "l4": "pool_v8_l4_core108",
}
EXPECTED_LEVELS = {
    "l0": {
        "rows": 177,
        "source_digest": (
            "495b2c8f4864199213a888a5f8323db08525c76213552f919e901e386784ea76"
        ),
    },
    "l1": {
        "rows": 215,
        "source_digest": (
            "30765ca9366965807b65e321a7492afe6d2f8e7ae0c9fbc3a629e4641a771bc1"
        ),
    },
    "l2": {
        "rows": 118,
        "source_digest": (
            "05737221cfc0aeb3ef08efc64504d3db031530f5cef1496a48b0239ad23d6b46"
        ),
    },
    "l3": {
        "rows": 120,
        "source_digest": (
            "aa696edde9a6bc5ee0c5275d9a7f05eed2a1bc56c600791ebb5c51a3d4953fc6"
        ),
    },
    "l4": {
        "rows": 108,
        "source_digest": (
            "8db07b0730b3864a3f864abf08eb5fcf94c144ffcea5d3224590560d429c836f"
        ),
    },
}
OPTIONAL_SIDECARS = (
    "parameters.json",
    "topology_contract.json",
    "factor_assignment.json",
    "candidate_evidence.json",
)
ARCHIVE_PAYLOAD = Path | bytes
PRIVATE_MANIFEST_KEYS = frozenset(
    {
        "proposal_workspace",
        "source_root",
        "repository_root",
    }
)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _payload_bytes(value: ARCHIVE_PAYLOAD) -> bytes:
    return value if isinstance(value, bytes) else value.read_bytes()


def _payload_size(value: ARCHIVE_PAYLOAD) -> int:
    return len(value) if isinstance(value, bytes) else value.stat().st_size


def _sanitized_manifest_bytes(value: Any) -> bytes:
    """Remove unused private workspace pointers from a public source capsule."""

    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {
                str(key): clean(child)
                for key, child in item.items()
                if str(key) not in PRIVATE_MANIFEST_KEYS
            }
        if isinstance(item, list):
            return [clean(child) for child in item]
        return item

    return (
        json.dumps(
            clean(value),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _inside(root: Path, relative: str, *, label: str) -> Path:
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ReleaseError(f"{label} escapes source bank: {relative}") from exc
    if not candidate.is_file():
        raise ReleaseError(f"{label} does not exist: {relative}")
    return candidate


def _record_files(
    bank: Path,
    record: dict[str, Any],
) -> dict[str, Path]:
    card_relative = record.get("path")
    if not isinstance(card_relative, str):
        raise ReleaseError(f"{record.get('candidate_id')}: missing card path")
    card_dir = (bank / card_relative).resolve()
    try:
        card_dir.relative_to(bank.resolve())
    except ValueError as exc:
        raise ReleaseError(f"card path escapes bank: {card_relative}") from exc
    if not card_dir.is_dir():
        raise ReleaseError(f"missing card directory: {card_relative}")

    files = {
        "program": _inside(
            bank,
            str(record.get("program_path") or f"{card_relative}/ground_truth.py"),
            label="program",
        ),
        "model_view": _inside(
            bank,
            str(record.get("model_view_path") or f"{card_relative}/model_view.png"),
            label="model view",
        ),
        "target": _inside(
            bank,
            f"{card_relative}/device_bw.png",
            label="target",
        ),
        "calibration": _inside(
            bank,
            f"{card_relative}/calibration.json",
            label="calibration",
        ),
    }
    for filename in OPTIONAL_SIDECARS:
        path = card_dir / filename
        if path.is_file():
            files[filename.removesuffix(".json")] = path
    if not isinstance(record.get("footprint_um"), list):
        path = card_dir / "footprint.json"
        if path.is_file():
            files["footprint"] = path
    return files


def _public_role(record: dict[str, Any]) -> str:
    role = str(record.get("variation_role") or record.get("public_role") or "semantic")
    return "semantic" if role == "semantic_base" else role


def _first(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if value:
            return str(value)
    return ""


def _family(level: str, record: dict[str, Any]) -> str:
    return (
        _first(record, "family", "composition_family")
        or {
            "l0": "Primitive catalog",
            "l1": "Primitive operations",
            "l2": "Composed operations",
            "l3": "Hierarchical representations",
            "l4": "Photonic components",
        }[level]
    )


def collect_source(
    source_root: Path,
) -> tuple[dict[str, ARCHIVE_PAYLOAD], dict[str, Any], dict[str, Any]]:
    """Return archive payload paths, source inventory metadata, and grammar map."""

    tasks_root = source_root / "rl" / "tasks"
    if not tasks_root.is_dir():
        raise ReleaseError(f"source root has no rl/tasks directory: {source_root}")

    payload: dict[str, ARCHIVE_PAYLOAD] = {}
    grammar_rows: list[dict[str, Any]] = []
    level_summaries: dict[str, Any] = {}
    curriculum_order = 0

    for level in LEVELS:
        bank_name = BANK_NAMES[level]
        bank = tasks_root / bank_name
        manifest_path = bank / "manifest.json"
        audit_path = bank / "audit_report.json"
        if not manifest_path.is_file() or not audit_path.is_file():
            raise ReleaseError(f"{level}: incomplete source bank at {bank}")
        manifest = read_json(manifest_path)
        audit = read_json(audit_path)
        records = manifest.get("records")
        if not isinstance(records, list):
            raise ReleaseError(f"{level}: manifest has no records")
        expected = EXPECTED_LEVELS[level]
        if len(records) != expected["rows"]:
            raise ReleaseError(
                f"{level}: row count {len(records)} != {expected['rows']}"
            )
        source_digest = manifest.get("dataset_digest_sha256")
        if source_digest != expected["source_digest"]:
            raise ReleaseError(f"{level}: source digest drift")
        if audit.get("dataset_digest_sha256") != source_digest:
            raise ReleaseError(f"{level}: manifest/audit digest mismatch")
        if "accepted_only" not in str(manifest.get("status", "")):
            raise ReleaseError(f"{level}: source bank is not accepted-only")

        prefix = Path("rl") / "tasks" / bank_name
        payload[(prefix / "manifest.json").as_posix()] = _sanitized_manifest_bytes(
            manifest
        )
        payload[(prefix / "audit_report.json").as_posix()] = audit_path
        role_counts: dict[str, int] = {}

        for record in records:
            files = _record_files(bank, record)
            for path in files.values():
                relative = path.relative_to(bank)
                payload[(prefix / relative).as_posix()] = path

            card_id = _first(record, "card_id", "candidate_id", "task_id")
            grammar_id = str(record.get("grammar_id") or card_id)
            role = _public_role(record)
            role_counts[role] = role_counts.get(role, 0) + 1
            factor_path = files.get("factor_assignment")
            parameter_path = files.get("parameters")
            grammar_rows.append(
                {
                    "id": card_id,
                    "level": level.upper(),
                    "curriculum_order": curriculum_order,
                    "concept_id": _first(
                        record,
                        "concept_id",
                        "operation_id",
                        "composition_id",
                        "identity_id",
                        "motif_id",
                        "card_id",
                        "candidate_id",
                    ),
                    "grammar_id": grammar_id,
                    "leakage_group_id": str(
                        record.get("leakage_group_id") or grammar_id
                    ),
                    "variation_role": role,
                    "family": _family(level, record),
                    "label": _first(
                        record,
                        "label",
                        "identity_label",
                        "composition_label",
                        "operation_label",
                        "concept_label",
                        "mode_label",
                    ),
                    "generator_program": (
                        prefix / files["program"].relative_to(bank)
                    ).as_posix(),
                    "factor_assignment": (
                        read_json(factor_path) if factor_path is not None else {}
                    ),
                    "parameters": (
                        read_json(parameter_path) if parameter_path is not None else {}
                    ),
                    "deterministic_seed": None,
                }
            )
            curriculum_order += 1

        level_summaries[level] = {
            "bank_name": bank_name,
            "row_count": len(records),
            "source_dataset_digest_sha256": source_digest,
            "generator_version": str(manifest.get("generator_version") or ""),
            "role_counts": dict(sorted(role_counts.items())),
        }

    inventory_entries = []
    for relative, source in sorted(payload.items()):
        source_bytes = _payload_bytes(source)
        inventory_entries.append(
            {
                "path": relative,
                "bytes": len(source_bytes),
                "sha256": _sha256_bytes(source_bytes),
            }
        )
    source_manifest = {
        "schema_version": "pixcell-core-source-v1",
        "core_name": CORE_NAME,
        "source_commit": SOURCE_COMMIT,
        "randomness": {
            "mode": "none",
            "seed": None,
            "explanation": (
                "core-v1 is an explicit deterministic enumeration; every factor "
                "assignment and executable generator program is frozen."
            ),
        },
        "bank_names": BANK_NAMES,
        "levels": level_summaries,
        "file_count": len(inventory_entries),
        "payload_bytes": sum(entry["bytes"] for entry in inventory_entries),
        "files": inventory_entries,
    }
    grammar_catalog = {
        "schema_version": "pixcell-grammar-catalog-v1",
        "core_name": CORE_NAME,
        "row_count": len(grammar_rows),
        "representation_count": len({row["grammar_id"] for row in grammar_rows}),
        "randomness": "none",
        "rows": grammar_rows,
    }
    return payload, source_manifest, grammar_catalog


def _tar_info(name: str, size: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.size = size
    info.mode = 0o644
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    info.pax_headers = {}
    return info


def write_deterministic_archive(
    output_path: Path,
    payload: dict[str, ARCHIVE_PAYLOAD],
    source_manifest: dict[str, Any],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    internal_manifest = (
        json.dumps(
            source_manifest,
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with output_path.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            compresslevel=9,
            mtime=0,
        ) as compressed:
            with tarfile.open(
                mode="w",
                fileobj=compressed,
                format=tarfile.PAX_FORMAT,
            ) as archive:
                for relative, source in sorted(payload.items()):
                    info = _tar_info(relative, _payload_size(source))
                    if isinstance(source, bytes):
                        archive.addfile(info, io.BytesIO(source))
                    else:
                        with source.open("rb") as handle:
                            archive.addfile(info, handle)
                info = _tar_info("source_manifest.json", len(internal_manifest))
                archive.addfile(info, io.BytesIO(internal_manifest))


def pack_core_v1(
    source_root: Path,
    dataset_root: Path,
) -> dict[str, Any]:
    dataset_root = dataset_root.expanduser().resolve()
    source_root = source_root.expanduser().resolve()
    catalog = read_json(dataset_root / "metadata" / "catalog.json")
    if catalog.get("release_digest_sha256") != EXPECTED_RELEASE_DIGEST:
        raise ReleaseError("public release digest is not the frozen core-v1 digest")
    if catalog.get("total_rows") != 738:
        raise ReleaseError("public release row count is not 738")

    payload, source_manifest, grammar_catalog = collect_source(source_root)
    core_root = dataset_root / "factory" / CORE_NAME
    archive_path = core_root / "source.tar.gz"
    write_deterministic_archive(archive_path, payload, source_manifest)
    write_json(core_root / "source_manifest.json", source_manifest)
    write_json(core_root / "grammar_catalog.json", grammar_catalog)

    archive_sha = sha256_file(archive_path)
    admission_policy_path = dataset_root / "factory" / "admission_policy.json"
    if not admission_policy_path.is_file():
        raise ReleaseError("factory/admission_policy.json is missing")
    reproducibility_report_path = (
        dataset_root / "factory" / CORE_NAME / "reproducibility_report.json"
    )
    if not reproducibility_report_path.is_file():
        raise ReleaseError("core-v1 reproducibility report is missing")
    reference_paths = [
        *(f"data/{level}/train-00000-of-00001.parquet" for level in LEVELS),
        "galleries/all.png",
        *(f"galleries/{level}.png" for level in LEVELS),
        "metadata/catalog.json",
        "metadata/audit_report.json",
        *(f"metadata/source_reports/{level}.json" for level in LEVELS),
    ]
    reference_artifacts = {
        relative: sha256_file(dataset_root / relative) for relative in reference_paths
    }
    freeze = {
        "schema_version": "pixcell-core-freeze-v1",
        "core_name": CORE_NAME,
        "release_digest_sha256": EXPECTED_RELEASE_DIGEST,
        "row_count": 738,
        "representation_count": 547,
        "accepted_only": True,
        "source_commit": SOURCE_COMMIT,
        "levels": {
            level: {
                "row_count": EXPECTED_LEVELS[level]["rows"],
                "source_dataset_digest_sha256": EXPECTED_LEVELS[level]["source_digest"],
            }
            for level in LEVELS
        },
        "source_bundle": {
            "path": "factory/core-v1/source.tar.gz",
            "sha256": archive_sha,
            "bytes": archive_path.stat().st_size,
            "inventory_path": "factory/core-v1/source_manifest.json",
            "file_count": source_manifest["file_count"],
            "uncompressed_payload_bytes": source_manifest["payload_bytes"],
        },
        "grammar_catalog": {
            "path": "factory/core-v1/grammar_catalog.json",
            "sha256": sha256_file(core_root / "grammar_catalog.json"),
            "row_count": grammar_catalog["row_count"],
            "representation_count": grammar_catalog["representation_count"],
        },
        "admission_policy": {
            "path": "factory/admission_policy.json",
            "sha256": sha256_file(admission_policy_path),
        },
        "reproducibility_report": {
            "path": "factory/core-v1/reproducibility_report.json",
            "sha256": sha256_file(reproducibility_report_path),
        },
        "determinism": {
            "randomness": "none",
            "seed": None,
            "archive_metadata_normalized": True,
            "expected_logical_digest_is_mandatory": True,
            "reference_artifacts_are_platform_specific": True,
        },
        "reference_artifacts": reference_artifacts,
        "build_command": "python scripts/build_all.py",
        "validation_command": ("python scripts/validate_release.py --execute-programs"),
    }
    write_json(core_root / "freeze.json", freeze)
    return freeze


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Working tree containing the five audited source banks.",
    )
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    freeze = pack_core_v1(args.source, args.dataset_root)
    bundle = freeze["source_bundle"]
    print(
        f"packed {freeze['row_count']} rows into {bundle['file_count']} source "
        f"files; archive sha256 {bundle['sha256']}"
    )


if __name__ == "__main__":
    main()
