"""
================================================================================
TEST PHASE 7: DETERMINISTIC UNDERWRITING DECISION ENGINE
================================================================================

This test suite validates the underwriting decision functionality:
1. Entry conditions (income verified, credit score, loan amount)
2. Credit score rule (< 700 → REJECT)
3. Pre-approved limit rule (> 2x limit → REJECT)
4. EMI affordability rule (FOIR > 50% → REJECT)
5. Deterministic behavior (same inputs → same outputs)
6. State persistence
7. Stage transitions (UNDERWRITING → SANCTION or REJECTION)

================================================================================
KEY PRINCIPLES BEING TESTED:
================================================================================

1. DECISIONS ARE FINAL
   - Once underwriting completes, decision cannot be changed
   - No re-underwriting allowed on same application

2. DECISIONS ARE DETERMINISTIC
   - Same inputs ALWAYS produce same output
   - No randomness, no LLM involvement

3. RULES APPLIED IN SEQUENCE
   - Credit score → Limit → EMI affordability
   - First failure terminates with specific reason

4. LLM CAN EXPLAIN BUT NOT DECIDE
   - Decision made by backend logic
   - LLM may paraphrase but cannot override

================================================================================
"""

import pytest
import sys
import os
from datetime import datetime

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from underwriting_decision_engine import (
    validate_entry_conditions,
    perform_underwriting,
    has_underwriting_completed,
    calculate_emi,
    check_credit_score_rule,
    check_pre_approved_limit_rule,
    check_emi_affordability_rule,
    get_approval_message,
    get_rejection_message,
    format_currency,
    LoanDecision,
    RejectionReason,
    MIN_CREDIT_SCORE,
    MAX_FOIR,
    DEFAULT_TENURE_MONTHS,
    DEFAULT_INTEREST_RATE
)


# ================================================================================
# TEST: ENTRY CONDITIONS
# ================================================================================

class TestUnderwritingEntryConditions:
    """Test that underwriting only starts when all conditions are met."""
    
    def test_cannot_start_without_income_verification(self):
        """Entry blocked if income not verified."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=False,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "Income not verified" in reason
    
    def test_cannot_start_without_salary(self):
        """Entry blocked if verified salary is missing."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=None,
            credit_score=750,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "salary" in reason.lower()
    
    def test_cannot_start_with_zero_salary(self):
        """Entry blocked if verified salary is zero."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=0,
            credit_score=750,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "salary" in reason.lower()
    
    def test_cannot_start_without_credit_score(self):
        """Entry blocked if credit score is missing."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=None,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "credit score" in reason.lower()
    
    def test_cannot_start_without_loan_amount(self):
        """Entry blocked if loan amount is missing."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=None
        )
        assert can_proceed is False
        assert "loan amount" in reason.lower()
    
    def test_cannot_start_with_zero_loan_amount(self):
        """Entry blocked if loan amount is zero."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=0
        )
        assert can_proceed is False
        assert "loan amount" in reason.lower()
    
    def test_can_start_with_all_conditions_met(self):
        """Entry allowed with all conditions met."""
        can_proceed, reason = validate_entry_conditions(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000
        )
        assert can_proceed is True


# ================================================================================
# TEST: CREDIT SCORE RULE
# ================================================================================

class TestCreditScoreRule:
    """Test Rule 1: Credit score < 700 → REJECT."""
    
    def test_credit_score_below_minimum_rejects(self):
        """Credit score 699 should be rejected."""
        passed, message = check_credit_score_rule(699)
        assert passed is False
        assert "below" in message.lower()
    
    def test_credit_score_exactly_minimum_passes(self):
        """Credit score exactly 700 should pass."""
        passed, message = check_credit_score_rule(700)
        assert passed is True
    
    def test_credit_score_above_minimum_passes(self):
        """Credit score 750 should pass."""
        passed, message = check_credit_score_rule(750)
        assert passed is True
    
    def test_excellent_credit_score_passes(self):
        """Credit score 850 should pass."""
        passed, message = check_credit_score_rule(850)
        assert passed is True
    
    def test_very_low_credit_score_rejects(self):
        """Credit score 500 should be rejected."""
        passed, message = check_credit_score_rule(500)
        assert passed is False


# ================================================================================
# TEST: PRE-APPROVED LIMIT RULE
# ================================================================================

class TestPreApprovedLimitRule:
    """Test Rule 2: Amount > 2x pre-approved limit → REJECT."""
    
    def test_amount_within_limit_passes(self):
        """Amount ≤ pre-approved limit should pass."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=300000,
            pre_approved_limit=500000
        )
        assert passed is True
        assert "within" in message.lower()
    
    def test_amount_exactly_at_limit_passes(self):
        """Amount exactly at pre-approved limit should pass."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=500000,
            pre_approved_limit=500000
        )
        assert passed is True
    
    def test_amount_up_to_2x_limit_passes(self):
        """Amount up to 2x pre-approved limit should pass (with income verification)."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=800000,
            pre_approved_limit=500000
        )
        assert passed is True
    
    def test_amount_exactly_2x_limit_passes(self):
        """Amount exactly 2x pre-approved limit should pass."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=1000000,
            pre_approved_limit=500000
        )
        assert passed is True
    
    def test_amount_exceeds_2x_limit_rejects(self):
        """Amount > 2x pre-approved limit should be rejected."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=1100000,
            pre_approved_limit=500000
        )
        assert passed is False
        assert "exceeds" in message.lower()
    
    def test_zero_pre_approved_limit_rejects_any_amount(self):
        """Zero pre-approved limit should reject any amount > 0."""
        passed, message = check_pre_approved_limit_rule(
            requested_amount=100000,
            pre_approved_limit=0
        )
        assert passed is False


# ================================================================================
# TEST: EMI AFFORDABILITY RULE
# ================================================================================

class TestEMIAffordabilityRule:
    """Test Rule 3: (existing_emi + new_emi) > 50% of salary → REJECT."""
    
    def test_emi_within_50_percent_passes(self):
        """EMI within 50% of salary should pass."""
        passed, message, foir = check_emi_affordability_rule(
            verified_monthly_salary=100000,
            existing_emi=10000,
            new_emi=30000
        )
        assert passed is True
        assert foir <= 50
    
    def test_emi_exactly_50_percent_passes(self):
        """EMI exactly 50% of salary should pass."""
        passed, message, foir = check_emi_affordability_rule(
            verified_monthly_salary=100000,
            existing_emi=0,
            new_emi=50000
        )
        assert passed is True
        assert foir == 50
    
    def test_emi_exceeds_50_percent_rejects(self):
        """EMI exceeding 50% of salary should be rejected."""
        passed, message, foir = check_emi_affordability_rule(
            verified_monthly_salary=100000,
            existing_emi=30000,
            new_emi=30000
        )
        assert passed is False
        assert foir > 50
    
    def test_high_existing_emi_causes_rejection(self):
        """High existing EMI should cause rejection."""
        passed, message, foir = check_emi_affordability_rule(
            verified_monthly_salary=100000,
            existing_emi=45000,
            new_emi=10000
        )
        assert passed is False
    
    def test_foir_percentage_calculated_correctly(self):
        """FOIR should be calculated as (total_obligations / salary) * 100."""
        passed, message, foir = check_emi_affordability_rule(
            verified_monthly_salary=100000,
            existing_emi=10000,
            new_emi=20000
        )
        assert foir == 30.0  # (10000 + 20000) / 100000 * 100


# ================================================================================
# TEST: EMI CALCULATION
# ================================================================================

class TestEMICalculation:
    """Test EMI calculation formula."""
    
    def test_emi_calculation_basic(self):
        """Test basic EMI calculation."""
        emi = calculate_emi(
            principal=100000,
            annual_rate=12.0,
            tenure_months=12
        )
        assert emi > 0
        # EMI for 1L at 12% for 12 months should be around ₹8,885
        assert 8800 < emi < 9000
    
    def test_emi_calculation_36_months(self):
        """Test EMI for 36 month tenure."""
        emi = calculate_emi(
            principal=500000,
            annual_rate=12.0,
            tenure_months=36
        )
        assert emi > 0
        # EMI for 5L at 12% for 36 months should be around ₹16,607
        assert 16500 < emi < 16700
    
    def test_emi_zero_principal_returns_zero(self):
        """Zero principal should return zero EMI."""
        emi = calculate_emi(principal=0, annual_rate=12.0, tenure_months=36)
        assert emi == 0
    
    def test_emi_zero_rate_simple_division(self):
        """Zero interest rate should return simple division."""
        emi = calculate_emi(principal=120000, annual_rate=0, tenure_months=12)
        assert emi == 10000  # 120000 / 12
    
    def test_emi_negative_principal_returns_zero(self):
        """Negative principal should return zero."""
        emi = calculate_emi(principal=-100000, annual_rate=12.0, tenure_months=36)
        assert emi == 0


# ================================================================================
# TEST: FULL UNDERWRITING FLOW - APPROVAL
# ================================================================================

class TestUnderwritingApproval:
    """Test successful loan approval scenarios."""
    
    def test_standard_approval(self):
        """Standard case with good credit, reasonable amount, affordable EMI."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000,
            existing_emi=10000,
            loan_tenure_months=36,
            interest_rate=12.0
        )
        
        assert result.decision == LoanDecision.APPROVED
        assert result.loan_status == "APPROVED"
        assert result.approval_reason is not None
        assert result.credit_score_passed is True
        assert result.limit_check_passed is True
        assert result.emi_affordability_passed is True
    
    def test_approval_has_calculated_emi(self):
        """Approved loan should have calculated EMI."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000,
            existing_emi=0
        )
        
        assert result.calculated_emi is not None
        assert result.calculated_emi > 0
    
    def test_approval_has_foir(self):
        """Approved loan should have FOIR percentage."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000,
            existing_emi=10000
        )
        
        assert result.foir is not None
        assert result.foir <= 50  # Must be within threshold for approval
    
    def test_approval_has_timestamp(self):
        """Approved loan should have timestamp."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.timestamp is not None
        assert "T" in result.timestamp  # ISO format


# ================================================================================
# TEST: FULL UNDERWRITING FLOW - REJECTION
# ================================================================================

class TestUnderwritingRejection:
    """Test loan rejection scenarios."""
    
    def test_rejection_low_credit_score(self):
        """Reject for credit score below 700."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=650,  # Below 700
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.decision == LoanDecision.REJECTED
        assert result.loan_status == "REJECTED"
        assert result.rejection_reason == RejectionReason.LOW_CREDIT_SCORE.value
        assert result.credit_score_passed is False
    
    def test_rejection_exceeds_limit(self):
        """Reject for amount exceeding 2x pre-approved limit."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=1000000,  # ₹10L
            pre_approved_limit=300000,  # Max allowed: ₹6L
        )
        
        assert result.decision == LoanDecision.REJECTED
        assert result.loan_status == "REJECTED"
        assert result.rejection_reason == RejectionReason.EXCEEDS_LIMIT.value
        assert result.credit_score_passed is True
        assert result.limit_check_passed is False
    
    def test_rejection_emi_unaffordable(self):
        """Reject for EMI exceeding 50% of income."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=50000,  # Low income
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=500000,
            existing_emi=20000,  # Already high obligations
            loan_tenure_months=24  # Short tenure = higher EMI
        )
        
        assert result.decision == LoanDecision.REJECTED
        assert result.loan_status == "REJECTED"
        assert result.rejection_reason == RejectionReason.EMI_UNAFFORDABLE.value
        assert result.credit_score_passed is True
        assert result.limit_check_passed is True
        assert result.emi_affordability_passed is False
    
    def test_rejection_has_specific_reason(self):
        """Rejected loan should have specific rejection reason."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=600,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.rejection_reason is not None
        assert len(result.rejection_reason) > 0


# ================================================================================
# TEST: ENTRY CONDITION FAILURE (PENDING STATE)
# ================================================================================

class TestUnderwritingPending:
    """Test pending state when entry conditions not met."""
    
    def test_pending_income_not_verified(self):
        """Pending when income not verified."""
        result = perform_underwriting(
            income_verified=False,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.decision == LoanDecision.PENDING
        assert result.loan_status == "PENDING"
    
    def test_pending_missing_salary(self):
        """Pending when salary is missing."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=None,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.decision == LoanDecision.PENDING
    
    def test_pending_missing_credit_score(self):
        """Pending when credit score is missing."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=None,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result.decision == LoanDecision.PENDING


# ================================================================================
# TEST: DETERMINISTIC BEHAVIOR
# ================================================================================

class TestDeterministicBehavior:
    """Test that underwriting is 100% reproducible."""
    
    def test_same_inputs_same_approval(self):
        """Same inputs should always produce same approval."""
        results = []
        for _ in range(5):
            result = perform_underwriting(
                income_verified=True,
                verified_monthly_salary_inr=100000,
                credit_score=750,
                requested_loan_amount=500000,
                pre_approved_limit=300000,
                existing_emi=10000
            )
            results.append((result.decision.value, result.calculated_emi))
        
        # All results should be identical
        assert len(set(results)) == 1
    
    def test_same_inputs_same_rejection(self):
        """Same inputs should always produce same rejection."""
        results = []
        for _ in range(5):
            result = perform_underwriting(
                income_verified=True,
                verified_monthly_salary_inr=100000,
                credit_score=650,  # Below threshold
                requested_loan_amount=500000,
                pre_approved_limit=300000
            )
            results.append((result.decision.value, result.rejection_reason))
        
        # All results should be identical
        assert len(set(results)) == 1
    
    def test_different_inputs_different_results(self):
        """Different inputs should produce different results."""
        result_approve = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        result_reject = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=650,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        assert result_approve.decision != result_reject.decision


# ================================================================================
# TEST: UNDERWRITING COMPLETION CHECK
# ================================================================================

class TestUnderwritingCompletion:
    """Test that underwriting can only run once."""
    
    def test_not_completed_initially(self):
        """has_underwriting_completed should return False for new applications."""
        assert has_underwriting_completed(None) is False
        assert has_underwriting_completed("PENDING") is False
    
    def test_completed_after_approval(self):
        """has_underwriting_completed should return True after approval."""
        assert has_underwriting_completed("APPROVED") is True
    
    def test_completed_after_rejection(self):
        """has_underwriting_completed should return True after rejection."""
        assert has_underwriting_completed("REJECTED") is True


# ================================================================================
# TEST: HELPER FUNCTIONS
# ================================================================================

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_format_currency_crores(self):
        """Format currency in crores."""
        assert "Cr" in format_currency(10000000)
    
    def test_format_currency_lakhs(self):
        """Format currency in lakhs."""
        assert "L" in format_currency(500000)
    
    def test_format_currency_thousands(self):
        """Format currency in thousands."""
        assert "₹" in format_currency(50000)
    
    def test_get_approval_message(self):
        """Get human-friendly approval message."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        message = get_approval_message(result, "John")
        assert "John" in message
        assert "approved" in message.lower()
    
    def test_get_rejection_message_credit(self):
        """Get human-friendly rejection message for credit score."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=650,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        
        message = get_rejection_message(result, "John")
        assert "John" in message
        assert "credit" in message.lower()


# ================================================================================
# TEST: STATE PERSISTENCE FIELDS
# ================================================================================

class TestStatePersistence:
    """Test that required state fields are returned."""
    
    def test_result_has_loan_status(self):
        """Result should have loan_status field."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        assert hasattr(result, 'loan_status')
        assert result.loan_status in ["APPROVED", "REJECTED", "PENDING"]
    
    def test_result_has_timestamp(self):
        """Result should have timestamp field."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        assert hasattr(result, 'timestamp')
        assert result.timestamp is not None
    
    def test_approval_has_approval_reason(self):
        """Approval should have approval_reason field."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=750,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        assert result.decision == LoanDecision.APPROVED
        assert result.approval_reason is not None
    
    def test_rejection_has_rejection_reason(self):
        """Rejection should have rejection_reason field."""
        result = perform_underwriting(
            income_verified=True,
            verified_monthly_salary_inr=100000,
            credit_score=650,
            requested_loan_amount=500000,
            pre_approved_limit=300000
        )
        assert result.decision == LoanDecision.REJECTED
        assert result.rejection_reason is not None


# ================================================================================
# RUN TESTS
# ================================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 7 TEST SUITE: UNDERWRITING DECISION ENGINE")
    print("=" * 80)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
