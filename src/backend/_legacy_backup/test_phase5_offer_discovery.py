"""
================================================================================
TEST PHASE 5: OFFER DISCOVERY AND DYNAMIC INTEREST RATE DETERMINATION
================================================================================

This test suite validates the offer discovery functionality:
1. Entry conditions (KYC must be complete)
2. Offer Mart lookup (existing customer, pre-approved offers)
3. Credit Bureau lookup (credit score retrieval)
4. Interest rate RANGE calculation (not fixed rates)
5. Credit band determination and modifiers
6. LLM communication (indicative rates only)
7. Stage transition to INCOME_DOC_UPLOAD

================================================================================
CREDIT BANDS AND BASE RATES:
================================================================================
Band A (≥800):    10.5% - 11.5% (Excellent)
Band B (750-799): 11.5% - 12.5% (Good)
Band C (700-749): 12.5% - 14.0% (Fair)
Band D (<700):    14.0% - 18.0% (Needs review, risk_flag set)

MODIFIERS:
- Existing customer: -0.25% off both min and max
- Pre-approved offer: -0.25% additional off both min and max

================================================================================
"""

import pytest
import sys
import os
from datetime import datetime

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from offer_discovery import (
    can_start_offer_discovery,
    lookup_offer_mart,
    lookup_credit_bureau,
    get_credit_band,
    calculate_interest_rate_range,
    perform_offer_discovery,
    format_offer_response_for_llm,
    OFFER_MART_DATABASE,
    CREDIT_BUREAU_DATABASE,
    CREDIT_BANDS,
    DEFAULT_CREDIT_SCORE
)


# ================================================================================
# TEST: ENTRY CONDITIONS
# ================================================================================

class TestOfferDiscoveryEntryConditions:
    """Test that offer discovery only starts when KYC is complete."""
    
    def test_cannot_start_without_kyc_verification(self):
        """Entry blocked if KYC not verified."""
        can_proceed, reason = can_start_offer_discovery(
            kyc_status="PENDING",
            pan_verified=False,
            aadhaar_verified=False
        )
        assert can_proceed is False
        assert "KYC not verified" in reason
    
    def test_cannot_start_without_pan_verification(self):
        """Entry blocked if PAN not verified."""
        can_proceed, reason = can_start_offer_discovery(
            kyc_status="VERIFIED",
            pan_verified=False,
            aadhaar_verified=True
        )
        assert can_proceed is False
        assert "PAN not verified" in reason
    
    def test_cannot_start_without_aadhaar_verification(self):
        """Entry blocked if Aadhaar not verified."""
        can_proceed, reason = can_start_offer_discovery(
            kyc_status="VERIFIED",
            pan_verified=True,
            aadhaar_verified=False
        )
        assert can_proceed is False
        assert "Aadhaar not verified" in reason
    
    def test_can_start_with_complete_kyc(self):
        """Entry allowed with complete KYC verification."""
        can_proceed, reason = can_start_offer_discovery(
            kyc_status="VERIFIED",
            pan_verified=True,
            aadhaar_verified=True
        )
        assert can_proceed is True


# ================================================================================
# TEST: OFFER MART LOOKUP (MOCK API)
# ================================================================================

class TestOfferMartLookup:
    """Test deterministic Offer Mart mock API."""
    
    def test_existing_customer_with_preapproved(self):
        """Test pre-approved customer lookup."""
        # 9876543210 is in mock database with pre-approved offer
        result = lookup_offer_mart("9876543210")
        assert result.existing_customer is True
        assert result.preapproved_offer is True
        assert result.preapproved_limit_inr == 500000
    
    def test_existing_customer_without_preapproved(self):
        """Test existing customer without pre-approved offer."""
        # 9876543220 is existing but no pre-approval (limit=0)
        result = lookup_offer_mart("9876543220")
        assert result.existing_customer is True
        assert result.preapproved_offer is False
        assert result.preapproved_limit_inr == 0
    
    def test_new_customer(self):
        """Test new customer (not in database)."""
        result = lookup_offer_mart("9999999999")
        assert result.existing_customer is False
        assert result.preapproved_offer is False
        assert result.preapproved_limit_inr == 0
    
    def test_high_value_preapproved_customer(self):
        """Test high-value pre-approved customer."""
        # 9876543212 has ₹10L pre-approved
        result = lookup_offer_mart("9876543212")
        assert result.existing_customer is True
        assert result.preapproved_offer is True
        assert result.preapproved_limit_inr == 1000000


# ================================================================================
# TEST: CREDIT BUREAU LOOKUP (MOCK API)
# ================================================================================

class TestCreditBureauLookup:
    """Test deterministic Credit Bureau mock API."""
    
    def test_excellent_credit_score(self):
        """Test customer with excellent credit score (≥800)."""
        # 9876543210 has 825 credit score
        result = lookup_credit_bureau("9876543210")
        assert result.credit_score == 825
        assert result.credit_band == "A"
    
    def test_good_credit_score(self):
        """Test customer with good credit score (750-799)."""
        # 9876543213 has 755 credit score
        result = lookup_credit_bureau("9876543213")
        assert result.credit_score == 755
        assert result.credit_band == "B"
    
    def test_fair_credit_score(self):
        """Test customer with fair credit score (700-749)."""
        # 9876543221 has 720 credit score
        result = lookup_credit_bureau("9876543221")
        assert result.credit_score == 720
        assert result.credit_band == "C"
    
    def test_poor_credit_score(self):
        """Test customer with poor credit score (<700)."""
        # 9876543240 has 680 credit score
        result = lookup_credit_bureau("9876543240")
        assert result.credit_score == 680
        assert result.credit_band == "D"
    
    def test_unknown_customer_gets_default_score(self):
        """Test new customer gets default credit score."""
        result = lookup_credit_bureau("9999999999")
        assert result.credit_score == DEFAULT_CREDIT_SCORE
        assert result.credit_band == "C"  # Default is Band C


# ================================================================================
# TEST: CREDIT BAND DETERMINATION
# ================================================================================

class TestCreditBandDetermination:
    """Test credit score to band mapping."""
    
    def test_band_a_excellent(self):
        """Test Band A for credit score ≥800."""
        band = get_credit_band(800)
        assert band == "A"
        
        band = get_credit_band(850)
        assert band == "A"
    
    def test_band_b_good(self):
        """Test Band B for credit score 750-799."""
        band = get_credit_band(750)
        assert band == "B"
        
        band = get_credit_band(799)
        assert band == "B"
    
    def test_band_c_fair(self):
        """Test Band C for credit score 700-749."""
        band = get_credit_band(700)
        assert band == "C"
        
        band = get_credit_band(749)
        assert band == "C"
    
    def test_band_d_needs_review(self):
        """Test Band D for credit score <700."""
        band = get_credit_band(699)
        assert band == "D"
        
        band = get_credit_band(600)
        assert band == "D"
        
        band = get_credit_band(500)
        assert band == "D"


# ================================================================================
# TEST: INTEREST RATE RANGE CALCULATION
# ================================================================================

class TestInterestRateCalculation:
    """Test interest rate RANGE calculation with modifiers."""
    
    def test_band_a_base_rates(self):
        """Test Band A base rates: 10.5% - 11.5%."""
        result = calculate_interest_rate_range(
            credit_score=810,
            existing_customer=False,
            preapproved_offer=False
        )
        assert result.rate_min == 10.5
        assert result.rate_max == 11.5
        assert "Band A" in result.band_reason
    
    def test_band_b_base_rates(self):
        """Test Band B base rates: 11.5% - 12.5%."""
        result = calculate_interest_rate_range(
            credit_score=765,
            existing_customer=False,
            preapproved_offer=False
        )
        assert result.rate_min == 11.5
        assert result.rate_max == 12.5
        assert "Band B" in result.band_reason
    
    def test_band_c_base_rates(self):
        """Test Band C base rates: 12.5% - 14.0%."""
        result = calculate_interest_rate_range(
            credit_score=720,
            existing_customer=False,
            preapproved_offer=False
        )
        assert result.rate_min == 12.5
        assert result.rate_max == 14.0
        assert "Band C" in result.band_reason
    
    def test_band_d_base_rates_with_risk_flag(self):
        """Test Band D base rates: 14.0% - 18.0% with risk flag."""
        result = calculate_interest_rate_range(
            credit_score=650,
            existing_customer=False,
            preapproved_offer=False
        )
        assert result.rate_min == 14.0
        assert result.rate_max == 18.0
        assert result.risk_flag is not None
        assert "Band D" in result.band_reason
    
    def test_existing_customer_modifier(self):
        """Test existing customer gets -0.25% discount."""
        # Band A with existing customer: 10.5-11.5 → 10.25-11.25
        result = calculate_interest_rate_range(
            credit_score=810,
            existing_customer=True,
            preapproved_offer=False
        )
        assert result.rate_min == 10.25
        assert result.rate_max == 11.25
    
    def test_preapproved_modifier(self):
        """Test pre-approved gets -0.25% additional discount."""
        # Band A with existing + preapproved: 10.5-11.5 → 10.0-11.0
        result = calculate_interest_rate_range(
            credit_score=810,
            existing_customer=True,
            preapproved_offer=True
        )
        assert result.rate_min == 10.0
        assert result.rate_max == 11.0
    
    def test_modifiers_apply_to_all_bands(self):
        """Test modifiers apply to all credit bands."""
        # Band C (12.5-14.0) with existing + preapproved
        result = calculate_interest_rate_range(
            credit_score=720,
            existing_customer=True,
            preapproved_offer=True
        )
        assert result.rate_min == 12.0  # 12.5 - 0.5
        assert result.rate_max == 13.5  # 14.0 - 0.5


# ================================================================================
# TEST: COMPLETE OFFER DISCOVERY FLOW
# ================================================================================

class TestCompleteOfferDiscovery:
    """Test the complete offer discovery flow."""
    
    def test_preapproved_customer_full_flow(self):
        """Test pre-approved customer gets best rates."""
        # 9876543210: existing, pre-approved, credit 825 (Band A)
        result = perform_offer_discovery("9876543210")
        
        assert result["existing_customer"] is True
        assert result["preapproved_offer"] is True
        assert result["preapproved_limit_inr"] == 500000
        assert result["credit_score"] == 825
        assert result["credit_band"] == "A"
        # Band A (10.5-11.5) - 0.25 (existing) - 0.25 (preapproved) = 10.0-11.0
        assert result["interest_rate_min"] == 10.0
        assert result["interest_rate_max"] == 11.0
        assert result["risk_flag"] is None
    
    def test_existing_customer_no_preapproval(self):
        """Test existing customer without pre-approval."""
        # 9876543220: existing, no pre-approval, credit 765 (Band B)
        result = perform_offer_discovery("9876543220")
        
        assert result["existing_customer"] is True
        assert result["preapproved_offer"] is False
        assert result["credit_score"] == 765
        assert result["credit_band"] == "B"
        # Band B (11.5-12.5) - 0.25 (existing) = 11.25-12.25
        assert result["interest_rate_min"] == 11.25
        assert result["interest_rate_max"] == 12.25
        assert result["risk_flag"] is None
    
    def test_new_customer_fair_credit(self):
        """Test new customer with fair credit score."""
        # New customer gets default credit score (725 = Band C)
        result = perform_offer_discovery("9999999999")
        
        assert result["existing_customer"] is False
        assert result["preapproved_offer"] is False
        assert result["credit_score"] == DEFAULT_CREDIT_SCORE  # 725
        assert result["credit_band"] == "C"
        # Band C (12.5-14.0), no modifiers
        assert result["interest_rate_min"] == 12.5
        assert result["interest_rate_max"] == 14.0
        assert result["risk_flag"] is None
    
    def test_customer_with_poor_credit(self):
        """Test customer with poor credit gets risk flag."""
        # 9876543240: credit 680 (Band D)
        result = perform_offer_discovery("9876543240")
        
        assert result["credit_score"] == 680
        assert result["credit_band"] == "D"
        # Band D (14.0-18.0)
        assert result["interest_rate_min"] == 14.0
        assert result["interest_rate_max"] == 18.0
        assert result["risk_flag"] is not None
        assert result["is_eligible"] is True  # Not rejected, just flagged
    
    def test_high_value_preapproved_customer(self):
        """Test high-value pre-approved customer."""
        # 9876543212: pre-approved ₹10L, credit 780 (Band B)
        result = perform_offer_discovery("9876543212")
        
        assert result["existing_customer"] is True
        assert result["preapproved_offer"] is True
        assert result["preapproved_limit_inr"] == 1000000
        assert result["credit_score"] == 780
        assert result["credit_band"] == "B"
        # Band B (11.5-12.5) - 0.5 (both modifiers) = 11.0-12.0
        assert result["interest_rate_min"] == 11.0
        assert result["interest_rate_max"] == 12.0


# ================================================================================
# TEST: LLM COMMUNICATION FORMAT
# ================================================================================

class TestLLMCommunicationFormat:
    """Test that LLM response format includes indicative disclaimers."""
    
    def test_response_includes_indicative_disclaimer(self):
        """LLM response must say rates are INDICATIVE, not final."""
        result = perform_offer_discovery("9876543210")
        response = format_offer_response_for_llm("Rahul", result)
        
        assert "indicative" in response.lower()
    
    def test_response_shows_rate_range(self):
        """LLM response must show rate as RANGE, not single value."""
        result = perform_offer_discovery("9876543210")
        response = format_offer_response_for_llm("Rahul", result)
        
        # Should contain rate range indicator
        assert "%" in response
        assert "–" in response or "-" in response
    
    def test_preapproved_response_mentions_limit(self):
        """Pre-approved response must mention the limit."""
        result = perform_offer_discovery("9876543210")
        response = format_offer_response_for_llm("Rahul", result)
        
        assert "500,000" in response or "5,00,000" in response or "pre-approved" in response.lower()
    
    def test_risk_flag_response_mentions_review(self):
        """Risk flag response must mention additional review."""
        result = perform_offer_discovery("9876543240")  # Poor credit
        response = format_offer_response_for_llm("Rahul", result)
        
        assert result["risk_flag"] is not None
        assert "review" in response.lower() or "⚠️" in response
    
    def test_response_never_promises_approval(self):
        """LLM response must never promise loan approval."""
        result = perform_offer_discovery("9876543210")
        response = format_offer_response_for_llm("Rahul", result)
        
        # Should not contain absolute promises
        assert "guaranteed" not in response.lower()
        assert "definitely" not in response.lower()


# ================================================================================
# TEST: DETERMINISTIC BEHAVIOR
# ================================================================================

class TestDeterministicBehavior:
    """Test that offer discovery is 100% reproducible."""
    
    def test_same_mobile_same_result(self):
        """Same mobile number should always return same result."""
        result1 = perform_offer_discovery("9876543210")
        result2 = perform_offer_discovery("9876543210")
        
        assert result1["existing_customer"] == result2["existing_customer"]
        assert result1["preapproved_offer"] == result2["preapproved_offer"]
        assert result1["preapproved_limit_inr"] == result2["preapproved_limit_inr"]
        assert result1["credit_score"] == result2["credit_score"]
        assert result1["credit_band"] == result2["credit_band"]
        assert result1["interest_rate_min"] == result2["interest_rate_min"]
        assert result1["interest_rate_max"] == result2["interest_rate_max"]
        assert result1["risk_flag"] == result2["risk_flag"]
    
    def test_different_mobiles_different_results(self):
        """Different mobile numbers can have different results."""
        result1 = perform_offer_discovery("9876543210")  # Pre-approved
        result2 = perform_offer_discovery("9876543220")  # Existing, no pre-approval
        result3 = perform_offer_discovery("9999999999")  # New customer
        
        # All should have different characteristics
        assert result1["preapproved_offer"] is True
        assert result2["preapproved_offer"] is False
        assert result3["existing_customer"] is False
    
    def test_no_random_values(self):
        """Credit scores and rates should never be random."""
        # Run 10 times and verify consistency
        for _ in range(10):
            result = perform_offer_discovery("9876543210")
            assert result["credit_score"] == 825
            assert result["interest_rate_min"] == 10.0
            assert result["interest_rate_max"] == 11.0


# ================================================================================
# TEST: EDGE CASES
# ================================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_mobile_number(self):
        """Empty mobile should get default/new customer treatment."""
        result = perform_offer_discovery("")
        assert result["existing_customer"] is False
        assert result["credit_score"] == DEFAULT_CREDIT_SCORE
    
    def test_credit_score_boundary_800(self):
        """Credit score exactly 800 should be Band A."""
        band = get_credit_band(800)
        assert band == "A"
    
    def test_credit_score_boundary_799(self):
        """Credit score 799 should be Band B."""
        band = get_credit_band(799)
        assert band == "B"
    
    def test_credit_score_boundary_750(self):
        """Credit score 750 should be Band B."""
        band = get_credit_band(750)
        assert band == "B"
    
    def test_credit_score_boundary_749(self):
        """Credit score 749 should be Band C."""
        band = get_credit_band(749)
        assert band == "C"
    
    def test_credit_score_boundary_700(self):
        """Credit score 700 should be Band C."""
        band = get_credit_band(700)
        assert band == "C"
    
    def test_credit_score_boundary_699(self):
        """Credit score 699 should be Band D."""
        band = get_credit_band(699)
        assert band == "D"
    
    def test_minimum_rate_floor(self):
        """Interest rate should never go below reasonable floor."""
        # Even with all modifiers, rate shouldn't be unreasonably low
        result = calculate_interest_rate_range(
            credit_score=850,  # Best possible
            existing_customer=True,
            preapproved_offer=True
        )
        assert result.rate_min >= 8.0  # Reasonable floor


# ================================================================================
# TEST: STAGE STATE INTEGRATION
# ================================================================================

class TestStageStateIntegration:
    """Test integration with StageState for Phase 5 fields."""
    
    def test_perform_discovery_returns_all_fields(self):
        """perform_offer_discovery should return all needed fields."""
        result = perform_offer_discovery("9876543210")
        
        # Check all expected fields exist
        assert "existing_customer" in result
        assert "preapproved_limit_inr" in result
        assert "preapproved_offer" in result
        assert "credit_score" in result
        assert "credit_band" in result
        assert "interest_rate_min" in result
        assert "interest_rate_max" in result
        assert "interest_rate_band_reason" in result
        assert "is_eligible" in result
        assert "risk_flag" in result
        assert "offer_lookup_timestamp" in result
        assert "credit_lookup_timestamp" in result


# ================================================================================
# RUN TESTS
# ================================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 5 TEST SUITE: OFFER DISCOVERY AND DYNAMIC INTEREST RATE")
    print("=" * 80)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
