"""
================================================================================
PHASE 5: OFFER DISCOVERY AND DYNAMIC INTEREST RATE DETERMINATION
================================================================================

This module handles pre-approved offer lookup and calculates interest rate RANGES
based on credit profile. Interest rates are NEVER fixed - they are always ranges.

================================================================================
WHY INTEREST RATE IS A RANGE (NOT A FIXED NUMBER)
================================================================================

REAL-WORLD NBFC PRACTICE:
   NBFCs never quote a single interest rate upfront. They provide indicative
   ranges because final pricing depends on:
   - Complete income verification
   - Debt-to-income ratio
   - Employment stability
   - Relationship value
   - Market conditions

REGULATORY COMPLIANCE:
   RBI guidelines require transparent disclosure of rate ranges.
   Promising a fixed rate before underwriting is misleading.

NEGOTIATION FLEXIBILITY:
   Range allows relationship managers to:
   - Reward loyalty
   - Match competitor offers
   - Adjust for risk factors discovered later

================================================================================
HOW CREDIT BANDS AFFECT PRICING
================================================================================

Credit scoring is the PRIMARY factor in interest rate determination:

BAND A (≥800): Prime customers
   - Lowest default risk
   - Base range: 10.5% – 11.5%
   - Eligible for premium offers

BAND B (750-799): Near-prime customers
   - Low default risk
   - Base range: 11.5% – 12.5%
   - Standard offers

BAND C (700-749): Standard customers
   - Moderate risk
   - Base range: 12.5% – 14.0%
   - May require additional documentation

BAND D (<700): Subprime customers
   - Higher risk
   - Not outright rejected (underwriting decides)
   - Flagged for manual review

================================================================================
WHY FINAL RATE IS DECIDED IN UNDERWRITING (NOT HERE)
================================================================================

This stage provides INDICATIVE rates. Final rate is determined in UNDERWRITING:

1. Income verification may reveal higher/lower capacity
2. Debt-to-income ratio affects risk pricing
3. Employment stability adds/removes risk premium
4. Document quality affects confidence in data
5. Relationship history may warrant loyalty discounts

The LLM MUST present rates as indicative, not final.

================================================================================
"""

import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass

# ================================================================================
# LOGGING CONFIGURATION
# ================================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | OFFER_DISCOVERY | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('offer_discovery')


# ================================================================================
# DATA STRUCTURES
# ================================================================================

@dataclass
class OfferMartResponse:
    """Response from Offer Mart API lookup."""
    customer_id: Optional[str]
    mobile_number: str
    existing_customer: bool
    preapproved_limit_inr: int
    preapproved_offer: bool
    lookup_timestamp: str


@dataclass
class CreditBureauResponse:
    """Response from Credit Bureau API lookup."""
    customer_id: Optional[str]
    mobile_number: str
    credit_score: int
    credit_band: str  # A, B, C, D
    score_date: str
    bureau_name: str


@dataclass
class InterestRateResult:
    """Calculated interest rate range."""
    rate_min: float
    rate_max: float
    band_reason: str
    modifiers_applied: list
    is_eligible: bool
    risk_flag: Optional[str]


# ================================================================================
# MOCK DATA FOR DEMO (DETERMINISTIC)
# ================================================================================
# These are deterministic test cases for demo/development.
# In production, these would be replaced with actual API calls.

# Offer Mart Database: Mobile -> (existing_customer, preapproved_limit)
OFFER_MART_DATABASE: Dict[str, Tuple[bool, int]] = {
    # Existing customers with pre-approved offers
    "9876543210": (True, 500000),    # Existing, ₹5L pre-approved
    "9876543211": (True, 750000),    # Existing, ₹7.5L pre-approved
    "9876543212": (True, 1000000),   # Existing, ₹10L pre-approved
    "9876543213": (True, 300000),    # Existing, ₹3L pre-approved
    
    # Existing customers without pre-approved offers
    "9876543220": (True, 0),         # Existing, no pre-approved offer
    "9876543221": (True, 0),         # Existing, no pre-approved offer
    
    # New customers (not in system)
    # Any mobile not in this dict is treated as new customer
}

# Credit Bureau Database: Mobile -> credit_score
# In production, this would call actual bureaus like CIBIL, Experian, etc.
CREDIT_BUREAU_DATABASE: Dict[str, int] = {
    # Excellent credit (Band A: ≥800)
    "9876543210": 825,
    "9876543211": 810,
    
    # Good credit (Band B: 750-799)
    "9876543212": 780,
    "9876543213": 755,
    "9876543220": 765,
    
    # Fair credit (Band C: 700-749)
    "9876543221": 720,
    "9876543230": 710,
    "9876543231": 705,
    
    # Poor credit (Band D: <700)
    "9876543240": 680,
    "9876543241": 650,
    "9876543242": 620,
}

# Default credit score for unknown customers (simulates bureau lookup)
DEFAULT_CREDIT_SCORE = 725  # Middle of Band C


# ================================================================================
# CREDIT SCORE BANDS
# ================================================================================
# These bands determine base interest rate ranges

CREDIT_BANDS = {
    "A": {
        "min_score": 800,
        "max_score": 900,
        "base_rate_min": 10.5,
        "base_rate_max": 11.5,
        "description": "Excellent credit - Prime customer"
    },
    "B": {
        "min_score": 750,
        "max_score": 799,
        "base_rate_min": 11.5,
        "base_rate_max": 12.5,
        "description": "Good credit - Near-prime customer"
    },
    "C": {
        "min_score": 700,
        "max_score": 749,
        "base_rate_min": 12.5,
        "base_rate_max": 14.0,
        "description": "Fair credit - Standard customer"
    },
    "D": {
        "min_score": 0,
        "max_score": 699,
        "base_rate_min": 14.0,
        "base_rate_max": 18.0,
        "description": "Below average credit - Higher risk"
    }
}

# Rate modifiers (reductions for favorable factors)
EXISTING_CUSTOMER_DISCOUNT = 0.25  # 0.25% reduction
PREAPPROVED_OFFER_DISCOUNT = 0.25  # Additional 0.25% reduction


# ================================================================================
# ENTRY CONDITION CHECK
# ================================================================================

def can_start_offer_discovery(
    kyc_status: Optional[str],
    pan_verified: bool,
    aadhaar_verified: bool
) -> Tuple[bool, str]:
    """
    Check if OFFER_DISCOVERY stage entry conditions are met.
    
    STRICT ENTRY CONDITIONS (Phase 5):
    1. KYC status must be VERIFIED
    2. PAN must be verified
    3. Aadhaar must be verified
    
    Args:
        kyc_status: Current KYC verification status
        pan_verified: Whether PAN has been verified
        aadhaar_verified: Whether Aadhaar has been verified
        
    Returns:
        Tuple of (can_proceed, reason)
    """
    if kyc_status != "VERIFIED":
        return False, f"KYC not verified. Status: {kyc_status}"
    
    if not pan_verified:
        return False, "PAN not verified. Cannot proceed with offer discovery."
    
    if not aadhaar_verified:
        return False, "Aadhaar not verified. Cannot proceed with offer discovery."
    
    return True, ""


# ================================================================================
# OFFER MART API (MOCK)
# ================================================================================

def lookup_offer_mart(
    mobile_number: str,
    customer_id: Optional[str] = None
) -> OfferMartResponse:
    """
    Look up customer in Offer Mart to check for pre-approved offers.
    
    This is a DETERMINISTIC lookup:
    - Same mobile always returns same result
    - LLM has NO role in determining outcome
    
    In production, this would call actual Offer Mart API.
    
    Args:
        mobile_number: Customer's verified mobile number
        customer_id: Optional customer ID for faster lookup
        
    Returns:
        OfferMartResponse with offer details
    """
    timestamp = datetime.now().isoformat()
    
    logger.info(f"Offer Mart API called for mobile: ****{mobile_number[-4:]}")
    
    # Normalize mobile number
    mobile = mobile_number.strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+91"):
        mobile = mobile[3:]
    if mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]
    
    # Lookup in mock database
    if mobile in OFFER_MART_DATABASE:
        existing, preapproved_limit = OFFER_MART_DATABASE[mobile]
        
        logger.info(f"Pre-approved limit: ₹{preapproved_limit:,}" if preapproved_limit > 0 
                   else "No pre-approved offer")
        
        return OfferMartResponse(
            customer_id=customer_id or f"CUST_{mobile[-6:]}",
            mobile_number=mobile,
            existing_customer=existing,
            preapproved_limit_inr=preapproved_limit,
            preapproved_offer=preapproved_limit > 0,
            lookup_timestamp=timestamp
        )
    
    # New customer - not in system
    logger.info("New customer - not found in Offer Mart")
    
    return OfferMartResponse(
        customer_id=None,
        mobile_number=mobile,
        existing_customer=False,
        preapproved_limit_inr=0,
        preapproved_offer=False,
        lookup_timestamp=timestamp
    )


# ================================================================================
# CREDIT BUREAU API (MOCK)
# ================================================================================

def lookup_credit_bureau(
    mobile_number: str,
    customer_id: Optional[str] = None
) -> CreditBureauResponse:
    """
    Look up customer's credit score from Credit Bureau.
    
    This is a DETERMINISTIC lookup:
    - Same mobile always returns same score
    - LLM CANNOT invent or modify credit scores
    
    In production, this would call actual bureaus (CIBIL, Experian, etc.)
    
    Args:
        mobile_number: Customer's verified mobile number
        customer_id: Optional customer ID
        
    Returns:
        CreditBureauResponse with credit score and band
    """
    timestamp = datetime.now().isoformat()
    
    logger.info(f"Credit Bureau API called for mobile: ****{mobile_number[-4:]}")
    
    # Normalize mobile number
    mobile = mobile_number.strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+91"):
        mobile = mobile[3:]
    if mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]
    
    # Lookup in mock database
    if mobile in CREDIT_BUREAU_DATABASE:
        credit_score = CREDIT_BUREAU_DATABASE[mobile]
    else:
        # Unknown customer - assign default score
        credit_score = DEFAULT_CREDIT_SCORE
    
    # Determine credit band
    credit_band = get_credit_band(credit_score)
    
    logger.info(f"Credit score: {credit_score} (Band {credit_band})")
    
    return CreditBureauResponse(
        customer_id=customer_id,
        mobile_number=mobile,
        credit_score=credit_score,
        credit_band=credit_band,
        score_date=timestamp,
        bureau_name="Mock Credit Bureau"
    )


def get_credit_band(credit_score: int) -> str:
    """
    Determine credit band from score.
    
    Args:
        credit_score: Customer's credit score
        
    Returns:
        Band letter (A, B, C, or D)
    """
    if credit_score >= 800:
        return "A"
    elif credit_score >= 750:
        return "B"
    elif credit_score >= 700:
        return "C"
    else:
        return "D"


# ================================================================================
# INTEREST RATE CALCULATION
# ================================================================================

def calculate_interest_rate_range(
    credit_score: int,
    existing_customer: bool,
    preapproved_offer: bool
) -> InterestRateResult:
    """
    Calculate interest rate RANGE based on credit profile.
    
    CRITICAL: This returns a RANGE, never a single number.
    Final rate is determined in UNDERWRITING, not here.
    
    The range is calculated as:
    1. Start with base range from credit band
    2. Apply modifiers (existing customer, pre-approved offer)
    3. Return final range with explanation
    
    Args:
        credit_score: Customer's credit score
        existing_customer: Whether customer exists in system
        preapproved_offer: Whether customer has pre-approved offer
        
    Returns:
        InterestRateResult with rate range and reasoning
    """
    logger.info(f"Credit score band identified: {get_credit_band(credit_score)}")
    
    # Get credit band
    band = get_credit_band(credit_score)
    band_config = CREDIT_BANDS[band]
    
    # Start with base range
    rate_min = band_config["base_rate_min"]
    rate_max = band_config["base_rate_max"]
    
    modifiers = []
    
    # Apply existing customer discount
    if existing_customer:
        rate_min -= EXISTING_CUSTOMER_DISCOUNT
        rate_max -= EXISTING_CUSTOMER_DISCOUNT
        modifiers.append(f"Existing customer discount: -{EXISTING_CUSTOMER_DISCOUNT}%")
    
    # Apply pre-approved offer discount
    if preapproved_offer:
        rate_min -= PREAPPROVED_OFFER_DISCOUNT
        rate_max -= PREAPPROVED_OFFER_DISCOUNT
        modifiers.append(f"Pre-approved offer discount: -{PREAPPROVED_OFFER_DISCOUNT}%")
    
    # Determine eligibility and risk flags
    is_eligible = True
    risk_flag = None
    
    if band == "D":
        # Don't reject, but flag for manual review
        risk_flag = "Below average credit - requires manual underwriting review"
        is_eligible = True  # Still eligible, but flagged
    
    # Build reasoning
    band_reason = f"Credit Band {band}: {band_config['description']}"
    if modifiers:
        band_reason += f". Modifiers: {', '.join(modifiers)}"
    
    logger.info(f"Interest rate range calculated: {rate_min:.2f}% – {rate_max:.2f}%")
    
    return InterestRateResult(
        rate_min=round(rate_min, 2),
        rate_max=round(rate_max, 2),
        band_reason=band_reason,
        modifiers_applied=modifiers,
        is_eligible=is_eligible,
        risk_flag=risk_flag
    )


# ================================================================================
# MAIN OFFER DISCOVERY FUNCTION
# ================================================================================

def perform_offer_discovery(
    mobile_number: str,
    customer_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Perform complete offer discovery for a customer.
    
    This is the main entry point for Phase 5 offer discovery.
    It combines Offer Mart lookup, Credit Bureau lookup, and
    interest rate calculation.
    
    Args:
        mobile_number: Customer's verified mobile number
        customer_id: Optional customer ID
        
    Returns:
        Dictionary with all offer discovery results
    """
    logger.info("=" * 60)
    logger.info("PHASE 5: OFFER DISCOVERY STARTED")
    logger.info("=" * 60)
    
    # Step 1: Offer Mart lookup
    offer_response = lookup_offer_mart(mobile_number, customer_id)
    
    # Step 2: Credit Bureau lookup
    credit_response = lookup_credit_bureau(mobile_number, customer_id)
    
    # Step 3: Calculate interest rate range
    rate_result = calculate_interest_rate_range(
        credit_score=credit_response.credit_score,
        existing_customer=offer_response.existing_customer,
        preapproved_offer=offer_response.preapproved_offer
    )
    
    logger.info("=" * 60)
    logger.info("PHASE 5: OFFER DISCOVERY COMPLETED")
    logger.info("=" * 60)
    
    return {
        # Offer Mart results
        "existing_customer": offer_response.existing_customer,
        "preapproved_limit_inr": offer_response.preapproved_limit_inr,
        "preapproved_offer": offer_response.preapproved_offer,
        "customer_id": offer_response.customer_id,
        
        # Credit Bureau results
        "credit_score": credit_response.credit_score,
        "credit_band": credit_response.credit_band,
        
        # Interest rate range
        "interest_rate_min": rate_result.rate_min,
        "interest_rate_max": rate_result.rate_max,
        "interest_rate_band_reason": rate_result.band_reason,
        
        # Eligibility
        "is_eligible": rate_result.is_eligible,
        "risk_flag": rate_result.risk_flag,
        
        # Timestamps
        "offer_lookup_timestamp": offer_response.lookup_timestamp,
        "credit_lookup_timestamp": credit_response.score_date,
    }


# ================================================================================
# LLM RESPONSE FORMATTING
# ================================================================================

def format_offer_response_for_llm(
    user_name: str,
    discovery_result: Dict[str, Any],
    loan_amount: Optional[int] = None
) -> str:
    """
    Format offer discovery results for LLM to present to user.
    
    CRITICAL: This formats the response in an INDICATIVE manner.
    LLM must NOT promise final rates.
    
    Args:
        user_name: Customer's name
        discovery_result: Results from perform_offer_discovery()
        loan_amount: Requested loan amount (if known)
        
    Returns:
        Formatted string for LLM to use in response
    """
    rate_min = discovery_result["interest_rate_min"]
    rate_max = discovery_result["interest_rate_max"]
    existing = discovery_result["existing_customer"]
    preapproved = discovery_result["preapproved_offer"]
    preapproved_limit = discovery_result["preapproved_limit_inr"]
    
    # Build response parts
    parts = []
    
    # Greeting based on customer type
    if existing and preapproved:
        parts.append(f"Great news, {user_name}! 🎉 As a valued existing customer, you have a pre-approved loan offer of up to ₹{preapproved_limit:,}.")
    elif existing:
        parts.append(f"Welcome back, {user_name}! Good to see you again. I've checked your profile.")
    else:
        parts.append(f"Thank you, {user_name}! I've reviewed your profile.")
    
    # Interest rate presentation (INDICATIVE, not final)
    parts.append(f"\nBased on your credit profile, your indicative interest rate would be in the range of **{rate_min}% – {rate_max}% per annum**.")
    
    # Explain what this means
    parts.append("\nThis is an indicative range — the final rate will be determined after income verification. I'll work to get you the best possible rate during the final evaluation.")
    
    # Risk flag if applicable
    if discovery_result.get("risk_flag"):
        parts.append("\n⚠️ Note: Your application may require additional review.")
    
    # Next step
    parts.append("\nTo proceed with your application, I'll need to verify your income. Would you like to continue?")
    
    return "\n".join(parts)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("PHASE 5: OFFER DISCOVERY MODULE TEST")
    print("=" * 70)
    
    # Test 1: Existing customer with pre-approved offer and excellent credit
    print("\n--- Test 1: Existing customer with pre-approved offer (Band A) ---")
    result = perform_offer_discovery("9876543210")
    print(f"Existing: {result['existing_customer']}, Pre-approved: ₹{result['preapproved_limit_inr']:,}")
    print(f"Credit Score: {result['credit_score']} (Band {result['credit_band']})")
    print(f"Interest Range: {result['interest_rate_min']}% – {result['interest_rate_max']}%")
    print(f"Reason: {result['interest_rate_band_reason']}")
    assert result['existing_customer'] == True
    assert result['preapproved_limit_inr'] == 500000
    assert result['interest_rate_min'] < result['interest_rate_max']
    
    # Test 2: Existing customer without pre-approved offer (Band B)
    print("\n--- Test 2: Existing customer, no pre-approved offer (Band B) ---")
    result = perform_offer_discovery("9876543220")
    print(f"Existing: {result['existing_customer']}, Pre-approved: ₹{result['preapproved_limit_inr']:,}")
    print(f"Credit Score: {result['credit_score']} (Band {result['credit_band']})")
    print(f"Interest Range: {result['interest_rate_min']}% – {result['interest_rate_max']}%")
    assert result['existing_customer'] == True
    assert result['preapproved_limit_inr'] == 0
    
    # Test 3: New customer (Band C - default)
    print("\n--- Test 3: New customer (Band C default) ---")
    result = perform_offer_discovery("9999999999")
    print(f"Existing: {result['existing_customer']}, Pre-approved: ₹{result['preapproved_limit_inr']:,}")
    print(f"Credit Score: {result['credit_score']} (Band {result['credit_band']})")
    print(f"Interest Range: {result['interest_rate_min']}% – {result['interest_rate_max']}%")
    assert result['existing_customer'] == False
    assert result['credit_score'] == DEFAULT_CREDIT_SCORE
    
    # Test 4: Customer with poor credit (Band D)
    print("\n--- Test 4: Customer with poor credit (Band D) ---")
    result = perform_offer_discovery("9876543240")
    print(f"Credit Score: {result['credit_score']} (Band {result['credit_band']})")
    print(f"Interest Range: {result['interest_rate_min']}% – {result['interest_rate_max']}%")
    print(f"Risk Flag: {result['risk_flag']}")
    assert result['credit_band'] == "D"
    assert result['risk_flag'] is not None
    assert result['is_eligible'] == True  # Not rejected, just flagged
    
    # Test 5: Entry conditions
    print("\n--- Test 5: Entry conditions ---")
    can_proceed, reason = can_start_offer_discovery("VERIFIED", True, True)
    print(f"All conditions met: {can_proceed}")
    assert can_proceed == True
    
    can_proceed, reason = can_start_offer_discovery("PENDING", True, True)
    print(f"KYC not verified: {can_proceed}, Reason: {reason}")
    assert can_proceed == False
    
    # Test 6: LLM response formatting
    print("\n--- Test 6: LLM response formatting ---")
    result = perform_offer_discovery("9876543210")
    response = format_offer_response_for_llm("Rahul", result)
    print(response)
    assert "indicative" in response.lower()
    assert "10.0%" in response or "10.00%" in response  # Discounted rate
    
    print("\n" + "=" * 70)
    print("ALL OFFER DISCOVERY MODULE TESTS PASSED!")
    print("=" * 70)
