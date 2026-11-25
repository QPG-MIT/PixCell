"""Guard token masking and the deliberate attention-only adapter boundary."""

import pytest

from rl.contract_algos.training_smoke import completion_labels, is_attention_target, parse_args


def test_masks_every_prompt_and_image_token_but_keeps_completion():
    assert completion_labels([1, 200, 200, 3], [1, 200, 200, 3, 41, 42, 9]) == [
        -100,
        -100,
        -100,
        -100,
        41,
        42,
        9,
    ]


@pytest.mark.parametrize("prompt,full", [([], [1]), ([1, 2], [1, 3, 4]), ([1, 2], [1, 2])])
def test_refuses_template_drift_or_missing_completion(prompt, full):
    with pytest.raises(ValueError):
        completion_labels(prompt, full)


def test_adapters_exclude_vision_and_moe_experts():
    assert is_attention_target("model.language_model.layers.0.self_attn.q_proj")
    assert is_attention_target("model.language_model.layers.0.self_attn.v_proj")
    for name in [
        "model.visual.layers.0.self_attn.q_proj",
        "model.vision.layers.0.self_attn.q_proj",
        "model.language_model.layers.0.mlp.experts.0.q_proj",
        "model.language_model.layers.0.mlp.up_proj",
        "model.language_model.layers.0.self_attn.o_proj",
        "lm_head",
    ]:
        assert not is_attention_target(name)


def test_refuses_overwriting_existing_results(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    (model / "config.json").write_text("{}")
    output = tmp_path / "run"
    output.mkdir()
    (output / "result.json").write_text("preserve me")
    with pytest.raises(SystemExit):
        parse_args(["--model-path", str(model), "--output-dir", str(output)])
    assert (output / "result.json").read_text() == "preserve me"
