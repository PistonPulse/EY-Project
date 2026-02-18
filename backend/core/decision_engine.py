"""
decision_engine.py
==================

Compliance-safe, deterministic decision engine for loan eligibility.

This module is the **single source of truth** for the final loan decision.
It combines four inputs into one auditable output:

1. **Underwriting rules** — 6-rule policy engine from ``underwriting_rules.py``.
2. **EMI affordability** — FOIR-gated check from ``emi_calculator.py``.
3. **Credit score** — band-based risk classification.
4. **DTI ratio** — Debt-to-Income ratio with hard/soft caps.

Returns
-------
``DecisionResult`` containing:
- ``decision``  — ``approved`` | ``conditional`` | ``referred`` | ``rejected``
- ``reasons``   — list of human-readable explanations
- ``maximum_eligible_amount`` — computed from the strictest binding constraint

Design Principles
-----------------
- **No ML** — every rule is deterministic and auditable.
- **Compliance-safe** — decisions trace back to named rules with thresholds.
- **Constraint binding** — the max eligible amount is the *minimum* of all
  individual caps (income-based, FOIR-based, policy-based, LTV-based).
- **RBI-aligned** — FOIR, LTV, and age limits follow standard Indian
  lending norms.

Architecture
------------
::

    ┌─────────────────────────────────────────────────────┐
    │                  DecisionEngine.decide()             │
    │                                                     │
    │   ┌──────────────┐  ┌───────────────┐               │
    │   │ Underwriting │  │     EMI       │               │
    │   │    Rules      │  │  Calculator   │               │
    │   │  (6 rules)   │  │ (affordability)│               │
    │   └──────┬───────┘  └──────┬────────┘               │
    │          │                 │                         │
    │   ┌──────┴───────┐  ┌─────┴─────────┐              │
    │   │ Credit Score  │  │   DTI Ratio    │              │
    │   │  (4 bands)   │  │  (hard/soft)   │              │
    │   └──────┬───────┘  └──────┬────────┘               │
    │          │                 │                         │
    │          └────────┬────────┘                         │
    │                   ▼                                  │
    │          DecisionResult                              │
    │   { decision, reasons, max_eligible_amount,          │
    │     rule_audit, risk_grade }                         │
    └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from backend.core.emi_calculator import (
    calculate_emi,
    check_affordability,
    compute_total_interest,
)
from backend.core.underwriting_rules import (
    Decision as UWDecision,
    UnderwritingDecision,
    evaluate as uw_evaluate,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Policy Constants
# ═══════════════════════════════════════════════════════════════════════════

# Credit score thresholds
SCORE_REJECT      = 650   # below → hard reject
SCORE_REFER       = 700   # 650–699 → refer for manual review
SCORE_CONDITIONAL = 750   # 700–749 → conditional approval possible
SCORE_APPROVE     = 750   # ≥ 750 → auto-approve eligible

# DTI thresholds
DTI_HARD_CAP      = 0.60  # above 60 % → reject
DTI_SOFT_CAP      = 0.50  # 50–60 % → conditional / reduced amount
DTI_COMFORTABLE   = 0.40  # ≤ 40 % → comfortable zone

# FOIR — Fixed Obligation to Income Ratio
MAX_FOIR          = 0.50  # EMI cannot exceed 50 % of income (RBI norm)

# Income multipliers for max-eligible calculation
INCOME_MULTIPLIERS: Dict[str, int] = {
    "personal":  15,
    "home":      60,
    "auto":      20,
    "business":  12,
    "education": 18,
    "gold":      10,
}

# Policy caps per loan type (₹)
POLICY_CAPS: Dict[str, float] = {
    "personal":   25_00_000,
    "home":     5_00_00_000,
    "auto":     1_00_00_000,
    "business":   50_00_000,
    "education":  20_00_000,
    "gold":       10_00_000,
}

# Base interest rates
BASE_RATES: Dict[str, float] = {
    "personal": 12.0, "home": 8.5, "auto": 9.5,
    "business": 14.0, "education": 10.0, "gold": 9.0,
}

# Default max tenure for each type (months)
MAX_TENURES: Dict[str, int] = {
    "personal": 60, "home": 300, "auto": 72,
    "business": 60, "education": 84, "gold": 36,
}


# ═══════════════════════════════════════════════════════════════════════════
# Enums & Data Models
# ═══════════════════════════════════════════════════════════════════════════

class FinalDecision(str, Enum):
    """Compliance-safe decision outcome."""
    APPROVED    = "approved"
    CONDITIONAL = "conditional"
    REFERRED    = "referred"
    REJECTED    = "rejected"


class RiskGrade(str, Enum):
    """Risk grading for the applicant."""
    LOW       = "low"
    MODERATE  = "moderate"
    HIGH      = "high"
    VERY_HIGH = "very_high"


@dataclass
class RuleAudit:
    """Audit record for a single rule evaluation."""
    rule_name: str
    description: str
    value: Any
    threshold: Any
    passed: bool
    impact: str = ""  # "blocking" or "advisory"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule": self.rule_name,
            "description": self.description,
            "value": self.value,
            "threshold": self.threshold,
            "passed": self.passed,
            "impact": self.impact,
        }


@dataclass
class DecisionResult:
    """
    Final, compliance-safe decision output.

    Attributes
    ----------
    decision : FinalDecision
        One of approved, conditional, referred, rejected.
    reasons : list[str]
        Human-readable explanations for the decision.
    maximum_eligible_amount : float
        The max loan amount the applicant qualifies for (₹),
        computed as the minimum of all binding constraints.
    requested_amount : float
        What the applicant originally asked for.
    proposed_emi : float
        EMI for the requested (or eligible) amount.
    credit_score : int
        Applicant's credit score.
    dti_ratio : float
        Debt-to-Income ratio (0.0–1.0).
    foir : float
        Fixed Obligation-to-Income ratio (0.0–1.0).
    risk_grade : RiskGrade
        Overall risk assessment.
    rule_audit : list[RuleAudit]
        Per-rule pass/fail audit trail.
    binding_constraint : str
        The name of the tightest constraint that capped the eligible amount.
    underwriting_result : UnderwritingDecision or None
        Raw result from the policy engine (for deep audit).
    """

    decision: FinalDecision = FinalDecision.REJECTED
    reasons: List[str] = field(default_factory=list)
    maximum_eligible_amount: float = 0.0
    requested_amount: float = 0.0
    proposed_emi: float = 0.0
    credit_score: int = 0
    dti_ratio: float = 0.0
    foir: float = 0.0
    risk_grade: RiskGrade = RiskGrade.VERY_HIGH
    rule_audit: List[RuleAudit] = field(default_factory=list)
    binding_constraint: str = ""
    underwriting_result: Optional[UnderwritingDecision] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision": self.decision.value,
            "reasons": self.reasons,
            "maximum_eligible_amount": self.maximum_eligible_amount,
            "requested_amount": self.requested_amount,
            "proposed_emi": self.proposed_emi,
            "credit_score": self.credit_score,
            "dti_ratio": round(self.dti_ratio, 4),
            "foir": round(self.foir, 4),
            "risk_grade": self.risk_grade.value,
            "rule_audit": [r.to_dict() for r in self.rule_audit],
            "binding_constraint": self.binding_constraint,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Max Eligible Amount Computation (Core Logic)
# ═══════════════════════════════════════════════════════════════════════════

def _compute_foir_limit(
    monthly_income: float,
    existing_emi: float,
    annual_rate: float,
    tenure_months: int,
) -> float:
    """
    Maximum loan amount allowed by the FOIR cap.

    affordable_emi = (income - existing_emi) × MAX_FOIR
    P = affordable_emi × ((1+r)^n - 1) / (r × (1+r)^n)
    """
    affordable_emi = (monthly_income - existing_emi) * MAX_FOIR
    if affordable_emi <= 0:
        return 0.0
    if annual_rate == 0:
        return affordable_emi * tenure_months
    r = annual_rate / 12 / 100
    factor = ((1 + r) ** tenure_months - 1) / (r * (1 + r) ** tenure_months)
    return round(affordable_emi * factor, 2)


def _compute_dti_limit(
    monthly_income: float,
    existing_emi: float,
    annual_rate: float,
    tenure_months: int,
) -> float:
    """
    Maximum loan amount allowed by the DTI soft cap (50%).
    Same as FOIR limit — DTI soft cap mirrors FOIR for consistency.
    """
    return _compute_foir_limit(monthly_income, existing_emi, annual_rate, tenure_months)


def _compute_income_multiplier_limit(
    monthly_income: float,
    loan_type: str,
) -> float:
    """Max amount based on income multiplier."""
    mult = INCOME_MULTIPLIERS.get(loan_type, 15)
    return round(monthly_income * mult, 2)


def _compute_dti(
    monthly_income: float,
    existing_emi: float,
    proposed_emi: float,
) -> float:
    """Debt-to-Income ratio."""
    if monthly_income <= 0:
        return 1.0
    return (existing_emi + proposed_emi) / monthly_income


def _compute_foir(
    monthly_income: float,
    existing_emi: float,
    proposed_emi: float,
) -> float:
    """Fixed Obligation-to-Income Ratio."""
    return _compute_dti(monthly_income, existing_emi, proposed_emi)


def _classify_risk(credit_score: int, dti: float, foir: float) -> RiskGrade:
    """Classify overall risk based on combined signals."""
    risk_points = 0

    # Credit score contribution
    if credit_score >= 800:
        risk_points += 0
    elif credit_score >= 750:
        risk_points += 1
    elif credit_score >= 700:
        risk_points += 2
    elif credit_score >= 650:
        risk_points += 3
    else:
        risk_points += 5

    # DTI contribution
    if dti <= DTI_COMFORTABLE:
        risk_points += 0
    elif dti <= DTI_SOFT_CAP:
        risk_points += 1
    elif dti <= DTI_HARD_CAP:
        risk_points += 2
    else:
        risk_points += 4

    # Map to grade
    if risk_points <= 1:
        return RiskGrade.LOW
    elif risk_points <= 3:
        return RiskGrade.MODERATE
    elif risk_points <= 5:
        return RiskGrade.HIGH
    else:
        return RiskGrade.VERY_HIGH


# ═══════════════════════════════════════════════════════════════════════════
# Decision Engine (Main Entry Point)
# ═══════════════════════════════════════════════════════════════════════════

class DecisionEngine:
    """
    Compliance-safe, deterministic decision engine.

    Combines underwriting rules, EMI affordability, credit score band,
    and DTI ratio into a single auditable decision with the maximum
    eligible loan amount.

    Usage::

        engine = DecisionEngine()
        result = engine.decide(
            credit_score=750,
            monthly_income=80_000,
            existing_emi=5_000,
            requested_amount=5_00_000,
            loan_type="personal",
            tenure_months=60,
        )
        print(result.decision)                  # "approved"
        print(result.maximum_eligible_amount)   # 820000.0
        print(result.reasons)                   # ["All rules passed.", ...]
    """

    def decide(
        self,
        credit_score: int,
        monthly_income: float,
        existing_emi: float,
        requested_amount: float,
        loan_type: str = "personal",
        tenure_months: int = 60,
        employment_type: str = "salaried",
        employment_months: int = 24,
        age: int = 30,
        property_value: float = 0.0,
        annual_rate: Optional[float] = None,
    ) -> DecisionResult:
        """
        Run the full decision engine and return a compliance-safe result.

        Parameters
        ----------
        credit_score : int
            Applicant's credit score (300–900).
        monthly_income : float
            Net monthly income (₹).
        existing_emi : float
            Total existing monthly EMI obligations (₹).
        requested_amount : float
            Loan amount requested (₹).
        loan_type : str
            Product category.
        tenure_months : int
            Proposed tenure in months.
        employment_type : str
            Employment classification.
        employment_months : int
            Current employment duration in months.
        age : int
            Applicant's age in years.
        property_value : float
            Property value for secured loans (₹).
        annual_rate : float or None
            Interest rate; defaults to product base rate.

        Returns
        -------
        DecisionResult
            Complete decision with reasons, max eligible amount, and audit trail.
        """
        rate = annual_rate or BASE_RATES.get(loan_type, 12.0)
        max_tenure = MAX_TENURES.get(loan_type, 60)
        policy_cap = POLICY_CAPS.get(loan_type, 25_00_000)

        audit: List[RuleAudit] = []
        reasons: List[str] = []
        hard_reject = False

        # ═══════════════════════════════════════════════════════════════
        # STEP 1: Run the 6-rule underwriting engine
        # ═══════════════════════════════════════════════════════════════
        uw_result = uw_evaluate(
            credit_score=credit_score,
            monthly_income=monthly_income,
            requested_amount=requested_amount,
            existing_obligations=existing_emi,
            age=age,
            employment_months=employment_months,
            loan_type=loan_type,
            property_value=property_value,
            annual_rate=rate,
            tenure_months=tenure_months,
        )

        # ═══════════════════════════════════════════════════════════════
        # STEP 2: Credit Score Evaluation
        # ═══════════════════════════════════════════════════════════════
        cs_pass = credit_score >= SCORE_REJECT
        audit.append(RuleAudit(
            rule_name="credit_score_minimum",
            description=f"Credit score must be ≥ {SCORE_REJECT}",
            value=credit_score,
            threshold=SCORE_REJECT,
            passed=cs_pass,
            impact="blocking",
        ))
        if not cs_pass:
            hard_reject = True
            reasons.append(
                f"Credit score {credit_score} is below the hard floor of {SCORE_REJECT}."
            )

        cs_auto = credit_score >= SCORE_APPROVE
        audit.append(RuleAudit(
            rule_name="credit_score_auto_approve",
            description=f"Auto-approve threshold ≥ {SCORE_APPROVE}",
            value=credit_score,
            threshold=SCORE_APPROVE,
            passed=cs_auto,
            impact="advisory",
        ))
        if cs_pass and not cs_auto:
            reasons.append(
                f"Credit score {credit_score} is in the review zone "
                f"({SCORE_REJECT}–{SCORE_APPROVE - 1})."
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 3: EMI Affordability (FOIR)
        # ═══════════════════════════════════════════════════════════════
        proposed_emi = calculate_emi(requested_amount, rate, tenure_months)
        foir = _compute_foir(monthly_income, existing_emi, proposed_emi)
        foir_pass = foir <= MAX_FOIR

        audit.append(RuleAudit(
            rule_name="emi_affordability_foir",
            description=f"FOIR must be ≤ {MAX_FOIR:.0%}",
            value=f"{foir:.1%}",
            threshold=f"{MAX_FOIR:.0%}",
            passed=foir_pass,
            impact="blocking",
        ))
        if not foir_pass:
            reasons.append(
                f"FOIR is {foir:.1%}, exceeding the RBI-compliant cap of {MAX_FOIR:.0%}. "
                f"EMI ₹{proposed_emi:,.0f} is unaffordable against income ₹{monthly_income:,.0f}."
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 4: DTI Ratio
        # ═══════════════════════════════════════════════════════════════
        dti = _compute_dti(monthly_income, existing_emi, proposed_emi)

        dti_hard_pass = dti <= DTI_HARD_CAP
        audit.append(RuleAudit(
            rule_name="dti_hard_cap",
            description=f"DTI must be ≤ {DTI_HARD_CAP:.0%}",
            value=f"{dti:.1%}",
            threshold=f"{DTI_HARD_CAP:.0%}",
            passed=dti_hard_pass,
            impact="blocking",
        ))
        if not dti_hard_pass:
            hard_reject = True
            reasons.append(
                f"DTI ratio {dti:.1%} exceeds the hard cap of {DTI_HARD_CAP:.0%}."
            )

        dti_soft_pass = dti <= DTI_SOFT_CAP
        audit.append(RuleAudit(
            rule_name="dti_soft_cap",
            description=f"DTI comfort zone ≤ {DTI_SOFT_CAP:.0%}",
            value=f"{dti:.1%}",
            threshold=f"{DTI_SOFT_CAP:.0%}",
            passed=dti_soft_pass,
            impact="advisory",
        ))
        if dti_hard_pass and not dti_soft_pass:
            reasons.append(
                f"DTI ratio {dti:.1%} is between the soft ({DTI_SOFT_CAP:.0%}) "
                f"and hard ({DTI_HARD_CAP:.0%}) caps — reduced amount may apply."
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 5: Policy Cap
        # ═══════════════════════════════════════════════════════════════
        cap_pass = requested_amount <= policy_cap
        audit.append(RuleAudit(
            rule_name="policy_cap",
            description=f"Amount ≤ policy cap ₹{policy_cap:,.0f}",
            value=f"₹{requested_amount:,.0f}",
            threshold=f"₹{policy_cap:,.0f}",
            passed=cap_pass,
            impact="blocking",
        ))
        if not cap_pass:
            reasons.append(
                f"Requested ₹{requested_amount:,.0f} exceeds the "
                f"{loan_type} loan policy cap of ₹{policy_cap:,.0f}."
            )

        # ═══════════════════════════════════════════════════════════════
        # STEP 6: Compute Maximum Eligible Amount
        # ═══════════════════════════════════════════════════════════════
        # Take the minimum of all individual limits (binding constraint)
        limits: Dict[str, float] = {}

        # 6a. FOIR-based limit (reverse-EMI from affordable EMI)
        foir_limit = _compute_foir_limit(monthly_income, existing_emi, rate, tenure_months)
        limits["foir_limit"] = foir_limit

        # 6b. Income multiplier limit
        income_limit = _compute_income_multiplier_limit(monthly_income, loan_type)
        limits["income_multiplier_limit"] = income_limit

        # 6c. Policy cap
        limits["policy_cap"] = policy_cap

        # 6d. LTV limit (secured loans)
        if loan_type in ("home", "auto") and property_value > 0:
            ltv_limit = property_value * 0.80
            limits["ltv_limit"] = ltv_limit

        # The max eligible = minimum of all limits
        max_eligible = min(limits.values()) if limits else 0.0
        max_eligible = round(max(max_eligible, 0), 2)

        # Find which constraint is binding
        binding = min(limits, key=limits.get) if limits else "none"

        audit.append(RuleAudit(
            rule_name="max_eligible_computation",
            description="Maximum eligible = min(all individual caps)",
            value=f"₹{max_eligible:,.0f}",
            threshold={k: f"₹{v:,.0f}" for k, v in limits.items()},
            passed=requested_amount <= max_eligible,
            impact="blocking",
        ))

        # ═══════════════════════════════════════════════════════════════
        # STEP 7: Final Decision
        # ═══════════════════════════════════════════════════════════════
        risk_grade = _classify_risk(credit_score, dti, foir)

        if hard_reject or credit_score < SCORE_REJECT:
            decision = FinalDecision.REJECTED
            max_eligible = 0.0
            reasons.append("❌ Application rejected due to policy violations.")

        elif uw_result.decision == UWDecision.REJECT:
            decision = FinalDecision.REJECTED
            max_eligible = 0.0
            reasons.extend(uw_result.reasons)

        elif credit_score < SCORE_REFER:
            decision = FinalDecision.REFERRED
            reasons.append(
                "Application referred for manual review (credit score in review zone)."
            )

        elif requested_amount <= max_eligible and cs_auto and dti_soft_pass:
            decision = FinalDecision.APPROVED
            reasons.append("✅ All eligibility rules passed — approved.")

        elif requested_amount <= max_eligible:
            decision = FinalDecision.CONDITIONAL
            reasons.append(
                "Conditionally approved — subject to additional verification."
            )

        else:
            # Requested exceeds eligible, but eligible > 0
            if max_eligible > 0:
                decision = FinalDecision.CONDITIONAL
                reasons.append(
                    f"Requested ₹{requested_amount:,.0f} exceeds your maximum eligible "
                    f"amount of ₹{max_eligible:,.0f}. Conditional approval for the "
                    f"eligible amount."
                )
            else:
                decision = FinalDecision.REJECTED
                reasons.append("No eligible amount could be determined.")

        # EMI for the eligible amount (for reporting)
        eligible_emi = calculate_emi(
            min(requested_amount, max_eligible) if max_eligible > 0 else 0,
            rate,
            tenure_months,
        )

        logger.info(
            "DecisionEngine | decision=%s max_eligible=%.0f binding=%s "
            "score=%d dti=%.2f foir=%.2f risk=%s",
            decision.value, max_eligible, binding,
            credit_score, dti, foir, risk_grade.value,
        )

        return DecisionResult(
            decision=decision,
            reasons=reasons,
            maximum_eligible_amount=max_eligible,
            requested_amount=requested_amount,
            proposed_emi=eligible_emi,
            credit_score=credit_score,
            dti_ratio=dti,
            foir=foir,
            risk_grade=risk_grade,
            rule_audit=audit,
            binding_constraint=binding,
            underwriting_result=uw_result,
        )


# ═══════════════════════════════════════════════════════════════════════════
# Module-Level Convenience
# ═══════════════════════════════════════════════════════════════════════════

# Singleton instance for simple imports
engine = DecisionEngine()


def decide(**kwargs) -> DecisionResult:
    """Module-level shortcut for ``DecisionEngine().decide(...)``."""
    return engine.decide(**kwargs)
