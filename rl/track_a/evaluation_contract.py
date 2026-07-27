"""Provenance and validation contract for Track A checkpoint reports."""

from __future__ import annotations

import hashlib
import json
import math
import re
import statistics
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.common.dataset_io import load_tasks
from rl.common.isolation import IMMUTABLE_IMAGE
from rl.track_a.curriculum import balanced_effective_pass


REPORT_SCHEMA_VERSION = "pixcell-track-a-executable-eval-v2"
DATASET_CONFIGURATION = "depth"
DATASET_SPLIT = "validation"
REPORT_SPLIT = f"{DATASET_CONFIGURATION}/{DATASET_SPLIT}"
CURRICULUM_LEVELS = ("L0", "L1", "L2", "L3", "L4")
FULL_GEOMETRY_TASKS = 1092
FULL_GEOMETRY_REPRESENTATIONS = 546
BEHAVIORAL_PROBE_TASKS = 40
BEHAVIORAL_PROBE_K = 4
BEHAVIORAL_PROBE_ATTEMPTS = BEHAVIORAL_PROBE_TASKS * BEHAVIORAL_PROBE_K
TASK_SELECTION_SEED = 7

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


def task_ids_sha256(opaque_ids: Sequence[str]) -> str:
    """Hash an exact task multiset independently of evaluation order."""

    payload = json.dumps(
        sorted(str(value) for value in opaque_ids),
        ensure_ascii=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _source_git_sha(repo_root: Path) -> str:
    value = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    if not _GIT_SHA_RE.fullmatch(value):
        raise RuntimeError(f"invalid source Git SHA: {value!r}")
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
    ).strip()
    if status:
        raise RuntimeError(
            "checkpoint report provenance requires a clean committed worktree"
        )
    return value


def _depth_release_sha256(dataset_root: Path) -> str:
    freeze_path = dataset_root / "depth-v1" / "factory" / "freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    value = str(freeze.get("logical_release_sha256", ""))
    if not _SHA256_RE.fullmatch(value):
        raise RuntimeError(
            f"{freeze_path} has no valid logical_release_sha256"
        )
    return value


@dataclass(frozen=True)
class CheckpointSelectionContract:
    """Immutable facts every report used for checkpoint selection must match."""

    source_git_sha: str
    depth_logical_release_sha256: str
    model: str
    renderer: str
    temperature: float
    top_p: float
    max_tokens: int
    task_selection_seed: int
    geometry_task_ids_sha256: str
    behavioral_task_ids_sha256_by_level: Mapping[str, str]


def build_checkpoint_selection_contract(
    repo_root: Path,
    dataset_root: Path,
) -> CheckpointSelectionContract:
    """Build the expected report contract from the committed recipe and data."""

    repo_root = repo_root.resolve()
    dataset_root = dataset_root.resolve()
    expected_dataset_root = (repo_root / "dataset").resolve()
    if dataset_root != expected_dataset_root:
        raise RuntimeError(
            "checkpoint report dataset_root must be the committed dataset at "
            f"{expected_dataset_root}; got {dataset_root}"
        )
    config = json.loads(
        (repo_root / "rl" / "track_a" / "config.json").read_text(
            encoding="utf-8"
        )
    )
    validation = load_tasks(
        dataset_root,
        configuration=DATASET_CONFIGURATION,
        split=DATASET_SPLIT,
    )
    if len(validation) != FULL_GEOMETRY_TASKS:
        raise RuntimeError(
            "checkpoint selection requires the complete frozen validation "
            f"split ({FULL_GEOMETRY_TASKS} tasks); observed {len(validation)}"
        )
    representation_count = len(
        {task.sampler.representation_id for task in validation}
    )
    if representation_count != FULL_GEOMETRY_REPRESENTATIONS:
        raise RuntimeError(
            "checkpoint selection requires the complete frozen validation "
            f"representation set ({FULL_GEOMETRY_REPRESENTATIONS}); "
            f"observed {representation_count}"
        )

    observed_levels = {
        task.sampler.level.upper() for task in validation
    }
    if observed_levels != set(CURRICULUM_LEVELS):
        raise RuntimeError(
            "validation curriculum levels differ from the report contract: "
            f"{sorted(observed_levels)}"
        )

    behavioral_digests: dict[str, str] = {}
    for level in CURRICULUM_LEVELS:
        level_tasks = [
            task
            for task in validation
            if task.sampler.level.upper() == level
        ]
        selected = balanced_effective_pass(
            level_tasks,
            seed=TASK_SELECTION_SEED,
            draws=BEHAVIORAL_PROBE_TASKS,
        )
        selected_ids = [task.sampler.opaque_id for task in selected]
        if (
            len(selected_ids) != BEHAVIORAL_PROBE_TASKS
            or len(set(selected_ids)) != BEHAVIORAL_PROBE_TASKS
        ):
            raise RuntimeError(
                f"{level} behavioral task selection is not exactly "
                f"{BEHAVIORAL_PROBE_TASKS} unique tasks"
            )
        behavioral_digests[level] = task_ids_sha256(selected_ids)

    model = config["model"]
    rl = config["rl"]
    return CheckpointSelectionContract(
        source_git_sha=_source_git_sha(repo_root),
        depth_logical_release_sha256=_depth_release_sha256(dataset_root),
        model=str(model["name"]),
        renderer=str(model["renderer"]),
        temperature=float(rl["temperature"]),
        top_p=float(rl["top_p"]),
        max_tokens=int(rl["max_output_tokens"]),
        task_selection_seed=TASK_SELECTION_SEED,
        geometry_task_ids_sha256=task_ids_sha256(
            [task.sampler.opaque_id for task in validation]
        ),
        behavioral_task_ids_sha256_by_level=behavioral_digests,
    )


def report_provenance(
    *,
    contract: CheckpointSelectionContract,
    sampler_path: str,
    role: str,
    levels: Sequence[str],
    task_ids: Sequence[str],
    representation_count: int,
    requested_rows: int | None,
    k: int,
    attempt_count: int,
    sandbox_image_ref: str,
    sandbox_image_id: str,
) -> dict[str, Any]:
    """Create the complete provenance record written beside eval metrics."""

    return {
        "source_git_sha": contract.source_git_sha,
        "depth_logical_release_sha256": (
            contract.depth_logical_release_sha256
        ),
        "dataset_configuration": DATASET_CONFIGURATION,
        "split": REPORT_SPLIT,
        "model": contract.model,
        "renderer": contract.renderer,
        "sampler_path": sampler_path,
        "evaluation_role": role,
        "levels": sorted(str(level).upper() for level in levels),
        "requested_rows": requested_rows,
        "task_count": len(task_ids),
        "attempt_count": attempt_count,
        "representation_count": representation_count,
        "task_ids_sha256": task_ids_sha256(task_ids),
        "task_selection_seed": contract.task_selection_seed,
        "candidate_sandbox": {
            "contract": "per-candidate-docker-v1",
            "image_ref": sandbox_image_ref,
            "image_id": sandbox_image_id,
        },
        "sampling": {
            "k": k,
            "temperature": contract.temperature,
            "top_p": contract.top_p,
            "max_tokens": contract.max_tokens,
        },
    }


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    return value


def _integer(value: Any, path: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{path} must be an integer")
    if value < minimum:
        raise ValueError(f"{path} must be >= {minimum}")
    return value


def _finite(value: Any, path: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{path} must be numeric")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{path} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{path} must be finite")
    return result


def _unit_metric(value: Any, path: str) -> float:
    result = _finite(value, path)
    if result < 0.0 or result > 1.0:
        raise ValueError(f"{path} must be in [0, 1]")
    return result


def _bounded_metric(value: Any, path: str, *, low: float, high: float) -> float:
    result = _finite(value, path)
    if result < low or result > high:
        raise ValueError(f"{path} must be in [{low}, {high}]")
    return result


def _exact(value: Any, expected: Any, path: str) -> None:
    if value != expected:
        raise ValueError(f"{path}={value!r}; expected {expected!r}")


def _close(value: float, expected: float, path: str) -> None:
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{path}={value!r}; expected {expected!r}")


def _validate_summary(
    summary: Any,
    *,
    path: str,
    tasks: int,
    attempts: int,
) -> None:
    values = _mapping(summary, path)
    _exact(_integer(values.get("tasks"), f"{path}.tasks"), tasks, f"{path}.tasks")
    _exact(
        _integer(values.get("attempts"), f"{path}.attempts"),
        attempts,
        f"{path}.attempts",
    )
    for field in (
        "pure_executable_rate",
        "mean_iou_at_1",
        "mean_best_at_k_iou",
    ):
        _unit_metric(values.get(field), f"{path}.{field}")


def _validate_behavioral_probe(
    value: Any,
    *,
    expected_task_ids_sha256: str,
) -> None:
    probe = _mapping(value, "behavioral_probe")
    _exact(
        probe.get("probe_kind"),
        "small-balanced-unmastered-g4",
        "behavioral_probe.probe_kind",
    )
    _exact(
        _integer(probe.get("group_size"), "behavioral_probe.group_size"),
        BEHAVIORAL_PROBE_K,
        "behavioral_probe.group_size",
    )
    _exact(
        _integer(probe.get("prompt_groups"), "behavioral_probe.prompt_groups"),
        BEHAVIORAL_PROBE_TASKS,
        "behavioral_probe.prompt_groups",
    )
    nonconstant_fraction = _unit_metric(
        probe.get("nonconstant_reward_group_fraction"),
        "behavioral_probe.nonconstant_reward_group_fraction",
    )
    mean_reward_std = _unit_metric(
        probe.get("mean_within_group_reward_std"),
        "behavioral_probe.mean_within_group_reward_std",
    )
    mean_programs = _bounded_metric(
        probe.get("mean_distinct_programs_per_prompt"),
        "behavioral_probe.mean_distinct_programs_per_prompt",
        low=1.0,
        high=float(BEHAVIORAL_PROBE_K),
    )
    mean_renders = _bounded_metric(
        probe.get("mean_distinct_successful_renders_per_prompt"),
        "behavioral_probe.mean_distinct_successful_renders_per_prompt",
        low=0.0,
        high=float(BEHAVIORAL_PROBE_K),
    )
    collapsed = probe.get("collapse_detected")
    if not isinstance(collapsed, bool):
        raise ValueError("behavioral_probe.collapse_detected must be boolean")

    signals = _mapping(
        probe.get("collapse_signals"),
        "behavioral_probe.collapse_signals",
    )
    for field in (
        "identical_program_every_group",
        "constant_render_and_reward_every_group",
    ):
        if not isinstance(signals.get(field), bool):
            raise ValueError(
                f"behavioral_probe.collapse_signals.{field} must be boolean"
            )

    groups = probe.get("groups")
    if not isinstance(groups, list):
        raise ValueError("behavioral_probe.groups must be an array")
    if len(groups) != BEHAVIORAL_PROBE_TASKS:
        raise ValueError(
            f"behavioral_probe.groups has {len(groups)} entries; "
            f"expected {BEHAVIORAL_PROBE_TASKS}"
        )
    opaque_ids: list[str] = []
    group_program_counts: list[int] = []
    group_render_counts: list[int] = []
    group_reward_stds: list[float] = []
    group_nonconstant: list[bool] = []
    for index, raw_group in enumerate(groups):
        path = f"behavioral_probe.groups[{index}]"
        group = _mapping(raw_group, path)
        opaque_id = str(group.get("opaque_id", ""))
        if not opaque_id:
            raise ValueError(f"{path}.opaque_id must be non-empty")
        opaque_ids.append(opaque_id)
        distinct_programs = _integer(
            group.get("distinct_program_count"),
            f"{path}.distinct_program_count",
            minimum=1,
        )
        if distinct_programs > BEHAVIORAL_PROBE_K:
            raise ValueError(
                f"{path}.distinct_program_count exceeds {BEHAVIORAL_PROBE_K}"
            )
        group_program_counts.append(distinct_programs)
        successful = _integer(
            group.get("successful_render_attempts"),
            f"{path}.successful_render_attempts",
        )
        if successful > BEHAVIORAL_PROBE_K:
            raise ValueError(
                f"{path}.successful_render_attempts exceeds "
                f"{BEHAVIORAL_PROBE_K}"
            )
        distinct_renders = _integer(
            group.get("distinct_successful_render_count"),
            f"{path}.distinct_successful_render_count",
        )
        if distinct_renders > successful:
            raise ValueError(
                f"{path}.distinct_successful_render_count exceeds "
                "successful_render_attempts"
            )
        group_render_counts.append(distinct_renders)
        group_reward_stds.append(
            _unit_metric(group.get("reward_std"), f"{path}.reward_std")
        )
        _unit_metric(group.get("reward_range"), f"{path}.reward_range")
        nonconstant = group.get("nonconstant_reward")
        if not isinstance(nonconstant, bool):
            raise ValueError(f"{path}.nonconstant_reward must be boolean")
        group_nonconstant.append(nonconstant)

    if len(set(opaque_ids)) != BEHAVIORAL_PROBE_TASKS:
        raise ValueError("behavioral_probe.groups contains duplicate tasks")
    observed_digest = task_ids_sha256(opaque_ids)
    if observed_digest != expected_task_ids_sha256:
        raise ValueError(
            "behavioral_probe.groups task set differs from provenance"
        )

    expected_nonconstant_fraction = (
        sum(group_nonconstant) / BEHAVIORAL_PROBE_TASKS
    )
    expected_mean_reward_std = statistics.fmean(group_reward_stds)
    expected_mean_programs = statistics.fmean(group_program_counts)
    expected_mean_renders = statistics.fmean(group_render_counts)
    _close(
        nonconstant_fraction,
        expected_nonconstant_fraction,
        "behavioral_probe.nonconstant_reward_group_fraction",
    )
    _close(
        mean_reward_std,
        expected_mean_reward_std,
        "behavioral_probe.mean_within_group_reward_std",
    )
    _close(
        mean_programs,
        expected_mean_programs,
        "behavioral_probe.mean_distinct_programs_per_prompt",
    )
    _close(
        mean_renders,
        expected_mean_renders,
        "behavioral_probe.mean_distinct_successful_renders_per_prompt",
    )
    identical_program_every_group = all(
        count == 1 for count in group_program_counts
    )
    constant_render_and_reward_every_group = all(
        render_count <= 1 and not nonconstant
        for render_count, nonconstant in zip(
            group_render_counts,
            group_nonconstant,
            strict=True,
        )
    )
    expected_collapsed = (
        identical_program_every_group
        or constant_render_and_reward_every_group
    )
    _exact(
        signals.get("identical_program_every_group"),
        identical_program_every_group,
        "behavioral_probe.collapse_signals.identical_program_every_group",
    )
    _exact(
        signals.get("constant_render_and_reward_every_group"),
        constant_render_and_reward_every_group,
        "behavioral_probe.collapse_signals."
        "constant_render_and_reward_every_group",
    )
    _exact(
        collapsed,
        expected_collapsed,
        "behavioral_probe.collapse_detected",
    )


def validate_evaluation_report(
    report: Mapping[str, Any],
    *,
    contract: CheckpointSelectionContract,
    expected_role: str,
) -> None:
    """Fail closed unless a report exactly matches the selection contract."""

    _exact(
        report.get("schema_version"),
        REPORT_SCHEMA_VERSION,
        "schema_version",
    )
    _exact(report.get("evaluation_role"), expected_role, "evaluation_role")
    provenance = _mapping(report.get("provenance"), "provenance")

    shared_expected = {
        "source_git_sha": contract.source_git_sha,
        "depth_logical_release_sha256": (
            contract.depth_logical_release_sha256
        ),
        "dataset_configuration": DATASET_CONFIGURATION,
        "split": REPORT_SPLIT,
        "model": contract.model,
        "renderer": contract.renderer,
        "evaluation_role": expected_role,
        "task_selection_seed": contract.task_selection_seed,
    }
    for field, expected in shared_expected.items():
        _exact(provenance.get(field), expected, f"provenance.{field}")

    sandbox = _mapping(
        provenance.get("candidate_sandbox"),
        "provenance.candidate_sandbox",
    )
    _exact(
        sandbox.get("contract"),
        "per-candidate-docker-v1",
        "provenance.candidate_sandbox.contract",
    )
    image_ref = str(sandbox.get("image_ref", ""))
    if not IMMUTABLE_IMAGE.fullmatch(image_ref):
        raise ValueError(
            "provenance.candidate_sandbox.image_ref must be immutable"
        )
    image_id = str(sandbox.get("image_id", ""))
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError(
            "provenance.candidate_sandbox.image_id must be a SHA-256 image ID"
        )

    sampler_path = str(report.get("sampler_path", ""))
    if not sampler_path:
        raise ValueError("sampler_path must be non-empty")
    _exact(provenance.get("sampler_path"), sampler_path, "provenance.sampler_path")
    _exact(report.get("model"), contract.model, "model")
    _exact(report.get("renderer"), contract.renderer, "renderer")
    _exact(report.get("split"), REPORT_SPLIT, "split")

    sampling = _mapping(provenance.get("sampling"), "provenance.sampling")
    expected_sampling = {
        "temperature": contract.temperature,
        "top_p": contract.top_p,
        "max_tokens": contract.max_tokens,
    }
    for field, expected in expected_sampling.items():
        observed = sampling.get(field)
        if isinstance(expected, float):
            observed = _finite(observed, f"provenance.sampling.{field}")
        else:
            observed = _integer(observed, f"provenance.sampling.{field}")
        _exact(observed, expected, f"provenance.sampling.{field}")
        _exact(report.get(field), expected, field)

    levels = provenance.get("levels")
    if not isinstance(levels, list) or any(
        not isinstance(level, str) for level in levels
    ):
        raise ValueError("provenance.levels must be an array of strings")
    if levels != sorted(set(levels)):
        raise ValueError("provenance.levels must be sorted and unique")

    task_count = _integer(provenance.get("task_count"), "provenance.task_count")
    attempt_count = _integer(
        provenance.get("attempt_count"),
        "provenance.attempt_count",
    )
    representation_count = _integer(
        provenance.get("representation_count"),
        "provenance.representation_count",
    )
    task_digest = str(provenance.get("task_ids_sha256", ""))
    if not _SHA256_RE.fullmatch(task_digest):
        raise ValueError("provenance.task_ids_sha256 must be a SHA-256 digest")
    k = _integer(sampling.get("k"), "provenance.sampling.k", minimum=1)
    _exact(report.get("k"), k, "k")
    _exact(report.get("levels"), "all" if len(levels) > 1 else levels[0], "levels")
    _exact(attempt_count, task_count * k, "provenance.attempt_count")

    if expected_role == "checkpoint-geometry":
        _exact(levels, list(CURRICULUM_LEVELS), "provenance.levels")
        _exact(
            provenance.get("requested_rows"),
            None,
            "provenance.requested_rows",
        )
        _exact(task_count, FULL_GEOMETRY_TASKS, "provenance.task_count")
        _exact(attempt_count, FULL_GEOMETRY_TASKS, "provenance.attempt_count")
        _exact(
            representation_count,
            FULL_GEOMETRY_REPRESENTATIONS,
            "provenance.representation_count",
        )
        _exact(k, 1, "provenance.sampling.k")
        _exact(
            task_digest,
            contract.geometry_task_ids_sha256,
            "provenance.task_ids_sha256",
        )
        if report.get("behavioral_probe") is not None:
            raise ValueError(
                "checkpoint-geometry report must not contain behavioral_probe"
            )
    elif expected_role == "behavioral-collapse-probe":
        if len(levels) != 1 or levels[0] not in CURRICULUM_LEVELS:
            raise ValueError(
                "behavioral report must name exactly one curriculum level"
            )
        _exact(
            provenance.get("requested_rows"),
            BEHAVIORAL_PROBE_TASKS,
            "provenance.requested_rows",
        )
        _exact(task_count, BEHAVIORAL_PROBE_TASKS, "provenance.task_count")
        _exact(
            attempt_count,
            BEHAVIORAL_PROBE_ATTEMPTS,
            "provenance.attempt_count",
        )
        if representation_count < 1 or representation_count > task_count:
            raise ValueError(
                "provenance.representation_count is outside task bounds"
            )
        _exact(k, BEHAVIORAL_PROBE_K, "provenance.sampling.k")
        expected_digest = contract.behavioral_task_ids_sha256_by_level.get(
            levels[0]
        )
        if expected_digest is None:
            raise ValueError(
                f"no behavioral task contract for level {levels[0]!r}"
            )
        _exact(
            task_digest,
            expected_digest,
            "provenance.task_ids_sha256",
        )
        _validate_behavioral_probe(
            report.get("behavioral_probe"),
            expected_task_ids_sha256=expected_digest,
        )
    else:
        raise ValueError(f"unsupported evaluation role: {expected_role!r}")

    _validate_summary(
        report.get("summary"),
        path="summary",
        tasks=task_count,
        attempts=attempt_count,
    )
    _unit_metric(
        report.get("representation_macro_mean_iou"),
        "representation_macro_mean_iou",
    )
    completion_tokens = _finite(
        report.get("mean_completion_tokens"),
        "mean_completion_tokens",
    )
    if completion_tokens < 0:
        raise ValueError("mean_completion_tokens must be non-negative")

    statuses = _mapping(report.get("statuses"), "statuses")
    status_total = sum(
        _integer(value, f"statuses.{name}") for name, value in statuses.items()
    )
    _exact(status_total, attempt_count, "statuses total")

    levels_summary = _mapping(report.get("levels_summary"), "levels_summary")
    _exact(sorted(levels_summary), levels, "levels_summary keys")
    level_tasks = 0
    level_attempts = 0
    for level, summary in levels_summary.items():
        values = _mapping(summary, f"levels_summary.{level}")
        tasks = _integer(values.get("tasks"), f"levels_summary.{level}.tasks")
        attempts = _integer(
            values.get("attempts"),
            f"levels_summary.{level}.attempts",
        )
        _validate_summary(
            values,
            path=f"levels_summary.{level}",
            tasks=tasks,
            attempts=attempts,
        )
        level_tasks += tasks
        level_attempts += attempts
    _exact(level_tasks, task_count, "levels_summary task total")
    _exact(level_attempts, attempt_count, "levels_summary attempt total")

    records = report.get("records")
    if records is not None:
        if not isinstance(records, list):
            raise ValueError("records must be null or an array")
        if len(records) != attempt_count:
            raise ValueError(
                f"records has {len(records)} entries; expected {attempt_count}"
            )
        record_ids: list[str] = []
        counts: Counter[str] = Counter()
        for index, raw_record in enumerate(records):
            path = f"records[{index}]"
            record = _mapping(raw_record, path)
            opaque_id = str(record.get("opaque_id", ""))
            if not opaque_id:
                raise ValueError(f"{path}.opaque_id must be non-empty")
            record_ids.append(opaque_id)
            counts[opaque_id] += 1
            _unit_metric(record.get("iou"), f"{path}.iou")
            _unit_metric(record.get("reward"), f"{path}.reward")
            if not isinstance(record.get("pure_executable"), bool):
                raise ValueError(f"{path}.pure_executable must be boolean")
            _integer(
                record.get("completion_tokens"),
                f"{path}.completion_tokens",
            )
        if set(counts.values()) != {k}:
            raise ValueError(f"records must contain exactly {k} attempts per task")
        if task_ids_sha256(list(counts)) != task_digest:
            raise ValueError("records task set differs from provenance")
