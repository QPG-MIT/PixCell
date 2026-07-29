from __future__ import annotations

import importlib.util
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
    prompt_asset_hashes,
    task_text,
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
    assert "Exact GDSFactory Extended Primitive Catalogue" in prompt
    assert '"footprint_um": [' in prompt
    assert messages[1]["content"][0]["text"] == core_row["code"]
    forbidden = (
        "DISPLAY NOTE",
        "magnification x:y",
        "target_image",
        "target raster",
        "candidate raster",
        "IoU",
        "calibration",
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


def test_direct_phase_a_contract_states_every_execution_obligation(core_row):
    prompt = build_prompt_text(observation_from_row(core_row))
    normalized = " ".join(prompt.split())
    required = (
        "BLACK is",
        "material on layer `(1, 0)`",
        "`footprint_um` is `[x-length, y-width]`",
        "GDSFactory 9.20.7",
        "Exact GDSFactory Extended Primitive Catalogue",
        "Ordinary GDSFactory assembly",
        "prebuilt device-level stencils",
        "raw polygon",
        "raster tracing",
        "runtime image reads",
        "live top-level",
        "@gf.cell",
        "reason internally about the topology",
        "Do not output the reasoning",
        'if __name__ == "__main__":',
        "complete executable program",
        "`device.gds`",
        '.write_gds("device.gds")',
        "filename in the catalogue's assembly example is illustrative",
        "Output only the complete Python program",
    )
    assert not [value for value in required if value not in normalized]


def test_direct_phase_a_asset_is_rl_owned_and_has_no_verifier_hints():
    task = task_text()
    forbidden = (
        "calibration",
        "magnification",
        "px/um",
        "target raster",
        "candidate raster",
        "IoU",
        "Dice",
        "metadata",
    )
    assert not [value for value in forbidden if value.casefold() in task.casefold()]
    hashes = prompt_asset_hashes()
    assert set(hashes) == {"catalog_sha256", "task_sha256"}
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes.values())


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


def test_contract_version_is_pinned():
    assert CONTRACT_VERSION == "pixcell-direct-reconstruction-v3"
