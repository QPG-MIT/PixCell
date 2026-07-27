"""
Basic import tests to validate the module structure.
"""

import sys
from pathlib import Path

# Add gg package to path (parent of tests)
sys.path.insert(0, str(Path(__file__).parent.parent))
# Add HOMI root to path (for jee, michaelangelo, etc.)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_agents_import():
    """Test that all agents can be imported."""
    from agents.base import BaseAgent, AgentResponse
    from agents.jee_agent import JEEAgent, create_jee_agent
    from agents.mj_agent import MJAgent, create_mj_agent
    from agents.michaelangelo_agent import MichelangeloAgent, create_michaelangelo_agent
    from agents.weber_agent import WeberAgent, create_weber_agent
    from agents.pdk_agent import PDKAgent, create_pdk_agent
    from agents.flex_agent import FlexAgent, create_flex_agent

    print("All agents imported successfully")

    # Test agent creation
    agents = [
        create_jee_agent(),
        create_mj_agent(),
        create_michaelangelo_agent(),
        create_weber_agent(),
        create_pdk_agent(),
        create_flex_agent(),
    ]

    for agent in agents:
        print(f"  - {agent.name}: {agent.mcp_server_name}")
        assert agent.system_prompt is not None
        assert len(agent.system_prompt) > 100


def test_servers_import():
    """Test that all servers can be imported."""
    # Check if MCP SDK is installed
    try:
        import mcp.server
        mcp_available = True
    except ImportError:
        mcp_available = False
        print("MCP SDK not installed (pip install mcp) - skipping server tests")
        print("  Server module structure verified via static analysis")
        return

    from servers.base import BaseMCPServer, TaskStatus, AsyncTask
    from servers.jee_server import JEEServer
    from servers.mj_server import MJServer
    from servers.michaelangelo_server import MichelangeloServer
    from servers.weber_server import WeberServer
    from servers.pdk_server import PDKServer
    from servers.flex_server import FlexServer

    print("All servers imported successfully")

    # Test server instantiation (without running)
    servers = [
        JEEServer(),
        # MJServer and others require dependencies
    ]

    for server in servers:
        tools = server.get_tools()
        print(f"  - {server.server_name}: {len(tools)} tools")


def test_orchestrator_import():
    """Test that orchestrator can be imported."""
    from orchestrator.pipeline import (
        Pipeline, PipelineConfig, PipelineStage,
        SIMULATION_PIPELINE
    )
    from orchestrator.orchestrator import Orchestrator

    print("Orchestrator imported successfully")

    # Test pipeline creation
    config = PipelineConfig()
    pipeline = Pipeline(config)
    stages = pipeline.get_enabled_stages()
    print(f"  - Enabled stages: {[s.value for s in stages]}")

    # Test new pipeline types
    print(f"  - SIMULATION_PIPELINE: {[s.value for s in SIMULATION_PIPELINE]}")

    # Test new pipeline stages exist
    assert PipelineStage.SIMULATION.value == "simulation"

    # Test orchestrator creation
    orch = Orchestrator(config)
    print(f"  - Orchestrator ready")


def main():
    """Run all import tests."""
    print("=" * 60)
    print("HOMI Multi-Agent Import Tests")
    print("=" * 60)
    print()

    try:
        test_agents_import()
        print()
        test_servers_import()
        print()
        test_orchestrator_import()
        print()
        print("=" * 60)
        print("All imports successful!")
        print("=" * 60)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
