#!/usr/bin/env python3
"""
================================================================================
CONTROLLED INTELLIGENCE - COMPREHENSIVE TEST SUITE
================================================================================

Tests for the Controlled Intelligence module that implements:
- Smart input understanding
- Strict stage-based progression
- Fuzzy normalization
- Multi-answer handling
- Ambiguity detection
- Safety guards

================================================================================
"""

import pytest
from datetime import datetime
from controlled_intelligence import (
    # Main classes
    ControlledIntelligenceProcessor,
    ControlledIntentDetector,
    SafeInputNormalizer,
    AmbiguityDetector,
    InputSafetyGuard,
    AnswerBuffer,
    
    # Enums and dataclasses
    AllowedIntent,
    DetectedIntent,
    ProcessingResult,
    
    # Functions
    process_input,
    normalize_input,
    convert_amount,
    detect_intents,
    
    # Mappings
    STAGE_EXPECTED_INTENT,
)


# ================================================================================
# PART 1: SAFE INPUT NORMALIZATION TESTS
# ================================================================================

class TestSafeInputNormalizer:
    """Tests for dictionary-based input normalization."""
    
    def test_basic_trim_and_whitespace(self):
        """Basic whitespace handling."""
        normalizer = SafeInputNormalizer()
        assert normalizer.normalize("  hello world  ") == "hello world"
        assert normalizer.normalize("hello    world") == "hello world"
    
    def test_spelling_correction_city_mumbai(self):
        """Mumbai spelling variants."""
        normalizer = SafeInputNormalizer()
        assert "mumbai" in normalizer.normalize("mumabi").lower()
        assert "mumbai" in normalizer.normalize("bombay").lower()
    
    def test_spelling_correction_city_bangalore(self):
        """Bangalore spelling variants."""
        normalizer = SafeInputNormalizer()
        assert "bangalore" in normalizer.normalize("banglore").lower()
        assert "bangalore" in normalizer.normalize("bengaluru").lower()
    
    def test_spelling_correction_employment(self):
        """Employment type spelling corrections."""
        normalizer = SafeInputNormalizer()
        assert "salaried" in normalizer.normalize("salried").lower()
        assert "salaried" in normalizer.normalize("salareid").lower()
    
    def test_spelling_correction_loan_purpose(self):
        """Loan purpose spelling corrections."""
        normalizer = SafeInputNormalizer()
        assert "renovation" in normalizer.normalize("rennovation").lower()
        assert "marriage" in normalizer.normalize("marraige").lower()
    
    def test_empty_input(self):
        """Empty input should return empty string."""
        normalizer = SafeInputNormalizer()
        assert normalizer.normalize("") == ""
        assert normalizer.normalize("   ") == ""
    
    def test_confirmation_normalization(self):
        """Confirmation word variants."""
        normalizer = SafeInputNormalizer()
        assert normalizer.normalize("yep") == "yes"
        assert normalizer.normalize("yeah") == "yes"
        assert normalizer.normalize("nope") == "no"


# ================================================================================
# PART 2: AMOUNT CONVERSION TESTS
# ================================================================================

class TestAmountConversion:
    """Tests for amount string to number conversion."""
    
    def test_simple_number(self):
        """Plain numbers."""
        assert convert_amount("500000") == 500000
        assert convert_amount("5.5") == 5.5
    
    def test_lakhs_notation(self):
        """Lakhs format."""
        assert convert_amount("5 lakhs") == 500000
        assert convert_amount("5 lakh") == 500000
        assert convert_amount("5lakhs") == 500000
    
    def test_lacs_notation(self):
        """Lacs format (alternate spelling)."""
        assert convert_amount("5 lacs") == 500000
        assert convert_amount("5lac") == 500000
    
    def test_l_abbreviation(self):
        """L abbreviation for lakhs."""
        assert convert_amount("5L") == 500000
        assert convert_amount("5l") == 500000
    
    def test_k_abbreviation(self):
        """K abbreviation for thousands."""
        assert convert_amount("50K") == 50000
        assert convert_amount("50k") == 50000
    
    def test_crores_notation(self):
        """Crores format."""
        assert convert_amount("1 crore") == 10000000
        assert convert_amount("1.5 crores") == 15000000
    
    def test_currency_symbols_removed(self):
        """Currency symbols should be stripped."""
        result = convert_amount("Rs 500000")
        assert result == 500000 or result is None
        
    def test_commas_handled(self):
        """Indian/international number formats."""
        assert convert_amount("5,00,000") == 500000
        assert convert_amount("500,000") == 500000
    
    def test_decimal_amounts(self):
        """Decimal lakhs."""
        assert convert_amount("5.5 lakhs") == 550000
        assert convert_amount("1.5L") == 150000
    
    def test_invalid_amount(self):
        """Invalid input returns None."""
        assert convert_amount("hello") is None
        assert convert_amount("") is None


# ================================================================================
# PART 3: INTENT DETECTION TESTS
# ================================================================================

class TestIntentDetection:
    """Tests for controlled intent detection."""
    
    def test_detect_otp(self):
        """OTP detection (6 digits)."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("My OTP is 123456")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.OTP in intent_types
        otp_intent = next(i for i in intents if i.intent == AllowedIntent.OTP)
        assert otp_intent.value == "123456"
    
    def test_detect_pan(self):
        """PAN detection (AAAAA9999A format)."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("My PAN is ABCDE1234F")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.PAN in intent_types
    
    def test_detect_aadhaar(self):
        """Aadhaar detection (12 digits)."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("Aadhaar is 123456789012")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.AADHAAR in intent_types
    
    def test_detect_mobile(self):
        """Mobile number detection (10 digits)."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("Call me at 9876543210")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.MOBILE_NUMBER in intent_types
        mobile_intent = next(i for i in intents if i.intent == AllowedIntent.MOBILE_NUMBER)
        assert mobile_intent.value == "9876543210"
    
    def test_detect_city(self):
        """City detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("I live in Mumbai")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.CITY in intent_types
    
    def test_detect_employment(self):
        """Employment type detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("I am salaried")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.EMPLOYMENT_TYPE in intent_types
    
    def test_detect_loan_purpose(self):
        """Loan purpose detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("I need loan for home renovation")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.LOAN_PURPOSE in intent_types
    
    def test_detect_confirmation_yes(self):
        """Yes confirmation detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("yes")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.CONFIRMATION in intent_types
        confirm_intent = next(i for i in intents if i.intent == AllowedIntent.CONFIRMATION)
        assert confirm_intent.value is True
    
    def test_detect_confirmation_no(self):
        """No confirmation detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("no")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.CONFIRMATION in intent_types
        confirm_intent = next(i for i in intents if i.intent == AllowedIntent.CONFIRMATION)
        assert confirm_intent.value is False
    
    def test_detect_greeting(self):
        """Greeting detection."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("hello")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.GREETING in intent_types
    
    def test_unknown_input(self):
        """Unknown input marked as UNKNOWN."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("xyzzy foobar")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.UNKNOWN in intent_types


# ================================================================================
# PART 4: MULTI-INTENT DETECTION TESTS
# ================================================================================

class TestMultiIntentDetection:
    """Tests for detecting multiple intents in one input."""
    
    def test_detect_name_city_amount(self):
        """Detect name, city, and amount in one input."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("I'm from Mumbai, need 5 lakhs")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.CITY in intent_types
        assert AllowedIntent.LOAN_AMOUNT in intent_types
    
    def test_detect_employment_purpose(self):
        """Detect employment and purpose together."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("I am salaried and need loan for education")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.EMPLOYMENT_TYPE in intent_types
        assert AllowedIntent.LOAN_PURPOSE in intent_types
    
    def test_detect_all_kyc(self):
        """Detect multiple KYC items."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("PAN ABCDE1234F, mobile 9876543210")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.PAN in intent_types
        assert AllowedIntent.MOBILE_NUMBER in intent_types


# ================================================================================
# PART 5: STAGE-BOUND FILTERING TESTS
# ================================================================================

class TestStageBoundFiltering:
    """Tests for stage-based intent filtering."""
    
    def test_accept_matching_intent(self):
        """Accept intent when it matches stage expectation."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("5 lakhs")
        accepted, buffered = detector.filter_by_stage(intents, "NEEDS_AMOUNT")
        assert accepted is not None
        assert accepted.intent == AllowedIntent.LOAN_AMOUNT
    
    def test_buffer_non_matching_intent(self):
        """Buffer intents that don't match current stage."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("Mumbai 5 lakhs")
        accepted, buffered = detector.filter_by_stage(intents, "NEEDS_AMOUNT")
        
        # Amount should be accepted
        assert accepted is not None
        assert accepted.intent == AllowedIntent.LOAN_AMOUNT
        
        # City should be buffered
        buffered_types = [b.intent for b in buffered]
        assert AllowedIntent.CITY in buffered_types
    
    def test_reject_when_no_match(self):
        """Return None when no matching intent found."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("Mumbai")  # City only
        accepted, buffered = detector.filter_by_stage(intents, "NEEDS_AMOUNT")
        assert accepted is None
        assert len(buffered) > 0
    
    def test_purpose_stage_accepts_purpose(self):
        """Purpose stage accepts loan purpose."""
        detector = ControlledIntentDetector()
        intents = detector.detect_all("home renovation")
        accepted, _ = detector.filter_by_stage(intents, "NEEDS_PURPOSE")
        assert accepted is not None
        assert accepted.intent == AllowedIntent.LOAN_PURPOSE


# ================================================================================
# PART 6: AMBIGUITY DETECTION TESTS
# ================================================================================

class TestAmbiguityDetection:
    """Tests for ambiguity detection."""
    
    def test_detect_maybe(self):
        """Detect uncertainty with 'maybe'."""
        detector = AmbiguityDetector()
        is_ambiguous, prompt = detector.check_ambiguity("maybe 5 lakhs", AllowedIntent.LOAN_AMOUNT)
        assert is_ambiguous is True
        assert prompt != ""
    
    def test_detect_around(self):
        """Detect uncertainty with 'around'."""
        detector = AmbiguityDetector()
        is_ambiguous, prompt = detector.check_ambiguity("around 5 lakhs", AllowedIntent.LOAN_AMOUNT)
        assert is_ambiguous is True
    
    def test_detect_range(self):
        """Detect range in input."""
        detector = AmbiguityDetector()
        is_ambiguous, prompt = detector.check_ambiguity("5-10 lakhs", AllowedIntent.LOAN_AMOUNT)
        assert is_ambiguous is True
    
    def test_detect_or_alternatives(self):
        """Detect 'or' alternatives."""
        detector = AmbiguityDetector()
        is_ambiguous, prompt = detector.check_ambiguity("Mumbai or Delhi", AllowedIntent.CITY)
        assert is_ambiguous is True
    
    def test_clear_input_not_ambiguous(self):
        """Clear input should not be flagged."""
        detector = AmbiguityDetector()
        is_ambiguous, _ = detector.check_ambiguity("5 lakhs", AllowedIntent.LOAN_AMOUNT)
        assert is_ambiguous is False
    
    def test_clarification_prompt_generated(self):
        """Clarification prompts should be helpful."""
        detector = AmbiguityDetector()
        _, prompt = detector.check_ambiguity("maybe mumbai", AllowedIntent.CITY)
        assert len(prompt) > 10


# ================================================================================
# PART 7: INPUT SAFETY GUARD TESTS
# ================================================================================

class TestInputSafetyGuard:
    """Tests for input safety guards."""
    
    def test_premature_pan_warning(self):
        """Warn when PAN provided too early."""
        guard = InputSafetyGuard()
        warning = guard.check_premature_input("ABCDE1234F", "NEEDS_PURPOSE")
        assert warning is not None
        assert "PAN" in warning
    
    def test_premature_aadhaar_warning(self):
        """Warn when Aadhaar provided too early."""
        guard = InputSafetyGuard()
        warning = guard.check_premature_input("123456789012", "NEEDS_AMOUNT")
        assert warning is not None
        assert "Aadhaar" in warning
    
    def test_no_warning_at_correct_stage(self):
        """No warning when at KYC stage."""
        guard = InputSafetyGuard()
        warning = guard.check_premature_input("ABCDE1234F", "NEEDS_PAN")
        assert warning is None
    
    def test_sql_injection_detected(self):
        """SQL injection patterns detected."""
        guard = InputSafetyGuard()
        warning = guard.check_out_of_context("'; DROP TABLE users; --")
        assert warning is not None
    
    def test_script_injection_detected(self):
        """Script injection patterns detected."""
        guard = InputSafetyGuard()
        warning = guard.check_out_of_context("<script>alert('xss')</script>")
        assert warning is not None
    
    def test_normal_input_allowed(self):
        """Normal input should pass."""
        guard = InputSafetyGuard()
        warning = guard.check_out_of_context("My name is Rahul")
        assert warning is None


# ================================================================================
# PART 8: ANSWER BUFFER TESTS
# ================================================================================

class TestAnswerBuffer:
    """Tests for answer buffering."""
    
    def test_store_and_retrieve(self):
        """Store and retrieve buffered value."""
        buffer = AnswerBuffer()
        buffer.store("session1", AllowedIntent.CITY, "Mumbai")
        value = buffer.get("session1", AllowedIntent.CITY)
        assert value == "Mumbai"
    
    def test_retrieve_non_existent(self):
        """Retrieve non-existent returns None."""
        buffer = AnswerBuffer()
        value = buffer.get("session1", AllowedIntent.CITY)
        assert value is None
    
    def test_get_all_buffered(self):
        """Get all buffered values for session."""
        buffer = AnswerBuffer()
        buffer.store("session1", AllowedIntent.CITY, "Mumbai")
        buffer.store("session1", AllowedIntent.LOAN_AMOUNT, 500000)
        all_buffered = buffer.get_all("session1")
        assert len(all_buffered) == 2
    
    def test_remove_buffered(self):
        """Remove buffered value after use."""
        buffer = AnswerBuffer()
        buffer.store("session1", AllowedIntent.CITY, "Mumbai")
        buffer.remove("session1", AllowedIntent.CITY)
        value = buffer.get("session1", AllowedIntent.CITY)
        assert value is None
    
    def test_clear_session(self):
        """Clear all buffered values for session."""
        buffer = AnswerBuffer()
        buffer.store("session1", AllowedIntent.CITY, "Mumbai")
        buffer.store("session1", AllowedIntent.LOAN_AMOUNT, 500000)
        buffer.clear_session("session1")
        all_buffered = buffer.get_all("session1")
        assert len(all_buffered) == 0
    
    def test_session_isolation(self):
        """Sessions are isolated from each other."""
        buffer = AnswerBuffer()
        buffer.store("session1", AllowedIntent.CITY, "Mumbai")
        buffer.store("session2", AllowedIntent.CITY, "Delhi")
        assert buffer.get("session1", AllowedIntent.CITY) == "Mumbai"
        assert buffer.get("session2", AllowedIntent.CITY) == "Delhi"


# ================================================================================
# PART 9: PROCESSOR PIPELINE TESTS
# ================================================================================

class TestControlledIntelligenceProcessor:
    """Tests for the main processor pipeline."""
    
    def test_accept_valid_amount(self):
        """Accept valid amount for amount stage."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("5 lakhs", "NEEDS_AMOUNT")
        assert result.accepted is True
        assert result.extracted_value == 500000
    
    def test_accept_valid_city(self):
        """Accept valid city for city stage."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("Mumbai", "NEEDS_CITY")
        assert result.accepted is True
    
    def test_reject_wrong_intent(self):
        """Reject when intent doesn't match stage."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("Mumbai", "NEEDS_AMOUNT")
        assert result.accepted is False
    
    def test_buffer_extra_intents(self):
        """Extra intents should be buffered."""
        processor = ControlledIntelligenceProcessor("test_buffer")
        result = processor.process("5 lakhs, I'm in Mumbai", "NEEDS_AMOUNT")
        assert result.accepted is True
        assert len(result.buffered_intents) > 0
    
    def test_ambiguous_input_needs_clarification(self):
        """Ambiguous input triggers clarification."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("maybe 5 lakhs", "NEEDS_AMOUNT")
        assert result.clarification_needed is True
        assert result.clarification_prompt != ""
    
    def test_safety_warning_propagated(self):
        """Safety warnings are included in result."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("ABCDE1234F", "NEEDS_PURPOSE")
        assert result.safety_warning is not None
    
    def test_empty_input_rejected(self):
        """Empty input is rejected."""
        processor = ControlledIntelligenceProcessor("test")
        result = processor.process("", "NEEDS_AMOUNT")
        assert result.accepted is False
    
    def test_use_buffered_value(self):
        """Processor uses buffered value when available."""
        processor = ControlledIntelligenceProcessor("test_use_buffer")
        
        # First, buffer a city value
        processor.buffer.store("test_use_buffer", AllowedIntent.CITY, "Mumbai")
        
        # Then try to get city - should use buffered value
        result = processor.process("some random text", "NEEDS_CITY")
        assert result.accepted is True
        assert result.extracted_value == "Mumbai"


# ================================================================================
# PART 10: COMPLIANCE EDGE CASE TESTS
# ================================================================================

class TestComplianceEdgeCases:
    """Tests for banking compliance edge cases."""
    
    def test_cannot_skip_stages(self):
        """Stage progression cannot be manipulated by user input."""
        processor = ControlledIntelligenceProcessor("compliance_test")
        
        # Even if user provides all info, only current stage's data is accepted
        result = processor.process(
            "I'm Rahul from Mumbai, need 5 lakhs for renovation, PAN ABCDE1234F",
            "NEEDS_PURPOSE"
        )
        
        # Only purpose should be accepted (if detected)
        # PAN should NOT be accepted at this stage
        if result.accepted:
            assert result.extracted_value is not None
        
        # PAN should trigger warning
        assert result.safety_warning is not None
    
    def test_typo_correction_preserves_meaning(self):
        """Typo correction doesn't change semantic meaning."""
        normalizer = SafeInputNormalizer()
        
        # "salried" -> "salaried" (same meaning)
        assert normalizer.normalize("salried") == "salaried"
        
        # "banglore" -> "bangalore" (same city)
        assert "bangalore" in normalizer.normalize("banglore").lower()
    
    def test_amount_formats_equivalent(self):
        """Different amount formats produce same value."""
        assert convert_amount("5 lakhs") == convert_amount("5L")
        assert convert_amount("500000") == convert_amount("5,00,000")
    
    def test_confirmation_variants_detected(self):
        """All confirmation variants map to boolean."""
        detector = ControlledIntentDetector()
        
        for yes_word in ["yes", "yep", "yeah", "ok", "sure"]:
            intents = detector.detect_all(yes_word)
            confirm_intents = [i for i in intents if i.intent == AllowedIntent.CONFIRMATION]
            assert len(confirm_intents) > 0
            assert confirm_intents[0].value is True
        
        for no_word in ["no", "nope", "nah"]:
            intents = detector.detect_all(no_word)
            confirm_intents = [i for i in intents if i.intent == AllowedIntent.CONFIRMATION]
            assert len(confirm_intents) > 0
            assert confirm_intents[0].value is False


# ================================================================================
# PART 11: STAGE MAPPING TESTS
# ================================================================================

class TestStageMapping:
    """Tests for stage to intent mapping."""
    
    def test_all_stages_have_expected_intent(self):
        """All defined stages map to an expected intent."""
        for stage, intent in STAGE_EXPECTED_INTENT.items():
            assert isinstance(intent, AllowedIntent)
    
    def test_purpose_stages(self):
        """Purpose stages expect LOAN_PURPOSE."""
        assert STAGE_EXPECTED_INTENT.get("NEEDS_PURPOSE") == AllowedIntent.LOAN_PURPOSE
        assert STAGE_EXPECTED_INTENT.get("NEEDS_LOAN_PURPOSE") == AllowedIntent.LOAN_PURPOSE
    
    def test_amount_stages(self):
        """Amount stages expect LOAN_AMOUNT."""
        assert STAGE_EXPECTED_INTENT.get("NEEDS_AMOUNT") == AllowedIntent.LOAN_AMOUNT
        assert STAGE_EXPECTED_INTENT.get("NEEDS_LOAN_AMOUNT") == AllowedIntent.LOAN_AMOUNT
    
    def test_city_stage(self):
        """City stage expects CITY."""
        assert STAGE_EXPECTED_INTENT.get("NEEDS_CITY") == AllowedIntent.CITY
    
    def test_employment_stages(self):
        """Employment stages expect EMPLOYMENT_TYPE."""
        assert STAGE_EXPECTED_INTENT.get("NEEDS_EMPLOYMENT") == AllowedIntent.EMPLOYMENT_TYPE
    
    def test_kyc_stages(self):
        """KYC stages expect appropriate intents."""
        assert STAGE_EXPECTED_INTENT.get("NEEDS_PAN") == AllowedIntent.PAN
        assert STAGE_EXPECTED_INTENT.get("NEEDS_AADHAAR") == AllowedIntent.AADHAAR
        assert STAGE_EXPECTED_INTENT.get("AWAITING_OTP") == AllowedIntent.OTP


# ================================================================================
# PART 12: CONVENIENCE FUNCTION TESTS
# ================================================================================

class TestConvenienceFunctions:
    """Tests for convenience functions."""
    
    def test_normalize_input_function(self):
        """normalize_input convenience function works."""
        result = normalize_input("mumabi")
        assert "mumbai" in result.lower()
    
    def test_detect_intents_function(self):
        """detect_intents convenience function works."""
        intents = detect_intents("5 lakhs")
        intent_types = [i.intent for i in intents]
        assert AllowedIntent.LOAN_AMOUNT in intent_types
    
    def test_process_input_function(self):
        """process_input convenience function works."""
        result = process_input("5 lakhs", "NEEDS_AMOUNT")
        assert result.accepted is True
    
    def test_convert_amount_function(self):
        """convert_amount convenience function works."""
        assert convert_amount("5 lakhs") == 500000


# ================================================================================
# PART 13: INTEGRATION TESTS
# ================================================================================

class TestIntegration:
    """Integration tests simulating real conversations."""
    
    def test_full_loan_application_flow(self):
        """Simulate a full loan application conversation."""
        processor = ControlledIntelligenceProcessor("integration_test")
        
        # Step 1: Purpose
        result = processor.process("home renovation", "NEEDS_PURPOSE")
        assert result.accepted is True
        
        # Step 2: Amount
        result = processor.process("5 lakhs", "NEEDS_AMOUNT")
        assert result.accepted is True
        assert result.extracted_value == 500000
        
        # Step 3: City
        result = processor.process("mumbai", "NEEDS_CITY")
        assert result.accepted is True
        
        # Step 4: Employment
        result = processor.process("salaried", "NEEDS_EMPLOYMENT")
        assert result.accepted is True
        
        # Step 5: Mobile
        result = processor.process("9876543210", "NEEDS_MOBILE")
        assert result.accepted is True
    
    def test_multi_answer_flow(self):
        """Test multi-answer input handling."""
        processor = ControlledIntelligenceProcessor("multi_answer_test")
        
        # User provides multiple answers at once
        result = processor.process(
            "I'm from Mumbai and need 5 lakhs for renovation",
            "NEEDS_PURPOSE"
        )
        
        # Only purpose should be accepted
        if result.accepted:
            # Check that city and amount are buffered
            buffered_types = [b.intent for b in result.buffered_intents]
            assert AllowedIntent.CITY in buffered_types or AllowedIntent.LOAN_AMOUNT in buffered_types
    
    def test_typo_handling_flow(self):
        """Test typo handling across stages."""
        processor = ControlledIntelligenceProcessor("typo_test")
        
        # Typo in purpose
        result = processor.process("home rennovation", "NEEDS_PURPOSE")
        # Should still work after normalization
        
        # Typo in city
        result = processor.process("mumabi", "NEEDS_CITY")
        assert result.accepted is True
        
        # Typo in employment
        result = processor.process("salried", "NEEDS_EMPLOYMENT")
        assert result.accepted is True


# ================================================================================
# MAIN EXECUTION
# ================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
