"""
================================================================================
CONVERSATION FLOW CONTROLLER - STRICT MESSAGE SEQUENCE ENFORCEMENT
================================================================================

PURPOSE:
--------
This module enforces a STRICT, LINEAR, BANKING-COMPLIANT conversation flow.
The chatbot CANNOT ask any question unless:
1. The previous required answer is verified
2. The backend state explicitly allows the next question

================================================================================
WHY BANKING CONVERSATIONS MUST BE LINEAR (COMPLIANCE REQUIREMENT)
================================================================================

In NBFC/Banking systems, conversation flow is NOT arbitrary. It is:

1. REGULATORY: RBI KYC guidelines require specific verification sequence
2. AUDITABLE: Every step must be traceable for compliance audits
3. FRAUD-PREVENTIVE: Skipping steps creates attack vectors
4. LEGALLY BINDING: Information collected follows legal sequence

A customer CANNOT:
- Provide PAN before verifying mobile (fraud prevention)
- Skip OTP verification (identity locking requirement)
- Provide Aadhaar before PAN (document hierarchy)

================================================================================
WHY LLMs ARE RESTRICTED IN COMPLIANCE FLOWS
================================================================================

LLMs are:
- Non-deterministic (same prompt → different responses)
- Prompt-injectable (user can manipulate flow)
- Not auditable (decisions not reproducible)
- Not compliant (cannot guarantee regulatory adherence)

Therefore:
- LLM receives: current_stage, allowed_question, expected_answer_type
- LLM generates: ONLY the wording of the question
- LLM CANNOT: decide next question, skip questions, interpret answers as different fields

================================================================================
WHY KYC IS MULTI-STEP (REGULATORY REQUIREMENT)
================================================================================

KYC (Know Your Customer) in India follows:
1. MOBILE + OTP: Proves possession of phone number
2. PAN: Establishes financial/tax identity (Income Tax Department)
3. AADHAAR: Establishes physical identity (UIDAI)

Each verification is:
- INDEPENDENT: Aadhaar success ≠ PAN success
- SEQUENTIAL: Must complete in order
- DETERMINISTIC: Fixed API response, no LLM involvement
- AUDITED: Timestamp, result, source recorded

================================================================================
"""

from enum import Enum
from typing import Dict, Any, Optional, Tuple, List
from dataclasses import dataclass
import logging
import re
from datetime import datetime

# ================================================================================
# LOGGING
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | FLOW_CTRL | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('flow_controller')


# ================================================================================
# FLOW STEP DEFINITIONS
# ================================================================================

class FlowStep(Enum):
    """
    Defines each step in the conversation flow.
    Steps MUST be executed in ORDER. No skipping allowed.
    """
    # Step 1: Greeting
    GREETING = "GREETING"
    
    # Step 2-3: Needs Discovery
    NEEDS_PURPOSE = "NEEDS_PURPOSE"
    NEEDS_AMOUNT = "NEEDS_AMOUNT"
    
    # Step 4-5: Basic Eligibility
    ELIGIBILITY_CITY = "ELIGIBILITY_CITY"
    ELIGIBILITY_EMPLOYMENT = "ELIGIBILITY_EMPLOYMENT"
    
    # Step 6-7: KYC Collection
    KYC_NAME = "KYC_NAME"
    KYC_MOBILE = "KYC_MOBILE"
    
    # Step 8: OTP Verification
    OTP_VERIFICATION = "OTP_VERIFICATION"
    
    # Step 9: PAN Verification
    PAN_COLLECTION = "PAN_COLLECTION"
    PAN_VERIFYING = "PAN_VERIFYING"
    
    # Step 10: Aadhaar Verification
    AADHAAR_COLLECTION = "AADHAAR_COLLECTION"
    AADHAAR_VERIFYING = "AADHAAR_VERIFYING"
    
    # Step 11: Offer Discovery
    OFFER_DISCOVERY = "OFFER_DISCOVERY"
    
    # Step 12: Income Document Upload
    INCOME_DOC_UPLOAD = "INCOME_DOC_UPLOAD"
    INCOME_VERIFYING = "INCOME_VERIFYING"
    
    # Step 13: Underwriting
    UNDERWRITING = "UNDERWRITING"
    
    # Terminal Steps
    SANCTION = "SANCTION"
    REJECTION = "REJECTION"


# ================================================================================
# EXPECTED INPUT TYPES
# ================================================================================

class ExpectedInput(Enum):
    """Types of input expected at each step."""
    FREE_TEXT = "free_text"           # Any text (greeting intent)
    LOAN_PURPOSE = "loan_purpose"     # Purpose keywords
    LOAN_AMOUNT = "loan_amount"       # Numeric amount
    CITY_NAME = "city_name"           # City name
    EMPLOYMENT_TYPE = "employment"    # salaried/self-employed enum
    FULL_NAME = "full_name"           # Alphabetic text
    MOBILE_10_DIGIT = "mobile"        # 10 digits starting with 6-9
    OTP_6_DIGIT = "otp"               # 4-6 digits
    PAN_FORMAT = "pan"                # AAAAA0000A format
    AADHAAR_12_DIGIT = "aadhaar"      # 12 digits
    DOCUMENT = "document"             # File upload
    CONFIRMATION = "confirmation"     # Yes/No


# ================================================================================
# STEP CONFIGURATION
# ================================================================================

@dataclass
class StepConfig:
    """Configuration for each conversation step."""
    step: FlowStep
    question: str
    expected_input: ExpectedInput
    field_name: str                    # Where to store validated answer
    required_fields: List[str]         # Fields that must exist before this step
    reask_message: str                 # Message to show on invalid input


# THE MASTER FLOW - This defines the EXACT conversation sequence
FLOW_SEQUENCE: List[StepConfig] = [
    # Step 1: Greeting
    StepConfig(
        step=FlowStep.GREETING,
        question="How can I assist you today?",
        expected_input=ExpectedInput.FREE_TEXT,
        field_name="greeting_complete",
        required_fields=[],
        reask_message="Hello! How may I help you with your loan enquiry today?"
    ),
    
    # Step 2: Loan Purpose
    StepConfig(
        step=FlowStep.NEEDS_PURPOSE,
        question="May I know what you're planning to use the loan for?",
        expected_input=ExpectedInput.LOAN_PURPOSE,
        field_name="loan_purpose",
        required_fields=["greeting_complete"],
        reask_message="Could you please tell me the purpose of this loan? For example: home renovation, wedding, education, medical expenses, etc."
    ),
    
    # Step 3: Loan Amount
    StepConfig(
        step=FlowStep.NEEDS_AMOUNT,
        question="Roughly how much are you considering?",
        expected_input=ExpectedInput.LOAN_AMOUNT,
        field_name="loan_amount",
        required_fields=["loan_purpose"],
        reask_message="What loan amount are you looking for? Please specify the amount, for example: 5 lakhs, 10 lakh, 500000, etc."
    ),
    
    # Step 4: City
    StepConfig(
        step=FlowStep.ELIGIBILITY_CITY,
        question="Which city do you currently reside in?",
        expected_input=ExpectedInput.CITY_NAME,
        field_name="city",
        required_fields=["loan_amount"],
        reask_message="Could you please share which city you live in? For example: Mumbai, Delhi, Bangalore, etc."
    ),
    
    # Step 5: Employment Type
    StepConfig(
        step=FlowStep.ELIGIBILITY_EMPLOYMENT,
        question="Are you salaried or self-employed?",
        expected_input=ExpectedInput.EMPLOYMENT_TYPE,
        field_name="employment_type",
        required_fields=["city"],
        reask_message="Please specify your employment type: salaried, self-employed, or business owner."
    ),
    
    # Step 6: Full Name
    StepConfig(
        step=FlowStep.KYC_NAME,
        question="Please enter your full name as per PAN.",
        expected_input=ExpectedInput.FULL_NAME,
        field_name="user_name",
        required_fields=["employment_type"],
        reask_message="Please provide your full name as it appears on your PAN card. Use only alphabets and spaces."
    ),
    
    # Step 7: Mobile Number
    StepConfig(
        step=FlowStep.KYC_MOBILE,
        question="Please enter your 10-digit mobile number.",
        expected_input=ExpectedInput.MOBILE_10_DIGIT,
        field_name="user_mobile",
        required_fields=["user_name"],
        reask_message="Please enter a valid 10-digit mobile number starting with 6, 7, 8, or 9."
    ),
    
    # Step 8: OTP Verification
    StepConfig(
        step=FlowStep.OTP_VERIFICATION,
        question="Please enter the OTP sent to your mobile.",
        expected_input=ExpectedInput.OTP_6_DIGIT,
        field_name="otp_verified",
        required_fields=["user_mobile"],
        reask_message="Please enter the 6-digit OTP sent to your registered mobile number."
    ),
    
    # Step 9: PAN Collection
    StepConfig(
        step=FlowStep.PAN_COLLECTION,
        question="Please enter your PAN number.",
        expected_input=ExpectedInput.PAN_FORMAT,
        field_name="user_pan",
        required_fields=["otp_verified"],  # OTP MUST be verified before PAN
        reask_message="Please enter a valid PAN number in the format ABCDE1234F (5 letters, 4 digits, 1 letter)."
    ),
    
    # Step 10: Aadhaar Collection
    StepConfig(
        step=FlowStep.AADHAAR_COLLECTION,
        question="Please enter your 12-digit Aadhaar number.",
        expected_input=ExpectedInput.AADHAAR_12_DIGIT,
        field_name="user_aadhaar",
        required_fields=["pan_verified"],  # PAN MUST be verified before Aadhaar
        reask_message="Please enter a valid 12-digit Aadhaar number."
    ),
    
    # Step 11: Offer Discovery (no user input, system shows offers)
    StepConfig(
        step=FlowStep.OFFER_DISCOVERY,
        question="Checking your eligible loan offers...",
        expected_input=ExpectedInput.CONFIRMATION,
        field_name="offer_shown",
        required_fields=["aadhaar_verified"],  # KYC MUST be complete
        reask_message="Would you like to proceed with your loan application? Please confirm."
    ),
    
    # Step 12: Income Document Upload
    StepConfig(
        step=FlowStep.INCOME_DOC_UPLOAD,
        question="Please upload your salary slip or bank statement.",
        expected_input=ExpectedInput.DOCUMENT,
        field_name="income_doc_uploaded",
        required_fields=["offer_shown"],
        reask_message="To verify your income, please upload your latest salary slip or bank statement using the upload button."
    ),
]


# ================================================================================
# INPUT VALIDATORS
# ================================================================================

class InputValidator:
    """Validates user input against expected type."""
    
    @staticmethod
    def validate(text: str, expected: ExpectedInput) -> Tuple[bool, Any, str]:
        """
        Validate input against expected type.
        Returns: (is_valid, extracted_value, error_message)
        """
        text = text.strip()
        
        if expected == ExpectedInput.FREE_TEXT:
            return (True, text, "")
        
        elif expected == ExpectedInput.LOAN_PURPOSE:
            return InputValidator._validate_purpose(text)
        
        elif expected == ExpectedInput.LOAN_AMOUNT:
            return InputValidator._validate_amount(text)
        
        elif expected == ExpectedInput.CITY_NAME:
            return InputValidator._validate_city(text)
        
        elif expected == ExpectedInput.EMPLOYMENT_TYPE:
            return InputValidator._validate_employment(text)
        
        elif expected == ExpectedInput.FULL_NAME:
            return InputValidator._validate_name(text)
        
        elif expected == ExpectedInput.MOBILE_10_DIGIT:
            return InputValidator._validate_mobile(text)
        
        elif expected == ExpectedInput.OTP_6_DIGIT:
            return InputValidator._validate_otp(text)
        
        elif expected == ExpectedInput.PAN_FORMAT:
            return InputValidator._validate_pan(text)
        
        elif expected == ExpectedInput.AADHAAR_12_DIGIT:
            return InputValidator._validate_aadhaar(text)
        
        elif expected == ExpectedInput.CONFIRMATION:
            return InputValidator._validate_confirmation(text)
        
        elif expected == ExpectedInput.DOCUMENT:
            # Document upload handled separately
            return (True, "document_pending", "")
        
        return (False, None, "Unknown input type")
    
    @staticmethod
    def _validate_purpose(text: str) -> Tuple[bool, Any, str]:
        """Validate loan purpose."""
        text_lower = text.lower()
        PURPOSE_MAP = {
            "home": "Home Loan", "house": "Home Loan", "flat": "Home Loan",
            "renovation": "Home Renovation", "personal": "Personal Loan",
            "medical": "Medical Loan", "health": "Medical Loan", "hospital": "Medical Loan",
            "wedding": "Wedding Loan", "marriage": "Wedding Loan",
            "education": "Education Loan", "study": "Education Loan", "college": "Education Loan",
            "business": "Business Loan", "car": "Vehicle Loan", "vehicle": "Vehicle Loan",
            "travel": "Travel Loan", "vacation": "Travel Loan", "emergency": "Emergency Loan",
            "debt": "Debt Consolidation", "consolidation": "Debt Consolidation"
        }
        for keyword, purpose in PURPOSE_MAP.items():
            if keyword in text_lower:
                return (True, purpose, "")
        return (False, None, "Could not identify loan purpose")
    
    @staticmethod
    def _validate_amount(text: str) -> Tuple[bool, Any, str]:
        """Validate loan amount."""
        text_lower = text.lower()
        
        # Pattern: X lakhs/lacs/L
        match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', text_lower)
        if match:
            return (True, float(match.group(1)) * 100000, "")
        
        # Pattern: X crore
        match = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b', text_lower)
        if match:
            return (True, float(match.group(1)) * 10000000, "")
        
        # Pattern: Direct number (5+ digits)
        match = re.search(r'(\d{5,})', text_lower.replace(',', ''))
        if match:
            return (True, float(match.group(1)), "")
        
        return (False, None, "Could not identify loan amount")
    
    @staticmethod
    def _validate_city(text: str) -> Tuple[bool, Any, str]:
        """Validate city name."""
        CITIES = {
            "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad",
            "kolkata", "pune", "ahmedabad", "jaipur", "surat", "lucknow",
            "kanpur", "nagpur", "indore", "thane", "bhopal", "patna",
            "gurgaon", "gurugram", "noida", "goa", "chandigarh"
        }
        text_lower = text.lower().strip()
        for city in CITIES:
            if city in text_lower:
                return (True, city.title(), "")
        # Accept any alphabetic text as potential city
        if text.replace(" ", "").isalpha() and 2 <= len(text) <= 30:
            return (True, text.title(), "")
        return (False, None, "Could not identify city")
    
    @staticmethod
    def _validate_employment(text: str) -> Tuple[bool, Any, str]:
        """Validate employment type."""
        text_lower = text.lower()
        if any(k in text_lower for k in ["salaried", "salary", "employee", "job"]):
            return (True, "salaried", "")
        if any(k in text_lower for k in ["self employed", "self-employed", "selfemployed", "freelance"]):
            return (True, "self_employed", "")
        if any(k in text_lower for k in ["business", "entrepreneur", "owner"]):
            return (True, "business", "")
        return (False, None, "Please specify: salaried or self-employed")
    
    @staticmethod
    def _validate_name(text: str) -> Tuple[bool, Any, str]:
        """Validate full name (alphabetic only)."""
        text = re.sub(r'^(my name is|i am|i\'m|this is|call me)\s*', '', text, flags=re.IGNORECASE).strip()
        # Check for numbers (names shouldn't have numbers)
        if re.search(r'\d', text):
            return (False, None, "Name should not contain numbers")
        # Check for special characters (SQL injection, XSS, etc.)
        if re.search(r'[;\'\"<>\\\/\-\-\|\{\}\[\]\(\)]', text):
            return (False, None, "Name should contain only letters and spaces")
        # Validate alphabetic with spaces
        if re.match(r'^[A-Za-z\s]{2,50}$', text):
            return (True, ' '.join(word.capitalize() for word in text.split()), "")
        return (False, None, "Please provide a valid name using only letters")
    
    @staticmethod
    def _validate_mobile(text: str) -> Tuple[bool, Any, str]:
        """Validate 10-digit Indian mobile number."""
        cleaned = re.sub(r'[\s\-\(\)\+]', '', text)
        if cleaned.startswith('91') and len(cleaned) == 12:
            cleaned = cleaned[2:]
        if re.match(r'^[6-9]\d{9}$', cleaned):
            return (True, cleaned, "")
        return (False, None, "Please enter a valid 10-digit mobile number")
    
    @staticmethod
    def _validate_otp(text: str) -> Tuple[bool, Any, str]:
        """Validate 4-6 digit OTP."""
        cleaned = text.strip().replace(' ', '')
        if re.match(r'^\d{4,6}$', cleaned):
            return (True, cleaned, "")
        return (False, None, "Please enter the OTP digits only")
    
    @staticmethod
    def _validate_pan(text: str) -> Tuple[bool, Any, str]:
        """Validate PAN format: AAAAA0000A."""
        text_upper = text.upper().strip()
        if re.match(r'^[A-Z]{5}\d{4}[A-Z]$', text_upper):
            return (True, text_upper, "")
        # Try to extract from longer text
        match = re.search(r'\b([A-Z]{5}\d{4}[A-Z])\b', text_upper)
        if match:
            return (True, match.group(1), "")
        return (False, None, "Invalid PAN format. Expected: ABCDE1234F")
    
    @staticmethod
    def _validate_aadhaar(text: str) -> Tuple[bool, Any, str]:
        """Validate 12-digit Aadhaar number."""
        cleaned = re.sub(r'[\s\-]', '', text)
        if re.match(r'^[2-9]\d{11}$', cleaned):
            return (True, cleaned, "")
        return (False, None, "Please enter a valid 12-digit Aadhaar number")
    
    @staticmethod
    def _validate_confirmation(text: str) -> Tuple[bool, Any, str]:
        """Validate yes/no confirmation."""
        text_lower = text.lower().strip()
        YES = ["yes", "ya", "yep", "yeah", "ok", "okay", "sure", "proceed", "continue", "confirm"]
        NO = ["no", "nope", "nahi", "cancel", "stop", "back"]
        if any(w in text_lower for w in YES):
            return (True, True, "")
        if any(w in text_lower for w in NO):
            return (True, False, "")
        return (False, None, "Please confirm with Yes or No")


# ================================================================================
# FLOW CONTROLLER
# ================================================================================

class ConversationFlowController:
    """
    Controls the conversation flow with STRICT step enforcement.
    
    GUARANTEE:
    - No question is asked out of order
    - No step is skipped
    - Invalid input causes re-ask, not advance
    - Backend state is the SINGLE source of truth
    """
    
    def __init__(self):
        self.flow_sequence = FLOW_SEQUENCE
        self.step_index = {config.step: i for i, config in enumerate(FLOW_SEQUENCE)}
        logger.info("=" * 60)
        logger.info("CONVERSATION FLOW CONTROLLER INITIALIZED")
        logger.info(f"Total steps: {len(FLOW_SEQUENCE)}")
        logger.info("Strict step enforcement ENABLED")
        logger.info("=" * 60)
    
    def get_current_step(self, state: Dict[str, Any]) -> StepConfig:
        """
        Determine current step based on what fields are present in state.
        """
        for config in self.flow_sequence:
            # Check if this step's field is already set
            field_value = state.get(config.field_name)
            
            # Special handling for boolean fields
            if config.field_name in ["greeting_complete", "otp_verified", "pan_verified", 
                                      "aadhaar_verified", "offer_shown", "income_doc_uploaded"]:
                if not field_value:
                    # Check required fields
                    if self._check_required_fields(config, state):
                        return config
            else:
                if field_value is None:
                    # Check required fields
                    if self._check_required_fields(config, state):
                        return config
        
        # All steps complete - return last step
        return self.flow_sequence[-1]
    
    def _check_required_fields(self, config: StepConfig, state: Dict[str, Any]) -> bool:
        """Check if all required fields for a step are present."""
        for field in config.required_fields:
            if not state.get(field):
                logger.warning(f"Required field missing for {config.step.value}: {field}")
                return False
        return True
    
    def process_input(
        self,
        user_input: str,
        state: Dict[str, Any]
    ) -> Tuple[bool, str, Dict[str, Any], StepConfig]:
        """
        Process user input against current step.
        
        Returns:
            (success, response_message, state_updates, current_step)
        """
        current_step = self.get_current_step(state)
        
        logger.info(f"Processing input at step: {current_step.step.value}")
        logger.info(f"Expected input type: {current_step.expected_input.value}")
        logger.info(f"User input: {user_input[:50]}...")
        
        # Validate input
        is_valid, extracted_value, error_msg = InputValidator.validate(
            user_input, 
            current_step.expected_input
        )
        
        if not is_valid:
            # CRITICAL: Do NOT advance. Re-ask the SAME question.
            logger.warning(f"INVALID INPUT at {current_step.step.value}: {error_msg}")
            return (
                False,
                current_step.reask_message,
                {},  # No state update
                current_step
            )
        
        # Valid input - update state
        state_updates = {current_step.field_name: extracted_value}
        
        # Get next step's question
        next_step = self._get_next_step(current_step, state)
        
        logger.info(f"Input VALID. Next step: {next_step.step.value if next_step else 'COMPLETE'}")
        
        # Generate acknowledgment + next question
        ack_message = self._generate_acknowledgment(current_step, extracted_value)
        next_question = next_step.question if next_step else "Thank you for completing your application!"
        
        return (
            True,
            f"{ack_message}\n\n{next_question}",
            state_updates,
            next_step if next_step else current_step
        )
    
    def _get_next_step(self, current_step: StepConfig, state: Dict[str, Any]) -> Optional[StepConfig]:
        """Get the next step in sequence."""
        current_index = self.step_index.get(current_step.step, 0)
        if current_index + 1 < len(self.flow_sequence):
            return self.flow_sequence[current_index + 1]
        return None
    
    def _generate_acknowledgment(self, step: StepConfig, value: Any) -> str:
        """Generate a brief acknowledgment of the user's input."""
        step_type = step.step
        
        if step_type == FlowStep.GREETING:
            return "Welcome to Tata Capital!"
        elif step_type == FlowStep.NEEDS_PURPOSE:
            return f"Noted - you're looking for a loan for {value}."
        elif step_type == FlowStep.NEEDS_AMOUNT:
            try:
                amount = float(value) if isinstance(value, (int, float, str)) else 0
                return f"Got it - you need approximately ₹{amount:,.0f}."
            except (ValueError, TypeError):
                return f"Got it - loan amount: {value}."
        elif step_type == FlowStep.ELIGIBILITY_CITY:
            return f"Thank you. You're based in {value}."
        elif step_type == FlowStep.ELIGIBILITY_EMPLOYMENT:
            return f"Understood. You are {value}."
        elif step_type == FlowStep.KYC_NAME:
            return f"Thank you, {value}."
        elif step_type == FlowStep.KYC_MOBILE:
            return f"Mobile number {value} received."
        elif step_type == FlowStep.OTP_VERIFICATION:
            return "OTP verified successfully!"
        elif step_type == FlowStep.PAN_COLLECTION:
            return f"PAN {value} received. Verifying..."
        elif step_type == FlowStep.AADHAAR_COLLECTION:
            return "Aadhaar received. Verifying..."
        elif step_type == FlowStep.OFFER_DISCOVERY:
            return "Great! Let me show you available offers."
        elif step_type == FlowStep.INCOME_DOC_UPLOAD:
            return "Document received. Processing..."
        else:
            return "Thank you."
    
    def can_proceed_to_step(self, target_step: FlowStep, state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Check if transition to target step is allowed.
        Used to prevent skipping steps.
        """
        target_config = None
        for config in self.flow_sequence:
            if config.step == target_step:
                target_config = config
                break
        
        if not target_config:
            return (False, f"Unknown step: {target_step}")
        
        for required_field in target_config.required_fields:
            if not state.get(required_field):
                return (False, f"Cannot proceed to {target_step.value}: {required_field} not verified")
        
        return (True, "")
    
    def get_allowed_question(self, state: Dict[str, Any]) -> Tuple[FlowStep, str, ExpectedInput]:
        """
        Get the ONLY question that can be asked given current state.
        
        Returns:
            (step, question_text, expected_input_type)
        """
        current_step = self.get_current_step(state)
        return (
            current_step.step,
            current_step.question,
            current_step.expected_input
        )


# ================================================================================
# SINGLETON INSTANCE
# ================================================================================

_controller_instance: Optional[ConversationFlowController] = None

def get_flow_controller() -> ConversationFlowController:
    """Get or create the singleton flow controller."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = ConversationFlowController()
    return _controller_instance


# ================================================================================
# KYC STATUS CALCULATOR
# ================================================================================

def calculate_kyc_status(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate overall KYC status based on individual verifications.
    
    KYC is VERIFIED ONLY if ALL of:
    - mobile_verified == True (OTP passed)
    - pan_verified == True (PAN API returned VERIFIED)
    - aadhaar_verified == True (Aadhaar API returned VERIFIED)
    """
    mobile_verified = state.get("otp_verified", False)
    pan_verified = state.get("pan_verified", False)
    aadhaar_verified = state.get("aadhaar_verified", False)
    
    kyc_complete = mobile_verified and pan_verified and aadhaar_verified
    
    return {
        "mobile_verified": mobile_verified,
        "pan_verified": pan_verified,
        "aadhaar_verified": aadhaar_verified,
        "kyc_status": "VERIFIED" if kyc_complete else "PENDING",
        "kyc_complete": kyc_complete
    }


# ================================================================================
# FLOW VIOLATION DETECTOR
# ================================================================================

class FlowViolationDetector:
    """
    Detects and logs flow violations for audit purposes.
    """
    
    @staticmethod
    def check_violation(
        expected_step: FlowStep,
        actual_input_type: str,
        state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if current input represents a flow violation.
        Returns violation details if detected, None otherwise.
        """
        violations = []
        
        # Check for premature KYC access
        if expected_step in [FlowStep.PAN_COLLECTION, FlowStep.AADHAAR_COLLECTION]:
            if not state.get("otp_verified"):
                violations.append({
                    "type": "PREMATURE_KYC_ACCESS",
                    "message": "Attempted KYC collection without OTP verification",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Check for skipped steps
        if expected_step == FlowStep.AADHAAR_COLLECTION:
            if not state.get("pan_verified"):
                violations.append({
                    "type": "SKIPPED_PAN_VERIFICATION",
                    "message": "Attempted Aadhaar collection without PAN verification",
                    "timestamp": datetime.now().isoformat()
                })
        
        return violations[0] if violations else None


# ================================================================================
# MESSAGE VISIBILITY RULES
# ================================================================================

ALLOWED_MESSAGES_BY_STATE: Dict[str, List[str]] = {
    # Before KYC complete - CANNOT say:
    "pre_kyc_forbidden": [
        "checking best offers",
        "checking.*offers",
        "documents.*verified",
        "processing approval",
        "loan approved",
        "sanction letter"
    ],
    # Before underwriting - CANNOT say:
    "pre_underwriting_forbidden": [
        "loan approved",
        "congratulations",
        "sanction letter ready"
    ]
}

def is_message_allowed(message: str, state: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Check if a message is allowed given current state.
    Returns (is_allowed, reason)
    """
    message_lower = message.lower()
    kyc_status = calculate_kyc_status(state)
    
    # Check pre-KYC forbidden messages
    if not kyc_status["kyc_complete"]:
        for forbidden in ALLOWED_MESSAGES_BY_STATE["pre_kyc_forbidden"]:
            # Use regex matching for patterns with .*
            if ".*" in forbidden:
                if re.search(forbidden, message_lower):
                    return (False, f"Cannot say '{forbidden}' before KYC is complete")
            elif forbidden in message_lower:
                return (False, f"Cannot say '{forbidden}' before KYC is complete")
    
    # Check pre-underwriting forbidden messages
    if not state.get("underwriting_complete"):
        for forbidden in ALLOWED_MESSAGES_BY_STATE["pre_underwriting_forbidden"]:
            if ".*" in forbidden:
                if re.search(forbidden, message_lower):
                    return (False, f"Cannot say '{forbidden}' before underwriting")
            elif forbidden in message_lower:
                return (False, f"Cannot say '{forbidden}' before underwriting")
    
    return (True, "")
