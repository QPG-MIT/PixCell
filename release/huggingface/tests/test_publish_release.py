from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from huggingface_hub import CommitOperationAdd, CommitOperationDelete

from release.huggingface.publish_release import (
    LEGACY_TAG_COMMITS,
    LEGACY_TAG_OBJECTS,
    RELEASE_TAG,
    SAFETY_TAG,
    PublicationError,
    parse_args,
    publish_release,
)


OLD_MAIN = "a" * 40
MERGED_MAIN = "b" * 40
PR_SHA = "c" * 40


def card_data() -> dict[str, Any]:
    return {
        "configs": [
            {"config_name": "depth", "default": True},
            {"config_name": "core"},
            {"config_name": "references"},
        ],
        "dataset_info": [
            {
                "config_name": "depth",
                "splits": [
                    {"name": "train", "num_examples": 3468},
                    {"name": "validation", "num_examples": 1092},
                ],
            },
            {
                "config_name": "core",
                "splits": [{"name": "train", "num_examples": 738}],
            },
            {
                "config_name": "references",
                "splits": [
                    {"name": "train", "num_examples": 3468},
                    {"name": "validation", "num_examples": 1092},
                ],
            },
        ],
    }


def make_package(root: Path) -> Path:
    package = root / "package"
    (package / "depth" / "data").mkdir(parents=True)
    (package / "references" / "data").mkdir(parents=True)
    (package / "core" / "data").mkdir(parents=True)
    (package / "README.md").write_text("---\n---\n# PixCell\n", encoding="utf-8")
    (package / "manifest.json").write_text(
        json.dumps({"schema_version": "pixcell-hf-release-manifest-v2"}),
        encoding="utf-8",
    )
    (package / "depth" / "data" / "train.parquet").write_bytes(b"depth")
    (package / "references" / "data" / "train.parquet").write_bytes(
        b"references"
    )
    (package / "core" / "data" / "train.parquet").write_bytes(b"core")
    return package


class FakeApi:
    def __init__(self, package: Path, *, bad_download: bool = False) -> None:
        self.package = package
        self.bad_download = bad_download
        self.main_sha = OLD_MAIN
        self.tags = dict(LEGACY_TAG_COMMITS)
        self.tag_objects = dict(LEGACY_TAG_OBJECTS)
        self.remote_files = {"README.md", "obsolete.txt"}
        self.pr_files = {
            path.relative_to(package).as_posix()
            for path in package.rglob("*")
            if path.is_file()
        }
        self.create_commit_calls: list[dict[str, Any]] = []
        self.create_tag_calls: list[dict[str, Any]] = []
        self.merge_calls: list[dict[str, Any]] = []

    def whoami(self) -> dict[str, Any]:
        return {"name": "release-operator", "orgs": [{"name": "qpaig-mit"}]}

    def list_repo_refs(self, **_: Any) -> Any:
        return SimpleNamespace(
            tags=[
                SimpleNamespace(
                    name=name,
                    target_commit=self.tag_objects.get(name, sha),
                )
                for name, sha in self.tags.items()
            ]
        )

    def repo_info(self, *, revision: str, **_: Any) -> Any:
        if revision == "main":
            return SimpleNamespace(
                sha=self.main_sha,
                card_data=card_data() if self.main_sha == MERGED_MAIN else None,
            )
        if revision == "refs/pr/17":
            return SimpleNamespace(sha=PR_SHA, card_data=card_data())
        if revision in self.tags:
            return SimpleNamespace(sha=self.tags[revision], card_data=None)
        if revision == MERGED_MAIN:
            return SimpleNamespace(sha=MERGED_MAIN, card_data=card_data())
        raise AssertionError(f"unexpected revision {revision}")

    def list_repo_files(self, *, revision: str, **_: Any) -> list[str]:
        if revision == OLD_MAIN:
            return sorted(self.remote_files)
        if revision in {"refs/pr/17", MERGED_MAIN}:
            return sorted(self.pr_files)
        raise AssertionError(f"unexpected file revision {revision}")

    def create_tag(self, **kwargs: Any) -> None:
        self.create_tag_calls.append(kwargs)
        assert kwargs["tag"] not in self.tags
        self.tags[kwargs["tag"]] = kwargs["revision"]
        self.tag_objects[kwargs["tag"]] = kwargs["revision"]

    def create_commit(self, **kwargs: Any) -> Any:
        self.create_commit_calls.append(kwargs)
        assert kwargs["create_pr"] is True
        assert kwargs["parent_commit"] == OLD_MAIN
        assert kwargs["revision"] == "main"
        return SimpleNamespace(
            oid=PR_SHA,
            pr_revision="refs/pr/17",
            pr_num=17,
            pr_url="https://huggingface.co/datasets/qpaig-mit/pixcell/discussions/17",
        )

    def merge_pull_request(self, **kwargs: Any) -> None:
        self.merge_calls.append(kwargs)
        self.main_sha = MERGED_MAIN


def downloader_for(api: FakeApi, temp: Path):
    def download(*, revision: str, filename: str, **_: Any) -> str:
        source = api.package / filename
        if api.bad_download and revision == "refs/pr/17" and filename == "README.md":
            corrupt = temp / "corrupt"
            corrupt.write_bytes(b"wrong")
            return str(corrupt)
        return str(source)

    return download


def test_dry_run_is_default_and_never_mutates(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    api = FakeApi(package)
    validations: list[Path] = []

    report = publish_release(
        package_root=package,
        dataset_root=tmp_path,
        repo_root=tmp_path,
        expected_main_sha=OLD_MAIN,
        api=api,
        validator=lambda release, _: validations.append(release),
        git_inspector=lambda _: "d" * 40,
    )

    assert report.mode == "dry-run"
    assert report.additions == 5
    assert report.deletions == 1
    assert set(report.add_paths) == api.pr_files
    assert report.delete_paths == ("obsolete.txt",)
    assert validations == [package]
    assert api.create_commit_calls == []
    assert api.create_tag_calls == []
    assert api.merge_calls == []


def test_apply_uses_one_atomic_pr_and_tags_only_after_validation(
    tmp_path: Path,
) -> None:
    package = make_package(tmp_path)
    api = FakeApi(package)
    validations: list[Path] = []

    report = publish_release(
        package_root=package,
        dataset_root=tmp_path,
        repo_root=tmp_path,
        expected_main_sha=OLD_MAIN,
        apply=True,
        api=api,
        downloader=downloader_for(api, tmp_path),
        validator=lambda release, _: validations.append(release),
        git_inspector=lambda _: "d" * 40,
        sleep=lambda _: None,
    )

    assert len(api.create_commit_calls) == 1
    operations = api.create_commit_calls[0]["operations"]
    additions = {
        operation.path_in_repo
        for operation in operations
        if isinstance(operation, CommitOperationAdd)
    }
    deletions = {
        operation.path_in_repo
        for operation in operations
        if isinstance(operation, CommitOperationDelete)
    }
    assert additions == api.pr_files
    assert deletions == {"obsolete.txt"}
    assert len(api.merge_calls) == 1
    assert [call["tag"] for call in api.create_tag_calls] == [
        SAFETY_TAG,
        RELEASE_TAG,
    ]
    assert api.tags[SAFETY_TAG] == OLD_MAIN
    assert api.tags[RELEASE_TAG] == MERGED_MAIN
    assert {
        tag: api.tags[tag] for tag in LEGACY_TAG_COMMITS
    } == LEGACY_TAG_COMMITS
    assert len(validations) == 3
    assert report.pull_request is not None
    assert report.merged_main_sha == MERGED_MAIN
    assert report.release_tag == RELEASE_TAG


def test_pr_byte_mismatch_blocks_merge_and_v2_tag(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    api = FakeApi(package, bad_download=True)

    with pytest.raises(PublicationError, match="has SHA-256"):
        publish_release(
            package_root=package,
            dataset_root=tmp_path,
            repo_root=tmp_path,
            expected_main_sha=OLD_MAIN,
            apply=True,
            api=api,
            downloader=downloader_for(api, tmp_path),
            validator=lambda *_: None,
            git_inspector=lambda _: "d" * 40,
            sleep=lambda _: None,
        )

    assert len(api.create_commit_calls) == 1
    assert api.merge_calls == []
    assert SAFETY_TAG in api.tags
    assert RELEASE_TAG not in api.tags


def test_legacy_tag_drift_fails_before_mutation(tmp_path: Path) -> None:
    package = make_package(tmp_path)
    api = FakeApi(package)
    api.tags["core-v1"] = "e" * 40

    with pytest.raises(PublicationError, match="legacy tag core-v1"):
        publish_release(
            package_root=package,
            dataset_root=tmp_path,
            repo_root=tmp_path,
            expected_main_sha=OLD_MAIN,
            apply=True,
            api=api,
            validator=lambda *_: None,
            git_inspector=lambda _: "d" * 40,
        )

    assert api.create_tag_calls == []
    assert api.create_commit_calls == []
    assert api.merge_calls == []


def test_legacy_annotated_tag_object_drift_fails_before_mutation(
    tmp_path: Path,
) -> None:
    package = make_package(tmp_path)
    api = FakeApi(package)
    api.tag_objects["depth-v1"] = "f" * 40

    with pytest.raises(PublicationError, match="legacy tag object depth-v1"):
        publish_release(
            package_root=package,
            dataset_root=tmp_path,
            repo_root=tmp_path,
            expected_main_sha=OLD_MAIN,
            apply=True,
            api=api,
            validator=lambda *_: None,
            git_inspector=lambda _: "d" * 40,
        )

    assert api.create_tag_calls == []
    assert api.create_commit_calls == []
    assert api.merge_calls == []


def test_cli_requires_expected_main_and_defaults_to_dry_run() -> None:
    with pytest.raises(SystemExit):
        parse_args(["--package-root", "/tmp/package"])
    args = parse_args(
        [
            "--package-root",
            "/tmp/package",
            "--expected-main-sha",
            OLD_MAIN,
        ]
    )
    assert args.apply is False
