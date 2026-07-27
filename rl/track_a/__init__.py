"""Track A: direct SFT followed by curriculum RL for a self-hostable model."""

from .prompt import CONTRACT_VERSION, build_prompt_text
from .reward import reward_for

__all__ = [
    "CONTRACT_VERSION",
    "build_prompt_text",
    "reward_for",
]
