#!/usr/bin/env python3
"""Track A SFT entrypoint.

One stage of supervised fine-tuning over the frozen depth-v1 rows, with the
same blind prompt the RL env samples with (prompt identity is what makes the
checkpoint resumable by ``train_rl``). Level-filtered: the campaign's SFT
arms train on L0 only.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import chz
from tinker_cookbook import cli_utils
from tinker_cookbook.supervised.train import Config, main

from rl.track_a.launch import run_launch_preflight
from rl.track_a.tinker_data import (
    DEFAULT_MODEL,
    DEFAULT_RENDERER,
    TrackASupervisedDatasetBuilder,
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
    levels: str = "L0"
    lora_rank: int = 32
    learning_rate: float = 1e-4
    lr_schedule: str = "linear"
    num_epochs: int = 2
    batch_size: int = 64
    max_length: int = 6144
    max_image: int = 1440
    save_every: int = 5
    eval_every: int = 5
    log_path: str = str(_TRACK_ROOT / "runs" / "track-a-sft")
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
    if not cfg.skip_preflight:
        run_launch_preflight(
            _REPO_ROOT,
            dataset_root=Path(cfg.dataset_root),
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            require_sandbox=False,
            tokenize_sft=True,
            sft_levels=cfg.levels,
            max_length=cfg.max_length,
            max_image=cfg.max_image,
        )
    config = Config(
        log_path=cfg.log_path,
        model_name=cfg.model_name,
        recipe_name="pixcell_track_a_sft",
        renderer_name=cfg.renderer_name,
        dataset_builder=TrackASupervisedDatasetBuilder(
            dataset_root=cfg.dataset_root,
            model_name=cfg.model_name,
            renderer_name=cfg.renderer_name,
            batch_size=cfg.batch_size,
            max_length=cfg.max_length,
            max_image=cfg.max_image,
            levels=cfg.levels,
        ),
        learning_rate=cfg.learning_rate,
        lr_schedule=cfg.lr_schedule,
        num_epochs=cfg.num_epochs,
        lora_rank=cfg.lora_rank,
        adam_beta1=0.9,
        adam_beta2=0.95,
        adam_eps=1e-8,
        save_every=cfg.save_every,
        eval_every=cfg.eval_every,
        wandb_project=cfg.wandb_project or None,
        wandb_name=cfg.wandb_name or None,
    )
    cli_utils.check_log_dir(cfg.log_path, behavior_if_exists="resume")
    await main(config)


if __name__ == "__main__":
    asyncio.run(cli_main(chz.entrypoint(CLIConfig)))
