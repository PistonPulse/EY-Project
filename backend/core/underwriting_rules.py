"""
underwriting_rules.py
=====================

Deterministic rule engine for credit policy and loan eligibility.

Responsibilities
----------------
- Evaluate an applicant profile against configurable underwriting rules.
- Return an ``UnderwritingDecision`` (APPROVE / REFER / REJECT) with rationale.
- Apply the following rule checks:
    1. **Credit-score threshold** — minimum CIBIL score for each product.
    2. **FOIR cap** — Fixed Obligation-to-Income Ratio must be ≤ threshold.
    3. **LTV ratio** — Loan-to-Value ratio for secured loans.
    4. **Age eligibility** — min / max age at maturity.
    5. **Employer / income stability** — minimum employment tenure.
    6. **Policy caps** — maximum loan amount per product category.

Design Notes
------------
- Rules are intentionally **deterministic** (no ML) so that every decision
  is fully auditable and explainable — a core compliance requirement.
- Rule parameters are defined as module-level constants; they can be
  externalised to a config file or database in production.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

from backend.core.emi_calculator import calculate_emi, check_affordability
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ── Rule parameter constants ─────────────────────────────────────────────

MIN_CREDIT_SCORE = 650
MAX_FOIR = 0.50           # 50 %
MAX_LTV = 0.80            # 80 % (for secured loans)
MIN_AGE = 21
MAX_AGE_AT_MATURITY = 60
MIN_EMPLOYMENT_MONTHS = 12
MAX_PERSONAL_LOAN = 2_500_000       # ₹25 lakh
MAX_HOME_LOAN = 50_000_000          # ₹5 crore
MAX_AUTO_LOAN = 10_000_000          # ₹1 crore


class Decision(str, Enum):
    """Underwriting decision outcome."""
    APPROVE = "approve"
    REFER = "refer"
    REJECT = "reject"


@dataclass
class UnderwritingDecision:
    """
    Result of the underwriting evaluation.

    Attributes
    ----------
    decision : Decision
        Final decision: APPROVE, REFER, or REJECT.
    max_eligible_amount : float
        Maximum loan amount the applicant qualifies for (₹).
    reasons : list[str]
        Human-readable reasons supporting the decision.
    rule_results : dict
        Detailed pass/fail result per rule for audit logging.
    """

    decision: Decision = Decision.REJECT
    max_eligible_amount: float = 0.0
    reasons: List[str] = field(default_factory=list)
    rule_results: Dict[str, Any] = field(default_factory=dict)


def evaluate(
    credit_score: int,
    monthly_income: float,
    requested_amount: float,
    existing_obligations: float = 0.0,
    age: int = 30,
    employment_months: int = 24,
    loan_type: str = "personal",
    property_value: float = 0.0,
    annual_rate: float = 10.5,
    tenure_months: int = 60,
) -> UnderwritingDecision:
    """
    Run all underwriting rules against the applicant profile.

    Parameters
    ----------
    credit_score : int
        Applicant's CIBIL / credit score.
    monthly_income : float
        Net monthly income (₹).
    requested_amount : float
        Loan amount requested by the applicant (₹).
    existing_obligations : float
        Total existing monthly EMI obligations (₹).
    age : int
        Applicant's current age in years.
    employment_months : int
        Duration of current employment in months.
    loan_type : str
        Loan product category (``personal``, ``home``, ``auto``).
    property_value : float
        Property value for secured (home / auto) loans (₹).
    annual_rate : float
        Assumed annual interest rate for EMI calculation.
    tenure_months : int
        Proposed loan tenure in months.

    Returns
    -------
    UnderwritingDecision
        Decision with reasons and per-rule audit trail.
    """
    reasons: List[str] = []
    rule_results: Dict[str, Any] = {}
    reject = False

    # ── Rule 1: Credit-score threshold ──────────────────────────────────
    score_pass = credit_score >= MIN_CREDIT_SCORE
    rule_results["credit_score"] = {"value": credit_score, "min": MIN_CREDIT_SCORE, "pass": score_pass}
    if not score_pass:
        reasons.append(f"Credit score {credit_score} is below minimum {MIN_CREDIT_SCORE}.")
        reject = True

    # ── Rule 2: Age eligibility ─────────────────────────────────────────
    age_at_maturity = age + (tenure_months // 12)
    age_pass = MIN_AGE <= age and age_at_maturity <= MAX_AGE_AT_MATURITY
    rule_results["age"] = {"current": age, "at_maturity": age_at_maturity, "pass": age_pass}
    if not age_pass:
        reasons.append(f"Age {age} (maturity {age_at_maturity}) outside {MIN_AGE}–{MAX_AGE_AT_MATURITY} window.")
        reject = True

    # ── Rule 3: Employment stability ────────────────────────────────────
    emp_pass = employment_months >= MIN_EMPLOYMENT_MONTHS
    rule_results["employment"] = {"months": employment_months, "min": MIN_EMPLOYMENT_MONTHS, "pass": emp_pass}
    if not emp_pass:
        reasons.append(f"Employment tenure {employment_months}m is below minimum {MIN_EMPLOYMENT_MONTHS}m.")

    # ── Rule 4: FOIR cap ────────────────────────────────────────────────
    proposed_emi = calculate_emi(requested_amount, annual_rate, tenure_months)
    total_obligations = existing_obligations + proposed_emi
    foir = total_obligations / monthly_income if monthly_income > 0 else 1.0
    foir_pass = foir <= MAX_FOIR
    rule_results["foir"] = {"value": round(foir, 4), "max": MAX_FOIR, "pass": foir_pass}
    if not foir_pass:
        reasons.append(f"FOIR {foir:.1%} exceeds cap of {MAX_FOIR:.0%}.")
        reject = True

    # ── Rule 5: Policy cap ──────────────────────────────────────────────
    cap_map = {"personal": MAX_PERSONAL_LOAN, "home": MAX_HOME_LOAN, "auto": MAX_AUTO_LOAN}
    policy_cap = cap_map.get(loan_type, MAX_PERSONAL_LOAN)
    cap_pass = requested_amount <= policy_cap
    rule_results["policy_cap"] = {"requested": requested_amount, "cap": policy_cap, "pass": cap_pass}
    if not cap_pass:
        reasons.append(f"Requested ₹{requested_amount:,.0f} exceeds policy cap ₹{policy_cap:,.0f}.")
        reject = True

    # ── Rule 6: LTV ratio (secured loans only) ──────────────────────────
    if loan_type in ("home", "auto") and property_value > 0:
        ltv = requested_amount / property_value
        ltv_pass = ltv <= MAX_LTV
        rule_results["ltv"] = {"value": round(ltv, 4), "max": MAX_LTV, "pass": ltv_pass}
        if not ltv_pass:
            reasons.append(f"LTV {ltv:.1%} exceeds maximum {MAX_LTV:.0%}.")
            reject = True

    # ── Final decision ──────────────────────────────────────────────────
    if reject:
        decision = Decision.REJECT
    elif not emp_pass:
        decision = Decision.REFER
        reasons.append("Referred for manual review due to employment stability concern.")
    else:
        decision = Decision.APPROVE
        reasons.append("All underwriting rules passed.")

    max_eligible = requested_amount if decision == Decision.APPROVE else 0.0

    logger.info("Underwriting decision=%s for amount=%.0f", decision.value, requested_amount)

    return UnderwritingDecision(
        decision=decision,
        max_eligible_amount=max_eligible,
        reasons=reasons,
        rule_results=rule_results,
    )
