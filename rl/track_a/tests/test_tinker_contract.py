from __future__ import annotations

import pytest

from rl.common.contracts import task_from_row
from rl.track_a.prompt import build_prompt_text
pytest.importorskip("tinker", reason="Tinker SDK env (rl/requirements-lock.txt) not installed")
pytest.importorskip("chz", reason="chz env (rl/requirements-lock.txt) not installed")

from rl.track_a.tinker_data import (
    TrackASupervisedDataset,
    _message,
    _renderer,
)


def test_tinker_sft_uses_the_same_blind_prompt_and_assistant_only_loss(core_row):
    task = task_from_row(core_row)
    renderer = _renderer(
        "Qwen/Qwen3.6-35B-A3B",
        "qwen3_5_disable_thinking",
    )
    message = _message(task, max_image=1440)
    assert message["role"] == "user"
    assert len(message["content"]) == 2
    assert message["content"][1]["text"] == build_prompt_text(task.observation)

    dataset = TrackASupervisedDataset(
        [task],
        renderer,
        batch_size=1,
        max_length=6144,
        max_image=1440,
        balanced=True,
    )
    datum = dataset.get_batch(0)[0]
    weights = datum.loss_fn_inputs["weights"].data
    assert datum.model_input.length <= 6144
    assert sum(weights) == pytest.approx(1.0, rel=1e-6)
    assert min(weights) == 0.0
    assert max(weights) > 0.0
