#!/usr/bin/env python3
"""The Track A campaign runner: one recipe, no ceremony.

    A  runA-l0sft-rl        no-think @ 4096   L0-SFT -> RL L0..L4
    B  runB-base-rl         no-think @ 4096   base   -> RL L0..L4
    C  runC-think-base-rl   think    @ 60000  base   -> RL L0..L4
    D  runD-think-l0sft-rl  think    @ 60000  L0-SFT -> RL L0..L4 (gated)
    E  runE-a-l1sft         no-think @ 4096   fork of A after rl-l0 -> L1-SFT (gated) -> RL L1..L4
    F  runF-a-mixed         no-think @ 4096   fork of A after rl-l0 -> RL L1..L4 at a 50% backward mix
    G  runG-a-ladder        no-think @ 4096   fork of A after rl-l0 -> SFT+RL ladder at every level (held until E reports)

Each stage is one subprocess over the lean entry points (crash isolation,
one W&B run per stage, per-stage console logs); stages chain on the previous
stage's final training weights with a fresh optimizer, exactly as the old
lineage chained its runs. A stage that already finished is skipped, so
re-running the same command resumes the campaign. Forked campaigns seed a
prefix of completed stages (checkpoint ledgers + DONE) from a source run and
continue from its weights with zero recompute.

The fixed probe (probe_eval) runs at campaign start and after every stage.
Every SFT insertion is gated by probes on the SFT'd level: fresh runs must
beat the base model (absolute rule); forked mid-lineage SFTs must not lose
executable rate and must gain IoU against the fork-origin probe (relative
rule). A failed mid-lineage gate skips the SFT and continues RL from the
pre-SFT weights — the negative result is recorded, the budget is not spent.

Smoke mode prices an operating point before the full campaign:
``--smoke nothink`` / ``--smoke think`` runs 2 GRPO steps at 2 groups.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from tinker_cookbook.checkpoint_utils import get_last_checkpoint

from rl.common.baselines import cached_rect_baseline
from rl.track_a.curriculum import LEVELS
from rl.track_a.launch import run_launch_preflight
from rl.track_a.probe_eval import run_probe, select_probe_tasks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATASET_ROOT = _REPO_ROOT / "dataset"

CONFIRM_SPEND = "PIXCELL_RUNS_V2"
DEFAULT_RUNS_ROOT = "~/pixcell-training/runs-v2"
FALLBACK_RUNS_ROOT = "~/pixcell-training/runs-v2"

SFT_GATE_MIN_EXECUTABLE = 0.75
SFT_GATE_RELATIVE_EXEC_SLACK = 0.10


@dataclass(frozen=True)
class RunPlan:
    key: str
    name: str
    renderer_name: str
    max_tokens: int
    sft_levels: tuple[str, ...] = ()
    sft_epochs: int = 2
    steps_per_level: int = 30
    replay_groups_per_step: int = 0
    fork_from: str = ""       # source run name under the same runs root
    fork_through: str = ""    # last stage seeded from the source, e.g. "rl-l0"

    @property
    def sft(self) -> bool:
        return bool(self.sft_levels)


RUN_PLANS = {
    "A": RunPlan("A", "runA-l0sft-rl", "qwen3_5_disable_thinking", 4096, ("L0",)),
    "B": RunPlan("B", "runB-base-rl", "qwen3_5_disable_thinking", 4096),
    "C": RunPlan("C", "runC-think-base-rl", "qwen3_5", 60000),
    "D": RunPlan("D", "runD-think-l0sft-rl", "qwen3_5", 60000, ("L0",)),
    "E": RunPlan(
        "E",
        "runE-a-l1sft",
        "qwen3_5_disable_thinking",
        4096,
        ("L0", "L1"),
        sft_epochs=1,
        fork_from="runA-l0sft-rl",
        fork_through="rl-l0",
    ),
    "F": RunPlan(
        "F",
        "runF-a-mixed",
        "qwen3_5_disable_thinking",
        4096,
        ("L0",),
        replay_groups_per_step=4,
        fork_from="runA-l0sft-rl",
        fork_through="rl-l0",
    ),
    "G": RunPlan(
        "G",
        "runG-a-ladder",
        "qwen3_5_disable_thinking",
        4096,
        ("L0", "L1", "L2", "L3", "L4"),
        sft_epochs=1,
        fork_from="runA-l0sft-rl",
        fork_through="rl-l0",
    ),
}
MODEL_NAME = "Qwen/Qwen3.6-35B-A3B"

_STAGE_ORDER = [
    name
    for level in LEVELS
    for name in (f"sft-{level.lower()}", f"rl-{level.lower()}")
]


@dataclass(frozen=True)
class Stage:
    name: str
    module: str
    args: dict[str, str] = field(default_factory=dict)

    @property
    def sft_level(self) -> str | None:
        if self.name.startswith("sft-"):
            return self.name.split("-", 1)[1].upper()
        return None


def build_stages(
    plan: RunPlan,
    *,
    run_root: Path,
    wandb_project: str,
    smoke: bool = False,
) -> list[Stage]:
    """The full ordered stage list for one run. Checkpoint chaining is
    resolved at execution time, not here. Forked prefixes appear here too —
    the DONE markers seeded by the fork make the runner skip them."""

    steps = 2 if smoke else plan.steps_per_level
    groups = "2" if smoke else "8"
    canaries = "8" if smoke else "40"
    stages: list[Stage] = []
    levels = ["L0"] if smoke else list(LEVELS)
    for level in levels:
        if not smoke and level in plan.sft_levels:
            stage_name = f"sft-{level.lower()}"
            stages.append(
                Stage(
                    name=stage_name,
                    module="rl.track_a.train_sft",
                    args={
                        "confirm_spend": CONFIRM_SPEND,
                        "model_name": MODEL_NAME,
                        "renderer_name": plan.renderer_name,
                        "levels": level,
                        "num_epochs": str(plan.sft_epochs),
                        "learning_rate": "1e-4",
                        "log_path": str(run_root / "stages" / stage_name),
                        "wandb_project": wandb_project,
                        "wandb_name": f"{plan.name}-{stage_name}",
                        "skip_preflight": "True",
                    },
                )
            )
        stage_name = f"rl-{level.lower()}"
        rl_args = {
            "confirm_spend": CONFIRM_SPEND,
            "model_name": MODEL_NAME,
            "renderer_name": plan.renderer_name,
            "current_level": level,
            "max_tokens": str(plan.max_tokens),
            "max_steps": str(steps),
            "groups_per_batch": groups,
            "group_size": "8",
            "validation_canaries": canaries,
            "reward_policy": "shaped_v3b",
            "log_path": str(run_root / "stages" / stage_name),
            "wandb_project": wandb_project,
            "wandb_name": f"{plan.name}-{stage_name}",
            "skip_preflight": "True",
        }
        if plan.replay_groups_per_step:
            rl_args["replay_groups_per_step"] = str(plan.replay_groups_per_step)
        stages.append(
            Stage(name=stage_name, module="rl.track_a.train_rl", args=rl_args)
        )
    return stages


def _stage_done(stage: Stage) -> bool:
    return (Path(stage.args["log_path"]) / "DONE").exists()


def _mark_done(stage: Stage) -> None:
    (Path(stage.args["log_path"]) / "DONE").write_text("ok\n", encoding="utf-8")


def _last_sampler_path(log_path: str) -> str:
    """Sampling-only weights (``.../sampler_weights/…``) — for probes."""

    record = get_last_checkpoint(log_path, required_key="sampler_path")
    if record is None or not record.sampler_path:
        raise RuntimeError(f"no sampler checkpoint recorded under {log_path}")
    return record.sampler_path


def _last_weights_path(log_path: str) -> str:
    """Training weights (``.../weights/…``) — the only form Tinker's
    load_weights accepts, so the only form stages may chain on."""

    record = get_last_checkpoint(log_path, required_key="state_path")
    if record is None or not record.state_path:
        raise RuntimeError(
            f"no training-weights checkpoint recorded under {log_path}"
        )
    return record.state_path


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    roots = [str(_REPO_ROOT / "src"), str(_REPO_ROOT)]
    if environment.get("PYTHONPATH"):
        roots.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(roots)
    return environment


def _execute_stage(stage: Stage, *, extra: dict[str, str]) -> None:
    log_dir = Path(stage.args["log_path"])
    log_dir.mkdir(parents=True, exist_ok=True)
    arguments = {**stage.args, **extra}
    command = [
        sys.executable,
        "-m",
        stage.module,
        *[f"{key}={value}" for key, value in arguments.items()],
    ]
    console = log_dir / "console.log"
    started = time.monotonic()
    with console.open("a", encoding="utf-8") as sink:
        sink.write(f"# {' '.join(command)}\n")
        sink.flush()
        completed = subprocess.run(
            command,
            cwd=_REPO_ROOT,
            env=_environment(),
            stdout=sink,
            stderr=subprocess.STDOUT,
        )
    if completed.returncode != 0:
        raise RuntimeError(
            f"stage {stage.name} failed with exit {completed.returncode}; "
            f"see {console}"
        )
    print(
        f"[{stage.name}] completed in {time.monotonic() - started:.0f}s",
        flush=True,
    )


def _probe(
    plan: RunPlan,
    *,
    run_root: Path,
    tag: str,
    model_path: str | None,
) -> dict:
    return run_probe(
        dataset_root=_DATASET_ROOT,
        model_name=MODEL_NAME,
        renderer_name=plan.renderer_name,
        model_path=model_path,
        max_tokens=plan.max_tokens,
        out_path=run_root / "probes" / f"{tag}.json",
    )


def _sft_gate(
    reference_probe: dict,
    sft_probe: dict,
    level: str,
    *,
    relative: bool,
) -> tuple[bool, str]:
    """Should RL proceed from this SFT checkpoint?

    Fresh lineages (reference = raw base model) use the absolute rule: the
    SFT'd level must be reliably executable and beat the base on IoU.
    Forked mid-lineage insertions use the relative rule: the SFT must not
    lose executable rate (beyond slack) and must gain IoU on its level —
    the dose-response caution made concrete.
    """

    reference = reference_probe["per_level"][level]
    candidate = sft_probe["per_level"][level]
    if relative:
        floor = reference["executable_rate"] - SFT_GATE_RELATIVE_EXEC_SLACK
        if candidate["executable_rate"] < floor:
            return False, (
                f"SFT {level} executable rate {candidate['executable_rate']:.3f} "
                f"lost more than {SFT_GATE_RELATIVE_EXEC_SLACK} vs the fork origin "
                f"({reference['executable_rate']:.3f})"
            )
    elif candidate["executable_rate"] < SFT_GATE_MIN_EXECUTABLE:
        return False, (
            f"SFT {level} executable rate {candidate['executable_rate']:.3f} < "
            f"{SFT_GATE_MIN_EXECUTABLE}"
        )
    if candidate["mean_iou"] <= reference["mean_iou"]:
        return False, (
            f"SFT {level} mean IoU {candidate['mean_iou']:.3f} does not beat "
            f"the reference {reference['mean_iou']:.3f}"
        )
    return True, f"sft beats reference on {level}"


def _write_provenance(plan: RunPlan, *, run_root: Path, smoke: bool) -> None:
    provenance = run_root / "provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    (provenance / "plan.json").write_text(
        json.dumps(
            {
                "plan": asdict(plan),
                "model_name": MODEL_NAME,
                "git_head": head,
                "git_dirty": bool(dirty),
                "smoke": smoke,
                "confirm_spend": CONFIRM_SPEND,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    probe_tasks = select_probe_tasks(_DATASET_ROOT)
    baselines = {
        task.sampler.opaque_id: {
            "level": task.sampler.level,
            **cached_rect_baseline(task.reference).__dict__,
        }
        for task in probe_tasks
    }
    (provenance / "probe_baselines.json").write_text(
        json.dumps(baselines, indent=2),
        encoding="utf-8",
    )


def _fork_l0_stage(source_run_root: Path, run_root: Path) -> None:
    """Legacy depth-variant fork: seed rl-l0 WITHOUT its DONE marker so the
    stage resumes and extends (the -s60 runs). Zero recompute."""

    source = source_run_root / "stages" / "rl-l0"
    target = run_root / "stages" / "rl-l0"
    if (target / "checkpoints.jsonl").exists():
        return
    if not (source / "DONE").exists():
        raise SystemExit(f"fork source not complete: {source}")
    target.mkdir(parents=True, exist_ok=True)
    for name in ("checkpoints.jsonl", "metrics.jsonl"):
        payload = (source / name).read_text(encoding="utf-8")
        (target / name).write_text(payload, encoding="utf-8")
    (run_root / "provenance").mkdir(parents=True, exist_ok=True)
    (run_root / "provenance" / "fork.json").write_text(
        json.dumps({"rl_l0_forked_from": str(source)}, indent=2),
        encoding="utf-8",
    )
    print(f"[fork] rl-l0 seeded from {source}", flush=True)


def _fork_stages_through(
    source_run_root: Path,
    run_root: Path,
    through: str,
) -> None:
    """Seed a completed prefix of stages from a source campaign: checkpoint
    ledgers, metrics, and DONE markers up to and including ``through``, plus
    the source's probe at the fork point as this run's gate reference. The
    runner then skips the prefix and chains from its final weights."""

    if through not in _STAGE_ORDER:
        raise SystemExit(f"unknown fork stage: {through}")
    if (run_root / "provenance" / "fork.json").exists():
        return
    seeded = []
    for name in _STAGE_ORDER:
        source = source_run_root / "stages" / name
        if source.is_dir():
            if not (source / "DONE").exists():
                raise SystemExit(f"fork source stage not complete: {source}")
            target = run_root / "stages" / name
            target.mkdir(parents=True, exist_ok=True)
            for artifact in ("checkpoints.jsonl", "metrics.jsonl"):
                payload = (source / artifact).read_text(encoding="utf-8")
                (target / artifact).write_text(payload, encoding="utf-8")
            (target / "DONE").write_text("forked\n", encoding="utf-8")
            seeded.append(name)
        if name == through:
            break
    if not seeded or seeded[-1] != through:
        raise SystemExit(
            f"fork source {source_run_root} has no completed {through}"
        )
    origin_probe = source_run_root / "probes" / f"{through}.json"
    if origin_probe.exists():
        (run_root / "probes").mkdir(parents=True, exist_ok=True)
        (run_root / "probes" / "fork-origin.json").write_text(
            origin_probe.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (run_root / "provenance").mkdir(parents=True, exist_ok=True)
    (run_root / "provenance" / "fork.json").write_text(
        json.dumps(
            {
                "forked_from": str(source_run_root),
                "through": through,
                "stages": seeded,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"[fork] seeded {seeded} from {source_run_root}", flush=True)


def _resolve_runs_root(value: str) -> Path:
    preferred = Path(value).expanduser()
    if str(preferred) == DEFAULT_RUNS_ROOT and not preferred.parent.exists():
        preferred = Path(FALLBACK_RUNS_ROOT).expanduser()
    preferred.mkdir(parents=True, exist_ok=True)
    return preferred


def run_campaign(args: argparse.Namespace) -> None:
    smoke = bool(args.smoke)
    if smoke:
        plan_key = "B" if args.smoke == "nothink" else "C"
        base_plan = RUN_PLANS[plan_key]
        plan = RunPlan(
            key=base_plan.key,
            name=f"smoke-{args.smoke}",
            renderer_name=base_plan.renderer_name,
            max_tokens=base_plan.max_tokens,
        )
    else:
        plan = RUN_PLANS[args.run]
        max_tokens = args.max_tokens or plan.max_tokens
        if (
            args.steps_per_level != plan.steps_per_level
            or args.fork_l0_from
            or max_tokens != plan.max_tokens
        ):
            name = plan.name
            if args.steps_per_level != plan.steps_per_level:
                name = f"{name}-s{args.steps_per_level}"
            if max_tokens != plan.max_tokens:
                name = f"{name}-t{max_tokens}"
            plan = RunPlan(
                key=plan.key,
                name=name,
                renderer_name=plan.renderer_name,
                max_tokens=max_tokens,
                # The legacy rl-l0 extension fork carries its source's
                # (possibly SFT-warm-started) lineage without seeding the
                # SFT stage dir; re-running SFT would discard the fork.
                sft_levels=() if args.fork_l0_from else plan.sft_levels,
                sft_epochs=plan.sft_epochs,
                steps_per_level=args.steps_per_level,
                replay_groups_per_step=plan.replay_groups_per_step,
                fork_from="" if args.fork_l0_from else plan.fork_from,
                fork_through="" if args.fork_l0_from else plan.fork_through,
            )
    runs_root = _resolve_runs_root(args.runs_root)
    run_root = runs_root / plan.name
    run_root.mkdir(parents=True, exist_ok=True)
    if args.fork_l0_from:
        _fork_l0_stage(Path(args.fork_l0_from), run_root)
    fork_from = args.fork_from or plan.fork_from
    fork_through = args.fork_through or plan.fork_through
    forked = False
    if fork_from and not args.fork_l0_from:
        source_root = Path(fork_from)
        if not source_root.is_absolute():
            source_root = runs_root / fork_from
        _fork_stages_through(source_root, run_root, fork_through or "rl-l0")
        forked = True
    required = ["TINKER_API_KEY", "WANDB_API_KEY"]
    if os.environ.get("PIXCELL_REQUIRE_ISOLATION", "0") == "1":
        required.append("PIXCELL_EVALUATOR_IMAGE")
    for variable in required:
        if not os.environ.get(variable):
            raise SystemExit(f"{variable} is not present")
    _write_provenance(plan, run_root=run_root, smoke=smoke)
    if not args.skip_preflight:
        run_launch_preflight(
            _REPO_ROOT,
            dataset_root=_DATASET_ROOT,
            model_name=MODEL_NAME,
            renderer_name=plan.renderer_name,
            require_sandbox=os.environ.get("PIXCELL_REQUIRE_ISOLATION", "0") == "1",
            tokenize_sft=plan.sft,
            sft_levels=",".join(plan.sft_levels),
        )

    stages = build_stages(
        plan,
        run_root=run_root,
        wandb_project=args.wandb_project,
        smoke=smoke,
    )
    checkpoint: str | None = None
    reference_probe: dict | None = None
    if not smoke:
        origin_path = run_root / "probes" / "fork-origin.json"
        base_path = run_root / "probes" / "base.json"
        if forked and origin_path.exists():
            reference_probe = json.loads(origin_path.read_text(encoding="utf-8"))
        elif base_path.exists():
            reference_probe = json.loads(base_path.read_text(encoding="utf-8"))
        elif not forked:
            print("[probe] base model", flush=True)
            reference_probe = _probe(
                plan, run_root=run_root, tag="base", model_path=None
            )

    for stage in stages:
        if _stage_done(stage):
            print(f"[{stage.name}] already complete, skipping", flush=True)
            checkpoint = _last_weights_path(stage.args["log_path"])
            continue
        pre_stage_checkpoint = checkpoint
        extra: dict[str, str] = {}
        if checkpoint:
            extra["load_checkpoint_path"] = checkpoint
        _execute_stage(stage, extra=extra)
        _mark_done(stage)
        checkpoint = _last_weights_path(stage.args["log_path"])
        if smoke:
            continue
        print(f"[probe] after {stage.name}", flush=True)
        probe = _probe(
            plan,
            run_root=run_root,
            tag=stage.name,
            model_path=_last_sampler_path(stage.args["log_path"]),
        )
        level = stage.sft_level
        if level is not None:
            if reference_probe is None:
                raise SystemExit(
                    f"no reference probe available to gate {stage.name}"
                )
            passed, reason = _sft_gate(
                reference_probe,
                probe,
                level,
                relative=forked or level != "L0",
            )
            gate_name = (
                "sft_gate.json" if stage.name == "sft-l0" else f"sft_gate-{stage.name}.json"
            )
            (run_root / "probes" / gate_name).write_text(
                json.dumps({"passed": passed, "reason": reason}, indent=2),
                encoding="utf-8",
            )
            if passed:
                print(f"[gate] {reason}", flush=True)
            elif forked or level != "L0":
                print(
                    f"[gate] {reason} — skipping this SFT, continuing RL "
                    "from the pre-SFT weights",
                    flush=True,
                )
                checkpoint = pre_stage_checkpoint
            elif plan.key == "D":
                print(f"[gate] {reason} — falling back to RL from base", flush=True)
                checkpoint = None
            else:
                raise SystemExit(f"SFT sanity gate failed: {reason}")
        else:
            # RL boundary reached: this probe becomes the moving reference
            # for any later SFT insertion (the ladder compares each rung
            # against the lineage state it would improve on).
            reference_probe = probe

    print(f"[{plan.name}] campaign complete", flush=True)
    if smoke:
        _summarize_smoke(run_root, stages)


def _summarize_smoke(run_root: Path, stages: list[Stage]) -> None:
    summary: dict[str, object] = {}
    for stage in stages:
        metrics_path = Path(stage.args["log_path"]) / "metrics.jsonl"
        if not metrics_path.exists():
            continue
        rows = [
            json.loads(line)
            for line in metrics_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        token_keys = sorted(
            {
                key
                for row in rows
                for key, value in row.items()
                if "token" in key.lower() and isinstance(value, (int, float))
            }
        )
        summary[stage.name] = {
            "steps": len(rows),
            "token_metrics": {
                key: sum(float(row.get(key, 0.0)) for row in rows)
                for key in token_keys
            },
            "reward_by_step": [
                row.get("env/all/reward/total") for row in rows
            ],
        }
    out = run_root / "smoke_summary.json"
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"[smoke] summary written to {out}", flush=True)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--run", choices=sorted(RUN_PLANS), help="which run to execute")
    result.add_argument(
        "--smoke",
        choices=("nothink", "think"),
        help="price an operating point: 2 GRPO steps at 2 groups on L0",
    )
    result.add_argument("--runs-root", default=DEFAULT_RUNS_ROOT)
    result.add_argument(
        "--steps-per-level",
        type=int,
        default=30,
        help="RL steps per curriculum level; non-default gets a -sN run-name suffix",
    )
    result.add_argument(
        "--fork-l0-from",
        default="",
        help="legacy depth-variant fork: seed rl-l0 WITHOUT DONE so it resumes and extends",
    )
    result.add_argument(
        "--fork-from",
        default="",
        help="run name/path whose completed stage prefix seeds this campaign (overrides the plan's fork_from)",
    )
    result.add_argument(
        "--fork-through",
        default="",
        help="last stage taken from the fork source (default: the plan's fork_through)",
    )
    result.add_argument(
        "--max-tokens",
        type=int,
        default=0,
        help="optional sampling-ceiling override; non-default gets a -tN run-name suffix (never applied to an existing run)",
    )
    result.add_argument("--wandb-project", default="pixcell-rl")
    result.add_argument("--confirm-spend", default="")
    result.add_argument("--skip-preflight", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.confirm_spend != CONFIRM_SPEND:
        raise SystemExit(f"paid launch blocked: pass --confirm-spend {CONFIRM_SPEND}")
    if bool(args.run) == bool(args.smoke):
        raise SystemExit(
            "pass exactly one of --run {A..G} or --smoke {nothink,think}"
        )
    run_campaign(args)


if __name__ == "__main__":
    main()
