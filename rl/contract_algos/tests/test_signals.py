from __future__ import annotations

from types import SimpleNamespace

import pytest

from rl.common.baselines import TaskBaseline
from rl.common.evaluator import Attribution, EvaluationResult, EvaluationStatus
from rl.contract_algos.audit import MeasurementFault, measurement_record, score_signals, summarize
from rl.contract_algos.splits import partition_rows


def task(task_id, group, image, target):
    return SimpleNamespace(
        sampler=SimpleNamespace(opaque_id=task_id, leakage_group_id=group, level="L1", split_role="train", representation_id=group),
        observation=SimpleNamespace(image_sha256=image),
        reference=SimpleNamespace(target_image_sha256=target),
        label="code",
    )


def test_grouping_is_order_independent_and_links_duplicate_rasters_transitively():
    tasks = [
        task("1", "a", "image1", "target1"),
        task("2", "a", "image2", "target2"),
        task("3", "b", "image2", "target3"),
        task("4", "c", "image4", "target3"),
        task("5", "d", "image5", "target5"),
    ]
    rows = partition_rows(tasks, seed=17)
    assert rows == partition_rows(list(reversed(tasks)), seed=17)
    assert len({row["component_id"] for row in rows[:4]}) == 1
    assert len({row["split"] for row in rows[:4]}) == 1
    assert rows[4]["component_id"] != rows[0]["component_id"]


@pytest.mark.parametrize("tasks,match", [
    ([task("1", "", "i", "t")], "missing leakage"),
    ([task("1", "a", "i", "t"), task("1", "b", "j", "u")], "duplicate task"),
])
def test_invalid_group_identity_fails(tasks, match):
    with pytest.raises(ValueError, match=match):
        partition_rows(tasks, seed=17)


@pytest.mark.parametrize("attribution,status", [
    (Attribution.REFERENCE, EvaluationStatus.REFERENCE_ERROR),
    (Attribution.EVALUATOR, EvaluationStatus.WORKER_ERROR),
])
def test_fault_is_never_a_zero_policy_reward(attribution, status):
    with pytest.raises(MeasurementFault):
        score_signals(EvaluationResult(status, attribution), TaskBaseline(0.5, 0.6, 1.0, 10.0))


def test_model_failure_zero_and_executable_rectangle_floor():
    baseline = TaskBaseline(0.5, 2 / 3, 1.0, 10.0)
    failure = score_signals(EvaluationResult(EvaluationStatus.SOURCE_REJECTED, Attribution.MODEL), baseline)
    assert set(failure["rewards"].values()) == {0.0}
    rectangle = EvaluationResult(EvaluationStatus.OK, Attribution.MODEL, iou=0.5, dice=2 / 3, metrics={"chamfer_boundary_um": 1.0})
    signal = score_signals(rectangle, baseline)
    assert signal["rewards"]["raw_iou"] == 0.5
    assert signal["rewards"]["shaped_v3b"] == 0.05


def test_constant_groups_have_zero_advantage_and_tied_rank():
    records = [{"task_id": "a", "candidate_id": name, "status": "syntax_error", "rewards": {policy: 0.0 for policy in ("raw_iou", "validity_floor", "shaped_v3b")}} for name in ("one", "two")]
    summary = summarize(records)
    for policy in summary["policies"].values():
        assert policy["nonconstant_group_fraction"] == 0
        group = policy["groups"][0]
        assert set(group["std_normalized_advantage"].values()) == {0.0}
        assert set(group["descending_rank_ties_share_rank"].values()) == {1}


def test_affine_validity_floor_has_identical_normalized_credit_on_valid_groups():
    baseline = TaskBaseline(0.1, 0.2, 1.0, 10.0)
    records = []
    for index, iou in enumerate((0.2, 0.5, 0.9)):
        result = EvaluationResult(EvaluationStatus.OK, Attribution.MODEL, iou=iou, dice=2*iou/(1+iou), metrics={"chamfer_boundary_um": 1-iou})
        records.append({"task_id": "a", "candidate_id": str(index), "status": "ok", **score_signals(result, baseline)})
    summary = summarize(records)
    advantages = [summary["policies"][policy]["groups"][0]["std_normalized_advantage"] for policy in ("raw_iou", "validity_floor")]
    assert advantages[0] == pytest.approx(advantages[1])
    assert summary["policy_pairs"]["validity_floor:raw_iou"][0]["pairwise_order_disagreement_fraction"] == 0


def test_sampling_latency_survives_and_model_claimed_metrics_are_recomputed():
    candidate = {
        "task_id": "a", "candidate_id": "sample-0", "completion": "invalid(",
        "latency_seconds": 1.25, "evaluation_latency_seconds": 999,
        "iou": 1.0, "rewards": {"raw_iou": 1.0},
    }
    result = EvaluationResult(
        EvaluationStatus.SYNTAX_ERROR, Attribution.MODEL, latency_seconds=0.003
    )
    record = measurement_record(
        candidate, task("a", "g", "image", "target"),
        TaskBaseline(0.5, 0.6, 1.0, 10.0), result,
    )
    assert record["latency_seconds"] == 1.25
    assert record["evaluation_latency_seconds"] == 0.003
    assert record["iou"] is None
    assert record["rewards"]["raw_iou"] == 0.0
    assert candidate["evaluation_latency_seconds"] == 999
