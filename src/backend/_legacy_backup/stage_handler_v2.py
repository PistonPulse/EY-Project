"""
================================================================================
PHASE 2 + PHASE 3 + PHASE 4: CONVERSATIONAL STAGE MESSAGE HANDLER
================================================================================

This module routes user messages through the strict stage machine WITH:
- PHASE 2: Proper question sequencing
- PHASE 3: Secure OTP verification for identity locking
- PHASE 4: Deterministic PAN and Aadhaar verification for KYC

================================================================================
PHASE 4: DETERMINISTIC DOCUMENT VERIFICATION (KYC_VERIFICATION)
================================================================================

WHY SEQUENTIAL PAN → AADHAAR VERIFICATION:
   1. PAN establishes financial identity (Income Tax)
   2. Aadhaar establishes physical identity (UIDAI)
   3. Cross-verification prevents identity fraud
   4. Sequential flow catches issues early (no wasted Aadhaar checks)

DETERMINISTIC VERIFICATION PROCESS:
   - TEST_PAN_DATABASE maps PANs to predefined outcomes
   - TEST_AADHAAR_DATABASE maps Aadhaars to predefined outcomes
   - No LLM involvement, no randomness, 100% reproducible
   - Each document has a deterministic result (VERIFIED, NOT_FOUND, etc.)

FAILURE HANDLING:
   - PAN fails → Immediate REJECTION, no Aadhaar collection
   - Aadhaar fails → Immediate REJECTION
   - Both verified → Advance to OFFER_DISCOVERY

================================================================================
PHASE 3: SECURE IDENTITY COLLECTION (KYC_COLLECTION + OTP_VERIFICATION)
================================================================================

WHY OTP PRECEDES KYC VERIFICATION:
   Identity must be LOCKED (verified) before any CRM data is fetched.
   Without OTP verification, an attacker could enter any mobile number
   and harvest sensitive customer data from CRM.

HOW IDENTITY LOCKING PREVENTS FRAUD:
   1. User provides name + mobile → KYC_COLLECTION (data stored, NOT verified)
   2. OTP sent to mobile → OTP_VERIFICATION (only legitimate user receives)
   3. OTP verified → Identity is LOCKED
   4. CRM lookup → KYC_VERIFICATION (ONLY happens after identity lock)

WHY LLM MUST NEVER CONTROL OTP LOGIC:
   LLM is non-deterministic and prompt-injectable.
   OTP verification MUST be deterministic string comparison.
   See otp_security.py for secure implementation.

================================================================================
PHASE 2 KEY IMPROVEMENTS OVER PHASE 1
================================================================================

1. ONE QUESTION AT A TIME
   - Never ask multiple questions in a single message
   - Wait for answer before asking next question
   - Track which questions have been asked/answered

2. PROPER QUESTION SEQUENCE
   - GREETING: Welcome only, don't ask for data
   - NEEDS_DISCOVERY: Purpose FIRST, then Amount
   - BASIC_ELIGIBILITY: City FIRST, then Employment Type
   - KYC_COLLECTION: Name FIRST, then Mobile

3. NATURAL CONVERSATION TONE
   - Friendly, professional NBFC style
   - Acknowledge user's answers
   - Smooth transitions between topics

4. REDIRECT HANDLING
   - Detect irrelevant/off-topic responses
   - Gently redirect back to current question

================================================================================
"""

import re
import random
import string
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import logging

from stage_machine_v2 import (
    Stage,
    StageEvent,
    StageState,
    StageController,
    get_stage_controller,
    get_current_stage,
    request_transition,
    update_session_data,
    get_session_state,
    get_stage_instruction,
    STAGE_INSTRUCTIONS
)

from conversation_prompts import (
    ConversationStep,
    STAGE_QUESTION_SEQUENCE,
    CONVERSATION_PROMPTS,
    REDIRECT_PROMPTS,
    get_prompt,
    get_redirect_prompt,
    extract_loan_purpose,
    extract_city,
    extract_employment_type,
    is_relevant_response,
    format_currency
)

# Phase 3: Import secure OTP module
from otp_security import (
    generate_otp as secure_generate_otp,
    verify_otp as secure_verify_otp,
    can_verify_otp,
    get_remaining_attempts,
    is_otp_verified,
    can_proceed_to_kyc_verification,
    simulate_otp_send,
    MAX_OTP_ATTEMPTS
)

# Phase 4: Import deterministic KYC verification module
from kyc_verification import (
    validate_pan_format,
    verify_pan,
    validate_aadhaar_format,
    verify_aadhaar,
    can_start_kyc_verification,
    extract_pan_from_message,
    extract_aadhaar_from_message,
    VerificationStatus,
    VerificationResult
)

# Phase 5: Import offer discovery module
from offer_discovery import (
    can_start_offer_discovery,
    perform_offer_discovery,
    format_offer_response_for_llm
)

# Phase 6: Import income verification module
from income_verification import (
    can_start_income_verification,
    can_upload_document,
    perform_income_verification,
    format_salary_for_display,
    get_upload_instructions,
    MAX_RETRY_ATTEMPTS
)

# Phase 7: Import underwriting decision engine
from underwriting_decision_engine import (
    validate_entry_conditions as validate_underwriting_entry,
    perform_underwriting,
    has_underwriting_completed,
    get_approval_message,
    get_rejection_message,
    format_currency,
    LoanDecision,
    RejectionReason
)

# Phase 8: Import journey closure service
from journey_closure_service import (
    validate_sanction_entry_conditions,
    validate_rejection_entry_conditions,
    close_journey_with_sanction,
    close_journey_with_rejection,
    get_sanction_state_updates,
    get_rejection_state_updates,
    get_sanction_confirmation_message,
    get_rejection_final_message,
    can_accept_further_input,
    is_journey_closed,
    JourneyStatus
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | HANDLER_V2 | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('stage_handler_v2')


# ================================================================================
# PHASE 3: OTP SECURITY INTEGRATION
# ================================================================================
# OTP generation and verification are handled by otp_security.py
# This ensures:
#   - Deterministic OTP generation (no LLM involvement)
#   - Secure OTP verification (exact string comparison)
#   - Proper attempt tracking and lockout
#
# TEST_USERS_OTP is defined in otp_security.py for demo purposes
# ================================================================================

def generate_otp(mobile: str) -> str:
    """
    Generate OTP for a mobile number using secure module.
    
    CRITICAL: This function delegates to otp_security.secure_generate_otp
    to ensure deterministic, secure OTP generation.
    
    LLM MUST NEVER be involved in OTP generation or verification.
    """
    otp, timestamp = secure_generate_otp(mobile)
    return otp

def extract_mobile_number(message: str) -> Optional[str]:
    """Extract a 10-digit Indian mobile number from user message."""
    cleaned = re.sub(r'[\s\-\(\)\+]', '', message)
    
    patterns = [
        r'(?:91)?([6-9]\d{9})\b',
        r'\b([6-9]\d{9})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)
    
    return None


def extract_loan_amount(message: str) -> Optional[float]:
    """Extract loan amount from user message."""
    message_lower = message.lower()
    
    # Pattern: X lakhs/lacs/L
    lakh_pattern = r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b'
    match = re.search(lakh_pattern, message_lower)
    if match:
        return float(match.group(1)) * 100000
    
    # Pattern: X crore
    crore_pattern = r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b'
    match = re.search(crore_pattern, message_lower)
    if match:
        return float(match.group(1)) * 10000000
    
    # Pattern: Direct number (5+ digits)
    number_pattern = r'(?:rs\.?\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})|\d{5,})(?:\s*(?:rupees|rs|inr))?'
    match = re.search(number_pattern, message_lower)
    if match:
        amount_str = match.group(1).replace(',', '')
        amount = float(amount_str)
        if amount >= 10000:
            return amount
    
    return None


def extract_name(message: str) -> Optional[str]:
    """Extract user's name from message."""
    NOT_NAMES = {
        'hello', 'hi', 'hey', 'good', 'morning', 'afternoon', 'evening',
        'yes', 'no', 'ok', 'okay', 'sure', 'thanks', 'thank',
        'loan', 'money', 'amount', 'home', 'personal', 'business',
        'i', 'me', 'my', 'you', 'your', 'the', 'a', 'an'
    }
    
    patterns = [
        r"(?:i'?m|i am|my name is|this is|call me)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:here|speaking)",
        r"(?:name|naam)\s*(?:is|hai|:)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            if name.lower() not in NOT_NAMES:
                return ' '.join(word.capitalize() for word in name.split())
    
    # Fallback: If the message looks like just a name (2-3 capitalized words)
    words = message.strip().split()
    if 1 <= len(words) <= 3:
        all_names = all(
            word[0].isupper() and word.lower() not in NOT_NAMES
            for word in words if len(word) > 1
        )
        if all_names:
            return ' '.join(word.capitalize() for word in words)
    
    return None


def extract_otp(message: str) -> Optional[str]:
    """Extract OTP from user message."""
    message = message.strip()
    
    # Just digits
    if re.match(r'^\d{4,6}$', message):
        return message
    
    # "OTP is X" patterns
    patterns = [
        r'(?:otp|code|verification)\s*(?:is|:)?\s*(\d{4,6})',
        r'(\d{4,6})\s*(?:is|:)?\s*(?:the\s*)?(?:otp|code)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Any 4-6 digit number
    numbers = re.findall(r'\b(\d{4,6})\b', message)
    if len(numbers) == 1:
        return numbers[0]
    
    return None


def is_greeting(message: str) -> bool:
    """Check if message is a greeting."""
    greetings = [
        'hi', 'hello', 'hey', 'good morning', 'good afternoon',
        'good evening', 'namaste', 'hola', 'greetings'
    ]
    message_lower = message.lower().strip()
    return any(g in message_lower for g in greetings)


def is_affirmative(message: str) -> bool:
    """Check if message is affirmative."""
    affirmatives = [
        'yes', 'yep', 'yeah', 'ya', 'yup', 'ok', 'okay', 'sure',
        'proceed', 'continue', 'confirm', 'agree', 'haan', 'ji'
    ]
    message_lower = message.lower().strip()
    return message_lower in affirmatives or any(a in message_lower for a in ['yes', 'ok', 'sure', 'proceed'])


# ================================================================================
# PHASE 2 + PHASE 3: CONVERSATIONAL STAGE MESSAGE HANDLER
# ================================================================================

class ConversationalStageHandler:
    """
    Handles user messages with PROPER question sequencing.
    
    ================================================================================
    PHASE 2 CONVERSATION FLOW
    ================================================================================
    
    GREETING STAGE:
    → Bot: "Hi! Welcome to Tata Capital..."
    → User: "Hi" / "Hello" / anything
    → Transition to NEEDS_DISCOVERY
    
    NEEDS_DISCOVERY STAGE:
    → Bot: "What would you like to use the loan for?"
    → User: "Home renovation"
    → Bot: "And roughly how much are you considering?"
    → User: "5 lakhs"
    → Transition to BASIC_ELIGIBILITY
    
    BASIC_ELIGIBILITY STAGE:
    → Bot: "Which city do you currently live in?"
    → User: "Mumbai"
    → Bot: "Are you salaried or self-employed?"
    → User: "Salaried"
    → Transition to KYC_COLLECTION
    
    KYC_COLLECTION STAGE:
    → Bot: "Could you please share your full name?"
    → User: "Rahul Sharma"
    → Bot: "And your 10-digit mobile number for verification?"
    → User: "9876543210"
    → Transition to OTP_VERIFICATION
    
    ================================================================================
    """
    
    def __init__(self, backend_services=None):
        """Initialize the handler."""
        self.controller = get_stage_controller()
        self.backend_services = backend_services
        
        logger.info("=" * 60)
        logger.info("PHASE 2: CONVERSATIONAL STAGE HANDLER INITIALIZED")
        logger.info("Question sequencing enabled")
        logger.info("=" * 60)
    
    def _get_context(self, state: StageState) -> Dict[str, Any]:
        """Build context dictionary for prompt formatting."""
        return {
            "loan_amount": state.loan_amount,
            "loan_purpose": state.loan_purpose,
            "user_name": state.user_name,
            "user_mobile": state.user_mobile,
            "city": state.city,
            "employment_type": state.employment_type,
            "otp_attempts": state.otp_attempts,
            "rejection_reason": state.rejection_reason,
        }
    
    def _mark_step_asked(self, session_id: str, step: ConversationStep):
        """Mark a conversation step as asked."""
        state = self.controller.get_or_create_session(session_id)
        if step.value not in state.questions_asked:
            state.questions_asked.append(step.value)
            state.conversation_step = step.value
            update_session_data(session_id, {
                "questions_asked": state.questions_asked,
                "conversation_step": step.value
            })
    
    def _mark_step_answered(self, session_id: str, step: ConversationStep):
        """Mark a conversation step as answered."""
        state = self.controller.get_or_create_session(session_id)
        if step.value not in state.questions_answered:
            state.questions_answered.append(step.value)
            update_session_data(session_id, {
                "questions_answered": state.questions_answered
            })
    
    def _was_asked(self, state: StageState, step: ConversationStep) -> bool:
        """Check if a question was already asked."""
        return step.value in state.questions_asked
    
    def _was_answered(self, state: StageState, step: ConversationStep) -> bool:
        """Check if a question was already answered."""
        return step.value in state.questions_answered
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        has_uploaded_docs: bool = False,
        documents_verified: bool = False,
        is_initial: bool = False
    ) -> Dict[str, Any]:
        """
        Process a user message with proper question sequencing.
        
        Args:
            session_id: Session identifier
            user_message: User's message
            has_uploaded_docs: Whether documents were uploaded
            documents_verified: Whether documents were verified
            is_initial: Whether this is the initial message (for greeting)
        
        Returns:
            Dict with stage info, response prompt, and context
        """
        logger.info("=" * 60)
        logger.info(f"PROCESSING MESSAGE (Phase 2)")
        logger.info(f"  Session: {session_id}")
        logger.info(f"  Message: {user_message[:50]}...")
        
        # Get current state
        state = self.controller.get_or_create_session(session_id)
        previous_stage = state.current_stage
        
        logger.info(f"  Current Stage: {previous_stage.value}")
        logger.info(f"  Conversation Step: {state.conversation_step}")
        
        # Process based on current stage with question sequencing
        result = self._process_for_stage(
            session_id=session_id,
            state=state,
            user_message=user_message,
            has_uploaded_docs=has_uploaded_docs,
            documents_verified=documents_verified,
            is_initial=is_initial
        )
        
        # Get updated state
        updated_state = self.controller.get_or_create_session(session_id)
        new_stage = updated_state.current_stage
        stage_changed = previous_stage != new_stage
        
        if stage_changed:
            logger.info(f"  Stage CHANGED: {previous_stage.value} → {new_stage.value}")
        else:
            logger.info(f"  Stage UNCHANGED: {new_stage.value}")
        
        logger.info(f"  Response: {result.get('bot_response', '')[:50]}...")
        logger.info("=" * 60)
        
        return {
            "session_id": session_id,
            "previous_stage": previous_stage.value,
            "current_stage": new_stage.value,
            "stage_changed": stage_changed,
            "stage_instruction": get_stage_instruction(new_stage),
            "state_data": updated_state.to_dict(),
            "transition_result": result.get("transition_result"),
            "show_upload": new_stage == Stage.INCOME_DOC_UPLOAD,
            "show_sanction_letter": new_stage == Stage.SANCTION and (updated_state.sanction_letter_generated or updated_state.sanction_reference),
            # Phase 8: Sanction letter download info
            "sanction_letter_path": updated_state.sanction_letter_path,
            "sanction_letter_reference": updated_state.sanction_letter_reference or updated_state.sanction_reference,
            "sanction_letter_generated": updated_state.sanction_letter_generated,
            # Phase 8: Journey closure info
            "journey_completed": updated_state.journey_completed,
            "session_closed": updated_state.session_closed,
            "closure_reason": updated_state.closure_reason,
            "extracted_data": result.get("extracted_data", {}),
            "otp_code": updated_state.otp_code if new_stage == Stage.OTP_VERIFICATION else None,
            # Phase 2 additions
            "bot_response": result.get("bot_response", ""),
            "conversation_step": updated_state.conversation_step,
            "next_question_step": result.get("next_question_step"),
        }
    
    def _process_for_stage(
        self,
        session_id: str,
        state: StageState,
        user_message: str,
        has_uploaded_docs: bool = False,
        documents_verified: bool = False,
        is_initial: bool = False
    ) -> Dict[str, Any]:
        """
        Process message with PROPER question sequencing per Phase 2 spec.
        """
        current = state.current_stage
        extracted_data = {}
        transition_result = None
        bot_response = ""
        next_question_step = None
        context = self._get_context(state)
        
        # =====================================================================
        # GREETING STAGE
        # =====================================================================
        # Rule: Welcome only. Do NOT ask for loan amount here.
        # AFTER greeting, immediately ask the first question of NEEDS_DISCOVERY.
        # =====================================================================
        if current == Stage.GREETING:
            # Generate welcome message
            welcome_msg = get_prompt(ConversationStep.GREETING_WELCOME, context)
            self._mark_step_asked(session_id, ConversationStep.GREETING_WELCOME)
            
            # Transition immediately to NEEDS_DISCOVERY
            success, new_stage, msg = request_transition(
                session_id,
                StageEvent.USER_GREETED
            )
            transition_result = {"success": success, "message": msg}
            
            # After greeting, immediately ask the first question of NEEDS_DISCOVERY
            # This creates a natural flow: "Hi! ... What would you like to use the loan for?"
            purpose_question = get_prompt(ConversationStep.NEEDS_ASK_PURPOSE, context)
            self._mark_step_asked(session_id, ConversationStep.NEEDS_ASK_PURPOSE)
            
            # Combine welcome + first question
            bot_response = f"{welcome_msg} {purpose_question}"
            next_question_step = ConversationStep.NEEDS_ASK_PURPOSE.value
        
        # =====================================================================
        # NEEDS_DISCOVERY STAGE
        # =====================================================================
        # Sequence: PURPOSE first → AMOUNT second → Confirm
        # =====================================================================
        elif current == Stage.NEEDS_DISCOVERY:
            current_step = ConversationStep(state.conversation_step) if state.conversation_step else None
            
            # STEP 1: Ask for PURPOSE (if not asked yet)
            if not self._was_asked(state, ConversationStep.NEEDS_ASK_PURPOSE):
                bot_response = get_prompt(ConversationStep.NEEDS_ASK_PURPOSE, context)
                self._mark_step_asked(session_id, ConversationStep.NEEDS_ASK_PURPOSE)
                next_question_step = ConversationStep.NEEDS_ASK_PURPOSE.value
            
            # STEP 2: Process PURPOSE answer, then ask for AMOUNT
            elif not self._was_answered(state, ConversationStep.NEEDS_ASK_PURPOSE):
                # Try to extract purpose from user message
                purpose = extract_loan_purpose(user_message)
                if purpose:
                    extracted_data["loan_purpose"] = purpose
                    update_session_data(session_id, {"loan_purpose": purpose})
                    self._mark_step_answered(session_id, ConversationStep.NEEDS_ASK_PURPOSE)
                    context["loan_purpose"] = purpose
                    
                    # Now ask for amount
                    bot_response = get_prompt(ConversationStep.NEEDS_ASK_AMOUNT, context)
                    self._mark_step_asked(session_id, ConversationStep.NEEDS_ASK_AMOUNT)
                    next_question_step = ConversationStep.NEEDS_ASK_AMOUNT.value
                else:
                    # Redirect - didn't get purpose
                    bot_response = get_redirect_prompt("NEEDS_DISCOVERY")
                    next_question_step = ConversationStep.NEEDS_ASK_PURPOSE.value
            
            # STEP 3: Process AMOUNT answer
            elif not self._was_answered(state, ConversationStep.NEEDS_ASK_AMOUNT):
                # Try to extract amount from user message
                amount = extract_loan_amount(user_message)
                if amount:
                    extracted_data["loan_amount"] = amount
                    update_session_data(session_id, {"loan_amount": amount})
                    self._mark_step_answered(session_id, ConversationStep.NEEDS_ASK_AMOUNT)
                    context["loan_amount"] = amount
                    
                    # Confirm and transition
                    confirm_msg = get_prompt(ConversationStep.NEEDS_CONFIRM, context)
                    self._mark_step_asked(session_id, ConversationStep.NEEDS_CONFIRM)
                    self._mark_step_answered(session_id, ConversationStep.NEEDS_CONFIRM)
                    
                    # Transition: NEEDS_DISCOVERY → BASIC_ELIGIBILITY
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.LOAN_AMOUNT_PROVIDED,
                        {"loan_amount": amount}
                    )
                    transition_result = {"success": success, "message": msg}
                    
                    # After confirming, ask the first question of BASIC_ELIGIBILITY
                    city_question = get_prompt(ConversationStep.ELIGIBILITY_ASK_CITY, context)
                    self._mark_step_asked(session_id, ConversationStep.ELIGIBILITY_ASK_CITY)
                    
                    # Combine confirmation + next question
                    bot_response = f"{confirm_msg} {city_question}"
                    next_question_step = ConversationStep.ELIGIBILITY_ASK_CITY.value
                else:
                    # Redirect - didn't get amount
                    bot_response = "I didn't quite catch that. What amount are you looking for?"
                    next_question_step = ConversationStep.NEEDS_ASK_AMOUNT.value
            
            if not transition_result:
                transition_result = {"success": False, "message": "Gathering needs information"}
        
        # =====================================================================
        # BASIC_ELIGIBILITY STAGE  
        # =====================================================================
        # Sequence: CITY first → EMPLOYMENT TYPE second → Confirm eligibility
        # =====================================================================
        elif current == Stage.BASIC_ELIGIBILITY:
            current_step = ConversationStep(state.conversation_step) if state.conversation_step else None
            
            # STEP 1: Ask for CITY (if not asked yet)
            if not self._was_asked(state, ConversationStep.ELIGIBILITY_ASK_CITY):
                bot_response = get_prompt(ConversationStep.ELIGIBILITY_ASK_CITY, context)
                self._mark_step_asked(session_id, ConversationStep.ELIGIBILITY_ASK_CITY)
                next_question_step = ConversationStep.ELIGIBILITY_ASK_CITY.value
            
            # STEP 2: Process CITY answer, then ask for EMPLOYMENT TYPE
            elif not self._was_answered(state, ConversationStep.ELIGIBILITY_ASK_CITY):
                # Try to extract city
                city = extract_city(user_message)
                if city or len(user_message.strip()) > 2:
                    city = city or user_message.strip().title()
                    extracted_data["city"] = city
                    update_session_data(session_id, {"city": city})
                    self._mark_step_answered(session_id, ConversationStep.ELIGIBILITY_ASK_CITY)
                    context["city"] = city
                    
                    # Now ask for employment type
                    bot_response = get_prompt(ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT, context)
                    self._mark_step_asked(session_id, ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT)
                    next_question_step = ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT.value
                else:
                    # Redirect
                    bot_response = get_redirect_prompt("BASIC_ELIGIBILITY")
                    next_question_step = ConversationStep.ELIGIBILITY_ASK_CITY.value
            
            # STEP 3: Process EMPLOYMENT TYPE answer
            elif not self._was_answered(state, ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT):
                # Try to extract employment type
                emp_type = extract_employment_type(user_message)
                if emp_type:
                    extracted_data["employment_type"] = emp_type
                    update_session_data(session_id, {"employment_type": emp_type})
                    self._mark_step_answered(session_id, ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT)
                    context["employment_type"] = emp_type
                    
                    # Confirm eligibility and transition
                    confirm_msg = get_prompt(ConversationStep.ELIGIBILITY_CONFIRM, context)
                    self._mark_step_asked(session_id, ConversationStep.ELIGIBILITY_CONFIRM)
                    self._mark_step_answered(session_id, ConversationStep.ELIGIBILITY_CONFIRM)
                    
                    # Transition: BASIC_ELIGIBILITY → KYC_COLLECTION
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.ELIGIBILITY_CHECKED
                    )
                    transition_result = {"success": success, "message": msg}
                    
                    # After confirming eligibility, ask for name
                    name_question = get_prompt(ConversationStep.KYC_ASK_NAME, context)
                    self._mark_step_asked(session_id, ConversationStep.KYC_ASK_NAME)
                    
                    # Combine confirmation + next question
                    bot_response = f"{confirm_msg} {name_question}"
                    next_question_step = ConversationStep.KYC_ASK_NAME.value
                else:
                    # Redirect
                    bot_response = "Please specify if you are salaried or self-employed."
                    next_question_step = ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT.value
            
            if not transition_result:
                transition_result = {"success": False, "message": "Checking eligibility"}
        
        # =====================================================================
        # KYC_COLLECTION STAGE
        # =====================================================================
        # Sequence: NAME first → MOBILE second
        # =====================================================================
        elif current == Stage.KYC_COLLECTION:
            current_step = ConversationStep(state.conversation_step) if state.conversation_step else None
            
            # STEP 1: Ask for NAME (if not asked yet)
            if not self._was_asked(state, ConversationStep.KYC_ASK_NAME):
                bot_response = get_prompt(ConversationStep.KYC_ASK_NAME, context)
                self._mark_step_asked(session_id, ConversationStep.KYC_ASK_NAME)
                next_question_step = ConversationStep.KYC_ASK_NAME.value
            
            # STEP 2: Process NAME answer, then ask for MOBILE
            elif not self._was_answered(state, ConversationStep.KYC_ASK_NAME):
                # Try to extract name
                name = extract_name(user_message)
                if name or (len(user_message.strip()) > 2 and user_message.strip()[0].isupper()):
                    name = name or user_message.strip().title()
                    extracted_data["user_name"] = name
                    update_session_data(session_id, {"user_name": name})
                    self._mark_step_answered(session_id, ConversationStep.KYC_ASK_NAME)
                    context["user_name"] = name
                    
                    # Now ask for mobile
                    bot_response = get_prompt(ConversationStep.KYC_ASK_MOBILE, context)
                    self._mark_step_asked(session_id, ConversationStep.KYC_ASK_MOBILE)
                    next_question_step = ConversationStep.KYC_ASK_MOBILE.value
                else:
                    # Redirect
                    bot_response = get_redirect_prompt("KYC_COLLECTION")
                    next_question_step = ConversationStep.KYC_ASK_NAME.value
            
            # STEP 3: Process MOBILE answer
            # =========================================================================
            # PHASE 3: IDENTITY COLLECTION (NOT VERIFICATION)
            # =========================================================================
            # At this point we ONLY collect identity information.
            # We do NOT validate format strictly, do NOT fetch any APIs.
            # OTP is generated and sent, but identity is NOT verified yet.
            # =========================================================================
            elif not self._was_answered(state, ConversationStep.KYC_ASK_MOBILE):
                # Try to extract mobile
                mobile = extract_mobile_number(user_message)
                if mobile:
                    extracted_data["user_mobile"] = mobile
                    
                    # =========================================================
                    # PHASE 3: SECURE OTP GENERATION
                    # =========================================================
                    # OTP is generated DETERMINISTICALLY using otp_security.py
                    # LLM is NOT involved in OTP generation or verification.
                    # This prevents prompt injection attacks.
                    # =========================================================
                    otp, otp_timestamp = secure_generate_otp(mobile)
                    
                    # Store identity data + OTP info (NOT verified yet)
                    update_session_data(session_id, {
                        "user_mobile": mobile,
                        "otp_code": otp,
                        "otp_generation_timestamp": otp_timestamp,
                        "otp_sent": True,
                        "otp_verified": False,  # CRITICAL: Not verified yet
                        "otp_attempts": 0  # Reset attempts for new OTP
                    })
                    extracted_data["otp_code"] = otp
                    self._mark_step_answered(session_id, ConversationStep.KYC_ASK_MOBILE)
                    context["user_mobile"] = mobile
                    
                    # Log OTP generation (for demo/testing ONLY)
                    logger.info(f"PHASE 3: OTP Generated: {otp} for {mobile} at {otp_timestamp}")
                    
                    # Simulate OTP send (would be SMS gateway in production)
                    send_status = simulate_otp_send(mobile, otp)
                    logger.info(f"PHASE 3: {send_status}")
                    
                    # Transition: KYC_COLLECTION → OTP_VERIFICATION
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.KYC_INFO_PROVIDED,
                        {
                            "user_mobile": mobile,
                            "otp_code": otp,
                            "otp_generation_timestamp": otp_timestamp,
                            "otp_sent": True,
                            "otp_verified": False
                        }
                    )
                    transition_result = {"success": success, "message": msg}
                    
                    # Show "Sending OTP..." then ask for OTP
                    bot_response = f"Sending OTP... {get_prompt(ConversationStep.OTP_SENT, context)}"
                    self._mark_step_asked(session_id, ConversationStep.OTP_SENT)
                    next_question_step = ConversationStep.OTP_SENT.value
                else:
                    # Redirect
                    bot_response = "Please enter a valid 10-digit mobile number."
                    next_question_step = ConversationStep.KYC_ASK_MOBILE.value
            
            if not transition_result:
                transition_result = {"success": False, "message": "Collecting KYC information"}
        
        # =====================================================================
        # OTP_VERIFICATION STAGE
        # =====================================================================
        # PHASE 3: SECURE OTP VERIFICATION
        # =====================================================================
        # PURPOSE: Verify control over mobile number before ANY data fetch.
        #
        # SECURITY RULES (NON-NEGOTIABLE):
        #   1. OTP verification is DETERMINISTIC (exact string match)
        #   2. LLM is NOT involved in verification decision
        #   3. Max 3 attempts before lockout
        #   4. Page refresh does NOT auto-verify OTP
        #   5. KYC_VERIFICATION is ONLY reachable after otp_verified = True
        #
        # This prevents:
        #   - Attackers harvesting CRM data with fake mobile numbers
        #   - Session hijacking attacks
        #   - Prompt injection to bypass verification
        # =====================================================================
        elif current == Stage.OTP_VERIFICATION:
            # =========================================================
            # PHASE 3: CHECK IF OTP VERIFICATION IS STILL ALLOWED
            # =========================================================
            current_attempts = state.otp_attempts
            
            # Check if already locked out
            if not can_verify_otp(current_attempts):
                logger.warning(f"PHASE 3: OTP locked out - {current_attempts} failed attempts")
                
                # Reset OTP state and go back to KYC collection
                update_session_data(session_id, {
                    "otp_sent": False,
                    "otp_code": None,
                    "otp_generation_timestamp": None,
                    "otp_attempts": 0,
                    "otp_verified": False
                })
                
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.OTP_FAILED
                )
                transition_result = {"success": success, "message": "OTP verification locked out"}
                bot_response = "You've exceeded the maximum number of OTP attempts. Please provide your mobile number again and we'll send a new OTP."
                next_question_step = ConversationStep.KYC_ASK_MOBILE.value
            else:
                # Extract OTP from user message
                entered_otp = extract_otp(user_message)
                
                if entered_otp:
                    # =========================================================
                    # PHASE 3: SECURE OTP VERIFICATION
                    # =========================================================
                    # This uses otp_security.secure_verify_otp which:
                    #   - Performs EXACT string comparison
                    #   - Tracks attempt count
                    #   - Returns deterministic result
                    #   - LLM has NO role in this decision
                    # =========================================================
                    stored_otp = state.otp_code
                    is_verified, verify_message, new_attempts = secure_verify_otp(
                        entered_otp=entered_otp,
                        stored_otp=stored_otp,
                        current_attempts=current_attempts
                    )
                    
                    if is_verified:
                        # =====================================================
                        # SUCCESS: Identity is now LOCKED
                        # =====================================================
                        # Only NOW can we proceed to KYC_VERIFICATION
                        # CRM lookup is ONLY allowed after this point
                        # =====================================================
                        update_session_data(session_id, {"otp_verified": True})
                        self._mark_step_answered(session_id, ConversationStep.OTP_SENT)
                        
                        logger.info(f"PHASE 3: OTP Verified Successfully! Identity LOCKED.")
                        
                        # Transition: OTP_VERIFICATION → KYC_VERIFICATION
                        success, new_stage, msg = request_transition(
                            session_id,
                            StageEvent.OTP_VERIFIED,
                            {"otp_verified": True}
                        )
                        transition_result = {"success": success, "message": msg}
                        
                        bot_response = get_prompt(ConversationStep.KYC_VERIFYING, context)
                        next_question_step = ConversationStep.KYC_VERIFYING.value
                    else:
                        # =====================================================
                        # FAILURE: OTP incorrect
                        # =====================================================
                        update_session_data(session_id, {"otp_attempts": new_attempts})
                        
                        remaining = get_remaining_attempts(new_attempts)
                        logger.warning(f"PHASE 3: Wrong OTP (attempt {new_attempts}/{MAX_OTP_ATTEMPTS}, {remaining} remaining)")
                        
                        if remaining == 0:
                            # Lockout - go back to KYC collection
                            update_session_data(session_id, {
                                "otp_sent": False,
                                "otp_code": None,
                                "otp_generation_timestamp": None,
                                "otp_attempts": 0,
                                "otp_verified": False
                            })
                            
                            success, new_stage, msg = request_transition(
                                session_id,
                                StageEvent.OTP_FAILED
                            )
                            transition_result = {"success": success, "message": "Too many OTP attempts"}
                            bot_response = "You've exceeded the maximum number of OTP attempts. Please provide your mobile number again and we'll send a new OTP."
                            next_question_step = ConversationStep.KYC_ASK_MOBILE.value
                        else:
                            transition_result = {"success": False, "message": f"Wrong OTP, {remaining} attempts remaining"}
                            context["otp_attempts"] = new_attempts
                            bot_response = f"That OTP doesn't match. You have {remaining} attempt(s) remaining. Please try again."
                            next_question_step = ConversationStep.OTP_RETRY.value
                else:
                    # No OTP in message - ask again
                    transition_result = {"success": False, "message": "Waiting for OTP"}
                    bot_response = get_redirect_prompt("OTP_VERIFICATION")
                    next_question_step = ConversationStep.OTP_SENT.value
        
        # =====================================================================
        # KYC_VERIFICATION STAGE
        # =====================================================================
        # PHASE 4: DETERMINISTIC PAN AND AADHAAR VERIFICATION
        # =====================================================================
        # 
        # VERIFICATION SEQUENCE (STRICT ORDER):
        #   1. Check entry conditions (OTP verified, name, mobile)
        #   2. Ask for PAN number → Verify PAN → Show result
        #   3. Ask for Aadhaar number → Verify Aadhaar → Show result
        #   4. Both verified → Advance to OFFER_DISCOVERY
        #   5. Either fails → Set REJECTED, advance to REJECTION
        #
        # DETERMINISTIC RESPONSES:
        #   - TEST_PAN_DATABASE in kyc_verification.py maps PANs to results
        #   - TEST_AADHAAR_DATABASE maps Aadhaars to results
        #   - No LLM decision-making, no randomness
        #
        # GATING RULES (NON-NEGOTIABLE):
        #   - OTP must be verified BEFORE entering this stage
        #   - PAN must be verified BEFORE asking for Aadhaar
        #   - Failure at any point → Immediate rejection
        #
        # =====================================================================
        elif current == Stage.KYC_VERIFICATION:
            # =========================================================
            # Step 0: VERIFY ENTRY CONDITIONS (Defense-in-depth)
            # =========================================================
            can_proceed, gate_reason = can_start_kyc_verification(
                otp_verified=state.otp_verified,
                full_name=state.user_name,
                mobile_number=state.user_mobile
            )
            
            if not can_proceed:
                # This should NEVER happen if stage machine is working correctly
                # But we check anyway as defense-in-depth
                logger.error(f"PHASE 4 SECURITY VIOLATION: KYC_VERIFICATION entry denied! Reason: {gate_reason}")
                
                # Force back to appropriate stage
                if not state.otp_verified:
                    bot_response = "For security, we need to verify your mobile number first. Please enter the OTP sent to your phone."
                    next_question_step = ConversationStep.OTP_SENT.value
                else:
                    bot_response = "Please provide your name to continue."
                    next_question_step = ConversationStep.KYC_ASK_NAME.value
                transition_result = {"success": False, "message": f"Security gate: {gate_reason}"}
            else:
                # Entry conditions met - determine current sub-step
                current_step = state.conversation_step
                pan_verified = state.pan_verified or False
                aadhaar_verified = state.aadhaar_verified or False
                
                logger.info(f"PHASE 4: KYC_VERIFICATION - step={current_step}, pan_verified={pan_verified}, aadhaar_verified={aadhaar_verified}")
                
                # =========================================================
                # Step 1: ASK FOR PAN (if not yet verified)
                # =========================================================
                if not pan_verified and current_step != ConversationStep.KYC_PAN_VERIFYING.value:
                    # Check if message contains a PAN
                    extracted_pan = extract_pan_from_message(user_message)
                    
                    if extracted_pan:
                        # Validate PAN format
                        is_valid_format, format_error = validate_pan_format(extracted_pan)
                        
                        if not is_valid_format:
                            logger.warning(f"PHASE 4: Invalid PAN format: {format_error}")
                            transition_result = {"success": False, "message": format_error}
                            bot_response = f"That doesn't look like a valid PAN number. {format_error} Please enter a valid 10-character PAN (e.g., ABCDE1234F)."
                            next_question_step = ConversationStep.KYC_ASK_PAN.value
                        else:
                            # Store PAN and show verifying message
                            update_session_data(session_id, {
                                "user_pan": extracted_pan.upper(),
                                "conversation_step": ConversationStep.KYC_PAN_VERIFYING.value
                            })
                            
                            transition_result = {"success": True, "message": "PAN received, verifying..."}
                            bot_response = get_prompt(ConversationStep.KYC_PAN_VERIFYING, context)
                            next_question_step = ConversationStep.KYC_PAN_VERIFYING.value
                    else:
                        # No PAN in message - ask for it
                        if current_step is None or current_step == ConversationStep.KYC_VERIFYING.value:
                            # First entry into this stage - ask for PAN
                            update_session_data(session_id, {
                                "conversation_step": ConversationStep.KYC_ASK_PAN.value
                            })
                        
                        transition_result = {"success": False, "message": "Waiting for PAN"}
                        bot_response = get_prompt(ConversationStep.KYC_ASK_PAN, context)
                        next_question_step = ConversationStep.KYC_ASK_PAN.value
                
                # =========================================================
                # Step 2: VERIFY PAN (deterministic check)
                # =========================================================
                elif not pan_verified and current_step == ConversationStep.KYC_PAN_VERIFYING.value:
                    # Perform deterministic PAN verification
                    pan_to_verify = state.user_pan
                    
                    if not pan_to_verify:
                        logger.error("PHASE 4: PAN_VERIFYING step reached without PAN stored!")
                        transition_result = {"success": False, "message": "PAN not found"}
                        bot_response = "Please provide your PAN number."
                        next_question_step = ConversationStep.KYC_ASK_PAN.value
                    else:
                        # Call deterministic verification
                        pan_result = verify_pan(pan_to_verify, state.user_name)
                        timestamp = datetime.now().isoformat()
                        
                        logger.info(f"PHASE 4: PAN verification result: {pan_result.status} for {pan_to_verify}")
                        
                        if pan_result.status == VerificationStatus.VERIFIED:
                            # PAN verified successfully
                            update_session_data(session_id, {
                                "pan_verified": True,
                                "pan_verification_timestamp": timestamp,
                                "conversation_step": ConversationStep.KYC_ASK_AADHAAR.value
                            })
                            
                            transition_result = {"success": True, "message": "PAN verified"}
                            context["pan_number"] = pan_to_verify
                            bot_response = f"✓ PAN verified successfully! Your PAN {pan_to_verify} is linked to {state.user_name}.\n\nNow, please provide your 12-digit Aadhaar number for final identity verification."
                            next_question_step = ConversationStep.KYC_ASK_AADHAAR.value
                        else:
                            # PAN verification failed - REJECT
                            failure_reason = pan_result.error_message or "PAN could not be verified"
                            
                            update_session_data(session_id, {
                                "pan_verified": False,
                                "pan_verification_timestamp": timestamp,
                                "kyc_status": "REJECTED",
                                "loan_status": "REJECTED",
                                "rejection_reason": f"PAN verification failed: {failure_reason}"
                            })
                            
                            # Transition to REJECTION stage
                            success, new_stage, msg = request_transition(
                                session_id,
                                StageEvent.KYC_FAILED,
                                {"rejection_reason": f"PAN verification failed: {failure_reason}"}
                            )
                            
                            transition_result = {"success": False, "message": "PAN verification failed"}
                            context["failure_reason"] = failure_reason
                            context["rejection_reason"] = f"We were unable to verify your PAN number. {failure_reason}"
                            bot_response = get_prompt(ConversationStep.KYC_PAN_FAILED, context) + "\n\n" + get_prompt(ConversationStep.REJECTION_COMPLETE, context)
                            next_question_step = ConversationStep.REJECTION_COMPLETE.value
                
                # =========================================================
                # Step 3: ASK FOR AADHAAR (after PAN verified)
                # =========================================================
                elif pan_verified and not aadhaar_verified and current_step != ConversationStep.KYC_AADHAAR_VERIFYING.value:
                    # Check if message contains an Aadhaar
                    extracted_aadhaar = extract_aadhaar_from_message(user_message)
                    
                    if extracted_aadhaar:
                        # Validate Aadhaar format
                        is_valid_format, format_error = validate_aadhaar_format(extracted_aadhaar)
                        
                        if not is_valid_format:
                            logger.warning(f"PHASE 4: Invalid Aadhaar format: {format_error}")
                            transition_result = {"success": False, "message": format_error}
                            bot_response = f"That doesn't look like a valid Aadhaar number. {format_error} Please enter a valid 12-digit Aadhaar number."
                            next_question_step = ConversationStep.KYC_ASK_AADHAAR.value
                        else:
                            # Store Aadhaar and show verifying message
                            update_session_data(session_id, {
                                "user_aadhaar": extracted_aadhaar,
                                "conversation_step": ConversationStep.KYC_AADHAAR_VERIFYING.value
                            })
                            
                            transition_result = {"success": True, "message": "Aadhaar received, verifying..."}
                            bot_response = get_prompt(ConversationStep.KYC_AADHAAR_VERIFYING, context)
                            next_question_step = ConversationStep.KYC_AADHAAR_VERIFYING.value
                    else:
                        # No Aadhaar in message - ask for it
                        transition_result = {"success": False, "message": "Waiting for Aadhaar"}
                        bot_response = get_prompt(ConversationStep.KYC_ASK_AADHAAR, context)
                        next_question_step = ConversationStep.KYC_ASK_AADHAAR.value
                
                # =========================================================
                # Step 4: VERIFY AADHAAR (deterministic check)
                # =========================================================
                elif pan_verified and not aadhaar_verified and current_step == ConversationStep.KYC_AADHAAR_VERIFYING.value:
                    # Perform deterministic Aadhaar verification
                    aadhaar_to_verify = state.user_aadhaar
                    
                    if not aadhaar_to_verify:
                        logger.error("PHASE 4: AADHAAR_VERIFYING step reached without Aadhaar stored!")
                        transition_result = {"success": False, "message": "Aadhaar not found"}
                        bot_response = "Please provide your 12-digit Aadhaar number."
                        next_question_step = ConversationStep.KYC_ASK_AADHAAR.value
                    else:
                        # Call deterministic verification
                        aadhaar_result = verify_aadhaar(aadhaar_to_verify, state.user_name)
                        timestamp = datetime.now().isoformat()
                        
                        logger.info(f"PHASE 4: Aadhaar verification result: {aadhaar_result.status} for {aadhaar_to_verify[:4]}****")
                        
                        if aadhaar_result.status == VerificationStatus.VERIFIED:
                            # Aadhaar verified successfully - BOTH VERIFIED!
                            update_session_data(session_id, {
                                "aadhaar_verified": True,
                                "aadhaar_verification_timestamp": timestamp,
                                "kyc_status": "VERIFIED",
                                "kyc_verified": True,
                                "conversation_step": ConversationStep.KYC_VERIFICATION_COMPLETE.value
                            })
                            
                            # Transition to OFFER_DISCOVERY
                            success, new_stage, msg = request_transition(
                                session_id,
                                StageEvent.KYC_VERIFIED,
                                {"kyc_verified": True, "kyc_status": "VERIFIED"}
                            )
                            
                            transition_result = {"success": True, "message": "KYC verification complete"}
                            bot_response = get_prompt(ConversationStep.KYC_VERIFICATION_COMPLETE, context)
                            next_question_step = ConversationStep.OFFER_CHECKING.value
                        else:
                            # Aadhaar verification failed - REJECT
                            failure_reason = aadhaar_result.error_message or "Aadhaar could not be verified"
                            
                            update_session_data(session_id, {
                                "aadhaar_verified": False,
                                "aadhaar_verification_timestamp": timestamp,
                                "kyc_status": "REJECTED",
                                "loan_status": "REJECTED",
                                "rejection_reason": f"Aadhaar verification failed: {failure_reason}"
                            })
                            
                            # Transition to REJECTION stage
                            success, new_stage, msg = request_transition(
                                session_id,
                                StageEvent.KYC_FAILED,
                                {"rejection_reason": f"Aadhaar verification failed: {failure_reason}"}
                            )
                            
                            transition_result = {"success": False, "message": "Aadhaar verification failed"}
                            context["failure_reason"] = failure_reason
                            context["rejection_reason"] = f"We were unable to verify your Aadhaar number. {failure_reason}"
                            bot_response = get_prompt(ConversationStep.KYC_AADHAAR_FAILED, context) + "\n\n" + get_prompt(ConversationStep.REJECTION_COMPLETE, context)
                            next_question_step = ConversationStep.REJECTION_COMPLETE.value
                
                # =========================================================
                # Step 5: BOTH VERIFIED - should have transitioned already
                # =========================================================
                elif pan_verified and aadhaar_verified:
                    logger.info("PHASE 4: Both PAN and Aadhaar verified, advancing to OFFER_DISCOVERY")
                    
                    # Transition to OFFER_DISCOVERY
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.KYC_VERIFIED,
                        {"kyc_verified": True, "kyc_status": "VERIFIED"}
                    )
                    
                    transition_result = {"success": True, "message": "KYC complete"}
                    bot_response = get_prompt(ConversationStep.KYC_VERIFICATION_COMPLETE, context)
                    next_question_step = ConversationStep.OFFER_LOOKUP_STARTED.value
        
        # =====================================================================
        # OFFER_DISCOVERY STAGE (Phase 5)
        # =====================================================================
        # Entry conditions: kyc_status == VERIFIED, pan_verified, aadhaar_verified
        # 1. Check Offer Mart for pre-approved offers (deterministic mock)
        # 2. Fetch credit score from Credit Bureau (deterministic mock)
        # 3. Calculate interest rate RANGE based on credit band + modifiers
        # 4. LLM presents rates as INDICATIVE, not final
        # 5. Transition to INCOME_DOC_UPLOAD
        # =====================================================================
        elif current == Stage.OFFER_DISCOVERY:
            logger.info("PHASE 5: OFFER_DISCOVERY handler started")
            
            # Step 1: Check entry conditions
            can_proceed, reason = can_start_offer_discovery(
                kyc_status=state.kyc_status,
                pan_verified=state.pan_verified,
                aadhaar_verified=state.aadhaar_verified
            )
            if not can_proceed:
                logger.warning(f"PHASE 5: Cannot start offer discovery - {reason}")
                transition_result = {"success": False, "message": reason}
                bot_response = f"Unable to proceed with offer discovery: {reason}"
                next_question_step = ConversationStep.OFFER_LOOKUP_STARTED.value
            else:
                # Step 2: Perform offer discovery (deterministic)
                mobile = state.user_mobile or ""
                logger.info(f"PHASE 5: Performing offer discovery for mobile: {mobile}")
                
                offer_result = perform_offer_discovery(mobile)
                
                # Step 3: Store results in session state
                update_session_data(session_id, {
                    "existing_customer": offer_result["existing_customer"],
                    "preapproved_offer": offer_result["preapproved_offer"],
                    "preapproved_limit": offer_result["preapproved_limit_inr"],
                    "credit_score": offer_result["credit_score"],
                    "credit_band": offer_result["credit_band"],
                    "interest_rate_min": offer_result["interest_rate_min"],
                    "interest_rate_max": offer_result["interest_rate_max"],
                    "interest_rate_band_reason": offer_result["interest_rate_band_reason"],
                    "risk_flag": offer_result["risk_flag"],
                    "offer_discovery_timestamp": datetime.now().isoformat()
                })
                
                # Step 4: Build response context for prompts
                rate_context = {
                    "rate_min": f"{offer_result['interest_rate_min']:.2f}",
                    "rate_max": f"{offer_result['interest_rate_max']:.2f}",
                    "preapproved_limit": format_currency(offer_result["preapproved_limit_inr"]) if offer_result["preapproved_limit_inr"] else None,
                    **context
                }
                
                # Step 5: Build appropriate response based on offer status
                if offer_result["risk_flag"]:
                    # Credit score too low - flag for manual review
                    logger.warning(f"PHASE 5: Risk flag raised - credit score {offer_result['credit_score']}")
                    bot_response = f"I've checked your profile. Based on your credit information, we'll need additional review. Your indicative interest rate range is {offer_result['interest_rate_min']:.2f}% - {offer_result['interest_rate_max']:.2f}% p.a. Please note this is preliminary and subject to verification."
                elif offer_result["preapproved_offer"]:
                    # Pre-approved customer
                    logger.info(f"PHASE 5: Pre-approved customer with limit ₹{offer_result['preapproved_limit_inr']}")
                    bot_response = get_prompt(ConversationStep.OFFER_PREAPPROVED_FOUND, rate_context)
                    bot_response += f"\n\n{get_prompt(ConversationStep.OFFER_RATE_CALCULATED, rate_context)}"
                elif offer_result["existing_customer"]:
                    # Existing customer (not pre-approved)
                    logger.info(f"PHASE 5: Existing customer, credit score {offer_result['credit_score']}")
                    bot_response = get_prompt(ConversationStep.OFFER_LOOKUP_STARTED, rate_context)
                    bot_response += f"\n\n{get_prompt(ConversationStep.OFFER_RATE_CALCULATED, rate_context)}"
                else:
                    # New customer
                    logger.info(f"PHASE 5: New customer, credit score {offer_result['credit_score']}")
                    bot_response = get_prompt(ConversationStep.OFFER_NEW_CUSTOMER, rate_context)
                    bot_response += f"\n\n{get_prompt(ConversationStep.OFFER_RATE_CALCULATED, rate_context)}"
                
                # Add transition prompt
                bot_response += f"\n\n{get_prompt(ConversationStep.OFFER_DISCOVERY_COMPLETE, rate_context)}"
                
                # Step 6: Log the offer result for debugging
                logger.info(f"PHASE 5: Offer discovery complete - "
                           f"existing={offer_result['existing_customer']}, "
                           f"preapproved={offer_result['preapproved_offer']}, "
                           f"credit_score={offer_result['credit_score']}, "
                           f"band={offer_result['credit_band']}, "
                           f"rate={offer_result['interest_rate_min']:.2f}-{offer_result['interest_rate_max']:.2f}%")
                
                # Step 7: Transition to INCOME_DOC_UPLOAD
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.OFFERS_CHECKED
                )
                transition_result = {"success": success, "message": msg}
                next_question_step = ConversationStep.INCOME_UPLOAD_REQUEST.value
        
        # =====================================================================
        # INCOME_DOC_UPLOAD STAGE (Phase 6)
        # =====================================================================
        # WHY INCOME VERIFICATION IS ISOLATED:
        #   Income verification runs EXACTLY ONCE per application.
        #   No looping, no repeated API calls, no UI toggles.
        #
        # WHY UPLOAD IS STAGE-CONTROLLED:
        #   Upload button visible ONLY in this stage.
        #   Disappears permanently after successful upload.
        #
        # HOW THIS PREVENTS UI DEADLOCKS:
        #   - Clear entry conditions prevent premature uploads
        #   - Single upload + optional retry = no infinite loops
        #   - State persists across reloads
        # =====================================================================
        elif current == Stage.INCOME_DOC_UPLOAD:
            logger.info("PHASE 6: INCOME_DOC_UPLOAD handler started")
            
            # Step 1: Check entry conditions
            can_proceed, reason = can_start_income_verification(
                kyc_status=state.kyc_status,
                interest_rate_min=state.interest_rate_min,
                interest_rate_max=state.interest_rate_max,
                requested_loan_amount=state.loan_amount
            )
            
            if not can_proceed:
                logger.error(f"PHASE 6: Entry conditions not met - {reason}")
                transition_result = {"success": False, "message": reason}
                bot_response = f"Unable to proceed with income verification: {reason}"
                next_question_step = ConversationStep.INCOME_UPLOAD_REQUEST.value
            
            # Step 2: Check if already verified (prevent re-verification)
            elif state.income_verified:
                logger.info("PHASE 6: Income already verified, advancing to UNDERWRITING")
                # Transition: INCOME_DOC_UPLOAD → UNDERWRITING
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.DOCUMENTS_UPLOADED,
                    {"documents_uploaded": ["salary_slip"]}
                )
                transition_result = {"success": success, "message": msg}
                bot_response = get_prompt(ConversationStep.INCOME_VERIFICATION_COMPLETE, context)
                next_question_step = ConversationStep.UNDERWRITING_PROCESSING.value
            
            # Step 3: Check if upload provided in this request
            elif has_uploaded_docs or documents_verified:
                logger.info("Salary document upload started")
                
                # Get file info from input
                file_name = extracted_data.get("file_name", "salary_slip.pdf")
                file_size = extracted_data.get("file_size", 5000)
                file_content = extracted_data.get("file_content", None)
                
                # Mark upload attempted
                update_session_data(session_id, {
                    "income_upload_attempted": True
                })
                
                # Perform income verification (deterministic)
                verification_result = perform_income_verification(
                    file_name=file_name,
                    file_size_bytes=file_size,
                    file_content=file_content,
                    retry_count=state.income_retry_count
                )
                
                if verification_result.success:
                    # Store verification results
                    logger.info(f"Salary parsing successful: ₹{verification_result.verified_monthly_salary_inr:,}")
                    logger.info("Income verification completed")
                    
                    update_session_data(session_id, {
                        "income_verified": True,
                        "verified_monthly_salary_inr": verification_result.verified_monthly_salary_inr,
                        "income_verification_timestamp": verification_result.verification_timestamp,
                        "income_document_id": verification_result.document_id,
                        "documents_uploaded": ["salary_slip"],
                        "documents_verified": True
                    })
                    
                    # Build response with salary amount
                    salary_display = format_salary_for_display(verification_result.verified_monthly_salary_inr)
                    income_context = {**context, "salary_amount": salary_display}
                    
                    bot_response = get_prompt(ConversationStep.INCOME_VERIFIED, income_context)
                    bot_response += f"\n\n{get_prompt(ConversationStep.INCOME_VERIFICATION_COMPLETE, income_context)}"
                    
                    # Transition: INCOME_DOC_UPLOAD → UNDERWRITING
                    logger.info("Stage advanced to UNDERWRITING")
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.DOCUMENTS_UPLOADED,
                        {"documents_uploaded": ["salary_slip"]}
                    )
                    transition_result = {"success": success, "message": msg}
                    next_question_step = ConversationStep.UNDERWRITING_PROCESSING.value
                
                elif verification_result.can_retry:
                    # Allow one retry
                    logger.warning(f"PHASE 6: Verification failed, retry allowed")
                    
                    update_session_data(session_id, {
                        "income_retry_count": state.income_retry_count + 1
                    })
                    
                    error_context = {**context, "error_message": verification_result.error_message}
                    bot_response = get_prompt(ConversationStep.INCOME_VERIFICATION_FAILED, error_context)
                    bot_response += f"\n\n{get_prompt(ConversationStep.INCOME_RETRY_ALLOWED, error_context)}"
                    
                    transition_result = {"success": False, "message": "Verification failed, retry allowed"}
                    next_question_step = ConversationStep.INCOME_UPLOAD_REQUEST.value
                
                else:
                    # Max retries exceeded - permanent failure
                    logger.error(f"PHASE 6: Verification failed, max retries exceeded")
                    
                    error_context = {**context, "error_message": verification_result.error_message}
                    bot_response = get_prompt(ConversationStep.INCOME_VERIFICATION_FAILED, error_context)
                    bot_response += "\n\nUnfortunately, we cannot proceed with your application at this time. Please contact our support team for assistance."
                    
                    transition_result = {"success": False, "message": "Verification failed permanently"}
                    next_question_step = ConversationStep.INCOME_VERIFICATION_FAILED.value
            
            else:
                # Step 4: No upload yet - request salary slip
                logger.info("PHASE 6: Waiting for salary document upload")
                
                # Check if upload is allowed
                can_upload, upload_reason = can_upload_document(
                    current_stage="INCOME_DOC_UPLOAD",
                    income_verified=state.income_verified,
                    upload_attempted=state.income_upload_attempted,
                    retry_count=state.income_retry_count
                )
                
                if not can_upload:
                    logger.warning(f"PHASE 6: Upload not allowed - {upload_reason}")
                    bot_response = f"Unable to upload: {upload_reason}"
                else:
                    bot_response = get_prompt(ConversationStep.INCOME_UPLOAD_REQUEST, context)
                
                transition_result = {"success": False, "message": "Waiting for document upload"}
                next_question_step = ConversationStep.INCOME_UPLOAD_REQUEST.value
        
        # =====================================================================
        # PHASE 7: UNDERWRITING STAGE - DETERMINISTIC DECISION ENGINE
        # =====================================================================
        # WHY UNDERWRITING IS ISOLATED:
        #   This stage makes FINAL loan approval/rejection decisions.
        #   Decisions MUST be deterministic and reproducible.
        #   Same inputs ALWAYS produce same outputs.
        #
        # WHY LLM CANNOT BE TRUSTED WITH APPROVALS:
        #   - LLMs can hallucinate justifications
        #   - Same prompt can produce different decisions
        #   - Regulatory compliance requires consistent criteria
        #   - Audit trail requires deterministic logic
        #
        # HOW THIS WORKS:
        #   1. Validate entry conditions (income verified, credit score, etc.)
        #   2. Run deterministic underwriting rules (credit, limit, EMI)
        #   3. Store FINAL decision (APPROVED or REJECTED)
        #   4. Transition to SANCTION or REJECTION stage
        #   5. LLM may EXPLAIN but CANNOT CHANGE the decision
        # =====================================================================
        elif current == Stage.UNDERWRITING:
            logger.info("=" * 60)
            logger.info("PHASE 7: UNDERWRITING STAGE ENTERED")
            logger.info("=" * 60)
            
            # Step 1: Check if underwriting has already been completed
            # This prevents re-running underwriting on the same application
            if state.underwriting_completed or has_underwriting_completed(state.loan_status):
                logger.warning("PHASE 7: Underwriting already completed, cannot re-run")
                
                if state.loan_status == "APPROVED":
                    bot_response = f"Your loan has already been approved! Reference: {state.sanction_reference}"
                    next_question_step = ConversationStep.SANCTION_COMPLETE.value
                else:
                    bot_response = f"Your application has already been processed. {state.rejection_reason}"
                    next_question_step = ConversationStep.REJECTION_COMPLETE.value
                
                transition_result = {"success": False, "message": "Underwriting already completed"}
            
            else:
                # Step 2: Validate entry conditions
                logger.info("Underwriting started")
                can_proceed, entry_reason = validate_underwriting_entry(
                    income_verified=state.income_verified,
                    verified_monthly_salary_inr=state.verified_monthly_salary_inr,
                    credit_score=state.credit_score,
                    requested_loan_amount=state.loan_amount
                )
                
                if not can_proceed:
                    # Entry conditions not met - block execution
                    logger.error(f"PHASE 7: Entry blocked - {entry_reason}")
                    bot_response = f"Unable to process application: {entry_reason}"
                    transition_result = {"success": False, "message": entry_reason}
                    next_question_step = ConversationStep.UNDERWRITING_STARTED.value
                
                else:
                    # Step 3: Perform deterministic underwriting
                    logger.info("Credit score evaluated")
                    
                    # Get interest rate for EMI calculation (use min rate as baseline)
                    interest_rate = state.interest_rate_min or state.interest_rate or 12.0
                    
                    # Perform underwriting with all rules
                    result = perform_underwriting(
                        income_verified=state.income_verified,
                        verified_monthly_salary_inr=state.verified_monthly_salary_inr,
                        credit_score=state.credit_score,
                        requested_loan_amount=state.loan_amount,
                        pre_approved_limit=state.pre_approved_limit,
                        existing_emi=state.existing_emi,
                        loan_tenure_months=state.loan_tenure_months,
                        interest_rate=interest_rate
                    )
                    
                    logger.info(f"EMI affordability calculated")
                    
                    # Step 4: Store decision in state (FINAL - cannot be changed)
                    update_session_data(session_id, {
                        "loan_status": result.loan_status,
                        "approval_reason": result.approval_reason,
                        "rejection_reason": result.rejection_reason,
                        "underwriting_timestamp": result.timestamp,
                        "underwriting_completed": True,
                        "calculated_emi": result.calculated_emi,
                        "foir": result.foir
                    })
                    
                    # Step 5: Handle APPROVED decision
                    if result.decision == LoanDecision.APPROVED:
                        logger.info(f"Loan APPROVED")
                        
                        # Generate sanction reference
                        sanction_ref = f"TATA/PL/{datetime.now().strftime('%Y%m%d')}/{session_id[:4].upper()}"
                        update_session_data(session_id, {
                            "sanction_reference": sanction_ref
                        })
                        
                        # Build approval context for LLM response
                        approval_context = {
                            **context,
                            "calculated_emi": result.calculated_emi,
                            "foir": result.foir,
                            "approval_reason": result.approval_reason
                        }
                        
                        bot_response = get_prompt(ConversationStep.UNDERWRITING_APPROVED, approval_context)
                        
                        # Transition: UNDERWRITING → SANCTION
                        logger.info("Stage advanced to SANCTION")
                        success, new_stage, msg = request_transition(
                            session_id,
                            StageEvent.UNDERWRITING_APPROVED,
                            {"sanction_reference": sanction_ref}
                        )
                        transition_result = {"success": success, "message": msg}
                        next_question_step = ConversationStep.SANCTION_COMPLETE.value
                    
                    # Step 6: Handle REJECTED decision
                    elif result.decision == LoanDecision.REJECTED:
                        logger.warning(f"Loan REJECTED: {result.rejection_reason}")
                        
                        # Build rejection context for LLM response
                        rejection_context = {
                            **context,
                            "rejection_reason": result.rejection_reason,
                            "calculated_emi": result.calculated_emi,
                            "foir": result.foir
                        }
                        
                        bot_response = get_prompt(ConversationStep.UNDERWRITING_REJECTED, rejection_context)
                        
                        # Transition: UNDERWRITING → REJECTION
                        logger.info("Stage advanced to REJECTION")
                        success, new_stage, msg = request_transition(
                            session_id,
                            StageEvent.UNDERWRITING_REJECTED,
                            {"rejection_reason": result.rejection_reason}
                        )
                        transition_result = {"success": success, "message": msg}
                        next_question_step = ConversationStep.REJECTION_COMPLETE.value
                    
                    # Step 7: Handle PENDING (incomplete data)
                    else:
                        logger.error(f"PHASE 7: Underwriting incomplete - {result.reason}")
                        bot_response = f"Unable to complete assessment: {result.reason}"
                        transition_result = {"success": False, "message": result.reason}
                        next_question_step = ConversationStep.UNDERWRITING_STARTED.value
        
        # =====================================================================
        # PHASE 8: SANCTION STAGE - TERMINAL STATE (APPROVED)
        # =====================================================================
        # WHY SANCTION IS A TERMINAL STAGE:
        #   Once a loan is sanctioned, the decision is FINAL.
        #   The sanction letter is a legally binding document.
        #   No further modifications are allowed to the loan terms.
        #
        # HOW CLEAN CLOSURE IMPROVES TRUST:
        #   - Approved users receive downloadable sanction letters
        #   - Clear next steps (disbursement)
        #   - Professional documentation
        #   - No lingering uncertainty
        #
        # WHAT HAPPENS IN THIS STAGE:
        #   1. Validate entry conditions (loan_status == APPROVED, underwriting_timestamp exists)
        #   2. Check if sanction letter already generated (prevent duplicates)
        #   3. Generate sanction letter PDF
        #   4. Store sanction letter path and reference
        #   5. Mark journey as complete
        #   6. Block any further input
        # =====================================================================
        elif current == Stage.SANCTION:
            logger.info("=" * 60)
            logger.info("PHASE 8: SANCTION STAGE ENTERED (TERMINAL)")
            logger.info("=" * 60)
            
            # Step 1: Validate entry conditions
            can_proceed, entry_reason = validate_sanction_entry_conditions(
                loan_status=state.loan_status,
                underwriting_timestamp=state.underwriting_timestamp
            )
            
            if not can_proceed:
                # Entry conditions not met - this should NEVER happen if stage machine is working
                logger.error(f"PHASE 8 SECURITY VIOLATION: SANCTION entry blocked! Reason: {entry_reason}")
                bot_response = f"Unable to proceed with sanction: {entry_reason}"
                transition_result = {"success": False, "message": entry_reason}
                next_question_step = ConversationStep.SANCTION_ENTRY_VALIDATION.value
            
            # Step 2: Check if journey already closed (prevent duplicate generation)
            elif is_journey_closed(state.journey_completed, state.session_closed):
                logger.warning("PHASE 8: Journey already closed, cannot re-generate sanction letter")
                
                # Return existing sanction letter info
                bot_response = get_prompt(ConversationStep.SANCTION_LETTER_READY, {
                    **context,
                    "sanction_reference": state.sanction_letter_reference or state.sanction_reference
                })
                transition_result = {"success": True, "message": "Sanction already complete"}
                next_question_step = ConversationStep.SANCTION_JOURNEY_COMPLETE.value
            
            # Step 3: Check if sanction letter already generated
            elif state.sanction_letter_generated:
                logger.info("PHASE 8: Sanction letter already generated, returning download info")
                
                bot_response = get_prompt(ConversationStep.SANCTION_LETTER_READY, {
                    **context,
                    "sanction_reference": state.sanction_letter_reference or state.sanction_reference
                })
                bot_response += "\n\n" + get_prompt(ConversationStep.SANCTION_JOURNEY_COMPLETE, context)
                
                transition_result = {"success": True, "message": "Sanction letter already generated"}
                next_question_step = ConversationStep.SANCTION_JOURNEY_COMPLETE.value
            
            else:
                # Step 4: Generate sanction letter
                logger.info("PHASE 8: Generating sanction letter...")
                
                # Show generating message
                bot_response = get_prompt(ConversationStep.SANCTION_LETTER_GENERATING, context)
                
                # Close journey with sanction
                closure_result = close_journey_with_sanction(
                    session_id=session_id,
                    customer_name=state.user_name or "Customer",
                    loan_amount=state.loan_amount or 0,
                    interest_rate=state.interest_rate_min or state.interest_rate or 12.0,
                    loan_tenure_months=state.loan_tenure_months or 36,
                    calculated_emi=state.calculated_emi or 0,
                    phone=state.user_mobile or "",
                    pan=state.user_pan or "",
                    sanction_letter_generated=state.sanction_letter_generated
                )
                
                if closure_result.journey_completed and closure_result.sanction_result:
                    # Step 5: Update session state with sanction details
                    sanction_updates = get_sanction_state_updates(closure_result.sanction_result)
                    update_session_data(session_id, sanction_updates)
                    
                    logger.info("PHASE 8: Sanction letter generated successfully")
                    logger.info(f"  Path: {closure_result.sanction_result.sanction_letter_path}")
                    logger.info(f"  Reference: {closure_result.sanction_result.sanction_letter_reference}")
                    
                    # Build confirmation message
                    sanction_context = {
                        **context,
                        "sanction_reference": closure_result.sanction_result.sanction_letter_reference
                    }
                    
                    bot_response = get_prompt(ConversationStep.SANCTION_LETTER_READY, sanction_context)
                    bot_response += "\n\n" + get_prompt(ConversationStep.SANCTION_JOURNEY_COMPLETE, sanction_context)
                    
                    transition_result = {"success": True, "message": "Loan journey completed - SANCTION"}
                    next_question_step = ConversationStep.SANCTION_JOURNEY_COMPLETE.value
                    
                    logger.info("Loan journey completed")
                else:
                    # Sanction letter generation failed
                    logger.error(f"PHASE 8: Sanction letter generation failed: {closure_result.error_message}")
                    bot_response = f"Your loan is approved, but we encountered an issue generating the sanction letter. Please contact support."
                    transition_result = {"success": False, "message": closure_result.error_message}
                    next_question_step = ConversationStep.SANCTION_LETTER_GENERATING.value
        
        # =====================================================================
        # PHASE 8: REJECTION STAGE - TERMINAL STATE (REJECTED)
        # =====================================================================
        # WHY REJECTION MUST BE FINAL:
        #   Clear, honest communication builds trust.
        #   Single clear reason (not a list of issues).
        #   No upselling or workaround suggestions.
        #   Professional closure maintains brand reputation.
        #
        # WHAT THIS STAGE DOES:
        #   1. Validate entry conditions (loan_status == REJECTED, rejection_reason exists)
        #   2. Process rejection to get customer-facing message
        #   3. Provide SINGLE clear reason (no list)
        #   4. Do NOT upsell or suggest workarounds
        #   5. End the journey respectfully
        #   6. Block any further input
        # =====================================================================
        elif current == Stage.REJECTION:
            logger.info("=" * 60)
            logger.info("PHASE 8: REJECTION STAGE ENTERED (TERMINAL)")
            logger.info("=" * 60)
            
            # Step 1: Validate entry conditions
            can_proceed, entry_reason = validate_rejection_entry_conditions(
                loan_status=state.loan_status,
                rejection_reason=state.rejection_reason
            )
            
            if not can_proceed:
                # Entry conditions not met - this should NEVER happen if stage machine is working
                logger.error(f"PHASE 8 SECURITY VIOLATION: REJECTION entry blocked! Reason: {entry_reason}")
                bot_response = f"Unable to process rejection: {entry_reason}"
                transition_result = {"success": False, "message": entry_reason}
                next_question_step = ConversationStep.REJECTION_ENTRY_VALIDATION.value
            
            # Step 2: Check if journey already closed
            elif is_journey_closed(state.journey_completed, state.session_closed):
                logger.warning("PHASE 8: Journey already closed")
                
                bot_response = get_prompt(ConversationStep.REJECTION_FINAL_MESSAGE, context)
                bot_response += "\n\n" + get_prompt(ConversationStep.REJECTION_JOURNEY_COMPLETE, context)
                
                transition_result = {"success": True, "message": "Rejection already processed"}
                next_question_step = ConversationStep.REJECTION_JOURNEY_COMPLETE.value
            
            else:
                # Step 3: Process rejection and close journey
                logger.info(f"PHASE 8: Processing rejection - {state.rejection_reason}")
                
                closure_result = close_journey_with_rejection(
                    rejection_reason=state.rejection_reason
                )
                
                # Step 4: Update session state with rejection details
                rejection_updates = get_rejection_state_updates(closure_result.rejection_result)
                update_session_data(session_id, rejection_updates)
                
                logger.info(f"PHASE 8: Rejection processed")
                logger.info(f"  Category: {closure_result.rejection_result.rejection_category.value}")
                
                # Step 5: Build final rejection message
                # Note: We use the standardized message, not the technical reason
                bot_response = closure_result.rejection_result.rejection_message
                bot_response += "\n\n" + get_prompt(ConversationStep.REJECTION_JOURNEY_COMPLETE, context)
                
                transition_result = {"success": True, "message": "Loan journey completed - REJECTION"}
                next_question_step = ConversationStep.REJECTION_JOURNEY_COMPLETE.value
                
                logger.info("Loan journey completed")
        
        return {
            "extracted_data": extracted_data,
            "transition_result": transition_result,
            "bot_response": bot_response,
            "next_question_step": next_question_step
        }
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get full session state as dictionary."""
        return get_session_state(session_id)
    
    def reset_session(self, session_id: str):
        """Reset a session to start over."""
        self.controller.reset_session(session_id)


# ================================================================================
# FACTORY FUNCTION
# ================================================================================

def create_conversational_handler(backend_services=None) -> ConversationalStageHandler:
    """
    Create a conversational stage handler with Phase 2 question sequencing.
    """
    return ConversationalStageHandler(backend_services)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 2: TESTING CONVERSATIONAL STAGE HANDLER")
    print("=" * 60)
    
    handler = create_conversational_handler()
    session_id = "test_conversational_001"
    
    # Reset for clean test
    handler.reset_session(session_id)
    
    # Simulate the CORRECT conversation flow
    conversation = [
        ("Hi!", "GREETING - User greets"),
        # Now in NEEDS_DISCOVERY
        ("for home renovation", "NEEDS_DISCOVERY - User provides purpose"),
        ("5 lakhs", "NEEDS_DISCOVERY - User provides amount"),
        # Now in BASIC_ELIGIBILITY
        ("Mumbai", "BASIC_ELIGIBILITY - User provides city"),
        ("salaried", "BASIC_ELIGIBILITY - User provides employment type"),
        # Now in KYC_COLLECTION
        ("Rahul Sharma", "KYC_COLLECTION - User provides name"),
        ("9876543210", "KYC_COLLECTION - User provides mobile"),
        # Now in OTP_VERIFICATION
        ("123456", "OTP_VERIFICATION - User enters OTP"),
    ]
    
    for user_msg, description in conversation:
        print(f"\n{'='*60}")
        print(f"TEST: {description}")
        print(f"USER: {user_msg}")
        
        result = handler.process_message(session_id, user_msg)
        
        print(f"STAGE: {result['previous_stage']} → {result['current_stage']}")
        print(f"BOT: {result.get('bot_response', '')[:100]}...")
        print(f"NEXT STEP: {result.get('next_question_step')}")
        if result.get('otp_code'):
            print(f"OTP: {result['otp_code']}")
        print(f"{'='*60}")
    
    # Continue through remaining stages
    print(f"\n{'='*60}")
    print("CONTINUING THROUGH KYC_VERIFICATION → OFFER_DISCOVERY → DOC_UPLOAD")
    
    result = handler.process_message(session_id, "proceed")
    print(f"After KYC_VERIFICATION: {result['current_stage']}")
    
    result = handler.process_message(session_id, "check offers")
    print(f"After OFFER_DISCOVERY: {result['current_stage']}")
    
    # Simulate document upload
    result = handler.process_message(session_id, "uploaded", has_uploaded_docs=True)
    print(f"After INCOME_DOC_UPLOAD: {result['current_stage']}")
    
    result = handler.process_message(session_id, "proceed")
    print(f"After UNDERWRITING: {result['current_stage']}")
    
    # Clean up
    handler.reset_session(session_id)
    
    print("\n" + "=" * 60)
    print("PHASE 2 CONVERSATIONAL HANDLER TEST COMPLETE")
    print("=" * 60)
