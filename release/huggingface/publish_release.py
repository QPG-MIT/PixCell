#!/usr/bin/env python3
"""Safely publish a validated PixCell dataset package through a Hub pull request.

The publisher does not build a release. It accepts a complete local package,
validates it, computes the exact replacement of the Hub repository, and places
all additions and deletions in one pull-request commit. Dry-run is the default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from huggingface_hub import (
    CommitOperationAdd,
    CommitOperationDelete,
    HfApi,
    hf_hub_download,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPO_ID = "qpaig-mit/pixcell"
DEFAULT_EXPECTED_ORG = "qpaig-mit"
REPO_TYPE = "dataset"
SAFETY_TAG = "v1.0.0"
RELEASE_TAG = "v2.0.0"
LEGACY_TAG_COMMITS = {
    "core-v1": "5f2e4f66506ac09bd0c751668df0ed937ee7b629",
    "depth-v1": "fb9c02024e09d35378d105ffe939f9a9ff962f15",
}
LEGACY_TAG_OBJECTS = {
    "core-v1": "7ee5016168263925515c21196642002d10e61433",
    "depth-v1": "096107d7c889c7b8e1942931da8679a0b7749935",
}
EXPECTED_CONFIG_SPLITS = {
    "depth": {"train": 3468, "validation": 1092},
    "core": {"train": 738},
    "references": {"train": 3468, "validation": 1092},
}
EXPECTED_DEFAULT_CONFIG = "depth"
EXPECTED_MANIFEST_SCHEMA = "pixcell-hf-release-manifest-v2"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
FORBIDDEN_PACKAGE_PARTS = frozenset({".git", ".cache", ".pytest_cache", "__pycache__"})
APPROVED_PACKAGE_RELATIVE = Path("release/huggingface/generated")


class PublicationError(RuntimeError):
    """Raised when a release safety assertion fails."""


@dataclass(frozen=True)
class PackageFile:
    path: str
    sha256: str
    size: int
    local_path: Path


@dataclass(frozen=True)
class PublicationReport:
    mode: str
    repo_id: str
    source_git_sha: str
    expected_main_sha: str
    package_root: str
    package_files: int
    additions: int
    deletions: int
    add_paths: tuple[str, ...]
    delete_paths: tuple[str, ...]
    safety_tag: str
    pull_request: str | None = None
    merged_main_sha: str | None = None
    release_tag: str | None = None


Validator = Callable[[Path, Path], Any]
Downloader = Callable[..., str]
GitInspector = Callable[[Path], str]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_git_source(repo_root: Path) -> str:
    """Require a real, clean Git worktree and return its committed HEAD."""

    repo_root = repo_root.resolve()

    def output(*args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    observed_root = Path(output("rev-parse", "--show-toplevel")).resolve()
    if observed_root != repo_root:
        raise PublicationError(f"publisher repo root is {repo_root}, Git reports {observed_root}")
    status = output("status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise PublicationError(
            "publication requires a clean worktree with every release source file committed"
        )
    head = output("rev-parse", "HEAD")
    if not SHA40.fullmatch(head):
        raise PublicationError(f"Git HEAD is not a full commit SHA: {head!r}")
    return head


def validate_local_package(package_root: Path, dataset_root: Path) -> Any:
    """Run the release validator without duplicating its policy here."""

    from release.huggingface.validate_release import validate_release

    report = validate_release(
        release_root=package_root.resolve(),
        dataset_root=dataset_root.resolve(),
    )
    if isinstance(report, Mapping) and report.get("status") not in (None, "pass"):
        raise PublicationError(f"release validator did not pass: {report}")
    return report


def package_inventory(package_root: Path) -> tuple[PackageFile, ...]:
    package_root = package_root.resolve()
    if not package_root.is_dir():
        raise PublicationError(f"package root is not a directory: {package_root}")
    for required in ("README.md", "manifest.json"):
        if not (package_root / required).is_file():
            raise PublicationError(f"package is missing {required}")

    try:
        manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read package manifest: {exc}") from exc
    if manifest.get("schema_version") != EXPECTED_MANIFEST_SCHEMA:
        raise PublicationError(
            f"unexpected package manifest schema: {manifest.get('schema_version')!r}"
        )

    records: list[PackageFile] = []
    for path in sorted(package_root.rglob("*")):
        if path.is_symlink():
            raise PublicationError(f"package contains a symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(package_root)
        if FORBIDDEN_PACKAGE_PARTS.intersection(relative.parts):
            raise PublicationError(f"package contains transient path: {relative}")
        records.append(
            PackageFile(
                path=relative.as_posix(),
                sha256=sha256_file(path),
                size=path.stat().st_size,
                local_path=path,
            )
        )
    if not records:
        raise PublicationError("package contains no files")
    return tuple(records)


def package_source_git_sha(package_root: Path) -> str:
    """Read and validate the source commit bound into a built package."""

    try:
        manifest = json.loads((package_root / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublicationError(f"cannot read package manifest: {exc}") from exc
    source_git_sha = str(manifest.get("source_git_sha", ""))
    if not SHA40.fullmatch(source_git_sha):
        raise PublicationError(f"package manifest has invalid source Git SHA {source_git_sha!r}")
    return source_git_sha


def _revision_sha(api: Any, repo_id: str, revision: str) -> str:
    info = api.repo_info(
        repo_id=repo_id,
        repo_type=REPO_TYPE,
        revision=revision,
    )
    sha = str(getattr(info, "sha", ""))
    if not SHA40.fullmatch(sha):
        raise PublicationError(f"Hub revision {revision!r} returned invalid SHA {sha!r}")
    return sha


def _tag_names(api: Any, repo_id: str) -> set[str]:
    refs = api.list_repo_refs(repo_id=repo_id, repo_type=REPO_TYPE)
    return {str(ref.name) for ref in refs.tags}


def assert_legacy_tags(api: Any, repo_id: str) -> None:
    refs = api.list_repo_refs(repo_id=repo_id, repo_type=REPO_TYPE)
    tag_objects = {str(ref.name): str(ref.target_commit) for ref in refs.tags}
    for tag, expected_commit in LEGACY_TAG_COMMITS.items():
        if tag not in tag_objects:
            raise PublicationError(f"required legacy tag is missing: {tag}")
        expected_object = LEGACY_TAG_OBJECTS[tag]
        observed_object = tag_objects[tag]
        if observed_object != expected_object:
            raise PublicationError(
                f"legacy tag object {tag} is {observed_object}, expected {expected_object}"
            )
        observed_commit = _revision_sha(api, repo_id, tag)
        if observed_commit != expected_commit:
            raise PublicationError(
                f"legacy tag {tag} resolves to {observed_commit}, expected {expected_commit}"
            )


def assert_authenticated_org(
    api: Any,
    *,
    repo_id: str,
    expected_org: str,
) -> None:
    namespace = repo_id.split("/", 1)[0]
    if namespace != expected_org:
        raise PublicationError(
            f"repository namespace {namespace!r} differs from expected "
            f"organization {expected_org!r}"
        )
    identity = api.whoami()
    organizations = {
        str(org.get("name")) for org in identity.get("orgs", []) if isinstance(org, Mapping)
    }
    if expected_org not in organizations:
        raise PublicationError(f"authenticated identity is not a member of {expected_org!r}")


def assert_default_configs(info: Any) -> None:
    card_data = getattr(info, "card_data", None)
    if card_data is None:
        raise PublicationError("Hub dataset has no parsed card metadata")
    if hasattr(card_data, "to_dict"):
        card_data = card_data.to_dict()
    if not isinstance(card_data, Mapping):
        raise PublicationError("Hub dataset card metadata is not a mapping")

    configs = card_data.get("configs")
    if not isinstance(configs, list):
        raise PublicationError("Hub dataset card has no configuration list")
    by_name: dict[str, Mapping[str, Any]] = {}
    for config in configs:
        if not isinstance(config, Mapping):
            raise PublicationError("Hub dataset card contains an invalid config")
        name = str(config.get("config_name", ""))
        if not name or name in by_name:
            raise PublicationError("Hub dataset card has missing/duplicate config names")
        by_name[name] = config
    if set(by_name) != set(EXPECTED_CONFIG_SPLITS):
        raise PublicationError(
            f"Hub configs are {sorted(by_name)}, expected {sorted(EXPECTED_CONFIG_SPLITS)}"
        )
    defaults = [name for name, config in by_name.items() if config.get("default") is True]
    if defaults != [EXPECTED_DEFAULT_CONFIG]:
        raise PublicationError(
            f"Hub default configs are {defaults}, expected [{EXPECTED_DEFAULT_CONFIG!r}]"
        )

    dataset_info = card_data.get("dataset_info")
    if not isinstance(dataset_info, list):
        raise PublicationError("Hub dataset card has no dataset_info list")
    observed_splits: dict[str, dict[str, int]] = {}
    for config in dataset_info:
        if not isinstance(config, Mapping):
            continue
        name = str(config.get("config_name", ""))
        splits = config.get("splits")
        if not isinstance(splits, list):
            continue
        observed_splits[name] = {
            str(split["name"]): int(split["num_examples"])
            for split in splits
            if isinstance(split, Mapping) and "name" in split and "num_examples" in split
        }
    if observed_splits != EXPECTED_CONFIG_SPLITS:
        raise PublicationError(
            f"Hub split metadata is {observed_splits}, expected {EXPECTED_CONFIG_SPLITS}"
        )


def _ensure_tag(
    api: Any,
    *,
    repo_id: str,
    tag: str,
    expected_sha: str,
    message: str,
) -> None:
    if tag not in _tag_names(api, repo_id):
        api.create_tag(
            repo_id=repo_id,
            repo_type=REPO_TYPE,
            tag=tag,
            revision=expected_sha,
            tag_message=message,
            exist_ok=False,
        )
    observed = _revision_sha(api, repo_id, tag)
    if observed != expected_sha:
        raise PublicationError(f"tag {tag} resolves to {observed}, expected {expected_sha}")


def _download_and_validate_revision(
    *,
    api: Any,
    downloader: Downloader,
    validator: Validator,
    repo_id: str,
    revision: str,
    inventory: Sequence[PackageFile],
    dataset_root: Path,
) -> None:
    expected_paths = {record.path for record in inventory}
    remote_paths = set(
        api.list_repo_files(
            repo_id=repo_id,
            repo_type=REPO_TYPE,
            revision=revision,
        )
    )
    if remote_paths != expected_paths:
        raise PublicationError(
            f"remote {revision} file set differs: "
            f"missing={sorted(expected_paths - remote_paths)}, "
            f"extra={sorted(remote_paths - expected_paths)}"
        )

    with tempfile.TemporaryDirectory(prefix="pixcell-hf-verify-") as temp:
        downloaded_root = Path(temp)
        for record in inventory:
            cached = Path(
                downloader(
                    repo_id=repo_id,
                    repo_type=REPO_TYPE,
                    revision=revision,
                    filename=record.path,
                )
            )
            observed = sha256_file(cached)
            if observed != record.sha256:
                raise PublicationError(
                    f"remote {revision}:{record.path} has SHA-256 {observed}, "
                    f"expected {record.sha256}"
                )
            destination = downloaded_root / record.path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(cached, destination)
        validator(downloaded_root, dataset_root)


def _wait_for_changed_main(
    api: Any,
    *,
    repo_id: str,
    previous_sha: str,
    timeout_seconds: float,
    poll_seconds: float,
    monotonic: Callable[[], float],
    sleep: Callable[[float], None],
) -> str:
    deadline = monotonic() + timeout_seconds
    while True:
        observed = _revision_sha(api, repo_id, "main")
        if observed != previous_sha:
            return observed
        if monotonic() >= deadline:
            raise PublicationError("timed out waiting for merged main revision")
        sleep(poll_seconds)


def publish_release(
    *,
    package_root: Path,
    dataset_root: Path,
    repo_root: Path,
    expected_main_sha: str,
    repo_id: str = DEFAULT_REPO_ID,
    expected_org: str = DEFAULT_EXPECTED_ORG,
    apply: bool = False,
    api: Any | None = None,
    downloader: Downloader = hf_hub_download,
    validator: Validator = validate_local_package,
    git_inspector: GitInspector = inspect_git_source,
    merge_timeout_seconds: float = 60.0,
    poll_seconds: float = 1.0,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> PublicationReport:
    """Plan or execute an atomic, version-preserving Hub publication."""

    if not SHA40.fullmatch(expected_main_sha):
        raise PublicationError("--expected-main-sha must be a full 40-char SHA")
    package_root = package_root.resolve()
    dataset_root = dataset_root.resolve()
    repo_root = repo_root.resolve()
    expected_dataset_root = (repo_root / "dataset").resolve()
    if dataset_root != expected_dataset_root:
        raise PublicationError(
            "dataset root must be bound to the publication repository: "
            f"expected {expected_dataset_root}, got {dataset_root}"
        )
    expected_package_root = (repo_root / APPROVED_PACKAGE_RELATIVE).resolve()
    if package_root != expected_package_root:
        raise PublicationError(
            "package root must be the approved repository release output: "
            f"expected {expected_package_root}, got {package_root}"
        )
    source_git_sha = git_inspector(repo_root)
    package_git_sha = package_source_git_sha(package_root)
    if package_git_sha != source_git_sha:
        raise PublicationError(
            "package source Git SHA differs from the clean publication "
            f"repository: package={package_git_sha}, repository={source_git_sha}"
        )
    validator(package_root, dataset_root)
    inventory = package_inventory(package_root)

    api = api or HfApi()
    assert_authenticated_org(api, repo_id=repo_id, expected_org=expected_org)
    observed_main = _revision_sha(api, repo_id, "main")
    if observed_main != expected_main_sha:
        raise PublicationError(f"Hub main moved to {observed_main}; expected {expected_main_sha}")
    assert_legacy_tags(api, repo_id)

    tag_names = _tag_names(api, repo_id)
    if SAFETY_TAG in tag_names:
        safety_sha = _revision_sha(api, repo_id, SAFETY_TAG)
        if safety_sha != expected_main_sha:
            raise PublicationError(
                f"{SAFETY_TAG} resolves to {safety_sha}, expected {expected_main_sha}"
            )
    if RELEASE_TAG in tag_names:
        raise PublicationError(f"{RELEASE_TAG} already exists; release tags are never moved")

    remote_files = set(
        api.list_repo_files(
            repo_id=repo_id,
            repo_type=REPO_TYPE,
            revision=expected_main_sha,
        )
    )
    local_files = {record.path for record in inventory}
    deletions = sorted(remote_files - local_files)
    report = PublicationReport(
        mode="apply" if apply else "dry-run",
        repo_id=repo_id,
        source_git_sha=source_git_sha,
        expected_main_sha=expected_main_sha,
        package_root=str(package_root),
        package_files=len(inventory),
        additions=len(inventory),
        deletions=len(deletions),
        add_paths=tuple(record.path for record in inventory),
        delete_paths=tuple(deletions),
        safety_tag=SAFETY_TAG,
    )
    if not apply:
        return report

    _ensure_tag(
        api,
        repo_id=repo_id,
        tag=SAFETY_TAG,
        expected_sha=expected_main_sha,
        message="PixCell dataset before the v2 schema release",
    )
    assert_legacy_tags(api, repo_id)
    if _revision_sha(api, repo_id, "main") != expected_main_sha:
        raise PublicationError("Hub main changed before pull-request creation")

    operations: list[Any] = [
        CommitOperationAdd(
            path_in_repo=record.path,
            path_or_fileobj=record.local_path,
        )
        for record in inventory
    ]
    operations.extend(CommitOperationDelete(path_in_repo=path) for path in deletions)
    commit = api.create_commit(
        repo_id=repo_id,
        repo_type=REPO_TYPE,
        revision="main",
        parent_commit=expected_main_sha,
        create_pr=True,
        operations=operations,
        commit_message="Publish PixCell dataset v2",
        commit_description=(
            "Publish generic core, depth, and references configurations; make depth the default."
        ),
    )
    pr_revision = getattr(commit, "pr_revision", None)
    pr_num = getattr(commit, "pr_num", None)
    pr_url = getattr(commit, "pr_url", None)
    if not pr_revision or not isinstance(pr_num, int) or not pr_url:
        raise PublicationError("Hub did not return a pull-request revision")

    _download_and_validate_revision(
        api=api,
        downloader=downloader,
        validator=validator,
        repo_id=repo_id,
        revision=str(pr_revision),
        inventory=inventory,
        dataset_root=dataset_root,
    )
    assert_default_configs(
        api.repo_info(
            repo_id=repo_id,
            repo_type=REPO_TYPE,
            revision=str(pr_revision),
        )
    )
    if _revision_sha(api, repo_id, "main") != expected_main_sha:
        raise PublicationError("Hub main changed while validating the pull request")
    assert_legacy_tags(api, repo_id)

    api.merge_pull_request(
        repo_id=repo_id,
        repo_type=REPO_TYPE,
        discussion_num=pr_num,
        comment="Validated exact package, schemas, splits, and release history.",
    )
    merged_sha = _wait_for_changed_main(
        api,
        repo_id=repo_id,
        previous_sha=expected_main_sha,
        timeout_seconds=merge_timeout_seconds,
        poll_seconds=poll_seconds,
        monotonic=monotonic,
        sleep=sleep,
    )
    _download_and_validate_revision(
        api=api,
        downloader=downloader,
        validator=validator,
        repo_id=repo_id,
        revision=merged_sha,
        inventory=inventory,
        dataset_root=dataset_root,
    )
    main_info = api.repo_info(
        repo_id=repo_id,
        repo_type=REPO_TYPE,
        revision="main",
    )
    if str(getattr(main_info, "sha", "")) != merged_sha:
        raise PublicationError("Hub main changed during post-merge validation")
    assert_default_configs(main_info)
    assert_legacy_tags(api, repo_id)

    _ensure_tag(
        api,
        repo_id=repo_id,
        tag=RELEASE_TAG,
        expected_sha=merged_sha,
        message="PixCell dataset v2",
    )
    if _revision_sha(api, repo_id, "main") != merged_sha:
        raise PublicationError("Hub main changed while creating the release tag")
    assert_legacy_tags(api, repo_id)

    return PublicationReport(
        **{
            **asdict(report),
            "pull_request": str(pr_url),
            "merged_main_sha": merged_sha,
            "release_tag": RELEASE_TAG,
        }
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument(
        "--dataset-root",
        type=Path,
        default=REPO_ROOT / "dataset",
    )
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--repo-id", default=DEFAULT_REPO_ID)
    parser.add_argument("--expected-org", default=DEFAULT_EXPECTED_ORG)
    parser.add_argument("--expected-main-sha", required=True)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create tags, open/merge the validated PR, and publish v2.0.0.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    report = publish_release(
        package_root=args.package_root,
        dataset_root=args.dataset_root,
        repo_root=args.repo_root,
        expected_main_sha=args.expected_main_sha,
        repo_id=args.repo_id,
        expected_org=args.expected_org,
        apply=args.apply,
    )
    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
