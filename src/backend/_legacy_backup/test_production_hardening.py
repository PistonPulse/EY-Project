#!/usr/bin/env python3
"""
================================================================================
PRODUCTION HARDENING - COMPREHENSIVE TEST SUITE
================================================================================

Tests for bank-grade reliability features:
- Session freeze after terminal stages
- Demo mode configuration
- Audit logging
- Timeout handling
- Purpose explanations
- Input normalization
- Response consistency

================================================================================
"""

import pytest
from datetime import datetime, timedelta
from production_hardening import (
    # Session freeze
    JourneyStatus,
    FreezeReason,
    JourneyState,
    SessionFreezeController,
    get_freeze_controller,
    TERMINAL_STAGES,
    
    # Demo mode
    DemoConfig,
    get_demo_config,
    enable_demo_mode,
    disable_demo_mode,
    
    # Audit logging
    AuditEventType,
    AuditEntry,
    AuditLogger,
    get_audit_logger,
    audit_log,
    
    # Timeout handling
    TimeoutConfig,
    SessionRecoveryState,
    TimeoutManager,
    get_timeout_manager,
    
    # Purpose explanations
    PURPOSE_EXPLANATIONS,
    get_purpose_explanation,
    
    # Input normalization
    InputNormalizationGuard,
    get_normalizer,
    
    # Response wrappers
    HardenedResponse,
    create_hardened_response,
    
    # Integration helpers
    check_and_audit_operation,
    
    # Convenience functions
    on_session_start,
    on_otp_sent,
    on_otp_verified,
    on_otp_failed,
    on_credit_score_fetched,
    on_income_verified,
    on_underwriting_complete,
    on_journey_complete,
)


# ================================================================================
# PART 1: SESSION FREEZE TESTS
# ================================================================================

class TestSessionFreezeController:
    """Tests for session freeze functionality."""
    
    def test_terminal_stages_defined(self):
        """Terminal stages should include SANCTION and REJECTION."""
        assert "SANCTION" in TERMINAL_STAGES
        assert "REJECTION" in TERMINAL_STAGES
        
    def test_active_session_allowed(self):
        """Active sessions should allow operations."""
        controller = SessionFreezeController()
        is_allowed, message = controller.check_session_status("test_session_1", "KYC_COLLECTION")
        assert is_allowed is True
        assert message == ""
        
    def test_sanction_stage_freezes_session(self):
        """SANCTION stage should freeze the session."""
        controller = SessionFreezeController()
        is_allowed, message = controller.check_session_status("freeze_test_1", "SANCTION")
        assert is_allowed is False
        assert "complete" in message.lower() or "approved" in message.lower()
        
    def test_rejection_stage_freezes_session(self):
        """REJECTION stage should freeze the session."""
        controller = SessionFreezeController()
        is_allowed, message = controller.check_session_status("freeze_test_2", "REJECTION")
        assert is_allowed is False
        assert controller.is_frozen("freeze_test_2")
        
    def test_frozen_session_blocks_all_operations(self):
        """Once frozen, session should block all subsequent operations."""
        controller = SessionFreezeController()
        
        # Freeze the session
        controller.check_session_status("freeze_test_3", "SANCTION")
        
        # Try to access it again
        is_allowed, message = controller.check_session_status("freeze_test_3", "GREETING")
        assert is_allowed is False
        
    def test_force_freeze(self):
        """Admin should be able to force freeze a session."""
        controller = SessionFreezeController()
        controller.force_freeze("admin_freeze_1", FreezeReason.FRAUD_DETECTED, "KYC_COLLECTION")
        
        assert controller.is_frozen("admin_freeze_1")
        state = controller.get_frozen_state("admin_freeze_1")
        assert state.freeze_reason == FreezeReason.FRAUD_DETECTED
        
    def test_freeze_message_for_sanctioned(self):
        """Sanctioned sessions should have appropriate message."""
        controller = SessionFreezeController()
        is_allowed, message = controller.check_session_status("msg_test_1", "SANCTION")
        assert "sanction" in message.lower() or "complete" in message.lower()
        
    def test_freeze_message_for_rejected(self):
        """Rejected sessions should have appropriate message."""
        controller = SessionFreezeController()
        is_allowed, message = controller.check_session_status("msg_test_2", "REJECTION")
        assert "could not approve" in message.lower() or "processed" in message.lower()


class TestJourneyState:
    """Tests for JourneyState dataclass."""
    
    def test_journey_state_creation(self):
        """JourneyState should be creatable."""
        state = JourneyState(
            session_id="test_session",
            status=JourneyStatus.FROZEN,
            freeze_reason=FreezeReason.LOAN_SANCTIONED,
            final_stage="SANCTION"
        )
        assert state.session_id == "test_session"
        assert state.status == JourneyStatus.FROZEN
        

# ================================================================================
# PART 2: DEMO MODE TESTS
# ================================================================================

class TestDemoConfig:
    """Tests for demo mode configuration."""
    
    def test_default_demo_users(self):
        """Demo config should have default approved and rejected users."""
        config = DemoConfig()
        assert len(config.approved_users) > 0
        assert len(config.rejected_users) > 0
        
    def test_is_demo_user_approved(self):
        """Should identify approved demo users."""
        config = DemoConfig()
        assert config.is_demo_user("9876543210") is True
        
    def test_is_demo_user_rejected(self):
        """Should identify rejected demo users."""
        config = DemoConfig()
        assert config.is_demo_user("9123456781") is True
        
    def test_is_not_demo_user(self):
        """Should return False for non-demo users."""
        config = DemoConfig()
        assert config.is_demo_user("9999999999") is False
        
    def test_get_demo_outcome_approved(self):
        """Should return correct outcome for approved user."""
        config = DemoConfig()
        outcome = config.get_demo_outcome("9876543210")
        assert outcome is not None
        assert outcome["outcome"] == "APPROVED"
        
    def test_get_demo_outcome_rejected(self):
        """Should return correct outcome for rejected user."""
        config = DemoConfig()
        outcome = config.get_demo_outcome("9123456781")
        assert outcome is not None
        assert outcome["outcome"] == "REJECTED"
        
    def test_fixed_otp(self):
        """Demo mode should have fixed OTP."""
        config = DemoConfig()
        assert config.get_demo_otp() == "123456"
        
    def test_session_tracking(self):
        """Should track used sessions."""
        config = DemoConfig()
        config.mark_session_used("session_1")
        assert config.is_session_used("session_1") is True
        assert config.is_session_used("session_2") is False


# ================================================================================
# PART 3: AUDIT LOGGING TESTS
# ================================================================================

class TestAuditLogger:
    """Tests for audit logging functionality."""
    
    def test_log_creates_entry(self):
        """Logging should create an audit entry."""
        logger = AuditLogger()
        entry = logger.log(
            session_id="audit_test_1",
            event_type=AuditEventType.OTP_SENT,
            result="SUCCESS",
            details={"mobile": "3210"},
            stage="KYC_COLLECTION"
        )
        assert entry is not None
        assert entry.event_type == AuditEventType.OTP_SENT
        
    def test_log_is_append_only(self):
        """Logs should be append-only."""
        logger = AuditLogger()
        logger.log("audit_test_2", AuditEventType.SESSION_STARTED, "SUCCESS", {}, "GREETING")
        logger.log("audit_test_2", AuditEventType.OTP_SENT, "SUCCESS", {}, "KYC_COLLECTION")
        
        entries = logger.get_session_log("audit_test_2")
        assert len(entries) == 2
        
    def test_session_isolation(self):
        """Each session should have its own log."""
        logger = AuditLogger()
        logger.log("session_a", AuditEventType.SESSION_STARTED, "SUCCESS", {}, "GREETING")
        logger.log("session_b", AuditEventType.SESSION_STARTED, "SUCCESS", {}, "GREETING")
        
        assert len(logger.get_session_log("session_a")) == 1
        assert len(logger.get_session_log("session_b")) == 1
        
    def test_timeline_display(self):
        """Should generate timeline for admin dashboard."""
        logger = AuditLogger()
        logger.log("timeline_test", AuditEventType.OTP_VERIFIED, "SUCCESS", {}, "KYC_VERIFICATION")
        logger.log("timeline_test", AuditEventType.CREDIT_SCORE_FETCHED, "SUCCESS", {"score": 780}, "CREDIT_CHECK")
        
        timeline = logger.get_session_timeline("timeline_test")
        assert len(timeline) == 2
        assert "OTP_VERIFIED" in timeline[0]
        
    def test_decision_summary(self):
        """Should generate decision summary."""
        logger = AuditLogger()
        logger.log("summary_test", AuditEventType.OTP_VERIFIED, "SUCCESS", {}, "KYC_VERIFICATION")
        logger.log("summary_test", AuditEventType.CREDIT_SCORE_FETCHED, "SUCCESS", {"score": 780}, "OFFER_DISCOVERY")
        logger.log("summary_test", AuditEventType.UNDERWRITING_APPROVED, "SUCCESS", {"amount": 500000}, "UNDERWRITING")
        
        summary = logger.get_decision_summary("summary_test")
        assert summary["final_outcome"] == "APPROVED"
        assert summary["verification_results"]["credit_score"] == 780
        
    def test_audit_entry_to_dict(self):
        """Audit entry should be JSON serializable."""
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            event_type=AuditEventType.OTP_SENT,
            session_id="dict_test",
            result="SUCCESS",
            details={"mobile": "3210"},
            stage_at_event="KYC_COLLECTION"
        )
        
        as_dict = entry.to_dict()
        assert "timestamp" in as_dict
        assert as_dict["event_type"] == "OTP_SENT"


# ================================================================================
# PART 4: TIMEOUT HANDLING TESTS
# ================================================================================

class TestTimeoutManager:
    """Tests for timeout management."""
    
    def test_otp_not_expired_immediately(self):
        """OTP should not be expired immediately after sending."""
        manager = TimeoutManager()
        manager.record_otp_sent("otp_test_1")
        
        is_expired, message = manager.is_otp_expired("otp_test_1")
        assert is_expired is False
        
    def test_otp_expired_without_sending(self):
        """OTP should be marked expired if never sent."""
        manager = TimeoutManager()
        is_expired, message = manager.is_otp_expired("no_otp_session")
        assert is_expired is True
        assert "No OTP" in message
        
    def test_activity_recording(self):
        """Activity should be recorded."""
        manager = TimeoutManager()
        manager.record_activity("activity_test")
        
        is_timeout, elapsed = manager.is_session_idle_timeout("activity_test")
        assert is_timeout is False
        assert elapsed < 5
        
    def test_session_pause_and_recovery(self):
        """Session should be pausable and recoverable."""
        manager = TimeoutManager()
        manager.pause_session(
            session_id="pause_test",
            stage="INCOME_DOC_UPLOAD",
            step="UPLOAD_DOCUMENT",
            collected_data={"name": "Test User"}
        )
        
        recovery = manager.get_recovery_state("pause_test")
        assert recovery is not None
        assert recovery.was_paused is True
        assert recovery.paused_stage == "INCOME_DOC_UPLOAD"
        
    def test_recovery_message_generated(self):
        """Resume message should be generated based on stage."""
        manager = TimeoutManager()
        manager.pause_session("msg_test", "OTP_VERIFICATION", "ENTER_OTP", {})
        
        recovery = manager.get_recovery_state("msg_test")
        assert "OTP" in recovery.resume_message
        
    def test_clear_recovery_state(self):
        """Recovery state should be clearable after resume."""
        manager = TimeoutManager()
        manager.pause_session("clear_test", "GREETING", "WELCOME", {})
        manager.clear_recovery_state("clear_test")
        
        assert manager.get_recovery_state("clear_test") is None


# ================================================================================
# PART 5: PURPOSE EXPLANATION TESTS
# ================================================================================

class TestPurposeExplanations:
    """Tests for purpose explanations."""
    
    def test_all_key_fields_have_explanations(self):
        """Key data fields should have explanations."""
        key_fields = ["name", "mobile", "otp", "pan", "aadhaar", "loan_amount", "salary_slip"]
        for field in key_fields:
            explanation = get_purpose_explanation(field)
            assert len(explanation) > 20  # Meaningful explanation
            
    def test_unknown_field_has_default(self):
        """Unknown fields should have default explanation."""
        explanation = get_purpose_explanation("unknown_field_xyz")
        assert "helps us process" in explanation.lower()
        
    def test_explanations_are_user_friendly(self):
        """Explanations should be user-friendly, not technical."""
        # Should NOT contain technical terms
        pan_explanation = get_purpose_explanation("pan")
        assert "API" not in pan_explanation
        assert "database" not in pan_explanation.lower()
        
        # Should contain user-friendly terms
        assert "verify" in pan_explanation.lower() or "identity" in pan_explanation.lower()


# ================================================================================
# PART 6: INPUT NORMALIZATION TESTS
# ================================================================================

class TestInputNormalization:
    """Tests for input normalization guardrails."""
    
    def test_aadhaar_with_spaces(self):
        """Aadhaar with spaces should normalize."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_aadhaar("1234 5678 9012")
        assert is_valid is True
        assert normalized == "123456789012"
        
    def test_aadhaar_with_dashes(self):
        """Aadhaar with dashes should normalize."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_aadhaar("1234-5678-9012")
        assert is_valid is True
        assert normalized == "123456789012"
        
    def test_invalid_aadhaar_rejected(self):
        """Invalid Aadhaar should be rejected."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_aadhaar("12345")
        assert is_valid is False
        
    def test_pan_uppercase(self):
        """PAN should be uppercased."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_pan("abcde1234f")
        assert is_valid is True
        assert normalized == "ABCDE1234F"
        
    def test_invalid_pan_rejected(self):
        """Invalid PAN format should be rejected."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_pan("ABC12345")
        assert is_valid is False
        
    def test_mobile_country_code_stripped(self):
        """Mobile should strip +91 prefix."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_mobile("+919876543210")
        assert is_valid is True
        assert normalized == "9876543210"
        
    def test_mobile_with_spaces(self):
        """Mobile with spaces should normalize."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_mobile("98765 43210")
        assert is_valid is True
        assert normalized == "9876543210"
        
    def test_invalid_mobile_rejected(self):
        """Invalid mobile should be rejected."""
        normalized, is_valid, msg = InputNormalizationGuard.normalize_mobile("12345")
        assert is_valid is False
        
    def test_amount_lakhs(self):
        """Amount in lakhs should normalize."""
        amount, is_valid, msg = InputNormalizationGuard.normalize_amount("5 lakh")
        assert is_valid is True
        assert amount == 500000
        
    def test_amount_l_notation(self):
        """Amount with L notation should normalize."""
        amount, is_valid, msg = InputNormalizationGuard.normalize_amount("5L")
        assert is_valid is True
        assert amount == 500000
        
    def test_amount_word_numbers(self):
        """Amount with word numbers should normalize."""
        amount, is_valid, msg = InputNormalizationGuard.normalize_amount("ten lakh")
        assert is_valid is True
        assert amount == 1000000
        
    def test_amount_with_commas(self):
        """Amount with commas should normalize."""
        amount, is_valid, msg = InputNormalizationGuard.normalize_amount("5,00,000")
        assert is_valid is True
        assert amount == 500000


# ================================================================================
# PART 7: HARDENED RESPONSE TESTS
# ================================================================================

class TestHardenedResponse:
    """Tests for hardened response wrapper."""
    
    def test_active_session_response(self):
        """Active session should have chat input enabled."""
        response = create_hardened_response(
            message="Please enter your name",
            session_id="response_test_1",
            current_stage="KYC_COLLECTION"
        )
        assert response.session_status == "ACTIVE"
        assert response.show_chat_input is True
        assert response.is_frozen is False
        
    def test_frozen_session_response(self):
        """Frozen session should have chat input disabled."""
        response = create_hardened_response(
            message="Your loan is approved!",
            session_id="response_test_2",
            current_stage="SANCTION"
        )
        assert response.session_status == "FROZEN"
        assert response.show_chat_input is False
        assert response.is_frozen is True
        
    def test_upload_button_only_at_upload_stage(self):
        """Upload button should only show at INCOME_DOC_UPLOAD."""
        # At upload stage
        response = create_hardened_response(
            message="Please upload documents",
            session_id="upload_test_1",
            current_stage="INCOME_DOC_UPLOAD"
        )
        assert response.show_upload_button is True
        
        # At other stage
        response = create_hardened_response(
            message="Verifying...",
            session_id="upload_test_2",
            current_stage="KYC_VERIFICATION"
        )
        assert response.show_upload_button is False
        
    def test_otp_input_only_at_otp_stage(self):
        """OTP input should only show at OTP_VERIFICATION."""
        response = create_hardened_response(
            message="Please enter OTP",
            session_id="otp_ui_test",
            current_stage="OTP_VERIFICATION"
        )
        assert response.show_otp_input is True
        
    def test_sanction_letter_only_at_sanction(self):
        """Sanction letter button should only show at SANCTION."""
        response = create_hardened_response(
            message="Loan approved!",
            session_id="sanction_test",
            current_stage="SANCTION"
        )
        assert response.show_sanction_letter is True
        
    def test_purpose_explanation_included(self):
        """Purpose explanation should be included when requested."""
        response = create_hardened_response(
            message="Please enter your PAN",
            session_id="purpose_test",
            current_stage="KYC_VERIFICATION",
            purpose_key="pan"
        )
        assert response.purpose_explanation is not None
        assert "RBI" in response.purpose_explanation or "verify" in response.purpose_explanation.lower()
        
    def test_response_to_dict(self):
        """Response should be JSON serializable."""
        response = create_hardened_response(
            message="Test",
            session_id="dict_test",
            current_stage="GREETING"
        )
        as_dict = response.to_dict()
        assert "message" in as_dict
        assert "session_status" in as_dict
        assert "show_chat_input" in as_dict


# ================================================================================
# PART 8: INTEGRATION TESTS
# ================================================================================

class TestIntegration:
    """Integration tests for production hardening."""
    
    def test_full_journey_to_sanction(self):
        """Test a complete journey that ends in sanction."""
        session_id = "integration_sanction_test"
        
        # Start session
        on_session_start(session_id)
        
        # OTP verification
        on_otp_sent(session_id, "9876543210", "KYC_COLLECTION")
        on_otp_verified(session_id, "KYC_VERIFICATION")
        
        # Credit check
        on_credit_score_fetched(session_id, 780, "OFFER_DISCOVERY")
        
        # Income verification
        on_income_verified(session_id, 88000, "INCOME_DOC_UPLOAD")
        
        # Underwriting
        on_underwriting_complete(session_id, True, {"amount": 500000}, "UNDERWRITING")
        
        # Complete journey
        on_journey_complete(session_id, "APPROVED", "SANCTION")
        
        # Verify frozen
        freeze_ctrl = get_freeze_controller()
        assert freeze_ctrl.is_frozen(session_id)
        
        # Verify audit log
        audit = get_audit_logger()
        summary = audit.get_decision_summary(session_id)
        assert summary["final_outcome"] == "APPROVED"
        
    def test_full_journey_to_rejection(self):
        """Test a complete journey that ends in rejection."""
        session_id = "integration_rejection_test"
        
        # Start session
        on_session_start(session_id)
        
        # OTP verification
        on_otp_sent(session_id, "9123456781", "KYC_COLLECTION")
        on_otp_verified(session_id, "KYC_VERIFICATION")
        
        # Credit check - low score
        on_credit_score_fetched(session_id, 580, "OFFER_DISCOVERY")
        
        # Underwriting - rejected
        on_underwriting_complete(session_id, False, {"reason": "Low credit score"}, "UNDERWRITING")
        
        # Complete journey
        on_journey_complete(session_id, "REJECTED", "REJECTION")
        
        # Verify frozen
        freeze_ctrl = get_freeze_controller()
        assert freeze_ctrl.is_frozen(session_id)
        
    def test_blocked_operation_after_freeze(self):
        """Operations should be blocked after journey freeze."""
        session_id = "block_test"
        
        # Freeze the session
        on_journey_complete(session_id, "APPROVED", "SANCTION")
        
        # Try to perform operation
        is_allowed, msg = check_and_audit_operation(session_id, "GREETING", "SEND_MESSAGE")
        assert is_allowed is False


# ================================================================================
# PART 9: COMPLIANCE TESTS
# ================================================================================

class TestCompliance:
    """Tests for NBFC compliance requirements."""
    
    def test_audit_logs_immutable(self):
        """Audit logs should be immutable (no modification method)."""
        logger = AuditLogger()
        
        # Log something
        logger.log("immutable_test", AuditEventType.SESSION_STARTED, "SUCCESS", {}, "GREETING")
        
        # Verify no modification methods exist
        assert not hasattr(logger, "delete_log")
        assert not hasattr(logger, "modify_log")
        assert not hasattr(logger, "clear_log")
        
    def test_terminal_stages_block_operations(self):
        """Terminal stages should block all operations."""
        controller = SessionFreezeController()
        
        for stage in TERMINAL_STAGES:
            is_allowed, _ = controller.check_session_status(f"terminal_test_{stage}", stage)
            assert is_allowed is False
            
    def test_no_auto_fill_inference(self):
        """Normalization should not infer missing data."""
        normalizer = InputNormalizationGuard()
        
        # Amount normalization should not assume tenure
        amount, is_valid, msg = normalizer.normalize_amount("5 lakh")
        # Result should only contain amount, not tenure
        assert "tenure" not in msg.lower()
        assert "months" not in msg.lower()
        
    def test_sensitive_data_masked_in_logs(self):
        """Sensitive data should be masked in audit logs."""
        logger = AuditLogger()
        
        # Log OTP sent with masked mobile
        entry = logger.log(
            "mask_test",
            AuditEventType.OTP_SENT,
            "SUCCESS",
            {"mobile": "3210"},  # Only last 4 digits
            "KYC_COLLECTION"
        )
        
        # Full mobile should not be in logs
        assert "9876543210" not in str(entry.to_dict())


# ================================================================================
# MAIN EXECUTION
# ================================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
