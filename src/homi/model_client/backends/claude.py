"""
Anthropic Claude backend using the anthropic SDK.

This backend supports:
- Extended thinking with configurable token budget
- Multi-turn conversations with vision
- Image input via base64 encoding
"""

import base64
import os
from typing import List

import anthropic

from ..base import ModelClient
from ..types import GenerationResponse, ModelConfig, VisionMessage


class ClaudeBackend(ModelClient):
    """Anthropic Claude backend using anthropic SDK.

    Example (Opus 4.5 with effort beta):
        backend = ClaudeBackend()
        response = backend.generate(
            messages=[VisionMessage(role="user", text="Describe this image", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, thinking_mode="enabled", thinking_budget=32000),
            model_id="claude-opus-4-5-20251101"
        )
        # Uses: betas=["effort-2025-11-24"], output_config={"effort": "high"}, max_tokens=64000

    Example (Other Claude models):
        response = backend.generate(
            messages=[VisionMessage(role="user", text="Describe this image", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, thinking_mode="enabled", thinking_budget=30000),
            model_id="claude-sonnet-4-5-20250929"
        )
        # Uses: standard thinking API, max_tokens=30000
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Claude backend.

        Args:
            api_key: Anthropic API key. If not provided, uses ANTHROPIC_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Anthropic API key required. Set ANTHROPIC_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = anthropic.Anthropic(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def supports_seed(self) -> bool:
        return False

    @property
    def supports_thinking(self) -> bool:
        return True

    def generate(
        self,
        messages: List[VisionMessage],
        config: ModelConfig,
        model_id: str
    ) -> GenerationResponse:
        """Generate a response from Claude.

        Args:
            messages: Conversation history with optional images.
            config: Generation configuration.
            model_id: Claude model ID (e.g., "claude-sonnet-4-5-20250929").

        Returns:
            GenerationResponse with the model's output.
        """
        # Build messages in Claude format
        claude_messages = []
        for msg in messages:
            content = []

            # Add images
            for i, img_bytes in enumerate(msg.images):
                mime_type = (
                    msg.image_mime_types[i]
                    if i < len(msg.image_mime_types)
                    else "image/png"
                )
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": base64.b64encode(img_bytes).decode("utf-8")
                    }
                })

            # Add text
            content.append({
                "type": "text",
                "text": msg.text
            })

            claude_messages.append({
                "role": msg.role,
                "content": content
            })

        # Check if this is Opus 4.5 (uses beta effort API)
        is_opus_45 = model_id == "claude-opus-4-5-20251101"

        # Look up model's max_tokens limit from registry
        from ..registry import MODEL_REGISTRY
        registry_key = f"anthropic/{model_id}"
        # Also try without date suffix for lookup
        model_info = MODEL_REGISTRY.get(registry_key, {})
        if not model_info:
            # Try finding by model_id field
            for key, info in MODEL_REGISTRY.items():
                if info.get("model_id") == model_id:
                    model_info = info
                    break

        # Get model's max_tokens limit (default to 16000 if not found)
        model_max_tokens = model_info.get("max_tokens", 16000)

        # Cap requested max_tokens to model's limit
        requested_max_tokens = config.max_tokens or model_max_tokens
        actual_max_tokens = min(requested_max_tokens, model_max_tokens)

        # Build request kwargs
        kwargs = {
            "model": model_id,
            "messages": claude_messages,
            "max_tokens": actual_max_tokens,
        }

        if is_opus_45:
            # Opus 4.5: Use beta effort API
            if config.thinking_mode:
                kwargs["betas"] = ["effort-2025-11-24"]
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": config.thinking_budget or 32000
                }
                kwargs["output_config"] = {"effort": "high"}
        else:
            # Other Claude models: Standard thinking API
            if config.thinking_mode:
                # Cap thinking budget to be less than max_tokens (must be strictly less)
                max_thinking = actual_max_tokens - 1000  # Leave room for output
                thinking_budget = min(config.thinking_budget or 10000, max_thinking)
                kwargs["thinking"] = {
                    "type": "enabled",
                    "budget_tokens": thinking_budget
                }

        # Generate response
        # Extended thinking with large budgets requires streaming (>10 min timeout)
        if config.thinking_mode:
            # Use streaming for extended thinking requests
            text_parts = []
            thinking_parts = []
            usage = None

            if is_opus_45:
                # Opus 4.5 with beta effort API - use stream helper
                with self.client.beta.messages.stream(**kwargs) as stream:
                    response = stream.get_final_message()
            else:
                # Other models - use standard stream helper
                with self.client.messages.stream(**kwargs) as stream:
                    response = stream.get_final_message()

            # Extract text from response blocks (filter out thinking blocks)
            for block in response.content:
                if hasattr(block, 'text'):
                    text_parts.append(block.text)
                elif hasattr(block, 'thinking'):
                    thinking_parts.append(block.thinking)

            # Extract usage
            if response.usage:
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return GenerationResponse(
                text="\n".join(text_parts),
                raw_response=response,
                usage=usage,
                thinking_content="\n".join(thinking_parts) if thinking_parts else None,
                model_id=model_id
            )
        else:
            # Non-thinking requests can use synchronous API
            response = self.client.messages.create(**kwargs)

            # Extract text from response blocks
            text_parts = []
            for block in response.content:
                if hasattr(block, 'text'):
                    text_parts.append(block.text)

            # Extract usage
            usage = None
            if response.usage:
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                }

            return GenerationResponse(
                text="\n".join(text_parts),
                raw_response=response,
                usage=usage,
                thinking_content=None,
                model_id=model_id
            )
