"""
================================================================================
PHASE 2: CONVERSATION PROMPTS AND QUESTION SEQUENCING
================================================================================

This module defines the conversation flow for each stage in the loan journey.
It ensures questions are asked in a natural, human-like, NBFC-compliant order.

================================================================================
WHY QUESTION SEQUENCE MATTERS
================================================================================

PROBLEM WITH RANDOM QUESTIONING:
- Asking for personal details before understanding needs feels intrusive
- Jumping to eligibility questions without context confuses customers
- Multiple questions in one message overwhelms users
- Robotic phrasing destroys trust

SOLUTION - HUMAN LOAN OFFICER APPROACH:
1. Build rapport first (GREETING)
2. Understand the need before offering solutions (NEEDS_DISCOVERY)
3. Light qualification before asking for ID (BASIC_ELIGIBILITY)
4. Collect identity only after trust is built (KYC_COLLECTION)

================================================================================
WHY PURPOSE IS ASKED BEFORE AMOUNT
================================================================================

PSYCHOLOGICAL REASONING:
- Asking "What do you need the money for?" shows genuine interest
- It builds rapport and trust before discussing numbers
- Customers feel heard, not processed
- It allows for tailored responses ("A home renovation? Great timing...")

COMPLIANCE REASONING:
- Understanding purpose helps with regulatory classification
- Loan purpose affects risk assessment
- Some purposes have different eligibility criteria

================================================================================
WHY ELIGIBILITY IS CHECKED BEFORE KYC
================================================================================

CUSTOMER EXPERIENCE:
- No one wants to share personal details for a loan they can't get
- Light filtering (city, employment) saves time for ineligible customers
- Builds confidence: "You seem eligible, let's verify your identity"

OPERATIONAL EFFICIENCY:
- Reduces KYC processing for ineligible applicants
- Saves API calls to verification services
- Reduces data handling burden for non-viable leads

================================================================================
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


# ================================================================================
# CONVERSATION SUB-STATES
# ================================================================================
# Within each stage, we track which question we're on.
# This prevents asking the same question twice and ensures proper sequencing.

class ConversationStep(Enum):
    """
    Sub-states within each stage to track conversation progress.
    """
    # GREETING stage steps
    GREETING_WELCOME = "GREETING_WELCOME"
    GREETING_COMPLETE = "GREETING_COMPLETE"
    
    # NEEDS_DISCOVERY stage steps
    NEEDS_ASK_PURPOSE = "NEEDS_ASK_PURPOSE"
    NEEDS_ASK_AMOUNT = "NEEDS_ASK_AMOUNT"
    NEEDS_CONFIRM = "NEEDS_CONFIRM"
    NEEDS_COMPLETE = "NEEDS_COMPLETE"
    
    # BASIC_ELIGIBILITY stage steps
    ELIGIBILITY_ASK_CITY = "ELIGIBILITY_ASK_CITY"
    ELIGIBILITY_ASK_EMPLOYMENT = "ELIGIBILITY_ASK_EMPLOYMENT"
    ELIGIBILITY_CONFIRM = "ELIGIBILITY_CONFIRM"
    ELIGIBILITY_COMPLETE = "ELIGIBILITY_COMPLETE"
    
    # KYC_COLLECTION stage steps
    KYC_ASK_NAME = "KYC_ASK_NAME"
    KYC_ASK_MOBILE = "KYC_ASK_MOBILE"
    KYC_COMPLETE = "KYC_COMPLETE"
    
    # OTP_VERIFICATION stage steps
    OTP_SENT = "OTP_SENT"
    OTP_RETRY = "OTP_RETRY"
    OTP_COMPLETE = "OTP_COMPLETE"
    
    # Phase 4: KYC_VERIFICATION stage steps
    # PAN verification comes FIRST, then Aadhaar
    KYC_ASK_PAN = "KYC_ASK_PAN"              # Ask user for PAN number
    KYC_PAN_VERIFYING = "KYC_PAN_VERIFYING"  # "Verifying PAN details..."
    KYC_PAN_VERIFIED = "KYC_PAN_VERIFIED"    # PAN verification successful
    KYC_PAN_FAILED = "KYC_PAN_FAILED"        # PAN verification failed
    KYC_ASK_AADHAAR = "KYC_ASK_AADHAAR"      # Ask user for Aadhaar number
    KYC_AADHAAR_VERIFYING = "KYC_AADHAAR_VERIFYING"  # "Verifying Aadhaar details..."
    KYC_AADHAAR_VERIFIED = "KYC_AADHAAR_VERIFIED"    # Aadhaar verification successful
    KYC_AADHAAR_FAILED = "KYC_AADHAAR_FAILED"        # Aadhaar verification failed
    KYC_VERIFICATION_COMPLETE = "KYC_VERIFICATION_COMPLETE"  # Both verified
    
    # Phase 5: OFFER_DISCOVERY stage steps
    # Deterministic offer lookup and interest rate calculation
    OFFER_LOOKUP_STARTED = "OFFER_LOOKUP_STARTED"    # "Checking your eligibility..."
    OFFER_PREAPPROVED_FOUND = "OFFER_PREAPPROVED_FOUND"  # Pre-approved offer found
    OFFER_NEW_CUSTOMER = "OFFER_NEW_CUSTOMER"        # New customer, no pre-approved
    OFFER_RATE_CALCULATED = "OFFER_RATE_CALCULATED"  # Interest rate range determined
    OFFER_DISCOVERY_COMPLETE = "OFFER_DISCOVERY_COMPLETE"  # Ready for next stage
    
    # Phase 6: INCOME_DOC_UPLOAD stage steps
    # Controlled salary document upload and deterministic income verification
    INCOME_UPLOAD_REQUEST = "INCOME_UPLOAD_REQUEST"      # Ask user to upload salary slip
    INCOME_UPLOAD_RECEIVED = "INCOME_UPLOAD_RECEIVED"    # Document received
    INCOME_VERIFYING = "INCOME_VERIFYING"                # "Verifying income details..."
    INCOME_VERIFIED = "INCOME_VERIFIED"                  # Income verification successful
    INCOME_VERIFICATION_FAILED = "INCOME_VERIFICATION_FAILED"  # Verification failed
    INCOME_RETRY_ALLOWED = "INCOME_RETRY_ALLOWED"        # Retry allowed (once)
    INCOME_VERIFICATION_COMPLETE = "INCOME_VERIFICATION_COMPLETE"  # Ready for underwriting
    
    # Phase 7: UNDERWRITING stage steps
    # Deterministic underwriting decision engine
    UNDERWRITING_STARTED = "UNDERWRITING_STARTED"            # "Processing your application..."
    UNDERWRITING_CREDIT_CHECK = "UNDERWRITING_CREDIT_CHECK"  # Credit score evaluation
    UNDERWRITING_LIMIT_CHECK = "UNDERWRITING_LIMIT_CHECK"    # Loan amount vs limit check
    UNDERWRITING_EMI_CHECK = "UNDERWRITING_EMI_CHECK"        # EMI affordability check
    UNDERWRITING_APPROVED = "UNDERWRITING_APPROVED"          # Loan approved
    UNDERWRITING_REJECTED = "UNDERWRITING_REJECTED"          # Loan rejected
    UNDERWRITING_COMPLETE = "UNDERWRITING_COMPLETE"          # Decision finalized
    
    # Later stages (simpler flow) - legacy, kept for compatibility
    KYC_VERIFYING = "KYC_VERIFYING"
    OFFER_CHECKING = "OFFER_CHECKING"  # DEPRECATED: Use OFFER_LOOKUP_STARTED
    DOC_UPLOAD_WAITING = "DOC_UPLOAD_WAITING"  # DEPRECATED: Use INCOME_UPLOAD_REQUEST
    UNDERWRITING_PROCESSING = "UNDERWRITING_PROCESSING"  # DEPRECATED: Use UNDERWRITING_STARTED
    SANCTION_COMPLETE = "SANCTION_COMPLETE"
    REJECTION_COMPLETE = "REJECTION_COMPLETE"
    
    # Phase 8: SANCTION stage steps
    # WHY SANCTION IS A TERMINAL STAGE:
    #   Once a loan is sanctioned, the journey ends cleanly.
    #   The sanction letter is a legally binding document.
    #   No further stage changes are allowed.
    SANCTION_ENTRY_VALIDATION = "SANCTION_ENTRY_VALIDATION"  # Validate entry conditions
    SANCTION_LETTER_GENERATING = "SANCTION_LETTER_GENERATING"  # "Generating sanction letter..."
    SANCTION_LETTER_READY = "SANCTION_LETTER_READY"  # Letter ready for download
    SANCTION_JOURNEY_COMPLETE = "SANCTION_JOURNEY_COMPLETE"  # Final closure message
    
    # Phase 8: REJECTION stage steps
    # WHY REJECTION MUST BE FINAL:
    #   Clear, honest communication builds trust.
    #   Single clear reason (no list of issues).
    #   No upselling or workaround suggestions.
    REJECTION_ENTRY_VALIDATION = "REJECTION_ENTRY_VALIDATION"  # Validate entry conditions
    REJECTION_PROCESSING = "REJECTION_PROCESSING"  # Processing rejection
    REJECTION_FINAL_MESSAGE = "REJECTION_FINAL_MESSAGE"  # Final rejection message
    REJECTION_JOURNEY_COMPLETE = "REJECTION_JOURNEY_COMPLETE"  # Journey ends


# ================================================================================
# STAGE QUESTION SEQUENCES
# ================================================================================
# Defines the EXACT order of questions for each stage.
# The chatbot MUST follow this sequence without skipping.

STAGE_QUESTION_SEQUENCE: Dict[str, List[ConversationStep]] = {
    "GREETING": [
        ConversationStep.GREETING_WELCOME,
        ConversationStep.GREETING_COMPLETE,
    ],
    
    "NEEDS_DISCOVERY": [
        ConversationStep.NEEDS_ASK_PURPOSE,     # First: Ask purpose
        ConversationStep.NEEDS_ASK_AMOUNT,      # Then: Ask amount
        ConversationStep.NEEDS_CONFIRM,         # Finally: Confirm
        ConversationStep.NEEDS_COMPLETE,
    ],
    
    "BASIC_ELIGIBILITY": [
        ConversationStep.ELIGIBILITY_ASK_CITY,      # First: Location
        ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT, # Then: Employment
        ConversationStep.ELIGIBILITY_CONFIRM,        # Confirm eligibility
        ConversationStep.ELIGIBILITY_COMPLETE,
    ],
    
    "KYC_COLLECTION": [
        ConversationStep.KYC_ASK_NAME,      # First: Name
        ConversationStep.KYC_ASK_MOBILE,    # Then: Mobile
        ConversationStep.KYC_COMPLETE,
    ],
    
    "OTP_VERIFICATION": [
        ConversationStep.OTP_SENT,
        ConversationStep.OTP_RETRY,
        ConversationStep.OTP_COMPLETE,
    ],
    
    # Phase 4: KYC_VERIFICATION with strict PAN → Aadhaar sequence
    # Entry condition: otp_verified == true
    # Must collect PAN FIRST, verify it, THEN collect Aadhaar
    "KYC_VERIFICATION": [
        ConversationStep.KYC_ASK_PAN,           # Step 1: Request PAN
        ConversationStep.KYC_PAN_VERIFYING,     # Step 2: Show verifying message
        ConversationStep.KYC_PAN_VERIFIED,      # Step 3: Confirm PAN success
        ConversationStep.KYC_ASK_AADHAAR,       # Step 4: Request Aadhaar
        ConversationStep.KYC_AADHAAR_VERIFYING, # Step 5: Show verifying message
        ConversationStep.KYC_AADHAAR_VERIFIED,  # Step 6: Confirm Aadhaar success
        ConversationStep.KYC_VERIFICATION_COMPLETE,  # Step 7: Both verified
    ],
    
    # Phase 5: OFFER_DISCOVERY with deterministic offer lookup
    # Entry conditions: kyc_status == VERIFIED, pan_verified, aadhaar_verified
    # LLM presents rates as INDICATIVE, not final
    "OFFER_DISCOVERY": [
        ConversationStep.OFFER_LOOKUP_STARTED,   # Step 1: Show checking message
        ConversationStep.OFFER_RATE_CALCULATED,  # Step 2: Show rate range
        ConversationStep.OFFER_DISCOVERY_COMPLETE,  # Step 3: Ready for next stage
    ],
    
    # Phase 6: INCOME_DOC_UPLOAD with controlled salary document upload
    # Entry conditions: kyc_status == VERIFIED, interest_rate_min/max exist, loan_amount known
    # Upload button visible ONLY in this stage, disappears after success
    "INCOME_DOC_UPLOAD": [
        ConversationStep.INCOME_UPLOAD_REQUEST,    # Step 1: Request salary slip
        ConversationStep.INCOME_VERIFYING,         # Step 2: Show verifying message
        ConversationStep.INCOME_VERIFIED,          # Step 3: Verification successful
        ConversationStep.INCOME_VERIFICATION_COMPLETE,  # Step 4: Ready for underwriting
    ],
    
    # Phase 7: UNDERWRITING with deterministic decision engine
    # Entry conditions: income_verified == True, credit_score exists, loan_amount exists
    # Decision runs exactly ONCE and is FINAL (no re-underwriting)
    # LLM may explain but CANNOT change the decision
    "UNDERWRITING": [
        ConversationStep.UNDERWRITING_STARTED,     # Step 1: Processing started
        ConversationStep.UNDERWRITING_CREDIT_CHECK,  # Step 2: Credit evaluation
        ConversationStep.UNDERWRITING_EMI_CHECK,   # Step 3: EMI affordability
        ConversationStep.UNDERWRITING_APPROVED,    # Step 4a: If approved
        ConversationStep.UNDERWRITING_REJECTED,    # Step 4b: If rejected
        ConversationStep.UNDERWRITING_COMPLETE,    # Step 5: Decision finalized
    ],
    
    # Phase 8: SANCTION stage with sanction letter generation
    # Entry conditions: loan_status == APPROVED, underwriting_timestamp exists
    # Terminal stage - no further transitions allowed
    "SANCTION": [
        ConversationStep.SANCTION_ENTRY_VALIDATION,   # Step 1: Validate entry
        ConversationStep.SANCTION_LETTER_GENERATING,  # Step 2: Generate letter
        ConversationStep.SANCTION_LETTER_READY,       # Step 3: Letter ready
        ConversationStep.SANCTION_JOURNEY_COMPLETE,   # Step 4: Journey ends
    ],
    
    # Phase 8: REJECTION stage with clear final message
    # Entry conditions: loan_status == REJECTED, rejection_reason exists
    # Terminal stage - no further transitions allowed
    "REJECTION": [
        ConversationStep.REJECTION_ENTRY_VALIDATION,  # Step 1: Validate entry
        ConversationStep.REJECTION_PROCESSING,        # Step 2: Process rejection
        ConversationStep.REJECTION_FINAL_MESSAGE,     # Step 3: Final message
        ConversationStep.REJECTION_JOURNEY_COMPLETE,  # Step 4: Journey ends
    ],
}


# ================================================================================
# CONVERSATION PROMPTS
# ================================================================================
# Natural, human-like prompts for each conversation step.
# Multiple variants for variety (randomly selected).

@dataclass
class ConversationPrompt:
    """A single conversation prompt with variants."""
    primary: str
    variants: List[str]
    tone: str  # friendly, professional, reassuring, celebratory
    can_skip_if: Optional[str] = None  # Data field that, if present, skips this step


CONVERSATION_PROMPTS: Dict[ConversationStep, ConversationPrompt] = {
    # =========================================================================
    # GREETING STAGE
    # =========================================================================
    ConversationStep.GREETING_WELCOME: ConversationPrompt(
        primary="Hi! Welcome to Tata Capital. I'm here to help you with a personal loan — it only takes a few minutes.",
        variants=[
            "Hello! Welcome to Tata Capital. I can help you get a personal loan today, and it's quite quick.",
            "Hi there! Thanks for reaching out to Tata Capital. Looking for a personal loan? I'm here to help.",
            "Welcome to Tata Capital! I'm your loan assistant. Let me help you explore your personal loan options.",
        ],
        tone="friendly",
    ),
    
    # =========================================================================
    # NEEDS_DISCOVERY STAGE
    # =========================================================================
    ConversationStep.NEEDS_ASK_PURPOSE: ConversationPrompt(
        primary="May I know what you're planning to use the loan for?",
        variants=[
            "What would you like to use this loan for?",
            "Could you share what the loan would be for?",
            "What's the purpose you have in mind for this loan?",
        ],
        tone="consultative",
        can_skip_if="loan_purpose",
    ),
    
    ConversationStep.NEEDS_ASK_AMOUNT: ConversationPrompt(
        primary="And roughly how much are you considering?",
        variants=[
            "What amount are you thinking of?",
            "How much would you need, approximately?",
            "What's the approximate amount you're looking at?",
        ],
        tone="consultative",
        can_skip_if="loan_amount",
    ),
    
    ConversationStep.NEEDS_CONFIRM: ConversationPrompt(
        primary="Got it! So you're looking at around {loan_amount} for {loan_purpose}. Let me check what options we have for you.",
        variants=[
            "Understood — {loan_amount} for {loan_purpose}. Let me see what we can offer.",
            "Perfect. {loan_amount} for {loan_purpose}. I'll check our best options for you.",
        ],
        tone="professional",
    ),
    
    # =========================================================================
    # BASIC_ELIGIBILITY STAGE
    # =========================================================================
    ConversationStep.ELIGIBILITY_ASK_CITY: ConversationPrompt(
        primary="Which city do you currently live in?",
        variants=[
            "What city are you based in?",
            "May I know which city you reside in?",
            "Where are you located currently?",
        ],
        tone="professional",
        can_skip_if="city",
    ),
    
    ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT: ConversationPrompt(
        primary="Are you salaried or self-employed?",
        variants=[
            "And are you employed with a company, or do you run your own business?",
            "Is this for salaried income or self-employment?",
            "Would you be salaried or self-employed?",
        ],
        tone="professional",
        can_skip_if="employment_type",
    ),
    
    ConversationStep.ELIGIBILITY_CONFIRM: ConversationPrompt(
        primary="Great — based on what you've shared, you should be eligible for a personal loan. Let me now verify your identity.",
        variants=[
            "Thanks! You seem to meet our basic criteria. Let's proceed to verify your details.",
            "Perfect. You look eligible. Now I just need to verify your identity to proceed.",
        ],
        tone="reassuring",
    ),
    
    # =========================================================================
    # KYC_COLLECTION STAGE
    # =========================================================================
    ConversationStep.KYC_ASK_NAME: ConversationPrompt(
        primary="Could you please share your full name as it appears on your ID?",
        variants=[
            "What is your full name, as per your official documents?",
            "May I have your full name please?",
        ],
        tone="professional",
        can_skip_if="user_name",
    ),
    
    ConversationStep.KYC_ASK_MOBILE: ConversationPrompt(
        primary="And your 10-digit mobile number for verification?",
        variants=[
            "What's your mobile number? I'll send an OTP to verify.",
            "Please share your mobile number — I'll verify it with an OTP.",
            "And your mobile number for a quick OTP verification?",
        ],
        tone="professional",
        can_skip_if="user_mobile",
    ),
    
    # =========================================================================
    # OTP_VERIFICATION STAGE
    # =========================================================================
    ConversationStep.OTP_SENT: ConversationPrompt(
        primary="I've sent a 6-digit OTP to your mobile number ending in {mobile_last4}. Please enter it here.",
        variants=[
            "An OTP has been sent to ******{mobile_last4}. Please enter the code.",
            "Check your phone — I've sent an OTP to {mobile_last4}. Share it here to continue.",
        ],
        tone="professional",
    ),
    
    ConversationStep.OTP_RETRY: ConversationPrompt(
        primary="That doesn't seem right. Could you please re-enter the OTP? You have {attempts_left} attempts remaining.",
        variants=[
            "Hmm, that OTP didn't match. Please try again — {attempts_left} attempts left.",
            "That wasn't correct. Check your SMS and enter the 6-digit code again. {attempts_left} attempts remaining.",
        ],
        tone="reassuring",
    ),
    
    # =========================================================================
    # PHASE 4: KYC_VERIFICATION STAGE - PAN and Aadhaar Verification
    # =========================================================================
    # Step 1: Request PAN number from user
    ConversationStep.KYC_ASK_PAN: ConversationPrompt(
        primary="Great, {user_name}! Your mobile has been verified. Now let's verify your identity. Please provide your PAN number.",
        variants=[
            "Perfect, {user_name}! Mobile verified. Now I need your PAN number for identity verification.",
            "Thanks {user_name}, mobile is verified! To proceed, please share your PAN number.",
            "Excellent! Now let's verify your identity. Could you please provide your 10-character PAN number?",
        ],
        tone="professional",
    ),
    
    # Step 2: Show PAN verification in progress
    ConversationStep.KYC_PAN_VERIFYING: ConversationPrompt(
        primary="Verifying your PAN details with government records... This may take a few seconds.",
        variants=[
            "Checking PAN details with the Income Tax database...",
            "Verifying your PAN number... Please wait a moment.",
            "Running PAN verification through our secure systems...",
        ],
        tone="professional",
    ),
    
    # Step 3: PAN verification successful
    ConversationStep.KYC_PAN_VERIFIED: ConversationPrompt(
        primary="✓ PAN verified successfully! Your PAN {pan_number} is linked to {user_name}.",
        variants=[
            "Great! PAN verification complete. {pan_number} is valid and matches your details.",
            "✓ PAN confirmed! We've verified {pan_number} against government records.",
        ],
        tone="reassuring",
    ),
    
    # Step 3 (alternate): PAN verification failed
    ConversationStep.KYC_PAN_FAILED: ConversationPrompt(
        primary="Sorry, we couldn't verify the PAN number you provided. {failure_reason}",
        variants=[
            "Unfortunately, PAN verification failed. {failure_reason}",
            "We're unable to verify this PAN number. {failure_reason}",
        ],
        tone="empathetic",
    ),
    
    # Step 4: Request Aadhaar number (only after PAN is verified)
    ConversationStep.KYC_ASK_AADHAAR: ConversationPrompt(
        primary="Now, please provide your 12-digit Aadhaar number for final identity verification.",
        variants=[
            "Almost done! Please share your 12-digit Aadhaar number.",
            "One more step — please enter your Aadhaar number.",
            "For the final verification, I need your 12-digit Aadhaar number.",
        ],
        tone="professional",
    ),
    
    # Step 5: Show Aadhaar verification in progress
    ConversationStep.KYC_AADHAAR_VERIFYING: ConversationPrompt(
        primary="Verifying your Aadhaar details with UIDAI... This may take a few seconds.",
        variants=[
            "Checking Aadhaar details with UIDAI database...",
            "Verifying your Aadhaar number... Please wait a moment.",
            "Running Aadhaar verification through secure UIDAI systems...",
        ],
        tone="professional",
    ),
    
    # Step 6: Aadhaar verification successful
    ConversationStep.KYC_AADHAAR_VERIFIED: ConversationPrompt(
        primary="✓ Aadhaar verified successfully! Your identity has been confirmed.",
        variants=[
            "Great! Aadhaar verification complete. Your identity is confirmed.",
            "✓ Aadhaar confirmed! We've verified your details with UIDAI.",
        ],
        tone="reassuring",
    ),
    
    # Step 6 (alternate): Aadhaar verification failed
    ConversationStep.KYC_AADHAAR_FAILED: ConversationPrompt(
        primary="Sorry, we couldn't verify the Aadhaar number you provided. {failure_reason}",
        variants=[
            "Unfortunately, Aadhaar verification failed. {failure_reason}",
            "We're unable to verify this Aadhaar number. {failure_reason}",
        ],
        tone="empathetic",
    ),
    
    # Step 7: Both PAN and Aadhaar verified
    ConversationStep.KYC_VERIFICATION_COMPLETE: ConversationPrompt(
        primary="🎉 Identity verification complete! Both your PAN and Aadhaar have been verified. Let me check your loan eligibility...",
        variants=[
            "Perfect! Your identity is fully verified. Now let me see what loan offers are available for you...",
            "✓ KYC complete! PAN and Aadhaar verified. Checking your eligible loan offers...",
        ],
        tone="celebratory",
    ),
    
    # =========================================================================
    # KYC_VERIFICATION STAGE (Legacy - kept for compatibility)
    # =========================================================================
    ConversationStep.KYC_VERIFYING: ConversationPrompt(
        primary="Thank you, {user_name}! I'm now verifying your details with our records...",
        variants=[
            "Got it, {user_name}. Just a moment while I verify your information.",
            "Thanks {user_name}! Verifying your identity now...",
        ],
        tone="professional",
    ),
    
    # =========================================================================
    # OFFER_DISCOVERY STAGE (Phase 5)
    # Entry conditions: kyc_status == VERIFIED, pan_verified, aadhaar_verified
    # LLM must present rates as INDICATIVE, not final
    # =========================================================================
    
    # Step 1: Show checking message
    ConversationStep.OFFER_LOOKUP_STARTED: ConversationPrompt(
        primary="Excellent! Your KYC is complete. Let me check our offers and calculate an indicative interest rate for you...",
        variants=[
            "Perfect! Now that your identity is verified, let me see what loan options are available for you...",
            "Great! Verification complete. I'm checking your credit profile for eligible offers...",
        ],
        tone="professional",
    ),
    
    # Step 1a: Found pre-approved offer
    ConversationStep.OFFER_PREAPPROVED_FOUND: ConversationPrompt(
        primary="Great news! You have a pre-approved offer with us up to ₹{preapproved_limit}! Let me finalize the indicative interest rate based on your profile...",
        variants=[
            "Wonderful! I found a pre-approved loan offer for you up to ₹{preapproved_limit}. Calculating your personalized rate...",
            "Excellent news! You're pre-approved for up to ₹{preapproved_limit}. Let me determine your indicative rate...",
        ],
        tone="celebratory",
    ),
    
    # Step 1b: New customer (no pre-approved offer)
    ConversationStep.OFFER_NEW_CUSTOMER: ConversationPrompt(
        primary="I'm checking your credit profile to determine your eligible loan amount and indicative interest rate...",
        variants=[
            "Let me review your credit information to provide you with the best available offers...",
            "I'm calculating your loan eligibility based on your credit profile...",
        ],
        tone="professional",
    ),
    
    # Step 2: Rate range calculated
    ConversationStep.OFFER_RATE_CALCULATED: ConversationPrompt(
        primary="Based on your credit profile, your **indicative interest rate** is **{rate_min}% - {rate_max}% p.a.** This is a preliminary estimate — the final rate will be confirmed after income verification and underwriting.",
        variants=[
            "Your indicative interest rate is **{rate_min}% to {rate_max}% per annum** based on your credit score. Please note this is preliminary and may change after full assessment.",
            "I've calculated an indicative rate of **{rate_min}% - {rate_max}% p.a.** for you. The final rate will depend on income verification and underwriting review.",
        ],
        tone="professional",
    ),
    
    # Step 3: Ready for next stage (INCOME_DOC_UPLOAD)
    ConversationStep.OFFER_DISCOVERY_COMPLETE: ConversationPrompt(
        primary="To proceed with your loan application, please upload your income documents. This will help finalize your offer and interest rate.",
        variants=[
            "Great! To confirm your eligibility and lock in your rate, please upload your income proof.",
            "Now let's verify your income to finalize your loan terms. Please upload your salary slip or bank statement.",
        ],
        tone="professional",
    ),
    
    # Legacy compatibility
    ConversationStep.OFFER_CHECKING: ConversationPrompt(
        primary="Great news! You're verified. Let me check what loan offers are available for you...",
        variants=[
            "Verification complete! Now checking your eligible offers...",
            "All verified. Let me see what we can offer you...",
        ],
        tone="friendly",
    ),
    
    # =========================================================================
    # INCOME_DOC_UPLOAD STAGE (Phase 6)
    # Entry conditions: kyc_status == VERIFIED, interest rates exist, loan amount known
    # Upload button visible ONLY in this stage, disappears after success
    # =========================================================================
    
    # Legacy prompt (kept for compatibility)
    ConversationStep.DOC_UPLOAD_WAITING: ConversationPrompt(
        primary="To finalize your loan, I'll need your income proof. Please upload your latest salary slip or bank statement using the button below.",
        variants=[
            "Almost there! Please upload your salary slip or income proof to proceed.",
            "Just one more step — upload your income document (salary slip or bank statement) to continue.",
        ],
        tone="professional",
    ),
    
    # Step 1: Request salary slip upload
    ConversationStep.INCOME_UPLOAD_REQUEST: ConversationPrompt(
        primary="Please upload your latest salary slip to continue with your loan application. I accept PDF, JPG, or PNG files.",
        variants=[
            "To verify your income, please upload your recent salary slip (PDF, JPG, or PNG).",
            "Almost there! Please upload your latest salary slip to proceed. Accepted formats: PDF, JPG, PNG.",
        ],
        tone="professional",
    ),
    
    # Step 2: Document received, verifying
    ConversationStep.INCOME_UPLOAD_RECEIVED: ConversationPrompt(
        primary="Thank you! I've received your document. Let me verify the details...",
        variants=[
            "Got it! Processing your salary slip now...",
            "Document received! Verifying your income details...",
        ],
        tone="professional",
    ),
    
    # Step 3: Verifying income
    ConversationStep.INCOME_VERIFYING: ConversationPrompt(
        primary="Verifying income details... This will just take a moment.",
        variants=[
            "Processing your salary slip... Please wait.",
            "Extracting income information from your document...",
        ],
        tone="professional",
    ),
    
    # Step 4: Income verification successful
    ConversationStep.INCOME_VERIFIED: ConversationPrompt(
        primary="✓ Income verified successfully! Your monthly salary of {salary_amount} has been confirmed.",
        variants=[
            "Great! Your income of {salary_amount}/month has been verified.",
            "✓ Salary verification complete! Monthly income: {salary_amount}.",
        ],
        tone="reassuring",
    ),
    
    # Step 4 (alternate): Verification failed
    ConversationStep.INCOME_VERIFICATION_FAILED: ConversationPrompt(
        primary="Sorry, I couldn't verify your income from the uploaded document. {error_message}",
        variants=[
            "Unfortunately, the salary slip couldn't be processed. {error_message}",
            "I wasn't able to extract salary information from your document. {error_message}",
        ],
        tone="empathetic",
    ),
    
    # Step 5: Retry allowed
    ConversationStep.INCOME_RETRY_ALLOWED: ConversationPrompt(
        primary="You can try uploading a different document. Please ensure it's clearly readable.",
        variants=[
            "Would you like to try with a different salary slip?",
            "Please upload a clearer copy of your salary slip to proceed.",
        ],
        tone="helpful",
    ),
    
    # Step 6: Income verification complete, ready for underwriting
    ConversationStep.INCOME_VERIFICATION_COMPLETE: ConversationPrompt(
        primary="Income verification complete! Now let me process your loan application...",
        variants=[
            "Perfect! All verifications are done. Processing your application now...",
            "Great! Your income is verified. Moving to final assessment...",
        ],
        tone="professional",
    ),
    
    # =========================================================================
    # PHASE 7: UNDERWRITING STAGE
    # =========================================================================
    # WHY THESE PROMPTS EXIST:
    #   LLM may use these to EXPLAIN the decision, but CANNOT CHANGE it.
    #   The decision is made by deterministic backend logic, not LLM.
    # =========================================================================
    
    # Step 1: Underwriting process started
    ConversationStep.UNDERWRITING_STARTED: ConversationPrompt(
        primary="Your application is now being evaluated by our underwriting system. This will just take a moment...",
        variants=[
            "Processing your loan application through our assessment system...",
            "Evaluating your application based on our lending criteria...",
        ],
        tone="professional",
    ),
    
    # Step 2: Credit score evaluation (LLM explaining, not deciding)
    ConversationStep.UNDERWRITING_CREDIT_CHECK: ConversationPrompt(
        primary="Checking your credit profile against our lending criteria...",
        variants=[
            "Evaluating your credit score and history...",
            "Reviewing your credit standing...",
        ],
        tone="professional",
    ),
    
    # Step 3: Loan amount vs limit check
    ConversationStep.UNDERWRITING_LIMIT_CHECK: ConversationPrompt(
        primary="Verifying the requested loan amount against your approved limits...",
        variants=[
            "Checking your loan eligibility based on your profile...",
            "Confirming the loan amount is within approved parameters...",
        ],
        tone="professional",
    ),
    
    # Step 4: EMI affordability check
    ConversationStep.UNDERWRITING_EMI_CHECK: ConversationPrompt(
        primary="Calculating EMI affordability based on your verified income...",
        variants=[
            "Assessing monthly payment capacity based on your income...",
            "Evaluating debt-to-income ratio for affordability...",
        ],
        tone="professional",
    ),
    
    # Step 5: Loan APPROVED (LLM explains, decision already made)
    ConversationStep.UNDERWRITING_APPROVED: ConversationPrompt(
        primary="🎉 Great news, {user_name}! Your loan application has been **APPROVED**!\n\n**Loan Amount:** {loan_amount}\n**Monthly EMI:** ₹{calculated_emi:,.2f}\n**Debt-to-Income Ratio:** {foir}%\n\nYour application met all our lending criteria. Moving to sanction...",
        variants=[
            "Congratulations, {user_name}! Your loan of {loan_amount} is **APPROVED**! Your monthly EMI will be ₹{calculated_emi:,.2f}. Proceeding to generate your sanction letter...",
        ],
        tone="celebratory",
    ),
    
    # Step 6: Loan REJECTED (LLM explains, decision already made)
    ConversationStep.UNDERWRITING_REJECTED: ConversationPrompt(
        primary="I'm sorry, {user_name}, but your loan application could not be approved at this time.\n\n**Reason:** {rejection_reason}\n\nThis decision is based on our standard lending criteria. You may consider reapplying after addressing the above concern.",
        variants=[
            "Unfortunately, {user_name}, we're unable to approve your application. {rejection_reason}. We encourage you to review this and consider reapplying in the future.",
        ],
        tone="empathetic",
    ),
    
    # Step 7: Underwriting complete (decision finalized)
    ConversationStep.UNDERWRITING_COMPLETE: ConversationPrompt(
        primary="Your loan assessment is complete. The decision has been recorded.",
        variants=[
            "Assessment finalized. The outcome has been saved to your application.",
        ],
        tone="professional",
    ),
    
    # Legacy prompt (kept for compatibility)
    ConversationStep.UNDERWRITING_PROCESSING: ConversationPrompt(
        primary="I've received your documents. Give me a moment to process your application...",
        variants=[
            "Documents received! Processing your loan application now...",
            "Thanks! I'm reviewing your application. This will just take a moment.",
        ],
        tone="professional",
    ),
    
    # =========================================================================
    # SANCTION STAGE
    # =========================================================================
    ConversationStep.SANCTION_COMPLETE: ConversationPrompt(
        primary="🎉 Congratulations, {user_name}! Your loan of {loan_amount} has been approved! You can download your sanction letter below.",
        variants=[
            "Wonderful news, {user_name}! Your loan for {loan_amount} is approved! Download your sanction letter now.",
            "🎊 Great news! {user_name}, your {loan_amount} loan is sanctioned. Your sanction letter is ready for download.",
        ],
        tone="celebratory",
    ),
    
    # =========================================================================
    # REJECTION STAGE
    # =========================================================================
    ConversationStep.REJECTION_COMPLETE: ConversationPrompt(
        primary="I'm sorry, {user_name}, but we're unable to approve your loan application at this time. {rejection_reason}",
        variants=[
            "Unfortunately, {user_name}, we cannot proceed with your application right now. {rejection_reason}",
        ],
        tone="empathetic",
    ),
    
    # =========================================================================
    # PHASE 8: SANCTION STAGE - JOURNEY CLOSURE (APPROVED)
    # =========================================================================
    # WHY SANCTION IS A TERMINAL STAGE:
    #   Once a loan is sanctioned, the journey ends cleanly.
    #   The sanction letter is a legally binding document.
    #   No further modifications are allowed to the loan terms.
    #   Customer receives downloadable sanction letter.
    #
    # LLM COMMUNICATION RULES:
    #   - LLM may congratulate and explain outcome
    #   - LLM must NOT offer negotiation or changes
    #   - LLM must NOT mention internal rules or formulas
    #   - LLM must NOT suggest manual override
    # =========================================================================
    
    # Step 1: Entry validation (internal, not shown to user)
    ConversationStep.SANCTION_ENTRY_VALIDATION: ConversationPrompt(
        primary="Validating sanction entry conditions...",
        variants=[],
        tone="professional",
    ),
    
    # Step 2: Generating sanction letter
    ConversationStep.SANCTION_LETTER_GENERATING: ConversationPrompt(
        primary="Your loan has been approved! Generating your sanction letter now...",
        variants=[
            "Congratulations! Preparing your sanction letter document...",
            "Great news! Creating your personalized sanction letter...",
        ],
        tone="celebratory",
    ),
    
    # Step 3: Sanction letter ready for download
    ConversationStep.SANCTION_LETTER_READY: ConversationPrompt(
        primary="🎉 Congratulations, {user_name}! Your personal loan has been approved.\n\n**Loan Amount:** {loan_amount}\n**Reference:** {sanction_reference}\n\nYou can download your sanction letter below.",
        variants=[
            "🎊 Wonderful news, {user_name}! Your loan of {loan_amount} is sanctioned!\n\n**Reference:** {sanction_reference}\n\nDownload your sanction letter using the button below.",
        ],
        tone="celebratory",
    ),
    
    # Step 4: Journey complete message
    ConversationStep.SANCTION_JOURNEY_COMPLETE: ConversationPrompt(
        primary="Thank you for choosing Aurora Finance! Please review your sanction letter carefully. Our team will contact you regarding disbursement.\n\nIf you have any questions, please call our helpline at 1800-123-4567.",
        variants=[
            "Thank you for banking with Aurora Finance! Please keep your sanction letter safe. You'll hear from us soon about disbursement.\n\nHelpline: 1800-123-4567",
        ],
        tone="professional",
    ),
    
    # =========================================================================
    # PHASE 8: REJECTION STAGE - JOURNEY CLOSURE (REJECTED)
    # =========================================================================
    # WHY REJECTION MUST BE FINAL:
    #   Clear, honest communication builds trust.
    #   Single clear reason (not a list of issues).
    #   No upselling or workaround suggestions.
    #   Professional closure maintains brand reputation.
    #
    # LLM COMMUNICATION RULES:
    #   - LLM may empathize with the customer
    #   - LLM must provide ONLY ONE clear reason
    #   - LLM must NOT upsell other products
    #   - LLM must NOT suggest workarounds
    #   - LLM must end the journey respectfully
    # =========================================================================
    
    # Step 1: Entry validation (internal, not shown to user)
    ConversationStep.REJECTION_ENTRY_VALIDATION: ConversationPrompt(
        primary="Processing rejection outcome...",
        variants=[],
        tone="professional",
    ),
    
    # Step 2: Processing rejection
    ConversationStep.REJECTION_PROCESSING: ConversationPrompt(
        primary="Processing your application outcome...",
        variants=[],
        tone="professional",
    ),
    
    # Step 3: Final rejection message (single clear reason, no upselling)
    ConversationStep.REJECTION_FINAL_MESSAGE: ConversationPrompt(
        primary="Thank you for your application. Based on our evaluation, we're unable to proceed due to eligibility criteria. You're welcome to apply again in the future.",
        variants=[
            "We appreciate your interest in Aurora Finance. Unfortunately, we're unable to approve your application at this time due to our lending criteria. You're welcome to reapply in the future.",
        ],
        tone="empathetic",
    ),
    
    # Step 4: Journey complete message
    ConversationStep.REJECTION_JOURNEY_COMPLETE: ConversationPrompt(
        primary="We wish you the best. If you have any questions, please call our helpline at 1800-123-4567.",
        variants=[
            "Thank you for considering Aurora Finance. For any queries, please contact us at 1800-123-4567.",
        ],
        tone="professional",
    ),
}


# ================================================================================
# REDIRECT PROMPTS (For irrelevant/off-topic responses)
# ================================================================================

REDIRECT_PROMPTS: Dict[str, List[str]] = {
    "GREETING": [
        "I appreciate the chat! Now, are you looking for a personal loan today?",
        "Happy to help! Would you like to explore a personal loan?",
    ],
    "NEEDS_DISCOVERY": [
        "I'd love to help, but first — what would you like to use the loan for?",
        "Let me understand your needs better. What's the loan purpose?",
    ],
    "BASIC_ELIGIBILITY": [
        "I just need a bit more info. Which city do you live in?",
        "To proceed, could you share which city you're based in?",
    ],
    "KYC_COLLECTION": [
        "To continue, I'll need your details. Could you share your full name?",
        "Let me just get your details. What's your full name?",
    ],
    "OTP_VERIFICATION": [
        "Please enter the 6-digit OTP sent to your mobile number.",
        "I need the OTP to verify your number. Please check your SMS.",
    ],
}


# ================================================================================
# LOAN PURPOSE EXTRACTION
# ================================================================================

LOAN_PURPOSE_KEYWORDS: Dict[str, List[str]] = {
    "home_renovation": ["renovation", "renovate", "home improvement", "repair", "remodel", "interior", "painting"],
    "medical": ["medical", "hospital", "surgery", "treatment", "health", "doctor"],
    "education": ["education", "studies", "tuition", "college", "university", "course", "school"],
    "wedding": ["wedding", "marriage", "shaadi"],
    "travel": ["travel", "trip", "vacation", "holiday", "tour"],
    "debt_consolidation": ["debt", "credit card", "consolidate", "pay off", "clear dues"],
    "business": ["business", "shop", "startup", "inventory", "equipment"],
    "vehicle": ["car", "bike", "vehicle", "scooter", "motorcycle"],
    "emergency": ["emergency", "urgent", "immediate"],
    "personal": ["personal", "general", "various"],
}


def extract_loan_purpose(message: str) -> Optional[str]:
    """
    Extract loan purpose from user message.
    
    Returns a standardized purpose category or None if not a valid purpose.
    """
    message_lower = message.lower().strip()
    
    # Filter out common irrelevant patterns
    irrelevant_patterns = [
        'haha', 'lol', 'hmm', 'umm', 'ok', 'okay', 'yes', 'no', 'hi', 'hello',
        'what', 'how', 'why', 'when', 'where', 'who', 'proceed', 'continue',
        'thanks', 'thank', 'sure', 'good', 'great', 'nice'
    ]
    
    # If message is mostly irrelevant, return None
    words = message_lower.split()
    if all(word in irrelevant_patterns or len(word) < 3 for word in words):
        return None
    
    for category, keywords in LOAN_PURPOSE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in message_lower:
                return category.replace("_", " ").title()
    
    # If message looks like a purpose (contains "for", describes something, etc.)
    purpose_indicators = ['for', 'need', 'want', 'require', 'get', 'buy', 'pay']
    has_purpose_indicator = any(ind in message_lower for ind in purpose_indicators)
    
    # Only accept as purpose if it has an indicator and is substantial
    if has_purpose_indicator and len(message) > 5:
        return message.strip()
    
    return None


def extract_city(message: str) -> Optional[str]:
    """
    Extract city name from user message.
    """
    # Major Indian cities
    INDIAN_CITIES = [
        "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "hyderabad",
        "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "kanpur",
        "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "vadodara",
        "ghaziabad", "ludhiana", "coimbatore", "kochi", "patna", "noida",
        "gurugram", "gurgaon", "chandigarh", "surat", "nashik", "faridabad"
    ]
    
    message_lower = message.lower()
    
    for city in INDIAN_CITIES:
        if city in message_lower:
            return city.title()
    
    # Try to extract if it looks like a city name (capitalized word)
    words = message.split()
    for word in words:
        if word[0].isupper() and len(word) > 2 and word.lower() not in ["yes", "no", "the", "and"]:
            return word
    
    return None


def extract_employment_type(message: str) -> Optional[str]:
    """
    Extract employment type from user message.
    """
    message_lower = message.lower()
    
    salaried_keywords = ["salaried", "salary", "employed", "job", "company", "corporate", "work for", "employee"]
    self_employed_keywords = ["self-employed", "self employed", "business", "own business", "freelance", "entrepreneur", "consultant"]
    
    for keyword in salaried_keywords:
        if keyword in message_lower:
            return "Salaried"
    
    for keyword in self_employed_keywords:
        if keyword in message_lower:
            return "Self-Employed"
    
    return None


# ================================================================================
# CONVERSATION STATE TRACKER
# ================================================================================

@dataclass
class ConversationProgress:
    """
    Tracks conversation progress within a stage.
    
    This ensures we don't repeat questions and follow proper sequence.
    """
    current_step: Optional[ConversationStep] = None
    questions_asked: List[str] = None
    questions_answered: List[str] = None
    
    def __post_init__(self):
        if self.questions_asked is None:
            self.questions_asked = []
        if self.questions_answered is None:
            self.questions_answered = []
    
    def mark_asked(self, step: ConversationStep):
        """Mark a question as asked."""
        if step.value not in self.questions_asked:
            self.questions_asked.append(step.value)
        self.current_step = step
    
    def mark_answered(self, step: ConversationStep):
        """Mark a question as answered."""
        if step.value not in self.questions_answered:
            self.questions_answered.append(step.value)
    
    def was_asked(self, step: ConversationStep) -> bool:
        """Check if a question was already asked."""
        return step.value in self.questions_asked
    
    def was_answered(self, step: ConversationStep) -> bool:
        """Check if a question was already answered."""
        return step.value in self.questions_answered
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_step": self.current_step.value if self.current_step else None,
            "questions_asked": self.questions_asked,
            "questions_answered": self.questions_answered,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationProgress":
        step_value = data.get("current_step")
        current_step = ConversationStep(step_value) if step_value else None
        return cls(
            current_step=current_step,
            questions_asked=data.get("questions_asked", []),
            questions_answered=data.get("questions_answered", []),
        )


# ================================================================================
# UTILITY FUNCTIONS
# ================================================================================

def format_currency(amount: float) -> str:
    """Format amount in Indian currency style."""
    if amount >= 10000000:
        return f"₹{amount/10000000:.1f} crore"
    elif amount >= 100000:
        return f"₹{amount/100000:.1f} lakh"
    else:
        return f"₹{amount:,.0f}"


def get_prompt(step: ConversationStep, context: Dict[str, Any] = None) -> str:
    """
    Get a formatted prompt for a conversation step.
    
    Args:
        step: The conversation step
        context: Variables to substitute in the prompt
    
    Returns:
        Formatted prompt string
    """
    import random
    
    prompt_data = CONVERSATION_PROMPTS.get(step)
    if not prompt_data:
        return "How can I help you?"
    
    # Randomly select primary or variant
    all_options = [prompt_data.primary] + prompt_data.variants
    template = random.choice(all_options)
    
    # Format with context
    if context:
        # Prepare formatting values
        format_values = {}
        
        if "loan_amount" in context and context["loan_amount"]:
            format_values["loan_amount"] = format_currency(context["loan_amount"])
        
        if "loan_purpose" in context and context["loan_purpose"]:
            format_values["loan_purpose"] = context["loan_purpose"]
        
        if "user_name" in context and context["user_name"]:
            format_values["user_name"] = context["user_name"]
        
        if "user_mobile" in context and context["user_mobile"]:
            format_values["mobile_last4"] = context["user_mobile"][-4:]
        
        if "otp_attempts" in context:
            format_values["attempts_left"] = 3 - context.get("otp_attempts", 0)
        
        if "rejection_reason" in context and context["rejection_reason"]:
            format_values["rejection_reason"] = context["rejection_reason"]
        
        # Safely format
        try:
            return template.format(**format_values)
        except KeyError:
            return template
    
    return template


def get_redirect_prompt(stage: str) -> str:
    """Get a redirect prompt for off-topic responses."""
    import random
    
    prompts = REDIRECT_PROMPTS.get(stage, ["How can I help you with your loan today?"])
    return random.choice(prompts)


def is_relevant_response(message: str, stage: str, current_step: ConversationStep) -> bool:
    """
    Check if user's response is relevant to the current question.
    
    This helps detect jokes, confusion, or irrelevant text.
    """
    message_lower = message.lower().strip()
    
    # Very short responses that aren't data
    if len(message) < 2:
        return False
    
    # Common irrelevant patterns
    irrelevant_patterns = [
        "haha", "lol", "lmao", "joke", "kidding",
        "what?", "huh?", "???", "...", 
        "i don't know", "idk", "not sure", "maybe",
        "hmm", "umm", "err",
    ]
    
    for pattern in irrelevant_patterns:
        if pattern in message_lower:
            return False
    
    # Stage-specific relevance checks
    if stage == "NEEDS_DISCOVERY":
        if current_step == ConversationStep.NEEDS_ASK_PURPOSE:
            # Should contain purpose-related words or be a substantial response
            return len(message) > 3
        elif current_step == ConversationStep.NEEDS_ASK_AMOUNT:
            # Should contain numbers or amount keywords
            return any(c.isdigit() for c in message) or any(
                kw in message_lower for kw in ["lakh", "lac", "thousand", "crore", "k"]
            )
    
    elif stage == "BASIC_ELIGIBILITY":
        if current_step == ConversationStep.ELIGIBILITY_ASK_CITY:
            # Should be a city name (capitalized or known city)
            return len(message) > 2
        elif current_step == ConversationStep.ELIGIBILITY_ASK_EMPLOYMENT:
            # Should contain employment keywords
            return any(kw in message_lower for kw in [
                "salaried", "salary", "self", "business", "employed", "work", "job", "company"
            ])
    
    elif stage == "KYC_COLLECTION":
        if current_step == ConversationStep.KYC_ASK_NAME:
            # Should be a name (2+ words or single capitalized word)
            return len(message.split()) >= 1 and len(message) > 2
        elif current_step == ConversationStep.KYC_ASK_MOBILE:
            # Should contain 10 digits
            digits = ''.join(c for c in message if c.isdigit())
            return len(digits) >= 10
    
    elif stage == "OTP_VERIFICATION":
        # Should contain 4-6 digits
        digits = ''.join(c for c in message if c.isdigit())
        return 4 <= len(digits) <= 6
    
    # Default: accept if substantial
    return len(message) > 2


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("PHASE 2: CONVERSATION PROMPTS TEST")
    print("=" * 60)
    
    # Test prompt retrieval
    print("\n--- Testing Prompt Retrieval ---")
    
    context = {
        "loan_amount": 500000,
        "loan_purpose": "Home Renovation",
        "user_name": "Rahul Sharma",
        "user_mobile": "9876543210",
    }
    
    test_steps = [
        ConversationStep.GREETING_WELCOME,
        ConversationStep.NEEDS_ASK_PURPOSE,
        ConversationStep.NEEDS_ASK_AMOUNT,
        ConversationStep.NEEDS_CONFIRM,
        ConversationStep.KYC_ASK_MOBILE,
        ConversationStep.SANCTION_COMPLETE,
    ]
    
    for step in test_steps:
        prompt = get_prompt(step, context)
        print(f"\n{step.value}:")
        print(f"  → {prompt}")
    
    # Test purpose extraction
    print("\n--- Testing Purpose Extraction ---")
    
    test_purposes = [
        "I want to renovate my home",
        "need money for wedding",
        "medical emergency",
        "for my daughter's education",
    ]
    
    for text in test_purposes:
        purpose = extract_loan_purpose(text)
        print(f"  '{text}' → {purpose}")
    
    # Test city extraction
    print("\n--- Testing City Extraction ---")
    
    test_cities = [
        "I live in Mumbai",
        "bangalore",
        "from Delhi",
    ]
    
    for text in test_cities:
        city = extract_city(text)
        print(f"  '{text}' → {city}")
    
    print("\n" + "=" * 60)
    print("PHASE 2 PROMPTS TEST COMPLETE")
    print("=" * 60)
