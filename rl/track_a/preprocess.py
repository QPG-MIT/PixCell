"""Versioned Track A image preprocessing."""

from __future__ import annotations

import io

from PIL import Image

from rl.common.contracts import ModelObservation


IMAGE_PREPROCESS_VERSION = "primary-view-long-edge-v1"


def model_image(
    observation: ModelObservation,
    *,
    max_long_edge: int = 1440,
) -> Image.Image:
    """Decode the one primary view and downscale only when necessary."""

    if max_long_edge < 1:
        raise ValueError("max_long_edge must be positive")
    image = Image.open(io.BytesIO(observation.image_bytes)).convert("RGB")
    image.load()
    if max(image.size) > max_long_edge:
        image.thumbnail((max_long_edge, max_long_edge), Image.Resampling.LANCZOS)
    return image
