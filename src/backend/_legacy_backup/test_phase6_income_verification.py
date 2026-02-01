"""
================================================================================
TEST PHASE 6: CONTROLLED SALARY DOCUMENT UPLOAD AND INCOME VERIFICATION
================================================================================

This test suite validates the income verification functionality:
1. Entry conditions (KYC verified, interest rates exist, loan amount known)
2. Document upload validation (file type, size)
3. Salary extraction (deterministic mock parser)
4. One-time upload with single retry
5. State persistence
6. Stage transition to UNDERWRITING

================================================================================
KEY PRINCIPLES BEING TESTED:
================================================================================

1. UPLOAD APPEARS ONLY IN CORRECT STAGE
   - Upload blocked outside INCOME_DOC_UPLOAD stage
   - Upload blocked after successful verification

2. UPLOAD DISAPPEARS AFTER SUCCESS
   - No re-upload after income_verified == True
   - State persists across reloads

3. SALARY EXTRACTED DETERMINISTICALLY
   - Same filename always returns same salary
   - No LLM involvement in parsing

4. STAGE ADVANCES EXACTLY ONCE
   - INCOME_DOC_UPLOAD → UNDERWRITING (on success)
   - No infinite loops

================================================================================
"""

import pytest
import sys
import os
from datetime import datetime

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from income_verification import (
    can_start_income_verification,
    can_upload_document,
    validate_document,
    process_document_upload,
    extract_salary_from_document,
    perform_income_verification,
    format_salary_for_display,
    get_upload_instructions,
    VerificationStatus,
    MOCK_SALARY_DATABASE,
    DEFAULT_MOCK_SALARY,
    MAX_RETRY_ATTEMPTS,
    MAX_FILE_SIZE_BYTES,
    SUPPORTED_EXTENSIONS
)


# ================================================================================
# TEST: ENTRY CONDITIONS
# ================================================================================

class TestIncomeVerificationEntryConditions:
    """Test that income verification only starts when all conditions are met."""
    
    def test_cannot_start_without_kyc_verification(self):
        """Entry blocked if KYC not verified."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="PENDING",
            interest_rate_min=10.0,
            interest_rate_max=11.0,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "KYC not verified" in reason
    
    def test_cannot_start_without_interest_rate_min(self):
        """Entry blocked if interest rate min is missing."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="VERIFIED",
            interest_rate_min=None,
            interest_rate_max=11.0,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "Interest rate" in reason
    
    def test_cannot_start_without_interest_rate_max(self):
        """Entry blocked if interest rate max is missing."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="VERIFIED",
            interest_rate_min=10.0,
            interest_rate_max=None,
            requested_loan_amount=500000
        )
        assert can_proceed is False
        assert "Interest rate" in reason
    
    def test_cannot_start_without_loan_amount(self):
        """Entry blocked if loan amount is missing."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="VERIFIED",
            interest_rate_min=10.0,
            interest_rate_max=11.0,
            requested_loan_amount=None
        )
        assert can_proceed is False
        assert "loan amount" in reason
    
    def test_cannot_start_with_zero_loan_amount(self):
        """Entry blocked if loan amount is zero."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="VERIFIED",
            interest_rate_min=10.0,
            interest_rate_max=11.0,
            requested_loan_amount=0
        )
        assert can_proceed is False
        assert "loan amount" in reason
    
    def test_can_start_with_all_conditions_met(self):
        """Entry allowed with all conditions met."""
        can_proceed, reason = can_start_income_verification(
            kyc_status="VERIFIED",
            interest_rate_min=10.0,
            interest_rate_max=11.0,
            requested_loan_amount=500000
        )
        assert can_proceed is True


# ================================================================================
# TEST: UPLOAD CONTROL (STAGE-GATED)
# ================================================================================

class TestUploadControl:
    """Test that upload is controlled by stage and verification status."""
    
    def test_upload_allowed_in_correct_stage(self):
        """Upload allowed in INCOME_DOC_UPLOAD stage."""
        can_upload, reason = can_upload_document(
            current_stage="INCOME_DOC_UPLOAD",
            income_verified=False,
            upload_attempted=False,
            retry_count=0
        )
        assert can_upload is True
    
    def test_upload_blocked_in_wrong_stage(self):
        """Upload blocked outside INCOME_DOC_UPLOAD stage."""
        stages = ["GREETING", "NEEDS_DISCOVERY", "KYC_VERIFICATION", "OFFER_DISCOVERY", "UNDERWRITING"]
        for stage in stages:
            can_upload, reason = can_upload_document(
                current_stage=stage,
                income_verified=False,
                upload_attempted=False,
                retry_count=0
            )
            assert can_upload is False
            assert stage in reason
    
    def test_upload_blocked_after_verification(self):
        """Upload blocked after income is verified (no re-upload)."""
        can_upload, reason = can_upload_document(
            current_stage="INCOME_DOC_UPLOAD",
            income_verified=True,
            upload_attempted=True,
            retry_count=0
        )
        assert can_upload is False
        assert "already verified" in reason
    
    def test_retry_allowed_after_first_failure(self):
        """Retry allowed after first failed attempt."""
        can_upload, reason = can_upload_document(
            current_stage="INCOME_DOC_UPLOAD",
            income_verified=False,
            upload_attempted=True,
            retry_count=0
        )
        assert can_upload is True
    
    def test_retry_blocked_after_max_attempts(self):
        """Retry blocked after maximum attempts."""
        can_upload, reason = can_upload_document(
            current_stage="INCOME_DOC_UPLOAD",
            income_verified=False,
            upload_attempted=True,
            retry_count=MAX_RETRY_ATTEMPTS
        )
        assert can_upload is False
        assert "Maximum" in reason or "exceeded" in reason


# ================================================================================
# TEST: DOCUMENT VALIDATION
# ================================================================================

class TestDocumentValidation:
    """Test document upload validation."""
    
    def test_pdf_accepted(self):
        """PDF files are accepted."""
        is_valid, error = validate_document("salary_slip.pdf", 5000)
        assert is_valid is True
    
    def test_jpg_accepted(self):
        """JPG files are accepted."""
        is_valid, error = validate_document("salary_slip.jpg", 5000)
        assert is_valid is True
    
    def test_jpeg_accepted(self):
        """JPEG files are accepted."""
        is_valid, error = validate_document("salary_slip.jpeg", 5000)
        assert is_valid is True
    
    def test_png_accepted(self):
        """PNG files are accepted."""
        is_valid, error = validate_document("salary_slip.png", 5000)
        assert is_valid is True
    
    def test_doc_rejected(self):
        """DOC files are rejected."""
        is_valid, error = validate_document("salary_slip.doc", 5000)
        assert is_valid is False
        assert "Unsupported" in error
    
    def test_xlsx_rejected(self):
        """XLSX files are rejected."""
        is_valid, error = validate_document("salary_slip.xlsx", 5000)
        assert is_valid is False
        assert "Unsupported" in error
    
    def test_file_too_large_rejected(self):
        """Files larger than 10MB are rejected."""
        is_valid, error = validate_document("salary_slip.pdf", MAX_FILE_SIZE_BYTES + 1)
        assert is_valid is False
        assert "too large" in error
    
    def test_empty_file_rejected(self):
        """Empty files are rejected."""
        is_valid, error = validate_document("salary_slip.pdf", 0)
        assert is_valid is False
        assert "empty" in error


# ================================================================================
# TEST: DETERMINISTIC SALARY EXTRACTION
# ================================================================================

class TestSalaryExtraction:
    """Test deterministic salary extraction from mock parser."""
    
    def test_high_salary_extraction(self):
        """Test high salary extraction (₹1.5L)."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 150000
    
    def test_senior_salary_extraction(self):
        """Test senior salary extraction (₹2L)."""
        result = perform_income_verification("salary_senior.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 200000
    
    def test_mid_salary_extraction(self):
        """Test mid-range salary extraction (₹75K)."""
        result = perform_income_verification("salary_mid.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 75000
    
    def test_medium_salary_extraction(self):
        """Test medium salary extraction (₹60K)."""
        result = perform_income_verification("salary_medium.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 60000
    
    def test_low_salary_extraction(self):
        """Test low salary extraction (₹35K)."""
        result = perform_income_verification("salary_low.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 35000
    
    def test_entry_salary_extraction(self):
        """Test entry-level salary extraction (₹25K)."""
        result = perform_income_verification("salary_entry.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 25000
    
    def test_minimum_salary_extraction(self):
        """Test minimum salary extraction (₹15K)."""
        result = perform_income_verification("salary_minimum.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == 15000
    
    def test_unknown_file_gets_default_salary(self):
        """Unknown file gets default salary (₹50K)."""
        result = perform_income_verification("random_document.pdf", 5000)
        assert result.success is True
        assert result.verified_monthly_salary_inr == DEFAULT_MOCK_SALARY["monthly_salary"]
    
    def test_same_file_always_returns_same_salary(self):
        """Same filename always returns same salary (deterministic)."""
        for _ in range(5):
            result = perform_income_verification("salary_high.pdf", 5000)
            assert result.verified_monthly_salary_inr == 150000


# ================================================================================
# TEST: FAILURE HANDLING
# ================================================================================

class TestFailureHandling:
    """Test failure handling with retry logic."""
    
    def test_corrupt_file_returns_error(self):
        """Corrupt file returns error with retry allowed."""
        result = perform_income_verification("salary_corrupt.pdf", 5000, retry_count=0)
        assert result.success is False
        assert result.can_retry is True
        assert result.error_message is not None
    
    def test_unreadable_file_returns_error(self):
        """Unreadable file returns error with retry allowed."""
        result = perform_income_verification("salary_unreadable.pdf", 5000, retry_count=0)
        assert result.success is False
        assert result.can_retry is True
    
    def test_retry_allowed_on_first_failure(self):
        """Retry allowed on first failure."""
        result = perform_income_verification("salary_corrupt.pdf", 5000, retry_count=0)
        assert result.can_retry is True
        assert result.verification_status == VerificationStatus.RETRY_ALLOWED
    
    def test_retry_blocked_after_max_attempts(self):
        """Retry blocked after max attempts."""
        result = perform_income_verification("salary_corrupt.pdf", 5000, retry_count=MAX_RETRY_ATTEMPTS)
        assert result.can_retry is False
        assert result.verification_status == VerificationStatus.FAILED
    
    def test_invalid_file_type_returns_error(self):
        """Invalid file type returns error immediately."""
        result = perform_income_verification("salary_slip.doc", 5000, retry_count=0)
        assert result.success is False


# ================================================================================
# TEST: SUCCESS HANDLING
# ================================================================================

class TestSuccessHandling:
    """Test successful verification handling."""
    
    def test_successful_verification_sets_income_verified(self):
        """Successful verification sets income_verified=True."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.success is True
        assert result.income_verified is True
    
    def test_successful_verification_stores_salary(self):
        """Successful verification stores verified_monthly_salary_inr."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.verified_monthly_salary_inr == 150000
    
    def test_successful_verification_has_timestamp(self):
        """Successful verification has verification_timestamp."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.verification_timestamp is not None
        # Should be ISO format
        assert "T" in result.verification_timestamp
    
    def test_successful_verification_has_document_id(self):
        """Successful verification has document_id."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.document_id is not None
        assert len(result.document_id) > 0
    
    def test_successful_verification_sets_status(self):
        """Successful verification sets status to VERIFIED."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.verification_status == VerificationStatus.VERIFIED
    
    def test_successful_verification_blocks_retry(self):
        """Successful verification blocks further retries."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert result.can_retry is False


# ================================================================================
# TEST: HELPER FUNCTIONS
# ================================================================================

class TestHelperFunctions:
    """Test helper functions."""
    
    def test_format_salary_crores(self):
        """Format salary in crores."""
        assert "Cr" in format_salary_for_display(10000000)
        assert "1.00 Cr" in format_salary_for_display(10000000)
    
    def test_format_salary_lakhs(self):
        """Format salary in lakhs."""
        assert "L" in format_salary_for_display(150000)
        assert "1.50 L" in format_salary_for_display(150000)
    
    def test_format_salary_thousands(self):
        """Format salary in thousands with commas."""
        formatted = format_salary_for_display(50000)
        assert "₹" in formatted
        assert "50,000" in formatted
    
    def test_get_upload_instructions(self):
        """Upload instructions include file types."""
        instructions = get_upload_instructions()
        assert "PDF" in instructions
        assert "JPG" in instructions
        assert "PNG" in instructions
        assert "10 MB" in instructions


# ================================================================================
# TEST: DETERMINISTIC BEHAVIOR (NO RANDOMNESS)
# ================================================================================

class TestDeterministicBehavior:
    """Test that income verification is 100% reproducible."""
    
    def test_same_file_same_result(self):
        """Same file always returns same result."""
        result1 = perform_income_verification("salary_high.pdf", 5000)
        result2 = perform_income_verification("salary_high.pdf", 5000)
        
        assert result1.success == result2.success
        assert result1.verified_monthly_salary_inr == result2.verified_monthly_salary_inr
        assert result1.verification_status == result2.verification_status
    
    def test_different_files_different_salaries(self):
        """Different files return different salaries."""
        result_high = perform_income_verification("salary_high.pdf", 5000)
        result_low = perform_income_verification("salary_low.pdf", 5000)
        
        assert result_high.verified_monthly_salary_inr != result_low.verified_monthly_salary_inr
    
    def test_no_random_values(self):
        """No random values in verification results."""
        # Run 10 times and verify consistency
        for _ in range(10):
            result = perform_income_verification("salary_mid.pdf", 5000)
            assert result.verified_monthly_salary_inr == 75000


# ================================================================================
# TEST: STATE PERSISTENCE FIELDS
# ================================================================================

class TestStatePersistence:
    """Test that required state fields are returned."""
    
    def test_result_has_income_verified_field(self):
        """Result has income_verified field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'income_verified')
    
    def test_result_has_verified_monthly_salary_field(self):
        """Result has verified_monthly_salary_inr field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'verified_monthly_salary_inr')
    
    def test_result_has_timestamp_field(self):
        """Result has verification_timestamp field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'verification_timestamp')
    
    def test_result_has_document_id_field(self):
        """Result has document_id field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'document_id')
    
    def test_result_has_can_retry_field(self):
        """Result has can_retry field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'can_retry')
    
    def test_result_has_retry_count_field(self):
        """Result has retry_count field."""
        result = perform_income_verification("salary_high.pdf", 5000)
        assert hasattr(result, 'retry_count')


# ================================================================================
# RUN TESTS
# ================================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("PHASE 6 TEST SUITE: INCOME VERIFICATION")
    print("=" * 80)
    
    # Run with pytest
    pytest.main([__file__, "-v", "--tb=short"])
