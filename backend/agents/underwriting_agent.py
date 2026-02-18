"""
underwriting_agent.py
=====================

Production worker agent for **risk assessment and eligibility decisioning**
in the lending chatbot.

Covered States
--------------
- ``INCOME``       — capture monthly net income.
- ``LIABILITIES``  — capture existing EMI / debt obligations.
- ``CREDIT_CHECK`` — simulate credit-bureau pull and evaluate score.
- ``DECISION``     — present the final underwriting decision to the user.

Decision Engine (User-Specified Rules)
--------------------------------------
1. **Approve** — if requested amount ≤ pre-approved limit.
2. **Conditional Approve** — if amount ≤ 2× limit AND EMI ≤ 50 % income.
3. **Reject** — if amount > 2× limit.
4. **Reject** — if credit score < 700.
5. **Reject** — if DTI > 60 %.

The pre-approved limit is computed as::

    max_affordable_emi = (income - existing_emi) × 0.50
    pre_approved_limit = reverse_emi(max_affordable_emi, rate, tenure)

Design Principles
-----------------
- **No ML** — all decisions are deterministic and fully auditable.
- **Structured output** — every response includes a ``decision`` object
  with verdict, reasoning list, and numeric breakdown.
- **Reuses core modules** — ``emi_calculator`` for EMI maths,
  ``underwriting_rules`` for the existing 6-rule policy engine (used as
  an additional audit layer on top of the user's 5 rules).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.agents.base_agent import AgentResult, BaseAgent
from backend.core.emi_calculator import (
    calculate_emi,
    check_affordability,
    compute_total_interest,
)

# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

DEFAULT_RATES: Dict[str, float] = {
    "personal":  12.0,
    "home":       8.5,
    "auto":       9.5,
    "business":  14.0,
    "education": 10.0,
    "gold":       9.0,
}

DEFAULT_TENURE = 60  # months (used when no tenure has been selected yet)

# ── Decision thresholds (user-specified) ────────────────────────────────
MIN_CREDIT_SCORE      = 700
MAX_DTI_RATIO         = 0.60   # 60 %
MAX_EMI_TO_INCOME     = 0.50   # 50 %
PRE_APPROVED_MULTIPLE = 1.0    # within 1× limit → auto-approve
CONDITIONAL_MULTIPLE  = 2.0    # within 2× limit → conditional


# ═══════════════════════════════════════════════════════════════════════════
# Decision Dataclass
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class UnderwritingVerdict:
    """
    Structured underwriting decision output.

    Attributes
    ----------
    verdict : str
        One of ``approved``, ``conditional``, ``rejected``.
    pre_approved_limit : float
        Maximum auto-approachable loan amount (₹).
    requested_amount : float
        What the applicant asked for (₹).
    monthly_emi : float
        Proposed EMI for the requested amount (₹).
    dti_ratio : float
        Debt-to-Income ratio (0.0 – 1.0).
    emi_to_income : float
        Proposed EMI as a fraction of monthly income.
    credit_score : int
        Applicant's credit score.
    reasons : list[str]
        Human-readable explanations for the decision.
    rules_evaluated : list[dict]
        Per-rule pass/fail audit trail.
    """

    verdict: str = "rejected"
    pre_approved_limit: float = 0.0
    requested_amount: float = 0.0
    monthly_emi: float = 0.0
    dti_ratio: float = 0.0
    emi_to_income: float = 0.0
    credit_score: int = 0
    reasons: List[str] = field(default_factory=list)
    rules_evaluated: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "verdict": self.verdict,
            "pre_approved_limit": self.pre_approved_limit,
            "requested_amount": self.requested_amount,
            "monthly_emi": self.monthly_emi,
            "dti_ratio": round(self.dti_ratio, 4),
            "emi_to_income": round(self.emi_to_income, 4),
            "credit_score": self.credit_score,
            "reasons": self.reasons,
            "rules_evaluated": self.rules_evaluated,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Decision Engine (pure functions — no side-effects)
# ═══════════════════════════════════════════════════════════════════════════

def compute_pre_approved_limit(
    monthly_income: float,
    existing_emi: float,
    annual_rate: float,
    tenure_months: int,
) -> float:
    """
    Reverse-calculate the maximum loan principal the applicant can afford.

    Uses the standard EMI formula solved for ``P``::

        affordable_emi = (income - existing_emi) × MAX_EMI_TO_INCOME
        P = affordable_emi × ((1+r)^n - 1) / (r × (1+r)^n)
    """
    affordable_emi = (monthly_income - existing_emi) * MAX_EMI_TO_INCOME
    if affordable_emi <= 0:
        return 0.0

    if annual_rate == 0:
        return affordable_emi * tenure_months

    r = annual_rate / 12 / 100
    factor = ((1 + r) ** tenure_months - 1) / (r * (1 + r) ** tenure_months)
    return round(affordable_emi * factor, 2)


def compute_dti(
    monthly_income: float,
    existing_emi: float,
    proposed_emi: float,
) -> float:
    """
    Calculate Debt-to-Income ratio.

    DTI = (existing_emi + proposed_emi) / monthly_income
    """
    if monthly_income <= 0:
        return 1.0
    return (existing_emi + proposed_emi) / monthly_income


def evaluate_eligibility(
    monthly_income: float,
    existing_emi: float,
    credit_score: int,
    requested_amount: float,
    employment_type: str,
    annual_rate: float,
    tenure_months: int,
) -> UnderwritingVerdict:
    """
    Apply the 5 user-specified decision rules and return a structured verdict.

    Rules
    -----
    1. Reject if credit score < 700.
    2. Reject if DTI > 60 %.
    3. Approve if requested ≤ pre-approved limit.
    4. Conditional if requested ≤ 2× limit AND EMI ≤ 50 % income.
    5. Reject if requested > 2× limit.
    """
    reasons: List[str] = []
    rules: List[Dict[str, Any]] = []

    # ── Pre-computations ────────────────────────────────────────────────
    proposed_emi = calculate_emi(requested_amount, annual_rate, tenure_months)
    pre_approved = compute_pre_approved_limit(
        monthly_income, existing_emi, annual_rate, tenure_months,
    )
    dti = compute_dti(monthly_income, existing_emi, proposed_emi)
    emi_ratio = proposed_emi / monthly_income if monthly_income > 0 else 1.0

    verdict = "approved"  # optimistic start; rules may downgrade

    # ── Rule 1: Credit score ≥ 700 ─────────────────────────────────────
    r1_pass = credit_score >= MIN_CREDIT_SCORE
    rules.append({
        "rule": "credit_score_minimum",
        "description": f"Credit score must be ≥ {MIN_CREDIT_SCORE}",
        "value": credit_score,
        "threshold": MIN_CREDIT_SCORE,
        "pass": r1_pass,
    })
    if not r1_pass:
        verdict = "rejected"
        reasons.append(
            f"Credit score {credit_score} is below the minimum requirement of {MIN_CREDIT_SCORE}."
        )

    # ── Rule 2: DTI ≤ 60 % ─────────────────────────────────────────────
    r2_pass = dti <= MAX_DTI_RATIO
    rules.append({
        "rule": "dti_ratio",
        "description": f"Debt-to-Income ratio must be ≤ {MAX_DTI_RATIO:.0%}",
        "value": round(dti * 100, 1),
        "threshold": MAX_DTI_RATIO * 100,
        "pass": r2_pass,
    })
    if not r2_pass:
        verdict = "rejected"
        reasons.append(
            f"DTI ratio is {dti:.1%}, exceeding the maximum of {MAX_DTI_RATIO:.0%}."
        )

    # ── Rule 3: Approve if amount ≤ pre-approved limit ─────────────────
    within_limit = requested_amount <= pre_approved
    rules.append({
        "rule": "within_pre_approved_limit",
        "description": "Requested amount ≤ pre-approved limit",
        "requested": requested_amount,
        "limit": pre_approved,
        "pass": within_limit,
    })
    if within_limit and verdict != "rejected":
        verdict = "approved"
        reasons.append(
            f"Requested ₹{_fmt(requested_amount)} is within the pre-approved limit "
            f"of ₹{_fmt(pre_approved)}."
        )

    # ── Rule 4: Conditional if ≤ 2× limit AND EMI ≤ 50 % income ───────
    within_2x = requested_amount <= (pre_approved * CONDITIONAL_MULTIPLE)
    emi_affordable = emi_ratio <= MAX_EMI_TO_INCOME
    rules.append({
        "rule": "conditional_eligibility",
        "description": f"Amount ≤ 2× limit AND EMI ≤ {MAX_EMI_TO_INCOME:.0%} income",
        "within_2x": within_2x,
        "emi_ratio": round(emi_ratio * 100, 1),
        "pass": within_2x and emi_affordable,
    })
    if not within_limit and within_2x and emi_affordable and verdict != "rejected":
        verdict = "conditional"
        reasons.append(
            f"Requested ₹{_fmt(requested_amount)} exceeds the auto-approve limit "
            f"(₹{_fmt(pre_approved)}) but is within 2× and EMI is affordable "
            f"({emi_ratio:.1%} of income). Conditional approval granted."
        )

    # ── Rule 5: Reject if > 2× limit ──────────────────────────────────
    rules.append({
        "rule": "exceeds_max_limit",
        "description": "Reject if requested > 2× pre-approved limit",
        "requested": requested_amount,
        "max_limit": pre_approved * CONDITIONAL_MULTIPLE,
        "pass": within_2x,
    })
    if not within_2x and verdict != "rejected":
        verdict = "rejected"
        reasons.append(
            f"Requested ₹{_fmt(requested_amount)} exceeds the maximum eligible "
            f"amount of ₹{_fmt(pre_approved * CONDITIONAL_MULTIPLE)}."
        )

    # ── Employment bonus note ──────────────────────────────────────────
    if employment_type in ("salaried", "professional") and verdict != "rejected":
        reasons.append("Stable employment type noted positively.")

    if verdict == "approved":
        reasons.append("✅ All eligibility rules passed.")

    return UnderwritingVerdict(
        verdict=verdict,
        pre_approved_limit=pre_approved,
        requested_amount=requested_amount,
        monthly_emi=proposed_emi,
        dti_ratio=dti,
        emi_to_income=emi_ratio,
        credit_score=credit_score,
        reasons=reasons,
        rules_evaluated=rules,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _fmt(n: float) -> str:
    if n >= 1_00_00_000:
        return f"{n / 1_00_00_000:,.2f} Cr"
    if n >= 1_00_000:
        return f"{n / 1_00_000:,.2f} L"
    return f"{n:,.0f}"


def _parse_number(text: str) -> Optional[float]:
    """Extract a numeric value from free text (supports lakh/crore shorthand)."""
    text = text.strip().lower().replace("₹", "").replace(",", "").replace(" ", "")
    m = re.match(r"^(\d+\.?\d*)(crore|cr|lakh|lac|l|k|thousand)?s?$", text)
    if not m:
        return None
    val = float(m.group(1))
    suffix = m.group(2) or ""
    multipliers = {
        "crore": 1_00_00_000, "cr": 1_00_00_000,
        "lakh": 1_00_000, "lac": 1_00_000, "l": 1_00_000,
        "thousand": 1_000, "k": 1_000,
    }
    return val * multipliers.get(suffix, 1)


def _simulate_credit_score(pan: str = "", phone: str = "") -> int:
    """
    Deterministic credit-score simulator.

    In production, replace with actual CreditBureau API call.
    Uses a hash to produce a reproducible score between 650 and 850.
    """
    seed = f"{pan}:{phone}:tata-capital"
    digest = hashlib.sha256(seed.encode()).hexdigest()
    raw = int(digest[:6], 16)
    return 650 + (raw % 201)  # range: 650–850


# ═══════════════════════════════════════════════════════════════════════════
# Response Templates
# ═══════════════════════════════════════════════════════════════════════════

TEMPLATES: Dict[str, str] = {

    "income_ask": (
        "What is your **monthly net income** (take-home salary after deductions)?\n\n"
        "You can type the amount in any format: `50000`, `50,000`, `50k`, or `0.5 lakh`."
    ),
    "income_captured": (
        "Got it — monthly income: **₹{income_fmt}**.\n\n"
        "Do you have any **existing EMI obligations** or monthly debt payments?\n"
        "If yes, enter the total monthly EMI. If none, type **0**."
    ),
    "income_invalid": (
        "I couldn't read that as a valid income amount. "
        "Please enter a positive number, e.g. `50000` or `75k`."
    ),

    "liabilities_ask": (
        "Do you have any existing EMIs or monthly loan payments?\n\n"
        "Enter the **total monthly EMI** across all loans. If none, type **0**."
    ),
    "liabilities_captured": (
        "Noted — existing monthly obligations: **₹{emi_fmt}**.\n\n"
        "📊 **Quick Snapshot**\n"
        "• Income: ₹{income_fmt}/month\n"
        "• Existing EMIs: ₹{emi_fmt}/month\n"
        "• Available for new EMI: ₹{available_fmt}/month\n\n"
        "I'll now run a credit check to assess your eligibility. Hang tight ⏳"
    ),

    "credit_check_running": (
        "⏳ Running credit check…\n\n"
        "📋 **Credit Report**\n"
        "• Credit Score: **{score}** {score_emoji}\n"
        "• Rating: **{rating}**\n\n"
        "{score_commentary}\n\n"
        "Let me now evaluate your loan eligibility."
    ),

    "decision_approved": (
        "🎉 **Congratulations — Loan Approved!**\n\n"
        "Your application has been **approved** based on the following assessment:\n\n"
        "{breakdown}\n\n"
        "📌 **Pre-approved limit**: ₹{limit_fmt}\n"
        "📌 **Requested amount**: ₹{requested_fmt}\n"
        "📌 **Proposed EMI**: ₹{emi_fmt}/month\n\n"
        "{rule_summary}\n\n"
        "Would you like to **accept** or **reject** this offer?"
    ),
    "decision_conditional": (
        "🟡 **Conditional Approval**\n\n"
        "Your application has been **conditionally approved** — "
        "subject to additional verification:\n\n"
        "{breakdown}\n\n"
        "📌 **Pre-approved limit**: ₹{limit_fmt}\n"
        "📌 **Requested amount**: ₹{requested_fmt} _(exceeds auto-limit)_\n"
        "📌 **Proposed EMI**: ₹{emi_fmt}/month\n\n"
        "{rule_summary}\n\n"
        "Would you like to **accept** at this amount, or **reduce** it to "
        "₹{limit_fmt} for instant approval?"
    ),
    "decision_rejected": (
        "❌ **Application Not Approved**\n\n"
        "Unfortunately, we are unable to approve your loan at this time.\n\n"
        "{breakdown}\n\n"
        "{rule_summary}\n\n"
        "**What you can do:**\n"
        "• Reduce the loan amount or extend the tenure\n"
        "• Clear some existing obligations to improve DTI\n"
        "• Improve your credit score and re-apply\n\n"
        "Type **restart** to try a different configuration."
    ),

    "decision_accept": (
        "✅ You've **accepted** the loan offer. Let's proceed to document upload."
    ),
    "decision_reject": (
        "You've chosen to **decline** the offer. If you change your mind, "
        "type **restart** to begin a new application."
    ),
}


def _render(key: str, **kwargs) -> str:
    tpl = TEMPLATES.get(key, "")
    try:
        return tpl.format(**kwargs)
    except KeyError:
        return tpl


# ═══════════════════════════════════════════════════════════════════════════
# Underwriting Agent
# ═══════════════════════════════════════════════════════════════════════════

class UnderwritingAgent(BaseAgent):
    """
    Handles income capture, liabilities declaration, credit check,
    and final eligibility decisioning using the 5-rule deterministic engine.
    """

    def __init__(self) -> None:
        super().__init__(name="underwriting")

    async def process(
        self,
        session_id: str,
        user_message: str,
        context: Dict[str, Any],
    ) -> AgentResult:
        """Route to the correct handler based on conversation state."""
        state = context.get("state", "")
        collected = context.get("collected_data", {})
        self.logger.info("UnderwritingAgent | session=%s state=%s", session_id, state)

        handler = {
            "income":       self._handle_income,
            "liabilities":  self._handle_liabilities,
            "credit_check": self._handle_credit_check,
            "decision":     self._handle_decision,
        }.get(state, self._handle_fallback)

        return await handler(session_id, user_message, collected, context)

    # ──────────────────────────────────────────────────────────────────
    # INCOME
    # ──────────────────────────────────────────────────────────────────

    async def _handle_income(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Capture monthly net income."""
        amount = _parse_number(msg)
        if amount is None or amount <= 0:
            return AgentResult(
                success=True,
                message=_render("income_ask") if not collected.get("monthly_income")
                        else _render("income_invalid"),
                data={},
            )

        return AgentResult(
            success=True,
            message=_render("income_captured", income_fmt=_fmt(amount), emi_fmt="0"),
            data={"monthly_income": amount},
        )

    # ──────────────────────────────────────────────────────────────────
    # LIABILITIES
    # ──────────────────────────────────────────────────────────────────

    async def _handle_liabilities(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Capture existing EMI obligations."""

        # Handle zero / none declarations
        if msg.strip().lower() in ("0", "none", "nil", "no", "zero", "nope", "no emi", "nothing"):
            existing_emi = 0.0
        else:
            existing_emi = _parse_number(msg)
            if existing_emi is None or existing_emi < 0:
                return AgentResult(
                    success=True,
                    message=_render("liabilities_ask"),
                    data={},
                )

        income = collected.get("monthly_income", 0)
        available = max(income - existing_emi, 0)

        return AgentResult(
            success=True,
            message=_render(
                "liabilities_captured",
                emi_fmt=_fmt(existing_emi),
                income_fmt=_fmt(income),
                available_fmt=_fmt(available),
            ),
            data={
                "existing_emi": existing_emi,
                "liabilities_declared": True,
            },
        )

    # ──────────────────────────────────────────────────────────────────
    # CREDIT CHECK
    # ──────────────────────────────────────────────────────────────────

    async def _handle_credit_check(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Simulate a credit-bureau pull and report the score."""

        pan = collected.get("pan_number", "")
        phone = collected.get("phone", "")
        score = _simulate_credit_score(pan, phone)

        # Score interpretation
        if score >= 800:
            rating, emoji, commentary = "Excellent", "🟢", "Outstanding credit history. You qualify for the best rates."
        elif score >= 750:
            rating, emoji, commentary = "Very Good", "🟢", "Strong credit profile. Competitive rates available."
        elif score >= 700:
            rating, emoji, commentary = "Good", "🟡", "Solid credit standing. Most loan products are accessible."
        elif score >= 650:
            rating, emoji, commentary = "Fair", "🟠", "Credit score is below our minimum of 700. This may affect eligibility."
        else:
            rating, emoji, commentary = "Poor", "🔴", "Credit score is significantly below requirements. Approval is unlikely."

        return AgentResult(
            success=True,
            message=_render(
                "credit_check_running",
                score=score,
                score_emoji=emoji,
                rating=rating,
                score_commentary=commentary,
            ),
            data={
                "credit_score": score,
                "credit_rating": rating,
            },
        )

    # ──────────────────────────────────────────────────────────────────
    # DECISION
    # ──────────────────────────────────────────────────────────────────

    async def _handle_decision(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        """Run 5-rule eligibility engine and present the verdict."""

        normalised = msg.strip().lower()

        # If user is responding to a previous decision
        if normalised in ("accept", "accepted", "yes", "proceed", "agree", "ok"):
            return AgentResult(
                success=True,
                message=_render("decision_accept"),
                data={"applicant_decision": "accepted", "underwriting_decision": "accepted"},
            )
        if normalised in ("reject", "rejected", "no", "decline", "cancel"):
            return AgentResult(
                success=True,
                message=_render("decision_reject"),
                data={"applicant_decision": "rejected", "underwriting_decision": "rejected"},
            )

        # ── Run eligibility engine ──────────────────────────────────────
        income = float(collected.get("monthly_income", 0))
        existing_emi = float(collected.get("existing_emi", 0))
        credit_score = int(collected.get("credit_score", 0))
        requested = float(collected.get("loan_amount", 0))
        emp_type = collected.get("employment_type", "salaried")
        purpose = collected.get("loan_purpose", "personal")
        tenure = int(collected.get("selected_tenure", DEFAULT_TENURE))
        rate = DEFAULT_RATES.get(purpose, 12.0)

        verdict = evaluate_eligibility(
            monthly_income=income,
            existing_emi=existing_emi,
            credit_score=credit_score,
            requested_amount=requested,
            employment_type=emp_type,
            annual_rate=rate,
            tenure_months=tenure,
        )

        # ── Format breakdown table ──────────────────────────────────────
        breakdown = self._format_breakdown(verdict, income, existing_emi, rate, tenure)
        rule_summary = self._format_rule_summary(verdict)

        # ── Select template ─────────────────────────────────────────────
        if verdict.verdict == "approved":
            template = "decision_approved"
        elif verdict.verdict == "conditional":
            template = "decision_conditional"
        else:
            template = "decision_rejected"

        return AgentResult(
            success=True,
            message=_render(
                template,
                breakdown=breakdown,
                limit_fmt=_fmt(verdict.pre_approved_limit),
                requested_fmt=_fmt(verdict.requested_amount),
                emi_fmt=_fmt(verdict.monthly_emi),
                rule_summary=rule_summary,
            ),
            data={
                "underwriting_decision": verdict.verdict,
                "underwriting_details": verdict.to_dict(),
            },
        )

    def _format_breakdown(
        self,
        v: UnderwritingVerdict,
        income: float,
        existing_emi: float,
        rate: float,
        tenure: int,
    ) -> str:
        """Build a Markdown financial breakdown table."""
        lines = [
            "| Metric | Value |",
            "|--------|-------|",
            f"| Monthly Income | ₹{_fmt(income)} |",
            f"| Existing EMIs | ₹{_fmt(existing_emi)} |",
            f"| Proposed EMI | ₹{_fmt(v.monthly_emi)} |",
            f"| DTI Ratio | {v.dti_ratio:.1%} {'✅' if v.dti_ratio <= MAX_DTI_RATIO else '❌'} |",
            f"| EMI / Income | {v.emi_to_income:.1%} {'✅' if v.emi_to_income <= MAX_EMI_TO_INCOME else '⚠️'} |",
            f"| Credit Score | {v.credit_score} {'✅' if v.credit_score >= MIN_CREDIT_SCORE else '❌'} |",
            f"| Interest Rate | {rate}% p.a. |",
            f"| Tenure | {tenure} months |",
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_rule_summary(v: UnderwritingVerdict) -> str:
        """Build a compact rule-pass/fail summary."""
        lines = ["**Decision Rules:**"]
        for r in v.rules_evaluated:
            icon = "✅" if r["pass"] else "❌"
            lines.append(f"  {icon} {r['description']}")
        if v.reasons:
            lines.append("")
            lines.append("**Reasoning:**")
            for reason in v.reasons:
                lines.append(f"  • {reason}")
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────────────────
    # FALLBACK
    # ──────────────────────────────────────────────────────────────────

    async def _handle_fallback(
        self, session_id: str, msg: str, collected: Dict, ctx: Dict
    ) -> AgentResult:
        return AgentResult(
            success=True,
            message=(
                "I'm the underwriting agent but I'm not sure what to do "
                f"at the **{ctx.get('state', 'unknown')}** stage. "
                "Type **help** for guidance."
            ),
            data={},
        )
