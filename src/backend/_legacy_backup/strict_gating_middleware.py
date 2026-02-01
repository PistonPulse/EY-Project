"""
================================================================================
STRICT GATING MIDDLEWARE
================================================================================

PURPOSE:
--------
This module provides a STRICT GATING MIDDLEWARE that sits between the API 
endpoint and the stage handler. It enforces absolute backend control by:

1. VALIDATING INPUT TYPE BEFORE PROCESSING
   - Every input must match the expected type for the current stage
   - Invalid input = re-ask (never advance, never interpret)

2. ENFORCING STAGE PRECONDITIONS  
   - Cannot enter OTP_VERIFICATION without name + mobile
   - Cannot enter KYC_VERIFICATION without OTP verified
   - Cannot enter INCOME_DOC_UPLOAD without KYC verified

3. PREVENTING PREMATURE MESSAGES
   - "Checking offers" only after KYC_VERIFICATION complete
   - "Processing approval" only in UNDERWRITING stage
   - Upload prompt only in INCOME_DOC_UPLOAD stage

4. PROVIDING DETERMINISTIC STAGE TRANSITIONS
   - No LLM involvement in stage decisions
   - Same input always produces same transition

================================================================================
WHY MIDDLEWARE INSTEAD OF MODIFYING HANDLERS:
================================================================================

The existing stage_handler_v2.py has complex logic that works correctly.
Rather than risk breaking existing functionality, we add a middleware layer
that:
- Intercepts requests BEFORE they reach the handler
- Validates input matches expected type
- Blocks requests that violate preconditions
- Logs all validation failures for debugging

This is a common pattern in banking systems where compliance requirements
demand an additional layer of validation.

================================================================================
INTEGRATION POINT:
================================================================================

In main.py /api/v2/chat endpoint:

    # BEFORE (current):
    result = conversational_handler.process_message(...)

    # AFTER (with gating):
    gated_result = strict_gating_middleware.process(
        session_id=request.session_id,
        user_message=request.message,
        handler=conversational_handler
    )
    if gated_result.blocked:
        return gated_result.reask_response
    result = gated_result.handler_result

================================================================================
"""

import re
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

# Import stage machine types
from stage_machine_v2 import (
    Stage,
    StageState,
    get_session_state,
    update_session_data
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | GATING | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('strict_gating')


# ================================================================================
# INPUT TYPE DEFINITIONS
# ================================================================================

class ExpectedInputType(Enum):
    """
    Defines what type of input is expected at each stage.
    The LLM cannot change these expectations - they are hardcoded.
    """
    ANY_TEXT = "any_text"              # For greeting, general responses
    LOAN_PURPOSE = "loan_purpose"       # Home loan, personal loan, etc.
    LOAN_AMOUNT = "loan_amount"         # Numeric amount in rupees/lakhs
    CITY = "city"                       # Indian city name
    EMPLOYMENT_TYPE = "employment"      # Salaried / Self-employed / Business
    FULL_NAME = "full_name"             # Person's full name (2-4 words)
    MOBILE_NUMBER = "mobile_number"     # 10-digit Indian mobile
    OTP_CODE = "otp_code"               # 4-6 digit OTP
    PAN_NUMBER = "pan_number"           # XXXXX0000X format
    AADHAAR_NUMBER = "aadhaar_number"   # 12-digit Aadhaar
    CONFIRMATION = "confirmation"       # Yes/No/Proceed/Continue
    DOCUMENT = "document"               # File upload (not text)


# ================================================================================
# STAGE → EXPECTED INPUT MAPPING
# ================================================================================

# Maps (stage, conversation_step) to expected input type
STAGE_EXPECTED_INPUT: Dict[Tuple[str, str], ExpectedInputType] = {
    # GREETING - Accept any text to start
    ("GREETING", "GREETING_WELCOME"): ExpectedInputType.ANY_TEXT,
    ("GREETING", None): ExpectedInputType.ANY_TEXT,
    
    # NEEDS_DISCOVERY - Purpose then Amount
    ("NEEDS_DISCOVERY", "NEEDS_ASK_PURPOSE"): ExpectedInputType.LOAN_PURPOSE,
    ("NEEDS_DISCOVERY", "NEEDS_ASK_AMOUNT"): ExpectedInputType.LOAN_AMOUNT,
    ("NEEDS_DISCOVERY", None): ExpectedInputType.LOAN_PURPOSE,
    
    # BASIC_ELIGIBILITY - City then Employment
    ("BASIC_ELIGIBILITY", "ELIGIBILITY_ASK_CITY"): ExpectedInputType.CITY,
    ("BASIC_ELIGIBILITY", "ELIGIBILITY_ASK_EMPLOYMENT"): ExpectedInputType.EMPLOYMENT_TYPE,
    ("BASIC_ELIGIBILITY", None): ExpectedInputType.CITY,
    
    # KYC_COLLECTION - Name then Mobile
    ("KYC_COLLECTION", "KYC_ASK_NAME"): ExpectedInputType.FULL_NAME,
    ("KYC_COLLECTION", "KYC_ASK_MOBILE"): ExpectedInputType.MOBILE_NUMBER,
    ("KYC_COLLECTION", None): ExpectedInputType.FULL_NAME,
    
    # OTP_VERIFICATION - OTP only
    ("OTP_VERIFICATION", "OTP_SENT"): ExpectedInputType.OTP_CODE,
    ("OTP_VERIFICATION", "OTP_RETRY"): ExpectedInputType.OTP_CODE,
    ("OTP_VERIFICATION", None): ExpectedInputType.OTP_CODE,
    
    # KYC_VERIFICATION - PAN then Aadhaar
    ("KYC_VERIFICATION", "KYC_ASK_PAN"): ExpectedInputType.PAN_NUMBER,
    ("KYC_VERIFICATION", "KYC_PAN_VERIFYING"): ExpectedInputType.ANY_TEXT,  # Wait for system
    ("KYC_VERIFICATION", "KYC_ASK_AADHAAR"): ExpectedInputType.AADHAAR_NUMBER,
    ("KYC_VERIFICATION", "KYC_AADHAAR_VERIFYING"): ExpectedInputType.ANY_TEXT,  # Wait for system
    ("KYC_VERIFICATION", "KYC_VERIFYING"): ExpectedInputType.PAN_NUMBER,  # First ask
    ("KYC_VERIFICATION", None): ExpectedInputType.PAN_NUMBER,
    
    # OFFER_DISCOVERY - Confirmation
    ("OFFER_DISCOVERY", "OFFER_CONFIRM_PROCEED"): ExpectedInputType.CONFIRMATION,
    ("OFFER_DISCOVERY", None): ExpectedInputType.CONFIRMATION,
    
    # INCOME_DOC_UPLOAD - Document or Confirmation
    ("INCOME_DOC_UPLOAD", "INCOME_UPLOAD_PROMPT"): ExpectedInputType.DOCUMENT,
    ("INCOME_DOC_UPLOAD", None): ExpectedInputType.DOCUMENT,
    
    # UNDERWRITING - Wait for system decision
    ("UNDERWRITING", None): ExpectedInputType.ANY_TEXT,
    
    # SANCTION - Session closed, read-only
    ("SANCTION", None): ExpectedInputType.ANY_TEXT,
    
    # REJECTION - Session closed, read-only
    ("REJECTION", None): ExpectedInputType.ANY_TEXT,
}


# ================================================================================
# INPUT VALIDATORS
# ================================================================================

def validate_loan_purpose(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains a recognizable loan purpose.
    Returns (is_valid, normalized_purpose or error)
    """
    text_lower = text.lower()
    
    PURPOSE_KEYWORDS = {
        "home": "Home Loan",
        "house": "Home Loan",
        "flat": "Home Loan",
        "apartment": "Home Loan",
        "property": "Home Loan",
        "renovation": "Home Renovation Loan",
        "personal": "Personal Loan",
        "medical": "Medical Loan",
        "health": "Medical Loan",
        "hospital": "Medical Loan",
        "wedding": "Wedding Loan",
        "marriage": "Wedding Loan",
        "education": "Education Loan",
        "study": "Education Loan",
        "college": "Education Loan",
        "business": "Business Loan",
        "car": "Vehicle Loan",
        "vehicle": "Vehicle Loan",
        "bike": "Vehicle Loan",
        "travel": "Travel Loan",
        "vacation": "Travel Loan",
        "debt": "Debt Consolidation",
        "consolidation": "Debt Consolidation",
        "emergency": "Emergency Loan",
    }
    
    for keyword, purpose in PURPOSE_KEYWORDS.items():
        if keyword in text_lower:
            return (True, purpose)
    
    return (False, "Could not identify loan purpose")


def validate_loan_amount(text: str) -> Tuple[bool, Optional[float]]:
    """
    Validate if text contains a valid loan amount.
    Returns (is_valid, amount_in_rupees or error)
    """
    text_lower = text.lower()
    
    # Pattern: X lakhs/lacs/L
    lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b'
    match = re.search(lakh_pattern, text_lower)
    if match:
        return (True, float(match.group(1)) * 100000)
    
    # Pattern: X crore
    crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b'
    match = re.search(crore_pattern, text_lower)
    if match:
        return (True, float(match.group(1)) * 10000000)
    
    # Pattern: Direct number (5+ digits)
    number_pattern = r'(?:rs\.?\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})|\d{5,})'
    match = re.search(number_pattern, text_lower)
    if match:
        amount_str = match.group(1).replace(',', '')
        amount = float(amount_str)
        if amount >= 10000:  # Minimum reasonable loan amount
            return (True, amount)
    
    return (False, "Could not identify loan amount")


def validate_city(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains an Indian city name.
    Returns (is_valid, normalized_city or error)
    """
    INDIAN_CITIES = {
        "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad",
        "kolkata", "pune", "ahmedabad", "jaipur", "surat", "lucknow",
        "kanpur", "nagpur", "indore", "thane", "bhopal", "patna",
        "vadodara", "ghaziabad", "ludhiana", "agra", "nashik", "ranchi",
        "faridabad", "meerut", "rajkot", "varanasi", "srinagar", "aurangabad",
        "gurgaon", "gurugram", "noida", "goa", "chandigarh", "coimbatore",
        "kochi", "cochin", "trivandrum", "thiruvananthapuram", "visakhapatnam",
        "vizag", "mangalore", "mangaluru", "mysore", "mysuru"
    }
    
    text_lower = text.lower().strip()
    words = text_lower.split()
    
    for word in words:
        word_clean = re.sub(r'[^\w]', '', word)
        if word_clean in INDIAN_CITIES:
            return (True, word_clean.title())
    
    # If message is 2-20 chars and looks like a city name
    if 2 <= len(text_lower) <= 20 and text_lower.isalpha():
        return (True, text.strip().title())
    
    return (False, "Could not identify city")


def validate_employment_type(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text indicates employment type.
    Returns (is_valid, normalized_type or error)
    """
    text_lower = text.lower()
    
    # Check self-employed FIRST (before "employed" which is a subset)
    if any(k in text_lower for k in ["self employed", "self-employed", "selfemployed", "freelance", "consultant"]):
        return (True, "self_employed")
    
    # Then check salaried
    if any(k in text_lower for k in ["salaried", "salary", "employee", "job", "employed"]):
        return (True, "salaried")
    
    if any(k in text_lower for k in ["business", "entrepreneur", "owner", "proprietor"]):
        return (True, "business")
    
    return (False, "Please specify: salaried, self-employed, or business owner")


def validate_full_name(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text is a person's full name.
    Returns (is_valid, normalized_name or error)
    """
    # Remove common prefixes
    text = re.sub(r'^(my name is|i am|i\'m|this is|call me)\s*', '', text, flags=re.IGNORECASE).strip()
    
    # Name should be 2-50 chars, mostly letters and spaces
    if not (2 <= len(text) <= 50):
        return (False, "Name should be 2-50 characters")
    
    # Check for numbers (names shouldn't have numbers)
    if re.search(r'\d', text):
        return (False, "Name should not contain numbers")
    
    # Check for special characters (SQL injection, XSS, etc.)
    if re.search(r'[;\'\"<>\\\/\-\-\|\{\}\[\]\(\)\!\@\#\$\%\^\&\*\=\+]', text):
        return (False, "Name should contain only letters and spaces")
    
    # Split into words
    words = text.split()
    if len(words) < 1 or len(words) > 5:
        return (False, "Please provide your full name")
    
    # Ensure only alphabetic characters and spaces
    if not re.match(r'^[A-Za-z\s]+$', text):
        return (False, "Name should contain only letters and spaces")
    
    # Basic validation - first letter of each word should be uppercase-able
    name = ' '.join(word.capitalize() for word in words)
    return (True, name)


def validate_mobile_number(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains a 10-digit Indian mobile number.
    Returns (is_valid, number or error)
    """
    # Remove spaces, dashes, parentheses
    cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
    
    # Remove country code if present
    if cleaned.startswith('91') and len(cleaned) == 12:
        cleaned = cleaned[2:]
    
    # Match 10-digit number starting with 6-9
    if re.match(r'^[6-9]\d{9}$', cleaned):
        return (True, cleaned)
    
    return (False, "Please enter a valid 10-digit mobile number")


def validate_otp_code(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains a 4-6 digit OTP.
    Returns (is_valid, otp or error)
    """
    # Remove spaces
    cleaned = text.strip().replace(' ', '')
    
    # Just digits, 4-6 characters
    if re.match(r'^\d{4,6}$', cleaned):
        return (True, cleaned)
    
    # Look for OTP pattern in text
    match = re.search(r'\b(\d{4,6})\b', text)
    if match:
        return (True, match.group(1))
    
    return (False, "Please enter the OTP sent to your mobile")


def validate_pan_number(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains a valid PAN number.
    Format: AAAAA0000A (5 letters, 4 digits, 1 letter)
    Returns (is_valid, pan or error)
    """
    text_upper = text.upper().strip()
    
    # Direct match
    if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', text_upper):
        return (True, text_upper)
    
    # Extract from text
    match = re.search(r'\b([A-Z]{5}\d{4}[A-Z])\b', text_upper)
    if match:
        return (True, match.group(1))
    
    return (False, "Please enter a valid PAN (format: ABCDE1234F)")


def validate_aadhaar_number(text: str) -> Tuple[bool, Optional[str]]:
    """
    Validate if text contains a valid Aadhaar number.
    Format: 12 digits, not starting with 0 or 1
    Returns (is_valid, aadhaar or error)
    """
    # Remove spaces and dashes
    cleaned = re.sub(r'[\s\-]', '', text)
    
    # 12 digits, not starting with 0 or 1
    if re.match(r'^[2-9]\d{11}$', cleaned):
        return (True, cleaned)
    
    # Extract from text
    match = re.search(r'\b([2-9]\d{11})\b', cleaned)
    if match:
        return (True, match.group(1))
    
    return (False, "Please enter a valid 12-digit Aadhaar number")


def validate_confirmation(text: str) -> Tuple[bool, Optional[bool]]:
    """
    Validate if text is a yes/no confirmation.
    Returns (is_valid, is_yes or error)
    """
    text_lower = text.lower().strip()
    
    YES_WORDS = ["yes", "ya", "yep", "yeah", "ok", "okay", "sure", "proceed", "continue", "confirm", "haan", "ji", "agreed"]
    NO_WORDS = ["no", "nope", "nahi", "cancel", "stop", "back"]
    
    if text_lower in YES_WORDS or any(w in text_lower for w in YES_WORDS):
        return (True, True)
    
    if text_lower in NO_WORDS or any(w in text_lower for w in NO_WORDS):
        return (True, False)
    
    return (False, "Please confirm with Yes or No")


# ================================================================================
# GATING RESULT
# ================================================================================

@dataclass
class GatingResult:
    """Result of gating validation"""
    allowed: bool
    blocked: bool = False
    reask_required: bool = False
    reask_message: str = ""
    precondition_failed: bool = False
    precondition_error: str = ""
    validated_data: Dict[str, Any] = field(default_factory=dict)
    log_entry: str = ""


# ================================================================================
# STRICT GATING MIDDLEWARE CLASS
# ================================================================================

class StrictGatingMiddleware:
    """
    Middleware that validates all inputs BEFORE they reach the stage handler.
    
    PRINCIPLE: 
    - Backend controls WHAT to expect
    - Validator controls WHETHER input matches
    - Handler controls HOW to process valid input
    - LLM controls HOW to phrase response (ONLY)
    """
    
    def __init__(self):
        logger.info("=" * 60)
        logger.info("STRICT GATING MIDDLEWARE INITIALIZED")
        logger.info("All inputs will be validated before processing")
        logger.info("=" * 60)
    
    def validate_input(
        self,
        session_id: str,
        user_message: str,
        current_stage: str,
        current_step: Optional[str],
        state_data: Dict[str, Any]
    ) -> GatingResult:
        """
        Validate user input against expected type for current stage.
        
        Returns:
            GatingResult indicating whether to proceed or block
        """
        result = GatingResult(allowed=True)
        
        # Get expected input type
        expected_type = STAGE_EXPECTED_INPUT.get(
            (current_stage, current_step),
            STAGE_EXPECTED_INPUT.get((current_stage, None), ExpectedInputType.ANY_TEXT)
        )
        
        logger.info(f"Validating input for stage={current_stage}, step={current_step}")
        logger.info(f"Expected input type: {expected_type.value}")
        logger.info(f"User message: {user_message[:50]}...")
        
        # =====================================================================
        # PRECONDITION CHECKS (HARD GATES)
        # =====================================================================
        
        # Gate: OTP_VERIFICATION requires name + mobile
        if current_stage == "OTP_VERIFICATION":
            if not state_data.get("user_name"):
                result.allowed = False
                result.precondition_failed = True
                result.precondition_error = "Name must be collected before OTP verification"
                result.log_entry = f"GATE BLOCKED: OTP_VERIFICATION without user_name"
                return result
            
            if not state_data.get("user_mobile"):
                result.allowed = False
                result.precondition_failed = True
                result.precondition_error = "Mobile number must be collected before OTP verification"
                result.log_entry = f"GATE BLOCKED: OTP_VERIFICATION without user_mobile"
                return result
        
        # Gate: KYC_VERIFICATION requires OTP verified
        if current_stage == "KYC_VERIFICATION":
            if not state_data.get("otp_verified"):
                result.allowed = False
                result.precondition_failed = True
                result.precondition_error = "OTP must be verified before KYC verification"
                result.log_entry = f"GATE BLOCKED: KYC_VERIFICATION without otp_verified"
                return result
        
        # Gate: INCOME_DOC_UPLOAD requires KYC verified
        if current_stage == "INCOME_DOC_UPLOAD":
            if not state_data.get("kyc_verified"):
                # Allow if both PAN and Aadhaar are verified
                pan_ok = state_data.get("pan_verified", False)
                aadhaar_ok = state_data.get("aadhaar_verified", False)
                if not (pan_ok and aadhaar_ok):
                    result.allowed = False
                    result.precondition_failed = True
                    result.precondition_error = "KYC must be verified before document upload"
                    result.log_entry = f"GATE BLOCKED: INCOME_DOC_UPLOAD without KYC verified"
                    return result
        
        # =====================================================================
        # INPUT TYPE VALIDATION
        # =====================================================================
        
        if expected_type == ExpectedInputType.ANY_TEXT:
            # Accept any text
            result.validated_data["raw_input"] = user_message
            result.log_entry = f"ACCEPTED: Any text allowed at {current_stage}"
            return result
        
        elif expected_type == ExpectedInputType.LOAN_PURPOSE:
            is_valid, value = validate_loan_purpose(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Could you tell me what you'd like to use the loan for? For example: home renovation, personal expenses, wedding, education, etc."
                result.log_entry = f"REASK: Expected loan purpose, got '{user_message[:30]}'"
            else:
                result.validated_data["loan_purpose"] = value
                result.log_entry = f"ACCEPTED: Loan purpose = {value}"
            return result
        
        elif expected_type == ExpectedInputType.LOAN_AMOUNT:
            is_valid, value = validate_loan_amount(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "I didn't catch the loan amount. Could you specify how much you're looking for? For example: 5 lakhs, 10 lakh, etc."
                result.log_entry = f"REASK: Expected loan amount, got '{user_message[:30]}'"
            else:
                result.validated_data["loan_amount"] = value
                result.log_entry = f"ACCEPTED: Loan amount = {value}"
            return result
        
        elif expected_type == ExpectedInputType.CITY:
            is_valid, value = validate_city(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Which city do you currently live in? Please share your city name."
                result.log_entry = f"REASK: Expected city, got '{user_message[:30]}'"
            else:
                result.validated_data["city"] = value
                result.log_entry = f"ACCEPTED: City = {value}"
            return result
        
        elif expected_type == ExpectedInputType.EMPLOYMENT_TYPE:
            is_valid, value = validate_employment_type(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Are you salaried or self-employed? Please specify your employment type."
                result.log_entry = f"REASK: Expected employment type, got '{user_message[:30]}'"
            else:
                result.validated_data["employment_type"] = value
                result.log_entry = f"ACCEPTED: Employment = {value}"
            return result
        
        elif expected_type == ExpectedInputType.FULL_NAME:
            is_valid, value = validate_full_name(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Could you please share your full name as it appears on your PAN card?"
                result.log_entry = f"REASK: Expected name, got '{user_message[:30]}'"
            else:
                result.validated_data["user_name"] = value
                result.log_entry = f"ACCEPTED: Name = {value}"
            return result
        
        elif expected_type == ExpectedInputType.MOBILE_NUMBER:
            is_valid, value = validate_mobile_number(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Please enter your 10-digit mobile number. This will be used to send you an OTP for verification."
                result.log_entry = f"REASK: Expected mobile, got '{user_message[:30]}'"
            else:
                result.validated_data["user_mobile"] = value
                result.log_entry = f"ACCEPTED: Mobile = {value}"
            return result
        
        elif expected_type == ExpectedInputType.OTP_CODE:
            is_valid, value = validate_otp_code(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Please enter the OTP sent to your registered mobile number."
                result.log_entry = f"REASK: Expected OTP, got '{user_message[:30]}'"
            else:
                result.validated_data["otp_entered"] = value
                result.log_entry = f"ACCEPTED: OTP entered"
            return result
        
        elif expected_type == ExpectedInputType.PAN_NUMBER:
            is_valid, value = validate_pan_number(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Please enter your PAN number in the format ABCDE1234F."
                result.log_entry = f"REASK: Expected PAN, got '{user_message[:30]}'"
            else:
                result.validated_data["pan_number"] = value
                result.log_entry = f"ACCEPTED: PAN = {value}"
            return result
        
        elif expected_type == ExpectedInputType.AADHAAR_NUMBER:
            is_valid, value = validate_aadhaar_number(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Please enter your 12-digit Aadhaar number."
                result.log_entry = f"REASK: Expected Aadhaar, got '{user_message[:30]}'"
            else:
                result.validated_data["aadhaar_number"] = value
                result.log_entry = f"ACCEPTED: Aadhaar entered"
            return result
        
        elif expected_type == ExpectedInputType.CONFIRMATION:
            is_valid, value = validate_confirmation(user_message)
            if not is_valid:
                result.allowed = False
                result.reask_required = True
                result.reask_message = "Would you like to proceed? Please confirm with Yes or No."
                result.log_entry = f"REASK: Expected confirmation, got '{user_message[:30]}'"
            else:
                result.validated_data["confirmed"] = value
                result.log_entry = f"ACCEPTED: Confirmation = {value}"
            return result
        
        elif expected_type == ExpectedInputType.DOCUMENT:
            # Document upload is handled separately - text input at doc stage is just confirmation
            result.validated_data["raw_input"] = user_message
            result.log_entry = f"ACCEPTED: Document stage - text as confirmation"
            return result
        
        # Default: accept
        result.validated_data["raw_input"] = user_message
        result.log_entry = f"ACCEPTED: Default pass-through"
        return result
    
    def get_reask_prompt(
        self,
        current_stage: str,
        current_step: Optional[str],
        gating_result: GatingResult
    ) -> str:
        """
        Generate a professional re-ask prompt when input validation fails.
        """
        if gating_result.precondition_failed:
            return f"I need some information first. {gating_result.precondition_error}. Let me take you back to the correct step."
        
        return gating_result.reask_message


# ================================================================================
# SINGLETON INSTANCE
# ================================================================================

_middleware_instance: Optional[StrictGatingMiddleware] = None

def get_gating_middleware() -> StrictGatingMiddleware:
    """Get or create the singleton middleware instance."""
    global _middleware_instance
    if _middleware_instance is None:
        _middleware_instance = StrictGatingMiddleware()
    return _middleware_instance
