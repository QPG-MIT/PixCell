#!/usr/bin/env python3
"""Spend-locked Track A G4 entrypoint."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import chz
from tinker.types import LossFnType
from tinker_cookbook import cli_utils
from tinker_cookbook.rl.train import Config, main

from rl.common.isolation import IsolationError
from rl.track_a.evaluation_contract import (
    build_checkpoint_selection_contract,
    validate_evaluation_report,
)
from rl.track_a.launch import bind_execution_boundary, run_launch_preflight
from rl.track_a.recipe import validate_rl_cli
from rl.track_a.tinker_data import (
    DEFAULT_MODEL,
    DEFAULT_RENDERER,
    TrackARLDatasetBuilder,
)


_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATASET_ROOT = _REPO_ROOT / "dataset"


@chz.chz
class CLIConfig:
    confirm_spend: str = ""
    dataset_root: str = str(_DATASET_ROOT)
    model_name: str = DEFAULT_MODEL
    renderer_name: str = DEFAULT_RENDERER
    load_checkpoint_path: str = ""
    mastery_report: str = ""
    current_level: str = ""
    replay_levels: str = ""
    lora_rank: int = 32
    group_size: int = 4
    groups_per_batch: int = 8
    learning_rate: float = 1e-5
    max_tokens: int = 4096
    temperature: float = 1.0
    max_steps: int = 30
    eval_every: int = 5
    save_every: int = 5
    log_path: str = str(_TRACK_ROOT / "runs" / "track-a-rl")
    loss_fn: LossFnType = "importance_sampling"


async def cli_main(cfg: CLIConfig) -> None:
    if not cfg.mastery_report.strip():
        raise SystemExit("paid launch blocked: mastery_report is required")
    try:
        mastery_path = Path(cfg.mastery_report).expanduser().resolve(strict=True)
        mastery_report = json.loads(mastery_path.read_text(encoding="utf-8"))
        if not isinstance(mastery_report, dict):
            raise ValueError("mastery report must be a JSON object")
        report_contract = build_checkpoint_selection_contract(
            _REPO_ROOT,
            Path(cfg.dataset_root),
        )
        validate_evaluation_report(
            mastery_report,
            contract=report_contract,
            expected_role="checkpoint-geometry",
        )
        resolved_launch = validate_rl_cli(
            _REPO_ROOT,
            cfg,
            mastery_report=mastery_report,
        )
        resolved_launch = bind_execution_boundary(resolved_launch)
    except (
        OSError,
        json.JSONDecodeError,
        RuntimeError,
        ValueError,
        IsolationError,
    ) as exc:
        raise SystemExit(f"paid launch blocked: {exc}") from exc
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not present")
    run_launch_preflight(_REPO_ROOT, resolved_launch=resolved_launch)
    config = Config(
        learning_rate=cfg.learning_rate,
        dataset_builder=TrackARLDatasetBuilder(
            dataset_root=cfg.dataset_root,
            batch_size=cfg.groups_per_batch,
            group_size=cfg.group_size,
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            max_image=1440,
            current_level=str(resolved_launch["current_level"]),
            replay_levels=",".join(resolved_launch["replay_levels"]),
        ),
        model_name=cfg.model_name,
        recipe_name="pixcell_track_a_rl",
        renderer_name=cfg.renderer_name,
        lora_rank=cfg.lora_rank,
        load_checkpoint_path=str(resolved_launch["load_checkpoint_path"]),
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        log_path=cfg.log_path,
        eval_every=cfg.eval_every,
        save_every=cfg.save_every,
        loss_fn=cfg.loss_fn,
        max_steps=cfg.max_steps,
        remove_constant_reward_groups=True,
        # Candidate mistakes return typed zero rewards. Reference or
        # evaluator faults have already exhausted the evaluator's one retry
        # and must abort rather than silently dropping a biased group.
        rollout_error_tolerance=False,
        kl_penalty_coef=0.0,
        num_groups_to_log=0,
    )
    cli_utils.check_log_dir(
        cfg.log_path,
        behavior_if_exists="raise",
    )
    await main(config)


if __name__ == "__main__":
    asyncio.run(cli_main(chz.entrypoint(CLIConfig)))
