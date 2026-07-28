"""The versioned direct Phase-A prompt shared by training and evaluation.

v3 adds the anisotropy scale note. The dataset's model image is the
max-visibility view — per-axis magnified, NOT physical aspect. Measured over
depth/train: 50% of rows exceed 1.6x aspect distortion (p90 = 5.0x, L4 max
31.6x). Above the 1.6x threshold the prompt states the per-axis render
scale, computed ONLY from model-visible inputs (the attached image's ink
bounding box and the stated footprint) — honest input, not leakage; the
private library shipped the same note for the same reason.
"""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from rl.common.contracts import ModelObservation


CONTRACT_VERSION = "pixcell-direct-reconstruction-v3"
SCALE_NOTE_ANISOTROPY_THRESHOLD = 1.6
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_PATH = (
    _REPO_ROOT
    / "src"
    / "michaelangelo"
    / "reference"
    / "gds_factory_function_catalogue_extended.md"
)
_TASK_PATH = (
    _REPO_ROOT / "rl" / "common" / "assets" / "phase_a_direct_v2.md"
)


def catalog_text() -> str:
    return _CATALOG_PATH.read_text(encoding="utf-8")


def task_text() -> str:
    return _TASK_PATH.read_text(encoding="utf-8").strip()


def prompt_asset_hashes() -> dict[str, str]:
    return {
        "catalog_sha256": hashlib.sha256(_CATALOG_PATH.read_bytes()).hexdigest(),
        "task_sha256": hashlib.sha256(_TASK_PATH.read_bytes()).hexdigest(),
    }


_SCALE_NOTE_CACHE: dict[str, str] = {}


def scale_note(observation: ModelObservation) -> str:
    """The anisotropy note, or an empty string below the threshold.

    Computed only from what the model can already see: the attached image's
    ink bounding box and the stated footprint.
    """

    cached = _SCALE_NOTE_CACHE.get(observation.image_sha256)
    if cached is not None:
        return cached
    array = np.asarray(
        Image.open(io.BytesIO(observation.image_bytes)).convert("L")
    )
    mask = array < 245
    ys, xs = np.where(mask)
    if xs.size == 0:
        note = ""
    else:
        bbox_w = int(xs.max()) - int(xs.min()) + 1
        bbox_h = int(ys.max()) - int(ys.min()) + 1
        length_um, width_um = observation.footprint_um
        scale_x = bbox_w / length_um
        scale_y = bbox_h / width_um
        anisotropy = max(scale_x / scale_y, scale_y / scale_x)
        if anisotropy <= SCALE_NOTE_ANISOTROPY_THRESHOLD:
            note = ""
        else:
            note = (
                "\nNOTE: the image is NOT drawn to physical scale - it is "
                f"rendered at {scale_x:.2f} px/um horizontally and "
                f"{scale_y:.2f} px/um vertically. Trust the stated footprint "
                "for physical dimensions, not the image's apparent aspect "
                "ratio.\n"
            )
    _SCALE_NOTE_CACHE[observation.image_sha256] = note
    return note


def build_prompt_text(observation: ModelObservation) -> str:
    """Build the only text visible to a direct image-to-code policy."""

    footprint_text = json.dumps(
        {"footprint_um": list(observation.footprint_um)},
        indent=2,
    )
    return f"""## Phase-A Device Input

The attached image is a device-only black-and-white silhouette. BLACK is
material on layer `(1, 0)` and WHITE is background.

Physical footprint, where `footprint_um` is `[x-length, y-width]`:

{footprint_text}
{scale_note(observation)}
---

## Exact GDSFactory Extended Primitive Catalogue

{catalog_text()}

---

## Direct Phase-A Programming Contract

{task_text()}"""


def openai_user_message(
    observation: ModelObservation,
    *,
    image_url: str,
) -> dict[str, Any]:
    """Serialize the one image-first user turn, with no system turn."""

    return {
        "role": "user",
        "content": [
            {"type": "image_url", "image_url": {"url": image_url}},
            {"type": "text", "text": build_prompt_text(observation)},
        ],
    }


def openai_sft_messages(
    example: Any,
    *,
    image_url: str,
) -> list[dict[str, Any]]:
    """Serialize ``image + fixed task context -> code`` for SFT."""

    return [
        openai_user_message(example.observation, image_url=image_url),
        {
            "role": "assistant",
            "content": [{"type": "text", "text": example.code}],
        },
    ]
