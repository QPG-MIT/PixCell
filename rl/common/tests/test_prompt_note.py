"""The v3 anisotropy scale note: honest input from model-visible state only."""

from __future__ import annotations

import hashlib
import io

import numpy as np
from PIL import Image

from rl.common.contracts import ModelObservation
from rl.common.prompt import CONTRACT_VERSION, build_prompt_text, scale_note


def _observation(
    ink_w: int,
    ink_h: int,
    footprint_um: tuple[float, float],
) -> ModelObservation:
    array = np.full((ink_h + 20, ink_w + 20), 255, dtype=np.uint8)
    array[10 : 10 + ink_h, 10 : 10 + ink_w] = 0
    image = Image.fromarray(array, mode="L")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    payload = buffer.getvalue()
    return ModelObservation(
        image_bytes=payload,
        footprint_um=footprint_um,
        image_sha256=hashlib.sha256(payload).hexdigest(),
    )


def test_contract_is_v3() -> None:
    assert CONTRACT_VERSION == "pixcell-direct-reconstruction-v3"


def test_isotropic_image_gets_no_note() -> None:
    # 200x100 ink for a 20x10 um footprint: 10 px/um on both axes.
    observation = _observation(200, 100, (20.0, 10.0))
    assert scale_note(observation) == ""
    assert "px/um" not in build_prompt_text(observation)


def test_distorted_image_states_both_axis_scales() -> None:
    # 200x180 ink for a 20x2 um footprint: 10 px/um in x, 90 px/um in y.
    observation = _observation(200, 180, (20.0, 2.0))
    note = scale_note(observation)
    assert "NOT drawn to physical scale" in note
    assert "10.00 px/um horizontally" in note
    assert "90.00 px/um vertically" in note
    assert "Trust the stated footprint" in note
    assert note in build_prompt_text(observation)


def test_note_only_uses_model_visible_state() -> None:
    observation = _observation(200, 180, (20.0, 2.0))
    note = scale_note(observation)
    assert observation.image_sha256 not in note
    assert "target" not in note.casefold()
    assert "calibration" not in note.casefold()
