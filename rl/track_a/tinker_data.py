"""Tinker Cookbook adapters over the dataset-native Track A contract.

Importing this module is free. A Tinker client is created only by the guarded
training entrypoints.
"""

from __future__ import annotations

import hashlib
import math
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import chz
import tinker
from tinker_cookbook.image_processing_utils import get_image_processor
from tinker_cookbook.renderers import (
    ImagePart,
    Message,
    TextPart,
    TrainOnWhat,
    get_text_content,
    get_renderer,
)
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

from rl.common.baselines import cached_rect_baseline
from rl.common.batcher import AsyncEvaluationBatcher
from rl.common.contracts import TaskRecord
from rl.common.dataset_io import load_tasks
from rl.common.evaluator import Attribution, EvaluationStatus, PixCellEvaluator
from rl.common.output import extract_code
from rl.track_a.curriculum import (
    balanced_effective_pass,
    deterministic_rl_batch,
    expected_replay_levels,
    hierarchical_sft_weights,
    normalize_level,
    normalize_replay_levels,
    stratified_physical_pass,
)
from rl.common.preprocess import model_image
from rl.common.prompt import build_prompt_text
from rl.track_a.reward import (
    REWARD_POLICIES,
    reward_for_policy,
    shaped_components,
)


DEFAULT_MODEL = "Qwen/Qwen3.6-35B-A3B"
DEFAULT_RENDERER = "qwen3_5_disable_thinking"
DEFAULT_MAX_IMAGE = 1440
_EVALUATION_BATCHER: AsyncEvaluationBatcher | None = None


class BrokenReferenceError(RuntimeError):
    """Fatal dataset/reference failure; the paid run should stop."""


class EvaluationInfrastructureError(RuntimeError):
    """Retry-exhausted evaluator fault; the paid stage must abort."""


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


def _renderer(
    model_name: str,
    renderer_name: str,
    *,
    effort: float | None = None,
):
    if model_name == "thinkingmachines/Inkling":
        # Re-scoped in for the bounded L4 RL-only arm (user direction,
        # 2026-07-29): RL under the shaped reward was designed but never
        # actually run on Inkling in either prior campaign.
        if renderer_name != "tml_v0" or effort is None:
            raise ValueError(
                "Inkling requires renderer_name='tml_v0' and explicit effort"
            )
        from rl.track_b.tml_shim import install_inkling_runtime

        install_inkling_runtime(effort=effort)
        tokenizer = get_tokenizer(model_name)
        return get_renderer(
            renderer_name,
            tokenizer,
            None,
            model_name=model_name,
        )
    if effort is not None:
        raise ValueError("effort is not a Qwen sampling knob")
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
        import os

        evaluator = PixCellEvaluator(
            # Several campaigns share one Docker daemon; transient container
            # faults under contention must be retried, not abort a paid
            # stage, and the wall timeout must leave headroom so contention
            # slows a measurement instead of falsifying it as a model
            # failure. Persistent evaluator faults still abort after the
            # retries are exhausted — no biased zeros either way.
            max_workers=int(os.environ.get("PIXCELL_EVAL_WORKERS", "8")),
            evaluator_retries=3,
            execution_timeout_seconds=float(
                os.environ.get("PIXCELL_EVAL_TIMEOUT", "20")
            ),
            # The load-bearing safety layer is the pre-execution AST source
            # gate plus subprocess rlimits — the tier the private library's
            # entire recorded campaign ran on. The Docker tier remains
            # available (PIXCELL_REQUIRE_ISOLATION=1) for record evals.
            require_isolation=(
                os.environ.get("PIXCELL_REQUIRE_ISOLATION", "0") == "1"
            ),
        )
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
        schedule_seed: int = 0,
    ) -> None:
        self._source = list(tasks)
        self.renderer = renderer
        self.batch_size = batch_size
        self.max_length = max_length
        self.max_image = max_image
        self.balanced = balanced
        self.schedule_seed = schedule_seed
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
            self._tasks = stratified_physical_pass(
                self._source,
                seed=self.schedule_seed + seed,
            )
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
    levels: str = ""
    include_validation: bool = True
    schedule_seed: int = 0
    winner_labels_path: str = ""

    def __call__(self):
        renderer = _renderer(self.model_name, self.renderer_name)
        root = Path(self.dataset_root)
        train = load_tasks(
            root,
            configuration="depth",
            split="train",
        )
        validation = (
            load_tasks(
                root,
                configuration="depth",
                split="validation",
            )
            if self.include_validation
            else []
        )
        train = _level_filter(train, self.levels)
        validation = (
            _level_filter(validation, self.levels)
            if self.include_validation
            else []
        )
        if self.winner_labels_path:
            from rl.track_a.harvest import apply_winner_labels

            train = apply_winner_labels(train, self.winner_labels_path)
        return (
            TrackASupervisedDataset(
                train,
                renderer,
                batch_size=self.batch_size,
                max_length=self.max_length,
                max_image=self.max_image,
                balanced=True,
                schedule_seed=self.schedule_seed,
            ),
            (
                TrackASupervisedDataset(
                    validation,
                    renderer,
                    batch_size=self.batch_size,
                    max_length=self.max_length,
                    max_image=self.max_image,
                    balanced=False,
                )
                if self.include_validation
                else None
            ),
        )


class TrackAEnv(Env):
    """Single-turn image-to-code bandit with private deterministic grading."""

    def __init__(
        self,
        task: TaskRecord,
        renderer,
        max_image: int,
        *,
        attempt_context: Mapping[str, object] | None = None,
        attempt_recorder: Callable[[Mapping[str, object]], None] | None = None,
        sample_recorder: Callable[[Mapping[str, object]], None] | None = None,
        reward_policy: str = "validity_floor",
    ) -> None:
        self.task = task
        self.renderer = renderer
        self.max_image = max_image
        self.attempt_context = dict(attempt_context or {})
        self.attempt_recorder = attempt_recorder
        self.sample_recorder = sample_recorder
        if reward_policy not in REWARD_POLICIES:
            raise ValueError(f"unknown reward policy: {reward_policy!r}")
        self.reward_policy = reward_policy
        self.prompt_tokens: int | None = None

    async def initial_observation(self):
        model_input = self.renderer.build_generation_prompt(
            [_message(self.task, max_image=self.max_image)]
        )
        self.prompt_tokens = int(model_input.length)
        return model_input, self.renderer.get_stop_sequences()

    async def step(self, action, *, extra=None):
        message, termination = self.renderer.parse_response(list(action))
        completion = get_text_content(message)
        raw_text = str(self.renderer.tokenizer.decode(list(action)))
        reasoning = ""
        content = message.get("content")
        if isinstance(content, list):
            reasoning = "\n".join(
                str(part.get("thinking", ""))
                for part in content
                if isinstance(part, Mapping) and part.get("type") == "thinking"
            )
        program = extract_code(completion)
        sample_record = {
            **self.attempt_context,
            "task": {
                "opaque_id": self.task.sampler.opaque_id,
                "level": self.task.sampler.level,
                "representation_id": self.task.sampler.representation_id,
                "realization_slot": self.task.sampler.realization_slot,
                "image_sha256": self.task.observation.image_sha256,
                "target_image_sha256": self.task.reference.target_image_sha256,
            },
            "sampling": {
                "prompt_tokens": self.prompt_tokens,
                "sampled_tokens": len(action),
                "raw_token_ids": [int(token) for token in action],
                "stop_reason": getattr(extra, "stop_reason", None),
                "channel_parse_complete": bool(termination.is_clean),
                "raw_text": raw_text,
                "raw_text_sha256": hashlib.sha256(
                    raw_text.encode("utf-8")
                ).hexdigest(),
                "reasoning_text": reasoning,
                "reasoning_characters": len(reasoning),
                "reasoning_sha256": hashlib.sha256(
                    reasoning.encode("utf-8")
                ).hexdigest(),
            },
            "answer_text": completion,
            "program": program,
            "program_sha256": hashlib.sha256(
                program.encode("utf-8")
            ).hexdigest(),
        }
        if self.sample_recorder is not None:
            self.sample_recorder(sample_record)
        baseline = (
            cached_rect_baseline(self.task.reference)
            if self.reward_policy == "shaped_v3b"
            else None
        )
        result = await _batcher().submit(self.task.reference, completion)
        reward = reward_for_policy(
            result,
            policy=self.reward_policy,
            baseline=baseline,
        )
        if reward is None:
            if result.attribution is Attribution.REFERENCE:
                raise BrokenReferenceError(result.error or result.status.value)
            raise EvaluationInfrastructureError(result.error or result.status.value)
        if self.attempt_recorder is not None:
            self.attempt_recorder(
                {
                    **sample_record,
                    "evaluation": {
                        "status": result.status.value,
                        "attribution": result.attribution.value,
                        "iou": result.iou,
                        "dice": result.dice,
                        "reward": reward,
                        "violations": list(result.violations),
                        "error": result.error,
                        "latency_seconds": result.latency_seconds,
                        "metrics": result.metrics,
                    },
                }
            )
        step_metrics = {
            "iou": float(result.iou or 0.0),
            "dice": float(result.dice or 0.0),
            "program_valid": float(result.status is EvaluationStatus.OK),
            "source_rejected": float(
                result.status is EvaluationStatus.SOURCE_REJECTED
            ),
            "latency_seconds": float(result.latency_seconds),
            "channel_parse_complete": float(termination.is_clean),
            "length_capped": float(
                getattr(extra, "stop_reason", None) == "length"
            ),
        }
        if baseline is not None:
            parts = shaped_components(result, baseline)
            step_metrics.update(
                iou_n=parts["iou_n"],
                teacher_nb=parts["teacher_nb"],
                degenerate=parts["degenerate"],
            )
        return StepResult(
            reward=reward,
            episode_done=True,
            next_observation=tinker.ModelInput.from_ints([]),
            next_stop_condition=[],
            metrics=step_metrics,
        )


@dataclass(frozen=True)
class PixCellGroupBuilder(EnvGroupBuilder):
    """Group builder that gives every rollout an immutable candidate key."""

    task: TaskRecord
    renderer: object
    max_image: int
    num_envs: int
    dataset_name: str
    step_index: int
    group_index: int
    attempt_recorder: Callable[[Mapping[str, object]], None] | None = None
    sample_recorder: Callable[[Mapping[str, object]], None] | None = None
    reward_policy: str = "validity_floor"
    attempt_metadata: Mapping[str, object] | None = None

    async def make_envs(self) -> Sequence[Env]:
        return [
            TrackAEnv(
                self.task,
                self.renderer,
                self.max_image,
                attempt_context={
                    **dict(self.attempt_metadata or {}),
                    "step": self.step_index,
                    "group": self.group_index,
                    "attempt": attempt_index,
                },
                attempt_recorder=self.attempt_recorder,
                sample_recorder=self.sample_recorder,
                reward_policy=self.reward_policy,
            )
            for attempt_index in range(1, self.num_envs + 1)
        ]

    async def compute_group_rewards(self, trajectory_group, env_group):
        del env_group
        return [(0.0, {}) for _ in trajectory_group]

    def logging_tags(self) -> list[str]:
        return [
            self.dataset_name,
            self.task.sampler.opaque_id,
            self.task.sampler.representation_id,
        ]


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
        attempt_recorder: Callable[[Mapping[str, object]], None] | None = None,
        sample_recorder: Callable[[Mapping[str, object]], None] | None = None,
        reward_policy: str = "validity_floor",
        schedule_seed: int = 10_000,
        attempt_metadata: Mapping[str, object] | None = None,
        replay_groups_per_step: int = 0,
    ) -> None:
        self.replay_groups_per_step = replay_groups_per_step
        self.current_tasks = list(current_tasks)
        self.replay_tasks = list(replay_tasks)
        self.renderer = renderer
        self.groups_per_batch = groups_per_batch
        self.group_size = group_size
        self.max_image = max_image
        self.n_batches = n_batches
        self.shuffle = shuffle
        self.attempt_recorder = attempt_recorder
        self.sample_recorder = sample_recorder
        if reward_policy not in REWARD_POLICIES:
            raise ValueError(f"unknown reward policy: {reward_policy!r}")
        self.reward_policy = reward_policy
        self.schedule_seed = schedule_seed
        self.attempt_metadata = dict(attempt_metadata or {})

    def __len__(self) -> int:
        return self.n_batches

    def get_batch(self, index: int) -> Sequence[EnvGroupBuilder]:
        selected = deterministic_rl_batch(
            self.current_tasks,
            self.replay_tasks,
            step=index,
            groups_per_batch=self.groups_per_batch,
            schedule_seed=self.schedule_seed,
            shuffle=self.shuffle,
            replay_groups_per_step=self.replay_groups_per_step,
        )
        return [
            PixCellGroupBuilder(
                task=task,
                renderer=self.renderer,
                max_image=self.max_image,
                num_envs=self.group_size,
                dataset_name=task.sampler.level,
                step_index=index,
                group_index=group_index,
                attempt_recorder=self.attempt_recorder,
                sample_recorder=self.sample_recorder,
                reward_policy=self.reward_policy,
                attempt_metadata=self.attempt_metadata,
            )
            for group_index, (_role, task) in enumerate(selected)
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
    group_size: int = 8
    model_name: str = DEFAULT_MODEL
    renderer_name: str = DEFAULT_RENDERER
    model_effort: float | None = None
    max_image: int = DEFAULT_MAX_IMAGE
    current_level: str = ""
    replay_levels: str = ""
    validation_canaries: int = 40
    attempt_recorder: Callable[[Mapping[str, object]], None] | None = None
    sample_recorder: Callable[[Mapping[str, object]], None] | None = None
    reward_policy: str = "shaped_v3b"
    require_prefix_replay: bool = True
    schedule_seed: int = 10_000
    attempt_metadata: Mapping[str, object] | None = None
    replay_groups_per_step: int = 0

    async def __call__(self):
        renderer = _renderer(
            self.model_name,
            self.renderer_name,
            effort=self.model_effort,
        )
        root = Path(self.dataset_root)
        if not self.current_level.strip():
            raise ValueError("current_level must be selected by the pre-RL executable gate")
        current = normalize_level(self.current_level)
        replay_levels = normalize_replay_levels(self.replay_levels)
        expected_replay = expected_replay_levels(current)
        if self.require_prefix_replay and replay_levels != expected_replay:
            raise ValueError(
                "replay_levels must be the complete ordered prefix before "
                f"{current}: {','.join(expected_replay)}"
            )
        all_train = load_tasks(root, configuration="depth", split="train")
        all_validation = (
            load_tasks(
                root,
                configuration="depth",
                split="validation",
            )
            if self.validation_canaries > 0
            else []
        )
        train = _level_filter(all_train, current)
        replay = (
            _level_filter(all_train, ",".join(replay_levels))
            if replay_levels
            else []
        )
        validation_levels = ",".join((*replay_levels, current))
        validation = (
            _level_filter(all_validation, validation_levels)
            if all_validation
            else []
        )
        validation = (
            balanced_effective_pass(
                validation,
                seed=7,
                draws=min(self.validation_canaries, len(validation)),
            )
            if self.validation_canaries > 0
            else []
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
                attempt_recorder=self.attempt_recorder,
                sample_recorder=self.sample_recorder,
                reward_policy=self.reward_policy,
                schedule_seed=self.schedule_seed,
                attempt_metadata=self.attempt_metadata,
                replay_groups_per_step=self.replay_groups_per_step,
            ),
            (
                TrackARLDataset(
                    validation,
                    [],
                    renderer,
                    groups_per_batch=len(validation),
                    group_size=1,
                    max_image=self.max_image,
                    n_batches=1,
                    shuffle=False,
                    reward_policy=self.reward_policy,
                    schedule_seed=self.schedule_seed,
                )
                if validation
                else None
            ),
        )
