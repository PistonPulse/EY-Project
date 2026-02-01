"""
================================================================================
STRICT STAGE ENFORCEMENT - BANKING COMPLIANCE MODULE
================================================================================

THIS MODULE ENFORCES ABSOLUTE STAGE CONTROL FOR NBFC LOAN CHATBOT.

================================================================================
WHY STRICT STAGE ENFORCEMENT IS REQUIRED IN BANKING
================================================================================

1. REGULATORY COMPLIANCE (RBI/NBFC Guidelines):
   - Every loan journey step MUST be documented
   - KYC verification CANNOT be skipped
   - OTP verification MUST precede data access
   - Decisions MUST be auditable

2. FRAUD PREVENTION:
   - Attackers cannot bypass verification by typing random text
   - Prompt injection cannot advance stages
   - Identity MUST be verified before CRM access

3. DATA INTEGRITY:
   - Only valid formatted data is stored
   - Invalid inputs are rejected, not "creatively interpreted"
   - Same input = same result (deterministic)

4. USER EXPERIENCE:
   - Predictable, professional flow
   - Clear error messages when input doesn't match
   - No confusion about what the system expects

================================================================================
WHY LLM MUST NEVER CONTROL FLOW
================================================================================

LLMs are NON-DETERMINISTIC:
- Same input can produce different outputs
- Prompt injection can manipulate decisions
- Context window issues cause forgetting
- Hallucination can skip critical steps

THEREFORE:
- Stage transitions = Python code ONLY
- Input validation = Regex/rules ONLY
- Data extraction = Pattern matching ONLY
- LLM = Response PHRASING only (after decision is made)

================================================================================
"""

from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import re
import logging
from datetime import datetime

# Import strict input validator
from strict_input_validator import (
    ExpectedInputType,
    ValidationResult,
    validate_input,
    normalize_input,
    get_expected_input_type,
    STAGE_EXPECTED_INPUT
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | STAGE_ENFORCE | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('strict_stage_enforcement')


# ================================================================================
# STAGE QUESTION MAP - EXACTLY ONE QUESTION PER (STAGE, STEP)
# ================================================================================

@dataclass
class StageQuestion:
    """
    Defines the SINGLE question for each stage/step combination.
    
    CRITICAL RULES:
    1. Each step has EXACTLY ONE question
    2. LLM can rephrase this question, but cannot change it
    3. Question defines what input is EXPECTED
    4. If user provides wrong input type, RE-ASK this question
    """
    stage: str
    step: str
    question_template: str
    expected_input: ExpectedInputType
    reask_template: str
    max_reasks: int = 3


# The DEFINITIVE list of questions - ONE per step
STAGE_QUESTIONS: Dict[str, StageQuestion] = {
    # GREETING - Welcome only, no data collection
    "GREETING:WELCOME": StageQuestion(
        stage="GREETING",
        step="WELCOME",
        question_template="Welcome to Tata Capital! I'm here to help you with your loan needs. How can I assist you today?",
        expected_input=ExpectedInputType.ANY_TEXT,
        reask_template="How may I help you today?"
    ),
    
    # NEEDS_DISCOVERY - Purpose first, then Amount
    "NEEDS_DISCOVERY:ASK_PURPOSE": StageQuestion(
        stage="NEEDS_DISCOVERY",
        step="ASK_PURPOSE",
        question_template="What would you like to use the loan for? For example: home renovation, wedding, education, medical expenses, or business needs.",
        expected_input=ExpectedInputType.LOAN_PURPOSE,
        reask_template="Could you tell me the purpose of your loan? This helps us find the best option for you."
    ),
    "NEEDS_DISCOVERY:ASK_AMOUNT": StageQuestion(
        stage="NEEDS_DISCOVERY",
        step="ASK_AMOUNT",
        question_template="How much loan amount are you looking for? Please share the amount in lakhs or as a number.",
        expected_input=ExpectedInputType.LOAN_AMOUNT,
        reask_template="Please enter the loan amount you need. For example: '5 lakhs' or '500000'."
    ),
    
    # BASIC_ELIGIBILITY - City first, then Employment
    "BASIC_ELIGIBILITY:ASK_CITY": StageQuestion(
        stage="BASIC_ELIGIBILITY",
        step="ASK_CITY",
        question_template="Which city do you currently reside in?",
        expected_input=ExpectedInputType.CITY,
        reask_template="Please share the city you live in. For example: Mumbai, Delhi, Bangalore."
    ),
    "BASIC_ELIGIBILITY:ASK_EMPLOYMENT": StageQuestion(
        stage="BASIC_ELIGIBILITY",
        step="ASK_EMPLOYMENT",
        question_template="Are you salaried or self-employed?",
        expected_input=ExpectedInputType.EMPLOYMENT,
        reask_template="Please tell us if you're salaried, self-employed, or a business owner."
    ),
    
    # KYC_COLLECTION - Name first, then Mobile
    "KYC_COLLECTION:ASK_NAME": StageQuestion(
        stage="KYC_COLLECTION",
        step="ASK_NAME",
        question_template="To proceed with verification, please share your full name as per your PAN card.",
        expected_input=ExpectedInputType.FULL_NAME,
        reask_template="Please enter your full name as it appears on your PAN card."
    ),
    "KYC_COLLECTION:ASK_MOBILE": StageQuestion(
        stage="KYC_COLLECTION",
        step="ASK_MOBILE",
        question_template="Please share your 10-digit mobile number for OTP verification.",
        expected_input=ExpectedInputType.MOBILE_NUMBER,
        reask_template="Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9."
    ),
    
    # OTP_VERIFICATION - OTP only
    "OTP_VERIFICATION:ASK_OTP": StageQuestion(
        stage="OTP_VERIFICATION",
        step="ASK_OTP",
        question_template="We've sent an OTP to your mobile number. Please enter the 6-digit code.",
        expected_input=ExpectedInputType.OTP_CODE,
        reask_template="Please enter the OTP sent to your mobile. It's a 4-6 digit code."
    ),
    
    # KYC_VERIFICATION - PAN first, then Aadhaar (if needed)
    "KYC_VERIFICATION:ASK_PAN": StageQuestion(
        stage="KYC_VERIFICATION",
        step="ASK_PAN",
        question_template="Please share your PAN number for identity verification.",
        expected_input=ExpectedInputType.PAN_NUMBER,
        reask_template="Please enter a valid PAN number. Format: ABCDE1234F (5 letters, 4 digits, 1 letter)."
    ),
    "KYC_VERIFICATION:ASK_AADHAAR": StageQuestion(
        stage="KYC_VERIFICATION",
        step="ASK_AADHAAR",
        question_template="Please share your Aadhaar number for additional verification.",
        expected_input=ExpectedInputType.AADHAAR_NUMBER,
        reask_template="Please enter a valid 12-digit Aadhaar number."
    ),
    
    # OFFER_DISCOVERY - Confirmation only
    "OFFER_DISCOVERY:CONFIRM_PROCEED": StageQuestion(
        stage="OFFER_DISCOVERY",
        step="CONFIRM_PROCEED",
        question_template="Based on your profile, here are your eligible offers. Would you like to proceed?",
        expected_input=ExpectedInputType.CONFIRMATION,
        reask_template="Please confirm if you'd like to proceed with the loan offer. Say 'yes' to continue or 'no' to reconsider."
    ),
    
    # INCOME_DOC_UPLOAD - Document upload (handled separately)
    "INCOME_DOC_UPLOAD:UPLOAD_PROMPT": StageQuestion(
        stage="INCOME_DOC_UPLOAD",
        step="UPLOAD_PROMPT",
        question_template="Please upload your salary slip or income proof using the upload button below.",
        expected_input=ExpectedInputType.DOCUMENT,
        reask_template="Please use the upload button to share your income document."
    ),
}


# ================================================================================
# STAGE ENFORCEMENT CLASS
# ================================================================================

class StrictStageEnforcer:
    """
    Enforces ABSOLUTE stage control - no exceptions.
    
    ================================================================================
    HOW IT PREVENTS HALLUCINATION AND CHAOS:
    ================================================================================
    
    1. INPUT VALIDATION FIRST:
       - User input is validated BEFORE any processing
       - If input doesn't match expected type, REJECT and re-ask
       - LLM never sees invalid input for flow decisions
    
    2. STAGE TRANSITIONS ARE EXPLICIT:
       - Only advance_stage() can change current stage
       - advance_stage() requires preconditions to be met
       - Invalid transitions are BLOCKED and logged
    
    3. ONE QUESTION AT A TIME:
       - Each step has exactly ONE question
       - User must answer current question before proceeding
       - No skipping, no multi-question messages
    
    4. DATA STORAGE IS CONTROLLED:
       - Only validated data is stored in state
       - Invalid data is never stored
       - State reflects what we ACTUALLY verified
    
    ================================================================================
    """
    
    def __init__(self, session_id: str, state: Dict[str, Any]):
        """Initialize enforcer with session state."""
        self.session_id = session_id
        self.state = state
        self.current_stage = state.get("current_stage", "GREETING")
        self.current_step = state.get("current_step", "WELCOME")
        self.reask_count = state.get("reask_count", 0)
    
    def get_question_key(self) -> str:
        """Get the key for current stage:step combination."""
        return f"{self.current_stage}:{self.current_step}"
    
    def get_current_question(self) -> Optional[StageQuestion]:
        """Get the question for current stage/step."""
        key = self.get_question_key()
        return STAGE_QUESTIONS.get(key)
    
    def get_expected_input_type(self) -> ExpectedInputType:
        """Get what input type is currently expected."""
        question = self.get_current_question()
        if question:
            return question.expected_input
        return ExpectedInputType.ANY_TEXT
    
    def process_input(self, raw_input: str) -> Dict[str, Any]:
        """
        Process user input with STRICT validation.
        
        Returns:
            Dict with:
            - valid: bool - whether input was accepted
            - extracted_value: Any - the extracted/cleaned value
            - should_reask: bool - whether to re-ask the same question
            - response_template: str - what to say back
            - advance_stage: bool - whether to advance to next stage
            - new_stage: str - the new stage (if advancing)
            - new_step: str - the new step (if advancing)
        """
        logger.info(f"Processing input for {self.current_stage}:{self.current_step}")
        logger.info(f"Raw input: {raw_input[:50]}...")
        
        # Get expected input type
        expected_type = self.get_expected_input_type()
        
        # Normalize and validate
        normalized = normalize_input(raw_input)
        validation = validate_input(normalized, expected_type)
        
        result = {
            "valid": validation.valid,
            "extracted_value": validation.extracted_value,
            "should_reask": False,
            "response_template": "",
            "advance_stage": False,
            "new_stage": self.current_stage,
            "new_step": self.current_step,
            "validation_error": validation.error_message
        }
        
        if not validation.valid:
            # Input doesn't match expected type - RE-ASK
            self.reask_count += 1
            question = self.get_current_question()
            
            if question and self.reask_count <= question.max_reasks:
                result["should_reask"] = True
                result["response_template"] = question.reask_template
                
                if validation.reask_hint:
                    result["response_template"] += f" ({validation.reask_hint})"
                
                logger.info(f"Invalid input - re-asking (attempt {self.reask_count})")
            else:
                # Max re-asks exceeded - still re-ask but log warning
                result["should_reask"] = True
                result["response_template"] = question.reask_template if question else "Please try again."
                logger.warning(f"Max re-asks exceeded for {self.get_question_key()}")
            
            return result
        
        # Input is valid - reset reask count
        self.reask_count = 0
        
        # Determine next step based on current stage
        next_stage, next_step = self._determine_next_step(validation.extracted_value)
        
        result["advance_stage"] = (next_stage != self.current_stage or next_step != self.current_step)
        result["new_stage"] = next_stage
        result["new_step"] = next_step
        
        logger.info(f"Valid input - advancing to {next_stage}:{next_step}")
        
        return result
    
    def _determine_next_step(self, extracted_value: Any) -> Tuple[str, str]:
        """
        Determine the next stage/step based on current position and extracted value.
        
        This is the DETERMINISTIC transition logic - NO LLM INVOLVEMENT.
        """
        current = f"{self.current_stage}:{self.current_step}"
        
        # =========================================================================
        # GREETING - Welcome → Ask Purpose (transition to NEEDS_DISCOVERY)
        # =========================================================================
        if current == "GREETING:WELCOME":
            return "NEEDS_DISCOVERY", "ASK_PURPOSE"
        
        # =========================================================================
        # NEEDS_DISCOVERY - Purpose → Amount → Eligibility (transition to BASIC_ELIGIBILITY)
        # =========================================================================
        elif current == "NEEDS_DISCOVERY:ASK_PURPOSE":
            return "NEEDS_DISCOVERY", "ASK_AMOUNT"
        elif current == "NEEDS_DISCOVERY:ASK_AMOUNT":
            return "BASIC_ELIGIBILITY", "ASK_CITY"
        
        # =========================================================================
        # BASIC_ELIGIBILITY - City → Employment → KYC (transition to KYC_COLLECTION)
        # =========================================================================
        elif current == "BASIC_ELIGIBILITY:ASK_CITY":
            return "BASIC_ELIGIBILITY", "ASK_EMPLOYMENT"
        elif current == "BASIC_ELIGIBILITY:ASK_EMPLOYMENT":
            return "KYC_COLLECTION", "ASK_NAME"
        
        # =========================================================================
        # KYC_COLLECTION - Name → Mobile → OTP (transition to OTP_VERIFICATION)
        # =========================================================================
        elif current == "KYC_COLLECTION:ASK_NAME":
            return "KYC_COLLECTION", "ASK_MOBILE"
        elif current == "KYC_COLLECTION:ASK_MOBILE":
            return "OTP_VERIFICATION", "ASK_OTP"
        
        # =========================================================================
        # OTP_VERIFICATION - OTP verified → KYC Verification
        # (This transition requires additional check - OTP must match)
        # =========================================================================
        elif current == "OTP_VERIFICATION:ASK_OTP":
            # OTP verification handled separately - this just advances
            return "KYC_VERIFICATION", "ASK_PAN"
        
        # =========================================================================
        # KYC_VERIFICATION - PAN → Aadhaar (optional) → Offer Discovery
        # =========================================================================
        elif current == "KYC_VERIFICATION:ASK_PAN":
            # PAN verified - can skip Aadhaar in demo
            return "OFFER_DISCOVERY", "CONFIRM_PROCEED"
        elif current == "KYC_VERIFICATION:ASK_AADHAAR":
            return "OFFER_DISCOVERY", "CONFIRM_PROCEED"
        
        # =========================================================================
        # OFFER_DISCOVERY - Confirm → Document Upload
        # =========================================================================
        elif current == "OFFER_DISCOVERY:CONFIRM_PROCEED":
            if extracted_value == "YES":
                return "INCOME_DOC_UPLOAD", "UPLOAD_PROMPT"
            else:
                # User said no - stay and explain options
                return "OFFER_DISCOVERY", "CONFIRM_PROCEED"
        
        # =========================================================================
        # INCOME_DOC_UPLOAD - Upload → Underwriting
        # (Handled by document upload endpoint, not chat)
        # =========================================================================
        elif current == "INCOME_DOC_UPLOAD:UPLOAD_PROMPT":
            # Stay here until document is uploaded via upload endpoint
            return "INCOME_DOC_UPLOAD", "UPLOAD_PROMPT"
        
        # Default - stay in current position
        return self.current_stage, self.current_step
    
    def can_advance_to_stage(self, target_stage: str) -> Tuple[bool, str]:
        """
        Check if transition to target stage is allowed.
        
        Returns (allowed, reason).
        """
        # Define required preconditions for each stage
        preconditions = {
            "NEEDS_DISCOVERY": [],  # No preconditions
            "BASIC_ELIGIBILITY": [
                ("loan_purpose", "Loan purpose must be provided"),
                ("loan_amount", "Loan amount must be provided"),
            ],
            "KYC_COLLECTION": [
                ("city", "City must be provided"),
                ("employment_type", "Employment type must be provided"),
            ],
            "OTP_VERIFICATION": [
                ("user_name", "Name must be provided"),
                ("user_mobile", "Mobile number must be provided"),
            ],
            "KYC_VERIFICATION": [
                ("otp_verified", "OTP must be verified first"),
            ],
            "OFFER_DISCOVERY": [
                ("pan_verified", "PAN must be verified first"),
            ],
            "INCOME_DOC_UPLOAD": [
                ("kyc_verified", "KYC must be completed first"),
            ],
            "UNDERWRITING": [
                ("documents_uploaded", "Documents must be uploaded first"),
            ],
            "SANCTION": [
                ("loan_status", "Underwriting must be completed first"),
            ],
            "REJECTION": [
                ("loan_status", "Underwriting must be completed first"),
            ],
        }
        
        required = preconditions.get(target_stage, [])
        
        for field, message in required:
            value = self.state.get(field)
            if not value:
                return False, message
        
        return True, "OK"


# ================================================================================
# HELPER FUNCTIONS
# ================================================================================

def get_question_for_stage(stage: str, step: str) -> Optional[str]:
    """Get the question template for a stage/step."""
    key = f"{stage}:{step}"
    question = STAGE_QUESTIONS.get(key)
    return question.question_template if question else None


def get_reask_for_stage(stage: str, step: str) -> Optional[str]:
    """Get the re-ask template for a stage/step."""
    key = f"{stage}:{step}"
    question = STAGE_QUESTIONS.get(key)
    return question.reask_template if question else None


def validate_stage_transition(
    current_stage: str,
    target_stage: str,
    state: Dict[str, Any]
) -> Tuple[bool, str]:
    """
    Validate that a stage transition is allowed.
    
    Returns (allowed, reason).
    """
    enforcer = StrictStageEnforcer(
        session_id=state.get("session_id", "unknown"),
        state=state
    )
    return enforcer.can_advance_to_stage(target_stage)
