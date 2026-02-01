"""
================================================================================
PHASE 2 VERIFICATION TEST: QUESTION SEQUENCING
================================================================================

This test file verifies that Phase 2 question sequencing works correctly:

1. GREETING: Welcome only, no data collection
2. NEEDS_DISCOVERY: Purpose FIRST, then Amount
3. BASIC_ELIGIBILITY: City FIRST, then Employment Type
4. KYC_COLLECTION: Name FIRST, then Mobile
5. OTP_VERIFICATION: Verify correct OTP handling

Run this file to verify Phase 2 implementation:
    python test_phase2_sequencing.py

================================================================================
"""

import sys
from typing import List, Tuple, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, '.')

from stage_handler_v2 import create_conversational_handler, ConversationalStageHandler
from conversation_prompts import ConversationStep


def print_divider(title: str = ""):
    """Print a visual divider."""
    print(f"\n{'='*70}")
    if title:
        print(f"  {title}")
        print('='*70)


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if details:
        print(f"       {details}")


def run_conversation_test() -> Tuple[int, int]:
    """
    Test the complete conversation flow with proper question sequencing.
    
    Returns:
        Tuple of (passed_tests, total_tests)
    """
    passed = 0
    total = 0
    
    handler = create_conversational_handler()
    session_id = "test_phase2_seq"
    
    # Reset for clean test
    handler.reset_session(session_id)
    
    print_divider("PHASE 2: QUESTION SEQUENCING TEST")
    
    # =========================================================================
    # TEST 1: GREETING STAGE
    # =========================================================================
    print_divider("TEST 1: GREETING STAGE")
    
    total += 1
    result = handler.process_message(session_id, "Hi!")
    
    # Check: Should transition from GREETING to NEEDS_DISCOVERY
    if result['previous_stage'] == "GREETING" and result['current_stage'] == "NEEDS_DISCOVERY":
        passed += 1
        print_result("Greeting transitions to NEEDS_DISCOVERY", True)
    else:
        print_result("Greeting transitions to NEEDS_DISCOVERY", False, 
                    f"Got: {result['previous_stage']} → {result['current_stage']}")
    
    # Check: Welcome message should NOT ask for loan amount
    total += 1
    bot_resp = result.get('bot_response', '').lower()
    asks_amount_in_greeting = any(kw in bot_resp for kw in ['how much', 'amount', 'lakh', 'loan amount'])
    if not asks_amount_in_greeting:
        passed += 1
        print_result("Greeting does NOT ask for loan amount", True)
    else:
        print_result("Greeting does NOT ask for loan amount", False, f"Response: {result['bot_response'][:50]}...")
    
    # =========================================================================
    # TEST 2: NEEDS_DISCOVERY - PURPOSE FIRST
    # =========================================================================
    print_divider("TEST 2: NEEDS_DISCOVERY - PURPOSE FIRST")
    
    # The greeting response should include the purpose question  
    # (combined: "Welcome... What would you like to use the loan for?")
    # So we check the greeting response, not the next message
    greeting_response = result.get('bot_response', '').lower()
    
    total += 1
    # First question should be about purpose (part of the greeting response)
    asks_purpose = any(kw in greeting_response for kw in ['purpose', 'what for', 'use the loan for', 'planning to use', 'what would you like to use', 'loan would be for'])
    if asks_purpose:
        passed += 1
        print_result("GREETING+NEEDS_DISCOVERY asks for PURPOSE first", True)
    else:
        print_result("GREETING+NEEDS_DISCOVERY asks for PURPOSE first", False, f"Response: {greeting_response[:80]}...")
    
    # Provide purpose
    result = handler.process_message(session_id, "home renovation")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('loan_purpose'):
        passed += 1
        print_result("Purpose extracted correctly", True, f"Purpose: {state.get('loan_purpose')}")
    else:
        print_result("Purpose extracted correctly", False)
    
    # =========================================================================
    # TEST 3: NEEDS_DISCOVERY - AMOUNT SECOND
    # =========================================================================
    print_divider("TEST 3: NEEDS_DISCOVERY - AMOUNT SECOND")
    
    total += 1
    bot_resp = result.get('bot_response', '').lower()
    # After purpose, should ask for amount
    asks_amount = any(kw in bot_resp for kw in ['how much', 'amount', 'considering', 'need'])
    if asks_amount:
        passed += 1
        print_result("After PURPOSE, asks for AMOUNT", True)
    else:
        print_result("After PURPOSE, asks for AMOUNT", False, f"Response: {result['bot_response'][:80]}...")
    
    # Provide amount - should transition to BASIC_ELIGIBILITY
    result = handler.process_message(session_id, "5 lakhs")
    
    total += 1
    if result['current_stage'] == "BASIC_ELIGIBILITY":
        passed += 1
        print_result("After amount, transitions to BASIC_ELIGIBILITY", True)
    else:
        print_result("After amount, transitions to BASIC_ELIGIBILITY", False, 
                    f"Current stage: {result['current_stage']}")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('loan_amount') == 500000:
        passed += 1
        print_result("Amount extracted correctly", True, f"Amount: {state.get('loan_amount')}")
    else:
        print_result("Amount extracted correctly", False, f"Got: {state.get('loan_amount')}")
    
    # =========================================================================
    # TEST 4: BASIC_ELIGIBILITY - CITY FIRST
    # =========================================================================
    print_divider("TEST 4: BASIC_ELIGIBILITY - CITY FIRST")
    
    # The city question should be included in the transition response from NEEDS_DISCOVERY
    # (combined: "Got it!... Which city do you currently live in?")
    transition_response = result.get('bot_response', '').lower()
    
    total += 1
    asks_city = any(kw in transition_response for kw in ['city', 'where', 'location', 'based in', 'live in', 'located'])
    if asks_city:
        passed += 1
        print_result("NEEDS_DISCOVERY→BASIC_ELIGIBILITY asks for CITY", True)
    else:
        print_result("NEEDS_DISCOVERY→BASIC_ELIGIBILITY asks for CITY", False, f"Response: {result['bot_response'][:80]}...")
    
    # Provide city
    result = handler.process_message(session_id, "Mumbai")
    
    # Provide city
    result = handler.process_message(session_id, "Mumbai")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('city'):
        passed += 1
        print_result("City extracted correctly", True, f"City: {state.get('city')}")
    else:
        print_result("City extracted correctly", False)
    
    # =========================================================================
    # TEST 5: BASIC_ELIGIBILITY - EMPLOYMENT SECOND
    # =========================================================================
    print_divider("TEST 5: BASIC_ELIGIBILITY - EMPLOYMENT SECOND")
    
    total += 1
    bot_resp = result.get('bot_response', '').lower()
    asks_employment = any(kw in bot_resp for kw in ['salaried', 'self-employed', 'employment', 'business'])
    if asks_employment:
        passed += 1
        print_result("After CITY, asks for EMPLOYMENT TYPE", True)
    else:
        print_result("After CITY, asks for EMPLOYMENT TYPE", False, f"Response: {result['bot_response'][:80]}...")
    
    # Provide employment - should transition to KYC_COLLECTION
    result = handler.process_message(session_id, "salaried")
    
    total += 1
    if result['current_stage'] == "KYC_COLLECTION":
        passed += 1
        print_result("After employment, transitions to KYC_COLLECTION", True)
    else:
        print_result("After employment, transitions to KYC_COLLECTION", False,
                    f"Current stage: {result['current_stage']}")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('employment_type') == "Salaried":
        passed += 1
        print_result("Employment type extracted correctly", True, f"Type: {state.get('employment_type')}")
    else:
        print_result("Employment type extracted correctly", False, f"Got: {state.get('employment_type')}")
    
    # =========================================================================
    # TEST 6: KYC_COLLECTION - NAME FIRST
    # =========================================================================
    print_divider("TEST 6: KYC_COLLECTION - NAME FIRST")
    
    # The name question should be included in the transition response from BASIC_ELIGIBILITY
    # (combined: "Great — based on what you've shared... Could you please share your full name?")
    transition_response = result.get('bot_response', '').lower()
    
    total += 1
    asks_name = any(kw in transition_response for kw in ['name', 'your name', 'full name'])
    if asks_name:
        passed += 1
        print_result("BASIC_ELIGIBILITY→KYC asks for NAME", True)
    else:
        print_result("BASIC_ELIGIBILITY→KYC asks for NAME", False, f"Response: {result['bot_response'][:80]}...")
    
    # Provide name
    result = handler.process_message(session_id, "Rahul Sharma")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('user_name'):
        passed += 1
        print_result("Name extracted correctly", True, f"Name: {state.get('user_name')}")
    else:
        print_result("Name extracted correctly", False)
    
    # =========================================================================
    # TEST 7: KYC_COLLECTION - MOBILE SECOND
    # =========================================================================
    print_divider("TEST 7: KYC_COLLECTION - MOBILE SECOND")
    
    total += 1
    bot_resp = result.get('bot_response', '').lower()
    asks_mobile = any(kw in bot_resp for kw in ['mobile', 'phone', 'number', '10-digit'])
    if asks_mobile:
        passed += 1
        print_result("After NAME, asks for MOBILE", True)
    else:
        print_result("After NAME, asks for MOBILE", False, f"Response: {result['bot_response'][:80]}...")
    
    # Provide mobile - should transition to OTP_VERIFICATION
    result = handler.process_message(session_id, "9876543210")
    
    total += 1
    if result['current_stage'] == "OTP_VERIFICATION":
        passed += 1
        print_result("After mobile, transitions to OTP_VERIFICATION", True)
    else:
        print_result("After mobile, transitions to OTP_VERIFICATION", False,
                    f"Current stage: {result['current_stage']}")
    
    total += 1
    state = result.get('state_data', {})
    if state.get('user_mobile') == "9876543210":
        passed += 1
        print_result("Mobile extracted correctly", True, f"Mobile: {state.get('user_mobile')}")
    else:
        print_result("Mobile extracted correctly", False, f"Got: {state.get('user_mobile')}")
    
    # =========================================================================
    # TEST 8: OTP_VERIFICATION
    # =========================================================================
    print_divider("TEST 8: OTP_VERIFICATION")
    
    # Verify OTP is generated and sent
    total += 1
    if result.get('otp_code'):
        passed += 1
        print_result("OTP generated", True, f"OTP: {result['otp_code']}")
    else:
        print_result("OTP generated", False)
    
    # Enter correct OTP
    result = handler.process_message(session_id, "123456")
    
    total += 1
    if result['current_stage'] == "KYC_VERIFICATION":
        passed += 1
        print_result("Correct OTP transitions to KYC_VERIFICATION", True)
    else:
        print_result("Correct OTP transitions to KYC_VERIFICATION", False,
                    f"Current stage: {result['current_stage']}")
    
    # Clean up
    handler.reset_session(session_id)
    
    return passed, total


def run_redirect_test() -> Tuple[int, int]:
    """
    Test redirect handling for irrelevant responses.
    
    Returns:
        Tuple of (passed_tests, total_tests)
    """
    passed = 0
    total = 0
    
    handler = create_conversational_handler()
    session_id = "test_phase2_redirect"
    
    # Reset for clean test
    handler.reset_session(session_id)
    
    print_divider("REDIRECT HANDLING TEST")
    
    # Get to NEEDS_DISCOVERY
    handler.process_message(session_id, "Hi!")
    
    # Test: Irrelevant response should get redirect
    total += 1
    result = handler.process_message(session_id, "haha what's up")
    
    # Should still be in NEEDS_DISCOVERY (no transition)
    if result['current_stage'] == "NEEDS_DISCOVERY":
        passed += 1
        print_result("Irrelevant response does NOT transition", True)
    else:
        print_result("Irrelevant response does NOT transition", False,
                    f"Stage: {result['current_stage']}")
    
    # Should get redirect message - either asks about purpose OR re-asks the purpose question
    total += 1
    bot_resp = result.get('bot_response', '').lower()
    is_redirect = any(kw in bot_resp for kw in ['purpose', 'loan', 'help', 'use', 'what for', 'would you like'])
    if is_redirect:
        passed += 1
        print_result("Redirect message asks relevant question", True)
    else:
        print_result("Redirect message asks relevant question", False,
                    f"Response: {result['bot_response'][:80]}...")
    
    # Clean up
    handler.reset_session(session_id)
    
    return passed, total


def run_data_persistence_test() -> Tuple[int, int]:
    """
    Test that data persists across messages.
    
    Returns:
        Tuple of (passed_tests, total_tests)
    """
    passed = 0
    total = 0
    
    handler = create_conversational_handler()
    session_id = "test_phase2_persist"
    
    # Reset for clean test
    handler.reset_session(session_id)
    
    print_divider("DATA PERSISTENCE TEST")
    
    # Go through the CORRECT flow
    handler.process_message(session_id, "Hi!")  # GREETING → NEEDS_DISCOVERY
    # NEEDS_DISCOVERY asks for purpose first
    handler.process_message(session_id, "home renovation")  # Purpose
    handler.process_message(session_id, "5 lakhs")  # Amount → BASIC_ELIGIBILITY
    # BASIC_ELIGIBILITY asks for city first
    handler.process_message(session_id, "Mumbai")  # City
    handler.process_message(session_id, "salaried")  # Employment → KYC_COLLECTION
    
    # Check all data is persisted
    result = handler.process_message(session_id, "proceed")
    state = result.get('state_data', {})
    
    total += 1
    if state.get('loan_purpose'):
        passed += 1
        print_result("Loan purpose persisted", True, f"Purpose: {state.get('loan_purpose')}")
    else:
        print_result("Loan purpose persisted", False)
    
    total += 1
    if state.get('loan_amount') == 500000:
        passed += 1
        print_result("Loan amount persisted", True, f"Amount: {state.get('loan_amount')}")
    else:
        print_result("Loan amount persisted", False, f"Got: {state.get('loan_amount')}")
    
    total += 1
    if state.get('city'):
        passed += 1
        print_result("City persisted", True, f"City: {state.get('city')}")
    else:
        print_result("City persisted", False)
    
    total += 1
    if state.get('employment_type'):
        passed += 1
        print_result("Employment type persisted", True, f"Type: {state.get('employment_type')}")
    else:
        print_result("Employment type persisted", False)
    
    # Clean up
    handler.reset_session(session_id)
    
    return passed, total


def main():
    """Run all Phase 2 verification tests."""
    print("\n")
    print("█" * 70)
    print("█" + " " * 68 + "█")
    print("█" + "    PHASE 2: QUESTION SEQUENCING VERIFICATION".center(68) + "█")
    print("█" + " " * 68 + "█")
    print("█" * 70)
    
    total_passed = 0
    total_tests = 0
    
    # Run tests
    p, t = run_conversation_test()
    total_passed += p
    total_tests += t
    
    p, t = run_redirect_test()
    total_passed += p
    total_tests += t
    
    p, t = run_data_persistence_test()
    total_passed += p
    total_tests += t
    
    # Print summary
    print_divider("TEST SUMMARY")
    
    print(f"\nTotal Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    print(f"Pass Rate: {100 * total_passed / total_tests:.1f}%")
    
    if total_passed == total_tests:
        print("\n🎉 ALL TESTS PASSED! Phase 2 implementation verified.")
    else:
        print(f"\n⚠️  {total_tests - total_passed} tests failed. Review implementation.")
    
    print("\n" + "="*70)
    
    return total_passed == total_tests


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
