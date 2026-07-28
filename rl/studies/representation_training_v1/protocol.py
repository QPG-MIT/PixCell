"""Load and validate the sealed representation-training study."""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.common.prompt import CONTRACT_VERSION
from rl.evaluation.tasks import canonical_json_sha256


SCHEMA_VERSION = "pixcell-representation-training-protocol-v1"
STUDY_ID = "representation-training-v1"
STUDY_RELATIVE_PATH = Path("rl/studies/representation_training_v1")
PROTOCOL_FILENAME = "protocol.json"
LEVELS = ("L0", "L1", "L2", "L3", "L4")
INITIAL_STAGE_IDS = (
    "qwen-mixed-sft",
    "qwen-l0-sft",
    "qwen-base-rl-l0",
    "inkling-l4-rl",
)
BASE_QWEN_RL_STAGE_IDS = tuple(f"qwen-base-rl-l{level}" for level in range(5))
L0_SFT_QWEN_RL_STAGE_IDS = tuple(
    f"qwen-l0-rl-l{level}" for level in range(1, 5)
)
_STAGE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class StageSpec:
    stage_id: str
    kind: str
    model_key: str
    recipe_key: str
    hypotheses: tuple[str, ...]
    parent: str
    levels: tuple[str, ...]
    current_level: str | None
    replay_levels: tuple[str, ...]
    waves: dict[str, dict[str, Any]]

    def wave(self, wave_name: str) -> dict[str, Any]:
        try:
            return dict(self.waves[wave_name])
        except KeyError as exc:
            raise ValueError(
                f"{self.stage_id} has no wave {wave_name!r}; "
                f"expected one of {sorted(self.waves)}"
            ) from exc


def repository_root() -> Path:
    return Path(__file__).resolve().parents[3]


def protocol_path(repo_root: Path) -> Path:
    return repo_root.expanduser().resolve() / STUDY_RELATIVE_PATH / PROTOCOL_FILENAME


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _logical_document(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != "logical_sha256"}


def _require_at_head(repo_root: Path, path: Path) -> None:
    relative = path.resolve(strict=True).relative_to(repo_root.resolve()).as_posix()
    try:
        subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
        committed = subprocess.check_output(
            ["git", "show", f"HEAD:{relative}"],
            cwd=repo_root,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError("training protocol is not committed at HEAD") from exc
    if committed != path.read_bytes():
        raise ValueError("training protocol bytes differ from HEAD")


def _validate_model(key: str, value: dict[str, Any]) -> None:
    required = {
        "model",
        "renderer",
        "thinking",
        "lora_rank",
        "context_tokens",
        "max_output_tokens",
        "max_image_long_edge",
    }
    if not required.issubset(value):
        raise ValueError(f"model {key} is missing fields")
    if value["max_output_tokens"] >= value["context_tokens"]:
        raise ValueError(f"model {key} output exhausts its context")
    if key == "qwen":
        if (
            value["model"] != "Qwen/Qwen3.6-35B-A3B"
            or value["renderer"] != "qwen3_5"
            or value.get("effort") is not None
        ):
            raise ValueError("qwen must use the thinking-on Qwen3.5 contract")
    elif key == "inkling":
        effort = value.get("effort")
        if (
            value["model"] != "thinkingmachines/Inkling"
            or value["renderer"] != "tml_v0"
            or isinstance(effort, bool)
            or not isinstance(effort, (int, float))
            or not math.isfinite(float(effort))
            or not 0 <= float(effort) < 1
        ):
            raise ValueError("inkling must use native tml_v0 with explicit effort")
    else:
        raise ValueError(f"unknown model key: {key}")


def _stage_spec(
    stage_id: str,
    value: dict[str, Any],
    *,
    protocol: dict[str, Any],
) -> StageSpec:
    if not _STAGE_ID.fullmatch(stage_id):
        raise ValueError(f"invalid stage ID: {stage_id!r}")
    kind = str(value.get("kind"))
    if kind not in {"sft", "rl"}:
        raise ValueError(f"{stage_id} has unsupported kind {kind!r}")
    model_key = str(value.get("model"))
    recipe_key = str(value.get("recipe"))
    if model_key not in protocol["models"]:
        raise ValueError(f"{stage_id} names an unknown model")
    if recipe_key not in protocol["recipes"]:
        raise ValueError(f"{stage_id} names an unknown recipe")
    hypotheses = tuple(str(item) for item in value.get("hypotheses", ()))
    if not hypotheses or any(item not in protocol["hypotheses"] for item in hypotheses):
        raise ValueError(f"{stage_id} has invalid hypothesis consumers")
    parent = str(value.get("parent", ""))
    if not parent:
        raise ValueError(f"{stage_id} has no checkpoint parent")
    levels = tuple(str(item).upper() for item in value.get("levels", ()))
    current = value.get("current_level")
    current_level = str(current).upper() if current is not None else None
    replay = tuple(str(item).upper() for item in value.get("replay_levels", ()))
    if kind == "sft":
        if not levels or any(item not in LEVELS for item in levels):
            raise ValueError(f"{stage_id} has invalid SFT levels")
        if current_level is not None or replay:
            raise ValueError(f"{stage_id} mixes SFT and RL selectors")
    else:
        if levels or current_level not in LEVELS:
            raise ValueError(f"{stage_id} has invalid RL level")
        expected_replay = LEVELS[: LEVELS.index(current_level)]
        if model_key == "qwen" and replay != expected_replay:
            raise ValueError(
                f"{stage_id} replay must be the ordered prefix before {current_level}"
            )
        if model_key == "inkling" and replay:
            raise ValueError("Inkling L4 pilot must not replay training rows")
    waves = value.get("waves")
    if not isinstance(waves, dict) or not waves:
        raise ValueError(f"{stage_id} has no waves")
    observed_steps: list[int] = []
    for wave_name, wave in waves.items():
        if not _STAGE_ID.fullmatch(str(wave_name)):
            raise ValueError(f"{stage_id} has invalid wave name")
        if not isinstance(wave, dict) or not str(wave.get("approval", "")):
            raise ValueError(f"{stage_id}/{wave_name} has no approval gate")
        steps = wave.get("max_steps")
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 1:
            raise ValueError(f"{stage_id}/{wave_name} has invalid max_steps")
        observed_steps.append(steps)
    if len(observed_steps) != len(set(observed_steps)):
        raise ValueError(f"{stage_id} waves must have distinct step ceilings")
    if kind == "sft" and tuple(waves) != ("complete",):
        raise ValueError("SFT stages run continuously; they do not stop after a smoke batch")
    return StageSpec(
        stage_id=stage_id,
        kind=kind,
        model_key=model_key,
        recipe_key=recipe_key,
        hypotheses=hypotheses,
        parent=parent,
        levels=levels,
        current_level=current_level,
        replay_levels=replay,
        waves={str(key): dict(item) for key, item in waves.items()},
    )


def load_protocol(
    repo_root: Path | None = None,
    *,
    require_committed: bool = False,
) -> dict[str, Any]:
    root = (repo_root or repository_root()).expanduser().resolve()
    path = protocol_path(root)
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported training protocol schema")
    if document.get("study_id") != STUDY_ID:
        raise ValueError("training protocol has the wrong study ID")
    if document.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("training protocol and prompt contract differ")
    observed = canonical_json_sha256(_logical_document(document))
    if document.get("logical_sha256") != observed:
        raise ValueError("training protocol logical SHA-256 mismatch")
    if not _SHA256.fullmatch(str(document["dataset"]["logical_release_sha256"])):
        raise ValueError("training protocol has an invalid dataset digest")
    if document["evaluation"].get("mastery_thresholds") != {
        "minimum_mean_raw_absolute_scale_iou": 0.8,
        "minimum_pure_executable_rate": 0.95,
    }:
        raise ValueError("training protocol has the wrong mastery thresholds")
    if document["evaluation"].get("curriculum_progress_holdout") != {
        "baseline_checkpoints": {
            "L0": "base:qwen",
            "L1": "qwen-base-rl-l0:complete",
            "L2": "qwen-base-rl-l1:complete",
            "L3": "qwen-base-rl-l2:complete",
            "L4": "qwen-base-rl-l3:complete",
        },
        "configuration": "depth",
        "evaluation_waves": [
            "step-5",
            "step-10",
            "step-15",
            "step-20",
            "step-25",
            "complete",
        ],
        "panel_prefix": "level-progress",
        "realization_slot": 6,
        "representations_by_level": {
            "L0": 93,
            "L1": 127,
            "L2": 98,
            "L3": 120,
            "L4": 108,
        },
        "rows_by_level": {
            "L0": 93,
            "L1": 127,
            "L2": 98,
            "L3": 120,
            "L4": 108,
        },
        "split": "validation",
    }:
        raise ValueError("training protocol has the wrong curriculum progress holdout")
    if document["evaluation"].get("final_selection_holdout") != {
        "configuration": "depth",
        "panel": "depth-final-selection",
        "realization_slot": 7,
        "representations": 546,
        "rows": 546,
        "split": "validation",
    }:
        raise ValueError("training protocol has the wrong final selection holdout")
    for key, value in document["models"].items():
        _validate_model(str(key), value)
    stages = {
        stage_id: _stage_spec(stage_id, value, protocol=document)
        for stage_id, value in document["stages"].items()
    }
    if set(INITIAL_STAGE_IDS) - set(stages):
        raise ValueError("training protocol omits an initial branch")
    if set(BASE_QWEN_RL_STAGE_IDS) - set(stages):
        raise ValueError("training protocol omits the pure Qwen RL curriculum")
    if set(document["recipes"]) != {"qwen_sft", "qwen_rl", "inkling_l4_rl"}:
        raise ValueError("training protocol has an unexpected recipe set")
    for recipe_name, recipe in document["recipes"].items():
        if recipe.get("checkpoint_ttl_seconds", "missing") is not None:
            raise ValueError(
                f"{recipe_name} periodic checkpoints must remain available "
                "for receipt-bound evaluation"
            )
    for stage in stages.values():
        if ":" not in stage.parent:
            raise ValueError(f"{stage.stage_id} has a malformed parent")
        parent_stage, parent_wave = stage.parent.split(":", 1)
        if stage.parent.startswith("base:"):
            if parent_wave != stage.model_key:
                raise ValueError(f"{stage.stage_id} has the wrong base parent")
        else:
            if parent_stage not in stages:
                raise ValueError(
                    f"{stage.stage_id} names unknown parent {stage.parent}"
                )
            parent_spec = stages[parent_stage]
            if parent_spec.model_key != stage.model_key:
                raise ValueError(f"{stage.stage_id} crosses model families")
            if (
                parent_wave != "complete-or-skip"
                and parent_wave not in parent_spec.waves
            ):
                raise ValueError(f"{stage.stage_id} names an unknown parent wave")
        if stage.kind == "sft" and stage.recipe_key != "qwen_sft":
            raise ValueError(f"{stage.stage_id} has a non-SFT recipe")
        if stage.kind == "rl" and stage.recipe_key not in {
            "qwen_rl",
            "inkling_l4_rl",
        }:
            raise ValueError(f"{stage.stage_id} has a non-RL recipe")
        if stage.model_key == "inkling" and stage.kind != "rl":
            raise ValueError("Inkling is sealed as an RL-only policy")
        if stage.kind == "rl":
            reward = document["recipes"][stage.recipe_key].get("reward")
            if reward != document["evaluation"]["geometry_signal"]:
                raise ValueError(f"{stage.stage_id} does not optimize the recorded signal")
            if stage.wave("smoke")["max_steps"] != 1:
                raise ValueError(f"{stage.stage_id} smoke must be exactly one step")
            if stage.model_key == "qwen":
                expected_waves = {
                    "smoke": 1,
                    "step-5": 5,
                    "step-10": 10,
                    "step-15": 15,
                    "step-20": 20,
                    "step-25": 25,
                    "complete": 30,
                }
                if {
                    name: int(wave["max_steps"])
                    for name, wave in stage.waves.items()
                } != expected_waves:
                    raise ValueError(f"{stage.stage_id} has wrong Qwen RL waves")
                if stage.stage_id in BASE_QWEN_RL_STAGE_IDS:
                    expected_gates = {
                        "smoke": (
                            "initial"
                            if stage.current_level == "L0"
                            else (
                                "prior-and-current-level-held-out-"
                                "transition-receipt"
                            )
                        ),
                        "step-5": "rollout-health-receipt",
                        "step-10": "current-level-held-out-promotion-receipt",
                        "step-15": "current-level-held-out-promotion-receipt",
                        "step-20": "current-level-held-out-promotion-receipt",
                        "step-25": "current-level-held-out-promotion-receipt",
                        "complete": "current-level-held-out-promotion-receipt",
                    }
                    observed_gates = {
                        name: str(stage.wave(name)["approval"])
                        for name in expected_waves
                    }
                    if observed_gates != expected_gates:
                        raise ValueError(
                            f"{stage.stage_id} has wrong pure-RL gates"
                        )
                elif stage.stage_id in L0_SFT_QWEN_RL_STAGE_IDS:
                    expected_gates = {
                        "smoke": (
                            "parent-receipt-and-source-transition"
                            if stage.current_level == "L1"
                            else "prior-level-held-out-promotion-receipt"
                        ),
                        "step-5": "rollout-health-receipt",
                        "step-10": "current-level-held-out-promotion-receipt",
                        "step-15": "current-level-held-out-promotion-receipt",
                        "step-20": "current-level-held-out-promotion-receipt",
                        "step-25": "current-level-held-out-promotion-receipt",
                        "complete": "current-level-held-out-promotion-receipt",
                    }
                    observed_gates = {
                        name: str(stage.wave(name)["approval"])
                        for name in expected_waves
                    }
                    if observed_gates != expected_gates:
                        raise ValueError(
                            f"{stage.stage_id} has wrong L0-SFT-to-RL gates"
                        )
                elif any(
                    stage.wave(name)["approval"] != "clean-smoke-receipt"
                    for name in expected_waves
                    if name != "smoke"
                ):
                    raise ValueError(f"{stage.stage_id} continuation gates changed")
            else:
                if set(stage.waves) != {
                    "smoke",
                    "pilot",
                    "coverage-extension",
                }:
                    raise ValueError("Inkling pilot has the wrong wave set")
                if (
                    stage.wave("pilot")["max_steps"] != 6
                    or stage.wave("coverage-extension")["max_steps"] != 14
                ):
                    raise ValueError("Inkling pilot ceilings changed")
            if (
                document["recipes"][stage.recipe_key].get("checkpoint_policy")
                != "unique_wave_ceiling"
            ):
                raise ValueError(
                    f"{stage.stage_id} does not bind unique wave checkpoints"
                )
    for level, stage_id in enumerate(BASE_QWEN_RL_STAGE_IDS):
        stage = stages[stage_id]
        expected_parent = (
            "base:qwen"
            if level == 0
            else f"qwen-base-rl-l{level - 1}:complete"
        )
        if (
            stage.kind != "rl"
            or stage.model_key != "qwen"
            or stage.recipe_key != "qwen_rl"
            or stage.hypotheses != ("RT-H06",)
            or stage.current_level != f"L{level}"
            or stage.replay_levels != LEVELS[:level]
            or stage.parent != expected_parent
        ):
            raise ValueError(f"{stage_id} changed the pure Qwen RL curriculum")
    for level, stage_id in enumerate(L0_SFT_QWEN_RL_STAGE_IDS, start=1):
        stage = stages[stage_id]
        expected_parent = (
            "qwen-l0-sft:complete"
            if level == 1
            else f"qwen-l0-rl-l{level - 1}:complete"
        )
        if (
            stage.kind != "rl"
            or stage.model_key != "qwen"
            or stage.recipe_key != "qwen_rl"
            or stage.hypotheses != ("RT-H03",)
            or stage.current_level != f"L{level}"
            or stage.replay_levels != LEVELS[:level]
            or stage.parent != expected_parent
        ):
            raise ValueError(f"{stage_id} changed the L0-SFT-to-RL curriculum")
    exact_edges = {
        stage.stage_id: stage.parent.split(":", 1)[0]
        for stage in stages.values()
        if not stage.parent.startswith("base:")
    }
    for origin in exact_edges:
        seen: set[str] = set()
        cursor = origin
        while cursor in exact_edges:
            if cursor in seen:
                raise ValueError("training stage graph contains a cycle")
            seen.add(cursor)
            cursor = exact_edges[cursor]
    if document["launch"].get("paid_launch_enabled") is not True:
        raise ValueError("training protocol is not launch-enabled")
    expected_retry_stages = list(L0_SFT_QWEN_RL_STAGE_IDS)
    if document["launch"].get("replicates") != ["r0", "r0-retry1"]:
        raise ValueError("training protocol has the wrong launch identities")
    if document["launch"].get("replicate_stage_scopes") != {
        "r0": ["*"],
        "r0-retry1": expected_retry_stages,
    }:
        raise ValueError("training protocol has the wrong launch identity scopes")
    if document["launch"].get("parent_replicate_overrides") != {
        "qwen-l0-rl-l1": {"r0-retry1": "r0"}
    }:
        raise ValueError("training protocol has the wrong parent identity override")
    if require_committed:
        _require_at_head(root, path)
    return document


def stage_spec(protocol: dict[str, Any], stage_id: str) -> StageSpec:
    try:
        value = protocol["stages"][stage_id]
    except KeyError as exc:
        raise ValueError(f"unknown training stage: {stage_id!r}") from exc
    return _stage_spec(stage_id, value, protocol=protocol)


def validate_stage_replicate(
    protocol: Mapping[str, Any],
    *,
    stage_id: str,
    replicate_id: str,
) -> None:
    """Validate one declared execution identity for one exact stage."""

    if replicate_id not in protocol["launch"]["replicates"]:
        raise ValueError("replicate is not declared in the protocol")
    scopes = protocol["launch"]["replicate_stage_scopes"]
    allowed = scopes.get(replicate_id)
    if not isinstance(allowed, list) or (
        "*" not in allowed and stage_id not in allowed
    ):
        raise ValueError("replicate is not declared for this training stage")


def parent_replicate_id(
    protocol: Mapping[str, Any],
    *,
    stage_id: str,
    replicate_id: str,
) -> str:
    """Resolve a protocol-bound parent execution identity."""

    validate_stage_replicate(
        protocol,
        stage_id=stage_id,
        replicate_id=replicate_id,
    )
    overrides = protocol["launch"]["parent_replicate_overrides"]
    stage_overrides = overrides.get(stage_id, {})
    if not isinstance(stage_overrides, Mapping):
        raise ValueError("parent replicate override is malformed")
    result = str(stage_overrides.get(replicate_id, replicate_id))
    if result not in protocol["launch"]["replicates"]:
        raise ValueError("parent replicate override names an unknown identity")
    return result


def validate_source_sha(repo_root: Path, expected_source_sha: str) -> str:
    if not _GIT_SHA.fullmatch(expected_source_sha):
        raise ValueError("expected source SHA must be a 40-character Git SHA")
    root = repo_root.expanduser().resolve()
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
    ).strip()
    if head != expected_source_sha:
        raise ValueError(f"HEAD {head} differs from expected {expected_source_sha}")
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        text=True,
    ).strip()
    if status:
        raise ValueError("paid training requires a completely clean worktree")
    return head
