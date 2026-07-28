"""Frozen protocol loading and exact baseline-launch binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rl.common.isolation import require_execution_boundary
from rl.common.preprocess import IMAGE_PREPROCESS_VERSION
from rl.common.prompt import CONTRACT_VERSION, prompt_asset_hashes
from rl.common.runtime import validate_runtime_stack
from rl.evaluation.tasks import (
    canonical_json_sha256,
    load_task_manifest,
    load_task_set,
)


PROTOCOL_SCHEMA = "pixcell-representation-curriculum-protocol-v1"
STUDY_RELATIVE_PATH = Path("rl/studies/representation_curriculum_v1")
PROTOCOL_FILENAME = "protocol.json"
TASK_MANIFEST_FILENAME = "task_manifest.json"
_SHA_RE = __import__("re").compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class ArmSpec:
    arm_id: str
    provider: str
    model: str
    renderer: str
    thinking: bool
    thinking_effort: float | None
    max_output_tokens: int
    context_tokens: int
    max_image_long_edge: int


@dataclass(frozen=True)
class JobSpec:
    hypothesis_id: str
    arm_id: str
    task_id: str
    attempt_index: int
    seed: int


def _logical_document(document: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in document.items() if key != "logical_sha256"}


def seal_protocol(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    document["logical_sha256"] = canonical_json_sha256(_logical_document(document))
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return document


def protocol_path(repo_root: Path, protocol_file: Path | None = None) -> Path:
    root = repo_root.expanduser().resolve()
    if protocol_file is None:
        return root / STUDY_RELATIVE_PATH / PROTOCOL_FILENAME
    candidate = protocol_file.expanduser().resolve(strict=True)
    if not candidate.is_relative_to(root):
        raise ValueError("baseline protocol must live inside the source repository")
    return candidate


def task_manifest_path(repo_root: Path) -> Path:
    return (
        repo_root.expanduser().resolve()
        / STUDY_RELATIVE_PATH
        / TASK_MANIFEST_FILENAME
    )


def _require_protocol_at_head(repo_root: Path, path: Path) -> None:
    root = repo_root.expanduser().resolve()
    candidate = path.expanduser().resolve(strict=True)
    if not candidate.is_relative_to(root):
        raise ValueError("baseline protocol must live inside the source repository")
    relative = candidate.relative_to(root).as_posix()
    try:
        subprocess.check_output(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
        committed = subprocess.check_output(
            ["git", "show", f"HEAD:{relative}"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(
            "baseline protocol must be tracked by the paid-launch commit"
        ) from exc
    if candidate.read_bytes() != committed:
        raise ValueError("baseline protocol bytes differ from the paid-launch commit")


def _validate_arm(arm_id: str, value: dict[str, Any]) -> ArmSpec:
    effort = value.get("thinking_effort")
    if effort is not None:
        effort = float(effort)
        if not math.isfinite(effort) or not 0 <= effort < 1:
            raise ValueError(f"{arm_id} has invalid thinking effort")
    result = ArmSpec(
        arm_id=arm_id,
        provider=str(value["provider"]),
        model=str(value["model"]),
        renderer=str(value["renderer"]),
        thinking=bool(value["thinking"]),
        thinking_effort=effort,
        max_output_tokens=int(value["max_output_tokens"]),
        context_tokens=int(value["context_tokens"]),
        max_image_long_edge=int(value["max_image_long_edge"]),
    )
    if result.provider != "tinker":
        raise ValueError(f"{arm_id} has unsupported provider {result.provider!r}")
    if result.max_output_tokens < 1 or result.context_tokens < 1:
        raise ValueError(f"{arm_id} has invalid token limits")
    if result.max_output_tokens >= result.context_tokens:
        raise ValueError(f"{arm_id} output cap exhausts the context window")
    if result.max_image_long_edge != 1440:
        raise ValueError(f"{arm_id} does not use the frozen 1440px image policy")
    if result.model == "thinkingmachines/Inkling":
        if result.renderer != "tml_v0" or result.thinking_effort is None:
            raise ValueError(f"{arm_id} has an invalid Inkling renderer contract")
    elif result.model == "Qwen/Qwen3.6-35B-A3B":
        expected = "qwen3_5" if result.thinking else "qwen3_5_disable_thinking"
        if result.renderer != expected or result.thinking_effort is not None:
            raise ValueError(f"{arm_id} has an invalid Qwen renderer contract")
    else:
        raise ValueError(f"{arm_id} uses an unregistered model")
    return result


def load_protocol(
    repo_root: Path,
    *,
    protocol_file: Path | None = None,
) -> dict[str, Any]:
    """Load a protocol only when it matches the active paid-launch contract."""

    root = repo_root.expanduser().resolve()
    document = load_archived_protocol(root, protocol_file=protocol_file)
    if document.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("protocol prompt contract does not match the runtime")
    arms = {
        arm_id: _validate_arm(arm_id, value)
        for arm_id, value in document["arms"].items()
    }
    if len(arms) != len(document["arms"]):
        raise ValueError("duplicate arm IDs")
    for hypothesis_id, hypothesis in document["hypotheses"].items():
        if not hypothesis_id.startswith("RC-H"):
            raise ValueError(f"invalid hypothesis ID: {hypothesis_id!r}")
        if hypothesis["status"] not in {"frozen", "conditional"}:
            raise ValueError(f"{hypothesis_id} is not launchable")
        if int(hypothesis["attempts_per_task"]) < 1:
            raise ValueError(f"{hypothesis_id} has no attempts")
        for arm_id in hypothesis.get("arm_ids", ()):
            if arm_id not in arms:
                raise ValueError(f"{hypothesis_id} names unknown arm {arm_id}")
        for wave_name, wave in hypothesis["waves"].items():
            indices = [int(value) for value in wave["attempt_indices"]]
            if wave_name not in {"smoke", "complete"}:
                raise ValueError(f"{hypothesis_id} has unsupported wave {wave_name}")
            if not indices or min(indices) < 1:
                raise ValueError(f"{hypothesis_id}/{wave_name} has invalid attempts")
            if max(indices) > int(hypothesis["attempts_per_task"]):
                raise ValueError(f"{hypothesis_id}/{wave_name} exceeds attempt count")
            if int(wave["task_count"]) < 1:
                raise ValueError(f"{hypothesis_id}/{wave_name} has no tasks")

    manifest = load_task_manifest(task_manifest_path(root), repo_root=root)
    expected_manifest_sha = document["task_manifest"]["logical_sha256"]
    if manifest["logical_sha256"] != expected_manifest_sha:
        raise ValueError("protocol does not bind the frozen task manifest")
    freeze = json.loads(
        (root / "dataset/depth-v1/factory/freeze.json").read_text(encoding="utf-8")
    )
    if (
        freeze["logical_release_sha256"]
        != document["dataset"]["logical_release_sha256"]
    ):
        raise ValueError("protocol does not bind the local depth release")
    return document


def load_archived_protocol(
    repo_root: Path,
    *,
    protocol_file: Path | None = None,
) -> dict[str, Any]:
    """Inspect a sealed historical protocol without making it launchable.

    This validates repository containment, schema, and the protocol's own
    logical digest. Paid entry points must use :func:`load_protocol`, which
    additionally requires the active model-visible contract.
    """

    root = repo_root.expanduser().resolve()
    document = json.loads(
        protocol_path(root, protocol_file).read_text(encoding="utf-8")
    )
    if document.get("schema_version") != PROTOCOL_SCHEMA:
        raise ValueError("unsupported representation-curriculum protocol schema")
    observed = canonical_json_sha256(_logical_document(document))
    if document.get("logical_sha256") != observed:
        raise ValueError("protocol logical SHA-256 mismatch")
    return document


def arm_spec(protocol: dict[str, Any], arm_id: str) -> ArmSpec:
    try:
        value = protocol["arms"][arm_id]
    except KeyError as exc:
        raise ValueError(f"unknown arm: {arm_id!r}") from exc
    return _validate_arm(arm_id, value)


def _validate_selection(
    protocol: dict[str, Any],
    selection: dict[str, Any],
) -> str:
    if selection.get("schema_version") != "pixcell-operating-point-selection-v1":
        raise ValueError("unsupported operating-point selection schema")
    if selection.get("study_id") != protocol["study_id"]:
        raise ValueError("operating-point selection belongs to another study")
    if selection.get("protocol_sha256") != protocol["logical_sha256"]:
        raise ValueError("operating-point selection has stale protocol provenance")
    if selection.get("source_hypothesis") != "RC-H00":
        raise ValueError("operating-point selection has the wrong source hypothesis")
    selected = str(selection.get("selected_arm", ""))
    allowed = set(protocol["hypotheses"]["RC-H00"]["arm_ids"])
    if selection.get("rescue_run"):
        allowed.update(protocol["hypotheses"]["RC-H00R"]["arm_ids"])
    if selected not in allowed:
        raise ValueError("operating-point selection names an ineligible arm")
    if not selection.get("complete"):
        raise ValueError("operating-point selection is not complete")
    return selected


def resolved_arm_ids(
    protocol: dict[str, Any],
    hypothesis_id: str,
    *,
    selection: dict[str, Any] | None,
) -> list[str]:
    try:
        hypothesis = protocol["hypotheses"][hypothesis_id]
    except KeyError as exc:
        raise ValueError(f"unknown hypothesis: {hypothesis_id!r}") from exc
    if hypothesis_id == "RC-H01":
        if selection is None:
            raise ValueError("RC-H01 requires the frozen operating-point selection")
        selected = _validate_selection(protocol, selection)
        incumbent = str(hypothesis["arm_roles"]["incumbent"])
        return [incumbent] if selected == incumbent else [incumbent, selected]
    if hypothesis_id == "RC-H00R":
        if selection is None or not selection.get("rescue_required"):
            raise ValueError("RC-H00R is forbidden unless RC-H00 triggers rescue")
    return [str(value) for value in hypothesis["arm_ids"]]


def deterministic_seed(
    protocol: dict[str, Any],
    *,
    task_id: str,
    attempt_index: int,
) -> int:
    namespace = str(protocol["sampling"]["seed_namespace"])
    digest = hashlib.sha256(
        f"{namespace}\0{task_id}\0{attempt_index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def jobs_for_wave(
    protocol: dict[str, Any],
    *,
    hypothesis_id: str,
    wave_name: str,
    task_ids: list[str],
    selection: dict[str, Any] | None = None,
) -> list[JobSpec]:
    hypothesis = protocol["hypotheses"].get(hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"unknown hypothesis: {hypothesis_id!r}")
    wave = hypothesis["waves"].get(wave_name)
    if wave is None:
        raise ValueError(f"{hypothesis_id} has no wave {wave_name!r}")
    count = int(wave["task_count"])
    if count > len(task_ids):
        raise ValueError(
            f"{hypothesis_id}/{wave_name} asks for {count} of {len(task_ids)} tasks"
        )
    arms = resolved_arm_ids(protocol, hypothesis_id, selection=selection)
    return [
        JobSpec(
            hypothesis_id=hypothesis_id,
            arm_id=arm_id,
            task_id=task_id,
            attempt_index=int(attempt_index),
            seed=deterministic_seed(
                protocol,
                task_id=task_id,
                attempt_index=int(attempt_index),
            ),
        )
        for attempt_index in wave["attempt_indices"]
        for task_id in task_ids[:count]
        for arm_id in arms
    ]


def _git_state(repo_root: Path) -> dict[str, Any]:
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
    ).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=repo_root,
        text=True,
    ).strip()
    return {"head": head, "clean": not bool(status)}


def _external_output_root(repo_root: Path, value: Path) -> Path:
    root = value.expanduser().resolve()
    repository = repo_root.expanduser().resolve()
    if (
        root == repository
        or root.is_relative_to(repository)
        or repository.is_relative_to(root)
    ):
        raise ValueError("mutable study output must not overlap the Git repository")
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir():
        raise ValueError("mutable study output is not a directory")
    return root


def build_launch_binding(
    *,
    repo_root: Path,
    hypothesis_id: str,
    wave_name: str,
    expected_source_sha: str,
    external_root: Path,
    selection: dict[str, Any] | None = None,
    protocol_file: Path | None = None,
) -> tuple[dict[str, Any], list[Any], list[JobSpec]]:
    """Resolve every semantic launch input before a remote client exists."""

    root = repo_root.expanduser().resolve()
    if not _SHA_RE.fullmatch(expected_source_sha):
        raise ValueError("expected_source_sha must be a full lowercase Git SHA")
    state = _git_state(root)
    if not state["clean"]:
        raise ValueError("paid baseline launch requires a clean worktree")
    if state["head"] != expected_source_sha:
        raise ValueError(
            f"source SHA mismatch: {state['head']} != {expected_source_sha}"
        )
    selected_protocol = protocol_path(root, protocol_file)
    _require_protocol_at_head(root, selected_protocol)
    protocol = load_protocol(root, protocol_file=selected_protocol)
    runtime = validate_runtime_stack(root)
    manifest = load_task_manifest(task_manifest_path(root), repo_root=root)
    hypothesis = protocol["hypotheses"].get(hypothesis_id)
    if hypothesis is None:
        raise ValueError(f"unknown hypothesis: {hypothesis_id!r}")
    task_set_name = str(hypothesis["task_set"])
    tasks = load_task_set(
        repo_root=root,
        manifest=manifest,
        task_set=task_set_name,
    )
    jobs = jobs_for_wave(
        protocol,
        hypothesis_id=hypothesis_id,
        wave_name=wave_name,
        task_ids=[task.task_id for task in tasks],
        selection=selection,
    )
    boundary = require_execution_boundary()
    output_root = _external_output_root(root, external_root)
    assets = prompt_asset_hashes()
    prompt_binding = {
        "contract_version": CONTRACT_VERSION,
        "preprocess_version": IMAGE_PREPROCESS_VERSION,
        **assets,
    }
    task_entries = manifest["task_sets"][task_set_name]
    arms = {
        arm_id: protocol["arms"][arm_id]
        for arm_id in resolved_arm_ids(
            protocol,
            hypothesis_id,
            selection=selection,
        )
    }
    binding = {
        "schema_version": "pixcell-baseline-launch-binding-v1",
        "study_id": protocol["study_id"],
        "hypothesis_id": hypothesis_id,
        "wave": wave_name,
        "source_git_sha": state["head"],
        "protocol_path": selected_protocol.relative_to(root).as_posix(),
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "task_set": task_set_name,
        "task_set_sha256": canonical_json_sha256(task_entries),
        "task_count": len({job.task_id for job in jobs}),
        "job_count": len(jobs),
        "prompt": prompt_binding,
        "prompt_sha256": canonical_json_sha256(prompt_binding),
        "arms": arms,
        "sampling": protocol["sampling"],
        "runtime": runtime,
        "sandbox": {
            "runtime_path": str(boundary.runtime_path),
            "daemon_endpoint": boundary.daemon_endpoint,
            "image_ref": boundary.image_ref,
            "image_id": boundary.image_id,
            "workspace_root": str(boundary.workspace_root),
        },
        "external_root": str(output_root),
        "selection_sha256": (
            canonical_json_sha256(selection) if selection is not None else None
        ),
        "jobs_sha256": canonical_json_sha256(
            [
                {
                    "hypothesis_id": job.hypothesis_id,
                    "arm_id": job.arm_id,
                    "task_id": job.task_id,
                    "attempt_index": job.attempt_index,
                    "seed": job.seed,
                }
                for job in jobs
            ]
        ),
    }
    binding["binding_sha256"] = canonical_json_sha256(binding)
    return binding, tasks, jobs


def required_credentials(protocol: dict[str, Any]) -> tuple[str, ...]:
    result = ["TINKER_API_KEY"]
    if protocol["tracking"]["mode"] == "online":
        result.append("WANDB_API_KEY")
    return tuple(result)


def validate_credentials(protocol: dict[str, Any]) -> None:
    missing = [key for key in required_credentials(protocol) if not os.getenv(key)]
    if missing:
        raise ValueError(f"missing launch credentials: {', '.join(missing)}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--seal", type=Path)
    return result


def main() -> None:
    args = parser().parse_args()
    if args.seal is None:
        raise SystemExit("--seal is required")
    document = seal_protocol(args.seal)
    print(document["logical_sha256"])


if __name__ == "__main__":
    main()
