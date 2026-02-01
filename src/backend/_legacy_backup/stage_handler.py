"""
================================================================================
PHASE 1: STAGE-BASED MESSAGE HANDLER
================================================================================

This module routes user messages through the strict stage machine.
It is the bridge between user input and the deterministic stage controller.

================================================================================
KEY RESPONSIBILITIES
================================================================================

1. EXTRACT DATA FROM MESSAGES
   - Parse user messages for relevant information
   - Extract mobile numbers, names, loan amounts, OTP codes
   - Store extracted data in stage state (NOT stage transitions)

2. DETERMINE APPROPRIATE EVENT
   - Based on current stage and extracted data
   - Decide which StageEvent to trigger (if any)
   - Never skip stages or create invalid transitions

3. REQUEST STAGE TRANSITIONS
   - Call StageController.transition() with the appropriate event
   - Handle success/failure responses
   - Log all transition attempts

4. GENERATE CONTEXT FOR LLM
   - Provide current stage instruction to LLM
   - Include relevant state data for response generation
   - LLM ONLY generates response text, NOT flow decisions

================================================================================
CRITICAL PRINCIPLE
================================================================================

This handler READS user messages and REQUESTS transitions.
It does NOT directly modify the stage.
Only StageController.transition() can change the current_stage.

================================================================================
"""

import re
import random
import string
from typing import Dict, Any, Optional, Tuple
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | HANDLER | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('stage_handler')


# ================================================================================
# TEST USERS FOR DEMO
# ================================================================================

TEST_USERS_OTP = {
    "9876543210": "123456",  # Rahul Mehta
    "9988776655": "123456",  # Amit Verma
    "9123456781": "123456",  # Priya Sharma
}


# ================================================================================
# DATA EXTRACTION UTILITIES
# ================================================================================

def extract_mobile_number(message: str) -> Optional[str]:
    """
    Extract a 10-digit Indian mobile number from user message.
    
    Valid formats:
    - 9876543210
    - +91 9876543210
    - 91-9876543210
    
    Must start with 6, 7, 8, or 9.
    """
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
    """
    Extract loan amount from user message.
    
    Handles:
    - 5 lakhs, 5L, 5 lacs
    - Rs. 5,00,000
    - 500000
    - 500000 rupees
    """
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
    
    # Pattern: Direct number (5+ digits) with optional currency prefix/suffix
    # Handles: 500000, 5,00,000, Rs. 500000, 500000 rupees
    number_pattern = r'(?:rs\.?\s*)?(\d{1,2}(?:,\d{2})*(?:,\d{3})|\d{5,})(?:\s*(?:rupees|rs|inr))?'
    match = re.search(number_pattern, message_lower)
    if match:
        amount_str = match.group(1).replace(',', '')
        amount = float(amount_str)
        if amount >= 10000:
            return amount
    
    return None


def extract_name(message: str) -> Optional[str]:
    """
    Extract user's name from message.
    
    Handles:
    - "I'm Rahul"
    - "My name is Priya Sharma"
    - "This is Amit"
    """
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
    
    return None


def extract_otp(message: str) -> Optional[str]:
    """
    Extract OTP from user message.
    
    Handles:
    - "123456"
    - "OTP is 123456"
    - "my code is 123456"
    """
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


def generate_otp(mobile: str) -> str:
    """Generate OTP for a mobile number."""
    if mobile in TEST_USERS_OTP:
        return TEST_USERS_OTP[mobile]
    return ''.join(random.choices(string.digits, k=6))


# ================================================================================
# STAGE MESSAGE HANDLER
# ================================================================================

class StageMessageHandler:
    """
    Handles user messages and routes them through the strict stage machine.
    
    ================================================================================
    PROCESSING FLOW
    ================================================================================
    
    1. Get current stage from StageController
    2. Extract relevant data from message
    3. Determine if a stage transition should occur
    4. Request transition via StageController.transition()
    5. Return response context for LLM
    
    ================================================================================
    CRITICAL RULES
    ================================================================================
    
    - This handler does NOT modify current_stage directly
    - All transitions go through StageController.transition()
    - Invalid transitions are blocked by StageController
    - LLM only generates response text based on stage context
    
    ================================================================================
    """
    
    def __init__(self, backend_services=None):
        """
        Initialize the handler.
        
        Args:
            backend_services: Optional backend services for CRM/Credit lookups
        """
        self.controller = get_stage_controller()
        self.backend_services = backend_services
        
        logger.info("=" * 60)
        logger.info("STAGE MESSAGE HANDLER INITIALIZED")
        logger.info("Using strict stage machine for flow control")
        logger.info("=" * 60)
    
    def process_message(
        self,
        session_id: str,
        user_message: str,
        has_uploaded_docs: bool = False,
        documents_verified: bool = False
    ) -> Dict[str, Any]:
        """
        Process a user message through the stage machine.
        
        ================================================================================
        THIS IS THE MAIN ENTRY POINT
        ================================================================================
        
        Steps:
        1. Get/create session and current stage
        2. Process message for current stage
        3. Extract data and request appropriate transition
        4. Return context for LLM response generation
        
        Args:
            session_id: Session identifier
            user_message: User's message
            has_uploaded_docs: Whether documents were uploaded
            documents_verified: Whether documents were verified
        
        Returns:
            Dict with stage info, transition result, and LLM context
        """
        logger.info("=" * 60)
        logger.info(f"PROCESSING MESSAGE")
        logger.info(f"  Session: {session_id}")
        logger.info(f"  Message: {user_message[:50]}...")
        
        # Step 1: Get current state
        state = self.controller.get_or_create_session(session_id)
        previous_stage = state.current_stage
        
        logger.info(f"  Current Stage: {previous_stage.value}")
        
        # Step 2: Process based on current stage
        result = self._process_for_stage(
            session_id=session_id,
            state=state,
            user_message=user_message,
            has_uploaded_docs=has_uploaded_docs,
            documents_verified=documents_verified
        )
        
        # Step 3: Get updated state
        updated_state = self.controller.get_or_create_session(session_id)
        new_stage = updated_state.current_stage
        stage_changed = previous_stage != new_stage
        
        if stage_changed:
            logger.info(f"  Stage CHANGED: {previous_stage.value} → {new_stage.value}")
        else:
            logger.info(f"  Stage UNCHANGED: {new_stage.value}")
        
        logger.info("=" * 60)
        
        # Step 4: Prepare response context
        return {
            "session_id": session_id,
            "previous_stage": previous_stage.value,
            "current_stage": new_stage.value,
            "stage_changed": stage_changed,
            "stage_instruction": get_stage_instruction(new_stage),
            "state_data": updated_state.to_dict(),
            "transition_result": result.get("transition_result"),
            "show_upload": new_stage == Stage.INCOME_DOC_UPLOAD,
            "show_sanction_letter": new_stage == Stage.SANCTION and updated_state.sanction_reference,
            "session_closed": updated_state.session_closed,
            "closure_reason": updated_state.closure_reason,
            "extracted_data": result.get("extracted_data", {}),
            "otp_code": updated_state.otp_code if new_stage == Stage.OTP_VERIFICATION else None,
        }
    
    def _process_for_stage(
        self,
        session_id: str,
        state: StageState,
        user_message: str,
        has_uploaded_docs: bool = False,
        documents_verified: bool = False
    ) -> Dict[str, Any]:
        """
        Process message based on current stage.
        
        Each stage has specific data extraction and transition rules.
        """
        current = state.current_stage
        extracted_data = {}
        transition_result = None
        
        # =====================================================================
        # GREETING STAGE
        # =====================================================================
        if current == Stage.GREETING:
            # Extract any early data
            loan_amount = extract_loan_amount(user_message)
            if loan_amount:
                extracted_data["loan_amount"] = loan_amount
                update_session_data(session_id, {"loan_amount": loan_amount})
            
            name = extract_name(user_message)
            if name:
                extracted_data["user_name"] = name
                update_session_data(session_id, {"user_name": name})
            
            # Transition: GREETING → NEEDS_DISCOVERY
            success, new_stage, msg = request_transition(
                session_id, 
                StageEvent.USER_GREETED
            )
            transition_result = {"success": success, "message": msg}
        
        # =====================================================================
        # NEEDS_DISCOVERY STAGE
        # =====================================================================
        elif current == Stage.NEEDS_DISCOVERY:
            # Extract loan amount
            loan_amount = extract_loan_amount(user_message)
            if loan_amount:
                extracted_data["loan_amount"] = loan_amount
                update_session_data(session_id, {"loan_amount": loan_amount})
                
                # Transition: NEEDS_DISCOVERY → BASIC_ELIGIBILITY
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.LOAN_AMOUNT_PROVIDED,
                    {"loan_amount": loan_amount}
                )
                transition_result = {"success": success, "message": msg}
            else:
                # Stay in stage - need loan amount
                transition_result = {"success": False, "message": "Waiting for loan amount"}
        
        # =====================================================================
        # BASIC_ELIGIBILITY STAGE
        # =====================================================================
        elif current == Stage.BASIC_ELIGIBILITY:
            # Auto-transition after eligibility check
            # In production, this would check credit score, income, etc.
            success, new_stage, msg = request_transition(
                session_id,
                StageEvent.ELIGIBILITY_CHECKED
            )
            transition_result = {"success": success, "message": msg}
        
        # =====================================================================
        # KYC_COLLECTION STAGE
        # =====================================================================
        elif current == Stage.KYC_COLLECTION:
            # Extract name
            name = extract_name(user_message)
            if name:
                extracted_data["user_name"] = name
                update_session_data(session_id, {"user_name": name})
            
            # Extract mobile number
            mobile = extract_mobile_number(user_message)
            if mobile:
                extracted_data["user_mobile"] = mobile
                
                # Generate and store OTP
                otp = generate_otp(mobile)
                update_session_data(session_id, {
                    "user_mobile": mobile,
                    "otp_code": otp,
                    "otp_sent": True,
                    "otp_attempts": 0
                })
                extracted_data["otp_code"] = otp
                
                logger.info(f"OTP Generated: {otp} for {mobile}")
                
                # Transition: KYC_COLLECTION → OTP_VERIFICATION
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.KYC_INFO_PROVIDED,
                    {"user_mobile": mobile, "otp_code": otp, "otp_sent": True}
                )
                transition_result = {"success": success, "message": msg}
            else:
                # Stay in stage - need mobile number
                transition_result = {"success": False, "message": "Waiting for mobile number"}
        
        # =====================================================================
        # OTP_VERIFICATION STAGE
        # =====================================================================
        elif current == Stage.OTP_VERIFICATION:
            # Extract OTP
            entered_otp = extract_otp(user_message)
            
            if entered_otp:
                expected_otp = state.otp_code
                
                if entered_otp == expected_otp:
                    # OTP correct
                    update_session_data(session_id, {"otp_verified": True})
                    
                    logger.info(f"OTP Verified Successfully!")
                    
                    # Transition: OTP_VERIFICATION → KYC_VERIFICATION
                    success, new_stage, msg = request_transition(
                        session_id,
                        StageEvent.OTP_VERIFIED,
                        {"otp_verified": True}
                    )
                    transition_result = {"success": success, "message": msg}
                else:
                    # OTP wrong
                    attempts = state.otp_attempts + 1
                    update_session_data(session_id, {"otp_attempts": attempts})
                    
                    logger.warning(f"Wrong OTP (attempt {attempts}/3)")
                    
                    if attempts >= 3:
                        # Too many attempts - go back to KYC collection
                        update_session_data(session_id, {
                            "otp_sent": False,
                            "otp_code": None,
                            "otp_attempts": 0
                        })
                        
                        success, new_stage, msg = request_transition(
                            session_id,
                            StageEvent.OTP_FAILED
                        )
                        transition_result = {"success": success, "message": "Too many OTP attempts"}
                    else:
                        transition_result = {"success": False, "message": f"Wrong OTP, {3-attempts} attempts remaining"}
            else:
                # No OTP in message
                transition_result = {"success": False, "message": "Waiting for OTP"}
        
        # =====================================================================
        # KYC_VERIFICATION STAGE
        # =====================================================================
        elif current == Stage.KYC_VERIFICATION:
            # Verify against backend services (CRM lookup)
            kyc_verified = True  # Simplified for Phase 1
            
            if self.backend_services and state.user_mobile:
                try:
                    kyc_response = self.backend_services.verify_kyc(
                        mobile_number=state.user_mobile
                    )
                    kyc_verified = kyc_response.kyc_status == "VERIFIED"
                    
                    if kyc_verified:
                        update_session_data(session_id, {
                            "kyc_verified": True,
                            "is_existing_customer": True,
                            "customer_id": kyc_response.customer_id,
                            "user_name": kyc_response.name or state.user_name,
                            "credit_score": getattr(kyc_response, 'credit_score', None),
                            "monthly_income": getattr(kyc_response, 'monthly_income', None)
                        })
                except Exception as e:
                    logger.error(f"KYC verification error: {e}")
                    kyc_verified = True  # Continue on error for demo
            
            if kyc_verified:
                # Transition: KYC_VERIFICATION → OFFER_DISCOVERY
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.KYC_VERIFIED,
                    {"kyc_verified": True}
                )
                transition_result = {"success": success, "message": msg}
            else:
                # KYC failed - reject
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.KYC_FAILED,
                    {"rejection_reason": "KYC verification failed"}
                )
                transition_result = {"success": success, "message": msg}
        
        # =====================================================================
        # OFFER_DISCOVERY STAGE
        # =====================================================================
        elif current == Stage.OFFER_DISCOVERY:
            # Check offers from backend services
            if self.backend_services and state.user_mobile:
                try:
                    offer_response = self.backend_services.check_offers(
                        mobile_number=state.user_mobile
                    )
                    
                    if offer_response.has_offer:
                        update_session_data(session_id, {
                            "pre_approved_limit": offer_response.preapproved_limit_inr,
                            "interest_rate": offer_response.interest_rate_percent
                        })
                except Exception as e:
                    logger.error(f"Offer check error: {e}")
            
            # Transition: OFFER_DISCOVERY → INCOME_DOC_UPLOAD
            success, new_stage, msg = request_transition(
                session_id,
                StageEvent.OFFERS_CHECKED
            )
            transition_result = {"success": success, "message": msg}
        
        # =====================================================================
        # INCOME_DOC_UPLOAD STAGE
        # =====================================================================
        elif current == Stage.INCOME_DOC_UPLOAD:
            # Check if documents uploaded
            if has_uploaded_docs or documents_verified:
                update_session_data(session_id, {
                    "documents_uploaded": ["income_proof"],
                    "documents_verified": documents_verified
                })
                
                # Transition: INCOME_DOC_UPLOAD → UNDERWRITING
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.DOCUMENTS_UPLOADED,
                    {"documents_uploaded": ["income_proof"]}
                )
                transition_result = {"success": success, "message": msg}
            else:
                # Stay in stage - waiting for upload
                transition_result = {"success": False, "message": "Waiting for document upload"}
        
        # =====================================================================
        # UNDERWRITING STAGE
        # =====================================================================
        elif current == Stage.UNDERWRITING:
            # Make underwriting decision
            # In production, this calls the underwriting engine
            approved = True  # Simplified for Phase 1
            
            if approved:
                sanction_ref = f"TATA/PL/{datetime.now().strftime('%Y%m%d')}/{session_id[:4].upper()}"
                update_session_data(session_id, {
                    "loan_status": "APPROVED",
                    "sanction_reference": sanction_ref
                })
                
                # Transition: UNDERWRITING → SANCTION
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.UNDERWRITING_APPROVED,
                    {"sanction_reference": sanction_ref}
                )
                transition_result = {"success": success, "message": msg}
            else:
                update_session_data(session_id, {
                    "loan_status": "REJECTED",
                    "rejection_reason": "Underwriting criteria not met"
                })
                
                # Transition: UNDERWRITING → REJECTION
                success, new_stage, msg = request_transition(
                    session_id,
                    StageEvent.UNDERWRITING_REJECTED,
                    {"rejection_reason": "Underwriting criteria not met"}
                )
                transition_result = {"success": success, "message": msg}
        
        # =====================================================================
        # TERMINAL STAGES (SANCTION / REJECTION)
        # =====================================================================
        elif current in (Stage.SANCTION, Stage.REJECTION):
            # No transitions from terminal states
            transition_result = {
                "success": False, 
                "message": f"Session completed ({current.value})"
            }
        
        return {
            "extracted_data": extracted_data,
            "transition_result": transition_result
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

def create_stage_handler(backend_services=None) -> StageMessageHandler:
    """
    Create a stage message handler.
    
    Args:
        backend_services: Optional backend services for CRM/Credit lookups
    
    Returns:
        Configured StageMessageHandler
    """
    return StageMessageHandler(backend_services)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING STAGE MESSAGE HANDLER")
    print("=" * 60)
    
    handler = create_stage_handler()
    session_id = "test_handler_001"
    
    # Reset for clean test
    handler.reset_session(session_id)
    
    # Simulate conversation
    messages = [
        "Hi there!",
        "I need a loan of 5 lakhs",
        "My name is Rahul and my number is 9876543210",
        "123456",  # OTP
        "proceed",  # KYC verification
        "check offers",  # Offer discovery
        # Document upload would be handled separately
    ]
    
    for msg in messages:
        print(f"\n{'='*60}")
        print(f"USER: {msg}")
        result = handler.process_message(session_id, msg)
        print(f"STAGE: {result['previous_stage']} → {result['current_stage']}")
        print(f"Changed: {result['stage_changed']}")
        if result.get('otp_code'):
            print(f"OTP: {result['otp_code']}")
        print(f"{'='*60}")
    
    # Test with document upload
    print(f"\n{'='*60}")
    print("SIMULATING DOCUMENT UPLOAD")
    result = handler.process_message(session_id, "uploaded", has_uploaded_docs=True)
    print(f"STAGE: {result['previous_stage']} → {result['current_stage']}")
    print(f"{'='*60}")
    
    # Clean up
    handler.reset_session(session_id)
    
    print("\n" + "=" * 60)
    print("HANDLER TEST COMPLETE")
    print("=" * 60)
