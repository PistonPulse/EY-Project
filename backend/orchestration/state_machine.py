"""
state_machine.py
================

Production-grade state machine for the Loan Application Chatbot.

Architecture
------------
Three core components work together:

1. **LoanState** — 14-stage enum matching the exact loan journey.
2. **Validators** — Per-state input validation that must pass before a
   transition is allowed.
3. **StateMachine** — Session-aware engine that enforces the stage sequence,
   validates inputs, tracks history, and manages retries.

State Flow
----------
::

    GREETING → PURPOSE → LOAN_AMOUNT → EMPLOYMENT → PHONE_VERIFICATION
    → PAN_VERIFICATION → INCOME → LIABILITIES → CREDIT_CHECK
    → OFFER_PRESENTATION → TENURE_SELECTION → DECISION
    → DOCUMENT_UPLOAD → SANCTION

Design Principles
-----------------
- **Deterministic** — every transition is guarded and auditable.
- **Validation-first** — no forward movement without clean data.
- **Modular** — validators are plain functions; swap / extend without
  touching the state machine core.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
#  1. Loan States
# ═══════════════════════════════════════════════════════════════════════════

class LoanState(str, Enum):
    """All 14 stages of the loan application chatbot journey."""

    GREETING            = "greeting"
    PURPOSE             = "purpose"
    LOAN_AMOUNT         = "loan_amount"
    EMPLOYMENT          = "employment"
    PHONE_VERIFICATION  = "phone_verification"
    PAN_VERIFICATION    = "pan_verification"
    INCOME              = "income"
    LIABILITIES         = "liabilities"
    CREDIT_CHECK        = "credit_check"
    OFFER_PRESENTATION  = "offer_presentation"
    TENURE_SELECTION    = "tenure_selection"
    DECISION            = "decision"
    DOCUMENT_UPLOAD     = "document_upload"
    SANCTION            = "sanction"

    # ── Terminal / special ──────────────────────────────────────────────
    ERROR               = "error"
    ABANDONED           = "abandoned"


# Ordered happy-path for progress tracking
HAPPY_PATH: List[LoanState] = [
    LoanState.GREETING,
    LoanState.PURPOSE,
    LoanState.LOAN_AMOUNT,
    LoanState.EMPLOYMENT,
    LoanState.PHONE_VERIFICATION,
    LoanState.PAN_VERIFICATION,
    LoanState.INCOME,
    LoanState.LIABILITIES,
    LoanState.CREDIT_CHECK,
    LoanState.OFFER_PRESENTATION,
    LoanState.TENURE_SELECTION,
    LoanState.DECISION,
    LoanState.DOCUMENT_UPLOAD,
    LoanState.SANCTION,
]


# ═══════════════════════════════════════════════════════════════════════════
#  2. Transition Table
# ═══════════════════════════════════════════════════════════════════════════

TRANSITIONS: Dict[LoanState, List[LoanState]] = {
    LoanState.GREETING:            [LoanState.PURPOSE],
    LoanState.PURPOSE:             [LoanState.LOAN_AMOUNT,       LoanState.ABANDONED],
    LoanState.LOAN_AMOUNT:         [LoanState.EMPLOYMENT,        LoanState.ABANDONED],
    LoanState.EMPLOYMENT:          [LoanState.PHONE_VERIFICATION, LoanState.ABANDONED],
    LoanState.PHONE_VERIFICATION:  [LoanState.PAN_VERIFICATION,  LoanState.ABANDONED],
    LoanState.PAN_VERIFICATION:    [LoanState.INCOME,            LoanState.ABANDONED],
    LoanState.INCOME:              [LoanState.LIABILITIES,       LoanState.ABANDONED],
    LoanState.LIABILITIES:         [LoanState.CREDIT_CHECK,      LoanState.ABANDONED],
    LoanState.CREDIT_CHECK:        [LoanState.OFFER_PRESENTATION, LoanState.ABANDONED],
    LoanState.OFFER_PRESENTATION:  [LoanState.TENURE_SELECTION,  LoanState.ABANDONED],
    LoanState.TENURE_SELECTION:    [LoanState.DECISION,          LoanState.ABANDONED],
    LoanState.DECISION:            [LoanState.DOCUMENT_UPLOAD,   LoanState.ABANDONED],
    LoanState.DOCUMENT_UPLOAD:     [LoanState.SANCTION,          LoanState.ABANDONED],
    LoanState.SANCTION:            [],
    LoanState.ERROR:               [LoanState.GREETING],
    LoanState.ABANDONED:           [LoanState.GREETING],
}


# ═══════════════════════════════════════════════════════════════════════════
#  3. Agent Routing Map  (state → worker-agent key)
# ═══════════════════════════════════════════════════════════════════════════

STAGE_AGENT_MAP: Dict[LoanState, str] = {
    LoanState.GREETING:            "sales",
    LoanState.PURPOSE:             "sales",
    LoanState.LOAN_AMOUNT:         "sales",
    LoanState.EMPLOYMENT:          "verification",
    LoanState.PHONE_VERIFICATION:  "verification",
    LoanState.PAN_VERIFICATION:    "verification",
    LoanState.INCOME:              "underwriting",
    LoanState.LIABILITIES:         "underwriting",
    LoanState.CREDIT_CHECK:        "underwriting",
    LoanState.OFFER_PRESENTATION:  "sales",
    LoanState.TENURE_SELECTION:    "sales",
    LoanState.DECISION:            "underwriting",
    LoanState.DOCUMENT_UPLOAD:     "document",
    LoanState.SANCTION:            "sanction",
}


# ═══════════════════════════════════════════════════════════════════════════
#  4. Input Validators  (one function per state)
# ═══════════════════════════════════════════════════════════════════════════
#
#  Each validator receives the session's collected_data dict and returns
#  (is_valid: bool, error_message: str).  An empty error_message means pass.
#
#  The StateMachine calls the validator for the CURRENT state before
#  allowing a forward transition.
# ═══════════════════════════════════════════════════════════════════════════

ValidatorFn = Callable[[Dict[str, Any]], Tuple[bool, str]]


def _validate_greeting(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Greeting requires the applicant's name."""
    name = data.get("applicant_name", "").strip()
    if not name or len(name) < 2:
        return False, "Please provide your full name (at least 2 characters)."
    return True, ""


def _validate_purpose(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Purpose must be one of the recognised loan categories."""
    valid_purposes = {"personal", "home", "auto", "business", "education", "gold"}
    purpose = data.get("loan_purpose", "").strip().lower()
    if purpose not in valid_purposes:
        return False, f"Loan purpose must be one of: {', '.join(sorted(valid_purposes))}."
    return True, ""


def _validate_loan_amount(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Loan amount must be a positive number within policy limits."""
    try:
        amount = float(data.get("loan_amount", 0))
    except (ValueError, TypeError):
        return False, "Loan amount must be a valid number."
    if amount < 10_000:
        return False, "Minimum loan amount is ₹10,000."
    if amount > 50_000_000:
        return False, "Maximum loan amount is ₹5,00,00,000."
    return True, ""


def _validate_employment(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Employment type and employer name are required."""
    valid_types = {"salaried", "self_employed", "business", "professional"}
    emp_type = data.get("employment_type", "").strip().lower()
    if emp_type not in valid_types:
        return False, f"Employment type must be one of: {', '.join(sorted(valid_types))}."
    employer = data.get("employer_name", "").strip()
    if not employer:
        return False, "Employer / business name is required."
    return True, ""


def _validate_phone(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Phone must be a valid 10-digit Indian mobile number."""
    phone = re.sub(r"[\s\-+]", "", str(data.get("phone", "")))
    phone = phone[-10:] if len(phone) > 10 else phone      # strip country code
    if not re.match(r"^[6-9]\d{9}$", phone):
        return False, "Provide a valid 10-digit mobile number (starting with 6-9)."
    if not data.get("phone_verified"):
        return False, "Phone number has not been verified (OTP pending)."
    return True, ""


def _validate_pan(data: Dict[str, Any]) -> Tuple[bool, str]:
    """PAN must match the ABCDE1234F format."""
    pan = str(data.get("pan_number", "")).strip().upper()
    if not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan):
        return False, "PAN must be in the format ABCDE1234F."
    if not data.get("pan_verified"):
        return False, "PAN has not been verified."
    return True, ""


def _validate_income(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Monthly income must be a positive number."""
    try:
        income = float(data.get("monthly_income", 0))
    except (ValueError, TypeError):
        return False, "Monthly income must be a valid number."
    if income <= 0:
        return False, "Monthly income must be greater than zero."
    return True, ""


def _validate_liabilities(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Existing liabilities must be a non-negative number."""
    try:
        liabilities = float(data.get("existing_emi", 0))
    except (ValueError, TypeError):
        return False, "Existing EMI / liabilities must be a valid number."
    if liabilities < 0:
        return False, "Existing liabilities cannot be negative."
    # "liabilities_declared" flag confirms the user explicitly stated them
    if not data.get("liabilities_declared"):
        return False, "Please confirm you have declared all existing liabilities."
    return True, ""


def _validate_credit_check(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Credit check must have completed and returned a score."""
    score = data.get("credit_score")
    if score is None:
        return False, "Credit score has not been fetched yet."
    try:
        score = int(score)
    except (ValueError, TypeError):
        return False, "Credit score must be a valid integer."
    if not (300 <= score <= 900):
        return False, "Credit score must be between 300 and 900."
    return True, ""


def _validate_offer_presentation(data: Dict[str, Any]) -> Tuple[bool, str]:
    """At least one offer must have been presented."""
    offers = data.get("loan_offers")
    if not offers or not isinstance(offers, list) or len(offers) == 0:
        return False, "No loan offers have been generated."
    return True, ""


def _validate_tenure_selection(data: Dict[str, Any]) -> Tuple[bool, str]:
    """User must have selected a valid tenure from the offered options."""
    tenure = data.get("selected_tenure")
    if tenure is None:
        return False, "Please select a loan tenure."
    try:
        tenure = int(tenure)
    except (ValueError, TypeError):
        return False, "Tenure must be a number (in months)."
    if tenure not in (12, 24, 36, 48, 60, 72, 84, 96, 120, 180, 240, 360):
        return False, "Selected tenure is not available. Choose from standard options."
    return True, ""


def _validate_decision(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Decision must be one of accepted / rejected."""
    decision = data.get("applicant_decision", "").strip().lower()
    if decision not in ("accepted", "rejected"):
        return False, "Please accept or reject the loan offer."
    if decision == "rejected":
        return False, "Offer rejected by applicant — cannot proceed to documents."
    return True, ""


def _validate_document_upload(data: Dict[str, Any]) -> Tuple[bool, str]:
    """All mandatory documents must be uploaded."""
    required_docs = {"id_proof", "address_proof", "income_proof"}
    uploaded = set(data.get("uploaded_documents", []))
    missing = required_docs - uploaded
    if missing:
        return False, f"Missing documents: {', '.join(sorted(missing))}."
    return True, ""


def _always_pass(_data: Dict[str, Any]) -> Tuple[bool, str]:
    """No validation required (terminal / auto-computed states)."""
    return True, ""


# ── Registry ────────────────────────────────────────────────────────────

STATE_VALIDATORS: Dict[LoanState, ValidatorFn] = {
    LoanState.GREETING:            _validate_greeting,
    LoanState.PURPOSE:             _validate_purpose,
    LoanState.LOAN_AMOUNT:         _validate_loan_amount,
    LoanState.EMPLOYMENT:          _validate_employment,
    LoanState.PHONE_VERIFICATION:  _validate_phone,
    LoanState.PAN_VERIFICATION:    _validate_pan,
    LoanState.INCOME:              _validate_income,
    LoanState.LIABILITIES:         _validate_liabilities,
    LoanState.CREDIT_CHECK:        _validate_credit_check,
    LoanState.OFFER_PRESENTATION:  _validate_offer_presentation,
    LoanState.TENURE_SELECTION:    _validate_tenure_selection,
    LoanState.DECISION:            _validate_decision,
    LoanState.DOCUMENT_UPLOAD:     _validate_document_upload,
    LoanState.SANCTION:            _always_pass,
    LoanState.ERROR:               _always_pass,
    LoanState.ABANDONED:           _always_pass,
}


# ═══════════════════════════════════════════════════════════════════════════
#  5. Session Data
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SessionData:
    """
    Complete runtime state for one chatbot conversation.

    Attributes
    ----------
    session_id     — Unique conversation identifier.
    state          — Current ``LoanState``.
    collected_data — All key-value pairs collected from the user so far.
    history        — Chronological audit log of transitions.
    created_at     — ISO-8601 session creation timestamp.
    updated_at     — ISO-8601 last-activity timestamp.
    retry_count    — Consecutive invalid inputs in the current state.
    error_context  — Human-readable cause if state == ERROR.
    metadata       — Arbitrary metadata (channel, device, IP, etc.).
    """

    session_id: str = ""
    state: LoanState = LoanState.GREETING
    collected_data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    retry_count: int = 0
    error_context: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.session_id:
            self.session_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now


# ═══════════════════════════════════════════════════════════════════════════
#  6. State Machine
# ═══════════════════════════════════════════════════════════════════════════

MAX_RETRIES = 5


class StateMachine:
    """
    Session-aware state machine with input validation and transition guards.

    Features
    --------
    - **Validation gate** — calls the per-state validator before every
      forward transition; rejects with a clear error if data is invalid.
    - **Transition guard** — only allows moves listed in ``TRANSITIONS``.
    - **Retry tracking** — counts consecutive bad inputs; escalates to
      ``ERROR`` after ``MAX_RETRIES``.
    - **Audit history** — every transition is timestamped and recorded.
    - **Session lifecycle** — create / get / restart / abandon.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionData] = {}

    # ── Session lifecycle ───────────────────────────────────────────────

    def create_session(self, session_id: Optional[str] = None, **meta) -> SessionData:
        """Create and store a new session."""
        session = SessionData(session_id=session_id or "", metadata=meta)
        self._sessions[session.session_id] = session
        logger.info("Session created: %s", session.session_id)
        return session

    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Return the session or ``None``."""
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> SessionData:
        """Return existing session or create a fresh one."""
        return self._sessions.get(session_id) or self.create_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        """Remove a session. Returns ``True`` if it existed."""
        return self._sessions.pop(session_id, None) is not None

    # ── State queries ───────────────────────────────────────────────────

    def current_state(self, session_id: str) -> LoanState:
        """Return current state (defaults to GREETING for unknown sessions)."""
        s = self._sessions.get(session_id)
        return s.state if s else LoanState.GREETING

    def collected_data(self, session_id: str) -> Dict[str, Any]:
        """Return a copy of all collected data."""
        s = self._sessions.get(session_id)
        return dict(s.collected_data) if s else {}

    def history(self, session_id: str) -> List[Dict[str, Any]]:
        """Return the full transition history."""
        s = self._sessions.get(session_id)
        return list(s.history) if s else []

    # ── Data collection ─────────────────────────────────────────────────

    def update_data(self, session_id: str, data: Dict[str, Any]) -> None:
        """Merge *data* into the session and reset the retry counter."""
        session = self.get_or_create(session_id)
        session.collected_data.update(data)
        session.updated_at = datetime.now(timezone.utc).isoformat()
        session.retry_count = 0
        logger.info("Session %s: data updated → %s", session_id, list(data.keys()))

    # ── Validation ──────────────────────────────────────────────────────

    def validate_current_state(self, session_id: str) -> Tuple[bool, str]:
        """
        Run the validator for the session's current state.

        Returns
        -------
        (True, "")  — all inputs valid, ready to advance.
        (False, msg) — validation failed with a human-readable reason.
        """
        session = self.get_or_create(session_id)
        validator = STATE_VALIDATORS.get(session.state, _always_pass)
        return validator(session.collected_data)

    # ── Transitions ─────────────────────────────────────────────────────

    def can_advance(self, session_id: str) -> bool:
        """Return ``True`` if validation passes for the current state."""
        ok, _ = self.validate_current_state(session_id)
        return ok

    def transition(
        self,
        session_id: str,
        target: LoanState,
        *,
        force: bool = False,
    ) -> LoanState:
        """
        Move the session to *target* state.

        Parameters
        ----------
        target : LoanState
            Desired next state.
        force : bool
            Skip validation (used for ERROR / ABANDONED moves).

        Raises
        ------
        ValueError
            Target is not reachable from the current state.
        PermissionError
            Validation failed for the current state's collected data.
        """
        session = self.get_or_create(session_id)
        current = session.state
        allowed = TRANSITIONS.get(current, [])

        # Guard 1 — Transition legality
        if target not in allowed:
            raise ValueError(
                f"Illegal transition: {current.value} → {target.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        # Guard 2 — Input validation
        if not force:
            valid, reason = self.validate_current_state(session_id)
            if not valid:
                raise PermissionError(
                    f"Cannot leave '{current.value}': {reason}"
                )

        # Record & apply
        now = datetime.now(timezone.utc).isoformat()
        session.history.append({
            "from": current.value,
            "to": target.value,
            "timestamp": now,
            "collected_fields": list(session.collected_data.keys()),
        })
        session.state = target
        session.updated_at = now
        session.retry_count = 0
        logger.info("Session %s: %s → %s", session_id, current.value, target.value)
        return target

    def advance(self, session_id: str) -> Tuple[bool, str]:
        """
        Validate and auto-advance to the next happy-path state.

        Returns
        -------
        (True, new_state_value)  — advanced successfully.
        (False, validation_msg)  — blocked; returns the validator error.
        """
        session = self.get_or_create(session_id)
        current = session.state

        # Find the next happy-path target
        allowed = TRANSITIONS.get(current, [])
        forward = [s for s in allowed if s not in (LoanState.ABANDONED,)]
        if not forward:
            return False, f"No forward transition from '{current.value}'."

        target = forward[0]

        try:
            self.transition(session_id, target)
            return True, target.value
        except PermissionError as exc:
            return False, str(exc)

    # ── Retry / error handling ──────────────────────────────────────────

    def record_retry(self, session_id: str) -> int:
        """
        Increment the retry counter.  Escalates to ERROR after ``MAX_RETRIES``.
        """
        session = self.get_or_create(session_id)
        session.retry_count += 1
        logger.warning(
            "Session %s: retry %d/%d in '%s'",
            session_id, session.retry_count, MAX_RETRIES, session.state.value,
        )
        if session.retry_count >= MAX_RETRIES:
            session.error_context = (
                f"Too many invalid inputs ({session.retry_count}) "
                f"in stage '{session.state.value}'."
            )
            self._force_error(session)
        return session.retry_count

    def _force_error(self, session: SessionData) -> None:
        now = datetime.now(timezone.utc).isoformat()
        session.history.append({
            "from": session.state.value,
            "to": LoanState.ERROR.value,
            "timestamp": now,
            "reason": session.error_context,
        })
        session.state = LoanState.ERROR
        session.updated_at = now
        logger.error("Session %s → ERROR: %s", session.session_id, session.error_context)

    # ── Convenience lifecycle ───────────────────────────────────────────

    def abandon(self, session_id: str, reason: str = "User abandoned") -> None:
        """Move session to ABANDONED."""
        session = self.get_or_create(session_id)
        now = datetime.now(timezone.utc).isoformat()
        session.history.append({
            "from": session.state.value,
            "to": LoanState.ABANDONED.value,
            "timestamp": now,
            "reason": reason,
        })
        session.state = LoanState.ABANDONED
        session.updated_at = now
        logger.info("Session %s abandoned: %s", session_id, reason)

    def restart(self, session_id: str) -> SessionData:
        """Reset to GREETING, preserving session ID and metadata."""
        session = self.get_or_create(session_id)
        now = datetime.now(timezone.utc).isoformat()
        session.history.append({
            "from": session.state.value,
            "to": LoanState.GREETING.value,
            "timestamp": now,
            "reason": "Session restarted",
        })
        session.state = LoanState.GREETING
        session.collected_data.clear()
        session.retry_count = 0
        session.error_context = ""
        session.updated_at = now
        logger.info("Session %s restarted", session_id)
        return session

    def progress(self, session_id: str) -> Dict[str, Any]:
        """
        Return a progress summary for the session.

        Includes current stage index, total stages, and percentage.
        """
        session = self.get_or_create(session_id)
        total = len(HAPPY_PATH)
        try:
            idx = HAPPY_PATH.index(session.state) + 1
        except ValueError:
            idx = 0
        return {
            "current_stage": session.state.value,
            "stage_index": idx,
            "total_stages": total,
            "percent": round(idx / total * 100) if total else 0,
        }

    @property
    def active_sessions(self) -> int:
        """Number of sessions in the store."""
        return len(self._sessions)
