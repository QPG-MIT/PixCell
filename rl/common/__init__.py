"""Shared PixCell task boundaries and deterministic measurement."""

from .contracts import (
    ModelObservation,
    SamplerMetadata,
    SupervisedExample,
    TaskRecord,
    VerifierReference,
)
from .evaluator import EvaluationResult, EvaluationStatus, PixCellEvaluator

__all__ = [
    "EvaluationResult",
    "EvaluationStatus",
    "ModelObservation",
    "PixCellEvaluator",
    "SamplerMetadata",
    "SupervisedExample",
    "TaskRecord",
    "VerifierReference",
]
