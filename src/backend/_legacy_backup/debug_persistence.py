#!/usr/bin/env python3
"""Debug script to trace persistence test flow."""

import sys
sys.path.insert(0, '.')

from stage_handler_v2 import create_conversational_handler

handler = create_conversational_handler()
session_id = 'debug_test'
handler.reset_session(session_id)

print("\n=== DEBUG: Tracing persistence test flow ===\n")

# Step 1: Hi
print("Step 1: Hi")
result = handler.process_message(session_id, "Hi!")
print(f"  Stage: {result['current_stage']}")
print(f"  Response: {result['bot_response'][:60]}...")

# Step 2: home renovation
print("\nStep 2: home renovation")
result = handler.process_message(session_id, "home renovation")
print(f"  Stage: {result['current_stage']}")
print(f"  Purpose: {result['state_data'].get('loan_purpose')}")
print(f"  Response: {result['bot_response'][:60]}...")

# Step 3: 5 lakhs
print("\nStep 3: 5 lakhs")
result = handler.process_message(session_id, "5 lakhs")
print(f"  Stage: {result['current_stage']}")
print(f"  Amount: {result['state_data'].get('loan_amount')}")
print(f"  Response: {result['bot_response'][:60]}...")

# Step 4: Mumbai
print("\nStep 4: Mumbai")
result = handler.process_message(session_id, "Mumbai")
print(f"  Stage: {result['current_stage']}")
print(f"  City: {result['state_data'].get('city')}")
print(f"  Response: {result['bot_response'][:60]}...")

# Step 5: salaried
print("\nStep 5: salaried")
result = handler.process_message(session_id, "salaried")
print(f"  Stage: {result['current_stage']}")
print(f"  Employment: {result['state_data'].get('employment_type')}")
print(f"  Response: {result['bot_response'][:60]}...")

# Final check
print("\n=== FINAL STATE ===")
state = result['state_data']
print(f"  loan_purpose: {state.get('loan_purpose')}")
print(f"  loan_amount: {state.get('loan_amount')}")
print(f"  city: {state.get('city')}")
print(f"  employment_type: {state.get('employment_type')}")

handler.reset_session(session_id)
