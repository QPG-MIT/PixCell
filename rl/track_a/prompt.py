"""Compatibility imports for the shared direct Phase-A prompt."""

from rl.common.prompt import (
    CONTRACT_VERSION,
    build_prompt_text,
    catalog_text,
    openai_sft_messages,
    openai_user_message,
    prompt_asset_hashes,
    task_text,
)

__all__ = [
    "CONTRACT_VERSION",
    "build_prompt_text",
    "catalog_text",
    "openai_sft_messages",
    "openai_user_message",
    "prompt_asset_hashes",
    "task_text",
]
