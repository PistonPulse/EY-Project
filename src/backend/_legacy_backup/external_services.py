"""
External Services Mock API
==========================
Simulates real-world banking microservices for the EY Techathon demo.

This module creates FastAPI endpoints that mimic:
1. Credit Bureau API (CIBIL-like) - Returns credit scores
2. CRM Server - Customer KYC data
3. Offer Engine - Pre-approved loan offers

PRIMARY KEY:
------------
mobile_number is the primary customer identifier across all services.
OTP verification must complete BEFORE any CRM lookup.

Architecture:
    Main Backend (port 8000)
         ↓ HTTP Requests
    External Services Router
         ├── /external-api/credit-bureau/score          (CIBIL)
         ├── /external-api/crm/customer/{mobile_number} (CRM)
         └── /external-api/offers/calculate             (Offer Engine)
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import hashlib
import asyncio

# Import the customer data
from mock_data import CUSTOMER_PROFILES

# ==================== API ROUTER ====================
external_api_router = APIRouter(
    prefix="/external-api",
    tags=["External Services (Mock)"]
)


# ==================== REQUEST/RESPONSE MODELS ====================

class CreditBureauRequest(BaseModel):
    """Request model for Credit Bureau API"""
    pan_number: str = Field(..., description="PAN card number", min_length=10, max_length=10)
    consent: bool = Field(True, description="User consent for credit check")


class CreditBureauResponse(BaseModel):
    """Response model from Credit Bureau (CIBIL-like)"""
    pan_number: str
    credit_score: int
    score_band: str  # Excellent, Good, Fair, Poor
    report_date: str
    bureau_name: str = "MOCK_CIBIL"
    inquiry_id: str
    factors: List[str] = []


class CRMCustomerResponse(BaseModel):
    """Response model for CRM Customer data"""
    customer_id: str
    name: str
    mobile_number: str  # Primary identifier
    pan: str
    email: str
    kyc_status: str
    financial_summary: Dict[str, Any]
    risk_profile: Dict[str, Any]
    relationship_since: str


class OfferRequest(BaseModel):
    """Request model for Offer Engine"""
    monthly_income: float = Field(..., gt=0, description="Monthly income in INR")
    credit_score: int = Field(..., ge=300, le=900, description="Credit score")
    existing_emi: float = Field(0, ge=0, description="Existing monthly EMI obligations")
    employment_type: str = Field("Salaried", description="Employment type")


class OfferResponse(BaseModel):
    """Response model from Offer Engine"""
    pre_approved_limit: int
    max_loan_amount: int
    interest_rate_range: Dict[str, float]
    max_tenure_months: int
    eligibility_status: str
    offer_validity: str
    offer_id: str


# ==================== UTILITY FUNCTIONS ====================

def pan_to_credit_score(pan: str) -> int:
    """
    Deterministic hash function to convert PAN to a credit score.
    Same PAN always gives the same score (300-900 range).
    
    Uses MD5 hash for consistent, deterministic output.
    """
    # Create hash of PAN
    pan_hash = hashlib.md5(pan.upper().encode()).hexdigest()
    
    # Convert first 8 hex chars to integer
    hash_int = int(pan_hash[:8], 16)
    
    # Map to 300-900 range
    score = 300 + (hash_int % 601)  # 601 values: 300-900
    
    return score


def get_score_band(score: int) -> str:
    """Get score band description"""
    if score >= 750:
        return "Excellent"
    elif score >= 700:
        return "Good"
    elif score >= 650:
        return "Fair"
    elif score >= 550:
        return "Poor"
    else:
        return "Very Poor"


def get_score_factors(score: int) -> List[str]:
    """Generate credit factors based on score"""
    factors = []
    if score >= 750:
        factors = [
            "Strong payment history",
            "Low credit utilization",
            "Long credit history",
            "Good mix of credit types"
        ]
    elif score >= 700:
        factors = [
            "Generally good payment history",
            "Moderate credit utilization",
            "Established credit history"
        ]
    elif score >= 650:
        factors = [
            "Some late payments in history",
            "Higher credit utilization",
            "Limited credit mix"
        ]
    else:
        factors = [
            "Multiple late/missed payments",
            "High credit utilization",
            "Limited credit history",
            "Recent credit inquiries"
        ]
    return factors


# ==================== CREDIT BUREAU ENDPOINT ====================

@external_api_router.post(
    "/credit-bureau/score",
    response_model=CreditBureauResponse,
    summary="Credit Bureau API (CIBIL Mock)",
    description="""
    Simulates a Credit Bureau API call to fetch credit score.
    
    **How it works:**
    - Takes a PAN number as input
    - Uses deterministic hashing to generate a consistent credit score
    - Same PAN always returns the same score (reproducible for testing)
    - Score range: 300-900
    
    **Real-world equivalent:** CIBIL, Experian, Equifax API
    """
)
async def get_credit_score(request: CreditBureauRequest):
    """
    Fetch credit score from the mock Credit Bureau.
    
    Simulates network latency (500ms) to mimic real API calls.
    """
    print(f"\n🔌 [CREDIT BUREAU API] Connecting to CIBIL...")
    print(f"   📋 PAN: {request.pan_number[:4]}XXXX{request.pan_number[-2:]}")
    
    # Simulate network latency
    await asyncio.sleep(0.5)
    
    # Check consent
    if not request.consent:
        print(f"   ❌ Credit check blocked - No consent")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User consent required for credit check"
        )
    
    # Generate deterministic credit score from PAN
    credit_score = pan_to_credit_score(request.pan_number)
    score_band = get_score_band(credit_score)
    factors = get_score_factors(credit_score)
    
    # Generate inquiry ID
    inquiry_id = f"INQ{datetime.now().strftime('%Y%m%d%H%M%S')}{request.pan_number[-4:]}"
    
    print(f"   ✅ Credit Score Retrieved: {credit_score} ({score_band})")
    print(f"   📊 Inquiry ID: {inquiry_id}")
    
    return CreditBureauResponse(
        pan_number=request.pan_number.upper(),
        credit_score=credit_score,
        score_band=score_band,
        report_date=datetime.now().isoformat(),
        inquiry_id=inquiry_id,
        factors=factors
    )


# ==================== CRM ENDPOINT ====================

@external_api_router.get(
    "/crm/customer/{mobile_number}",
    response_model=CRMCustomerResponse,
    summary="CRM Server API",
    description="""
    Simulates a CRM API call to fetch customer KYC data.
    
    **How it works:**
    - Takes a mobile_number as input (primary key)
    - Looks up customer in the mock database
    - Returns full customer profile if found
    - Returns 404 if customer not found
    
    **OTP Gate:**
    - This endpoint should only be called AFTER OTP verification
    - mobile_number is the identity key verified via OTP
    
    **Real-world equivalent:** Salesforce, internal CRM systems
    """
)
async def get_customer_from_crm(mobile_number: str):
    """
    Fetch customer details from the mock CRM.
    
    Simulates network latency (300ms) to mimic real API calls.
    Uses mobile_number as primary key for customer lookup.
    """
    print(f"\n🔌 [CRM API] Connecting to Customer Database...")
    print(f"   📱 Mobile Number: XXXXXX{mobile_number[-4:]}")
    
    # Simulate network latency
    await asyncio.sleep(0.3)
    
    # Look up customer using mobile_number as primary key
    customer = CUSTOMER_PROFILES.get(mobile_number)
    
    if not customer:
        print(f"   ❌ Customer not found in CRM")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with mobile_number {mobile_number[-4:].rjust(10, 'X')} not found in CRM"
        )
    
    # Build CRM response
    financial = customer.get("financial_data", {})
    behavioral = customer.get("behavioral_flags", {})
    
    print(f"   ✅ Customer Found: {customer['name']}")
    print(f"   📊 Risk Category: {behavioral.get('risk_category', 'UNKNOWN')}")
    
    return CRMCustomerResponse(
        customer_id=f"CRM_{mobile_number[-6:]}",
        name=customer["name"],
        mobile_number=customer["mobile_number"],
        pan=customer["pan"],
        email=customer.get("email", ""),
        kyc_status="VERIFIED",
        financial_summary={
            "credit_score": financial.get("credit_score"),  # Include credit score
            "monthly_income": financial.get("monthly_income"),
            "annual_income": financial.get("annual_income"),
            "employment_type": financial.get("employment_type"),
            "company": financial.get("company"),
            "work_experience_years": financial.get("work_experience_years"),
            "existing_debt": financial.get("total_monthly_debt"),
            "existing_loans": financial.get("existing_loans", []),
            "debt_to_income_ratio": financial.get("debt_to_income_ratio"),
            "bank_balance": financial.get("bank_balance")
        },
        risk_profile={
            "category": behavioral.get("risk_category"),
            "loan_history": behavioral.get("loan_history"),
            "payment_delays": behavioral.get("payment_delays"),
            "fraud_alerts": behavioral.get("fraud_alerts"),
            "bounced_cheques": behavioral.get("bounced_cheques")
        },
        relationship_since="2020-01-15"  # Mock date
    )


# ==================== OFFER ENGINE ENDPOINT ====================

@external_api_router.post(
    "/offers/calculate",
    response_model=OfferResponse,
    summary="Offer Engine API",
    description="""
    Simulates an Offer Engine API to calculate pre-approved loan limits.
    
    **Formula:**
    - Base limit = 12x monthly income
    - Adjusted by credit score multiplier
    - Reduced by existing EMI obligations
    
    **Credit Score Multipliers:**
    - 750+: 1.5x (up to 18x monthly income)
    - 700-749: 1.2x (up to 14.4x monthly income)
    - 650-699: 1.0x (12x monthly income)
    - Below 650: 0.6x (7.2x monthly income)
    
    **Real-world equivalent:** Internal offer calculation engines
    """
)
async def calculate_offer(request: OfferRequest):
    """
    Calculate pre-approved loan offer based on income and credit score.
    
    Simulates network latency (400ms) to mimic real API calls.
    """
    print(f"\n🔌 [OFFER ENGINE API] Calculating Pre-Approved Offer...")
    print(f"   💰 Monthly Income: ₹{request.monthly_income:,.0f}")
    print(f"   📊 Credit Score: {request.credit_score}")
    print(f"   📋 Existing EMI: ₹{request.existing_emi:,.0f}")
    
    # Simulate network latency
    await asyncio.sleep(0.4)
    
    # Base calculation: 12x monthly income
    base_limit = request.monthly_income * 12
    
    # Credit score multiplier
    if request.credit_score >= 750:
        multiplier = 1.5
        min_rate, max_rate = 10.5, 14.0
        eligibility = "SUPER_PRIME"
    elif request.credit_score >= 700:
        multiplier = 1.2
        min_rate, max_rate = 12.0, 16.0
        eligibility = "PRIME"
    elif request.credit_score >= 650:
        multiplier = 1.0
        min_rate, max_rate = 14.0, 18.0
        eligibility = "NEAR_PRIME"
    else:
        multiplier = 0.6
        min_rate, max_rate = 18.0, 24.0
        eligibility = "SUB_PRIME"
    
    # Apply multiplier
    adjusted_limit = base_limit * multiplier
    
    # Reduce by existing obligations (debt burden adjustment)
    if request.existing_emi > 0:
        debt_reduction = request.existing_emi * 36  # Assume 36 month projection
        adjusted_limit -= debt_reduction
    
    # Ensure minimum limit
    pre_approved = max(int(adjusted_limit), 50000)
    
    # Cap at 50 lakhs
    pre_approved = min(pre_approved, 5000000)
    
    # Generate offer ID
    offer_id = f"OFR{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"   ✅ Pre-Approved Limit: ₹{pre_approved:,}")
    print(f"   📈 Interest Rate: {min_rate}% - {max_rate}%")
    print(f"   🏷️ Eligibility: {eligibility}")
    print(f"   🎫 Offer ID: {offer_id}")
    
    return OfferResponse(
        pre_approved_limit=pre_approved,
        max_loan_amount=pre_approved,
        interest_rate_range={"min": min_rate, "max": max_rate},
        max_tenure_months=60,
        eligibility_status=eligibility,
        offer_validity=(datetime.now().replace(day=1, month=(datetime.now().month % 12) + 1)).isoformat(),
        offer_id=offer_id
    )


# ==================== HEALTH CHECK ====================

@external_api_router.get(
    "/health",
    summary="External Services Health Check",
    description="Check if all external service mocks are running"
)
async def external_services_health():
    """Health check for external services"""
    return {
        "status": "healthy",
        "services": {
            "credit_bureau": "online",
            "crm": "online",
            "offer_engine": "online"
        },
        "timestamp": datetime.now().isoformat(),
        "message": "All external service mocks are operational"
    }
