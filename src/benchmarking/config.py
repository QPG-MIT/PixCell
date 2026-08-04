"""
Benchmark configuration: models, phases, and settings.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from homi.paths import michaelangelo_dir, workspace_root


@dataclass
class ProviderLimits:
    """Per-provider parallelism limits based on API rate limits."""
    # How many (paper × model) combinations to run in parallel per provider
    parallel_runs: int = 4
    # How many seeds to run in parallel within each run
    parallel_seeds_phase1: int = 8
    parallel_seeds_phase2: int = 4


# Provider-specific limits (adjust based on your API tier)
DEFAULT_PROVIDER_LIMITS: Dict[str, ProviderLimits] = {
    # Gemini: You have 1B+ token limits - essentially unlimited
    "gemini": ProviderLimits(
        parallel_runs=50,        # Run all paper×model combos
        parallel_seeds_phase1=15,  # All seeds in parallel
        parallel_seeds_phase2=5,   # All top-k seeds in parallel
    ),
    # Claude: Tier-dependent, conservative default
    "claude": ProviderLimits(
        parallel_runs=2,
        parallel_seeds_phase1=4,
        parallel_seeds_phase2=2,
    ),
    # OpenAI: Tier-dependent, conservative default
    "openai": ProviderLimits(
        parallel_runs=2,
        parallel_seeds_phase1=4,
        parallel_seeds_phase2=2,
    ),
    # OpenRouter (Kimi, Qwen, Grok, Llama): Shared limits
    "openrouter": ProviderLimits(
        parallel_runs=4,
        parallel_seeds_phase1=6,
        parallel_seeds_phase2=3,
    ),
}


def get_provider_for_family(family: str) -> str:
    """Map model family to provider for rate limiting."""
    if family == "gemini":
        return "gemini"
    elif family == "claude":
        return "claude"
    elif family == "openai":
        return "openai"
    else:
        # kimi, qwen, grok, llama all go through OpenRouter
        return "openrouter"


@dataclass
class BenchmarkModel:
    """Definition of a model to benchmark."""
    name: str                 # Display name
    model_key: str            # Registry key (e.g., "gemini/gemini-3-pro-preview")
    family: str               # Model family for grouping
    supports_seed: bool       # Whether model supports deterministic seeds
    supports_thinking: bool   # Whether model supports extended thinking


# Latest model from each of the 7 families
BENCHMARK_MODELS: List[BenchmarkModel] = [
    BenchmarkModel(
        name="Gemini 3 Pro",
        model_key="gemini/gemini-3-pro-preview",
        family="gemini",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Claude Opus 4.5",
        model_key="anthropic/claude-opus-4.5",
        family="claude",
        supports_seed=False,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="GPT-5.2",
        model_key="openai/gpt-5.2",
        family="openai",
        supports_seed=False,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Kimi-K1.5",
        model_key="moonshotai/kimi-k1.5",
        family="kimi",
        supports_seed=True,
        supports_thinking=False,  # K1.5 doesn't have thinking mode
    ),
    BenchmarkModel(
        name="Qwen3-VL-235B-Thinking",
        model_key="qwen/qwen3-vl-235b-a22b-thinking",
        family="qwen",
        supports_seed=True,
        supports_thinking=True,
    ),
    BenchmarkModel(
        name="Grok-4",
        model_key="x-ai/grok-4",
        family="grok",
        supports_seed=True,
        supports_thinking=True,
    ),
]


@dataclass
class Phase1Config:
    """Phase 1 (multi-seed exploration) configuration."""
    num_seeds: int = 15           # Total seeds/runs to test
    base_seed: int = 1333         # Base seed for seed-supporting models
    num_parallel: int = 8         # Parallel workers
    max_attempts: int = 3         # Max attempts per turn on failure
    reasoning_effort: str = "high"  # Reasoning effort: high, medium, low


@dataclass
class Phase2Config:
    """Phase 2 (extended iteration) configuration."""
    top_k: int = 5                # Number of top seeds by SSE to continue
    num_parallel: int = 4         # Parallel workers
    additional_turns: int = 2     # Additional turns beyond Phase 1
    max_attempts: int = 3         # Max attempts per turn on failure


@dataclass
class BenchmarkConfig:
    """Complete benchmark configuration."""
    papers: List[str] = field(default_factory=list)
    models: List[BenchmarkModel] = field(default_factory=lambda: BENCHMARK_MODELS.copy())
    phase1: Phase1Config = field(default_factory=Phase1Config)
    phase2: Phase2Config = field(default_factory=Phase2Config)
    num_parallel_models: int = 6          # Legacy: max parallel models (fallback)
    provider_limits: Dict[str, ProviderLimits] = field(
        default_factory=lambda: DEFAULT_PROVIDER_LIMITS.copy()
    )
    output_dir: Path = field(default_factory=lambda: Path("benchmark_results"))
    # The eight shipped input fixtures (silhouette + footprint + calibration)
    projects_dir: Path = field(default_factory=lambda: workspace_root() / "data" / "benchmark")
    michaelangelo_dir: Path = field(default_factory=michaelangelo_dir)

    def get_limits_for_model(self, model: "BenchmarkModel") -> ProviderLimits:
        """Get parallelism limits for a specific model based on its provider."""
        provider = get_provider_for_family(model.family)
        return self.provider_limits.get(provider, ProviderLimits())

    @classmethod
    def default(cls) -> "BenchmarkConfig":
        """Create default benchmark configuration over the shipped fixtures."""
        return cls(
            papers=[f"final_{i}" for i in range(1, 9)],
            models=BENCHMARK_MODELS.copy(),
            phase1=Phase1Config(),
            phase2=Phase2Config(),
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "papers": self.papers,
            "models": [
                {
                    "name": m.name,
                    "model_key": m.model_key,
                    "family": m.family,
                    "supports_seed": m.supports_seed,
                    "supports_thinking": m.supports_thinking,
                }
                for m in self.models
            ],
            "phase1": {
                "num_seeds": self.phase1.num_seeds,
                "base_seed": self.phase1.base_seed,
                "num_parallel": self.phase1.num_parallel,
                "max_attempts": self.phase1.max_attempts,
                "reasoning_effort": self.phase1.reasoning_effort,
            },
            "phase2": {
                "top_k": self.phase2.top_k,
                "num_parallel": self.phase2.num_parallel,
                "additional_turns": self.phase2.additional_turns,
                "max_attempts": self.phase2.max_attempts,
            },
            "num_parallel_models": self.num_parallel_models,
            "provider_limits": {
                provider: {
                    "parallel_runs": limits.parallel_runs,
                    "parallel_seeds_phase1": limits.parallel_seeds_phase1,
                    "parallel_seeds_phase2": limits.parallel_seeds_phase2,
                }
                for provider, limits in self.provider_limits.items()
            },
            "output_dir": str(self.output_dir),
            "projects_dir": str(self.projects_dir),
            "michaelangelo_dir": str(self.michaelangelo_dir),
        }
