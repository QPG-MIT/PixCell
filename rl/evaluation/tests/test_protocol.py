from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rl.evaluation.protocol import (
    deterministic_seed,
    jobs_for_wave,
    load_archived_protocol,
    load_protocol,
    resolved_arm_ids,
)
from rl.evaluation.tasks import load_task_manifest
from rl.studies.representation_curriculum_v1 import (
    run_baseline as archived_runner,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_MANIFEST = (
    REPO_ROOT / "rl/studies/representation_curriculum_v1/task_manifest.json"
)
BASE_PROTOCOL = TASK_MANIFEST.with_name("protocol.json")
QWEN32_PROTOCOL = (
    TASK_MANIFEST.parent / "extensions/qwen32/protocol.json"
)
QWEN60_PROTOCOL = (
    TASK_MANIFEST.parent / "extensions/qwen60/protocol.json"
)


def _protocol() -> dict:
    return load_archived_protocol(REPO_ROOT, protocol_file=BASE_PROTOCOL)


def _selection(
    selected: str,
    *,
    complete: bool = True,
    protocol: dict | None = None,
) -> dict:
    protocol = protocol or _protocol()
    return {
        "schema_version": "pixcell-operating-point-selection-v1",
        "study_id": protocol["study_id"],
        "protocol_sha256": protocol["logical_sha256"],
        "source_hypothesis": "RC-H00",
        "selected_arm": selected,
        "rescue_required": False,
        "rescue_run": False,
        "complete": complete,
    }


def _task_ids(task_set: str) -> list[str]:
    manifest = load_task_manifest(TASK_MANIFEST, repo_root=REPO_ROOT)
    return [value["task_id"] for value in manifest["task_sets"][task_set]]


def test_protocol_freezes_baseline_and_forbids_unfrozen_training():
    protocol = _protocol()
    assert protocol["study_id"] == "representation-curriculum-v1"
    assert protocol["hypotheses"]["RC-H00"]["status"] == "frozen"
    assert protocol["hypotheses"]["RC-H01"]["status"] == "frozen"
    assert protocol["hypotheses"]["RC-H02"]["status"] == "frozen"
    assert all(
        value["status"] == "launch_forbidden_until_protocol_frozen"
        for value in protocol["future_hypothesis_registry"].values()
    )


def test_qwen_factorial_is_matched_and_seed_paired():
    protocol = _protocol()
    arms = [
        protocol["arms"][value]
        for value in protocol["hypotheses"]["RC-H00"]["arm_ids"]
    ]
    assert {(value["thinking"], value["max_output_tokens"]) for value in arms} == {
        (False, 4096),
        (False, 16384),
        (True, 4096),
        (True, 16384),
    }
    first = deterministic_seed(protocol, task_id="same", attempt_index=1)
    assert first == deterministic_seed(
        protocol,
        task_id="same",
        attempt_index=1,
    )
    assert first != deterministic_seed(
        protocol,
        task_id="same",
        attempt_index=2,
    )


def test_wave_job_counts_are_exact():
    protocol = _protocol()
    dev = _task_ids("qwen_operating_point")
    bench = _task_ids("f1_f8")
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00",
            wave_name="smoke",
            task_ids=dev,
        )
    ) == 4
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H00",
            wave_name="complete",
            task_ids=dev,
        )
    ) == 320
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H02",
            wave_name="smoke",
            task_ids=bench,
        )
    ) == 8
    assert len(
        jobs_for_wave(
            protocol,
            hypothesis_id="RC-H02",
            wave_name="complete",
            task_ids=bench,
        )
    ) == 32


def test_qwen_baseline_keeps_incumbent_control_when_winner_differs():
    protocol = _protocol()
    assert resolved_arm_ids(
        protocol,
        "RC-H01",
        selection=_selection("qwen-off-4096", protocol=protocol),
    ) == ["qwen-off-4096"]
    assert resolved_arm_ids(
        protocol,
        "RC-H01",
        selection=_selection("qwen-on-16384", protocol=protocol),
    ) == ["qwen-off-4096", "qwen-on-16384"]


def test_conditional_rescue_is_fail_closed():
    protocol = _protocol()
    with pytest.raises(ValueError, match="forbidden"):
        resolved_arm_ids(
            protocol,
            "RC-H00R",
            selection=_selection("qwen-on-16384", protocol=protocol),
        )
    triggered = _selection(
        "qwen-on-16384",
        complete=False,
        protocol=protocol,
    )
    triggered["rescue_required"] = True
    assert resolved_arm_ids(
        protocol,
        "RC-H00R",
        selection=triggered,
    ) == ["qwen-on-32768-confirmation"]


@pytest.mark.parametrize(
    "protocol_file",
    (BASE_PROTOCOL, QWEN32_PROTOCOL, QWEN60_PROTOCOL),
)
def test_superseded_v1_protocols_are_rejected_for_paid_launch(
    protocol_file: Path,
):
    with pytest.raises(
        ValueError,
        match="prompt contract does not match the runtime",
    ):
        load_protocol(REPO_ROOT, protocol_file=protocol_file)


def test_archived_runner_binds_its_own_protocol(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
):
    captured: dict[str, object] = {}

    async def fake_run_baseline(**kwargs):
        captured.update(kwargs)
        return {"summaries": {}}

    class FakeParser:
        @staticmethod
        def parse_args():
            return SimpleNamespace(
                hypothesis="RC-H02",
                wave="smoke",
                expected_source_sha="a" * 40,
                confirm_spend="PIXCELL_PHASE1_BASELINE",
                external_root=tmp_path,
                selection=None,
            )

    monkeypatch.setattr(archived_runner, "run_baseline", fake_run_baseline)
    monkeypatch.setattr(archived_runner, "parser", FakeParser)
    archived_runner.main()
    assert captured["protocol_file"] == BASE_PROTOCOL
    assert captured["hypothesis_id"] == "RC-H02"
    assert json.loads(capsys.readouterr().out) == {}
