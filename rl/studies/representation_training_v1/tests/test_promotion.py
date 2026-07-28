from __future__ import annotations

import copy
import subprocess
import sys
from dataclasses import replace
from pathlib import Path, PurePosixPath

import pytest

from rl.common.prompt import prompt_asset_hashes
from rl.studies.representation_training_v1 import promotion
from rl.studies.representation_training_v1.protocol import (
    STUDY_ID,
    file_sha256,
    load_protocol,
    protocol_path,
    stage_spec,
)
from rl.studies.representation_training_v1.store import (
    StageKey,
    TrainingRecord,
    TrainingStore,
    canonical_sha256,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
SOURCE_SHA = "a" * 40
CHECKPOINT = {
    "name": "final",
    "batch": 55,
    "epoch": 1,
    "final": True,
    "state_path": "tinker://unit/weights/final",
    "sampler_path": "tinker://unit/sampler_weights/final",
    "role": "terminal",
    "training_progress_fraction": 1.0,
}


def test_record_approval_import_does_not_require_tinker() -> None:
    script = """
import importlib.abc
import sys

class BlockOptionalTrainingModules(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in {"chz", "tinker", "tinker_cookbook"}:
            raise ModuleNotFoundError(f"blocked optional module: {fullname}")
        return None

sys.meta_path.insert(0, BlockOptionalTrainingModules())
import rl.studies.representation_training_v1.record_approval
"""
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_record_approval_accepts_dual_level_transition_evidence() -> None:
    from rl.studies.representation_training_v1.record_approval import parser

    args = parser().parse_args(
        [
            "--stage",
            "qwen-base-rl-l1",
            "--wave",
            "smoke",
            "--evaluation-stage",
            "qwen-base-rl-l0",
            "--evaluation-wave",
            "complete",
            "--evaluation-checkpoint",
            "000030",
            "--evaluation-report-record-sha256",
            "a" * 64,
            "--entry-baseline-report-record-sha256",
            "b" * 64,
            "--expected-source-sha",
            "c" * 40,
        ]
    )

    assert args.entry_baseline_report_record_sha256 == "b" * 64


CHECKPOINT_INVENTORY_SHA256 = canonical_sha256([CHECKPOINT])


def test_report_aggregate_rejects_non_model_status_and_failure_iou() -> None:
    base = {
        "status": "runtime_error",
        "pure_executable": False,
        "raw_absolute_scale_iou": 0.0,
    }
    promotion._aggregate([base])

    with pytest.raises(
        promotion.PromotionError,
        match="non-model evaluation status",
    ):
        promotion._aggregate([{**base, "status": "measurement_error"}])
    with pytest.raises(
        promotion.PromotionError,
        match="failed model output has nonzero IoU",
    ):
        promotion._aggregate([{**base, "raw_absolute_scale_iou": 0.1}])


def _record(
    payload: dict,
    *,
    record_sha: str,
    relative: str,
) -> TrainingRecord:
    return TrainingRecord(
        payload=payload,
        payload_sha256="e" * 64,
        record_sha256=record_sha,
        relative_path=PurePosixPath(relative),
    )


def _level_report(first_unmastered: str | None) -> dict:
    levels: dict[str, dict] = {}
    for level in ("L0", "L1", "L2", "L3", "L4"):
        mastered = first_unmastered is None or int(level[1:]) < int(first_unmastered[1:])
        levels[level] = {
            "mean_raw_absolute_scale_iou": 0.85 if mastered else 0.70,
            "pure_executable_rate": 0.98 if mastered else 0.90,
        }
    return {"levels": levels}


def _evidence(
    *,
    stage_id: str,
    wave: str,
    panel: str,
    first_unmastered: str | None,
) -> promotion.EvaluationEvidence:
    key = StageKey(STUDY_ID, stage_id, "r0")
    manifest = _record(
        {},
        record_sha="b" * 64,
        relative=f"studies/x/stages/{stage_id}/manifest.json",
    )
    receipt = _record(
        {
            "checkpoint": {
                key: CHECKPOINT[key]
                for key in (
                    "name",
                    "batch",
                    "epoch",
                    "final",
                    "state_path",
                    "sampler_path",
                )
            },
            "checkpoint_inventory": {
                "count": 1,
                "entries": [CHECKPOINT],
                "logical_sha256": CHECKPOINT_INVENTORY_SHA256,
            },
        },
        record_sha="c" * 64,
        relative=f"studies/x/stages/{stage_id}/waves/{wave}/receipt.json",
    )
    return promotion.EvaluationEvidence(
        key=key,
        wave=wave,
        checkpoint_name="final",
        checkpoint=CHECKPOINT,
        checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
        panel=panel,
        report={},
        report_payload=_level_report(first_unmastered),
        report_record_sha256="d" * 64,
        report_payload_sha256="e" * 64,
        report_relative_path=(
            f"studies/x/stages/{stage_id}/evaluations/{wave}/final/{panel}/report.json"
        ),
        evaluation_manifest_payload_sha256="f" * 64,
        evaluation_manifest_record_sha256="a" * 64,
        evaluation_manifest_relative_path=(
            f"studies/x/stages/{stage_id}/evaluations/{wave}/final/{panel}/manifest.json"
        ),
        training_manifest=manifest,
        training_receipt=receipt,
    )


def _git_transition_history(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "--initial-branch=main"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for key, value in (
        ("user.name", "PixCell test"),
        ("user.email", "pixcell-test@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=repo,
            check=True,
        )
    (repo / "bridge.txt").write_text("producer\n", encoding="utf-8")
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "producer"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    producer = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
    ).strip()
    (repo / "bridge.txt").write_text("consumer\n", encoding="utf-8")
    subprocess.run(["git", "add", "--all"], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "consumer"],
        cwd=repo,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    consumer = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
    ).strip()
    return repo, producer, consumer


def _cross_source_evidence(
    protocol: dict,
    *,
    producer_source_git_sha: str,
) -> promotion.EvaluationEvidence:
    base = _evidence(
        stage_id="qwen-l0-sft",
        wave="complete",
        panel=promotion.PANEL_DEPTH_VALIDATION,
        first_unmastered="L1",
    )
    model = dict(protocol["models"]["qwen"])
    prompt_assets = prompt_asset_hashes()
    dataset = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "split": "depth/validation",
        "logical_release_sha256": protocol["dataset"]["logical_release_sha256"],
        "freeze_file_sha256": "1" * 64,
        "parquet_shards": {"depth.parquet": "2" * 64},
    }
    sandbox = {
        "runtime_path": "/usr/bin/docker",
        "daemon_endpoint": "unix:///var/run/docker.sock",
        "image_ref": "pixcell-evaluator@sha256:" + "3" * 64,
        "image_id": "sha256:" + "3" * 64,
        "workspace_root": "/tmp/pixcell-evaluation",
    }
    manifest = _record(
        {
            "source_git_sha": producer_source_git_sha,
            "protocol_logical_sha256": protocol["logical_sha256"],
            "protocol_file_sha256": "4" * 64,
            "contract_version": protocol["contract_version"],
            "prompt_assets": prompt_assets,
            "dataset": {key: value for key, value in dataset.items() if key != "split"},
            "model": model,
            "sandbox": None,
        },
        record_sha="8" * 64,
        relative=(
            "studies/representation-training-v1/stages/qwen-l0-sft/runs/r0/run_manifest.json"
        ),
    )
    receipt = replace(
        base.training_receipt,
        payload={
            **base.training_receipt.payload,
            "stage_id": "qwen-l0-sft",
            "wave": "complete",
            "run_manifest_record_sha256": manifest.record_sha256,
        },
        record_sha256="9" * 64,
    )
    sampler = {
        "model": model["model"],
        "renderer": model["renderer"],
        "effort": model.get("effort"),
    }
    report_payload = {
        **base.report_payload,
        "provenance": {
            "source_git_sha": producer_source_git_sha,
            "protocol": {
                "logical_sha256": protocol["logical_sha256"],
                "file_sha256": "4" * 64,
                "contract_version": protocol["contract_version"],
            },
            "prompt_assets": prompt_assets,
            "dataset": dataset,
            "task_panel": {
                "panel": promotion.PANEL_DEPTH_VALIDATION,
                "task_count": 1_092,
                "logical_sha256": "5" * 64,
            },
            "sampler": sampler,
            "sampling": {
                "attempts_per_task": 1,
                "max_output_tokens": 60_000,
                "temperature": 1.0,
                "top_p": 1.0,
                "max_image_long_edge": 1_920,
            },
            "sandbox": sandbox,
            "evaluation_manifest_record_sha256": "a" * 64,
        },
    }
    return replace(
        base,
        training_manifest=manifest,
        training_receipt=receipt,
        report_payload=report_payload,
        evaluation_manifest_payload_sha256="b" * 64,
        evaluation_manifest_record_sha256="a" * 64,
    )


def _historical_parent_records(
    tmp_path: Path,
    protocol: dict,
    *,
    producer_source_git_sha: str,
) -> tuple[
    TrainingRecord,
    TrainingRecord,
    TrainingRecord,
    dict,
    dict,
    object,
]:
    dataset = promotion._dataset_binding(REPO_ROOT / "dataset", protocol)
    parent_stage = stage_spec(protocol, "qwen-l0-sft")
    stage_payload = {
        "stage_id": parent_stage.stage_id,
        "kind": parent_stage.kind,
        "model_key": parent_stage.model_key,
        "recipe_key": parent_stage.recipe_key,
        "hypotheses": list(parent_stage.hypotheses),
        "parent_policy": parent_stage.parent,
        "levels": list(parent_stage.levels),
        "current_level": parent_stage.current_level,
        "replay_levels": list(parent_stage.replay_levels),
        "waves": parent_stage.waves,
    }
    manifest = _record(
        {
            "source_git_sha": producer_source_git_sha,
            "protocol_logical_sha256": "0" * 64,
            "protocol_file_sha256": "1" * 64,
            "contract_version": protocol["contract_version"],
            "prompt_assets": prompt_asset_hashes(),
            "dataset": dataset,
            "model": protocol["models"]["qwen"],
            "recipe": protocol["recipes"]["qwen_sft"],
            "stage": stage_payload,
        },
        record_sha="2" * 64,
        relative=(
            "studies/representation-training-v1/stages/"
            "qwen-l0-sft/runs/r0/run_manifest.json"
        ),
    )
    checkpoint = {
        **CHECKPOINT,
        "batch": 0,
        "epoch": 1,
    }
    inventory_sha = canonical_sha256([checkpoint])
    log_path = tmp_path / "tinker"
    log_path.mkdir(parents=True)
    local_artifacts = {}
    for name, content in (
        ("checkpoints.jsonl", "{}\n"),
        ("metrics.jsonl", "{}\n"),
    ):
        path = log_path / name
        path.write_text(content, encoding="utf-8")
        local_artifacts[name] = promotion.file_sha256(path)
    invocation = _record(
        {
            "source_git_sha": producer_source_git_sha,
            "run_manifest_record_sha256": manifest.record_sha256,
        },
        record_sha="3" * 64,
        relative=(
            "studies/representation-training-v1/stages/qwen-l0-sft/"
            "runs/r0/invocations/complete-unit/start.json"
        ),
    )
    receipt = _record(
        {
            "stage_id": "qwen-l0-sft",
            "wave": "complete",
            "run_manifest_record_sha256": manifest.record_sha256,
            "invocation_id": "complete-unit",
            "invocation_record_sha256": invocation.record_sha256,
            "checkpoint": {
                field: checkpoint[field]
                for field in (
                    "name",
                    "batch",
                    "epoch",
                    "final",
                    "state_path",
                    "sampler_path",
                )
            },
            "checkpoint_inventory": {
                "count": 1,
                "entries": [checkpoint],
                "logical_sha256": inventory_sha,
            },
            "local_artifact_sha256": local_artifacts,
        },
        record_sha="4" * 64,
        relative=(
            "studies/representation-training-v1/stages/qwen-l0-sft/"
            "runs/r0/waves/complete/receipt.json"
        ),
    )

    class ParentStore:
        @staticmethod
        def load_manifest(_key):
            return manifest

        @staticmethod
        def load_wave_receipt(_key, *, wave):
            assert wave == "complete"
            return receipt

        @staticmethod
        def load_invocation(_key, *, invocation_id):
            assert invocation_id == "complete-unit"
            return invocation

        @staticmethod
        def tinker_log_path(_key):
            return log_path

    return manifest, receipt, invocation, checkpoint, local_artifacts, ParentStore()


def _synthetic_depth_report(
    protocol: dict,
) -> tuple[
    list[promotion.PanelTaskIdentity],
    dict,
    dict,
    TrainingRecord,
    TrainingRecord,
]:
    tasks = [
        promotion.PanelTaskIdentity(
            task_id=f"task-{index:04d}",
            level=f"L{index % 5}",
            representation_id=f"rep-{index % 546:03d}",
            image_sha256=f"{index % 16:x}" * 64,
            target_image_sha256=f"{(index + 1) % 16:x}" * 64,
            footprint_um=(20.0 + index / 1_000, 10.0),
        )
        for index in range(1_092)
    ]
    records = [
        {
            "task_id": task.task_id,
            "level": task.level,
            "representation_id": task.representation_id,
            "status": "ok",
            "pure_executable": True,
            "raw_absolute_scale_iou": 0.85,
            "completion_tokens": 1_000,
            "stop_reason": "stop",
            "cap_hit": False,
            "channel_parse_complete": True,
            "answer_text_sha256": "1" * 64,
            "render_sha256": "2" * 64,
            "sample_record_sha256": "3" * 64,
            "evaluation_record_sha256": "4" * 64,
        }
        for task in tasks
    ]
    by_level: dict[str, list[dict]] = {}
    by_representation: dict[str, list[dict]] = {}
    for record in records:
        by_level.setdefault(record["level"], []).append(record)
        by_representation.setdefault(record["representation_id"], []).append(record)
    representations = {
        key: promotion._aggregate(values) for key, values in sorted(by_representation.items())
    }
    task_panel = {
        "schema_version": "pixcell-training-evaluation-task-panel-v1",
        "selection_seed": None,
        **promotion._panel_manifest(
            tasks,
            panel=promotion.PANEL_DEPTH_VALIDATION,
        ),
    }
    dataset_manifest = promotion._dataset_binding(REPO_ROOT / "dataset", protocol)
    dataset_report = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "split": "depth/validation",
        "logical_release_sha256": dataset_manifest["logical_release_sha256"],
        "freeze_file_sha256": dataset_manifest["freeze_file_sha256"],
        "parquet_shards": dataset_manifest["parquet_shards"],
    }
    sandbox = {
        "runtime_path": "/usr/bin/docker",
        "daemon_endpoint": "unix:///var/run/docker.sock",
        "image_ref": "pixcell-evaluator@sha256:" + "7" * 64,
        "image_id": "sha256:" + "7" * 64,
        "workspace_root": "/tmp/workspace",
    }
    manifest = _record(
        {
            "source_git_sha": SOURCE_SHA,
            "protocol_logical_sha256": protocol["logical_sha256"],
            "dataset": dataset_manifest,
        },
        record_sha="8" * 64,
        relative="studies/x/stages/qwen-mixed-sft/runs/r0/run_manifest.json",
    )
    receipt = _record(
        {
            "stage_id": "qwen-mixed-sft",
            "wave": "complete",
            "run_manifest_record_sha256": manifest.record_sha256,
            "checkpoint": {
                "name": "final",
                "batch": 55,
                "epoch": 1,
                "final": True,
                "state_path": CHECKPOINT["state_path"],
                "sampler_path": "tinker://unit/sampler_weights/final",
            },
            "checkpoint_inventory": {
                "count": 1,
                "entries": [CHECKPOINT],
                "logical_sha256": CHECKPOINT_INVENTORY_SHA256,
            },
        },
        record_sha="9" * 64,
        relative=("studies/x/stages/qwen-mixed-sft/runs/r0/waves/complete/receipt.json"),
    )
    model = protocol["models"]["qwen"]
    sampler = {
        "model": model["model"],
        "renderer": model["renderer"],
        "effort": model.get("effort"),
        "sampler_path": receipt.payload["checkpoint"]["sampler_path"],
        "checkpoint_name": "final",
        "checkpoint": CHECKPOINT,
        "checkpoint_inventory_sha256": CHECKPOINT_INVENTORY_SHA256,
        "training_run_manifest_record_sha256": manifest.record_sha256,
        "training_wave_receipt_record_sha256": receipt.record_sha256,
        "training_wave_receipt_relative_path": str(receipt.relative_path),
    }
    sampling = {
        "attempts_per_task": 1,
        "max_output_tokens": 60_000,
        "temperature": 1.0,
        "top_p": 1.0,
        "max_image_long_edge": 1_920,
        "seed_algorithm": "sha256-bound deterministic 31-bit seed",
    }
    evaluation_manifest = {
        "record_sha256": "a" * 64,
        "payload": {
            "study_id": STUDY_ID,
            "stage_id": "qwen-mixed-sft",
            "wave": "complete",
            "checkpoint_name": "final",
            "replicate_id": "r0",
            "panel": promotion.PANEL_DEPTH_VALIDATION,
            "source_git_sha": SOURCE_SHA,
            "protocol_logical_sha256": protocol["logical_sha256"],
            "protocol_file_sha256": file_sha256(protocol_path(REPO_ROOT)),
            "contract_version": protocol["contract_version"],
            "task_panel": task_panel,
            "prompt_assets": prompt_asset_hashes(),
            "dataset": dataset_manifest,
            "sampler": {
                key: sampler[key]
                for key in (
                    "sampler_path",
                    "checkpoint_name",
                    "checkpoint",
                    "checkpoint_inventory_sha256",
                    "training_run_manifest_record_sha256",
                    "training_wave_receipt_record_sha256",
                )
            },
            "model": model,
            "sampling": {
                **sampling,
                "sample_concurrency": 8,
                "evaluation_batch_size": 32,
                "evaluator_workers": 8,
            },
            "sandbox": sandbox,
        },
    }
    report = {
        "schema_version": "pixcell-training-checkpoint-evaluation-v1",
        "study_id": STUDY_ID,
        "stage_id": "qwen-mixed-sft",
        "wave": "complete",
        "checkpoint_name": "final",
        "replicate_id": "r0",
        "panel": promotion.PANEL_DEPTH_VALIDATION,
        "summary": promotion._aggregate(records),
        "representation_macro_mean_iou": (
            sum(value["mean_raw_absolute_scale_iou"] for value in representations.values())
            / len(representations)
        ),
        "levels": {key: promotion._aggregate(values) for key, values in sorted(by_level.items())},
        "representations": representations,
        "records": records,
        "provenance": {
            "source_git_sha": SOURCE_SHA,
            "protocol": {
                "logical_sha256": protocol["logical_sha256"],
                "file_sha256": file_sha256(protocol_path(REPO_ROOT)),
                "contract_version": protocol["contract_version"],
            },
            "dataset": dataset_report,
            "task_panel": task_panel,
            "sampler": sampler,
            "sampling": sampling,
            "prompt_assets": prompt_asset_hashes(),
            "sandbox": sandbox,
            "evaluation_manifest_record_sha256": evaluation_manifest["record_sha256"],
        },
    }
    return tasks, report, evaluation_manifest, manifest, receipt


def test_first_unmastered_is_ordered_and_rejects_nonfinite() -> None:
    assert promotion.first_unmastered_level(_level_report("L2")) == "L2"
    assert promotion.first_unmastered_level(_level_report(None)) is None
    invalid = _level_report("L2")
    invalid["levels"]["L1"]["mean_raw_absolute_scale_iou"] = float("nan")
    with pytest.raises(promotion.PromotionError, match="finite"):
        promotion.first_unmastered_level(invalid)


def test_mixed_checkpoint_ranking_uses_iou_then_purity_then_progress() -> None:
    candidates = [
        {
            "checkpoint_name": "000014",
            "representation_macro_mean_iou": 0.80,
            "pure_executable_rate": 0.99,
            "training_progress_fraction": 0.25,
        },
        {
            "checkpoint_name": "000028",
            "representation_macro_mean_iou": 0.81,
            "pure_executable_rate": 0.90,
            "training_progress_fraction": 0.50,
        },
        {
            "checkpoint_name": "000042",
            "representation_macro_mean_iou": 0.81,
            "pure_executable_rate": 0.95,
            "training_progress_fraction": 0.75,
        },
        {
            "checkpoint_name": "final",
            "representation_macro_mean_iou": 0.81,
            "pure_executable_rate": 0.95,
            "training_progress_fraction": 1.0,
        },
    ]
    assert promotion._best_mixed_checkpoint(candidates)["checkpoint_name"] == "final"


def test_mixed_selection_requires_every_report_and_rejects_nonwinner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pytest.importorskip("chz", reason="Tinker is an optional RL dependency")
    pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
    pytest.importorskip(
        "tinker_cookbook",
        reason="Tinker Cookbook is an optional RL dependency",
    )
    from rl.studies.representation_training_v1 import evaluation

    periodic = {
        "name": "000014",
        "batch": 14,
        "epoch": 0,
        "final": False,
        "state_path": "tinker://unit/weights/000014",
        "sampler_path": "tinker://unit/sampler_weights/000014",
        "role": "periodic",
        "training_progress_fraction": 0.25,
    }
    entries = [periodic, CHECKPOINT]
    inventory_sha = canonical_sha256(entries)
    receipt = _record(
        {
            "checkpoint": {
                key: CHECKPOINT[key]
                for key in (
                    "name",
                    "batch",
                    "epoch",
                    "final",
                    "state_path",
                    "sampler_path",
                )
            },
            "checkpoint_inventory": {
                "count": 2,
                "entries": entries,
                "logical_sha256": inventory_sha,
            },
        },
        record_sha="c" * 64,
        relative=("studies/x/stages/qwen-mixed-sft/waves/complete/receipt.json"),
    )

    def scored(
        checkpoint: dict,
        *,
        iou: float,
        pure: float,
        report_sha: str,
    ) -> promotion.EvaluationEvidence:
        base = _evidence(
            stage_id="qwen-mixed-sft",
            wave="complete",
            panel=promotion.PANEL_DEPTH_VALIDATION,
            first_unmastered="L2",
        )
        payload = {
            **base.report_payload,
            "representation_macro_mean_iou": iou,
            "summary": {"pure_executable_rate": pure},
        }
        return replace(
            base,
            checkpoint_name=checkpoint["name"],
            checkpoint=checkpoint,
            checkpoint_inventory_sha256=inventory_sha,
            report_payload=payload,
            report_record_sha256=report_sha,
            training_receipt=receipt,
        )

    selected = scored(
        CHECKPOINT,
        iou=0.80,
        pure=0.99,
        report_sha="d" * 64,
    )
    periodic_report = scored(
        periodic,
        iou=0.90,
        pure=0.90,
        report_sha="f" * 64,
    )

    class FakeReportStore:
        def __init__(self, **kwargs) -> None:
            self.checkpoint_name = kwargs["checkpoint_name"]

        def load_report(self) -> dict | None:
            if self.checkpoint_name == periodic["name"]:
                return {"record_sha256": periodic_report.report_record_sha256}
            return None

    monkeypatch.setattr(
        evaluation,
        "CheckpointEvaluationStore",
        FakeReportStore,
    )
    monkeypatch.setattr(
        promotion,
        "validate_checkpoint_report",
        lambda **_kwargs: periodic_report,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    store = TrainingStore(
        repo_root=repo,
        external_root=tmp_path / "external",
    )
    with pytest.raises(promotion.PromotionError, match="deterministic best"):
        promotion._mixed_checkpoint_selection(
            repo_root=repo,
            protocol=load_protocol(REPO_ROOT),
            store=store,
            selected=selected,
            expected_source_sha=SOURCE_SHA,
        )

    monkeypatch.setattr(
        FakeReportStore,
        "load_report",
        lambda _self: None,
    )
    with pytest.raises(promotion.PromotionError, match="complete depth-validation"):
        promotion._mixed_checkpoint_selection(
            repo_root=repo,
            protocol=load_protocol(REPO_ROOT),
            store=store,
            selected=selected,
            expected_source_sha=SOURCE_SHA,
        )


def test_plans_bind_reports_and_clean_smoke_storage() -> None:
    protocol = load_protocol(REPO_ROOT)
    mixed = promotion.approval_plan(
        stage_spec(protocol, "qwen-mixed-rl-l2"),
        "smoke",
    )
    assert mixed.expected_panel == promotion.PANEL_DEPTH_VALIDATION
    assert mixed.allowed_evaluation_checkpoints == (
        ("qwen-mixed-sft", "complete"),
        ("qwen-mixed-rl-l0", "complete"),
        ("qwen-mixed-rl-l1", "complete"),
    )
    continuation = promotion.approval_plan(
        stage_spec(protocol, "qwen-mixed-rl-l2"),
        "step-5",
    )
    assert continuation.storage_wave == "step-5"
    assert continuation.expected_panel == promotion.PANEL_PROGRESS


def test_pure_base_level_transition_binds_prior_and_current_slot6_panels() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-base-rl-l2")
    plan = promotion.approval_plan(stage, "smoke")
    assert plan.gate == (
        "prior-and-current-level-held-out-transition-receipt"
    )
    assert plan.expected_panel == "level-progress-l1"
    assert plan.entry_baseline_panel == "level-progress-l2"
    assert plan.allowed_evaluation_checkpoints == (
        ("qwen-base-rl-l1", "complete"),
    )

    prior = _evidence(
        stage_id="qwen-base-rl-l1",
        wave="complete",
        panel="level-progress-l1",
        first_unmastered=None,
    )
    baseline = replace(
        prior,
        panel="level-progress-l2",
        report_record_sha256="1" * 64,
        report_payload_sha256="2" * 64,
        report_relative_path=(
            "studies/x/stages/qwen-base-rl-l1/evaluations/"
            "complete/final/level-progress-l2/report.json"
        ),
        evaluation_manifest_payload_sha256="3" * 64,
        evaluation_manifest_record_sha256="4" * 64,
        evaluation_manifest_relative_path=(
            "studies/x/stages/qwen-base-rl-l1/evaluations/"
            "complete/final/level-progress-l2/manifest.json"
        ),
    )
    payload = promotion._approval_payload(
        stage=stage,
        wave_name="smoke",
        plan=plan,
        evidence=prior,
        entry_baseline_evidence=baseline,
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    assert payload["evaluation"]["panel"] == "level-progress-l1"
    assert payload["entry_baseline"]["panel"] == "level-progress-l2"
    assert (
        payload["evaluation"]["checkpoint"]
        == payload["entry_baseline"]["checkpoint"]
    )
    assert payload["parent_stage_id"] == "qwen-base-rl-l1"
    assert payload["parent_wave"] == "complete"

    with pytest.raises(promotion.PromotionError, match="requires the .* baseline"):
        promotion._approval_payload(
            stage=stage,
            wave_name="smoke",
            plan=plan,
            evidence=prior,
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    with pytest.raises(promotion.PromotionError, match="exact same parent checkpoint"):
        promotion._approval_payload(
            stage=stage,
            wave_name="smoke",
            plan=plan,
            evidence=prior,
            entry_baseline_evidence=replace(
                baseline,
                checkpoint={**baseline.checkpoint, "sampler_path": "tinker://other"},
            ),
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )
    mismatched_artifact_chains = (
        replace(baseline, checkpoint_inventory_sha256="6" * 64),
        replace(
            baseline,
            training_manifest=replace(
                baseline.training_manifest,
                record_sha256="7" * 64,
            ),
        ),
        replace(
            baseline,
            training_receipt=replace(
                baseline.training_receipt,
                record_sha256="8" * 64,
            ),
        ),
    )
    for mismatched in mismatched_artifact_chains:
        with pytest.raises(
            promotion.PromotionError,
            match="exact same parent checkpoint",
        ):
            promotion._approval_payload(
                stage=stage,
                wave_name="smoke",
                plan=plan,
                evidence=prior,
                entry_baseline_evidence=mismatched,
                source_git_sha=SOURCE_SHA,
                protocol=protocol,
            )


def test_same_source_approval_is_recomputed_from_both_bound_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-base-rl-l2")
    plan = promotion.approval_plan(stage, "smoke")
    prior = _evidence(
        stage_id="qwen-base-rl-l1",
        wave="complete",
        panel=plan.expected_panel,
        first_unmastered=None,
    )
    baseline = replace(
        prior,
        panel=str(plan.entry_baseline_panel),
        report_record_sha256="1" * 64,
        report_payload_sha256="2" * 64,
        report_relative_path=(
            "studies/x/stages/qwen-base-rl-l1/evaluations/"
            "complete/final/level-progress-l2/report.json"
        ),
        evaluation_manifest_payload_sha256="3" * 64,
        evaluation_manifest_record_sha256="4" * 64,
        evaluation_manifest_relative_path=(
            "studies/x/stages/qwen-base-rl-l1/evaluations/"
            "complete/final/level-progress-l2/manifest.json"
        ),
    )
    payload = promotion._approval_payload(
        stage=stage,
        wave_name="smoke",
        plan=plan,
        evidence=prior,
        entry_baseline_evidence=baseline,
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    approval = _record(
        payload,
        record_sha="5" * 64,
        relative=(
            "studies/representation-training-v1/stages/qwen-base-rl-l2/"
            "runs/r0/waves/smoke/approval.json"
        ),
    )
    calls: list[dict] = []

    def validate_report(**kwargs):
        calls.append(dict(kwargs))
        if kwargs["panel"] == plan.expected_panel:
            assert kwargs["expected_report_record_sha256"] == "d" * 64
            return prior
        assert kwargs["panel"] == plan.entry_baseline_panel
        assert kwargs["expected_report_record_sha256"] == "1" * 64
        return baseline

    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(
        promotion,
        "validate_checkpoint_report",
        validate_report,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    store = TrainingStore(repo_root=repo, external_root=tmp_path / "external")
    observed = promotion.validate_same_source_wave_approval(
        repo_root=repo,
        protocol=protocol,
        store=store,
        stage=stage,
        wave_name="smoke",
        replicate_id="r0",
        source_git_sha=SOURCE_SHA,
        approval=approval,
    )
    assert observed is prior
    assert [call["panel"] for call in calls] == [
        "level-progress-l1",
        "level-progress-l2",
    ]

    tampered = replace(
        approval,
        payload={
            **approval.payload,
            "entry_baseline": {
                **approval.payload["entry_baseline"],
                "report_payload_sha256": "9" * 64,
            },
        },
    )
    with pytest.raises(promotion.PromotionError, match="canonically recomputed"):
        promotion.validate_same_source_wave_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage,
            wave_name="smoke",
            replicate_id="r0",
            source_git_sha=SOURCE_SHA,
            approval=tampered,
        )


def test_same_source_current_level_approval_rejects_minimal_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-base-rl-l0")
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    store = TrainingStore(repo_root=repo, external_root=tmp_path / "external")
    approval = _record(
        {
            "schema_version": promotion.APPROVAL_SCHEMA_VERSION,
            "decision": "approve",
            "approval_gate": "current-level-held-out-promotion-receipt",
            "stage_id": stage.stage_id,
            "wave": "step-10",
            "source_git_sha": SOURCE_SHA,
            "protocol_logical_sha256": protocol["logical_sha256"],
        },
        record_sha="6" * 64,
        relative=(
            "studies/representation-training-v1/stages/qwen-base-rl-l0/"
            "runs/r0/waves/step-10/approval.json"
        ),
    )
    with pytest.raises(promotion.PromotionError, match="approval.evaluation"):
        promotion.validate_same_source_wave_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage,
            wave_name="step-10",
            replicate_id="r0",
            source_git_sha=SOURCE_SHA,
            approval=approval,
        )


def test_mixed_approval_selects_first_unmastered_and_binds_parent() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-mixed-rl-l2")
    evidence = _evidence(
        stage_id="qwen-mixed-sft",
        wave="complete",
        panel=promotion.PANEL_DEPTH_VALIDATION,
        first_unmastered="L2",
    )
    payload = promotion._approval_payload(
        stage=stage,
        wave_name="smoke",
        plan=promotion.approval_plan(stage, "smoke"),
        evidence=evidence,
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    assert payload["schema_version"] == promotion.APPROVAL_SCHEMA_VERSION
    assert "evidence_source_git_sha" not in payload
    assert "source_transition" not in payload
    assert payload["decision"] == "approve"
    assert payload["approval_gate"] == "first-unmastered-entry-receipt"
    assert payload["parent_stage_id"] == "qwen-mixed-sft"
    assert payload["parent_wave"] == "complete"
    assert payload["parent_receipt_record_sha256"] == "c" * 64
    assert payload["selected_parent_checkpoint"] == CHECKPOINT
    assert payload["selected_parent_checkpoint_inventory_sha256"] == CHECKPOINT_INVENTORY_SHA256
    assert payload["mastery"]["selected_level"] == "L2"

    wrong = _evidence(
        stage_id="qwen-mixed-sft",
        wave="complete",
        panel=promotion.PANEL_DEPTH_VALIDATION,
        first_unmastered="L1",
    )
    with pytest.raises(promotion.PromotionError, match="first unmastered"):
        promotion._approval_payload(
            stage=stage,
            wave_name="smoke",
            plan=promotion.approval_plan(stage, "smoke"),
            evidence=wrong,
            source_git_sha=SOURCE_SHA,
            protocol=protocol,
        )


def test_clean_smoke_approval_does_not_masquerade_as_parent() -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-mixed-rl-l2")
    evidence = _evidence(
        stage_id=stage.stage_id,
        wave="smoke",
        panel=promotion.PANEL_PROGRESS,
        first_unmastered=None,
    )
    payload = promotion._approval_payload(
        stage=stage,
        wave_name="step-5",
        plan=promotion.approval_plan(stage, "step-5"),
        evidence=evidence,
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    assert "parent_receipt_record_sha256" not in payload
    assert payload["evaluation"]["training_wave_receipt_record_sha256"] == "c" * 64
    assert payload["prior_wave"] == "smoke"
    assert payload["prior_receipt_record_sha256"] == "c" * 64


def test_entry_approval_cannot_authorize_continuation(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    stage = stage_spec(protocol, "qwen-mixed-rl-l2")
    entry = promotion._approval_payload(
        stage=stage,
        wave_name="smoke",
        plan=promotion.approval_plan(stage, "smoke"),
        evidence=_evidence(
            stage_id="qwen-mixed-sft",
            wave="complete",
            panel=promotion.PANEL_DEPTH_VALIDATION,
            first_unmastered="L2",
        ),
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    continuation = promotion._approval_payload(
        stage=stage,
        wave_name="step-5",
        plan=promotion.approval_plan(stage, "step-5"),
        evidence=_evidence(
            stage_id=stage.stage_id,
            wave="smoke",
            panel=promotion.PANEL_PROGRESS,
            first_unmastered=None,
        ),
        source_git_sha=SOURCE_SHA,
        protocol=protocol,
    )
    repo = tmp_path / "repo"
    repo.mkdir()
    store = TrainingStore(
        repo_root=repo,
        external_root=tmp_path / "external",
    )
    key = StageKey(STUDY_ID, stage.stage_id, "r0")
    with store.acquire_stage_lock(key):
        store.write_wave_approval(key, wave="smoke", payload=entry)
        assert store.load_wave_approval(key, wave="step-5") is None
        store.write_wave_approval(
            key,
            wave="step-5",
            payload=continuation,
        )
    assert (
        store.load_wave_approval(key, wave="smoke").payload["approval_gate"]
        == "first-unmastered-entry-receipt"
    )
    assert (
        store.load_wave_approval(key, wave="step-5").payload["approval_gate"]
        == "clean-smoke-receipt"
    )


def test_depth_report_recomputes_all_rows_metrics_and_provenance() -> None:
    protocol = load_protocol(REPO_ROOT)
    tasks, report, evaluation_manifest, manifest, receipt = _synthetic_depth_report(protocol)
    promotion._validate_report_payload(
        repo_root=REPO_ROOT,
        protocol=protocol,
        expected_source_sha=SOURCE_SHA,
        key=StageKey(STUDY_ID, "qwen-mixed-sft", "r0"),
        wave="complete",
        checkpoint_name="final",
        selected_checkpoint=CHECKPOINT,
        checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
        panel=promotion.PANEL_DEPTH_VALIDATION,
        report=report,
        evaluation_manifest=evaluation_manifest,
        training_manifest=manifest,
        training_receipt=receipt,
        expected_tasks=tasks,
    )
    report_dataset = report["provenance"]["dataset"]
    manifest_dataset = evaluation_manifest["payload"]["dataset"]
    manifest_only_fields = {
        "train_rows",
        "validation_rows",
        "reference_artifacts_sha256",
        "reference_artifact_count",
    }
    assert manifest_only_fields.isdisjoint(report_dataset)
    assert manifest_only_fields.issubset(manifest_dataset)

    tampered_manifest = copy.deepcopy(evaluation_manifest)
    tampered_manifest["payload"]["dataset"]["reference_artifact_count"] += 1
    with pytest.raises(
        promotion.PromotionError,
        match="evaluation-manifest dataset differs from the frozen release",
    ):
        promotion._validate_report_payload(
            repo_root=REPO_ROOT,
            protocol=protocol,
            expected_source_sha=SOURCE_SHA,
            key=StageKey(STUDY_ID, "qwen-mixed-sft", "r0"),
            wave="complete",
            checkpoint_name="final",
            selected_checkpoint=CHECKPOINT,
            checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
            panel=promotion.PANEL_DEPTH_VALIDATION,
            report=report,
            evaluation_manifest=tampered_manifest,
            training_manifest=manifest,
            training_receipt=receipt,
            expected_tasks=tasks,
        )

    overfull_report = copy.deepcopy(report)
    overfull_report["provenance"]["dataset"]["reference_artifact_count"] = (
        manifest_dataset["reference_artifact_count"]
    )
    with pytest.raises(
        promotion.PromotionError,
        match="report dataset projection differs",
    ):
        promotion._validate_report_payload(
            repo_root=REPO_ROOT,
            protocol=protocol,
            expected_source_sha=SOURCE_SHA,
            key=StageKey(STUDY_ID, "qwen-mixed-sft", "r0"),
            wave="complete",
            checkpoint_name="final",
            selected_checkpoint=CHECKPOINT,
            checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
            panel=promotion.PANEL_DEPTH_VALIDATION,
            report=overfull_report,
            evaluation_manifest=evaluation_manifest,
            training_manifest=manifest,
            training_receipt=receipt,
            expected_tasks=tasks,
        )

    nonfinite = copy.deepcopy(report)
    nonfinite["summary"]["mean_raw_absolute_scale_iou"] = float("nan")
    with pytest.raises(promotion.PromotionError, match="finite"):
        promotion._validate_report_payload(
            repo_root=REPO_ROOT,
            protocol=protocol,
            expected_source_sha=SOURCE_SHA,
            key=StageKey(STUDY_ID, "qwen-mixed-sft", "r0"),
            wave="complete",
            checkpoint_name="final",
            selected_checkpoint=CHECKPOINT,
            checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
            panel=promotion.PANEL_DEPTH_VALIDATION,
            report=nonfinite,
            evaluation_manifest=evaluation_manifest,
            training_manifest=manifest,
            training_receipt=receipt,
            expected_tasks=tasks,
        )

    with pytest.raises(promotion.PromotionError, match="expected 1092"):
        promotion._validate_report_payload(
            repo_root=REPO_ROOT,
            protocol=protocol,
            expected_source_sha=SOURCE_SHA,
            key=StageKey(STUDY_ID, "qwen-mixed-sft", "r0"),
            wave="complete",
            checkpoint_name="final",
            selected_checkpoint=CHECKPOINT,
            checkpoint_inventory_sha256=CHECKPOINT_INVENTORY_SHA256,
            panel=promotion.PANEL_DEPTH_VALIDATION,
            report=report,
            evaluation_manifest=evaluation_manifest,
            training_manifest=manifest,
            training_receipt=receipt,
            expected_tasks=tasks[:-1],
        )


def test_record_approval_requires_human_confirmation_and_is_immutable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    with pytest.raises(promotion.PromotionError, match="human approval"):
        promotion.record_wave_approval(
            repo_root=tmp_path / "missing",
            external_root=tmp_path / "external",
            stage_id="qwen-mixed-rl-l2",
            wave_name="smoke",
            replicate_id="r0",
            evaluation_stage_id="qwen-mixed-sft",
            evaluation_wave="complete",
            evaluation_checkpoint_name="final",
            evaluation_report_record_sha256="d" * 64,
            expected_source_sha=SOURCE_SHA,
            confirmation="wrong",
        )

    repo = tmp_path / "repo"
    repo.mkdir()
    external = tmp_path / "external"
    protocol = load_protocol(REPO_ROOT)
    evidence = _evidence(
        stage_id="qwen-l0-sft",
        wave="complete",
        panel=promotion.PANEL_DEPTH_VALIDATION,
        first_unmastered="L1",
    )
    monkeypatch.setattr(
        promotion,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(
        promotion,
        "validate_checkpoint_report",
        lambda **_kwargs: evidence,
    )
    kwargs = {
        "repo_root": repo,
        "external_root": external,
        "stage_id": "qwen-sequential-sft-l1",
        "wave_name": "complete",
        "replicate_id": "r0",
        "evaluation_stage_id": "qwen-l0-sft",
        "evaluation_wave": "complete",
        "evaluation_checkpoint_name": "final",
        "evaluation_report_record_sha256": "d" * 64,
        "expected_source_sha": SOURCE_SHA,
        "confirmation": promotion.APPROVAL_CONFIRMATION_TOKEN,
    }
    first = promotion.record_wave_approval(**kwargs)
    second = promotion.record_wave_approval(**kwargs)
    assert first == second
    store = TrainingStore(repo_root=repo, external_root=external)
    approval = store.load_wave_approval(
        StageKey(STUDY_ID, "qwen-sequential-sft-l1", "r0"),
        wave="complete",
    )
    assert approval is not None
    assert approval.payload["decision"] == "approve"
    assert approval.payload["explicit_human_confirmation"] is True


def test_cross_source_v2_binds_exact_evidence_scope_and_one_child(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, producer, consumer = _git_transition_history(tmp_path)
    external = tmp_path / "external"
    protocol = load_protocol(REPO_ROOT)
    evidence = _cross_source_evidence(
        protocol,
        producer_source_git_sha=producer,
    )
    monkeypatch.setattr(
        promotion,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(
        promotion,
        "file_sha256",
        lambda _path: "4" * 64,
    )
    report_calls: list[dict] = []

    def validate_report(**kwargs):
        report_calls.append(dict(kwargs))
        assert kwargs["expected_source_sha"] == producer
        return evidence

    monkeypatch.setattr(
        promotion,
        "validate_checkpoint_report",
        validate_report,
    )
    result = promotion.record_wave_approval(
        repo_root=repo,
        external_root=external,
        stage_id="qwen-sequential-sft-l1",
        wave_name="complete",
        replicate_id="r0",
        evaluation_stage_id="qwen-l0-sft",
        evaluation_wave="complete",
        evaluation_checkpoint_name="final",
        evaluation_report_record_sha256=evidence.report_record_sha256,
        expected_source_sha=consumer,
        evidence_source_sha=producer,
        approved_change_paths=["bridge.txt"],
        confirmation=promotion.APPROVAL_CONFIRMATION_TOKEN,
    )
    assert result["approval_schema_version"] == (
        promotion.SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION
    )
    assert result["evidence_source_git_sha"] == producer
    assert result["consumer_source_git_sha"] == consumer

    key = StageKey(STUDY_ID, "qwen-sequential-sft-l1", "r0")
    store = TrainingStore(repo_root=repo, external_root=external)
    approval = store.load_wave_approval(key, wave="complete")
    assert approval is not None
    payload = approval.payload
    assert payload["schema_version"] == (promotion.SOURCE_TRANSITION_APPROVAL_SCHEMA_VERSION)
    assert payload["evaluation"]["report_record_sha256"] == (evidence.report_record_sha256)
    assert payload["evaluation"]["training_run_manifest_record_sha256"] == (
        evidence.training_manifest.record_sha256
    )
    assert payload["evaluation"]["training_wave_receipt_record_sha256"] == (
        evidence.training_receipt.record_sha256
    )
    assert payload["evaluation"]["evaluation_manifest_record_sha256"] == (
        evidence.evaluation_manifest_record_sha256
    )
    transition = payload["source_transition"]
    assert transition["scope"]["child"] == {
        "stage_id": "qwen-sequential-sft-l1",
        "wave": "complete",
        "replicate_id": "r0",
        "approval_gate": "parent-evaluation-receipt",
    }
    assert transition["scope"]["approved_changes"]["paths"] == ["bridge.txt"]
    assert (
        transition["evidence"]["checkpoint_inventory"]
        == (evidence.training_receipt.payload["checkpoint_inventory"])
    )
    assert transition["evidence"]["evaluation_manifest"]["record_sha256"] == (
        evidence.evaluation_manifest_record_sha256
    )
    assert transition["equivalence"]["model"]["producer_training"] == (protocol["models"]["qwen"])
    assert transition["equivalence"]["renderer"]["producer_evaluation"] == {
        "model": protocol["models"]["qwen"]["model"],
        "renderer": protocol["models"]["qwen"]["renderer"],
        "effort": protocol["models"]["qwen"].get("effort"),
    }
    assert (
        promotion.validate_source_transition_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage_spec(protocol, "qwen-sequential-sft-l1"),
            wave_name="complete",
            replicate_id="r0",
            consumer_source_git_sha=consumer,
            approval=approval,
        )
        == evidence
    )
    with pytest.raises(promotion.PromotionError, match="another replicate"):
        promotion.validate_source_transition_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage_spec(protocol, "qwen-sequential-sft-l1"),
            wave_name="complete",
            replicate_id="r1",
            consumer_source_git_sha=consumer,
            approval=approval,
        )

    tampered_payload = copy.deepcopy(payload)
    tampered_payload["source_transition"]["evidence"]["evaluation_report"]["record_sha256"] = (
        "0" * 64
    )
    tampered = replace(approval, payload=tampered_payload)
    with pytest.raises(promotion.PromotionError, match="recomputed evidence"):
        promotion.validate_source_transition_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage_spec(protocol, "qwen-sequential-sft-l1"),
            wave_name="complete",
            replicate_id="r0",
            consumer_source_git_sha=consumer,
            approval=tampered,
        )
    assert all(call["expected_source_sha"] == producer for call in report_calls)
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("paid training requires a completely clean worktree")
        ),
    )
    with pytest.raises(promotion.PromotionError, match="clean HEAD"):
        promotion.validate_source_transition_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage_spec(protocol, "qwen-sequential-sft-l1"),
            wave_name="complete",
            replicate_id="r0",
            consumer_source_git_sha=consumer,
            approval=approval,
        )


def test_cross_source_recording_rejects_missing_or_wrong_change_scope(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo, producer, consumer = _git_transition_history(tmp_path)
    protocol = load_protocol(REPO_ROOT)
    monkeypatch.setattr(
        promotion,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    common = {
        "repo_root": repo,
        "external_root": tmp_path / "external",
        "stage_id": "qwen-sequential-sft-l1",
        "wave_name": "complete",
        "replicate_id": "r0",
        "evaluation_stage_id": "qwen-l0-sft",
        "evaluation_wave": "complete",
        "evaluation_checkpoint_name": "final",
        "evaluation_report_record_sha256": "d" * 64,
        "expected_source_sha": consumer,
        "evidence_source_sha": producer,
        "confirmation": promotion.APPROVAL_CONFIRMATION_TOKEN,
    }
    with pytest.raises(promotion.PromotionError, match="explicit approved"):
        promotion.record_wave_approval(**common)
    with pytest.raises(
        promotion.PromotionError,
        match="approved change paths",
    ):
        promotion.record_wave_approval(
            **common,
            approved_change_paths=["wrong.txt"],
        )
    with pytest.raises(
        promotion.PromotionError,
        match="same-source v1",
    ):
        promotion.record_wave_approval(
            **{
                **common,
                "evidence_source_sha": consumer,
            },
            approved_change_paths=["bridge.txt"],
        )


def test_historical_parent_evidence_binds_receipt_without_evaluation(
    tmp_path: Path,
) -> None:
    protocol = load_protocol(REPO_ROOT)
    producer = "b" * 40
    manifest, receipt, invocation, checkpoint, artifacts, store = (
        _historical_parent_records(
            tmp_path,
            protocol,
            producer_source_git_sha=producer,
        )
    )
    observed = promotion._parent_receipt_transition_evidence(
        repo_root=REPO_ROOT,
        protocol=protocol,
        store=store,
        replicate_id="r0",
    )
    assert observed[:4] == (manifest, receipt, invocation, checkpoint)
    document = observed[4]
    assert "evaluation" not in document["evidence"]
    assert document["evidence"]["local_artifact_sha256"] == artifacts
    assert (
        document["stable_equivalence"]["prompt_assets"]
        == prompt_asset_hashes()
    )

    manifest.payload["prompt_assets"] = {
        **prompt_asset_hashes(),
        "task_sha256": "f" * 64,
    }
    with pytest.raises(promotion.PromotionError, match="stable contract"):
        promotion._parent_receipt_transition_evidence(
            repo_root=REPO_ROOT,
            protocol=protocol,
            store=store,
            replicate_id="r0",
        )


def test_parent_receipt_transition_records_and_revalidates_exact_bridge(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo, producer, consumer = _git_transition_history(tmp_path)
    protocol = load_protocol(REPO_ROOT)
    manifest, receipt, invocation, checkpoint, _artifacts, _store = (
        _historical_parent_records(
            tmp_path / "parent",
            protocol,
            producer_source_git_sha=producer,
        )
    )
    stable = {
        "stable_equivalence": {
            "contract_version": protocol["contract_version"],
            "prompt_assets": prompt_asset_hashes(),
            "dataset": promotion._dataset_binding(REPO_ROOT / "dataset", protocol),
            "model": protocol["models"]["qwen"],
            "recipe": protocol["recipes"]["qwen_sft"],
            "stage": dict(manifest.payload["stage"]),
        },
        "evidence": {
            "parent_run_manifest": {"record_sha256": manifest.record_sha256},
            "parent_wave_receipt": {"record_sha256": receipt.record_sha256},
            "parent_invocation": {"record_sha256": invocation.record_sha256},
            "checkpoint_inventory": receipt.payload["checkpoint_inventory"],
            "selected_checkpoint": checkpoint,
        },
    }
    monkeypatch.setattr(
        promotion,
        "load_protocol",
        lambda *_args, **_kwargs: protocol,
    )
    monkeypatch.setattr(
        promotion,
        "validate_source_sha",
        lambda _root, expected: expected,
    )
    monkeypatch.setattr(promotion, "file_sha256", lambda _path: "5" * 64)
    monkeypatch.setattr(
        promotion,
        "_parent_receipt_transition_evidence",
        lambda **_kwargs: (
            manifest,
            receipt,
            invocation,
            checkpoint,
            stable,
        ),
    )
    external = tmp_path / "external"
    with pytest.raises(promotion.PromotionError, match="human approval"):
        promotion.record_parent_receipt_transition_approval(
            repo_root=repo,
            external_root=external,
            stage_id="qwen-l0-rl-l1",
            wave_name="smoke",
            replicate_id="r0",
            expected_source_sha=consumer,
            approved_change_paths=["bridge.txt"],
            confirmation="wrong",
        )
    result = promotion.record_parent_receipt_transition_approval(
        repo_root=repo,
        external_root=external,
        stage_id="qwen-l0-rl-l1",
        wave_name="smoke",
        replicate_id="r0",
        expected_source_sha=consumer,
        approved_change_paths=["bridge.txt"],
        confirmation=promotion.APPROVAL_CONFIRMATION_TOKEN,
    )
    assert result["parent_receipt_record_sha256"] == receipt.record_sha256
    store = TrainingStore(repo_root=repo, external_root=external)
    key = StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0")
    approval = store.load_wave_approval(key, wave="smoke")
    assert approval is not None
    assert approval.payload["schema_version"] == (
        promotion.PARENT_RECEIPT_TRANSITION_APPROVAL_SCHEMA_VERSION
    )
    assert approval.payload["selected_parent_checkpoint"] == checkpoint
    assert "evaluation" not in approval.payload
    promotion.validate_parent_receipt_transition_approval(
        repo_root=repo,
        protocol=protocol,
        store=store,
        stage=stage_spec(protocol, "qwen-l0-rl-l1"),
        wave_name="smoke",
        replicate_id="r0",
        consumer_source_git_sha=consumer,
        approval=approval,
    )

    tampered = replace(
        approval,
        payload={
            **approval.payload,
            "parent_receipt_record_sha256": "0" * 64,
        },
    )
    with pytest.raises(promotion.PromotionError, match="recomputed evidence"):
        promotion.validate_parent_receipt_transition_approval(
            repo_root=repo,
            protocol=protocol,
            store=store,
            stage=stage_spec(protocol, "qwen-l0-rl-l1"),
            wave_name="smoke",
            replicate_id="r0",
            consumer_source_git_sha=consumer,
            approval=tampered,
        )
