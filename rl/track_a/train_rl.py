#!/usr/bin/env python3
"""Spend-locked Track A G4 entrypoint."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import chz
from tinker.types import LossFnType
from tinker_cookbook import cli_utils
from tinker_cookbook.rl.train import Config, main

from rl.track_a.launch import run_launch_preflight
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
    if cfg.confirm_spend != "TRACK_A_RL":
        raise SystemExit(
            "paid launch blocked: pass confirm_spend=TRACK_A_RL after local preflight"
        )
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not present")
    if not cfg.load_checkpoint_path:
        raise SystemExit("load_checkpoint_path must name the selected SFT checkpoint")
    if not cfg.current_level:
        raise SystemExit(
            "current_level must be the first level not mastered by the selected SFT checkpoint"
        )
    run_launch_preflight(_REPO_ROOT)
    config = Config(
        learning_rate=cfg.learning_rate,
        dataset_builder=TrackARLDatasetBuilder(
            dataset_root=cfg.dataset_root,
            batch_size=cfg.groups_per_batch,
            group_size=cfg.group_size,
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            max_image=1440,
            current_level=cfg.current_level,
            replay_levels=cfg.replay_levels,
        ),
        model_name=cfg.model_name,
        recipe_name="pixcell_track_a_rl",
        renderer_name=cfg.renderer_name,
        lora_rank=cfg.lora_rank,
        load_checkpoint_path=cfg.load_checkpoint_path,
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        log_path=cfg.log_path,
        eval_every=cfg.eval_every,
        save_every=cfg.save_every,
        loss_fn=cfg.loss_fn,
        max_steps=cfg.max_steps,
        remove_constant_reward_groups=True,
        rollout_error_tolerance=True,
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
