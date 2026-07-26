#!/usr/bin/env python3
"""Rebuild the frozen PixCell core-v1 release from its standalone source bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from typing import Any

from _shared import ReleaseError, read_json, scan_text, sha256_file
from build_release import build_release
from validate_release import validate_release


CORE_NAME = "core-v1"


def _safe_members(archive: tarfile.TarFile) -> list[tarfile.TarInfo]:
    members = archive.getmembers()
    names: set[str] = set()
    for member in members:
        path = Path(member.name)
        if (
            not member.isfile()
            or path.is_absolute()
            or ".." in path.parts
            or member.name in names
        ):
            raise ReleaseError(f"unsafe source archive member: {member.name}")
        names.add(member.name)
    return members


def _extract_and_verify(
    archive_path: Path,
    inventory_path: Path,
    destination: Path,
) -> None:
    expected = read_json(inventory_path)
    entries = expected.get("files")
    if not isinstance(entries, list):
        raise ReleaseError("core source inventory has no files")
    expected_files = {
        str(entry["path"]): {
            "bytes": int(entry["bytes"]),
            "sha256": str(entry["sha256"]),
        }
        for entry in entries
    }

    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = _safe_members(archive)
        archive_names = {member.name for member in members}
        if archive_names != {*expected_files, "source_manifest.json"}:
            missing = sorted(set(expected_files) - archive_names)
            extra = sorted(archive_names - {*expected_files, "source_manifest.json"})
            raise ReleaseError(
                f"source archive inventory drift; missing={missing[:3]}, "
                f"extra={extra[:3]}"
            )
        internal_member = archive.getmember("source_manifest.json")
        extracted = archive.extractfile(internal_member)
        if extracted is None:
            raise ReleaseError("source archive internal manifest is unreadable")
        internal = json.loads(extracted.read().decode("utf-8"))
        if internal != expected:
            raise ReleaseError("source archive internal/external manifests differ")
        for member in members:
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ReleaseError(f"could not read archive member: {member.name}")
            with target.open("wb") as handle:
                if Path(member.name).suffix in {".json", ".py"}:
                    payload = source.read()
                    try:
                        text = payload.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        raise ReleaseError(
                            f"source text is not UTF-8: {member.name}"
                        ) from exc
                    hits = scan_text(f"source/{member.name}", text)
                    if hits:
                        raise ReleaseError("; ".join(hits))
                    handle.write(payload)
                else:
                    shutil.copyfileobj(source, handle)

    for relative, evidence in expected_files.items():
        path = destination / relative
        if path.stat().st_size != evidence["bytes"]:
            raise ReleaseError(f"source size drift: {relative}")
        if sha256_file(path) != evidence["sha256"]:
            raise ReleaseError(f"source digest drift: {relative}")


def build_all(dataset_root: Path) -> dict[str, Any]:
    dataset_root = dataset_root.expanduser().resolve()
    core_root = dataset_root / "factory" / CORE_NAME
    freeze = read_json(core_root / "freeze.json")
    if freeze.get("core_name") != CORE_NAME:
        raise ReleaseError("core freeze name drift")
    bundle = freeze.get("source_bundle")
    if not isinstance(bundle, dict):
        raise ReleaseError("core freeze has no source bundle")
    archive_path = dataset_root / str(bundle["path"])
    inventory_path = dataset_root / str(bundle["inventory_path"])
    if sha256_file(archive_path) != bundle.get("sha256"):
        raise ReleaseError("frozen source archive digest drift")
    grammar = freeze.get("grammar_catalog")
    if not isinstance(grammar, dict):
        raise ReleaseError("core freeze has no grammar catalog")
    grammar_path = dataset_root / str(grammar.get("path", ""))
    if not grammar_path.is_file():
        raise ReleaseError("core grammar catalog is missing")
    if sha256_file(grammar_path) != grammar.get("sha256"):
        raise ReleaseError("core grammar catalog digest drift")
    grammar_catalog = read_json(grammar_path)
    if grammar_catalog.get("row_count") != freeze.get(
        "row_count"
    ) or grammar_catalog.get("representation_count") != freeze.get(
        "representation_count"
    ):
        raise ReleaseError("core grammar catalog count drift")
    policy = freeze.get("admission_policy")
    if not isinstance(policy, dict):
        raise ReleaseError("core freeze has no admission policy")
    policy_path = dataset_root / str(policy.get("path", ""))
    if not policy_path.is_file() or sha256_file(policy_path) != policy.get("sha256"):
        raise ReleaseError("core admission policy digest drift")
    reproducibility = freeze.get("reproducibility_report")
    if not isinstance(reproducibility, dict):
        raise ReleaseError("core freeze has no reproducibility report")
    reproducibility_path = dataset_root / str(reproducibility.get("path", ""))
    if not reproducibility_path.is_file() or sha256_file(
        reproducibility_path
    ) != reproducibility.get("sha256"):
        raise ReleaseError("core reproducibility report digest drift")

    with tempfile.TemporaryDirectory(prefix="pixcell-core-v1-source.") as temporary:
        source_root = Path(temporary)
        _extract_and_verify(archive_path, inventory_path, source_root)
        catalog = build_release(
            source_root,
            dataset_root,
            expected_release_digest=str(freeze["release_digest_sha256"]),
            expected_row_count=int(freeze["row_count"]),
        )

    expected_digest = freeze.get("release_digest_sha256")
    if catalog.get("release_digest_sha256") != expected_digest:
        raise ReleaseError(
            "rebuilt release digest differs from frozen core-v1: "
            f"{catalog.get('release_digest_sha256')} != {expected_digest}"
        )
    if catalog.get("total_rows") != freeze.get("row_count"):
        raise ReleaseError("rebuilt row count differs from frozen core-v1")
    report = validate_release(dataset_root)
    if report["release_digest_sha256"] != expected_digest:
        raise ReleaseError("post-build validation digest differs from core-v1")
    artifact_mismatches: list[str] = []
    reference_artifacts = freeze.get("reference_artifacts", {})
    if isinstance(reference_artifacts, dict):
        for relative, expected_sha in sorted(reference_artifacts.items()):
            path = dataset_root / relative
            if not path.is_file() or sha256_file(path) != expected_sha:
                artifact_mismatches.append(relative)
    return {
        "core_name": CORE_NAME,
        "release_digest_sha256": expected_digest,
        "total_rows": report["total_rows"],
        "level_counts": report["level_counts"],
        "source_archive_sha256": bundle["sha256"],
        "static_validation": "passed",
        "reference_artifact_match": not artifact_mismatches,
        "reference_artifact_mismatches": artifact_mismatches,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Dataset package root (default: parent of scripts/).",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    report = build_all(args.root)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
