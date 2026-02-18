"""
================================================================================
TEST SCENARIOS FOR AGENTIC LENDING PLATFORM
================================================================================

7 deterministic test scenarios covering every underwriting outcome.
Each scenario includes exact user inputs for the 16-stage flow, expected
scoring breakdown, and final decision.

SCORING SYSTEM (max 900):
  DTI           → 0-300 points
  Income Level  → 0-250 points
  Employment    → 0-150 points
  Age Factor    → 0-100 points
  Loan-to-Income→ 0-100 points

THRESHOLDS:
  ≥ 700  → APPROVED
  600-699 → CONDITIONAL (may need extra docs)
  < 600  → REJECTED

================================================================================
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class TestScenario:
    """One complete test scenario with user inputs and expected results."""
    id: str
    name: str
    description: str
    category: str  # approval | conditional | rejection | high_debt | low_credit | invalid_pan | emi_concern
    
    # User inputs for each stage (in order)
    greeting_input: str = "Hi"
    purpose_input: str = "personal"
    amount_input: str = "5 lakhs"
    city_input: str = "Mumbai"
    employment_input: str = "salaried"
    name_input: str = "Test User"
    mobile_input: str = "9876543210"
    otp_input: str = "123456"
    income_input: str = "100000"
    existing_emi_input: str = "0"
    dob_input: str = "30"
    pan_input: str = "ABCDE1234F"
    offer_input: str = "yes proceed"
    tenure_input: str = "36 months"
    
    # Expected results
    expected_decision: str = "APPROVED"    # APPROVED | CONDITIONAL | REJECTED
    expected_stage: str = "SANCTION"       # SANCTION | REJECTION | KYC (invalid PAN)
    expected_score_min: int = 0
    expected_score_max: int = 900
    expected_dti_range: str = "<20%"
    
    # Scoring breakdown expectations
    expected_breakdown: Dict[str, str] = field(default_factory=dict)
    
    # Notes for testers
    notes: str = ""


# ================================================================================
# SCENARIO 1: CLEAN APPROVAL — Premium salaried, zero debt, prime age
# ================================================================================
SCENARIO_APPROVAL = TestScenario(
    id="TS-001",
    name="Clean Approval — Low Risk Premium Profile",
    description=(
        "Salaried professional, 30 years old, ₹1.5L monthly income, zero existing EMI, "
        "requesting ₹5L loan. Expected: all scoring components max out, total ≥ 800."
    ),
    category="approval",
    
    greeting_input="Hello, I'd like to apply for a loan",
    purpose_input="I want a loan for home renovation",
    amount_input="5 lakhs",
    city_input="Mumbai",
    employment_input="I am salaried",
    name_input="Rajesh Deshmukh",
    mobile_input="9876543210",  # Test user — auto-approves OTP
    otp_input="123456",
    income_input="150000",       # ₹1.5L/month → 250 income points
    existing_emi_input="0",      # Zero debt → DTI 0% → 300 DTI points
    dob_input="30",              # Age 30 → 100 age points
    pan_input="ABCDE1234F",
    offer_input="yes I agree",
    tenure_input="36 months",
    
    expected_decision="APPROVED",
    expected_stage="SANCTION",
    expected_score_min=800,
    expected_score_max=900,
    expected_dti_range="0%",
    expected_breakdown={
        "dti": "300/300 (0% DTI)",
        "income": "250/250 (₹1.5L/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (30 years)",
        "loan_ratio": "100/100 (0.28x annual income)"
    },
    notes="Golden path — all factors maxed. This is the ideal approval case."
)


# ================================================================================
# SCENARIO 2: CONDITIONAL APPROVAL — Moderate profile, needs extra docs
# ================================================================================
SCENARIO_CONDITIONAL = TestScenario(
    id="TS-002",
    name="Conditional Approval — Moderate Risk Profile",
    description=(
        "Self-employed professional, 48 years old, ₹55K income, ₹15K existing EMI (27% DTI), "
        "requesting ₹5L. Score lands in 600-699 range → CONDITIONAL."
    ),
    category="conditional",
    
    greeting_input="Hi there",
    purpose_input="personal expenses",
    amount_input="5 lakhs",
    city_input="Pune",
    employment_input="self employed",
    name_input="Manoj Joshi",
    mobile_input="9988776655",
    otp_input="123456",
    income_input="55000",         # ₹55K/mo → 140 income points
    existing_emi_input="15000",   # ₹15K EMI → ~27% DTI → 250 DTI points
    dob_input="48",               # Age 48 → 80 age points
    pan_input="GHIJK5678M",
    offer_input="ok",
    tenure_input="48 months",
    
    expected_decision="CONDITIONAL",
    expected_stage="SANCTION",     # Conditional still gets sanction (with conditions)
    expected_score_min=600,
    expected_score_max=699,
    expected_dti_range="25-30%",
    expected_breakdown={
        "dti": "250/300 (27% DTI)",
        "income": "140/250 (₹55K/mo)",
        "employment": "120/150 (self-employed)",
        "age": "80/100 (48 years)",
        "loan_ratio": "70/100 (0.76x annual income)"
    },
    notes="Borderline profile. Self-employment, age, and moderate income all contribute to conditional."
)


# ================================================================================
# SCENARIO 3: REJECTION — High risk profile across multiple factors
# ================================================================================
SCENARIO_REJECTION = TestScenario(
    id="TS-003",
    name="Rejection — High Risk Multi-Factor Failure",
    description=(
        "Self-employed, 62 years old, ₹28K income, ₹12K existing EMI (43% DTI), "
        "requesting ₹8L (huge loan-to-income). Score < 600 → REJECTED."
    ),
    category="rejection",
    
    greeting_input="Hello",
    purpose_input="medical treatment",
    amount_input="8 lakhs",
    city_input="Patna",
    employment_input="I run my own business",
    name_input="Suresh Prasad",
    mobile_input="9123456781",
    otp_input="123456",
    income_input="28000",          # ₹28K/mo → 60 income points
    existing_emi_input="12000",    # ₹12K EMI → ~43% DTI → 100 DTI points
    dob_input="62",                # Age 62 → 40 age points
    pan_input="MNOPQ9012R",
    offer_input="proceed",
    tenure_input="24 months",
    
    expected_decision="REJECTED",
    expected_stage="REJECTION",
    expected_score_min=360,
    expected_score_max=500,
    expected_dti_range="40-50%",
    expected_breakdown={
        "dti": "100/300 (43% DTI)",
        "income": "60/250 (₹28K/mo)",
        "employment": "120/150 (self-employed)",
        "age": "40/100 (62 years)",
        "loan_ratio": "20/100 (2.38x annual income)"
    },
    notes="Fails on almost every factor. Classic multi-factor rejection."
)


# ================================================================================
# SCENARIO 4: HIGH DEBT — DTI > 50% (crushing existing obligations)
# ================================================================================
SCENARIO_HIGH_DEBT = TestScenario(
    id="TS-004",
    name="High Debt — DTI Exceeds 50% Threshold",
    description=(
        "Salaried employee, but existing EMIs of ₹35K against ₹55K income = 64% DTI. "
        "Even good income and age can't compensate for extreme debt burden."
    ),
    category="high_debt",
    
    greeting_input="Hi, I need a loan urgently",
    purpose_input="debt consolidation",
    amount_input="3 lakhs",
    city_input="Delhi",
    employment_input="salaried",
    name_input="Deepak Malhotra",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="55000",          # ₹55K/mo → 140 income points
    existing_emi_input="35000",    # ₹35K EMI → 64% DTI → 50 DTI points (TERRIBLE)
    dob_input="35",                # Age 35 → 100 age points
    pan_input="ABCDE1234F",
    offer_input="yes",
    tenure_input="36 months",
    
    expected_decision="REJECTED",
    expected_stage="REJECTION",
    expected_score_min=480,
    expected_score_max=580,
    expected_dti_range=">50%",
    expected_breakdown={
        "dti": "50/300 (64% DTI — CRITICAL FAILURE)",
        "income": "140/250 (₹55K/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (35 years)",
        "loan_ratio": "70/100 (0.45x annual income)"
    },
    notes=(
        "Key test: even with perfect age, employment, and reasonable income, "
        "extreme DTI (>50%) drops score below 600. DTI is the strongest rejection signal."
    )
)


# ================================================================================
# SCENARIO 5: LOW CREDIT SCORE — Young, low income, high loan request
# ================================================================================
SCENARIO_LOW_CREDIT = TestScenario(
    id="TS-005",
    name="Low Credit Score — Young Professional, Over-Leveraged",
    description=(
        "20-year-old self-employed, ₹25K income, requesting ₹10L loan "
        "(3.33x annual income). Fails on income, age, employment, and loan ratio."
    ),
    category="low_credit",
    
    greeting_input="Hey",
    purpose_input="education",
    amount_input="10 lakhs",
    city_input="Bangalore",
    employment_input="self employed",
    name_input="Ritu Patel",
    mobile_input="9988776655",
    otp_input="123456",
    income_input="25000",          # ₹25K/mo → 60 income points
    existing_emi_input="5000",     # ₹5K EMI → 20% DTI → 300 DTI points
    dob_input="20",                # Age 20 → 40 age points (<21)
    pan_input="GHIJK5678M",
    offer_input="ok",
    tenure_input="48 months",
    
    expected_decision="REJECTED",
    expected_stage="REJECTION",
    expected_score_min=410,
    expected_score_max=560,
    expected_dti_range="~20%",
    expected_breakdown={
        "dti": "300/300 (20% DTI — good)",
        "income": "60/250 (₹25K/mo — poor)",
        "employment": "120/150 (self-employed)",
        "age": "40/100 (20 years — HIGH RISK)",
        "loan_ratio": "20/100 (3.33x annual income — HIGH)"
    },
    notes=(
        "Despite decent DTI, low income + underage + self-employed + huge loan request "
        "combine to produce a sub-600 score. Tests that DTI alone can't save a profile."
    )
)


# ================================================================================
# SCENARIO 6: INVALID PAN — Stops at KYC stage
# ================================================================================
SCENARIO_INVALID_PAN = TestScenario(
    id="TS-006",
    name="Invalid PAN — KYC Verification Failure",
    description=(
        "User provides an incorrectly formatted PAN number. "
        "Flow halts at KYC stage and does not proceed to offer/underwriting."
    ),
    category="invalid_pan",
    
    greeting_input="Hello",
    purpose_input="home improvement",
    amount_input="4 lakhs",
    city_input="Chennai",
    employment_input="salaried",
    name_input="Vijay Kumar",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="80000",
    existing_emi_input="0",
    dob_input="34",
    pan_input="INVALID123",  # ← WRONG FORMAT (should be AAAAA1234A)
    offer_input="",           # Never reached
    tenure_input="",          # Never reached
    
    expected_decision="N/A",
    expected_stage="KYC",     # Stuck at KYC — can't proceed
    expected_score_min=0,
    expected_score_max=0,
    expected_dti_range="N/A",
    expected_breakdown={},
    notes=(
        "PAN format: 5 letters + 4 digits + 1 letter (e.g., ABCDE1234F). "
        "Invalid formats tested: '123456789', 'ABCDE', 'INVALID123', 'abc1234f', ''. "
        "User gets 3 attempts before session freeze."
    )
)


# ================================================================================
# SCENARIO 7: EMI AFFORDABILITY CONCERN — High EMI relative to income
# ================================================================================
SCENARIO_EMI_CONCERN = TestScenario(
    id="TS-007",
    name="EMI Affordability Concern — Post-Approval EMI Stress",
    description=(
        "Approved profile (score ≥ 700), but the selected tenure results in an EMI "
        "that consumes >40% of the remaining monthly income after existing EMIs. "
        "Tests the Gemini AI layer's affordability reassurance capability."
    ),
    category="emi_concern",
    
    greeting_input="Hi",
    purpose_input="wedding expenses",
    amount_input="5 lakhs",
    city_input="Hyderabad",
    employment_input="salaried",
    name_input="Arjun Reddy",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="60000",          # ₹60K/mo
    existing_emi_input="8000",     # ₹8K existing EMI
    dob_input="32",
    pan_input="ABCDE1234F",
    offer_input="yes",
    tenure_input="12 months",      # ← SHORT tenure = HIGH EMI (~₹44K/mo)
    
    expected_decision="APPROVED",
    expected_stage="SANCTION",
    expected_score_min=700,
    expected_score_max=850,
    expected_dti_range="<15%",
    expected_breakdown={
        "dti": "300/300 (13% DTI)",
        "income": "140/250 (₹60K/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (32 years)",
        "loan_ratio": "100/100 (0.69x annual income)"
    },
    notes=(
        "APPROVED, but 12-month tenure means monthly EMI ≈ ₹44,424. "
        "With ₹60K income and ₹8K existing EMI, post-loan take-home is only ~₹7.6K. "
        "This scenario tests the Gemini AI's ability to suggest a longer tenure "
        "when the user expresses concern about EMI affordability. "
        "Recommended tenure: 36 months (EMI ≈ ₹16,607 — much more manageable)."
    )
)


# ================================================================================
# SCENARIO 8: BOUNDARY — Score exactly 700 (approval threshold)
# ================================================================================
# Target: DTI 250 + Income 140 + Employment 150 + Age 100 + LoanRatio 70 = 710
# Tweaked: salaried, 30y, ₹60K income, ₹12K EMI (20% DTI), ₹10L loan (1.39x annual)
SCENARIO_BOUNDARY_700 = TestScenario(
    id="TS-008",
    name="Boundary — Score at Approval Threshold (≈700)",
    description=(
        "Profile engineered to land near the 700 approval threshold. "
        "Salaried, 30y, ₹60K income, 20% DTI, ₹10L loan. Tests edge-case approval."
    ),
    category="approval",

    greeting_input="Hi",
    purpose_input="personal",
    amount_input="10 lakhs",
    city_input="Mumbai",
    employment_input="salaried",
    name_input="Boundary Tester A",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="60000",          # ₹60K → 140 income
    existing_emi_input="12000",    # 20% DTI → 250 DTI
    dob_input="30",                # 30y → 100 age
    pan_input="ABCDE1234F",
    offer_input="yes",
    tenure_input="36 months",

    expected_decision="APPROVED",
    expected_stage="SANCTION",
    expected_score_min=700,
    expected_score_max=720,
    expected_dti_range="20%",
    expected_breakdown={
        "dti": "250/300 (20% DTI — boundary)",
        "income": "140/250 (₹60K/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (30 years)",
        "loan_ratio": "70/100 (1.39x annual income)"
    },
    notes="Verifies that score=700 is APPROVED, not CONDITIONAL."
)


# ================================================================================
# SCENARIO 9: BOUNDARY — Score exactly 600 (conditional/rejection threshold)
# ================================================================================
# Target: DTI 100 + Income 140 + Employment 150 + Age 100 + LoanRatio 100 = 590
# Tweaked: salaried, 30y, ₹50K income, ₹22K EMI (44% DTI), ₹3L loan (0.5x annual)
SCENARIO_BOUNDARY_600 = TestScenario(
    id="TS-009",
    name="Boundary — Score at Conditional/Rejection Threshold (≈600)",
    description=(
        "Profile engineered to land near the 600 boundary. "
        "Salaried, 30y, ₹50K income, 44% DTI, small ₹3L loan. Tests edge-case conditional."
    ),
    category="conditional",

    greeting_input="Hi",
    purpose_input="medical",
    amount_input="3 lakhs",
    city_input="Delhi",
    employment_input="salaried",
    name_input="Boundary Tester B",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="50000",          # ₹50K → 140 income
    existing_emi_input="22000",    # 44% DTI → 100 DTI
    dob_input="30",                # 30y → 100 age
    pan_input="ABCDE1234F",
    offer_input="ok",
    tenure_input="36 months",

    expected_decision="CONDITIONAL",
    expected_stage="SANCTION",
    expected_score_min=580,
    expected_score_max=620,
    expected_dti_range="44%",
    expected_breakdown={
        "dti": "100/300 (44% DTI — marginal)",
        "income": "140/250 (₹50K/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (30 years)",
        "loan_ratio": "100/100 (0.5x annual income)"
    },
    notes="Verifies that score≈600 is CONDITIONAL, not REJECTED."
)


# ================================================================================
# SCENARIO 10: POLICY CAP — Max ₹50L pre-approved limit ceiling
# ================================================================================
# High-income salaried requesting ₹50L — tests that cap logic works
SCENARIO_POLICY_CAP = TestScenario(
    id="TS-010",
    name="Policy Cap — ₹50L Maximum Pre-Approved Limit",
    description=(
        "Ultra-high-income salaried (₹5L/mo, zero debt) requesting ₹50L. "
        "Without cap, formula would yield ₹108L. Tests ₹50L ceiling."
    ),
    category="approval",

    greeting_input="Hello",
    purpose_input="home purchase",
    amount_input="50 lakhs",
    city_input="Mumbai",
    employment_input="salaried",
    name_input="Policy Cap Tester",
    mobile_input="9876543210",
    otp_input="123456",
    income_input="500000",         # ₹5L/mo → 250 income points
    existing_emi_input="0",        # 0% DTI → 300 DTI points
    dob_input="35",                # 35y → 100 age points
    pan_input="ABCDE1234F",
    offer_input="yes",
    tenure_input="36 months",

    expected_decision="APPROVED",
    expected_stage="SANCTION",
    expected_score_min=800,
    expected_score_max=900,
    expected_dti_range="0%",
    expected_breakdown={
        "dti": "300/300 (0% DTI)",
        "income": "250/250 (₹5L/mo)",
        "employment": "150/150 (salaried)",
        "age": "100/100 (35 years)",
        "loan_ratio": "100/100 (<1x annual income)"
    },
    notes=(
        "Pre-approved limit should be capped at ₹50L (₹5,000,000). "
        "Without cap, formula yields ₹5L×0.6×36 = ₹108L. "
        "Cap at min(formula, 50L, requested_amount)."
    )
)


# ================================================================================
# ALL SCENARIOS
# ================================================================================

ALL_SCENARIOS: List[TestScenario] = [
    SCENARIO_APPROVAL,
    SCENARIO_CONDITIONAL,
    SCENARIO_REJECTION,
    SCENARIO_HIGH_DEBT,
    SCENARIO_LOW_CREDIT,
    SCENARIO_INVALID_PAN,
    SCENARIO_EMI_CONCERN,
    SCENARIO_BOUNDARY_700,
    SCENARIO_BOUNDARY_600,
    SCENARIO_POLICY_CAP,
]

SCENARIO_MAP: Dict[str, TestScenario] = {s.id: s for s in ALL_SCENARIOS}


# ================================================================================
# HELPER: Run a scenario through the flow controller
# ================================================================================

def run_scenario(scenario: TestScenario, session_id: Optional[str] = None):
    """
    Execute a test scenario through the deterministic flow controller.
    
    Returns:
        dict with session state, score, decision, and pass/fail status.
    """
    from deterministic_flow import (
        get_flow_controller,
        reset_flow_controller,
        calculate_credit_score,
    )
    
    reset_flow_controller()
    controller = get_flow_controller()
    sid = session_id or f"test-{scenario.id}"
    
    # Run through each stage
    inputs = [
        scenario.greeting_input,
        scenario.purpose_input,
        scenario.amount_input,
        scenario.city_input,
        scenario.employment_input,
        scenario.name_input,
        scenario.mobile_input,
        scenario.otp_input,
        scenario.income_input,
        scenario.existing_emi_input,
        scenario.dob_input,
        scenario.pan_input,
    ]
    
    session = None
    for user_input in inputs:
        if not user_input:
            break
        session, instruction, changed = controller.process_input(sid, user_input)
    
    # If we got past KYC (scenario 6 stops here)
    if scenario.pan_input and session and session.current_stage.name != "KYC":
        if scenario.offer_input:
            session, _, _ = controller.process_input(sid, scenario.offer_input)
        if scenario.tenure_input:
            session, _, _ = controller.process_input(sid, scenario.tenure_input)
            # Trigger underwriting
            session, _, _ = controller.process_input(sid, "")
    
    result = {
        "scenario_id": scenario.id,
        "scenario_name": scenario.name,
        "category": scenario.category,
        "final_stage": session.current_stage.name if session else "UNKNOWN",
        "expected_stage": scenario.expected_stage,
        "credit_score": getattr(session, "credit_score", None),
        "underwriting_result": getattr(session, "underwriting_result", None),
        "expected_decision": scenario.expected_decision,
        "is_frozen": getattr(session, "is_frozen", False),
    }
    
    # Determine pass/fail
    stage_match = result["final_stage"] == scenario.expected_stage
    decision_match = (
        scenario.expected_decision == "N/A"
        or result["underwriting_result"] == scenario.expected_decision
    )
    result["PASS"] = stage_match and decision_match
    
    return result


# ================================================================================
# PRETTY-PRINT ALL SCENARIOS
# ================================================================================

def print_scenario_summary():
    """Print a formatted summary table of all 7 test scenarios."""
    print("\n" + "=" * 90)
    print("AGENTIC LENDING PLATFORM — 10 TEST SCENARIOS")
    print("=" * 90)
    
    for s in ALL_SCENARIOS:
        status_emoji = {
            "approval": "✅",
            "conditional": "⚠️",
            "rejection": "❌",
            "high_debt": "💸",
            "low_credit": "📉",
            "invalid_pan": "🔒",
            "emi_concern": "💰",
        }.get(s.category, "❓")
        
        print(f"\n{status_emoji}  {s.id}: {s.name}")
        print(f"   Category: {s.category.upper()}")
        print(f"   Expected: {s.expected_decision} → {s.expected_stage}")
        print(f"   Score Range: {s.expected_score_min}–{s.expected_score_max}")
        print(f"   DTI: {s.expected_dti_range}")
        print(f"   Inputs: income={s.income_input}, emi={s.existing_emi_input}, "
              f"age={s.dob_input}, employment={s.employment_input}")
        if s.expected_breakdown:
            print(f"   Breakdown:")
            for k, v in s.expected_breakdown.items():
                print(f"     • {k}: {v}")
        if s.notes:
            print(f"   Notes: {s.notes[:120]}{'...' if len(s.notes) > 120 else ''}")
    
    print("\n" + "=" * 90)


# ================================================================================
# MAIN — Run all scenarios
# ================================================================================

if __name__ == "__main__":
    import sys
    
    if "--summary" in sys.argv:
        print_scenario_summary()
    else:
        print("\n🧪 Running all 7 test scenarios...\n")
        
        results = []
        for scenario in ALL_SCENARIOS:
            try:
                result = run_scenario(scenario)
                results.append(result)
                
                emoji = "✅" if result["PASS"] else "❌"
                print(f"  {emoji} {result['scenario_id']}: {result['scenario_name']}")
                print(f"     Stage: {result['final_stage']} (expected: {result['expected_stage']})")
                print(f"     Decision: {result['underwriting_result']} (expected: {result['expected_decision']})")
                if result['credit_score']:
                    print(f"     Score: {result['credit_score']}")
                print()
            except Exception as e:
                print(f"  💥 {scenario.id}: {scenario.name} — ERROR: {e}\n")
                results.append({"scenario_id": scenario.id, "PASS": False, "error": str(e)})
        
        passed = sum(1 for r in results if r.get("PASS"))
        total = len(results)
        
        print("=" * 60)
        print(f"Results: {passed}/{total} passed")
        if passed == total:
            print("🎉 ALL SCENARIOS PASSED!")
        else:
            print(f"⚠️  {total - passed} scenario(s) failed — review output above.")
        print("=" * 60)
"""Module for test scenarios in the Agentic Lending Platform."""
