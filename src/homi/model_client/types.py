"""
Core types for the unified model client.

This module provides data classes for model configuration, messages with vision support,
and generation responses that work across all providers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ModelConfig:
    """Configuration for a model generation request.

    Attributes:
        temperature: Sampling temperature (0.0-2.0). Higher = more random.
        max_tokens: Maximum tokens in the response.
        seed: Random seed for reproducibility (only works with supporting models).
        thinking_mode: Thinking/reasoning mode level ("high", "medium", "low", etc.).
        thinking_budget: Token budget for extended thinking (Claude-specific).
    """
    temperature: float = 1.0
    max_tokens: int = 16000
    seed: Optional[int] = None
    thinking_mode: Optional[str] = None
    thinking_budget: Optional[int] = None


@dataclass
class VisionMessage:
    """A message with optional image content for multi-turn conversations.

    Attributes:
        role: Message role - "user" or "assistant".
        text: The text content of the message.
        images: List of image bytes (PNG, JPEG, etc.).
        image_mime_types: MIME types for each image (defaults to "image/png").
    """
    role: str
    text: str
    images: List[bytes] = field(default_factory=list)
    image_mime_types: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate message structure."""
        if self.role not in ("user", "assistant", "model"):
            raise ValueError(f"Invalid role: {self.role}. Must be 'user' or 'assistant'.")
        # Ensure mime types match images
        if self.images and not self.image_mime_types:
            self.image_mime_types = ["image/png"] * len(self.images)
        elif len(self.image_mime_types) < len(self.images):
            # Pad with default
            self.image_mime_types.extend(
                ["image/png"] * (len(self.images) - len(self.image_mime_types))
            )


@dataclass
class GenerationResponse:
    """Unified response from any model.

    Attributes:
        text: The extracted text response from the model.
        raw_response: The original provider-specific response object.
        usage: Token usage statistics (varies by provider).
        thinking_content: Thinking/reasoning content if available.
        model_id: The model that generated this response.
    """
    text: str
    raw_response: Any
    usage: Optional[Dict[str, int]] = None
    thinking_content: Optional[str] = None
    model_id: Optional[str] = None


@dataclass
class ModelCapabilities:
    """Capabilities of a specific model.

    Attributes:
        supports_seed: Whether the model supports deterministic seed parameter.
        supports_thinking: Whether the model supports thinking/reasoning modes.
        supports_vision: Whether the model can process images.
        max_tokens: Maximum tokens the model can generate.
        thinking_levels: Available thinking levels (e.g., ["low", "medium", "high"]).
        thinking_type: Type of thinking config ("levels", "budget", "effort").
    """
    supports_seed: bool = False
    supports_thinking: bool = False
    supports_vision: bool = True
    max_tokens: int = 16000
    thinking_levels: Optional[List[str]] = None
    thinking_type: Optional[str] = None
