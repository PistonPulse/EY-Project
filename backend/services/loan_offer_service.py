"""
loan_offer_service.py
=====================

Loan offer generation and comparison service.

Simulated Endpoint
------------------
``GET /offer``  →  :meth:`LoanOfferService.generate_offer`

Returns:
- **Pre-approved loan limit** (calculated via income multiplier logic).
- **Interest rate range** (min–max based on credit score band).
- Multiple offer variants across different tenures for comparison.

Income Multiplier Logic
-----------------------
::

    net_monthly_income × multiplier = pre-approved limit

Multipliers vary by loan type:
    - Personal:    15×
    - Home:        60×
    - Auto:        20×
    - Business:    12×
    - Education:   18×
    - Gold:        10×

The limit is then capped by FOIR (50 %) to ensure the EMI remains
affordable.

Interest Rate Ranges (by credit score)
--------------------------------------
::

    Score ≥ 800 → base_rate − 1.0 % to base_rate
    Score ≥ 750 → base_rate − 0.5 % to base_rate + 0.5 %
    Score ≥ 700 → base_rate       to base_rate + 1.0 %
    Score < 700 → base_rate + 1.0 % to base_rate + 2.5 %
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from backend.core.emi_calculator import (
    calculate_emi,
    compute_total_interest,
)
from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

# Income multipliers per loan type (monthly income × multiplier = limit)
INCOME_MULTIPLIERS: Dict[str, int] = {
    "personal":   15,
    "home":       60,
    "auto":       20,
    "business":   12,
    "education":  18,
    "gold":       10,
}

# Base interest rates per loan type (% p.a.)
BASE_RATES: Dict[str, float] = {
    "personal":  12.0,
    "home":       8.5,
    "auto":       9.5,
    "business":  14.0,
    "education": 10.0,
    "gold":       9.0,
}

# Standard tenure options per loan type (months)
TENURE_OPTIONS: Dict[str, List[int]] = {
    "personal":  [12, 24, 36, 48, 60],
    "home":      [60, 120, 180, 240, 300],
    "auto":      [12, 24, 36, 48, 60, 72],
    "business":  [12, 24, 36, 48, 60],
    "education": [12, 24, 36, 48, 60, 84],
    "gold":      [6, 12, 18, 24, 36],
}

# FOIR cap — EMI must not exceed this fraction of income
MAX_FOIR = 0.50

# Processing fee
PROCESSING_FEE_PCT = 0.02  # 2 %

# Employment-type bonus multipliers (boost to the base multiplier)
EMPLOYMENT_BONUS: Dict[str, float] = {
    "salaried":      1.0,   # no bonus
    "professional":  0.95,  # slight reduction
    "self_employed":  0.80,
    "business":      0.85,
}


# ═══════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class RateRange:
    """Interest rate range for the offer."""
    min_rate: float = 0.0
    max_rate: float = 0.0
    offered_rate: float = 0.0   # the rate actually applied

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_rate": round(self.min_rate, 2),
            "max_rate": round(self.max_rate, 2),
            "offered_rate": round(self.offered_rate, 2),
        }


@dataclass
class LoanOffer:
    """
    A single loan-offer variant presented to the applicant.
    """
    offer_id: str = ""
    loan_amount: float = 0.0
    interest_rate: float = 0.0
    tenure_months: int = 0
    emi: float = 0.0
    processing_fee: float = 0.0
    total_interest: float = 0.0
    total_payable: float = 0.0
    is_recommended: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "offer_id": self.offer_id,
            "loan_amount": self.loan_amount,
            "interest_rate": self.interest_rate,
            "tenure_months": self.tenure_months,
            "emi": self.emi,
            "processing_fee": self.processing_fee,
            "total_interest": self.total_interest,
            "total_payable": self.total_payable,
            "is_recommended": self.is_recommended,
        }


@dataclass
class OfferResult:
    """
    Complete offer bundle returned by ``GET /offer``.
    """
    pre_approved_limit: float = 0.0
    income_multiplier: int = 0
    rate_range: RateRange = field(default_factory=RateRange)
    offers: List[LoanOffer] = field(default_factory=list)
    recommended_offer_id: str = ""
    loan_type: str = ""
    credit_score: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pre_approved_limit": self.pre_approved_limit,
            "income_multiplier": self.income_multiplier,
            "rate_range": self.rate_range.to_dict(),
            "offers": [o.to_dict() for o in self.offers],
            "recommended_offer_id": self.recommended_offer_id,
            "loan_type": self.loan_type,
            "credit_score": self.credit_score,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Pure Calculation Functions
# ═══════════════════════════════════════════════════════════════════════════

def compute_rate_range(credit_score: int, loan_type: str) -> RateRange:
    """
    Determine the interest rate range based on credit score band.

    Returns (min_rate, max_rate, offered_rate) where offered_rate is the
    midpoint of the band.
    """
    base = BASE_RATES.get(loan_type, 12.0)

    if credit_score >= 800:
        min_r, max_r = base - 1.0, base
    elif credit_score >= 750:
        min_r, max_r = base - 0.5, base + 0.5
    elif credit_score >= 700:
        min_r, max_r = base, base + 1.0
    else:
        min_r, max_r = base + 1.0, base + 2.5

    offered = round((min_r + max_r) / 2, 2)
    return RateRange(min_rate=round(min_r, 2), max_rate=round(max_r, 2), offered_rate=offered)


def compute_pre_approved_limit(
    monthly_income: float,
    loan_type: str,
    employment_type: str = "salaried",
    existing_emi: float = 0.0,
    rate: float = 12.0,
) -> float:
    """
    Calculate the pre-approved loan limit using income multiplier logic.

    Steps:
    1. base_limit = monthly_income × multiplier × employment_bonus
    2. affordable_emi = (income − existing_emi) × FOIR
    3. emi_based_limit = reverse_emi(affordable_emi, rate, max_tenure)
    4. final_limit = min(base_limit, emi_based_limit)
    """
    multiplier = INCOME_MULTIPLIERS.get(loan_type, 15)
    emp_factor = EMPLOYMENT_BONUS.get(employment_type, 1.0)

    # Step 1: Income multiplier limit
    base_limit = monthly_income * multiplier * emp_factor

    # Step 2: FOIR-based affordable EMI
    affordable_emi = (monthly_income - existing_emi) * MAX_FOIR
    if affordable_emi <= 0:
        return 0.0

    # Step 3: Reverse-calculate max principal from affordable EMI
    max_tenure = max(TENURE_OPTIONS.get(loan_type, [60]))
    if rate == 0:
        emi_limit = affordable_emi * max_tenure
    else:
        r = rate / 12 / 100
        factor = ((1 + r) ** max_tenure - 1) / (r * (1 + r) ** max_tenure)
        emi_limit = affordable_emi * factor

    # Step 4: Take the lesser of the two caps
    final_limit = min(base_limit, emi_limit)
    return round(max(final_limit, 0), 2)


def _generate_offer_id(loan_type: str, tenure: int, idx: int) -> str:
    """Generate a deterministic offer ID."""
    seed = f"{loan_type}:{tenure}:{idx}"
    short = hashlib.sha256(seed.encode()).hexdigest()[:6].upper()
    return f"OFF-{short}"


# ═══════════════════════════════════════════════════════════════════════════
# Loan Offer Service
# ═══════════════════════════════════════════════════════════════════════════

class LoanOfferService:
    """
    Generates personalised loan offers based on applicant profile.

    Simulates:
    - ``GET /offer`` → :meth:`generate_offer`

    Usage::

        svc = LoanOfferService()
        result = await svc.generate_offer(
            monthly_income=80000,
            credit_score=750,
            loan_type="personal",
        )
        print(result.pre_approved_limit)
        print(result.rate_range.to_dict())
        for offer in result.offers:
            print(offer.to_dict())
    """

    def __init__(self) -> None:
        self._selected: Dict[str, str] = {}  # session_id → offer_id

    # ──────────────────────────────────────────────────────────────────
    # GET /offer
    # ──────────────────────────────────────────────────────────────────

    async def generate_offer(
        self,
        monthly_income: float,
        credit_score: int,
        loan_type: str = "personal",
        employment_type: str = "salaried",
        existing_emi: float = 0.0,
        requested_amount: Optional[float] = None,
    ) -> OfferResult:
        """
        Generate a complete offer bundle.

        **Simulates:** ``GET /offer``

        Parameters
        ----------
        monthly_income : float
            Applicant's monthly net income (₹).
        credit_score : int
            Credit score (300–900).
        loan_type : str
            Loan product category.
        employment_type : str
            Employment classification.
        existing_emi : float
            Total existing monthly EMI obligations (₹).
        requested_amount : float or None
            If provided, offers are generated for this specific amount
            (capped at the pre-approved limit). Otherwise, the limit
            itself is used.

        Returns
        -------
        OfferResult
            Pre-approved limit, rate range, and list of tenure-varied offers.
        """
        # Rate range
        rates = compute_rate_range(credit_score, loan_type)

        # Pre-approved limit
        limit = compute_pre_approved_limit(
            monthly_income, loan_type, employment_type, existing_emi, rates.offered_rate,
        )

        # Determine the offer amount
        offer_amount = min(requested_amount, limit) if requested_amount else limit
        offer_amount = max(offer_amount, 0)

        # Generate one offer per available tenure
        tenures = TENURE_OPTIONS.get(loan_type, [60])
        offers: List[LoanOffer] = []
        recommended_id = ""

        for idx, tenure in enumerate(tenures):
            emi = calculate_emi(offer_amount, rates.offered_rate, tenure)
            total_interest = compute_total_interest(offer_amount, rates.offered_rate, tenure)
            total_payable = round(offer_amount + total_interest, 2)
            fee = round(offer_amount * PROCESSING_FEE_PCT, 2)
            offer_id = _generate_offer_id(loan_type, tenure, idx)

            # Recommend the middle tenure option
            is_recommended = idx == len(tenures) // 2

            offers.append(LoanOffer(
                offer_id=offer_id,
                loan_amount=offer_amount,
                interest_rate=rates.offered_rate,
                tenure_months=tenure,
                emi=emi,
                processing_fee=fee,
                total_interest=total_interest,
                total_payable=total_payable,
                is_recommended=is_recommended,
            ))

            if is_recommended:
                recommended_id = offer_id

        multiplier = INCOME_MULTIPLIERS.get(loan_type, 15)

        logger.info(
            "Offer generated | type=%s income=%.0f score=%d limit=%.0f "
            "rate=%.2f%% offers=%d",
            loan_type, monthly_income, credit_score, limit,
            rates.offered_rate, len(offers),
        )

        return OfferResult(
            pre_approved_limit=limit,
            income_multiplier=multiplier,
            rate_range=rates,
            offers=offers,
            recommended_offer_id=recommended_id,
            loan_type=loan_type,
            credit_score=credit_score,
        )

    # ──────────────────────────────────────────────────────────────────
    # Legacy API (backward compat with existing agent code)
    # ──────────────────────────────────────────────────────────────────

    async def generate_offers(
        self,
        loan_amount: float,
        credit_score: int,
        income: float,
        loan_type: str = "personal",
        employment_type: str = "salaried",
        existing_emi: float = 0.0,
    ) -> List[LoanOffer]:
        """
        Generate offer variants (legacy interface).

        Wraps :meth:`generate_offer` and returns just the offers list.
        """
        result = await self.generate_offer(
            monthly_income=income,
            credit_score=credit_score,
            loan_type=loan_type,
            employment_type=employment_type,
            existing_emi=existing_emi,
            requested_amount=loan_amount,
        )
        return result.offers

    # ──────────────────────────────────────────────────────────────────
    # Offer Selection
    # ──────────────────────────────────────────────────────────────────

    async def select_offer(self, offer_id: str, session_id: str) -> Dict[str, Any]:
        """
        Record the applicant's selected offer.

        Returns confirmation with the selected offer ID.
        """
        self._selected[session_id] = offer_id
        logger.info("Offer %s selected for session %s", offer_id, session_id)
        return {"offer_id": offer_id, "status": "selected", "session_id": session_id}

    async def get_selected_offer(self, session_id: str) -> Optional[str]:
        """Return the offer ID selected for this session, if any."""
        return self._selected.get(session_id)
