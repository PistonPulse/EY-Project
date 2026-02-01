"""
================================================================================
PHASE 3: MOCK BACKEND SERVICES
================================================================================

PURPOSE:
--------
This module simulates real NBFC backend systems that would exist in a production
environment. Instead of the LLM inventing/hallucinating customer data, all 
information is retrieved from these mock services which read from a single 
source of truth: the Master Customer Dataset.

WHY THIS ARCHITECTURE:
----------------------
In a real NBFC system, the chatbot would integrate with:
1. CRM/KYC System - For identity verification
2. Offer Engine - For pre-approved loan offers
3. Credit Bureau - For credit score retrieval

By simulating these services, we ensure:
- No LLM hallucination of sensitive financial data
- Consistent, verifiable responses
- Realistic banking workflow simulation
- Easy migration path to real APIs in production

SERVICES IMPLEMENTED:
---------------------
1. CRMService (KYC Server)
   - Input: mobile_number OR pan
   - Output: KYC data if found, NOT_FOUND status otherwise
   - Called during: KYC_VERIFICATION stage

2. OfferMartService (Pre-Approved Offers)
   - Input: customer_id (mobile_number)
   - Output: Pre-approved limit, interest rate, tenure
   - Called during: OFFER_CHECK stage

3. CreditBureauService (CIBIL Simulation)
   - Input: pan OR mobile_number
   - Output: Credit score, bureau name
   - Called during: CREDIT_CHECK stage

DATA SOURCE:
------------
All services read from CUSTOMER_PROFILES in mock_data.py
This is the SINGLE SOURCE OF TRUTH for all customer data.

PRIMARY KEY:
------------
mobile_number is the primary customer identifier across all services.
OTP verification MUST complete before any CRM lookup.

================================================================================
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Import the master dataset
from mock_data import CUSTOMER_PROFILES, MockDataProvider


# ================================================================================
# SERVICE RESPONSE MODELS
# ================================================================================
# These dataclasses define the structure of service responses,
# ensuring consistency and type safety across the system.

@dataclass
class KYCResponse:
    """
    Response from CRM/KYC Service.
    
    Mirrors what a real KYC API would return:
    - Customer identity details
    - Verification status
    - Timestamp of verification
    
    NOTE: Uses mobile_number as primary identifier (verified via OTP)
    """
    kyc_status: str  # "VERIFIED", "NOT_FOUND", "PARTIAL_MATCH"
    customer_id: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    city: Optional[str] = None
    mobile_number: Optional[str] = None  # Primary identifier
    aadhaar_masked: Optional[str] = None  # Only last 4 digits
    pan: Optional[str] = None
    email: Optional[str] = None
    existing_customer: bool = False
    verification_timestamp: Optional[str] = None
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "kyc_status": self.kyc_status,
            "customer_id": self.customer_id,
            "name": self.name,
            "age": self.age,
            "city": self.city,
            "mobile_number": self.mobile_number,
            "phone": self.mobile_number,  # DEPRECATED alias for backward compatibility
            "aadhaar_masked": self.aadhaar_masked,
            "pan": self.pan,
            "email": self.email,
            "existing_customer": self.existing_customer,
            "verification_timestamp": self.verification_timestamp,
            "error_message": self.error_message,
        }


@dataclass
class OfferResponse:
    """
    Response from Offer Mart Service.
    
    Mirrors what a real offer engine would return:
    - Pre-approved status
    - Loan offer details
    - Terms and conditions
    """
    has_offer: bool
    customer_id: Optional[str] = None
    preapproved_limit_inr: float = 0
    interest_rate_percent: float = 0
    max_tenure_months: int = 0
    min_tenure_months: int = 0
    processing_fee_percent: float = 0
    offer_valid_until: Optional[str] = None
    offer_type: Optional[str] = None  # "PERSONAL", "HOME", "BUSINESS"
    special_conditions: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_offer": self.has_offer,
            "customer_id": self.customer_id,
            "preapproved_limit_inr": self.preapproved_limit_inr,
            "interest_rate_percent": self.interest_rate_percent,
            "max_tenure_months": self.max_tenure_months,
            "min_tenure_months": self.min_tenure_months,
            "processing_fee_percent": self.processing_fee_percent,
            "offer_valid_until": self.offer_valid_until,
            "offer_type": self.offer_type,
            "special_conditions": self.special_conditions,
        }


@dataclass
class CreditBureauResponse:
    """
    Response from Credit Bureau Service (CIBIL simulation).
    
    Mirrors what a real credit bureau API would return:
    - Credit score
    - Score band/category
    - Bureau identification
    """
    success: bool
    credit_score: Optional[int] = None
    score_band: Optional[str] = None  # "EXCELLENT", "GOOD", "FAIR", "POOR"
    bureau_name: str = "MockCIBIL"
    report_date: Optional[str] = None
    pan: Optional[str] = None
    accounts_count: int = 0
    overdue_accounts: int = 0
    enquiries_last_6_months: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "credit_score": self.credit_score,
            "score_band": self.score_band,
            "bureau_name": self.bureau_name,
            "report_date": self.report_date,
            "pan": self.pan,
            "accounts_count": self.accounts_count,
            "overdue_accounts": self.overdue_accounts,
            "enquiries_last_6_months": self.enquiries_last_6_months,
            "error_message": self.error_message,
        }


# ================================================================================
# CRM SERVICE (KYC SERVER)
# ================================================================================
# Simulates a Customer Relationship Management / KYC verification system.
# In production, this would connect to the bank's core banking system.

class CRMService:
    """
    CRM/KYC Service - Simulates customer identity verification.
    
    PURPOSE:
    --------
    This service simulates what a real CRM/KYC system would do:
    - Lookup customer by mobile_number or PAN
    - Return verified identity information
    - Flag if customer is new or existing
    
    DATA SOURCE:
    ------------
    Reads from CUSTOMER_PROFILES (master dataset).
    NO data is invented or hallucinated.
    
    PRIMARY KEY:
    ------------
    mobile_number is the primary customer identifier.
    OTP verification must complete BEFORE CRM lookup.
    
    INTEGRATION POINT:
    ------------------
    Called during KYC_VERIFICATION stage by the Verification Agent.
    
    USAGE:
        crm = CRMService()
        response = crm.verify_customer(mobile_number="9876543210")
        if response.kyc_status == "VERIFIED":
            # Use response.name, response.pan, etc.
    """
    
    def __init__(self):
        """Initialize CRM Service with data provider."""
        self.data_provider = MockDataProvider()
        print("🏦 CRM Service initialized (KYC Server)")
    
    def verify_customer(
        self, 
        mobile_number: Optional[str] = None, 
        pan: Optional[str] = None
    ) -> KYCResponse:
        """
        Verify customer identity using mobile_number or PAN.
        
        This simulates a real KYC verification API call.
        
        Args:
            mobile_number: Customer's 10-digit mobile number (primary key)
            pan: Customer's PAN number
            
        Returns:
            KYCResponse with verification status and customer data
            
        HOW IT REMOVES RANDOM BEHAVIOR:
        --------------------------------
        - Only returns data that EXISTS in the master dataset
        - If customer not found, returns NOT_FOUND (no invention)
        - LLM receives only verified, consistent data
        
        OTP GATE:
        ---------
        This method should only be called AFTER OTP verification.
        mobile_number is the identity key verified via OTP.
        """
        print(f"\n🔍 CRM SERVICE: Verifying customer (mobile_number={mobile_number}, pan={pan})")
        
        # Must have at least one identifier
        if not mobile_number and not pan:
            return KYCResponse(
                kyc_status="ERROR",
                error_message="Either mobile_number or PAN is required for verification"
            )
        
        # Clean inputs
        clean_mobile = "".join(filter(str.isdigit, mobile_number)) if mobile_number else None
        clean_pan = pan.upper().strip() if pan else None
        
        # Lookup in master dataset using mobile_number as primary key
        customer = None
        
        if clean_mobile:
            customer = CUSTOMER_PROFILES.get(clean_mobile)
        
        if not customer and clean_pan:
            # Search by PAN
            for profile in CUSTOMER_PROFILES.values():
                if profile.get("pan") == clean_pan:
                    customer = profile
                    break
        
        # Customer not found in dataset
        if not customer:
            print(f"   ❌ Customer NOT FOUND in database")
            return KYCResponse(
                kyc_status="NOT_FOUND",
                error_message="Customer not found in our records",
                verification_timestamp=datetime.now().isoformat()
            )
        
        # Customer found - return verified data
        fin_data = customer.get("financial_data", {})
        
        # Generate customer_id from mobile_number
        customer_mobile = customer.get("mobile_number", "")
        customer_id = f"CUST_{customer_mobile[-4:]}" if customer_mobile else None
        
        # Calculate age (mock - derive from risk category as placeholder)
        # In real system, this would be from actual DOB
        mock_age = 30  # Default
        risk_category = customer.get("behavioral_flags", {}).get("risk_category", "")
        if risk_category in ["SUPER_PRIME", "PRIME"]:
            mock_age = 35
        elif risk_category == "THIN_FILE":
            mock_age = 25
        
        # Mock city from company (in real system, this would be address data)
        company = fin_data.get("company", "")
        city_map = {
            "TCS": "Mumbai",
            "Infosys": "Bangalore",
            "Wipro": "Pune",
            "Amazon": "Hyderabad",
            "Google": "Bangalore",
            "Microsoft": "Hyderabad",
            "HCL": "Noida",
            "Tech Mahindra": "Pune",
            "Accenture": "Mumbai",
            "Cognizant": "Chennai",
        }
        mock_city = city_map.get(company, "Delhi")
        
        print(f"   ✅ Customer VERIFIED: {customer.get('name')}")
        
        return KYCResponse(
            kyc_status="VERIFIED",
            customer_id=customer_id,
            name=customer.get("name"),
            age=mock_age,
            city=mock_city,
            mobile_number=customer.get("mobile_number"),
            aadhaar_masked="XXXX-XXXX-" + customer.get("mobile_number", "0000")[-4:],  # Mock aadhaar
            pan=customer.get("pan"),
            email=customer.get("email"),
            existing_customer=True,
            verification_timestamp=datetime.now().isoformat()
        )
    
    def check_existing_customer(self, mobile_number: str) -> bool:
        """
        Quick check if customer exists in database.
        
        Args:
            mobile_number: Customer's mobile number
            
        Returns:
            True if customer exists, False otherwise
        """
        clean_mobile = "".join(filter(str.isdigit, mobile_number))
        return clean_mobile in CUSTOMER_PROFILES


# ================================================================================
# OFFER MART SERVICE
# ================================================================================
# Simulates a pre-approved loan offer engine.
# In production, this would connect to the bank's offer management system.

class OfferMartService:
    """
    Offer Mart Service - Simulates pre-approved loan offers.
    
    PURPOSE:
    --------
    This service simulates what a real offer engine would do:
    - Check if customer has pre-approved offers
    - Return offer details (limit, rate, tenure)
    - Provide offer validity and conditions
    
    DATA SOURCE:
    ------------
    Calculates pre-approved limit based on:
    - Customer's credit score (from master dataset)
    - Customer's monthly income (from master dataset)
    - Existing customer status
    
    NO random offers are generated.
    
    PRIMARY KEY:
    ------------
    mobile_number is the primary lookup key.
    OTP verification must complete BEFORE offer check.
    
    INTEGRATION POINT:
    ------------------
    Called during OFFER_CHECK stage by the Sales Agent.
    
    BUSINESS LOGIC:
    ---------------
    Pre-approved limit calculation:
    - Credit Score >= 750: 15x monthly income
    - Credit Score >= 700: 10x monthly income
    - Credit Score >= 650: 5x monthly income
    - Credit Score < 650: No pre-approved offer
    
    Interest rate assignment:
    - Credit Score >= 800: 10.5%
    - Credit Score >= 750: 11.5%
    - Credit Score >= 700: 12.5%
    - Credit Score >= 650: 14.0%
    - Credit Score < 650: 16.0%
    """
    
    def __init__(self):
        """Initialize Offer Mart Service."""
        self.data_provider = MockDataProvider()
        print("🎁 Offer Mart Service initialized")
    
    def check_preapproved_offers(
        self, 
        customer_id: str = None,
        mobile_number: str = None
    ) -> OfferResponse:
        """
        Check for pre-approved loan offers.
        
        This simulates a real offer engine API call.
        
        Args:
            customer_id: Customer ID (e.g., "CUST_3210")
            mobile_number: Customer's mobile number (primary lookup key)
            
        Returns:
            OfferResponse with offer details or no-offer status
            
        HOW IT REMOVES RANDOM BEHAVIOR:
        --------------------------------
        - Pre-approved limit is CALCULATED, not invented
        - Calculation uses REAL data from master dataset
        - Interest rates are from a FIXED business rule table
        - No LLM guessing of financial offers
        
        OTP GATE:
        ---------
        This method should only be called AFTER OTP verification.
        mobile_number is the identity key verified via OTP.
        """
        print(f"\n🎁 OFFER MART: Checking offers (customer_id={customer_id}, mobile_number={mobile_number})")
        
        # Lookup customer
        customer = None
        
        if mobile_number:
            clean_mobile = "".join(filter(str.isdigit, mobile_number))
            customer = CUSTOMER_PROFILES.get(clean_mobile)
        elif customer_id:
            # Extract mobile from customer_id (format: CUST_XXXX)
            mobile_suffix = customer_id.replace("CUST_", "")
            for profile_mobile, profile in CUSTOMER_PROFILES.items():
                if profile_mobile.endswith(mobile_suffix):
                    customer = profile
                    break
        
        # Customer not found
        if not customer:
            print(f"   ❌ No customer found - no offers available")
            return OfferResponse(
                has_offer=False,
                customer_id=customer_id
            )
        
        # Get financial data
        fin_data = customer.get("financial_data", {})
        credit_score = fin_data.get("credit_score", 0)
        monthly_income = fin_data.get("monthly_income", 0)
        
        # Business rule: Minimum credit score for pre-approved offers
        if credit_score < 650:
            print(f"   ❌ Credit score {credit_score} below threshold - no pre-approved offer")
            return OfferResponse(
                has_offer=False,
                customer_id=customer_id or f"CUST_{customer.get('mobile_number', '')[-4:]}"
            )
        
        # Calculate pre-approved limit based on credit score and income
        # This is the BUSINESS LOGIC - not LLM invention
        if credit_score >= 750:
            income_multiplier = 15
        elif credit_score >= 700:
            income_multiplier = 10
        else:  # 650-699
            income_multiplier = 5
        
        preapproved_limit = monthly_income * income_multiplier
        
        # Cap at reasonable maximum
        preapproved_limit = min(preapproved_limit, 2500000)  # Max 25 lakhs
        
        # Determine interest rate based on credit score
        # This is a FIXED business rule table
        if credit_score >= 800:
            interest_rate = 10.5
        elif credit_score >= 750:
            interest_rate = 11.5
        elif credit_score >= 700:
            interest_rate = 12.5
        elif credit_score >= 650:
            interest_rate = 14.0
        else:
            interest_rate = 16.0
        
        # Fixed tenure options
        max_tenure = 60  # 5 years
        min_tenure = 12  # 1 year
        
        # Processing fee based on credit quality
        if credit_score >= 750:
            processing_fee = 0.5  # 0.5%
        else:
            processing_fee = 1.0  # 1%
        
        # Offer validity (30 days from now)
        from datetime import timedelta
        valid_until = (datetime.now() + timedelta(days=30)).isoformat()
        
        print(f"   ✅ Pre-approved offer: ₹{preapproved_limit:,.0f} @ {interest_rate}%")
        
        return OfferResponse(
            has_offer=True,
            customer_id=customer_id or f"CUST_{customer.get('mobile_number', '')[-4:]}",
            preapproved_limit_inr=preapproved_limit,
            interest_rate_percent=interest_rate,
            max_tenure_months=max_tenure,
            min_tenure_months=min_tenure,
            processing_fee_percent=processing_fee,
            offer_valid_until=valid_until,
            offer_type="PERSONAL",
            special_conditions="Subject to income document verification"
        )


# ================================================================================
# CREDIT BUREAU SERVICE (CIBIL SIMULATION)
# ================================================================================
# Simulates a credit bureau API like CIBIL, Experian, or Equifax.
# In production, this would connect to actual bureau APIs.

class CreditBureauService:
    """
    Credit Bureau Service - Simulates CIBIL/credit score retrieval.
    
    PURPOSE:
    --------
    This service simulates what a real credit bureau API would do:
    - Retrieve credit score for a customer
    - Provide score band/category
    - Return bureau metadata
    
    DATA SOURCE:
    ------------
    Reads credit_score directly from master dataset.
    NO score is invented or guessed.
    
    PRIMARY KEY:
    ------------
    mobile_number is the primary lookup key.
    OTP verification must complete BEFORE credit check.
    
    INTEGRATION POINT:
    ------------------
    Called during CREDIT_CHECK stage by the Underwriting Agent.
    
    SCORE BANDS:
    ------------
    - 800+: EXCELLENT
    - 750-799: VERY_GOOD
    - 700-749: GOOD
    - 650-699: FAIR
    - 600-649: POOR
    - Below 600: VERY_POOR
    """
    
    def __init__(self):
        """Initialize Credit Bureau Service."""
        self.data_provider = MockDataProvider()
        self.bureau_name = "MockCIBIL"
        print("📊 Credit Bureau Service initialized (MockCIBIL)")
    
    def get_credit_score(
        self,
        pan: str = None,
        mobile_number: str = None
    ) -> CreditBureauResponse:
        """
        Get credit score from bureau.
        
        This simulates a real credit bureau API call.
        
        Args:
            pan: Customer's PAN number
            mobile_number: Customer's mobile number (primary lookup key)
            
        Returns:
            CreditBureauResponse with score and metadata
            
        HOW IT REMOVES RANDOM BEHAVIOR:
        --------------------------------
        - Credit score comes DIRECTLY from master dataset
        - Score band is CALCULATED from fixed rules
        - No LLM invention of credit scores
        - Consistent score for same customer across sessions
        
        OTP GATE:
        ---------
        This method should only be called AFTER OTP verification.
        mobile_number is the identity key verified via OTP.
        """
        print(f"\n📊 CREDIT BUREAU: Fetching score (pan={pan}, mobile_number={mobile_number})")
        
        # Lookup customer using mobile_number as primary key
        customer = None
        
        if mobile_number:
            clean_mobile = "".join(filter(str.isdigit, mobile_number))
            customer = CUSTOMER_PROFILES.get(clean_mobile)
        
        if not customer and pan:
            clean_pan = pan.upper().strip()
            for profile in CUSTOMER_PROFILES.values():
                if profile.get("pan") == clean_pan:
                    customer = profile
                    break
        
        # Customer not found
        if not customer:
            print(f"   ❌ No credit record found")
            return CreditBureauResponse(
                success=False,
                error_message="No credit record found for the provided details",
                bureau_name=self.bureau_name
            )
        
        # Get credit data from master dataset
        fin_data = customer.get("financial_data", {})
        behavioral = customer.get("behavioral_flags", {})
        
        credit_score = fin_data.get("credit_score", 0)
        
        # Determine score band (FIXED business rules)
        if credit_score >= 800:
            score_band = "EXCELLENT"
        elif credit_score >= 750:
            score_band = "VERY_GOOD"
        elif credit_score >= 700:
            score_band = "GOOD"
        elif credit_score >= 650:
            score_band = "FAIR"
        elif credit_score >= 600:
            score_band = "POOR"
        else:
            score_band = "VERY_POOR"
        
        # Mock account data based on existing loans
        existing_loans = fin_data.get("existing_loans", [])
        accounts_count = len(existing_loans) + 1  # At least one account
        
        # Overdue based on payment delays
        payment_delays = behavioral.get("payment_delays", 0)
        overdue_accounts = 1 if payment_delays > 2 else 0
        
        print(f"   ✅ Credit score retrieved: {credit_score} ({score_band})")
        
        return CreditBureauResponse(
            success=True,
            credit_score=credit_score,
            score_band=score_band,
            bureau_name=self.bureau_name,
            report_date=datetime.now().isoformat(),
            pan=customer.get("pan"),
            accounts_count=accounts_count,
            overdue_accounts=overdue_accounts,
            enquiries_last_6_months=1  # Mock value
        )
    
    def get_score_interpretation(self, score: int) -> str:
        """
        Get human-readable interpretation of credit score.
        
        Args:
            score: Credit score (300-900 range)
            
        Returns:
            String description of what the score means
        """
        if score >= 800:
            return "Excellent credit history. You qualify for the best interest rates."
        elif score >= 750:
            return "Very good credit. You qualify for competitive interest rates."
        elif score >= 700:
            return "Good credit history. You qualify for standard loan products."
        elif score >= 650:
            return "Fair credit. Some lenders may offer loans at higher rates."
        elif score >= 600:
            return "Below average credit. Limited loan options available."
        else:
            return "Poor credit history. Loan approval may be difficult."


# ================================================================================
# UNIFIED BACKEND SERVICES FACADE
# ================================================================================
# Provides a single interface to all backend services.
# Worker Agents interact with this facade instead of individual services.

class BackendServices:
    """
    Unified facade for all backend services.
    
    PURPOSE:
    --------
    Provides a single point of access to:
    - CRM Service (KYC verification)
    - Offer Mart Service (pre-approved offers)
    - Credit Bureau Service (credit scores)
    
    This ensures:
    - Consistent service initialization
    - Easy mocking for tests
    - Clean integration with Worker Agents
    
    PRIMARY KEY:
    ------------
    mobile_number is the primary customer identifier.
    All service calls use mobile_number for lookup.
    OTP verification must complete BEFORE any service call.
    
    USAGE IN WORKER AGENTS:
    -----------------------
    The Master Agent initializes BackendServices and passes it to
    Worker Agents. Worker Agents call specific methods:
    
    # In Verification Agent:
    kyc_result = backend_services.verify_kyc(mobile_number="9876543210")
    
    # In Sales Agent:
    offer_result = backend_services.check_offers(mobile_number="9876543210")
    
    # In Underwriting Agent:
    credit_result = backend_services.get_credit_report(mobile_number="9876543210")
    """
    
    def __init__(self):
        """Initialize all backend services."""
        print("\n" + "="*60)
        print("🏗️ INITIALIZING BACKEND SERVICES (Phase 3)")
        print("="*60)
        
        self.crm_service = CRMService()
        self.offer_mart_service = OfferMartService()
        self.credit_bureau_service = CreditBureauService()
        
        print("="*60)
        print("✅ All backend services ready")
        print("   📌 Data source: Master Customer Dataset")
        print("   📌 Primary key: mobile_number (verified via OTP)")
        print("   📌 No LLM hallucination - all data is verified")
        print("="*60 + "\n")
    
    # ==================== KYC METHODS ====================
    
    def verify_kyc(
        self, 
        mobile_number: str = None, 
        pan: str = None
    ) -> KYCResponse:
        """
        Verify customer KYC.
        
        Called during: KYC_VERIFICATION stage
        Called by: Verification Agent
        
        Args:
            mobile_number: Customer's mobile number (primary key)
            pan: Customer's PAN number
            
        Returns:
            KYCResponse with verification status
            
        OTP GATE:
        ---------
        This should only be called AFTER OTP verification.
        """
        return self.crm_service.verify_customer(mobile_number=mobile_number, pan=pan)
    
    def is_existing_customer(self, mobile_number: str) -> bool:
        """Quick check if customer exists."""
        return self.crm_service.check_existing_customer(mobile_number)
    
    # ==================== OFFER METHODS ====================
    
    def check_offers(
        self, 
        mobile_number: str = None,
        customer_id: str = None
    ) -> OfferResponse:
        """
        Check for pre-approved offers.
        
        Called during: OFFER_CHECK stage
        Called by: Sales Agent
        
        Args:
            mobile_number: Customer's mobile number (primary key)
            customer_id: Customer ID
            
        Returns:
            OfferResponse with offer details
            
        OTP GATE:
        ---------
        This should only be called AFTER OTP verification.
        """
        return self.offer_mart_service.check_preapproved_offers(
            customer_id=customer_id,
            mobile_number=mobile_number
        )
    
    # ==================== CREDIT METHODS ====================
    
    def get_credit_report(
        self, 
        mobile_number: str = None,
        pan: str = None
    ) -> CreditBureauResponse:
        """
        Get credit report from bureau.
        
        Called during: CREDIT_CHECK stage
        Called by: Underwriting Agent
        
        Args:
            mobile_number: Customer's mobile number (primary key)
            pan: Customer's PAN number
            
        Returns:
            CreditBureauResponse with credit score
            
        OTP GATE:
        ---------
        This should only be called AFTER OTP verification.
        """
        return self.credit_bureau_service.get_credit_score(
            pan=pan,
            mobile_number=mobile_number
        )
    
    def get_score_interpretation(self, score: int) -> str:
        """Get human-readable score interpretation."""
        return self.credit_bureau_service.get_score_interpretation(score)


# ================================================================================
# FACTORY FUNCTION
# ================================================================================

def create_backend_services() -> BackendServices:
    """
    Create and return initialized backend services.
    
    Returns:
        BackendServices instance with all services ready
    """
    return BackendServices()


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    """Test the backend services."""
    
    print("\n" + "="*60)
    print("🧪 TESTING BACKEND SERVICES")
    print("   Primary Key: mobile_number (verified via OTP)")
    print("="*60)
    
    # Initialize services
    services = create_backend_services()
    
    # Test 1: KYC Verification
    print("\n--- Test 1: KYC Verification ---")
    kyc_result = services.verify_kyc(mobile_number="9876543210")
    print(f"Status: {kyc_result.kyc_status}")
    print(f"Name: {kyc_result.name}")
    print(f"PAN: {kyc_result.pan}")
    print(f"Mobile Number: {kyc_result.mobile_number}")
    
    # Test 2: Offer Check
    print("\n--- Test 2: Offer Check ---")
    offer_result = services.check_offers(mobile_number="9876543210")
    print(f"Has Offer: {offer_result.has_offer}")
    print(f"Pre-approved Limit: ₹{offer_result.preapproved_limit_inr:,.0f}")
    print(f"Interest Rate: {offer_result.interest_rate_percent}%")
    
    # Test 3: Credit Bureau
    print("\n--- Test 3: Credit Bureau ---")
    credit_result = services.get_credit_report(mobile_number="9876543210")
    print(f"Credit Score: {credit_result.credit_score}")
    print(f"Score Band: {credit_result.score_band}")
    print(f"Bureau: {credit_result.bureau_name}")
    
    # Test 4: Unknown customer
    print("\n--- Test 4: Unknown Customer ---")
    unknown_kyc = services.verify_kyc(mobile_number="1111111111")
    print(f"Status: {unknown_kyc.kyc_status}")
    print(f"Message: {unknown_kyc.error_message}")
    
    print("\n" + "="*60)
    print("✅ All tests completed")
    print("="*60)
