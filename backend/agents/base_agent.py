"""
base_agent.py
=============

Abstract base class for all worker agents in the lending platform.

Responsibilities
----------------
- Define the ``process()`` contract that every worker agent must implement.
- Provide shared hooks for logging, error boundaries, and metric emission.
- Enforce a consistent response envelope across all agents.

Design Notes
------------
- Each agent receives a session context dict that the Master Agent assembles.
- The ``process()`` method should return an ``AgentResult`` dataclass so that
  the orchestration layer can uniformly aggregate outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from backend.utils.logger import get_logger


@dataclass
class AgentResult:
    """
    Standardised result envelope returned by every worker agent.

    Attributes
    ----------
    success : bool
        Whether the agent completed its task without errors.
    message : str
        Human-readable summary of the outcome.
    data : dict
        Arbitrary key-value payload (e.g. extracted fields, decisions).
    next_state : str or None
        Suggested next state for the state machine (``None`` = stay in current).
    errors : list[str]
        List of error descriptions if ``success`` is False.
    """

    success: bool = True
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    next_state: Optional[str] = None
    errors: list = field(default_factory=list)


class BaseAgent(ABC):
    """
    Abstract base class for domain-specific worker agents.

    Subclasses must implement :meth:`process`.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = get_logger(f"agent.{name}")

    @abstractmethod
    async def process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """
        Execute the agent's domain-specific logic.

        Parameters
        ----------
        session_id : str
            Unique session / application identifier.
        user_message : str
            Raw text input from the user.
        context : dict
            Shared session context assembled by the Master Agent.

        Returns
        -------
        AgentResult
            Standardised outcome envelope.
        """
        ...

    async def safe_process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """
        Error-boundary wrapper around :meth:`process`.

        Catches any exception, logs it, and returns a failed ``AgentResult``
        instead of propagating the error up to the orchestration layer.
        """
        try:
            self.logger.info("Processing | session=%s", session_id)
            result = await self.process(session_id, user_message, context)
            self.logger.info("Completed  | session=%s success=%s", session_id, result.success)
            return result
        except Exception as exc:
            self.logger.exception("Unhandled error in %s | session=%s", self.name, session_id)
            return AgentResult(
                success=False,
                message=f"Agent '{self.name}' encountered an internal error.",
                errors=[str(exc)],
            )
