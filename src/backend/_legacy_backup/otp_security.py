"""
================================================================================
PHASE 3: SECURE OTP VERIFICATION MODULE
================================================================================

This module handles secure OTP generation and verification for identity locking.

================================================================================
WHY OTP PRECEDES KYC VERIFICATION
================================================================================

SECURITY PRINCIPLE: Identity must be LOCKED before any verification occurs.

1. IDENTITY LOCKING prevents:
   - Fraudsters impersonating legitimate customers
   - Session hijacking attacks
   - Data harvesting without authentication

2. SEQUENCE is non-negotiable:
   - User provides Name + Mobile → KYC_COLLECTION (data collection ONLY)
   - OTP is sent to mobile → OTP_VERIFICATION (authentication)
   - OTP is verified → KYC_VERIFICATION (CRM lookup ALLOWED)
   
   CRM lookup MUST NEVER happen before OTP is verified.

================================================================================
HOW IDENTITY LOCKING PREVENTS FRAUD
================================================================================

WITHOUT identity locking:
   - Attacker enters victim's mobile number
   - System fetches victim's data from CRM (credit score, income, offers)
   - Attacker gathers sensitive data without any authentication
   - This is a MASSIVE privacy and security breach

WITH identity locking (Phase 3):
   - Attacker enters victim's mobile number
   - System generates OTP sent to victim's phone
   - Attacker cannot proceed without OTP
   - Victim's data is NEVER exposed to attacker

================================================================================
WHY LLM MUST NEVER CONTROL OTP LOGIC
================================================================================

LLMs are:
   - Non-deterministic: Same input can produce different outputs
   - Prompt-injectable: Malicious prompts can bypass security
   - Context-manipulable: Crafted history can trick validation

OTP verification MUST be:
   - Deterministic: Same OTP + same stored OTP = always match (or not)
   - Immutable: No prompt can bypass the check
   - Auditable: Every attempt is logged with timestamp

Therefore:
   - OTP generation: Python random.choices (NOT LLM)
   - OTP comparison: Python string equality (NOT LLM interpretation)
   - Attempt tracking: Integer counter (NOT LLM memory)

================================================================================
"""

import random
import string
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

# ================================================================================
# CONFIGURATION CONSTANTS
# ================================================================================

# Maximum number of OTP verification attempts before lockout
MAX_OTP_ATTEMPTS = 3

# OTP length (6 digits for security)
OTP_LENGTH = 6

# Test users for demo/development (predictable OTPs)
TEST_USERS_OTP: Dict[str, str] = {
    "9876543210": "123456",  # Rahul Mehta - Demo user
    "9988776655": "123456",  # Amit Verma - Demo user
    "9123456781": "123456",  # Priya Sharma - Demo user
}

# ================================================================================
# LOGGING CONFIGURATION
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | OTP_SECURITY | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('otp_security')


# ================================================================================
# OTP GENERATION
# ================================================================================

def generate_otp(mobile_number: str) -> Tuple[str, str]:
    """
    Generate a secure 6-digit OTP for the given mobile number.
    
    ================================================================================
    SECURITY DESIGN
    ================================================================================
    
    1. This function is DETERMINISTIC for test users (predictable for demos)
    2. For non-test users, generates RANDOM 6-digit OTP
    3. Returns OTP + timestamp for expiry tracking
    4. LLM has NO role in OTP generation
    
    ================================================================================
    
    Args:
        mobile_number: 10-digit mobile number
        
    Returns:
        Tuple of (otp_code, generation_timestamp)
    """
    timestamp = datetime.now().isoformat()
    
    # Check if this is a test user (for demo purposes)
    if mobile_number in TEST_USERS_OTP:
        otp = TEST_USERS_OTP[mobile_number]
        logger.info(f"OTP generated for TEST user: {mobile_number} → {otp}")
    else:
        # Generate random 6-digit OTP for non-test users
        otp = ''.join(random.choices(string.digits, k=OTP_LENGTH))
        logger.info(f"OTP generated for user: {mobile_number} → {otp}")
    
    return otp, timestamp


def verify_otp(
    entered_otp: str,
    stored_otp: str,
    current_attempts: int
) -> Tuple[bool, str, int]:
    """
    Verify an OTP attempt against the stored OTP.
    
    ================================================================================
    SECURITY DESIGN
    ================================================================================
    
    1. DETERMINISTIC comparison: Python string equality (NOT LLM)
    2. Attempt counting: Integer increment (NOT LLM memory)
    3. Lockout after MAX_OTP_ATTEMPTS failures
    4. Returns clear success/failure with attempt count
    
    ================================================================================
    
    CRITICAL: This function performs EXACT string matching.
    The LLM is NOT involved in OTP verification.
    
    ================================================================================
    
    Args:
        entered_otp: OTP entered by user
        stored_otp: OTP stored in session state
        current_attempts: Number of previous failed attempts
        
    Returns:
        Tuple of (is_verified, message, new_attempt_count)
    """
    # Normalize inputs
    entered_otp = str(entered_otp).strip()
    stored_otp = str(stored_otp).strip()
    
    # Check if already exceeded attempts
    if current_attempts >= MAX_OTP_ATTEMPTS:
        logger.warning(f"OTP verification blocked: Max attempts ({MAX_OTP_ATTEMPTS}) exceeded")
        return False, "Maximum OTP attempts exceeded. Please request a new OTP.", current_attempts
    
    # DETERMINISTIC OTP verification - exact string match
    if entered_otp == stored_otp:
        logger.info(f"OTP verified successfully!")
        return True, "OTP verified successfully.", current_attempts
    else:
        new_attempts = current_attempts + 1
        remaining = MAX_OTP_ATTEMPTS - new_attempts
        
        if remaining > 0:
            logger.warning(f"Wrong OTP entered (attempt {new_attempts}/{MAX_OTP_ATTEMPTS})")
            return False, f"Incorrect OTP. You have {remaining} attempt(s) remaining.", new_attempts
        else:
            logger.warning(f"OTP verification failed: Max attempts reached")
            return False, "Maximum OTP attempts exceeded. Please request a new OTP.", new_attempts


def can_verify_otp(otp_attempts: int) -> bool:
    """
    Check if user can still attempt OTP verification.
    
    Args:
        otp_attempts: Current number of failed attempts
        
    Returns:
        True if attempts remaining, False if locked out
    """
    return otp_attempts < MAX_OTP_ATTEMPTS


def get_remaining_attempts(otp_attempts: int) -> int:
    """
    Get the number of remaining OTP attempts.
    
    Args:
        otp_attempts: Current number of failed attempts
        
    Returns:
        Number of remaining attempts (0 if locked out)
    """
    return max(0, MAX_OTP_ATTEMPTS - otp_attempts)


# ================================================================================
# GATING FUNCTIONS
# ================================================================================

def is_otp_verified(otp_verified: bool) -> bool:
    """
    Check if OTP has been verified for this session.
    
    ================================================================================
    GATING RULE
    ================================================================================
    
    This is the ONLY function that determines if KYC_VERIFICATION can proceed.
    
    KYC_VERIFICATION stage REQUIRES:
        is_otp_verified(state.otp_verified) == True
    
    If False, the system MUST NOT:
        - Perform CRM lookup
        - Fetch customer data
        - Show pre-approved offers
        - Proceed to any stage beyond OTP_VERIFICATION
    
    ================================================================================
    
    Args:
        otp_verified: The otp_verified field from session state
        
    Returns:
        True if OTP verified, False otherwise
    """
    return otp_verified is True


def can_proceed_to_kyc_verification(otp_verified: bool, otp_attempts: int) -> Tuple[bool, str]:
    """
    Determine if session can proceed to KYC_VERIFICATION stage.
    
    ================================================================================
    STRICT GATING RULE - NON-NEGOTIABLE
    ================================================================================
    
    KYC_VERIFICATION is ONLY accessible when:
        1. otp_verified == True
        2. otp_attempts < MAX_OTP_ATTEMPTS (not locked out)
    
    This function is called BEFORE any CRM lookup.
    
    ================================================================================
    
    Args:
        otp_verified: Whether OTP has been verified
        otp_attempts: Number of OTP attempts made
        
    Returns:
        Tuple of (can_proceed, reason)
    """
    if otp_attempts >= MAX_OTP_ATTEMPTS:
        return False, "OTP verification locked out. Too many failed attempts."
    
    if not otp_verified:
        return False, "OTP not verified. Cannot proceed to KYC verification."
    
    return True, "OTP verified. KYC verification allowed."


# ================================================================================
# SIMULATE OTP SENDING (Demo Only)
# ================================================================================

def simulate_otp_send(mobile_number: str, otp_code: str) -> str:
    """
    Simulate sending OTP to mobile number.
    
    In production, this would integrate with an SMS gateway.
    For demo purposes, this just logs and returns a message.
    
    Args:
        mobile_number: Mobile number to send OTP to
        otp_code: The OTP code to send
        
    Returns:
        Status message
    """
    logger.info(f"SIMULATING OTP SEND: {otp_code} to {mobile_number}")
    return f"OTP sent to mobile number ending in ***{mobile_number[-4:]}"


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 3: OTP SECURITY MODULE TEST")
    print("=" * 60)
    
    # Test 1: Generate OTP for test user
    print("\n--- Test 1: Generate OTP (test user) ---")
    otp, ts = generate_otp("9876543210")
    print(f"OTP: {otp}, Timestamp: {ts}")
    assert otp == "123456", "Test user should get predictable OTP"
    
    # Test 2: Generate OTP for non-test user
    print("\n--- Test 2: Generate OTP (random user) ---")
    otp, ts = generate_otp("9999999999")
    print(f"OTP: {otp}, Timestamp: {ts}")
    assert len(otp) == 6 and otp.isdigit(), "OTP should be 6 digits"
    
    # Test 3: Verify correct OTP
    print("\n--- Test 3: Verify correct OTP ---")
    success, msg, attempts = verify_otp("123456", "123456", 0)
    print(f"Result: {success}, Message: {msg}, Attempts: {attempts}")
    assert success is True, "Correct OTP should verify"
    
    # Test 4: Verify wrong OTP
    print("\n--- Test 4: Verify wrong OTP ---")
    success, msg, attempts = verify_otp("000000", "123456", 0)
    print(f"Result: {success}, Message: {msg}, Attempts: {attempts}")
    assert success is False, "Wrong OTP should fail"
    assert attempts == 1, "Attempts should increment"
    
    # Test 5: Max attempts exceeded
    print("\n--- Test 5: Max attempts exceeded ---")
    success, msg, attempts = verify_otp("000000", "123456", 3)
    print(f"Result: {success}, Message: {msg}, Attempts: {attempts}")
    assert success is False, "Should be locked out"
    
    # Test 6: Gating check
    print("\n--- Test 6: Gating check ---")
    can_proceed, reason = can_proceed_to_kyc_verification(True, 0)
    print(f"Can proceed: {can_proceed}, Reason: {reason}")
    assert can_proceed is True, "Should allow with verified OTP"
    
    can_proceed, reason = can_proceed_to_kyc_verification(False, 0)
    print(f"Can proceed: {can_proceed}, Reason: {reason}")
    assert can_proceed is False, "Should block without OTP"
    
    print("\n" + "=" * 60)
    print("ALL OTP SECURITY TESTS PASSED!")
    print("=" * 60)
