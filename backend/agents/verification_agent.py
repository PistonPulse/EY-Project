"""
verification_agent.py
=====================

Production worker agent for **identity verification** stages of the
lending chatbot.

Covered States
--------------
- ``EMPLOYMENT``          — capture employment type & employer name.
- ``PHONE_VERIFICATION``  — validate Indian mobile number + simulate OTP flow.
- ``PAN_VERIFICATION``    — validate PAN format + simulate NSDL verification.

Architecture
------------
::

    User Message
         │
         ▼
    VerificationAgent.process()
         │
         ├── state == "employment"
         │     └─ _handle_employment()   → extract type + employer
         │
         ├── state == "phone_verification"
         │     ├─ _handle_phone_input()  → validate + send OTP
         │     └─ _handle_otp_verify()   → check OTP code
         │
         └── state == "pan_verification"
               └─ _handle_pan_input()    → validate + simulate NSDL check

Design Principles
-----------------
- **Reuses ``utils.validators``** — no duplicated regex logic.
- **Simulated OTP** — deterministic 6-digit code for demo; swap with a
  real SMS gateway in production.
- **Structured validation status** — every response returns a ``data`` dict
  with ``verified: bool``, ``field``, ``value`` (masked), and ``errors``.
- **Conversational templates** — all user-facing text is parameterised.
"""

from __future__ import annotations

import hashlib
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.base_agent import AgentResult, BaseAgent
from backend.utils.validators import validate_mobile, validate_pan, validate_aadhaar


# ═══════════════════════════════════════════════════════════════════════════
# OTP Simulator
# ═══════════════════════════════════════════════════════════════════════════

class OTPSimulator:
    """
    Deterministic OTP simulator for demo / testing.

    In production, replace ``send()`` with an SMS API call (e.g., MSG91,
    Twilio) and ``verify()`` with a time-limited cache / Redis lookup.

    The simulated OTP is derived from the phone number + a secret salt
    so it's reproducible within a session but not trivially guessable.
    """

    _SALT = "tata-capital-demo-2026"
    _EXPIRY_SECONDS = 300  # 5 minutes

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}

    def send(self, phone: str) -> str:
        """
        Generate and 'send' an OTP for the given phone number.

        Returns the OTP (in production this would only go to the user's phone).
        """
        otp = self._generate(phone)
        self._store[phone] = {
            "otp": otp,
            "created_at": time.time(),
            "attempts": 0,
        }
        return otp

    def verify(self, phone: str, user_otp: str) -> Tuple[bool, str]:
        """
        Check the user-supplied OTP against the stored value.

        Returns
        -------
        (True, "")           — verified.
        (False, reason_str)  — failed with human-readable reason.
        """
        record = self._store.get(phone)
        if record is None:
            return False, "No OTP has been sent to this number. Please request a new one."

        # Expiry check
        elapsed = time.time() - record["created_at"]
        if elapsed > self._EXPIRY_SECONDS:
            del self._store[phone]
            return False, "OTP has expired. Please request a new one."

        # Attempt limit (3 tries)
        record["attempts"] += 1
        if record["attempts"] > 3:
            del self._store[phone]
            return False, "Too many failed attempts. Please request a new OTP."

        if user_otp.strip() != record["otp"]:
            remaining = 3 - record["attempts"]
            return False, f"Incorrect OTP. {remaining} attempt(s) remaining."

        # Success — clean up
        del self._store[phone]
        return True, ""

    def _generate(self, phone: str) -> str:
        """Produce a deterministic 6-digit OTP from phone + salt."""
        digest = hashlib.sha256(f"{phone}:{self._SALT}".encode()).hexdigest()
        return str(int(digest[:8], 16) % 900_000 + 100_000)


# ═══════════════════════════════════════════════════════════════════════════
# Employment Parsing Helpers
# ═══════════════════════════════════════════════════════════════════════════

EMPLOYMENT_TYPES = {"salaried", "self_employed", "business", "professional"}

EMPLOYMENT_SYNONYMS: Dict[str, str] = {
    "salaried":       "salaried",
    "salary":         "salaried",
    "employed":       "salaried",
    "job":            "salaried",
    "service":        "salaried",
    "private":        "salaried",
    "government":     "salaried",
    "self employed":  "self_employed",
    "self-employed":  "self_employed",
    "freelance":      "self_employed",
    "freelancer":     "self_employed",
    "consultant":     "self_employed",
    "contractor":     "self_employed",
    "business":       "business",
    "businessman":    "business",
    "owner":          "business",
    "entrepreneur":   "business",
    "startup":        "business",
    "professional":   "professional",
    "doctor":         "professional",
    "lawyer":         "professional",
    "ca":             "professional",
    "architect":      "professional",
    "engineer":       "professional",
}


def _detect_employment_type(text: str) -> Optional[str]:
    """Map free-text input to a canonical employment type."""
    normalised = text.strip().lower()
    if normalised in EMPLOYMENT_SYNONYMS:
        return EMPLOYMENT_SYNONYMS[normalised]
    for keyword, emp_type in EMPLOYMENT_SYNONYMS.items():
        if keyword in normalised:
            return emp_type
    return None


def _extract_employer(text: str) -> Optional[str]:
    """
    Best-effort employer / business name extraction.

    Looks for patterns like:
    - "I work at TCS"
    - "employer: Infosys"
    - "company name is Wipro"
    """
    patterns = [
        r"(?:work(?:ing)?\s+(?:at|for|in|with)\s+)(.+)",
        r"(?:employer|company|firm|organisation|organization)\s*(?:is|:|-|=)\s*(.+)",
        r"(?:company\s+name\s*(?:is|:)\s*)(.+)",
        r"(?:at|for)\s+([A-Z][A-Za-z\s&.]+)",
    ]
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip().rstrip(".")
            if len(name) >= 2:
                return name.title()
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Phone / PAN Extraction Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _extract_phone(text: str) -> Optional[str]:
    """Pull a 10-digit Indian mobile number from free text."""
    cleaned = re.sub(r"[\s\-\(\)+]", "", text)
    # Try with country code prefix
    m = re.search(r"(?:91)?([6-9]\d{9})", cleaned)
    return m.group(1) if m else None


def _extract_pan(text: str) -> Optional[str]:
    """Pull a PAN from free text."""
    m = re.search(r"[A-Z]{5}\d{4}[A-Z]", text.upper())
    return m.group(0) if m else None


def _extract_otp(text: str) -> Optional[str]:
    """Pull a 6-digit OTP from free text."""
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None


def _extract_aadhaar(text: str) -> Optional[str]:
    """Pull a 12-digit Aadhaar from free text (with or without spaces)."""
    cleaned = text.replace(" ", "")
    m = re.search(r"\d{12}", cleaned)
    return m.group(0) if m else None


def _mask(value: str, visible: int = 4) -> str:
    """Mask all but the last *visible* characters."""
    if len(value) <= visible:
        return value
    return "X" * (len(value) - visible) + value[-visible:]


# ═══════════════════════════════════════════════════════════════════════════
# Response Templates
# ═══════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, str] = {

    # ── Employment ──────────────────────────────────────────────────────
    "employment_ask": (
        "Let's capture your employment details.\n\n"
        "What is your **employment type**?\n"
        "• **Salaried** — working for a company\n"
        "• **Self-employed** — freelancer / consultant\n"
        "• **Business** — own a business\n"
        "• **Professional** — doctor, CA, lawyer, etc."
    ),
    "employment_type_captured": (
        "Got it — you're **{emp_type_display}**.\n\n"
        "Who is your employer / business name?"
    ),
    "employment_complete": (
        "✅ Employment details recorded:\n\n"
        "• Type: **{emp_type_display}**\n"
        "• Employer: **{employer}**\n\n"
        "Next, I'll need to verify your mobile number."
    ),
    "employment_invalid": (
        "I couldn't identify your employment type from that.\n\n"
        "Please choose from: **Salaried** · **Self-employed** · "
        "**Business** · **Professional**"
    ),

    # ── Phone ───────────────────────────────────────────────────────────
    "phone_ask": (
        "Please provide your **10-digit mobile number** (starting with 6-9).\n\n"
        "We'll send a One-Time Password (OTP) for verification."
    ),
    "phone_invalid": (
        "❌ **{phone}** is not a valid Indian mobile number.\n\n"
        "A valid number has **10 digits** and starts with **6, 7, 8, or 9**.\n"
        "Example: `9876543210`"
    ),
    "otp_sent": (
        "📱 OTP sent to **{masked_phone}**!\n\n"
        "Please enter the **6-digit OTP** to verify your number.\n\n"
        "🔒 _The OTP is valid for 5 minutes._\n\n"
        "💡 **Demo hint**: Your OTP is `{otp}` _(this hint won't appear in production)_."
    ),
    "otp_success": (
        "✅ **Mobile verified!** ({masked_phone})\n\n"
        "Your phone number has been successfully verified.\n"
        "Let's move on to PAN verification."
    ),
    "otp_failed": (
        "❌ {reason}\n\n"
        "Please try again or type **resend** to get a new OTP."
    ),
    "otp_resent": (
        "🔄 New OTP sent to **{masked_phone}**.\n\n"
        "Please enter the **6-digit code**.\n\n"
        "💡 **Demo hint**: Your new OTP is `{otp}`."
    ),

    # ── PAN ─────────────────────────────────────────────────────────────
    "pan_ask": (
        "Please enter your **PAN number** for identity verification.\n\n"
        "Format: 5 letters + 4 digits + 1 letter (e.g., `ABCDE1234F`)."
    ),
    "pan_invalid": (
        "❌ **{pan}** is not a valid PAN number.\n\n"
        "PAN must follow the format **ABCDE1234F**:\n"
        "• 5 uppercase letters → 4 digits → 1 uppercase letter\n\n"
        "Please try again."
    ),
    "pan_verified": (
        "✅ **PAN verified!** ({masked_pan})\n\n"
        "• PAN: **{masked_pan}**\n"
        "• Name on PAN: **{pan_name}**\n"
        "• Status: **Active** ✓\n\n"
        "🔐 Your identity has been successfully verified."
    ),
    "pan_name_mismatch": (
        "⚠️ The name on PAN (**{pan_name}**) doesn't match the name you "
        "provided (**{applicant_name}**). Please verify and re-enter your PAN."
    ),

    # ── Summary ─────────────────────────────────────────────────────────
    "verification_summary": (
        "🔒 **Verification Summary**\n\n"
        "| Check | Status |\n"
        "|-------|--------|\n"
        "| Mobile ({masked_phone}) | {phone_status} |\n"
        "| PAN ({masked_pan}) | {pan_status} |\n\n"
        "{next_step}"
    ),
}


def _render(key: str, **kwargs) -> str:
    tpl = TEMPLATES.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


# ═══════════════════════════════════════════════════════════════════════════
# Verification Agent
# ═══════════════════════════════════════════════════════════════════════════

class VerificationAgent(BaseAgent):
    """
    Handles employment capture, mobile-number validation with OTP,
    and PAN verification using regex + simulated NSDL lookup.

    All validation logic delegates to ``utils.validators``; the OTP flow
    uses a deterministic simulator for demo/testing.
    """

    def __init__(self) -> None:
        super().__init__(name="verification")
        self._otp = OTPSimulator()
        # Track which sessions are in the OTP-entry sub-flow
        self._awaiting_otp: Dict[str, str] = {}  # session_id → phone

    async def process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """Route to the correct handler based on conversation state."""
        state = context.get("state", "")
        collected = context.get("collected_data", {})
        self.logger.info("VerificationAgent | session=%s state=%s", session_id, state)

        handler = {
            "employment":         self._handle_employment,
            "phone_verification": self._handle_phone,
            "pan_verification":   self._handle_pan,
        }.get(state, self._handle_fallback)

        return await handler(session_id, user_message, collected, context)

    # ──────────────────────────────────────────────────────────────────
    # EMPLOYMENT
    # ──────────────────────────────────────────────────────────────────

    async def _handle_employment(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Capture employment type and employer name."""

        existing_type = collected.get("employment_type")
        existing_employer = collected.get("employer_name")

        # If we already have the type, we're waiting for the employer name
        if existing_type and not existing_employer:
            employer = _extract_employer(msg) or msg.strip().title()
            if len(employer) < 2:
                return AgentResult(
                    success=True,
                    message="Please provide a valid employer or business name.",
                    data={},
                )
            display = existing_type.replace("_", "-").title()
            return AgentResult(
                success=True,
                message=_render(
                    "employment_complete",
                    emp_type_display=display,
                    employer=employer,
                ),
                data={
                    "employer_name": employer,
                },
            )

        # Try to detect employment type from the message
        emp_type = _detect_employment_type(msg)
        if not emp_type:
            return AgentResult(
                success=True,
                message=_render("employment_ask") if not existing_type
                        else _render("employment_invalid"),
                data={},
            )

        display = emp_type.replace("_", "-").title()

        # Check if employer is also in the same message
        employer = _extract_employer(msg)
        if employer:
            return AgentResult(
                success=True,
                message=_render(
                    "employment_complete",
                    emp_type_display=display,
                    employer=employer,
                ),
                data={
                    "employment_type": emp_type,
                    "employer_name": employer,
                },
            )

        # Ask for employer in next turn
        return AgentResult(
            success=True,
            message=_render("employment_type_captured", emp_type_display=display),
            data={"employment_type": emp_type},
        )

    # ──────────────────────────────────────────────────────────────────
    # PHONE VERIFICATION
    # ──────────────────────────────────────────────────────────────────

    async def _handle_phone(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Validate mobile number and run OTP flow."""

        # Sub-flow: are we waiting for an OTP entry?
        if session_id in self._awaiting_otp:
            return await self._handle_otp_entry(session_id, msg, collected)

        # Check for resend request
        if msg.strip().lower() in ("resend", "new otp", "resend otp", "send again"):
            phone = collected.get("phone")
            if phone:
                return self._send_otp(session_id, phone)
            return AgentResult(
                success=True,
                message=_render("phone_ask"),
                data={},
            )

        # Try to extract a phone number
        phone = _extract_phone(msg)
        if not phone:
            return AgentResult(
                success=True,
                message=_render("phone_ask"),
                data={},
            )

        # Validate format
        valid, reason = validate_mobile(phone)
        if not valid:
            return AgentResult(
                success=False,
                message=_render("phone_invalid", phone=phone),
                data={},
                errors=[reason],
            )

        # Phone is valid — send OTP
        return self._send_otp(session_id, phone)

    def _send_otp(self, session_id: str, phone: str) -> AgentResult:
        """Generate OTP and return the 'OTP sent' response."""
        otp = self._otp.send(phone)
        self._awaiting_otp[session_id] = phone
        masked = _mask(phone)
        return AgentResult(
            success=True,
            message=_render("otp_sent", masked_phone=masked, otp=otp),
            data={"phone": phone},
        )

    async def _handle_otp_entry(
        self, session_id: str, msg: str, collected: Dict
    ) -> AgentResult:
        """Verify user-entered OTP."""
        phone = self._awaiting_otp[session_id]
        masked = _mask(phone)

        # User wants a resend
        if msg.strip().lower() in ("resend", "new otp", "resend otp", "send again"):
            otp = self._otp.send(phone)
            return AgentResult(
                success=True,
                message=_render("otp_resent", masked_phone=masked, otp=otp),
                data={},
            )

        # Extract 6-digit code
        code = _extract_otp(msg)
        if not code:
            return AgentResult(
                success=True,
                message="Please enter the **6-digit OTP** sent to your phone.",
                data={},
            )

        # Verify
        verified, reason = self._otp.verify(phone, code)
        if not verified:
            return AgentResult(
                success=False,
                message=_render("otp_failed", reason=reason),
                data={},
                errors=[reason],
            )

        # OTP verified successfully
        del self._awaiting_otp[session_id]
        return AgentResult(
            success=True,
            message=_render("otp_success", masked_phone=masked),
            data={
                "phone": phone,
                "phone_verified": True,
                "phone_verification_status": "verified",
            },
        )

    # ──────────────────────────────────────────────────────────────────
    # PAN VERIFICATION
    # ──────────────────────────────────────────────────────────────────

    async def _handle_pan(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Validate PAN format and simulate NSDL verification."""

        # Extract PAN from message
        pan = _extract_pan(msg)
        if not pan:
            return AgentResult(
                success=True,
                message=_render("pan_ask"),
                data={},
            )

        # Format validation via utils.validators
        valid, reason = validate_pan(pan)
        if not valid:
            return AgentResult(
                success=False,
                message=_render("pan_invalid", pan=pan),
                data={},
                errors=[reason],
            )

        # Simulate NSDL PAN verification lookup
        pan_name = self._simulate_nsdl_lookup(pan)
        masked = _mask(pan)

        # Optional: name match check
        applicant_name = collected.get("applicant_name", "")
        if applicant_name and not self._fuzzy_name_match(pan_name, applicant_name):
            return AgentResult(
                success=True,
                message=_render(
                    "pan_name_mismatch",
                    pan_name=pan_name,
                    applicant_name=applicant_name,
                ),
                data={},
            )

        return AgentResult(
            success=True,
            message=_render(
                "pan_verified",
                masked_pan=masked,
                pan_name=pan_name,
            ),
            data={
                "pan_number": pan,
                "pan_verified": True,
                "pan_name": pan_name,
                "pan_verification_status": "verified",
                "kyc_verified": True,
            },
        )

    @staticmethod
    def _simulate_nsdl_lookup(pan: str) -> str:
        """
        Simulate an NSDL PAN verification response.

        In production, replace with an actual NSDL / UTIITSL API call.
        Returns a simulated name associated with the PAN.
        """
        # Use the 4th character of PAN to determine 'type':
        #   P = Individual, C = Company, H = HUF, etc.
        pan_type_char = pan[3] if len(pan) > 3 else "P"
        type_map = {
            "P": "Individual",
            "C": "Company",
            "H": "HUF",
            "F": "Firm",
            "A": "AOP",
            "T": "Trust",
            "B": "BOI",
            "L": "Local Authority",
            "J": "Artificial Juridical Person",
            "G": "Government",
        }
        entity_type = type_map.get(pan_type_char, "Individual")
        # Return a deterministic placeholder name
        return f"PAN Holder ({entity_type})"

    @staticmethod
    def _fuzzy_name_match(pan_name: str, applicant_name: str) -> bool:
        """
        Loose name match — checks if any word from the applicant's name
        appears in the PAN-returned name.

        In production: use Levenshtein distance or a proper name-matching
        service (e.g., from the credit bureau).
        """
        # For demo mode, the NSDL lookup returns a generic name,
        # so always pass the match.
        if "PAN Holder" in pan_name:
            return True
        applicant_words = {w.lower() for w in applicant_name.split() if len(w) > 1}
        pan_words = {w.lower() for w in pan_name.split() if len(w) > 1}
        return bool(applicant_words & pan_words)

    # ──────────────────────────────────────────────────────────────────
    # FALLBACK
    # ──────────────────────────────────────────────────────────────────

    async def _handle_fallback(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        state = ctx.get("state", "unknown")
        return AgentResult(
            success=True,
            message=(
                f"I'm the verification agent but I'm not sure what to do "
                f"in the **{state}** stage. Type **help** for guidance."
            ),
            data={},
        )
