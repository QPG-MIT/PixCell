from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from release.huggingface.build_release import build_release
from release.huggingface.validate_release import (
    ReleaseValidationError,
    _purity_checkers,
    validate_release,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = REPO_ROOT / "dataset"


@pytest.fixture(scope="module")
def built_release(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output = tmp_path_factory.mktemp("pixcell-hf-v2") / "release"
    build_release(dataset_root=DATASET_ROOT, output=output)
    return output


def test_complete_release_validates_against_frozen_sources(
    built_release: Path,
) -> None:
    report = validate_release(
        release_root=built_release,
        dataset_root=DATASET_ROOT,
    )
    assert report["status"] == "pass"
    assert report["configurations"]["depth"] == {
        "train": 3468,
        "validation": 1092,
    }
    assert report["core_rows"] == 738
    assert report["opaque_ids"] == 4560
    manifest = json.loads((built_release / "manifest.json").read_text(encoding="utf-8"))
    expected_source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert manifest["source_git_sha"] == expected_source_sha


def test_support_file_drift_is_rejected(
    built_release: Path,
    tmp_path: Path,
) -> None:
    damaged = tmp_path / "damaged"
    shutil.copytree(built_release, damaged)
    with (damaged / "README.md").open("a", encoding="utf-8") as handle:
        handle.write("\ncorrupt\n")
    with pytest.raises(
        ReleaseValidationError,
        match="support-file hash differs",
    ):
        validate_release(
            release_root=damaged,
            dataset_root=DATASET_ROOT,
        )


def test_release_applies_frozen_and_current_source_policies() -> None:
    policies = _purity_checkers(DATASET_ROOT)
    assert set(policies) == {"frozen-admission", "canonical-runtime"}
    source = "exec('print(1)')"
    assert policies["frozen-admission"](source) == []
    assert "dynamic execution: exec" in policies["canonical-runtime"](source)
