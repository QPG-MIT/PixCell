"""
HOMI MCP Orchestrator CLI

Usage:
    python -m gg paper.pdf -p standard -o ./output
"""

import asyncio
from gg.client import main

if __name__ == "__main__":
    asyncio.run(main())
