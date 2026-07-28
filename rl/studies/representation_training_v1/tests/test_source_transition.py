from __future__ import annotations

import copy
import subprocess
from pathlib import Path

import pytest

from rl.studies.representation_training_v1.protocol import (
    validate_source_sha,
)
from rl.studies.representation_training_v1.source_transition import (
    SourceTransitionError,
    approved_change_scope,
    build_source_transition,
    source_transition_git_facts,
    validate_source_transition,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args],
        cwd=repo,
        text=True,
    ).strip()


def _commit(repo: Path, message: str) -> str:
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    return _git(repo, "rev-parse", "HEAD")


@pytest.fixture
def git_history(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        ["git", "config", "user.name", "PixCell test"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "pixcell-test@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "core.hooksPath", "/dev/null"],
        cwd=repo,
        check=True,
    )
    (repo / "policy.py").write_text("VALUE = 1\n", encoding="utf-8")
    producer = _commit(repo, "producer")
    (repo / "policy.py").write_text("VALUE = 2\n", encoding="utf-8")
    (repo / "review.txt").write_text("reviewed\n", encoding="utf-8")
    consumer = _commit(repo, "consumer")
    return repo, producer, consumer


def test_transition_binds_ancestry_trees_diff_and_exact_scope(
    git_history: tuple[Path, str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, producer, consumer = git_history
    facts = source_transition_git_facts(
        repo_root=repo,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
    )
    assert facts["merge_base_git_sha"] == producer
    assert facts["producer_source_git_sha"] == producer
    assert facts["consumer_source_git_sha"] == consumer
    assert facts["producer_tree_git_sha"] != facts["consumer_tree_git_sha"]
    assert facts["ancestor_distance"] == 1
    assert facts["changed_path_count"] == 2
    assert facts["changed_paths"] == [
        {"status": "M", "path": "policy.py"},
        {"status": "A", "path": "review.txt"},
    ]
    assert facts["raw_changes"] == [
        {
            "status": "M",
            "old_mode": "100644",
            "new_mode": "100644",
            "old_object": _git(repo, "rev-parse", f"{producer}:policy.py"),
            "new_object": _git(repo, "rev-parse", f"{consumer}:policy.py"),
            "path": "policy.py",
        },
        {
            "status": "A",
            "old_mode": "000000",
            "new_mode": "100644",
            "old_object": "0" * 40,
            "new_object": _git(repo, "rev-parse", f"{consumer}:review.txt"),
            "path": "review.txt",
        },
    ]
    original_inventory_sha256 = facts["raw_change_inventory_sha256"]
    monkeypatch.setenv("GIT_DIFF_OPTS", "--unified=0")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "2")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "diff.algorithm")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "minimal")
    monkeypatch.setenv("GIT_CONFIG_KEY_1", "diff.renames")
    monkeypatch.setenv("GIT_CONFIG_VALUE_1", "true")
    assert (
        source_transition_git_facts(
            repo_root=repo,
            producer_source_git_sha=producer,
            consumer_source_git_sha=consumer,
        )
        == facts
    )
    assert facts["raw_change_inventory_sha256"] == original_inventory_sha256
    subprocess.run(
        ["git", "replace", producer, consumer],
        cwd=repo,
        check=True,
    )
    assert (
        source_transition_git_facts(
            repo_root=repo,
            producer_source_git_sha=producer,
            consumer_source_git_sha=consumer,
        )
        == facts
    )

    paths = ["review.txt", "policy.py"]
    approved = approved_change_scope(facts, paths)
    assert approved["paths"] == ["policy.py", "review.txt"]
    assert approved["entries"] == facts["raw_changes"]
    assert approved["raw_change_inventory_sha256"] == facts["raw_change_inventory_sha256"]

    transition = build_source_transition(
        repo_root=repo,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
        scope={"child": {"stage_id": "child", "wave": "smoke"}},
        approved_change_paths=paths,
        equivalence={"protocol": "exact"},
        evidence={"report_record_sha256": "a" * 64},
    )
    assert (
        validate_source_transition(
            transition,
            repo_root=repo,
            producer_source_git_sha=producer,
            consumer_source_git_sha=consumer,
            scope={"child": {"stage_id": "child", "wave": "smoke"}},
            approved_change_paths=paths,
            equivalence={"protocol": "exact"},
            evidence={"report_record_sha256": "a" * 64},
        )
        == transition
    )

    tampered = copy.deepcopy(transition)
    tampered["git"]["raw_changes"][0]["new_object"] = "0" * 40
    with pytest.raises(SourceTransitionError, match="differs"):
        validate_source_transition(
            tampered,
            repo_root=repo,
            producer_source_git_sha=producer,
            consumer_source_git_sha=consumer,
            scope={"child": {"stage_id": "child", "wave": "smoke"}},
            approved_change_paths=paths,
            equivalence={"protocol": "exact"},
            evidence={"report_record_sha256": "a" * 64},
        )


def test_transition_rejects_wrong_scope_and_non_ancestor(
    git_history: tuple[Path, str, str],
) -> None:
    repo, producer, consumer = git_history
    facts = source_transition_git_facts(
        repo_root=repo,
        producer_source_git_sha=producer,
        consumer_source_git_sha=consumer,
    )
    with pytest.raises(SourceTransitionError, match="approved change paths"):
        approved_change_scope(facts, ["policy.py"])
    with pytest.raises(SourceTransitionError, match="approved change paths"):
        approved_change_scope(
            facts,
            ["policy.py", "review.txt", "unrelated.txt"],
        )
    with pytest.raises(SourceTransitionError, match="explicit approved"):
        approved_change_scope(facts, None)

    subprocess.run(
        ["git", "switch", "--detach", producer],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    (repo / "sibling.txt").write_text("sibling\n", encoding="utf-8")
    sibling = _commit(repo, "sibling")
    with pytest.raises(SourceTransitionError, match="not an ancestor"):
        source_transition_git_facts(
            repo_root=repo,
            producer_source_git_sha=sibling,
            consumer_source_git_sha=consumer,
        )
    grafts = repo / ".git" / "info" / "grafts"
    grafts.write_text("", encoding="utf-8")
    with pytest.raises(SourceTransitionError, match="grafts"):
        source_transition_git_facts(
            repo_root=repo,
            producer_source_git_sha=producer,
            consumer_source_git_sha=consumer,
        )


def test_source_validation_rejects_wrong_sha_and_dirty_tree(
    git_history: tuple[Path, str, str],
) -> None:
    repo, producer, consumer = git_history
    assert validate_source_sha(repo, consumer) == consumer
    with pytest.raises(ValueError, match="differs"):
        validate_source_sha(repo, producer)

    (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ValueError, match="clean worktree"):
        validate_source_sha(repo, consumer)
