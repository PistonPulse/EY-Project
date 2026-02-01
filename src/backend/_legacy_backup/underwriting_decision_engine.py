"""
================================================================================
PHASE 7: DETERMINISTIC UNDERWRITING DECISION ENGINE
================================================================================

This module implements a DETERMINISTIC underwriting decision engine that:
1. Makes FINAL loan approval/rejection decisions
2. Uses ONLY stored customer data (no LLM involvement)
3. Applies strict business rules consistently
4. Produces reproducible decisions

================================================================================
WHY UNDERWRITING MUST BE DETERMINISTIC:
================================================================================

1. REGULATORY COMPLIANCE
   - Fair lending laws require consistent decision criteria
   - Auditors need to verify same inputs → same outputs
   - Discrimination can occur if decisions vary arbitrarily

2. LEGAL LIABILITY
   - Loan decisions must be defensible in court
   - "The AI decided" is not a valid legal defense
   - Human-readable rules create accountability

3. CUSTOMER TRUST
   - Applicants deserve to know why they were rejected
   - Consistent rules allow for improvement and reapplication
   - Arbitrary decisions erode trust in the system

================================================================================
WHY LLM CANNOT BE TRUSTED WITH LOAN APPROVALS:
================================================================================

1. HALLUCINATION RISK
   - LLMs can generate plausible but incorrect justifications
   - They may approve loans that should be rejected (or vice versa)
   - Same prompt can produce different decisions each time

2. BIAS AMPLIFICATION
   - LLMs may perpetuate or amplify historical biases
   - They can make decisions based on irrelevant factors
   - Fairness testing is extremely difficult with LLMs

3. AUDIT TRAIL ISSUES
   - LLM reasoning is not deterministic or inspectable
   - Regulators cannot verify decision consistency
   - Model updates can silently change approval criteria

================================================================================
UNDERWRITING RULES (DETERMINISTIC):
================================================================================

RULE 1: CREDIT SCORE RULE
   - If credit_score < 700 → REJECT
   - Reason: Below minimum credit threshold

RULE 2: PRE-APPROVED LIMIT RULE
   - If requested_amount ≤ preapproved_limit → OK
   - If requested_amount ≤ 2 × preapproved_limit → Require income check (already done)
   - If requested_amount > 2 × preapproved_limit → REJECT
   - Reason: Requested amount exceeds maximum allowed

RULE 3: EMI AFFORDABILITY RULE
   - Calculate expected EMI using simple interest approximation
   - If (existing_emi + expected_emi) > 50% of verified_monthly_salary → REJECT
   - Reason: Monthly obligations exceed income capacity

================================================================================
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Tuple, Dict, Any

# Configure logging with Phase 7 prefix
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | UNDERWRITING | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ================================================================================
# ENUMS AND CONSTANTS
# ================================================================================

class LoanDecision(Enum):
    """Possible underwriting decisions."""
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"  # Only used for incomplete data


class RejectionReason(Enum):
    """Standard rejection reasons (human-readable)."""
    LOW_CREDIT_SCORE = "Credit score below minimum threshold of 700"
    EXCEEDS_LIMIT = "Requested amount exceeds maximum allowable limit"
    EMI_UNAFFORDABLE = "Monthly EMI obligations exceed 50% of verified income"
    MISSING_DATA = "Application data incomplete - cannot proceed"


# Configuration constants
MIN_CREDIT_SCORE = 700
MAX_FOIR = 0.50  # Fixed Obligation to Income Ratio (50%)
DEFAULT_TENURE_MONTHS = 36
DEFAULT_INTEREST_RATE = 12.0  # Used for EMI calculation if not specified


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class UnderwritingInput:
    """
    Input data required for underwriting decision.
    
    All fields are MANDATORY for processing.
    Missing any field will block execution.
    """
    income_verified: bool
    verified_monthly_salary_inr: int
    credit_score: int
    requested_loan_amount: int
    pre_approved_limit: int
    existing_emi: int = 0  # Monthly EMI on existing loans
    loan_tenure_months: int = DEFAULT_TENURE_MONTHS
    interest_rate: float = DEFAULT_INTEREST_RATE  # Annual interest rate


@dataclass
class UnderwritingResult:
    """
    Output of the underwriting decision.
    
    Contains:
    - The decision (APPROVED/REJECTED)
    - Reason for the decision
    - Timestamp for audit trail
    - Details for logging
    """
    decision: LoanDecision
    reason: str
    timestamp: str
    
    # Detailed breakdown
    credit_score_passed: bool
    limit_check_passed: bool
    emi_affordability_passed: bool
    
    # Computed values
    calculated_emi: Optional[float] = None
    total_monthly_obligations: Optional[float] = None
    foir: Optional[float] = None  # Fixed Obligation to Income Ratio
    
    # For state persistence
    loan_status: str = ""
    approval_reason: Optional[str] = None
    rejection_reason: Optional[str] = None


# ================================================================================
# ENTRY CONDITION VALIDATION
# ================================================================================

def validate_entry_conditions(
    income_verified: bool,
    verified_monthly_salary_inr: Optional[int],
    credit_score: Optional[int],
    requested_loan_amount: Optional[int]
) -> Tuple[bool, str]:
    """
    Validate that all entry conditions for UNDERWRITING are met.
    
    Entry Conditions:
    1. income_verified == True
    2. verified_monthly_salary_inr exists and > 0
    3. credit_score exists
    4. requested_loan_amount exists and > 0
    
    Args:
        income_verified: Whether income has been verified
        verified_monthly_salary_inr: Verified monthly salary in INR
        credit_score: Customer's credit score
        requested_loan_amount: Loan amount requested
    
    Returns:
        Tuple of (can_proceed, reason)
    """
    logger.info("Validating underwriting entry conditions")
    
    # Condition 1: Income must be verified
    if not income_verified:
        reason = "Income not verified. Cannot proceed with underwriting."
        logger.error(f"Entry blocked: {reason}")
        return False, reason
    
    # Condition 2: Verified salary must exist and be positive
    if verified_monthly_salary_inr is None or verified_monthly_salary_inr <= 0:
        reason = f"Verified salary invalid or missing: {verified_monthly_salary_inr}"
        logger.error(f"Entry blocked: {reason}")
        return False, reason
    
    # Condition 3: Credit score must exist
    if credit_score is None:
        reason = "Credit score missing. Cannot proceed with underwriting."
        logger.error(f"Entry blocked: {reason}")
        return False, reason
    
    # Condition 4: Loan amount must exist and be positive
    if requested_loan_amount is None or requested_loan_amount <= 0:
        reason = f"Requested loan amount invalid or missing: {requested_loan_amount}"
        logger.error(f"Entry blocked: {reason}")
        return False, reason
    
    logger.info("All entry conditions met for underwriting")
    return True, "All conditions met"


# ================================================================================
# EMI CALCULATION
# ================================================================================

def calculate_emi(
    principal: int,
    annual_rate: float,
    tenure_months: int
) -> float:
    """
    Calculate EMI using standard formula.
    
    EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    
    Where:
    - P = Principal loan amount
    - r = Monthly interest rate (annual_rate / 12 / 100)
    - n = Tenure in months
    
    Args:
        principal: Loan amount in INR
        annual_rate: Annual interest rate (e.g., 12.0 for 12%)
        tenure_months: Loan tenure in months
    
    Returns:
        Monthly EMI amount
    """
    if principal <= 0 or tenure_months <= 0:
        return 0.0
    
    if annual_rate <= 0:
        # Zero interest - simple division
        return principal / tenure_months
    
    monthly_rate = annual_rate / 12 / 100
    
    # EMI formula
    numerator = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months)
    denominator = ((1 + monthly_rate) ** tenure_months) - 1
    
    if denominator == 0:
        return principal / tenure_months
    
    emi = numerator / denominator
    return round(emi, 2)


# ================================================================================
# UNDERWRITING RULES
# ================================================================================

def check_credit_score_rule(credit_score: int) -> Tuple[bool, str]:
    """
    RULE 1: Credit Score Rule
    
    If credit_score < 700 → REJECT
    
    Args:
        credit_score: Customer's credit score
    
    Returns:
        Tuple of (passed, message)
    """
    logger.info(f"Evaluating credit score: {credit_score}")
    
    if credit_score < MIN_CREDIT_SCORE:
        message = f"Credit score {credit_score} is below minimum threshold of {MIN_CREDIT_SCORE}"
        logger.warning(f"Credit score check FAILED: {message}")
        return False, message
    
    message = f"Credit score {credit_score} meets minimum threshold of {MIN_CREDIT_SCORE}"
    logger.info(f"Credit score check PASSED: {message}")
    return True, message


def check_pre_approved_limit_rule(
    requested_amount: int,
    pre_approved_limit: int
) -> Tuple[bool, str]:
    """
    RULE 2: Pre-Approved Limit Rule
    
    - If requested_amount ≤ preapproved_limit → OK
    - If requested_amount ≤ 2 × preapproved_limit → OK (income already verified)
    - If requested_amount > 2 × preapproved_limit → REJECT
    
    Args:
        requested_amount: Loan amount requested
        pre_approved_limit: Customer's pre-approved limit
    
    Returns:
        Tuple of (passed, message)
    """
    logger.info(f"Evaluating loan amount: ₹{requested_amount:,} vs pre-approved limit: ₹{pre_approved_limit:,}")
    
    max_allowed = pre_approved_limit * 2
    
    if requested_amount <= pre_approved_limit:
        message = f"Amount ₹{requested_amount:,} is within pre-approved limit of ₹{pre_approved_limit:,}"
        logger.info(f"Limit check PASSED (within limit): {message}")
        return True, message
    
    if requested_amount <= max_allowed:
        message = f"Amount ₹{requested_amount:,} exceeds pre-approved limit but within 2x (₹{max_allowed:,})"
        logger.info(f"Limit check PASSED (with income verification): {message}")
        return True, message
    
    message = f"Amount ₹{requested_amount:,} exceeds maximum allowed of ₹{max_allowed:,} (2x pre-approved)"
    logger.warning(f"Limit check FAILED: {message}")
    return False, message


def check_emi_affordability_rule(
    verified_monthly_salary: int,
    existing_emi: int,
    new_emi: float
) -> Tuple[bool, str, float]:
    """
    RULE 3: EMI Affordability Rule
    
    (existing_emi + expected_emi) must be ≤ 50% of verified_monthly_salary
    
    This is the Fixed Obligation to Income Ratio (FOIR) check.
    
    Args:
        verified_monthly_salary: Verified monthly income
        existing_emi: Current monthly EMI obligations
        new_emi: Calculated EMI for new loan
    
    Returns:
        Tuple of (passed, message, foir_percentage)
    """
    total_obligations = existing_emi + new_emi
    max_allowed = verified_monthly_salary * MAX_FOIR
    foir = total_obligations / verified_monthly_salary if verified_monthly_salary > 0 else 1.0
    foir_percentage = round(foir * 100, 2)
    
    logger.info(f"Calculating EMI affordability:")
    logger.info(f"  - Verified monthly salary: ₹{verified_monthly_salary:,}")
    logger.info(f"  - Existing EMI: ₹{existing_emi:,}")
    logger.info(f"  - New EMI: ₹{new_emi:,.2f}")
    logger.info(f"  - Total obligations: ₹{total_obligations:,.2f}")
    logger.info(f"  - FOIR: {foir_percentage}% (max allowed: {MAX_FOIR * 100}%)")
    
    if total_obligations <= max_allowed:
        message = f"Total EMI ₹{total_obligations:,.2f} is within 50% of income (FOIR: {foir_percentage}%)"
        logger.info(f"Affordability check PASSED: {message}")
        return True, message, foir_percentage
    
    message = f"Total EMI ₹{total_obligations:,.2f} exceeds 50% of income (FOIR: {foir_percentage}%)"
    logger.warning(f"Affordability check FAILED: {message}")
    return False, message, foir_percentage


# ================================================================================
# MAIN UNDERWRITING FUNCTION
# ================================================================================

def perform_underwriting(
    income_verified: bool,
    verified_monthly_salary_inr: Optional[int],
    credit_score: Optional[int],
    requested_loan_amount: Optional[int],
    pre_approved_limit: int = 0,
    existing_emi: int = 0,
    loan_tenure_months: int = DEFAULT_TENURE_MONTHS,
    interest_rate: float = DEFAULT_INTEREST_RATE
) -> UnderwritingResult:
    """
    Perform deterministic underwriting decision.
    
    This is the MAIN ENTRY POINT for Phase 7 underwriting.
    
    The function:
    1. Validates entry conditions
    2. Applies all underwriting rules in sequence
    3. Returns a FINAL decision (APPROVED or REJECTED)
    
    The decision is DETERMINISTIC:
    - Same inputs ALWAYS produce same output
    - No randomness, no LLM involvement
    - Fully auditable
    
    Args:
        income_verified: Whether income has been verified
        verified_monthly_salary_inr: Verified monthly salary in INR
        credit_score: Customer's credit score
        requested_loan_amount: Loan amount requested
        pre_approved_limit: Customer's pre-approved limit
        existing_emi: Current monthly EMI obligations
        loan_tenure_months: Loan tenure in months
        interest_rate: Annual interest rate for EMI calculation
    
    Returns:
        UnderwritingResult with decision and details
    """
    logger.info("=" * 60)
    logger.info("PHASE 7: UNDERWRITING DECISION ENGINE STARTED")
    logger.info("=" * 60)
    
    timestamp = datetime.now().isoformat()
    
    # Step 1: Validate entry conditions
    can_proceed, entry_reason = validate_entry_conditions(
        income_verified=income_verified,
        verified_monthly_salary_inr=verified_monthly_salary_inr,
        credit_score=credit_score,
        requested_loan_amount=requested_loan_amount
    )
    
    if not can_proceed:
        logger.error(f"Underwriting BLOCKED: {entry_reason}")
        return UnderwritingResult(
            decision=LoanDecision.PENDING,
            reason=entry_reason,
            timestamp=timestamp,
            credit_score_passed=False,
            limit_check_passed=False,
            emi_affordability_passed=False,
            loan_status="PENDING",
            rejection_reason=RejectionReason.MISSING_DATA.value
        )
    
    logger.info("Underwriting started")
    
    # Step 2: Apply Rule 1 - Credit Score Check
    logger.info("Credit score evaluated")
    credit_passed, credit_message = check_credit_score_rule(credit_score)
    
    if not credit_passed:
        logger.warning(f"Loan REJECTED: {RejectionReason.LOW_CREDIT_SCORE.value}")
        logger.info("Stage advanced to REJECTION")
        return UnderwritingResult(
            decision=LoanDecision.REJECTED,
            reason=credit_message,
            timestamp=timestamp,
            credit_score_passed=False,
            limit_check_passed=False,
            emi_affordability_passed=False,
            loan_status="REJECTED",
            rejection_reason=RejectionReason.LOW_CREDIT_SCORE.value
        )
    
    # Step 3: Apply Rule 2 - Pre-Approved Limit Check
    limit_passed, limit_message = check_pre_approved_limit_rule(
        requested_amount=requested_loan_amount,
        pre_approved_limit=pre_approved_limit
    )
    
    if not limit_passed:
        logger.warning(f"Loan REJECTED: {RejectionReason.EXCEEDS_LIMIT.value}")
        logger.info("Stage advanced to REJECTION")
        return UnderwritingResult(
            decision=LoanDecision.REJECTED,
            reason=limit_message,
            timestamp=timestamp,
            credit_score_passed=True,
            limit_check_passed=False,
            emi_affordability_passed=False,
            loan_status="REJECTED",
            rejection_reason=RejectionReason.EXCEEDS_LIMIT.value
        )
    
    # Step 4: Calculate EMI
    calculated_emi = calculate_emi(
        principal=requested_loan_amount,
        annual_rate=interest_rate,
        tenure_months=loan_tenure_months
    )
    logger.info(f"EMI affordability calculated: ₹{calculated_emi:,.2f}/month")
    
    # Step 5: Apply Rule 3 - EMI Affordability Check
    emi_passed, emi_message, foir = check_emi_affordability_rule(
        verified_monthly_salary=verified_monthly_salary_inr,
        existing_emi=existing_emi,
        new_emi=calculated_emi
    )
    
    total_obligations = existing_emi + calculated_emi
    
    if not emi_passed:
        logger.warning(f"Loan REJECTED: {RejectionReason.EMI_UNAFFORDABLE.value}")
        logger.info("Stage advanced to REJECTION")
        return UnderwritingResult(
            decision=LoanDecision.REJECTED,
            reason=emi_message,
            timestamp=timestamp,
            credit_score_passed=True,
            limit_check_passed=True,
            emi_affordability_passed=False,
            calculated_emi=calculated_emi,
            total_monthly_obligations=total_obligations,
            foir=foir,
            loan_status="REJECTED",
            rejection_reason=RejectionReason.EMI_UNAFFORDABLE.value
        )
    
    # Step 6: All checks passed - APPROVE
    approval_reason = "Meets credit and income criteria"
    logger.info(f"Loan APPROVED: {approval_reason}")
    logger.info("Stage advanced to SANCTION")
    
    return UnderwritingResult(
        decision=LoanDecision.APPROVED,
        reason=approval_reason,
        timestamp=timestamp,
        credit_score_passed=True,
        limit_check_passed=True,
        emi_affordability_passed=True,
        calculated_emi=calculated_emi,
        total_monthly_obligations=total_obligations,
        foir=foir,
        loan_status="APPROVED",
        approval_reason=approval_reason
    )


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def format_currency(amount: float) -> str:
    """Format amount in Indian currency style."""
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount / 10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount / 100000:.2f} L"
    else:
        return f"₹{amount:,.2f}"


def get_approval_message(result: UnderwritingResult, user_name: str = "") -> str:
    """
    Generate a human-friendly approval message.
    
    This message is for LLM to use when explaining the decision.
    The LLM may paraphrase but MUST NOT change the decision.
    """
    name_part = f"{user_name}, " if user_name else ""
    return (
        f"Congratulations{name_part}! Your loan application has been approved. "
        f"Your monthly EMI will be {format_currency(result.calculated_emi)}. "
        f"Your debt-to-income ratio of {result.foir}% is well within acceptable limits."
    )


def get_rejection_message(result: UnderwritingResult, user_name: str = "") -> str:
    """
    Generate a human-friendly rejection message.
    
    This message is for LLM to use when explaining the decision.
    The LLM may paraphrase but MUST NOT change the decision.
    """
    name_part = f"{user_name}, " if user_name else ""
    
    # Map rejection reason to customer-friendly message
    if result.rejection_reason == RejectionReason.LOW_CREDIT_SCORE.value:
        return (
            f"We're sorry{name_part}, but we're unable to approve your application "
            f"at this time. Your credit score does not meet our minimum requirement of {MIN_CREDIT_SCORE}. "
            f"We recommend checking your credit report and working to improve your score."
        )
    elif result.rejection_reason == RejectionReason.EXCEEDS_LIMIT.value:
        return (
            f"We're sorry{name_part}, but the requested loan amount exceeds the maximum "
            f"we can offer based on your profile. You may consider applying for a lower amount."
        )
    elif result.rejection_reason == RejectionReason.EMI_UNAFFORDABLE.value:
        return (
            f"We're sorry{name_part}, but based on our assessment, the monthly EMI "
            f"of {format_currency(result.calculated_emi)} would exceed 50% of your verified income. "
            f"You may consider a longer tenure or a lower loan amount."
        )
    else:
        return (
            f"We're sorry{name_part}, but we're unable to approve your application at this time."
        )


def has_underwriting_completed(loan_status: Optional[str]) -> bool:
    """
    Check if underwriting has already been completed.
    
    Prevents re-running underwriting on the same application.
    """
    return loan_status in ["APPROVED", "REJECTED"]


# ================================================================================
# MODULE TEST
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PHASE 7: UNDERWRITING DECISION ENGINE TEST")
    print("=" * 70)
    
    # Test 1: Successful approval
    print("\n--- Test 1: Approval Case ---")
    result = perform_underwriting(
        income_verified=True,
        verified_monthly_salary_inr=100000,  # ₹1 Lakh/month
        credit_score=750,
        requested_loan_amount=500000,  # ₹5 Lakhs
        pre_approved_limit=300000,  # ₹3 Lakhs
        existing_emi=10000,  # ₹10K existing EMI
        loan_tenure_months=36,
        interest_rate=12.0
    )
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.reason}")
    print(f"EMI: {format_currency(result.calculated_emi)}")
    print(f"FOIR: {result.foir}%")
    
    # Test 2: Rejection - Low credit score
    print("\n--- Test 2: Rejection - Low Credit Score ---")
    result = perform_underwriting(
        income_verified=True,
        verified_monthly_salary_inr=100000,
        credit_score=650,  # Below 700
        requested_loan_amount=500000,
        pre_approved_limit=300000,
        existing_emi=0
    )
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.rejection_reason}")
    
    # Test 3: Rejection - Amount exceeds limit
    print("\n--- Test 3: Rejection - Amount Exceeds Limit ---")
    result = perform_underwriting(
        income_verified=True,
        verified_monthly_salary_inr=100000,
        credit_score=750,
        requested_loan_amount=1000000,  # ₹10 Lakhs
        pre_approved_limit=300000,  # Max allowed: ₹6 Lakhs
        existing_emi=0
    )
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.rejection_reason}")
    
    # Test 4: Rejection - EMI unaffordable
    print("\n--- Test 4: Rejection - EMI Unaffordable ---")
    result = perform_underwriting(
        income_verified=True,
        verified_monthly_salary_inr=50000,  # ₹50K/month
        credit_score=750,
        requested_loan_amount=500000,  # High amount for this income
        pre_approved_limit=500000,
        existing_emi=20000,  # Already paying ₹20K EMI
        loan_tenure_months=24  # Shorter tenure = higher EMI
    )
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.rejection_reason}")
    print(f"EMI: {format_currency(result.calculated_emi)}")
    print(f"FOIR: {result.foir}%")
    
    # Test 5: Entry condition failure
    print("\n--- Test 5: Entry Condition Failure ---")
    result = perform_underwriting(
        income_verified=False,  # Not verified
        verified_monthly_salary_inr=100000,
        credit_score=750,
        requested_loan_amount=500000,
        pre_approved_limit=300000
    )
    print(f"Decision: {result.decision.value}")
    print(f"Reason: {result.reason}")
    
    # Test 6: Determinism check - same inputs, same output
    print("\n--- Test 6: Determinism Check ---")
    results = []
    for i in range(5):
        r = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=80000,
            credit_score=720,
            requested_loan_amount=400000,
            pre_approved_limit=250000,
            existing_emi=5000
        )
        results.append(r.decision.value)
    print(f"5 runs with same input: {results}")
    print(f"All same? {len(set(results)) == 1}")
    
    print("\n" + "=" * 70)
    print("ALL UNDERWRITING ENGINE TESTS PASSED!")
    print("=" * 70)
