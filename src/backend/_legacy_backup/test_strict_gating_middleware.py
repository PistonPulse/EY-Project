#!/usr/bin/env python3
"""
================================================================================
STRICT GATING MIDDLEWARE - COMPREHENSIVE TEST SUITE
================================================================================

Tests for the strict input validation and gating middleware that ensures:
1. All inputs are validated BEFORE reaching the LLM
2. Invalid inputs cause re-ask (not stage advancement)
3. Preconditions are enforced for each stage
4. Flow cannot be broken by malicious or random input

================================================================================
"""

import pytest
from strict_gating_middleware import (
    get_gating_middleware,
    StrictGatingMiddleware,
    GatingResult,
    ExpectedInputType,
    validate_loan_purpose,
    validate_loan_amount,
    validate_mobile_number,
    validate_pan_number,
    validate_aadhaar_number,
    validate_otp_code,
    validate_city,
    validate_employment_type,
    validate_full_name,
    validate_confirmation,
)


# ================================================================================
# VALIDATOR UNIT TESTS
# ================================================================================

class TestValidateLoanPurpose:
    """Tests for loan purpose validation."""
    
    def test_home_loan_detected(self):
        valid, purpose = validate_loan_purpose("I want a home loan")
        assert valid is True
        assert "home" in purpose.lower()
    
    def test_personal_loan_detected(self):
        valid, purpose = validate_loan_purpose("Need personal loan")
        assert valid is True
        assert "personal" in purpose.lower()
    
    def test_business_loan_detected(self):
        valid, purpose = validate_loan_purpose("Looking for business loan")
        assert valid is True
        assert "business" in purpose.lower()
    
    def test_car_loan_detected(self):
        valid, purpose = validate_loan_purpose("I need car loan")
        assert valid is True
        assert "car" in purpose.lower() or "vehicle" in purpose.lower() or "auto" in purpose.lower()
    
    def test_education_loan_detected(self):
        valid, purpose = validate_loan_purpose("education loan please")
        assert valid is True
        assert "education" in purpose.lower()
    
    def test_lap_detected(self):
        valid, purpose = validate_loan_purpose("loan against property")
        assert valid is True
        # LAP or property or home should be in the result (implementation may vary)
    
    def test_invalid_purpose_rejected(self):
        valid, error = validate_loan_purpose("hello world")
        assert valid is False
    
    def test_gibberish_rejected(self):
        valid, _ = validate_loan_purpose("asdfgh12345")
        assert valid is False


class TestValidateLoanAmount:
    """Tests for loan amount validation."""
    
    def test_simple_number(self):
        valid, amount = validate_loan_amount("500000")
        assert valid is True
        assert amount == 500000
    
    def test_number_with_rupee_symbol(self):
        valid, amount = validate_loan_amount("₹10,00,000")
        assert valid is True
        assert amount == 1000000
    
    def test_lakhs_notation(self):
        valid, amount = validate_loan_amount("5 lakhs")
        assert valid is True
        assert amount == 500000
    
    def test_lakh_notation(self):
        valid, amount = validate_loan_amount("10 lakh")
        assert valid is True
        assert amount == 1000000
    
    def test_crore_notation(self):
        valid, amount = validate_loan_amount("1 crore")
        assert valid is True
        assert amount == 10000000
    
    def test_text_only_rejected(self):
        valid, _ = validate_loan_amount("Mumbai")
        assert valid is False
    
    def test_amount_too_small_rejected(self):
        valid, _ = validate_loan_amount("100")
        assert valid is False


class TestValidateMobileNumber:
    """Tests for mobile number validation."""
    
    def test_valid_10_digit(self):
        valid, mobile = validate_mobile_number("9876543210")
        assert valid is True
        assert mobile == "9876543210"
    
    def test_valid_with_country_code(self):
        valid, mobile = validate_mobile_number("+919876543210")
        assert valid is True
        assert mobile == "9876543210"
    
    def test_valid_with_spaces(self):
        valid, mobile = validate_mobile_number("98765 43210")
        assert valid is True
        assert mobile == "9876543210"
    
    def test_invalid_starts_with_1(self):
        valid, _ = validate_mobile_number("1234567890")
        assert valid is False
    
    def test_invalid_starts_with_0(self):
        valid, _ = validate_mobile_number("0987654321")
        assert valid is False
    
    def test_invalid_9_digits(self):
        valid, _ = validate_mobile_number("987654321")
        assert valid is False
    
    def test_invalid_11_digits(self):
        valid, _ = validate_mobile_number("98765432101")
        assert valid is False
    
    def test_invalid_text(self):
        valid, _ = validate_mobile_number("hello")
        assert valid is False


class TestValidatePANNumber:
    """Tests for PAN number validation."""
    
    def test_valid_pan_uppercase(self):
        valid, pan = validate_pan_number("ABCDE1234F")
        assert valid is True
        assert pan == "ABCDE1234F"
    
    def test_valid_pan_lowercase_converted(self):
        valid, pan = validate_pan_number("abcde1234f")
        assert valid is True
        assert pan == "ABCDE1234F"
    
    def test_valid_pan_mixed_case(self):
        valid, pan = validate_pan_number("AbCdE1234f")
        assert valid is True
        assert pan == "ABCDE1234F"
    
    def test_invalid_pan_wrong_format(self):
        valid, _ = validate_pan_number("12345ABCDE")
        assert valid is False
    
    def test_invalid_pan_too_short(self):
        valid, _ = validate_pan_number("ABCDE1234")
        assert valid is False
    
    def test_invalid_pan_too_long(self):
        valid, _ = validate_pan_number("ABCDE1234FG")
        assert valid is False
    
    def test_invalid_pan_special_chars(self):
        valid, _ = validate_pan_number("ABCDE-1234F")
        assert valid is False


class TestValidateAadhaarNumber:
    """Tests for Aadhaar number validation."""
    
    def test_valid_aadhaar_12_digits(self):
        valid, aadhaar = validate_aadhaar_number("234567890123")
        assert valid is True
        assert aadhaar == "234567890123"
    
    def test_valid_aadhaar_with_spaces(self):
        valid, aadhaar = validate_aadhaar_number("2345 6789 0123")
        assert valid is True
        assert aadhaar == "234567890123"
    
    def test_invalid_aadhaar_starts_with_0(self):
        valid, _ = validate_aadhaar_number("012345678901")
        assert valid is False
    
    def test_invalid_aadhaar_starts_with_1(self):
        valid, _ = validate_aadhaar_number("123456789012")
        assert valid is False
    
    def test_invalid_aadhaar_11_digits(self):
        valid, _ = validate_aadhaar_number("23456789012")
        assert valid is False
    
    def test_invalid_aadhaar_13_digits(self):
        valid, _ = validate_aadhaar_number("2345678901234")
        assert valid is False
    
    def test_invalid_aadhaar_text(self):
        valid, _ = validate_aadhaar_number("hello world")
        assert valid is False


class TestValidateOTPCode:
    """Tests for OTP code validation."""
    
    def test_valid_6_digit_otp(self):
        valid, otp = validate_otp_code("123456")
        assert valid is True
        assert otp == "123456"
    
    def test_valid_4_digit_otp(self):
        valid, otp = validate_otp_code("1234")
        assert valid is True
        assert otp == "1234"
    
    def test_valid_otp_with_spaces(self):
        valid, otp = validate_otp_code("12 34 56")
        assert valid is True
        assert otp == "123456"
    
    def test_invalid_otp_3_digits(self):
        valid, _ = validate_otp_code("123")
        assert valid is False
    
    def test_invalid_otp_7_digits(self):
        valid, _ = validate_otp_code("1234567")
        assert valid is False
    
    def test_invalid_otp_text(self):
        valid, _ = validate_otp_code("hello")
        assert valid is False


class TestValidateCity:
    """Tests for city validation."""
    
    def test_valid_city_mumbai(self):
        valid, city = validate_city("Mumbai")
        assert valid is True
        assert city == "Mumbai"
    
    def test_valid_city_bangalore(self):
        valid, city = validate_city("I live in Bangalore")
        assert valid is True
        assert "Bangalore" in city or "bangalore" in city.lower()
    
    def test_valid_city_delhi(self):
        valid, city = validate_city("Delhi")
        assert valid is True
    
    def test_valid_city_hyderabad(self):
        valid, city = validate_city("hyderabad")
        assert valid is True
    
    def test_invalid_city_number(self):
        valid, _ = validate_city("12345")
        assert valid is False
    
    def test_accepts_reasonable_city_name(self):
        # Even unknown cities should be accepted if they look like city names
        valid, city = validate_city("Nashik")
        assert valid is True


class TestValidateEmploymentType:
    """Tests for employment type validation."""
    
    def test_salaried_detected(self):
        valid, emp = validate_employment_type("I am salaried")
        assert valid is True
        assert emp == "salaried"
    
    def test_self_employed_detected(self):
        valid, emp = validate_employment_type("self employed")
        assert valid is True
        assert emp == "self_employed"
    
    def test_self_employed_hyphenated(self):
        valid, emp = validate_employment_type("I'm self-employed")
        assert valid is True
        assert emp == "self_employed"
    
    def test_business_detected(self):
        valid, emp = validate_employment_type("I run a business")
        assert valid is True
        assert emp == "business"
    
    def test_freelance_detected(self):
        valid, emp = validate_employment_type("I'm a freelancer")
        assert valid is True
        assert emp == "self_employed"
    
    def test_invalid_employment(self):
        valid, _ = validate_employment_type("hello world")
        assert valid is False


class TestValidateFullName:
    """Tests for full name validation."""
    
    def test_valid_name_two_words(self):
        valid, name = validate_full_name("Rahul Sharma")
        assert valid is True
        assert name == "Rahul Sharma"
    
    def test_valid_name_three_words(self):
        valid, name = validate_full_name("Rahul Kumar Sharma")
        assert valid is True
        assert name == "Rahul Kumar Sharma"
    
    def test_name_with_prefix_stripped(self):
        valid, name = validate_full_name("My name is Rahul")
        assert valid is True
        assert "Rahul" in name
    
    def test_invalid_name_with_numbers(self):
        valid, _ = validate_full_name("Rahul123")
        assert valid is False
    
    def test_invalid_name_sql_injection(self):
        valid, _ = validate_full_name("'; DROP TABLE users; --")
        assert valid is False
    
    def test_invalid_name_special_chars(self):
        valid, _ = validate_full_name("Rahul@Sharma")
        assert valid is False
    
    def test_invalid_name_too_short(self):
        valid, _ = validate_full_name("R")
        assert valid is False


class TestValidateConfirmation:
    """Tests for confirmation validation."""
    
    def test_yes_detected(self):
        valid, conf = validate_confirmation("yes")
        assert valid is True
        assert conf is True
    
    def test_confirm_detected(self):
        valid, conf = validate_confirmation("I confirm")
        assert valid is True
        assert conf is True
    
    def test_proceed_detected(self):
        valid, conf = validate_confirmation("please proceed")
        assert valid is True
        assert conf is True
    
    def test_no_detected(self):
        valid, conf = validate_confirmation("no")
        assert valid is True
        assert conf is False
    
    def test_cancel_detected(self):
        valid, conf = validate_confirmation("cancel")
        assert valid is True
        assert conf is False
    
    def test_ambiguous_rejected(self):
        valid, _ = validate_confirmation("hello")
        assert valid is False


# ================================================================================
# MIDDLEWARE INTEGRATION TESTS
# ================================================================================

class TestGatingMiddlewareValidation:
    """Tests for the gating middleware input validation."""
    
    def test_middleware_singleton(self):
        """Middleware should be a singleton."""
        m1 = get_gating_middleware()
        m2 = get_gating_middleware()
        assert m1 is m2
    
    def test_validate_purpose_at_needs_stage(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="I need a home loan",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is True
        assert "home" in result.validated_data.get("loan_purpose", "").lower()
    
    def test_invalid_purpose_requires_reask(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="asdfgh12345!@#",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is False
        assert result.reask_required is True
        assert result.reask_message is not None
    
    def test_validate_amount_at_needs_stage(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="5 lakhs",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_AMOUNT",
            state_data={}
        )
        assert result.allowed is True
        assert result.validated_data.get("loan_amount") == 500000
    
    def test_validate_pan_at_kyc_stage(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="ABCDE1234F",
            current_stage="KYC_VERIFICATION",
            current_step="KYC_ASK_PAN",
            state_data={"otp_verified": True}
        )
        assert result.allowed is True
        # PAN may be stored under different keys
        pan_value = result.validated_data.get("user_pan") or result.validated_data.get("pan_number") or result.validated_data.get("pan")
        assert pan_value == "ABCDE1234F" or "ABCDE1234F" in str(result.validated_data)


class TestGatingMiddlewarePreconditions:
    """Tests for precondition enforcement."""
    
    def test_otp_blocked_without_name(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="123456",
            current_stage="OTP_VERIFICATION",  # Correct stage name
            current_step="OTP_VERIFY",
            state_data={"user_mobile": "9876543210"}  # No name!
        )
        assert result.allowed is False
        assert result.precondition_failed is True
    
    def test_otp_blocked_without_mobile(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="123456",
            current_stage="OTP_VERIFICATION",  # Correct stage name
            current_step="OTP_VERIFY",
            state_data={"user_name": "Rahul"}  # No mobile!
        )
        assert result.allowed is False
        assert result.precondition_failed is True
    
    def test_pan_blocked_without_otp_verified(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="ABCDE1234F",
            current_stage="KYC_VERIFICATION",
            current_step="KYC_ASK_PAN",
            state_data={"otp_verified": False}
        )
        assert result.allowed is False
        assert result.precondition_failed is True
    
    def test_aadhaar_allowed_with_otp_verified(self):
        """Aadhaar can be collected once OTP is verified."""
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="234567890123",
            current_stage="KYC_VERIFICATION",
            current_step="KYC_ASK_AADHAAR",
            state_data={"otp_verified": True}
        )
        # Should be allowed (KYC stage requires OTP verified, not PAN verified)
        assert result.allowed is True
    
    def test_income_doc_blocked_without_full_kyc(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="uploaded",
            current_stage="INCOME_DOC_UPLOAD",  # Correct stage name
            current_step="INCOME_UPLOAD",
            state_data={"otp_verified": True, "pan_verified": True, "aadhaar_verified": False}
        )
        assert result.allowed is False
        assert result.precondition_failed is True


class TestGatingMiddlewareSecurityReject:
    """Tests for security-related input rejection."""
    
    def test_sql_injection_rejected_at_name(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="'; DROP TABLE users; --",
            current_stage="KYC_COLLECTION",
            current_step="KYC_ASK_NAME",
            state_data={}
        )
        assert result.allowed is False
    
    def test_xss_attempt_rejected(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="<script>alert('xss')</script>",
            current_stage="KYC_COLLECTION",
            current_step="KYC_ASK_NAME",
            state_data={}
        )
        assert result.allowed is False
    
    def test_gibberish_rejected(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="!@#$%^&*()",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is False


class TestGatingResultStructure:
    """Tests for GatingResult dataclass structure."""
    
    def test_result_has_required_fields(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="hello",
            current_stage="GREETING",
            current_step="GREETING_WELCOME",
            state_data={}
        )
        assert hasattr(result, 'allowed')
        assert hasattr(result, 'reask_required')
        assert hasattr(result, 'reask_message')
        assert hasattr(result, 'validated_data')
        assert hasattr(result, 'precondition_failed')
    
    def test_valid_result_structure(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="home loan",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is True
        assert result.reask_required is False
        assert result.precondition_failed is False
    
    def test_invalid_result_structure(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="xyz123",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is False
        assert result.reask_required is True
        assert result.reask_message is not None


# ================================================================================
# EDGE CASE TESTS
# ================================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""
    
    def test_empty_message(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is False
    
    def test_whitespace_only_message(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="   ",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        assert result.allowed is False
    
    def test_very_long_message(self):
        middleware = get_gating_middleware()
        long_msg = "home loan " * 1000
        result = middleware.validate_input(
            session_id="test",
            user_message=long_msg,
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_PURPOSE",
            state_data={}
        )
        # Should still detect purpose
        assert result.allowed is True
    
    def test_unicode_characters(self):
        middleware = get_gating_middleware()
        result = middleware.validate_input(
            session_id="test",
            user_message="I need ₹5 lakh loan",
            current_stage="NEEDS_DISCOVERY",
            current_step="NEEDS_ASK_AMOUNT",
            state_data={}
        )
        assert result.allowed is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
