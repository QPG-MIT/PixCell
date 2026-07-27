"""
Unified Model Client for HOMI.

This package provides a unified interface to interact with multiple AI model providers
for GDS generation. Supported providers:

- Google Gemini (direct API) - 5 models
- Anthropic Claude (direct API) - 9 models
- OpenAI GPT (direct API) - 10 models
- Meta Llama (via OpenRouter) - 4 models
- Moonshot Kimi (via OpenRouter) - 4 models
- Alibaba Qwen-VL (via OpenRouter) - 22 models

Total: 54 vision-language models

Usage:
    from homi.model_client import create_client, ModelConfig, VisionMessage

    # Create a client for any model
    client, model_id = create_client("anthropic/claude-sonnet-4.5")

    # Generate a response
    response = client.generate(
        messages=[VisionMessage(role="user", text="Describe this device", images=[img_bytes])],
        config=ModelConfig(temperature=1.0, thinking_mode="high"),
        model_id=model_id
    )

    print(response.text)
"""

from typing import Tuple, TYPE_CHECKING

from .base import ModelClient, get_provider_for_model
from .registry import (
    MODEL_REGISTRY,
    get_model_info,
    get_model_capabilities,
    list_models,
    list_providers,
    get_models_with_seed_support,
    get_models_with_thinking,
)
from .types import (
    ModelConfig,
    VisionMessage,
    GenerationResponse,
    ModelCapabilities,
)

# Lazy imports for backends to avoid requiring all SDKs at import time
if TYPE_CHECKING:
    from .backends.gemini import GeminiBackend
    from .backends.claude import ClaudeBackend
    from .backends.openai import OpenAIBackend
    from .backends.openrouter import OpenRouterBackend


def create_client(model_name: str) -> Tuple[ModelClient, str]:
    """Create a model client from unified model name.

    This is the main factory function for creating model clients. It automatically
    selects the appropriate backend based on the model name.

    Args:
        model_name: Unified model name in format "provider/model-name".
            Examples:
                - "gemini/gemini-3-flash-preview"
                - "anthropic/claude-sonnet-4.5"
                - "openai/gpt-5.2"
                - "meta-llama/llama-4-maverick"
                - "qwen/qwen3-vl-235b-a22b-thinking"

    Returns:
        Tuple of (client instance, model_id for API call).

    Raises:
        ValueError: If model name is not in the registry.
        ImportError: If required SDK for the provider is not installed.

    Example:
        # Create a Claude client
        client, model_id = create_client("anthropic/claude-sonnet-4.5")

        # Create a Gemini client
        client, model_id = create_client("gemini/gemini-3-flash-preview")

        # Create an OpenRouter client for Llama
        client, model_id = create_client("meta-llama/llama-4-maverick")
    """
    if model_name not in MODEL_REGISTRY:
        available = ", ".join(list(MODEL_REGISTRY.keys())[:10])
        raise ValueError(
            f"Unknown model: {model_name}. "
            f"Available models include: {available}... "
            f"({len(MODEL_REGISTRY)} total). "
            f"Use list_models() to see all options."
        )

    model_info = MODEL_REGISTRY[model_name]
    provider = model_info["provider"]
    model_id = model_info["model_id"]

    # Lazy import backends to avoid requiring all SDKs at import time
    if provider == "gemini":
        from .backends.gemini import GeminiBackend
        return GeminiBackend(), model_id
    elif provider == "claude":
        from .backends.claude import ClaudeBackend
        return ClaudeBackend(), model_id
    elif provider == "openai":
        from .backends.openai import OpenAIBackend
        return OpenAIBackend(), model_id
    elif provider == "openrouter":
        from .backends.openrouter import OpenRouterBackend
        return OpenRouterBackend(), model_id
    else:
        raise ValueError(f"Unknown provider: {provider}")


def supports_seed(model_name: str) -> bool:
    """Check if a model supports deterministic seed parameter.

    Args:
        model_name: Unified model name.

    Returns:
        True if the model supports seed parameter.
    """
    caps = get_model_capabilities(model_name)
    return caps.supports_seed


def supports_thinking(model_name: str) -> bool:
    """Check if a model supports thinking/reasoning modes.

    Args:
        model_name: Unified model name.

    Returns:
        True if the model supports thinking modes.
    """
    caps = get_model_capabilities(model_name)
    return caps.supports_thinking


__all__ = [
    # Factory function
    "create_client",

    # Types
    "ModelConfig",
    "VisionMessage",
    "GenerationResponse",
    "ModelCapabilities",

    # Registry functions
    "MODEL_REGISTRY",
    "get_model_info",
    "get_model_capabilities",
    "list_models",
    "list_providers",
    "get_models_with_seed_support",
    "get_models_with_thinking",

    # Utility functions
    "supports_seed",
    "supports_thinking",
    "get_provider_for_model",

    # Base class (for advanced usage / subclassing)
    "ModelClient",
]


# Lazy accessor for backend classes
def __getattr__(name):
    """Lazy load backend classes."""
    if name == "GeminiBackend":
        from .backends.gemini import GeminiBackend
        return GeminiBackend
    elif name == "ClaudeBackend":
        from .backends.claude import ClaudeBackend
        return ClaudeBackend
    elif name == "OpenAIBackend":
        from .backends.openai import OpenAIBackend
        return OpenAIBackend
    elif name == "OpenRouterBackend":
        from .backends.openrouter import OpenRouterBackend
        return OpenRouterBackend
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
