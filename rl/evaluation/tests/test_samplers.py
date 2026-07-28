from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from rl.evaluation import samplers
from rl.evaluation.samplers import (
    INKLING_MODEL,
    QWEN_MODEL,
    SampleResult,
    SamplerConfigurationError,
    SamplerTarget,
    SamplingProtocolError,
    SamplingRequest,
    TinkerSampler,
)


def test_target_binds_exactly_one_location_and_renderer_contract() -> None:
    qwen = SamplerTarget(
        model_name=QWEN_MODEL,
        renderer_name="qwen3_5_disable_thinking",
        base_model=QWEN_MODEL,
    )
    assert qwen.client_kwargs == {"base_model": QWEN_MODEL}

    checkpoint = SamplerTarget(
        model_name=QWEN_MODEL,
        renderer_name="qwen3_5",
        model_path="tinker://run/sampler_weights/000001",
    )
    assert checkpoint.client_kwargs == {"model_path": "tinker://run/sampler_weights/000001"}

    with pytest.raises(SamplerConfigurationError, match="exactly one"):
        SamplerTarget(
            model_name=QWEN_MODEL,
            renderer_name="qwen3_5",
        )
    with pytest.raises(SamplerConfigurationError, match="exactly one"):
        SamplerTarget(
            model_name=QWEN_MODEL,
            renderer_name="qwen3_5",
            base_model=QWEN_MODEL,
            model_path="tinker://run/sampler_weights/1",
        )
    with pytest.raises(SamplerConfigurationError, match="exactly match"):
        SamplerTarget(
            model_name=QWEN_MODEL,
            renderer_name="qwen3_5",
            base_model="Qwen/Qwen3.6-35B-A3B-alias",
        )
    with pytest.raises(SamplerConfigurationError, match="requires one of"):
        SamplerTarget(
            model_name=QWEN_MODEL,
            renderer_name="qml_v0",
            base_model=QWEN_MODEL,
        )


def test_inkling_requires_explicit_valid_effort() -> None:
    target = SamplerTarget(
        model_name=INKLING_MODEL,
        renderer_name="tml_v0",
        base_model=INKLING_MODEL,
        effort=0.9,
    )
    assert target.effort == 0.9

    for effort in (None, -0.1, 1.0, float("nan"), True):
        with pytest.raises(SamplerConfigurationError, match="explicit finite"):
            SamplerTarget(
                model_name=INKLING_MODEL,
                renderer_name="tml_v0",
                base_model=INKLING_MODEL,
                effort=effort,
            )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_tokens": 0, "temperature": 1.0, "top_p": 1.0, "seed": 1}, "max_tokens"),
        ({"max_tokens": 1, "temperature": -0.1, "top_p": 1.0, "seed": 1}, "temperature"),
        ({"max_tokens": 1, "temperature": 1.0, "top_p": 0.0, "seed": 1}, "top_p"),
        ({"max_tokens": 1, "temperature": 1.0, "top_p": 1.0, "seed": -1}, "seed"),
    ],
)
def test_sampling_request_has_no_implicit_invalid_controls(kwargs, message) -> None:
    with pytest.raises(SamplerConfigurationError, match=message):
        SamplingRequest(**kwargs)


class _FakeTokenizer:
    _decode = {
        1: "plan ",
        2: "carefully",
        99: "</think>",
        3: "\n\n```python\npass\n```",
    }

    def encode(self, text, *, add_special_tokens):
        assert add_special_tokens is False
        assert text == "</think>"
        return [99]

    def decode(self, tokens):
        return "".join(self._decode[token] for token in tokens)


class _FakeRenderer:
    def build_generation_prompt(self, messages):
        return SimpleNamespace(length=17, messages=messages)

    def get_stop_sequences(self):
        return [777]


def test_qwen_channel_accounting_is_an_exact_sampled_token_partition() -> None:
    thinking = samplers._QwenCodec(_FakeRenderer(), _FakeTokenizer(), "qwen3_5")
    decoded = thinking.decode([1, 2, 99, 3])
    assert decoded.reasoning_text == "plan carefully"
    assert decoded.answer_text == "```python\npass\n```"
    assert decoded.reasoning_tokens_exact == 3
    assert decoded.answer_tokens_exact == 1
    assert decoded.reasoning_tokens_exact + decoded.answer_tokens_exact == 4
    assert decoded.channel_parse_complete is True

    truncated = thinking.decode([1, 2])
    assert truncated.reasoning_tokens_exact == 2
    assert truncated.answer_tokens_exact == 0
    assert truncated.answer_text == ""
    assert truncated.channel_parse_complete is False

    direct = samplers._QwenCodec(
        _FakeRenderer(),
        _FakeTokenizer(),
        "qwen3_5_disable_thinking",
    ).decode([3])
    assert direct.reasoning_tokens_exact == 0
    assert direct.answer_tokens_exact == 1
    assert direct.channel_parse_complete is True


def test_sampler_is_lazy_and_sends_exactly_one_explicit_sample(monkeypatch) -> None:
    tinker = pytest.importorskip(
        "tinker",
        reason="Tinker SDK env (rl/requirements-lock.txt) not installed",
    )

    calls: dict[str, object] = {"factory": 0}

    class FakeCodec:
        def build_prompt(self, messages):
            calls["messages"] = messages
            return SimpleNamespace(length=123)

        def stop_sequences(self):
            return [456]

        def decode(self, tokens):
            calls["decoded"] = list(tokens)
            return samplers._DecodedCompletion(
                raw_text="raw",
                completion_text="answer",
                reasoning_text="",
                answer_text="answer",
                reasoning_tokens_exact=0,
                answer_tokens_exact=len(tokens),
                reasoning_tokens_estimate=None,
                answer_tokens_estimate=None,
                channel_token_count_basis="test",
                channel_parse_complete=True,
            )

    class FakeSamplingClient:
        async def sample_async(self, **kwargs):
            calls["sample"] = kwargs
            return SimpleNamespace(
                sequences=[SimpleNamespace(tokens=[10, 11], stop_reason="length")]
            )

    class FakeService:
        def create_sampling_client(self, **kwargs):
            calls["client"] = kwargs
            return FakeSamplingClient()

    def factory():
        calls["factory"] = int(calls["factory"]) + 1
        return FakeService()

    monkeypatch.setattr(samplers, "_build_codec", lambda _target: FakeCodec())
    target = SamplerTarget(
        model_name=QWEN_MODEL,
        renderer_name="qwen3_5_disable_thinking",
        base_model=QWEN_MODEL,
    )
    sampler = TinkerSampler(target, service_client_factory=factory)
    assert calls["factory"] == 0

    # Prompt validation and tokenization remain zero-client operations.
    assert sampler.build_prompt([{"role": "user", "content": "prompt"}]).length == 123
    assert calls["factory"] == 0

    result = asyncio.run(
        sampler.sample(
            [{"role": "user", "content": "prompt"}],
            SamplingRequest(
                max_tokens=8192,
                temperature=1.0,
                top_p=0.95,
                seed=20260727,
            ),
        )
    )
    assert isinstance(result, SampleResult)
    assert calls["factory"] == 1
    assert calls["client"] == {"base_model": QWEN_MODEL}
    sample_call = calls["sample"]
    assert sample_call["num_samples"] == 1
    params = sample_call["sampling_params"]
    assert isinstance(params, tinker.SamplingParams)
    assert params.max_tokens == 8192
    assert params.temperature == 1.0
    assert params.top_p == 0.95
    assert params.seed == 20260727
    assert params.stop == [456]
    assert result.prompt_tokens == 123
    assert result.completion_tokens == 2
    assert result.stop_reason == "length"
    assert result.cap_hit is True
    assert result.raw_text == "raw"
    assert result.answer_text == "answer"


def test_sampler_rejects_backend_multi_completion(monkeypatch) -> None:
    pytest.importorskip(
        "tinker",
        reason="Tinker SDK env (rl/requirements-lock.txt) not installed",
    )

    class FakeCodec:
        def build_prompt(self, _messages):
            return SimpleNamespace(length=1)

        def stop_sequences(self):
            return [2]

    class FakeSamplingClient:
        async def sample_async(self, **_kwargs):
            return SimpleNamespace(
                sequences=[
                    SimpleNamespace(tokens=[1], stop_reason="stop"),
                    SimpleNamespace(tokens=[2], stop_reason="stop"),
                ]
            )

    class FakeService:
        def create_sampling_client(self, **_kwargs):
            return FakeSamplingClient()

    monkeypatch.setattr(samplers, "_build_codec", lambda _target: FakeCodec())
    sampler = TinkerSampler(
        SamplerTarget(
            model_name=QWEN_MODEL,
            renderer_name="qwen3_5",
            base_model=QWEN_MODEL,
        ),
        service_client_factory=FakeService,
    )
    with pytest.raises(SamplingProtocolError, match="exactly one"):
        asyncio.run(
            sampler.sample(
                [{"role": "user", "content": "prompt"}],
                SamplingRequest(
                    max_tokens=8,
                    temperature=1.0,
                    top_p=1.0,
                    seed=1,
                ),
            )
        )


def test_tml_renderer_uses_instance_effort_and_channel_estimates() -> None:
    pytest.importorskip("tml_renderers")
    pytest.importorskip(
        "tinker",
        reason="Tinker SDK env (rl/requirements-lock.txt) not installed",
    )
    from tml_renderers import chat as tml_chat
    from tml_renderers import tokenizers as tml_tokenizers
    from tml_renderers import v0 as tml_v0

    tokenizer = tml_tokenizers.o200k_base_chat()
    codec = samplers._InklingCodec(tml_v0.Renderer(tokenizer), tokenizer, 0.9)
    prompt = codec.build_prompt([{"role": "user", "content": "draw it"}])
    assert prompt.length > 0

    model = tml_chat.Author(tml_chat.AuthorKind.Model)
    messages = [
        tml_chat.Message(tml_chat.Thinking("inspect geometry"), model),
        tml_chat.Message(tml_chat.Text("```python\npass\n```"), model),
        tml_chat.Message(tml_chat.ModelEndSampling(), model),
    ]
    example = codec._renderer.render_for_sft(messages)[0]
    sampled: list[int] = []
    for wrapper in example.input_token_spans:
        inner = wrapper.span
        if hasattr(inner, "tokens"):
            sampled.extend(inner.tokens)

    decoded = codec.decode(sampled)
    assert decoded.reasoning_text == "inspect geometry"
    assert decoded.answer_text == "```python\npass\n```"
    assert decoded.reasoning_tokens_exact is None
    assert decoded.answer_tokens_exact is None
    assert decoded.reasoning_tokens_estimate == len(tokenizer.encode_ordinary("inspect geometry"))
    assert decoded.answer_tokens_estimate == len(tokenizer.encode_ordinary("```python\npass\n```"))
    assert decoded.channel_token_count_basis.startswith("estimate_")
    assert "excludes_tml_framing" in decoded.channel_token_count_basis
    assert decoded.channel_parse_complete is True


class _FakeTmlTokenizer:
    def __init__(self, raw_text: str) -> None:
        self.raw_text = raw_text

    def decode(self, tokens):
        assert list(tokens) == [11, 12]
        return self.raw_text

    def encode_ordinary(self, text):
        return list(text.encode("utf-8"))


class _FakeTmlParser:
    def __init__(self, parsed=None, error: Exception | None = None) -> None:
        self.parsed = [] if parsed is None else parsed
        self.error = error

    def parse_tokens(self, tokens):
        assert list(tokens) == [11, 12]
        if self.error is not None:
            raise self.error
        return self.parsed


class _FakeTmlRenderer:
    def __init__(self, parser: _FakeTmlParser) -> None:
        self.parser = parser

    def render_for_completion(self, messages):
        assert messages == []
        return [], self.parser


@pytest.mark.parametrize(
    ("parsed", "error", "expected_basis"),
    [
        (
            None,
            ValueError("truncated TML object"),
            "tml_parse_failed_raw_decode_fallback_channel_partition_unknown",
        ),
        (
            [],
            None,
            (
                "tml_parse_had_no_usable_channel_text_raw_decode_fallback_"
                "channel_partition_unknown"
            ),
        ),
    ],
)
def test_inkling_raw_decode_fallback_preserves_unparseable_completion(
    parsed,
    error,
    expected_basis,
) -> None:
    pytest.importorskip("tml_renderers")
    raw = "partial framing followed by ```python\nprint('recover me')\n```"
    codec = samplers._InklingCodec(
        _FakeTmlRenderer(_FakeTmlParser(parsed=parsed, error=error)),
        _FakeTmlTokenizer(raw),
        0.9,
    )

    decoded = codec.decode([11, 12])

    assert decoded.raw_text == raw
    assert decoded.completion_text == raw
    assert decoded.reasoning_text is None
    assert decoded.answer_text == ""
    assert decoded.reasoning_tokens_exact is None
    assert decoded.answer_tokens_exact is None
    assert decoded.reasoning_tokens_estimate is None
    assert decoded.answer_tokens_estimate is None
    assert decoded.channel_token_count_basis == expected_basis
    assert decoded.channel_parse_complete is False


def test_inkling_raw_decode_fallback_rejects_terminal_or_whitespace_as_usable() -> None:
    pytest.importorskip("tml_renderers")
    from tml_renderers import chat as tml_chat

    model = tml_chat.Author(tml_chat.AuthorKind.Model)
    parsed = [
        tml_chat.Message(tml_chat.Thinking(" \n\t"), model),
        tml_chat.Message(tml_chat.Text("   "), model),
        tml_chat.Message(tml_chat.ModelEndSampling(), model),
    ]
    raw = "```python\nprint('raw survives')\n```"
    codec = samplers._InklingCodec(
        _FakeTmlRenderer(_FakeTmlParser(parsed=parsed)),
        _FakeTmlTokenizer(raw),
        0.9,
    )

    decoded = codec.decode([11, 12])

    assert decoded.completion_text == raw
    assert decoded.channel_parse_complete is False
    assert "parse_had_no_usable_channel_text" in decoded.channel_token_count_basis


def test_inkling_preserves_usable_parsed_channels_without_terminal_marker() -> None:
    pytest.importorskip("tml_renderers")
    from tml_renderers import chat as tml_chat

    model = tml_chat.Author(tml_chat.AuthorKind.Model)
    parsed = [
        tml_chat.Message(tml_chat.Thinking("inspect"), model),
        tml_chat.Message(tml_chat.Text("```python\npass\n```"), model),
    ]
    codec = samplers._InklingCodec(
        _FakeTmlRenderer(_FakeTmlParser(parsed=parsed)),
        _FakeTmlTokenizer("raw TML serialization"),
        0.9,
    )

    decoded = codec.decode([11, 12])

    assert decoded.completion_text == "<think>inspect</think>\n```python\npass\n```"
    assert decoded.reasoning_text == "inspect"
    assert decoded.answer_text == "```python\npass\n```"
    assert decoded.reasoning_tokens_estimate == len("inspect".encode("utf-8"))
    assert decoded.answer_tokens_estimate == len("```python\npass\n```".encode("utf-8"))
    assert decoded.channel_parse_complete is False
