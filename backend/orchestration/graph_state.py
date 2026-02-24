"""
graph_state.py
==============

Defines the state schema for the LangGraph orchestration.
"""

from typing import Annotated, Any, Dict, List, TypedDict, Union
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from backend.orchestration.state_machine import LoanState

class AgentState(TypedDict):
    """
    Represents the state of the loan application agent.
    
    Attributes
    ----------
    session_id : str
        The unique ID of the session.
    messages : List[BaseMessage]
        Chat history (LangGraph standard).
    current_stage : LoanState
        The current stage in the 14-step loan journey.
    next_stage : LoanState
        The target stage to transition to.
    collected_data : Dict[str, Any]
        Aggregated data collected from the user (income, pan, etc.).
    error : str
        Error message if validation fails.
    """
    session_id: str
    messages: Annotated[List[BaseMessage], add_messages]
    current_stage: LoanState
    next_stage: LoanState
    collected_data: Dict[str, Any]
    error: str
