"""
================================================================================
PHASE 8: JOURNEY CLOSURE SERVICE - SANCTION LETTER & REJECTION HANDLING
================================================================================

This module implements the FINAL stage of the loan journey:
1. Generating sanction letters for APPROVED loans
2. Providing clear rejection messages for REJECTED loans
3. Closing the journey cleanly and professionally

================================================================================
WHY SANCTION IS A TERMINAL STAGE:
================================================================================

1. JOURNEY FINALITY
   - Once a loan is sanctioned, the decision is FINAL
   - The sanction letter is a legally binding document
   - No further modifications are allowed to the loan terms
   - Customer journey ends with a positive outcome

2. DOCUMENT INTEGRITY
   - Sanction letter contains verified, immutable data
   - Re-generation would create audit inconsistencies
   - Single generation ensures document uniqueness
   - Reference numbers are tied to specific sanctions

3. REGULATORY COMPLIANCE
   - NBFCs must maintain sanction letter records
   - Each sanction must have a unique reference
   - Re-running sanction could trigger duplicate records
   - Auditors require single-point-of-truth documents

================================================================================
WHY REJECTION MUST BE FINAL:
================================================================================

1. CUSTOMER RESPECT
   - Clear, honest communication builds trust
   - No false hope or misleading suggestions
   - Professional closure maintains brand reputation
   - Single clear reason prevents confusion

2. OPERATIONAL EFFICIENCY
   - Rejected applications don't re-enter pipeline
   - No wasted resources on declined applications
   - Clean data for analytics and reporting
   - Clear rejection prevents support escalations

3. LEGAL PROTECTION
   - Documented rejection with specific reason
   - No ambiguity about decision outcome
   - Prevents future disputes about application status
   - Audit trail shows clear decision path

================================================================================
HOW CLEAN CLOSURE IMPROVES TRUST:
================================================================================

1. FOR APPROVED CUSTOMERS:
   - Immediate access to sanction letter
   - Clear next steps (disbursement)
   - Professional documentation
   - No lingering uncertainty

2. FOR REJECTED CUSTOMERS:
   - Clear, respectful communication
   - Specific reason (single, not list)
   - No upselling or cross-selling
   - Invitation to apply again in future

3. FOR THE NBFC:
   - Clean audit trails
   - Proper document retention
   - Efficient resource utilization
   - Reduced customer complaints

================================================================================
"""

import os
import logging
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Tuple, Dict, Any
from enum import Enum

# Import PDF generator for sanction letters
from pdf_generator import generate_sanction_letter, SANCTION_LETTERS_FOLDER

# Configure logging with Phase 8 prefix
logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s | PHASE8_CLOSURE | %(levelname)s | %(message)s', datefmt='%H:%M:%S')
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


# ================================================================================
# CONSTANTS AND CONFIGURATION
# ================================================================================

class JourneyStatus(Enum):
    """Final journey status after closure."""
    SANCTIONED = "SANCTIONED"      # Loan approved, sanction letter generated
    REJECTED = "REJECTED"          # Loan rejected, clear reason provided
    INCOMPLETE = "INCOMPLETE"      # Journey not yet closed


class RejectionCategory(Enum):
    """
    Standard rejection categories.
    ONLY ONE category is shown to the customer.
    """
    LOW_CREDIT_SCORE = "low_credit_score"
    INCOME_ELIGIBILITY = "income_eligibility"
    KYC_VERIFICATION_FAILURE = "kyc_verification_failure"
    EXCEEDS_LIMIT = "exceeds_limit"
    EMI_UNAFFORDABLE = "emi_unaffordable"
    UNKNOWN = "unknown"


# Standard rejection messages (customer-facing)
REJECTION_MESSAGES: Dict[RejectionCategory, str] = {
    RejectionCategory.LOW_CREDIT_SCORE: 
        "Thank you for your application. Based on our evaluation, we're unable to proceed "
        "due to credit eligibility criteria. You're welcome to apply again in the future "
        "after improving your credit profile.",
    
    RejectionCategory.INCOME_ELIGIBILITY:
        "Thank you for your application. Based on our evaluation, we're unable to proceed "
        "due to income eligibility criteria. You're welcome to apply again in the future "
        "when your income profile has changed.",
    
    RejectionCategory.KYC_VERIFICATION_FAILURE:
        "Thank you for your application. Unfortunately, we were unable to verify your "
        "identity documents. Please ensure your PAN and Aadhaar details are correct "
        "and consider reapplying.",
    
    RejectionCategory.EXCEEDS_LIMIT:
        "Thank you for your application. The requested loan amount exceeds our approved "
        "limit for your profile. You're welcome to apply again with a lower amount.",
    
    RejectionCategory.EMI_UNAFFORDABLE:
        "Thank you for your application. Based on our evaluation, the monthly EMI "
        "obligations would exceed our affordability threshold. You're welcome to "
        "apply again for a lower amount or longer tenure.",
    
    RejectionCategory.UNKNOWN:
        "Thank you for your application. Based on our evaluation, we're unable to "
        "proceed with your loan request at this time. You're welcome to apply again "
        "in the future."
}


# ================================================================================
# DATA CLASSES
# ================================================================================

@dataclass
class SanctionResult:
    """Result of sanction letter generation."""
    success: bool
    sanction_letter_path: Optional[str]
    sanction_letter_reference: Optional[str]
    sanction_timestamp: str
    error_message: Optional[str] = None
    
    @property
    def sanction_letter_url(self) -> Optional[str]:
        """Return URL-style path for frontend download."""
        if self.sanction_letter_path and os.path.exists(self.sanction_letter_path):
            # Return relative path from backend folder
            filename = os.path.basename(self.sanction_letter_path)
            return f"/sanction_letters/{filename}"
        return None


@dataclass
class RejectionResult:
    """Result of rejection processing."""
    success: bool
    rejection_category: RejectionCategory
    rejection_message: str
    rejection_timestamp: str
    
    @property
    def is_final(self) -> bool:
        """Rejection is always final."""
        return True


@dataclass
class JourneyClosureResult:
    """Final result of journey closure."""
    journey_completed: bool
    journey_status: JourneyStatus
    timestamp: str
    sanction_result: Optional[SanctionResult] = None
    rejection_result: Optional[RejectionResult] = None
    error_message: Optional[str] = None


# ================================================================================
# ENTRY CONDITION VALIDATION
# ================================================================================

def validate_sanction_entry_conditions(
    loan_status: Optional[str],
    underwriting_timestamp: Optional[str]
) -> Tuple[bool, str]:
    """
    Validate that all entry conditions for SANCTION stage are met.
    
    Entry Conditions (STRICT):
    1. loan_status == "APPROVED"
    2. underwriting_timestamp exists
    
    Args:
        loan_status: Current loan status from underwriting
        underwriting_timestamp: When underwriting decision was made
    
    Returns:
        Tuple of (can_proceed, reason)
    """
    logger.info("Validating SANCTION entry conditions")
    
    # Condition 1: Loan must be APPROVED
    if loan_status != "APPROVED":
        reason = f"Loan status must be APPROVED, got: {loan_status}"
        logger.error(f"SANCTION entry blocked: {reason}")
        return False, reason
    
    # Condition 2: Underwriting timestamp must exist
    if not underwriting_timestamp:
        reason = "Underwriting timestamp missing - underwriting not completed"
        logger.error(f"SANCTION entry blocked: {reason}")
        return False, reason
    
    logger.info("All SANCTION entry conditions met")
    return True, "All conditions met"


def validate_rejection_entry_conditions(
    loan_status: Optional[str],
    rejection_reason: Optional[str]
) -> Tuple[bool, str]:
    """
    Validate that all entry conditions for REJECTION stage are met.
    
    Entry Conditions (STRICT):
    1. loan_status == "REJECTED"
    2. rejection_reason exists
    
    Args:
        loan_status: Current loan status from underwriting
        rejection_reason: Reason for rejection
    
    Returns:
        Tuple of (can_proceed, reason)
    """
    logger.info("Validating REJECTION entry conditions")
    
    # Condition 1: Loan must be REJECTED
    if loan_status != "REJECTED":
        reason = f"Loan status must be REJECTED, got: {loan_status}"
        logger.error(f"REJECTION entry blocked: {reason}")
        return False, reason
    
    # Condition 2: Rejection reason must exist
    if not rejection_reason:
        reason = "Rejection reason missing - cannot reject without reason"
        logger.error(f"REJECTION entry blocked: {reason}")
        return False, reason
    
    logger.info("All REJECTION entry conditions met")
    return True, "All conditions met"


# ================================================================================
# SANCTION LETTER GENERATION
# ================================================================================

def generate_sanction_letter_for_approved_loan(
    customer_name: str,
    loan_amount: float,
    interest_rate: float,
    loan_tenure_months: int,
    calculated_emi: float,
    phone: str = "",
    pan: str = "",
    session_id: str = ""
) -> SanctionResult:
    """
    Generate a sanction letter PDF for an approved loan.
    
    This function:
    1. Validates all required data is present
    2. Calls the PDF generator to create the letter
    3. Returns the file path for download
    
    Args:
        customer_name: Customer's full name
        loan_amount: Approved loan amount in INR
        interest_rate: Interest rate per annum
        loan_tenure_months: Loan tenure in months
        calculated_emi: Monthly EMI amount
        phone: Customer's phone number
        pan: Customer's PAN number
        session_id: Session ID for file naming
    
    Returns:
        SanctionResult with file path and reference
    """
    logger.info("=" * 60)
    logger.info("Sanction letter generation started")
    logger.info("=" * 60)
    
    timestamp = datetime.now().isoformat()
    
    # Validate required data
    if not customer_name:
        logger.error("Customer name missing for sanction letter")
        return SanctionResult(
            success=False,
            sanction_letter_path=None,
            sanction_letter_reference=None,
            sanction_timestamp=timestamp,
            error_message="Customer name is required"
        )
    
    if not loan_amount or loan_amount <= 0:
        logger.error(f"Invalid loan amount: {loan_amount}")
        return SanctionResult(
            success=False,
            sanction_letter_path=None,
            sanction_letter_reference=None,
            sanction_timestamp=timestamp,
            error_message="Valid loan amount is required"
        )
    
    try:
        # Generate the PDF
        logger.info(f"Generating sanction letter for {customer_name}")
        logger.info(f"  Loan Amount: ₹{loan_amount:,.2f}")
        logger.info(f"  Interest Rate: {interest_rate}% p.a.")
        logger.info(f"  Tenure: {loan_tenure_months} months")
        logger.info(f"  EMI: ₹{calculated_emi:,.2f}")
        
        pdf_path = generate_sanction_letter(
            customer_name=customer_name,
            loan_amount=int(loan_amount),
            interest_rate=interest_rate,
            tenure=loan_tenure_months,
            emi=int(calculated_emi),
            phone=phone,
            pan=pan,
            session_id=session_id
        )
        
        # Generate reference number
        sanction_ref = f"AURORA/SL/{datetime.now().strftime('%Y%m%d')}/{session_id[:6].upper() if session_id else 'XXXXXX'}"
        
        logger.info("Sanction letter generated successfully")
        logger.info(f"  Path: {pdf_path}")
        logger.info(f"  Reference: {sanction_ref}")
        
        return SanctionResult(
            success=True,
            sanction_letter_path=pdf_path,
            sanction_letter_reference=sanction_ref,
            sanction_timestamp=timestamp
        )
        
    except Exception as e:
        logger.error(f"Failed to generate sanction letter: {str(e)}")
        return SanctionResult(
            success=False,
            sanction_letter_path=None,
            sanction_letter_reference=None,
            sanction_timestamp=timestamp,
            error_message=f"PDF generation failed: {str(e)}"
        )


# ================================================================================
# REJECTION HANDLING
# ================================================================================

def categorize_rejection(rejection_reason: str) -> RejectionCategory:
    """
    Categorize a rejection reason into a standard category.
    
    This ensures customers receive a SINGLE clear reason,
    not a list of technical details.
    
    Args:
        rejection_reason: Raw rejection reason from underwriting
    
    Returns:
        RejectionCategory for customer messaging
    """
    reason_lower = rejection_reason.lower()
    
    # Map technical reasons to categories
    if "credit score" in reason_lower or "credit threshold" in reason_lower:
        return RejectionCategory.LOW_CREDIT_SCORE
    
    if "income" in reason_lower or "salary" in reason_lower or "emi" in reason_lower or "foir" in reason_lower:
        if "exceed" in reason_lower or "afford" in reason_lower:
            return RejectionCategory.EMI_UNAFFORDABLE
        return RejectionCategory.INCOME_ELIGIBILITY
    
    if "kyc" in reason_lower or "pan" in reason_lower or "aadhaar" in reason_lower or "verification" in reason_lower:
        return RejectionCategory.KYC_VERIFICATION_FAILURE
    
    if "limit" in reason_lower or "exceed" in reason_lower or "amount" in reason_lower:
        return RejectionCategory.EXCEEDS_LIMIT
    
    return RejectionCategory.UNKNOWN


def process_rejection(rejection_reason: str) -> RejectionResult:
    """
    Process a loan rejection and generate customer-facing message.
    
    This function:
    1. Categorizes the technical rejection reason
    2. Generates a polite, professional customer message
    3. Does NOT upsell or suggest workarounds
    
    Args:
        rejection_reason: Technical reason from underwriting
    
    Returns:
        RejectionResult with customer-facing message
    """
    logger.info("=" * 60)
    logger.info(f"Loan rejected: {rejection_reason}")
    logger.info("=" * 60)
    
    timestamp = datetime.now().isoformat()
    
    # Categorize the rejection
    category = categorize_rejection(rejection_reason)
    logger.info(f"Rejection category: {category.value}")
    
    # Get customer-facing message
    message = REJECTION_MESSAGES.get(category, REJECTION_MESSAGES[RejectionCategory.UNKNOWN])
    
    logger.info(f"Customer message generated")
    
    return RejectionResult(
        success=True,
        rejection_category=category,
        rejection_message=message,
        rejection_timestamp=timestamp
    )


# ================================================================================
# JOURNEY CLOSURE
# ================================================================================

def close_journey_with_sanction(
    session_id: str,
    customer_name: str,
    loan_amount: float,
    interest_rate: float,
    loan_tenure_months: int,
    calculated_emi: float,
    phone: str = "",
    pan: str = "",
    sanction_letter_generated: bool = False
) -> JourneyClosureResult:
    """
    Close the journey with a successful sanction.
    
    This function:
    1. Validates sanction hasn't already been generated (prevent duplicates)
    2. Generates the sanction letter PDF
    3. Returns journey closure result
    
    Args:
        session_id: Session ID
        customer_name: Customer's full name
        loan_amount: Approved loan amount
        interest_rate: Interest rate per annum
        loan_tenure_months: Loan tenure in months
        calculated_emi: Monthly EMI
        phone: Customer phone
        pan: Customer PAN
        sanction_letter_generated: Whether letter was already generated
    
    Returns:
        JourneyClosureResult with sanction details
    """
    logger.info("Loan journey completed - SANCTION")
    timestamp = datetime.now().isoformat()
    
    # Check if already generated (prevent duplicates)
    if sanction_letter_generated:
        logger.warning("Sanction letter already generated - preventing duplicate")
        return JourneyClosureResult(
            journey_completed=True,
            journey_status=JourneyStatus.SANCTIONED,
            timestamp=timestamp,
            error_message="Sanction letter already generated"
        )
    
    # Generate sanction letter
    sanction_result = generate_sanction_letter_for_approved_loan(
        customer_name=customer_name,
        loan_amount=loan_amount,
        interest_rate=interest_rate,
        loan_tenure_months=loan_tenure_months,
        calculated_emi=calculated_emi,
        phone=phone,
        pan=pan,
        session_id=session_id
    )
    
    if sanction_result.success:
        logger.info("Journey completed successfully with SANCTION")
        return JourneyClosureResult(
            journey_completed=True,
            journey_status=JourneyStatus.SANCTIONED,
            timestamp=timestamp,
            sanction_result=sanction_result
        )
    else:
        logger.error(f"Journey closure failed: {sanction_result.error_message}")
        return JourneyClosureResult(
            journey_completed=False,
            journey_status=JourneyStatus.INCOMPLETE,
            timestamp=timestamp,
            sanction_result=sanction_result,
            error_message=sanction_result.error_message
        )


def close_journey_with_rejection(
    rejection_reason: str
) -> JourneyClosureResult:
    """
    Close the journey with a rejection.
    
    This function:
    1. Processes the rejection reason
    2. Generates customer-facing message
    3. Marks journey as completed
    
    Args:
        rejection_reason: Technical reason from underwriting
    
    Returns:
        JourneyClosureResult with rejection details
    """
    logger.info("Loan journey completed - REJECTION")
    timestamp = datetime.now().isoformat()
    
    # Process rejection
    rejection_result = process_rejection(rejection_reason)
    
    return JourneyClosureResult(
        journey_completed=True,
        journey_status=JourneyStatus.REJECTED,
        timestamp=timestamp,
        rejection_result=rejection_result
    )


# ================================================================================
# STATE PERSISTENCE HELPERS
# ================================================================================

def get_sanction_state_updates(sanction_result: SanctionResult) -> Dict[str, Any]:
    """
    Get state updates for sanction completion.
    
    These fields should be persisted to session state
    after successful sanction letter generation.
    """
    return {
        "sanction_letter_generated": sanction_result.success,
        "sanction_letter_path": sanction_result.sanction_letter_path,
        "sanction_letter_reference": sanction_result.sanction_letter_reference,
        "sanction_timestamp": sanction_result.sanction_timestamp,
        "journey_completed": sanction_result.success,
        "session_closed": sanction_result.success,
        "closure_reason": "SANCTION_COMPLETE" if sanction_result.success else "SANCTION_FAILED"
    }


def get_rejection_state_updates(rejection_result: RejectionResult) -> Dict[str, Any]:
    """
    Get state updates for rejection completion.
    
    These fields should be persisted to session state
    after rejection processing.
    """
    return {
        "rejection_category": rejection_result.rejection_category.value,
        "rejection_message": rejection_result.rejection_message,
        "rejection_timestamp": rejection_result.rejection_timestamp,
        "journey_completed": True,
        "session_closed": True,
        "closure_reason": "REJECTION_COMPLETE"
    }


# ================================================================================
# CHATBOT MESSAGE GENERATORS
# ================================================================================

def get_sanction_confirmation_message(
    customer_name: str,
    loan_amount: float,
    sanction_reference: str
) -> str:
    """
    Generate the congratulatory message for sanction.
    
    Example:
    "Congratulations! Your personal loan has been approved.
    You can download your sanction letter below."
    """
    amount_formatted = format_currency(loan_amount)
    
    return (
        f"🎉 Congratulations, {customer_name}!\n\n"
        f"Your personal loan of {amount_formatted} has been approved!\n\n"
        f"**Sanction Reference:** {sanction_reference}\n\n"
        f"You can download your sanction letter below. "
        f"Please review it carefully before proceeding to disbursement.\n\n"
        f"Thank you for choosing Aurora Finance!"
    )


def get_rejection_final_message(rejection_reason: str) -> str:
    """
    Generate the final rejection message.
    
    Uses the standard message based on categorized reason.
    Does NOT upsell or suggest workarounds.
    """
    rejection_result = process_rejection(rejection_reason)
    return rejection_result.rejection_message


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def format_currency(amount: float) -> str:
    """Format currency in Indian format with ₹ symbol."""
    if amount >= 10000000:  # 1 crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 lakh
        return f"₹{amount/100000:.2f} L"
    elif amount >= 1000:
        return f"₹{amount/1000:.1f}K"
    else:
        return f"₹{amount:,.0f}"


def is_journey_closed(journey_completed: bool, session_closed: bool) -> bool:
    """Check if journey is already closed."""
    return journey_completed or session_closed


def can_accept_further_input(
    current_stage: str,
    journey_completed: bool,
    session_closed: bool
) -> Tuple[bool, str]:
    """
    Check if further user input should be accepted.
    
    After SANCTION or REJECTION, no further inputs should be processed.
    
    Returns:
        Tuple of (can_accept, reason)
    """
    if is_journey_closed(journey_completed, session_closed):
        return False, "Journey has been completed. No further input accepted."
    
    if current_stage in ["SANCTION", "REJECTION"]:
        return False, f"Application is in terminal state: {current_stage}"
    
    return True, "Input accepted"


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 8: JOURNEY CLOSURE SERVICE TEST")
    print("=" * 60)
    
    # Test 1: Sanction entry validation
    print("\n--- Test 1: Sanction Entry Validation ---")
    
    # Valid case
    can_proceed, reason = validate_sanction_entry_conditions(
        loan_status="APPROVED",
        underwriting_timestamp="2025-01-31T10:00:00"
    )
    print(f"Valid case: can_proceed={can_proceed}, reason={reason}")
    
    # Invalid case - wrong status
    can_proceed, reason = validate_sanction_entry_conditions(
        loan_status="REJECTED",
        underwriting_timestamp="2025-01-31T10:00:00"
    )
    print(f"Wrong status: can_proceed={can_proceed}, reason={reason}")
    
    # Invalid case - missing timestamp
    can_proceed, reason = validate_sanction_entry_conditions(
        loan_status="APPROVED",
        underwriting_timestamp=None
    )
    print(f"Missing timestamp: can_proceed={can_proceed}, reason={reason}")
    
    # Test 2: Rejection entry validation
    print("\n--- Test 2: Rejection Entry Validation ---")
    
    can_proceed, reason = validate_rejection_entry_conditions(
        loan_status="REJECTED",
        rejection_reason="Credit score below threshold"
    )
    print(f"Valid case: can_proceed={can_proceed}, reason={reason}")
    
    # Test 3: Rejection categorization
    print("\n--- Test 3: Rejection Categorization ---")
    
    test_reasons = [
        "Credit score 650 is below minimum threshold of 700",
        "Monthly EMI obligations exceed 50% of verified income",
        "PAN verification failed",
        "Requested amount exceeds maximum limit",
        "Some unknown reason"
    ]
    
    for reason in test_reasons:
        category = categorize_rejection(reason)
        print(f"'{reason[:40]}...' → {category.value}")
    
    # Test 4: Sanction letter generation
    print("\n--- Test 4: Sanction Letter Generation ---")
    
    sanction_result = generate_sanction_letter_for_approved_loan(
        customer_name="Rahul Sharma",
        loan_amount=500000,
        interest_rate=12.5,
        loan_tenure_months=36,
        calculated_emi=16750,
        phone="9876543210",
        pan="ABCDE1234F",
        session_id="test_phase8_001"
    )
    
    print(f"Success: {sanction_result.success}")
    print(f"Path: {sanction_result.sanction_letter_path}")
    print(f"Reference: {sanction_result.sanction_letter_reference}")
    print(f"URL: {sanction_result.sanction_letter_url}")
    
    # Test 5: Complete journey closure
    print("\n--- Test 5: Journey Closure ---")
    
    # Approved case
    closure_result = close_journey_with_sanction(
        session_id="test_phase8_002",
        customer_name="Priya Patel",
        loan_amount=300000,
        interest_rate=11.5,
        loan_tenure_months=24,
        calculated_emi=14100,
        phone="9876543211",
        pan="XYZAB5678C"
    )
    
    print(f"Approved closure: completed={closure_result.journey_completed}, status={closure_result.journey_status.value}")
    
    # Rejected case
    closure_result = close_journey_with_rejection(
        rejection_reason="Credit score 650 is below minimum threshold of 700"
    )
    
    print(f"Rejected closure: completed={closure_result.journey_completed}, status={closure_result.journey_status.value}")
    print(f"Message: {closure_result.rejection_result.rejection_message[:100]}...")
    
    print("\n" + "=" * 60)
    print("PHASE 8: JOURNEY CLOSURE SERVICE TEST COMPLETE")
    print("=" * 60)
