"""
Model registry for the HOMI system.

Contains definitions for all 59 supported models across 7 providers:
- Google Gemini (5 models) - Direct API
- Anthropic Claude (9 models) - Direct API
- OpenAI GPT (10 models) - Direct API
- Meta Llama (4 models) - OpenRouter
- Moonshot Kimi (4 models) - OpenRouter
- Alibaba Qwen-VL (22 models) - OpenRouter
- xAI Grok (7 models) - OpenRouter
"""

from typing import Any, Dict, List, Optional

from .types import ModelCapabilities


# Full model registry with all 54 models
MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # Google Gemini (7 models) - Direct API via google.genai
    # =========================================================================
    "gemini/gemini-3.1-pro-preview": {
        "provider": "gemini",
        "model_id": "gemini-3.1-pro-preview",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "levels",
        "thinking_levels": ["low", "high"],
    },
    "gemini/gemini-3.1-flash-lite-preview": {
        "provider": "gemini",
        "model_id": "gemini-3.1-flash-lite-preview",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "levels",
        "thinking_levels": ["minimal", "low", "medium", "high"],
    },
    "gemini/gemini-3-flash-preview": {
        "provider": "gemini",
        "model_id": "gemini-3-flash-preview",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "levels",
        "thinking_levels": ["minimal", "low", "medium", "high"],  # Per Google docs
    },
    "gemini/gemini-3-pro-preview": {
        "provider": "gemini",
        "model_id": "gemini-3-pro-preview",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "levels",
        "thinking_levels": ["low", "high"],  # Per Google docs - cannot disable
    },
    "gemini/gemini-2.5-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.5-flash",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "budget",  # Gemini 2.5 uses thinkingBudget (token count)
        "thinking_budget_range": [0, 24576],  # 0 disables thinking, per Google docs
    },
    "gemini/gemini-2.5-pro": {
        "provider": "gemini",
        "model_id": "gemini-2.5-pro",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 65536,
        "thinking_type": "budget",  # Gemini 2.5 uses thinkingBudget (token count)
        "thinking_budget_range": [128, 32768],  # min/max tokens
    },
    "gemini/gemini-2.0-flash": {
        "provider": "gemini",
        "model_id": "gemini-2.0-flash-001",
        "supports_seed": True,
        "supports_thinking": False,  # Gemini 2.0 does NOT support thinking
        "supports_vision": True,
        "max_tokens": 65536,
    },

    # =========================================================================
    # Anthropic Claude (9 models) - Direct API via anthropic SDK
    # =========================================================================
    "anthropic/claude-opus-4.5": {
        "provider": "claude",
        "model_id": "claude-opus-4-5-20251101",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 64000,  # Only Opus 4.5 supports 64K output
        "thinking_type": "budget",
    },
    "anthropic/claude-sonnet-4.5": {
        "provider": "claude",
        "model_id": "claude-sonnet-4-5-20250929",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "budget",
    },
    "anthropic/claude-haiku-4.5": {
        "provider": "claude",
        "model_id": "claude-haiku-4-5-20251001",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "budget",
    },
    "anthropic/claude-opus-4": {
        "provider": "claude",
        "model_id": "claude-opus-4-20250514",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,  # Opus 4 supports 32K output
        "thinking_type": "budget",
    },
    "anthropic/claude-sonnet-4": {
        "provider": "claude",
        "model_id": "claude-sonnet-4-20250514",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "budget",
    },
    "anthropic/claude-3.7-sonnet": {
        "provider": "claude",
        "model_id": "claude-3-7-sonnet-20250219",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "budget",
    },
    "anthropic/claude-3.7-sonnet:thinking": {
        "provider": "claude",
        "model_id": "claude-3-7-sonnet-20250219",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "budget",
        "default_thinking": True,
    },
    "anthropic/claude-3.5-sonnet": {
        "provider": "claude",
        "model_id": "claude-3-5-sonnet-20241022",
        "supports_seed": False,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 8192,
    },
    "anthropic/claude-3.5-haiku": {
        "provider": "claude",
        "model_id": "claude-3-5-haiku-20241022",
        "supports_seed": False,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 8192,
    },

    # =========================================================================
    # OpenAI GPT (10 models) - Direct API via openai SDK (responses API)
    # =========================================================================
    # GPT-5.2 - reasoning: none (default), low, medium, high, xhigh
    "openai/gpt-5.2": {
        "provider": "openai",
        "model_id": "gpt-5.2",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "effort",
        "thinking_levels": ["none", "low", "medium", "high", "xhigh"],
        "default_thinking": "none",
    },
    # GPT-5.2 Pro - reasoning: medium (default), high, xhigh (cannot use none/minimal/low)
    "openai/gpt-5.2-pro": {
        "provider": "openai",
        "model_id": "gpt-5.2-pro",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "effort",
        "thinking_levels": ["medium", "high", "xhigh"],
        "default_thinking": "medium",
    },
    # GPT-5 - reasoning: minimal, low, medium (default), high (no xhigh)
    "openai/gpt-5": {
        "provider": "openai",
        "model_id": "gpt-5",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "effort",
        "thinking_levels": ["minimal", "low", "medium", "high"],
        "default_thinking": "medium",
    },
    # GPT-5 Mini - reasoning: low, medium (default), high (no minimal/xhigh)
    "openai/gpt-5-mini": {
        "provider": "openai",
        "model_id": "gpt-5-mini",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "effort",
        "thinking_levels": ["low", "medium", "high"],
        "default_thinking": "medium",
    },
    # GPT-5 Nano - reasoning: low, medium (default), high
    "openai/gpt-5-nano": {
        "provider": "openai",
        "model_id": "gpt-5-nano",
        "supports_seed": False,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "effort",
        "thinking_levels": ["low", "medium", "high"],
        "default_thinking": "medium",
    },
    # GPT-4.1 - NO reasoning support (low latency, 1M context)
    "openai/gpt-4.1": {
        "provider": "openai",
        "model_id": "gpt-4.1",
        "supports_seed": False,
        "supports_thinking": False,  # No reasoning step
        "supports_vision": True,
        "max_tokens": 16000,
    },
    # GPT-4.1 Mini - NO reasoning support (low latency)
    "openai/gpt-4.1-mini": {
        "provider": "openai",
        "model_id": "gpt-4.1-mini",
        "supports_seed": False,
        "supports_thinking": False,  # No reasoning step
        "supports_vision": True,
        "max_tokens": 16000,
    },
    # GPT-4.1 Nano - NO reasoning support (low latency)
    "openai/gpt-4.1-nano": {
        "provider": "openai",
        "model_id": "gpt-4.1-nano",
        "supports_seed": False,
        "supports_thinking": False,  # No reasoning step
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "openai/gpt-4o": {
        "provider": "openai",
        "model_id": "gpt-4o",
        "supports_seed": False,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "openai/gpt-4o-mini": {
        "provider": "openai",
        "model_id": "gpt-4o-mini",
        "supports_seed": False,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },

    # =========================================================================
    # Meta Llama (4 models) - via OpenRouter
    # =========================================================================
    "meta-llama/llama-4-maverick": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-4-maverick",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "meta-llama/llama-4-scout": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-4-scout",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "meta-llama/llama-3.2-90b-vision": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.2-90b-vision-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "meta-llama/llama-3.2-11b-vision": {
        "provider": "openrouter",
        "model_id": "meta-llama/llama-3.2-11b-vision-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },

    # =========================================================================
    # Moonshot AI Kimi (4 models) - via OpenRouter
    # =========================================================================
    "moonshotai/kimi-vl-a3b-instruct": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-vl-a3b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },
    "moonshotai/kimi-vl-a3b-thinking": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-vl-a3b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "builtin",
    },
    "moonshotai/kimi-vl-a3b-thinking:free": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-vl-a3b-thinking:free",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 16000,
        "thinking_type": "builtin",
    },
    "moonshotai/kimi-k1.5": {
        "provider": "openrouter",
        "model_id": "moonshotai/kimi-k1.5",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 16000,
    },

    # =========================================================================
    # Alibaba Qwen-VL (22 models) - via OpenRouter
    # =========================================================================
    # Qwen3-VL MoE
    "qwen/qwen3-vl-235b-a22b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-235b-a22b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-235b-a22b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-235b-a22b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    "qwen/qwen3-vl-30b-a3b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-30b-a3b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-30b-a3b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-30b-a3b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    # Qwen3-VL Dense
    "qwen/qwen3-vl-32b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-32b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-32b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-32b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    "qwen/qwen3-vl-8b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-8b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-8b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-8b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    "qwen/qwen3-vl-4b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-4b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-4b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-4b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    "qwen/qwen3-vl-2b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-2b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen3-vl-2b-thinking": {
        "provider": "openrouter",
        "model_id": "qwen/qwen3-vl-2b-thinking",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 32000,
        "thinking_type": "builtin",
    },
    # Qwen2.5-VL
    "qwen/qwen2.5-vl-72b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-72b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen2.5-vl-32b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-32b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen2.5-vl-32b-instruct:free": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-32b-instruct:free",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen2.5-vl-7b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-7b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen2.5-vl-3b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-vl-3b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    # Qwen2.5-Omni
    "qwen/qwen2.5-omni-7b": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-omni-7b",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    "qwen/qwen2.5-omni-3b": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2.5-omni-3b",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },
    # Qwen2-VL (Legacy)
    "qwen/qwen2-vl-72b-instruct": {
        "provider": "openrouter",
        "model_id": "qwen/qwen2-vl-72b-instruct",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32000,
    },

    # =========================================================================
    # xAI Grok (7 models) - OpenRouter
    # =========================================================================
    "x-ai/grok-4": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 131072,
        "thinking_type": "native",
    },
    "x-ai/grok-4-fast": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4-fast",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 131072,
        "thinking_type": "native",
    },
    "x-ai/grok-4-fast:nitro": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4-fast:nitro",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 131072,
    },
    "x-ai/grok-4.1-fast": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4.1-fast",
        "supports_seed": True,
        "supports_thinking": True,
        "supports_vision": True,
        "max_tokens": 131072,
        "thinking_type": "native",
    },
    "x-ai/grok-4.1-fast:nitro": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-4.1-fast:nitro",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 131072,
    },
    "x-ai/grok-2-vision-1212": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-2-vision-1212",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 32768,
    },
    "x-ai/grok-vision-beta": {
        "provider": "openrouter",
        "model_id": "x-ai/grok-vision-beta",
        "supports_seed": True,
        "supports_thinking": False,
        "supports_vision": True,
        "max_tokens": 8192,
    },
}


def get_model_info(model_name: str) -> Dict[str, Any]:
    """Get information about a model.

    Args:
        model_name: Unified model name (e.g., "anthropic/claude-sonnet-4").

    Returns:
        Dictionary with model metadata.

    Raises:
        ValueError: If model is not in registry.
    """
    if model_name not in MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Available models: {list(MODEL_REGISTRY.keys())}"
        )
    return MODEL_REGISTRY[model_name]


def get_model_capabilities(model_name: str) -> ModelCapabilities:
    """Get capabilities object for a model.

    Args:
        model_name: Unified model name.

    Returns:
        ModelCapabilities dataclass instance.
    """
    info = get_model_info(model_name)
    return ModelCapabilities(
        supports_seed=info.get("supports_seed", False),
        supports_thinking=info.get("supports_thinking", False),
        supports_vision=info.get("supports_vision", True),
        max_tokens=info.get("max_tokens", 16000),
        thinking_levels=info.get("thinking_levels"),
        thinking_type=info.get("thinking_type"),
    )


def list_models(provider: Optional[str] = None) -> List[str]:
    """List all available models, optionally filtered by provider.

    Args:
        provider: Optional provider filter ("gemini", "claude", "openai", "openrouter").

    Returns:
        List of model names.
    """
    if provider is None:
        return list(MODEL_REGISTRY.keys())
    return [
        name for name, info in MODEL_REGISTRY.items()
        if info.get("provider") == provider
    ]


def list_providers() -> List[str]:
    """List all available providers."""
    return ["gemini", "claude", "openai", "openrouter"]


def get_models_with_seed_support() -> List[str]:
    """Get list of models that support deterministic seed parameter."""
    return [
        name for name, info in MODEL_REGISTRY.items()
        if info.get("supports_seed", False)
    ]


def get_models_with_thinking() -> List[str]:
    """Get list of models that support thinking/reasoning modes."""
    return [
        name for name, info in MODEL_REGISTRY.items()
        if info.get("supports_thinking", False)
    ]
