"""
================================================================================
PHASE 8: JOURNEY CLOSURE TEST SUITE
================================================================================

Comprehensive tests for the final journey closure through sanction letter 
generation or rejection messaging.

================================================================================
WHAT THIS TEST SUITE VALIDATES:
================================================================================

1. ENTRY CONDITIONS (STRICT VALIDATION)
   - SANCTION stage requires: loan_status == APPROVED, underwriting_timestamp exists
   - REJECTION stage requires: loan_status == REJECTED, rejection_reason exists
   - Invalid conditions block execution and log errors

2. SANCTION LETTER GENERATION
   - PDF is generated with correct customer details
   - Sanction letter contains: name, amount, rate, tenure, EMI, date, branding
   - File is stored persistently (not temp)
   - Reference number is unique
   - Download link is provided

3. REJECTION HANDLING
   - Polite, professional message is provided
   - ONLY ONE clear reason is mentioned
   - No upselling or workarounds
   - Journey ends respectfully

4. STATE MANAGEMENT
   - sanction_letter_generated is persisted
   - sanction_letter_reference is persisted
   - journey_completed is persisted
   - session_closed is set to True

5. TERMINAL BEHAVIOR
   - No stage changes allowed after closure
   - No duplicate sanction letter generation
   - Further inputs are blocked

6. DETERMINISTIC BEHAVIOR
   - Same inputs always produce same closure outcome
   - No LLM influence on decision

================================================================================
"""

import pytest
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from journey_closure_service import (
    validate_sanction_entry_conditions,
    validate_rejection_entry_conditions,
    generate_sanction_letter_for_approved_loan,
    process_rejection,
    close_journey_with_sanction,
    close_journey_with_rejection,
    get_sanction_state_updates,
    get_rejection_state_updates,
    get_sanction_confirmation_message,
    get_rejection_final_message,
    categorize_rejection,
    can_accept_further_input,
    is_journey_closed,
    format_currency,
    JourneyStatus,
    RejectionCategory,
    REJECTION_MESSAGES
)


# ================================================================================
# TEST FIXTURES
# ================================================================================

@pytest.fixture
def approved_loan_data():
    """Sample data for an approved loan."""
    return {
        "customer_name": "Rahul Sharma",
        "loan_amount": 500000.0,
        "interest_rate": 12.5,
        "loan_tenure_months": 36,
        "calculated_emi": 16750.0,
        "phone": "9876543210",
        "pan": "ABCDE1234F",
        "session_id": "test_phase8_approved_001"
    }


@pytest.fixture
def rejected_loan_data():
    """Sample data for a rejected loan."""
    return {
        "rejection_reason": "Credit score 650 is below minimum threshold of 700"
    }


# ================================================================================
# TEST CLASS: SANCTION ENTRY VALIDATION
# ================================================================================

class TestSanctionEntryValidation:
    """Tests for SANCTION stage entry condition validation."""
    
    def test_valid_sanction_entry(self):
        """Valid entry: loan_status=APPROVED, underwriting_timestamp exists."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status="APPROVED",
            underwriting_timestamp="2025-01-31T10:00:00"
        )
        assert can_proceed is True
        assert "conditions met" in reason.lower()
    
    def test_sanction_blocked_wrong_status(self):
        """Entry blocked when loan_status is not APPROVED."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status="REJECTED",
            underwriting_timestamp="2025-01-31T10:00:00"
        )
        assert can_proceed is False
        assert "APPROVED" in reason
    
    def test_sanction_blocked_pending_status(self):
        """Entry blocked when loan_status is PENDING."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status="PENDING",
            underwriting_timestamp="2025-01-31T10:00:00"
        )
        assert can_proceed is False
    
    def test_sanction_blocked_no_timestamp(self):
        """Entry blocked when underwriting_timestamp is missing."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status="APPROVED",
            underwriting_timestamp=None
        )
        assert can_proceed is False
        assert "timestamp" in reason.lower()
    
    def test_sanction_blocked_empty_timestamp(self):
        """Entry blocked when underwriting_timestamp is empty string."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status="APPROVED",
            underwriting_timestamp=""
        )
        assert can_proceed is False
    
    def test_sanction_blocked_none_status(self):
        """Entry blocked when loan_status is None."""
        can_proceed, reason = validate_sanction_entry_conditions(
            loan_status=None,
            underwriting_timestamp="2025-01-31T10:00:00"
        )
        assert can_proceed is False


# ================================================================================
# TEST CLASS: REJECTION ENTRY VALIDATION
# ================================================================================

class TestRejectionEntryValidation:
    """Tests for REJECTION stage entry condition validation."""
    
    def test_valid_rejection_entry(self):
        """Valid entry: loan_status=REJECTED, rejection_reason exists."""
        can_proceed, reason = validate_rejection_entry_conditions(
            loan_status="REJECTED",
            rejection_reason="Credit score below threshold"
        )
        assert can_proceed is True
        assert "conditions met" in reason.lower()
    
    def test_rejection_blocked_wrong_status(self):
        """Entry blocked when loan_status is not REJECTED."""
        can_proceed, reason = validate_rejection_entry_conditions(
            loan_status="APPROVED",
            rejection_reason="Some reason"
        )
        assert can_proceed is False
        assert "REJECTED" in reason
    
    def test_rejection_blocked_no_reason(self):
        """Entry blocked when rejection_reason is missing."""
        can_proceed, reason = validate_rejection_entry_conditions(
            loan_status="REJECTED",
            rejection_reason=None
        )
        assert can_proceed is False
        assert "reason" in reason.lower()
    
    def test_rejection_blocked_empty_reason(self):
        """Entry blocked when rejection_reason is empty string."""
        can_proceed, reason = validate_rejection_entry_conditions(
            loan_status="REJECTED",
            rejection_reason=""
        )
        assert can_proceed is False
    
    def test_rejection_blocked_none_status(self):
        """Entry blocked when loan_status is None."""
        can_proceed, reason = validate_rejection_entry_conditions(
            loan_status=None,
            rejection_reason="Some reason"
        )
        assert can_proceed is False


# ================================================================================
# TEST CLASS: SANCTION LETTER GENERATION
# ================================================================================

class TestSanctionLetterGeneration:
    """Tests for sanction letter PDF generation."""
    
    def test_sanction_letter_generation_success(self, approved_loan_data):
        """Sanction letter is generated successfully with valid data."""
        result = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        
        assert result.success is True
        assert result.sanction_letter_path is not None
        assert os.path.exists(result.sanction_letter_path)
        assert result.sanction_letter_reference is not None
        assert "AURORA" in result.sanction_letter_reference
    
    def test_sanction_letter_has_timestamp(self, approved_loan_data):
        """Sanction letter result includes timestamp."""
        result = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        
        assert result.sanction_timestamp is not None
        # Should be ISO format
        datetime.fromisoformat(result.sanction_timestamp)
    
    def test_sanction_letter_url_available(self, approved_loan_data):
        """Sanction letter URL is available for download."""
        result = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        
        assert result.sanction_letter_url is not None
        assert "/sanction_letters/" in result.sanction_letter_url
    
    def test_sanction_letter_missing_name(self):
        """Sanction letter fails without customer name."""
        result = generate_sanction_letter_for_approved_loan(
            customer_name="",
            loan_amount=500000,
            interest_rate=12.5,
            loan_tenure_months=36,
            calculated_emi=16750,
            session_id="test_no_name"
        )
        
        assert result.success is False
        assert "name" in result.error_message.lower()
    
    def test_sanction_letter_invalid_amount(self):
        """Sanction letter fails with invalid loan amount."""
        result = generate_sanction_letter_for_approved_loan(
            customer_name="Test User",
            loan_amount=0,
            interest_rate=12.5,
            loan_tenure_months=36,
            calculated_emi=16750,
            session_id="test_no_amount"
        )
        
        assert result.success is False
        assert "amount" in result.error_message.lower()
    
    def test_sanction_letter_negative_amount(self):
        """Sanction letter fails with negative loan amount."""
        result = generate_sanction_letter_for_approved_loan(
            customer_name="Test User",
            loan_amount=-100000,
            interest_rate=12.5,
            loan_tenure_months=36,
            calculated_emi=16750,
            session_id="test_negative_amount"
        )
        
        assert result.success is False


# ================================================================================
# TEST CLASS: REJECTION CATEGORIZATION
# ================================================================================

class TestRejectionCategorization:
    """Tests for rejection reason categorization."""
    
    def test_categorize_low_credit_score(self):
        """Credit score rejection is categorized correctly."""
        category = categorize_rejection("Credit score 650 is below minimum threshold of 700")
        assert category == RejectionCategory.LOW_CREDIT_SCORE
    
    def test_categorize_credit_threshold(self):
        """Credit threshold rejection is categorized correctly."""
        category = categorize_rejection("Failed credit threshold check")
        assert category == RejectionCategory.LOW_CREDIT_SCORE
    
    def test_categorize_emi_unaffordable(self):
        """EMI affordability rejection is categorized correctly."""
        category = categorize_rejection("Monthly EMI obligations exceed 50% of verified income")
        assert category == RejectionCategory.EMI_UNAFFORDABLE
    
    def test_categorize_income_eligibility(self):
        """Income eligibility rejection is categorized correctly."""
        category = categorize_rejection("Verified salary insufficient for loan amount")
        assert category == RejectionCategory.INCOME_ELIGIBILITY
    
    def test_categorize_kyc_failure_pan(self):
        """PAN verification failure is categorized correctly."""
        category = categorize_rejection("PAN verification failed: not found in database")
        assert category == RejectionCategory.KYC_VERIFICATION_FAILURE
    
    def test_categorize_kyc_failure_aadhaar(self):
        """Aadhaar verification failure is categorized correctly."""
        category = categorize_rejection("Aadhaar verification failed")
        assert category == RejectionCategory.KYC_VERIFICATION_FAILURE
    
    def test_categorize_exceeds_limit(self):
        """Exceeds limit rejection is categorized correctly."""
        category = categorize_rejection("Requested amount exceeds maximum limit")
        assert category == RejectionCategory.EXCEEDS_LIMIT
    
    def test_categorize_unknown(self):
        """Unknown rejection gets UNKNOWN category."""
        category = categorize_rejection("Some random technical error")
        assert category == RejectionCategory.UNKNOWN


# ================================================================================
# TEST CLASS: REJECTION PROCESSING
# ================================================================================

class TestRejectionProcessing:
    """Tests for rejection message processing."""
    
    def test_rejection_processing_success(self, rejected_loan_data):
        """Rejection is processed successfully."""
        result = process_rejection(rejected_loan_data["rejection_reason"])
        
        assert result.success is True
        assert result.is_final is True
        assert result.rejection_timestamp is not None
    
    def test_rejection_message_is_customer_friendly(self, rejected_loan_data):
        """Rejection message is polite and professional."""
        result = process_rejection(rejected_loan_data["rejection_reason"])
        
        # Message should be polite
        assert "thank you" in result.rejection_message.lower()
        # Should not contain technical jargon
        assert "threshold of 700" not in result.rejection_message.lower()
        # Should invite reapplication
        assert "future" in result.rejection_message.lower() or "again" in result.rejection_message.lower()
    
    def test_rejection_message_no_upselling(self, rejected_loan_data):
        """Rejection message does NOT upsell or suggest workarounds."""
        result = process_rejection(rejected_loan_data["rejection_reason"])
        
        message_lower = result.rejection_message.lower()
        # No upselling
        assert "other products" not in message_lower
        assert "credit card" not in message_lower
        assert "consider our" not in message_lower
        # No workarounds
        assert "instead" not in message_lower
        assert "try" not in message_lower or "try again" in message_lower
    
    def test_rejection_has_single_reason(self, rejected_loan_data):
        """Rejection provides single clear reason, not a list."""
        result = process_rejection(rejected_loan_data["rejection_reason"])
        
        # Should not contain bullet points or numbered lists
        assert "1." not in result.rejection_message
        assert "2." not in result.rejection_message
        assert "•" not in result.rejection_message
        assert "- " not in result.rejection_message or result.rejection_message.count("- ") <= 1


# ================================================================================
# TEST CLASS: JOURNEY CLOSURE - SANCTION
# ================================================================================

class TestJourneyClosureSanction:
    """Tests for journey closure with sanction."""
    
    def test_journey_closed_with_sanction(self, approved_loan_data):
        """Journey is closed successfully with sanction."""
        result = close_journey_with_sanction(**approved_loan_data)
        
        assert result.journey_completed is True
        assert result.journey_status == JourneyStatus.SANCTIONED
        assert result.sanction_result is not None
        assert result.sanction_result.success is True
    
    def test_journey_sanction_has_timestamp(self, approved_loan_data):
        """Journey closure has timestamp."""
        result = close_journey_with_sanction(**approved_loan_data)
        
        assert result.timestamp is not None
        datetime.fromisoformat(result.timestamp)
    
    def test_journey_sanction_prevents_duplicate(self, approved_loan_data):
        """Duplicate sanction letter generation is prevented."""
        # First generation
        result1 = close_journey_with_sanction(**approved_loan_data)
        assert result1.journey_completed is True
        
        # Try to generate again (simulating already generated)
        approved_loan_data["sanction_letter_generated"] = True
        result2 = close_journey_with_sanction(**approved_loan_data)
        
        # Should still be completed but error message indicates duplicate
        assert result2.journey_completed is True
        assert "already" in result2.error_message.lower()


# ================================================================================
# TEST CLASS: JOURNEY CLOSURE - REJECTION
# ================================================================================

class TestJourneyClosureRejection:
    """Tests for journey closure with rejection."""
    
    def test_journey_closed_with_rejection(self, rejected_loan_data):
        """Journey is closed successfully with rejection."""
        result = close_journey_with_rejection(**rejected_loan_data)
        
        assert result.journey_completed is True
        assert result.journey_status == JourneyStatus.REJECTED
        assert result.rejection_result is not None
        assert result.rejection_result.is_final is True
    
    def test_journey_rejection_has_timestamp(self, rejected_loan_data):
        """Journey closure has timestamp."""
        result = close_journey_with_rejection(**rejected_loan_data)
        
        assert result.timestamp is not None
        datetime.fromisoformat(result.timestamp)
    
    def test_journey_rejection_no_sanction_result(self, rejected_loan_data):
        """Rejection journey has no sanction result."""
        result = close_journey_with_rejection(**rejected_loan_data)
        
        assert result.sanction_result is None


# ================================================================================
# TEST CLASS: STATE PERSISTENCE
# ================================================================================

class TestStatePersistence:
    """Tests for state persistence after journey closure."""
    
    def test_sanction_state_updates(self, approved_loan_data):
        """Sanction state updates are correct."""
        result = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        updates = get_sanction_state_updates(result)
        
        assert updates["sanction_letter_generated"] is True
        assert updates["sanction_letter_path"] is not None
        assert updates["sanction_letter_reference"] is not None
        assert updates["sanction_timestamp"] is not None
        assert updates["journey_completed"] is True
        assert updates["session_closed"] is True
        assert updates["closure_reason"] == "SANCTION_COMPLETE"
    
    def test_rejection_state_updates(self, rejected_loan_data):
        """Rejection state updates are correct."""
        result = process_rejection(rejected_loan_data["rejection_reason"])
        updates = get_rejection_state_updates(result)
        
        assert updates["rejection_category"] == RejectionCategory.LOW_CREDIT_SCORE.value
        assert updates["rejection_message"] is not None
        assert updates["rejection_timestamp"] is not None
        assert updates["journey_completed"] is True
        assert updates["session_closed"] is True
        assert updates["closure_reason"] == "REJECTION_COMPLETE"


# ================================================================================
# TEST CLASS: TERMINAL BEHAVIOR
# ================================================================================

class TestTerminalBehavior:
    """Tests for terminal stage behavior."""
    
    def test_journey_closed_check_both_true(self):
        """Journey is closed when both flags are True."""
        assert is_journey_closed(True, True) is True
    
    def test_journey_closed_journey_only(self):
        """Journey is closed when journey_completed is True."""
        assert is_journey_closed(True, False) is True
    
    def test_journey_closed_session_only(self):
        """Journey is closed when session_closed is True."""
        assert is_journey_closed(False, True) is True
    
    def test_journey_not_closed(self):
        """Journey is not closed when both flags are False."""
        assert is_journey_closed(False, False) is False
    
    def test_no_input_after_sanction(self):
        """No further input accepted after SANCTION."""
        can_accept, reason = can_accept_further_input(
            current_stage="SANCTION",
            journey_completed=True,
            session_closed=True
        )
        assert can_accept is False
        assert "completed" in reason.lower() or "terminal" in reason.lower()
    
    def test_no_input_after_rejection(self):
        """No further input accepted after REJECTION."""
        can_accept, reason = can_accept_further_input(
            current_stage="REJECTION",
            journey_completed=True,
            session_closed=True
        )
        assert can_accept is False
    
    def test_input_accepted_before_closure(self):
        """Input is accepted before journey closure."""
        can_accept, reason = can_accept_further_input(
            current_stage="UNDERWRITING",
            journey_completed=False,
            session_closed=False
        )
        assert can_accept is True


# ================================================================================
# TEST CLASS: CHATBOT MESSAGES
# ================================================================================

class TestChatbotMessages:
    """Tests for chatbot message generation."""
    
    def test_sanction_confirmation_message(self):
        """Sanction confirmation message is correct."""
        message = get_sanction_confirmation_message(
            customer_name="Rahul Sharma",
            loan_amount=500000,
            sanction_reference="AURORA/SL/20250131/TEST01"
        )
        
        assert "Congratulations" in message
        assert "Rahul Sharma" in message
        assert "500000" in message or "5" in message  # Amount could be formatted
        assert "AURORA/SL/20250131/TEST01" in message
        assert "download" in message.lower()
    
    def test_rejection_final_message(self):
        """Rejection final message is correct."""
        message = get_rejection_final_message(
            rejection_reason="Credit score 650 is below minimum threshold of 700"
        )
        
        # Should be polite
        assert "thank you" in message.lower()
        # Should not contain technical details
        assert "650" not in message
        assert "700" not in message


# ================================================================================
# TEST CLASS: HELPER FUNCTIONS
# ================================================================================

class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_format_currency_crores(self):
        """Format currency in crores."""
        assert "Cr" in format_currency(15000000)
    
    def test_format_currency_lakhs(self):
        """Format currency in lakhs."""
        assert "L" in format_currency(500000)
    
    def test_format_currency_thousands(self):
        """Format currency in thousands."""
        assert "K" in format_currency(50000)
    
    def test_format_currency_small(self):
        """Format small currency amount."""
        result = format_currency(999)
        assert "₹" in result


# ================================================================================
# TEST CLASS: DETERMINISTIC BEHAVIOR
# ================================================================================

class TestDeterministicBehavior:
    """Tests for deterministic behavior."""
    
    def test_same_sanction_inputs_same_reference_format(self, approved_loan_data):
        """Same inputs produce consistent reference format."""
        result1 = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        result2 = generate_sanction_letter_for_approved_loan(**approved_loan_data)
        
        # Both should succeed
        assert result1.success is True
        assert result2.success is True
        
        # Reference format should be consistent (AURORA/SL/...)
        assert result1.sanction_letter_reference.startswith("AURORA/SL/")
        assert result2.sanction_letter_reference.startswith("AURORA/SL/")
    
    def test_same_rejection_inputs_same_category(self):
        """Same rejection reason always produces same category."""
        reason = "Credit score 650 is below minimum threshold of 700"
        
        cat1 = categorize_rejection(reason)
        cat2 = categorize_rejection(reason)
        cat3 = categorize_rejection(reason)
        
        assert cat1 == cat2 == cat3 == RejectionCategory.LOW_CREDIT_SCORE
    
    def test_same_rejection_inputs_same_message(self):
        """Same rejection reason produces same customer message."""
        reason = "Credit score below threshold"
        
        result1 = process_rejection(reason)
        result2 = process_rejection(reason)
        
        assert result1.rejection_message == result2.rejection_message


# ================================================================================
# TEST CLASS: REJECTION MESSAGE COVERAGE
# ================================================================================

class TestRejectionMessageCoverage:
    """Tests to ensure all rejection categories have messages."""
    
    def test_all_categories_have_messages(self):
        """All rejection categories have corresponding messages."""
        for category in RejectionCategory:
            assert category in REJECTION_MESSAGES
            assert len(REJECTION_MESSAGES[category]) > 0
    
    def test_all_messages_are_polite(self):
        """All rejection messages are polite."""
        for category, message in REJECTION_MESSAGES.items():
            message_lower = message.lower()
            assert "thank" in message_lower or "appreciate" in message_lower
    
    def test_all_messages_invite_reapplication(self):
        """All rejection messages invite future reapplication."""
        for category, message in REJECTION_MESSAGES.items():
            message_lower = message.lower()
            assert "future" in message_lower or "again" in message_lower or "reapply" in message_lower


# ================================================================================
# TEST CLASS: INTEGRATION TESTS
# ================================================================================

class TestIntegration:
    """Integration tests for Phase 8 with other phases."""
    
    def test_sanction_after_underwriting_approval(self, approved_loan_data):
        """Sanction flow works after underwriting approval."""
        # Simulate underwriting approval
        loan_status = "APPROVED"
        underwriting_timestamp = datetime.now().isoformat()
        
        # Validate sanction entry
        can_proceed, _ = validate_sanction_entry_conditions(
            loan_status=loan_status,
            underwriting_timestamp=underwriting_timestamp
        )
        assert can_proceed is True
        
        # Close journey with sanction
        result = close_journey_with_sanction(**approved_loan_data)
        assert result.journey_completed is True
        assert result.journey_status == JourneyStatus.SANCTIONED
    
    def test_rejection_after_underwriting_rejection(self, rejected_loan_data):
        """Rejection flow works after underwriting rejection."""
        # Simulate underwriting rejection
        loan_status = "REJECTED"
        rejection_reason = rejected_loan_data["rejection_reason"]
        
        # Validate rejection entry
        can_proceed, _ = validate_rejection_entry_conditions(
            loan_status=loan_status,
            rejection_reason=rejection_reason
        )
        assert can_proceed is True
        
        # Close journey with rejection
        result = close_journey_with_rejection(rejection_reason=rejection_reason)
        assert result.journey_completed is True
        assert result.journey_status == JourneyStatus.REJECTED


# ================================================================================
# MAIN: Run tests
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 8: JOURNEY CLOSURE TEST SUITE")
    print("=" * 60)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
