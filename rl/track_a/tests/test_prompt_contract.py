from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

from homi.conductor.source_policy import ALLOWED_COMPONENTS
from rl.common.contracts import (
    ModelObservation,
    observation_from_row,
    supervised_from_row,
)
from rl.track_a.prompt import (
    CONTRACT_VERSION,
    build_prompt_text,
    catalog_text,
    openai_sft_messages,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_prompt_is_one_blind_image_first_turn(core_row):
    example = supervised_from_row(core_row)
    messages = openai_sft_messages(example, image_url="data:image/png;base64,TEST")
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert [part["type"] for part in messages[0]["content"]] == [
        "image_url",
        "text",
    ]
    prompt = messages[0]["content"][1]["text"]
    assert "GDSFactory Function Catalog" in prompt
    assert '"footprint_um": [' in prompt
    assert messages[1]["content"][0]["text"] == core_row["code"]
    forbidden = (
        "DISPLAY NOTE",
        "magnification x:y",
        "px/um",
        core_row["id"],
        core_row["representation_id"],
        core_row["family"],
    )
    assert not [value for value in forbidden if value and value in prompt]


def test_hidden_fields_cannot_change_prompt(core_row):
    first = dict(core_row)
    second = dict(core_row)
    for key in (
        "instruction",
        "target_image",
        "metadata_json",
        "parameters_json",
        "topology_json",
        "port_signature_json",
        "family",
        "label",
        "level",
        "representation_id",
    ):
        second[key] = f"SECRET_SENTINEL_{key}"
    assert build_prompt_text(observation_from_row(first)) == build_prompt_text(
        observation_from_row(second)
    )


def test_prompt_builder_accepts_no_verifier_or_label_state(core_row):
    observation = observation_from_row(core_row)
    assert set(observation.__dataclass_fields__) == {
        "image_bytes",
        "footprint_um",
        "image_sha256",
    }
    assert isinstance(observation, ModelObservation)
    assert core_row["code"] not in build_prompt_text(observation)


def test_catalog_dataset_and_runtime_whitelists_are_identical():
    shared_path = REPO_ROOT / "dataset" / "scripts" / "_shared.py"
    spec = importlib.util.spec_from_file_location("dataset_shared_test", shared_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    advertised = frozenset(
        re.findall(r"\bgf\.components\.([A-Za-z_]\w*)", catalog_text())
    )
    assert advertised == ALLOWED_COMPONENTS == frozenset(module.ALLOWED_COMPONENTS)
    assert "bezier" in ALLOWED_COMPONENTS


def test_committed_config_binds_contract_and_is_spend_locked():
    path = REPO_ROOT / "rl" / "track_a" / "config.json"
    config = json.loads(path.read_text())
    assert config["contract_version"] == CONTRACT_VERSION
    assert config["model"]["name"] == "Qwen/Qwen3.6-35B-A3B"
    assert config["model"]["renderer"] == "qwen3_5_disable_thinking"
    assert config["model"]["lora_rank"] == 32
    assert config["sft"]["dataset_repo_id"] == "qpaig-mit/pixcell"
    assert config["sft"]["dataset_configuration"] == "depth"
    assert config["sft"]["verifier_configuration"] == "references"
    assert config["sft"]["dataset_revision"] == "v2.0.0"
    assert config["sft"]["max_sequence_tokens"] == 6144
    assert config["rl"]["group_size"] == 4
    assert config["rl"]["groups_per_batch"] == 8
    assert config["launch"]["paid_launch_enabled"] is False
