#!/usr/bin/env python3
"""
Weber - GDSFactory Interactive Explorer Generator

Takes any GDSFactory Python script and generates a full-featured interactive
explorer with parameterization, component swapping, and layer assignment.

Usage:
    python run.py scripts/my_device.py
    python run.py scripts/my_device.py --skip-agent
    python run.py scripts/my_device.py --tidy3d
    python run.py scripts/my_device.py -o my_explorer/
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Weber: Generate interactive explorers from GDSFactory scripts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full AI-powered analysis (requires ANTHROPIC_API_KEY)
  python run.py scripts/my_device.py

  # Skip AI agent, use smart defaults (still has full functionality)
  python run.py scripts/my_device.py --skip-agent

  # Include Tidy3D FDTD simulation panel
  python run.py scripts/my_device.py --tidy3d

  # Custom output directory
  python run.py scripts/my_device.py -o my_explorer/

  # Provide API key directly
  python run.py scripts/my_device.py --api-key sk-...
"""
    )

    parser.add_argument(
        "script",
        help="GDSFactory script to process"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: output/{script_name}_explorer)"
    )
    parser.add_argument(
        "--skip-agent",
        action="store_true",
        help="Skip Claude API, use smart defaults (still has full functionality)"
    )
    parser.add_argument(
        "--tidy3d",
        action="store_true",
        help="Include Tidy3D FDTD simulation integration"
    )
    parser.add_argument(
        "--api-key",
        help="Anthropic API key (or set ANTHROPIC_API_KEY environment variable)"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Don't use cached agent responses"
    )
    parser.add_argument(
        "--name",
        help="Device name (default: derived from script name)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    # Check script exists
    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Error: Script not found: {args.script}")
        sys.exit(1)

    if not script_path.suffix == ".py":
        print(f"Warning: Script does not have .py extension: {args.script}")

    # Import Weber modules
    try:
        from weber.core.analyzer import analyze_script
        from weber.core.default_slots import generate_default_slots
        from weber.core.generator import generate_explorer
        from weber.core.config import get_anthropic_api_key
    except ImportError as e:
        print(f"Error: Failed to import Weber modules: {e}")
        print("Make sure you're running from the Weber directory")
        sys.exit(1)

    # Stage 1: Analyze
    print(f"[1/3] Analyzing {script_path.name}...")
    try:
        analysis = analyze_script(str(script_path))
        if args.verbose:
            print(f"      Found {len(analysis.components)} components")
            print(f"      Found {len(analysis.parameters)} parameters")
            print(f"      Found {len(analysis.functions)} functions")
            if analysis.main_function:
                print(f"      Main function: {analysis.main_function}")
    except Exception as e:
        print(f"Error analyzing script: {e}")
        sys.exit(1)

    # Stage 2: Slot Generation
    if args.skip_agent:
        print("[2/3] Generating slot definitions (smart defaults)...")
        slots = generate_default_slots(analysis)
        if args.verbose:
            print(f"      Generated {len(slots.slots)} slots")
            print(f"      Generated {len(slots.layer_groups)} layer groups")
    else:
        # Check for API key
        api_key = args.api_key or get_anthropic_api_key()
        if not api_key:
            print("Warning: No Anthropic API key found.")
            print("         Set ANTHROPIC_API_KEY or use --api-key, or use --skip-agent")
            print("         Falling back to smart defaults...")
            slots = generate_default_slots(analysis)
        else:
            print("[2/3] Running Claude API slot agent...")
            try:
                from weber.core.slot_agent import SlotAgent
                agent = SlotAgent(api_key=api_key)
                script_source = script_path.read_text()
                slots = agent.analyze(
                    analysis,
                    script_source,
                    use_cache=not args.no_cache
                )
                if args.verbose:
                    print(f"      Generated {len(slots.slots)} slots")
                    print(f"      Generated {len(slots.layer_groups)} layer groups")
                    print(f"      Generated {len(slots.global_params)} global parameters")
            except Exception as e:
                print(f"Warning: Agent failed: {e}")
                print("         Falling back to smart defaults...")
                slots = generate_default_slots(analysis)

    # Stage 3: Generate Explorer
    output_dir = args.output
    if output_dir is None:
        output_dir = f"output/{script_path.stem}_explorer"

    print(f"[3/3] Generating explorer in {output_dir}...")
    try:
        result_path = generate_explorer(
            script_path=str(script_path),
            slots=slots,
            output_dir=output_dir,
            include_tidy3d=args.tidy3d,
            device_name=args.name
        )

        print()
        print("=" * 60)
        print("Done! Your explorer has been generated.")
        print("=" * 60)
        print()
        print(f"Run with:")
        print(f"  streamlit run {result_path}/app.py")
        print()
        print("Generated files:")
        for f in sorted(result_path.iterdir()):
            print(f"  - {f.name}")

    except Exception as e:
        print(f"Error generating explorer: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
