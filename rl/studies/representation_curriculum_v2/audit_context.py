#!/usr/bin/env python3
"""Render every v2 baseline input and prove that it fits without remote access."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from rl.evaluation.protocol import arm_spec, load_protocol
from rl.evaluation.runner import _messages, _sampler_target
from rl.evaluation.samplers import TinkerSampler
from rl.evaluation.tasks import load_task_manifest, load_task_set


REPO_ROOT = Path(__file__).resolve().parents[3]
PROTOCOL_FILE = Path(__file__).with_name("protocol.json")
TASK_MANIFEST_FILE = Path(__file__).with_name("task_manifest.json")


@contextmanager
def _offline_model_assets() -> Iterator[None]:
    """Fail closed rather than fetching a missing renderer asset."""

    names = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")
    previous = {name: os.environ.get(name) for name in names}
    os.environ.update({name: "1" for name in names})
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def audit_context() -> dict[str, Any]:
    """Return exact renderer lengths; raise before any remote client can exist."""

    protocol = load_protocol(REPO_ROOT, protocol_file=PROTOCOL_FILE)
    manifest = load_task_manifest(TASK_MANIFEST_FILE, repo_root=REPO_ROOT)
    tasks = load_task_set(
        repo_root=REPO_ROOT,
        manifest=manifest,
        task_set="f1_f8",
    )
    arm_ids = [
        arm_id
        for hypothesis in protocol["hypotheses"].values()
        for arm_id in hypothesis["arm_ids"]
    ]
    rows: list[dict[str, Any]] = []
    summaries: dict[str, dict[str, int]] = {}

    def forbidden_remote_client() -> Any:
        raise AssertionError("context audit must not create a remote client")

    with _offline_model_assets():
        for arm_id in arm_ids:
            arm = arm_spec(protocol, arm_id)
            sampler = TinkerSampler(
                _sampler_target(arm),
                service_client_factory=forbidden_remote_client,
            )
            arm_rows: list[dict[str, Any]] = []
            for task in tasks:
                prompt = sampler.build_prompt(_messages(task, arm))
                prompt_tokens = int(prompt.length)
                headroom = (
                    arm.context_tokens - arm.max_output_tokens - prompt_tokens
                )
                if headroom < 0:
                    raise ValueError(
                        f"{arm_id}/{task.task_id} exceeds its context window: "
                        f"{prompt_tokens}+{arm.max_output_tokens}>"
                        f"{arm.context_tokens}"
                    )
                arm_rows.append(
                    {
                        "arm_id": arm_id,
                        "task_id": task.task_id,
                        "prompt_tokens": prompt_tokens,
                        "max_output_tokens": arm.max_output_tokens,
                        "context_tokens": arm.context_tokens,
                        "headroom_tokens": headroom,
                    }
                )
            rows.extend(arm_rows)
            summaries[arm_id] = {
                "task_count": len(arm_rows),
                "max_prompt_tokens": max(
                    row["prompt_tokens"] for row in arm_rows
                ),
                "min_headroom_tokens": min(
                    row["headroom_tokens"] for row in arm_rows
                ),
            }
    return {
        "schema_version": "pixcell-direct-context-audit-v1",
        "study_id": protocol["study_id"],
        "protocol_sha256": protocol["logical_sha256"],
        "task_manifest_sha256": manifest["logical_sha256"],
        "remote_client_created": False,
        "summaries": summaries,
        "rows": rows,
    }


def main() -> None:
    print(json.dumps(audit_context(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
