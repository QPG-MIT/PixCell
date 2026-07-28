"""Native TMLv0 runtime bridge for Inkling RL.

The pinned Tinker Cookbook predates native Inkling registration.  This module
provides the small adapter needed by a Track B launcher without changing any
other model path:

* the native ``o200k_base_chat`` tokenizer is registered only for
  ``thinkingmachines/Inkling``;
* TMLv0 receives one explicit, immutable thinking-effort value;
* sampled thinking and final-text channels remain separate; and
* every supervised rendering entrypoint fails closed.

Importing this module has no registration side effects.  A launcher must call
``install_inkling_runtime(effort=...)`` before constructing a Tinker training
client.  No environment variable supplies a default effort.
"""

from __future__ import annotations

import base64
import io
import logging
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, NoReturn

import tinker
from tml_renderers import chat as tml_chat
from tml_renderers import tinker as tml_tinker
from tml_renderers import tokenizers as tml_tokenizers
from tml_renderers import v0 as tml_v0

from tinker_cookbook.renderers import (
    Message,
    ParseTermination,
    RenderContext,
    Renderer,
    Role,
    TextPart,
    ThinkingPart,
    TrainOnWhat,
    get_registered_renderer_names,
    register_renderer,
)
from tinker_cookbook.renderers.base import RenderedMessage
from tinker_cookbook.tokenizer_utils import (
    get_registered_tokenizer_names,
    register_tokenizer,
)


logger = logging.getLogger(__name__)

MODEL_NAME = "thinkingmachines/Inkling"
RENDERER_NAME = "tml_v0"


class InklingRuntimeError(RuntimeError):
    """The requested runtime binding is absent, ambiguous, or incompatible."""


class InklingSupervisionDisabled(InklingRuntimeError):
    """Track B deliberately does not expose an Inkling SFT serialization path."""


@dataclass(frozen=True)
class InklingRuntimeBinding:
    model_name: str
    renderer_name: str
    effort: float


@dataclass(frozen=True)
class DecodedInklingResponse:
    """Channel-preserving interpretation of one sampled token sequence."""

    raw_text: str
    reasoning_text: str
    final_text: str
    termination: ParseTermination

    @property
    def channel_parse_complete(self) -> bool:
        return self.termination is ParseTermination.STOP_SEQUENCE


def _validate_effort(value: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) < 1.0
    ):
        raise ValueError("Inkling effort must be an explicit finite number in [0, 1)")
    return float(value)


class InklingTokenizer:
    """Cookbook-facing adapter over the native TML o200k chat tokenizer."""

    name_or_path = MODEL_NAME

    def __init__(self) -> None:
        self._tokenizer = tml_tokenizers.o200k_base_chat()

    @property
    def tml_tokenizer(self) -> tml_tokenizers.O200kBaseChatTokenizer:
        return self._tokenizer

    @property
    def eos_token(self) -> str:
        return self._tokenizer.eos_token

    def decode(self, token_ids: Sequence[int], **_kwargs: Any) -> str:
        return self._tokenizer.decode(list(token_ids))

    def encode(
        self,
        text: str,
        add_special_tokens: bool = False,
        **_kwargs: Any,
    ) -> list[int]:
        if add_special_tokens:
            raise NotImplementedError(
                "the Inkling tokenizer bridge encodes ordinary text only"
            )
        return self._tokenizer.encode_ordinary(text)


_TOKENIZER: InklingTokenizer | None = None
_RUNTIME_EFFORT: float | None = None


def _tokenizer_factory() -> InklingTokenizer:
    global _TOKENIZER
    if _TOKENIZER is None:
        _TOKENIZER = InklingTokenizer()
    return _TOKENIZER


def _pil_to_data_uri(image: Any) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def _normalize_media(messages: Sequence[Message]) -> list[dict[str, Any]]:
    """Convert Cookbook image parts to the OSS image shape TMLv0 consumes."""

    normalized: list[dict[str, Any]] = []
    for message in messages:
        item = dict(message)
        content = item.get("content")
        if not isinstance(content, list):
            normalized.append(item)
            continue
        parts: list[Any] = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "image":
                image = part.get("image")
                if isinstance(image, str):
                    url = image
                elif hasattr(image, "convert") and hasattr(image, "save"):
                    url = _pil_to_data_uri(image)
                else:
                    raise TypeError(
                        "TML ImagePart.image must be a string or PIL-compatible image"
                    )
                parts.append({"type": "image_url", "image_url": {"url": url}})
            else:
                parts.append(part)
        normalized.append({**item, "content": parts})
    return normalized


def _render_input(messages: Sequence[Message]) -> list[tml_chat.OpenAIMessage]:
    return list(
        tml_chat.OpenAIMessage.from_oss_messages(_normalize_media(messages))
    )


class InklingTmlV0Renderer(Renderer):
    """Sampling-only Cookbook renderer over native TMLv0 channels."""

    supports_streaming = False

    def __init__(self, tokenizer: InklingTokenizer, *, effort: float) -> None:
        if not isinstance(tokenizer, InklingTokenizer):
            raise TypeError("InklingTmlV0Renderer requires InklingTokenizer")
        super().__init__(tokenizer)
        self.effort = _validate_effort(effort)
        self._tml = tml_v0.Renderer(tokenizer.tml_tokenizer)

    def __reduce__(self) -> tuple[Any, tuple[float]]:
        # Do not depend on process-global Cookbook registries when an
        # EnvGroupBuilder is unpickled in a worker.
        return (_restore_renderer, (self.effort,))

    @property
    def has_extension_property(self) -> bool:
        return True

    def get_stop_sequences(self) -> list[int]:
        return list(self._tml.stop())

    def build_generation_prompt(
        self,
        messages: list[Message],
        role: Role = "assistant",
        prefill: str | None = None,
    ) -> tinker.ModelInput:
        if role != "assistant":
            raise NotImplementedError("TMLv0 generates assistant turns only")
        if prefill is not None:
            raise NotImplementedError("TMLv0 does not accept an assistant prefill")
        spans, _parser = self._tml.render_for_completion_with_effort(
            _render_input(messages),
            self.effort,
        )
        return tml_tinker.token_spans_to_tinker_model_input(spans)

    def _raw_decode(self, response: Sequence[int]) -> str:
        try:
            return str(self.tokenizer.decode(list(response)))
        except Exception:
            return ""

    def decode_response(self, response: Sequence[int]) -> DecodedInklingResponse:
        """Parse native channels without ever folding reasoning into final text."""

        sampled = list(response)
        raw_text = self._raw_decode(sampled)
        _spans, parser = self._tml.render_for_completion([])
        try:
            parsed = list(parser.parse_tokens(sampled))
        except Exception:
            return DecodedInklingResponse(
                raw_text=raw_text,
                reasoning_text="",
                final_text="",
                termination=ParseTermination.MALFORMED,
            )

        reasoning: list[str] = []
        final: list[str] = []
        saw_end = False
        unknown_channel = False
        for message in parsed:
            content = message.content
            if isinstance(content, tml_chat.ModelEndSampling):
                saw_end = True
            elif isinstance(content, tml_chat.Thinking):
                reasoning.append(getattr(content, "text", str(content)))
            elif isinstance(content, tml_chat.Text):
                final.append(getattr(content, "text", str(content)))
            else:
                # Tools and future channel types are outside PixCell's
                # image-to-code contract. Do not reinterpret them as code.
                unknown_channel = True

        termination = (
            ParseTermination.STOP_SEQUENCE
            if saw_end and not unknown_channel
            else ParseTermination.MALFORMED
        )
        return DecodedInklingResponse(
            raw_text=raw_text,
            reasoning_text="\n".join(reasoning),
            final_text="\n".join(final),
            termination=termination,
        )

    def parse_response(
        self,
        response: list[int],
    ) -> tuple[Message, ParseTermination]:
        decoded = self.decode_response(response)
        parts = []
        if decoded.reasoning_text:
            parts.append(
                ThinkingPart(type="thinking", thinking=decoded.reasoning_text)
            )
        if decoded.final_text:
            parts.append(TextPart(type="text", text=decoded.final_text))
        return (
            Message(role="assistant", content=parts),
            decoded.termination,
        )

    def decode_action_text(self, response: Sequence[int]) -> str:
        """Return only the final Text channel for code extraction."""

        return self.decode_response(response).final_text

    @staticmethod
    def _supervision_disabled() -> NoReturn:
        raise InklingSupervisionDisabled(
            "Track B Inkling is RL-only; supervised TML serialization is disabled"
        )

    def render_message(
        self,
        message: Message,
        ctx: RenderContext,
    ) -> RenderedMessage:
        del message, ctx
        self._supervision_disabled()

    def build_supervised_examples(
        self,
        messages: list[Message],
        train_on_what: TrainOnWhat = TrainOnWhat.LAST_ASSISTANT_TURN,
    ) -> list[tuple[tinker.ModelInput, Any]]:
        del messages, train_on_what
        self._supervision_disabled()

    def build_supervised_example(
        self,
        messages: list[Message],
        train_on_what: TrainOnWhat = TrainOnWhat.LAST_ASSISTANT_MESSAGE,
    ) -> tuple[tinker.ModelInput, Any]:
        del messages, train_on_what
        self._supervision_disabled()


def _restore_renderer(effort: float) -> InklingTmlV0Renderer:
    return InklingTmlV0Renderer(_tokenizer_factory(), effort=effort)


def _configured_effort() -> float:
    if _RUNTIME_EFFORT is None:
        raise InklingRuntimeError(
            "install_inkling_runtime(effort=...) must run before renderer creation"
        )
    return _RUNTIME_EFFORT


def _renderer_factory(
    tokenizer: Any,
    image_processor: Any = None,
) -> InklingTmlV0Renderer:
    if image_processor is not None:
        raise InklingRuntimeError(
            "Inkling tokenizes images natively and must not receive an HF image processor"
        )
    if not isinstance(tokenizer, InklingTokenizer):
        raise InklingRuntimeError(
            "the tml_v0 Track B registration is restricted to InklingTokenizer"
        )
    return InklingTmlV0Renderer(tokenizer, effort=_configured_effort())


def _is_inkling_model(model_name: str | None) -> bool:
    return bool(model_name) and str(model_name).split(":", 1)[0] == MODEL_NAME


def _patch_sdk_tokenizer_loader() -> None:
    """Route only Inkling SDK tokenizer requests to the native adapter."""

    import tinker.lib.public_interfaces.sampling_client as sampling_client
    import tinker.lib.public_interfaces.training_client as training_client

    def patch(module: Any) -> None:
        original = module._load_tokenizer_from_model_info
        if getattr(original, "_pixcell_track_b_inkling", False):
            return

        def inkling_aware(model_name: str, tokenizer_id: str | None = None):
            if _is_inkling_model(model_name):
                return _tokenizer_factory()
            return original(model_name, tokenizer_id)

        inkling_aware._pixcell_track_b_inkling = True
        module._load_tokenizer_from_model_info = inkling_aware

    patch(sampling_client)
    patch(training_client)
    logger.info("installed Inkling-only Tinker SDK tokenizer bridge")


def install_inkling_runtime(*, effort: float) -> InklingRuntimeBinding:
    """Install one immutable Inkling runtime binding for this process.

    Repeating the same binding is idempotent.  Attempting to change effort
    after registration fails rather than silently changing prompt identity.
    """

    global _RUNTIME_EFFORT
    resolved = _validate_effort(effort)
    if _RUNTIME_EFFORT is not None:
        if resolved != _RUNTIME_EFFORT:
            raise InklingRuntimeError(
                f"Inkling effort is already bound to {_RUNTIME_EFFORT}; "
                f"refusing {resolved}"
            )
        _patch_sdk_tokenizer_loader()
        return InklingRuntimeBinding(MODEL_NAME, RENDERER_NAME, resolved)

    if MODEL_NAME in get_registered_tokenizer_names():
        raise InklingRuntimeError(
            f"tokenizer {MODEL_NAME!r} was registered before the Track B bridge"
        )
    if RENDERER_NAME in get_registered_renderer_names():
        raise InklingRuntimeError(
            f"renderer {RENDERER_NAME!r} was registered before the Track B bridge"
        )

    _RUNTIME_EFFORT = resolved
    register_tokenizer(MODEL_NAME, _tokenizer_factory)
    register_renderer(RENDERER_NAME, _renderer_factory)
    _patch_sdk_tokenizer_loader()
    return InklingRuntimeBinding(MODEL_NAME, RENDERER_NAME, resolved)
