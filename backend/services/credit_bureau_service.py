"""
credit_bureau_service.py
========================

Mock Credit Bureau API for development, demo, and testing.

Simulated Endpoint
------------------
``GET /credit-score?pan=``  →  :meth:`CreditBureauService.fetch_credit_score`

Returns a **deterministic credit score between 650 and 850**, seeded from
the PAN number using SHA-256 hashing.  The same PAN always produces the
same score across invocations — no randomness involved.

Additionally provides:
- Full credit report with simulated active loans, enquiry counts, and
  default history (also deterministic per PAN).
- In-memory per-PAN cache to avoid redundant computation within a session.

Production Swap
---------------
Replace the method bodies with ``httpx.AsyncClient`` calls to the real
Credit Bureau API (CIBIL / Experian / CRIF).  The interface stays the same.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from backend.utils.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class CreditReport:
    """
    Structured credit-bureau report for an applicant.

    Attributes
    ----------
    pan : str
        PAN number used for the enquiry.
    credit_score : int
        Numeric credit score (650–850 range in mock).
    score_band : str
        Human-readable band: Excellent / Very Good / Good / Fair / Poor.
    active_loans : list[dict]
        Currently active loan accounts (simulated).
    defaults : list[dict]
        Past defaults / write-offs (simulated).
    enquiry_count_last_6m : int
        Number of credit enquiries in the last 6 months.
    total_outstanding : float
        Total outstanding amount across all active loans (₹).
    oldest_account_months : int
        Age of the oldest credit account in months.
    credit_utilisation_pct : float
        Credit utilisation ratio (0–100).
    raw_response : dict
        Full raw API response for audit / debugging.
    """

    pan: str = ""
    credit_score: int = 0
    score_band: str = ""
    active_loans: List[Dict[str, Any]] = field(default_factory=list)
    defaults: List[Dict[str, Any]] = field(default_factory=list)
    enquiry_count_last_6m: int = 0
    total_outstanding: float = 0.0
    oldest_account_months: int = 0
    credit_utilisation_pct: float = 0.0
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to JSON-safe dict (masks PAN)."""
        masked = f"XXXXXX{self.pan[-4:]}" if len(self.pan) >= 4 else self.pan
        return {
            "pan": masked,
            "credit_score": self.credit_score,
            "score_band": self.score_band,
            "active_loans": self.active_loans,
            "defaults": self.defaults,
            "enquiry_count_last_6m": self.enquiry_count_last_6m,
            "total_outstanding": self.total_outstanding,
            "oldest_account_months": self.oldest_account_months,
            "credit_utilisation_pct": self.credit_utilisation_pct,
        }


# ═══════════════════════════════════════════════════════════════════════════
# Deterministic Scoring Engine
# ═══════════════════════════════════════════════════════════════════════════

def _seed(pan: str) -> str:
    """Return a hex digest used to derive all deterministic fields."""
    return hashlib.sha256(f"credit-bureau:{pan.upper().strip()}".encode()).hexdigest()


def _pan_to_score(pan: str) -> int:
    """
    Map a PAN to a credit score in the range **650–850**.

    Uses the first 6 hex characters of the SHA-256 digest as a seed,
    converted to an integer, and mapped into [650, 850].

    The same PAN always returns the same score (deterministic).
    """
    digest = _seed(pan)
    raw = int(digest[:6], 16)
    return 650 + (raw % 201)  # 0–200 → 650–850


def _score_to_band(score: int) -> str:
    """Map a numeric score to a human-readable band."""
    if score >= 800:
        return "Excellent"
    if score >= 750:
        return "Very Good"
    if score >= 700:
        return "Good"
    if score >= 650:
        return "Fair"
    return "Poor"


def _generate_active_loans(pan: str) -> List[Dict[str, Any]]:
    """
    Generate deterministic simulated active loans based on PAN hash.

    Number of loans and amounts are derived from the digest.
    """
    digest = _seed(pan)

    # Number of active loans: 0–3
    n_loans = int(digest[6:8], 16) % 4

    loan_types = ["Personal Loan", "Home Loan", "Auto Loan", "Credit Card"]
    lenders = ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Kotak Mahindra"]

    loans: List[Dict[str, Any]] = []
    for i in range(n_loans):
        offset = 8 + i * 4
        chunk = digest[offset: offset + 4]
        amount_seed = int(chunk, 16)

        loan_type = loan_types[amount_seed % len(loan_types)]
        lender = lenders[(amount_seed >> 4) % len(lenders)]

        if loan_type == "Home Loan":
            outstanding = 10_00_000 + (amount_seed % 40_00_000)
            emi = round(outstanding / 180, 0)
        elif loan_type == "Credit Card":
            outstanding = 5_000 + (amount_seed % 95_000)
            emi = round(outstanding * 0.05, 0)
        else:
            outstanding = 50_000 + (amount_seed % 4_50_000)
            emi = round(outstanding / 48, 0)

        loans.append({
            "loan_type": loan_type,
            "lender": lender,
            "outstanding": outstanding,
            "emi": emi,
            "status": "active",
        })

    return loans


def _generate_defaults(pan: str) -> List[Dict[str, Any]]:
    """
    Generate deterministic simulated defaults.

    Only PANs whose score < 700 tend to have defaults.
    """
    score = _pan_to_score(pan)
    if score >= 720:
        return []

    digest = _seed(pan)
    n_defaults = int(digest[20:22], 16) % 2  # 0 or 1

    defaults: List[Dict[str, Any]] = []
    for i in range(n_defaults):
        offset = 22 + i * 4
        chunk = digest[offset: offset + 4]
        amount = 10_000 + (int(chunk, 16) % 90_000)
        defaults.append({
            "loan_type": "Personal Loan",
            "amount": amount,
            "settled": int(digest[offset], 16) % 2 == 0,
            "year": 2020 + (int(digest[offset + 1], 16) % 4),
        })

    return defaults


def _generate_full_report(pan: str) -> CreditReport:
    """Build a complete deterministic CreditReport from a PAN."""
    digest = _seed(pan)
    score = _pan_to_score(pan)
    band = _score_to_band(score)
    active_loans = _generate_active_loans(pan)
    defaults = _generate_defaults(pan)

    total_outstanding = sum(l["outstanding"] for l in active_loans)
    enquiry_count = int(digest[16:18], 16) % 6  # 0–5
    oldest_months = 12 + (int(digest[18:20], 16) % 120)  # 12–131 months
    utilisation = round((int(digest[14:16], 16) % 80) + 5, 1)  # 5–84 %

    return CreditReport(
        pan=pan.upper().strip(),
        credit_score=score,
        score_band=band,
        active_loans=active_loans,
        defaults=defaults,
        enquiry_count_last_6m=enquiry_count,
        total_outstanding=total_outstanding,
        oldest_account_months=oldest_months,
        credit_utilisation_pct=utilisation,
        raw_response={
            "provider": "mock_credit_bureau",
            "version": "1.0",
            "pan": pan.upper().strip(),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════
# CreditBureauService
# ═══════════════════════════════════════════════════════════════════════════

class CreditBureauService:
    """
    Mock credit bureau API with deterministic PAN-based scoring.

    Simulates:
    - ``GET /credit-score?pan=``      → :meth:`fetch_credit_score`
    - ``GET /credit-report?pan=``     → :meth:`fetch_credit_report`

    Usage::

        bureau = CreditBureauService()
        score  = await bureau.fetch_credit_score("ABCPK1234A")   # e.g. 782
        report = await bureau.fetch_credit_report("ABCPK1234A")  # full report
    """

    def __init__(self) -> None:
        # In-memory cache: PAN → CreditReport (avoids recomputation)
        self._cache: Dict[str, CreditReport] = {}

    # ──────────────────────────────────────────────────────────────────
    # GET /credit-score?pan=
    # ──────────────────────────────────────────────────────────────────

    async def fetch_credit_score(self, pan: str) -> int:
        """
        Return a deterministic credit score (650–850) for the given PAN.

        **Simulates:** ``GET /credit-score?pan={pan}``

        The score is derived from ``SHA-256(pan)`` and will always be
        identical for the same PAN input.

        Parameters
        ----------
        pan : str
            10-character Indian PAN (e.g. ``ABCPK1234A``).

        Returns
        -------
        int
            Credit score in range [650, 850].
        """
        pan = pan.upper().strip()
        score = _pan_to_score(pan)
        band = _score_to_band(score)
        logger.info(
            "Credit score lookup | PAN=%s score=%d band=%s",
            f"XXXXXX{pan[-4:]}" if len(pan) >= 4 else pan,
            score,
            band,
        )
        return score

    # ──────────────────────────────────────────────────────────────────
    # GET /credit-report?pan=
    # ──────────────────────────────────────────────────────────────────

    async def fetch_credit_report(self, pan: str, dob: str = "") -> CreditReport:
        """
        Return a full deterministic credit report for the given PAN.

        **Simulates:** ``GET /credit-report?pan={pan}``

        Includes score, active loans, defaults, enquiry count, and
        credit utilisation — all deterministically derived from the PAN.

        Parameters
        ----------
        pan : str
            10-character Indian PAN.
        dob : str
            Date of birth (unused in mock; present for interface parity).

        Returns
        -------
        CreditReport
            Complete simulated credit report.
        """
        pan = pan.upper().strip()

        # Return cached report if available
        if pan in self._cache:
            logger.info("Credit report cache hit | PAN=XXXXXX%s", pan[-4:])
            return self._cache[pan]

        report = _generate_full_report(pan)
        self._cache[pan] = report

        logger.info(
            "Credit report generated | PAN=XXXXXX%s score=%d loans=%d defaults=%d",
            pan[-4:],
            report.credit_score,
            len(report.active_loans),
            len(report.defaults),
        )
        return report

    # ──────────────────────────────────────────────────────────────────
    # Admin / Debug
    # ──────────────────────────────────────────────────────────────────

    def clear_cache(self) -> None:
        """Clear the in-memory report cache."""
        self._cache.clear()
        logger.info("Credit bureau cache cleared.")

    @property
    def cache_size(self) -> int:
        return len(self._cache)
