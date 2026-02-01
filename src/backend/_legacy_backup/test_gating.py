#!/usr/bin/env python3
"""
Test script for strict gating middleware
"""

from strict_gating_middleware import (
    get_gating_middleware,
    validate_loan_purpose,
    validate_loan_amount,
    validate_mobile_number,
    validate_pan_number,
    validate_aadhaar_number,
    validate_otp_code,
    validate_city,
    validate_employment_type,
    validate_full_name,
    validate_confirmation
)

print("=" * 60)
print("STRICT GATING MIDDLEWARE - VALIDATOR TESTS")
print("=" * 60)

# Test loan purpose
print("\n1. Testing loan_purpose validator:")
test_cases = [
    ("I need a home loan", True, "Home Loan"),
    ("personal expenses", True, "Personal Loan"),
    ("12345", False, None),
    ("random text", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_loan_purpose(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test loan amount
print("\n2. Testing loan_amount validator:")
test_cases = [
    ("5 lakhs", True, 500000.0),
    ("10 lakh", True, 1000000.0),
    ("mumbai", False, None),
    ("500000", True, 500000.0),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_loan_amount(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test mobile
print("\n3. Testing mobile_number validator:")
test_cases = [
    ("9876543210", True, "9876543210"),
    ("919876543210", True, "9876543210"),
    ("12345", False, None),
    ("1234567890", False, None),  # Doesn't start with 6-9
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_mobile_number(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test PAN
print("\n4. Testing pan_number validator:")
test_cases = [
    ("ABCDE1234F", True, "ABCDE1234F"),
    ("abcde1234f", True, "ABCDE1234F"),  # Should uppercase
    ("random", False, None),
    ("12345", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_pan_number(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test OTP
print("\n5. Testing otp_code validator:")
test_cases = [
    ("123456", True, "123456"),
    ("1234", True, "1234"),
    ("abc", False, None),
    ("12", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_otp_code(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test city
print("\n6. Testing city validator:")
test_cases = [
    ("Mumbai", True, "Mumbai"),
    ("delhi", True, "Delhi"),
    ("BANGALORE", True, "Bangalore"),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_city(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test employment
print("\n7. Testing employment_type validator:")
test_cases = [
    ("salaried", True, "salaried"),
    ("self employed", True, "self_employed"),
    ("business owner", True, "business"),
    ("random", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_employment_type(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test name
print("\n8. Testing full_name validator:")
test_cases = [
    ("Rahul Sharma", True, "Rahul Sharma"),
    ("My name is Priya", True, "Priya"),
    ("12345", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_full_name(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

# Test confirmation
print("\n9. Testing confirmation validator:")
test_cases = [
    ("yes", True, True),
    ("no", True, False),
    ("proceed", True, True),
    ("random", False, None),
]
for input_text, expected_valid, expected_result in test_cases:
    valid, result = validate_confirmation(input_text)
    status = "✅" if valid == expected_valid else "❌"
    print(f"  {status} '{input_text}' → valid={valid}, result={result}")

print("\n" + "=" * 60)
print("GATING MIDDLEWARE INTEGRATION TEST")
print("=" * 60)

# Test the middleware gating logic
middleware = get_gating_middleware()

# Simulate a validation at NEEDS_DISCOVERY asking for purpose
print("\n10. Testing middleware.validate_input():")

# Test 1: Valid purpose at correct stage
result = middleware.validate_input(
    session_id="test_1",
    user_message="home loan",
    current_stage="NEEDS_DISCOVERY",
    current_step="NEEDS_ASK_PURPOSE",
    state_data={}
)
print(f"  ✅ Valid purpose at NEEDS_ASK_PURPOSE: allowed={result.allowed}")

# Test 2: Invalid input at purpose stage (number instead of purpose)
result = middleware.validate_input(
    session_id="test_2",
    user_message="12345",
    current_stage="NEEDS_DISCOVERY",
    current_step="NEEDS_ASK_PURPOSE",
    state_data={}
)
print(f"  ✅ Invalid input at NEEDS_ASK_PURPOSE: allowed={result.allowed}, reask={result.reask_required}")

# Test 3: OTP stage without mobile (precondition fail)
result = middleware.validate_input(
    session_id="test_3",
    user_message="123456",
    current_stage="OTP_VERIFICATION",
    current_step="OTP_SENT",
    state_data={"user_name": "Test"}  # Missing user_mobile
)
print(f"  ✅ OTP stage without mobile: allowed={result.allowed}, precondition_failed={result.precondition_failed}")

# Test 4: OTP stage with all preconditions
result = middleware.validate_input(
    session_id="test_4",
    user_message="123456",
    current_stage="OTP_VERIFICATION",
    current_step="OTP_SENT",
    state_data={"user_name": "Test", "user_mobile": "9876543210"}
)
print(f"  ✅ OTP stage with preconditions: allowed={result.allowed}")

# Test 5: KYC_VERIFICATION without OTP verified
result = middleware.validate_input(
    session_id="test_5",
    user_message="ABCDE1234F",
    current_stage="KYC_VERIFICATION",
    current_step="KYC_ASK_PAN",
    state_data={"otp_verified": False}
)
print(f"  ✅ KYC without OTP verified: allowed={result.allowed}, precondition_failed={result.precondition_failed}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETE")
print("=" * 60)
