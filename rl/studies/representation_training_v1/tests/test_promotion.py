from __future__ import annotations

import copy
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
CHECKPOINT_INVENTORY_SHA256 = canonical_sha256([CHECKPOINT])


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
        mastered = (
            first_unmastered is None
            or int(level[1:]) < int(first_unmastered[1:])
        )
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
            f"studies/x/stages/{stage_id}/evaluations/"
            f"{wave}/final/{panel}/report.json"
        ),
        training_manifest=manifest,
        training_receipt=receipt,
    )


def _synthetic_depth_report(protocol: dict) -> tuple[
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
        by_representation.setdefault(record["representation_id"], []).append(
            record
        )
    representations = {
        key: promotion._aggregate(values)
        for key, values in sorted(by_representation.items())
    }
    task_panel = {
        "schema_version": "pixcell-training-evaluation-task-panel-v1",
        "selection_seed": None,
        **promotion._panel_manifest(
            tasks,
            panel=promotion.PANEL_DEPTH_VALIDATION,
        ),
    }
    dataset_manifest = {
        "repo_id": protocol["dataset"]["repo_id"],
        "revision": protocol["dataset"]["revision"],
        "configuration": protocol["dataset"]["configuration"],
        "logical_release_sha256": protocol["dataset"][
            "logical_release_sha256"
        ],
        "freeze_file_sha256": "5" * 64,
        "parquet_shards": [{"path": "depth.parquet", "sha256": "6" * 64}],
    }
    dataset_report = {**dataset_manifest, "split": "depth/validation"}
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
            "dataset": {
                "logical_release_sha256": protocol["dataset"][
                    "logical_release_sha256"
                ]
            },
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
        relative=(
            "studies/x/stages/qwen-mixed-sft/runs/r0/"
            "waves/complete/receipt.json"
        ),
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
            sum(
                value["mean_raw_absolute_scale_iou"]
                for value in representations.values()
            )
            / len(representations)
        ),
        "levels": {
            key: promotion._aggregate(values)
            for key, values in sorted(by_level.items())
        },
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
            "evaluation_manifest_record_sha256": evaluation_manifest[
                "record_sha256"
            ],
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
    assert (
        promotion._best_mixed_checkpoint(candidates)["checkpoint_name"]
        == "final"
    )


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
        relative=(
            "studies/x/stages/qwen-mixed-sft/waves/complete/receipt.json"
        ),
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
    assert payload["decision"] == "approve"
    assert payload["approval_gate"] == "first-unmastered-entry-receipt"
    assert payload["parent_stage_id"] == "qwen-mixed-sft"
    assert payload["parent_wave"] == "complete"
    assert payload["parent_receipt_record_sha256"] == "c" * 64
    assert payload["selected_parent_checkpoint"] == CHECKPOINT
    assert (
        payload["selected_parent_checkpoint_inventory_sha256"]
        == CHECKPOINT_INVENTORY_SHA256
    )
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
    tasks, report, evaluation_manifest, manifest, receipt = (
        _synthetic_depth_report(protocol)
    )
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
        "stage_id": "qwen-l0-rl-l1",
        "wave_name": "smoke",
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
        StageKey(STUDY_ID, "qwen-l0-rl-l1", "r0"),
        wave="smoke",
    )
    assert approval is not None
    assert approval.payload["decision"] == "approve"
    assert approval.payload["explicit_human_confirmation"] is True
