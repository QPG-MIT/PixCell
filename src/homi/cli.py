"""
HOMI CLI - Unified command-line interface.

Usage:
    homi doctor                   # Preflight: backend, keys, pins
    homi extract paper.pdf --output projects/mydevice
    homi generate projects/mydevice
    homi studio                   # Chat front door + light table
    homi optimize projects/mydevice/output/best.py
    homi explore projects/mydevice/output/best.py
    homi simulate projects/mydevice/output/best.gds
    homi benchmark --papers 1x2_coupler --families gemini claude
    homi serve                    # Start all MCP servers
    homi serve mj michaelangelo   # Start specific servers
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from homi.paths import projects_dir


def _detach_log_path(args) -> Path:
    """Where a detached stage writes its progress (the artifact channel)."""
    if args.command == "generate":
        return args.project_dir / "output" / "generate.log"
    if args.command == "retarget":
        workdir = args.workdir or args.script_path.parent / "retarget"
        return Path(workdir) / "retarget.log"
    if args.command == "extract":
        if args.output is None:
            raise SystemExit("--detach with extract requires -o/--output")
        return args.output / "extract.log"
    if args.command == "optimize":
        project = _manifest_project_for_args(args)
        return Path(project) / "output" / "polish.log"
    if args.command == "simulate":
        project = _manifest_project_for_args(args)
        return Path(project) / "output" / "simulate.log"
    raise SystemExit(f"--detach is not supported for `{args.command}`")


_MANIFEST_STAGE_BY_COMMAND = {
    "extract": "extract",
    "generate": "generate",
    "optimize": "polish",
    "retarget": "retarget",
    "simulate": "simulate",
}


def _manifest_stage_for_args(args) -> str | None:
    """Canonical progress-surface stage for a parsed CLI command."""
    return _MANIFEST_STAGE_BY_COMMAND.get(getattr(args, "command", None))


def _spawn_detached(log_path: Path) -> None:
    """Re-exec this command detached in a NEW SESSION and return immediately.

    Plain ``nohup ... &`` is not conductor-safe: codex kills the whole
    process group when a shell tool-call returns (measured 2026-07-09 — the
    studio conductor's detached generate died before its first log write).
    A new session escapes the group kill, so the stage survives under any
    conductor CLI; the log file is the only progress channel.
    """
    argv = [a for a in sys.argv[1:] if a != "--detach"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    # queued is written BEFORE the child exists: a fast child's `running`
    # (which carries its own pid) must never be regressed by the parent.
    project = _manifest_project_for_args(_ARGS_FOR_DETACH)
    stage = _manifest_stage_for_args(_ARGS_FOR_DETACH) or (argv[0] if argv else "")
    _write_stage_manifest(project, stage, status="queued", log=str(log_path))
    # scrub the caller's pane identity: a detached stage must never inherit
    # a conductor's $TMUX_PANE (nothing consumes it since the RunWorkspace
    # move, but a stale one invites exactly the spawn-beside-caller bug)
    env = {k: v for k, v in os.environ.items() if k != "TMUX_PANE"}
    with open(log_path, "a") as log:
        proc = subprocess.Popen(
            # -u: the log is the only progress channel — stream it live
            # instead of block-buffering until exit
            [sys.executable, "-u", "-m", "homi.cli", *argv],
            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
            start_new_session=True, env=env,
        )
    print(f"detached: pid={proc.pid} log={log_path}")


_ARGS_FOR_DETACH = None  # stashed by main() before _spawn_detached runs


def _manifest_project_for_args(args) -> Path | None:
    """Project dir for the stage manifest, from PARSED args (never argv
    guessing — option-first orderings like `generate --cli cdxx <dir>` broke
    the positional heuristic)."""
    if args is None:
        return None
    command = getattr(args, "command", None)
    if command == "generate":
        return getattr(args, "project_dir", None)
    if command == "extract":
        return getattr(args, "output", None)
    artifact = {
        "optimize": getattr(args, "script_path", None),
        "retarget": getattr(args, "script_path", None),
        "simulate": getattr(args, "gds_path", None),
    }.get(command)
    if artifact is not None:
        artifact = Path(artifact)
        # Promoted web artifacts are project/output/best.{py,gds}.  For a
        # standalone script/GDS, its own directory is the smallest honest
        # project boundary available.
        return artifact.parent.parent if artifact.parent.name == "output" else artifact.parent
    return None


def _write_stage_manifest(project_dir: Path | None, stage: str, **fields) -> None:
    """Machine-readable stage state (`output/stage_<stage>.json`).

    Terminal truth for progress surfaces (web banner, studio strip): parsed,
    never inferred from logs. Best-effort — a manifest failure never breaks
    the stage itself.
    """
    if project_dir is None or not stage:
        return
    import json as _json
    from datetime import datetime, timezone

    try:
        out = Path(project_dir) / "output"
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"stage_{stage}.json"
        record = {}
        if path.exists():
            try:
                record = _json.loads(path.read_text())
            except (ValueError, OSError):
                record = {}
        record.update({"stage": stage, **fields,
                       "updated_at": datetime.now(timezone.utc).isoformat()})
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(_json.dumps(record, indent=1))
        os.replace(tmp, path)
    except OSError:
        pass


def main():
    parser = argparse.ArgumentParser(
        prog="homi",
        description="HOMI - Photonic Multimodal Intelligence: Paper to GDS Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  homi doctor
  homi extract paper.pdf -o projects/ring_resonator
  homi generate projects/ring_resonator
  homi studio
  homi optimize projects/ring_resonator --method nelder-mead
  homi benchmark --papers 1x2_coupler --families gemini
  homi serve
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- extract ---
    p_extract = subparsers.add_parser("extract", help="Extract device images from a research paper")
    p_extract.add_argument("input", type=Path, help="PDF file or image path")
    p_extract.add_argument("-o", "--output", type=Path, default=None, help="Output project directory")
    p_extract.add_argument("--device", type=str, default=None, help="Device description (e.g. 'ring resonator in Figure 3')")
    p_extract.add_argument("--num-variants", type=int, default=5, help="Number of B&W variants to generate")
    p_extract.add_argument("--cli", type=str, default=None,
                           help="Worker CLI alias (default cdxx, host codex pinned gpt-5.5 medium fast; NO boxes)")
    p_extract.add_argument("--detach", action="store_true",
                           help="Run in a new session and return immediately; progress in <output>/extract.log")

    # --- generate ---
    p_generate = subparsers.add_parser("generate", help="Generate GDS from device image (agent recreate loop)")
    p_generate.add_argument("project_dir", type=Path, help="Project directory with device_bw.png and footprint.json")
    p_generate.add_argument("--baseline", action="store_true",
                            help="Run the legacy Michaelangelo multi-seed sweep instead of the agent loop")
    p_generate.add_argument("--cli", type=str, default="cdxx",
                            help="Worker CLI alias for the agent loop (default cdxx, host codex pinned gpt-5.5 medium fast; NO boxes)")
    p_generate.add_argument("--worker-model", type=str, default=None, help="Worker model override")
    p_generate.add_argument("--worker-effort", type=str, default=None, help="Worker reasoning effort")
    p_generate.add_argument("--preset", choices=["quick", "balanced", "thorough", "maximum"], default="balanced",
                            help="(--baseline only) multi-seed preset")
    p_generate.add_argument("--model", type=str, default="gemini/gemini-3-flash-preview",
                            help="(--baseline only) VLM model (provider/name)")
    p_generate.add_argument("--phase1-only", action="store_true", help="(--baseline only) run Phase 1 only")
    p_generate.add_argument("--base-seed", type=int, default=1333, help="(--baseline only) base seed")
    p_generate.add_argument("--detach", action="store_true",
                            help="Run in a new session and return immediately; progress in <project>/output/generate.log")

    # --- studio ---
    p_studio = subparsers.add_parser(
        "studio", help="Launch PixCell studio — chat-first: the conductor + the light table"
    )
    p_studio.add_argument("--port", type=int, default=2718)
    p_studio.add_argument("--edit", action="store_true", help="Open in marimo edit mode")

    # --- web (the public front door) ---
    p_web = subparsers.add_parser(
        "web", help="Launch the web front door — per-session conductor panes + live light table"
    )
    p_web.add_argument("--port", type=int, default=2719)
    p_web.add_argument("--host", type=str, default="127.0.0.1",
                       help="Bind address (non-loopback requires HOMI_WEB_ALLOW_LAN=1)")
    p_web.add_argument("--capacity", type=int, default=2,
                       help="Max concurrent live conductor panes")
    p_web.add_argument("--cli", type=str, default="cxx",
                       help="Conductor CLI alias (default cxx: host claude full-auto)")

    # --- retarget (Phase B) ---
    p_retarget = subparsers.add_parser(
        "retarget", help="Retarget a device to a layer stack against a function spec (Phase B)"
    )
    p_retarget.add_argument("script_path", type=Path, help="Recreated parametric device script")
    p_retarget.add_argument("--stack", type=Path, required=True, help="Layer stack JSON")
    p_retarget.add_argument("--spec", type=Path, required=True, help="Function spec JSON (WHAT, never WHY)")
    p_retarget.add_argument("--tier1-cap", type=int, default=3, help="Tier-1 FDTD calls per stack")
    p_retarget.add_argument("--ceiling", type=float, default=0.45, help="Tier-1 FlexCredit ceiling per call")
    p_retarget.add_argument("--cli", type=str, default="cdxx",
                            help="Worker CLI alias (default cdxx, host codex pinned gpt-5.5 medium fast; NO boxes)")
    p_retarget.add_argument("--workdir", type=Path, default=None, help="Worker workdir (default: <script dir>/retarget)")
    p_retarget.add_argument("--detach", action="store_true",
                            help="Run in a new session and return immediately; progress in <workdir>/retarget.log")

    # --- optimize ---
    p_optimize = subparsers.add_parser("optimize", help="Optimize GDS parameters with JEE")
    p_optimize.add_argument("script_path", type=Path, help="GDSFactory script to optimize")
    p_optimize.add_argument(
        "--target", type=Path, default=None,
        help="Target image (auto-discovers project device_bw.png or component image)")
    p_optimize.add_argument("--method", choices=["nelder-mead", "powell"], default="nelder-mead")
    p_optimize.add_argument("--max-iterations", type=int, default=150)
    p_optimize.add_argument("--explore", action="store_true", help="Run grid exploration + parallel optimization")
    p_optimize.add_argument(
        "--promote", action="store_true",
        help="gate the optimized source/GDS and replace best.py/best.gds only on strict success",
    )
    p_optimize.add_argument(
        "--detach", action="store_true",
        help="Run in a detached process; progress in <project>/output/polish.log",
    )

    # --- explore ---
    p_explore = subparsers.add_parser(
        "explore", help="Generate the device workbench (marimo instrument)"
    )
    p_explore.add_argument("script_path", type=Path, help="GDSFactory script")
    p_explore.add_argument("-o", "--output", type=Path, default=None, help="Output directory")
    p_explore.add_argument("--draw", action="store_true",
                           help="Include the Draw tab (sketch -> dispatch recreation worker)")
    p_explore.add_argument("--launch", action="store_true", help="Immediately serve the workbench")

    # --- simulate ---
    p_simulate = subparsers.add_parser("simulate", help="Upload GDS to Tidy3D for simulation")
    p_simulate.add_argument("gds_path", type=Path, help="GDS file to simulate")
    p_simulate.add_argument("--material", type=str, default="Silicon (SOI)", help="Material platform")
    p_simulate.add_argument("--thickness", type=float, default=220, help="Device thickness in nm")
    p_simulate.add_argument("--wavelength", type=float, default=1.55, help="Wavelength in um")
    p_simulate.add_argument(
        "--detach", action="store_true",
        help="Create the draft in a detached process; progress in output/simulate.log",
    )

    # --- benchmark ---
    p_bench = subparsers.add_parser("benchmark", help="Run multi-model benchmark")
    p_bench.add_argument("--papers", nargs="+", default=["1x2_coupler", "2_004629"])
    p_bench.add_argument("--families", nargs="+", default=None, choices=["gemini", "claude", "openai", "kimi", "qwen", "grok"])
    p_bench.add_argument("--phase1-seeds", type=int, default=15)
    p_bench.add_argument("--phase1-parallel", type=int, default=8)
    p_bench.add_argument("--aggregate", type=Path, default=None, help="Only aggregate existing results")
    p_bench.add_argument("--output-dir", type=Path, default=Path("benchmark_results"))
    p_bench.add_argument("--dry-run", action="store_true")

    # --- serve ---
    p_serve = subparsers.add_parser("serve", help="Start MCP servers")
    p_serve.add_argument("servers", nargs="*", default=[], help="Specific servers to start (default: all)")

    # --- app ---

    # --- api ---
    p_api = subparsers.add_parser("api", help="Start the REST API server")
    p_api.add_argument("--host", type=str, default="0.0.0.0")
    p_api.add_argument("--port", type=int, default=8000)
    p_api.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    # --- migrate ---
    p_migrate = subparsers.add_parser("migrate", help="Migrate GDS to target PDK")
    p_migrate.add_argument("gds_path", type=Path, help="GDS file to migrate")
    p_migrate.add_argument("--target-pdk", type=str, required=True, help="Target PDK name")
    p_migrate.add_argument("-o", "--output", type=Path, default=None, help="Output path for converted GDS")
    p_migrate.add_argument("--drc", action="store_true", help="Run DRC after conversion")

    subparsers.add_parser(
        "doctor",
        help="Preflight: python/gdsfactory pins, worker backend, keys, dirs",
    )

    # --- runs (worker-run workspaces) ---
    p_runs = subparsers.add_parser(
        "runs", help="Worker-run workspaces: list, garbage-collect, kill"
    )
    p_runs.add_argument("action", choices=["ls", "gc", "kill"], nargs="?", default="ls")
    p_runs.add_argument("run_id", nargs="?", default=None, help="run id (for kill)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if getattr(args, "detach", False):
        global _ARGS_FOR_DETACH
        _ARGS_FOR_DETACH = args
        _spawn_detached(_detach_log_path(args))
        return
    manifest_stage = _manifest_stage_for_args(args)
    if manifest_stage:
        proj = _manifest_project_for_args(args)
        if proj is not None:
            from datetime import datetime, timezone
            _write_stage_manifest(Path(proj), manifest_stage, status="running",
                                  pid=os.getpid(),
                                  started_at=datetime.now(timezone.utc).isoformat())

    commands = {
        "extract": cmd_extract,
        "generate": cmd_generate,
        "retarget": cmd_retarget,
        "studio": cmd_studio,
        "web": cmd_web,
        "optimize": cmd_optimize,
        "explore": cmd_explore,
        "simulate": cmd_simulate,
        "benchmark": cmd_benchmark,
        "serve": cmd_serve,
        "api": cmd_api,
        "migrate": cmd_migrate,
        "doctor": cmd_doctor,
        "runs": cmd_runs,
    }

    handler = commands[args.command]
    # handlers signal failure with a nonzero int return — that status must
    # reach the shell (detached stages and CI read the exit code). SystemExit
    # inside a handler must still land a terminal manifest (a permanently
    # `running` stage blocks every progress surface).
    rc_int = 1
    stage_error = None
    try:
        rc = handler(args)
        rc_int = int(rc) if isinstance(rc, int) else 0
    except SystemExit as e:
        rc_int = int(e.code) if isinstance(e.code, int) else 1
    except BaseException as exc:
        # An unexpected exception used to leave stage_<name>.json permanently
        # `running`, which blocked retry, cancellation, and session reaping.
        # Preserve the exception for the CLI while terminalizing the durable
        # progress record in the finally block.
        stage_error = f"{type(exc).__name__}: {str(exc)[:500]}"
        raise
    finally:
        if manifest_stage:
            proj = _manifest_project_for_args(args)
            if proj is not None:
                from datetime import datetime, timezone

                fields = {
                    "status": "completed" if rc_int == 0 else "failed",
                    "exit": rc_int,
                    "ended_at": datetime.now(timezone.utc).isoformat(),
                }
                if stage_error:
                    fields["detail"] = stage_error
                _write_stage_manifest(Path(proj), manifest_stage, **fields)
    sys.exit(rc_int)


# =============================================================================
# Command handlers
# =============================================================================


def cmd_doctor(args):
    from homi.doctor import main as doctor_main

    sys.exit(doctor_main())


def cmd_extract(args):
    """Extract device images from a research paper (agent-first perception).

    Perception (which figure is the device, where to crop, the dimensions) is
    done by a dispatched extractor agent using its own eyes and the keyless
    tools — NOT by out-of-band VLM scoring. PDFs and direct images both go
    through the agent; the only surviving API call is the B&W raster
    generation the agent invokes itself (generate_bw_variants).
    """
    from homi import dispatch

    input_path = args.input.resolve()
    if not input_path.exists():
        print(f"Error: {input_path} not found")
        sys.exit(1)

    # Determine output directory
    if args.output:
        output_dir = args.output.resolve()
    else:
        stem = input_path.stem
        output_dir = projects_dir() / stem
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Extracting from: {input_path}")
    print(f"Output: {output_dir}")

    input_kind = "pdf" if input_path.suffix.lower() == ".pdf" else "image"
    print("Dispatching extractor agent (agent-first perception, no VLM scoring)...")
    result = dispatch.dispatch_extractor_agent(
        str(input_path), str(output_dir), hint=getattr(args, "device", None),
        input_kind=input_kind, cli=getattr(args, "cli", None),
    )
    print(f"  backend={result['backend']} status={result['status']}")
    for name, present in (result.get("artifacts") or {}).items():
        print(f"  {'✓' if present else '✗'} {name}")
    if result["status"] not in ("ok", "planned"):
        # artifact-judged failures often carry no error/stderr — the worker's
        # own final output is the only evidence of what went wrong
        detail = (result.get("error") or result.get("stderr_tail")
                  or (result.get("output_tail") or "")[-1200:])
        print(f"  extractor failed: {detail}")
        return 1

    print(f"\nDone. Project directory: {output_dir}")
    return 0


def cmd_generate(args):
    """Generate GDS from a device image.

    Default: the Phase-A agent recreate loop — dispatch a worker agent that
    writes a primitives-only parametric script and iterates against the
    calibrated IoU verifier, then accept ONLY through the conductor gate
    (recomputed IoU + purity; no worker-reported number enters the record).
    ``--baseline`` runs the legacy Michaelangelo multi-seed sweep instead
    (kept: it is the paper's measured chatbot-era baseline).
    """
    project_dir = args.project_dir.resolve()
    component_dir = project_dir / "component"

    # Check prerequisites
    device_bw = project_dir / "device_bw.png"
    footprint_json = project_dir / "footprint.json"
    if not device_bw.exists():
        device_bw = component_dir / "component.png"
    if not device_bw.exists():
        print("Error: No device_bw.png or component/component.png found")
        sys.exit(1)

    if not footprint_json.exists():
        fp_in_comp = component_dir / "footprint.json"
        if fp_in_comp.exists():
            footprint_json = fp_in_comp
        else:
            print("Error: No footprint.json found")
            sys.exit(1)

    if not getattr(args, "baseline", False):
        return _generate_agent_first(args, project_dir, device_bw, footprint_json)

    return _generate_baseline(args, project_dir, component_dir, device_bw, footprint_json)


def _generate_agent_first(args, project_dir, device_bw, footprint_json):
    """Dispatch the Phase-A recreate worker and gate its artifacts."""
    import shutil as _shutil

    from homi import conductor, dispatch

    # Canonicalize inputs where the phase_a brief expects them.
    canonical_bw = project_dir / "device_bw.png"
    canonical_fp = project_dir / "footprint.json"
    if device_bw.resolve() != canonical_bw.resolve():
        _shutil.copy2(device_bw, canonical_bw)
    if footprint_json.resolve() != canonical_fp.resolve():
        _shutil.copy2(footprint_json, canonical_fp)

    workdir = project_dir / "output" / "recreation_agent"
    workdir.mkdir(parents=True, exist_ok=True)

    print(f"Project: {project_dir}")
    print("Dispatching Phase-A recreation worker (agent is the optimizer)...")
    result = dispatch.dispatch_agent(
        "phase_a",
        {
            "INPUT_DIR": str(project_dir),
            "WORKDIR": str(workdir),
            "GIT_RULE": "Do NOT run any git commands.",
        },
        workdir=str(workdir),
        cli=args.cli,
        model=getattr(args, "worker_model", None),
        effort=getattr(args, "worker_effort", None),
    )
    print(f"  backend={result['backend']} status={result['status']}")
    if result["status"] not in ("ok", "planned"):
        print(f"  worker failed: {result.get('error') or result.get('output_tail', '')[-400:]}")
        return 1
    if result["status"] == "planned":
        return 0

    del _shutil, conductor  # promotion is centralized below
    from homi.conductor.promote import gate_and_promote

    try:
        outcome = gate_and_promote(project_dir, workdir)
    except FileNotFoundError as e:
        print(f"  {e}")
        return 1
    gate = outcome.gate
    print(f"  gate: IoU={gate.iou:.4f} claim={outcome.claim_status} "
          f"purity={'clean' if not gate.purity else gate.purity} "
          f"knob={outcome.knob_status} promoted={outcome.promoted}")
    if not outcome.promoted:
        for reason in outcome.reasons:
            print(f"    - {reason}")
        print("  NOT PROMOTED — artifacts kept for inspection "
              f"({project_dir / 'output' / 'gate.json'}).")
        return 1

    output_dir = project_dir / "output"
    print("\nBest result (gate-verified):")
    print(f"  GDS: {output_dir / 'best.gds'}")
    print(f"  Script: {output_dir / 'best.py'}")
    print(f"  IoU: {gate.iou:.4f} (recomputed)")
    return 0


def _generate_baseline(args, project_dir, component_dir, device_bw, footprint_json):
    """The legacy Michaelangelo multi-seed sweep (the measured baseline)."""
    from homi import gds_generation

    import json
    with open(footprint_json) as f:
        fp = json.load(f)

    length_um = fp.get("footprint_um", [fp.get("length_um", 50)])[0] if "footprint_um" in fp else fp.get("length_um", 50)
    width_um = fp.get("footprint_um", [0, fp.get("width_um", 30)])[1] if "footprint_um" in fp else fp.get("width_um", 30)

    print(f"Project: {project_dir}")
    print(f"Device: {device_bw}")
    print(f"Footprint: {length_um} x {width_um} um")
    print(f"Preset: {args.preset}")
    print(f"Model: {args.model}")

    from homi.paths import michaelangelo_dir as _mdir

    michaelangelo_dir = _mdir()

    # Setup component directory if not already done
    # Signature: (component_dir: Path, device_bw_path: str, footprint_length_um, footprint_width_um)
    if not component_dir.exists():
        print("\nSetting up component directory...")
        gds_generation.setup_component_directory(
            component_dir, str(device_bw), length_um, width_um
        )

    # Run calibration if needed — signature: (component_dir: Path, michaelangelo_dir: Path)
    calibration_file = component_dir / "calibration.json"
    if not calibration_file.exists():
        print("Running calibration...")
        gds_generation.run_calibration(component_dir, michaelangelo_dir)

    # Preset config
    presets = {
        "quick": {"seed_range": 2, "additional_turns": 2, "num_parallel": 4},
        "balanced": {"seed_range": 6, "additional_turns": 3, "num_parallel": 8},
        "thorough": {"seed_range": 12, "additional_turns": 5, "num_parallel": 8},
        "maximum": {"seed_range": 20, "additional_turns": 8, "num_parallel": 12},
    }
    preset = presets[args.preset]

    # Phase 1 — signature: (component_dir: Path, michaelangelo_dir: Path, base_seed, seed_range, num_parallel, model)
    print(f"\nPhase 1: Exploring {2 * preset['seed_range'] + 1} seeds...")
    gds_generation.run_phase1(
        component_dir,
        michaelangelo_dir,
        base_seed=args.base_seed,
        seed_range=preset["seed_range"],
        num_parallel=preset["num_parallel"],
        model=args.model,
    )
    print("  Phase 1 complete.")

    if args.phase1_only:
        print("Phase 1 only mode. Skipping Phase 2.")
        return

    # Phase 2 — signature: (component_dir: Path, michaelangelo_dir: Path, additional_turns, num_parallel, model, ...)
    print(f"\nPhase 2: Extended iteration ({preset['additional_turns']} additional turns)...")
    gds_generation.run_phase2(
        component_dir,
        michaelangelo_dir,
        additional_turns=preset["additional_turns"],
        num_parallel=preset["num_parallel"],
        model=args.model,
    )
    print("  Phase 2 complete.")

    # Collect best output — signature: (component_dir: Path, output_dir: Path)
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)
    best = gds_generation.collect_best_output(component_dir, output_dir)
    if best:
        print("\nBest result:")
        print(f"  GDS: {best.get('gds_path', 'N/A')}")
        print(f"  Script: {best.get('script_path', 'N/A')}")
        print(f"  IoU: {best.get('iou', 'N/A')}")
    else:
        print("\nNo successful results. Try a different preset or refine the B&W image.")


def cmd_studio(args):
    """Launch PixCell studio (chat-first marimo app)."""
    import subprocess

    import homi

    app_path = Path(homi.__file__).parent / "studio_app.py"
    mode = "edit" if getattr(args, "edit", False) else "run"
    marimo = Path(sys.executable).parent / "marimo"
    print(f"PixCell studio ({mode}) on port {args.port} — chat drives the pipeline; "
          "the table shows what the agents verified.")
    subprocess.run([str(marimo), mode, str(app_path), "--port", str(args.port)],
                   check=False)


def cmd_web(args):
    """Launch the web front door (per-session conductor panes + SSE)."""
    from homi.paths import repo_root, workspace_root
    from homi.web.daemon import serve

    root = repo_root() or workspace_root()
    serve(root, host=args.host, port=args.port,
          capacity=args.capacity, cli=args.cli)
    return 0


def cmd_runs(args):
    """Worker-run workspaces: `homi runs ls|gc|kill <run_id>`."""
    from homi import workspace

    if args.action == "ls":
        infos = workspace.list_runs()
        if not infos:
            print("no recorded runs")
            return 0
        for i in infos:
            where = i.session or "headless"
            print(f"{i.run_id:44s} {i.status:8s} {where}")
        return 0
    if args.action == "gc":
        killed = workspace.gc_runs()
        print(f"collected {len(killed)} leftover session(s)"
              + (": " + ", ".join(killed) if killed else ""))
        return 0
    # kill
    if not args.run_id:
        print("Error: homi runs kill needs a run id (see `homi runs ls`)")
        return 1
    for i in workspace.list_runs():
        if i.run_id == args.run_id:
            if i.session:
                import subprocess as _sp

                _sp.run(["tmux", "kill-session", "-t", i.session],
                        capture_output=True, text=True, timeout=15)
            i.status = "killed"
            workspace._persist(i)
            print(f"killed {i.run_id}")
            return 0
    print(f"Error: no run named {args.run_id}")
    return 1


def _canonical_measured_metrics(payload: dict) -> dict[str, float]:
    """Map tier-1 fixture fields onto the public specification vocabulary."""
    measured = {
        str(key): float(value)
        for key, value in payload.items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    split = measured.get("split_fraction_t", measured.get("split_fraction"))
    if split is not None:
        measured.setdefault("balance", split)
        measured.setdefault("coupling_ratio", split)
        measured.setdefault("uniformity", abs(split - 0.5))
    if "transmission" not in measured:
        transmission = measured.get("transmission_total", measured.get("T"))
        if transmission is None and "insertion_loss_db" in measured:
            loss_db = measured["insertion_loss_db"]
            transmission = 10 ** ((loss_db if loss_db <= 0 else -loss_db) / 10)
        if transmission is not None:
            measured["transmission"] = transmission
    return measured


def _write_retarget_result(
    *,
    workdir: Path,
    stack_path: Path,
    spec_path: Path,
) -> dict:
    """Evaluate Phase-B artifacts and atomically own ``result.json``.

    Workers optimize and write device/fixture artifacts; the deterministic
    evaluator, not the worker's final prose, decides pass/fail/unmeasured.
    """
    import json as _json

    from homi.spec_optimization import evaluate

    stack = _json.loads(stack_path.read_text())
    spec = _json.loads(spec_path.read_text())
    stack_id = stack_path.stem
    stack_dir = workdir / stack_id
    stack_dir.mkdir(parents=True, exist_ok=True)
    device = stack_dir / f"device_{stack_id}.py"
    if not device.is_file():
        matches = sorted(workdir.rglob(f"device_{stack_id}.py"))
        device = matches[-1] if matches else device

    measured_file = device.parent / "measured.json"
    measured = {}
    if measured_file.is_file():
        try:
            raw = _json.loads(measured_file.read_text())
            if isinstance(raw, dict):
                measured = _canonical_measured_metrics(raw)
        except (OSError, ValueError, TypeError):
            measured = {}

    if not device.is_file():
        result = {
            "verdict": "unmeasured",
            "fom": measured,
            "detail": f"Phase-B produced no device_{stack_id}.py artifact",
        }
    else:
        try:
            report = evaluate(
                device,
                stack,
                spec,
                measured_metrics=measured,
                cache_dir=device.parent / "mode_cache",
            )
            fom = {
                verdict.metric: verdict.measured
                for verdict in report.verdicts
                if verdict.measured is not None
            }
            verdict = (
                "pass" if report.passes
                else "unmeasured" if report.unmeasured
                else "fail"
            )
            result = {
                "verdict": verdict,
                "fom": fom,
                "detail": report.reason or "all specified targets pass",
                "report": report.to_dict(),
            }
        except Exception as exc:  # noqa: BLE001 - measurement failure is a verdict
            result = {
                "verdict": "unmeasured",
                "fom": measured,
                "detail": f"evaluation failed: {type(exc).__name__}: {str(exc)[:300]}",
            }

    result.update({
        "stack": stack_id,
        "stack_label": stack.get("label", stack_id),
        "spec": spec_path.name,
    })
    path = stack_dir / "result.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(_json.dumps(result, indent=1, default=str))
    os.replace(tmp, path)
    return result


def cmd_retarget(args):
    """Retarget a recreated device to a layer stack against a function spec.

    Phase-B protocol: dispatch a worker agent with the phase_b brief; the
    worker reasons and optimizes, the evaluator measures (tier-0 locally), and
    tier-1 FDTD runs ONLY through this conductor-serviced MEASURE loop under a
    per-stack call cap. Requires the anu pane backend — the handshake is
    multi-turn, which a one-shot headless CLI cannot service. Cloud spend
    stays gated by the tier-1 cost ceiling.
    """
    import json as _json
    import shutil as _shutil
    import subprocess as _subprocess

    from homi import briefs
    from homi.conductor import CapLedger, lint
    from homi.conductor.measure import service_loop

    script_path = args.script_path.resolve()
    stack_path = args.stack.resolve()
    spec_path = args.spec.resolve()
    for p in (script_path, stack_path, spec_path):
        if not p.exists():
            print(f"Error: {p} not found")
            return 1

    from homi import workspace as _workspace

    backend = _workspace.resolve_backend()
    if backend == "headless" and not (_shutil.which("claude") or _shutil.which("codex")):
        print("Error: homi retarget needs a worker backend — anu (`pane` + tmux), "
              "or `claude`/`codex` on PATH for the headless multi-turn session.")
        return 1

    workdir = (args.workdir or script_path.parent / "retarget").resolve()
    workdir.mkdir(parents=True, exist_ok=True)

    # Blind protocol: worker inputs must not leak device class or mechanism.
    spec_hits = lint(spec_path.read_text())
    if spec_hits:
        print(f"Error: hint-lint blocked dispatch — spec file leaks {spec_hits}")
        return 1

    brief = briefs.render(
        "phase_b_retarget",
        STACKS=str(stack_path),
        SPECS=str(spec_path),
        TIER1_CAP=str(args.tier1_cap),
        WORKDIR=str(workdir),
        GIT_RULE="Do NOT run any git commands.",
    )

    stack = _json.loads(stack_path.read_text())

    def run_tier1(req):
        fixture = Path(req.fixture).resolve()
        cmd = [
            sys.executable, "-m", "homi.conductor.tier1",
            "--dir", str(fixture.parent), "--gds", fixture.name,
            "--thickness-nm", str(int(round(float(stack.get("thickness_um", 0.22)) * 1000))),
            "--ceiling", str(args.ceiling),
        ]
        if stack.get("core_n") is not None:
            cmd += ["--core-n", str(stack["core_n"])]
        if stack.get("clad_n") is not None:
            cmd += ["--clad-n", str(stack["clad_n"])]
        proc = _subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            raise RuntimeError((proc.stderr or proc.stdout)[-500:])
        measured_path = fixture.parent / "measured.json"
        return _json.loads(measured_path.read_text())

    print(f"Dispatching Phase-B retarget worker (cap {args.tier1_cap} tier-1 calls/stack, "
          f"{backend} backend)...")
    # own the run's lifecycle here: the session is killed only on a completed
    # protocol; a BLOCKED verdict or a transport failure keeps it (with an
    # attach hint) for inspection.
    ws = _workspace.open_run("phase_b", str(workdir))
    status = "failed"
    try:
        # spawn inside the try: a partial tmux spawn failure must still
        # close the run (keeping any created session with the attach hint)
        worker = ws.spawn(role="phase-b", cli=args.cli)
        worker.send(brief)
        out = service_loop(worker.send, lambda: worker.wait(3600),
                           CapLedger(per_stack=args.tier1_cap), run_tier1)
        print(out[-1500:])
        status = "ok" if "PHASE_B DONE" in out else "failed"
    finally:
        ws.close(status)
    if status != "ok":
        return 1
    result = _write_retarget_result(
        workdir=workdir,
        stack_path=stack_path,
        spec_path=spec_path,
    )
    detail = result.get("detail")
    suffix = f" - {detail}" if detail else ""
    print(f"Recorded {stack_path.stem}: {result['verdict']}{suffix}")
    return 0


def _discover_optimize_inputs(
        script_path: Path, explicit_target: Path | None = None,
) -> tuple[Path | None, Path | None, Path | None]:
    """Find target, recorded calibration, and footprint for JEE.

    The promoted web layout keeps ``best.py`` in ``project/output`` and the
    gate's exact calibration beside ``output/recreation_*/component.png``.
    Legacy projects instead use ``component/``.  Prefer the frozen project
    target and newest gate calibration, falling back without path guessing in
    the optimizer itself.
    """
    script_path = Path(script_path).resolve()
    script_dir = script_path.parent
    project = script_dir.parent if script_dir.name == "output" else script_dir

    recreation_dirs: list[Path] = []
    for root in (script_dir, project / "output"):
        if root.is_dir():
            recreation_dirs.extend(root.glob("recreation_*"))
    recreation_dirs = list({p.resolve(): p.resolve() for p in recreation_dirs}.values())
    recreation_dirs.sort(
        key=lambda p: (p / "calibration.json").stat().st_mtime
        if (p / "calibration.json").is_file() else -1,
        reverse=True,
    )

    target: Path | None
    if explicit_target is not None:
        target = Path(explicit_target).expanduser().resolve()
    else:
        target = next((p for p in (
            project / "device_bw.png",
            *(d / "component.png" for d in recreation_dirs),
            project / "component" / "component.png",
            script_dir / "component" / "component.png",
        ) if p.is_file()), None)

    calibration: Path | None = None
    if target is not None:
        sibling = target.parent / "calibration.json"
        if sibling.is_file():
            calibration = sibling
    # A recreation calibration is valid for the canonical frozen project mask,
    # which is copied byte-for-byte into that recreation workdir.
    canonical_target = project / "device_bw.png"
    if (calibration is None and target is not None
            and canonical_target.is_file()
            and target == canonical_target.resolve()):
        import filecmp

        # Session reuse or a replaced upload must not pair a new mask with a
        # stale calibration.  Generation copied this target into its workdir,
        # so byte identity is the durable provenance check available here.
        calibration = next((
            d / "calibration.json" for d in recreation_dirs
            if (d / "calibration.json").is_file()
            and (d / "component.png").is_file()
            and filecmp.cmp(canonical_target, d / "component.png", shallow=False)
        ), None)
    if calibration is None:
        calibration = next((p for p in (
            script_dir / "jee_calibration.json",
            project / "component" / "calibration.json",
        ) if p.is_file()), None)

    footprint = next((p for p in (
        project / "footprint.json",
        project / "component" / "footprint.json",
        script_dir / "footprint.json",
        script_dir / "component" / "footprint.json",
    ) if p.is_file()), None)
    return target, calibration, footprint


def _polish_knob(project: Path, best_params: dict) -> tuple[str, float | None] | None:
    """Recover the prior gate's tested parameter, with a safe fallback."""
    import json as _json

    gate = {}
    try:
        gate = _json.loads((project / "output" / "gate.json").read_text())
    except (OSError, ValueError):
        pass
    knob = gate.get("knob") if isinstance(gate, dict) else None
    if isinstance(knob, dict) and knob.get("param"):
        width = None
        expected = knob.get("expected_area_growth_um2")
        delta = knob.get("delta_um")
        if (isinstance(expected, (int, float))
                and isinstance(delta, (int, float)) and delta):
            width = float(expected) / float(delta)
        return str(knob["param"]), width
    if best_params:
        return str(next(iter(best_params))), None
    return None


def _promote_polished_candidate(
    *,
    script_path: Path,
    target: Path,
    calibration: Path,
    result: dict,
    int_params: set,
) -> tuple[bool, str]:
    """Materialize optimized source, strictly gate it, then install atomically."""
    import hashlib
    import json as _json
    import shutil as _shutil
    from datetime import datetime, timezone

    from homi.conductor.gate import recompute_metrics
    from homi.conductor.promote import gate_and_promote
    from homi.jee_integration import apply_parameter_values

    project = (
        script_path.parent.parent
        if script_path.parent.name == "output"
        else script_path.parent
    )
    output = project / "output"
    jee_output = script_path.parent / "jee_output"
    best_gds = jee_output / "best_component.gds"
    best_params = result.get("best_params") or {}
    if not best_gds.is_file() or not best_params:
        return False, "optimizer produced no promotable source/GDS pair"

    polished_source = apply_parameter_values(
        script_path.read_text(), best_params, int_params=int_params)
    revision = hashlib.sha256(
        polished_source.encode("utf-8") + best_gds.read_bytes()
    ).hexdigest()[:12]
    candidate = jee_output / f"candidate_{revision}"
    candidate.mkdir(parents=True, exist_ok=True)
    (candidate / "device.py").write_text(polished_source)
    _shutil.copy2(best_gds, candidate / "device.gds")
    _shutil.copy2(target, candidate / "component.png")
    _shutil.copy2(calibration, candidate / "calibration.json")

    metrics = recompute_metrics(
        candidate / "device.gds",
        candidate / "component.png",
        candidate / "calibration.json",
    )
    knob = _polish_knob(project, best_params)
    submission = {
        "claimed_iou": float(metrics["IoU"]),
        "knob": ({"name": knob[0], "width_um": knob[1]} if knob else {}),
        "source": "jee-polish",
        "best_params": best_params,
    }
    (candidate / "submission.json").write_text(
        _json.dumps(submission, indent=1)
    )

    staging = jee_output / f"promotion_{revision}"
    outcome = gate_and_promote(staging, candidate, strict=True)
    if not outcome.promoted:
        reason = "; ".join(outcome.reasons) or "strict gate refused candidate"
        return False, reason

    staged_output = staging / "output"
    record = _json.loads((staged_output / "gate.json").read_text())
    old_gate = {}
    try:
        old_gate = _json.loads((output / "gate.json").read_text())
    except (OSError, ValueError):
        pass
    record.update({
        "source_stage": "polish",
        "revision": revision,
        "baseline_iou": old_gate.get("iou"),
        "optimizer": {
            "method": result.get("method"),
            "baseline_sse": result.get("baseline_sse"),
            "best_sse": result.get("best_sse"),
            "improvement_pct": result.get("improvement_pct"),
            "best_params": best_params,
        },
    })
    (staged_output / "gate.json").write_text(
        _json.dumps(record, indent=1, default=str)
    )

    # Keep the previous promoted record recoverable before installing the new
    # revision.  The gate is replaced last, so observers never treat a partial
    # installation as the new accepted revision.
    if (output / "best.py").is_file() and (output / "best.gds").is_file():
        old_material = (output / "best.py").read_bytes() + (output / "best.gds").read_bytes()
        old_revision = hashlib.sha256(old_material).hexdigest()[:12]
        archive = output / "revisions" / old_revision
        archive.mkdir(parents=True, exist_ok=True)
        for name in ("best.py", "best.gds", "gate.json"):
            source = output / name
            if source.is_file() and not (archive / name).exists():
                _shutil.copy2(source, archive / name)

    installs = {
        "best.py": staged_output / "best.py",
        "best.gds": staged_output / "best.gds",
        "gate.json": staged_output / "gate.json",
    }
    prepared = {}
    for name, source in installs.items():
        temp = output / f".{name}.polish-{revision}.tmp"
        _shutil.copy2(source, temp)
        prepared[name] = temp
    os.replace(prepared["best.py"], output / "best.py")
    os.replace(prepared["best.gds"], output / "best.gds")
    os.replace(prepared["gate.json"], output / "gate.json")

    summary = {
        **result,
        "promoted": True,
        "revision": revision,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
        "gate_iou": outcome.gate.iou,
    }
    summary_tmp = output / "jee_optimization_result.json.tmp"
    summary_tmp.write_text(_json.dumps(summary, indent=1, default=str))
    os.replace(summary_tmp, output / "jee_optimization_result.json")
    return True, f"promoted revision {revision} at IoU {outcome.gate.iou:.4f}"


def cmd_optimize(args):
    """Optimize GDS parameters with JEE."""
    from homi import jee_integration

    script_path = args.script_path.resolve()
    if not script_path.exists():
        print(f"Error: {script_path} not found")
        sys.exit(1)

    target, recorded_calibration, footprint_path = _discover_optimize_inputs(
        script_path, args.target)
    if target is None or not target.exists():
        print("Error: No target image found. Specify with --target")
        sys.exit(1)

    print(f"Script: {script_path}")
    print(f"Target: {target}")
    print(f"Method: {args.method}")

    # Extract parameters — actual function: extract_factory_and_params(script_path: Path)
    # Returns: (factory_fn, param_names, param_bounds, baseline)
    print("\nExtracting parameters...")
    factory_fn, param_names, param_bounds, baseline, int_params = jee_integration.extract_factory_and_params(script_path)
    print(f"  Found {len(param_names)} tunable parameters: {', '.join(param_names)}")
    for name, (lo, hi) in param_bounds.items():
        print(f"    {name}: {baseline[name]:.3f} (bounds: {lo:.3f} - {hi:.3f})")

    # Prepare calibration — signature: (target_image_path: Path, footprint_json_path: Path, output_path: Path)
    calibration_path = recorded_calibration
    if calibration_path is not None:
        print(f"Using recorded calibration: {calibration_path}")
    elif footprint_path:
        calibration_path = script_path.parent / "jee_calibration.json"
        print("Preparing calibration...")
        jee_integration.prepare_calibration(
            Path(target), footprint_path, calibration_path
        )
    else:
        print("Error: No recorded calibration or footprint.json found")
        return 1

    output_dir = script_path.parent / "jee_output"
    output_dir.mkdir(exist_ok=True)

    if args.explore:
        # Signature: (script_path: Path, target_image_path: Path, calibration_path: Path, output_dir: Path, config, callback)
        print("\nRunning exploration (grid search + parallel optimization)...")
        result = jee_integration.run_jee_exploration(
            script_path, Path(target), calibration_path, output_dir
        )
    else:
        # Signature: (script_path: Path, target_image_path: Path, calibration_path: Path, output_dir: Path, config: Dict)
        print(f"\nRunning {args.method} optimization (max {args.max_iterations} iterations)...")
        config = jee_integration.get_jee_default_config()
        config["method"] = "Nelder-Mead" if args.method == "nelder-mead" else "Powell"
        config["max_iterations"] = args.max_iterations
        result = jee_integration.run_jee_optimization(
            script_path, Path(target), calibration_path, output_dir, config
        )

    if result and not result.get("error"):
        improvement = result.get("improvement_pct", 0)
        best_sse = result.get("best_sse", "N/A")
        print("\nOptimization complete.")
        print(f"  SSE improvement: {improvement:.1f}%")
        print(f"  Best SSE: {best_sse}")
        if "best_params" in result:
            print("  Optimized parameters:")
            for k, v in result["best_params"].items():
                orig = baseline.get(k, "?")
                print(f"    {k}: {orig} -> {v:.4f}")
        print(f"  Output: {output_dir}")
        if getattr(args, "promote", False):
            promoted, detail = _promote_polished_candidate(
                script_path=script_path,
                target=Path(target),
                calibration=Path(calibration_path),
                result={**result, "method": args.method},
                int_params=int_params,
            )
            print(f"  Gate: {detail}")
            return 0 if promoted else 1
        return 0
    else:
        detail = result.get("error") if isinstance(result, dict) else None
        print(f"\nOptimization failed{f': {detail}' if detail else '.'}")
        return 1


def cmd_explore(args):
    """Generate the device workbench (default) or the legacy Streamlit explorer."""
    script_path = args.script_path.resolve()
    if not script_path.exists():
        print(f"Error: {script_path} not found")
        sys.exit(1)

    output_dir = args.output or script_path.parent
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    from homi.workbench import generate_workbench

    print(f"Script: {script_path}")
    notebook = generate_workbench(
        script_path, output_dir, draw=getattr(args, "draw", False)
    )
    print(f"  Workbench: {notebook}")
    # marimo lives beside the interpreter running us — works from a
    # checkout .venv AND an installed (uvx/pip) environment alike.
    marimo_bin = Path(sys.executable).parent / "marimo"
    run_cmd = [str(marimo_bin), "run", str(notebook)]
    if args.launch:
        import subprocess

        print("\nServing workbench...")
        subprocess.run(run_cmd, check=False)
    else:
        print(f"\nTo serve: {' '.join(run_cmd)}")
        print(f"To edit:  {marimo_bin} edit {notebook}")
    return


def cmd_simulate(args):
    """Upload GDS to Tidy3D for simulation."""
    from homi import flex_integration
    import gdsfactory as gf

    gds_path = args.gds_path.resolve()
    if not gds_path.exists():
        print(f"Error: {gds_path} not found")
        sys.exit(1)

    # Check Tidy3D availability
    if not flex_integration.is_tidy3d_available():
        print("Error: Tidy3D not available. Install with: pip install tidy3d")
        sys.exit(1)

    import os
    api_key = os.environ.get("TIDY3D_API_KEY")
    if not api_key:
        print("Error: TIDY3D_API_KEY not set")
        sys.exit(1)

    print(f"GDS: {gds_path}")
    print(f"Material: {args.material}")
    print(f"Thickness: {args.thickness} nm")
    print(f"Wavelength: {args.wavelength} um")

    # Load GDS into a gdsfactory Component
    print("\nLoading GDS component...")
    component = gf.import_gds(str(gds_path))

    # create_and_upload_simulation signature: (component: Any, config: Dict, api_key: str)
    config = {
        "material": args.material,
        "thickness_nm": args.thickness,
        "wavelength_um": args.wavelength,
        "layers": [(1, 0)],
    }

    print("Creating and uploading simulation...")
    result = flex_integration.create_and_upload_simulation(component, config, api_key)

    if result and result.get("task_id"):
        print("\nSimulation uploaded successfully.")
        print(f"  Task ID: {result['task_id']}")
        if result.get("web_url"):
            print(f"  Workbench: {result['web_url']}")
        # Upload creates a cloud DRAFT only. Persist that fact where every
        # front door already watches for it; a human still has to press Start.
        project = _manifest_project_for_args(args)
        if project is not None:
            import json as _json
            import os as _os

            draft_dir = Path(project) / "output" / "simulation"
            draft_dir.mkdir(parents=True, exist_ok=True)
            draft = draft_dir / "draft.json"
            payload = {
                "task_id": result["task_id"],
                "url": result.get("web_url"),
                "est_credits": result.get("estimated_cost"),
                "state": "awaiting_human_start",
            }
            tmp = draft.with_suffix(".json.tmp")
            tmp.write_text(_json.dumps(payload, indent=1))
            _os.replace(tmp, draft)
        return 0
    else:
        print("\nSimulation upload failed.")
        return 1


def cmd_benchmark(args):
    """Run multi-model benchmark."""
    sys.argv = ["homi-benchmark"]
    if args.aggregate:
        sys.argv.extend(["--aggregate", str(args.aggregate)])
    else:
        sys.argv.extend(["--papers"] + args.papers)
        if args.families:
            sys.argv.extend(["--families"] + args.families)
        sys.argv.extend(["--phase1-seeds", str(args.phase1_seeds)])
        sys.argv.extend(["--phase1-parallel", str(args.phase1_parallel)])
        sys.argv.extend(["--output-dir", str(args.output_dir)])
        if args.dry_run:
            sys.argv.append("--dry-run")

    from benchmarking.cli import main as bench_main
    bench_main()


def cmd_serve(args):
    """Start MCP servers."""
    import subprocess
    import signal

    all_servers = {
        "mj": "gg.servers.mj_server",
        "michaelangelo": "gg.servers.michaelangelo_server",
        "jee": "gg.servers.jee_server",
        "weber": "gg.servers.weber_server",
        "flex": "gg.servers.flex_server",
        "pdk": "gg.servers.pdk_server",
        "raphael": "gg.servers.raphael_server",
    }

    if args.servers:
        servers = {k: v for k, v in all_servers.items() if k in args.servers}
        unknown = set(args.servers) - set(all_servers.keys())
        if unknown:
            print(f"Unknown servers: {unknown}")
            print(f"Available: {', '.join(all_servers.keys())}")
            sys.exit(1)
    else:
        servers = all_servers

    print(f"Starting {len(servers)} MCP server(s)...")
    processes = []
    for name, module in servers.items():
        print(f"  {name}: python -m {module}")
        proc = subprocess.Popen(
            [sys.executable, "-m", module],
            cwd=str(Path(__file__).parent.parent),
        )
        processes.append((name, proc))

    def shutdown(sig, frame):
        print("\nShutting down servers...")
        for name, proc in processes:
            proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    print(f"\n{len(processes)} servers running. Press Ctrl+C to stop.")

    while True:
        for name, proc in processes:
            ret = proc.poll()
            if ret is not None:
                print(f"  {name} exited with code {ret}")
                shutdown(None, None)
        import time
        time.sleep(1)


def cmd_api(args):
    """Start the REST API server."""
    try:
        import uvicorn
    except ImportError:
        print("Error: uvicorn not installed. Run: pip install 'homi[api]'")
        sys.exit(1)

    print(f"Starting HOMI API on {args.host}:{args.port}")
    print(f"Docs: http://{args.host}:{args.port}/docs")
    uvicorn.run(
        "homi.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


def cmd_migrate(args):
    """Migrate GDS to target PDK — drives the same PDKServer handlers the
    homi-pdk MCP tools use (there is no separate pdk_manager module)."""
    import asyncio
    import json as _json

    from gg.servers.pdk_server import PDKServer

    def unwrap(res):
        # @tool_handler returns MCP [TextContent(json)] — unwrap to the dict.
        if isinstance(res, list):
            return _json.loads(res[0].text)
        return res

    gds_path = args.gds_path.resolve()
    if not gds_path.exists():
        print(f"Error: {gds_path} not found")
        sys.exit(1)

    output_path = args.output or gds_path.parent / f"{gds_path.stem}_{args.target_pdk}.gds"

    print(f"GDS: {gds_path}")
    print(f"Target PDK: {args.target_pdk}")
    print(f"Output: {output_path}")

    srv = PDKServer()

    print("\nConverting layers...")
    result = unwrap(asyncio.run(srv._convert_to_pdk({
        "gds_path": str(gds_path),
        "pdk_name": args.target_pdk,
        "output_path": str(output_path),
    })))
    if result.get("status") == "success":
        print(f"  Converted: {output_path}")
    else:
        print(f"  Conversion failed: {result.get('error', result)}")
        sys.exit(1)

    if args.drc:
        print("\nRunning DRC...")
        drc = unwrap(asyncio.run(srv._run_drc({
            "gds_path": str(output_path),
            "pdk_name": args.target_pdk,
        })))
        violations = drc.get("violations") or []
        if violations:
            print(f"  {len(violations)} DRC violations found:")
            for v in violations[:10]:
                print(f"    - {v}")
        else:
            print("  DRC passed.")


if __name__ == "__main__":
    main()
