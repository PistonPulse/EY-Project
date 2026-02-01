"""
================================================================================
PHASE 4: DETERMINISTIC UNDERWRITING RULES ENGINE
================================================================================

PURPOSE:
--------
This module implements the loan eligibility and underwriting decision logic
using deterministic rules that mirror real-world NBFC underwriting criteria.

WHY DETERMINISTIC RULES (NOT LLM):
----------------------------------
In real banking systems, loan approval/rejection decisions are NEVER made by
AI language models. They are governed by:
1. Regulatory compliance (RBI guidelines for NBFCs)
2. Risk management policies
3. Credit committee approved rules
4. Auditable decision trails

If we let an LLM decide approvals, we would face:
- Random approvals/rejections (hallucination risk)
- Regulatory non-compliance
- Audit failures
- Discrimination risks
- Legal liability

UNDERWRITING RULES IMPLEMENTED:
-------------------------------
Based on real NBFC practices, this engine implements:

Rule 1: CREDIT SCORE CHECK (Hard Cut-off)
   - If credit_score < 700 → REJECT
   - Reason: NBFCs typically have minimum CIBIL thresholds (650-750)

Rule 2: PRE-APPROVED LIMIT CHECK
   - If requested_amount ≤ preapproved_limit → INSTANT APPROVAL
   - Reason: Customer already vetted for this amount

Rule 3: EXTENDED LIMIT WITH INCOME VERIFICATION
   - If requested_amount ≤ 2x preapproved_limit → Require salary slip
   - If EMI ≤ 50% of monthly_income → APPROVE
   - Else → REJECT (EMI burden too high)
   - Reason: FOIR (Fixed Obligation to Income Ratio) is industry standard

Rule 4: EXCESS AMOUNT CHECK
   - If requested_amount > 2x preapproved_limit → REJECT
   - Reason: Risk appetite limits exceeded

EMI CALCULATION:
----------------
Uses standard amortization formula:
EMI = P × r × (1+r)^n / ((1+r)^n - 1)
Where:
- P = Principal (loan amount)
- r = Monthly interest rate
- n = Number of months (tenure)

DATA SOURCES:
-------------
All inputs come from verified backend services (Phase 3):
- credit_score → Credit Bureau Service
- preapproved_limit → Offer Mart Service
- monthly_income → CRM Service (from customer dataset)
- requested_amount → User input (NEEDS_ANALYSIS stage)

================================================================================
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# ================================================================================
# UNDERWRITING ENUMS AND CONSTANTS
# ================================================================================

class LoanStatus(Enum):
    """
    Possible loan decision outcomes.
    
    These map to real NBFC loan statuses:
    - APPROVED: Loan sanctioned, ready for disbursement
    - REJECTED: Loan declined, customer informed of reasons
    - PENDING_DOCS: Conditional approval, waiting for documents
    - UNDER_REVIEW: Manual review required (not implemented in MVP)
    """
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PENDING_DOCS = "PENDING_DOCS"
    UNDER_REVIEW = "UNDER_REVIEW"


class ApprovalType(Enum):
    """
    Types of loan approval.
    
    Real NBFCs categorize approvals by:
    - INSTANT: Pre-approved customers, minimal checks
    - INCOME_VERIFIED: Standard approval with income proof
    - COLLATERAL_BACKED: Secured loan with collateral (future)
    """
    INSTANT_PREAPPROVED = "Instant Pre-Approved"
    INCOME_VERIFIED = "Income Verified Approval"
    MANUAL_REVIEW = "Manual Review Approval"


class RejectionReason(Enum):
    """
    Standardized rejection reasons.
    
    These are compliant reasons that can be disclosed to customers.
    Real NBFCs have standardized rejection codes for regulatory reporting.
    """
    LOW_CREDIT_SCORE = "Credit score below minimum threshold"
    EMI_EXCEEDS_INCOME = "EMI exceeds 50% of monthly income"
    AMOUNT_EXCEEDS_ELIGIBILITY = "Requested amount exceeds eligibility limit"
    INSUFFICIENT_INCOME = "Monthly income does not meet minimum requirements"
    DOCUMENTS_NOT_VERIFIED = "Required documents not verified"
    HIGH_EXISTING_DEBT = "Existing debt obligations too high"


# ================================================================================
# UNDERWRITING CONFIGURATION
# ================================================================================
# These constants mirror real NBFC policy parameters.
# In production, these would be loaded from a policy management system.

class UnderwritingConfig:
    """
    Underwriting policy parameters.
    
    WHY THESE VALUES:
    -----------------
    - MIN_CREDIT_SCORE: 700 is typical for personal loans
    - DEFAULT_INTEREST_RATE: 12.5% is mid-range for unsecured loans
    - MAX_FOIR: 50% is RBI-recommended for retail lending
    - EXTENDED_LIMIT_MULTIPLIER: 2x allows room for income verification
    - DEFAULT_TENURE: 48 months is common for personal loans
    """
    
    # Credit Score Thresholds
    MIN_CREDIT_SCORE: int = 700
    EXCELLENT_SCORE: int = 800
    GOOD_SCORE: int = 750
    
    # Interest Rates (per annum)
    DEFAULT_INTEREST_RATE: float = 12.5
    EXCELLENT_RATE: float = 10.5
    GOOD_RATE: float = 11.5
    STANDARD_RATE: float = 12.5
    HIGH_RISK_RATE: float = 14.0
    
    # Income Rules
    MAX_FOIR: float = 0.50  # Fixed Obligation to Income Ratio
    MIN_MONTHLY_INCOME: float = 25000  # Minimum income requirement
    
    # Limit Rules
    EXTENDED_LIMIT_MULTIPLIER: float = 2.0  # Can request up to 2x pre-approved
    
    # Default Values
    DEFAULT_TENURE_MONTHS: int = 48
    MIN_TENURE_MONTHS: int = 12
    MAX_TENURE_MONTHS: int = 60


# ================================================================================
# UNDERWRITING DECISION RESULT
# ================================================================================

@dataclass
class UnderwritingDecision:
    """
    Result of the underwriting rules engine.
    
    This dataclass captures the complete decision for audit and display:
    - loan_status: The final decision (APPROVED/REJECTED/PENDING)
    - approval_type: Type of approval (if approved)
    - rejection_reason: Reason for rejection (if rejected)
    - calculated_emi: Monthly EMI amount
    - effective_interest_rate: Interest rate applied
    - requires_salary_slip: Whether salary slip is needed
    - decision_timestamp: When decision was made (audit trail)
    - decision_factors: Detailed breakdown of factors considered
    """
    
    # Primary Decision
    loan_status: LoanStatus
    
    # Approval Details (populated if APPROVED)
    approval_type: Optional[ApprovalType] = None
    approved_amount: float = 0
    approved_tenure_months: int = 48
    
    # Rejection Details (populated if REJECTED)
    rejection_reason: Optional[RejectionReason] = None
    rejection_details: Optional[str] = None
    
    # Calculated Values
    calculated_emi: float = 0
    effective_interest_rate: float = 0
    total_interest_payable: float = 0
    total_repayment_amount: float = 0
    
    # Conditional Requirements
    requires_salary_slip: bool = False
    salary_slip_verified: bool = False
    
    # Audit Trail
    decision_timestamp: str = ""
    decision_factors: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.decision_timestamp == "":
            self.decision_timestamp = datetime.now().isoformat()
        if self.decision_factors is None:
            self.decision_factors = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "loan_status": self.loan_status.value,
            "approval_type": self.approval_type.value if self.approval_type else None,
            "approved_amount": self.approved_amount,
            "approved_tenure_months": self.approved_tenure_months,
            "rejection_reason": self.rejection_reason.value if self.rejection_reason else None,
            "rejection_details": self.rejection_details,
            "calculated_emi": self.calculated_emi,
            "effective_interest_rate": self.effective_interest_rate,
            "total_interest_payable": self.total_interest_payable,
            "total_repayment_amount": self.total_repayment_amount,
            "requires_salary_slip": self.requires_salary_slip,
            "salary_slip_verified": self.salary_slip_verified,
            "decision_timestamp": self.decision_timestamp,
            "decision_factors": self.decision_factors,
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary of decision."""
        if self.loan_status == LoanStatus.APPROVED:
            return (
                f"✅ APPROVED ({self.approval_type.value})\n"
                f"   Amount: ₹{self.approved_amount:,.0f}\n"
                f"   EMI: ₹{self.calculated_emi:,.0f}/month\n"
                f"   Rate: {self.effective_interest_rate}% p.a.\n"
                f"   Tenure: {self.approved_tenure_months} months"
            )
        elif self.loan_status == LoanStatus.REJECTED:
            return (
                f"❌ REJECTED\n"
                f"   Reason: {self.rejection_reason.value if self.rejection_reason else 'N/A'}\n"
                f"   Details: {self.rejection_details or 'N/A'}"
            )
        elif self.loan_status == LoanStatus.PENDING_DOCS:
            return (
                f"⏳ PENDING - Salary Slip Required\n"
                f"   Provisional EMI: ₹{self.calculated_emi:,.0f}/month\n"
                f"   Upload salary slip to continue"
            )
        else:
            return f"🔄 {self.loan_status.value}"


# ================================================================================
# EMI CALCULATOR
# ================================================================================

class EMICalculator:
    """
    Standard EMI calculator using amortization formula.
    
    FORMULA:
    --------
    EMI = P × r × (1+r)^n / ((1+r)^n - 1)
    
    Where:
    - P = Principal (loan amount)
    - r = Monthly interest rate (annual rate / 12 / 100)
    - n = Number of monthly installments (tenure in months)
    
    This is the standard formula used by all banks and NBFCs.
    """
    
    @staticmethod
    def calculate_emi(
        principal: float,
        annual_interest_rate: float,
        tenure_months: int
    ) -> float:
        """
        Calculate monthly EMI.
        
        Args:
            principal: Loan amount in INR
            annual_interest_rate: Interest rate per annum (e.g., 12.5 for 12.5%)
            tenure_months: Loan tenure in months
            
        Returns:
            Monthly EMI amount in INR
        """
        if principal <= 0 or tenure_months <= 0:
            return 0
        
        if annual_interest_rate <= 0:
            # Zero interest - simple division
            return principal / tenure_months
        
        # Convert annual rate to monthly rate
        monthly_rate = annual_interest_rate / 100 / 12
        
        # EMI formula: P × r × (1+r)^n / ((1+r)^n - 1)
        emi = (
            principal * monthly_rate * 
            ((1 + monthly_rate) ** tenure_months) / 
            (((1 + monthly_rate) ** tenure_months) - 1)
        )
        
        return round(emi, 0)
    
    @staticmethod
    def calculate_total_interest(
        principal: float,
        emi: float,
        tenure_months: int
    ) -> float:
        """Calculate total interest payable over loan tenure."""
        total_payment = emi * tenure_months
        return round(total_payment - principal, 0)
    
    @staticmethod
    def get_interest_rate_for_score(credit_score: int) -> float:
        """
        Determine interest rate based on credit score.
        
        This mirrors real NBFC risk-based pricing:
        - Higher score = Lower rate (lower risk)
        - Lower score = Higher rate (higher risk)
        """
        if credit_score >= UnderwritingConfig.EXCELLENT_SCORE:
            return UnderwritingConfig.EXCELLENT_RATE
        elif credit_score >= UnderwritingConfig.GOOD_SCORE:
            return UnderwritingConfig.GOOD_RATE
        elif credit_score >= UnderwritingConfig.MIN_CREDIT_SCORE:
            return UnderwritingConfig.STANDARD_RATE
        else:
            return UnderwritingConfig.HIGH_RISK_RATE


# ================================================================================
# UNDERWRITING RULES ENGINE
# ================================================================================

class UnderwritingEngine:
    """
    Deterministic underwriting rules engine.
    
    PURPOSE:
    --------
    This engine makes loan approval/rejection decisions based on:
    1. Credit score (from Credit Bureau Service)
    2. Pre-approved limit (from Offer Mart Service)
    3. Monthly income (from CRM Service)
    4. Requested loan amount (from user input)
    5. Document verification status
    
    RULE HIERARCHY:
    ---------------
    Rules are evaluated in order of priority:
    
    1. HARD REJECT: Credit score < 700
       → Immediate rejection, no further checks
    
    2. INSTANT APPROVAL: Amount ≤ Pre-approved limit
       → Approved without income verification
    
    3. CONDITIONAL APPROVAL: Amount ≤ 2x Pre-approved limit
       → Requires salary slip
       → Approved if EMI ≤ 50% of income
    
    4. EXCESS REJECT: Amount > 2x Pre-approved limit
       → Rejected, exceeds eligibility
    
    WHY THIS ORDER:
    ---------------
    - Credit score is the primary risk indicator
    - Pre-approved limits are already risk-assessed
    - Extended limits need income verification
    - Amounts beyond 2x are outside risk appetite
    """
    
    def __init__(self):
        """Initialize the underwriting engine."""
        self.emi_calculator = EMICalculator()
        print("📊 PHASE 4: Underwriting Engine initialized")
        print("   - Rule 1: Credit Score Hard Cut-off (< 700 → REJECT)")
        print("   - Rule 2: Pre-Approved Instant Check")
        print("   - Rule 3: Extended Limit with Income Verification")
        print("   - Rule 4: Excess Amount Rejection")
    
    def evaluate(
        self,
        credit_score: int,
        requested_amount: float,
        preapproved_limit: float,
        monthly_income: float,
        tenure_months: int = None,
        salary_slip_uploaded: bool = False,
        existing_emi: float = 0
    ) -> UnderwritingDecision:
        """
        Evaluate loan application and return decision.
        
        Args:
            credit_score: Customer's CIBIL score (from Credit Bureau)
            requested_amount: Loan amount requested (from user)
            preapproved_limit: Pre-approved limit (from Offer Mart)
            monthly_income: Monthly salary (from CRM/dataset)
            tenure_months: Loan tenure (default: 48 months)
            salary_slip_uploaded: Whether salary slip was uploaded
            existing_emi: Existing EMI obligations
            
        Returns:
            UnderwritingDecision with complete decision details
        """
        print("\n" + "="*60)
        print("🏦 UNDERWRITING ENGINE - LOAN EVALUATION")
        print("="*60)
        
        # Use default tenure if not provided
        if tenure_months is None or tenure_months <= 0:
            tenure_months = UnderwritingConfig.DEFAULT_TENURE_MONTHS
        
        # Log inputs
        print(f"📥 INPUTS:")
        print(f"   Credit Score: {credit_score}")
        print(f"   Requested Amount: ₹{requested_amount:,.0f}")
        print(f"   Pre-approved Limit: ₹{preapproved_limit:,.0f}")
        print(f"   Monthly Income: ₹{monthly_income:,.0f}")
        print(f"   Tenure: {tenure_months} months")
        print(f"   Salary Slip: {'Uploaded' if salary_slip_uploaded else 'Not uploaded'}")
        print(f"   Existing EMI: ₹{existing_emi:,.0f}")
        
        # Initialize decision factors for audit
        decision_factors = {
            "credit_score": credit_score,
            "requested_amount": requested_amount,
            "preapproved_limit": preapproved_limit,
            "monthly_income": monthly_income,
            "tenure_months": tenure_months,
            "salary_slip_uploaded": salary_slip_uploaded,
            "existing_emi": existing_emi,
        }
        
        # Calculate interest rate based on credit score
        interest_rate = EMICalculator.get_interest_rate_for_score(credit_score)
        decision_factors["interest_rate"] = interest_rate
        
        # Calculate EMI for requested amount
        calculated_emi = self.emi_calculator.calculate_emi(
            principal=requested_amount,
            annual_interest_rate=interest_rate,
            tenure_months=tenure_months
        )
        decision_factors["calculated_emi"] = calculated_emi
        
        # Calculate total interest
        total_interest = EMICalculator.calculate_total_interest(
            principal=requested_amount,
            emi=calculated_emi,
            tenure_months=tenure_months
        )
        
        # ═══════════════════════════════════════════════════════════════════
        # RULE 1: CREDIT SCORE HARD CUT-OFF
        # ═══════════════════════════════════════════════════════════════════
        # Real NBFC Policy: Minimum CIBIL score requirement
        # Rationale: Below 700 indicates high default risk
        
        print("\n📋 RULE 1: Credit Score Check")
        if credit_score < UnderwritingConfig.MIN_CREDIT_SCORE:
            print(f"   ❌ FAILED: Score {credit_score} < {UnderwritingConfig.MIN_CREDIT_SCORE}")
            decision_factors["rule_applied"] = "RULE_1_CREDIT_SCORE"
            decision_factors["rule_result"] = "REJECTED"
            
            return UnderwritingDecision(
                loan_status=LoanStatus.REJECTED,
                rejection_reason=RejectionReason.LOW_CREDIT_SCORE,
                rejection_details=f"Your credit score of {credit_score} is below our minimum requirement of {UnderwritingConfig.MIN_CREDIT_SCORE}. We recommend improving your credit score before reapplying.",
                calculated_emi=calculated_emi,
                effective_interest_rate=interest_rate,
                decision_factors=decision_factors
            )
        print(f"   ✅ PASSED: Score {credit_score} >= {UnderwritingConfig.MIN_CREDIT_SCORE}")
        
        # ═══════════════════════════════════════════════════════════════════
        # RULE 2: PRE-APPROVED INSTANT CHECK
        # ═══════════════════════════════════════════════════════════════════
        # Real NBFC Policy: Instant approval for pre-assessed customers
        # Rationale: Customer already qualified for this amount
        
        print("\n📋 RULE 2: Pre-Approved Limit Check")
        if requested_amount <= preapproved_limit:
            print(f"   ✅ PASSED: ₹{requested_amount:,.0f} <= ₹{preapproved_limit:,.0f}")
            decision_factors["rule_applied"] = "RULE_2_PREAPPROVED"
            decision_factors["rule_result"] = "APPROVED"
            
            return UnderwritingDecision(
                loan_status=LoanStatus.APPROVED,
                approval_type=ApprovalType.INSTANT_PREAPPROVED,
                approved_amount=requested_amount,
                approved_tenure_months=tenure_months,
                calculated_emi=calculated_emi,
                effective_interest_rate=interest_rate,
                total_interest_payable=total_interest,
                total_repayment_amount=requested_amount + total_interest,
                requires_salary_slip=False,
                decision_factors=decision_factors
            )
        print(f"   ⏭️ SKIPPED: ₹{requested_amount:,.0f} > ₹{preapproved_limit:,.0f}")
        
        # ═══════════════════════════════════════════════════════════════════
        # RULE 3: EXTENDED LIMIT WITH INCOME VERIFICATION
        # ═══════════════════════════════════════════════════════════════════
        # Real NBFC Policy: Up to 2x pre-approved with income proof
        # Rationale: Higher amounts need FOIR validation
        
        extended_limit = preapproved_limit * UnderwritingConfig.EXTENDED_LIMIT_MULTIPLIER
        print(f"\n📋 RULE 3: Extended Limit Check (2x = ₹{extended_limit:,.0f})")
        
        if requested_amount <= extended_limit:
            print(f"   ✅ Within extended limit: ₹{requested_amount:,.0f} <= ₹{extended_limit:,.0f}")
            
            # Check if salary slip is required and uploaded
            if not salary_slip_uploaded:
                print(f"   ⏳ PENDING: Salary slip required for verification")
                decision_factors["rule_applied"] = "RULE_3_INCOME_VERIFICATION"
                decision_factors["rule_result"] = "PENDING_DOCS"
                
                return UnderwritingDecision(
                    loan_status=LoanStatus.PENDING_DOCS,
                    calculated_emi=calculated_emi,
                    effective_interest_rate=interest_rate,
                    total_interest_payable=total_interest,
                    total_repayment_amount=requested_amount + total_interest,
                    requires_salary_slip=True,
                    salary_slip_verified=False,
                    decision_factors=decision_factors
                )
            
            # Salary slip uploaded - verify FOIR
            print(f"   📄 Salary slip uploaded - checking FOIR")
            
            # Calculate FOIR (Fixed Obligation to Income Ratio)
            total_monthly_obligation = calculated_emi + existing_emi
            foir = total_monthly_obligation / monthly_income if monthly_income > 0 else 1.0
            decision_factors["total_monthly_obligation"] = total_monthly_obligation
            decision_factors["foir"] = foir
            
            print(f"   📊 FOIR Calculation:")
            print(f"      New EMI: ₹{calculated_emi:,.0f}")
            print(f"      Existing EMI: ₹{existing_emi:,.0f}")
            print(f"      Total Obligation: ₹{total_monthly_obligation:,.0f}")
            print(f"      Monthly Income: ₹{monthly_income:,.0f}")
            print(f"      FOIR: {foir:.2%} (max allowed: {UnderwritingConfig.MAX_FOIR:.0%})")
            
            if foir <= UnderwritingConfig.MAX_FOIR:
                print(f"   ✅ FOIR PASSED: {foir:.2%} <= {UnderwritingConfig.MAX_FOIR:.0%}")
                decision_factors["rule_applied"] = "RULE_3_INCOME_VERIFICATION"
                decision_factors["rule_result"] = "APPROVED"
                
                return UnderwritingDecision(
                    loan_status=LoanStatus.APPROVED,
                    approval_type=ApprovalType.INCOME_VERIFIED,
                    approved_amount=requested_amount,
                    approved_tenure_months=tenure_months,
                    calculated_emi=calculated_emi,
                    effective_interest_rate=interest_rate,
                    total_interest_payable=total_interest,
                    total_repayment_amount=requested_amount + total_interest,
                    requires_salary_slip=True,
                    salary_slip_verified=True,
                    decision_factors=decision_factors
                )
            else:
                print(f"   ❌ FOIR FAILED: {foir:.2%} > {UnderwritingConfig.MAX_FOIR:.0%}")
                decision_factors["rule_applied"] = "RULE_3_INCOME_VERIFICATION"
                decision_factors["rule_result"] = "REJECTED"
                
                # Calculate maximum affordable EMI
                max_emi = (monthly_income * UnderwritingConfig.MAX_FOIR) - existing_emi
                decision_factors["max_affordable_emi"] = max_emi
                
                return UnderwritingDecision(
                    loan_status=LoanStatus.REJECTED,
                    rejection_reason=RejectionReason.EMI_EXCEEDS_INCOME,
                    rejection_details=f"The EMI of ₹{calculated_emi:,.0f} would be {foir:.0%} of your monthly income, exceeding our maximum of {UnderwritingConfig.MAX_FOIR:.0%}. Maximum affordable EMI is ₹{max_emi:,.0f}.",
                    calculated_emi=calculated_emi,
                    effective_interest_rate=interest_rate,
                    requires_salary_slip=True,
                    salary_slip_verified=True,
                    decision_factors=decision_factors
                )
        
        # ═══════════════════════════════════════════════════════════════════
        # RULE 4: EXCESS AMOUNT REJECTION
        # ═══════════════════════════════════════════════════════════════════
        # Real NBFC Policy: Amounts beyond 2x pre-approved are outside risk appetite
        # Rationale: Prevents over-leveraging
        
        print(f"\n📋 RULE 4: Excess Amount Check")
        print(f"   ❌ FAILED: ₹{requested_amount:,.0f} > ₹{extended_limit:,.0f} (2x limit)")
        decision_factors["rule_applied"] = "RULE_4_EXCESS_AMOUNT"
        decision_factors["rule_result"] = "REJECTED"
        
        return UnderwritingDecision(
            loan_status=LoanStatus.REJECTED,
            rejection_reason=RejectionReason.AMOUNT_EXCEEDS_ELIGIBILITY,
            rejection_details=f"Your requested amount of ₹{requested_amount:,.0f} exceeds your maximum eligibility of ₹{extended_limit:,.0f}. Please consider reducing the loan amount.",
            calculated_emi=calculated_emi,
            effective_interest_rate=interest_rate,
            decision_factors=decision_factors
        )


# ================================================================================
# FACTORY FUNCTION
# ================================================================================

def create_underwriting_engine() -> UnderwritingEngine:
    """
    Create and return an underwriting engine instance.
    
    Returns:
        Configured UnderwritingEngine
    """
    return UnderwritingEngine()


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    """Test the underwriting engine with sample scenarios."""
    
    print("\n" + "="*70)
    print("🧪 TESTING UNDERWRITING ENGINE")
    print("="*70)
    
    engine = create_underwriting_engine()
    
    # Test Case 1: Low credit score rejection
    print("\n" + "-"*70)
    print("TEST CASE 1: Low Credit Score (Should REJECT)")
    print("-"*70)
    decision1 = engine.evaluate(
        credit_score=650,
        requested_amount=500000,
        preapproved_limit=300000,
        monthly_income=75000
    )
    print(f"\nRESULT:\n{decision1.get_summary()}")
    
    # Test Case 2: Pre-approved instant approval
    print("\n" + "-"*70)
    print("TEST CASE 2: Within Pre-Approved Limit (Should APPROVE - Instant)")
    print("-"*70)
    decision2 = engine.evaluate(
        credit_score=780,
        requested_amount=250000,
        preapproved_limit=300000,
        monthly_income=75000
    )
    print(f"\nRESULT:\n{decision2.get_summary()}")
    
    # Test Case 3: Extended limit - pending salary slip
    print("\n" + "-"*70)
    print("TEST CASE 3: Extended Limit without Salary Slip (Should be PENDING)")
    print("-"*70)
    decision3 = engine.evaluate(
        credit_score=750,
        requested_amount=500000,
        preapproved_limit=300000,
        monthly_income=75000,
        salary_slip_uploaded=False
    )
    print(f"\nRESULT:\n{decision3.get_summary()}")
    
    # Test Case 4: Extended limit - with salary slip (approved)
    print("\n" + "-"*70)
    print("TEST CASE 4: Extended Limit with Salary Slip (Should APPROVE)")
    print("-"*70)
    decision4 = engine.evaluate(
        credit_score=750,
        requested_amount=500000,
        preapproved_limit=300000,
        monthly_income=75000,
        salary_slip_uploaded=True
    )
    print(f"\nRESULT:\n{decision4.get_summary()}")
    
    # Test Case 5: Extended limit - EMI too high
    print("\n" + "-"*70)
    print("TEST CASE 5: Extended Limit but EMI > 50% Income (Should REJECT)")
    print("-"*70)
    decision5 = engine.evaluate(
        credit_score=750,
        requested_amount=500000,
        preapproved_limit=300000,
        monthly_income=25000,  # Low income
        salary_slip_uploaded=True
    )
    print(f"\nRESULT:\n{decision5.get_summary()}")
    
    # Test Case 6: Amount exceeds eligibility
    print("\n" + "-"*70)
    print("TEST CASE 6: Amount > 2x Pre-Approved (Should REJECT)")
    print("-"*70)
    decision6 = engine.evaluate(
        credit_score=780,
        requested_amount=800000,
        preapproved_limit=300000,
        monthly_income=75000
    )
    print(f"\nRESULT:\n{decision6.get_summary()}")
    
    print("\n" + "="*70)
    print("✅ All test cases completed")
    print("="*70)
