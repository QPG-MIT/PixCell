"""
Base MCP Server class with common patterns for HOMI agents.

Provides:
- Tool registration helpers
- Error handling wrappers
- JSON serialization utilities
- Async task management for long-running operations
"""

from __future__ import annotations

import asyncio
import json
import logging
import traceback
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, TypeVar

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Status of an async task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AsyncTask:
    """Tracks a long-running async task."""
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    message: str
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        now = datetime.utcnow().isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for HOMI types."""

    def default(self, obj: Any) -> Any:
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if hasattr(obj, "__dict__"):
            return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        return super().default(obj)


def serialize_result(result: Any) -> str:
    """Serialize a result to JSON string."""
    return json.dumps(result, cls=JSONEncoder, indent=2)


def tool_handler(func: Callable) -> Callable:
    """
    Decorator for tool handlers that provides:
    - Automatic error handling
    - Result serialization
    - Logging
    """
    async def wrapper(self, arguments: Dict[str, Any]) -> List[TextContent]:
        tool_name = func.__name__
        logger.info(f"Tool called: {tool_name} with args: {arguments}")

        try:
            # Call the actual handler
            if asyncio.iscoroutinefunction(func):
                result = await func(self, arguments)
            else:
                result = func(self, arguments)

            # Serialize result
            if isinstance(result, str):
                content = result
            else:
                content = serialize_result(result)

            logger.info(f"Tool {tool_name} completed successfully")
            return [TextContent(type="text", text=content)]

        except Exception as e:
            error_msg = f"Error in {tool_name}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return [TextContent(
                type="text",
                text=serialize_result({
                    "status": "error",
                    "error": str(e),
                    "tool": tool_name,
                    "traceback": traceback.format_exc()
                })
            )]

    # Preserve function metadata
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


class BaseMCPServer(ABC):
    """
    Base class for HOMI MCP servers.

    Subclasses should:
    1. Define server_name and server_version
    2. Implement get_tools() to return tool definitions
    3. Implement handle_tool() to dispatch tool calls
    """

    server_name: str = "homi-base"
    server_version: str = "0.1.0"

    def __init__(self):
        self.server = Server(self.server_name)
        self._tasks: Dict[str, AsyncTask] = {}
        self._task_futures: Dict[str, asyncio.Future] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        """Set up MCP protocol handlers."""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return self.get_tools()

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            return await self.handle_tool(name, arguments)

    @abstractmethod
    def get_tools(self) -> List[Tool]:
        """Return list of tools this server provides."""
        pass

    @abstractmethod
    async def handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle a tool call."""
        pass

    # --- Async Task Management ---

    def create_task(self, message: str = "Starting...") -> str:
        """Create a new async task and return its ID."""
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = AsyncTask(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=0.0,
            message=message
        )
        return task_id

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ):
        """Update an async task's status."""
        if task_id not in self._tasks:
            raise ValueError(f"Unknown task: {task_id}")

        task = self._tasks[task_id]
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        if message is not None:
            task.message = message
        if result is not None:
            task.result = result
        if error is not None:
            task.error = error
        task.updated_at = datetime.utcnow().isoformat()

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get an async task by ID."""
        return self._tasks.get(task_id)

    def start_background_task(
        self,
        task_id: str,
        coro: asyncio.coroutine
    ) -> None:
        """Start a background task."""
        self.update_task(task_id, status=TaskStatus.RUNNING)

        async def run_task():
            try:
                result = await coro
                self.update_task(
                    task_id,
                    status=TaskStatus.COMPLETED,
                    progress=1.0,
                    result=result,
                    message="Completed"
                )
            except Exception as e:
                self.update_task(
                    task_id,
                    status=TaskStatus.FAILED,
                    error=str(e),
                    message=f"Failed: {e}"
                )

        future = asyncio.create_task(run_task())
        self._task_futures[task_id] = future

    # --- Server Lifecycle ---

    async def run(self):
        """Run the MCP server."""
        logger.info(f"Starting {self.server_name} v{self.server_version}")

        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
