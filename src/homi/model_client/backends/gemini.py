"""
Google Gemini backend using the google.genai SDK.

This backend supports:
- Native seed parameter for reproducible generation
- Thinking modes with configurable levels
- Multi-turn conversations with vision
"""

import os
from typing import List

from google import genai
from google.genai import types

from ..base import ModelClient
from ..types import GenerationResponse, ModelConfig, VisionMessage


class GeminiBackend(ModelClient):
    """Google Gemini backend using google.genai SDK.

    Example:
        backend = GeminiBackend()
        response = backend.generate(
            messages=[VisionMessage(role="user", text="Describe this image", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, seed=1333, thinking_mode="high"),
            model_id="gemini-3-flash-preview"
        )
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the Gemini backend.

        Args:
            api_key: Gemini API key. If not provided, uses GEMINI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Gemini API key required. Set GEMINI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = genai.Client(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def supports_seed(self) -> bool:
        return True

    @property
    def supports_thinking(self) -> bool:
        return True

    def generate(
        self,
        messages: List[VisionMessage],
        config: ModelConfig,
        model_id: str
    ) -> GenerationResponse:
        """Generate a response from Gemini.

        Args:
            messages: Conversation history with optional images.
            config: Generation configuration.
            model_id: Gemini model ID (e.g., "gemini-3-flash-preview").

        Returns:
            GenerationResponse with the model's output.
        """
        # Build conversation history in Gemini format
        history = []
        for msg in messages:
            parts = []

            # Add images first (Gemini prefers images before text)
            for i, img_bytes in enumerate(msg.images):
                mime_type = (
                    msg.image_mime_types[i]
                    if i < len(msg.image_mime_types)
                    else "image/png"
                )
                parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))

            # Add text
            parts.append(types.Part.from_text(text=msg.text))

            # Map role - Gemini uses "model" instead of "assistant"
            role = "model" if msg.role == "assistant" else msg.role
            history.append(types.Content(role=role, parts=parts))

        # Build generation config
        gen_config_kwargs = {
            "temperature": config.temperature,
        }

        # Add seed if provided
        if config.seed is not None:
            gen_config_kwargs["seed"] = config.seed

        # Add thinking config if enabled
        # Gemini 3.x uses thinking_level (high/medium/low)
        # Gemini 2.5 uses thinking_budget (token count)
        if config.thinking_mode:
            # Import registry to check model's thinking type
            from ..registry import MODEL_REGISTRY
            model_key = f"gemini/{model_id}"
            model_info = MODEL_REGISTRY.get(model_key, {})
            thinking_type = model_info.get("thinking_type", "levels")

            if thinking_type == "budget":
                # Gemini 2.5 uses token budget (-1 = dynamic, or specific count)
                # Map "high" to max budget, "low" to small budget
                budget_range = model_info.get("thinking_budget_range", [128, 16384])
                if config.thinking_mode == "high":
                    budget = budget_range[1]  # Max tokens
                elif config.thinking_mode == "medium":
                    budget = (budget_range[0] + budget_range[1]) // 2
                elif config.thinking_mode == "low":
                    budget = budget_range[0]
                else:
                    budget = -1  # Dynamic
                gen_config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_budget=budget
                )
            else:
                # Gemini 3.x uses thinking levels
                gen_config_kwargs["thinking_config"] = types.ThinkingConfig(
                    thinking_level=config.thinking_mode
                )

        gen_config = types.GenerateContentConfig(**gen_config_kwargs)

        # Generate response
        response = self.client.models.generate_content(
            model=model_id,
            contents=history,
            config=gen_config
        )

        # Extract usage if available
        usage = None
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = {
                "input_tokens": getattr(response.usage_metadata, 'prompt_token_count', 0),
                "output_tokens": getattr(response.usage_metadata, 'candidates_token_count', 0),
                "total_tokens": getattr(response.usage_metadata, 'total_token_count', 0),
            }

        return GenerationResponse(
            text=response.text,
            raw_response=response,
            usage=usage,
            model_id=model_id
        )
