"""
Base Agent class for HOMI sub-agents.

Each agent:
1. Has a specialized system prompt defining its role
2. Has access to its MCP server's tools
3. Can execute tools and handle errors
4. Reports results back to the orchestrator
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    """Status of an agent's response."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some work done but not complete
    FAILED = "failed"
    NEEDS_INPUT = "needs_input"  # Needs clarification from orchestrator


@dataclass
class AgentResponse:
    """Response from an agent to the orchestrator."""
    status: AgentStatus
    message: str
    result: Optional[Any] = None
    error: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    next_steps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "suggestions": self.suggestions,
            "metrics": self.metrics,
            "next_steps": self.next_steps
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class BaseAgent(ABC):
    """
    Base class for HOMI agents.

    Subclasses must implement:
    - name: The agent's identifier
    - system_prompt: The agent's system prompt
    - execute(): Main execution logic
    """

    name: str = "base-agent"
    mcp_server_name: str = "homi-base"

    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """Return the agent's system prompt."""
        pass

    @abstractmethod
    async def execute(self, task: str, context: Dict[str, Any]) -> AgentResponse:
        """
        Execute a task.

        Args:
            task: Description of what to do
            context: Additional context (file paths, previous results, etc.)

        Returns:
            AgentResponse with results or error information
        """
        pass

    def _make_success(
        self,
        message: str,
        result: Any = None,
        metrics: Dict[str, Any] = None,
        next_steps: List[str] = None
    ) -> AgentResponse:
        """Helper to create a success response."""
        return AgentResponse(
            status=AgentStatus.SUCCESS,
            message=message,
            result=result,
            metrics=metrics or {},
            next_steps=next_steps or []
        )

    def _make_partial(
        self,
        message: str,
        result: Any = None,
        suggestions: List[str] = None
    ) -> AgentResponse:
        """Helper to create a partial success response."""
        return AgentResponse(
            status=AgentStatus.PARTIAL,
            message=message,
            result=result,
            suggestions=suggestions or []
        )

    def _make_error(
        self,
        error: str,
        suggestions: List[str] = None
    ) -> AgentResponse:
        """Helper to create an error response."""
        return AgentResponse(
            status=AgentStatus.FAILED,
            message=f"Failed: {error}",
            error=error,
            suggestions=suggestions or []
        )

    def _make_needs_input(
        self,
        message: str,
        options: List[str] = None
    ) -> AgentResponse:
        """Helper to request input from orchestrator."""
        return AgentResponse(
            status=AgentStatus.NEEDS_INPUT,
            message=message,
            suggestions=options or []
        )
