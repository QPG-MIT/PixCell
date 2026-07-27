"""
HOMI MCP Client - LLM-Driven Orchestration

Connects Claude to MCP servers for intelligent paper-to-GDS pipeline execution.
Claude reads the orchestrator system prompt, has access to all MCP tools,
and progressively calls them to process papers.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from gg.orchestrator.orchestrator import ORCHESTRATOR_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# Server configurations
SERVERS = {
    "homi-mj": {
        "module": "gg.servers.mj_server",
        "description": "Paper processing and image extraction"
    },
    "homi-michaelangelo": {
        "module": "gg.servers.michaelangelo_server",
        "description": "GDS generation from images"
    },
    "homi-jee": {
        "module": "gg.servers.jee_server",
        "description": "GDS parameter optimization"
    },
    "homi-weber": {
        "module": "gg.servers.weber_server",
        "description": "Interactive explorer generation"
    },
    "homi-flex": {
        "module": "gg.servers.flex_server",
        "description": "Tidy3D FDTD simulation"
    },
    "homi-pdk": {
        "module": "gg.servers.pdk_server",
        "description": "Foundry PDK mapping"
    },
}


class MCPOrchestrator:
    """
    LLM-driven orchestrator that uses Claude to coordinate MCP tools.

    Launches MCP servers, collects their tools, and lets Claude
    decide which tools to call to process papers.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        servers: Optional[List[str]] = None
    ):
        """
        Initialize the MCP orchestrator.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            servers: List of server names to start (defaults to all)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        self.model = model
        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.server_names = servers or list(SERVERS.keys())

        # Will be populated when servers start
        self._server_sessions: Dict[str, ClientSession] = {}
        self._tools: List[Dict[str, Any]] = []
        self._tool_to_server: Dict[str, str] = {}

    async def start_servers(self) -> None:
        """Start all configured MCP servers and collect their tools."""
        logger.info(f"Starting {len(self.server_names)} MCP servers...")

        python_path = sys.executable
        homi_root = Path(__file__).parent.parent

        for server_name in self.server_names:
            if server_name not in SERVERS:
                logger.warning(f"Unknown server: {server_name}")
                continue

            server_config = SERVERS[server_name]
            module = server_config["module"]

            logger.info(f"Starting {server_name}...")

            try:
                # Create server parameters
                server_params = StdioServerParameters(
                    command=python_path,
                    args=["-m", module],
                    cwd=str(homi_root),
                    env={**os.environ}
                )

                # Connect to server
                read, write = await stdio_client(server_params).__aenter__()
                session = ClientSession(read, write)
                await session.__aenter__()

                # Initialize and get tools
                await session.initialize()
                tools_response = await session.list_tools()

                # Store session and tools
                self._server_sessions[server_name] = session

                for tool in tools_response.tools:
                    # Convert MCP tool to Claude format
                    claude_tool = {
                        "name": f"{server_name}__{tool.name}",  # Prefix with server name
                        "description": f"[{server_name}] {tool.description}",
                        "input_schema": tool.inputSchema
                    }
                    self._tools.append(claude_tool)
                    self._tool_to_server[claude_tool["name"]] = server_name

                logger.info(f"  {server_name}: {len(tools_response.tools)} tools")

            except Exception as e:
                logger.error(f"Failed to start {server_name}: {e}")

        logger.info(f"Total tools available: {len(self._tools)}")

    async def stop_servers(self) -> None:
        """Stop all running MCP servers."""
        for server_name, session in self._server_sessions.items():
            try:
                await session.__aexit__(None, None, None)
                logger.info(f"Stopped {server_name}")
            except Exception as e:
                logger.warning(f"Error stopping {server_name}: {e}")

        self._server_sessions.clear()

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call an MCP tool and return its result.

        Args:
            tool_name: Full tool name (server__tool format)
            arguments: Tool arguments

        Returns:
            Tool result
        """
        server_name = self._tool_to_server.get(tool_name)
        if not server_name:
            return {"error": f"Unknown tool: {tool_name}"}

        session = self._server_sessions.get(server_name)
        if not session:
            return {"error": f"Server not running: {server_name}"}

        # Extract actual tool name (remove server prefix)
        actual_tool_name = tool_name.split("__", 1)[1]

        try:
            result = await session.call_tool(actual_tool_name, arguments)

            # Parse result
            if result.content and len(result.content) > 0:
                text = result.content[0].text
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"result": text}

            return {"result": "Tool completed with no output"}

        except Exception as e:
            logger.error(f"Tool call failed: {tool_name}: {e}")
            return {"error": str(e)}

    async def run(
        self,
        pdf_path: str,
        output_dir: str = "./output",
        pipeline_type: str = "standard",
        footprint: Optional[Dict[str, float]] = None,
        max_turns: int = 50
    ) -> Dict[str, Any]:
        """
        Run the full pipeline with Claude as orchestrator.

        Args:
            pdf_path: Path to research paper PDF
            output_dir: Directory for outputs
            pipeline_type: Pipeline type (quick, standard, full, simulation)
            footprint: Optional device footprint {length_um, width_um}
            max_turns: Maximum conversation turns

        Returns:
            Final results dict
        """
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Build initial user message
        user_content = f"""Process this research paper and generate a fabrication-ready GDS design.

**Input:**
- PDF Path: {pdf_path}
- Output Directory: {output_dir}
- Pipeline Type: {pipeline_type}
"""
        if footprint:
            user_content += f"- Footprint: {footprint['length_um']} x {footprint['width_um']} μm\n"

        user_content += """
**Instructions:**
1. Start by extracting device images from the paper using MJ tools
2. Generate GDS from the best device image using Michaelangelo tools
3. Optimize the GDS parameters using JEE tools
4. Generate an interactive explorer using Weber tools
5. Report final results with paths and metrics

Use the appropriate tools for each stage. Handle errors gracefully and report progress.
"""

        messages = [{"role": "user", "content": user_content}]

        logger.info(f"Starting pipeline: {pipeline_type}")
        logger.info(f"PDF: {pdf_path}")
        logger.info(f"Output: {output_dir}")

        # Main conversation loop
        for turn in range(max_turns):
            logger.info(f"Turn {turn + 1}/{max_turns}")

            # Call Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                tools=self._tools,
                messages=messages
            )

            # Process response
            assistant_content = response.content
            messages.append({"role": "assistant", "content": assistant_content})

            # Check if done
            if response.stop_reason == "end_turn":
                logger.info("Pipeline completed")
                # Extract final text response
                final_text = ""
                for block in assistant_content:
                    if hasattr(block, "text"):
                        final_text += block.text
                return {
                    "success": True,
                    "message": final_text,
                    "turns": turn + 1
                }

            # Handle tool use
            if response.stop_reason == "tool_use":
                tool_results = []

                for block in assistant_content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_id = block.id

                        logger.info(f"Calling tool: {tool_name}")

                        # Execute tool
                        result = await self.call_tool(tool_name, tool_input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result, indent=2)
                        })

                # Add tool results to conversation
                messages.append({"role": "user", "content": tool_results})
            else:
                # Unexpected stop reason
                logger.warning(f"Unexpected stop reason: {response.stop_reason}")
                break

        return {
            "success": False,
            "message": "Max turns reached",
            "turns": max_turns
        }

    async def __aenter__(self):
        await self.start_servers()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_servers()


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="HOMI MCP Orchestrator - LLM-driven paper-to-GDS pipeline"
    )
    parser.add_argument("pdf_path", help="Path to research paper PDF")
    parser.add_argument("-o", "--output", default="./output", help="Output directory")
    parser.add_argument(
        "-p", "--pipeline",
        choices=["quick", "standard", "full", "simulation"],
        default="standard",
        help="Pipeline type"
    )
    parser.add_argument("--length", type=float, help="Device length in μm")
    parser.add_argument("--width", type=float, help="Device width in μm")
    parser.add_argument("--model", default="claude-sonnet-4-20250514", help="Claude model")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )

    # Build footprint if provided
    footprint = None
    if args.length and args.width:
        footprint = {"length_um": args.length, "width_um": args.width}

    # Run orchestrator
    async with MCPOrchestrator(model=args.model) as orchestrator:
        result = await orchestrator.run(
            pdf_path=args.pdf_path,
            output_dir=args.output,
            pipeline_type=args.pipeline,
            footprint=footprint
        )

    # Print result
    print("\n" + "=" * 60)
    print("HOMI Pipeline Result")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"Turns: {result['turns']}")
    print(f"\n{result['message']}")


if __name__ == "__main__":
    asyncio.run(main())
