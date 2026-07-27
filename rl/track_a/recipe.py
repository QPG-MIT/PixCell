"""Canonical Track A recipe and curriculum invariants.

Paid entrypoints intentionally accept only operational inputs (confirmation,
checkpoint/report paths, and a contained log directory).  Model, data, and
optimization settings are loaded from the committed recipe and cannot be
silently changed at the command line.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from rl.common.isolation import require_execution_boundary


LEVELS = ("L0", "L1", "L2", "L3", "L4")
CONFIG_RELATIVE_PATH = Path("rl/track_a/config.json")
DATASET_RELATIVE_PATH = Path("dataset")
RUNS_RELATIVE_PATH = Path("rl/track_a/runs")
_TINKER_SAMPLER_PATH = re.compile(
    r"^(tinker://[^/\s]+/)(sampler_weights)(/[^/\s]+)$"
)


def load_recipe(repo_root: Path) -> dict[str, Any]:
    """Load the single committed Track A recipe."""

    path = (repo_root / CONFIG_RELATIVE_PATH).resolve()
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "pixcell-track-a-config-v1":
        raise ValueError("unsupported Track A recipe schema")
    return value


def canonical_dataset_root(repo_root: Path) -> Path:
    return (repo_root / DATASET_RELATIVE_PATH).resolve()


def canonical_config_path(repo_root: Path) -> Path:
    return (repo_root / CONFIG_RELATIVE_PATH).resolve()


def _same_number(actual: Any, expected: Any) -> bool:
    if isinstance(actual, bool) or isinstance(expected, bool):
        return actual is expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isclose(float(actual), float(expected), rel_tol=0.0, abs_tol=0.0)
    return actual == expected


def _require_equal(name: str, actual: Any, expected: Any) -> None:
    if not _same_number(actual, expected):
        raise ValueError(
            f"{name}={actual!r} overrides the committed Track A value {expected!r}"
        )


def _require_canonical_dataset(repo_root: Path, value: str | Path) -> Path:
    observed = Path(value).expanduser().resolve()
    expected = canonical_dataset_root(repo_root)
    if observed != expected:
        raise ValueError(
            f"dataset_root must be the committed dataset at {expected}; got {observed}"
        )
    return observed


def _require_contained_log_path(repo_root: Path, value: str | Path) -> Path:
    observed = Path(value).expanduser().resolve()
    root = (repo_root / RUNS_RELATIVE_PATH).resolve()
    if observed == root or not observed.is_relative_to(root):
        raise ValueError(f"log_path must be a new child of {root}; got {observed}")
    return observed


def _require_contained_report_path(repo_root: Path, value: str | Path) -> Path:
    observed = Path(value).expanduser().resolve()
    root = (repo_root / RUNS_RELATIVE_PATH).resolve()
    if not observed.is_relative_to(root) or observed.suffix != ".json":
        raise ValueError(f"output must be a JSON child of {root}; got {observed}")
    if observed.exists():
        raise ValueError(f"output must not already exist: {observed}")
    return observed


def file_sha256(path: Path) -> str:
    """Hash one launch input exactly as preflight will consume it."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weights_path_for_sampler(sampler_path: str) -> str:
    """Return the weights checkpoint paired with a Tinker sampler checkpoint."""

    match = _TINKER_SAMPLER_PATH.fullmatch(sampler_path)
    if match is None:
        raise ValueError(
            "mastery report sampler_path must be a Tinker sampler_weights checkpoint"
        )
    return f"{match.group(1)}weights{match.group(3)}"


def validate_sft_cli(repo_root: Path, cfg: Any) -> dict[str, Any]:
    """Reject every paid SFT recipe override and return its resolved binding."""

    recipe = load_recipe(repo_root)
    model = recipe["model"]
    sft = recipe["sft"]
    launch = recipe["launch"]
    _require_canonical_dataset(repo_root, cfg.dataset_root)
    _require_equal("model_name", cfg.model_name, model["name"])
    _require_equal("renderer_name", cfg.renderer_name, model["renderer"])
    _require_equal("lora_rank", cfg.lora_rank, model["lora_rank"])
    _require_equal("learning_rate", cfg.learning_rate, sft["learning_rate"])
    _require_equal("lr_schedule", cfg.lr_schedule, sft["tinker_lr_schedule"])
    _require_equal("num_epochs", cfg.num_epochs, sft["effective_passes"])
    _require_equal("batch_size", cfg.batch_size, sft["batch_size"])
    _require_equal("max_length", cfg.max_length, sft["max_sequence_tokens"])
    _require_equal("max_image", cfg.max_image, model["max_image_long_edge"])
    _require_equal("save_every", cfg.save_every, sft["save_every_steps"])
    _require_equal("eval_every", cfg.eval_every, sft["evaluate_every_steps"])
    _require_equal("max_steps", cfg.max_steps, sft["max_steps"])
    _require_contained_log_path(repo_root, cfg.log_path)
    _require_equal(
        "confirm_spend",
        cfg.confirm_spend,
        launch["confirmation_tokens"]["sft"],
    )
    return {
        "kind": "sft",
        "dataset_root": str(canonical_dataset_root(repo_root)),
        "config_path": str(canonical_config_path(repo_root)),
        "model_name": cfg.model_name,
        "renderer_name": cfg.renderer_name,
        "lora_rank": cfg.lora_rank,
        "learning_rate": cfg.learning_rate,
        "lr_schedule": cfg.lr_schedule,
        "num_epochs": cfg.num_epochs,
        "batch_size": cfg.batch_size,
        "max_length": cfg.max_length,
        "max_image": cfg.max_image,
        "save_every": cfg.save_every,
        "eval_every": cfg.eval_every,
        "max_steps": cfg.max_steps,
    }


def normalize_level(value: str) -> str:
    level = value.strip().upper()
    if level not in LEVELS:
        raise ValueError(f"expected exactly one curriculum level in {LEVELS}; got {value!r}")
    return level


def normalize_replay_levels(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    values = tuple(item.strip().upper() for item in value.split(",") if item.strip())
    if len(values) != len(set(values)):
        raise ValueError("replay_levels must not contain duplicates")
    unknown = [item for item in values if item not in LEVELS]
    if unknown:
        raise ValueError(f"unknown replay levels: {unknown}")
    if values != tuple(sorted(values, key=LEVELS.index)):
        raise ValueError("replay_levels must be in curriculum order")
    return values


def expected_replay_levels(current_level: str) -> tuple[str, ...]:
    current = normalize_level(current_level)
    return LEVELS[: LEVELS.index(current)]


def first_unmastered_level(
    report: Mapping[str, Any],
    *,
    minimum_iou: float,
    minimum_pure_executable_rate: float,
) -> str | None:
    """Compute the first curriculum level that misses either mastery threshold."""

    levels = report.get("levels_summary")
    if not isinstance(levels, Mapping):
        raise ValueError("mastery report has no levels_summary mapping")
    for level in LEVELS:
        summary = levels.get(level)
        if not isinstance(summary, Mapping):
            raise ValueError(f"mastery report is missing {level}")
        try:
            iou = float(summary["mean_iou_at_1"])
            pure = float(summary["pure_executable_rate"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"mastery report has invalid {level} metrics") from exc
        if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (iou, pure)):
            raise ValueError(f"mastery report has out-of-range {level} metrics")
        if iou < minimum_iou or pure < minimum_pure_executable_rate:
            return level
    return None


def validate_curriculum_selection(
    recipe: Mapping[str, Any],
    report: Mapping[str, Any],
    *,
    current_level: str,
    replay_levels: str,
) -> tuple[str, tuple[str, ...]]:
    """Bind caller-supplied curriculum arguments to the computed mastery result."""

    curriculum = recipe["rl"]["curriculum"]
    computed = first_unmastered_level(
        report,
        minimum_iou=float(curriculum["minimum_iou"]),
        minimum_pure_executable_rate=float(
            curriculum["minimum_pure_executable_rate"]
        ),
    )
    if computed is None:
        raise ValueError("all curriculum levels are mastered; no RL stage may start")
    current = normalize_level(current_level)
    if current != computed:
        raise ValueError(
            f"current_level must be the computed first unmastered level {computed}; "
            f"got {current}"
        )
    replay = normalize_replay_levels(replay_levels)
    expected = expected_replay_levels(current)
    if replay != expected:
        rendered = ",".join(expected)
        raise ValueError(
            f"replay_levels must be exactly the earlier levels {rendered!r}; "
            f"got {replay_levels!r}"
        )
    return current, replay


def validate_rl_cli(
    repo_root: Path,
    cfg: Any,
    *,
    mastery_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Reject recipe overrides and validate the computed curriculum stage."""

    recipe = load_recipe(repo_root)
    model = recipe["model"]
    rl = recipe["rl"]
    launch = recipe["launch"]
    _require_canonical_dataset(repo_root, cfg.dataset_root)
    _require_equal("model_name", cfg.model_name, model["name"])
    _require_equal("renderer_name", cfg.renderer_name, model["renderer"])
    _require_equal("lora_rank", cfg.lora_rank, model["lora_rank"])
    _require_equal("group_size", cfg.group_size, rl["group_size"])
    _require_equal("groups_per_batch", cfg.groups_per_batch, rl["groups_per_batch"])
    _require_equal("learning_rate", cfg.learning_rate, rl["learning_rate"])
    _require_equal("max_tokens", cfg.max_tokens, rl["max_output_tokens"])
    _require_equal("temperature", cfg.temperature, rl["temperature"])
    if not isinstance(cfg.max_steps, int) or not 1 <= cfg.max_steps <= rl["stage_max_steps"]:
        raise ValueError(
            f"max_steps must be between 1 and the committed ceiling "
            f"{rl['stage_max_steps']}; got {cfg.max_steps!r}"
        )
    _require_equal("eval_every", cfg.eval_every, rl["evaluate_every_steps"])
    _require_equal("save_every", cfg.save_every, rl["save_every_steps"])
    _require_equal("loss_fn", cfg.loss_fn, rl["loss_fn"])
    _require_contained_log_path(repo_root, cfg.log_path)
    _require_equal(
        "confirm_spend",
        cfg.confirm_spend,
        launch["confirmation_tokens"]["rl"],
    )
    if not str(cfg.load_checkpoint_path).strip():
        raise ValueError("load_checkpoint_path must name the selected SFT checkpoint")
    mastery_path = Path(cfg.mastery_report).expanduser().resolve(strict=True)
    if not mastery_path.is_file():
        raise ValueError("mastery_report must be a regular JSON file")
    report_sampler = str(mastery_report.get("sampler_path", ""))
    expected_checkpoint = weights_path_for_sampler(report_sampler)
    _require_equal(
        "load_checkpoint_path",
        cfg.load_checkpoint_path,
        expected_checkpoint,
    )
    current, replay = validate_curriculum_selection(
        recipe,
        mastery_report,
        current_level=cfg.current_level,
        replay_levels=cfg.replay_levels,
    )
    return {
        "kind": "rl",
        "dataset_root": str(canonical_dataset_root(repo_root)),
        "config_path": str(canonical_config_path(repo_root)),
        "model_name": cfg.model_name,
        "renderer_name": cfg.renderer_name,
        "lora_rank": cfg.lora_rank,
        "group_size": cfg.group_size,
        "groups_per_batch": cfg.groups_per_batch,
        "learning_rate": cfg.learning_rate,
        "max_tokens": cfg.max_tokens,
        "temperature": cfg.temperature,
        "max_steps": cfg.max_steps,
        "eval_every": cfg.eval_every,
        "save_every": cfg.save_every,
        "loss_fn": cfg.loss_fn,
        "current_level": current,
        "replay_levels": list(replay),
        "load_checkpoint_path": expected_checkpoint,
        "mastery_report": str(mastery_path),
        "mastery_report_sha256": file_sha256(mastery_path),
    }


def validate_evaluation_binding(
    repo_root: Path,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Recompute the exact checkpoint-evaluation contract."""

    recipe = load_recipe(repo_root)
    model = recipe["model"]
    rl = recipe["rl"]
    evaluation = recipe["checkpoint_evaluation"]
    role = binding.get("role")
    if role == "checkpoint-geometry":
        expected_levels = "all"
        expected_rows = 0
        expected_k = evaluation["geometry_k"]
    elif role == "behavioral-collapse-probe":
        expected_levels = normalize_level(str(binding.get("levels", "")))
        expected_rows = evaluation["behavioral_rows"]
        expected_k = evaluation["behavioral_k"]
    else:
        raise ValueError(f"unknown checkpoint evaluation role: {role!r}")
    sampler_path = str(binding.get("sampler_path", "")).strip()
    if not sampler_path:
        raise ValueError("sampler_path is required")
    output = _require_contained_report_path(
        repo_root,
        str(binding.get("output", "")),
    )
    expected = {
        "kind": "evaluation",
        "dataset_root": str(canonical_dataset_root(repo_root)),
        "config_path": str(canonical_config_path(repo_root)),
        "model_name": model["name"],
        "renderer_name": model["renderer"],
        "lora_rank": model["lora_rank"],
        "sampler_path": sampler_path,
        "role": role,
        "levels": expected_levels,
        "rows": expected_rows,
        "k": expected_k,
        "temperature": rl["temperature"],
        "top_p": rl["top_p"],
        "max_tokens": rl["max_output_tokens"],
        "seed": evaluation["task_selection_seed"],
        "max_image": model["max_image_long_edge"],
        "concurrency": evaluation["sampling_concurrency"],
        "evaluator_workers": evaluation["evaluator_workers"],
        "include_records": evaluation["include_records"],
        "output": str(output),
    }
    for name, expected_value in expected.items():
        _require_equal(name, binding.get(name), expected_value)
    return expected


def validate_evaluation_cli(repo_root: Path, args: Any) -> dict[str, Any]:
    """Reject checkpoint-evaluation overrides and return its launch binding."""

    recipe = load_recipe(repo_root)
    _require_equal(
        "confirm_spend",
        args.confirm_spend,
        recipe["launch"]["confirmation_tokens"]["evaluation"],
    )
    _require_canonical_dataset(repo_root, args.dataset_root)
    role = (
        "behavioral-collapse-probe"
        if args.behavioral_probe
        else "checkpoint-geometry"
    )
    levels = str(args.levels).strip().upper() if args.behavioral_probe else "all"
    candidate = {
        "kind": "evaluation",
        "dataset_root": str(canonical_dataset_root(repo_root)),
        "config_path": str(canonical_config_path(repo_root)),
        "model_name": args.model_name,
        "renderer_name": args.renderer_name,
        "lora_rank": recipe["model"]["lora_rank"],
        "sampler_path": args.sampler_path,
        "role": role,
        "levels": levels,
        "rows": args.rows,
        "k": args.k,
        "temperature": args.temperature,
        "top_p": recipe["rl"]["top_p"],
        "max_tokens": args.max_tokens,
        "seed": args.seed,
        "max_image": recipe["model"]["max_image_long_edge"],
        "concurrency": args.concurrency,
        "evaluator_workers": args.evaluator_workers,
        "include_records": args.include_records,
        "output": str(Path(args.output).expanduser().resolve()),
    }
    return validate_evaluation_binding(repo_root, candidate)


def canonical_json_sha256(value: Mapping[str, Any]) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def validate_resolved_binding(
    repo_root: Path,
    binding: Mapping[str, Any],
) -> dict[str, Any]:
    """Revalidate a serialized launch binding inside the preflight process."""

    kind = binding.get("kind")
    recipe = load_recipe(repo_root)
    model = recipe["model"]
    _require_equal(
        "dataset_root",
        str(Path(str(binding.get("dataset_root", ""))).resolve()),
        str(canonical_dataset_root(repo_root)),
    )
    _require_equal(
        "config_path",
        str(Path(str(binding.get("config_path", ""))).resolve()),
        str(canonical_config_path(repo_root)),
    )
    _require_equal("model_name", binding.get("model_name"), model["name"])
    _require_equal("renderer_name", binding.get("renderer_name"), model["renderer"])
    _require_equal("lora_rank", binding.get("lora_rank"), model["lora_rank"])
    if kind == "sft":
        sft = recipe["sft"]
        expected = {
            "learning_rate": sft["learning_rate"],
            "lr_schedule": sft["tinker_lr_schedule"],
            "num_epochs": sft["effective_passes"],
            "batch_size": sft["batch_size"],
            "max_length": sft["max_sequence_tokens"],
            "max_image": model["max_image_long_edge"],
            "save_every": sft["save_every_steps"],
            "eval_every": sft["evaluate_every_steps"],
            "max_steps": sft["max_steps"],
        }
    elif kind == "rl":
        rl = recipe["rl"]
        expected = {
            "group_size": rl["group_size"],
            "groups_per_batch": rl["groups_per_batch"],
            "learning_rate": rl["learning_rate"],
            "max_tokens": rl["max_output_tokens"],
            "temperature": rl["temperature"],
            "eval_every": rl["evaluate_every_steps"],
            "save_every": rl["save_every_steps"],
            "loss_fn": rl["loss_fn"],
        }
        checkpoint_path = str(binding.get("load_checkpoint_path", ""))
        mastery_path = Path(str(binding.get("mastery_report", ""))).resolve(
            strict=True
        )
        if not mastery_path.is_file():
            raise ValueError("resolved RL mastery_report is not a regular file")
        mastery_sha256 = file_sha256(mastery_path)
        _require_equal(
            "mastery_report_sha256",
            binding.get("mastery_report_sha256"),
            mastery_sha256,
        )
        try:
            mastery_report = json.loads(mastery_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError("resolved RL mastery_report is not valid JSON") from exc
        if not isinstance(mastery_report, Mapping):
            raise ValueError("resolved RL mastery_report must be a JSON object")
        from rl.track_a.evaluation_contract import (
            build_checkpoint_selection_contract,
            validate_evaluation_report,
        )

        report_contract = build_checkpoint_selection_contract(
            repo_root,
            canonical_dataset_root(repo_root),
        )
        validate_evaluation_report(
            mastery_report,
            contract=report_contract,
            expected_role="checkpoint-geometry",
        )
        expected_checkpoint = weights_path_for_sampler(
            str(mastery_report.get("sampler_path", ""))
        )
        _require_equal(
            "load_checkpoint_path",
            checkpoint_path,
            expected_checkpoint,
        )
        max_steps = binding.get("max_steps")
        if (
            not isinstance(max_steps, int)
            or not 1 <= max_steps <= int(rl["stage_max_steps"])
        ):
            raise ValueError("resolved RL max_steps exceeds the committed ceiling")
        current = normalize_level(str(binding.get("current_level", "")))
        replay_value = binding.get("replay_levels")
        if not isinstance(replay_value, list):
            raise ValueError("resolved RL replay_levels must be a list")
        replay = normalize_replay_levels(",".join(str(item) for item in replay_value))
        if replay != expected_replay_levels(current):
            raise ValueError("resolved RL replay levels are not all earlier levels")
        validate_curriculum_selection(
            recipe,
            mastery_report,
            current_level=current,
            replay_levels=",".join(replay),
        )
    elif kind == "evaluation":
        evaluation = validate_evaluation_binding(repo_root, binding)
        expected = {
            name: value
            for name, value in evaluation.items()
            if name not in {"kind", "dataset_root", "config_path", "candidate_sandbox"}
        }
    else:
        raise ValueError(f"unknown resolved launch kind: {kind!r}")
    for name, expected_value in expected.items():
        _require_equal(name, binding.get(name), expected_value)
    if kind in {"rl", "evaluation"}:
        sandbox = binding.get("candidate_sandbox")
        if not isinstance(sandbox, Mapping):
            raise ValueError("resolved launch has no candidate_sandbox binding")
        boundary = require_execution_boundary()
        sandbox_expected = {
            "runtime_path": str(boundary.runtime_path),
            "daemon_endpoint": boundary.daemon_endpoint,
            "image_ref": boundary.image_ref,
            "image_id": boundary.image_id,
            "workspace_root": str(boundary.workspace_root),
        }
        for name, expected_value in sandbox_expected.items():
            _require_equal(
                f"candidate_sandbox.{name}",
                sandbox.get(name),
                expected_value,
            )
    return dict(binding)
