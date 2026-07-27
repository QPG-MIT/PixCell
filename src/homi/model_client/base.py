"""
Abstract base class for model clients.

All provider backends (Gemini, Claude, OpenAI, OpenRouter) inherit from this class
to provide a unified interface for model generation.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple

from .types import GenerationResponse, ModelConfig, VisionMessage


class ModelClient(ABC):
    """Abstract base class for AI model clients.

    All provider backends must implement this interface to ensure consistent
    behavior across different AI providers.

    Example usage:
        client = GeminiBackend()
        response = client.generate(
            messages=[VisionMessage(role="user", text="Hello", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, seed=1333),
            model_id="gemini-3-flash-preview"
        )
        print(response.text)
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (gemini, claude, openai, openrouter)."""
        pass

    @property
    def supports_seed(self) -> bool:
        """Whether this provider supports native seed parameter for reproducibility."""
        return False

    @property
    def supports_thinking(self) -> bool:
        """Whether this provider supports thinking/reasoning modes."""
        return False

    @abstractmethod
    def generate(
        self,
        messages: List[VisionMessage],
        config: ModelConfig,
        model_id: str
    ) -> GenerationResponse:
        """Generate a response from the model.

        Args:
            messages: List of messages forming the conversation history.
                     Each message can contain text and optional images.
            config: Generation configuration (temperature, seed, thinking mode, etc.).
            model_id: The specific model ID to use (provider-specific format).

        Returns:
            GenerationResponse with the model's text output and metadata.

        Raises:
            Exception: If the API call fails or returns an error.
        """
        pass

    def validate_config(self, config: ModelConfig) -> ModelConfig:
        """Validate and adjust config for this provider's capabilities.

        Override this method to handle provider-specific config requirements.

        Args:
            config: The requested configuration.

        Returns:
            Adjusted configuration compatible with this provider.
        """
        # Clear seed if not supported
        if not self.supports_seed and config.seed is not None:
            # Log warning? For now, just clear it
            config = ModelConfig(
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                seed=None,
                thinking_mode=config.thinking_mode if self.supports_thinking else None,
                thinking_budget=config.thinking_budget
            )
        return config


def get_provider_for_model(model_name: str) -> str:
    """Extract provider from unified model name.

    Args:
        model_name: Unified model name (e.g., "anthropic/claude-sonnet-4").

    Returns:
        Provider name (e.g., "anthropic").

    Raises:
        ValueError: If model name format is invalid.
    """
    if "/" not in model_name:
        raise ValueError(
            f"Invalid model name format: {model_name}. "
            "Expected format: 'provider/model-name' (e.g., 'anthropic/claude-sonnet-4')"
        )
    return model_name.split("/")[0]
