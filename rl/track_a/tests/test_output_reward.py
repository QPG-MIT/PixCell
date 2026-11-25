from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.common.dataset_io import load_tasks
from rl.common.evaluator import (
    Attribution,
    EvaluationResult,
    EvaluationStatus,
)
from rl.common.output import extract_code
from rl.track_a.reward import reward_for, reward_for_policy


def test_extract_code_handles_reasoning_and_last_fence():
    text = (
        "<think>private scratch</think>\n"
        "```python\nprint('wrong')\n```\n"
        "```python\nimport gdsfactory as gf\nc.write_gds('device.gds')\n```"
    )
    assert extract_code(text).startswith("import gdsfactory")


def test_reward_is_full_precision_direct_iou():
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.401234567891,
        dice=0.5,
    )
    assert reward_for(result) == pytest.approx(0.05 + 0.95 * 0.401234567891)


def test_only_model_failures_become_zero():
    model = EvaluationResult(EvaluationStatus.NO_GDS, Attribution.MODEL)
    evaluator = EvaluationResult(
        EvaluationStatus.MEASUREMENT_ERROR,
        Attribution.EVALUATOR,
        retryable=True,
    )
    reference = EvaluationResult(
        EvaluationStatus.REFERENCE_ERROR,
        Attribution.REFERENCE,
    )
    assert reward_for(model) == 0.0
    assert reward_for(evaluator) is None
    assert reward_for(reference) is None


def test_raw_iou_reward_has_no_validity_floor():
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.401234567891,
    )
    assert reward_for_policy(result, policy="raw_iou") == pytest.approx(
        0.401234567891
    )


@pytest.mark.parametrize("iou", [float("nan"), float("inf"), -0.1, 1.1])
def test_raw_iou_reward_rejects_invalid_measurements(iou):
    result = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=iou,
    )
    with pytest.raises(ValueError):
        reward_for_policy(result, policy="raw_iou")


def test_paid_sample_is_recorded_before_evaluator_failure(monkeypatch) -> None:
    pytest.importorskip("chz", reason="Tinker is an optional RL dependency")
    pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
    pytest.importorskip(
        "tinker_cookbook",
        reason="Tinker Cookbook is an optional RL dependency",
    )
    from rl.track_a import tinker_data

    repo_root = Path(__file__).resolve().parents[3]
    task = load_tasks(
        repo_root / "dataset",
        configuration="depth",
        split="train",
    )[0]
    sample_records: list[dict] = []
    evaluated_records: list[dict] = []

    class Tokenizer:
        @staticmethod
        def decode(_tokens):
            return "```python\nprint('sample')\n```"

    class Renderer:
        tokenizer = Tokenizer()

        @staticmethod
        def parse_response(_tokens):
            return (
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "```python\nprint('sample')\n```",
                        }
                    ],
                },
                SimpleNamespace(is_clean=True),
            )

    class FailingBatcher:
        @staticmethod
        async def submit(_reference, _completion):
            return EvaluationResult(
                EvaluationStatus.MEASUREMENT_ERROR,
                Attribution.EVALUATOR,
                retryable=True,
                error="unit evaluator failure",
            )

    monkeypatch.setattr(tinker_data, "_batcher", lambda: FailingBatcher())
    env = tinker_data.TrackAEnv(
        task,
        Renderer(),
        max_image=1920,
        attempt_context={"step": 0, "attempt": 1},
        sample_recorder=lambda value: sample_records.append(dict(value)),
        attempt_recorder=lambda value: evaluated_records.append(dict(value)),
        reward_policy="raw_iou",
    )
    env.prompt_tokens = 123
    with pytest.raises(
        tinker_data.EvaluationInfrastructureError,
        match="unit evaluator failure",
    ):
        asyncio.run(
            env.step(
                [1, 2],
                extra=SimpleNamespace(stop_reason="length"),
            )
        )
    assert len(sample_records) == 1
    assert sample_records[0]["sampling"]["raw_token_ids"] == [1, 2]
    assert sample_records[0]["program"] == "print('sample')"
    assert evaluated_records == []


def _ok(iou: float, dice: float, chamfer: float | None) -> EvaluationResult:
    return EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=iou,
        dice=dice,
        metrics={"chamfer_boundary_um": chamfer},
    )


def _baseline(
    iou_rect: float = 0.5,
    dice_rect: float = 0.6,
    chamfer_rect: float | None = 4.0,
    diag_um: float = 20.0,
):
    from rl.common.baselines import TaskBaseline

    return TaskBaseline(
        iou_rect=iou_rect,
        dice_rect=dice_rect,
        chamfer_rect_boundary_um=chamfer_rect,
        diag_um=diag_um,
    )


def test_shaped_normalizes_iou_against_rectangle():
    # dice at its rect value and chamfer at the rect chamfer: only iou_n pays.
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.75, dice=0.6, chamfer=4.0)
    reward = reward_for_policy(result, policy="shaped_v3b", baseline=baseline)
    assert reward == pytest.approx(0.05 + 0.40 * ((0.75 - 0.5) / 0.5))


def test_shaped_rect_equivalent_program_earns_exactly_the_floor():
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.5, dice=0.6, chamfer=4.0)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05)


def test_shaped_degenerate_target_scores_raw():
    import math as _math

    baseline = _baseline(iou_rect=0.96, dice_rect=0.97, chamfer_rect=0.1, diag_um=20.0)
    result = _ok(iou=0.9, dice=0.92, chamfer=0.5)
    tau = 0.05 * 20.0
    expected = 0.05 + 0.40 * 0.9 + 0.15 * 0.92 + 0.40 * _math.exp(-0.5 / tau)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(expected)


def test_shaped_teacher_denominator_floor():
    import math as _math

    # tau = 1.0 (diag 20); t2b = 0.9, t2b_rect = 0.8 -> 0.1 / max(0.2, 0.3)
    baseline = _baseline(
        iou_rect=0.5,
        dice_rect=0.6,
        chamfer_rect=-_math.log(0.8),
        diag_um=20.0,
    )
    result = _ok(iou=0.5, dice=0.6, chamfer=-_math.log(0.9))
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05 + 0.40 * (0.1 / 0.3))


def test_shaped_model_failures_are_zero_and_faults_are_masked():
    baseline = _baseline()
    crash = EvaluationResult(EvaluationStatus.RUNTIME_ERROR, Attribution.MODEL)
    rejected = EvaluationResult(EvaluationStatus.SOURCE_REJECTED, Attribution.MODEL)
    fault = EvaluationResult(
        EvaluationStatus.MEASUREMENT_ERROR, Attribution.EVALUATOR, retryable=True
    )
    assert reward_for_policy(crash, policy="shaped_v3b", baseline=baseline) == 0.0
    assert reward_for_policy(rejected, policy="shaped_v3b", baseline=baseline) == 0.0
    assert reward_for_policy(fault, policy="shaped_v3b", baseline=baseline) is None


def test_shaped_missing_chamfer_scores_teacher_zero():
    baseline = _baseline(iou_rect=0.5, dice_rect=0.6, chamfer_rect=4.0)
    result = _ok(iou=0.5, dice=0.6, chamfer=None)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(0.05)


def test_shaped_requires_a_baseline():
    with pytest.raises(ValueError):
        reward_for_policy(_ok(0.5, 0.5, 1.0), policy="shaped_v3b")


def test_shaped_perfect_program_reaches_one():
    baseline = _baseline(iou_rect=0.3, dice_rect=0.4, chamfer_rect=50.0, diag_um=20.0)
    result = _ok(iou=1.0, dice=1.0, chamfer=0.0)
    assert reward_for_policy(
        result, policy="shaped_v3b", baseline=baseline
    ) == pytest.approx(1.0)


def test_validity_only_policy_semantics():
    ok = _ok(iou=0.0, dice=0.0, chamfer=None)
    crash = EvaluationResult(EvaluationStatus.RUNTIME_ERROR, Attribution.MODEL)
    rejected = EvaluationResult(EvaluationStatus.SOURCE_REJECTED, Attribution.MODEL)
    no_gds = EvaluationResult(EvaluationStatus.NO_GDS, Attribution.MODEL)
    fault = EvaluationResult(
        EvaluationStatus.MEASUREMENT_ERROR, Attribution.EVALUATOR, retryable=True
    )
    ref_fault = EvaluationResult(
        EvaluationStatus.REFERENCE_ERROR, Attribution.REFERENCE
    )
    assert reward_for_policy(ok, policy="validity_only") == 1.0
    assert reward_for_policy(crash, policy="validity_only") == 0.0
    assert reward_for_policy(rejected, policy="validity_only") == 0.0
    assert reward_for_policy(no_gds, policy="validity_only") == 0.0
    assert reward_for_policy(fault, policy="validity_only") is None
    assert reward_for_policy(ref_fault, policy="validity_only") is None


def test_rc01_policy_formula_overflow_empty_and_fault_attribution():
    from rl.track_a.reward import REWARD_POLICIES

    assert "validity_only" in REWARD_POLICIES
    assert "rc01" in REWARD_POLICIES

    normal = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.8,
        dice=0.88,
        metrics={
            "rc01": {
                "score": 0.72,
                "overflow_factor": 1.0,
                "beta0_a": 1,
                "version": "1.2.0",
            },
            "rc01_empty": False,
        },
    )
    assert reward_for_policy(normal, policy="rc01") == pytest.approx(
        0.05 * 1.0 + 0.95 * 0.72
    )

    overflowed = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=1.0,
        dice=1.0,
        metrics={
            "rc01": {
                "score": 0.20,
                "overflow_factor": 0.25,
                "beta0_a": 1,
                "version": "1.2.0",
            },
            "rc01_empty": False,
        },
    )
    assert reward_for_policy(overflowed, policy="rc01") == pytest.approx(
        0.05 * 0.25 + 0.95 * 0.20
    )

    empty_render = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.0,
        dice=0.0,
        metrics={
            "rc01": {
                "score": 0.0,
                "overflow_factor": 1.0,
                "beta0_a": 0,
                "version": "1.2.0",
            },
            "rc01_empty": True,
        },
    )
    assert reward_for_policy(empty_render, policy="rc01") == 0.0

    # Empty detected via beta0_a == 0 even without rc01_empty flag
    empty_beta0 = EvaluationResult(
        EvaluationStatus.OK,
        Attribution.MODEL,
        iou=0.0,
        dice=0.0,
        metrics={"rc01": {"score": 0.0, "overflow_factor": 1.0, "beta0_a": 0}},
    )
    assert reward_for_policy(empty_beta0, policy="rc01") == 0.0

    crash = EvaluationResult(EvaluationStatus.RUNTIME_ERROR, Attribution.MODEL)
    fault = EvaluationResult(
        EvaluationStatus.WORKER_ERROR, Attribution.EVALUATOR, retryable=True
    )
    ref_fault = EvaluationResult(
        EvaluationStatus.REFERENCE_ERROR, Attribution.REFERENCE
    )
    assert reward_for_policy(crash, policy="rc01") == 0.0
    assert reward_for_policy(fault, policy="rc01") is None
    assert reward_for_policy(ref_fault, policy="rc01") is None

    # Missing or non-finite RC-01 score must fail closed
    missing = _ok(iou=0.5, dice=0.5, chamfer=1.0)
    with pytest.raises(ValueError, match="RC-01 score"):
        reward_for_policy(missing, policy="rc01")

    for bad_score in (float("nan"), float("inf"), -0.1, 1.1):
        bad = EvaluationResult(
            EvaluationStatus.OK,
            Attribution.MODEL,
            iou=0.5,
            metrics={"rc01": {"score": bad_score, "overflow_factor": 1.0, "beta0_a": 1}},
        )
        with pytest.raises(ValueError):
            reward_for_policy(bad, policy="rc01")


def test_evaluator_wires_rc01_with_gds_size_um_overflow_and_empty_render(monkeypatch):
    """End-to-end check that PixCellEvaluator passes gds_size_um from render_gds_absolute
    into RC-01 v1.2.0 and produces strict finite JSON diagnostics even on empty renders."""
    import hashlib
    import io
    import json

    import gdstk
    from PIL import Image, ImageDraw

    from rl.common.contracts import VerifierReference
    from rl.common.evaluator import PixCellEvaluator

    # Create a clean calibrated 128x128 target containing a 10x10 um square inside [14,14,114,114]
    img = Image.new("L", (128, 128), 255)
    ImageDraw.Draw(img).rectangle([14, 14, 113, 113], fill=0)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    target_bytes = buf.getvalue()
    reference = VerifierReference(
        target_image_bytes=target_bytes,
        footprint_um=(10.0, 10.0),
        target_image_sha256=hashlib.sha256(target_bytes).hexdigest(),
    )

    def _run_with_polys(polys: list[gdstk.Polygon]) -> EvaluationResult:
        def fake_run(_self, _source: str, workdir: Path):
            lib = gdstk.Library()
            cell = gdstk.Cell("top")
            for poly in polys:
                cell.add(poly)
            lib.add(cell)
            lib.write_gds(workdir / "device.gds")
            return EvaluationStatus.OK, None

        with PixCellEvaluator(max_workers=1, evaluator_retries=0) as evaluator:
            monkeypatch.setattr(PixCellEvaluator, "_run_candidate", fake_run)
            return evaluator.evaluate(reference, "x = 1\n")

    res_fit = _run_with_polys([gdstk.rectangle((0.0, 0.0), (10.0, 10.0), layer=1, datatype=0)])
    assert res_fit.status is EvaluationStatus.OK
    json.dumps(res_fit.metrics, allow_nan=False)
    assert res_fit.metrics["rc01"]["version"] == "1.2.0"
    assert res_fit.metrics["rc01"]["overflow_clipped"] is False
    assert res_fit.metrics["rc01"]["overflow_factor"] == pytest.approx(1.0)
    assert res_fit.metrics["rc01_empty"] is False
    assert reward_for_policy(res_fit, policy="rc01") > 0.98

    # Massive 80x40 um GDS overflows the 12.8x12.8 um canvas despite filling the clipped frame
    res_ov = _run_with_polys([gdstk.rectangle((0.0, 0.0), (80.0, 40.0), layer=1, datatype=0)])
    assert res_ov.status is EvaluationStatus.OK
    json.dumps(res_ov.metrics, allow_nan=False)
    assert res_ov.metrics["rc01"]["overflow_clipped"] is True
    ov_fac = res_ov.metrics["rc01"]["overflow_factor"]
    assert 0.0 < ov_fac < 0.25
    expected_ov_reward = 0.05 * ov_fac + 0.95 * res_ov.metrics["rc01"]["score"]
    assert reward_for_policy(res_ov, policy="rc01") == pytest.approx(expected_ov_reward)
    assert expected_ov_reward < 0.25

    # Two widely separated polygons whose vertical center is empty and both polygons clip
    # completely outside the 12.8x12.8 um canvas -> empty raster, finite JSON, 0.0 RC-01 reward
    res_empty = _run_with_polys(
        [
            gdstk.rectangle((0.0, 0.0), (1.0, 1.0), layer=1, datatype=0),
            gdstk.rectangle((0.0, 100.0), (1.0, 101.0), layer=1, datatype=0),
        ]
    )
    assert res_empty.status is EvaluationStatus.OK
    json.dumps(res_empty.metrics, allow_nan=False)
    assert res_empty.metrics["rc01_empty"] is True
    assert res_empty.metrics["rc01"]["mean_bnd_dist_px"] is None
    assert reward_for_policy(res_empty, policy="rc01") == 0.0
    assert reward_for_policy(res_empty, policy="validity_only") == 1.0
