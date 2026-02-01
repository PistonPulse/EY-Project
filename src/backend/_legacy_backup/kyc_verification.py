"""
================================================================================
PHASE 4: DETERMINISTIC PAN AND AADHAAR VERIFICATION MODULE
================================================================================

This module handles secure, deterministic PAN and Aadhaar verification for KYC.

================================================================================
WHY PAN VERIFICATION PRECEDES AADHAAR VERIFICATION
================================================================================

REGULATORY COMPLIANCE:
   PAN (Permanent Account Number) is the primary financial identifier in India.
   It is issued by the Income Tax Department and links all financial transactions.
   Verifying PAN first establishes the user's tax identity before proceeding.

FRAUD PREVENTION:
   1. PAN verification confirms the user has a valid tax identity
   2. This prevents fraudsters from using stolen Aadhaar numbers
   3. PAN-Aadhaar linkage can be cross-verified

SEQUENCE:
   1. User enters PAN → format validation → CRM API verification
   2. ONLY if PAN verified → Ask for Aadhaar
   3. User enters Aadhaar → format validation → KYC API verification
   4. ONLY if both verified → KYC complete

================================================================================
WHY VERIFICATION MUST BE SEQUENTIAL (NOT PARALLEL)
================================================================================

1. DEPENDENCY CHAIN:
   - Aadhaar verification may depend on PAN verification results
   - Some fraud patterns require seeing one ID before the other

2. ERROR HANDLING:
   - If PAN fails, no need to attempt Aadhaar verification
   - Cleaner failure states and error messages

3. USER EXPERIENCE:
   - Sequential flow feels more human and deliberate
   - Users understand each step is being verified

4. AUDIT TRAIL:
   - Each verification has its own timestamp
   - Can trace exactly which step failed and when

================================================================================
HOW DETERMINISTIC APIS PREVENT HALLUCINATION
================================================================================

WITHOUT deterministic APIs:
   - LLM might "decide" verification passed based on patterns
   - Prompt injection could bypass verification ("assume PAN is verified")
   - Non-deterministic responses could approve invalid documents

WITH deterministic APIs (this module):
   - Verification result is a FIXED mapping: input → output
   - Test users have predetermined results (for demo)
   - Production would call actual NSDL/UIDAI APIs
   - LLM has NO role in determining verification outcome

================================================================================
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

# ================================================================================
# LOGGING CONFIGURATION
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | KYC_VERIFICATION | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('kyc_verification')


# ================================================================================
# VERIFICATION STATUS ENUM
# ================================================================================

class VerificationStatus:
    """Possible verification statuses."""
    VERIFIED = "VERIFIED"
    NOT_FOUND = "NOT_FOUND"
    FORMAT_INVALID = "FORMAT_INVALID"
    PENDING = "PENDING"


# ================================================================================
# VERIFICATION RESULT DATACLASS
# ================================================================================

@dataclass
class VerificationResult:
    """Result of a PAN or Aadhaar verification."""
    status: str
    name_on_record: Optional[str] = None
    timestamp: Optional[str] = None
    error_message: Optional[str] = None


# ================================================================================
# TEST DATA FOR DEMO
# ================================================================================
# These are deterministic test cases for demo/development.
# In production, these would be replaced with actual API calls.

# Test PAN numbers and their verification results
# Format: PAN -> (status, name_on_pan)
TEST_PAN_DATABASE: Dict[str, Tuple[str, str]] = {
    "ABCDE1234F": (VerificationStatus.VERIFIED, "Rahul Mehta"),
    "FGHIJ5678K": (VerificationStatus.VERIFIED, "Amit Verma"),
    "KLMNO9012P": (VerificationStatus.VERIFIED, "Priya Sharma"),
    "PQRST3456U": (VerificationStatus.VERIFIED, "Vikram Singh"),
    "UVWXY7890Z": (VerificationStatus.VERIFIED, "Neha Gupta"),
    # Invalid/Not found PANs
    "ZZZZZ0000Z": (VerificationStatus.NOT_FOUND, None),
}

# Test Aadhaar numbers and their verification results
# Format: Aadhaar -> (status, name_on_aadhaar)
TEST_AADHAAR_DATABASE: Dict[str, Tuple[str, str]] = {
    "123456789012": (VerificationStatus.VERIFIED, "Rahul Mehta"),
    "234567890123": (VerificationStatus.VERIFIED, "Amit Verma"),
    "345678901234": (VerificationStatus.VERIFIED, "Priya Sharma"),
    "456789012345": (VerificationStatus.VERIFIED, "Vikram Singh"),
    "567890123456": (VerificationStatus.VERIFIED, "Neha Gupta"),
    # Invalid/Not found Aadhaar
    "000000000000": (VerificationStatus.NOT_FOUND, None),
}


# ================================================================================
# PAN VERIFICATION
# ================================================================================

def validate_pan_format(pan: str) -> Tuple[bool, str]:
    """
    Validate PAN format: AAAAA9999A (5 letters, 4 digits, 1 letter)
    
    Args:
        pan: PAN number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not pan:
        return False, "PAN number is required"
    
    # Normalize: uppercase, remove spaces
    pan = pan.upper().strip().replace(" ", "")
    
    # PAN format: 5 letters + 4 digits + 1 letter
    pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
    
    if not re.match(pan_pattern, pan):
        return False, "Invalid PAN format. PAN should be 10 characters (e.g., ABCDE1234F)"
    
    return True, ""


def verify_pan(pan: str, user_name: str = None) -> VerificationResult:
    """
    Verify PAN against CRM/NSDL mock API.
    
    This is a DETERMINISTIC verification:
    - Same PAN always produces same result
    - LLM has NO role in determining outcome
    - Test PANs have predetermined results
    
    Args:
        pan: PAN number to verify
        user_name: User's name for cross-reference (optional)
        
    Returns:
        VerificationResult with status, name_on_record, timestamp, and error_message
    """
    timestamp = datetime.now().isoformat()
    
    # Normalize PAN
    pan = pan.upper().strip().replace(" ", "")
    
    logger.info(f"PHASE 4: PAN verification started for {pan}")
    
    # Format validation first (no API call for invalid format)
    is_valid, error_msg = validate_pan_format(pan)
    if not is_valid:
        logger.warning(f"PHASE 4: PAN format invalid: {error_msg}")
        return VerificationResult(
            status=VerificationStatus.FORMAT_INVALID,
            name_on_record=None,
            timestamp=timestamp,
            error_message=error_msg
        )
    
    # Check against test database (deterministic)
    if pan in TEST_PAN_DATABASE:
        status, name = TEST_PAN_DATABASE[pan]
        logger.info(f"PHASE 4: PAN verification result: {status}")
        return VerificationResult(
            status=status,
            name_on_record=name,
            timestamp=timestamp,
            error_message=None
        )
    
    # For any PAN not in test database, simulate NOT_FOUND
    # In production, this would call actual NSDL API
    logger.info(f"PHASE 4: PAN verification result: NOT_FOUND (not in test database)")
    return VerificationResult(
        status=VerificationStatus.NOT_FOUND,
        name_on_record=None,
        timestamp=timestamp,
        error_message="PAN not found in government records"
    )


# ================================================================================
# AADHAAR VERIFICATION
# ================================================================================

def validate_aadhaar_format(aadhaar: str) -> Tuple[bool, str]:
    """
    Validate Aadhaar format: 12 digits
    
    Args:
        aadhaar: Aadhaar number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not aadhaar:
        return False, "Aadhaar number is required"
    
    # Normalize: remove spaces, dashes
    aadhaar = aadhaar.strip().replace(" ", "").replace("-", "")
    
    # Aadhaar format: exactly 12 digits
    if not re.match(r'^\d{12}$', aadhaar):
        return False, "Invalid Aadhaar format. Aadhaar should be 12 digits"
    
    return True, ""


def verify_aadhaar(aadhaar: str, user_name: str = None) -> VerificationResult:
    """
    Verify Aadhaar against UIDAI mock API.
    
    This is a DETERMINISTIC verification:
    - Same Aadhaar always produces same result
    - LLM has NO role in determining outcome
    - Test Aadhaar numbers have predetermined results
    
    Args:
        aadhaar: Aadhaar number to verify
        user_name: User's name for cross-reference (optional)
        
    Returns:
        VerificationResult with status, name_on_record, timestamp, and error_message
    """
    timestamp = datetime.now().isoformat()
    
    # Normalize Aadhaar
    aadhaar = aadhaar.strip().replace(" ", "").replace("-", "")
    
    logger.info(f"PHASE 4: Aadhaar verification started for ****{aadhaar[-4:]}")
    
    # Format validation first (no API call for invalid format)
    is_valid, error_msg = validate_aadhaar_format(aadhaar)
    if not is_valid:
        logger.warning(f"PHASE 4: Aadhaar format invalid: {error_msg}")
        return VerificationResult(
            status=VerificationStatus.FORMAT_INVALID,
            name_on_record=None,
            timestamp=timestamp,
            error_message=error_msg
        )
    
    # Check against test database (deterministic)
    if aadhaar in TEST_AADHAAR_DATABASE:
        status, name = TEST_AADHAAR_DATABASE[aadhaar]
        logger.info(f"PHASE 4: Aadhaar verification result: {status}")
        return VerificationResult(
            status=status,
            name_on_record=name,
            timestamp=timestamp,
            error_message=None
        )
    
    # For any Aadhaar not in test database, simulate NOT_FOUND
    # In production, this would call actual UIDAI API
    logger.info(f"PHASE 4: Aadhaar verification result: NOT_FOUND (not in test database)")
    return VerificationResult(
        status=VerificationStatus.NOT_FOUND,
        name_on_record=None,
        timestamp=timestamp,
        error_message="Aadhaar not found in UIDAI records"
    )


# ================================================================================
# ENTRY CONDITION CHECK
# ================================================================================

def can_start_kyc_verification(
    otp_verified: bool,
    full_name: Optional[str] = None,
    mobile_number: Optional[str] = None,
    user_name: Optional[str] = None,
    user_mobile: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if KYC_VERIFICATION stage entry conditions are met.
    
    STRICT ENTRY CONDITIONS (Phase 4):
    1. OTP must be verified
    2. Full name must be present
    3. Mobile number must be present
    
    Args:
        otp_verified: Whether OTP has been verified
        full_name: User's full name (alternative param)
        mobile_number: User's mobile number (alternative param)
        user_name: User's full name (alternative param)
        user_mobile: User's mobile number (alternative param)
        
    Returns:
        Tuple of (can_proceed, reason)
    """
    # Support both parameter naming conventions
    name = full_name or user_name
    mobile = mobile_number or user_mobile
    
    if not otp_verified:
        return False, "OTP not verified. Cannot proceed with KYC verification."
    
    if not name:
        return False, "Full name is missing. Cannot proceed with KYC verification."
    
    if not mobile:
        return False, "Mobile number is missing. Cannot proceed with KYC verification."
    
    return True, ""


# ================================================================================
# KYC STATUS CHECK
# ================================================================================

def get_kyc_status(
    pan_verified: bool,
    aadhaar_verified: bool
) -> str:
    """
    Determine overall KYC status.
    
    Args:
        pan_verified: Whether PAN is verified
        aadhaar_verified: Whether Aadhaar is verified
        
    Returns:
        KYC status string
    """
    if pan_verified and aadhaar_verified:
        return "VERIFIED"
    elif not pan_verified:
        return "PAN_PENDING"
    else:
        return "AADHAAR_PENDING"


def can_proceed_to_offers(
    pan_verified: bool,
    aadhaar_verified: bool
) -> Tuple[bool, str]:
    """
    Check if KYC is complete and can proceed to offer discovery.
    
    Args:
        pan_verified: Whether PAN is verified
        aadhaar_verified: Whether Aadhaar is verified
        
    Returns:
        Tuple of (can_proceed, reason)
    """
    if not pan_verified:
        return False, "PAN verification pending"
    
    if not aadhaar_verified:
        return False, "Aadhaar verification pending"
    
    return True, "KYC verified. Proceeding to offer discovery."


# ================================================================================
# EXTRACTION UTILITIES
# ================================================================================

def extract_pan_from_message(message: str) -> Optional[str]:
    """
    Extract PAN number from user message.
    
    Args:
        message: User's message
        
    Returns:
        Extracted PAN or None
    """
    # Normalize
    message = message.upper().strip()
    
    # Pattern: 5 letters + 4 digits + 1 letter
    pan_pattern = r'\b([A-Z]{5}[0-9]{4}[A-Z])\b'
    match = re.search(pan_pattern, message)
    
    if match:
        return match.group(1)
    
    # If message is exactly 10 chars and looks like PAN
    if len(message) == 10 and re.match(r'^[A-Z]{5}[0-9]{4}[A-Z]$', message):
        return message
    
    return None


def extract_aadhaar_from_message(message: str) -> Optional[str]:
    """
    Extract Aadhaar number from user message.
    
    Args:
        message: User's message
        
    Returns:
        Extracted Aadhaar or None (normalized to 12 digits)
    """
    # First try to find spaced format (XXXX XXXX XXXX)
    spaced_pattern = r'(\d{4}\s+\d{4}\s+\d{4})'
    spaced_match = re.search(spaced_pattern, message)
    if spaced_match:
        return spaced_match.group(1).replace(" ", "")
    
    # Then try to find 12 consecutive digits
    aadhaar_pattern = r'(\d{12})'
    match = re.search(aadhaar_pattern, message)
    if match:
        return match.group(1)
    
    # If message after cleaning is exactly 12 digits
    cleaned = message.strip().replace(" ", "").replace("-", "")
    if len(cleaned) == 12 and cleaned.isdigit():
        return cleaned
    
    return None


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 4: KYC VERIFICATION MODULE TEST")
    print("=" * 60)
    
    # Test 1: PAN format validation
    print("\n--- Test 1: PAN format validation ---")
    valid, msg = validate_pan_format("ABCDE1234F")
    print(f"ABCDE1234F: Valid={valid}")
    assert valid == True, "Valid PAN should pass"
    
    valid, msg = validate_pan_format("INVALID")
    print(f"INVALID: Valid={valid}, Message={msg}")
    assert valid == False, "Invalid PAN should fail"
    
    # Test 2: PAN verification (now returns VerificationResult)
    print("\n--- Test 2: PAN verification ---")
    result = verify_pan("ABCDE1234F", "Test User")
    print(f"ABCDE1234F: Status={result.status}, Name={result.name_on_record}")
    assert result.status == VerificationStatus.VERIFIED, "Test PAN should verify"
    
    result = verify_pan("ZZZZZ0000Z", "Test User")
    print(f"ZZZZZ0000Z: Status={result.status}")
    assert result.status == VerificationStatus.NOT_FOUND, "Unknown PAN should fail"
    
    # Test 3: Aadhaar format validation
    print("\n--- Test 3: Aadhaar format validation ---")
    valid, msg = validate_aadhaar_format("123456789012")
    print(f"123456789012: Valid={valid}")
    assert valid == True, "Valid Aadhaar should pass"
    
    valid, msg = validate_aadhaar_format("12345")
    print(f"12345: Valid={valid}, Message={msg}")
    assert valid == False, "Invalid Aadhaar should fail"
    
    # Test 4: Aadhaar verification (now returns VerificationResult)
    print("\n--- Test 4: Aadhaar verification ---")
    result = verify_aadhaar("123456789012", "Test User")
    print(f"123456789012: Status={result.status}, Name={result.name_on_record}")
    assert result.status == VerificationStatus.VERIFIED, "Test Aadhaar should verify"
    
    result = verify_aadhaar("000000000000", "Test User")
    print(f"000000000000: Status={result.status}")
    assert result.status == VerificationStatus.NOT_FOUND, "Unknown Aadhaar should fail"
    
    # Test 5: Entry conditions
    print("\n--- Test 5: Entry conditions ---")
    can_proceed, reason = can_start_kyc_verification(
        otp_verified=True, 
        full_name="Rahul", 
        mobile_number="9876543210"
    )
    print(f"All conditions met: {can_proceed}")
    assert can_proceed == True, "Should allow with all conditions"
    
    can_proceed, reason = can_start_kyc_verification(
        otp_verified=False, 
        full_name="Rahul", 
        mobile_number="9876543210"
    )
    print(f"OTP not verified: {can_proceed}, Reason: {reason}")
    assert can_proceed == False, "Should block without OTP"
    
    # Test 6: Extraction
    print("\n--- Test 6: Extraction ---")
    pan = extract_pan_from_message("My PAN is ABCDE1234F")
    print(f"Extract PAN from 'My PAN is ABCDE1234F': {pan}")
    assert pan == "ABCDE1234F", "Should extract PAN"
    
    aadhaar = extract_aadhaar_from_message("1234 5678 9012")
    print(f"Extract Aadhaar from '1234 5678 9012': {aadhaar}")
    assert aadhaar == "123456789012", "Should extract Aadhaar"
    
    aadhaar = extract_aadhaar_from_message("My Aadhaar is 123456789012")
    print(f"Extract Aadhaar from 'My Aadhaar is 123456789012': {aadhaar}")
    assert aadhaar == "123456789012", "Should extract Aadhaar from sentence"
    
    print("\n" + "=" * 60)
    print("ALL KYC VERIFICATION MODULE TESTS PASSED!")
    print("=" * 60)
