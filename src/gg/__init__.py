"""
HOMI MCP - Multi-Agent System for Photonics Design Automation

This package contains:
- servers/: MCP servers providing tools for each domain
- agents/: Agent wrappers with specialized system prompts
- orchestrator/: Pipeline coordination and main orchestrator
- client.py: LLM-driven MCP orchestrator using Claude
- tests/: Import and integration tests

Usage:
    python -m gg paper.pdf -p standard -o ./output
"""

__version__ = "0.1.0"

from gg.client import MCPOrchestrator

__all__ = ["MCPOrchestrator"]
