"""
graph.py
========

LangGraph implementation of the loan application workflow.

This module replaces the manual orchestration logic in ``MasterAgent`` with a 
declarative state graph. It wraps the existing deterministic agents as graph nodes.
"""

from typing import Dict, Any, Literal

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from backend.orchestration.graph_state import AgentState
from backend.orchestration.state_machine import LoanState, STAGE_AGENT_MAP
from backend.agents.sales_agent import SalesAgent
from backend.agents.verification_agent import VerificationAgent
from backend.agents.underwriting_agent import UnderwritingAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.sanction_agent import SanctionAgent

# ── Initialise Agents ────────────────────────────────────────────────────────
# We use singletons here as the agents are stateless (they rely on passed context)
_agents = {
    "sales": SalesAgent(),
    "verification": VerificationAgent(),
    "underwriting": UnderwritingAgent(),
    "document": DocumentAgent(),
    "sanction": SanctionAgent(),
}

# ── Node Functions ───────────────────────────────────────────────────────────

async def run_sales_agent(state: AgentState) -> Dict[str, Any]:
    return await _run_agent("sales", state)

async def run_verification_agent(state: AgentState) -> Dict[str, Any]:
    return await _run_agent("verification", state)

async def run_underwriting_agent(state: AgentState) -> Dict[str, Any]:
    return await _run_agent("underwriting", state)

async def run_document_agent(state: AgentState) -> Dict[str, Any]:
    return await _run_agent("document", state)

async def run_sanction_agent(state: AgentState) -> Dict[str, Any]:
    return await _run_agent("sanction", state)

async def _run_agent(agent_key: str, state: AgentState) -> Dict[str, Any]:
    """Generic wrapper to run a worker agent and update state."""
    agent = _agents[agent_key]
    
    # Extract latest user message
    user_msg = state["messages"][-1].content if state["messages"] else ""
    session_id = state["session_id"]
    
    # Build context from state
    context = {
        "state": state["current_stage"].value,
        **state["collected_data"]
    }

    # Run agent
    result = await agent.safe_process(session_id, user_msg, context)
    
    updates = {}
    if result.success:
        # Update collected data
        if result.data:
            state["collected_data"].update(result.data)
            updates["collected_data"] = state["collected_data"] # Return full updated dict or rely on merger? 
            # TypedDict doesn't auto-merge deep dicts, so we overwrite for safety in this simple implementation
        
        # Add agent response to history
        updates["messages"] = [AIMessage(content=result.message)]
    else:
        updates["error"] = "; ".join(result.errors)
        updates["messages"] = [AIMessage(content=f"Error: {result.message}")]

    return updates

# ── Router Logic ─────────────────────────────────────────────────────────────

def route_by_stage(state: AgentState) -> Literal["sales", "verification", "underwriting", "document", "sanction", "__end__"]:
    """Determine which agent node to run based on the current stage."""
    stage = state["current_stage"]
    
    # Map stage to agent key
    agent_key = STAGE_AGENT_MAP.get(stage)
    
    if not agent_key:
        return END
        
    # Return the name of the node (must match add_node names below)
    return agent_key

# ── Graph Construction ───────────────────────────────────────────────────────

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("sales", run_sales_agent)
workflow.add_node("verification", run_verification_agent)
workflow.add_node("underwriting", run_underwriting_agent)
workflow.add_node("document", run_document_agent)
workflow.add_node("sanction", run_sanction_agent)

# Add conditional entry point
# The graph starts by checking the stage and routing to the right agent
workflow.set_conditional_entry_point(
    route_by_stage,
    {
        "sales": "sales",
        "verification": "verification",
        "underwriting": "underwriting",
        "document": "document",
        "sanction": "sanction",
        END: END
    }
)

# All agents return to END (single-turn execution)
# The MasterAgent loop handles the multi-turn aspect
workflow.add_edge("sales", END)
workflow.add_edge("verification", END)
workflow.add_edge("underwriting", END)
workflow.add_edge("document", END)
workflow.add_edge("sanction", END)

# Compile
app = workflow.compile()
