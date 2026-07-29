#!/usr/bin/env python3
"""The Track A campaign runner: four runs, one recipe, no ceremony.

    A  runA-l0sft-rl        no-think @ 4096   L0-SFT -> RL L0..L4
    B  runB-base-rl         no-think @ 4096   base   -> RL L0..L4
    C  runC-think-base-rl   think    @ 60000  base   -> RL L0..L4
    D  runD-think-l0sft-rl  think    @ 60000  L0-SFT -> RL L0..L4 (gated)

Each stage is one subprocess over the lean entry points (crash isolation,
one W&B run per stage, per-stage console logs); stages chain on the previous
stage's final sampler weights with a fresh optimizer, exactly as the old
lineage chained its runs. A stage that already finished is skipped, so
re-running the same command resumes the campaign.

The fixed probe (probe_eval) runs at campaign start — the base-model
baseline; there are no separate baselining studies — and after every stage.
Run A's and D's SFT must beat the base probe on L0 (executable >= 0.75 and
higher mean IoU) before RL spends anything; on failure A aborts for
diagnosis and D falls back to RL-from-base (the SFT collapse is itself a
finding — see the renderer-diagnostic precedent).

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
from dataclasses import asdict, dataclass
from pathlib import Path

from tinker_cookbook.checkpoint_utils import get_last_checkpoint

from rl.common.baselines import cached_rect_baseline
from rl.track_a.curriculum import LEVELS
from rl.track_a.launch import run_launch_preflight
from rl.track_a.probe_eval import run_probe, select_probe_tasks

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATASET_ROOT = _REPO_ROOT / "dataset"

CONFIRM_SPEND = "PIXCELL_RUNS_V2"
DEFAULT_RUNS_ROOT = "/Volumes/aadarwal_vx/QPG-MIT/PixCell-training/runs-v2"
FALLBACK_RUNS_ROOT = "~/pixcell-training/runs-v2"

SFT_GATE_MIN_EXECUTABLE = 0.75


@dataclass(frozen=True)
class RunPlan:
    key: str
    name: str
    renderer_name: str
    max_tokens: int
    sft: bool
    steps_per_level: int = 30


RUN_PLANS = {
    "A": RunPlan("A", "runA-l0sft-rl", "qwen3_5_disable_thinking", 4096, True),
    "B": RunPlan("B", "runB-base-rl", "qwen3_5_disable_thinking", 4096, False),
    "C": RunPlan("C", "runC-think-base-rl", "qwen3_5", 60000, False),
    "D": RunPlan("D", "runD-think-l0sft-rl", "qwen3_5", 60000, True),
}
MODEL_NAME = "Qwen/Qwen3.6-35B-A3B"


@dataclass(frozen=True)
class Stage:
    name: str
    module: str
    args: dict[str, str]


def build_stages(
    plan: RunPlan,
    *,
    run_root: Path,
    wandb_project: str,
    smoke: bool = False,
) -> list[Stage]:
    """The full ordered stage list for one run. Checkpoint chaining is
    resolved at execution time, not here."""

    steps = 2 if smoke else plan.steps_per_level
    groups = "2" if smoke else "8"
    canaries = "8" if smoke else "40"
    stages: list[Stage] = []
    if plan.sft and not smoke:
        stages.append(
            Stage(
                name="sft-l0",
                module="rl.track_a.train_sft",
                args={
                    "confirm_spend": CONFIRM_SPEND,
                    "model_name": MODEL_NAME,
                    "renderer_name": plan.renderer_name,
                    "levels": "L0",
                    "num_epochs": "2",
                    "learning_rate": "1e-4",
                    "log_path": str(run_root / "stages" / "sft-l0"),
                    "wandb_project": wandb_project,
                    "wandb_name": f"{plan.name}-sft-l0",
                    "skip_preflight": "True",
                },
            )
        )
    levels = ["L0"] if smoke else list(LEVELS)
    for level in levels:
        stage_name = f"rl-{level.lower()}"
        stages.append(
            Stage(
                name=stage_name,
                module="rl.track_a.train_rl",
                args={
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
                },
            )
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


def _sft_gate(base_probe: dict, sft_probe: dict) -> tuple[bool, str]:
    base_l0 = base_probe["per_level"]["L0"]
    sft_l0 = sft_probe["per_level"]["L0"]
    if sft_l0["executable_rate"] < SFT_GATE_MIN_EXECUTABLE:
        return False, (
            f"SFT L0 executable rate {sft_l0['executable_rate']:.3f} < "
            f"{SFT_GATE_MIN_EXECUTABLE}"
        )
    if sft_l0["mean_iou"] <= base_l0["mean_iou"]:
        return False, (
            f"SFT L0 mean IoU {sft_l0['mean_iou']:.3f} does not beat base "
            f"{base_l0['mean_iou']:.3f}"
        )
    return True, "sft beats base on L0"


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
            sft=False,
        )
    else:
        plan = RUN_PLANS[args.run]
    runs_root = _resolve_runs_root(args.runs_root)
    run_root = runs_root / plan.name
    run_root.mkdir(parents=True, exist_ok=True)
    for variable in ("TINKER_API_KEY", "WANDB_API_KEY", "PIXCELL_EVALUATOR_IMAGE"):
        if not os.environ.get(variable):
            raise SystemExit(f"{variable} is not present")
    _write_provenance(plan, run_root=run_root, smoke=smoke)
    if not args.skip_preflight:
        run_launch_preflight(
            _REPO_ROOT,
            dataset_root=_DATASET_ROOT,
            model_name=MODEL_NAME,
            renderer_name=plan.renderer_name,
            require_sandbox=True,
            tokenize_sft=plan.sft,
            sft_levels="L0" if plan.sft else "",
        )

    stages = build_stages(
        plan,
        run_root=run_root,
        wandb_project=args.wandb_project,
        smoke=smoke,
    )
    checkpoint: str | None = None
    base_probe: dict | None = None
    if not smoke:
        base_tag = "base"
        base_path = run_root / "probes" / f"{base_tag}.json"
        if base_path.exists():
            base_probe = json.loads(base_path.read_text(encoding="utf-8"))
        else:
            print("[probe] base model", flush=True)
            base_probe = _probe(plan, run_root=run_root, tag=base_tag, model_path=None)

    for stage in stages:
        if _stage_done(stage):
            print(f"[{stage.name}] already complete, skipping", flush=True)
            if stage.module.endswith("train_sft") or stage.module.endswith("train_rl"):
                checkpoint = _last_weights_path(stage.args["log_path"])
            continue
        extra: dict[str, str] = {}
        if checkpoint:
            extra["load_checkpoint_path"] = checkpoint
        _execute_stage(stage, extra=extra)
        _mark_done(stage)
        checkpoint = _last_weights_path(stage.args["log_path"])
        if not smoke:
            print(f"[probe] after {stage.name}", flush=True)
            probe = _probe(
                plan,
                run_root=run_root,
                tag=stage.name,
                model_path=_last_sampler_path(stage.args["log_path"]),
            )
            if stage.name == "sft-l0":
                assert base_probe is not None
                passed, reason = _sft_gate(base_probe, probe)
                (run_root / "probes" / "sft_gate.json").write_text(
                    json.dumps({"passed": passed, "reason": reason}, indent=2),
                    encoding="utf-8",
                )
                if not passed and plan.key == "D":
                    print(
                        f"[gate] {reason} — falling back to RL from base",
                        flush=True,
                    )
                    checkpoint = None
                elif not passed:
                    raise SystemExit(f"SFT sanity gate failed: {reason}")
                else:
                    print(f"[gate] {reason}", flush=True)

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
    result.add_argument("--wandb-project", default="pixcell-rl")
    result.add_argument("--confirm-spend", default="")
    result.add_argument("--skip-preflight", action="store_true")
    return result


def main() -> None:
    args = parser().parse_args()
    if args.confirm_spend != CONFIRM_SPEND:
        raise SystemExit(f"paid launch blocked: pass --confirm-spend {CONFIRM_SPEND}")
    if bool(args.run) == bool(args.smoke):
        raise SystemExit("pass exactly one of --run {A,B,C,D} or --smoke {nothink,think}")
    run_campaign(args)


if __name__ == "__main__":
    main()
