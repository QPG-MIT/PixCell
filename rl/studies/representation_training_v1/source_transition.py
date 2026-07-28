"""Deterministic Git facts for an explicitly reviewed source transition.

Evaluation evidence is produced and validated at one clean commit.  A later
consumer commit may use that evidence only when the producer is an exact
ancestor and an immutable approval records the complete transition.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .store import canonical_sha256


SOURCE_TRANSITION_SCHEMA_VERSION = "pixcell-training-source-transition-v2"
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_GIT_MODE = re.compile(r"^[0-7]{6}$")
_GIT_STATUS = re.compile(r"^[A-Z][0-9]*$")


class SourceTransitionError(RuntimeError):
    """A producer-to-consumer source transition is invalid or unverifiable."""


def _sha(value: Any, field: str) -> str:
    result = str(value)
    if not _GIT_SHA.fullmatch(result):
        raise SourceTransitionError(f"{field} must be a full lowercase Git SHA")
    return result


def _git(repo_root: Path, *args: str) -> bytes:
    # These are local object-database queries.  Inheriting arbitrary GIT_* or
    # user configuration makes even a commit-to-commit diff dependent on the
    # invoking shell (for example GIT_DIFF_OPTS changes patch serialization).
    # Keep only executable lookup and force Git's replace/config surfaces off.
    environment = {
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_OPTIONAL_LOCKS": "0",
        "LANG": "C",
        "LC_ALL": "C",
        "PATH": os.environ.get("PATH", os.defpath),
    }
    try:
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.quotepath=false",
                "-c",
                "diff.external=",
                "-c",
                "diff.noprefix=false",
                "-c",
                "core.attributesFile=/dev/null",
                *args,
            ],
            cwd=repo_root,
            check=True,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError):
            detail = exc.stderr.decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise SourceTransitionError(f"git {' '.join(args)} failed{suffix}") from exc
    return result.stdout


def _repository_root(repo_root: Path) -> Path:
    root = repo_root.expanduser().resolve(strict=True)
    observed = Path(_git(root, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve(
        strict=True
    )
    if observed != root:
        raise SourceTransitionError(
            "source transition repository root is not the Git worktree root"
        )
    grafts = Path(_git(root, "rev-parse", "--git-path", "info/grafts").decode("utf-8").strip())
    if not grafts.is_absolute():
        grafts = root / grafts
    if grafts.exists():
        raise SourceTransitionError("source transition refuses a repository with legacy Git grafts")
    return root


def _relative_path(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise SourceTransitionError(f"{field} must be a string path")
    raw = value
    path = PurePosixPath(raw)
    if (
        not raw
        or "\0" in raw
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
        or path.is_absolute()
        or raw != path.as_posix()
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise SourceTransitionError(f"{field} must be a normalized relative POSIX path")
    return raw


def _commit(repo_root: Path, value: Any, field: str) -> str:
    requested = _sha(value, field)
    resolved = (
        _git(
            repo_root,
            "rev-parse",
            "--verify",
            f"{requested}^{{commit}}",
        )
        .decode("ascii")
        .strip()
    )
    if resolved != requested:
        raise SourceTransitionError(f"{field} does not resolve exactly")
    return resolved


def _raw_changes(repo_root: Path, producer: str, consumer: str) -> list[dict[str, str]]:
    raw = _git(
        repo_root,
        "diff-tree",
        "--raw",
        "-z",
        "--no-abbrev",
        "--full-index",
        "--no-commit-id",
        "-r",
        "--no-renames",
        producer,
        consumer,
        "--",
    )
    parts = raw.split(b"\0")
    if parts and parts[-1] == b"":
        parts.pop()
    if len(parts) % 2:
        raise SourceTransitionError("git returned malformed raw changed-path data")
    changes: list[dict[str, str]] = []
    for index in range(0, len(parts), 2):
        try:
            header = parts[index].decode("ascii")
            path = parts[index + 1].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceTransitionError("Git returned a raw change that is not UTF-8") from exc
        fields = header.split(" ")
        if len(fields) != 5 or not fields[0].startswith(":"):
            raise SourceTransitionError("git returned a malformed raw change header")
        old_mode = fields[0][1:]
        new_mode, old_object, new_object, status = fields[1:]
        if (
            not _GIT_MODE.fullmatch(old_mode)
            or not _GIT_MODE.fullmatch(new_mode)
            or not _GIT_SHA.fullmatch(old_object)
            or not _GIT_SHA.fullmatch(new_object)
            or not _GIT_STATUS.fullmatch(status)
        ):
            raise SourceTransitionError("git returned invalid raw change fields")
        changes.append(
            {
                "status": status,
                "old_mode": old_mode,
                "new_mode": new_mode,
                "old_object": old_object,
                "new_object": new_object,
                "path": _relative_path(path, "changed path"),
            }
        )
    changes.sort(
        key=lambda item: (
            item["path"],
            item["status"],
            item["old_mode"],
            item["new_mode"],
            item["old_object"],
            item["new_object"],
        )
    )
    return changes


def source_transition_git_facts(
    *,
    repo_root: Path,
    producer_source_git_sha: str,
    consumer_source_git_sha: str,
) -> dict[str, Any]:
    """Return the exact, recomputable Git relationship between two commits."""

    root = _repository_root(repo_root)
    producer = _commit(
        root,
        producer_source_git_sha,
        "producer_source_git_sha",
    )
    consumer = _commit(
        root,
        consumer_source_git_sha,
        "consumer_source_git_sha",
    )
    if producer == consumer:
        raise SourceTransitionError(
            "a source transition requires different producer and consumer commits"
        )
    merge_base = _git(root, "merge-base", producer, consumer).decode("ascii").strip()
    if merge_base != producer:
        raise SourceTransitionError("the evidence producer is not an ancestor of the consumer")
    producer_tree = (
        _git(
            root,
            "rev-parse",
            "--verify",
            f"{producer}^{{tree}}",
        )
        .decode("ascii")
        .strip()
    )
    consumer_tree = (
        _git(
            root,
            "rev-parse",
            "--verify",
            f"{consumer}^{{tree}}",
        )
        .decode("ascii")
        .strip()
    )
    distance_text = (
        _git(
            root,
            "rev-list",
            "--count",
            f"{producer}..{consumer}",
        )
        .decode("ascii")
        .strip()
    )
    try:
        distance = int(distance_text)
    except ValueError as exc:
        raise SourceTransitionError("git returned an invalid ancestor distance") from exc
    if distance < 1:
        raise SourceTransitionError("source transition has no consumer commits")

    raw_changes = _raw_changes(root, producer, consumer)
    changed_paths = [{"status": item["status"], "path": item["path"]} for item in raw_changes]
    return {
        "schema_version": "pixcell-training-source-transition-git-v1",
        "producer_source_git_sha": producer,
        "consumer_source_git_sha": consumer,
        "merge_base_git_sha": merge_base,
        "producer_tree_git_sha": producer_tree,
        "consumer_tree_git_sha": consumer_tree,
        "ancestor_distance": distance,
        "changed_path_count": len(changed_paths),
        "changed_paths": changed_paths,
        "raw_changes": raw_changes,
        "raw_change_inventory_sha256": canonical_sha256(raw_changes),
    }


def approved_change_scope(
    git_facts: Mapping[str, Any],
    approved_change_paths: Sequence[str] | None,
) -> dict[str, Any]:
    """Bind explicit human-reviewed paths to the exact committed Git diff."""

    if approved_change_paths is None:
        raise SourceTransitionError(
            "cross-source approval requires an explicit approved change scope"
        )
    if isinstance(approved_change_paths, (str, bytes)):
        raise SourceTransitionError("approved change scope must be a sequence of paths")
    approved = [_relative_path(value, "approved change path") for value in approved_change_paths]
    if len(set(approved)) != len(approved):
        raise SourceTransitionError("approved change scope repeats a path")
    approved.sort()
    raw_changes = git_facts.get("raw_changes")
    if not isinstance(raw_changes, list):
        raise SourceTransitionError("Git facts have no raw change inventory")
    observed: list[dict[str, str]] = []
    required = {
        "status",
        "old_mode",
        "new_mode",
        "old_object",
        "new_object",
        "path",
    }
    for index, raw_entry in enumerate(raw_changes):
        if not isinstance(raw_entry, Mapping):
            raise SourceTransitionError(f"Git raw change {index} is not an object")
        if set(raw_entry) != required:
            raise SourceTransitionError(f"Git raw change {index} has foreign fields")
        status = str(raw_entry.get("status", ""))
        old_mode = str(raw_entry.get("old_mode", ""))
        new_mode = str(raw_entry.get("new_mode", ""))
        old_object = str(raw_entry.get("old_object", ""))
        new_object = str(raw_entry.get("new_object", ""))
        if (
            not _GIT_STATUS.fullmatch(status)
            or not _GIT_MODE.fullmatch(old_mode)
            or not _GIT_MODE.fullmatch(new_mode)
            or not _GIT_SHA.fullmatch(old_object)
            or not _GIT_SHA.fullmatch(new_object)
        ):
            raise SourceTransitionError(f"Git raw change {index} has invalid fields")
        observed.append(
            {
                "status": status,
                "old_mode": old_mode,
                "new_mode": new_mode,
                "old_object": old_object,
                "new_object": new_object,
                "path": _relative_path(
                    raw_entry.get("path"),
                    f"Git raw change {index}",
                ),
            }
        )
    observed.sort(
        key=lambda item: (
            item["path"],
            item["status"],
            item["old_mode"],
            item["new_mode"],
            item["old_object"],
            item["new_object"],
        )
    )
    observed_paths = [item["path"] for item in observed]
    if approved != observed_paths:
        raise SourceTransitionError(
            "approved change paths differ from the exact producer-to-consumer diff"
        )
    changed_paths = [{"status": item["status"], "path": item["path"]} for item in observed]
    if (
        git_facts.get("changed_path_count") != len(observed)
        or git_facts.get("changed_paths") != changed_paths
    ):
        raise SourceTransitionError("Git path projection differs from its raw change inventory")
    inventory_sha256 = str(git_facts.get("raw_change_inventory_sha256", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", inventory_sha256) or inventory_sha256 != canonical_sha256(
        observed
    ):
        raise SourceTransitionError("Git facts have an invalid raw change inventory digest")
    scope = {
        "schema_version": "pixcell-training-approved-change-scope-v1",
        "policy": "exact-committed-path-status-mode-and-object-inventory",
        "paths": approved,
        "entries": observed,
        "changed_path_count": len(observed),
        "raw_change_inventory_sha256": inventory_sha256,
    }
    scope["logical_sha256"] = canonical_sha256(scope)
    return scope


def build_source_transition(
    *,
    repo_root: Path,
    producer_source_git_sha: str,
    consumer_source_git_sha: str,
    scope: Mapping[str, Any],
    approved_change_paths: Sequence[str] | None,
    equivalence: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the canonical transition document embedded in a v2 approval."""

    git_facts = source_transition_git_facts(
        repo_root=repo_root,
        producer_source_git_sha=producer_source_git_sha,
        consumer_source_git_sha=consumer_source_git_sha,
    )
    authorization = dict(scope)
    authorization["approved_changes"] = approved_change_scope(
        git_facts,
        approved_change_paths,
    )
    document: dict[str, Any] = {
        "schema_version": SOURCE_TRANSITION_SCHEMA_VERSION,
        "git": git_facts,
        "scope": authorization,
        "equivalence": dict(equivalence),
        "evidence": dict(evidence),
    }
    document["logical_sha256"] = canonical_sha256(document)
    return document


def validate_source_transition(
    observed: Any,
    *,
    repo_root: Path,
    producer_source_git_sha: str,
    consumer_source_git_sha: str,
    scope: Mapping[str, Any],
    approved_change_paths: Sequence[str] | None,
    equivalence: Mapping[str, Any],
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    """Rebuild and compare every transition field, including its Git diff."""

    if not isinstance(observed, Mapping):
        raise SourceTransitionError("source transition must be an object")
    expected = build_source_transition(
        repo_root=repo_root,
        producer_source_git_sha=producer_source_git_sha,
        consumer_source_git_sha=consumer_source_git_sha,
        scope=scope,
        approved_change_paths=approved_change_paths,
        equivalence=equivalence,
        evidence=evidence,
    )
    if dict(observed) != expected:
        raise SourceTransitionError(
            "source transition differs from the current repository and evidence"
        )
    return expected
