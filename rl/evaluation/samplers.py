"""Lazy, one-completion Tinker samplers for frozen baseline evaluations.

This module owns transport and renderer bookkeeping only. Callers supply the
already-built cookbook ``Message`` conversation, and the evaluation runner owns
task selection, persistence, and geometry scoring.
"""

from __future__ import annotations

import base64
import io
import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any, Protocol


QWEN_MODEL = "Qwen/Qwen3.6-35B-A3B"
INKLING_MODEL = "thinkingmachines/Inkling"
QWEN_RENDERERS = frozenset({"qwen3_5", "qwen3_5_disable_thinking"})
INKLING_RENDERER = "tml_v0"
TML_RENDERERS_VERSION = "0.1.0"


class SamplerConfigurationError(ValueError):
    """A target or sampling request is not fully and unambiguously bound."""


class SamplingProtocolError(RuntimeError):
    """Tinker returned a response outside the one-completion contract."""


@dataclass(frozen=True)
class SamplerTarget:
    """Exact model location plus the renderer needed to interpret its tokens.

    ``model_name`` identifies the base family for tokenizer/renderer loading.
    Exactly one of ``base_model`` and ``model_path`` is the Tinker sampling
    location. A checkpoint therefore remains explicitly tied to its base
    family instead of trying to infer that family from an opaque URI.
    """

    model_name: str
    renderer_name: str
    base_model: str | None = None
    model_path: str | None = None
    effort: float | None = None

    def __post_init__(self) -> None:
        locations = int(self.base_model is not None) + int(self.model_path is not None)
        if locations != 1:
            raise SamplerConfigurationError("exactly one of base_model or model_path must be set")
        if self.base_model is not None and self.base_model != self.model_name:
            raise SamplerConfigurationError(
                "base_model must exactly match model_name; aliases are not accepted"
            )
        if self.model_path is not None and not self.model_path.strip():
            raise SamplerConfigurationError("model_path must be non-empty")

        if self.model_name == QWEN_MODEL:
            if self.renderer_name not in QWEN_RENDERERS:
                raise SamplerConfigurationError(
                    f"{QWEN_MODEL} requires one of {sorted(QWEN_RENDERERS)}"
                )
            if self.effort is not None:
                raise SamplerConfigurationError(
                    "effort is a TML/Inkling setting and must be omitted for Qwen"
                )
            return

        if self.model_name == INKLING_MODEL:
            if self.renderer_name != INKLING_RENDERER:
                raise SamplerConfigurationError(
                    f"{INKLING_MODEL} requires renderer_name={INKLING_RENDERER!r}"
                )
            if (
                self.effort is None
                or isinstance(self.effort, bool)
                or not math.isfinite(self.effort)
                or not 0.0 <= self.effort < 1.0
            ):
                raise SamplerConfigurationError(
                    "Inkling effort must be an explicit finite number in [0, 1)"
                )
            return

        raise SamplerConfigurationError(f"unsupported model_name: {self.model_name!r}")

    @property
    def client_kwargs(self) -> dict[str, str]:
        if self.base_model is not None:
            return {"base_model": self.base_model}
        assert self.model_path is not None
        return {"model_path": self.model_path}


@dataclass(frozen=True)
class SamplingRequest:
    """Every stochastic and length control sent to Tinker, with no defaults."""

    max_tokens: int
    temperature: float
    top_p: float
    seed: int

    def __post_init__(self) -> None:
        if (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
        ):
            raise SamplerConfigurationError("max_tokens must be a positive integer")
        if (
            isinstance(self.temperature, bool)
            or not math.isfinite(self.temperature)
            or self.temperature < 0.0
        ):
            raise SamplerConfigurationError("temperature must be a finite non-negative number")
        if (
            isinstance(self.top_p, bool)
            or not math.isfinite(self.top_p)
            or not 0.0 < self.top_p <= 1.0
        ):
            raise SamplerConfigurationError("top_p must be finite and in (0, 1]")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise SamplerConfigurationError("seed must be a non-negative integer")


@dataclass(frozen=True)
class SampleResult:
    """One sampled completion with transport and channel accounting.

    Qwen channel counts are exact sampled-token partitions. Inkling's TML
    parser identifies the channels exactly, but its public parser does not
    expose per-channel token spans. Its ``*_estimate`` fields therefore count
    only re-encoded channel text and deliberately exclude TML framing tokens.
    """

    prompt_tokens: int
    completion_tokens: int
    stop_reason: str
    cap_hit: bool
    raw_text: str
    completion_text: str
    reasoning_text: str | None
    answer_text: str
    reasoning_tokens_exact: int | None
    answer_tokens_exact: int | None
    reasoning_tokens_estimate: int | None
    answer_tokens_estimate: int | None
    channel_token_count_basis: str
    channel_parse_complete: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class _DecodedCompletion:
    raw_text: str
    completion_text: str
    reasoning_text: str | None
    answer_text: str
    reasoning_tokens_exact: int | None
    answer_tokens_exact: int | None
    reasoning_tokens_estimate: int | None
    answer_tokens_estimate: int | None
    channel_token_count_basis: str
    channel_parse_complete: bool


class _Codec(Protocol):
    def build_prompt(self, messages: Sequence[Any]) -> Any: ...

    def stop_sequences(self) -> list[int]: ...

    def decode(self, tokens: Sequence[int]) -> _DecodedCompletion: ...


class _QwenCodec:
    def __init__(self, renderer: Any, tokenizer: Any, renderer_name: str) -> None:
        self._renderer = renderer
        self._tokenizer = tokenizer
        self._renderer_name = renderer_name
        self._think_close = list(tokenizer.encode("</think>", add_special_tokens=False))
        if not self._think_close:
            raise SamplingProtocolError("Qwen tokenizer produced no </think> tokens")

    @classmethod
    def load(cls, target: SamplerTarget) -> _QwenCodec:
        from tinker_cookbook.image_processing_utils import get_image_processor
        from tinker_cookbook.renderers import get_renderer
        from tinker_cookbook.tokenizer_utils import get_tokenizer

        tokenizer = get_tokenizer(target.model_name)
        image_processor = get_image_processor(target.model_name)
        renderer = get_renderer(
            target.renderer_name,
            tokenizer,
            image_processor,
            model_name=target.model_name,
        )
        return cls(renderer, tokenizer, target.renderer_name)

    def build_prompt(self, messages: Sequence[Any]) -> Any:
        return self._renderer.build_generation_prompt(list(messages))

    def stop_sequences(self) -> list[int]:
        return list(self._renderer.get_stop_sequences())

    @staticmethod
    def _first_subsequence(tokens: Sequence[int], needle: Sequence[int]) -> int | None:
        limit = len(tokens) - len(needle) + 1
        for index in range(max(0, limit)):
            if list(tokens[index : index + len(needle)]) == list(needle):
                return index
        return None

    def decode(self, tokens: Sequence[int]) -> _DecodedCompletion:
        sampled = list(tokens)
        raw_text = str(self._tokenizer.decode(sampled))
        if self._renderer_name == "qwen3_5_disable_thinking":
            return _DecodedCompletion(
                raw_text=raw_text,
                completion_text=raw_text,
                reasoning_text="",
                answer_text=raw_text,
                reasoning_tokens_exact=0,
                answer_tokens_exact=len(sampled),
                reasoning_tokens_estimate=None,
                answer_tokens_estimate=None,
                channel_token_count_basis=("qwen_disabled_thinking_all_sampled_tokens_are_answer"),
                channel_parse_complete=True,
            )

        close_at = self._first_subsequence(sampled, self._think_close)
        if close_at is None:
            # The generation prompt has already opened the thinking channel.
            # Until </think> is sampled, every sampled token is in that channel.
            return _DecodedCompletion(
                raw_text=raw_text,
                completion_text=f"<think>\n{raw_text}",
                reasoning_text=raw_text,
                answer_text="",
                reasoning_tokens_exact=len(sampled),
                answer_tokens_exact=0,
                reasoning_tokens_estimate=None,
                answer_tokens_estimate=None,
                channel_token_count_basis=("qwen_thinking_open_channel_without_closing_delimiter"),
                channel_parse_complete=False,
            )

        answer_at = close_at + len(self._think_close)
        reasoning_tokens = sampled[:close_at]
        answer_tokens = sampled[answer_at:]
        reasoning_text = str(self._tokenizer.decode(reasoning_tokens))
        answer_text = str(self._tokenizer.decode(answer_tokens)).lstrip()
        return _DecodedCompletion(
            raw_text=raw_text,
            completion_text=f"<think>\n{reasoning_text}</think>\n{answer_text}",
            reasoning_text=reasoning_text,
            answer_text=answer_text,
            reasoning_tokens_exact=answer_at,
            answer_tokens_exact=len(sampled) - answer_at,
            reasoning_tokens_estimate=None,
            answer_tokens_estimate=None,
            channel_token_count_basis=(
                "qwen_sampled_tokens_partitioned_at_first_think_close_"
                "closing_delimiter_assigned_to_reasoning"
            ),
            channel_parse_complete=True,
        )


def _pil_to_data_uri(image: Any) -> str:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    payload = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{payload}"


def _normalize_tml_media(messages: Sequence[Any]) -> list[dict[str, Any]]:
    """Convert cookbook ImagePart values to the OSS image_url shape TML reads."""

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
                        "TML ImagePart.image must be a path/data URI string or PIL image"
                    )
                parts.append({"type": "image_url", "image_url": {"url": url}})
            else:
                parts.append(part)
        normalized.append({**item, "content": parts})
    return normalized


class _InklingCodec:
    def __init__(self, native_renderer: Any, tokenizer: Any, effort: float) -> None:
        self._renderer = native_renderer
        self._tokenizer = tokenizer
        self._effort = effort

    @classmethod
    def load(cls, target: SamplerTarget) -> _InklingCodec:
        try:
            installed = version("tml-renderers")
        except PackageNotFoundError as exc:
            raise SamplerConfigurationError(
                f"tml-renderers=={TML_RENDERERS_VERSION} is required for Inkling"
            ) from exc
        if installed != TML_RENDERERS_VERSION:
            raise SamplerConfigurationError(
                f"Inkling requires tml-renderers=={TML_RENDERERS_VERSION}; found {installed}"
            )

        from tml_renderers import tokenizers as tml_tokenizers
        from tml_renderers import v0 as tml_v0

        tokenizer = tml_tokenizers.o200k_base_chat()
        return cls(tml_v0.Renderer(tokenizer), tokenizer, float(target.effort))

    def _render_input(self, messages: Sequence[Any]) -> list[Any]:
        from tml_renderers import chat as tml_chat

        return list(tml_chat.OpenAIMessage.from_oss_messages(_normalize_tml_media(messages)))

    def build_prompt(self, messages: Sequence[Any]) -> Any:
        from tml_renderers import tinker as tml_tinker

        spans, _parser = self._renderer.render_for_completion_with_effort(
            self._render_input(messages),
            self._effort,
        )
        return tml_tinker.token_spans_to_tinker_model_input(spans)

    def stop_sequences(self) -> list[int]:
        return list(self._renderer.stop())

    def decode(self, tokens: Sequence[int]) -> _DecodedCompletion:
        from tml_renderers import chat as tml_chat

        sampled = list(tokens)
        raw_text = str(self._tokenizer.decode(sampled))
        _spans, parser = self._renderer.render_for_completion([])
        try:
            parsed = list(parser.parse_tokens(sampled))
        except Exception:
            return _DecodedCompletion(
                raw_text=raw_text,
                completion_text=raw_text,
                reasoning_text=None,
                answer_text="",
                reasoning_tokens_exact=None,
                answer_tokens_exact=None,
                reasoning_tokens_estimate=None,
                answer_tokens_estimate=None,
                channel_token_count_basis=("tml_parse_failed_no_channel_token_estimate"),
                channel_parse_complete=False,
            )

        reasoning_parts: list[str] = []
        answer_parts: list[str] = []
        saw_end = False
        for message in parsed:
            content = message.content
            if isinstance(content, tml_chat.ModelEndSampling):
                saw_end = True
            elif isinstance(content, tml_chat.Thinking):
                reasoning_parts.append(getattr(content, "text", str(content)))
            elif isinstance(content, tml_chat.Text):
                answer_parts.append(getattr(content, "text", str(content)))
            else:
                # Tools are not part of PixCell's contract. Keeping an unknown
                # model channel visible in the answer is safer than dropping it.
                answer_parts.append(str(content))

        reasoning_text = "\n".join(reasoning_parts)
        answer_text = "\n".join(answer_parts)
        reasoning_estimate = sum(
            len(self._tokenizer.encode_ordinary(part)) for part in reasoning_parts
        )
        answer_estimate = sum(len(self._tokenizer.encode_ordinary(part)) for part in answer_parts)
        completion_text = (
            "".join(f"<think>{part}</think>\n" for part in reasoning_parts) + answer_text
        )
        return _DecodedCompletion(
            raw_text=raw_text,
            completion_text=completion_text,
            reasoning_text=reasoning_text,
            answer_text=answer_text,
            reasoning_tokens_exact=None,
            answer_tokens_exact=None,
            reasoning_tokens_estimate=reasoning_estimate,
            answer_tokens_estimate=answer_estimate,
            channel_token_count_basis=(
                "estimate_o200k_encode_ordinary_of_parsed_channel_text_excludes_tml_framing"
            ),
            channel_parse_complete=saw_end,
        )


def _build_codec(target: SamplerTarget) -> _Codec:
    if target.model_name == QWEN_MODEL:
        return _QwenCodec.load(target)
    if target.model_name == INKLING_MODEL:
        return _InklingCodec.load(target)
    raise AssertionError(f"unvalidated sampler target: {target.model_name}")


def _default_service_client_factory() -> Any:
    import tinker

    return tinker.ServiceClient()


class TinkerSampler:
    """A lazy sampling client with a strict one-request/one-completion surface."""

    def __init__(
        self,
        target: SamplerTarget,
        *,
        service_client_factory: Callable[[], Any] | None = None,
    ) -> None:
        self.target = target
        self._service_client_factory = service_client_factory or _default_service_client_factory
        self._codec: _Codec | None = None
        self._sampling_client: Any | None = None

    def _get_codec(self) -> _Codec:
        if self._codec is None:
            self._codec = _build_codec(self.target)
        return self._codec

    def build_prompt(self, messages: Sequence[Any]) -> Any:
        if not messages:
            raise SamplerConfigurationError("messages must not be empty")
        return self._get_codec().build_prompt(messages)

    def _get_sampling_client(self) -> Any:
        if self._sampling_client is None:
            service = self._service_client_factory()
            self._sampling_client = service.create_sampling_client(**self.target.client_kwargs)
        return self._sampling_client

    async def sample(
        self,
        messages: Sequence[Any],
        request: SamplingRequest,
    ) -> SampleResult:
        """Sample exactly one completion; this is the first method that creates a client."""

        import tinker

        codec = self._get_codec()
        prompt = self.build_prompt(messages)
        response = await self._get_sampling_client().sample_async(
            prompt=prompt,
            num_samples=1,
            sampling_params=tinker.SamplingParams(
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                seed=request.seed,
                stop=codec.stop_sequences(),
            ),
        )
        sequences = list(response.sequences)
        if len(sequences) != 1:
            raise SamplingProtocolError(
                f"expected exactly one completion, received {len(sequences)}"
            )
        sequence = sequences[0]
        tokens = list(sequence.tokens)
        stop_reason = str(sequence.stop_reason)
        decoded = codec.decode(tokens)
        return SampleResult(
            prompt_tokens=int(prompt.length),
            completion_tokens=len(tokens),
            stop_reason=stop_reason,
            cap_hit=stop_reason == "length",
            raw_text=decoded.raw_text,
            completion_text=decoded.completion_text,
            reasoning_text=decoded.reasoning_text,
            answer_text=decoded.answer_text,
            reasoning_tokens_exact=decoded.reasoning_tokens_exact,
            answer_tokens_exact=decoded.answer_tokens_exact,
            reasoning_tokens_estimate=decoded.reasoning_tokens_estimate,
            answer_tokens_estimate=decoded.answer_tokens_estimate,
            channel_token_count_basis=decoded.channel_token_count_basis,
            channel_parse_complete=decoded.channel_parse_complete,
        )
