"""
orchestration
=============

Master Agent and state-machine layer for the Loan Application Chatbot.

Public API
----------
::

    from backend.orchestration import MasterAgent

    agent = MasterAgent()
    envelope = await agent.handle_message("session-123", "Hi, I need a loan")
    print(envelope.to_dict())
"""

from backend.orchestration.master_agent import MasterAgent, ResponseEnvelope
from backend.orchestration.state_machine import (
    HAPPY_PATH,
    LoanState,
    SessionData,
    StateMachine,
    STAGE_AGENT_MAP,
    STATE_VALIDATORS,
    TRANSITIONS,
)

__all__ = [
    "MasterAgent",
    "ResponseEnvelope",
    "HAPPY_PATH",
    "LoanState",
    "SessionData",
    "StateMachine",
    "STAGE_AGENT_MAP",
    "STATE_VALIDATORS",
    "TRANSITIONS",
]
