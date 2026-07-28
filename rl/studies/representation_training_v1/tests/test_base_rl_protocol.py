from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from rl.studies.representation_training_v1.protocol import (
    BASE_QWEN_RL_STAGE_IDS,
    L0_SFT_QWEN_RL_STAGE_IDS,
    STUDY_RELATIVE_PATH,
    load_protocol,
    stage_spec,
)


REPO_ROOT = Path(__file__).resolve().parents[4]


def _write_mutated_protocol(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    source = (
        REPO_ROOT
        / STUDY_RELATIVE_PATH
        / "protocol.json"
    )
    document = json.loads(source.read_text(encoding="utf-8"))
    mutate(document)
    logical = {
        key: value for key, value in document.items() if key != "logical_sha256"
    }
    document["logical_sha256"] = hashlib.sha256(
        json.dumps(
            logical,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    target = tmp_path / STUDY_RELATIVE_PATH / "protocol.json"
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def test_base_qwen_rl_contract_is_exact() -> None:
    protocol = load_protocol(REPO_ROOT)
    for level, stage_id in enumerate(BASE_QWEN_RL_STAGE_IDS):
        stage = stage_spec(protocol, stage_id)
        assert stage.current_level == f"L{level}"
        assert stage.parent == (
            "base:qwen"
            if level == 0
            else f"qwen-base-rl-l{level - 1}:complete"
        )
        assert stage.replay_levels == tuple(f"L{prior}" for prior in range(level))
        assert stage.hypotheses == ("RT-H06",)
        assert stage.wave("smoke")["approval"] == (
            "initial"
            if level == 0
            else "prior-and-current-level-held-out-transition-receipt"
        )
        assert stage.wave("step-5")["approval"] == "rollout-health-receipt"
        for wave in ("step-10", "step-15", "step-20", "step-25", "complete"):
            assert (
                stage.wave(wave)["approval"]
                == "current-level-held-out-promotion-receipt"
            )


def test_l0_sft_to_qwen_rl_contract_uses_modern_level_gates() -> None:
    protocol = load_protocol(REPO_ROOT)
    for level, stage_id in enumerate(L0_SFT_QWEN_RL_STAGE_IDS, start=1):
        stage = stage_spec(protocol, stage_id)
        assert stage.current_level == f"L{level}"
        assert stage.parent == (
            "qwen-l0-sft:complete"
            if level == 1
            else f"qwen-l0-rl-l{level - 1}:complete"
        )
        assert stage.replay_levels == tuple(f"L{prior}" for prior in range(level))
        assert stage.hypotheses == ("RT-H03",)
        assert stage.wave("smoke")["approval"] == (
            "parent-receipt-and-source-transition"
            if level == 1
            else "prior-level-held-out-promotion-receipt"
        )
        assert stage.wave("step-5")["approval"] == "rollout-health-receipt"
        for wave in ("step-10", "step-15", "step-20", "step-25", "complete"):
            assert (
                stage.wave(wave)["approval"]
                == "current-level-held-out-promotion-receipt"
            )


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda value: value["stages"]["qwen-base-rl-l0"]["waves"]["smoke"].update(
                {"approval": "base-level-held-out-baseline-receipt"}
            ),
            "wrong pure-RL gates",
        ),
        (
            lambda value: value["stages"]["qwen-base-rl-l0"]["waves"]["step-5"].update(
                {"approval": "clean-smoke-receipt"}
            ),
            "wrong pure-RL gates",
        ),
        (
            lambda value: value["stages"]["qwen-l0-rl-l1"]["waves"]["smoke"].update(
                {"approval": "entry-evaluation-and-promotion-receipt"}
            ),
            "wrong L0-SFT-to-RL gates",
        ),
        (
            lambda value: value["stages"]["qwen-base-rl-l2"].update(
                {"parent": "qwen-base-rl-l0:complete"}
            ),
            "changed the pure Qwen RL curriculum",
        ),
        (
            lambda value: value["evaluation"]["curriculum_progress_holdout"].update(
                {"realization_slot": 7}
            ),
            "wrong curriculum progress holdout",
        ),
        (
            lambda value: value["evaluation"]["final_selection_holdout"].update(
                {"realization_slot": 6}
            ),
            "wrong final selection holdout",
        ),
    ],
)
def test_base_qwen_rl_contract_mutations_fail_closed(
    tmp_path: Path,
    mutate: Callable[[dict[str, Any]], None],
    message: str,
) -> None:
    _write_mutated_protocol(tmp_path, mutate)
    with pytest.raises(ValueError, match=message):
        load_protocol(tmp_path)
