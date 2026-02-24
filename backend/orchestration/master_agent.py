"""
master_agent.py
===============

Production Master Agent for the 14-stage Loan Application Chatbot.

Orchestrates session management, intent detection, agent routing,
validation-gated state advancement, and unexpected-input resilience.

See ``state_machine.py`` for the full state definitions and validators.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from backend.agents.base_agent import AgentResult, BaseAgent
from backend.agents.sales_agent import SalesAgent
from backend.agents.verification_agent import VerificationAgent
from backend.agents.underwriting_agent import UnderwritingAgent
from backend.agents.document_agent import DocumentAgent
from backend.agents.sanction_agent import SanctionAgent
from backend.intelligence import intent_detector
from backend.intelligence.gemini_client import maybe_use_ai
from backend.orchestration.state_machine import (
    HAPPY_PATH,
    LoanState,
    SessionData,
    StateMachine,
    STAGE_AGENT_MAP,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Response Envelope
# ═══════════════════════════════════════════════════════════════════════════

class ResponseEnvelope:
    """Unified response returned to the frontend / API caller."""

    __slots__ = (
        "response", "state", "session_id", "data",
        "validation_error", "suggestions", "progress", "metadata",
    )

    def __init__(
        self,
        response: str,
        state: str,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        validation_error: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        progress: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.response = response
        self.state = state
        self.session_id = session_id
        self.data = data or {}
        self.validation_error = validation_error or ""
        self.suggestions = suggestions or []
        self.progress = progress or {}
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in self.__slots__}


# ═══════════════════════════════════════════════════════════════════════════
# Global Commands
# ═══════════════════════════════════════════════════════════════════════════

_RESTART = {"restart", "start over", "reset", "begin again", "new application"}
_STATUS  = {"status", "where am i", "current stage", "progress"}
_HELP    = {"help", "what can you do", "options", "menu"}
_QUIT    = {"quit", "exit", "cancel", "bye", "goodbye", "stop"}


# ═══════════════════════════════════════════════════════════════════════════
# Stage Prompts  (what the bot says when entering each state)
# ═══════════════════════════════════════════════════════════════════════════

STAGE_PROMPTS: Dict[LoanState, str] = {
    LoanState.GREETING:
        "Hello! 👋 Welcome to Tata Capital. I'm your AI lending assistant.\n"
        "To begin, may I know your **full name**?",
    LoanState.PURPOSE:
        "What type of loan are you looking for?\n"
        "Options: **Personal** · **Home** · **Auto** · **Business** · **Education** · **Gold**",
    LoanState.LOAN_AMOUNT:
        "How much loan amount do you need? (₹10,000 – ₹5 Cr)",
    LoanState.EMPLOYMENT:
        "Tell me about your employment:\n"
        "• Type: **Salaried** / **Self-employed** / **Business** / **Professional**\n"
        "• Employer or business name",
    LoanState.PHONE_VERIFICATION:
        "Please provide your **10-digit mobile number**. We'll send an OTP for verification.",
    LoanState.PAN_VERIFICATION:
        "Please enter your **PAN number** (e.g., ABCDE1234F) for identity verification.",
    LoanState.INCOME:
        "What is your **monthly net income** (₹)?",
    LoanState.LIABILITIES:
        "Do you have any **existing EMIs or liabilities**?\n"
        "If yes, please enter the total monthly EMI amount. If none, type **0**.",
    LoanState.CREDIT_CHECK:
        "Hang tight ⏳ — I'm running your credit check. This takes a few moments…",
    LoanState.OFFER_PRESENTATION:
        "🎉 Great news! Here are your personalised loan offers. Review them below.",
    LoanState.TENURE_SELECTION:
        "Select a **loan tenure** (in months):\n"
        "12 · 24 · 36 · 48 · 60 · 84 · 120 · 180 · 240 · 360",
    LoanState.DECISION:
        "Please review the final terms and **accept** or **reject** the offer.",
    LoanState.DOCUMENT_UPLOAD:
        "Please upload the following documents:\n"
        "1️⃣ ID Proof  2️⃣ Address Proof  3️⃣ Income Proof",
    LoanState.SANCTION:
        "✅ Congratulations! Your loan has been **sanctioned**. "
        "The sanction letter is being prepared.",
    LoanState.ERROR:
        "Something went wrong. Type **restart** to begin a new application.",
    LoanState.ABANDONED:
        "Your session was closed. Type **restart** whenever you'd like to return. 👋",
}


# ═══════════════════════════════════════════════════════════════════════════
# Master Agent
# ═══════════════════════════════════════════════════════════════════════════

class MasterAgent:
    """
    Central orchestrator for the 14-stage loan chatbot.

    Call ``handle_message(session_id, text)`` for every user turn.
    """

    def __init__(self) -> None:
        self.sm = StateMachine()
        self._agents: Dict[str, BaseAgent] = {
            "sales":        SalesAgent(),
            "verification": VerificationAgent(),
            "underwriting": UnderwritingAgent(),
            "document":     DocumentAgent(),
            "sanction":     SanctionAgent(),
        }

    # ── Public entry point ──────────────────────────────────────────────

    async def handle_message(self, session_id: str, user_message: str) -> ResponseEnvelope:
        """Process a single user message end-to-end."""
        t0 = time.perf_counter()
        session = self.sm.get_or_create(session_id)
        state = session.state

        logger.info("handle | session=%s state=%s msg=%s", session_id, state.value, user_message[:80])

        # ── 1. Global commands ──────────────────────────────────────────
        gcmd = self._global_command(session, user_message)
        if gcmd:
            gcmd.metadata["latency_ms"] = _ms(t0)
            return gcmd

        # ── 2. Terminal state guard ─────────────────────────────────────
        if state == LoanState.SANCTION:
            return self._envelope(session, STAGE_PROMPTS[LoanState.SANCTION], latency=t0)
        if state in (LoanState.ERROR, LoanState.ABANDONED):
            return self._envelope(
                session,
                STAGE_PROMPTS.get(state, "Type **restart** to begin again."),
                suggestions=["restart"],
                latency=t0,
            )

        # ── 3. Detect intent ───────────────────────────────────────────
        intent = await intent_detector.detect(user_message)

        # ── 4. LangGraph Execution ─────────────────────────────────────
        # We now delegate the agent execution to the LangGraph application.
        # This satisfies the "Agentic AI Framework" requirement while keeping
        # our deterministic StateMachine as the comprehensive guardrail.

        from langchain_core.messages import HumanMessage
        from backend.orchestration.graph import app

        # Build initial graph state
        graph_input = {
            "session_id": session_id,
            "current_stage": state,
            "collected_data": session.collected_data,
            "messages": [HumanMessage(content=user_message)],
        }

        # Execute graph (runs the appropriate agent node based on stage)
        # Note: We await ainvoke() because the graph nodes are async
        graph_output = await app.ainvoke(graph_input)

        # Extract results
        ai_messages = graph_output.get("messages", [])
        response_text = ai_messages[-1].content if ai_messages else "I'm not sure how to respond."
        updated_data = graph_output.get("collected_data", {})
        error_msg = graph_output.get("error")

        # ── 6. Handle agent failure ────────────────────────────────────
        if error_msg:
            retries = self.sm.record_retry(session_id)
            session = self.sm.get_or_create(session_id)
            return self._envelope(
                session,
                response_text or "That didn't work. Please try again.",
                validation_error=error_msg,
                suggestions=["help"],
                metadata={"agent": STAGE_AGENT_MAP.get(state), "retries": retries},
                latency=t0,
            )

        # ── 7. Merge collected data ────────────────────────────────────
        if updated_data:
            self.sm.update_data(session_id, updated_data)

        # ── 8. Validate & advance ──────────────────────────────────────
        advanced, adv_msg = self.sm.advance(session_id)
        session = self.sm.get_or_create(session_id)  # refresh

        if advanced:
            nudge = STAGE_PROMPTS.get(session.state, "")
            if nudge:
                response_text = f"{response_text}\n\n{nudge}"

        if not advanced and adv_msg:
            # Validation blocked advancement — tell the user what's missing
            validation_error = adv_msg
        else:
            validation_error = ""

        # ── 9. Gemini Convers-AI layer (optional enhancement) ──────
        #    Called ONLY for conversational intents (hesitation,
        #    affordability, rate/tenure queries).  Never for
        #    underwriting, KYC, documents, or sanction stages.
        ai_used = False
        ai_response = await maybe_use_ai(
            intent=intent.intent_type.value,
            user_message=user_message,
            stage=session.state.value,
            context=self._build_context(session, intent),
        )
        if ai_response:
            response_text = ai_response
            ai_used = True

        return self._envelope(
            session,
            response_text,
            data=updated_data,
            validation_error=validation_error,
            metadata={
                "agent": STAGE_AGENT_MAP.get(state),
                "intent": intent.intent_type.value,
                "advanced": advanced,
                "ai_enhanced": ai_used,
            },
            latency=t0,
        )

    # ── Global command handler ──────────────────────────────────────────

    def _global_command(self, session: SessionData, msg: str) -> Optional[ResponseEnvelope]:
        norm = msg.strip().lower()
        sid = session.session_id

        if norm in _RESTART:
            self.sm.restart(sid)
            session = self.sm.get_or_create(sid)
            return self._envelope(
                session, "🔄 Session restarted!\n\n" + STAGE_PROMPTS[LoanState.GREETING]
            )

        if norm in _STATUS:
            prog = self.sm.progress(sid)
            bar = _progress_bar(prog["stage_index"], prog["total_stages"])
            valid, reason = self.sm.validate_current_state(sid)
            lines = [
                "📊 **Application Progress**",
                f"Stage: **{session.state.value.replace('_', ' ').title()}**",
                bar,
            ]
            if not valid:
                lines.append(f"\n⏳ Blocked: {reason}")
            return self._envelope(session, "\n".join(lines))

        if norm in _HELP:
            return self._envelope(
                session,
                "🤖 **Commands**: restart · status · help · quit\n\n"
                f"**Current stage**: {session.state.value.replace('_', ' ').title()}\n\n"
                + STAGE_PROMPTS.get(session.state, ""),
            )

        if norm in _QUIT:
            self.sm.abandon(sid, "User quit")
            session = self.sm.get_or_create(sid)
            return self._envelope(session, STAGE_PROMPTS[LoanState.ABANDONED])

        return None

    # ── Helpers ─────────────────────────────────────────────────────────

    def _envelope(
        self,
        session: SessionData,
        response: str,
        data: Optional[Dict] = None,
        validation_error: str = "",
        suggestions: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
        latency: Optional[float] = None,
    ) -> ResponseEnvelope:
        meta = metadata or {}
        if latency is not None:
            meta["latency_ms"] = _ms(latency)
        return ResponseEnvelope(
            response=response,
            state=session.state.value,
            session_id=session.session_id,
            data=data,
            validation_error=validation_error,
            suggestions=suggestions,
            progress=self.sm.progress(session.session_id),
            metadata=meta,
        )

    @staticmethod
    def _build_context(session: SessionData, intent) -> Dict[str, Any]:
        return {
            "state": session.state.value,
            "collected_data": dict(session.collected_data),
            "intent": intent.intent_type.value,
            "intent_confidence": intent.confidence,
            "intent_entities": intent.entities or {},
            "retry_count": session.retry_count,
        }

    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Query helper for API endpoints."""
        s = self.sm.get_session(session_id)
        if s is None:
            return {"exists": False}
        valid, reason = self.sm.validate_current_state(session_id)
        return {
            "exists": True,
            "session_id": s.session_id,
            "state": s.state.value,
            "collected_fields": list(s.collected_data.keys()),
            "can_advance": valid,
            "validation_error": reason,
            "retry_count": s.retry_count,
            "progress": self.sm.progress(session_id),
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Utilities
# ═══════════════════════════════════════════════════════════════════════════

def _ms(start: float) -> float:
    return round((time.perf_counter() - start) * 1000, 2)


def _progress_bar(current: int, total: int, width: int = 14) -> str:
    filled = int(width * current / total) if total else 0
    return f"[{'█' * filled}{'░' * (width - filled)}] {current}/{total} ({round(current / total * 100)}%)"
