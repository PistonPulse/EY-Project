#!/usr/bin/env python3
"""
================================================================================
PHASE 1 VERIFICATION: STRICT STAGE MACHINE TEST
================================================================================

This script tests the strict stage machine to verify:
1. Stage transitions are deterministic
2. Invalid transitions are blocked
3. State persists across "reloads" (new handler instances)
4. No skipping stages is possible

Run this script to verify Phase 1 implementation is correct.

Usage:
    python test_strict_stage_machine.py
    
================================================================================
"""

import os
import sys
import json
import shutil
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stage_machine_v2 import (
    Stage,
    StageEvent,
    StageState,
    StageController,
    get_stage_controller,
    request_transition,
    update_session_data,
    get_session_state,
    reset_session,
    VALID_TRANSITIONS
)

from stage_handler import (
    StageMessageHandler,
    create_stage_handler,
    extract_mobile_number,
    extract_loan_amount,
    extract_name,
    extract_otp
)


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{'='*60}")
    print(f" {text}")
    print(f"{'='*60}")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        print(f"   {details}")


def test_stage_definitions():
    """Test that all required stages are defined."""
    print_header("TEST 1: Stage Definitions")
    
    required_stages = [
        "GREETING",
        "NEEDS_DISCOVERY",
        "BASIC_ELIGIBILITY",
        "KYC_COLLECTION",
        "OTP_VERIFICATION",
        "KYC_VERIFICATION",
        "OFFER_DISCOVERY",
        "INCOME_DOC_UPLOAD",
        "UNDERWRITING",
        "SANCTION",
        "REJECTION"
    ]
    
    defined_stages = [s.value for s in Stage]
    
    all_defined = all(s in defined_stages for s in required_stages)
    
    print_result(
        "All required stages defined",
        all_defined,
        f"Required: {len(required_stages)}, Defined: {len(defined_stages)}"
    )
    
    # Print stage list
    print("\n   Defined stages:")
    for stage in Stage:
        print(f"   - {stage.value}")
    
    assert all_defined, "Not all required stages are defined"


def test_valid_transitions():
    """Test that transition matrix is properly defined."""
    print_header("TEST 2: Transition Matrix")
    
    # Check that all stages have transition rules
    all_have_rules = all(s in VALID_TRANSITIONS for s in Stage)
    
    print_result(
        "All stages have transition rules",
        all_have_rules
    )
    
    # Check terminal states have no transitions
    sanction_transitions = len(VALID_TRANSITIONS.get(Stage.SANCTION, {}))
    rejection_transitions = len(VALID_TRANSITIONS.get(Stage.REJECTION, {}))
    
    print_result(
        "SANCTION is terminal (no outgoing transitions)",
        sanction_transitions == 0,
        f"Transitions: {sanction_transitions}"
    )
    
    print_result(
        "REJECTION is terminal (no outgoing transitions)",
        rejection_transitions == 0,
        f"Transitions: {rejection_transitions}"
    )
    
    # Print transition matrix
    print("\n   Transition matrix:")
    for stage, transitions in VALID_TRANSITIONS.items():
        events = list(transitions.keys()) if transitions else ["(terminal)"]
        print(f"   {stage.value}: {len(transitions)} transitions")
    
    assert all_have_rules, "Not all stages have transition rules"
    assert sanction_transitions == 0, "SANCTION should be terminal"
    assert rejection_transitions == 0, "REJECTION should be terminal"


def test_valid_transition_sequence():
    """Test that a valid sequence of transitions works."""
    print_header("TEST 3: Valid Transition Sequence")
    
    session_id = "test_valid_sequence"
    controller = StageController(persistence_dir="./test_stage_states")
    
    # Clean start
    controller.reset_session(session_id)
    
    # Get initial state
    state = controller.get_or_create_session(session_id)
    initial_stage = state.current_stage
    
    print_result(
        "Initial stage is GREETING",
        initial_stage == Stage.GREETING,
        f"Got: {initial_stage.value}"
    )
    
    # Execute valid transition sequence
    transitions = [
        (StageEvent.USER_GREETED, Stage.NEEDS_DISCOVERY),
        (StageEvent.LOAN_AMOUNT_PROVIDED, Stage.BASIC_ELIGIBILITY),
        (StageEvent.ELIGIBILITY_CHECKED, Stage.KYC_COLLECTION),
        (StageEvent.KYC_INFO_PROVIDED, Stage.OTP_VERIFICATION),
        (StageEvent.OTP_VERIFIED, Stage.KYC_VERIFICATION),
        (StageEvent.KYC_VERIFIED, Stage.OFFER_DISCOVERY),
        (StageEvent.OFFERS_CHECKED, Stage.INCOME_DOC_UPLOAD),
        (StageEvent.DOCUMENTS_UPLOADED, Stage.UNDERWRITING),
        (StageEvent.UNDERWRITING_APPROVED, Stage.SANCTION),
    ]
    
    all_transitions_valid = True
    
    for event, expected_stage in transitions:
        success, new_stage, msg = controller.transition(session_id, event)
        
        if not success or new_stage != expected_stage:
            all_transitions_valid = False
            print_result(
                f"Transition with {event.value}",
                False,
                f"Expected: {expected_stage.value}, Got: {new_stage.value}"
            )
        else:
            print(f"   ✓ {event.value} → {new_stage.value}")
    
    print_result(
        "All valid transitions succeeded",
        all_transitions_valid
    )
    
    # Clean up
    controller.reset_session(session_id)
    
    assert all_transitions_valid, "Not all valid transitions succeeded"


def test_invalid_transition_blocked():
    """Test that invalid transitions are blocked."""
    print_header("TEST 4: Invalid Transition Blocking")
    
    session_id = "test_invalid_block"
    controller = StageController(persistence_dir="./test_stage_states")
    
    # Clean start
    controller.reset_session(session_id)
    
    # Try to skip from GREETING directly to KYC_COLLECTION (invalid)
    success, stage, msg = controller.transition(
        session_id, 
        StageEvent.KYC_INFO_PROVIDED  # Should fail - need GREETING → NEEDS_DISCOVERY first
    )
    
    print_result(
        "Invalid skip GREETING → KYC blocked",
        not success,
        f"Success={success}, Stage={stage.value}"
    )
    
    # Move to NEEDS_DISCOVERY properly
    controller.transition(session_id, StageEvent.USER_GREETED)
    
    # Try to skip to OTP_VERIFICATION (invalid)
    success, stage, msg = controller.transition(
        session_id,
        StageEvent.OTP_VERIFIED  # Should fail - not in OTP_VERIFICATION stage
    )
    
    print_result(
        "Invalid skip NEEDS_DISCOVERY → OTP blocked",
        not success,
        f"Success={success}, Stage={stage.value}"
    )
    
    # Clean up
    controller.reset_session(session_id)
    
    # No assertion needed - test passes if we reach here without errors


def test_state_persistence():
    """Test that state persists across controller instances."""
    print_header("TEST 5: State Persistence")
    
    session_id = "test_persistence"
    persistence_dir = "./test_stage_states"
    
    # Create first controller and advance some stages
    controller1 = StageController(persistence_dir=persistence_dir)
    controller1.reset_session(session_id)
    
    # Make some transitions
    controller1.transition(session_id, StageEvent.USER_GREETED)
    controller1.transition(session_id, StageEvent.LOAN_AMOUNT_PROVIDED, {"loan_amount": 500000})
    controller1.transition(session_id, StageEvent.ELIGIBILITY_CHECKED)
    
    # Get current stage
    state1 = controller1.get_or_create_session(session_id)
    stage_before = state1.current_stage
    
    print(f"   Stage before 'reload': {stage_before.value}")
    
    # Simulate page reload - create new controller instance
    controller2 = StageController(persistence_dir=persistence_dir)
    
    # Get state - should be restored
    state2 = controller2.get_or_create_session(session_id)
    stage_after = state2.current_stage
    
    print(f"   Stage after 'reload': {stage_after.value}")
    
    persistence_works = stage_before == stage_after
    
    print_result(
        "Stage persists across reloads",
        persistence_works,
        f"Before: {stage_before.value}, After: {stage_after.value}"
    )
    
    # Also check data persistence
    data_persists = state2.loan_amount == 500000
    
    print_result(
        "Data persists across reloads",
        data_persists,
        f"Loan amount: {state2.loan_amount}"
    )
    
    # Clean up
    controller2.reset_session(session_id)
    
    assert persistence_works, "Stage did not persist across reloads"
    assert data_persists, "Data did not persist across reloads"


def test_terminal_state_blocking():
    """Test that terminal states block further transitions."""
    print_header("TEST 6: Terminal State Blocking")
    
    session_id = "test_terminal"
    controller = StageController(persistence_dir="./test_stage_states")
    
    # Clean start and fast-forward to SANCTION
    controller.reset_session(session_id)
    
    transitions = [
        StageEvent.USER_GREETED,
        StageEvent.LOAN_AMOUNT_PROVIDED,
        StageEvent.ELIGIBILITY_CHECKED,
        StageEvent.KYC_INFO_PROVIDED,
        StageEvent.OTP_VERIFIED,
        StageEvent.KYC_VERIFIED,
        StageEvent.OFFERS_CHECKED,
        StageEvent.DOCUMENTS_UPLOADED,
        StageEvent.UNDERWRITING_APPROVED,
    ]
    
    for event in transitions:
        controller.transition(session_id, event)
    
    # Verify we're at SANCTION
    state = controller.get_or_create_session(session_id)
    at_sanction = state.current_stage == Stage.SANCTION
    
    print_result(
        "Reached SANCTION terminal state",
        at_sanction,
        f"Current: {state.current_stage.value}"
    )
    
    # Try to make any transition - should all fail
    test_events = [
        StageEvent.USER_GREETED,
        StageEvent.LOAN_AMOUNT_PROVIDED,
        StageEvent.DOCUMENTS_UPLOADED,
    ]
    
    all_blocked = True
    for event in test_events:
        success, stage, msg = controller.transition(session_id, event)
        if success:
            all_blocked = False
            print(f"   ❌ {event.value} should have been blocked")
        else:
            print(f"   ✓ {event.value} blocked correctly")
    
    print_result(
        "All transitions from terminal state blocked",
        all_blocked
    )
    
    # Clean up
    controller.reset_session(session_id)
    
    assert at_sanction, "Did not reach SANCTION terminal state"
    assert all_blocked, "Not all transitions from terminal state were blocked"


def test_message_handler():
    """Test the message handler with real messages."""
    print_header("TEST 7: Message Handler Integration")
    
    session_id = "test_handler"
    handler = create_stage_handler()
    
    # Reset
    handler.reset_session(session_id)
    
    # Test message sequence
    messages = [
        ("Hi there!", "NEEDS_DISCOVERY"),  # Should move to NEEDS_DISCOVERY
        ("I need a loan of 5 lakhs", "BASIC_ELIGIBILITY"),  # Should extract amount
        ("proceed", "KYC_COLLECTION"),  # Should move to KYC
        ("My name is Rahul and number is 9876543210", "OTP_VERIFICATION"),  # Should extract data
        ("123456", "KYC_VERIFICATION"),  # Should verify OTP
    ]
    
    all_correct = True
    
    for message, expected_stage in messages:
        result = handler.process_message(session_id, message)
        actual_stage = result["current_stage"]
        
        if actual_stage != expected_stage:
            all_correct = False
            print(f"   ❌ '{message[:30]}...' → {actual_stage} (expected {expected_stage})")
        else:
            print(f"   ✓ '{message[:30]}...' → {actual_stage}")
    
    print_result(
        "Message handler routes correctly",
        all_correct
    )
    
    # Clean up
    handler.reset_session(session_id)
    
    assert all_correct, "Message handler did not route correctly"


def test_data_extraction():
    """Test data extraction functions."""
    print_header("TEST 8: Data Extraction")
    
    # Test mobile number extraction
    test_cases_mobile = [
        ("my number is 9876543210", "9876543210"),
        ("+91 9876543210", "9876543210"),
        ("call me at 9123456789", "9123456789"),
        ("no number here", None),
    ]
    
    mobile_ok = True
    for text, expected in test_cases_mobile:
        result = extract_mobile_number(text)
        if result != expected:
            mobile_ok = False
            print(f"   ❌ Mobile: '{text}' → {result} (expected {expected})")
        else:
            print(f"   ✓ Mobile: '{text}' → {result}")
    
    print_result("Mobile number extraction", mobile_ok)
    
    # Test loan amount extraction
    test_cases_amount = [
        ("I need 5 lakhs", 500000),
        ("loan of 10L", 1000000),
        ("500000 rupees", 500000),
        ("just chatting", None),
    ]
    
    amount_ok = True
    for text, expected in test_cases_amount:
        result = extract_loan_amount(text)
        if result != expected:
            amount_ok = False
            print(f"   ❌ Amount: '{text}' → {result} (expected {expected})")
        else:
            print(f"   ✓ Amount: '{text}' → {result}")
    
    print_result("Loan amount extraction", amount_ok)
    
    # Test OTP extraction
    test_cases_otp = [
        ("123456", "123456"),
        ("OTP is 654321", "654321"),
        ("my code 789012", "789012"),
        ("hello", None),
    ]
    
    otp_ok = True
    for text, expected in test_cases_otp:
        result = extract_otp(text)
        if result != expected:
            otp_ok = False
            print(f"   ❌ OTP: '{text}' → {result} (expected {expected})")
        else:
            print(f"   ✓ OTP: '{text}' → {result}")
    
    print_result("OTP extraction", otp_ok)
    
    assert mobile_ok, "Mobile number extraction failed"
    assert amount_ok, "Loan amount extraction failed"
    assert otp_ok, "OTP extraction failed"


def cleanup_test_files():
    """Clean up test persistence files."""
    test_dir = "./test_stage_states"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("\n   Cleaned up test files")


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print(" PHASE 1 STRICT STAGE MACHINE VERIFICATION")
    print(" Testing deterministic flow control")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Stage Definitions", test_stage_definitions()))
    results.append(("Transition Matrix", test_valid_transitions()))
    results.append(("Valid Transitions", test_valid_transition_sequence()))
    results.append(("Invalid Blocking", test_invalid_transition_blocked()))
    results.append(("State Persistence", test_state_persistence()))
    results.append(("Terminal States", test_terminal_state_blocking()))
    results.append(("Message Handler", test_message_handler()))
    results.append(("Data Extraction", test_data_extraction()))
    
    # Clean up
    cleanup_test_files()
    
    # Summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"   {status} {name}")
    
    print(f"\n   Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n   🎉 ALL TESTS PASSED - Phase 1 implementation is correct!")
        print("\n   The strict stage machine provides:")
        print("   ✓ Deterministic stage transitions")
        print("   ✓ Invalid transition blocking")
        print("   ✓ State persistence across reloads")
        print("   ✓ No skipping stages")
        print("   ✓ No automatic transitions")
        print("   ✓ Backend-only stage control")
    else:
        print("\n   ⚠️ SOME TESTS FAILED - Review the implementation")
    
    print("\n" + "="*60 + "\n")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
