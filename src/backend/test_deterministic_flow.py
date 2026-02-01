"""
================================================================================
TESTS FOR DETERMINISTIC FLOW CONTROLLER
================================================================================

Tests verify:
1. Strict 13-stage sequence
2. Out-of-order input handling (ignored)
3. Stage requirements enforcement
4. Terminal state freezing
5. OTP verification
6. PAN verification
7. EMI calculation
8. Underwriting decision

================================================================================
"""

import pytest
from deterministic_flow import (
    FlowStage,
    SessionState,
    DeterministicFlowController,
    get_flow_controller,
    reset_flow_controller,
    process_message,
    get_session_state,
    reset_session,
    TERMINAL_STAGES,
    NEXT_STAGE,
    STAGE_REQUIREMENTS,
    STAGE_QUESTIONS,
    TENURE_OPTIONS,
    INTEREST_RATE_RANGE
)


# ================================================================================
# FIXTURES
# ================================================================================

@pytest.fixture
def controller():
    """Fresh controller for each test - uses singleton."""
    reset_flow_controller()
    return get_flow_controller()

@pytest.fixture
def session_id():
    """Standard test session ID."""
    return "test-session-001"


# ================================================================================
# TEST: STAGE ENUMERATION
# ================================================================================

class TestFlowStageEnum:
    """Test stage enumeration is correct."""
    
    def test_has_exactly_14_stages(self):
        """Must have exactly 14 stages (13 + REJECTION)."""
        assert len(FlowStage) == 14
    
    def test_stages_numbered_correctly(self):
        """Stages numbered 1-14."""
        assert FlowStage.GREETING.value == 1
        assert FlowStage.PURPOSE.value == 2
        assert FlowStage.AMOUNT.value == 3
        assert FlowStage.CITY.value == 4
        assert FlowStage.EMPLOYMENT_TYPE.value == 5
        assert FlowStage.NAME.value == 6
        assert FlowStage.MOBILE.value == 7
        assert FlowStage.OTP.value == 8
        assert FlowStage.KYC.value == 9
        assert FlowStage.OFFER_DISCUSSION.value == 10
        assert FlowStage.TENURE_SELECTION.value == 11
        assert FlowStage.UNDERWRITING.value == 12
        assert FlowStage.SANCTION.value == 13
        assert FlowStage.REJECTION.value == 14
    
    def test_terminal_stages(self):
        """SANCTION and REJECTION are terminal."""
        assert FlowStage.SANCTION in TERMINAL_STAGES
        assert FlowStage.REJECTION in TERMINAL_STAGES
        assert len(TERMINAL_STAGES) == 2


# ================================================================================
# TEST: STAGE TRANSITIONS
# ================================================================================

class TestStageTransitions:
    """Test stage transition matrix."""
    
    def test_greeting_to_purpose(self):
        """GREETING → PURPOSE."""
        assert NEXT_STAGE[FlowStage.GREETING] == FlowStage.PURPOSE
    
    def test_purpose_to_amount(self):
        """PURPOSE → AMOUNT."""
        assert NEXT_STAGE[FlowStage.PURPOSE] == FlowStage.AMOUNT
    
    def test_amount_to_city(self):
        """AMOUNT → CITY."""
        assert NEXT_STAGE[FlowStage.AMOUNT] == FlowStage.CITY
    
    def test_city_to_employment(self):
        """CITY → EMPLOYMENT_TYPE."""
        assert NEXT_STAGE[FlowStage.CITY] == FlowStage.EMPLOYMENT_TYPE
    
    def test_employment_to_name(self):
        """EMPLOYMENT_TYPE → NAME."""
        assert NEXT_STAGE[FlowStage.EMPLOYMENT_TYPE] == FlowStage.NAME
    
    def test_name_to_mobile(self):
        """NAME → MOBILE."""
        assert NEXT_STAGE[FlowStage.NAME] == FlowStage.MOBILE
    
    def test_mobile_to_otp(self):
        """MOBILE → OTP."""
        assert NEXT_STAGE[FlowStage.MOBILE] == FlowStage.OTP
    
    def test_otp_to_kyc(self):
        """OTP → KYC."""
        assert NEXT_STAGE[FlowStage.OTP] == FlowStage.KYC
    
    def test_kyc_to_offer(self):
        """KYC → OFFER_DISCUSSION."""
        assert NEXT_STAGE[FlowStage.KYC] == FlowStage.OFFER_DISCUSSION
    
    def test_offer_to_tenure(self):
        """OFFER_DISCUSSION → TENURE_SELECTION."""
        assert NEXT_STAGE[FlowStage.OFFER_DISCUSSION] == FlowStage.TENURE_SELECTION
    
    def test_tenure_to_underwriting(self):
        """TENURE_SELECTION → UNDERWRITING."""
        assert NEXT_STAGE[FlowStage.TENURE_SELECTION] == FlowStage.UNDERWRITING
    
    def test_terminal_stages_have_no_next(self):
        """Terminal stages have no next stage."""
        assert FlowStage.SANCTION not in NEXT_STAGE
        assert FlowStage.REJECTION not in NEXT_STAGE


# ================================================================================
# TEST: SESSION MANAGEMENT
# ================================================================================

class TestSessionManagement:
    """Test session creation and management."""
    
    def test_create_new_session(self, controller, session_id):
        """New session starts at GREETING."""
        session = controller.get_or_create_session(session_id)
        assert session.session_id == session_id
        assert session.current_stage == FlowStage.GREETING
    
    def test_get_existing_session(self, controller, session_id):
        """Getting existing session returns same instance."""
        session1 = controller.get_or_create_session(session_id)
        session1.loan_amount = 500000
        session2 = controller.get_or_create_session(session_id)
        assert session2.loan_amount == 500000
    
    def test_reset_session(self, controller, session_id):
        """Reset clears all data."""
        session = controller.get_or_create_session(session_id)
        session.loan_amount = 500000
        session.current_stage = FlowStage.AMOUNT
        
        reset_session = controller.reset_session(session_id)
        assert reset_session.current_stage == FlowStage.GREETING
        assert reset_session.loan_amount is None
    
    def test_is_frozen_false_for_new_session(self, controller, session_id):
        """New session is not frozen."""
        controller.get_or_create_session(session_id)
        assert not controller.is_frozen(session_id)
    
    def test_is_frozen_true_for_terminal_stage(self, controller, session_id):
        """Session at terminal stage is frozen."""
        session = controller.get_or_create_session(session_id)
        session.current_stage = FlowStage.SANCTION
        session.is_frozen = True
        assert controller.is_frozen(session_id)


# ================================================================================
# TEST: DATA EXTRACTION
# ================================================================================

class TestDataExtraction:
    """Test data extraction from user messages."""
    
    def test_extract_purpose_home(self, controller):
        """Extract home purpose."""
        purpose = controller._extract_purpose("i need loan for home renovation")
        assert purpose == "home"
    
    def test_extract_purpose_education(self, controller):
        """Extract education purpose."""
        purpose = controller._extract_purpose("for my daughter's education")
        assert purpose == "education"
    
    def test_extract_purpose_medical(self, controller):
        """Extract medical purpose."""
        purpose = controller._extract_purpose("medical treatment")
        assert purpose == "medical"
    
    def test_extract_amount_lakhs(self, controller):
        """Extract amount in lakhs."""
        amount = controller._extract_amount("5 lakhs")
        assert amount == 500000
    
    def test_extract_amount_lacs(self, controller):
        """Extract amount in lacs."""
        amount = controller._extract_amount("3 lacs")
        assert amount == 300000
    
    def test_extract_amount_crore(self, controller):
        """Extract amount in crores."""
        amount = controller._extract_amount("1 crore")
        assert amount == 10000000
    
    def test_extract_amount_number(self, controller):
        """Extract amount as number."""
        amount = controller._extract_amount("500000")
        assert amount == 500000
    
    def test_extract_city_mumbai(self, controller):
        """Extract city Mumbai."""
        city = controller._extract_city("I live in Mumbai")
        assert city == "Mumbai"
    
    def test_extract_city_bangalore(self, controller):
        """Extract city Bangalore."""
        city = controller._extract_city("bangalore")
        assert city == "Bangalore"
    
    def test_extract_employment_salaried(self, controller):
        """Extract salaried employment."""
        emp = controller._extract_employment_type("i am salaried")
        assert emp == "salaried"
    
    def test_extract_employment_self_employed(self, controller):
        """Extract self-employed."""
        emp = controller._extract_employment_type("i run my own business")
        assert emp == "self_employed"
    
    def test_extract_name_simple(self, controller):
        """Extract simple name."""
        name = controller._extract_name("Rahul Mehta")
        assert name == "Rahul Mehta"
    
    def test_extract_name_with_prefix(self, controller):
        """Extract name with 'my name is' prefix."""
        name = controller._extract_name("My name is Priya Sharma")
        assert name == "Priya Sharma"
    
    def test_extract_mobile_simple(self, controller):
        """Extract 10-digit mobile."""
        mobile = controller._extract_mobile("9876543210")
        assert mobile == "9876543210"
    
    def test_extract_mobile_with_prefix(self, controller):
        """Extract mobile with +91 prefix."""
        mobile = controller._extract_mobile("+91 9876543210")
        assert mobile == "9876543210"
    
    def test_extract_otp_simple(self, controller):
        """Extract 6-digit OTP."""
        otp = controller._extract_otp("123456")
        assert otp == "123456"
    
    def test_extract_pan(self, controller):
        """Extract PAN number."""
        pan = controller._extract_pan("My PAN is ABCDE1234F")
        assert pan == "ABCDE1234F"
    
    def test_extract_tenure_years(self, controller):
        """Extract tenure in years."""
        tenure = controller._extract_tenure("3 years")
        assert tenure == 36
    
    def test_extract_tenure_months(self, controller):
        """Extract tenure in months."""
        tenure = controller._extract_tenure("24 months")
        assert tenure == 24


# ================================================================================
# TEST: STRICT SEQUENCE ENFORCEMENT
# ================================================================================

class TestStrictSequence:
    """Test that stages advance ONLY in correct order."""
    
    def test_greeting_advances_on_any_input(self, controller, session_id):
        """Any input at GREETING advances to PURPOSE."""
        session, instruction, changed = controller.process_input(session_id, "Hi")
        assert session.current_stage == FlowStage.PURPOSE
        assert changed is True
    
    def test_purpose_needs_purpose(self, controller, session_id):
        """PURPOSE stage needs loan purpose to advance."""
        controller.process_input(session_id, "Hi")  # → PURPOSE
        session, instruction, changed = controller.process_input(session_id, "ok")  # Single word, no purpose keyword
        assert session.current_stage == FlowStage.PURPOSE  # Still at PURPOSE
        assert changed is False
    
    def test_purpose_advances_with_purpose(self, controller, session_id):
        """PURPOSE advances with valid purpose."""
        controller.process_input(session_id, "Hi")
        session, instruction, changed = controller.process_input(session_id, "home renovation")
        assert session.current_stage == FlowStage.AMOUNT
        assert session.loan_purpose == "home"
    
    def test_amount_ignores_purpose(self, controller, session_id):
        """At AMOUNT stage, purpose input is ignored."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home renovation")  # → AMOUNT
        session, instruction, changed = controller.process_input(session_id, "education")
        # Should still be at AMOUNT, not re-process purpose
        assert session.current_stage == FlowStage.AMOUNT
        assert session.loan_purpose == "home"  # Unchanged
    
    def test_full_sequence_happy_path(self, controller, session_id):
        """Full journey completes correctly."""
        # GREETING → PURPOSE
        session, _, _ = controller.process_input(session_id, "Hello")
        assert session.current_stage == FlowStage.PURPOSE
        
        # PURPOSE → AMOUNT
        session, _, _ = controller.process_input(session_id, "home renovation")
        assert session.current_stage == FlowStage.AMOUNT
        
        # AMOUNT → CITY
        session, _, _ = controller.process_input(session_id, "5 lakhs")
        assert session.current_stage == FlowStage.CITY
        
        # CITY → EMPLOYMENT_TYPE
        session, _, _ = controller.process_input(session_id, "Mumbai")
        assert session.current_stage == FlowStage.EMPLOYMENT_TYPE
        
        # EMPLOYMENT_TYPE → NAME
        session, _, _ = controller.process_input(session_id, "salaried")
        assert session.current_stage == FlowStage.NAME
        
        # NAME → MOBILE
        session, _, _ = controller.process_input(session_id, "Rahul Mehta")
        assert session.current_stage == FlowStage.MOBILE
        
        # MOBILE → OTP
        session, _, _ = controller.process_input(session_id, "9876543210")
        assert session.current_stage == FlowStage.OTP
        
        # OTP → KYC
        session, _, _ = controller.process_input(session_id, "123456")
        assert session.current_stage == FlowStage.KYC
        
        # KYC → OFFER_DISCUSSION
        session, _, _ = controller.process_input(session_id, "ABCDE1234F")
        assert session.current_stage == FlowStage.OFFER_DISCUSSION
        
        # OFFER_DISCUSSION → TENURE_SELECTION
        session, _, _ = controller.process_input(session_id, "yes proceed")
        assert session.current_stage == FlowStage.TENURE_SELECTION
        
        # TENURE_SELECTION → UNDERWRITING
        session, _, _ = controller.process_input(session_id, "3 years")
        assert session.current_stage == FlowStage.UNDERWRITING
        
        # UNDERWRITING → SANCTION (for test user 9876543210)
        session, _, _ = controller.process_input(session_id, "")
        assert session.current_stage == FlowStage.SANCTION
        assert session.is_frozen is True


# ================================================================================
# TEST: OUT-OF-ORDER INPUT HANDLING
# ================================================================================

class TestOutOfOrderHandling:
    """Test that out-of-order inputs are ignored."""
    
    def test_mobile_at_purpose_stage_ignored(self, controller, session_id):
        """Mobile number at PURPOSE stage is ignored."""
        controller.process_input(session_id, "Hi")  # → PURPOSE
        session, instruction, changed = controller.process_input(session_id, "9876543210")
        # Should stay at PURPOSE
        assert session.current_stage == FlowStage.PURPOSE
        assert session.user_mobile is None
    
    def test_pan_at_amount_stage_ignored(self, controller, session_id):
        """PAN at AMOUNT stage is ignored."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "education")  # → AMOUNT
        session, instruction, changed = controller.process_input(session_id, "ABCDE1234F")
        # Should stay at AMOUNT
        assert session.current_stage == FlowStage.AMOUNT
        assert session.pan_number is None
    
    def test_amount_at_name_stage_ignored(self, controller, session_id):
        """Amount at NAME stage is ignored."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")  # → AMOUNT
        controller.process_input(session_id, "5 lakhs")  # → CITY
        controller.process_input(session_id, "Delhi")  # → EMPLOYMENT_TYPE
        controller.process_input(session_id, "salaried")  # → NAME
        
        session, instruction, changed = controller.process_input(session_id, "10 lakhs")
        # Should stay at NAME, amount unchanged
        assert session.current_stage == FlowStage.NAME
        assert session.loan_amount == 500000  # Original amount


# ================================================================================
# TEST: OTP VERIFICATION
# ================================================================================

class TestOTPVerification:
    """Test OTP verification logic."""
    
    def test_otp_generated_on_mobile_input(self, controller, session_id):
        """OTP is generated when mobile is provided."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul Mehta")
        
        session = controller.get_session(session_id)
        controller.process_input(session_id, "9876543210")
        
        assert session.generated_otp is not None
        assert session.generated_otp == "123456"  # Test user
    
    def test_correct_otp_advances(self, controller, session_id):
        """Correct OTP advances to KYC."""
        # Fast forward to OTP stage
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        
        session, _, _ = controller.process_input(session_id, "123456")
        assert session.current_stage == FlowStage.KYC
        assert session.otp_verified is True
    
    def test_wrong_otp_does_not_advance(self, controller, session_id):
        """Wrong OTP does not advance."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        
        session, _, _ = controller.process_input(session_id, "999999")
        assert session.current_stage == FlowStage.OTP
        assert session.otp_verified is False
    
    def test_three_wrong_otps_freezes_session(self, controller, session_id):
        """3 wrong OTPs freezes the session."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        
        controller.process_input(session_id, "111111")  # Attempt 1
        controller.process_input(session_id, "222222")  # Attempt 2
        session, _, _ = controller.process_input(session_id, "333333")  # Attempt 3
        
        assert session.is_frozen is True
        assert session.freeze_reason == "OTP_ATTEMPTS_EXCEEDED"


# ================================================================================
# TEST: PAN VERIFICATION
# ================================================================================

class TestPANVerification:
    """Test PAN verification logic."""
    
    def test_valid_pan_advances(self, controller, session_id):
        """Valid PAN advances to OFFER_DISCUSSION."""
        # Fast forward to KYC
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session, _, _ = controller.process_input(session_id, "ABCDE1234F")
        assert session.current_stage == FlowStage.OFFER_DISCUSSION
        assert session.pan_verified is True
    
    def test_invalid_pan_format_rejected(self, controller, session_id):
        """Invalid PAN format does not advance."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session, _, _ = controller.process_input(session_id, "INVALID")
        assert session.current_stage == FlowStage.KYC  # Still at KYC


# ================================================================================
# TEST: EMI CALCULATION
# ================================================================================

class TestEMICalculation:
    """Test EMI calculation logic."""
    
    def test_emi_calculated_correctly(self, controller):
        """EMI formula is correct."""
        # 500000 @ 12% for 36 months
        emi = controller._calculate_emi(500000, 12.0, 36)
        # Expected: ~16607
        assert 16600 <= emi <= 16700
    
    def test_emi_zero_for_zero_principal(self, controller):
        """EMI is 0 for 0 principal."""
        emi = controller._calculate_emi(0, 12.0, 36)
        assert emi == 0
    
    def test_emi_zero_for_zero_tenure(self, controller):
        """EMI is 0 for 0 tenure."""
        emi = controller._calculate_emi(500000, 12.0, 0)
        assert emi == 0


# ================================================================================
# TEST: UNDERWRITING DECISION
# ================================================================================

class TestUnderwriting:
    """Test underwriting decision logic."""
    
    def test_approved_user_gets_sanction(self, controller, session_id):
        """Test user 9876543210 gets SANCTION."""
        # Full journey for approved user
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        controller.process_input(session_id, "yes")
        controller.process_input(session_id, "3 years")
        session, _, _ = controller.process_input(session_id, "")
        
        assert session.current_stage == FlowStage.SANCTION
        assert session.underwriting_result == "APPROVED"
    
    def test_rejected_user_gets_rejection(self, controller, session_id):
        """Test user 9123456781 gets REJECTION."""
        # Full journey for rejected user
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Priya Sharma")  # Full name required
        controller.process_input(session_id, "9123456781")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "MNOPQ9012R")
        controller.process_input(session_id, "yes")
        controller.process_input(session_id, "3 years")
        session, _, _ = controller.process_input(session_id, "")
        
        assert session.current_stage == FlowStage.REJECTION
        assert session.underwriting_result == "REJECTED"


# ================================================================================
# TEST: TERMINAL STATE
# ================================================================================

class TestTerminalState:
    """Test terminal state behavior."""
    
    def test_sanction_is_terminal(self, controller, session_id):
        """SANCTION stage cannot accept further input."""
        session = controller.get_or_create_session(session_id)
        session.current_stage = FlowStage.SANCTION
        session.is_frozen = True
        
        session, instruction, changed = controller.process_input(session_id, "I want another loan")
        assert session.current_stage == FlowStage.SANCTION
        assert changed is False
        assert "complete" in instruction.lower()
    
    def test_rejection_is_terminal(self, controller, session_id):
        """REJECTION stage cannot accept further input."""
        session = controller.get_or_create_session(session_id)
        session.current_stage = FlowStage.REJECTION
        session.is_frozen = True
        
        session, instruction, changed = controller.process_input(session_id, "Can I try again?")
        assert session.current_stage == FlowStage.REJECTION
        assert changed is False


# ================================================================================
# TEST: CONVENIENCE FUNCTIONS
# ================================================================================

class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    def test_process_message_returns_dict(self, session_id):
        """process_message returns proper dict."""
        reset_flow_controller()
        result = process_message(session_id, "Hello")
        
        assert "session" in result
        assert "instruction" in result
        assert "stage_changed" in result
        assert "is_frozen" in result
        assert "current_stage" in result
    
    def test_get_session_state_returns_dict(self, session_id):
        """get_session_state returns session dict."""
        reset_flow_controller()
        process_message(session_id, "Hi")
        
        state = get_session_state(session_id)
        assert "session_id" in state
        assert "current_stage" in state
    
    def test_reset_session_clears_state(self, session_id):
        """reset_session clears all state."""
        reset_flow_controller()
        process_message(session_id, "Hi")
        process_message(session_id, "home renovation")
        
        state = reset_session(session_id)
        assert state["current_stage"] == "GREETING"
        assert state["loan_purpose"] is None


# ================================================================================
# TEST: STAGE QUESTIONS
# ================================================================================

class TestStageQuestions:
    """Test that all stages have questions defined."""
    
    def test_all_stages_have_questions(self):
        """Every stage has a question defined."""
        for stage in FlowStage:
            assert stage in STAGE_QUESTIONS
            assert len(STAGE_QUESTIONS[stage]) > 0


# ================================================================================
# TEST: INCOME FROM DATABASE (NO FILE UPLOAD)
# ================================================================================

class TestIncomeFromDatabase:
    """
    Test that income verification uses ONLY customer database.
    NO file upload. NO salary slip. NO OCR.
    """
    
    def test_income_source_is_always_database(self, controller, session_id):
        """Income source must be database, never upload."""
        session = controller.get_or_create_session(session_id)
        assert session.income_source == "CUSTOMER_DATABASE"
    
    def test_income_fetched_from_customer_profile(self, controller, session_id):
        """Income data comes from CUSTOMER_PROFILES."""
        # Use a known customer mobile number
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9127384590")  # Rahul Mehta in mock_data
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "AQMPR1234L")
        # At OFFER_DISCUSSION, acknowledge to trigger offer calculation
        session, _, _ = controller.process_input(session_id, "yes proceed")
        
        # After acknowledging offer, income should be fetched
        assert session.monthly_income == 60000  # From mock_data
        assert session.annual_income == 720000
    
    def test_no_file_upload_fields_in_session(self, controller, session_id):
        """Session state has no file upload related fields."""
        session = controller.get_or_create_session(session_id)
        session_dict = session.to_dict()
        
        # These fields should NOT exist
        assert "salary_slip" not in session_dict
        assert "uploaded_file" not in session_dict
        assert "document_upload" not in session_dict
        assert "ocr_result" not in session_dict
    
    def test_income_source_in_response(self, controller, session_id):
        """Response includes income_source = CUSTOMER_DATABASE."""
        session = controller.get_or_create_session(session_id)
        session_dict = session.to_dict()
        assert session_dict["income_source"] == "CUSTOMER_DATABASE"


# ================================================================================
# TEST: FOIR-BASED UNDERWRITING
# ================================================================================

class TestFOIRUnderwriting:
    """Test FOIR (Fixed Obligation to Income Ratio) based underwriting."""
    
    def test_underwriting_uses_database_credit_score(self, controller, session_id):
        """Credit score comes from database, not user input."""
        # Full journey with known test user
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "5 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")  # Test user
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        controller.process_input(session_id, "yes")
        controller.process_input(session_id, "3 years")
        session, _, _ = controller.process_input(session_id, "")
        
        # Credit score should be set from test user data
        assert session.credit_score == 780
    
    def test_credit_score_never_exposed_to_user(self, controller, session_id):
        """Credit score must never be in API response."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        
        response_dict = session.to_dict()
        assert "credit_score" not in response_dict


# ================================================================================
# TEST: INTEREST RATE AS RANGE (NOT FIXED)
# ================================================================================

class TestInterestRateRange:
    """Test interest rate is shown as RANGE, not fixed single value."""
    
    def test_interest_rate_range_exists(self, controller):
        """Controller must have INTEREST_RATE_RANGE constant."""
        from deterministic_flow import INTEREST_RATE_RANGE
        assert "min" in INTEREST_RATE_RANGE
        assert "max" in INTEREST_RATE_RANGE
        assert INTEREST_RATE_RANGE["min"] < INTEREST_RATE_RANGE["max"]
    
    def test_session_has_interest_rate_min_max(self, controller, session_id):
        """Session state must have interest_rate_min and interest_rate_max in to_dict."""
        # Complete journey to OFFER stage and trigger offer calculation
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        # Now at OFFER - send any message to trigger _calculate_offer
        session, _, _ = controller.process_input(session_id, "ok")
        session_dict = session.to_dict()
        
        assert "interest_rate_min" in session_dict
        assert "interest_rate_max" in session_dict
        assert session_dict["interest_rate_min"] is not None
        assert session_dict["interest_rate_max"] is not None
    
    def test_interest_rate_is_range_in_offer(self, controller, session_id):
        """At OFFER stage, interest must be RANGE not fixed value."""
        # Go through journey to OFFER stage
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        # Now at OFFER_DISCUSSION - send message to trigger offer
        session, _, _ = controller.process_input(session_id, "ok")
        
        assert session.interest_rate_min > 0
        assert session.interest_rate_max > session.interest_rate_min
        # final_interest_rate should NOT be set yet (until tenure selection)
        assert session.final_interest_rate is None


# ================================================================================
# TEST: TENURE OPTIONS (12/24/36/48 MONTHS)
# ================================================================================

class TestTenureOptions:
    """Test tenure must be one of 12, 24, 36, 48 months."""
    
    def test_tenure_options_constant_exists(self, controller):
        """TENURE_OPTIONS constant must exist."""
        from deterministic_flow import TENURE_OPTIONS
        assert TENURE_OPTIONS == [12, 24, 36, 48]
    
    def test_valid_tenure_12_months(self, controller, session_id):
        """12 months is valid tenure."""
        # Full journey to tenure stage
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "12 months")
        assert session.selected_tenure == 12
    
    def test_valid_tenure_24_months(self, controller, session_id):
        """24 months is valid tenure."""
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "24 months")
        assert session.selected_tenure == 24
    
    def test_valid_tenure_36_months(self, controller, session_id):
        """36 months (3 years) is valid tenure."""
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "3 years")
        assert session.selected_tenure == 36
    
    def test_valid_tenure_48_months(self, controller, session_id):
        """48 months (4 years) is valid tenure."""
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "4 years")
        assert session.selected_tenure == 48
    
    def test_invalid_tenure_60_months_rejected(self, controller, session_id):
        """60 months (5 years) is NOT valid."""
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "60 months")
        # Should still be at tenure selection stage
        assert session.current_stage == FlowStage.TENURE_SELECTION
        assert session.selected_tenure is None
    
    def test_invalid_tenure_18_months_rejected(self, controller, session_id):
        """18 months is NOT a valid option."""
        self._journey_to_tenure_stage(controller, session_id)
        session, _, _ = controller.process_input(session_id, "18 months")
        # Should still be at tenure selection
        assert session.current_stage == FlowStage.TENURE_SELECTION
    
    def _journey_to_tenure_stage(self, controller, session_id):
        """Helper to reach TENURE_SELECTION stage."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        controller.process_input(session_id, "yes")  # Acknowledge offer


# ================================================================================
# TEST: EMI CALCULATED ONLY AFTER TENURE SELECTION
# ================================================================================

class TestEMIAfterTenure:
    """Test EMI is calculated ONLY after user selects tenure."""
    
    def test_emi_not_calculated_at_offer_stage(self, controller, session_id):
        """At OFFER stage, calculated_emi should be None."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        # Now at OFFER_DISCUSSION
        session = controller.get_or_create_session(session_id)
        
        # EMI should NOT be calculated yet
        assert session.calculated_emi is None
    
    def test_emi_calculated_after_tenure_selection(self, controller, session_id):
        """After selecting tenure, EMI is calculated."""
        # Journey to offer
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        controller.process_input(session_id, "yes")  # Acknowledge offer
        
        # Now select tenure
        session, _, _ = controller.process_input(session_id, "36 months")
        
        # EMI should now be calculated
        assert session.calculated_emi is not None
        assert session.calculated_emi > 0
    
    def test_emi_options_available_for_comparison(self, controller, session_id):
        """EMI options for all tenures should be available after offer."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        # At OFFER - send message to trigger offer calculation
        session, _, _ = controller.process_input(session_id, "tell me more")
        session_dict = session.to_dict()
        
        # emi_options should be present with 4 tenure options
        assert "emi_options" in session_dict
        emi_options = session_dict["emi_options"]
        assert emi_options is not None
        assert 12 in emi_options or "12" in str(emi_options)
    
    def test_final_interest_rate_set_after_tenure(self, controller, session_id):
        """Final interest rate is set only after tenure selection."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        
        # At offer - final rate not set
        session = controller.get_or_create_session(session_id)
        assert session.final_interest_rate is None
        
        controller.process_input(session_id, "yes")
        session, _, _ = controller.process_input(session_id, "24 months")
        
        # After tenure - final rate is set
        assert session.final_interest_rate is not None
        assert session.final_interest_rate >= 10.5
        assert session.final_interest_rate <= 18.0


# ================================================================================
# TEST: CREDIT SCORE DETERMINES INTEREST RATE
# ================================================================================

class TestCreditScoreInterestRate:
    """Test credit score determines final interest rate."""
    
    def test_high_credit_score_gets_low_rate(self, controller, session_id):
        """Credit score >= 800 gets minimum rate."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 800
        
        rate = controller._get_interest_rate_for_credit_score(800)
        assert rate == 10.5  # Minimum rate
    
    def test_low_credit_score_gets_high_rate(self, controller, session_id):
        """Credit score < 650 gets maximum rate."""
        rate = controller._get_interest_rate_for_credit_score(600)
        assert rate == 18.0  # Maximum rate
    
    def test_medium_credit_score_gets_default_rate(self, controller, session_id):
        """Credit score 700-749 gets default rate."""
        rate = controller._get_interest_rate_for_credit_score(700)
        assert rate == 12.0  # Default rate


# ================================================================================
# TEST: STRICT UNDERWRITING RULES (PART 4)
# ================================================================================

class TestStrictUnderwritingRules:
    """
    Test strict underwriting rules:
    1. Credit score < 700 → REJECT
    2. Credit score ≥ 700 → continue
    3. Requested amount ≤ pre-approved → auto approve
    4. Requested amount > pre-approved → reject
    """
    
    def test_credit_score_below_700_rejected(self, controller, session_id):
        """Credit score < 700 → auto REJECT."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 699
        session.loan_amount = 300000
        session.pre_approved_limit = 500000
        
        decision, reason = controller._perform_underwriting(session)
        assert decision == "REJECTED"
        assert reason == "CREDIT_CRITERIA_NOT_MET"
    
    def test_credit_score_exactly_700_continues(self, controller, session_id):
        """Credit score = 700 → continues to amount check."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 700
        session.loan_amount = 300000
        session.pre_approved_limit = 500000
        
        decision, reason = controller._perform_underwriting(session)
        # Should pass credit check and amount check
        assert decision == "APPROVED"
        assert reason is None
    
    def test_credit_score_above_700_continues(self, controller, session_id):
        """Credit score > 700 → continues to amount check."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        session.loan_amount = 300000
        session.pre_approved_limit = 500000
        
        decision, reason = controller._perform_underwriting(session)
        assert decision == "APPROVED"
    
    def test_amount_within_limit_approved(self, controller, session_id):
        """Requested amount ≤ pre-approved → APPROVED."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        session.loan_amount = 300000  # Requesting 3L
        session.pre_approved_limit = 500000  # Approved for 5L
        
        decision, reason = controller._perform_underwriting(session)
        assert decision == "APPROVED"
        assert reason is None
    
    def test_amount_exactly_at_limit_approved(self, controller, session_id):
        """Requested amount = pre-approved → APPROVED."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        session.loan_amount = 500000  # Requesting exactly 5L
        session.pre_approved_limit = 500000  # Approved for 5L
        
        decision, reason = controller._perform_underwriting(session)
        assert decision == "APPROVED"
        assert reason is None
    
    def test_amount_exceeds_limit_rejected(self, controller, session_id):
        """Requested amount > pre-approved → REJECTED."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        session.loan_amount = 600000  # Requesting 6L
        session.pre_approved_limit = 500000  # Only approved for 5L
        
        decision, reason = controller._perform_underwriting(session)
        assert decision == "REJECTED"
        assert reason == "AMOUNT_EXCEEDS_ELIGIBILITY"
    
    def test_test_user_priya_rejected_for_low_credit(self, controller, session_id):
        """Test user Priya (credit 580) is rejected."""
        # Full journey for rejected user
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Mumbai")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Priya Sharma")
        controller.process_input(session_id, "9123456781")  # Priya - credit 580
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "MNOPQ9012R")
        controller.process_input(session_id, "yes")
        controller.process_input(session_id, "36 months")
        session, _, _ = controller.process_input(session_id, "")
        
        assert session.current_stage == FlowStage.REJECTION
        assert session.underwriting_result == "REJECTED"
        assert session.rejection_reason == "CREDIT_CRITERIA_NOT_MET"
    
    def test_test_user_amit_approved_at_720(self, controller, session_id):
        """Test user Amit (credit 720) is approved if amount within limit."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "home")
        controller.process_input(session_id, "3 lakhs")  # Small amount
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Amit Verma")
        controller.process_input(session_id, "9988776655")  # Amit - credit 720
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "GHIJK5678M")
        controller.process_input(session_id, "yes")
        controller.process_input(session_id, "24 months")
        session, _, _ = controller.process_input(session_id, "")
        
        assert session.credit_score == 720
        assert session.underwriting_result == "APPROVED"


# ================================================================================
# TEST: CREDIT SCORE NEVER EXPOSED TO LLM
# ================================================================================

class TestCreditScoreNeverExposed:
    """Test that credit score is NEVER exposed to LLM or user."""
    
    def test_credit_score_not_in_session_dict(self, controller, session_id):
        """Credit score must NOT be in to_dict() output."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        
        session_dict = session.to_dict()
        assert "credit_score" not in session_dict
    
    def test_rejection_reason_not_mention_credit_score(self, controller, session_id):
        """Rejection reason code must not mention specific credit score."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 600  # Set low credit score
        session.loan_amount = 300000
        session.pre_approved_limit = 500000
        
        decision, reason = controller._perform_underwriting(session)
        
        # Should be rejected for low credit score
        assert decision == "REJECTED"
        # Reason should be generic code, not specific number
        assert "600" not in str(reason)
        assert reason == "CREDIT_CRITERIA_NOT_MET"  # Generic code
    
    def test_stage_questions_for_rejection_no_credit_mention(self, controller):
        """REJECTION stage instruction must not mention credit score."""
        from deterministic_flow import STAGE_QUESTIONS
        
        rejection_instruction = STAGE_QUESTIONS[FlowStage.REJECTION]
        assert "credit score" not in rejection_instruction.lower() or "never mention credit score" in rejection_instruction.lower()


# ================================================================================
# TEST: DATA INTEGRITY - ONE CUSTOMER PER SESSION (PART 5)
# ================================================================================

class TestIdentityLocking:
    """Test identity is locked after OTP verification."""
    
    def test_identity_locked_after_otp(self, controller, session_id):
        """Identity must be locked after OTP verification."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        session, _, _ = controller.process_input(session_id, "123456")  # OTP
        
        assert session.identity_locked is True
        assert session.identity_locked_at is not None
    
    def test_application_id_generated_after_otp(self, controller, session_id):
        """Application ID must be generated after OTP verification."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test User")
        controller.process_input(session_id, "9876543210")
        session, _, _ = controller.process_input(session_id, "123456")
        
        assert session.application_id is not None
        assert session.application_id.startswith("APP-")
    
    def test_expected_pan_set_for_known_user(self, controller, session_id):
        """Expected PAN should be set for known test users."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")  # Rahul's mobile
        session, _, _ = controller.process_input(session_id, "123456")
        
        assert session.expected_pan == "ABCDE1234F"  # Rahul's PAN


# ================================================================================
# TEST: PAN MUST MATCH CUSTOMER (PART 5)
# ================================================================================

class TestPANIdentityMatch:
    """Test PAN must belong to same customer - no cross-user documents."""
    
    def test_correct_pan_passes(self, controller, session_id):
        """Correct PAN for customer passes verification."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        session, _, _ = controller.process_input(session_id, "ABCDE1234F")  # Rahul's PAN
        
        assert session.pan_verified is True
        assert session.identity_mismatch is False
    
    def test_wrong_pan_halts_journey(self, controller, session_id):
        """Wrong PAN for customer halts journey."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")  # Rahul's mobile
        controller.process_input(session_id, "123456")
        session, _, _ = controller.process_input(session_id, "MNOPQ9012R")  # Priya's PAN - WRONG!
        
        assert session.identity_mismatch is True
        # Could be PAN_IDENTITY_MISMATCH (wrong PAN for user) or CROSS_USER_DOCUMENT (PAN belongs to another user)
        assert session.identity_mismatch_reason in ["PAN_IDENTITY_MISMATCH", "CROSS_USER_DOCUMENT"]
        assert session.is_frozen is True
    
    def test_cross_user_pan_rejected(self, controller, session_id):
        """Using another customer's PAN is rejected."""
        # Amit's journey with Rahul's PAN
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Amit")
        controller.process_input(session_id, "9988776655")  # Amit's mobile
        controller.process_input(session_id, "123456")
        session, _, _ = controller.process_input(session_id, "ABCDE1234F")  # Rahul's PAN - CROSS USER!
        
        assert session.identity_mismatch is True
        assert session.is_frozen is True
    
    def test_halted_session_cannot_continue(self, controller, session_id):
        """Once halted for mismatch, session cannot continue."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "MNOPQ9012R")  # Wrong PAN
        
        # Try to continue - should be blocked
        session, instruction, changed = controller.process_input(session_id, "I want to proceed")
        
        assert "halted" in instruction.lower()
        assert changed is False


# ================================================================================
# TEST: APPLICATION ID FOR ADMIN DASHBOARD (PART 5)
# ================================================================================

class TestApplicationIdForAdmin:
    """Test application_id is available for admin dashboard."""
    
    def test_application_id_in_to_dict(self, controller, session_id):
        """Application ID should be in to_dict() for admin dashboard."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session = controller.get_or_create_session(session_id)
        session_dict = session.to_dict()
        
        assert "application_id" in session_dict
        assert session_dict["application_id"] is not None
    
    def test_identity_locked_in_to_dict(self, controller, session_id):
        """Identity locked status should be in to_dict()."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session = controller.get_or_create_session(session_id)
        session_dict = session.to_dict()
        
        assert "identity_locked" in session_dict
        assert session_dict["identity_locked"] is True
    
    def test_expected_pan_not_exposed(self, controller, session_id):
        """Expected PAN should NOT be in to_dict() (security)."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session = controller.get_or_create_session(session_id)
        session_dict = session.to_dict()
        
        assert "expected_pan" not in session_dict


# ================================================================================
# TEST: ADMIN DASHBOARD (PART 6)
# ================================================================================

class TestAdminDashboard:
    """
    Test admin dashboard view.
    
    REQUIREMENTS:
    - READ-ONLY: No actions, no modifications
    - BACKEND STATE ONLY: Shows deterministic state machine truth
    - NEVER DISCONNECT: Stable data, no websocket-dependent fields
    - NEVER INFER: Only actual values, no computed/guessed fields
    
    Shows:
    - Application ID
    - Current stage
    - KYC status
    - Offer eligibility
    - Decision reason
    """
    
    def test_to_admin_dict_exists(self, controller, session_id):
        """Session must have to_admin_dict() method."""
        session = controller.get_or_create_session(session_id)
        assert hasattr(session, 'to_admin_dict')
    
    def test_admin_dict_has_application_id(self, controller, session_id):
        """Admin view must have application_id."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "application_id" in admin_dict
        assert admin_dict["application_id"] is not None
    
    def test_admin_dict_has_stage_info(self, controller, session_id):
        """Admin view must have stage progression info."""
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "stage" in admin_dict
        assert "current_stage" in admin_dict["stage"]
        assert "stage_number" in admin_dict["stage"]
        assert "total_stages" in admin_dict["stage"]
        assert "progress_percent" in admin_dict["stage"]
        assert "is_terminal" in admin_dict["stage"]
    
    def test_admin_dict_has_kyc_status(self, controller, session_id):
        """Admin view must have KYC status."""
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "kyc" in admin_dict
        assert "otp_verified" in admin_dict["kyc"]
        assert "pan_verified" in admin_dict["kyc"]
        assert "identity_locked" in admin_dict["kyc"]
        assert "identity_mismatch" in admin_dict["kyc"]
    
    def test_admin_dict_has_offer_eligibility(self, controller, session_id):
        """Admin view must have offer eligibility."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Test")
        controller.process_input(session_id, "9876543210")
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "ABCDE1234F")
        controller.process_input(session_id, "ok")  # Trigger offer calculation
        
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "offer" in admin_dict
        assert "pre_approved_limit" in admin_dict["offer"]
        assert "requested_amount" in admin_dict["offer"]
        assert "interest_rate_range" in admin_dict["offer"]
    
    def test_admin_dict_has_decision_info(self, controller, session_id):
        """Admin view must have decision info."""
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "decision" in admin_dict
        assert "underwriting_complete" in admin_dict["decision"]
        assert "underwriting_result" in admin_dict["decision"]
        assert "rejection_reason" in admin_dict["decision"]
        assert "is_frozen" in admin_dict["decision"]
    
    def test_admin_dict_has_customer_info_masked(self, controller, session_id):
        """Admin view must have customer info with mobile masked."""
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Rahul")
        controller.process_input(session_id, "9876543210")
        
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "customer" in admin_dict
        assert admin_dict["customer"]["name"] == "Rahul"
        assert admin_dict["customer"]["mobile_masked"] == "XXXXXX3210"  # Last 4 only
    
    def test_admin_dict_has_timestamps(self, controller, session_id):
        """Admin view must have timestamps."""
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert "timestamps" in admin_dict
        assert "created_at" in admin_dict["timestamps"]
        assert "last_updated" in admin_dict["timestamps"]
    
    def test_admin_dict_no_credit_score(self, controller, session_id):
        """Admin view must NOT expose credit score."""
        session = controller.get_or_create_session(session_id)
        session.credit_score = 750
        admin_dict = session.to_admin_dict()
        
        # Credit score should not be in admin dict
        assert "credit_score" not in admin_dict
        # Also check nested dicts
        for key, value in admin_dict.items():
            if isinstance(value, dict):
                assert "credit_score" not in value
    
    def test_admin_dict_shows_rejection_reason_code(self, controller, session_id):
        """Admin view shows rejection reason code (internal)."""
        # Journey with rejected user
        controller.process_input(session_id, "Hi")
        controller.process_input(session_id, "personal")
        controller.process_input(session_id, "3 lakhs")
        controller.process_input(session_id, "Delhi")
        controller.process_input(session_id, "salaried")
        controller.process_input(session_id, "Priya")
        controller.process_input(session_id, "9123456781")  # Priya - low credit
        controller.process_input(session_id, "123456")
        controller.process_input(session_id, "MNOPQ9012R")
        controller.process_input(session_id, "ok")
        controller.process_input(session_id, "36 months")
        controller.process_input(session_id, "")  # Trigger underwriting
        
        session = controller.get_or_create_session(session_id)
        admin_dict = session.to_admin_dict()
        
        assert admin_dict["decision"]["underwriting_result"] == "REJECTED"
        assert admin_dict["decision"]["rejection_reason"] == "CREDIT_CRITERIA_NOT_MET"


class TestAdminConvenienceFunctions:
    """Test admin convenience functions."""
    
    def test_get_admin_state_returns_dict(self, controller, session_id):
        """get_admin_state() returns admin dict."""
        from deterministic_flow import get_admin_state
        
        # Create a session first
        controller.process_input(session_id, "Hi")
        
        admin_state = get_admin_state(session_id)
        assert admin_state is not None
        assert "application_id" in admin_state or admin_state["application_id"] is None
        assert "stage" in admin_state
    
    def test_get_admin_state_returns_none_for_invalid_session(self, controller):
        """get_admin_state() returns None for non-existent session."""
        from deterministic_flow import get_admin_state
        
        admin_state = get_admin_state("non-existent-session-xyz")
        assert admin_state is None
    
    def test_get_all_admin_sessions_returns_list(self, controller, session_id):
        """get_all_admin_sessions() returns list of admin dicts."""
        from deterministic_flow import get_all_admin_sessions
        
        # Create some sessions
        controller.process_input(session_id, "Hi")
        controller.process_input("session-2", "Hello")
        
        all_sessions = get_all_admin_sessions()
        assert isinstance(all_sessions, list)
        assert len(all_sessions) >= 2


# ================================================================================
# RUN TESTS
# ================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
