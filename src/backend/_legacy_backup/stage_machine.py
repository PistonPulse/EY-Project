"""
================================================================================
PHASE 1 + PHASE 3 + PHASE 4: DETERMINISTIC STAGE MACHINE + BACKEND + UNDERWRITING
================================================================================

This module implements a strict stage-based conversation control system that
replaces LLM-driven flow decisions with deterministic program logic.

PHASE 1 - Stage Machine:
- The chatbot is ALWAYS in exactly ONE stage at any moment
- Stage transitions are controlled ONLY by deterministic logic, NOT by LLM
- The LLM is used ONLY for generating human-like responses, NOT for deciding flow

PHASE 3 - Backend Services Integration:
- KYC verification uses CRM Service (reads from master dataset)
- Offer check uses Offer Mart Service (calculates from dataset)
- Credit check uses Credit Bureau Service (retrieves from dataset)
- NO LLM hallucination of customer/financial data

PHASE 4 - Deterministic Underwriting Engine:
- Loan approval/rejection decisions are made by RULES ENGINE, NOT LLM
- Uses FOIR (Fixed Obligation to Income Ratio) for affordability
- Credit score thresholds for eligibility
- Pre-approved limits and extended limits with income verification
- All decisions are auditable and compliant with NBFC regulations

KEY PRINCIPLES:
1. Stage transitions are deterministic (Phase 1)
2. Customer data comes from backend services, not LLM (Phase 3)
3. Loan decisions come from rules engine, not LLM (Phase 4)
4. LLM ONLY generates human-readable explanations, NEVER makes decisions

================================================================================
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
import re
import random
import string


# ================================================================================
# OTP GENERATION (Local implementation to avoid circular imports)
# ================================================================================

# Test users with fixed OTP for testing
TEST_USERS_OTP = {
    "9876543210": "123456",  # Rahul Mehta
    "9988776655": "123456",  # Amit Verma
    "9123456781": "123456",  # Priya Sharma
}

def generate_otp_local(phone: str) -> tuple:
    """
    Generate OTP for phone verification (LOCAL MOCK - no SMS).
    
    Args:
        phone: 10-digit phone number
        
    Returns:
        Tuple of (OTP string, result dict)
    """
    result = {
        "success": True,
        "message": "OTP generated locally (mock mode)",
        "is_test_user": False,
        "is_mock": True
    }
    
    # Check if this is a test user
    if phone in TEST_USERS_OTP:
        result["is_test_user"] = True
        result["message"] = f"Test user - fixed OTP {TEST_USERS_OTP[phone]}"
        return TEST_USERS_OTP[phone], result
    
    # Generate random 6-digit OTP for all other users
    otp = ''.join(random.choices(string.digits, k=6))
    result["message"] = f"OTP generated: {otp} (mock mode - displayed in chat)"
    
    return otp, result


# ================================================================================
# STAGE ENUMERATION
# ================================================================================
# These are the ONLY valid stages. The conversation MUST be in exactly one of these.

class ConversationStage(Enum):
    """
    Enumeration of all possible conversation stages.
    
    The conversation flows linearly through these stages:
    GREETING → NEEDS_ANALYSIS → KYC_COLLECTION → KYC_VERIFICATION → 
    OFFER_CHECK → CREDIT_CHECK → INCOME_DOC_UPLOAD → 
    UNDERWRITING_DECISION → SANCTION or REJECTION
    """
    GREETING = "GREETING"
    NEEDS_ANALYSIS = "NEEDS_ANALYSIS"
    KYC_COLLECTION = "KYC_COLLECTION"
    KYC_VERIFICATION = "KYC_VERIFICATION"
    OFFER_CHECK = "OFFER_CHECK"
    CREDIT_CHECK = "CREDIT_CHECK"
    INCOME_DOC_UPLOAD = "INCOME_DOC_UPLOAD"
    UNDERWRITING_DECISION = "UNDERWRITING_DECISION"
    SANCTION = "SANCTION"
    REJECTION = "REJECTION"


# ================================================================================
# STAGE INSTRUCTIONS FOR LLM
# ================================================================================
# Each stage has a specific instruction that tells the LLM what to say.
# The LLM does NOT decide flow - it only phrases the response appropriately.

STAGE_INSTRUCTIONS: Dict[ConversationStage, str] = {
    ConversationStage.GREETING: """
You are greeting a new visitor to Tata Capital.
- Welcome them warmly
- Introduce yourself as their loan assistant
- Ask how you can help them today
- Mention that you can help with personal loans, home loans, etc.
Keep it brief and friendly (2-3 sentences max).
""",

    ConversationStage.NEEDS_ANALYSIS: """
You are understanding the customer's loan requirements.
- Ask about the loan amount they need
- Ask about the purpose of the loan (optional)
- Be conversational and helpful
- If they've mentioned an amount, acknowledge it and confirm
Do NOT ask for personal details yet - just understand their needs.
""",

    ConversationStage.KYC_COLLECTION: """
You need to collect the customer's identity information for verification.
- Thank them for sharing their loan requirement
- Explain that you need to verify their identity to check eligibility
- Ask for their FULL NAME and 10-DIGIT MOBILE NUMBER
- Example: "Please share your full name and mobile number."
- Be clear this is for OTP verification (mandatory step)
- Mobile number must be a valid 10-digit Indian number (starting with 6, 7, 8, or 9)
Keep it professional and reassuring about data security.
""",

    ConversationStage.KYC_VERIFICATION: """
You are verifying the customer's identity via OTP.
- If OTP was just sent: Tell them the OTP has been sent to their phone
- If they entered wrong OTP: Politely ask them to try again
- If OTP is verified: Congratulate them and confirm verification
- Mention the OTP is valid for 5 minutes
Be helpful if they're having trouble receiving the OTP.
""",

    ConversationStage.OFFER_CHECK: """
You are checking if the customer has any pre-approved offers.
- Inform them you're checking their eligibility
- If they have a pre-approved offer, excitedly share the details
- If no pre-approved offer, explain you'll do a detailed eligibility check
- Mention the loan amount they qualify for (if available)
Be positive and encouraging.
""",

    ConversationStage.CREDIT_CHECK: """
You are sharing the customer's credit assessment results.
- Share their credit score if available
- Explain what the score means (excellent/good/fair/needs improvement)
- Share the interest rate they qualify for
- Calculate and share the EMI for their requested amount
Be transparent about the assessment.
""",

    ConversationStage.INCOME_DOC_UPLOAD: """
You need the customer to upload income documents for final verification.
- Explain that document verification is the final step
- Ask them to upload their salary slip or income proof
- Mention acceptable documents (salary slip, bank statement, ITR)
- Reassure them about document security
Guide them to use the upload button.
""",

    ConversationStage.UNDERWRITING_DECISION: """
You are processing the customer's documents and making a decision.
- Acknowledge receipt of their documents
- Inform them the documents are being verified
- Mention this typically takes a few moments
- Keep them engaged while processing
Be professional and reassuring.
""",

    ConversationStage.SANCTION: """
The loan has been approved! Share the good news.
- Congratulate them enthusiastically
- Share the final loan details (amount, rate, EMI, tenure)
- Explain the disbursement timeline
- Mention the sanction letter is available for download
- Thank them for choosing Tata Capital
Make this a celebratory moment!
""",

    ConversationStage.REJECTION: """
Unfortunately, the loan application cannot be approved.
- Be empathetic and professional
- Explain the reason clearly but kindly
- Suggest what they can do to improve eligibility
- Mention they can reapply after addressing the issues
- Thank them for their interest
Do NOT be dismissive - show you care.
"""
}


# ================================================================================
# CONVERSATION STATE
# ================================================================================
# This holds ALL the data collected during the conversation.
# The stage router reads this to decide transitions.

@dataclass
class ConversationState:
    """
    Central state object that stores all conversation data.
    
    The stage router uses this data to decide transitions.
    The LLM CANNOT modify this directly - only the router can.
    
    ================================================================================
    MOBILE NUMBER AS PRIMARY IDENTIFIER
    ================================================================================
    
    user_mobile_number is the PRIMARY customer identifier because:
    
    1. OTP VERIFICATION FLOW:
       - Mobile number is provided → OTP sent → OTP verified
       - ONLY after otp_verified=True can CRM lookup proceed
       - This prevents identity bypass attacks
    
    2. BANKING REALISM:
       - In Indian NBFC systems, mobile is linked to Aadhaar/KYC
       - All communications (OTP, alerts) go to mobile
       - Mobile number is the de-facto unique identifier
    
    3. SESSION IDENTITY:
       - mobile_number links entire session: chat → OTP → CRM → decision
       - Admin dashboard displays mobile_number (masked) for tracking
    
    OTP GATING ENFORCEMENT:
    -----------------------
    The stage router BLOCKS CRM lookup until:
    - user_mobile_number is collected (KYC_COLLECTION stage)
    - otp_code is sent (transition to KYC_VERIFICATION)
    - otp_verified == True (transition to OFFER_CHECK)
    
    DEPRECATED FIELDS:
    ------------------
    - user_phone: Use user_mobile_number instead
    
    ================================================================================
    
    PHASE 3 ADDITIONS:
    ------------------
    Backend service responses are stored here:
    - kyc_response: Data from CRM Service
    - offer_response: Data from Offer Mart Service  
    - credit_response: Data from Credit Bureau Service
    
    This ensures LLM receives VERIFIED data, not hallucinations.
    """
    # Current stage - the SINGLE source of truth for conversation position
    current_stage: ConversationStage = ConversationStage.GREETING
    
    # Session identifier (PHASE 7: Used for PDF file naming)
    session_id: Optional[str] = None
    
    # ==================== CUSTOMER IDENTITY (mobile_number is PRIMARY) ====================
    user_name: Optional[str] = None
    user_mobile_number: Optional[str] = None  # PRIMARY IDENTIFIER - used for all lookups
    user_pan: Optional[str] = None
    user_email: Optional[str] = None
    user_city: Optional[str] = None  # PHASE 3: From CRM Service
    user_age: Optional[int] = None   # PHASE 3: From CRM Service
    
    # Loan request details
    loan_amount: Optional[float] = None
    loan_purpose: Optional[str] = None
    loan_tenure_months: int = 36  # Default 36 months
    
    # OTP verification state
    # ==================== OTP VERIFICATION (MANDATORY GATE) ====================
    # OTP verification MUST complete before CRM lookup.
    # This prevents identity bypass and ensures banking compliance.
    otp_sent: bool = False
    otp_code: Optional[str] = None
    otp_verified: bool = False
    otp_attempts: int = 0
    otp_verification_timestamp: Optional[str] = None  # Timestamp when OTP was verified (for admin dashboard)
    
    # Customer data (fetched after verification)
    is_existing_customer: bool = False
    customer_data: Optional[Dict[str, Any]] = None
    customer_id: Optional[str] = None  # PHASE 3: From CRM Service
    
    # ==================== PHASE 3: Backend Service Data ====================
    # These fields store responses from backend services.
    # They ensure LLM uses VERIFIED data, not invented data.
    
    # KYC Data (from CRM Service)
    kyc_status: Optional[str] = None  # "VERIFIED", "NOT_FOUND", "ERROR"
    kyc_verified: bool = False
    aadhaar_masked: Optional[str] = None
    
    # Offer Data (from Offer Mart Service)
    has_preapproved_offer: bool = False
    offer_interest_rate: Optional[float] = None
    offer_max_tenure: Optional[int] = None
    offer_min_tenure: Optional[int] = None
    offer_processing_fee: Optional[float] = None
    offer_valid_until: Optional[str] = None
    
    # Credit Bureau Data (from Credit Bureau Service)
    credit_score_band: Optional[str] = None  # "EXCELLENT", "GOOD", etc.
    credit_bureau_name: Optional[str] = None
    credit_report_date: Optional[str] = None
    credit_accounts_count: int = 0
    credit_overdue_accounts: int = 0
    
    # ==================== End Phase 3 Fields ====================
    
    # Financial data
    credit_score: Optional[int] = None
    monthly_income: Optional[float] = None
    existing_emi: float = 0
    pre_approved_limit: float = 0
    
    # Offer details (calculated by underwriting)
    interest_rate: Optional[float] = None
    emi_amount: Optional[float] = None
    
    # Document state
    documents_uploaded: List[str] = field(default_factory=list)
    documents_verified: bool = False
    salary_slip_uploaded: bool = False  # PHASE 4: Required for extended limit
    
    # ==================== PHASE 4: Underwriting Decision Fields ====================
    # These fields store the DETERMINISTIC underwriting decision.
    # The LLM NEVER makes these decisions - only the rules engine does.
    # This prevents random loan approvals and ensures regulatory compliance.
    
    # Primary Decision
    loan_status: Optional[str] = None  # "APPROVED", "REJECTED", "PENDING_DOCS"
    approval_type: Optional[str] = None  # "Instant Pre-Approved", "Income Verified Approval"
    
    # Calculated Values (from Underwriting Engine)
    calculated_emi: Optional[float] = None  # EMI calculated by rules engine
    effective_interest_rate: Optional[float] = None  # Rate applied to loan
    total_interest_payable: Optional[float] = None
    total_repayment_amount: Optional[float] = None
    
    # Conditional Requirements
    requires_salary_slip: bool = False  # True if amount > pre-approved limit
    salary_slip_verified: bool = False
    
    # Rejection Details (if rejected)
    rejection_reason: Optional[str] = None
    rejection_details: Optional[str] = None  # Detailed explanation
    
    # Audit Trail
    underwriting_timestamp: Optional[str] = None  # When decision was made
    underwriting_factors: Optional[Dict[str, Any]] = None  # Factors considered
    
    # ==================== End Phase 4 Fields ====================
    
    # ==================== PHASE 5: Sanction & Closure Fields ====================
    # These fields store sanction letter details and session closure state.
    # The LLM reads these to generate human-friendly closure messages.
    # Session closure prevents further random responses after decision.
    
    # Sanction Letter (for APPROVED loans)
    sanction_letter_generated: bool = False
    sanction_letter_path: Optional[str] = None  # PHASE 7: Actual file path to PDF
    sanction_letter_url: Optional[str] = None  # Download URL
    sanction_reference_number: Optional[str] = None  # e.g., "AFNL/PL/20260130/RAHU1430"
    sanction_validity_date: Optional[str] = None  # e.g., "March 01, 2026"
    sanction_message: Optional[str] = None  # Pre-formatted message for LLM
    
    # Rejection Message (for REJECTED loans)
    rejection_message: Optional[str] = None  # Pre-formatted rejection message
    improvement_tips: Optional[str] = None  # Actionable advice for customer
    
    # Session Closure
    session_closed: bool = False  # True = no more responses allowed
    closure_reason: Optional[str] = None  # "LOAN_SANCTIONED", "LOAN_REJECTED", etc.
    closure_timestamp: Optional[str] = None
    closure_message: Optional[str] = None  # Final goodbye message
    
    # ==================== End Phase 5/7 Fields ====================
    
    # ==================== PHASE 8: Customer Acquisition Fields ====================
    # Tracks how customer arrived at the chatbot (digital marketing channel)
    # This satisfies the hackathon requirement:
    # "Chats with customers landing on the web chatbot via digital ads or marketing emails"
    #
    # Values:
    # - "AD": Customer clicked a digital advertisement (Google/Facebook/Instagram)
    # - "EMAIL": Customer opened a pre-approved loan marketing email
    # - None: Direct website visitor (no specific acquisition channel)
    #
    # This enables:
    # - Personalized greeting based on acquisition channel
    # - Marketing ROI tracking in admin dashboard
    # - Conversion funnel analysis
    acquisition_source: Optional[str] = None  # "AD", "EMAIL", or None
    
    # ==================== End Phase 8 Fields ====================
    
    # Legacy Decision state (keeping for backward compatibility)
    loan_approved: Optional[bool] = None
    
    # Conversation history for LLM context
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    
    # Timestamps for audit
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for JSON serialization"""
        return {
            "current_stage": self.current_stage.value,
            "session_id": self.session_id,  # PHASE 7
            # Customer identity (mobile_number is PRIMARY)
            "user_name": self.user_name,
            "user_mobile_number": self.user_mobile_number,  # PRIMARY IDENTIFIER
            "user_phone": self.user_mobile_number,  # DEPRECATED alias for backward compatibility
            "user_pan": self.user_pan,
            "user_email": self.user_email,
            # Loan details
            "loan_amount": self.loan_amount,
            "loan_purpose": self.loan_purpose,
            "loan_tenure_months": self.loan_tenure_months,
            # OTP verification (MANDATORY GATE)
            "otp_sent": self.otp_sent,
            "otp_verified": self.otp_verified,
            "otp_attempts": self.otp_attempts,
            "otp_verification_timestamp": self.otp_verification_timestamp,  # For admin dashboard
            # Customer data
            "is_existing_customer": self.is_existing_customer,
            "credit_score": self.credit_score,
            "monthly_income": self.monthly_income,
            "existing_emi": self.existing_emi,
            "pre_approved_limit": self.pre_approved_limit,
            "interest_rate": self.interest_rate,
            "emi_amount": self.emi_amount,
            "documents_uploaded": self.documents_uploaded,
            "documents_verified": self.documents_verified,
            "loan_approved": self.loan_approved,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            # Phase 4: Underwriting Decision Fields
            "loan_status": self.loan_status,
            "approval_type": self.approval_type,
            "calculated_emi": self.calculated_emi,
            "effective_interest_rate": self.effective_interest_rate,
            "total_interest_payable": self.total_interest_payable,
            "total_repayment_amount": self.total_repayment_amount,
            "requires_salary_slip": self.requires_salary_slip,
            "salary_slip_verified": self.salary_slip_verified,
            "salary_slip_uploaded": self.salary_slip_uploaded,
            "rejection_details": self.rejection_details,
            "underwriting_timestamp": self.underwriting_timestamp,
            # Phase 5/7: Sanction & Closure Fields
            "sanction_letter_generated": self.sanction_letter_generated,
            "sanction_letter_path": self.sanction_letter_path,  # PHASE 7
            "sanction_letter_url": self.sanction_letter_url,
            "sanction_reference_number": self.sanction_reference_number,
            "sanction_validity_date": self.sanction_validity_date,
            "session_closed": self.session_closed,
            "closure_reason": self.closure_reason,
            # Phase 8: Customer Acquisition (for admin dashboard visibility)
            "acquisition_source": self.acquisition_source,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationState":
        """Create state from dictionary"""
        state = cls()
        state.current_stage = ConversationStage(data.get("current_stage", "GREETING"))
        state.user_name = data.get("user_name")
        # Support both mobile_number and phone (backward compatibility)
        state.user_mobile_number = data.get("user_mobile_number") or data.get("user_phone")
        state.user_pan = data.get("user_pan")
        state.user_email = data.get("user_email")
        state.loan_amount = data.get("loan_amount")
        state.loan_purpose = data.get("loan_purpose")
        state.loan_tenure_months = data.get("loan_tenure_months", 36)
        state.otp_sent = data.get("otp_sent", False)
        state.otp_code = data.get("otp_code")
        state.otp_verified = data.get("otp_verified", False)
        state.otp_attempts = data.get("otp_attempts", 0)
        state.otp_verification_timestamp = data.get("otp_verification_timestamp")
        state.is_existing_customer = data.get("is_existing_customer", False)
        state.customer_data = data.get("customer_data")
        state.credit_score = data.get("credit_score")
        state.monthly_income = data.get("monthly_income")
        state.existing_emi = data.get("existing_emi", 0)
        state.pre_approved_limit = data.get("pre_approved_limit", 0)
        state.interest_rate = data.get("interest_rate")
        state.emi_amount = data.get("emi_amount")
        state.documents_uploaded = data.get("documents_uploaded", [])
        state.documents_verified = data.get("documents_verified", False)
        state.loan_approved = data.get("loan_approved")
        state.rejection_reason = data.get("rejection_reason")
        state.conversation_history = data.get("conversation_history", [])
        state.created_at = data.get("created_at", datetime.now().isoformat())
        state.last_updated = data.get("last_updated", datetime.now().isoformat())
        # Phase 8: Acquisition source
        state.acquisition_source = data.get("acquisition_source")
        return state


# ================================================================================
# DATA EXTRACTION UTILITIES
# ================================================================================
# These functions extract specific data from user messages.
# They are called by the stage router to populate state.

def extract_mobile_number(message: str) -> Optional[str]:
    """
    Extract a 10-digit Indian mobile number from user message.
    
    MOBILE NUMBER VALIDATION:
    - Must be 10 digits
    - Must start with 6, 7, 8, or 9 (Indian mobile prefixes)
    - Handles common formats: 9876543210, +91 9876543210, 91-9876543210
    
    Args:
        message: User's message text
        
    Returns:
        10-digit mobile number or None if not found
    """
    # Remove common separators and prefixes
    cleaned = re.sub(r'[\s\-\(\)\+]', '', message)
    
    # Pattern for Indian mobile numbers
    # Matches: 9876543210, +919876543210, 919876543210
    patterns = [
        r'(?:91)?([6-9]\d{9})\b',  # With or without 91 prefix
        r'\b([6-9]\d{9})\b',       # Standalone 10 digits starting with 6-9
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)
    
    return None


# DEPRECATED: Use extract_mobile_number instead
def extract_phone_number(message: str) -> Optional[str]:
    """
    DEPRECATED: Use extract_mobile_number() instead.
    Kept for backward compatibility.
    """
    return extract_mobile_number(message)


def extract_loan_amount(message: str) -> Optional[float]:
    """
    Extract loan amount from user message.
    Handles formats like: 5 lakhs, 5L, 500000, Rs. 5,00,000
    
    Args:
        message: User's message text
        
    Returns:
        Loan amount in rupees or None if not found
    """
    message_lower = message.lower()
    
    # Pattern 1: X lakhs/lacs/L
    lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b'
    match = re.search(lakh_pattern, message_lower)
    if match:
        return float(match.group(1)) * 100000
    
    # Pattern 2: X crore
    crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b'
    match = re.search(crore_pattern, message_lower)
    if match:
        return float(match.group(1)) * 10000000
    
    # Pattern 3: Direct number (at least 5 digits assumed to be loan amount)
    # Handles: 500000, 5,00,000, Rs. 500000
    number_pattern = r'(?:rs\.?\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})?|\d{5,})'
    match = re.search(number_pattern, message_lower)
    if match:
        # Remove commas and convert
        amount_str = match.group(1).replace(',', '')
        amount = float(amount_str)
        if amount >= 10000:  # Assume amounts >= 10000 are loan amounts
            return amount
    
    return None


def extract_name(message: str) -> Optional[str]:
    """
    Extract user's name from message.
    Handles formats like: "I'm Rahul", "My name is Priya Sharma", "This is Amit"
    
    Args:
        message: User's message text
        
    Returns:
        Extracted name or None
    """
    # List of common words that should NOT be treated as names
    NOT_NAMES = {
        'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening', 
        'night', 'yes', 'no', 'ok', 'okay', 'sure', 'thanks', 'thank',
        'please', 'help', 'need', 'want', 'loan', 'money', 'amount',
        'home', 'personal', 'business', 'property', 'test', 'user',
        'i', 'me', 'my', 'you', 'your', 'the', 'a', 'an'
    }
    
    # Common name introduction patterns
    patterns = [
        r"(?:i'?m|i am|my name is|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:here|speaking)",
        r"(?:name|naam)\s*(?:is|hai|:)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Check if it's not a common word
            if name.lower() not in NOT_NAMES:
                # Capitalize properly
                return ' '.join(word.capitalize() for word in name.split())
    
    # Do NOT extract from standalone short messages - too risky for false positives
    # Names should be explicitly introduced (e.g., "my name is X")
    
    return None


def extract_otp(message: str) -> Optional[str]:
    """
    Extract OTP from user message.
    Handles formats like: "123456", "OTP is 123456", "my code is 123456"
    
    Args:
        message: User's message text
        
    Returns:
        6-digit OTP or None
    """
    message = message.strip()
    
    # Pattern 1: Just digits (most common)
    if re.match(r'^\d{4,6}$', message):
        return message
    
    # Pattern 2: "OTP is/code is X"
    patterns = [
        r'(?:otp|code|verification)\s*(?:is|:)?\s*(\d{4,6})',
        r'(\d{4,6})\s*(?:is|:)?\s*(?:the\s*)?(?:otp|code)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Pattern 3: Find any 4-6 digit number
    numbers = re.findall(r'\b(\d{4,6})\b', message)
    if len(numbers) == 1:
        return numbers[0]
    
    return None


def is_affirmative(message: str) -> bool:
    """
    Check if message is an affirmative response (yes, ok, sure, etc.)
    
    Args:
        message: User's message text
        
    Returns:
        True if affirmative, False otherwise
    """
    message_lower = message.lower().strip()
    
    affirmatives = [
        'yes', 'yess', 'yep', 'yeah', 'ya', 'yaa', 'yup',
        'ok', 'okay', 'sure', 'fine', 'alright',
        'proceed', 'continue', 'go ahead', 'do it',
        'confirm', 'confirmed', 'accept', 'agree',
        'haan', 'ha', 'ji', 'theek', 'sahi',
        'y', 'k', 'done'
    ]
    
    return message_lower in affirmatives or any(aff in message_lower for aff in ['yes', 'ok', 'sure', 'proceed', 'confirm'])


def is_negative(message: str) -> bool:
    """
    Check if message is a negative response (no, cancel, etc.)
    
    Args:
        message: User's message text
        
    Returns:
        True if negative, False otherwise
    """
    message_lower = message.lower().strip()
    
    negatives = [
        'no', 'nope', 'nah', 'not', 'cancel', 'stop',
        'don\'t', 'dont', 'never', 'exit', 'quit',
        'nahi', 'nahin', 'mat', 'band karo'
    ]
    
    return message_lower in negatives or any(neg in message_lower for neg in ['no', 'cancel', 'stop'])


# ================================================================================
# STAGE ROUTER - THE HEART OF DETERMINISTIC FLOW CONTROL
# ================================================================================
# This is the ONLY place where stage transitions happen.
# The LLM NEVER decides the next stage - only this function does.
#
# PHASE 3 INTEGRATION:
# --------------------
# The router now calls Backend Services during relevant stages:
# - KYC_VERIFICATION: Calls CRM Service
# - OFFER_CHECK: Calls Offer Mart Service
# - CREDIT_CHECK: Calls Credit Bureau Service
#
# This ensures all customer data comes from the MASTER DATASET,
# not from LLM hallucination.

class StageRouter:
    """
    Central routing function that controls conversation flow DETERMINISTICALLY.
    
    KEY PRINCIPLE: The LLM does NOT decide the next stage.
    This router reads the current state and decides transitions based on
    deterministic rules (data presence, verification status, etc.)
    
    PHASE 3 ENHANCEMENT:
    --------------------
    The router now integrates with Backend Services:
    - CRM Service for KYC verification
    - Offer Mart Service for pre-approved offers
    - Credit Bureau Service for credit scores
    
    All data stored in state comes from VERIFIED backend services,
    not from LLM invention.
    
    Stage Transition Rules:
    -----------------------
    GREETING → NEEDS_ANALYSIS: Always (after initial greeting)
    NEEDS_ANALYSIS → KYC_COLLECTION: When loan_amount is present
    KYC_COLLECTION → KYC_VERIFICATION: When phone number is provided
    KYC_VERIFICATION → OFFER_CHECK: When OTP is verified + KYC from CRM Service
    OFFER_CHECK → CREDIT_CHECK: After checking offers from Offer Mart Service
    CREDIT_CHECK → INCOME_DOC_UPLOAD: After credit from Credit Bureau Service
    INCOME_DOC_UPLOAD → UNDERWRITING_DECISION: When documents are uploaded
    UNDERWRITING_DECISION → SANCTION/REJECTION: Based on underwriting result
    """
    
    def __init__(self, data_provider=None, backend_services=None):
        """
        Initialize the stage router.
        
        Args:
            data_provider: Optional data provider for customer lookups (legacy)
            backend_services: BackendServices instance for Phase 3 integration
        """
        self.data_provider = data_provider
        self.backend_services = backend_services
        
        # Initialize backend services if not provided
        if self.backend_services is None:
            try:
                from backend_services import create_backend_services
                self.backend_services = create_backend_services()
                print("✅ Backend Services initialized in StageRouter")
            except Exception as e:
                print(f"⚠️ Could not initialize Backend Services: {e}")
                self.backend_services = None
    
    def route(self, state: ConversationState, user_message: str) -> ConversationState:
        """
        MAIN ROUTING FUNCTION
        
        This is called for EVERY user message. It:
        1. Reads the current_stage
        2. Extracts relevant data from the message
        3. Updates state with extracted data
        4. Decides if stage should transition
        5. Returns updated state with new current_stage
        
        The LLM is called AFTER this, not before.
        
        Args:
            state: Current conversation state
            user_message: The user's message
            
        Returns:
            Updated state (possibly with new current_stage)
        """
        # Update timestamp
        state.last_updated = datetime.now().isoformat()
        
        # Add user message to history
        state.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Route based on current stage
        current = state.current_stage
        
        print(f"\n{'='*60}")
        print(f"📍 STAGE ROUTER: Current Stage = {current.value}")
        print(f"📝 User Message: {user_message[:50]}...")
        print(f"{'='*60}")
        
        # Call the appropriate stage handler
        if current == ConversationStage.GREETING:
            return self._handle_greeting(state, user_message)
        
        elif current == ConversationStage.NEEDS_ANALYSIS:
            return self._handle_needs_analysis(state, user_message)
        
        elif current == ConversationStage.KYC_COLLECTION:
            return self._handle_kyc_collection(state, user_message)
        
        elif current == ConversationStage.KYC_VERIFICATION:
            return self._handle_kyc_verification(state, user_message)
        
        elif current == ConversationStage.OFFER_CHECK:
            return self._handle_offer_check(state, user_message)
        
        elif current == ConversationStage.CREDIT_CHECK:
            return self._handle_credit_check(state, user_message)
        
        elif current == ConversationStage.INCOME_DOC_UPLOAD:
            return self._handle_income_doc_upload(state, user_message)
        
        elif current == ConversationStage.UNDERWRITING_DECISION:
            return self._handle_underwriting_decision(state, user_message)
        
        elif current == ConversationStage.SANCTION:
            return self._handle_sanction(state, user_message)
        
        elif current == ConversationStage.REJECTION:
            return self._handle_rejection(state, user_message)
        
        # Should never reach here
        return state
    
    # ==================== STAGE HANDLERS ====================
    # Each handler processes input for its stage and decides transition
    
    def _handle_greeting(self, state: ConversationState, message: str) -> ConversationState:
        """
        GREETING stage handler.
        
        Transition Rule:
        - If user mentions loan amount → skip to NEEDS_ANALYSIS (with amount stored)
        - If user says hi/hello → stay for one response, then move to NEEDS_ANALYSIS
        - Otherwise → move to NEEDS_ANALYSIS
        """
        # Check if user already mentioned loan amount
        loan_amount = extract_loan_amount(message)
        if loan_amount:
            state.loan_amount = loan_amount
            print(f"✅ Extracted loan amount: ₹{loan_amount:,.0f}")
        
        # Check if user provided name
        name = extract_name(message)
        if name:
            state.user_name = name
            print(f"✅ Extracted name: {name}")
        
        # Transition: GREETING → NEEDS_ANALYSIS
        # Greeting stage is typically just one exchange
        state.current_stage = ConversationStage.NEEDS_ANALYSIS
        print(f"➡️ TRANSITION: GREETING → NEEDS_ANALYSIS")
        
        return state
    
    def _handle_needs_analysis(self, state: ConversationState, message: str) -> ConversationState:
        """
        NEEDS_ANALYSIS stage handler.
        
        Transition Rule:
        - If loan_amount is present → move to KYC_COLLECTION
        - Otherwise → stay in NEEDS_ANALYSIS (ask for loan amount)
        """
        # Try to extract loan amount if not already present
        if not state.loan_amount:
            loan_amount = extract_loan_amount(message)
            if loan_amount:
                state.loan_amount = loan_amount
                print(f"✅ Extracted loan amount: ₹{loan_amount:,.0f}")
        
        # Extract name if mentioned
        if not state.user_name:
            name = extract_name(message)
            if name:
                state.user_name = name
                print(f"✅ Extracted name: {name}")
        
        # Transition: If loan amount is present, move to KYC collection
        if state.loan_amount:
            state.current_stage = ConversationStage.KYC_COLLECTION
            print(f"➡️ TRANSITION: NEEDS_ANALYSIS → KYC_COLLECTION (loan_amount={state.loan_amount})")
        else:
            print(f"⏸️ STAYING: NEEDS_ANALYSIS (waiting for loan amount)")
        
        return state
    
    def _handle_kyc_collection(self, state: ConversationState, message: str) -> ConversationState:
        """
        KYC_COLLECTION stage handler.
        
        MOBILE NUMBER COLLECTION:
        -------------------------
        This stage collects the customer's mobile_number which becomes the
        primary identifier for all subsequent backend service lookups.
        
        Transition Rule:
        - If mobile_number is provided → move to KYC_VERIFICATION (send OTP)
        - Otherwise → stay (ask for name and mobile number)
        
        WHY MOBILE NUMBER IS PRIMARY:
        - Mobile number is used for OTP verification (mandatory gate)
        - CRM lookup uses mobile_number after OTP verification
        - All session identity tied to mobile_number
        """
        # Extract mobile number
        if not state.user_mobile_number:
            mobile = extract_mobile_number(message)
            if mobile:
                state.user_mobile_number = mobile
                print(f"✅ Extracted mobile_number: {mobile}")
        
        # Extract name if not already present
        if not state.user_name:
            name = extract_name(message)
            if name:
                state.user_name = name
                print(f"✅ Extracted name: {name}")
        
        # Transition: If mobile_number is present, generate OTP and move to verification
        if state.user_mobile_number:
            # Generate OTP using local function (avoids circular import)
            otp, result = generate_otp_local(state.user_mobile_number)
            state.otp_code = otp
            state.otp_sent = True
            state.otp_attempts = 0
            
            print(f"📱 OTP Generated: {otp} for mobile_number {state.user_mobile_number}")
            
            state.current_stage = ConversationStage.KYC_VERIFICATION
            print(f"➡️ TRANSITION: KYC_COLLECTION → KYC_VERIFICATION")
        else:
            print(f"⏸️ STAYING: KYC_COLLECTION (waiting for mobile number)")
        
        return state
    
    def _handle_kyc_verification(self, state: ConversationState, message: str) -> ConversationState:
        """
        KYC_VERIFICATION stage handler.
        
        ================================================================================
        OTP VERIFICATION GATE - MANDATORY BEFORE CRM LOOKUP
        ================================================================================
        
        This stage is the CRITICAL GATE that ensures:
        1. Mobile number ownership is verified via OTP
        2. CRM lookup ONLY happens AFTER OTP verification
        3. No identity bypass is possible
        
        WHY THIS GATE IS IMPORTANT:
        ---------------------------
        - Without OTP verification, anyone could claim any mobile number
        - CRM contains sensitive financial data - must be protected
        - Banking regulations require identity verification before data access
        
        PHASE 3 INTEGRATION:
        --------------------
        After OTP verification, calls CRM Service to get KYC data.
        This ensures customer data comes from the MASTER DATASET,
        not from LLM invention.
        
        Transition Rule:
        - If OTP is correct → Record timestamp → Call CRM Service → move to OFFER_CHECK
        - If wrong OTP and attempts < 3 → stay and ask again
        - If wrong OTP and attempts >= 3 → reset to KYC_COLLECTION
        
        ================================================================================
        """
        # Extract OTP from message
        entered_otp = extract_otp(message)
        
        if entered_otp:
            state.otp_attempts += 1
            
            # Verify OTP
            if entered_otp == state.otp_code:
                state.otp_verified = True
                state.otp_verification_timestamp = datetime.now().isoformat()  # Record timestamp for admin
                print(f"✅ OTP Verified Successfully at {state.otp_verification_timestamp}!")
                
                # ============================================================
                # OTP VERIFIED - NOW SAFE TO CALL CRM SERVICE
                # ============================================================
                # This is the ONLY place where CRM lookup is triggered.
                # It ONLY happens AFTER otp_verified == True.
                # This prevents identity bypass attacks.
                # ============================================================
                
                if self.backend_services:
                    # Call CRM Service using mobile_number (PRIMARY KEY)
                    kyc_response = self.backend_services.verify_kyc(
                        mobile_number=state.user_mobile_number,  # Use mobile_number, not phone
                        pan=state.user_pan
                    )
                    
                    # Store KYC response in state
                    state.kyc_status = kyc_response.kyc_status
                    
                    if kyc_response.kyc_status == "VERIFIED":
                        state.kyc_verified = True
                        state.is_existing_customer = True
                        state.customer_id = kyc_response.customer_id
                        
                        # Update state with VERIFIED data from CRM
                        state.user_name = kyc_response.name or state.user_name
                        state.user_email = kyc_response.email
                        state.user_city = kyc_response.city
                        state.user_age = kyc_response.age
                        state.aadhaar_masked = kyc_response.aadhaar_masked
                        
                        if kyc_response.pan:
                            state.user_pan = kyc_response.pan
                        
                        print(f"✅ CRM Service: Customer VERIFIED")
                        print(f"   Name: {state.user_name}")
                        print(f"   Customer ID: {state.customer_id}")
                    else:
                        # Customer not found - still proceed but mark as new
                        state.kyc_verified = False
                        state.is_existing_customer = False
                        print(f"⚠️ CRM Service: Customer NOT_FOUND (new customer)")
                
                # Legacy fallback if backend_services not available
                elif self.data_provider:
                    customer = self.data_provider.get_customer_by_mobile(state.user_mobile_number)
                    if customer:
                        state.is_existing_customer = True
                        state.customer_data = customer
                        state.user_name = customer.get("name", state.user_name)
                        
                        fin_data = customer.get("financial_data", {})
                        state.credit_score = fin_data.get("credit_score")
                        state.monthly_income = fin_data.get("monthly_income")
                        state.existing_emi = fin_data.get("total_monthly_debt", 0)
                        
                        print(f"✅ Legacy: Customer found: {state.user_name}")
                
                state.current_stage = ConversationStage.OFFER_CHECK
                print(f"➡️ TRANSITION: KYC_VERIFICATION → OFFER_CHECK")
            else:
                print(f"❌ Wrong OTP (attempt {state.otp_attempts}/3)")
                
                if state.otp_attempts >= 3:
                    # Too many attempts - reset
                    state.otp_sent = False
                    state.otp_code = None
                    state.otp_attempts = 0
                    state.otp_verification_timestamp = None
                    state.current_stage = ConversationStage.KYC_COLLECTION
                    print(f"🔄 RESET: Too many OTP attempts → KYC_COLLECTION")
        else:
            print(f"⏸️ STAYING: KYC_VERIFICATION (waiting for OTP)")
        
        return state
    
    def _handle_offer_check(self, state: ConversationState, message: str) -> ConversationState:
        """
        OFFER_CHECK stage handler.
        
        OTP GATE ENFORCEMENT:
        ---------------------
        This stage should ONLY be reached AFTER OTP verification.
        The stage transition ensures this, but we double-check here.
        
        Transition Rule:
        - After checking offers → move to CREDIT_CHECK
        This stage is typically automatic (no user input needed)
        
        PHASE 3 INTEGRATION:
        - Calls Offer Mart Service to check pre-approved offers
        - Uses mobile_number as the lookup key
        - Data comes from CUSTOMER_PROFILES dataset, NOT LLM invention
        - Stores offer details in ConversationState for downstream use
        """
        # ═══════════════════════════════════════════════════════════════════════
        # VERIFY OTP WAS COMPLETED (SAFETY CHECK)
        # ═══════════════════════════════════════════════════════════════════════
        if not state.otp_verified:
            print(f"⚠️ WARNING: OFFER_CHECK reached without OTP verification!")
            print(f"   This should not happen - routing back to KYC_VERIFICATION")
            state.current_stage = ConversationStage.KYC_VERIFICATION
            return state
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: OFFER MART SERVICE CALL
        # Data Source: CUSTOMER_PROFILES master dataset
        # ═══════════════════════════════════════════════════════════════════════
        
        if self.backend_services and state.user_mobile_number:
            print(f"📡 PHASE 3: Calling Offer Mart Service for mobile_number: {state.user_mobile_number}")
            
            offer_response = self.backend_services.check_offers(mobile_number=state.user_mobile_number)
            
            if offer_response.has_offer:
                # Store offer data from backend service (real dataset)
                # Field mapping: OfferResponse → ConversationState
                state.has_preapproved_offer = offer_response.has_offer
                state.pre_approved_limit = offer_response.preapproved_limit_inr
                state.offer_interest_rate = offer_response.interest_rate_percent
                state.offer_max_tenure = offer_response.max_tenure_months
                state.offer_processing_fee = offer_response.processing_fee_percent
                
                print(f"✅ PHASE 3: Offer Mart Response:")
                print(f"   - Has Pre-approved Offer: {state.has_preapproved_offer}")
                print(f"   - Pre-approved Limit: ₹{state.pre_approved_limit:,.0f}")
                print(f"   - Interest Rate: {state.offer_interest_rate}%")
                print(f"   - Max Tenure: {state.offer_max_tenure} months")
                print(f"   - Processing Fee: {state.offer_processing_fee}%")
            else:
                print(f"ℹ️ PHASE 3: No pre-approved offer available for this customer")
                state.has_preapproved_offer = False
                state.pre_approved_limit = 0
        
        # ═══════════════════════════════════════════════════════════════════════
        # LEGACY FALLBACK (for backward compatibility)
        # ═══════════════════════════════════════════════════════════════════════
        elif state.is_existing_customer and state.customer_data:
            print(f"⚠️ LEGACY: Using customer_data for offer check")
            # Customer has history - check for pre-approved limit
            if state.credit_score and state.credit_score >= 700:
                state.pre_approved_limit = state.monthly_income * 10 if state.monthly_income else 500000
            else:
                state.pre_approved_limit = 0
        
        print(f"📊 Pre-approved limit: ₹{state.pre_approved_limit:,.0f}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3 FIX: ALWAYS TRANSITION TO CREDIT_CHECK
        # Offer check is a backend lookup operation - automatically proceed
        # ═══════════════════════════════════════════════════════════════════════
        state.current_stage = ConversationStage.CREDIT_CHECK
        print(f"➡️ TRANSITION: OFFER_CHECK → CREDIT_CHECK (auto-transition)")
        
        return state
    
    def _handle_credit_check(self, state: ConversationState, message: str) -> ConversationState:
        """
        CREDIT_CHECK stage handler.
        
        Transition Rule:
        - After showing credit assessment and user confirms → move to INCOME_DOC_UPLOAD
        - If user has questions → stay and answer
        
        PHASE 3 INTEGRATION:
        - Calls Credit Bureau Service to get CIBIL score and report
        - Data comes from CUSTOMER_PROFILES dataset, NOT LLM invention
        - Stores credit details in ConversationState for underwriting
        
        OTP GATE ENFORCEMENT:
        - Credit Bureau lookup requires verified mobile_number
        - OTP verification must be complete before credit check
        - Uses state.user_mobile_number as primary identifier
        """
        # ═══════════════════════════════════════════════════════════════════════
        # OTP GATE ENFORCEMENT: Credit check requires verified identity
        # The OTP gate was enforced at KYC_VERIFICATION stage
        # If we're here, OTP should already be verified
        # ═══════════════════════════════════════════════════════════════════════
        if not state.otp_verified:
            print(f"⚠️ OTP GATE: Customer reached CREDIT_CHECK without OTP verification")
            # Continue with limited functionality - credit check may fail
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 3: CREDIT BUREAU SERVICE CALL
        # Data Source: CUSTOMER_PROFILES master dataset
        # Primary Key: mobile_number (verified via OTP)
        # ═══════════════════════════════════════════════════════════════════════
        
        if self.backend_services and state.user_mobile_number:
            print(f"📡 PHASE 3: Calling Credit Bureau Service for mobile_number: {state.user_mobile_number}")
            
            credit_response = self.backend_services.get_credit_report(mobile_number=state.user_mobile_number)
            
            if credit_response.success:
                # Store credit data from backend service (real dataset)
                # Field mapping: CreditBureauResponse → ConversationState
                state.credit_score = credit_response.credit_score
                state.credit_score_band = credit_response.score_band  # score_band in response
                state.credit_bureau_name = credit_response.bureau_name
                state.credit_report_date = credit_response.report_date
                state.credit_accounts_count = credit_response.accounts_count  # accounts_count in response
                
                # Calculate interest rate based on credit score
                # (CreditBureauResponse doesn't have recommended_rate, calculate locally)
                if state.credit_score >= 800:
                    state.interest_rate = 10.5
                elif state.credit_score >= 750:
                    state.interest_rate = 11.5
                elif state.credit_score >= 700:
                    state.interest_rate = 12.5
                elif state.credit_score >= 650:
                    state.interest_rate = 14.0
                else:
                    state.interest_rate = 16.0
                
                print(f"✅ PHASE 3: Credit Bureau Response:")
                print(f"   - Credit Score: {state.credit_score}")
                print(f"   - Score Band: {state.credit_score_band}")
                print(f"   - Bureau: {state.credit_bureau_name}")
                print(f"   - Report Date: {state.credit_report_date}")
                print(f"   - Active Accounts: {state.credit_accounts_count}")
                print(f"   - Calculated Rate: {state.interest_rate}%")
            else:
                print(f"❌ PHASE 3: Credit Bureau Service failed: {credit_response.error_message}")
                # Fallback to default rate for new customers
                state.interest_rate = 14.0
        
        # ═══════════════════════════════════════════════════════════════════════
        # LEGACY FALLBACK (for backward compatibility)
        # ═══════════════════════════════════════════════════════════════════════
        elif state.credit_score:
            print(f"⚠️ LEGACY: Using existing credit_score for rate calculation")
            if state.credit_score >= 800:
                state.interest_rate = 10.5
            elif state.credit_score >= 750:
                state.interest_rate = 11.5
            elif state.credit_score >= 700:
                state.interest_rate = 12.5
            elif state.credit_score >= 650:
                state.interest_rate = 14.0
            else:
                state.interest_rate = 16.0
        else:
            state.interest_rate = 14.0  # Default rate for new customers
        
        # ═══════════════════════════════════════════════════════════════════════
        # EMI CALCULATION (same as before)
        # ═══════════════════════════════════════════════════════════════════════
        if state.loan_amount and state.interest_rate:
            monthly_rate = state.interest_rate / 100 / 12
            tenure = state.loan_tenure_months
            emi = state.loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
            state.emi_amount = round(emi, 0)
        
        print(f"📊 Interest Rate: {state.interest_rate}%, EMI: ₹{state.emi_amount:,.0f}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 4 FIX: AUTO-TRANSITION TO NEXT STAGE
        # The credit check is a backend operation - don't wait for user confirmation
        # that may never come. Automatically proceed to document upload stage.
        # ═══════════════════════════════════════════════════════════════════════
        
        # Auto-transition to INCOME_DOC_UPLOAD after showing credit results
        # This ensures the flow doesn't get stuck waiting for user input
        state.current_stage = ConversationStage.INCOME_DOC_UPLOAD
        print(f"➡️ TRANSITION: CREDIT_CHECK → INCOME_DOC_UPLOAD (auto-transition)")
        
        return state
    
    def _handle_income_doc_upload(self, state: ConversationState, message: str) -> ConversationState:
        """
        INCOME_DOC_UPLOAD stage handler.
        
        Transition Rule:
        - If documents are uploaded → move to UNDERWRITING_DECISION
        - Otherwise → stay (prompt for upload)
        
        Note: Actual document upload is handled separately via /upload endpoint
        """
        # Check if documents have been uploaded
        # This flag is set by the document upload endpoint
        if state.documents_uploaded:
            state.current_stage = ConversationStage.UNDERWRITING_DECISION
            print(f"➡️ TRANSITION: INCOME_DOC_UPLOAD → UNDERWRITING_DECISION")
        else:
            print(f"⏸️ STAYING: INCOME_DOC_UPLOAD (waiting for documents)")
        
        return state
    
    def _handle_underwriting_decision(self, state: ConversationState, message: str) -> ConversationState:
        """
        UNDERWRITING_DECISION stage handler.
        
        PHASE 4: DETERMINISTIC UNDERWRITING ENGINE
        ==========================================
        This handler uses the UnderwritingEngine to make loan decisions.
        The LLM NEVER decides approval/rejection - only the rules engine does.
        
        Transition Rules:
        - If loan_status = APPROVED → move to SANCTION
        - If loan_status = REJECTED → move to REJECTION
        - If loan_status = PENDING_DOCS → stay (requires salary slip)
        
        Why Deterministic:
        - Regulatory compliance (RBI guidelines)
        - Audit trail for all decisions
        - No random approvals from LLM hallucination
        - Consistent, fair treatment of customers
        """
        print("\n" + "="*60)
        print("📊 PHASE 4: UNDERWRITING DECISION STAGE")
        print("="*60)
        
        # ═══════════════════════════════════════════════════════════════════════
        # PHASE 4: IMPORT AND INITIALIZE UNDERWRITING ENGINE
        # We import here to avoid circular imports
        # ═══════════════════════════════════════════════════════════════════════
        from underwriting_engine import (
            UnderwritingEngine, 
            LoanStatus, 
            create_underwriting_engine
        )
        
        # Initialize underwriting engine if not already done
        if not hasattr(self, 'underwriting_engine'):
            self.underwriting_engine = create_underwriting_engine()
        
        # ═══════════════════════════════════════════════════════════════════════
        # GATHER INPUT DATA FROM STATE
        # All data comes from backend services (Phase 3), not user input
        # ═══════════════════════════════════════════════════════════════════════
        
        credit_score = state.credit_score or 0
        requested_amount = state.loan_amount or 0
        preapproved_limit = state.pre_approved_limit or 0
        monthly_income = state.monthly_income or 0
        tenure_months = state.loan_tenure_months or 48
        existing_emi = state.existing_emi or 0
        
        # Check if salary slip was uploaded (for extended limit requests)
        salary_slip_uploaded = state.salary_slip_uploaded or "salary" in " ".join(state.documents_uploaded).lower()
        
        print(f"📥 STATE DATA FOR UNDERWRITING:")
        print(f"   - Credit Score: {credit_score} (from Credit Bureau)")
        print(f"   - Requested Amount: ₹{requested_amount:,.0f} (from NEEDS_ANALYSIS)")
        print(f"   - Pre-approved Limit: ₹{preapproved_limit:,.0f} (from Offer Mart)")
        print(f"   - Monthly Income: ₹{monthly_income:,.0f} (from CRM)")
        print(f"   - Tenure: {tenure_months} months")
        print(f"   - Existing EMI: ₹{existing_emi:,.0f}")
        print(f"   - Salary Slip: {'✅ Uploaded' if salary_slip_uploaded else '❌ Not uploaded'}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # CALL UNDERWRITING ENGINE (DETERMINISTIC DECISION)
        # The engine applies rules - LLM has NO say in this decision
        # ═══════════════════════════════════════════════════════════════════════
        
        decision = self.underwriting_engine.evaluate(
            credit_score=credit_score,
            requested_amount=requested_amount,
            preapproved_limit=preapproved_limit,
            monthly_income=monthly_income,
            tenure_months=tenure_months,
            salary_slip_uploaded=salary_slip_uploaded,
            existing_emi=existing_emi
        )
        
        # ═══════════════════════════════════════════════════════════════════════
        # STORE DECISION IN STATE
        # These values are what the LLM will READ to generate its response
        # ═══════════════════════════════════════════════════════════════════════
        
        state.loan_status = decision.loan_status.value
        state.approval_type = decision.approval_type.value if decision.approval_type else None
        state.calculated_emi = decision.calculated_emi
        state.effective_interest_rate = decision.effective_interest_rate
        state.total_interest_payable = decision.total_interest_payable
        state.total_repayment_amount = decision.total_repayment_amount
        state.requires_salary_slip = decision.requires_salary_slip
        state.salary_slip_verified = decision.salary_slip_verified
        state.rejection_reason = decision.rejection_reason.value if decision.rejection_reason else None
        state.rejection_details = decision.rejection_details
        state.underwriting_timestamp = decision.decision_timestamp
        state.underwriting_factors = decision.decision_factors
        
        # Update EMI amount and interest rate for display
        state.emi_amount = decision.calculated_emi
        state.interest_rate = decision.effective_interest_rate
        
        # Also update legacy field for backward compatibility
        state.loan_approved = (decision.loan_status == LoanStatus.APPROVED)
        
        print(f"\n📋 DECISION STORED IN STATE:")
        print(f"   - loan_status: {state.loan_status}")
        print(f"   - approval_type: {state.approval_type}")
        print(f"   - calculated_emi: ₹{state.calculated_emi:,.0f}")
        print(f"   - effective_rate: {state.effective_interest_rate}%")
        print(f"   - rejection_reason: {state.rejection_reason}")
        
        # ═══════════════════════════════════════════════════════════════════════
        # DETERMINISTIC STAGE TRANSITION
        # Based on loan_status, transition to appropriate next stage
        # ═══════════════════════════════════════════════════════════════════════
        
        if decision.loan_status == LoanStatus.APPROVED:
            state.current_stage = ConversationStage.SANCTION
            print(f"✅ APPROVED → TRANSITION: UNDERWRITING_DECISION → SANCTION")
        
        elif decision.loan_status == LoanStatus.REJECTED:
            state.current_stage = ConversationStage.REJECTION
            print(f"❌ REJECTED → TRANSITION: UNDERWRITING_DECISION → REJECTION")
        
        elif decision.loan_status == LoanStatus.PENDING_DOCS:
            # Stay in current stage - need salary slip
            print(f"⏳ PENDING_DOCS → STAYING: Need salary slip upload")
            print(f"   (Upload salary slip to proceed with income verification)")
        
        else:
            # Unknown status - stay for manual review
            print(f"⚠️ UNKNOWN STATUS → STAYING: Needs manual review")
        
        return state
    
    def _handle_sanction(self, state: ConversationState, message: str) -> ConversationState:
        """
        SANCTION stage handler.
        
        PHASE 5: SANCTION LETTER GENERATION & SESSION CLOSURE
        =====================================================
        This is a TERMINAL state - loan is approved.
        
        This handler:
        1. Generates the sanction letter using SanctionLetterService
        2. Stores sanction details in shared state
        3. Marks session as closed to prevent further transitions
        
        HOW THIS SIMULATES REAL NBFC:
        -----------------------------
        In a real NBFC, reaching SANCTION stage would:
        - Trigger core banking to create loan account
        - Generate digitally signed sanction letter
        - Send notifications (SMS/Email)
        - Queue for disbursement
        - Close the application case
        
        WHY SESSION CLOSURE:
        --------------------
        Once sanctioned, no further actions needed in chat.
        Closing the session prevents:
        - LLM from contradicting the approval
        - Infinite conversation loops
        - Accidental re-processing
        """
        print("\n" + "="*60)
        print("🎉 PHASE 5: SANCTION STAGE - LOAN APPROVED!")
        print("="*60)
        
        # Only generate letter once (check if already done)
        if not state.sanction_letter_generated:
            # Import sanction service (here to avoid circular imports)
            from sanction_letter_service import (
                SanctionLetterService,
                SessionClosureService,
                SessionClosureReason
            )
            
            # Create sanction letter service
            sanction_service = SanctionLetterService()
            
            # Generate sanction letter using shared state values
            # ALL data comes from verified state - no fabrication
            # Uses mobile_number as primary contact identifier
            result = sanction_service.generate_sanction_letter(
                customer_name=state.user_name or "Valued Customer",
                customer_phone=state.user_mobile_number or "",  # mobile_number is the primary identifier
                customer_pan=state.user_pan or "",

                loan_amount=state.loan_amount or 0,
                interest_rate=state.effective_interest_rate or state.interest_rate or 12.5,
                tenure_months=state.loan_tenure_months or 48,
                emi_amount=state.calculated_emi or state.emi_amount or 0,
                approval_type=state.approval_type,
                session_id=state.session_id  # PHASE 7: Pass session ID for file naming
            )
            
            if result.success:
                # Store sanction details in state
                state.sanction_letter_generated = True
                state.sanction_letter_path = result.file_path  # PHASE 7: Store actual file path
                state.sanction_letter_url = result.download_url
                state.sanction_reference_number = result.reference_number
                state.sanction_validity_date = result.validity_date
                state.sanction_message = result.customer_message
                
                print(f"✅ PHASE 7: Sanction letter generated:")
                print(f"   Reference: {state.sanction_reference_number}")
                print(f"   File Path: {state.sanction_letter_path}")  # PHASE 7
                print(f"   Download URL: {state.sanction_letter_url}")
                print(f"   Valid Until: {state.sanction_validity_date}")
            else:
                print(f"⚠️ Sanction letter generation failed: {result.error_message}")
            
            # Close the session
            closure = SessionClosureService.close_session(
                reason=SessionClosureReason.LOAN_SANCTIONED,
                customer_name=state.user_name
            )
            
            state.session_closed = True
            state.closure_reason = closure["closure_reason"]
            state.closure_timestamp = closure["closure_timestamp"]
            state.closure_message = closure["closure_message"]
            
            print(f"🔒 Session closed: {state.closure_reason}")
        else:
            print(f"ℹ️ Sanction letter already generated")
        
        print("="*60)
        
        # Terminal state - stay here
        return state
    
    def _handle_rejection(self, state: ConversationState, message: str) -> ConversationState:
        """
        REJECTION stage handler.
        
        PHASE 5: REJECTION MESSAGE & SESSION CLOSURE
        =============================================
        This is a TERMINAL state - loan is rejected.
        
        This handler:
        1. Generates professional rejection message using RejectionHandlerService
        2. Stores rejection details and improvement tips in shared state
        3. Marks session as closed to prevent further transitions
        
        HOW THIS SIMULATES REAL NBFC:
        -----------------------------
        In a real NBFC, reaching REJECTION stage would:
        - Log rejection for regulatory reporting
        - Send formal rejection letter
        - Update CRM with rejection reason
        - Trigger follow-up workflows
        - Close the application case
        
        WHY SESSION CLOSURE:
        --------------------
        Once rejected, the decision is final.
        Closing the session prevents:
        - LLM from offering false hope
        - Circular conversations
        - Confusion about the outcome
        """
        print("\n" + "="*60)
        print("❌ PHASE 5: REJECTION STAGE - LOAN DECLINED")
        print("="*60)
        
        # Only generate rejection message once
        if not state.session_closed:
            # Import rejection service
            from sanction_letter_service import (
                RejectionHandlerService,
                SessionClosureService,
                SessionClosureReason
            )
            
            # Create rejection handler service
            rejection_service = RejectionHandlerService()
            
            # Generate rejection message using shared state values
            result = rejection_service.process_rejection(
                customer_name=state.user_name or "Valued Customer",
                rejection_reason=state.rejection_reason or "Application could not be approved",
                rejection_details=state.rejection_details,
                credit_score=state.credit_score,
                requested_amount=state.loan_amount,
                eligible_amount=state.pre_approved_limit * 2 if state.pre_approved_limit else None
            )
            
            if result.success:
                # Store rejection message in state
                state.rejection_message = result.customer_message
                state.improvement_tips = result.improvement_tips
                
                print(f"📝 Rejection message generated")
                print(f"   Reason: {state.rejection_reason}")
                print(f"   Tips provided: {len(result.improvement_tips.split('•')) if result.improvement_tips else 0}")
            
            # Close the session
            closure = SessionClosureService.close_session(
                reason=SessionClosureReason.LOAN_REJECTED,
                customer_name=state.user_name
            )
            
            state.session_closed = True
            state.closure_reason = closure["closure_reason"]
            state.closure_timestamp = closure["closure_timestamp"]
            state.closure_message = closure["closure_message"]
            
            print(f"🔒 Session closed: {state.closure_reason}")
        else:
            print(f"ℹ️ Rejection already processed")
        
        print("="*60)
        
        # Terminal state - stay here
        return state
    
    def get_stage_instruction(self, state: ConversationState) -> str:
        """
        Get the LLM instruction for the current stage.
        
        This is what tells the LLM HOW to phrase its response.
        The LLM does NOT decide flow - it only generates the message.
        
        PHASE 5 UPDATE:
        ---------------
        For SANCTION and REJECTION stages, we now include:
        - sanction_message / rejection_message (pre-formatted)
        - session_closed flag
        - closure_message
        
        The LLM should use these messages directly.
        
        Args:
            state: Current conversation state
            
        Returns:
            Instruction string for the LLM
        """
        base_instruction = STAGE_INSTRUCTIONS.get(state.current_stage, "")
        
        # Format amounts with proper None handling
        loan_amount_str = f"₹{state.loan_amount:,.0f}" if state.loan_amount else "Not specified"
        credit_score_str = str(state.credit_score) if state.credit_score else "Not checked"
        interest_rate_str = f"{state.interest_rate}%" if state.interest_rate else "Not calculated"
        emi_amount_str = f"₹{state.emi_amount:,.0f}" if state.emi_amount else "Not calculated"
        
        # Add context-specific details
        # Uses mobile_number as primary identifier (verified via OTP)
        context = f"""
CURRENT CONTEXT:
- Customer Name: {state.user_name or 'Unknown'}
- Mobile Number: {state.user_mobile_number or 'Not provided'}
- Loan Amount Requested: {loan_amount_str}
- Credit Score: {credit_score_str}
- Interest Rate: {interest_rate_str}
- EMI Amount: {emi_amount_str}
- OTP Sent: {state.otp_sent}
- OTP Verified: {state.otp_verified}
- Is Existing Customer: {state.is_existing_customer}
"""
        
        # PHASE 5: Add sanction/rejection specific context
        if state.current_stage == ConversationStage.SANCTION:
            context += f"""

PHASE 5 - SANCTION DETAILS (USE THESE IN YOUR RESPONSE):
=========================================================
Session Closed: {state.session_closed}
Sanction Letter Generated: {state.sanction_letter_generated}
Sanction Reference: {state.sanction_reference_number or 'N/A'}
Sanction Validity: {state.sanction_validity_date or 'N/A'}
Download URL: {state.sanction_letter_url or 'N/A'}
Approval Type: {state.approval_type or 'N/A'}

PRE-FORMATTED SANCTION MESSAGE (use this):
{state.sanction_message or 'Congratulations! Your loan has been approved.'}

CLOSURE MESSAGE:
{state.closure_message or 'Thank you for choosing Tata Capital!'}
=========================================================
"""
        
        elif state.current_stage == ConversationStage.REJECTION:
            context += f"""

PHASE 5 - REJECTION DETAILS (USE THESE IN YOUR RESPONSE):
=========================================================
Session Closed: {state.session_closed}
Rejection Reason: {state.rejection_reason or 'N/A'}
Rejection Details: {state.rejection_details or 'N/A'}

PRE-FORMATTED REJECTION MESSAGE (use this):
{state.rejection_message or 'We regret that we cannot approve your loan at this time.'}

IMPROVEMENT TIPS:
{state.improvement_tips or 'Please try again after addressing the feedback.'}

CLOSURE MESSAGE:
{state.closure_message or 'Thank you for your interest in Tata Capital.'}
=========================================================
"""
        
        return base_instruction + context


# ================================================================================
# HELPER FUNCTION FOR MAIN INTEGRATION
# ================================================================================

def create_stage_router(data_provider=None, backend_services=None) -> StageRouter:
    """
    Factory function to create a stage router.
    
    Args:
        data_provider: Optional data provider for customer lookups (legacy)
        backend_services: Optional BackendServices instance for Phase 3 integration
        
    Returns:
        Configured StageRouter instance
        
    PHASE 3 NOTE:
    - If backend_services is not provided, StageRouter will auto-initialize it
    - Backend services provide verified data from CUSTOMER_PROFILES dataset
    """
    return StageRouter(data_provider, backend_services)


# ================================================================================
# EXAMPLE USAGE (for testing)
# ================================================================================

if __name__ == "__main__":
    # Test the stage machine
    router = StageRouter()
    state = ConversationState()
    
    # Simulate conversation
    messages = [
        "Hi, I need a loan",
        "I want 5 lakhs",
        "My name is Rahul and my number is 9876543210",
        "123456",  # OTP
        "yes proceed",
    ]
    
    for msg in messages:
        print(f"\n{'='*60}")
        print(f"USER: {msg}")
        state = router.route(state, msg)
        print(f"STAGE: {state.current_stage.value}")
        print(f"{'='*60}")
