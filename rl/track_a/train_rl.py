#!/usr/bin/env python3
"""Track A GRPO entrypoint — one curriculum stage.

Single-turn blind reconstruction with the shaped v3-b reward. One invocation
trains one level for ``max_steps`` steps with the exact ordered replay prefix
(80/20 five-step cycle); the campaign runner chains stages by passing the
previous stage's final weights as ``load_checkpoint_path``.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import chz
from tinker.types import LossFnType
from tinker_cookbook import cli_utils
from tinker_cookbook.rl.train import Config, main

from rl.track_a.curriculum import expected_replay_levels, normalize_level
from rl.track_a.launch import run_launch_preflight
from rl.track_a.tinker_data import (
    DEFAULT_MODEL,
    DEFAULT_RENDERER,
    TrackARLDatasetBuilder,
)


_TRACK_ROOT = Path(__file__).resolve().parent
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATASET_ROOT = _REPO_ROOT / "dataset"

CONFIRM_SPEND = "PIXCELL_RUNS_V2"


@chz.chz
class CLIConfig:
    confirm_spend: str = ""
    dataset_root: str = str(_DATASET_ROOT)
    model_name: str = DEFAULT_MODEL
    renderer_name: str = DEFAULT_RENDERER
    model_effort: float = -1.0
    load_checkpoint_path: str = ""
    current_level: str = "L0"
    lora_rank: int = 32
    group_size: int = 8
    groups_per_batch: int = 8
    learning_rate: float = 1e-5
    max_tokens: int = 4096
    temperature: float = 1.0
    max_steps: int = 30
    eval_every: int = 5
    save_every: int = 5
    validation_canaries: int = 40
    reward_policy: str = "shaped_v3b"
    replay_groups_per_step: int = 0
    log_path: str = str(_TRACK_ROOT / "runs" / "track-a-rl")
    loss_fn: LossFnType = "importance_sampling"
    wandb_project: str = ""
    wandb_name: str = ""
    skip_preflight: bool = False


async def cli_main(cfg: CLIConfig) -> None:
    from rl.track_a.transport import disable_pyqwest_transport

    disable_pyqwest_transport()
    if cfg.confirm_spend != CONFIRM_SPEND:
        raise SystemExit(
            f"paid launch blocked: pass confirm_spend={CONFIRM_SPEND}"
        )
    if not os.environ.get("TINKER_API_KEY"):
        raise SystemExit("TINKER_API_KEY is not present")
    current = normalize_level(cfg.current_level)
    replay_levels = expected_replay_levels(current)
    if not cfg.skip_preflight:
        run_launch_preflight(
            _REPO_ROOT,
            dataset_root=Path(cfg.dataset_root),
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            require_sandbox=True,
        )
    config = Config(
        learning_rate=cfg.learning_rate,
        dataset_builder=TrackARLDatasetBuilder(
            dataset_root=cfg.dataset_root,
            batch_size=cfg.groups_per_batch,
            group_size=cfg.group_size,
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            model_effort=cfg.model_effort if cfg.model_effort >= 0 else None,
            max_image=1440,
            current_level=current,
            replay_levels=",".join(replay_levels),
            validation_canaries=cfg.validation_canaries,
            reward_policy=cfg.reward_policy,
            replay_groups_per_step=cfg.replay_groups_per_step,
        ),
        model_name=cfg.model_name,
        recipe_name="pixcell_track_a_rl",
        renderer_name=cfg.renderer_name,
        lora_rank=cfg.lora_rank,
        load_checkpoint_path=cfg.load_checkpoint_path or None,
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
        num_groups_to_log=2,
        rollout_json_export=True,
        wandb_project=cfg.wandb_project or None,
        wandb_name=cfg.wandb_name or None,
    )
    cli_utils.check_log_dir(cfg.log_path, behavior_if_exists="resume")
    await main(config)


if __name__ == "__main__":
    asyncio.run(cli_main(chz.entrypoint(CLIConfig)))
