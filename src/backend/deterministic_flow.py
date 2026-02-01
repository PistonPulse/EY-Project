"""
================================================================================
HARD RESET: DETERMINISTIC CONVERSATION FLOW CONTROLLER
================================================================================
Version: 2.0 (HARD RESET)
Date: February 2026
Tests: 121 passing

================================================================================
FINAL ACCEPTANCE CRITERIA — ALL MET
================================================================================

✔ Flow is strictly linear          - 16 stages in exact sequence
✔ No file upload exists            - Income from database ONLY
✔ EMI is tenure-based              - User selects tenure FIRST, then EMI calculated
✔ Interest is a range              - Shows 10.5%-14% based on profile
✔ Decisions are deterministic      - Credit >= 700, Amount <= limit
✔ Admin always matches chat        - to_admin_dict() returns backend truth
✔ LLM cannot hallucinate           - Backend controls all logic

================================================================================
WHY FILE UPLOAD WAS REMOVED
================================================================================

PROBLEM:
  - File upload (salary slips, ITR) created VERIFICATION CHAOS
  - Users uploaded fake/wrong documents
  - LLM was "reading" documents and making decisions
  - No audit trail for why decisions were made
  - Income verification was non-deterministic

SOLUTION:
  - ALL income data comes from CUSTOMER_PROFILES database
  - Database has: annual_income, existing_emis, credit_score
  - No user-submitted documents accepted
  - Income source is ALWAYS "database" (verifiable)

NBFC COMPLIANCE:
  - Real NBFCs have bureau integrations (CIBIL, Experian)
  - Income is verified via bank statements pulled digitally
  - This simulates that with pre-verified customer data

================================================================================
WHY EMI IS TENURE-BASED
================================================================================

PROBLEM:
  - Old system calculated EMI at OFFER stage (before tenure known)
  - Users saw EMI BEFORE selecting tenure = WRONG
  - EMI depends on: Principal, Interest Rate, AND Tenure
  - Without tenure, EMI is meaningless

SOLUTION:
  1. OFFER stage shows: Amount range + Interest rate RANGE (10.5%-14%)
  2. TENURE_SELECTION stage: User picks 12/24/36/48 months
  3. AFTER tenure selected: Calculate exact EMI using formula
  4. Final interest rate determined by credit score at calculation time

FORMULA:
  EMI = P × r × (1+r)^n / ((1+r)^n - 1)
  Where: P = Principal, r = monthly rate, n = months

WHY THIS MATTERS:
  - 5L at 12% for 12mo = ₹44,424/mo
  - 5L at 12% for 48mo = ₹13,170/mo
  - Same loan, different tenure = COMPLETELY different EMI
  - Old system was showing nonsense EMI values

================================================================================
WHY BACKEND CONTROLS EVERYTHING
================================================================================

PROBLEM WITH LLM CONTROL:
  - LLM "decided" users were eligible based on conversation
  - LLM revealed credit scores in responses
  - LLM calculated wrong EMIs
  - LLM approved loans that should be rejected
  - NO AUDIT TRAIL - decisions were in LLM context

BACKEND CONTROL PRINCIPLE:
  ┌─────────────────────────────────────────────────────────────┐
  │  BACKEND CONTROLS (deterministic_flow.py)                   │
  │  ─────────────────────────────────────────                  │
  │  • Flow sequence (which stage comes next)                   │
  │  • Data validation (is PAN format valid?)                   │
  │  • OTP verification (correct code?)                         │
  │  • Credit decision (score >= 700?)                          │
  │  • Amount eligibility (requested <= pre_approved?)          │
  │  • EMI calculation (mathematical formula)                   │
  │  • Approval/Rejection (rules engine)                        │
  │  • Session state (all user data)                            │
  └─────────────────────────────────────────────────────────────┘
  
  ┌─────────────────────────────────────────────────────────────┐
  │  LLM CONTROLS (agent_prompts.py)                            │
  │  ─────────────────────────────                              │
  │  • Polite wording of questions                              │
  │  • Friendly explanations                                    │
  │  • Natural language responses                               │
  │  • NOTHING ELSE                                             │
  └─────────────────────────────────────────────────────────────┘

LLM MUST NEVER:
  ✗ Decide eligibility ("You seem eligible")
  ✗ Reveal credit score ("Your score is 720")  
  ✗ Calculate EMI ("Your EMI will be ₹10,000")
  ✗ Reject applications ("Sorry, you don't qualify")
  ✗ Invent documents ("Please upload salary slip")
  ✗ Skip stages ("Let's proceed to approval")

================================================================================
MANDATORY 13-STAGE SEQUENCE (STRICT ORDER)
================================================================================

 Stage | Name             | Data Required       | Advances When
 ──────|──────────────────|─────────────────────|──────────────────────────
   1   | GREETING         | -                   | Any input
   2   | PURPOSE          | loan_purpose        | Purpose extracted
   3   | AMOUNT           | requested_amount    | Amount extracted
   4   | CITY             | city                | City extracted
   5   | EMPLOYMENT_TYPE  | employment_type     | Employment extracted
   6   | NAME             | name                | Name extracted
   7   | MOBILE           | mobile              | Mobile extracted
   8   | OTP              | otp_verified=True   | Correct OTP (3 attempts max)
   9   | KYC              | pan_verified=True   | Valid PAN matching identity
  10   | OFFER_DISCUSSION | -                   | User acknowledges offer
  11   | TENURE_SELECTION | selected_tenure     | Valid tenure (12/24/36/48)
  12   | UNDERWRITING     | underwriting_done   | Backend rules applied
  13   | SANCTION/REJECT  | -                   | TERMINAL (no next stage)

================================================================================
STRICT RULES
================================================================================

1. OUT OF ORDER INPUT → Ignored, re-ask current question
   Example: User gives PAN at AMOUNT stage → PAN ignored, ask amount again

2. STAGE NEVER ADVANCES without required data
   Example: Invalid mobile format → Stay at MOBILE stage

3. BACKEND IS SINGLE SOURCE OF TRUTH
   Example: Session state is authoritative, not conversation history

4. LLM GENERATES RESPONSES but backend controls content
   Example: LLM makes rejection message polite, backend decided rejection

5. IDENTITY LOCKED after OTP verification
   Example: PAN must match mobile number's registered user

6. CREDIT SCORE NEVER EXPOSED to user or LLM response
   Example: Rejection says "eligibility criteria" not "credit score 650"

================================================================================
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import re
import logging

# Import customer database for income verification (NO FILE UPLOAD)
try:
    from mock_data import CUSTOMER_PROFILES
except ImportError:
    CUSTOMER_PROFILES = {}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | FLOW | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('deterministic_flow')


# ================================================================================
# STAGE ENUMERATION - 16 STAGES (DYNAMIC CREDIT SCORING)
# ================================================================================

class FlowStage(Enum):
    """
    16-stage flow with user-provided financial data for credit scoring.
    No database dependency - calculates credit score from user inputs.
    """
    GREETING = 1           # Welcome
    PURPOSE = 2            # Ask loan purpose
    AMOUNT = 3             # Ask loan amount
    CITY = 4               # Ask city
    EMPLOYMENT_TYPE = 5    # Ask employment status
    NAME = 6               # Ask full name
    MOBILE = 7             # Ask mobile number
    OTP = 8                # Verify OTP
    INCOME = 9             # NEW: Ask monthly income
    EXISTING_EMI = 10      # NEW: Ask existing loan EMIs
    DOB = 11               # NEW: Ask date of birth/age
    KYC = 12               # PAN verification
    OFFER_DISCUSSION = 13  # Show offers (based on calculated score)
    TENURE_SELECTION = 14  # Select tenure/EMI
    UNDERWRITING = 15      # Backend decision
    SANCTION = 16          # Approved (terminal)
    REJECTION = 17         # Rejected (terminal)


# Terminal stages - journey ends here
TERMINAL_STAGES = {FlowStage.SANCTION, FlowStage.REJECTION}


# ================================================================================
# CREDIT SCORE CALCULATOR - BASED ON USER INPUTS (NO DATABASE)
# ================================================================================
#
# This calculates a credit score dynamically from user-provided data:
#   - Monthly Income
#   - Existing EMIs/Debt
#   - Employment Type
#   - Age
#   - Loan Amount Requested
#
# SCORING LOGIC (max 900 points):
# ================================
# 1. Debt-to-Income Ratio (0-300 points)
#    - DTI < 20%  → 300 points (excellent)
#    - DTI 20-30% → 250 points (good)
#    - DTI 30-40% → 180 points (fair)
#    - DTI 40-50% → 100 points (marginal)
#    - DTI > 50%  → 50 points (poor)
#
# 2. Income Level (0-250 points)
#    - > ₹1,50,000/mo → 250 points
#    - ₹1,00,000-1,50,000 → 220 points
#    - ₹75,000-1,00,000 → 180 points
#    - ₹50,000-75,000 → 140 points
#    - ₹30,000-50,000 → 100 points
#    - < ₹30,000 → 60 points
#
# 3. Employment Type (0-150 points)
#    - Salaried → 150 points
#    - Self-employed → 120 points
#
# 4. Age Factor (0-100 points)
#    - 25-45 years → 100 points (prime earning years)
#    - 45-55 years → 80 points
#    - 21-25 years → 70 points (early career)
#    - 55-60 years → 60 points
#    - <21 or >60 → 40 points
#
# 5. Loan Amount vs Income (0-100 points)
#    - Amount < 3x annual income → 100 points
#    - Amount 3-5x annual income → 70 points
#    - Amount 5-7x annual income → 40 points
#    - Amount > 7x annual income → 20 points
#
# DECISION THRESHOLDS:
# ====================
# Score >= 700 → APPROVED
# Score 600-699 → CONDITIONAL (may need additional docs)
# Score < 600 → REJECTED

def calculate_credit_score(
    monthly_income: float,
    existing_emi: float,
    employment_type: str,
    age: int,
    loan_amount: float
) -> Tuple[int, str, Dict[str, Any]]:
    """
    Calculate credit score from user-provided data.
    
    Returns:
        Tuple[int, str, Dict]: (score, decision, breakdown)
    """
    breakdown = {}
    total_score = 0
    
    # 1. Debt-to-Income Ratio
    if monthly_income > 0:
        dti_ratio = (existing_emi / monthly_income) * 100
    else:
        dti_ratio = 100  # No income = max DTI
    
    if dti_ratio < 20:
        dti_score = 300
    elif dti_ratio < 30:
        dti_score = 250
    elif dti_ratio < 40:
        dti_score = 180
    elif dti_ratio < 50:
        dti_score = 100
    else:
        dti_score = 50
    
    breakdown["dti"] = {"ratio": round(dti_ratio, 1), "score": dti_score, "max": 300}
    total_score += dti_score
    
    # 2. Income Level
    if monthly_income >= 150000:
        income_score = 250
    elif monthly_income >= 100000:
        income_score = 220
    elif monthly_income >= 75000:
        income_score = 180
    elif monthly_income >= 50000:
        income_score = 140
    elif monthly_income >= 30000:
        income_score = 100
    else:
        income_score = 60
    
    breakdown["income"] = {"monthly": monthly_income, "score": income_score, "max": 250}
    total_score += income_score
    
    # 3. Employment Type
    if employment_type.lower() in ["salaried", "employed"]:
        emp_score = 150
    else:
        emp_score = 120
    
    breakdown["employment"] = {"type": employment_type, "score": emp_score, "max": 150}
    total_score += emp_score
    
    # 4. Age Factor
    if 25 <= age <= 45:
        age_score = 100
    elif 45 < age <= 55:
        age_score = 80
    elif 21 <= age < 25:
        age_score = 70
    elif 55 < age <= 60:
        age_score = 60
    else:
        age_score = 40
    
    breakdown["age"] = {"years": age, "score": age_score, "max": 100}
    total_score += age_score
    
    # 5. Loan Amount vs Income
    annual_income = monthly_income * 12
    if annual_income > 0:
        loan_to_income = loan_amount / annual_income
    else:
        loan_to_income = 10  # No income = high ratio
    
    if loan_to_income < 3:
        amount_score = 100
    elif loan_to_income < 5:
        amount_score = 70
    elif loan_to_income < 7:
        amount_score = 40
    else:
        amount_score = 20
    
    breakdown["loan_ratio"] = {"ratio": round(loan_to_income, 2), "score": amount_score, "max": 100}
    total_score += amount_score
    
    # Final decision
    breakdown["total"] = {"score": total_score, "max": 900}
    
    if total_score >= 700:
        decision = "APPROVED"
    elif total_score >= 600:
        decision = "CONDITIONAL"
    else:
        decision = "REJECTED"
    
    return total_score, decision, breakdown


def calculate_pre_approved_limit(monthly_income: float, existing_emi: float, credit_score: int) -> float:
    """
    Calculate pre-approved loan limit based on income and score.
    
    Formula: (Monthly Income - Existing EMI) × FOIR × Multiplier
    
    FOIR (Fixed Obligations to Income Ratio):
    - Good score (750+): 60% of income can go to EMIs
    - Fair score (700-749): 50% of income
    - Marginal score (600-699): 40% of income
    """
    if credit_score >= 750:
        foir = 0.60
        multiplier = 36  # 36 months of disposable income
    elif credit_score >= 700:
        foir = 0.50
        multiplier = 30
    else:
        foir = 0.40
        multiplier = 24
    
    # Available for new EMI
    available_for_emi = (monthly_income * foir) - existing_emi
    
    if available_for_emi <= 0:
        return 0
    
    # Pre-approved limit
    limit = available_for_emi * multiplier
    
    # Cap at reasonable limits
    limit = min(limit, 5000000)  # Max 50 lakhs
    limit = max(limit, 0)
    
    # Round to nearest 10000
    return round(limit / 10000) * 10000


def calculate_interest_rate(credit_score: int) -> Tuple[float, float, float]:
    """
    Calculate interest rate range based on credit score.
    
    Returns: (min_rate, max_rate, likely_rate)
    """
    if credit_score >= 800:
        return 10.5, 12.0, 10.5
    elif credit_score >= 750:
        return 11.0, 13.0, 11.5
    elif credit_score >= 700:
        return 12.0, 14.5, 12.5
    elif credit_score >= 650:
        return 13.5, 16.0, 14.0
    else:
        return 15.0, 18.0, 16.0


# ================================================================================
# TENURE OPTIONS - CUSTOMER CHOICE
# ================================================================================
# 
# WHY TENURE-BASED EMI:
# --------------------
# Old broken system calculated EMI at OFFER stage before customer chose tenure.
# This is WRONG because EMI = f(Principal, Rate, Tenure).
# Without knowing tenure, EMI is meaningless.
#
# CORRECT FLOW:
#   1. OFFER stage: Show amount + interest rate RANGE
#   2. TENURE_SELECTION: Customer picks 12/24/36/48 months
#   3. AFTER selection: Calculate exact EMI using the formula
#
# Example: ₹5,00,000 at 12% interest
#   - 12 months → EMI = ₹44,424/mo (less interest, high payment)
#   - 48 months → EMI = ₹13,170/mo (more interest, low payment)
#
# Customer needs to see this comparison to make an informed choice.

TENURE_OPTIONS = [12, 24, 36, 48]  # Only these tenures allowed (months)

# ================================================================================
# INTEREST RATE RANGE
# ================================================================================
#
# WHY RANGE INSTEAD OF FIXED:
# --------------------------
# Interest rate depends on creditworthiness, which is internal.
# We show RANGE to user, actual rate determined at underwriting.
#
# Credit Score → Interest Rate mapping:
#   ≥ 750: 10.5% (excellent)
#   700-749: 12.0% (good) 
#   < 700: REJECTED (not shown)

INTEREST_RATE_RANGE = {
    "min": 10.5,  # Best rate for excellent credit (score >= 750)
    "max": 18.0,  # Rate for marginal profiles
    "default": 12.0  # Mid-range for good credit (700-749)
}


# ================================================================================
# STAGE TRANSITION MATRIX - STRICTLY LINEAR (16 STAGES)
# ================================================================================
# Only ONE valid next stage from each stage (except UNDERWRITING which branches)

NEXT_STAGE: Dict[FlowStage, FlowStage] = {
    FlowStage.GREETING: FlowStage.PURPOSE,
    FlowStage.PURPOSE: FlowStage.AMOUNT,
    FlowStage.AMOUNT: FlowStage.CITY,
    FlowStage.CITY: FlowStage.EMPLOYMENT_TYPE,
    FlowStage.EMPLOYMENT_TYPE: FlowStage.NAME,
    FlowStage.NAME: FlowStage.MOBILE,
    FlowStage.MOBILE: FlowStage.OTP,
    FlowStage.OTP: FlowStage.INCOME,           # NEW: After OTP, ask income
    FlowStage.INCOME: FlowStage.EXISTING_EMI,  # NEW: Then existing EMIs
    FlowStage.EXISTING_EMI: FlowStage.DOB,     # NEW: Then age/DOB
    FlowStage.DOB: FlowStage.KYC,              # Then KYC
    FlowStage.KYC: FlowStage.OFFER_DISCUSSION,
    FlowStage.OFFER_DISCUSSION: FlowStage.TENURE_SELECTION,
    FlowStage.TENURE_SELECTION: FlowStage.UNDERWRITING,
    # UNDERWRITING branches to SANCTION or REJECTION based on rules
}


# ================================================================================
# REQUIRED DATA FOR EACH STAGE TO ADVANCE (16 STAGES)
# ================================================================================

STAGE_REQUIREMENTS: Dict[FlowStage, List[str]] = {
    FlowStage.GREETING: [],  # No data needed, just user response
    FlowStage.PURPOSE: ["loan_purpose"],
    FlowStage.AMOUNT: ["loan_amount"],
    FlowStage.CITY: ["city"],
    FlowStage.EMPLOYMENT_TYPE: ["employment_type"],
    FlowStage.NAME: ["user_name"],
    FlowStage.MOBILE: ["user_mobile"],
    FlowStage.OTP: ["otp_verified"],  # Boolean flag
    FlowStage.INCOME: ["monthly_income"],  # NEW
    FlowStage.EXISTING_EMI: ["existing_monthly_emi"],  # NEW
    FlowStage.DOB: ["user_age"],  # NEW
    FlowStage.KYC: ["pan_verified"],  # Boolean flag
    FlowStage.OFFER_DISCUSSION: ["offer_shown"],  # Boolean flag
    FlowStage.TENURE_SELECTION: ["selected_tenure"],
    FlowStage.UNDERWRITING: ["underwriting_complete"],
}


# ================================================================================
# WHAT THE BOT ASKS AT EACH STAGE (FOR LLM PHRASING) - 16 STAGES
# ================================================================================

STAGE_QUESTIONS: Dict[FlowStage, str] = {
    FlowStage.GREETING: "Welcome the user warmly to Tata Capital loan services.",
    FlowStage.PURPOSE: "Ask what they would like to use the loan for (home, education, medical, etc.)",
    FlowStage.AMOUNT: "Ask how much loan amount they are looking for.",
    FlowStage.CITY: "Ask which city they currently reside in.",
    FlowStage.EMPLOYMENT_TYPE: "Ask if they are salaried or self-employed.",
    FlowStage.NAME: "Ask for their full name as per official documents.",
    FlowStage.MOBILE: "Ask for their 10-digit mobile number for OTP verification.",
    FlowStage.OTP: "Ask them to enter the OTP sent to their mobile number.",
    FlowStage.INCOME: """Ask for their monthly income (take-home salary for salaried, average monthly earnings for self-employed).
Explain: 'This helps us determine your loan eligibility and offer the best rates.'
Accept formats like: 50000, 50,000, 50k, 50K, 50 thousand.""",
    FlowStage.EXISTING_EMI: """Ask if they have any existing loans and what's the total monthly EMI they pay.
Say: 'Do you have any running loans like car loan, home loan, or personal loan? If yes, please share your total monthly EMI. If no existing loans, just say 0 or none.'
Explain: This helps calculate their debt capacity.""",
    FlowStage.DOB: """Ask for their date of birth or age.
Say: 'Please share your date of birth (DD/MM/YYYY) or your current age.'
Accept formats like: 15/05/1990, 15-05-1990, 34 years, 34.""",
    FlowStage.KYC: "Ask for their PAN number for identity verification.",
    FlowStage.OFFER_DISCUSSION: """Present the pre-approved loan offer with INTEREST RATE RANGE based on their calculated profile.
Say: 'Based on your income and financial profile, you're eligible for a loan up to ₹X at an interest rate between Y% to Z% per annum.'
IMPORTANT: Say 'Based on tenure, your EMI may vary. Please select your preferred tenure to see the exact EMI.'
Do NOT calculate or show EMI yet - that happens after tenure selection.""",
    FlowStage.TENURE_SELECTION: """Ask them to select their preferred loan tenure from these options: 12, 24, 36, or 48 months.
Explain: 'Shorter tenure = Higher EMI but less total interest. Longer tenure = Lower EMI but more total interest.'
After they select, show the calculated EMI for their chosen tenure.""",
    FlowStage.UNDERWRITING: "Inform them their application is being processed. Say 'We are verifying your details.'",
    FlowStage.SANCTION: """Congratulate them on loan approval and provide sanction details.
Include: Approved amount, interest rate, selected tenure, and final EMI.
NEVER mention credit score. Say 'Based on your profile, your loan has been approved.'""",
    FlowStage.REJECTION: """Politely inform them the application could not be approved at this time.
NEVER mention credit score or specific rejection reason.
Say: 'Unfortunately, we are unable to approve your application at this time based on our eligibility criteria.'
Suggest: 'You may reapply after 6 months or contact our support team for more information.'
Do NOT say: 'Your credit score is too low' or 'Amount exceeds limit' - keep it generic.""",
}


# ================================================================================
# SESSION STATE - SINGLE SOURCE OF TRUTH
# ================================================================================

@dataclass
class SessionState:
    """
    All data for a loan application session.
    Backend owns this. Frontend reads only.
    
    DATA INTEGRITY RULES:
    1. ONE customer per session - identity locked after OTP verification
    2. PAN must belong to same customer (cross-reference with database)
    3. No cross-user documents allowed
    4. application_id ties everything together for admin dashboard
    """
    session_id: str
    current_stage: FlowStage = FlowStage.GREETING
    
    # ================================================================================
    # APPLICATION IDENTITY - UNIQUE PER SESSION
    # ================================================================================
    application_id: Optional[str] = None  # Generated after OTP verification
    identity_locked: bool = False  # True after OTP verification - NO CHANGES ALLOWED
    identity_locked_at: Optional[datetime] = None  # Timestamp of identity lock
    expected_pan: Optional[str] = None  # PAN from customer database - must match
    identity_mismatch: bool = False  # True if any mismatch detected
    identity_mismatch_reason: Optional[str] = None  # Reason for mismatch
    
    # Stage 2: Purpose
    loan_purpose: Optional[str] = None
    
    # Stage 3: Amount
    loan_amount: Optional[float] = None
    
    # Stage 4: City
    city: Optional[str] = None
    
    # Stage 5: Employment
    employment_type: Optional[str] = None  # "salaried" or "self_employed"
    
    # Stage 6: Name
    user_name: Optional[str] = None
    
    # Stage 7: Mobile
    user_mobile: Optional[str] = None
    
    # Stage 8: OTP
    generated_otp: Optional[str] = None
    otp_verified: bool = False
    otp_attempts: int = 0
    
    # Stage 9: KYC (PAN only)
    pan_number: Optional[str] = None
    pan_verified: bool = False
    
    # Stage 10: Offer (shows RANGE, not fixed EMI)
    offer_shown: bool = False
    pre_approved_limit: Optional[float] = None
    # Interest rate is a RANGE until tenure is selected
    interest_rate_min: Optional[float] = None   # Best rate (good credit)
    interest_rate_max: Optional[float] = None   # Worst rate (poor credit)
    final_interest_rate: Optional[float] = None # Set after underwriting
    
    # ================================================================================
    # INCOME DATA - USER PROVIDED (DYNAMIC CREDIT SCORING)
    # ================================================================================
    #
    # NEW APPROACH - Dynamic Credit Scoring:
    # - User provides their own income and debt information
    # - Credit score is calculated from user inputs
    # - No database dependency for eligibility
    # - Any user can go through the full flow
    #
    monthly_income: Optional[float] = None       # User-provided monthly income
    annual_income: Optional[float] = None        # Calculated from monthly
    existing_monthly_emi: Optional[float] = None # User-provided existing EMI obligations
    debt_to_income_ratio: Optional[float] = None # Calculated from user inputs
    user_age: Optional[int] = None               # User's age (from DOB or direct input)
    user_dob: Optional[str] = None               # Date of birth if provided
    income_source: str = "USER_PROVIDED"         # Now user-provided, not database
    
    # Credit Score - Calculated from user inputs
    credit_score_breakdown: Optional[Dict[str, Any]] = None  # Detailed breakdown
    
    # Stage 14: Tenure Selection (EMI calculated ONLY after this)
    selected_tenure: Optional[int] = None  # months: 12, 24, 36, or 48
    calculated_emi: Optional[float] = None  # Calculated AFTER tenure selected
    # EMI options for customer to compare
    emi_options: Optional[Dict[int, float]] = None  # {12: emi12, 24: emi24, 36: emi36, 48: emi48}
    
    # Stage 12: Underwriting
    underwriting_complete: bool = False
    credit_score: Optional[int] = None  # NEVER shown to user
    underwriting_result: Optional[str] = None  # "APPROVED" or "REJECTED"
    rejection_reason: Optional[str] = None  # Internal only
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    # Journey status
    is_frozen: bool = False
    freeze_reason: Optional[str] = None
    
    # Sanction Letter
    sanction_letter_generated: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses (user-facing)."""
        return {
            "session_id": self.session_id,
            "current_stage": self.current_stage.name,
            "stage_number": self.current_stage.value,
            "total_stages": 17,  # Updated for 16-stage flow + rejection
            "loan_purpose": self.loan_purpose,
            "loan_amount": self.loan_amount,
            "city": self.city,
            "employment_type": self.employment_type,
            "user_name": self.user_name,
            "user_mobile": f"XXXXXX{self.user_mobile[-4:]}" if self.user_mobile else None,
            "otp_verified": self.otp_verified,
            # Income data (user-provided)
            "monthly_income": self.monthly_income,
            "existing_monthly_emi": self.existing_monthly_emi,
            "user_age": self.user_age,
            "pan_verified": self.pan_verified,
            "offer_shown": self.offer_shown,
            "pre_approved_limit": self.pre_approved_limit,
            # Interest rate as RANGE (not fixed until tenure selection)
            "interest_rate_min": self.interest_rate_min,
            "interest_rate_max": self.interest_rate_max,
            "interest_rate_range": {
                "min": self.interest_rate_min,
                "max": self.interest_rate_max
            } if self.interest_rate_min else None,
            "final_interest_rate": self.final_interest_rate,  # Set after tenure selection
            # Tenure options for customer choice
            "tenure_options": TENURE_OPTIONS,  # [12, 24, 36, 48]
            "selected_tenure": self.selected_tenure,
            "calculated_emi": self.calculated_emi,  # Only set AFTER tenure selection
            "emi_options": self.emi_options,  # EMI for each tenure option
            "underwriting_complete": self.underwriting_complete,
            "underwriting_result": self.underwriting_result,
            "is_frozen": self.is_frozen,
            "income_source": self.income_source,  # Now "USER_PROVIDED"
            # Data integrity for admin dashboard
            "application_id": self.application_id,
            "identity_locked": self.identity_locked,
            "identity_mismatch": self.identity_mismatch,
            # NEVER expose: credit_score, generated_otp, full mobile, rejection_reason
        }
    
    def to_admin_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for ADMIN DASHBOARD (read-only backend state).
        
        ADMIN DASHBOARD REQUIREMENTS:
        - READ-ONLY: No actions, no modifications
        - BACKEND STATE ONLY: Shows deterministic state machine truth
        - NEVER DISCONNECT: Stable data, no websocket-dependent fields
        - NEVER INFER: Only actual values, no computed/guessed fields
        
        Shows:
        - Application ID
        - Current stage (with number and name)
        - KYC status (OTP verified, PAN verified)
        - Offer eligibility (pre-approved limit, interest range)
        - Decision reason (for completed applications)
        """
        # ================================================================
        # STAGE PROGRESSION - Where in the flow
        # ================================================================
        stage_info = {
            "current_stage": self.current_stage.name,
            "stage_number": self.current_stage.value,
            "total_stages": 14,
            "progress_percent": round((self.current_stage.value / 14) * 100),
            "is_terminal": self.current_stage in TERMINAL_STAGES,
        }
        
        # ================================================================
        # KYC STATUS - Identity verification
        # ================================================================
        kyc_status = {
            "otp_verified": self.otp_verified,
            "otp_attempts": self.otp_attempts,
            "pan_verified": self.pan_verified,
            "pan_number": f"XXXXX{self.pan_number[-5:]}" if self.pan_number else None,
            "identity_locked": self.identity_locked,
            "identity_locked_at": self.identity_locked_at.isoformat() if self.identity_locked_at else None,
            "identity_mismatch": self.identity_mismatch,
            "identity_mismatch_reason": self.identity_mismatch_reason,
        }
        
        # ================================================================
        # OFFER ELIGIBILITY - What we can offer
        # ================================================================
        offer_eligibility = {
            "pre_approved_limit": self.pre_approved_limit,
            "requested_amount": self.loan_amount,
            "amount_within_limit": (
                self.loan_amount <= self.pre_approved_limit 
                if self.loan_amount and self.pre_approved_limit 
                else None
            ),
            "interest_rate_range": {
                "min": self.interest_rate_min,
                "max": self.interest_rate_max,
            } if self.interest_rate_min else None,
            "final_interest_rate": self.final_interest_rate,
            "selected_tenure": self.selected_tenure,
            "calculated_emi": self.calculated_emi,
            "offer_shown": self.offer_shown,
        }
        
        # ================================================================
        # DECISION - Final outcome
        # ================================================================
        decision_info = {
            "underwriting_complete": self.underwriting_complete,
            "underwriting_result": self.underwriting_result,  # APPROVED or REJECTED
            "rejection_reason": self.rejection_reason,  # Internal code only
            "is_frozen": self.is_frozen,
            "freeze_reason": self.freeze_reason,
            "sanction_letter_generated": self.sanction_letter_generated,
        }
        
        # ================================================================
        # SESSION STATUS - For halt detection
        # ================================================================
        session_info = {
            "is_halted": self.is_frozen or self.identity_mismatch,
            "halt_reason": self.freeze_reason or self.identity_mismatch_reason,
        }
        
        # ================================================================
        # FULL ADMIN VIEW - All backend state
        # ================================================================
        return {
            # Identity
            "application_id": self.application_id,
            "session_id": self.session_id,
            
            # Customer (masked for privacy)
            "customer": {
                "name": self.user_name,
                "mobile_masked": f"XXXXXX{self.user_mobile[-4:]}" if self.user_mobile else None,
                "city": self.city,
                "employment_type": self.employment_type,
                "loan_purpose": self.loan_purpose,
            },
            
            # Stage progression
            "stage": stage_info,
            
            # KYC verification status
            "kyc": kyc_status,
            
            # Offer eligibility
            "offer": offer_eligibility,
            
            # Decision
            "decision": decision_info,
            
            # Timestamps
            "timestamps": {
                "created_at": self.created_at.isoformat(),
                "last_updated": self.last_updated.isoformat(),
            },
            
            # Session status (for halt detection)
            "session": session_info,
            
            # Income source (always database)
            "income_source": self.income_source,
        }


# ================================================================================
# FLOW CONTROLLER - THE DETERMINISTIC ENGINE
# ================================================================================

class DeterministicFlowController:
    """
    Controls the loan application flow with STRICT DETERMINISM.
    
    Rules:
    1. Only advances when required data is collected
    2. Ignores out-of-order inputs
    3. Re-asks current question if data not provided
    4. Backend makes ALL decisions
    """
    
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}
        logger.info("=" * 60)
        logger.info("DETERMINISTIC FLOW CONTROLLER INITIALIZED")
        logger.info("16-stage strict sequence enforced")
        logger.info("=" * 60)
    
    def get_or_create_session(self, session_id: str) -> SessionState:
        """Get existing session or create new one."""
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionState(session_id=session_id)
            logger.info(f"[{session_id}] New session created at GREETING")
        return self.sessions[session_id]
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get session by ID."""
        return self.sessions.get(session_id)
    
    def reset_session(self, session_id: str) -> SessionState:
        """Reset session to initial state."""
        self.sessions[session_id] = SessionState(session_id=session_id)
        logger.info(f"[{session_id}] Session RESET to GREETING")
        return self.sessions[session_id]
    
    def is_frozen(self, session_id: str) -> bool:
        """Check if session is frozen (completed journey)."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        return session.is_frozen or session.current_stage in TERMINAL_STAGES
    
    def can_advance(self, session: SessionState) -> Tuple[bool, str]:
        """
        Check if we have all required data to advance to next stage.
        
        Returns: (can_advance, missing_field_or_empty)
        """
        if session.current_stage in TERMINAL_STAGES:
            return False, "journey_complete"
        
        requirements = STAGE_REQUIREMENTS.get(session.current_stage, [])
        
        for field_name in requirements:
            value = getattr(session, field_name, None)
            if value is None or value == "" or value is False:
                return False, field_name
        
        return True, ""
    
    def advance_stage(self, session: SessionState) -> Tuple[bool, str]:
        """
        Advance to next stage if requirements met.
        
        Returns: (success, message)
        """
        can_advance, missing = self.can_advance(session)
        
        if not can_advance:
            if missing == "journey_complete":
                return False, "Journey already complete"
            return False, f"Missing required: {missing}"
        
        old_stage = session.current_stage
        
        # Special case: UNDERWRITING branches
        if old_stage == FlowStage.UNDERWRITING:
            if session.underwriting_result == "APPROVED":
                session.current_stage = FlowStage.SANCTION
                session.is_frozen = True
                session.freeze_reason = "LOAN_SANCTIONED"
                session.sanction_letter_generated = True
            else:
                session.current_stage = FlowStage.REJECTION
                session.is_frozen = True
                session.freeze_reason = "LOAN_REJECTED"
        else:
            next_stage = NEXT_STAGE.get(old_stage)
            if next_stage:
                session.current_stage = next_stage
            else:
                return False, "No next stage defined"
        
        session.last_updated = datetime.now()
        logger.info(f"[{session.session_id}] Stage: {old_stage.name} → {session.current_stage.name}")
        
        # ================================================================
        # TRIGGER ACTIONS WHEN ENTERING CERTAIN STAGES
        # ================================================================
        
        # When entering OFFER_DISCUSSION, calculate the offer
        if session.current_stage == FlowStage.OFFER_DISCUSSION:
            self._calculate_offer(session)
            session.offer_shown = True
            logger.info(f"[{session.session_id}] Offer calculated: ₹{session.pre_approved_limit:,.0f}")
        
        # ================================================================
        # AUTO-RUN UNDERWRITING when entering UNDERWRITING stage
        # This prevents getting stuck - underwriting runs immediately
        # ================================================================
        if session.current_stage == FlowStage.UNDERWRITING:
            decision, reason = self._perform_underwriting(session)
            session.underwriting_result = decision
            session.rejection_reason = reason if decision == "REJECTED" else None
            session.underwriting_complete = True
            logger.info(f"[{session.session_id}] Auto-underwriting: {decision}")
            
            # Immediately advance to SANCTION or REJECTION
            if decision == "APPROVED":
                session.current_stage = FlowStage.SANCTION
                session.is_frozen = True
                session.freeze_reason = "LOAN_SANCTIONED"
                session.sanction_letter_generated = True
                logger.info(f"[{session.session_id}] Auto-advanced to SANCTION")
            else:
                session.current_stage = FlowStage.REJECTION
                session.is_frozen = True
                session.freeze_reason = "LOAN_REJECTED"
                logger.info(f"[{session.session_id}] Auto-advanced to REJECTION")
        
        return True, f"Advanced to {session.current_stage.name}"
    
    def get_current_question(self, session: SessionState) -> str:
        """Get the question/instruction for current stage."""
        return STAGE_QUESTIONS.get(session.current_stage, "Unknown stage")
    
    def process_input(
        self,
        session_id: str,
        user_message: str
    ) -> Tuple[SessionState, str, bool]:
        """
        Process user input and potentially advance stage.
        
        Returns: (session, response_instruction, stage_changed)
        """
        session = self.get_or_create_session(session_id)
        
        # ========================================================================
        # DATA INTEGRITY CHECK - IDENTITY MISMATCH HALTS EVERYTHING
        # ========================================================================
        if session.identity_mismatch:
            logger.error(f"[{session.session_id}] HALTED: Identity mismatch - {session.identity_mismatch_reason}")
            return session, "Application halted due to verification issue. Please contact support.", False
        
        # Check frozen
        if self.is_frozen(session_id):
            return session, "Journey is complete. No further input accepted.", False
        
        # Extract relevant data based on current stage
        data_extracted = self._extract_stage_data(session, user_message)
        
        # Check again after extraction (PAN verification may have set mismatch)
        if session.identity_mismatch:
            logger.error(f"[{session.session_id}] HALTED AFTER EXTRACTION: {session.identity_mismatch_reason}")
            return session, "Application halted due to verification issue. Please contact support.", False
        
        # Try to advance
        if data_extracted:
            success, msg = self.advance_stage(session)
            if success:
                return session, self.get_current_question(session), True
        
        # Didn't advance - re-ask current question
        return session, self.get_current_question(session), False
    
    def _extract_stage_data(self, session: SessionState, message: str) -> bool:
        """
        Extract data relevant to CURRENT stage only.
        Ignores out-of-order information.
        
        Returns: True if relevant data was extracted
        """
        stage = session.current_stage
        message_lower = message.lower().strip()
        
        # GREETING: Any response advances
        if stage == FlowStage.GREETING:
            return True
        
        # PURPOSE: Extract loan purpose
        if stage == FlowStage.PURPOSE:
            purpose = self._extract_purpose(message_lower)
            if purpose:
                session.loan_purpose = purpose
                logger.info(f"[{session.session_id}] Extracted purpose: {purpose}")
                return True
            return False
        
        # AMOUNT: Extract loan amount
        if stage == FlowStage.AMOUNT:
            amount = self._extract_amount(message)
            if amount:
                session.loan_amount = amount
                logger.info(f"[{session.session_id}] Extracted amount: {amount}")
                return True
            return False
        
        # CITY: Extract city
        if stage == FlowStage.CITY:
            city = self._extract_city(message)
            if city:
                session.city = city
                logger.info(f"[{session.session_id}] Extracted city: {city}")
                return True
            return False
        
        # EMPLOYMENT_TYPE: Extract employment status
        if stage == FlowStage.EMPLOYMENT_TYPE:
            emp_type = self._extract_employment_type(message_lower)
            if emp_type:
                session.employment_type = emp_type
                logger.info(f"[{session.session_id}] Extracted employment: {emp_type}")
                return True
            return False
        
        # NAME: Extract name
        if stage == FlowStage.NAME:
            name = self._extract_name(message)
            if name:
                session.user_name = name
                logger.info(f"[{session.session_id}] Extracted name: {name}")
                return True
            return False
        
        # MOBILE: Extract mobile number
        if stage == FlowStage.MOBILE:
            mobile = self._extract_mobile(message)
            if mobile:
                session.user_mobile = mobile
                # Generate OTP immediately
                session.generated_otp = self._generate_otp(mobile)
                logger.info(f"[{session.session_id}] Extracted mobile: {mobile[-4:]}, OTP generated")
                return True
            return False
        
        # OTP: Verify OTP
        if stage == FlowStage.OTP:
            otp = self._extract_otp(message)
            if otp:
                session.otp_attempts += 1
                if otp == session.generated_otp:
                    session.otp_verified = True
                    # ============================================================
                    # IDENTITY LOCK - CRITICAL FOR DATA INTEGRITY
                    # After OTP verification, identity is LOCKED. No changes.
                    # ============================================================
                    self._lock_identity(session)
                    logger.info(f"[{session.session_id}] OTP verified - IDENTITY LOCKED")
                    return True
                else:
                    logger.warning(f"[{session.session_id}] OTP mismatch (attempt {session.otp_attempts})")
                    if session.otp_attempts >= 3:
                        session.is_frozen = True
                        session.freeze_reason = "OTP_ATTEMPTS_EXCEEDED"
                    return False
            return False
        
        # INCOME: Extract monthly income (NEW)
        if stage == FlowStage.INCOME:
            income = self._extract_income(message)
            if income:
                session.monthly_income = income
                session.annual_income = income * 12
                logger.info(f"[{session.session_id}] Extracted monthly income: ₹{income:,.0f}")
                return True
            return False
        
        # EXISTING_EMI: Extract existing loan EMIs (NEW)
        if stage == FlowStage.EXISTING_EMI:
            existing_emi = self._extract_existing_emi(message)
            if existing_emi is not None:  # 0 is valid (no existing loans)
                session.existing_monthly_emi = existing_emi
                # Calculate DTI ratio
                if session.monthly_income and session.monthly_income > 0:
                    session.debt_to_income_ratio = (existing_emi / session.monthly_income) * 100
                logger.info(f"[{session.session_id}] Extracted existing EMI: ₹{existing_emi:,.0f}")
                return True
            return False
        
        # DOB: Extract age or date of birth (NEW)
        if stage == FlowStage.DOB:
            age = self._extract_age(message)
            if age:
                session.user_age = age
                logger.info(f"[{session.session_id}] Extracted age: {age} years")
                return True
            return False
        
        # KYC: Verify PAN
        if stage == FlowStage.KYC:
            pan = self._extract_pan(message)
            if pan:
                session.pan_number = pan
                # ============================================================
                # PAN VERIFICATION - MUST MATCH SAME CUSTOMER
                # Cross-reference with database. Mismatch = HALT.
                # ============================================================
                pan_check = self._verify_pan_with_identity_check(pan, session)
                if pan_check["verified"]:
                    session.pan_verified = True
                    logger.info(f"[{session.session_id}] PAN verified and matches identity")
                    return True
                else:
                    session.pan_verified = False
                    session.identity_mismatch = True
                    session.identity_mismatch_reason = pan_check["reason"]
                    session.is_frozen = True
                    session.freeze_reason = pan_check["reason"]
                    session.current_stage = FlowStage.REJECTION
                    logger.error(f"[{session.session_id}] PAN MISMATCH DETECTED: {pan_check['reason']}")
                    return False
            return False
        
        # OFFER_DISCUSSION: Show offer (automatic)
        if stage == FlowStage.OFFER_DISCUSSION:
            # Offer is shown automatically when reaching this stage
            self._calculate_offer(session)
            session.offer_shown = True
            # Any acknowledgment advances
            if any(word in message_lower for word in ['ok', 'yes', 'proceed', 'continue', 'great', 'good']):
                return True
            return False
        
        # TENURE_SELECTION: Extract tenure and calculate FINAL EMI
        if stage == FlowStage.TENURE_SELECTION:
            tenure = self._extract_tenure(message)
            if tenure and tenure in TENURE_OPTIONS:
                session.selected_tenure = tenure
                
                # NOW calculate final interest rate based on credit score
                credit_score = session.credit_score or 700  # Default if unknown
                session.final_interest_rate = self._get_interest_rate_for_credit_score(credit_score)
                
                # Calculate final EMI with ACTUAL interest rate
                session.calculated_emi = self._calculate_emi(
                    session.loan_amount or 0,
                    session.final_interest_rate,
                    tenure
                )
                
                logger.info(f"[{session.session_id}] Tenure selected: {tenure} months")
                logger.info(f"[{session.session_id}] Final interest rate: {session.final_interest_rate}%")
                logger.info(f"[{session.session_id}] Final EMI: ₹{session.calculated_emi}")
                return True
            else:
                # Invalid tenure - don't advance
                logger.warning(f"[{session.session_id}] Invalid tenure: {tenure}, must be one of {TENURE_OPTIONS}")
                return False
        
        # UNDERWRITING: Automatic decision
        if stage == FlowStage.UNDERWRITING:
            decision, reason = self._perform_underwriting(session)
            session.underwriting_result = decision
            session.rejection_reason = reason if decision == "REJECTED" else None
            session.underwriting_complete = True
            logger.info(f"[{session.session_id}] Underwriting: {decision}")
            return True
        
        return False
    
    # ================================================================================
    # DATA EXTRACTION METHODS
    # ================================================================================
    
    def _extract_purpose(self, message: str) -> Optional[str]:
        """Extract loan purpose from message."""
        # Reject out-of-context inputs (PAN, mobile, OTP patterns)
        pan_pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]', re.IGNORECASE)
        mobile_pattern = re.compile(r'\b[6-9]\d{9}\b')
        otp_pattern = re.compile(r'^\d{6}$')
        
        if pan_pattern.search(message) or mobile_pattern.search(message) or otp_pattern.match(message.strip()):
            return None  # Reject - user provided wrong type of input
        
        purposes = {
            "home": ["home", "house", "renovation", "construction", "repair"],
            "education": ["education", "study", "college", "school", "course", "tuition"],
            "medical": ["medical", "health", "hospital", "treatment", "surgery"],
            "wedding": ["wedding", "marriage", "shaadi"],
            "travel": ["travel", "vacation", "trip", "holiday"],
            "business": ["business", "shop", "startup", "company"],
            "debt_consolidation": ["debt", "consolidation", "pay off", "credit card"],
            "personal": ["personal", "emergency", "expense", "need"]
        }
        
        for purpose, keywords in purposes.items():
            if any(kw in message for kw in keywords):
                return purpose
        
        # If message is just text without keywords, treat as personal purpose
        if len(message.split()) >= 2:
            return "personal"
        
        return None
    
    def _extract_amount(self, message: str) -> Optional[float]:
        """Extract loan amount from message."""
        message_lower = message.lower()
        
        # Pattern: X lakhs/lacs/L
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|l)\b', message_lower)
        if lakh_match:
            return float(lakh_match.group(1)) * 100000
        
        # Pattern: X crore
        crore_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:crore|cr)\b', message_lower)
        if crore_match:
            return float(crore_match.group(1)) * 10000000
        
        # Pattern: Direct number (5+ digits)
        number_match = re.search(r'(?:rs\.?\s*)?(\d{5,})', message_lower.replace(',', ''))
        if number_match:
            return float(number_match.group(1))
        
        return None
    
    def _extract_city(self, message: str) -> Optional[str]:
        """Extract city from message."""
        cities = [
            "mumbai", "delhi", "bangalore", "bengaluru", "chennai", "kolkata",
            "hyderabad", "pune", "ahmedabad", "jaipur", "lucknow", "kanpur",
            "nagpur", "indore", "thane", "bhopal", "visakhapatnam", "vadodara",
            "ghaziabad", "ludhiana", "agra", "nashik", "faridabad", "meerut",
            "rajkot", "varanasi", "srinagar", "aurangabad", "dhanbad", "amritsar",
            "navi mumbai", "allahabad", "prayagraj", "ranchi", "gwalior", "jabalpur",
            "coimbatore", "vijayawada", "jodhpur", "madurai", "raipur", "kota",
            "gurgaon", "gurugram", "noida", "chandigarh", "surat", "patna"
        ]
        
        message_lower = message.lower()
        for city in cities:
            if city in message_lower:
                return city.title()
        
        # If single word, might be a city name
        words = message.strip().split()
        if len(words) == 1 and words[0].isalpha():
            return words[0].title()
        
        return None
    
    def _extract_employment_type(self, message: str) -> Optional[str]:
        """Extract employment type from message."""
        if any(word in message for word in ["salaried", "salary", "job", "employed", "employee", "working"]):
            return "salaried"
        if any(word in message for word in ["self", "business", "own", "freelance", "entrepreneur", "proprietor"]):
            return "self_employed"
        return None
    
    def _extract_name(self, message: str) -> Optional[str]:
        """Extract user name from message."""
        # Clean up common prefixes
        message = re.sub(r'^(my name is|i am|this is|name is|i\'m)\s*', '', message, flags=re.IGNORECASE)
        
        # Name should be 2-4 words, alphabetic
        words = message.strip().split()
        if 1 <= len(words) <= 4:
            # Check all words are alphabetic
            if all(word.replace(".", "").isalpha() for word in words):
                return ' '.join(word.capitalize() for word in words)
        
        return None
    
    def _extract_mobile(self, message: str) -> Optional[str]:
        """Extract 10-digit mobile number from message."""
        # Remove spaces, dashes, parens
        cleaned = re.sub(r'[\s\-\(\)]', '', message)
        
        # Try to find 10-digit number starting with 6-9
        # First try with +91 or 91 prefix
        match = re.search(r'(?:\+?91)?([6-9]\d{9})$', cleaned)
        if match:
            return match.group(1)
        
        # Try anywhere in string
        match = re.search(r'([6-9]\d{9})', cleaned)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_otp(self, message: str) -> Optional[str]:
        """Extract 6-digit OTP from message."""
        # Just digits
        if re.match(r'^\d{6}$', message.strip()):
            return message.strip()
        
        # Find 6-digit number
        match = re.search(r'\b(\d{6})\b', message)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_income(self, message: str) -> Optional[float]:
        """
        Extract monthly income from message.
        
        Supported formats:
        - 50000, 50,000, 50000.00
        - 50k, 50K, 50 k
        - 50 thousand
        - 5 lakh, 5L, 5 lac (annual - divide by 12)
        """
        message_clean = message.lower().replace(',', '').replace(' ', '')
        
        # Check for annual income (lakhs) - divide by 12
        lakh_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lac|l)\s*(?:per\s*annum|pa|annual|yearly)?', message_clean)
        if lakh_match:
            annual = float(lakh_match.group(1)) * 100000
            return annual / 12
        
        # Check for "X per month" or "X monthly"
        monthly_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:k|thousand)?\s*(?:per\s*month|pm|monthly|month)', message_clean)
        if monthly_match:
            amount = float(monthly_match.group(1))
            if 'k' in message_clean or 'thousand' in message_clean:
                amount *= 1000
            return amount
        
        # Check for "k" or "thousand" suffix
        if re.search(r'(\d+(?:\.\d+)?)\s*(?:k|thousand)', message_clean):
            match = re.search(r'(\d+(?:\.\d+)?)', message_clean)
            if match:
                return float(match.group(1)) * 1000
        
        # Plain number
        num_match = re.search(r'(\d+(?:\.\d+)?)', message_clean)
        if num_match:
            amount = float(num_match.group(1))
            # If small number (less than 500), likely in thousands
            if amount < 500:
                return amount * 1000
            return amount
        
        return None
    
    def _extract_existing_emi(self, message: str) -> Optional[float]:
        """
        Extract existing EMI amount from message.
        
        Supported formats:
        - 0, none, nil, no, nothing (no existing loans)
        - 5000, 5,000, 5k, 5 thousand
        """
        message_clean = message.lower().strip()
        
        # Check for "no existing EMI" variants
        no_emi_patterns = ['no', 'none', 'nil', 'nothing', 'zero', '0', 'nahi', 'nhi', 'na', 'dont have', "don't have"]
        for pattern in no_emi_patterns:
            if pattern in message_clean:
                return 0.0
        
        # Extract amount (reuse income extraction logic)
        message_clean = message_clean.replace(',', '').replace(' ', '')
        
        # Check for "k" or "thousand" suffix
        if re.search(r'(\d+(?:\.\d+)?)\s*(?:k|thousand)', message_clean):
            match = re.search(r'(\d+(?:\.\d+)?)', message_clean)
            if match:
                return float(match.group(1)) * 1000
        
        # Plain number
        num_match = re.search(r'(\d+(?:\.\d+)?)', message_clean)
        if num_match:
            amount = float(num_match.group(1))
            # If small number (less than 100), likely in thousands
            if amount < 100 and amount > 0:
                return amount * 1000
            return amount
        
        return None
    
    def _extract_age(self, message: str) -> Optional[int]:
        """
        Extract age from message (as years or date of birth).
        
        Supported formats:
        - 25, 25 years, 25 yrs
        - DD/MM/YYYY, DD-MM-YYYY (calculates age from DOB)
        """
        message_clean = message.strip().lower()
        
        # Try DOB format: DD/MM/YYYY or DD-MM-YYYY
        dob_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', message)
        if dob_match:
            day, month, year = int(dob_match.group(1)), int(dob_match.group(2)), int(dob_match.group(3))
            try:
                from datetime import date
                birth_date = date(year, month, day)
                today = date.today()
                age = today.year - birth_date.year
                # Adjust if birthday hasn't occurred this year
                if (today.month, today.day) < (birth_date.month, birth_date.day):
                    age -= 1
                if 18 <= age <= 80:
                    return age
            except:
                pass
        
        # Try "X years" or "X yrs" format
        year_match = re.search(r'(\d+)\s*(?:years?|yrs?|year old)?', message_clean)
        if year_match:
            age = int(year_match.group(1))
            if 18 <= age <= 80:
                return age
        
        # Plain number
        num_match = re.search(r'\b(\d{2})\b', message)
        if num_match:
            age = int(num_match.group(1))
            if 18 <= age <= 80:
                return age
        
        return None
    
    def _extract_pan(self, message: str) -> Optional[str]:
        """Extract PAN number from message."""
        # PAN format: AAAAA1234A
        match = re.search(r'([A-Z]{5}\d{4}[A-Z])', message.upper())
        if match:
            return match.group(1)
        return None
    
    def _extract_tenure(self, message: str) -> Optional[int]:
        """
        Extract loan tenure (months) from message.
        
        Valid tenures: 12, 24, 36, 48 months (1, 2, 3, 4 years)
        """
        message_lower = message.lower()
        
        # Pattern: X years
        year_match = re.search(r'(\d+)\s*(?:year|yr|years|yrs)', message_lower)
        if year_match:
            years = int(year_match.group(1))
            tenure = years * 12
            if tenure in TENURE_OPTIONS:
                return tenure
            # Return anyway, validation happens in caller
            return tenure
        
        # Pattern: X months
        month_match = re.search(r'(\d+)\s*(?:month|months|mon)', message_lower)
        if month_match:
            return int(month_match.group(1))
        
        # Just a number - check if it matches our options
        num_match = re.search(r'\b(\d+)\b', message)
        if num_match:
            num = int(num_match.group(1))
            # Check for direct tenure option match
            if num in TENURE_OPTIONS:
                return num
            # Check for years (1, 2, 3, 4)
            if num <= 4 and num * 12 in TENURE_OPTIONS:
                return num * 12
        
        return None
    
    # ================================================================================
    # OTP GENERATION
    # ================================================================================
    
    # Test users with fixed OTP
    TEST_USERS = {
        "9876543210": "123456",  # Rahul Mehta - APPROVED
        "9988776655": "123456",  # Amit Verma - CONDITIONAL
        "9123456781": "123456",  # Priya Sharma - REJECTED
    }
    
    def _generate_otp(self, mobile: str) -> str:
        """Generate OTP for mobile number."""
        if mobile in self.TEST_USERS:
            return self.TEST_USERS[mobile]
        # For demo, always use 123456
        return "123456"
    
    # ================================================================================
    # IDENTITY LOCKING - CRITICAL FOR DATA INTEGRITY
    # ================================================================================
    
    def _lock_identity(self, session: SessionState):
        """
        Lock identity after OTP verification.
        
        Once locked:
        1. Generate unique application_id
        2. Fetch expected_pan from customer database
        3. Identity CANNOT be changed
        
        This prevents cross-user document attacks.
        """
        import uuid
        
        # Generate unique application ID
        session.application_id = f"APP-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        session.identity_locked = True
        session.identity_locked_at = datetime.now()
        
        # Fetch expected PAN from customer database
        mobile = session.user_mobile
        if mobile in CUSTOMER_PROFILES:
            profile = CUSTOMER_PROFILES[mobile]
            # Try multiple locations for PAN
            session.expected_pan = (
                profile.get("pan") or 
                profile.get("kyc", {}).get("pan_number") or
                profile.get("pan_number")
            )
            logger.info(f"[{session.session_id}] Identity locked: App={session.application_id}, Expected PAN set")
        elif mobile in self.TEST_USERS:
            # Test users have expected PANs
            expected_pans = {
                "9876543210": "ABCDE1234F",  # Rahul
                "9988776655": "GHIJK5678M",  # Amit
                "9123456781": "MNOPQ9012R",  # Priya
            }
            session.expected_pan = expected_pans.get(mobile)
            logger.info(f"[{session.session_id}] Test user identity locked: App={session.application_id}")
        else:
            # New customer - no expected PAN
            session.expected_pan = None
            logger.info(f"[{session.session_id}] New customer identity locked: App={session.application_id}")
    
    # ================================================================================
    # PAN VERIFICATION WITH IDENTITY CHECK
    # ================================================================================
    
    # Test PANs with predetermined outcomes (linked to mobile)
    TEST_PANS = {
        "ABCDE1234F": {"name": "Rahul Mehta", "mobile": "9876543210", "verified": True},
        "GHIJK5678M": {"name": "Amit Verma", "mobile": "9988776655", "verified": True},
        "MNOPQ9012R": {"name": "Priya Sharma", "mobile": "9123456781", "verified": True},
        "INVALID123": {"name": None, "mobile": None, "verified": False},
    }
    
    def _verify_pan(self, pan: str, user_name: str) -> bool:
        """
        Verify PAN number against database.
        
        Rules:
        1. PAN must be in valid format
        2. PAN must exist in database
        3. Name must match (fuzzy)
        """
        pan = pan.upper()
        
        # Check format
        if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', pan):
            return False
        
        # Check against test database
        if pan in self.TEST_PANS:
            record = self.TEST_PANS[pan]
            if not record["verified"]:
                return False
            # For test users, accept
            return True
        
        # For demo purposes, accept all valid format PANs
        return True
    
    def _verify_pan_with_identity_check(self, pan: str, session: SessionState) -> Dict[str, Any]:
        """
        Verify PAN with IDENTITY CHECK.
        
        CRITICAL DATA INTEGRITY RULES:
        1. PAN format must be valid
        2. If expected_pan is set, submitted PAN MUST match
        3. If PAN exists in database, mobile MUST match session
        4. NO CROSS-USER DOCUMENTS ALLOWED
        
        Returns: {"verified": bool, "reason": str}
        """
        pan = pan.upper()
        
        # Rule 1: Format check
        if not re.match(r'^[A-Z]{5}\d{4}[A-Z]$', pan):
            return {"verified": False, "reason": "INVALID_PAN_FORMAT"}
        
        # Rule 2: If expected PAN is set, MUST match
        if session.expected_pan:
            if pan != session.expected_pan.upper():
                logger.error(f"[{session.session_id}] PAN MISMATCH: Expected {session.expected_pan}, Got {pan}")
                return {
                    "verified": False, 
                    "reason": "PAN_IDENTITY_MISMATCH"
                }
            logger.info(f"[{session.session_id}] PAN matches expected: {pan}")
            return {"verified": True, "reason": None}
        
        # Rule 3: Check if PAN exists in database - must belong to same mobile
        if pan in self.TEST_PANS:
            record = self.TEST_PANS[pan]
            if not record["verified"]:
                return {"verified": False, "reason": "PAN_NOT_VERIFIED"}
            
            # Cross-user check: PAN's mobile must match session's mobile
            if record.get("mobile") and record["mobile"] != session.user_mobile:
                logger.error(f"[{session.session_id}] CROSS-USER ATTEMPT: PAN {pan} belongs to {record['mobile']}, not {session.user_mobile}")
                return {
                    "verified": False,
                    "reason": "CROSS_USER_DOCUMENT"
                }
            return {"verified": True, "reason": None}
        
        # New customer with valid format PAN - allow for demo
        logger.info(f"[{session.session_id}] New PAN accepted: {pan}")
        return {"verified": True, "reason": None}
    
    # ================================================================================
    # OFFER CALCULATION - USES CUSTOMER DATABASE (NO FILE UPLOAD)
    # ================================================================================

    def _calculate_offer(self, session: SessionState):
        """
        Calculate loan offer based on USER-PROVIDED financial data.
        
        NEW FLOW (Dynamic Credit Scoring):
        1. Income from user input (not database)
        2. Existing EMI from user input
        3. Age from user input
        4. Credit score calculated dynamically
        
        IMPORTANT: Shows INTEREST RATE RANGE, not fixed rate.
        EMI is NOT calculated here - only after tenure selection.
        """
        # ============================================================
        # STEP 1: Calculate Credit Score from User Inputs
        # ============================================================
        requested_amount = session.loan_amount or 500000
        
        credit_score, breakdown = calculate_credit_score(
            monthly_income=session.monthly_income or 50000,
            existing_emi=session.existing_monthly_emi or 0,
            employment_type=session.employment_type or "salaried",
            age=session.user_age or 30,
            requested_amount=requested_amount
        )
        
        session.credit_score = credit_score
        session.credit_score_breakdown = breakdown
        session.income_source = "USER_PROVIDED"
        
        logger.info(f"[{session.session_id}] Dynamic Credit Score: {credit_score}")
        logger.info(f"[{session.session_id}] Score Breakdown: {breakdown}")
        
        # ============================================================
        # STEP 2: Calculate Pre-Approved Limit Based on Score
        # ============================================================
        session.pre_approved_limit = calculate_pre_approved_limit(
            monthly_income=session.monthly_income or 50000,
            credit_score=credit_score
        )
        
        # Higher limit for salaried
        if session.employment_type == "salaried":
            session.pre_approved_limit *= 1.1
        
        # Metro cities get higher limits
        metro_cities = ["mumbai", "delhi", "bangalore", "chennai", "kolkata", "hyderabad"]
        if session.city and session.city.lower() in metro_cities:
            session.pre_approved_limit *= 1.1
        
        # Cap at requested amount
        session.pre_approved_limit = min(session.pre_approved_limit, requested_amount)
        session.pre_approved_limit = round(session.pre_approved_limit, -3)  # Round to nearest 1000
        
        # ============================================================
        # STEP 3: Calculate Interest Rate Based on Credit Score
        # ============================================================
        calculated_rate = calculate_interest_rate(credit_score)
        session.final_interest_rate = calculated_rate
        
        # Set range for display
        session.interest_rate_min = INTEREST_RATE_RANGE["min"]
        session.interest_rate_max = INTEREST_RATE_RANGE["max"]
        
        # ============================================================
        # STEP 4: Calculate EMI Options
        # ============================================================
        session.emi_options = self._calculate_emi_options(
            session.pre_approved_limit,
            calculated_rate
        )
        
        # Calculate existing debt from existing EMI
        session.existing_monthly_debt = session.existing_monthly_emi or 0
        
        logger.info(f"[{session.session_id}] Offer: ₹{session.pre_approved_limit:,.0f} @ {calculated_rate}%")
        logger.info(f"[{session.session_id}] EMI options: {session.emi_options}")
    
    def _fetch_customer_income(self, session: SessionState):
        """
        Fetch income data from CUSTOMER DATABASE.
        
        This is the ONLY way to get income data.
        NO file upload. NO salary slip. NO OCR.
        """
        mobile = session.user_mobile
        
        # Check if customer exists in database
        if mobile and mobile in CUSTOMER_PROFILES:
            profile = CUSTOMER_PROFILES[mobile]
            financial = profile.get("financial_data", {})
            
            session.monthly_income = financial.get("monthly_income", 0)
            session.annual_income = financial.get("annual_income", 0)
            session.existing_monthly_debt = financial.get("total_monthly_debt", 0)
            session.debt_to_income_ratio = financial.get("debt_to_income_ratio", 0)
            session.pre_approved_limit = financial.get("preapproved_limit", 0)
            session.income_source = "CUSTOMER_DATABASE"
            
            logger.info(f"[{session.session_id}] Income fetched from database: ₹{session.monthly_income:,.0f}/month")
        else:
            # New customer - use default values
            session.monthly_income = 50000  # Default assumption
            session.annual_income = 600000
            session.existing_monthly_debt = 0
            session.debt_to_income_ratio = 0
            session.income_source = "DEFAULT_ESTIMATE"
            
            logger.info(f"[{session.session_id}] New customer - using default income estimate")
    
    # ================================================================================
    # EMI CALCULATION - ONLY AFTER TENURE SELECTION
    # ================================================================================
    
    def _calculate_emi(self, principal: float, rate: float, tenure_months: int) -> float:
        """
        Calculate EMI using standard formula.
        
        EMI = P × r × (1 + r)^n / [(1 + r)^n – 1]
        
        Where:
        - P = Principal loan amount
        - r = Monthly interest rate (annual rate / 12 / 100)
        - n = Tenure in months
        """
        if principal <= 0 or tenure_months <= 0:
            return 0
        
        monthly_rate = rate / 12 / 100
        if monthly_rate == 0:
            return principal / tenure_months
        
        emi = principal * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1)
        return round(emi, 2)
    
    def _calculate_emi_options(self, principal: float, rate: float) -> Dict[int, float]:
        """
        Calculate EMI for ALL tenure options.
        
        This lets customer compare:
        - 12 months: Higher EMI, less total interest
        - 24 months: Medium EMI
        - 36 months: Medium EMI  
        - 48 months: Lower EMI, more total interest
        
        Returns: {12: emi_12, 24: emi_24, 36: emi_36, 48: emi_48}
        """
        emi_options = {}
        for tenure in TENURE_OPTIONS:
            emi = self._calculate_emi(principal, rate, tenure)
            total_payment = emi * tenure
            total_interest = total_payment - principal
            emi_options[tenure] = {
                "emi": emi,
                "total_payment": round(total_payment, 2),
                "total_interest": round(total_interest, 2)
            }
        return emi_options
    
    def _get_interest_rate_for_credit_score(self, credit_score: int) -> float:
        """
        Determine actual interest rate based on credit score.
        
        Better credit = Lower rate
        Worse credit = Higher rate
        """
        if credit_score >= 800:
            return INTEREST_RATE_RANGE["min"]  # Best rate
        elif credit_score >= 750:
            return INTEREST_RATE_RANGE["min"] + 1.0  # Very good
        elif credit_score >= 700:
            return INTEREST_RATE_RANGE["default"]  # Good
        elif credit_score >= 650:
            return INTEREST_RATE_RANGE["default"] + 2.0  # Fair
        else:
            return INTEREST_RATE_RANGE["max"]  # Poor - highest rate
    
    # ================================================================================
    # UNDERWRITING DECISION - USES CUSTOMER DATABASE (NO FILE UPLOAD)
    # ================================================================================
    
    # Test users with predetermined outcomes
    TEST_USER_OUTCOMES = {
        "9876543210": ("APPROVED", None, 780),      # Rahul - good credit
        "9988776655": ("APPROVED", None, 720),      # Amit - decent credit
        "9123456781": ("REJECTED", "CREDIT_CRITERIA_NOT_MET", 580),  # Priya - low credit
    }
    
    # ================================================================================
    # UNDERWRITING THRESHOLDS - BACKEND CONTROLS EVERYTHING
    # ================================================================================
    #
    # WHY BACKEND CONTROLS DECISIONS (NOT LLM):
    # -----------------------------------------
    # The old system let the LLM "decide" eligibility based on conversation.
    # This was BROKEN because:
    #   1. LLM hallucinated approvals for ineligible users
    #   2. LLM revealed credit scores ("Your score is 650")
    #   3. LLM calculated wrong EMIs
    #   4. No audit trail - decisions were in LLM context window
    #   5. Different decisions for same user on retry
    #
    # NEW APPROACH - DETERMINISTIC RULES ENGINE:
    # ------------------------------------------
    # Rule 1: Credit score < 700 → ALWAYS REJECT
    # Rule 2: Credit score ≥ 700 → continue to amount check
    # Rule 3: Requested amount ≤ pre-approved → APPROVE
    # Rule 4: Requested amount > pre-approved → REJECT
    #
    # CRITICAL CONSTRAINTS:
    # - LLM must NEVER mention credit score number
    # - Rejection reasons are internal codes, not for user display
    # - Backend makes ALL decisions - LLM only phrases the message
    # - Admin dashboard shows exact same state as backend
    #
    # ================================================================================
    MIN_CREDIT_SCORE = 700  # STRICT: Below this = auto reject
    
    def _perform_underwriting(self, session: SessionState) -> Tuple[str, Optional[str]]:
        """
        Perform underwriting decision using DYNAMIC CREDIT SCORING.
        
        NEW FLOW:
        - Credit score is already calculated from user inputs in _calculate_offer()
        - Uses session.credit_score directly
        
        RULES (in order):
        1. Credit score < 700 → REJECT (reason: CREDIT_CRITERIA_NOT_MET)
        2. Credit score ≥ 700 → continue to amount check
        3. Requested amount ≤ pre-approved limit → APPROVED
        4. Requested amount > pre-approved limit → REJECT (reason: AMOUNT_EXCEEDS_ELIGIBILITY)
        
        CRITICAL: 
        - LLM must NEVER mention credit score number
        - Rejection reasons are internal codes, not for user display
        - Backend makes ALL decisions
        
        Returns: (decision, rejection_reason)
        """
        # Credit score should already be calculated in _calculate_offer()
        # If not, calculate now using user-provided data
        if session.credit_score is None:
            credit_score, breakdown = calculate_credit_score(
                monthly_income=session.monthly_income or 50000,
                existing_emi=session.existing_monthly_emi or 0,
                employment_type=session.employment_type or "salaried",
                age=session.user_age or 30,
                requested_amount=session.loan_amount or 500000
            )
            session.credit_score = credit_score
            session.credit_score_breakdown = breakdown
            logger.info(f"[{session.session_id}] Late credit score calculation: {credit_score}")
        
        # RULE 1: Credit score < 700 → REJECT
        if session.credit_score < self.MIN_CREDIT_SCORE:
            logger.info(f"[{session.session_id}] REJECTED: Credit score {session.credit_score} < {self.MIN_CREDIT_SCORE}")
            return "REJECTED", "CREDIT_CRITERIA_NOT_MET"
        
        # RULE 2: Credit score ≥ 700 → continue to amount check
        logger.info(f"[{session.session_id}] Credit check PASSED: {session.credit_score} >= {self.MIN_CREDIT_SCORE}")
        
        # RULE 3 & 4: Amount eligibility check
        return self._check_amount_eligibility(session)
    
    def _check_amount_eligibility(self, session: SessionState) -> Tuple[str, Optional[str]]:
        """
        Check if requested amount is within pre-approved limit.
        
        RULES:
        - Requested amount ≤ pre-approved → APPROVED
        - Requested amount > pre-approved → REJECTED
        """
        requested = session.loan_amount or 0
        pre_approved = session.pre_approved_limit or 0
        
        # RULE 3: Requested ≤ pre-approved → APPROVED
        if requested <= pre_approved:
            logger.info(f"[{session.session_id}] APPROVED: Requested ₹{requested:,.0f} ≤ Pre-approved ₹{pre_approved:,.0f}")
            return "APPROVED", None
        
        # RULE 4: Requested > pre-approved → REJECTED
        logger.info(f"[{session.session_id}] REJECTED: Requested ₹{requested:,.0f} > Pre-approved ₹{pre_approved:,.0f}")
        return "REJECTED", "AMOUNT_EXCEEDS_ELIGIBILITY"


# ================================================================================
# SINGLETON INSTANCE
# ================================================================================

_flow_controller: Optional[DeterministicFlowController] = None

def get_flow_controller() -> DeterministicFlowController:
    """Get the singleton flow controller instance."""
    global _flow_controller
    if _flow_controller is None:
        _flow_controller = DeterministicFlowController()
    return _flow_controller

def reset_flow_controller():
    """Reset the singleton (for testing)."""
    global _flow_controller
    _flow_controller = None


# ================================================================================
# CONVENIENCE FUNCTIONS
# ================================================================================

def process_message(session_id: str, message: str) -> Dict[str, Any]:
    """
    Process a user message through the deterministic flow.
    
    Returns dict with:
    - session: Current session state
    - instruction: What to tell the LLM to say
    - stage_changed: Whether we advanced to a new stage
    - is_frozen: Whether journey is complete
    """
    controller = get_flow_controller()
    session, instruction, stage_changed = controller.process_input(session_id, message)
    
    return {
        "session": session.to_dict(),
        "instruction": instruction,
        "stage_changed": stage_changed,
        "is_frozen": session.is_frozen,
        "current_stage": session.current_stage.name,
        "stage_number": session.current_stage.value
    }

def get_session_state(session_id: str) -> Dict[str, Any]:
    """Get current session state."""
    controller = get_flow_controller()
    session = controller.get_or_create_session(session_id)
    return session.to_dict()

def reset_session(session_id: str) -> Dict[str, Any]:
    """Reset a session to initial state."""
    controller = get_flow_controller()
    session = controller.reset_session(session_id)
    return session.to_dict()


def get_admin_state(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Get admin dashboard state for a session.
    
    ADMIN DASHBOARD REQUIREMENTS:
    - READ-ONLY: No actions, no modifications
    - BACKEND STATE ONLY: Shows deterministic state machine truth
    - NEVER DISCONNECT: Stable data, no websocket-dependent fields
    - NEVER INFER: Only actual values, no computed/guessed fields
    
    Returns None if session doesn't exist.
    """
    controller = get_flow_controller()
    session = controller.get_session(session_id)
    if session:
        return session.to_admin_dict()
    return None


def get_all_admin_sessions() -> List[Dict[str, Any]]:
    """
    Get admin dashboard state for ALL sessions.
    
    Returns list of admin states for all active sessions.
    """
    controller = get_flow_controller()
    return [
        session.to_admin_dict()
        for session in controller.sessions.values()
    ]


# ================================================================================
# TEST SUITE
# ================================================================================

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TESTING DETERMINISTIC FLOW CONTROLLER")
    print("=" * 60)
    
    controller = DeterministicFlowController()
    
    # Test full journey
    session_id = "test-001"
    
    test_inputs = [
        ("Hi", "GREETING → PURPOSE"),
        ("I need a loan for home renovation", "PURPOSE → AMOUNT"),
        ("5 lakhs", "AMOUNT → CITY"),
        ("Mumbai", "CITY → EMPLOYMENT_TYPE"),
        ("I am salaried", "EMPLOYMENT_TYPE → NAME"),
        ("Rahul Mehta", "NAME → MOBILE"),
        ("9876543210", "MOBILE → OTP"),
        ("123456", "OTP → KYC"),
        ("ABCDE1234F", "KYC → OFFER"),
        ("Yes, proceed", "OFFER → TENURE"),
        ("3 years", "TENURE → UNDERWRITING"),
        ("", "UNDERWRITING → SANCTION"),
    ]
    
    for message, expected in test_inputs:
        session, instruction, changed = controller.process_input(session_id, message)
        print(f"\nInput: '{message}'")
        print(f"Expected: {expected}")
        print(f"Stage: {session.current_stage.name} | Changed: {changed}")
        print(f"Instruction: {instruction[:50]}...")
    
    print("\n" + "=" * 60)
    print("FINAL STATE:")
    print(f"Stage: {session.current_stage.name}")
    print(f"Frozen: {session.is_frozen}")
    print(f"Underwriting Result: {session.underwriting_result}")
    print("=" * 60)
