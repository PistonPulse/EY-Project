"""
TataSmartAgent - Hub-and-Spoke Multi-Agent Architecture
Implements a true agentic loan officer using LangGraph with dynamic routing

Architecture:
    ┌─────────────────────────────────────────┐
    │              MASTER AGENT               │
    │         (Router & Orchestrator)         │
    └─────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┬─────────────┬─────────────┐
    ▼             ▼             ▼             ▼             ▼
┌───────┐   ┌───────────┐   ┌───────────┐   ┌───────┐   ┌─────────┐
│ Sales │   │Verification│   │Underwriting│   │ Trust │   │Document │
│ Agent │   │   Agent    │   │   Agent    │   │ Agent │   │  Agent  │
└───────┘   └───────────┘   └───────────┘   └───────┘   └─────────┘
"""

import os
import json
import asyncio
from typing import TypedDict, Annotated, Literal, Optional, Dict, Any, List
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field
import httpx

from mock_data import MockDataProvider
from api_client import ExternalAPIClient
from agent_prompts import (
    GLOBAL_BANKING_RULES,
    SALES_AGENT_PROMPT,
    VERIFICATION_AGENT_PROMPT,
    UNDERWRITER_AGENT_PROMPT,
    TRUST_AGENT_PROMPT,
    DOCUMENT_AGENT_PROMPT,
    build_agent_prompt,
    get_prompt_context,
    format_indian_currency
)


# ==================== API DATA PROVIDER ====================
class APIDataProvider:
    """
    Data provider that fetches data via HTTP from external microservices.
    
    This replaces direct data access with real API calls to demonstrate
    microservices architecture. Each method makes HTTP requests to our
    mock external services (Credit Bureau, CRM, Offer Engine).
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/external-api"):
        self.base_url = base_url
        self.api_client = ExternalAPIClient(base_url)
        self._fallback = MockDataProvider()  # Fallback if API is down
        self._api_events = []  # Track API call events for admin dashboard
        
    def get_api_events(self) -> List[Dict[str, Any]]:
        """Get and clear accumulated API events for admin dashboard"""
        events = self._api_events.copy()
        self._api_events.clear()
        return events
    
    def _log_api_event(self, event_type: str, data: Dict[str, Any]):
        """Log an API event for the admin dashboard"""
        self._api_events.append({
            "type": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_customer_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Fetch customer KYC data from CRM API.
        
        Makes a real HTTP GET request to /external-api/crm/customer/{phone}
        Falls back to local data if API is unavailable.
        """
        clean_phone = "".join(filter(str.isdigit, phone))
        
        # Log API call event
        self._log_api_event("API_CALL_CRM", {
            "service": "CRM",
            "endpoint": f"/crm/customer/{clean_phone[-4:].rjust(10, 'X')}",
            "agent": "Verification"
        })
        
        try:
            # Use synchronous request for compatibility with existing code
            with httpx.Client(timeout=10.0) as client:
                print(f"\n{'='*50}")
                print(f"🔗 CONNECTING TO CRM SERVER...")
                print(f"   Endpoint: GET /external-api/crm/customer/{clean_phone}")
                print(f"   Phone: XXXXXX{clean_phone[-4:]}")
                print(f"{'='*50}")
                
                response = client.get(f"{self.base_url}/crm/customer/{clean_phone}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ CRM RESPONSE:")
                    print(f"   Customer: {data.get('name')}")
                    print(f"   KYC Status: {data.get('kyc_status')}")
                    
                    # Log successful API response
                    self._log_api_event("API_RESPONSE_CRM", {
                        "service": "CRM",
                        "found": True,
                        "name": data.get("name"),
                        "kyc_status": data.get("kyc_status"),
                        "agent": "Verification"
                    })
                    
                    # Transform CRM response to match expected format
                    # CRM returns financial_summary, we need financial_data
                    fin_summary = data.get("financial_summary", {})
                    risk_profile = data.get("risk_profile", {})
                    
                    customer_data = {
                        "name": data.get("name"),
                        "phone": data.get("phone"),
                        "pan": data.get("pan"),
                        "email": data.get("email"),
                        "financial_data": {
                            "credit_score": fin_summary.get("credit_score", 0),
                            "annual_income": fin_summary.get("annual_income", 0),
                            "monthly_income": fin_summary.get("monthly_income", 0),
                            "employment_type": fin_summary.get("employment_type", "Unknown"),
                            "company": fin_summary.get("company", "Unknown"),
                            "work_experience_years": fin_summary.get("work_experience_years", 0),
                            "existing_loans": fin_summary.get("existing_loans", []),
                            "total_monthly_debt": fin_summary.get("existing_debt", 0),
                            "debt_to_income_ratio": fin_summary.get("debt_to_income_ratio", 0),
                            "bank_balance": fin_summary.get("bank_balance", 0),
                        },
                        "behavioral_flags": {
                            "loan_history": risk_profile.get("loan_history", "Unknown"),
                            "payment_delays": risk_profile.get("payment_delays", 0),
                            "fraud_alerts": risk_profile.get("fraud_alerts", 0),
                            "bounced_cheques": risk_profile.get("bounced_cheques", 0),
                            "risk_category": risk_profile.get("category", "Unknown"),
                        },
                        "application_history": data.get("application_history", [])
                    }
                    return customer_data
                    
                elif response.status_code == 404:
                    print(f"⚠️ CRM: Customer not found")
                    # Log not found response
                    self._log_api_event("API_RESPONSE_CRM", {
                        "service": "CRM",
                        "found": False,
                        "agent": "Verification"
                    })
                    return None
                else:
                    print(f"❌ CRM ERROR: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"⏱️ CRM TIMEOUT - Using fallback")
            return self._fallback.get_customer_by_phone(clean_phone)
        except Exception as e:
            print(f"❌ CRM CONNECTION ERROR: {e} - Using fallback")
            return self._fallback.get_customer_by_phone(clean_phone)
    
    def get_credit_score(self, pan_number: str) -> Dict[str, Any]:
        """
        Fetch credit score from Credit Bureau API.
        
        Makes a real HTTP POST request to /external-api/credit-bureau/score
        """
        # Log API call event
        self._log_api_event("API_CALL_CREDIT_BUREAU", {
            "service": "CIBIL",
            "pan": f"{pan_number[:4]}XXXX{pan_number[-2:]}",
            "agent": "Verification"
        })
        
        try:
            with httpx.Client(timeout=10.0) as client:
                print(f"\n{'='*50}")
                print(f"🔗 CONNECTING TO CREDIT BUREAU (CIBIL)...")
                print(f"   Endpoint: POST /external-api/credit-bureau/score")
                print(f"   PAN: {pan_number[:4]}XXXX{pan_number[-2:]}")
                print(f"{'='*50}")
                
                response = client.post(
                    f"{self.base_url}/credit-bureau/score",
                    json={"pan_number": pan_number, "consent": True}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ CREDIT BUREAU RESPONSE:")
                    print(f"   Credit Score: {data.get('credit_score')}")
                    print(f"   Score Band: {data.get('score_band')}")
                    
                    # Log successful API response
                    self._log_api_event("API_RESPONSE_CREDIT_BUREAU", {
                        "service": "CIBIL",
                        "credit_score": data.get("credit_score"),
                        "score_band": data.get("score_band"),
                        "agent": "Verification"
                    })
                    return data
                else:
                    print(f"❌ CREDIT BUREAU ERROR: {response.status_code}")
                    return {"error": True, "credit_score": 0}
                    
        except Exception as e:
            print(f"❌ CREDIT BUREAU CONNECTION ERROR: {e}")
            return {"error": True, "credit_score": 0, "message": str(e)}
    
    def calculate_offer(
        self, 
        monthly_income: float, 
        credit_score: int,
        existing_emi: float = 0,
        employment_type: str = "Salaried"
    ) -> Dict[str, Any]:
        """
        Calculate pre-approved loan offer from Offer Engine API.
        
        Makes a real HTTP POST request to /external-api/offers/calculate
        """
        # Log API call event
        self._log_api_event("API_CALL_OFFER_ENGINE", {
            "service": "Offer Engine",
            "income": monthly_income,
            "agent": "Underwriting"
        })
        
        try:
            with httpx.Client(timeout=10.0) as client:
                print(f"\n{'='*50}")
                print(f"🔗 CONNECTING TO OFFER ENGINE...")
                print(f"   Endpoint: POST /external-api/offers/calculate")
                print(f"   Income: ₹{monthly_income:,.0f}/month")
                print(f"   Credit Score: {credit_score}")
                print(f"{'='*50}")
                
                response = client.post(
                    f"{self.base_url}/offers/calculate",
                    json={
                        "monthly_income": monthly_income,
                        "credit_score": credit_score,
                        "existing_emi": existing_emi,
                        "employment_type": employment_type
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ OFFER ENGINE RESPONSE:")
                    print(f"   Pre-Approved Limit: ₹{data.get('pre_approved_limit'):,}")
                    print(f"   Eligibility: {data.get('eligibility_status')}")
                    
                    # Log successful API response
                    self._log_api_event("API_RESPONSE_OFFER_ENGINE", {
                        "service": "Offer Engine",
                        "pre_approved_limit": data.get("pre_approved_limit"),
                        "eligibility_status": data.get("eligibility_status"),
                        "agent": "Underwriting"
                    })
                    return data
                else:
                    print(f"❌ OFFER ENGINE ERROR: {response.status_code}")
                    return {"error": True, "pre_approved_limit": 0}
                    
        except Exception as e:
            print(f"❌ OFFER ENGINE CONNECTION ERROR: {e}")
            return {"error": True, "pre_approved_limit": 0, "message": str(e)}
    
    def fuzzy_match_by_name(self, name: str, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Find customer by fuzzy name matching.
        Delegates to MockDataProvider for now since CRM API doesn't support fuzzy search.
        
        In production, this would call a CRM search endpoint with fuzzy matching.
        """
        return self._fallback.fuzzy_match_by_name(name, threshold)


# ==================== STATE DEFINITION ====================
class AgentState(TypedDict):
    """
    Comprehensive state for the Hub-and-Spoke architecture.
    This state flows through all agents and maintains conversation context.
    """
    # Conversation History
    conversation_history: List[Dict[str, Any]]  # List of {role, content, timestamp}
    current_message: str  # Latest user message
    
    # User Profile
    user_profile: Dict[str, Any]  # {name, phone, email, verified, pan}
    
    # Loan Request Details
    loan_request: Dict[str, Any]  # {amount, tenure, purpose, type}
    pending_loan_request: Dict[str, Any]  # Loan amount mentioned before verification
    
    # Financial Data (from verification)
    financial_data: Dict[str, Any]  # {credit_score, monthly_income, annual_income, 
                                     #  existing_debt, debt_to_income_ratio, 
                                     #  pre_approved_limit, employment_type, company}
    
    # Negotiation State
    negotiation_state: Dict[str, Any]  # {current_offered_rate, floor_rate, 
                                        #  attempt_count, max_attempts, 
                                        #  last_offer, emi_amount}
    
    # Document State
    document_state: Dict[str, Any]  # {uploaded_docs, required_docs, 
                                     #  verification_status, pending_docs}
    
    # Trust & Risk Analysis
    trust_analysis: Dict[str, Any]  # {trust_score, risk_category, fraud_flags, 
                                     #  behavioral_score, red_flags}
    
    # OTP Verification State
    otp_state: Dict[str, Any]  # {otp_sent, otp_code, otp_phone, otp_verified, otp_attempts}
    
    # Decision State
    decision: Dict[str, Any]  # {loan_decision, conditions, decline_reason}
    
    # Routing Control
    next_step: str  # Which agent to route to next
    
    # Response
    ai_response: str  # Final response to send to user
    
    # UI Control Flags
    show_upload: bool  # Show document upload button
    show_sanction_letter: bool  # Show sanction letter download
    loan_details: Optional[Dict[str, Any]]  # Final approved loan details
    
    # Admin Logging
    admin_log: List[Dict[str, Any]]  # Logs for admin dashboard
    
    # Risk Control State (for fraud detection)
    risk_control: Dict[str, Any]  # {fraud_status, math_check, bank_check, visual_check}


# ==================== FRAUD DETECTION FUNCTIONS ====================
def validate_salary_math(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Mathematical Integrity Check for Salary Slip
    
    Validates that: (basic + hra + allowances) - (pf + tax + other_deductions) = net_pay
    
    Args:
        extracted_data: Extracted salary slip data with earnings and deductions
        
    Returns:
        Dict with validation status and details
    """
    result = {
        "status": "PASSED",
        "calculated_net": 0,
        "extracted_net": 0,
        "difference": 0,
        "details": {}
    }
    
    try:
        # Extract earnings
        earnings = extracted_data.get("earnings", {})
        basic_pay = float(earnings.get("basic_pay", 0) or 0)
        hra = float(earnings.get("hra", 0) or 0)
        special_allowances = float(earnings.get("special_allowances", 0) or 0)
        other_earnings = float(earnings.get("other_earnings", 0) or 0)
        
        # Extract deductions
        deductions = extracted_data.get("deductions", {})
        pf_deduction = float(deductions.get("pf_deduction", 0) or 0)
        tax_deduction = float(deductions.get("tax_deduction", 0) or 0)
        professional_tax = float(deductions.get("professional_tax", 0) or 0)
        other_deductions = float(deductions.get("other_deductions", 0) or 0)
        
        # Calculate expected net
        total_earnings = basic_pay + hra + special_allowances + other_earnings
        total_deductions = pf_deduction + tax_deduction + professional_tax + other_deductions
        calculated_net = total_earnings - total_deductions
        
        # Get extracted net
        extracted_net = float(extracted_data.get("net_salary", 0) or 0)
        
        # Also check against gross if available
        extracted_gross = float(extracted_data.get("gross_salary", 0) or 0)
        extracted_total_deductions = float(extracted_data.get("total_deductions", 0) or 0)
        
        # Calculate difference
        difference = abs(calculated_net - extracted_net)
        
        result["calculated_net"] = calculated_net
        result["extracted_net"] = extracted_net
        result["difference"] = difference
        result["details"] = {
            "total_earnings": total_earnings,
            "total_deductions": total_deductions,
            "earnings_breakdown": {
                "basic_pay": basic_pay,
                "hra": hra,
                "special_allowances": special_allowances,
                "other_earnings": other_earnings
            },
            "deductions_breakdown": {
                "pf_deduction": pf_deduction,
                "tax_deduction": tax_deduction,
                "professional_tax": professional_tax,
                "other_deductions": other_deductions
            }
        }
        
        # STRICT CHECK: Allow only ₹10 rounding error
        if difference > 10:
            result["status"] = "FRAUD_DETECTED"
            result["reason"] = f"Internal salary components do not add up to the net pay. Calculated: ₹{calculated_net:,.0f}, Shown: ₹{extracted_net:,.0f}, Difference: ₹{difference:,.0f}"
        else:
            result["status"] = "PASSED"
            result["reason"] = "Salary components verified - mathematics checks out"
            
        # Additional check: Gross salary validation if available
        if extracted_gross > 0 and abs(total_earnings - extracted_gross) > 10:
            result["status"] = "FRAUD_DETECTED"
            result["reason"] = f"Earnings don't match gross salary. Calculated: ₹{total_earnings:,.0f}, Gross shown: ₹{extracted_gross:,.0f}"
            
    except Exception as e:
        result["status"] = "ERROR"
        result["reason"] = f"Could not validate salary math: {str(e)}"
    
    return result


def cross_check_bank_statement(salary_data: Dict[str, Any], bank_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Cross-check salary credit in bank statement
    
    Validates that salary appears as a credit in bank statement within +/- 5 days
    
    Args:
        salary_data: Extracted salary slip data with net_salary and salary_date
        bank_data: Extracted bank statement data with transactions
        
    Returns:
        Dict with validation status and details
    """
    from datetime import datetime, timedelta
    
    result = {
        "status": "PASSED",
        "salary_found": False,
        "matching_transaction": None,
        "details": {}
    }
    
    try:
        net_salary = float(salary_data.get("net_salary", 0) or 0)
        salary_date_str = salary_data.get("salary_date")
        
        if not net_salary:
            result["status"] = "SKIPPED"
            result["reason"] = "No salary amount to verify"
            return result
        
        # Get credit transactions from bank statement
        transactions = bank_data.get("transactions", [])
        credit_summary = bank_data.get("credit_summary", {})
        salary_credits = credit_summary.get("salary_credits", [])
        
        # Parse salary date if available
        salary_date = None
        if salary_date_str:
            try:
                salary_date = datetime.strptime(salary_date_str, "%Y-%m-%d")
            except:
                salary_date = None
        
        # Check for matching credit transaction
        tolerance = 0.05  # 5% tolerance for amount matching
        date_window = 5  # +/- 5 days
        
        matching_found = False
        matching_transaction = None
        
        for txn in transactions:
            if txn.get("type") != "CREDIT":
                continue
                
            txn_amount = float(txn.get("amount", 0) or 0)
            
            # Check amount match (within 5% tolerance or exact)
            amount_diff = abs(txn_amount - net_salary)
            amount_match = amount_diff <= (net_salary * tolerance) or amount_diff <= 100
            
            if amount_match:
                # If we have dates, check date window
                if salary_date and txn.get("date"):
                    try:
                        txn_date = datetime.strptime(txn["date"], "%Y-%m-%d")
                        days_diff = abs((txn_date - salary_date).days)
                        if days_diff <= date_window:
                            matching_found = True
                            matching_transaction = txn
                            break
                    except:
                        # If date parsing fails, still count amount match
                        matching_found = True
                        matching_transaction = txn
                        break
                else:
                    # No dates to compare, just use amount match
                    matching_found = True
                    matching_transaction = txn
                    break
        
        # Also check salary_credits summary
        if not matching_found and salary_credits:
            for credit_amount in salary_credits:
                amount_diff = abs(float(credit_amount) - net_salary)
                if amount_diff <= (net_salary * tolerance) or amount_diff <= 100:
                    matching_found = True
                    matching_transaction = {"amount": credit_amount, "description": "Salary credit"}
                    break
        
        result["salary_found"] = matching_found
        result["matching_transaction"] = matching_transaction
        result["details"] = {
            "expected_salary": net_salary,
            "total_credits_found": len([t for t in transactions if t.get("type") == "CREDIT"]),
            "date_checked": salary_date_str
        }
        
        if matching_found:
            result["status"] = "PASSED"
            result["reason"] = f"Salary credit of ₹{net_salary:,.0f} found in bank statement"
        else:
            result["status"] = "DISCREPANCY"
            result["reason"] = f"Salary credit of ₹{net_salary:,.0f} not found in bank statement within the expected date window"
            
    except Exception as e:
        result["status"] = "ERROR"
        result["reason"] = f"Could not cross-check bank statement: {str(e)}"
    
    return result


def check_visual_forgery(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check visual forgery indicators from Gemini Vision analysis
    
    Args:
        extracted_data: Extracted document data with visual_analysis
        
    Returns:
        Dict with forgery check status
    """
    result = {
        "status": "PASSED",
        "suspicion_score": 0,
        "flags": [],
        "requires_manual_review": False
    }
    
    try:
        visual = extracted_data.get("visual_analysis", {})
        
        if not visual:
            result["status"] = "SKIPPED"
            result["reason"] = "No visual analysis data available"
            return result
        
        suspicion_score = int(visual.get("suspicion_score", 0) or 0)
        result["suspicion_score"] = suspicion_score
        
        # Check individual flags
        if visual.get("font_consistency") == False:
            result["flags"].append("INCONSISTENT_FONTS")
        
        if visual.get("alignment_quality") == False:
            result["flags"].append("SUSPICIOUS_ALIGNMENT")
        
        if visual.get("signs_of_editing") == True:
            result["flags"].append("EDITING_DETECTED")
        
        if visual.get("image_quality") == "poor":
            result["flags"].append("POOR_QUALITY")
        
        # Determine status based on suspicion score
        if suspicion_score > 70:
            result["status"] = "MANUAL_REVIEW"
            result["requires_manual_review"] = True
            result["reason"] = f"High suspicion score ({suspicion_score}/100) - document flagged for manual review"
        elif suspicion_score > 40 or len(result["flags"]) >= 2:
            result["status"] = "WARNING"
            result["reason"] = f"Moderate suspicion ({suspicion_score}/100) with flags: {', '.join(result['flags'])}"
        else:
            result["status"] = "PASSED"
            result["reason"] = "No significant visual anomalies detected"
            
    except Exception as e:
        result["status"] = "ERROR"
        result["reason"] = f"Could not check visual forgery: {str(e)}"
    
    return result


# ==================== OTP VERIFICATION SYSTEM ====================
import random
import string

# Test users with fixed OTP for testing
TEST_USERS_OTP = {
    "9876543210": "123456",  # Priya Sharma
    "9988776655": "123456",  # Amit Patel
    "9123456789": "123456",  # Rajesh Kumar
}

def generate_otp(phone: str, send_sms: bool = False) -> tuple[str, dict]:
    """
    Generate OTP for phone verification (LOCAL MOCK - no SMS).
    All OTPs are displayed directly in the chat for demo purposes.
    
    For test users (Priya, Amit, Rajesh), returns fixed OTP "123456".
    For other users, generates a random 6-digit OTP.
    
    Args:
        phone: 10-digit phone number
        send_sms: Ignored - SMS is disabled in mock mode
        
    Returns:
        Tuple of (OTP string, result dict)
    """
    result = {
        "success": True,
        "message": "OTP generated locally (mock mode)",
        "is_test_user": False,
        "is_mock": True
    }
    
    # Check if this is a test user
    if phone in TEST_USERS_OTP:
        result["is_test_user"] = True
        result["message"] = f"Test user - fixed OTP {TEST_USERS_OTP[phone]}"
        print(f"📱 [MOCK OTP] Test user {phone[-4:].rjust(10, 'X')} - OTP: {TEST_USERS_OTP[phone]}")
        return TEST_USERS_OTP[phone], result
    
    # Generate random 6-digit OTP for all other users
    otp = ''.join(random.choices(string.digits, k=6))
    
    result["message"] = f"OTP generated: {otp} (mock mode - displayed in chat)"
    print(f"📱 [MOCK OTP] Generated for {phone[-4:].rjust(10, 'X')} - OTP: {otp}")
    
    return otp, result

def verify_otp(phone: str, entered_otp: str, expected_otp: str) -> bool:
    """
    Verify OTP entered by user.
    
    Args:
        phone: User's phone number
        entered_otp: OTP entered by user
        expected_otp: OTP that was sent to user
        
    Returns:
        True if OTP matches, False otherwise
    """
    # Clean the entered OTP
    entered_otp = entered_otp.strip()
    
    return entered_otp == expected_otp

def extract_otp_from_message(message: str) -> Optional[str]:
    """
    Extract OTP from user's message.
    Handles various formats like "123", "my otp is 123", "otp: 123456", etc.
    
    Args:
        message: User's message
        
    Returns:
        Extracted OTP string or None if not found
    """
    import re
    
    # Clean message
    message = message.strip().lower()
    
    # Pattern 1: Just digits (common for OTP responses)
    if re.match(r'^\d{3,6}$', message):
        return message
    
    # Pattern 2: "otp is 123" or "otp: 123456" or "my otp is 123"
    otp_patterns = [
        r'otp\s*(?:is|:|\s)\s*(\d{3,6})',
        r'code\s*(?:is|:|\s)\s*(\d{3,6})',
        r'(\d{3,6})\s*(?:is|:)?\s*(?:the\s*)?otp',
        r'verify(?:ing)?\s*(?:with)?\s*(\d{3,6})',
    ]
    
    for pattern in otp_patterns:
        match = re.search(pattern, message)
        if match:
            return match.group(1)
    
    # Pattern 3: Find any 3-6 digit number in the message
    numbers = re.findall(r'\b(\d{3,6})\b', message)
    if len(numbers) == 1:
        return numbers[0]
    
    return None

def is_otp_request_message(message: str) -> bool:
    """
    Check if user's message is likely an OTP submission.
    
    Args:
        message: User's message
        
    Returns:
        True if message appears to be OTP submission
    """
    message = message.strip().lower()
    
    # Pure digit message (3-6 digits)
    if message.isdigit() and 3 <= len(message) <= 6:
        return True
    
    # Contains OTP-related keywords
    otp_keywords = ['otp', 'code', 'verify', 'verification']
    if any(keyword in message for keyword in otp_keywords):
        return True
    
    return False


# ==================== ROUTING DECISIONS ====================
class RoutingDecision(BaseModel):
    """Structured output for Master Agent routing decisions"""
    next_agent: Literal["sales", "verification", "underwriting", "trust", "document", "response", "fraud_check"]
    reasoning: str = Field(description="Brief explanation of why this agent was chosen")
    extracted_intent: str = Field(description="What the user is trying to do")


# ==================== GEMINI LLM WRAPPER ====================
class GeminiLLM:
    """Wrapper for Google Gemini API interactions"""
    
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        
        self.llm_structured = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.2,  # Lower temperature for routing decisions
            convert_system_message_to_human=True
        )
    
    async def generate(self, system_prompt: str, user_message: str, 
                       conversation_history: List[Dict] = None) -> str:
        """Generate a response using Gemini"""
        messages = [SystemMessage(content=system_prompt)]
        
        # Add conversation history
        if conversation_history:
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg["content"]))
        
        messages.append(HumanMessage(content=user_message))
        
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def generate_agent_response(self, agent_name: str, state: Dict, 
                                       user_message: str, 
                                       conversation_history: List[Dict] = None,
                                       additional_context: str = "") -> str:
        """
        Generate a response using the appropriate agent persona and prompts.
        
        Args:
            agent_name: Name of the agent (sales, verification, underwriting, etc.)
            state: Current conversation state
            user_message: The user's message
            conversation_history: Previous messages
            additional_context: Any additional context for the response
            
        Returns:
            Generated response string
        """
        # Build the full agent prompt with context
        agent_prompt = build_agent_prompt(agent_name, state)
        
        # Add any additional context if provided
        if additional_context:
            agent_prompt += f"\n\n**ADDITIONAL CONTEXT:**\n{additional_context}"
        
        # Add instruction to respond directly
        agent_prompt += """

**RESPONSE INSTRUCTION:**
Based on the above context and the user's message, generate a professional, helpful response.
Keep it conversational (2-3 sentences max per point).
Follow all the behavioral guidelines above.
Respond DIRECTLY as the agent - do not include any meta-commentary."""
        
        return await self.generate(agent_prompt, user_message, conversation_history)
    
    async def route(self, system_prompt: str, context: str) -> RoutingDecision:
        """Get structured routing decision from Gemini"""
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context)
        ]
        
        structured_llm = self.llm_structured.with_structured_output(RoutingDecision)
        result = await structured_llm.ainvoke(messages)
        return result
    
    async def analyze_document(self, file_data: str, mime_type: str, prompt: str) -> Dict[str, Any]:
        """
        Analyze a document image using Gemini Vision API
        
        Args:
            file_data: Base64 encoded image/document data
            mime_type: MIME type of the file (e.g., 'image/jpeg', 'application/pdf')
            prompt: Extraction prompt specifying what to extract
            
        Returns:
            Dict with extracted document fields
        """
        from langchain_core.messages import HumanMessage
        import google.generativeai as genai
        
        # Configure Gemini
        api_key = os.environ.get("GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        
        # Use gemini-2.0-flash for vision (supports multimodal)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Create the image part
        image_part = {
            "mime_type": mime_type,
            "data": file_data
        }
        
        # Generate content with vision
        response = model.generate_content([prompt, image_part])
        
        # Parse JSON from response
        response_text = response.text
        
        # Clean up response if it contains markdown code blocks
        if "```" in response_text:
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        try:
            extracted = json.loads(response_text)
            return extracted
        except json.JSONDecodeError:
            # Return raw response if JSON parsing fails
            return {
                "raw_response": response_text,
                "confidence": 30,
                "error": "Could not parse JSON from response"
            }


# ==================== HUB-AND-SPOKE GRAPH ====================
class LoanAgentGraph:
    """
    Hub-and-Spoke Multi-Agent System for Loan Processing
    
    Master Agent (Hub) routes to specialized Worker Agents (Spokes):
    - Sales Agent: Handles greetings, negotiations, persuasion
    - Verification Agent: Verifies identity, fetches customer data
    - Underwriting Agent: Calculates eligibility, rates, EMI
    - Trust Agent: Analyzes risk, fraud detection
    - Document Agent: Handles document upload and verification
    """
    
    def __init__(self, gemini_api_key: str):
        self.llm = GeminiLLM(gemini_api_key)
        self.data_provider = APIDataProvider()  # Uses HTTP calls to external microservices
        self.graph = self._build_graph()
        
        print("\n" + "="*60)
        print("🏦 TATA CAPITAL AI UNDERWRITER - HUB-AND-SPOKE ARCHITECTURE")
        print("="*60)
        print("📍 Mode: PRODUCTION (Full Gemini AI)")
        print("🔀 Architecture: Hub-and-Spoke Multi-Agent")
        print("🤖 Agents: Master, Sales, Verification, Underwriting, Trust, Document")
        print("🌐 Data Source: External Microservices (CRM, Credit Bureau, Offer Engine)")
        print("="*60 + "\n")
    
    def _build_graph(self) -> StateGraph:
        """Build the Hub-and-Spoke state graph"""
        workflow = StateGraph(AgentState)
        
        # Add all nodes (Hub + Spokes)
        workflow.add_node("master", self.master_node)
        workflow.add_node("sales", self.sales_agent_node)
        workflow.add_node("verification", self.verification_agent_node)
        workflow.add_node("underwriting", self.underwriting_agent_node)
        workflow.add_node("trust", self.trust_agent_node)
        workflow.add_node("document", self.document_agent_node)
        workflow.add_node("fraud_check", self.risk_control_agent_node)  # NEW: Fraud Detection Agent
        workflow.add_node("response", self.response_node)
        
        # Entry point is always Master
        workflow.set_entry_point("master")
        
        # Master routes to appropriate spoke based on next_step
        workflow.add_conditional_edges(
            "master",
            self._route_from_master,
            {
                "sales": "sales",
                "verification": "verification",
                "underwriting": "underwriting",
                "trust": "trust",
                "document": "document",
                "fraud_check": "fraud_check",
                "response": "response"
            }
        )
        
        # All spokes return to response node
        workflow.add_edge("sales", "response")
        workflow.add_edge("verification", "response")
        workflow.add_edge("underwriting", "response")
        workflow.add_edge("trust", "response")
        workflow.add_edge("document", "response")
        workflow.add_edge("fraud_check", "response")  # Fraud check also returns to response
        workflow.add_edge("response", END)
        
        return workflow.compile()
    
    def _route_from_master(self, state: AgentState) -> str:
        """Route from master to appropriate spoke"""
        return state.get("next_step", "response")
    
    # ==================== MASTER NODE (HUB) ====================
    async def master_node(self, state: AgentState) -> AgentState:
        """
        MASTER AGENT (Hub)
        
        Responsibilities:
        1. Analyze user's message and current state
        2. Decide which Worker Agent should handle the request
        3. Route to appropriate spoke
        """
        log_entry = {
            "agent": "Master Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "routing_decision"
        }
        
        user_message = state["current_message"]
        user_message_lower = user_message.lower().strip()
        
        # ==================== EXTRACT AND STORE PENDING LOAN AMOUNT ====================
        # Check if user is mentioning a loan amount before they're verified
        is_verified = state.get("user_profile", {}).get("verified", False)
        if not is_verified:
            # Check for loan amount mentions
            loan_amount_patterns = ["lakh", "lakhs", "lac", "lacs", "want", "need", "borrow"]
            if any(p in user_message_lower for p in loan_amount_patterns):
                # Try to extract the amount
                import re
                amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs)', user_message_lower)
                if amount_match:
                    pending_amount = int(float(amount_match.group(1)) * 100000)
                    state["pending_loan_request"] = {"amount": pending_amount}
                    log_entry["pending_loan_amount"] = pending_amount
                    log_entry["message"] = f"Stored pending loan request: Rs. {pending_amount:,}"
        
        # Check if user is confirming their identity (pending_match flow)
        pending_match = state.get("user_profile", {}).get("pending_match")
        if pending_match:
            # Expanded confirmation phrases including common typos
            confirmation_phrases = [
                "yes", "yess", "yss", "ys", "ya", "yaa", "yup", "yep", "yeah", "yea",
                "that's me", "thats me", "that is me", "its me", "it's me", "it is me",
                "correct", "right", "true", "affirmative", "absolutely",
                "confirm", "confirmed", "i confirm", "yes confirm",
                "yes that's me", "yes thats me", "yes it's me", "yes its me",
                "haan", "ha", "ji", "ji haan", "sahi hai", "theek hai", "ok", "okay"
            ]
            if any(phrase in user_message_lower for phrase in confirmation_phrases) or user_message_lower in ["y", "yes", "yss", "yep"]:
                # User confirmed - route to verification to complete the process
                state["user_profile"]["confirmed_match"] = True
                state["next_step"] = "verification"
                log_entry["routing"] = "verification"
                log_entry["reasoning"] = "User confirmed their identity"
                log_entry["message"] = "-> Routing to Verification Agent: User confirmed identity"
                log_entry["type"] = "info"
                state.setdefault("admin_log", []).append(log_entry)
                return state
        
        # Check user type for differentiated routing (Existing vs New Prospect)
        user_type = state.get("user_profile", {}).get("user_type")
        is_new_lead = state.get("user_profile", {}).get("is_new_lead", False)
        is_verified = state.get("user_profile", {}).get("verified", False)
        financial_data = state.get("financial_data", {})
        
        # NEW PROSPECT HANDLING - Need to collect data first before underwriting
        if is_new_lead and is_verified:
            # Check if we have salary info
            monthly_income = financial_data.get("monthly_income")
            credit_score = financial_data.get("credit_score")
            
            # Check if user is providing salary/income information
            salary_keywords = ["salary", "income", "earn", "monthly", "per month", "pm", "lpa", "lakhs per", "k per month", "rupees"]
            amount_patterns = any(char.isdigit() for char in user_message)
            
            if (any(kw in user_message_lower for kw in salary_keywords) or amount_patterns) and not monthly_income:
                # User might be sharing salary - route to underwriting to extract and store
                state["next_step"] = "underwriting"
                log_entry["routing"] = "underwriting"
                log_entry["reasoning"] = "New prospect providing income details - collecting data"
                log_entry["message"] = "→ Routing to Underwriting Agent: Collecting income data from new prospect"
                log_entry["type"] = "info"
                state.setdefault("admin_log", []).append(log_entry)
                return state
            
            # If no salary yet, prompt for it
            if not monthly_income:
                # Check if they're asking for loan without providing salary first
                loan_keywords = ["loan", "borrow", "lakh", "lakhs", "need money", "credit"]
                if any(kw in user_message_lower for kw in loan_keywords):
                    state["next_step"] = "underwriting"
                    log_entry["routing"] = "underwriting"
                    log_entry["reasoning"] = "New prospect asking about loan - need to collect financial info first"
                    log_entry["type"] = "info"
                    state.setdefault("admin_log", []).append(log_entry)
                    return state
        
        # Build context for routing decision
        context = f"""
CURRENT USER MESSAGE: "{user_message}"

CURRENT STATE:
- User Profile: {json.dumps(state.get('user_profile', {}), indent=2)}
- Loan Request: {json.dumps(state.get('loan_request', {}), indent=2)}
- Financial Data: {json.dumps(state.get('financial_data', {}), indent=2)}
- Negotiation State: {json.dumps(state.get('negotiation_state', {}), indent=2)}
- Document State: {json.dumps(state.get('document_state', {}), indent=2)}
- Trust Analysis: {json.dumps(state.get('trust_analysis', {}), indent=2)}

CONVERSATION HISTORY (last 3 messages):
{json.dumps(state.get('conversation_history', [])[-3:], indent=2)}
"""
        
        routing_prompt = """You are the Master Router Agent for Tata Capital's AI Loan System.

Your job is to analyze the user's message and current state, then decide which specialized agent should handle this request.

ROUTING RULES:
1. SALES AGENT - Route here if:
   - User sends greeting (hi, hello, hey, good morning, etc.)
   - User is negotiating interest rate (asking for lower rate, better deal, discount)
   - User needs persuasion or has objections
   - User is asking general questions about the loan process
   - User accepts or shows interest in proceeding

2. VERIFICATION AGENT - Route here if:
   - User provides their name, phone number, or PAN
   - User needs identity verification
   - User profile is empty and they're sharing personal details
   - Need to fetch customer data from database

3. UNDERWRITING AGENT - Route here if:
   - User mentions loan amount they want (e.g., "I need 5 lakhs", "want to borrow 3 lakh")
   - User asks about eligibility or how much they can get
   - User asks about EMI calculation
   - Need to calculate interest rates based on credit profile
   - User asks about loan tenure or repayment

4. TRUST AGENT - Route here if:
   - Suspicious behavior detected
   - Need to analyze risk before proceeding
   - User's responses seem inconsistent or fraudulent
   - High-risk profile needs additional verification

5. DOCUMENT AGENT - Route here if:
   - User mentions uploading documents
   - User says they've uploaded or want to upload files
   - Document verification is pending
   - User asks what documents are needed

6. FRAUD_CHECK AGENT - Route here if:
   - Documents have been uploaded and need fraud verification
   - Salary slip needs mathematical validation
   - Bank statement needs cross-checking with salary
   - Visual forgery analysis is required
   - Document authenticity is in question

7. RESPONSE AGENT - Route here if:
   - A direct response can be generated without specialized processing
   - Simple acknowledgment needed

Analyze the message carefully and choose the MOST appropriate agent."""

        try:
            routing = await self.llm.route(routing_prompt, context)
            state["next_step"] = routing.next_agent
            
            log_entry["routing"] = routing.next_agent
            log_entry["reasoning"] = routing.reasoning
            log_entry["intent"] = routing.extracted_intent
            log_entry["message"] = f"→ Routing to {routing.next_agent.upper()} Agent: {routing.reasoning}"
            log_entry["type"] = "info"
            
            print(f"🔀 MASTER: Routing to {routing.next_agent.upper()} - {routing.reasoning}")
            
        except Exception as e:
            print(f"❌ Master routing error: {e}")
            state["next_step"] = "sales"  # Default to sales on error
            log_entry["error"] = str(e)
            log_entry["message"] = "→ Defaulting to Sales Agent due to routing error"
            log_entry["type"] = "warning"
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== SALES AGENT (SPOKE) ====================
    async def sales_agent_node(self, state: AgentState) -> AgentState:
        """
        SALES AGENT
        
        Responsibilities:
        1. Handle greetings and initial contact
        2. Negotiate interest rates with persuasion
        3. Guide customer through the loan process
        4. Handle objections and concerns
        """
        log_entry = {
            "agent": "Sales Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "sales_interaction"
        }
        
        user_profile = state.get("user_profile", {})
        negotiation = state.get("negotiation_state", {})
        financial = state.get("financial_data", {})
        loan_request = state.get("loan_request", {})
        
        try:
            # Build sales context
            customer_name = user_profile.get("name", "valued customer")
            credit_score = financial.get("credit_score", 0)
            current_rate = negotiation.get("current_offered_rate")
            floor_rate = negotiation.get("floor_rate")
            attempt_count = negotiation.get("attempt_count", 0)
            loan_amount = loan_request.get("amount", 0)
            emi = loan_request.get("emi", 0)
            
            # Get underwriting decision
            underwriting_decision = loan_request.get("underwriting_decision")
            underwriting_reason = loan_request.get("underwriting_reason")
            
            # Check user intent
            user_msg_lower = state["current_message"].lower()
            negotiation_keywords = ["lower", "reduce", "less", "better", "discount", "negotiate", "cheaper"]
            proceed_keywords = ["proceed", "accept", "ok", "okay", "fine", "agree", "done", "confirm", "yes proceed", "let's do it", "go ahead"]
            
            # ==================== NEGOTIATION FLOW ====================
            # Business Rule: Max 2 negotiation attempts, then firm offer
            max_negotiations = 2
            
            if loan_amount > 0 and current_rate and any(kw in user_msg_lower for kw in negotiation_keywords):
                new_count = attempt_count + 1
                state["negotiation_state"]["attempt_count"] = new_count
                
                # Check if already exhausted negotiation attempts
                if new_count > max_negotiations:
                    state["ai_response"] = f"""{customer_name}, I've already given you our best possible rate at {current_rate}% p.a.

This rate is **non-negotiable** and already reflects a special discount for your excellent credit profile.

**Your Final Offer:**
• Loan Amount: {format_indian_currency(loan_amount)}
• Interest Rate: {current_rate}% p.a.
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: 36 months

Would you like to proceed? This rate is locked for the next 24 hours. 🔒"""
                    log_entry["negotiation_attempt"] = new_count
                    log_entry["message"] = "Max negotiations reached - presenting final offer"
                
                elif current_rate > floor_rate:
                    # Can reduce rate - but only by small amount
                    reduction = 0.25
                    new_rate = max(floor_rate, round(current_rate - reduction, 2))
                    state["negotiation_state"]["current_offered_rate"] = new_rate
                    
                    # Calculate new EMI
                    monthly_rate = new_rate / 100 / 12
                    tenure_months = 36
                    new_emi = int(loan_amount * monthly_rate * ((1 + monthly_rate) ** tenure_months) / (((1 + monthly_rate) ** tenure_months) - 1))
                    state["loan_request"]["emi"] = new_emi
                    
                    log_entry["rate_change"] = f"{current_rate}% -> {new_rate}%"
                    log_entry["negotiation_attempt"] = new_count
                    
                    if new_rate == floor_rate or new_count == max_negotiations:
                        # This is the final offer
                        savings = int((emi - new_emi) * 36) if emi > 0 else 0
                        state["ai_response"] = f"""Alright {customer_name}, I spoke with my senior manager and this is the **absolute best** we can offer:

**Your Final Offer:**
• Loan Amount: {format_indian_currency(loan_amount)}
• **Interest Rate: {new_rate}% p.a.** (reduced from {current_rate}%)
• **Monthly EMI: {format_indian_currency(new_emi)}**
• Tenure: 36 months
• **You Save: {format_indian_currency(savings)}** over the loan tenure

This is a special rate reserved for premium customers. I cannot reduce it further.

Shall I proceed with the disbursement? 🙏"""
                    else:
                        savings = int((emi - new_emi) * 36) if emi > 0 else 0
                        state["ai_response"] = f"""I managed to get approval for a reduction, {customer_name}. 😊

**Your Updated Offer:**
• Loan Amount: {format_indian_currency(loan_amount)}
• **Interest Rate: {new_rate}% p.a.** (down from {current_rate}%)
• **Monthly EMI: {format_indian_currency(new_emi)}**
• Tenure: 36 months
• **You Save: {format_indian_currency(savings)}** over the loan tenure

Shall I proceed with this offer?"""
                else:
                    # Already at floor rate
                    state["ai_response"] = f"""I understand you'd like a lower rate, {customer_name}, but {floor_rate}% is genuinely our lowest rate.

This is a **premium rate** that we only offer to customers with exceptional credit profiles like yours (780+ score).

**Your Offer:**
- Loan Amount: Rs. {loan_amount:,}
- Interest Rate: {floor_rate}% p.a. (Best Available)
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: 36 months

Would you like to proceed?"""
                
                log_entry["negotiation_attempt"] = new_count
            
            # ==================== PROCEED/ACCEPT FLOW ====================
            elif loan_amount > 0 and any(kw in user_msg_lower for kw in proceed_keywords):
                state["loan_request"]["status"] = "ACCEPTED"
                state["ai_response"] = f"""Wonderful, {customer_name}! Let me finalize your loan. 🎉

**Confirmed Loan Details:**
• Loan Amount: {format_indian_currency(loan_amount)}
• Interest Rate: {current_rate}% p.a.
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: 36 months
• First EMI Date: 5th of next month

**Next Steps:**
📄 Please upload your Salary Slip for verification

Once verified, the amount will be disbursed within 24 hours!

Click the upload button below to proceed."""
                state["show_upload"] = True
            
            # ==================== UNDERWRITING DECISIONS ====================
            elif underwriting_decision == "REJECT":
                state["ai_response"] = f"""Thank you for your interest in Tata Capital, {customer_name}.

After careful review, we're unable to approve your loan application at this time.

**Reason:** {underwriting_reason}

**What you can do:**
• Review your credit report for any errors
• Reduce existing debts to improve your profile
• Re-apply after 6 months with updated financials

We'd love to serve you in the future! For assistance, call 1800-209-0088. 🙏"""
            
            elif underwriting_decision == "APPROVE_INSTANT":
                state["ai_response"] = f"""Congratulations, {customer_name}! 🎉

**Your loan of {format_indian_currency(loan_amount)} is INSTANTLY APPROVED!**

**Loan Details:**
• Amount: {format_indian_currency(loan_amount)}
• Interest Rate: {current_rate}% per annum  
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: 36 months

This is a competitive rate based on your excellent credit profile. Shall I proceed with the disbursement?"""
            
            elif underwriting_decision == "APPROVE_WITH_DOCS":
                emi = loan_request.get("emi", 0)
                state["ai_response"] = f"""Good news, {customer_name}! 😊

**Your loan is CONDITIONALLY APPROVED!**

**Loan Details:**
• Amount: {format_indian_currency(loan_amount)}
• Interest Rate: {current_rate}% per annum  
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: 36 months

**Condition:** Please upload your salary slip for income verification.

**Reason:** {underwriting_reason}

Shall I proceed? Please upload your salary slip to continue. 📄"""
            
            else:
                # Standard sales flow - user is greeting or asking general questions
                # Check if user has shared name/phone yet
                if not user_profile.get("name") and not user_profile.get("phone"):
                    # New user - ask for identity
                    state["ai_response"] = """Hello! Welcome to Tata Capital! 😊

I'm here to help you get **instant pre-approval** for a personal loan!

To get started, please share:
• Your full name
• Your 10-digit mobile number

This helps me check your eligibility and pre-approved offers!"""
                elif user_profile.get("name") and not user_profile.get("phone"):
                    # Have name but no phone
                    name = user_profile.get("name")
                    state["ai_response"] = f"""Nice to meet you, {name}! 😊

To check your eligibility and any pre-approved offers, I'll need your **10-digit mobile number**.

This is completely secure and helps me fetch your profile instantly!"""
                elif user_profile.get("verified"):
                    # User is verified - handle general queries
                    name = user_profile.get("name", "there")
                    pre_approved = financial.get("pre_approved_limit", 0)
                    
                    if pre_approved > 0:
                        state["ai_response"] = f"""Hi {name}! Great to have you here! 😊

I can see you have a **pre-approved loan limit of {format_indian_currency(pre_approved)}**!

How much would you like to borrow today? Just tell me the amount and I'll get you instant approval!"""
                    else:
                        state["ai_response"] = f"""Hi {name}! How can I help you today?

I can assist you with:
• Personal loan applications
• Checking your eligibility
• EMI calculations
• Document requirements

What would you like to know?"""
                else:
                    # Fallback for other cases
                    state["ai_response"] = """Hello! Welcome to Tata Capital! 😊

I'm here to help you with personal loans. To serve you better, could you please share:
• Your full name
• Your 10-digit mobile number"""
            
        except Exception as e:
            print(f"Sales Agent error: {e}")
            state["ai_response"] = "Hello! Welcome to Tata Capital! I'm here to help you with your personal loan needs. Could you please share your name and phone number so I can check your eligibility? 😊"
            log_entry["error"] = str(e)
            log_entry["type"] = "warning"
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== VERIFICATION AGENT (SPOKE) ====================
    async def verification_agent_node(self, state: AgentState) -> AgentState:
        """
        VERIFICATION AGENT
        
        Responsibilities:
        1. Extract name, phone, PAN from user message
        2. Verify customer against database
        3. Fetch and populate financial data
        4. Update user profile
        """
        log_entry = {
            "agent": "Verification Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "identity_verification"
        }
        
        user_message = state["current_message"]
        customer_data = None
        match_type = None
        
        # Get current verified user info
        current_user_name = state.get("user_profile", {}).get("name")
        is_verified = state.get("user_profile", {}).get("verified", False)
        
        # Check if user is claiming to be someone different while already verified
        if is_verified and current_user_name:
            # Extract name from current message to check for mismatch
            name_check_prompt = """Extract ONLY the person's name from this message. Return just the name or "none" if no name is mentioned.
Examples:
- "i am tanisha" -> "tanisha"
- "my name is raj" -> "raj"
- "how are you" -> "none"
- "I need a loan" -> "none"
"""
            try:
                name_response = await self.llm.generate(name_check_prompt, user_message, [])
                claimed_name = name_response.strip().lower().replace('"', '').replace("'", "")
                
                if claimed_name and claimed_name != "none" and claimed_name != "null":
                    # User mentioned a name - check if it matches current verified user
                    current_name_lower = current_user_name.lower()
                    current_first_name = current_name_lower.split()[0] if current_name_lower else ""
                    
                    # If the claimed name doesn't match the verified user
                    if claimed_name not in current_name_lower and current_first_name not in claimed_name:
                        log_entry["message"] = f"⚠️ Identity mismatch: User claims to be '{claimed_name}' but is verified as '{current_user_name}'"
                        log_entry["type"] = "warning"
                        state.setdefault("admin_log", []).append(log_entry)
                        
                        state["ai_response"] = f"I notice you mentioned the name '{claimed_name.title()}', but you're currently logged in as {current_user_name}. If you'd like to switch accounts, please start a new chat session. Otherwise, how can I help you with your loan today?"
                        return state
            except Exception as e:
                print(f"Name check error: {e}")
                # Continue with normal flow if extraction fails
        
        # ==================== OTP VERIFICATION CHECK ====================
        # Initialize OTP state if not exists
        if "otp_state" not in state:
            state["otp_state"] = {}
        
        otp_state = state.get("otp_state", {})
        
        # Check if OTP was sent and user is responding with OTP
        if otp_state.get("otp_sent") and not otp_state.get("otp_verified"):
            # User should be entering OTP
            entered_otp = extract_otp_from_message(user_message)
            
            if entered_otp:
                expected_otp = otp_state.get("otp_code")
                otp_phone = otp_state.get("otp_phone")
                otp_attempts = otp_state.get("otp_attempts", 0) + 1
                state["otp_state"]["otp_attempts"] = otp_attempts
                
                if verify_otp(otp_phone, entered_otp, expected_otp):
                    # OTP verified successfully!
                    state["otp_state"]["otp_verified"] = True
                    log_entry["message"] = f"✓ OTP verified successfully for phone {otp_phone[-4:].rjust(10, 'X')}"
                    log_entry["type"] = "success"
                    
                    # Restore phone to user_profile if needed
                    if not state.get("user_profile"):
                        state["user_profile"] = {}
                    state["user_profile"]["phone"] = otp_phone
                    if otp_state.get("otp_name"):
                        state["user_profile"]["name"] = otp_state.get("otp_name")
                    
                    # Get customer data and proceed with verification
                    customer_data = self.data_provider.get_customer_by_phone(otp_phone)
                    if customer_data:
                        match_type = "PHONE_OTP_VERIFIED"
                        # Continue to customer_data processing below
                    else:
                        # Phone not in database - treat as new prospect
                        match_type = "NEW_PROSPECT_OTP_VERIFIED"
                        # Skip the extraction block - we already have the phone
                else:
                    # Wrong OTP
                    if otp_attempts >= 3:
                        # Too many attempts - reset OTP flow
                        state["otp_state"] = {}
                        log_entry["message"] = f"✗ OTP verification failed after 3 attempts for {otp_phone[-4:].rjust(10, 'X')}"
                        log_entry["type"] = "error"
                        state.setdefault("admin_log", []).append(log_entry)
                        
                        state["ai_response"] = "You've exceeded the maximum OTP attempts. For security reasons, please start over by sharing your phone number again."
                        return state
                    else:
                        remaining = 3 - otp_attempts
                        log_entry["message"] = f"✗ Wrong OTP entered. Attempts: {otp_attempts}/3"
                        log_entry["type"] = "warning"
                        state.setdefault("admin_log", []).append(log_entry)
                        
                        state["ai_response"] = f"That OTP doesn't match. Please check and try again. You have {remaining} attempt{'s' if remaining > 1 else ''} remaining."
                        return state
            else:
                # User didn't enter OTP - remind them with the stored OTP
                otp_phone = otp_state.get("otp_phone", "")
                otp_code = otp_state.get("otp_code", "")
                
                state["ai_response"] = f"Please enter the OTP for your phone number ending with {otp_phone[-4:]}.\n\n**Your OTP: {otp_code}**"
                return state
        
        # Check if user confirmed a pending match - now needs OTP
        if state.get("user_profile", {}).get("confirmed_match") and state.get("user_profile", {}).get("pending_match"):
            pending_customer = state["user_profile"]["pending_match"]
            pending_phone = pending_customer.get("phone")
            pending_name = pending_customer.get("name")
            
            # Check if OTP already verified for this match
            if otp_state.get("otp_verified") and otp_state.get("otp_phone") == pending_phone:
                # OTP already verified - proceed with customer data
                customer_data = pending_customer
                match_type = "CONFIRMED_NAME_OTP_VERIFIED"
                state["user_profile"]["phone"] = pending_phone
                del state["user_profile"]["pending_match"]
                del state["user_profile"]["confirmed_match"]
                state["user_profile"]["name"] = customer_data.get("name")
                log_entry["message"] = f"✓ User confirmed identity with OTP: {customer_data.get('name')}"
                log_entry["type"] = "success"
            else:
                # Need to send OTP for the confirmed match
                otp_code, sms_result = generate_otp(pending_phone)
                state["otp_state"] = {
                    "otp_sent": True,
                    "otp_code": otp_code,
                    "otp_phone": pending_phone,
                    "otp_verified": False,
                    "otp_attempts": 0,
                    "otp_name": pending_name,
                    "sms_result": sms_result
                }
                
                is_test_user = sms_result.get("is_test_user", False)
                log_entry["message"] = f"📱 OTP generated for {pending_phone[-4:].rjust(10, 'X')} ({pending_name})" + (" (Test user: 123456)" if is_test_user else f" (Mock mode)")
                log_entry["type"] = "info"
                state.setdefault("admin_log", []).append(log_entry)
                
                # Show OTP directly in chat for demo purposes
                state["ai_response"] = f"Great! To verify it's you, {pending_name}, I've generated an OTP for your phone number ending with {pending_phone[-4:]}.\n\n**Your OTP: {otp_code}**\n\nPlease enter the OTP to continue."
                return state
        
        if not customer_data:
            # Skip extraction if OTP was just verified (we already have the phone)
            otp_just_verified = otp_state.get("otp_verified") and match_type in ["NEW_PROSPECT_OTP_VERIFIED", None]
            
            if not otp_just_verified:
                # Need to extract entities and verify - normal flow
                extraction_prompt = """Extract the following information from the user's message. 
Return ONLY a JSON object with these fields (use null if not found):
{
    "name": "Full name of the person",
    "phone": "10-digit phone number (remove spaces, +91, etc.)",
    "pan": "PAN card number (10 characters)"
}

Examples:
- "I am Priya and my number is 9876543210" -> {"name": "Priya", "phone": "9876543210", "pan": null}
- "My name is Amit Patel, phone 91234 56789" -> {"name": "Amit Patel", "phone": "9123456789", "pan": null}
- "Rajesh Kumar here, PAN is ABCDE1234F" -> {"name": "Rajesh Kumar", "phone": null, "pan": "ABCDE1234F"}"""

                try:
                    extraction_response = await self.llm.generate(
                        extraction_prompt, 
                        user_message,
                        []
                    )
                    
                    # Parse JSON from response
                    json_match = extraction_response
                    if "```" in json_match:
                        json_match = json_match.split("```")[1].replace("json", "").strip()
                    
                    extracted = json.loads(json_match)
                    
                    # Update user profile
                    if not state.get("user_profile"):
                        state["user_profile"] = {}
                    
                    if extracted.get("name"):
                        state["user_profile"]["name"] = extracted["name"]
                    if extracted.get("phone"):
                        state["user_profile"]["phone"] = extracted["phone"]
                    if extracted.get("pan"):
                        state["user_profile"]["pan"] = extracted["pan"]
                    
                    log_entry["extracted"] = extracted
                    log_entry["message"] = f"✓ Extracted: {extracted}"
                    log_entry["type"] = "success"
                    
                    # Try to verify against database
                    phone = state["user_profile"].get("phone")
                    name = state["user_profile"].get("name")
                    
                    # Strategy 1: Exact phone match (preferred - most secure) - Now requires OTP
                    if phone:
                        found_customer = self.data_provider.get_customer_by_phone(phone)
                        
                        # Add API call events to admin_log for dashboard visibility
                        for api_event in self.data_provider.get_api_events():
                            state.setdefault("admin_log", []).append({
                                "agent": api_event["data"].get("agent", "System"),
                                "timestamp": api_event["timestamp"],
                                "type": api_event["type"],
                                "message": f"🌐 {api_event['type']}: {api_event['data'].get('service', 'API')}",
                                "api_event": api_event
                            })
                        
                        if found_customer:
                            # Found customer - need OTP verification first
                            customer_name = found_customer.get("name")
                            
                            # Check if OTP already verified for this phone
                            if otp_state.get("otp_verified") and otp_state.get("otp_phone") == phone:
                                # OTP already verified - proceed
                                customer_data = found_customer
                                match_type = "PHONE_OTP_VERIFIED"
                            else:
                                # Send OTP for verification
                                otp_code, sms_result = generate_otp(phone)
                                state["otp_state"] = {
                                    "otp_sent": True,
                                    "otp_code": otp_code,
                                    "otp_phone": phone,
                                    "otp_verified": False,
                                    "otp_attempts": 0,
                                    "otp_name": customer_name,
                                    "sms_result": sms_result
                                }
                                
                                is_test_user = sms_result.get("is_test_user", False)
                                log_entry["verification_status"] = "OTP_SENT"
                                log_entry["message"] = f"📱 OTP generated for {phone[-4:].rjust(10, 'X')} ({customer_name})" + (" (Test user: 123456)" if is_test_user else " (Mock mode)")
                                log_entry["type"] = "info"
                                state.setdefault("admin_log", []).append(log_entry)
                                
                                # Show OTP directly in chat for demo purposes
                                state["ai_response"] = f"Hi {customer_name}! I found your profile. To verify it's you, I've generated an OTP for your phone number ending with {phone[-4:]}.\n\n**Your OTP: {otp_code}**\n\nPlease enter the OTP to continue."
                                return state
                        else:
                            # Phone not in database - this is a new prospect, also need OTP
                            # For new users, still send OTP for phone verification (real SMS for non-test users)
                            otp_code, sms_result = generate_otp(phone)
                            state["otp_state"] = {
                                "otp_sent": True,
                                "otp_code": otp_code,
                                "otp_phone": phone,
                                "otp_verified": False,
                                "otp_attempts": 0,
                                "otp_name": name or "New Prospect",
                                "is_new_prospect": True,
                                "sms_result": sms_result
                            }
                            
                            is_test_user = sms_result.get("is_test_user", False)
                            log_entry["verification_status"] = "OTP_SENT_NEW_PROSPECT"
                            log_entry["message"] = f"📱 OTP generated for new prospect {phone[-4:].rjust(10, 'X')}" + (" (Test user: 123456)" if is_test_user else " (Mock mode)")
                            log_entry["type"] = "info"
                            state.setdefault("admin_log", []).append(log_entry)
                            
                            # Show OTP directly in chat for demo purposes
                            state["ai_response"] = f"Welcome{', ' + name if name else ''}! To verify your phone number, I've generated an OTP for your number ending with {phone[-4:]}.\n\n**Your OTP: {otp_code}**\n\nPlease enter the OTP to continue."
                            return state
                    
                    # Strategy 2: Fuzzy name match (fallback - only if unique match)
                    if not customer_data and name:
                        fuzzy_result = self.data_provider.fuzzy_match_by_name(name)
                        
                        if fuzzy_result.get("unique") and fuzzy_result.get("customer"):
                            # Found a match - but ask for confirmation first
                            matched_customer = fuzzy_result["customer"]
                            matched_name = matched_customer.get("name")
                            matched_phone_last4 = matched_customer.get("phone", "")[-4:]
                            
                            state["user_profile"]["pending_match"] = matched_customer
                            state["user_profile"]["verified"] = False
                            
                            log_entry["verification_status"] = "PENDING_CONFIRMATION"
                            log_entry["message"] = f"Found potential match: {matched_name} - awaiting confirmation"
                            log_entry["type"] = "info"
                            
                            state["ai_response"] = f"Hi! I found a profile for **{matched_name}** with phone number ending in **{matched_phone_last4}**. Is this you?"
                            
                            state.setdefault("admin_log", []).append(log_entry)
                            return state
                        
                        elif fuzzy_result.get("matches") and len(fuzzy_result["matches"]) > 1:
                            # Multiple people with similar names - ask for phone
                            names_found = fuzzy_result.get("names_found", [])
                            state["user_profile"]["verified"] = False
                            log_entry["verification_status"] = "MULTIPLE_MATCHES"
                            log_entry["message"] = f"Multiple customers found with similar name: {names_found}"
                            log_entry["type"] = "warning"
                            
                            state["ai_response"] = f"Hi {name}! I found multiple profiles with similar names. Could you please share your **phone number** so I can pull up the correct account?"
                            
                            state.setdefault("admin_log", []).append(log_entry)
                            return state
                    
                except Exception as e:
                    print(f"❌ Verification extraction error: {e}")
                    log_entry["error"] = str(e)
                    log_entry["type"] = "warning"
                    
                    state["ai_response"] = "I'd be happy to help you! Could you please share your **name** and **phone number**?"
                    state.setdefault("admin_log", []).append(log_entry)
                    return state
                
        # Process verified customer data (works for both phone match and confirmed name match)
        if customer_data:
            state["user_profile"]["verified"] = True
            state["user_profile"]["name"] = customer_data.get("name", state["user_profile"].get("name"))
            
            # Populate financial data
            fin_data = customer_data.get("financial_data", {})
            state["financial_data"] = {
                "credit_score": fin_data.get("credit_score", 0),
                "monthly_income": fin_data.get("monthly_income", 0),
                "annual_income": fin_data.get("annual_income", 0),
                "existing_debt": fin_data.get("total_monthly_debt", 0),
                "debt_to_income_ratio": fin_data.get("debt_to_income_ratio", 0),
                "employment_type": fin_data.get("employment_type", "Unknown"),
                "company": fin_data.get("company", "Unknown"),
                "bank_balance": fin_data.get("bank_balance", 0)
            }
            
            # Calculate pre-approved limit
            credit_score = fin_data.get("credit_score", 0)
            monthly_income = fin_data.get("monthly_income", 0)
            
            if credit_score >= 750:
                pre_approved = min(monthly_income * 60, 2000000)
            elif credit_score >= 700:
                pre_approved = min(monthly_income * 48, 1500000)
            elif credit_score >= 650:
                pre_approved = min(monthly_income * 36, 1000000)
            else:
                pre_approved = min(monthly_income * 24, 500000)
            
            state["financial_data"]["pre_approved_limit"] = pre_approved
            
            # Set floor rate based on credit score
            if credit_score >= 750:
                floor_rate = 10.25
                initial_rate = 11.99
            elif credit_score >= 700:
                floor_rate = 11.5
                initial_rate = 13.5
            elif credit_score >= 650:
                floor_rate = 12.25
                initial_rate = 14.99
            else:
                floor_rate = 14.0
                initial_rate = 17.99
            
            state["negotiation_state"] = {
                "floor_rate": floor_rate,
                "current_offered_rate": initial_rate,
                "attempt_count": 0,
                "max_attempts": 3
            }
            
            # ====== ENHANCED TRUST ANALYSIS (Auto-triggered after verification) ======
            behavioral = customer_data.get("behavioral_flags", {})
            risk_category = behavioral.get("risk_category", "MEDIUM")
            payment_delays = behavioral.get("payment_delays", 0)
            fraud_alerts = behavioral.get("fraud_alerts", 0)
            bounced_cheques = behavioral.get("bounced_cheques", 0)
            
            # Calculate comprehensive trust score based on CRM data
            trust_score = 100
            fraud_flags = []
            
            # Credit score impact
            if credit_score >= 750:
                trust_score -= 0
            elif credit_score >= 700:
                trust_score -= 10
            elif credit_score >= 650:
                trust_score -= 20
            else:
                trust_score -= 35
                fraud_flags.append(f"Low credit score: {credit_score}")
            
            # Risk category impact
            if risk_category == "FRAUD":
                trust_score -= 50
                fraud_flags.append("🚨 FRAUD ALERT: Customer flagged for fraud")
            elif risk_category == "HIGH_RISK":
                trust_score -= 30
                fraud_flags.append("⚠️ High-risk customer profile")
            elif risk_category == "YELLOW_FLAG":
                trust_score -= 15
                fraud_flags.append("⚠️ Yellow flag: Requires additional verification")
            
            # Payment history impact
            if payment_delays > 0:
                trust_score -= min(payment_delays * 5, 20)
                fraud_flags.append(f"Payment delays: {payment_delays} instances")
            
            # Fraud alerts impact
            if fraud_alerts > 0:
                trust_score -= fraud_alerts * 15
                fraud_flags.append(f"🚨 Active fraud alerts: {fraud_alerts}")
            
            # Bounced cheques impact
            if bounced_cheques > 0:
                trust_score -= bounced_cheques * 10
                fraud_flags.append(f"Bounced cheques: {bounced_cheques}")
            
            # Ensure score is within bounds
            trust_score = max(0, min(100, trust_score))
            
            state["trust_analysis"] = {
                "trust_score": trust_score,
                "risk_category": risk_category,
                "fraud_flags": fraud_flags,
                "behavioral_score": 80 if payment_delays == 0 else 60,
                "credit_score": credit_score,
                "analysis_source": "CRM_BEHAVIORAL_DATA"
            }
            
            # Log Trust Analysis to Admin Dashboard
            trust_log_entry = {
                "agent": "Trust & Safety Agent",
                "timestamp": datetime.now().isoformat(),
                "action": "automated_trust_analysis",
                "trust_score": trust_score,
                "risk_category": risk_category,
                "type": "error" if risk_category == "FRAUD" else ("warning" if risk_category in ["HIGH_RISK", "YELLOW_FLAG"] else "success"),
                "message": f"🛡️ Trust Analysis: Score {trust_score}/100 | Risk: {risk_category}" + (f" | Flags: {len(fraud_flags)}" if fraud_flags else "")
            }
            state.setdefault("admin_log", []).append(trust_log_entry)
            
            # Log individual fraud flags if any
            for flag in fraud_flags:
                flag_log = {
                    "agent": "Trust & Safety Agent",
                    "timestamp": datetime.now().isoformat(),
                    "type": "error" if "FRAUD" in flag or "🚨" in flag else "warning",
                    "message": f"  └─ {flag}"
                }
                state.setdefault("admin_log", []).append(flag_log)
            
            log_entry["verification_status"] = "VERIFIED"
            log_entry["match_type"] = match_type
            log_entry["credit_score"] = credit_score
            log_entry["trust_score"] = trust_score
            log_entry["message"] = f"✓ Customer verified ({match_type}): {state['user_profile']['name']} (Credit: {credit_score}, Trust: {trust_score})"
            
            # Mark as existing customer
            state["user_profile"]["user_type"] = "EXISTING_CUSTOMER"
            state["user_profile"]["is_new_lead"] = False
            
            # Check for pending loan request that was mentioned before verification
            pending_loan = state.get("pending_loan_request", {})
            pending_amount = pending_loan.get("amount", 0)
            
            # Also check loan_request.pending_message for stored loan intent
            if pending_amount == 0:
                pending_message = state.get("loan_request", {}).get("pending_message", "")
                if pending_message:
                    import re
                    amount_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs)', pending_message.lower())
                    if amount_match:
                        pending_amount = int(float(amount_match.group(1)) * 100000)
                        log_entry["extracted_from_pending_message"] = pending_message
            
            name = state["user_profile"]["name"]
            
            if pending_amount > 0:
                # User already mentioned loan amount - process it directly!
                log_entry["pending_loan_processed"] = pending_amount
                
                # Store the loan request
                state["loan_request"] = state.get("loan_request", {})
                state["loan_request"]["amount"] = pending_amount
                
                # Check if amount is within pre-approved limit
                if pending_amount <= pre_approved:
                    # Calculate EMI
                    monthly_rate = initial_rate / 100 / 12
                    tenure = 36
                    emi = int(pending_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1))
                    
                    state["loan_request"]["emi"] = emi
                    state["loan_request"]["underwriting_decision"] = "APPROVE_INSTANT"
                    state["loan_request"]["underwriting_reason"] = "Pre-approved customer within limit"
                    
                    state["ai_response"] = f"""Welcome back, {name}! Great news!

**Your loan of Rs. {pending_amount:,} is INSTANTLY APPROVED!**

**Your Profile:**
- Credit Score: **{credit_score}/900** {'(Excellent!)' if credit_score >= 750 else '(Good!)' if credit_score >= 700 else '(Fair)'}
- Pre-approved Limit: Rs. {pre_approved:,}

**Loan Details:**
- Amount: Rs. {pending_amount:,}
- Interest Rate: {initial_rate}% per annum
- Monthly EMI: Rs. {emi:,}
- Tenure: 36 months

This is a competitive rate based on your excellent credit profile. Shall I proceed with the disbursement?"""
                else:
                    state["ai_response"] = f"""Welcome back, {name}!

I see you're interested in Rs. {pending_amount:,}, but your pre-approved limit is Rs. {pre_approved:,}.

**Your Profile:**
- Credit Score: **{credit_score}/900**
- Pre-approved Limit: Rs. {pre_approved:,}

Would you like to proceed with a loan up to Rs. {pre_approved:,}, or provide additional income documents to qualify for a higher amount?"""
                
                # Clear pending request
                state["pending_loan_request"] = {}
                if "pending_message" in state.get("loan_request", {}):
                    del state["loan_request"]["pending_message"]
            else:
                # No pending loan - show standard welcome
                state["ai_response"] = f"""Welcome back, {name}! Great to see you again!

**You have a pre-approved offer waiting!**

**Your Profile:**
- Credit Score: **{credit_score}/900** {'(Excellent!)' if credit_score >= 750 else '(Good!)' if credit_score >= 700 else '(Fair)'}
- **Pre-approved Limit:** Rs. {pre_approved:,}
- Interest Rate: Starting from {floor_rate}% p.a.
- Employment: {fin_data.get('employment_type', 'Salaried')} at {fin_data.get('company', 'your company')}

Would you like to proceed with your pre-approved offer? Just tell me how much you'd like to borrow!"""
                    
        else:
            # NEW PROSPECT FLOW - Create lead only after OTP verification
            name = state["user_profile"].get("name")
            phone = state["user_profile"].get("phone")
            
            # Check if OTP was verified for new prospect
            otp_verified_for_new = (
                otp_state.get("otp_verified") and 
                otp_state.get("is_new_prospect") and 
                otp_state.get("otp_phone") == phone
            )
            
            # Create a new lead in the database only if OTP is verified
            if phone and otp_verified_for_new:
                customer_data = self.data_provider.create_lead(phone, name)
                state["user_profile"]["verified"] = True  # We created them, so they're verified
                state["user_profile"]["user_type"] = "NEW_PROSPECT"
                state["user_profile"]["is_new_lead"] = True
                state["user_profile"]["name"] = name or "New Prospect"
                
                # Initialize empty financial data for new prospects
                state["financial_data"] = {
                    "credit_score": None,
                    "monthly_income": None,
                    "annual_income": None,
                    "existing_debt": None,
                    "debt_to_income_ratio": None,
                    "employment_type": None,
                    "company": None,
                    "bank_balance": None,
                    "pre_approved_limit": 0
                }
                
                # Initialize negotiation state with default values
                state["negotiation_state"] = {
                    "floor_rate": 14.0,  # Default floor rate for unknown credit
                    "current_offered_rate": 17.99,  # Default rate for unknown credit
                    "attempt_count": 0,
                    "max_attempts": 3
                }
                
                state["trust_analysis"] = {
                    "trust_score": 50,  # Neutral trust for new leads
                    "risk_category": "UNKNOWN",
                    "fraud_flags": [],
                    "behavioral_score": 50
                }
                
                log_entry["verification_status"] = "NEW_LEAD_CREATED"
                log_entry["user_type"] = "NEW_PROSPECT"
                log_entry["message"] = f"✓ Created new lead: {name or 'Unknown'} ({phone})"
                log_entry["type"] = "info"
                
                # Generate new prospect welcome message
                display_name = name if name and name.lower() not in ["none", "null", ""] else ""
                if display_name:
                    state["ai_response"] = f"""Hi {display_name}, thanks for choosing Tata Capital!

I see you're new here - welcome aboard! 

To check your loan eligibility, I'll need a few details:

**First, what is your monthly salary?**

(This helps me calculate your loan limit and the best interest rate for you)"""
                else:
                    state["ai_response"] = f"""Hi there, thanks for choosing Tata Capital!

I see you're new here - welcome aboard!

To get started, could you please tell me:
1. **Your name**
2. **Your monthly salary**

This helps me calculate your loan eligibility!"""
            else:
                # No phone number provided yet
                state["user_profile"]["verified"] = False
                state["user_profile"]["user_type"] = "NEW_PROSPECT"
                log_entry["verification_status"] = "NEEDS_PHONE"
                log_entry["message"] = "New prospect - needs phone number for lead creation"
                
                display_name = name if name and name.lower() not in ["none", "null", ""] else ""
                if display_name:
                    state["ai_response"] = f"""Hi {display_name}! Welcome to Tata Capital!

To get you started and check your loan eligibility, I'll need your **10-digit phone number**.

This helps me create your profile and give you personalized loan offers!"""
                else:
                    state["ai_response"] = """Welcome to Tata Capital!

I'd love to help you with a personal loan. To get started, please share:
- Your **name**
- Your **10-digit phone number**

Example: "I am Rahul and my number is 9876543210\""""
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== UNDERWRITING AGENT (SPOKE) ====================
    async def underwriting_agent_node(self, state: AgentState) -> AgentState:
        """
        UNDERWRITING AGENT
        
        Responsibilities:
        1. Calculate loan eligibility
        2. Determine interest rates based on credit profile
        3. Calculate EMI
        4. Make approval/rejection decisions
        """
        log_entry = {
            "agent": "Underwriting Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "loan_underwriting"
        }
        
        # Check if user is verified - if not, redirect to verification
        user_profile = state.get("user_profile", {})
        if not user_profile.get("verified"):
            log_entry["message"] = "User not verified - redirecting to verification first"
            log_entry["type"] = "warning"
            state.setdefault("admin_log", []).append(log_entry)
            # Save the loan request intent for later
            state["ai_response"] = "I'd love to help you with that loan! But first, I need to verify your identity. Could you please share your name and 10-digit phone number?"
            return state

        # ...existing code...

        user_message = state["current_message"].lower()
        financial = state.get("financial_data", {})
        user_profile = state.get("user_profile", {})

        negotiation = state.get("negotiation_state", {})

        monthly_income = financial.get("monthly_income")
        credit_score = financial.get("credit_score")

        # Try to extract salary/income from the message
        income_prompt = """Extract salary/income information from this message. Return ONLY a JSON object:
    {"monthly_income": <number in rupees or null>, "employment_type": "<Salaried/Self-Employed/Business or null>"}

    IMPORTANT: If the user gives ANNUAL/YEARLY salary, DIVIDE BY 12 to get monthly income.
    - "per annum", "yearly", "annual", "p.a.", "PA", "per year" = ANNUAL (divide by 12)
    - "monthly", "per month", "p.m.", "PM" = MONTHLY (use as is)

    Examples:
    - "my salary is 75000" -> {"monthly_income": 75000, "employment_type": "Salaried"}
    - "I earn 1.2 lakh per month" -> {"monthly_income": 120000, "employment_type": "Salaried"}
    - "I'm self employed making around 80k" -> {"monthly_income": 80000, "employment_type": "Self-Employed"}
    - "50k monthly" -> {"monthly_income": 50000, "employment_type": null}
    - "I need a loan" -> {"monthly_income": null, "employment_type": null}
    - "my annual income is 12 lakhs" -> {"monthly_income": 100000, "employment_type": "Salaried"}
    - "25 lakhs per annum" -> {"monthly_income": 208333, "employment_type": "Salaried"}
    - "I earn 24 lakh yearly" -> {"monthly_income": 200000, "employment_type": "Salaried"}
    - "my CTC is 18 lakhs PA" -> {"monthly_income": 150000, "employment_type": "Salaried"}
    - "annual salary 30 lakh" -> {"monthly_income": 250000, "employment_type": "Salaried"}
    - "2 lakhs monthly" -> {"monthly_income": 200000, "employment_type": "Salaried"}"""

        try:
            income_response = await self.llm.generate(income_prompt, user_message, [])
            
            if "```" in income_response:
                income_response = income_response.split("```")[1].replace("json", "").strip()
            
            income_info = json.loads(income_response)
            
            if income_info.get("monthly_income"):
                # Update financial data
                state["financial_data"]["monthly_income"] = income_info["monthly_income"]
                state["financial_data"]["annual_income"] = income_info["monthly_income"] * 12
                
                if income_info.get("employment_type"):
                    state["financial_data"]["employment_type"] = income_info["employment_type"]
                
                # Update the lead in the database
                phone = user_profile.get("phone")
                if phone:
                    self.data_provider.update_lead(phone, {
                        "monthly_income": income_info["monthly_income"],
                        "employment_type": income_info.get("employment_type")
                    })
                
                # Assume a default credit score for new prospects (will be updated after PAN verification)
                # For now, use a conservative estimate
                estimated_credit_score = 700  # Neutral assumption
                state["financial_data"]["credit_score"] = estimated_credit_score
                
                # Calculate pre-approved limit based on income (conservative for new leads)
                monthly_income = income_info["monthly_income"]
                pre_approved = min(monthly_income * 36, 1000000)  # More conservative for new leads
                state["financial_data"]["pre_approved_limit"] = pre_approved
                
                # Update negotiation rates for new prospect
                state["negotiation_state"] = {
                    "floor_rate": 12.5,
                    "current_offered_rate": 15.99,
                    "attempt_count": 0,
                    "max_attempts": 3
                }
                
                log_entry["income_collected"] = income_info
                log_entry["message"] = f"✓ Collected income for new prospect: {format_indian_currency(monthly_income)}/month"
                log_entry["type"] = "success"
                
                customer_name = user_profile.get("name", "there")
                state["ai_response"] = f"""Thanks {customer_name}! I've noted your monthly income as **{format_indian_currency(monthly_income)}**. 😊

Based on your income, here's what we can offer:

**Your Eligibility:**
• **Pre-approved Limit:** Up to {format_indian_currency(pre_approved)}
• **Interest Rate:** Starting from {state["negotiation_state"]["current_offered_rate"]}% p.a.

Just tell me **how much you'd like to borrow** and I'll process your application!"""
                
                state.setdefault("admin_log", []).append(log_entry)
                return state
                
        except Exception as e:
            print(f"Income extraction error: {e}")
        
        # If we still don't have income, ask for it
        if not monthly_income:
            customer_name = user_profile.get("name", "there")
            state["ai_response"] = f"""Hi {customer_name}! To check your loan eligibility, I need to know your income.

**What is your monthly salary/income?** 💰

For example: "My salary is ₹75,000 per month" or "I earn 25 lakhs per annum"

This helps me calculate the best loan offer for you!"""
            
            log_entry["message"] = "New prospect - waiting for income information"
            log_entry["type"] = "info"
            state.setdefault("admin_log", []).append(log_entry)
            return state
        
        # EXISTING CUSTOMER OR NEW LEAD WITH DATA - Standard underwriting flow
        # Extract loan amount from message
        amount_prompt = """Extract the loan amount from this message. Return ONLY a JSON object:
{"amount": <number in rupees>, "purpose": "<purpose if mentioned>", "tenure": <months if mentioned>}

Examples:
- "I need 5 lakhs" -> {"amount": 500000, "purpose": null, "tenure": null}
- "want to borrow 3 lakh for home renovation" -> {"amount": 300000, "purpose": "home renovation", "tenure": null}
- "8 lakhs for 36 months" -> {"amount": 800000, "purpose": null, "tenure": 36}
- "need loan for wedding" -> {"amount": null, "purpose": "wedding", "tenure": null}"""

        try:
            amount_response = await self.llm.generate(amount_prompt, user_message, [])
            
            if "```" in amount_response:
                amount_response = amount_response.split("```")[1].replace("json", "").strip()
            
            loan_info = json.loads(amount_response)
            
            # Update loan request
            if not state.get("loan_request"):
                state["loan_request"] = {}
            
            if loan_info.get("amount"):
                state["loan_request"]["amount"] = loan_info["amount"]
            if loan_info.get("purpose"):
                state["loan_request"]["purpose"] = loan_info["purpose"]
            if loan_info.get("tenure"):
                state["loan_request"]["tenure"] = loan_info["tenure"]
            else:
                state["loan_request"]["tenure"] = 36  # Default tenure
            
            log_entry["extracted_loan"] = loan_info
            
        except Exception as e:
            print(f"Amount extraction error: {e}")
            loan_info = {}
        
        # Get values for STRICT RULE ENGINE CALCULATION (NO LLM GUESSING)
        requested_amount = state.get("loan_request", {}).get("amount", 0)
        pre_approved = financial.get("pre_approved_limit", 500000)
        credit_score = financial.get("credit_score", 650)
        existing_debt = financial.get("existing_debt", 0)
        tenure = state.get("loan_request", {}).get("tenure", 36)
        
        # ========== STRICT VERIFICATION: Use PROVEN salary from documents ==========
        document_state = state.get("document_state", {})
        proven_salary = document_state.get("proven_salary")
        salary_source = financial.get("salary_source", "CLAIMED")
        
        # ALWAYS prefer proven_salary from documents over claimed salary
        if proven_salary:
            monthly_income = proven_salary
            salary_source = "DOCUMENT_VERIFIED"
            log_entry["salary_source"] = "PROVEN (from document)"
        else:
            monthly_income = financial.get("monthly_income", 50000)
            log_entry["salary_source"] = "CLAIMED (no document yet)"
        
        # Check for discrepancies that affect underwriting
        discrepancy_flags = document_state.get("discrepancy_flags", [])
        
        # If there's a name mismatch, we cannot proceed
        if "NAME_MISMATCH" in discrepancy_flags:
            decision = "REJECT"
            reason = "Document identity mismatch - cannot verify applicant"
            state["loan_request"]["underwriting_decision"] = decision
            state["loan_request"]["underwriting_reason"] = reason
            state["ai_response"] = f"""I'm sorry, but I cannot proceed with your loan application.

**Reason:** The name on your uploaded document doesn't match your registered profile.

Please ensure you upload documents that match your registered identity, or contact customer support for assistance."""
            state.setdefault("admin_log", []).append(log_entry)
            return state
        
        # PHASE 3: STRICT BUSINESS RULES - NO LLM DECISIONS
        decision = None
        reason = None
        
        # Add salary verification note to reason
        salary_note = f" (Verified from document)" if salary_source == "DOCUMENT_VERIFIED" else " (Claimed - pending verification)"
        
        # Rule 1: Credit Score Check
        if credit_score < 700:
            decision = "REJECT"
            reason = f"Credit score {credit_score} is below minimum requirement of 700"
            
        # Rule 2: Instant Approval 
        elif requested_amount <= pre_approved:
            decision = "APPROVE_INSTANT"
            reason = f"Loan amount ₹{requested_amount:,} is within pre-approved limit ₹{pre_approved:,}{salary_note}"
            
        # Rule 3: Conditional Approval
        elif requested_amount <= (2 * pre_approved):
            # Calculate EMI at 12% for 3 years (36 months)
            monthly_rate = 12.0 / 12 / 100  # 12% annual = 1% monthly
            emi = requested_amount * monthly_rate * ((1 + monthly_rate) ** 36) / (((1 + monthly_rate) ** 36) - 1)
            emi = round(emi)
            
            # Check EMI affordability using PROVEN/VERIFIED income
            if emi <= (0.5 * monthly_income):
                decision = "APPROVE_WITH_DOCS"
                reason = f"EMI ₹{emi:,} is {(emi/monthly_income*100):.1f}% of verified income{salary_note}"
            else:
                decision = "REJECT"
                reason = f"EMI ₹{emi:,} is {(emi/monthly_income*100):.1f}% of income (>50% limit)"
                
        # Rule 4: Hard Limit
        else:  # requested_amount > (2 * pre_approved)
            decision = "REJECT"
            reason = f"Loan amount ₹{requested_amount:,} exceeds 2x pre-approved limit ₹{(2*pre_approved):,}"
        
        # Store the EXACT decision in state
        state["loan_request"]["underwriting_decision"] = decision
        state["loan_request"]["underwriting_reason"] = reason
        state["loan_request"]["credit_score"] = credit_score
        state["loan_request"]["pre_approved"] = pre_approved
        state["loan_request"]["requested_amount"] = requested_amount
        
        # Calculate current rate and EMI for display
        current_rate = negotiation.get("current_offered_rate", 12.0)
        monthly_rate = current_rate / 12 / 100
        if monthly_rate > 0 and decision in ["APPROVE_INSTANT", "APPROVE_WITH_DOCS"]:
            emi = requested_amount * monthly_rate * ((1 + monthly_rate) ** tenure) / (((1 + monthly_rate) ** tenure) - 1)
        else:
            emi = 0
        emi = round(emi)
        
        # Update states
        state["negotiation_state"]["emi_amount"] = emi
        state["negotiation_state"]["approved_amount"] = requested_amount if decision != "REJECT" else 0
        state["loan_request"]["amount"] = requested_amount
        state["loan_request"]["emi"] = emi
        
        log_entry["calculation"] = {
            "requested": requested_amount,
            "pre_approved": pre_approved,
            "credit_score": credit_score,
            "decision": decision,
            "reason": reason,
            "emi": emi,
            "rate": current_rate
        }
        log_entry["message"] = f"RULE ENGINE: {decision} - {reason}"
        log_entry["type"] = "success" if decision != "REJECT" else "error"
        
        # PHASE 3: Generate response directly from underwriting (don't route to Sales)
        name = user_profile.get("name", "valued customer")
        purpose = state.get("loan_request", {}).get("purpose", "")
        tenure = state.get("loan_request", {}).get("tenure", 36)
        
        if decision == "REJECT":
            state["ai_response"] = f"""Thank you for your interest in Tata Capital, {name}.

After careful review, we're unable to approve your loan application at this time.

**Reason:** {reason}

**What you can do:**
• Review your credit report for any errors
• Reduce existing debts to improve your profile
• Consider a smaller loan amount
• Re-apply after 6 months with updated financials

We'd love to serve you in the future! For assistance, call 1800-209-0088. 🙏"""
            
        elif decision == "APPROVE_INSTANT":
            state["ai_response"] = f"""Congratulations, {name}! 🎉

**Your loan is INSTANTLY APPROVED!**

**Loan Details:**
• Amount: {format_indian_currency(requested_amount)}{' for ' + purpose if purpose else ''}
• Interest Rate: {current_rate}% per annum
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: {tenure} months

This is a competitive rate based on your excellent credit profile. Shall I proceed with the disbursement?"""
            
        elif decision == "APPROVE_WITH_DOCS":
            state["ai_response"] = f"""Good news, {name}! 😊

**Your loan is CONDITIONALLY APPROVED!**

**Loan Details:**
• Amount: {format_indian_currency(requested_amount)}{' for ' + purpose if purpose else ''}
• Interest Rate: {current_rate}% per annum
• Monthly EMI: {format_indian_currency(emi)}
• Tenure: {tenure} months

**Condition:** Please upload your salary slip for income verification.

📄 Upload your latest salary slip to proceed with disbursement."""
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== TRUST AGENT (SPOKE) ====================
    async def trust_agent_node(self, state: AgentState) -> AgentState:
        """
        TRUST & SAFETY AGENT
        
        Responsibilities:
        1. Analyze behavioral patterns
        2. Detect fraud indicators
        3. Calculate trust score
        4. Flag suspicious activities
        """
        log_entry = {
            "agent": "Trust & Safety Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "trust_analysis"
        }
        
        user_message = state["current_message"]
        user_profile = state.get("user_profile", {})
        financial = state.get("financial_data", {})
        
        # Trust analysis prompt
        trust_prompt = """Analyze this loan application interaction for potential fraud or risk indicators.

Return a JSON object:
{
    "trust_score": <0-100>,
    "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
    "red_flags": ["list of concerns if any"],
    "reasoning": "brief explanation"
}

Look for:
- Urgency or desperation signals
- Inconsistent information
- Pressure tactics from customer
- Unusual requests
- Signs of identity fraud

Be balanced - most customers are genuine."""

        context = f"""
Message: "{user_message}"
User Profile: {json.dumps(user_profile)}
Financial Data: {json.dumps(financial)}
"""

        try:
            analysis_response = await self.llm.generate(trust_prompt, context, [])
            
            if "```" in analysis_response:
                analysis_response = analysis_response.split("```")[1].replace("json", "").strip()
            
            analysis = json.loads(analysis_response)
            
            # Update trust analysis
            state["trust_analysis"] = {
                "trust_score": analysis.get("trust_score", 70),
                "risk_category": analysis.get("risk_level", "MEDIUM"),
                "fraud_flags": analysis.get("red_flags", []),
                "behavioral_score": analysis.get("trust_score", 70),
                "reasoning": analysis.get("reasoning", "")
            }
            
            log_entry["trust_score"] = analysis.get("trust_score")
            log_entry["risk_level"] = analysis.get("risk_level")
            log_entry["message"] = f"✓ Trust Score: {analysis.get('trust_score')}, Risk: {analysis.get('risk_level')}"
            log_entry["type"] = "success" if analysis.get("risk_level") in ["LOW", "MEDIUM"] else "warning"
            
            # Generate appropriate response based on risk
            if analysis.get("risk_level") == "CRITICAL":
                state["ai_response"] = "I appreciate your interest, but I'm noticing some concerns with this application. For security purposes, I'll need to verify some additional information. Could you please provide your PAN card number for verification?"
            else:
                state["ai_response"] = ""  # Let other agents respond
                
        except Exception as e:
            print(f"Trust analysis error: {e}")
            log_entry["error"] = str(e)
            log_entry["type"] = "warning"
            state["trust_analysis"] = {"trust_score": 50, "risk_category": "MEDIUM"}
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== CONSISTENCY VERIFICATION ====================
    def verify_consistency(self, state: AgentState) -> Dict[str, Any]:
        """
        VERIFY CONSISTENCY - Cross-check claimed vs proven data
        
        Rules:
        1. Salary: If proven_salary < 90% of claimed_salary → Discrepancy
        2. Name: If fuzzy match < 80% → Reject document
        
        Returns:
            Dict with verification results and any discrepancies
        """
        result = {
            "is_consistent": True,
            "discrepancies": [],
            "verified_values": {},
            "warnings": []
        }
        
        financial = state.get("financial_data", {})
        document_state = state.get("document_state", {})
        user_profile = state.get("user_profile", {})
        
        # ---- SALARY CONSISTENCY CHECK ----
        claimed_salary = financial.get("monthly_income", 0)
        proven_salary = document_state.get("proven_salary")
        
        if proven_salary and claimed_salary > 0:
            # STRICT RULE: proven_salary must be >= 90% of claimed_salary
            if proven_salary < (0.9 * claimed_salary):
                result["is_consistent"] = False
                result["discrepancies"].append({
                    "type": "SALARY_DISCREPANCY",
                    "claimed": claimed_salary,
                    "proven": proven_salary,
                    "difference_pct": round((1 - proven_salary/claimed_salary) * 100, 1),
                    "message": f"Document shows ₹{proven_salary:,}, which is {round((1 - proven_salary/claimed_salary) * 100, 1)}% lower than claimed ₹{claimed_salary:,}"
                })
                # Use PROVEN value for underwriting
                result["verified_values"]["monthly_income"] = proven_salary
            else:
                result["verified_values"]["monthly_income"] = proven_salary
        elif proven_salary:
            result["verified_values"]["monthly_income"] = proven_salary
        
        # ---- NAME CONSISTENCY CHECK ----
        claimed_name = user_profile.get("name", "")
        document_name = document_state.get("document_name")
        name_similarity = document_state.get("name_similarity")
        
        if document_name and claimed_name:
            if name_similarity is not None:
                if name_similarity < 80:
                    result["is_consistent"] = False
                    result["discrepancies"].append({
                        "type": "NAME_MISMATCH",
                        "claimed": claimed_name,
                        "document": document_name,
                        "similarity": name_similarity,
                        "message": f"Name mismatch: '{document_name}' vs '{claimed_name}' ({name_similarity}% match)"
                    })
                else:
                    result["verified_values"]["verified_name"] = document_name
        
        # ---- PAN CONSISTENCY CHECK ----
        claimed_pan = user_profile.get("pan")
        verified_pan = document_state.get("verified_pan")
        
        if verified_pan:
            if claimed_pan and claimed_pan.upper() != verified_pan.upper():
                result["warnings"].append({
                    "type": "PAN_UPDATE",
                    "message": f"PAN updated from {claimed_pan} to {verified_pan} based on document"
                })
            result["verified_values"]["pan"] = verified_pan
        
        return result
    
    # ==================== DOCUMENT AGENT (SPOKE) ====================
    async def document_agent_node(self, state: AgentState) -> AgentState:
        """
        DOCUMENT AGENT
        
        Responsibilities:
        1. Guide user on required documents
        2. Process uploaded documents
        3. Verify document authenticity
        4. Update verification status
        """
        log_entry = {
            "agent": "Document Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "document_processing"
        }
        
        user_message = state["current_message"].lower()
        doc_state = state.get("document_state", {})
        user_profile = state.get("user_profile", {})
        financial = state.get("financial_data", {})
        
        # Check if user is verified - if not, redirect to verification
        if not user_profile.get("verified"):
            log_entry["message"] = "User not verified - redirecting to verification first"
            log_entry["type"] = "warning"
            state.setdefault("admin_log", []).append(log_entry)
            
            state["ai_response"] = "Before we discuss documents, I'll need to verify your identity first. Could you please share your name and 10-digit phone number?"
            return state
        
        uploaded = doc_state.get("uploaded_docs", [])
        credit_score = financial.get("credit_score", 650)
        
        # Determine required documents based on credit score
        if credit_score >= 750:
            required_docs = ["PAN Card", "Salary Slip"]
        elif credit_score >= 700:
            required_docs = ["PAN Card", "Salary Slip", "Bank Statement"]
        else:
            required_docs = ["PAN Card", "Salary Slip", "Bank Statement", "CIBIL Report"]
        
        state["document_state"]["required_docs"] = required_docs
        pending = [doc for doc in required_docs if doc not in uploaded]
        state["document_state"]["pending_docs"] = pending
        
        # Check if user is asking about documents or has uploaded
        if "upload" in user_message or "document" in user_message:
            if len(uploaded) == 0:
                # First time asking about documents
                state["ai_response"] = f"""Great! To finalize your loan, I'll need a few quick documents:

📄 **Required Documents:**
{chr(10).join([f'• {doc}' for doc in required_docs])}

{'Just 2 documents needed - your excellent credit score qualifies you for minimal documentation! 🌟' if credit_score >= 750 else 'Standard documentation for your profile.'}

Click the **📎 Upload** button below to start uploading. You can upload them one by one! 📤"""
                state["show_upload"] = True
            else:
                # Some documents already uploaded
                state["ai_response"] = f"""Thanks! I've received {len(uploaded)} document(s).

✅ **Uploaded:** {', '.join(uploaded)}
📄 **Still needed:** {', '.join(pending) if pending else 'All done!'}

{'Upload the remaining documents using the 📎 button below!' if pending else '🎉 All documents received! Processing your application...'}"""
                state["show_upload"] = len(pending) > 0
        
        log_entry["uploaded"] = uploaded
        log_entry["pending"] = pending
        log_entry["message"] = f"📄 Docs: {len(uploaded)}/{len(required_docs)} uploaded"
        log_entry["type"] = "info"
        
        state.setdefault("admin_log", []).append(log_entry)
        return state
    
    # ==================== RISK CONTROL AGENT (SPOKE) ====================
    async def risk_control_agent_node(self, state: AgentState) -> AgentState:
        """
        RISK CONTROL AGENT (Fraud Detection)
        
        Responsibilities:
        1. Mathematical Integrity Check for salary components
        2. Bank Statement Cross-Check for salary credits
        3. Visual Forgery Detection via Gemini Vision analysis
        
        If ANY fraud is detected:
        - Set fraud_detected = True
        - Respond with polite rejection message
        """
        log_entry = {
            "agent": "Risk Control Agent",
            "timestamp": datetime.now().isoformat(),
            "action": "fraud_detection"
        }
        
        doc_state = state.get("document_state", {})
        uploaded_docs = doc_state.get("uploaded_docs", [])
        extracted_data = doc_state.get("extracted_data", {})
        
        # Initialize risk control state
        risk_control = {
            "fraud_detected": False,
            "math_check": None,
            "bank_check": None,
            "visual_check": [],
            "overall_status": "PENDING",
            "fraud_reasons": []
        }
        
        fraud_detected = False
        fraud_reasons = []
        
        # ==================== 1. MATHEMATICAL INTEGRITY CHECK ====================
        if "Salary Slip" in uploaded_docs:
            salary_data = extracted_data.get("Salary Slip", {})
            math_result = validate_salary_math(salary_data)
            risk_control["math_check"] = math_result
            
            log_entry["math_check"] = {
                "status": math_result["status"],
                "calculated": math_result.get("calculated_net", 0),
                "extracted": math_result.get("extracted_net", 0),
                "difference": math_result.get("difference", 0)
            }
            
            if math_result["status"] == "FRAUD_DETECTED":
                fraud_detected = True
                fraud_reasons.append(f"📊 Math Check Failed: {math_result.get('reason', 'Internal inconsistency detected')}")
        
        # ==================== 2. BANK STATEMENT CROSS-CHECK ====================
        if "Salary Slip" in uploaded_docs and "Bank Statement" in uploaded_docs:
            salary_data = extracted_data.get("Salary Slip", {})
            bank_data = extracted_data.get("Bank Statement", {})
            bank_result = cross_check_bank_statement(salary_data, bank_data)
            risk_control["bank_check"] = bank_result
            
            log_entry["bank_check"] = {
                "status": bank_result["status"],
                "salary_found": bank_result.get("salary_found", False),
                "expected": bank_result.get("details", {}).get("expected_salary", 0)
            }
            
            if bank_result["status"] == "DISCREPANCY":
                fraud_detected = True
                fraud_reasons.append(f"🏦 Bank Check Failed: {bank_result.get('reason', 'Salary not found in bank statement')}")
        
        # ==================== 3. VISUAL FORGERY CHECK ====================
        visual_results = []
        for doc_type in uploaded_docs:
            doc_data = extracted_data.get(doc_type, {})
            visual_result = check_visual_forgery(doc_data)
            visual_result["document_type"] = doc_type
            visual_results.append(visual_result)
            
            if visual_result["status"] == "MANUAL_REVIEW":
                fraud_detected = True
                fraud_reasons.append(f"🔍 Visual Check ({doc_type}): {visual_result.get('reason', 'Document flagged for manual review')}")
            elif visual_result["status"] == "WARNING":
                # Warnings don't trigger fraud, but are logged
                log_entry.setdefault("warnings", []).append(f"Visual warning on {doc_type}: {visual_result.get('reason')}")
        
        risk_control["visual_check"] = visual_results
        risk_control["fraud_detected"] = fraud_detected
        risk_control["fraud_reasons"] = fraud_reasons
        
        # ==================== DETERMINE RESPONSE ====================
        if fraud_detected:
            risk_control["overall_status"] = "FRAUD_DETECTED"
            
            # Polite rejection message
            state["ai_response"] = f"""**Document Verification Issue**

I'm having trouble verifying the authenticity of your uploaded documents. This could happen due to:
- Image quality issues
- Documents not being original copies
- Formatting inconsistencies

**What you can do:**
- Please upload the **original PDF** downloaded directly from your payroll portal or bank.
- If uploading photos, ensure they're clear and not cropped.

**Need help?** Our team can assist you at **1800-XXX-XXXX** (Toll-free).

_Your application is safe - you can re-upload the correct documents to continue._"""
            
            # Mark documents as needing re-upload
            doc_state["verification_status"] = "FRAUD_SUSPECTED"
            doc_state["requires_reupload"] = True
            state["document_state"] = doc_state
            
            log_entry["message"] = f"🚨 FRAUD DETECTED: {'; '.join(fraud_reasons)}"
            log_entry["type"] = "error"
        else:
            risk_control["overall_status"] = "PASSED"
            
            # All checks passed - proceed to underwriting
            state["ai_response"] = f"""**Document Verification Complete**

All your documents have been verified successfully:
{''.join([f"{chr(10)}- {doc} (Verified)" for doc in uploaded_docs])}

Your application is now being processed for final approval. I'll update you shortly with your loan offer!"""
            
            doc_state["verification_status"] = "VERIFIED"
            state["document_state"] = doc_state
            
            log_entry["message"] = f"✅ All fraud checks passed for {len(uploaded_docs)} documents"
            log_entry["type"] = "success"
        
        # Store risk control state
        state["risk_control"] = risk_control
        
        # Log summary
        log_entry["fraud_detected"] = fraud_detected
        log_entry["documents_checked"] = uploaded_docs
        state.setdefault("admin_log", []).append(log_entry)
        
        return state
    
    # ==================== RESPONSE NODE ====================
    async def response_node(self, state: AgentState) -> AgentState:
        """
        RESPONSE NODE
        
        Final node that ensures a response is set.
        Adds the response to conversation history.
        """
        log_entry = {
            "agent": "Response Generator",
            "timestamp": datetime.now().isoformat(),
            "action": "response_finalization"
        }
        
        # If no response was set by agents, generate a default
        if not state.get("ai_response"):
            state["ai_response"] = "I'm here to help you with your loan application! Could you tell me more about what you're looking for?"
        
        # Add to conversation history
        state["conversation_history"].append({
            "role": "assistant",
            "content": state["ai_response"],
            "timestamp": datetime.now().isoformat()
        })
        
        log_entry["message"] = "✓ Response finalized"
        log_entry["type"] = "success"
        state.setdefault("admin_log", []).append(log_entry)
        
        return state
    
    # ==================== MAIN EXECUTION ====================
    async def process_message(self, user_message: str, 
                              conversation_history: List = None,
                              previous_state: Dict = None) -> Dict[str, Any]:
        """
        Process a user message through the Hub-and-Spoke architecture.
        
        Flow:
        1. Message arrives at Master Agent (Hub)
        2. Master analyzes and routes to appropriate Spoke
        3. Spoke processes and generates response
        4. Response node finalizes output
        
        Returns a dict compatible with main.py expectations:
        - ai_response: The AI's response text
        - messages: List of {role, content} for conversation history
        - admin_log: List of agent activity logs
        - trust_score: Numeric trust score
        - name, phone, pan: User details
        - customer_verified: Boolean
        - customer_profile: Full customer data
        - conversation_stage: Current stage
        - loan_decision: Decision if made
        - show_upload, show_sanction_letter: UI flags
        - loan_details: Final loan details if approved
        """
        print(f"\n{'='*60}")
        print("🚀 PROCESSING MESSAGE: Hub-and-Spoke Architecture")
        print(f"{'='*60}\n")
        
        # Restore state from previous interactions
        restored_user_profile = {}
        restored_loan_request = {}
        restored_pending_loan = {}
        restored_financial_data = {}
        restored_negotiation = {}
        restored_document = {}
        restored_trust = {}
        restored_otp = {}
        
        if previous_state:
            # Handle both old format (flat) and new format (nested)
            if previous_state.get("user_profile"):
                restored_user_profile = previous_state["user_profile"]
            else:
                # Old flat format
                restored_user_profile = {
                    "name": previous_state.get("name"),
                    "phone": previous_state.get("phone"),
                    "pan": previous_state.get("pan"),
                    "verified": previous_state.get("verified")
                }
            
            restored_loan_request = previous_state.get("loan_request", {})
            restored_pending_loan = previous_state.get("pending_loan_request", {})
            restored_financial_data = previous_state.get("financial_data", {})
            restored_negotiation = previous_state.get("negotiation_state", {})
            restored_document = previous_state.get("document_state", {})
            restored_trust = previous_state.get("trust_analysis", {})
            restored_otp = previous_state.get("otp_state", {})
        
        # Initialize state
        initial_state: AgentState = {
            "conversation_history": conversation_history or [],
            "current_message": user_message,
            "user_profile": restored_user_profile,
            "loan_request": restored_loan_request,
            "pending_loan_request": restored_pending_loan,
            "financial_data": restored_financial_data,
            "negotiation_state": restored_negotiation,
            "document_state": restored_document,
            "trust_analysis": restored_trust,
            "otp_state": restored_otp,
            "decision": {},
            "next_step": "",
            "ai_response": "",
            "show_upload": False,
            "show_sanction_letter": False,
            "loan_details": None,
            "admin_log": []
        }
        
        # Add user message to history
        initial_state["conversation_history"].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Execute the graph
        final_state = await self.graph.ainvoke(initial_state)
        
        print(f"\n📊 FINAL STATE:")
        print(f"User: {final_state.get('user_profile', {}).get('name', 'Unknown')}")
        print(f"Trust Score: {final_state.get('trust_analysis', {}).get('trust_score', 'N/A')}")
        print(f"Response Length: {len(final_state.get('ai_response', ''))}")
        print(f"{'='*60}\n")
        
        # Build response compatible with main.py
        user_profile = final_state.get("user_profile", {})
        trust_analysis = final_state.get("trust_analysis", {})
        financial_data = final_state.get("financial_data", {})
        
        # Build customer_profile in expected format
        customer_profile = None
        if user_profile.get("verified"):
            customer_profile = {
                "name": user_profile.get("name"),
                "phone": user_profile.get("phone"),
                "pan": user_profile.get("pan"),
                "financial_data": financial_data,
                "behavioral_flags": {
                    "risk_category": trust_analysis.get("risk_category", "MEDIUM")
                }
            }
        
        # Determine conversation stage
        stage = "greeting"
        if user_profile.get("verified"):
            if final_state.get("loan_request", {}).get("amount"):
                stage = "underwriting"
            else:
                stage = "offer"
        elif user_profile.get("name"):
            stage = "verification"
        
        # Convert conversation history to messages format
        messages = []
        for msg in final_state.get("conversation_history", []):
            messages.append({
                "role": msg.get("role"),
                "content": msg.get("content")
            })
        
        # Return result in expected format
        return {
            # Core response
            "ai_response": final_state.get("ai_response", ""),
            "messages": messages,
            
            # Admin logging
            "admin_log": final_state.get("admin_log", []),
            
            # Trust & Risk
            "trust_score": trust_analysis.get("trust_score", 50),
            "fraud_flags": trust_analysis.get("fraud_flags", []),
            
            # User identification
            "name": user_profile.get("name"),
            "phone": user_profile.get("phone"),
            "pan": user_profile.get("pan"),
            "customer_verified": user_profile.get("verified", False),
            "customer_profile": customer_profile,
            "verification_status": "VERIFIED" if user_profile.get("verified") else "PENDING",
            
            # Conversation state
            "conversation_stage": stage,
            "loan_decision": final_state.get("decision", {}).get("loan_decision"),
            "missing_info": [],
            
            # UI Flags
            "show_upload": final_state.get("show_upload", False),
            "show_sanction_letter": final_state.get("show_sanction_letter", False),
            "loan_details": final_state.get("loan_details"),
            
            # Preserve state for next call (nested format)
            "user_profile": user_profile,
            "loan_request": final_state.get("loan_request", {}),
            "pending_loan_request": final_state.get("pending_loan_request", {}),
            "financial_data": financial_data,
            "negotiation_state": final_state.get("negotiation_state", {}),
            "document_state": final_state.get("document_state", {}),
            "trust_analysis": trust_analysis,
            "otp_state": final_state.get("otp_state", {})
        }


# ==================== FACTORY FUNCTION ====================
async def create_agent(gemini_api_key: str) -> LoanAgentGraph:
    """Factory function to create the Hub-and-Spoke agent"""
    return LoanAgentGraph(gemini_api_key)
