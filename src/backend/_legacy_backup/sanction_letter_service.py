"""
================================================================================
PHASE 5: SANCTION LETTER SERVICE
================================================================================

PURPOSE:
--------
This module handles the final stage of the loan journey:
1. Generating sanction letters for APPROVED loans
2. Creating professional rejection messages for REJECTED loans
3. Providing session closure to prevent further interactions

HOW THIS SIMULATES REAL NBFC APPROVAL DESK:
-------------------------------------------
In a real NBFC, after underwriting approves a loan:

1. The Credit Operations team generates a formal Sanction Letter
2. The letter contains legally binding terms:
   - Loan amount sanctioned
   - Interest rate (fixed/floating)
   - Tenure and EMI schedule
   - Terms & conditions
   - Validity period (usually 30 days)

3. The letter is digitally signed and sent to customer
4. Customer reviews and accepts the sanction
5. Only then does disbursement happen

This service mimics that workflow by:
- Reading ONLY from verified shared state (no LLM fabrication)
- Generating a professional PDF sanction letter
- Storing the letter URL for download
- Marking the session as closed to prevent further random responses

WHY FINAL CLOSURE MATTERS:
--------------------------
Once a loan decision is made (APPROVED or REJECTED):
- The conversation must END cleanly
- No further stage transitions should occur
- The LLM should only provide closure messaging
- This prevents:
  - Conflicting responses
  - LLM changing the decision
  - Infinite conversation loops
  - Audit/compliance issues

================================================================================
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


# ================================================================================
# CLOSURE STATUS
# ================================================================================

class SessionClosureReason(Enum):
    """
    Reasons for session closure.
    
    These map to final states in the loan journey:
    - LOAN_SANCTIONED: Happy path - loan approved and letter generated
    - LOAN_REJECTED: Sad path - loan declined with reason
    - USER_CANCELLED: User chose not to proceed
    - SESSION_TIMEOUT: Session expired
    """
    LOAN_SANCTIONED = "LOAN_SANCTIONED"
    LOAN_REJECTED = "LOAN_REJECTED"
    USER_CANCELLED = "USER_CANCELLED"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"


# ================================================================================
# SANCTION LETTER RESULT
# ================================================================================

@dataclass
class SanctionResult:
    """
    Result of sanction letter generation.
    
    PHASE 7: Now includes file_path for the actual generated PDF document.
    
    Contains:
    - success: Whether generation succeeded
    - letter_generated: If PDF was created
    - file_path: Local path to the generated PDF (PHASE 7)
    - download_url: API endpoint to download letter
    - reference_number: Unique sanction reference
    - validity_date: When the sanction expires
    - customer_message: Human-friendly message for display
    - error_message: If something went wrong
    """
    success: bool
    letter_generated: bool = False
    file_path: Optional[str] = None  # PHASE 7: Actual PDF file path
    download_url: Optional[str] = None
    reference_number: Optional[str] = None
    validity_date: Optional[str] = None
    customer_message: str = ""
    error_message: Optional[str] = None
    
    # Loan details for display
    sanctioned_amount: float = 0
    interest_rate: float = 0
    tenure_months: int = 0
    emi_amount: float = 0
    approval_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "letter_generated": self.letter_generated,
            "file_path": self.file_path,  # PHASE 7
            "download_url": self.download_url,
            "reference_number": self.reference_number,
            "validity_date": self.validity_date,
            "customer_message": self.customer_message,
            "error_message": self.error_message,
            "sanctioned_amount": self.sanctioned_amount,
            "interest_rate": self.interest_rate,
            "tenure_months": self.tenure_months,
            "emi_amount": self.emi_amount,
            "approval_type": self.approval_type,
        }


@dataclass
class RejectionResult:
    """
    Result of rejection handling.
    
    Contains:
    - success: Whether rejection was processed
    - rejection_reason: Standardized reason code
    - rejection_details: Detailed explanation
    - improvement_tips: What customer can do
    - customer_message: Human-friendly rejection message
    """
    success: bool
    rejection_reason: Optional[str] = None
    rejection_details: Optional[str] = None
    improvement_tips: Optional[str] = None
    customer_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "rejection_reason": self.rejection_reason,
            "rejection_details": self.rejection_details,
            "improvement_tips": self.improvement_tips,
            "customer_message": self.customer_message,
        }


# ================================================================================
# SANCTION LETTER SERVICE
# ================================================================================

class SanctionLetterService:
    """
    Service for generating sanction letters and handling loan closure.
    
    PURPOSE:
    --------
    This service is the final step in the loan journey. It:
    1. Validates that loan is actually approved (from shared state)
    2. Generates a professional sanction letter PDF
    3. Creates a download URL for the customer
    4. Returns a customer-friendly congratulations message
    
    REAL NBFC SIMULATION:
    ---------------------
    In a real NBFC, this would:
    - Trigger core banking system to create loan account
    - Generate digitally signed documents
    - Send SMS/Email notifications
    - Update CRM with sanction details
    - Queue for disbursement processing
    
    IMPORTANT:
    ----------
    This service NEVER decides approval - it only processes
    loans that were ALREADY approved by the Underwriting Engine.
    """
    
    def __init__(self, session_id: str = None):
        """Initialize the sanction letter service."""
        self.session_id = session_id
        print("\n📜 PHASE 5: Sanction Letter Service initialized")
    
    def generate_sanction_letter(
        self,
        customer_name: str,
        customer_phone: str,
        customer_pan: str,
        loan_amount: float,
        interest_rate: float,
        tenure_months: int,
        emi_amount: float,
        approval_type: str = None,
        session_id: str = None
    ) -> SanctionResult:
        """
        Generate sanction letter for an approved loan.
        
        PHASE 5: This method:
        1. Reads customer details from shared state
        2. Generates a unique reference number
        3. Creates PDF sanction letter (using existing pdf_generator)
        4. Returns download URL and customer message
        
        Args:
            customer_name: From state.user_name
            customer_phone: From state.user_phone
            customer_pan: From state.user_pan
            loan_amount: From state.loan_amount
            interest_rate: From state.effective_interest_rate
            tenure_months: From state.loan_tenure_months
            emi_amount: From state.calculated_emi
            approval_type: From state.approval_type
            session_id: Session ID for download URL
            
        Returns:
            SanctionResult with letter details, file_path, and customer message
        """
        print("\n" + "="*60)
        print("📜 PHASE 7: SANCTION LETTER GENERATION")
        print("="*60)
        
        try:
            # Validate inputs
            if not customer_name:
                customer_name = "Valued Customer"
            if not loan_amount or loan_amount <= 0:
                return SanctionResult(
                    success=False,
                    error_message="Invalid loan amount"
                )
            
            # Generate unique reference number
            # Format: AFNL/PL/YYYYMMDD/XXXX (Aurora Finance NBFC Ltd)
            today = datetime.now()
            name_code = customer_name.replace(" ", "").upper()[:4]
            reference_number = f"AFNL/PL/{today.strftime('%Y%m%d')}/{name_code}{today.strftime('%H%M')}"
            
            # Calculate validity date (30 days from today)
            from datetime import timedelta
            validity_date = (today + timedelta(days=30)).strftime("%B %d, %Y")
            
            # Determine session ID for download URL
            sid = session_id or self.session_id or "default"
            download_url = f"/api/download-sanction/{sid}"
            
            # Log sanction details
            print(f"📋 SANCTION DETAILS:")
            print(f"   Customer: {customer_name}")
            print(f"   Phone: {customer_phone}")
            print(f"   PAN: {customer_pan}")
            print(f"   Amount: ₹{loan_amount:,.0f}")
            print(f"   Interest Rate: {interest_rate}% p.a.")
            print(f"   Tenure: {tenure_months} months")
            print(f"   EMI: ₹{emi_amount:,.0f}/month")
            print(f"   Approval Type: {approval_type}")
            print(f"   Reference: {reference_number}")
            print(f"   Valid Until: {validity_date}")
            print(f"   Download URL: {download_url}")
            
            # ================================================================
            # PHASE 7: GENERATE ACTUAL PDF DOCUMENT
            # ================================================================
            # This is the key Phase 7 addition - we now generate a real PDF
            # file and store it in the /sanction_letters folder.
            #
            # The PDF generator:
            # 1. Uses ONLY values from shared state (passed as params)
            # 2. Does NOT use any LLM-generated content
            # 3. Saves to persistent storage for download
            # 4. Returns the file path
            # ================================================================
            
            from pdf_generator import generate_sanction_letter as generate_pdf
            
            pdf_file_path = generate_pdf(
                customer_name=customer_name,
                loan_amount=int(loan_amount),
                interest_rate=interest_rate,
                tenure=tenure_months,
                emi=int(emi_amount),
                phone=customer_phone or "",
                pan=customer_pan or "",
                approval_type=approval_type,
                session_id=sid
            )
            
            print(f"📄 PHASE 7: PDF generated at: {pdf_file_path}")
            
            # Generate customer message
            # This is what the LLM will use to communicate with customer
            customer_message = self._create_sanction_message(
                customer_name=customer_name,
                loan_amount=loan_amount,
                interest_rate=interest_rate,
                tenure_months=tenure_months,
                emi_amount=emi_amount,
                approval_type=approval_type,
                reference_number=reference_number,
                validity_date=validity_date
            )
            
            print(f"\n✅ PHASE 7: Sanction letter generated successfully")
            print(f"   File: {pdf_file_path}")
            print(f"   Download URL: {download_url}")
            print(f"="*60)
            
            return SanctionResult(
                success=True,
                letter_generated=True,
                file_path=pdf_file_path,  # PHASE 7: Store actual file path
                download_url=download_url,
                reference_number=reference_number,
                validity_date=validity_date,
                customer_message=customer_message,
                sanctioned_amount=loan_amount,
                interest_rate=interest_rate,
                tenure_months=tenure_months,
                emi_amount=emi_amount,
                approval_type=approval_type
            )
            
        except Exception as e:
            print(f"❌ Sanction letter generation failed: {e}")
            return SanctionResult(
                success=False,
                error_message=str(e)
            )
    
    def _create_sanction_message(
        self,
        customer_name: str,
        loan_amount: float,
        interest_rate: float,
        tenure_months: int,
        emi_amount: float,
        approval_type: str,
        reference_number: str,
        validity_date: str
    ) -> str:
        """
        Create the customer-facing sanction message.
        
        This message template is what the LLM should use.
        All values are from shared state - no fabrication.
        """
        
        # Calculate total repayment
        total_repayment = emi_amount * tenure_months
        total_interest = total_repayment - loan_amount
        
        message = f"""
🎉 CONGRATULATIONS, {customer_name}!

Your personal loan has been APPROVED!

═══════════════════════════════════════
📋 SANCTION DETAILS
═══════════════════════════════════════
✅ Loan Amount: ₹{loan_amount:,.0f}
✅ Approval Type: {approval_type or 'Standard Approval'}
✅ Interest Rate: {interest_rate}% per annum
✅ Tenure: {tenure_months} months
✅ Monthly EMI: ₹{emi_amount:,.0f}
✅ Total Repayment: ₹{total_repayment:,.0f}
✅ Total Interest: ₹{total_interest:,.0f}

📄 Reference Number: {reference_number}
📅 Offer Valid Until: {validity_date}
═══════════════════════════════════════

Your sanction letter is ready for download.
Click the button below to download your official sanction letter.

NEXT STEPS:
1. Download and review your sanction letter
2. Visit your nearest Tata Capital branch for document verification
3. Complete KYC formalities
4. Disbursement within 24-48 hours after documentation

Thank you for choosing Tata Capital! 🙏
"""
        return message


# ================================================================================
# REJECTION HANDLER SERVICE
# ================================================================================

class RejectionHandlerService:
    """
    Service for handling loan rejections professionally.
    
    PURPOSE:
    --------
    When a loan is rejected by the Underwriting Engine, this service:
    1. Reads the rejection reason from shared state
    2. Generates a professional, empathetic rejection message
    3. Provides actionable improvement tips
    4. Encourages future reapplication
    
    REAL NBFC SIMULATION:
    ---------------------
    In a real NBFC, rejections would:
    - Be logged for regulatory reporting
    - Trigger CRM follow-up workflows
    - Send formal rejection letter
    - Offer alternative products if available
    
    IMPORTANT:
    ----------
    This service NEVER decides rejection - it only handles
    rejections ALREADY decided by the Underwriting Engine.
    """
    
    # Improvement tips based on rejection reason
    IMPROVEMENT_TIPS = {
        "Credit score below minimum threshold": [
            "Check your credit report for errors and dispute any inaccuracies",
            "Pay all existing EMIs and credit card bills on time",
            "Reduce credit card utilization below 30%",
            "Avoid applying for multiple loans/cards in short period",
            "Consider becoming an authorized user on a family member's old credit card",
            "Wait 6-12 months while building credit history"
        ],
        "EMI exceeds 50% of monthly income": [
            "Consider a smaller loan amount that fits your budget",
            "Extend the tenure to reduce monthly EMI",
            "Pay off existing loans to reduce total obligations",
            "Wait for salary increment before reapplying",
            "Add a co-applicant with additional income"
        ],
        "Requested amount exceeds eligibility limit": [
            "Apply for a smaller loan amount within your eligibility",
            "Consider a secured loan (against property/FD) for higher amounts",
            "Improve credit score to increase eligibility",
            "Wait for income growth before reapplying"
        ]
    }
    
    def __init__(self):
        """Initialize the rejection handler service."""
        print("📝 PHASE 5: Rejection Handler Service initialized")
    
    def process_rejection(
        self,
        customer_name: str,
        rejection_reason: str,
        rejection_details: str = None,
        credit_score: int = None,
        requested_amount: float = None,
        eligible_amount: float = None
    ) -> RejectionResult:
        """
        Process a loan rejection and generate customer message.
        
        Args:
            customer_name: From state.user_name
            rejection_reason: From state.rejection_reason
            rejection_details: From state.rejection_details
            credit_score: From state.credit_score (for context)
            requested_amount: From state.loan_amount
            eligible_amount: Maximum eligible amount (if applicable)
            
        Returns:
            RejectionResult with message and improvement tips
        """
        print("\n" + "="*60)
        print("📝 PHASE 5: REJECTION HANDLING")
        print("="*60)
        
        try:
            # Get improvement tips for this rejection reason
            tips = self.IMPROVEMENT_TIPS.get(rejection_reason, [
                "Review your application details",
                "Consider reapplying after 6 months",
                "Contact customer support for more information"
            ])
            
            # Format improvement tips
            tips_text = "\n".join([f"  • {tip}" for tip in tips[:4]])
            
            print(f"📋 REJECTION DETAILS:")
            print(f"   Customer: {customer_name}")
            print(f"   Reason: {rejection_reason}")
            print(f"   Details: {rejection_details}")
            print(f"   Credit Score: {credit_score}")
            
            # Generate customer message
            customer_message = self._create_rejection_message(
                customer_name=customer_name,
                rejection_reason=rejection_reason,
                rejection_details=rejection_details,
                tips_text=tips_text,
                credit_score=credit_score,
                requested_amount=requested_amount,
                eligible_amount=eligible_amount
            )
            
            print(f"\n✅ Rejection message generated")
            print(f"="*60)
            
            return RejectionResult(
                success=True,
                rejection_reason=rejection_reason,
                rejection_details=rejection_details,
                improvement_tips=tips_text,
                customer_message=customer_message
            )
            
        except Exception as e:
            print(f"❌ Rejection handling failed: {e}")
            return RejectionResult(
                success=False,
                customer_message="We apologize, but we could not process your application at this time."
            )
    
    def _create_rejection_message(
        self,
        customer_name: str,
        rejection_reason: str,
        rejection_details: str,
        tips_text: str,
        credit_score: int = None,
        requested_amount: float = None,
        eligible_amount: float = None
    ) -> str:
        """
        Create the customer-facing rejection message.
        
        This is empathetic, professional, and provides actionable advice.
        """
        
        name = customer_name or "Valued Customer"
        
        message = f"""
Dear {name},

Thank you for your interest in Tata Capital Personal Loan.

After careful evaluation of your application, we regret to inform you that we are unable to approve your loan request at this time.

═══════════════════════════════════════
📋 REASON FOR DECISION
═══════════════════════════════════════
{rejection_reason}

{rejection_details or ''}
═══════════════════════════════════════

We understand this may not be the outcome you were hoping for, and we want to help you improve your chances for future applications.

💡 WHAT YOU CAN DO:
{tips_text}

"""
        
        # Add context-specific information
        if credit_score and "credit score" in rejection_reason.lower():
            message += f"""
📊 Your current credit score: {credit_score}
📈 Minimum required score: 700

"""
        
        if eligible_amount and "exceeds" in rejection_reason.lower():
            message += f"""
💰 Your maximum eligibility: ₹{eligible_amount:,.0f}
💰 You requested: ₹{requested_amount:,.0f}

Consider applying for a smaller amount within your eligibility.

"""
        
        message += """
═══════════════════════════════════════
We encourage you to work on the above suggestions and reapply in the future. 
Our team is here to help you achieve your financial goals.

For any queries, please contact:
📞 Customer Support: 1800-209-5555
📧 Email: support@tatacapital.com

Thank you for considering Tata Capital.
We hope to serve you in the future. 🙏
═══════════════════════════════════════
"""
        return message


# ================================================================================
# SESSION CLOSURE SERVICE
# ================================================================================

class SessionClosureService:
    """
    Service for cleanly closing chat sessions.
    
    WHY THIS IS IMPORTANT:
    ----------------------
    Once a loan decision is made, the conversation must END:
    
    1. Prevents LLM from contradicting the decision
    2. Stops infinite conversation loops
    3. Creates clear audit trail
    4. Matches real banking workflows (case closed)
    
    In real NBFCs, after sanction/rejection:
    - The case is marked as CLOSED
    - No further actions on that case
    - New application = new case number
    """
    
    @staticmethod
    def close_session(
        reason: SessionClosureReason,
        customer_name: str = None,
        final_message: str = None
    ) -> Dict[str, Any]:
        """
        Close a chat session with appropriate messaging.
        
        Args:
            reason: Why the session is being closed
            customer_name: For personalized closure message
            final_message: Optional custom closing message
            
        Returns:
            Dict with closure details
        """
        print(f"\n🔒 CLOSING SESSION: {reason.value}")
        
        closure_messages = {
            SessionClosureReason.LOAN_SANCTIONED: f"""
Thank you, {customer_name or 'valued customer'}! 

Your loan application journey is now complete.
📥 Don't forget to download your sanction letter.
📝 Visit your nearest branch to complete documentation.

This chat session is now closed.
For any queries, call 1800-209-5555.

Have a great day! 🙏
""",
            
            SessionClosureReason.LOAN_REJECTED: f"""
Thank you for your interest, {customer_name or 'valued customer'}.

We hope the suggestions provided help you in your future application.
Please don't hesitate to reapply once you've addressed the feedback.

This chat session is now closed.
For any queries, call 1800-209-5555.

Best wishes! 🙏
""",
            
            SessionClosureReason.USER_CANCELLED: """
We understand. Your application has been cancelled.
You can start a new application anytime.

This chat session is now closed.
Thank you for considering Tata Capital. 🙏
""",
            
            SessionClosureReason.SESSION_TIMEOUT: """
This session has expired due to inactivity.
Please start a new chat to continue.

Thank you for your patience. 🙏
"""
        }
        
        return {
            "session_closed": True,
            "closure_reason": reason.value,
            "closure_timestamp": datetime.now().isoformat(),
            "closure_message": final_message or closure_messages.get(reason, "Session closed."),
            "allow_further_messages": False
        }


# ================================================================================
# FACTORY FUNCTIONS
# ================================================================================

def create_sanction_service(session_id: str = None) -> SanctionLetterService:
    """Create a sanction letter service instance."""
    return SanctionLetterService(session_id)

def create_rejection_service() -> RejectionHandlerService:
    """Create a rejection handler service instance."""
    return RejectionHandlerService()


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    """Test the sanction letter service."""
    
    print("\n" + "="*70)
    print("🧪 TESTING PHASE 5: SANCTION LETTER SERVICE")
    print("="*70)
    
    # Test 1: Generate sanction letter
    print("\n--- Test 1: Sanction Letter Generation ---")
    service = create_sanction_service("test-session-001")
    result = service.generate_sanction_letter(
        customer_name="Rahul Mehta",
        customer_phone="9876543210",
        customer_pan="ABCDE1234F",
        loan_amount=500000,
        interest_rate=11.5,
        tenure_months=48,
        emi_amount=13045,
        approval_type="Instant Pre-Approved",
        session_id="test-session-001"
    )
    print(f"\nSanction Result:")
    print(f"  Success: {result.success}")
    print(f"  Reference: {result.reference_number}")
    print(f"  Download URL: {result.download_url}")
    print(f"\nCustomer Message Preview:")
    print(result.customer_message[:500] + "...")
    
    # Test 2: Handle rejection
    print("\n--- Test 2: Rejection Handling ---")
    rejection_service = create_rejection_service()
    rejection_result = rejection_service.process_rejection(
        customer_name="Priya Sharma",
        rejection_reason="Credit score below minimum threshold",
        rejection_details="Your credit score of 650 is below our minimum requirement of 700.",
        credit_score=650,
        requested_amount=500000
    )
    print(f"\nRejection Result:")
    print(f"  Success: {rejection_result.success}")
    print(f"  Reason: {rejection_result.rejection_reason}")
    print(f"\nCustomer Message Preview:")
    print(rejection_result.customer_message[:500] + "...")
    
    # Test 3: Session closure
    print("\n--- Test 3: Session Closure ---")
    closure = SessionClosureService.close_session(
        reason=SessionClosureReason.LOAN_SANCTIONED,
        customer_name="Rahul Mehta"
    )
    print(f"\nClosure Result:")
    print(f"  Closed: {closure['session_closed']}")
    print(f"  Reason: {closure['closure_reason']}")
    print(f"  Message Preview: {closure['closure_message'][:200]}...")
    
    print("\n" + "="*70)
    print("✅ All Phase 5 tests completed")
    print("="*70)
