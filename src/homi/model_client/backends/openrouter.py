"""
OpenRouter backend for accessing models via OpenRouter API.

This backend provides access to:
- Meta Llama models
- Moonshot Kimi models
- Alibaba Qwen-VL models

Uses the OpenAI SDK with a custom base URL.
"""

import base64
import os
from typing import List

from openai import OpenAI

from ..base import ModelClient
from ..types import GenerationResponse, ModelConfig, VisionMessage


class OpenRouterBackend(ModelClient):
    """OpenRouter backend using openai SDK with custom base URL.

    Provides access to various models via OpenRouter's unified API:
    - Meta Llama (llama-4-maverick, llama-4-scout, etc.)
    - Moonshot Kimi (kimi-vl-a3b-instruct, kimi-vl-a3b-thinking, etc.)
    - Alibaba Qwen-VL (qwen3-vl-235b, qwen2.5-vl-72b, etc.)

    Example:
        backend = OpenRouterBackend()
        response = backend.generate(
            messages=[VisionMessage(role="user", text="Describe this image", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, seed=1333),
            model_id="meta-llama/llama-4-maverick"
        )
    """

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str | None = None,
        site_url: str = "https://homi.dev",
        site_name: str = "HOMI"
    ):
        """Initialize the OpenRouter backend.

        Args:
            api_key: OpenRouter API key. If not provided, uses OPENROUTER_API_KEY env var.
            site_url: Site URL for OpenRouter attribution/rankings.
            site_name: Site name for OpenRouter attribution/rankings.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key required. Set OPENROUTER_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(
            base_url=self.OPENROUTER_BASE_URL,
            api_key=self.api_key,
            default_headers={
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            }
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def supports_seed(self) -> bool:
        return True  # OpenRouter supports seed parameter

    @property
    def supports_thinking(self) -> bool:
        return False  # Thinking is model-specific, not provider-level

    def generate(
        self,
        messages: List[VisionMessage],
        config: ModelConfig,
        model_id: str
    ) -> GenerationResponse:
        """Generate a response via OpenRouter.

        Args:
            messages: Conversation history with optional images.
            config: Generation configuration.
            model_id: OpenRouter model ID (e.g., "meta-llama/llama-4-maverick").

        Returns:
            GenerationResponse with the model's output.
        """
        # Build messages in OpenAI chat format (OpenRouter compatible)
        openai_messages = []
        for msg in messages:
            content = []

            # Add text first (OpenRouter recommends text before images)
            content.append({
                "type": "text",
                "text": msg.text
            })

            # Add images as data URLs
            for i, img_bytes in enumerate(msg.images):
                mime_type = (
                    msg.image_mime_types[i]
                    if i < len(msg.image_mime_types)
                    else "image/png"
                )
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{b64}"
                    }
                })

            openai_messages.append({
                "role": msg.role,
                "content": content
            })

        # Build request kwargs
        kwargs = {
            "model": model_id,
            "messages": openai_messages,
            "temperature": config.temperature,
        }

        # Add seed if provided (OpenRouter supports this)
        if config.seed is not None:
            kwargs["seed"] = config.seed

        # Add max_tokens if specified
        if config.max_tokens:
            kwargs["max_tokens"] = config.max_tokens

        # Generate response
        response = self.client.chat.completions.create(**kwargs)

        # Extract text from response
        text = ""
        if response.choices and len(response.choices) > 0:
            text = response.choices[0].message.content or ""

        # Extract usage if available
        usage = None
        if response.usage:
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }

        return GenerationResponse(
            text=text,
            raw_response=response,
            usage=usage,
            model_id=model_id
        )
