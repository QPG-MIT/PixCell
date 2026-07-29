from __future__ import annotations

import pickle

import pytest


pytest.importorskip("tinker", reason="Tinker is an optional RL dependency")
pytest.importorskip(
    "tinker_cookbook",
    reason="Tinker Cookbook is an optional RL dependency",
)
pytest.importorskip(
    "tml_renderers",
    reason="Inkling native rendering is an optional RL dependency",
)

import tinker
from tinker_cookbook.renderers import (
    Message,
    ParseTermination,
    RenderContext,
    TextPart,
    TrainOnWhat,
    get_renderer,
    unregister_renderer,
)
from tinker_cookbook.tokenizer_utils import (
    get_tokenizer,
    unregister_tokenizer,
)
from tml_renderers import chat as tml_chat
from tml_renderers import tinker as tml_tinker

from rl.track_b import tml_shim


@pytest.fixture()
def direct_renderer() -> tml_shim.InklingTmlV0Renderer:
    return tml_shim.InklingTmlV0Renderer(
        tml_shim.InklingTokenizer(),
        effort=0.9,
    )


@pytest.fixture()
def clean_registration(monkeypatch):
    unregister_renderer(tml_shim.RENDERER_NAME)
    unregister_tokenizer(tml_shim.MODEL_NAME)
    monkeypatch.setattr(tml_shim, "_RUNTIME_EFFORT", None)
    monkeypatch.setattr(tml_shim, "_TOKENIZER", None)
    monkeypatch.setattr(tml_shim, "_patch_sdk_tokenizer_loader", lambda: None)
    yield
    unregister_renderer(tml_shim.RENDERER_NAME)
    unregister_tokenizer(tml_shim.MODEL_NAME)


def _action_tokens(
    renderer: tml_shim.InklingTmlV0Renderer,
    *,
    reasoning: str,
    final: str,
) -> list[int]:
    model = tml_chat.Author(tml_chat.AuthorKind.Model)
    messages = [
        tml_chat.Message(content=tml_chat.Thinking(reasoning), author=model),
        tml_chat.Message(content=tml_chat.Text(final), author=model),
        tml_chat.Message(content=tml_chat.ModelEndSampling(), author=model),
    ]
    examples = list(renderer._tml.render_for_sft(messages))
    assert len(examples) == 1
    model_input, weights = (
        tml_tinker.training_example_to_tinker_model_input_and_weights(examples[0])
    )
    flat: list[int | None] = []
    for chunk in model_input.chunks:
        if isinstance(chunk, tinker.EncodedTextChunk):
            flat.extend(list(chunk.tokens))
        else:
            flat.extend([None] * chunk.length)
    selected = [
        token
        for token, weight in zip(flat, weights, strict=True)
        if weight != 0.0
    ]
    assert selected and None not in selected
    return [int(token) for token in selected]


@pytest.mark.parametrize("effort", [True, -0.1, 1.0, float("nan")])
def test_effort_must_be_explicit_and_valid(effort):
    with pytest.raises((TypeError, ValueError)):
        tml_shim.InklingTmlV0Renderer(
            tml_shim.InklingTokenizer(),
            effort=effort,
        )


def test_generation_uses_constructor_effort_not_environment(
    direct_renderer,
    monkeypatch,
):
    monkeypatch.setenv("PIXCELL_TML_EFFORT", "0.2")
    prompt = direct_renderer.build_generation_prompt(
        [Message(role="user", content="Recreate the device.")]
    )
    tokens: list[int] = []
    for chunk in prompt.chunks:
        if isinstance(chunk, tinker.EncodedTextChunk):
            tokens.extend(chunk.tokens)
    decoded = direct_renderer.tokenizer.decode(tokens)
    assert "Thinking effort level: 0.9" in decoded
    assert "Thinking effort level: 0.2" not in decoded


def test_channel_decode_returns_only_final_text(direct_renderer):
    action = _action_tokens(
        direct_renderer,
        reasoning="PRIVATE REASONING SENTINEL",
        final="FINAL_CODE_SENTINEL = 1",
    )
    decoded = direct_renderer.decode_response(action)
    assert decoded.termination is ParseTermination.STOP_SEQUENCE
    assert decoded.channel_parse_complete
    assert decoded.reasoning_text == "PRIVATE REASONING SENTINEL"
    assert decoded.final_text == "FINAL_CODE_SENTINEL = 1"
    assert direct_renderer.decode_action_text(action) == "FINAL_CODE_SENTINEL = 1"
    assert "PRIVATE REASONING" not in direct_renderer.decode_action_text(action)

    message, termination = direct_renderer.parse_response(action)
    assert termination is ParseTermination.STOP_SEQUENCE
    assert message["content"] == [
        {"type": "thinking", "thinking": "PRIVATE REASONING SENTINEL"},
        {"type": "text", "text": "FINAL_CODE_SENTINEL = 1"},
    ]


def test_malformed_native_response_does_not_turn_raw_framing_into_code(
    direct_renderer,
):
    # A lone native message-open token is deliberately incomplete.
    decoded = direct_renderer.decode_response([200001])
    assert decoded.termination is ParseTermination.MALFORMED
    assert decoded.final_text == ""
    assert direct_renderer.decode_action_text([200001]) == ""


def test_supervised_paths_fail_closed(direct_renderer):
    messages = [
        Message(role="user", content="image task"),
        Message(role="assistant", content=[TextPart(type="text", text="code")]),
    ]
    with pytest.raises(tml_shim.InklingSupervisionDisabled):
        direct_renderer.build_supervised_example(messages)
    with pytest.raises(tml_shim.InklingSupervisionDisabled):
        direct_renderer.build_supervised_examples(
            messages,
            train_on_what=TrainOnWhat.LAST_ASSISTANT_TURN,
        )
    with pytest.raises(tml_shim.InklingSupervisionDisabled):
        direct_renderer.render_message(
            messages[0],
            RenderContext(
                idx=0,
                is_last=True,
                prev_message=None,
                last_user_index=0,
            ),
        )


def test_renderer_pickle_preserves_explicit_effort(direct_renderer):
    restored = pickle.loads(pickle.dumps(direct_renderer))
    assert isinstance(restored, tml_shim.InklingTmlV0Renderer)
    assert restored.effort == 0.9


def test_install_is_inkling_only_and_immutable(clean_registration):
    binding = tml_shim.install_inkling_runtime(effort=0.9)
    assert binding == tml_shim.InklingRuntimeBinding(
        model_name=tml_shim.MODEL_NAME,
        renderer_name=tml_shim.RENDERER_NAME,
        effort=0.9,
    )
    assert tml_shim.install_inkling_runtime(effort=0.9) == binding
    with pytest.raises(tml_shim.InklingRuntimeError, match="already bound"):
        tml_shim.install_inkling_runtime(effort=0.8)

    tokenizer = get_tokenizer(tml_shim.MODEL_NAME)
    renderer = get_renderer(
        tml_shim.RENDERER_NAME,
        tokenizer,
        None,
        model_name=tml_shim.MODEL_NAME,
    )
    assert isinstance(tokenizer, tml_shim.InklingTokenizer)
    assert isinstance(renderer, tml_shim.InklingTmlV0Renderer)
    assert renderer.effort == 0.9

    class OtherTokenizer:
        name_or_path = "other/model"

    with pytest.raises(tml_shim.InklingRuntimeError, match="restricted"):
        tml_shim._renderer_factory(OtherTokenizer(), None)
    assert not tml_shim._is_inkling_model("Qwen/Qwen3.6-35B-A3B")
    assert tml_shim._is_inkling_model("thinkingmachines/Inkling:peft:262144")


def test_no_registration_happens_from_environment_alone(
    clean_registration,
    monkeypatch,
):
    monkeypatch.setenv("PIXCELL_TML_EFFORT", "0.9")
    assert tml_shim._RUNTIME_EFFORT is None
