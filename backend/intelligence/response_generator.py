"""
response_generator.py
=====================

LLM-powered response synthesis for the Agentic Lending Platform.

Responsibilities
----------------
- Accept the agent result, detected intent, and session context.
- Compose a natural-language response by combining:
  • Canned templates from ``templates.response_messages``.
  • Dynamic data from agent results (e.g., EMI figures, eligibility status).
  • LLM generation for free-form or follow-up answers.
- Return a formatted string ready for the frontend.

Design Notes
------------
- Template-first approach: prefer deterministic templates for compliance-
  sensitive stages; use LLM only for conversational polish.
- All LLM calls go through the configured provider in ``config.settings``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def generate(
    agent_message: str,
    context: Dict[str, Any],
    use_llm: bool = False,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Produce the final user-facing response.

    Parameters
    ----------
    agent_message : str
        The raw message produced by the worker agent.
    context : dict
        Session context containing user profile, state, history, etc.
    use_llm : bool
        Whether to enhance the response with an LLM call.
    system_prompt : str or None
        Optional system prompt override for the LLM.

    Returns
    -------
    str
        The final formatted response string.

    TODO
    ----
    - Fetch matching template from ``response_messages`` if available.
    - If ``use_llm`` is True, call the LLM API to polish / extend.
    - Apply any compliance disclaimers required for the current stage.
    """
    logger.info("Generating response | use_llm=%s", use_llm)

    # Placeholder — return the agent message as-is
    return agent_message
