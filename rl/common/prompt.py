"""The versioned blind Phase-A prompt shared by training and evaluation."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from rl.common.contracts import ModelObservation


CONTRACT_VERSION = "pixcell-blind-phase-a-direct-v1"
_REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG_PATH = (
    _REPO_ROOT
    / "src"
    / "michaelangelo"
    / "reference"
    / "gds_factory_function_catalogue_extended.md"
)
_TASK_PATH = _REPO_ROOT / "src" / "michaelangelo" / "templates" / "prompt.md"


def catalog_text() -> str:
    return _CATALOG_PATH.read_text(encoding="utf-8")


def task_text() -> str:
    return _TASK_PATH.read_text(encoding="utf-8").strip()


def prompt_asset_hashes() -> dict[str, str]:
    return {
        "catalog_sha256": hashlib.sha256(_CATALOG_PATH.read_bytes()).hexdigest(),
        "task_sha256": hashlib.sha256(_TASK_PATH.read_bytes()).hexdigest(),
    }


def build_prompt_text(observation: ModelObservation) -> str:
    """Build the only text visible to a direct image-to-code policy."""

    footprint_text = json.dumps(
        {"footprint_um": list(observation.footprint_um)},
        indent=2,
    )
    return f"""## GDSFactory Function Catalog (Reference)

{catalog_text()}

---

## Device Footprint Constraint

{footprint_text}

---

## Task

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
