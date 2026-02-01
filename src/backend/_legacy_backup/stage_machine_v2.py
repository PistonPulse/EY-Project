"""
================================================================================
PHASE 1: STRICT DETERMINISTIC STAGE MACHINE
================================================================================

This module implements a STRICT stage-based conversation control system.
It is the SINGLE SOURCE OF TRUTH for the loan application journey.

================================================================================
WHY A STRICT STAGE MACHINE IS REQUIRED
================================================================================

PROBLEM:
- Without strict flow control, the chatbot jumps between stages randomly
- LLM decisions are non-deterministic - same input can produce different outputs
- UI state becomes inconsistent with backend state
- Verification triggers at wrong times or skips entirely
- System becomes unpredictable and unreliable

SOLUTION:
- ONE variable (current_stage) controls the entire flow
- ONLY backend Python logic can update current_stage
- Stage transitions are EXPLICIT and SEQUENTIAL
- Invalid transitions are BLOCKED and LOGGED
- State persists across page reloads

================================================================================
WHY LLMs MUST NEVER CONTROL FLOW
================================================================================

LLMs are:
- Non-deterministic (same input → different outputs)
- Context-dependent (responses vary with history)
- Prone to "hallucination" (inventing data/skipping steps)
- Not auditable (can't trace why a decision was made)

This stage machine ensures:
- DETERMINISTIC flow (same input → same stage transition)
- AUDITABLE decisions (every transition is logged)
- REGULATORY COMPLIANCE (no skipped verification steps)
- PREDICTABLE behavior (system acts the same every time)

================================================================================
STAGE DEFINITIONS (NON-NEGOTIABLE)
================================================================================

These are the ONLY valid stages. No others are permitted.

GREETING           - Initial contact, welcome user
NEEDS_DISCOVERY    - Understand loan requirements (amount, purpose)
BASIC_ELIGIBILITY  - Initial eligibility check (before KYC)
KYC_COLLECTION     - Collect identity information (name, mobile)
OTP_VERIFICATION   - Verify mobile number via OTP
KYC_VERIFICATION   - Verify identity against CRM/database
OFFER_DISCOVERY    - Check pre-approved offers
INCOME_DOC_UPLOAD  - Collect income documents
UNDERWRITING       - Make loan decision (rules engine only)
SANCTION           - Loan approved (terminal state)
REJECTION          - Loan rejected (terminal state)

================================================================================
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import logging

# ================================================================================
# CONFIGURE LOGGING
# ================================================================================
# Clear, visible logs for debugging stage transitions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | STAGE_MACHINE | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('stage_machine')


# ================================================================================
# STAGE ENUMERATION - THE ONLY VALID STAGES
# ================================================================================

class Stage(Enum):
    """
    Enumeration of ALL valid stages in the loan journey.
    
    NO OTHER VALUES ARE PERMITTED.
    The system MUST be in exactly ONE of these stages at all times.
    """
    GREETING = "GREETING"
    NEEDS_DISCOVERY = "NEEDS_DISCOVERY"
    BASIC_ELIGIBILITY = "BASIC_ELIGIBILITY"
    KYC_COLLECTION = "KYC_COLLECTION"
    OTP_VERIFICATION = "OTP_VERIFICATION"
    KYC_VERIFICATION = "KYC_VERIFICATION"
    OFFER_DISCOVERY = "OFFER_DISCOVERY"
    INCOME_DOC_UPLOAD = "INCOME_DOC_UPLOAD"
    UNDERWRITING = "UNDERWRITING"
    SANCTION = "SANCTION"
    REJECTION = "REJECTION"


# ================================================================================
# EVENTS - TRIGGERS FOR STAGE TRANSITIONS
# ================================================================================

class StageEvent(Enum):
    """
    Events that can trigger stage transitions.
    
    Each event represents a SPECIFIC user action or system outcome.
    Events are the ONLY way to request a stage transition.
    """
    # User actions
    USER_GREETED = "USER_GREETED"
    LOAN_AMOUNT_PROVIDED = "LOAN_AMOUNT_PROVIDED"
    ELIGIBILITY_CHECKED = "ELIGIBILITY_CHECKED"
    KYC_INFO_PROVIDED = "KYC_INFO_PROVIDED"
    OTP_SENT = "OTP_SENT"
    OTP_VERIFIED = "OTP_VERIFIED"
    OTP_FAILED = "OTP_FAILED"
    KYC_VERIFIED = "KYC_VERIFIED"
    KYC_FAILED = "KYC_FAILED"
    OFFERS_CHECKED = "OFFERS_CHECKED"
    DOCUMENTS_UPLOADED = "DOCUMENTS_UPLOADED"
    UNDERWRITING_APPROVED = "UNDERWRITING_APPROVED"
    UNDERWRITING_REJECTED = "UNDERWRITING_REJECTED"
    
    # System events
    SESSION_STARTED = "SESSION_STARTED"
    SESSION_RESET = "SESSION_RESET"


# ================================================================================
# VALID TRANSITIONS - THE STAGE TRANSITION MATRIX
# ================================================================================
# This defines EXACTLY which transitions are allowed.
# Any transition NOT in this matrix will be BLOCKED.

VALID_TRANSITIONS: Dict[Stage, Dict[StageEvent, Stage]] = {
    Stage.GREETING: {
        StageEvent.USER_GREETED: Stage.NEEDS_DISCOVERY,
        StageEvent.LOAN_AMOUNT_PROVIDED: Stage.NEEDS_DISCOVERY,  # Can skip if amount in first message
    },
    
    Stage.NEEDS_DISCOVERY: {
        StageEvent.LOAN_AMOUNT_PROVIDED: Stage.BASIC_ELIGIBILITY,
    },
    
    Stage.BASIC_ELIGIBILITY: {
        StageEvent.ELIGIBILITY_CHECKED: Stage.KYC_COLLECTION,
    },
    
    Stage.KYC_COLLECTION: {
        StageEvent.KYC_INFO_PROVIDED: Stage.OTP_VERIFICATION,
    },
    
    Stage.OTP_VERIFICATION: {
        StageEvent.OTP_VERIFIED: Stage.KYC_VERIFICATION,
        StageEvent.OTP_FAILED: Stage.KYC_COLLECTION,  # Go back to collect again
    },
    
    Stage.KYC_VERIFICATION: {
        StageEvent.KYC_VERIFIED: Stage.OFFER_DISCOVERY,
        StageEvent.KYC_FAILED: Stage.REJECTION,  # KYC failure = rejection
    },
    
    Stage.OFFER_DISCOVERY: {
        StageEvent.OFFERS_CHECKED: Stage.INCOME_DOC_UPLOAD,
    },
    
    Stage.INCOME_DOC_UPLOAD: {
        StageEvent.DOCUMENTS_UPLOADED: Stage.UNDERWRITING,
    },
    
    Stage.UNDERWRITING: {
        StageEvent.UNDERWRITING_APPROVED: Stage.SANCTION,
        StageEvent.UNDERWRITING_REJECTED: Stage.REJECTION,
    },
    
    # Terminal states - no transitions allowed
    Stage.SANCTION: {},
    Stage.REJECTION: {},
}


# ================================================================================
# STAGE STATE - THE SINGLE SOURCE OF TRUTH
# ================================================================================

@dataclass
class StageState:
    """
    The SINGLE SOURCE OF TRUTH for the loan application state.
    
    CRITICAL RULES:
    1. current_stage is the ONLY variable that controls flow
    2. Only StageController.transition() can modify current_stage
    3. UI and LLM may ONLY READ this state
    4. State persists across page reloads
    """
    # =========================================================================
    # CORE STAGE CONTROL (THE SINGLE SOURCE OF TRUTH)
    # =========================================================================
    current_stage: Stage = Stage.GREETING
    
    # =========================================================================
    # SESSION IDENTITY
    # =========================================================================
    session_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # =========================================================================
    # TRANSITION HISTORY (FOR AUDIT)
    # =========================================================================
    transition_history: list = field(default_factory=list)
    
    # =========================================================================
    # COLLECTED DATA (READ-ONLY FOR LLM)
    # =========================================================================
    # User identity
    user_name: Optional[str] = None
    user_mobile: Optional[str] = None
    user_pan: Optional[str] = None
    user_email: Optional[str] = None
    
    # Loan request
    loan_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    loan_tenure_months: int = 36
    
    # =========================================================================
    # PHASE 3: OTP VERIFICATION - IDENTITY LOCKING
    # =========================================================================
    # WHY OTP PRECEDES KYC VERIFICATION:
    #   Identity must be LOCKED (verified) before any CRM data is fetched.
    #   Without OTP verification, an attacker could enter any mobile number
    #   and harvest sensitive customer data from CRM.
    #
    # HOW IDENTITY LOCKING PREVENTS FRAUD:
    #   1. User provides name + mobile → stored but NOT verified
    #   2. OTP sent to mobile → only legitimate user receives it
    #   3. OTP verified → identity is LOCKED
    #   4. CRM lookup → ONLY happens after identity lock
    #
    # WHY LLM MUST NEVER CONTROL OTP LOGIC:
    #   LLM is non-deterministic and prompt-injectable.
    #   OTP verification MUST be deterministic string comparison.
    #   See otp_security.py for implementation.
    # =========================================================================
    otp_code: Optional[str] = None
    otp_generation_timestamp: Optional[str] = None  # When OTP was generated
    otp_sent: bool = False
    otp_verified: bool = False
    otp_attempts: int = 0  # Max 3 attempts allowed
    
    # KYC status
    kyc_verified: bool = False
    is_existing_customer: bool = False
    customer_id: Optional[str] = None
    
    # =========================================================================
    # PHASE 4: PAN AND AADHAAR VERIFICATION
    # =========================================================================
    # WHY PAN PRECEDES AADHAAR:
    #   PAN is the primary financial identifier (Income Tax Dept).
    #   Verifying PAN first establishes tax identity before proceeding.
    #   PAN-Aadhaar linkage can then be cross-verified.
    #
    # WHY VERIFICATION MUST BE SEQUENTIAL:
    #   1. Aadhaar verification may depend on PAN results
    #   2. If PAN fails, no need to verify Aadhaar
    #   3. Cleaner failure states and audit trail
    #
    # HOW DETERMINISTIC APIs PREVENT HALLUCINATION:
    #   LLM has NO role in determining verification outcome.
    #   Same PAN/Aadhaar always produces same result.
    #   See kyc_verification.py for implementation.
    # =========================================================================
    user_aadhaar: Optional[str] = None
    pan_verified: bool = False
    pan_verification_timestamp: Optional[str] = None
    aadhaar_verified: bool = False
    aadhaar_verification_timestamp: Optional[str] = None
    kyc_status: Optional[str] = None  # VERIFIED, PAN_PENDING, AADHAAR_PENDING
    
    # =========================================================================
    # PHASE 5: OFFER DISCOVERY AND INTEREST RATE RANGE
    # =========================================================================
    # WHY INTEREST RATE IS A RANGE (NOT A FIXED NUMBER):
    #   NBFCs never quote a single rate upfront. Ranges allow for:
    #   - Income verification adjustments
    #   - Relationship value consideration
    #   - Market condition flexibility
    #   - Negotiation room for RMs
    #
    # HOW CREDIT BANDS AFFECT PRICING:
    #   Band A (≥800): 10.5% – 11.5% base
    #   Band B (750-799): 11.5% – 12.5% base
    #   Band C (700-749): 12.5% – 14.0% base
    #   Band D (<700): 14.0% – 18.0% (flagged for review)
    #
    # MODIFIERS:
    #   - Existing customer: -0.25%
    #   - Pre-approved offer: -0.25%
    #
    # WHY FINAL RATE IS DECIDED IN UNDERWRITING:
    #   This stage provides INDICATIVE rates. Final rate depends on:
    #   - Income verification results
    #   - Debt-to-income ratio
    #   - Employment stability
    #   - Document quality
    # =========================================================================
    interest_rate_min: Optional[float] = None  # Lower bound of rate range
    interest_rate_max: Optional[float] = None  # Upper bound of rate range
    interest_rate_band_reason: Optional[str] = None  # Explanation of rate band
    credit_band: Optional[str] = None  # A, B, C, or D
    preapproved_offer: bool = False  # Whether customer has pre-approved offer
    offer_discovery_timestamp: Optional[str] = None
    risk_flag: Optional[str] = None  # For Band D customers
    
    # Financial data (legacy field kept for compatibility)
    credit_score: Optional[int] = None
    monthly_income: Optional[float] = None
    pre_approved_limit: float = 0
    interest_rate: Optional[float] = None  # DEPRECATED: Use interest_rate_min/max
    emi_amount: Optional[float] = None
    
    # Document status
    documents_uploaded: list = field(default_factory=list)
    documents_verified: bool = False
    
    # =========================================================================
    # PHASE 6: INCOME VERIFICATION
    # =========================================================================
    # WHY INCOME VERIFICATION IS ISOLATED:
    #   Income verification is a critical financial validation step that MUST:
    #   - Run exactly once per application
    #   - Produce deterministic, reproducible results
    #   - Not be influenced by LLM hallucinations
    #
    # WHY UPLOAD IS STAGE-CONTROLLED:
    #   Upload button visibility tied to stage prevents:
    #   - Premature uploads before KYC
    #   - Late uploads after underwriting
    #   - Orphaned documents without context
    #
    # HOW THIS PREVENTS UI DEADLOCKS:
    #   - Button appears exactly when needed
    #   - Button disappears after success (no re-upload)
    #   - Clear state transitions
    #   - No flickering or race conditions
    # =========================================================================
    income_verified: bool = False
    verified_monthly_salary_inr: Optional[int] = None
    income_verification_timestamp: Optional[str] = None
    income_document_id: Optional[str] = None
    income_upload_attempted: bool = False
    income_retry_count: int = 0
    
    # =========================================================================
    # PHASE 7: UNDERWRITING DECISION
    # =========================================================================
    # WHY UNDERWRITING IS ISOLATED:
    #   Underwriting makes FINAL loan approval/rejection decisions.
    #   This decision MUST be deterministic and auditable.
    #   LLM involvement would introduce inconsistency and legal risk.
    #
    # WHY DECISIONS MUST BE DETERMINISTIC:
    #   - Regulatory compliance requires consistent decision criteria
    #   - Same inputs MUST always produce same outputs
    #   - Auditors need verifiable decision logic
    #
    # WHY LLM CANNOT BE TRUSTED WITH APPROVALS:
    #   - LLMs can hallucinate justifications
    #   - Same prompt can produce different decisions
    #   - Bias amplification risk
    #   - Audit trail issues
    # =========================================================================
    loan_status: Optional[str] = None  # APPROVED, REJECTED, PENDING
    approval_reason: Optional[str] = None  # If APPROVED
    rejection_reason: Optional[str] = None  # If REJECTED
    underwriting_timestamp: Optional[str] = None  # When decision was made
    underwriting_completed: bool = False  # Prevents re-running underwriting
    calculated_emi: Optional[float] = None  # EMI computed during underwriting
    foir: Optional[float] = None  # Fixed Obligation to Income Ratio (%)
    existing_emi: int = 0  # Customer's existing monthly EMI obligations
    sanction_reference: Optional[str] = None  # Reference number for approved loans
    
    # =========================================================================
    # PHASE 8: JOURNEY CLOSURE STATE
    # =========================================================================
    # WHY SANCTION IS A TERMINAL STAGE:
    #   Once a loan is sanctioned, the decision is FINAL.
    #   The sanction letter is a legally binding document.
    #   No further modifications are allowed to the loan terms.
    #
    # WHY REJECTION MUST BE FINAL:
    #   Clear, honest communication builds trust.
    #   No false hope or misleading suggestions.
    #   Professional closure maintains brand reputation.
    #
    # HOW CLEAN CLOSURE IMPROVES TRUST:
    #   - Approved users receive downloadable sanction letters
    #   - Rejected users receive clear, respectful messages
    #   - Journey ends cleanly with no ambiguity
    #   - No further inputs accepted after closure
    # =========================================================================
    sanction_letter_generated: bool = False  # Whether sanction letter was created
    sanction_letter_path: Optional[str] = None  # File path to PDF
    sanction_letter_reference: Optional[str] = None  # Unique letter reference
    sanction_timestamp: Optional[str] = None  # When letter was generated
    rejection_category: Optional[str] = None  # Standardized rejection category
    rejection_message: Optional[str] = None  # Customer-facing rejection message
    rejection_timestamp: Optional[str] = None  # When rejection was processed
    journey_completed: bool = False  # Whether journey has ended
    
    # Session closure
    session_closed: bool = False
    closure_reason: Optional[str] = None
    
    # =========================================================================
    # PHASE 2: CONVERSATION PROGRESS TRACKING
    # =========================================================================
    # Track which sub-step we're on within each stage (for question sequencing)
    conversation_step: Optional[str] = None  # Current ConversationStep value
    questions_asked: list = field(default_factory=list)  # List of asked ConversationStep values
    questions_answered: list = field(default_factory=list)  # List of answered ConversationStep values
    
    # Additional data for BASIC_ELIGIBILITY stage
    city: Optional[str] = None
    employment_type: Optional[str] = None  # "Salaried" or "Self-Employed"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "current_stage": self.current_stage.value,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "transition_history": self.transition_history,
            "user_name": self.user_name,
            "user_mobile": self.user_mobile,
            "user_pan": self.user_pan,
            "user_email": self.user_email,
            "loan_amount": self.loan_amount,
            "loan_purpose": self.loan_purpose,
            "loan_tenure_months": self.loan_tenure_months,
            "otp_code": self.otp_code,
            "otp_generation_timestamp": self.otp_generation_timestamp,
            "otp_sent": self.otp_sent,
            "otp_verified": self.otp_verified,
            "otp_attempts": self.otp_attempts,
            "kyc_verified": self.kyc_verified,
            "is_existing_customer": self.is_existing_customer,
            "customer_id": self.customer_id,
            # Phase 4: PAN and Aadhaar verification
            "user_aadhaar": self.user_aadhaar,
            "pan_verified": self.pan_verified,
            "pan_verification_timestamp": self.pan_verification_timestamp,
            "aadhaar_verified": self.aadhaar_verified,
            "aadhaar_verification_timestamp": self.aadhaar_verification_timestamp,
            "kyc_status": self.kyc_status,
            # Phase 5: Offer discovery and interest rate range
            "interest_rate_min": self.interest_rate_min,
            "interest_rate_max": self.interest_rate_max,
            "interest_rate_band_reason": self.interest_rate_band_reason,
            "credit_band": self.credit_band,
            "preapproved_offer": self.preapproved_offer,
            "offer_discovery_timestamp": self.offer_discovery_timestamp,
            "risk_flag": self.risk_flag,
            # Phase 6: Income verification
            "income_verified": self.income_verified,
            "verified_monthly_salary_inr": self.verified_monthly_salary_inr,
            "income_verification_timestamp": self.income_verification_timestamp,
            "income_document_id": self.income_document_id,
            "income_upload_attempted": self.income_upload_attempted,
            "income_retry_count": self.income_retry_count,
            # Financial data
            "credit_score": self.credit_score,
            "monthly_income": self.monthly_income,
            "pre_approved_limit": self.pre_approved_limit,
            "interest_rate": self.interest_rate,
            "emi_amount": self.emi_amount,
            "documents_uploaded": self.documents_uploaded,
            "documents_verified": self.documents_verified,
            # Phase 7: Underwriting decision
            "loan_status": self.loan_status,
            "approval_reason": self.approval_reason,
            "rejection_reason": self.rejection_reason,
            "underwriting_timestamp": self.underwriting_timestamp,
            "underwriting_completed": self.underwriting_completed,
            "calculated_emi": self.calculated_emi,
            "foir": self.foir,
            "existing_emi": self.existing_emi,
            "sanction_reference": self.sanction_reference,
            # Phase 8: Journey closure
            "sanction_letter_generated": self.sanction_letter_generated,
            "sanction_letter_path": self.sanction_letter_path,
            "sanction_letter_reference": self.sanction_letter_reference,
            "sanction_timestamp": self.sanction_timestamp,
            "rejection_category": self.rejection_category,
            "rejection_message": self.rejection_message,
            "rejection_timestamp": self.rejection_timestamp,
            "journey_completed": self.journey_completed,
            "session_closed": self.session_closed,
            "closure_reason": self.closure_reason,
            # Phase 2: Conversation tracking
            "conversation_step": self.conversation_step,
            "questions_asked": self.questions_asked,
            "questions_answered": self.questions_answered,
            "city": self.city,
            "employment_type": self.employment_type,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageState":
        """Create state from dictionary."""
        state = cls()
        state.current_stage = Stage(data.get("current_stage", "GREETING"))
        state.session_id = data.get("session_id", "")
        state.created_at = data.get("created_at", datetime.now().isoformat())
        state.last_updated = data.get("last_updated", datetime.now().isoformat())
        state.transition_history = data.get("transition_history", [])
        state.user_name = data.get("user_name")
        state.user_mobile = data.get("user_mobile")
        state.user_pan = data.get("user_pan")
        state.user_email = data.get("user_email")
        state.loan_amount = data.get("loan_amount")
        state.loan_purpose = data.get("loan_purpose")
        state.loan_tenure_months = data.get("loan_tenure_months", 36)
        state.otp_code = data.get("otp_code")
        state.otp_generation_timestamp = data.get("otp_generation_timestamp")
        state.otp_sent = data.get("otp_sent", False)
        state.otp_verified = data.get("otp_verified", False)
        state.otp_attempts = data.get("otp_attempts", 0)
        state.kyc_verified = data.get("kyc_verified", False)
        state.is_existing_customer = data.get("is_existing_customer", False)
        state.customer_id = data.get("customer_id")
        state.credit_score = data.get("credit_score")
        state.monthly_income = data.get("monthly_income")
        state.pre_approved_limit = data.get("pre_approved_limit", 0)
        state.interest_rate = data.get("interest_rate")
        state.emi_amount = data.get("emi_amount")
        state.documents_uploaded = data.get("documents_uploaded", [])
        state.documents_verified = data.get("documents_verified", False)
        state.session_closed = data.get("session_closed", False)
        state.closure_reason = data.get("closure_reason")
        # Phase 2: Conversation tracking
        state.conversation_step = data.get("conversation_step")
        state.questions_asked = data.get("questions_asked", [])
        state.questions_answered = data.get("questions_answered", [])
        state.city = data.get("city")
        state.employment_type = data.get("employment_type")
        
        # Phase 4: KYC Verification fields
        state.user_aadhaar = data.get("user_aadhaar")
        state.pan_verified = data.get("pan_verified", False)
        state.pan_verification_timestamp = data.get("pan_verification_timestamp")
        state.aadhaar_verified = data.get("aadhaar_verified", False)
        state.aadhaar_verification_timestamp = data.get("aadhaar_verification_timestamp")
        state.kyc_status = data.get("kyc_status")
        
        # Phase 5: Offer discovery and interest rate range
        state.interest_rate_min = data.get("interest_rate_min")
        state.interest_rate_max = data.get("interest_rate_max")
        state.interest_rate_band_reason = data.get("interest_rate_band_reason")
        state.credit_band = data.get("credit_band")
        state.preapproved_offer = data.get("preapproved_offer", False)
        state.offer_discovery_timestamp = data.get("offer_discovery_timestamp")
        state.risk_flag = data.get("risk_flag")
        
        # Phase 6: Income verification
        state.income_verified = data.get("income_verified", False)
        state.verified_monthly_salary_inr = data.get("verified_monthly_salary_inr")
        state.income_verification_timestamp = data.get("income_verification_timestamp")
        state.income_document_id = data.get("income_document_id")
        state.income_upload_attempted = data.get("income_upload_attempted", False)
        state.income_retry_count = data.get("income_retry_count", 0)
        
        # Phase 7: Underwriting decision
        state.loan_status = data.get("loan_status")
        state.approval_reason = data.get("approval_reason")
        state.rejection_reason = data.get("rejection_reason")
        state.underwriting_timestamp = data.get("underwriting_timestamp")
        state.underwriting_completed = data.get("underwriting_completed", False)
        state.calculated_emi = data.get("calculated_emi")
        state.foir = data.get("foir")
        state.existing_emi = data.get("existing_emi", 0)
        state.sanction_reference = data.get("sanction_reference")
        
        # Phase 8: Journey closure
        state.sanction_letter_generated = data.get("sanction_letter_generated", False)
        state.sanction_letter_path = data.get("sanction_letter_path")
        state.sanction_letter_reference = data.get("sanction_letter_reference")
        state.sanction_timestamp = data.get("sanction_timestamp")
        state.rejection_category = data.get("rejection_category")
        state.rejection_message = data.get("rejection_message")
        state.rejection_timestamp = data.get("rejection_timestamp")
        state.journey_completed = data.get("journey_completed", False)
        return state


# ================================================================================
# STAGE CONTROLLER - THE ONLY COMPONENT THAT CAN CHANGE STAGE
# ================================================================================

class StageController:
    """
    The CENTRALIZED STAGE ROUTER that controls ALL stage transitions.
    
    ================================================================================
    CRITICAL DESIGN PRINCIPLES
    ================================================================================
    
    1. SINGLE POINT OF CONTROL
       - This is the ONLY code that can modify current_stage
       - All transition requests go through transition() method
       - Invalid transitions are BLOCKED
    
    2. DETERMINISTIC TRANSITIONS
       - Given a (current_stage, event) pair, the next stage is FIXED
       - No randomness, no LLM decisions, no context-dependent logic
       - Same input ALWAYS produces same output
    
    3. EXPLICIT LOGGING
       - Every transition attempt is logged
       - Blocked transitions are logged with reason
       - Full audit trail for debugging
    
    4. STATE PERSISTENCE
       - State is saved after every transition
       - Survives page reloads
       - Prevents state loss
    
    ================================================================================
    """
    
    def __init__(self, persistence_dir: str = None):
        """
        Initialize the stage controller.
        
        Args:
            persistence_dir: Directory for state persistence files.
                           Defaults to ./stage_states/
        """
        self.persistence_dir = persistence_dir or os.path.join(
            os.path.dirname(__file__), "stage_states"
        )
        os.makedirs(self.persistence_dir, exist_ok=True)
        
        # In-memory cache for active sessions
        self._sessions: Dict[str, StageState] = {}
        
        logger.info("=" * 60)
        logger.info("STAGE CONTROLLER INITIALIZED")
        logger.info(f"Persistence directory: {self.persistence_dir}")
        logger.info("=" * 60)
    
    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================
    
    def get_or_create_session(self, session_id: str) -> StageState:
        """
        Get existing session or create new one.
        
        PERSISTENCE RULE:
        - First checks in-memory cache
        - Then checks persistence file
        - Finally creates new session
        
        This ensures page reloads don't reset the stage.
        """
        # Check in-memory cache first
        if session_id in self._sessions:
            logger.info(f"Session found in cache: {session_id}")
            return self._sessions[session_id]
        
        # Try to load from persistence
        state = self._load_state(session_id)
        if state:
            self._sessions[session_id] = state
            logger.info(f"Session loaded from persistence: {session_id}")
            logger.info(f"Stage restored: {state.current_stage.value}")
            return state
        
        # Create new session
        state = StageState()
        state.session_id = session_id
        state.created_at = datetime.now().isoformat()
        state.last_updated = datetime.now().isoformat()
        
        # Record initial stage
        state.transition_history.append({
            "timestamp": datetime.now().isoformat(),
            "event": "SESSION_STARTED",
            "from_stage": None,
            "to_stage": Stage.GREETING.value,
            "success": True
        })
        
        self._sessions[session_id] = state
        self._persist_state(state)
        
        logger.info(f"New session created: {session_id}")
        logger.info(f"Stage initialized: {state.current_stage.value}")
        
        return state
    
    def get_current_stage(self, session_id: str) -> Stage:
        """
        Get the current stage for a session.
        
        This is a READ-ONLY operation.
        """
        state = self.get_or_create_session(session_id)
        return state.current_stage
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the full session state as a dictionary.
        
        This is for UI/admin to READ the state.
        They cannot modify it directly.
        """
        if session_id in self._sessions:
            return self._sessions[session_id].to_dict()
        
        state = self._load_state(session_id)
        if state:
            return state.to_dict()
        
        return None
    
    # =========================================================================
    # STAGE TRANSITION - THE CORE FUNCTION
    # =========================================================================
    
    def transition(
        self, 
        session_id: str, 
        event: StageEvent,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Stage, str]:
        """
        Attempt a stage transition.
        
        THIS IS THE ONLY WAY TO CHANGE THE CURRENT STAGE.
        
        ================================================================================
        TRANSITION RULES
        ================================================================================
        
        1. Get current state for session
        2. Look up valid transitions for current stage
        3. Check if the event triggers a valid transition
        4. If valid: update stage, log, persist, return success
        5. If invalid: log blocked attempt, return failure
        
        ================================================================================
        
        Args:
            session_id: The session identifier
            event: The event triggering the transition
            data: Optional data to store with the transition
        
        Returns:
            Tuple of (success: bool, new_stage: Stage, message: str)
        """
        state = self.get_or_create_session(session_id)
        current_stage = state.current_stage
        
        logger.info("-" * 60)
        logger.info(f"TRANSITION REQUEST")
        logger.info(f"  Session: {session_id}")
        logger.info(f"  Current Stage: {current_stage.value}")
        logger.info(f"  Event: {event.value}")
        
        # Check if session is closed (terminal state)
        if state.session_closed:
            msg = f"Session closed. No transitions allowed. Reason: {state.closure_reason}"
            logger.warning(f"  BLOCKED: {msg}")
            return False, current_stage, msg
        
        # Check if current stage is terminal
        if current_stage in (Stage.SANCTION, Stage.REJECTION):
            msg = f"Terminal stage reached ({current_stage.value}). No further transitions."
            logger.warning(f"  BLOCKED: {msg}")
            
            # Mark session as closed
            state.session_closed = True
            state.closure_reason = f"TERMINAL_STAGE_{current_stage.value}"
            self._persist_state(state)
            
            return False, current_stage, msg
        
        # Get valid transitions for current stage
        valid_transitions = VALID_TRANSITIONS.get(current_stage, {})
        
        # Check if event triggers a valid transition
        if event not in valid_transitions:
            msg = f"Invalid transition blocked: {current_stage.value} + {event.value}"
            logger.warning(f"  BLOCKED: {msg}")
            logger.warning(f"  Valid events for {current_stage.value}: {list(valid_transitions.keys())}")
            
            # Record blocked attempt
            state.transition_history.append({
                "timestamp": datetime.now().isoformat(),
                "event": event.value,
                "from_stage": current_stage.value,
                "to_stage": None,
                "success": False,
                "reason": "Invalid transition"
            })
            self._persist_state(state)
            
            return False, current_stage, msg
        
        # Valid transition - execute it
        new_stage = valid_transitions[event]
        old_stage = current_stage
        
        # Update state
        state.current_stage = new_stage
        state.last_updated = datetime.now().isoformat()
        
        # Store provided data
        if data:
            self._apply_data(state, data)
        
        # Handle terminal states
        if new_stage == Stage.SANCTION:
            state.session_closed = True
            state.closure_reason = "LOAN_SANCTIONED"
            state.loan_status = "APPROVED"
        elif new_stage == Stage.REJECTION:
            state.session_closed = True
            state.closure_reason = "LOAN_REJECTED"
            state.loan_status = "REJECTED"
        
        # Record successful transition
        state.transition_history.append({
            "timestamp": datetime.now().isoformat(),
            "event": event.value,
            "from_stage": old_stage.value,
            "to_stage": new_stage.value,
            "success": True,
            "data": data
        })
        
        # Persist state
        self._persist_state(state)
        
        msg = f"Stage transition: {old_stage.value} → {new_stage.value}"
        logger.info(f"  SUCCESS: {msg}")
        logger.info("-" * 60)
        
        return True, new_stage, msg
    
    # =========================================================================
    # DATA MANAGEMENT
    # =========================================================================
    
    def update_data(
        self, 
        session_id: str, 
        data: Dict[str, Any]
    ) -> StageState:
        """
        Update session data WITHOUT changing the stage.
        
        This is for storing user input, extracted entities, etc.
        The current_stage is NOT modified by this method.
        
        Args:
            session_id: The session identifier
            data: Data to update
        
        Returns:
            Updated state
        """
        state = self.get_or_create_session(session_id)
        
        logger.info(f"Data update for session {session_id}: {list(data.keys())}")
        
        self._apply_data(state, data)
        state.last_updated = datetime.now().isoformat()
        self._persist_state(state)
        
        return state
    
    def _apply_data(self, state: StageState, data: Dict[str, Any]):
        """Apply data dictionary to state fields."""
        if "user_name" in data:
            state.user_name = data["user_name"]
        if "user_mobile" in data:
            state.user_mobile = data["user_mobile"]
        if "user_pan" in data:
            state.user_pan = data["user_pan"]
        if "user_email" in data:
            state.user_email = data["user_email"]
        if "loan_amount" in data:
            state.loan_amount = data["loan_amount"]
        if "loan_purpose" in data:
            state.loan_purpose = data["loan_purpose"]
        if "loan_tenure_months" in data:
            state.loan_tenure_months = data["loan_tenure_months"]
        # Phase 3: OTP fields - LLM MUST NEVER modify these directly
        if "otp_code" in data:
            state.otp_code = data["otp_code"]
        if "otp_generation_timestamp" in data:
            state.otp_generation_timestamp = data["otp_generation_timestamp"]
        if "otp_sent" in data:
            state.otp_sent = data["otp_sent"]
        if "otp_verified" in data:
            state.otp_verified = data["otp_verified"]
        if "otp_attempts" in data:
            state.otp_attempts = data["otp_attempts"]
        if "kyc_verified" in data:
            state.kyc_verified = data["kyc_verified"]
        if "is_existing_customer" in data:
            state.is_existing_customer = data["is_existing_customer"]
        if "customer_id" in data:
            state.customer_id = data["customer_id"]
        if "credit_score" in data:
            state.credit_score = data["credit_score"]
        if "monthly_income" in data:
            state.monthly_income = data["monthly_income"]
        if "pre_approved_limit" in data:
            state.pre_approved_limit = data["pre_approved_limit"]
        if "interest_rate" in data:
            state.interest_rate = data["interest_rate"]
        if "emi_amount" in data:
            state.emi_amount = data["emi_amount"]
        if "documents_uploaded" in data:
            state.documents_uploaded = data["documents_uploaded"]
        if "documents_verified" in data:
            state.documents_verified = data["documents_verified"]
        if "loan_status" in data:
            state.loan_status = data["loan_status"]
        if "rejection_reason" in data:
            state.rejection_reason = data["rejection_reason"]
        if "sanction_reference" in data:
            state.sanction_reference = data["sanction_reference"]
        # Phase 2: Conversation tracking fields
        if "conversation_step" in data:
            state.conversation_step = data["conversation_step"]
        if "questions_asked" in data:
            state.questions_asked = data["questions_asked"]
        if "questions_answered" in data:
            state.questions_answered = data["questions_answered"]
        if "city" in data:
            state.city = data["city"]
        if "employment_type" in data:
            state.employment_type = data["employment_type"]
        
        # Phase 4: KYC Verification fields - ONLY system code can modify these
        if "user_aadhaar" in data:
            state.user_aadhaar = data["user_aadhaar"]
        if "pan_verified" in data:
            state.pan_verified = data["pan_verified"]
        if "pan_verification_timestamp" in data:
            state.pan_verification_timestamp = data["pan_verification_timestamp"]
        if "aadhaar_verified" in data:
            state.aadhaar_verified = data["aadhaar_verified"]
        if "aadhaar_verification_timestamp" in data:
            state.aadhaar_verification_timestamp = data["aadhaar_verification_timestamp"]
        if "kyc_status" in data:
            state.kyc_status = data["kyc_status"]
        
        # Phase 5: Offer discovery fields - LLM MUST NEVER calculate these
        if "interest_rate_min" in data:
            state.interest_rate_min = data["interest_rate_min"]
        if "interest_rate_max" in data:
            state.interest_rate_max = data["interest_rate_max"]
        if "interest_rate_band_reason" in data:
            state.interest_rate_band_reason = data["interest_rate_band_reason"]
        if "credit_band" in data:
            state.credit_band = data["credit_band"]
        if "preapproved_offer" in data:
            state.preapproved_offer = data["preapproved_offer"]
        if "offer_discovery_timestamp" in data:
            state.offer_discovery_timestamp = data["offer_discovery_timestamp"]
        if "risk_flag" in data:
            state.risk_flag = data["risk_flag"]
        
        # Phase 6: Income verification fields - ONLY system code can modify these
        if "income_verified" in data:
            state.income_verified = data["income_verified"]
        if "verified_monthly_salary_inr" in data:
            state.verified_monthly_salary_inr = data["verified_monthly_salary_inr"]
        if "income_verification_timestamp" in data:
            state.income_verification_timestamp = data["income_verification_timestamp"]
        if "income_document_id" in data:
            state.income_document_id = data["income_document_id"]
        if "income_upload_attempted" in data:
            state.income_upload_attempted = data["income_upload_attempted"]
        if "income_retry_count" in data:
            state.income_retry_count = data["income_retry_count"]
        
        # Phase 7: Underwriting decision fields - CRITICAL: LLM cannot modify these
        # These fields represent the FINAL loan decision and must be deterministic
        if "loan_status" in data:
            state.loan_status = data["loan_status"]
        if "approval_reason" in data:
            state.approval_reason = data["approval_reason"]
        if "rejection_reason" in data:
            state.rejection_reason = data["rejection_reason"]
        if "underwriting_timestamp" in data:
            state.underwriting_timestamp = data["underwriting_timestamp"]
        if "underwriting_completed" in data:
            state.underwriting_completed = data["underwriting_completed"]
        if "calculated_emi" in data:
            state.calculated_emi = data["calculated_emi"]
        if "foir" in data:
            state.foir = data["foir"]
        if "existing_emi" in data:
            state.existing_emi = data["existing_emi"]
        if "sanction_reference" in data:
            state.sanction_reference = data["sanction_reference"]
    
    # =========================================================================
    # STATE PERSISTENCE
    # =========================================================================
    
    def _get_persistence_path(self, session_id: str) -> str:
        """Get the file path for a session's state."""
        # Sanitize session_id for filename
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        return os.path.join(self.persistence_dir, f"{safe_id}.json")
    
    def _persist_state(self, state: StageState):
        """
        Persist state to file.
        
        This ensures state survives:
        - Page reloads
        - Server restarts
        - Browser refreshes
        """
        path = self._get_persistence_path(state.session_id)
        try:
            with open(path, 'w') as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(f"State persisted: {path}")
        except Exception as e:
            logger.error(f"Failed to persist state: {e}")
    
    def _load_state(self, session_id: str) -> Optional[StageState]:
        """
        Load state from persistence file.
        
        Returns None if file doesn't exist or is invalid.
        """
        path = self._get_persistence_path(session_id)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return StageState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def reset_session(self, session_id: str):
        """
        Reset a session completely.
        
        This deletes all state and starts fresh.
        Use with caution - for testing/admin only.
        """
        # Remove from cache
        if session_id in self._sessions:
            del self._sessions[session_id]
        
        # Remove persistence file
        path = self._get_persistence_path(session_id)
        if os.path.exists(path):
            os.remove(path)
        
        logger.info(f"Session reset: {session_id}")


# ================================================================================
# SINGLETON INSTANCE
# ================================================================================
# Use a single controller instance across the application

_controller_instance: Optional[StageController] = None


def get_stage_controller() -> StageController:
    """
    Get the global StageController instance.
    
    This ensures all parts of the application use the same controller
    and share the same state.
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = StageController()
    return _controller_instance


# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

def get_current_stage(session_id: str) -> Stage:
    """Get current stage for a session."""
    return get_stage_controller().get_current_stage(session_id)


def request_transition(
    session_id: str, 
    event: StageEvent, 
    data: Optional[Dict[str, Any]] = None
) -> Tuple[bool, Stage, str]:
    """Request a stage transition."""
    return get_stage_controller().transition(session_id, event, data)


def update_session_data(session_id: str, data: Dict[str, Any]) -> StageState:
    """Update session data without changing stage."""
    return get_stage_controller().update_data(session_id, data)


def get_session_state(session_id: str) -> Optional[Dict[str, Any]]:
    """Get full session state as dictionary."""
    return get_stage_controller().get_session_state(session_id)


def reset_session(session_id: str):
    """Reset a session completely."""
    get_stage_controller().reset_session(session_id)


# ================================================================================
# STAGE INSTRUCTIONS FOR LLM
# ================================================================================
# These tell the LLM what to communicate at each stage.
# The LLM READS these instructions, it does NOT decide the flow.

STAGE_INSTRUCTIONS: Dict[Stage, str] = {
    Stage.GREETING: """
You are greeting a new visitor to Tata Capital.
- Welcome them warmly
- Introduce yourself as their loan assistant
- Ask how you can help them today
- Keep it brief (2-3 sentences)
""",

    Stage.NEEDS_DISCOVERY: """
You are understanding the customer's loan needs.
- Ask about the loan amount they need
- Ask about the purpose (optional)
- Be conversational and helpful
- Do NOT ask for personal details yet
""",

    Stage.BASIC_ELIGIBILITY: """
You are confirming basic eligibility.
- Acknowledge the loan amount requested
- Explain you'll need to verify their identity
- Keep it reassuring and professional
""",

    Stage.KYC_COLLECTION: """
You need to collect identity information.
- Ask for their FULL NAME
- Ask for their 10-DIGIT MOBILE NUMBER
- Explain this is for OTP verification
- Be clear about data security
""",

    Stage.OTP_VERIFICATION: """
You are verifying their mobile number via OTP.
- Confirm OTP has been sent
- Ask them to enter the 6-digit code
- Mention it's valid for 5 minutes
- Be helpful if they need it resent
""",

    Stage.KYC_VERIFICATION: """
You are confirming their identity verification.
- Confirm their identity is being verified
- Share that verification was successful (if it was)
- Be professional and reassuring
""",

    Stage.OFFER_DISCOVERY: """
You are checking pre-approved offers.
- Tell them you're checking offers
- Share any pre-approved limits found
- Explain the interest rate offered
- Be positive about the opportunity
""",

    Stage.INCOME_DOC_UPLOAD: """
You need income documents for final approval.
- Ask them to upload salary slip or income proof
- Mention acceptable documents
- Reassure about document security
- Guide them to use the upload button
""",

    Stage.UNDERWRITING: """
You are processing their application.
- Acknowledge documents received
- Tell them you're making the final decision
- Keep them informed of progress
""",

    Stage.SANCTION: """
The loan has been approved!
- Congratulate them enthusiastically
- Share the final loan details
- Mention sanction letter is available
- Thank them for choosing Tata Capital
""",

    Stage.REJECTION: """
The loan application was not approved.
- Be empathetic and professional
- Explain the reason clearly
- Suggest improvement steps
- Thank them for their interest
"""
}


def get_stage_instruction(stage: Stage) -> str:
    """Get the LLM instruction for a stage."""
    return STAGE_INSTRUCTIONS.get(stage, "Process this stage.")


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    # Test the stage machine
    print("\n" + "=" * 60)
    print("TESTING STRICT STAGE MACHINE")
    print("=" * 60)
    
    controller = StageController(persistence_dir="./test_stage_states")
    
    session_id = "test_session_001"
    
    # Reset for clean test
    controller.reset_session(session_id)
    
    # Get initial state
    state = controller.get_or_create_session(session_id)
    print(f"\nInitial stage: {state.current_stage.value}")
    
    # Test valid transitions
    print("\n--- Testing Valid Transitions ---")
    
    transitions = [
        (StageEvent.USER_GREETED, {"user_name": "Test User"}),
        (StageEvent.LOAN_AMOUNT_PROVIDED, {"loan_amount": 500000}),
        (StageEvent.ELIGIBILITY_CHECKED, {}),
        (StageEvent.KYC_INFO_PROVIDED, {"user_mobile": "9876543210"}),
        (StageEvent.OTP_VERIFIED, {"otp_verified": True}),
        (StageEvent.KYC_VERIFIED, {"kyc_verified": True}),
        (StageEvent.OFFERS_CHECKED, {"pre_approved_limit": 300000}),
        (StageEvent.DOCUMENTS_UPLOADED, {"documents_uploaded": ["salary_slip"]}),
        (StageEvent.UNDERWRITING_APPROVED, {"sanction_reference": "TATA/PL/2026/001"}),
    ]
    
    for event, data in transitions:
        success, new_stage, msg = controller.transition(session_id, event, data)
        print(f"\nEvent: {event.value}")
        print(f"Result: {'✅' if success else '❌'} {msg}")
        print(f"New Stage: {new_stage.value}")
    
    # Test invalid transition (should be blocked)
    print("\n--- Testing Invalid Transition (should be blocked) ---")
    success, stage, msg = controller.transition(session_id, StageEvent.LOAN_AMOUNT_PROVIDED)
    print(f"Event: LOAN_AMOUNT_PROVIDED on SANCTION stage")
    print(f"Result: {'✅ (unexpected!)' if success else '❌ BLOCKED (expected)'} {msg}")
    
    # Clean up test files
    controller.reset_session(session_id)
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)
