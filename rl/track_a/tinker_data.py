"""Tinker Cookbook adapters over the dataset-native Track A contract.

Importing this module is free. A Tinker client is created only by the guarded
training entrypoints.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from functools import partial
from pathlib import Path

import chz
import tinker
from tinker_cookbook.image_processing_utils import get_image_processor
from tinker_cookbook.renderers import (
    ImagePart,
    Message,
    TextPart,
    TrainOnWhat,
    get_renderer,
)
from tinker_cookbook.rl.problem_env import ProblemGroupBuilder
from tinker_cookbook.rl.types import (
    Env,
    EnvGroupBuilder,
    RLDataset,
    RLDatasetBuilder,
    StepResult,
)
from tinker_cookbook.supervised.data import conversation_to_datum
from tinker_cookbook.supervised.types import (
    SupervisedDataset,
    SupervisedDatasetBuilder,
)
from tinker_cookbook.tokenizer_utils import get_tokenizer

from rl.common.batcher import AsyncEvaluationBatcher
from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks
from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.track_a.curriculum import (
    balanced_effective_pass,
    hierarchical_sft_weights,
    stratified_physical_pass,
)
from rl.track_a.preprocess import model_image
from rl.track_a.prompt import build_prompt_text
from rl.track_a.reward import reward_for


DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_RENDERER = "qwen3_5_disable_thinking"
DEFAULT_MAX_IMAGE = 1440
_EVALUATION_BATCHER: AsyncEvaluationBatcher | None = None


class BrokenReferenceError(RuntimeError):
    """Fatal dataset/reference failure; the paid run should stop."""


class EvaluationInfrastructureError(RuntimeError):
    """Retry-exhausted evaluator fault; cookbook drops the affected group."""


def _message(task: TaskRecord, *, max_image: int) -> Message:
    return Message(
        role="user",
        content=[
            ImagePart(
                type="image",
                image=model_image(task.observation, max_long_edge=max_image),
            ),
            TextPart(type="text", text=build_prompt_text(task.observation)),
        ],
    )


def _renderer(model_name: str, renderer_name: str):
    tokenizer = get_tokenizer(model_name)
    processor = get_image_processor(model_name)
    return get_renderer(
        renderer_name,
        tokenizer,
        processor,
        model_name=model_name,
    )


def _batcher() -> AsyncEvaluationBatcher:
    global _EVALUATION_BATCHER
    if _EVALUATION_BATCHER is None:
        evaluator = PixCellEvaluator(max_workers=8, evaluator_retries=1)
        _EVALUATION_BATCHER = AsyncEvaluationBatcher(
            evaluator,
            max_batch_size=32,
            flush_delay_seconds=0.01,
        )
    return _EVALUATION_BATCHER


class TrackASupervisedDataset(SupervisedDataset):
    def __init__(
        self,
        tasks: list[TaskRecord],
        renderer,
        *,
        batch_size: int,
        max_length: int,
        max_image: int,
        balanced: bool,
    ) -> None:
        self._source = list(tasks)
        self.renderer = renderer
        self.batch_size = batch_size
        self.max_length = max_length
        self.max_image = max_image
        self.balanced = balanced
        self._tasks = list(tasks)
        self._multipliers = (
            hierarchical_sft_weights(self._source)
            if self.balanced
            else {task.sampler.opaque_id: 1.0 for task in self._source}
        )
        self.set_epoch(0)

    def __len__(self) -> int:
        return math.ceil(len(self._tasks) / self.batch_size)

    def set_epoch(self, seed: int = 0) -> None:
        if self.balanced:
            self._tasks = stratified_physical_pass(self._source, seed=seed)
        else:
            self._tasks = list(self._source)
            random.Random(seed).shuffle(self._tasks)

    def _datum(self, task: TaskRecord):
        assistant = Message(
            role="assistant",
            content=[TextPart(type="text", text=task.label)],
        )
        datum = conversation_to_datum(
            [_message(task, max_image=self.max_image), assistant],
            self.renderer,
            max_length=self.max_length,
            train_on_what=TrainOnWhat.LAST_ASSISTANT_MESSAGE,
            reduction="mean",
        )
        multiplier = self._multipliers[task.sampler.opaque_id]
        weights = datum.loss_fn_inputs["weights"]
        values = [float(value) * multiplier for value in weights.data]
        datum.loss_fn_inputs["weights"] = tinker.TensorData(
            data=values,
            dtype="float32",
            shape=list(weights.shape or [len(values)]),
        )
        return datum

    def get_batch(self, index: int):
        start = index * self.batch_size
        return [
            self._datum(task)
            for task in self._tasks[start : start + self.batch_size]
        ]


@chz.chz
class TrackASupervisedDatasetBuilder(SupervisedDatasetBuilder):
    dataset_root: str
    model_name: str = DEFAULT_MODEL
    renderer_name: str = DEFAULT_RENDERER
    batch_size: int = 64
    max_length: int = 6144
    max_image: int = DEFAULT_MAX_IMAGE

    def __call__(self):
        renderer = _renderer(self.model_name, self.renderer_name)
        root = Path(self.dataset_root)
        train = load_tasks(
            root,
            configuration="depth",
            split="train",
        )
        validation = load_tasks(
            root,
            configuration="depth",
            split="validation",
        )
        return (
            TrackASupervisedDataset(
                train,
                renderer,
                batch_size=self.batch_size,
                max_length=self.max_length,
                max_image=self.max_image,
                balanced=True,
            ),
            TrackASupervisedDataset(
                validation,
                renderer,
                batch_size=self.batch_size,
                max_length=self.max_length,
                max_image=self.max_image,
                balanced=False,
            ),
        )


class TrackAEnv(Env):
    """Single-turn image-to-code bandit with private deterministic grading."""

    def __init__(self, task: TaskRecord, renderer, max_image: int) -> None:
        self.task = task
        self.renderer = renderer
        self.max_image = max_image

    async def initial_observation(self):
        model_input = self.renderer.build_generation_prompt(
            [_message(self.task, max_image=self.max_image)]
        )
        return model_input, self.renderer.get_stop_sequences()

    async def step(self, action, *, extra=None):
        del extra
        decode = getattr(self.renderer, "decode_action_text", None)
        completion = (
            decode(action)
            if decode is not None
            else self.renderer.tokenizer.decode(action)
        )
        result = await _batcher().submit(self.task.reference, completion)
        reward = reward_for(result)
        if reward is None:
            if result.attribution is Attribution.REFERENCE:
                raise BrokenReferenceError(result.error or result.status.value)
            raise EvaluationInfrastructureError(result.error or result.status.value)
        return StepResult(
            reward=reward,
            episode_done=True,
            next_observation=tinker.ModelInput.from_ints([]),
            next_stop_condition=[],
            metrics={
                "iou": float(result.iou or 0.0),
                "dice": float(result.dice or 0.0),
                "program_valid": float(result.status is EvaluationStatus.OK),
                "source_rejected": float(
                    result.status is EvaluationStatus.SOURCE_REJECTED
                ),
                "latency_seconds": float(result.latency_seconds),
            },
        )


class TrackARLDataset(RLDataset):
    def __init__(
        self,
        current_tasks: list[TaskRecord],
        replay_tasks: list[TaskRecord],
        renderer,
        *,
        groups_per_batch: int,
        group_size: int,
        max_image: int,
        n_batches: int,
        shuffle: bool,
    ) -> None:
        self.current_tasks = list(current_tasks)
        self.replay_tasks = list(replay_tasks)
        self.renderer = renderer
        self.groups_per_batch = groups_per_batch
        self.group_size = group_size
        self.max_image = max_image
        self.n_batches = n_batches
        self.shuffle = shuffle

    def __len__(self) -> int:
        return self.n_batches

    def get_batch(self, index: int) -> Sequence[EnvGroupBuilder]:
        count = min(self.groups_per_batch, len(self.current_tasks))
        if self.shuffle and self.replay_tasks:
            if self.groups_per_batch == 8:
                replay_count = (2, 2, 2, 1, 1)[index % 5]
            else:
                replay_count = max(1, round(0.2 * self.groups_per_batch))
            replay_count = min(replay_count, count, len(self.replay_tasks))
            current_count = count - replay_count
            current_order = stratified_physical_pass(
                self.current_tasks,
                seed=10_000 + index // max(1, len(self.current_tasks)),
            )
            replay_order = stratified_physical_pass(
                self.replay_tasks,
                seed=20_000 + index // max(1, len(self.replay_tasks)),
            )
            current_start = (index * max(1, current_count)) % len(current_order)
            replay_start = (index * max(1, replay_count)) % len(replay_order)
            selected = [
                current_order[(current_start + offset) % len(current_order)]
                for offset in range(current_count)
            ]
            selected.extend(
                replay_order[(replay_start + offset) % len(replay_order)]
                for offset in range(replay_count)
            )
            random.Random(30_000 + index).shuffle(selected)
        elif self.shuffle:
            order = stratified_physical_pass(
                self.current_tasks,
                seed=10_000 + index // max(1, len(self.current_tasks)),
            )
            start = (index * count) % len(order)
            selected = [
                order[(start + offset) % len(order)] for offset in range(count)
            ]
        else:
            selected = self.current_tasks[:count]
        return [
            ProblemGroupBuilder(
                env_thunk=partial(TrackAEnv, task, self.renderer, self.max_image),
                num_envs=self.group_size,
                dataset_name=task.sampler.level,
            )
            for task in selected
        ]


def _level_filter(tasks: list[TaskRecord], levels: str) -> list[TaskRecord]:
    allowed = {item.strip().upper() for item in levels.split(",") if item.strip()}
    if not allowed:
        return tasks
    selected = [task for task in tasks if task.sampler.level.upper() in allowed]
    if not selected:
        raise ValueError(f"no rows match levels={levels!r}")
    return selected


@chz.chz
class TrackARLDatasetBuilder(RLDatasetBuilder):
    dataset_root: str
    batch_size: int = 8
    group_size: int = 4
    model_name: str = DEFAULT_MODEL
    renderer_name: str = DEFAULT_RENDERER
    max_image: int = DEFAULT_MAX_IMAGE
    current_level: str = ""
    replay_levels: str = ""
    validation_canaries: int = 40

    async def __call__(self):
        renderer = _renderer(self.model_name, self.renderer_name)
        root = Path(self.dataset_root)
        if not self.current_level.strip():
            raise ValueError("current_level must be selected by the pre-RL executable gate")
        all_train = load_tasks(root, configuration="depth", split="train")
        all_validation = load_tasks(
            root,
            configuration="depth",
            split="validation",
        )
        train = _level_filter(all_train, self.current_level)
        replay = (
            _level_filter(all_train, self.replay_levels)
            if self.replay_levels.strip()
            else []
        )
        validation_levels = ",".join(
            item
            for item in (self.current_level, self.replay_levels)
            if item.strip()
        )
        validation = _level_filter(all_validation, validation_levels)
        validation = balanced_effective_pass(
            validation,
            seed=7,
            draws=min(self.validation_canaries, len(validation)),
        )
        return (
            TrackARLDataset(
                train,
                replay,
                renderer,
                groups_per_batch=self.batch_size,
                group_size=self.group_size,
                max_image=self.max_image,
                n_batches=100_000,
                shuffle=True,
            ),
            TrackARLDataset(
                validation,
                [],
                renderer,
                groups_per_batch=len(validation),
                group_size=1,
                max_image=self.max_image,
                n_batches=1,
                shuffle=False,
            ),
        )
