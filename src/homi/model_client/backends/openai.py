"""
OpenAI GPT backend using the openai SDK (Responses API).

This backend supports:
- Reasoning with configurable effort levels
- Multi-turn conversations with vision
- Image input via data URLs
"""

import base64
import os
from typing import List

from openai import OpenAI

from ..base import ModelClient
from ..types import GenerationResponse, ModelConfig, VisionMessage


class OpenAIBackend(ModelClient):
    """OpenAI GPT backend using openai SDK with Responses API.

    Example:
        backend = OpenAIBackend()
        response = backend.generate(
            messages=[VisionMessage(role="user", text="Describe this image", images=[img_bytes])],
            config=ModelConfig(temperature=1.0, thinking_mode="high"),
            model_id="gpt-5.2"
        )
    """

    def __init__(self, api_key: str | None = None):
        """Initialize the OpenAI backend.

        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )
        self.client = OpenAI(api_key=self.api_key)

    @property
    def provider_name(self) -> str:
        return "openai"

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
        """Generate a response from OpenAI GPT.

        Args:
            messages: Conversation history with optional images.
            config: Generation configuration.
            model_id: OpenAI model ID (e.g., "gpt-5.2").

        Returns:
            GenerationResponse with the model's output.
        """
        # Build input in OpenAI responses API format
        openai_input = []
        for msg in messages:
            content = []

            # Add images as data URLs
            for i, img_bytes in enumerate(msg.images):
                mime_type = (
                    msg.image_mime_types[i]
                    if i < len(msg.image_mime_types)
                    else "image/png"
                )
                b64 = base64.b64encode(img_bytes).decode("utf-8")
                content.append({
                    "type": "input_image",
                    "image_url": f"data:{mime_type};base64,{b64}"
                })

            # Add text
            content.append({
                "type": "input_text",
                "text": msg.text
            })

            # Map role for assistant responses
            if msg.role == "assistant":
                # For assistant messages in input, use output_text format
                openai_input.append({
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": msg.text}]
                })
            else:
                openai_input.append({
                    "role": msg.role,
                    "content": content
                })

        # Build request kwargs
        kwargs = {
            "model": model_id,
            "input": openai_input,
        }

        # Add reasoning if enabled
        if config.thinking_mode:
            kwargs["reasoning"] = {"effort": config.thinking_mode}

        # Generate response
        response = self.client.responses.create(**kwargs)

        # Extract text from response output
        text_parts = []
        for item in response.output:
            if item.type == "message":
                for content in item.content:
                    if content.type == "output_text":
                        text_parts.append(content.text)

        # Extract usage if available
        usage = None
        if hasattr(response, 'usage') and response.usage:
            usage = {
                "input_tokens": getattr(response.usage, 'input_tokens', 0),
                "output_tokens": getattr(response.usage, 'output_tokens', 0),
                "total_tokens": getattr(response.usage, 'total_tokens', 0),
            }

        return GenerationResponse(
            text="\n".join(text_parts),
            raw_response=response,
            usage=usage,
            model_id=model_id
        )
