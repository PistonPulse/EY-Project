"""
Mock Data Provider for TataSmartAgent v3.0
Contains 50 diverse customer profiles for testing the agentic workflow
Updated with new customer database

================================================================================
MOBILE NUMBER AS PRIMARY IDENTIFIER - ARCHITECTURE DECISION
================================================================================

WHY mobile_number IS THE PRIMARY KEY:
-------------------------------------
1. BANKING REALISM:
   - In Indian NBFC/banking systems, mobile number is the de-facto unique identifier
   - All communications (OTP, alerts, statements) go to mobile
   - KYC regulations mandate mobile verification before any financial transaction
   
2. OTP GATING:
   - Mobile number enables OTP verification flow
   - OTP must be verified BEFORE any CRM/financial data lookup
   - This prevents identity bypass attacks
   
3. SESSION IDENTITY:
   - Mobile number links: chat session → OTP verification → CRM lookup → loan decision
   - Single source of truth throughout the conversation
   
4. ADMIN DASHBOARD VISIBILITY:
   - Mobile number (masked) shown on admin dashboard
   - OTP verification status and timestamp visible
   - Audit trail for compliance

DATA STRUCTURE:
---------------
CUSTOMER_PROFILES = {
    "9127384590": {  # <-- mobile_number is the key
        "name": "...",
        "mobile_number": "9127384590",  # <-- redundant but explicit
        ...
    }
}

CRM LOOKUP FLOW (POST-OTP):
---------------------------
1. User provides mobile_number → OTP sent
2. User enters OTP → verified
3. ONLY THEN: CRM lookup by mobile_number
4. Customer data returned from verified source

================================================================================
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

# ==================== DATACLASS DEFINITIONS ====================
@dataclass
class CustomerProfile:
    """Structured customer profile using dataclass for better type safety"""
    id: str
    name: str
    phone: str
    pan: str
    email: str
    credit_score: int
    monthly_income: float
    annual_income: float
    total_debt: float
    debt_to_income_ratio: float
    risk_category: str  # PRIME, FRAUD, HIGH_RISK, YELLOW_FLAG, etc.
    flags: List[str]
    employment_type: str
    company: str
    work_experience_years: int
    bank_balance: float
    payment_delays: int
    fraud_alerts: int
    bounced_cheques: int
    loan_history: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return asdict(self)


def get_risk_category(credit_score: int, existing_customer: bool) -> str:
    """Determine risk category based on credit score"""
    if credit_score >= 800:
        return "SUPER_PRIME"
    elif credit_score >= 750:
        return "PRIME"
    elif credit_score >= 700:
        return "NEAR_PRIME"
    elif credit_score >= 650:
        return "SUB_PRIME"
    else:
        return "HIGH_RISK"


def get_loan_history(credit_score: int) -> str:
    """Determine loan history based on credit score"""
    if credit_score >= 750:
        return "Excellent"
    elif credit_score >= 700:
        return "Good"
    elif credit_score >= 650:
        return "Fair"
    else:
        return "Poor"


# Mock Customer Database - 50 Diverse Profiles from CSV
CUSTOMER_PROFILES: Dict[str, Dict[str, Any]] = {
    # ================================================================================
    # TEST USERS (matching TEST_INPUTS.md)
    # ================================================================================
    # Rahul Mehta - APPROVED case (Credit 750+, Pre-approved ₹10L)
    "9876543210": {
        "name": "Rahul Mehta",
        "mobile_number": "9876543210",
        "pan": "ABCDE1234F",
        "aadhaar": "1234-5678-9012",
        "email": "rahul.mehta@test.com",
        "age": 35,
        "city": "Mumbai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 780,
            "annual_income": 1200000,
            "monthly_income": 100000,
            "employment_type": "Salaried",
            "company": "TCS",
            "work_experience_years": 10,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 500000,
            "preapproved_limit": 1000000,  # ₹10L
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # Amit Verma - CONDITIONAL case (Credit 720, Pre-approved ₹5L)
    "9988776655": {
        "name": "Amit Verma",
        "mobile_number": "9988776655",
        "pan": "GHIJK5678M",
        "aadhaar": "2345-6789-0123",
        "email": "amit.verma@test.com",
        "age": 40,
        "city": "Bangalore",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 720,
            "annual_income": 900000,
            "monthly_income": 75000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 12,
            "existing_loans": [{"type": "Car Loan", "emi": 15000, "outstanding": 200000}],
            "total_monthly_debt": 15000,
            "debt_to_income_ratio": 0.2,
            "bank_balance": 300000,
            "preapproved_limit": 500000,  # ₹5L
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # Priya Sharma - REJECTED case (Credit 650, Pre-approved ₹3L)
    "9123456781": {
        "name": "Priya Sharma",
        "mobile_number": "9123456781",
        "pan": "MNOPQ9012R",
        "aadhaar": "3456-7890-1234",
        "email": "priya.sharma@test.com",
        "age": 28,
        "city": "Delhi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 650,
            "annual_income": 600000,
            "monthly_income": 50000,
            "employment_type": "Self-Employed",
            "company": "Freelancer",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Personal Loan", "emi": 10000, "outstanding": 150000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.2,
            "bank_balance": 100000,
            "preapproved_limit": 300000,  # ₹3L
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 3,
            "fraud_alerts": 0,
            "bounced_cheques": 1,
            "risk_category": "SUBPRIME",
        },
        "application_history": [],
    },
    # ================================================================================
    # ORIGINAL PROFILES (from CSV)
    # ================================================================================
    # C001 - Rahul Mehta (original)
    "9127384590": {
        "name": "Rahul Mehta",
        "mobile_number": "9127384590",
        "pan": "AQMPR1234L",
        "aadhaar": "2345-6789-1234",
        "email": "rahul.mehta@email.com",
        "age": 32,
        "city": "Mumbai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 780,
            "annual_income": 720000,
            "monthly_income": 60000,
            "employment_type": "Salaried",
            "company": "TCS",
            "work_experience_years": 8,
            "existing_loans": [{"type": "Personal Loan", "emi": 8000, "outstanding": 100000}],
            "total_monthly_debt": 8000,
            "debt_to_income_ratio": 0.133,
            "bank_balance": 300000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C002 - Priya Sharma
    "9815467328": {
        "name": "Priya Sharma",
        "mobile_number": "9815467328",
        "pan": "BTXPS2345K",
        "aadhaar": "3456-7891-2345",
        "email": "priya.sharma@email.com",
        "age": 29,
        "city": "Delhi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 820,
            "annual_income": 1020000,
            "monthly_income": 85000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Credit Card", "emi": 12000, "outstanding": 150000}],
            "total_monthly_debt": 12000,
            "debt_to_income_ratio": 0.141,
            "bank_balance": 500000,
            "preapproved_limit": 500000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C003 - Amit Verma
    "9890347612": {
        "name": "Amit Verma",
        "mobile_number": "9890347612",
        "pan": "CPRTV3456Z",
        "aadhaar": "4567-8912-3456",
        "email": "amit.verma@email.com",
        "age": 35,
        "city": "Pune",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 690,
            "annual_income": 660000,
            "monthly_income": 55000,
            "employment_type": "Salaried",
            "company": "Wipro",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Two Wheeler Loan", "emi": 5000, "outstanding": 50000}],
            "total_monthly_debt": 5000,
            "debt_to_income_ratio": 0.091,
            "bank_balance": 200000,
            "preapproved_limit": 200000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C004 - Neha Kapoor
    "9001786543": {
        "name": "Neha Kapoor",
        "mobile_number": "9001786543",
        "pan": "DPKPN4567Q",
        "aadhaar": "5678-9123-4567",
        "email": "neha.kapoor@email.com",
        "age": 28,
        "city": "Bangalore",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 760,
            "annual_income": 864000,
            "monthly_income": 72000,
            "employment_type": "Salaried",
            "company": "Amazon",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Car Loan", "emi": 10000, "outstanding": 250000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.139,
            "bank_balance": 400000,
            "preapproved_limit": 400000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C005 - Arjun Singh
    "9174628391": {
        "name": "Arjun Singh",
        "mobile_number": "9174628391",
        "pan": "ESRTS5678P",
        "aadhaar": "6789-1234-5678",
        "email": "arjun.singh@email.com",
        "age": 34,
        "city": "Chandigarh",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 730,
            "annual_income": 780000,
            "monthly_income": 65000,
            "employment_type": "Salaried",
            "company": "HCL",
            "work_experience_years": 9,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 350000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C006 - Kavya Nair
    "9081764523": {
        "name": "Kavya Nair",
        "mobile_number": "9081764523",
        "pan": "FNTCK6789R",
        "aadhaar": "7891-2345-6789",
        "email": "kavya.nair@email.com",
        "age": 30,
        "city": "Kochi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 790,
            "annual_income": 816000,
            "monthly_income": 68000,
            "employment_type": "Salaried",
            "company": "Tech Mahindra",
            "work_experience_years": 7,
            "existing_loans": [{"type": "Personal Loan", "emi": 9000, "outstanding": 120000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.132,
            "bank_balance": 350000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C007 - Rohit Iyer
    "9345871620": {
        "name": "Rohit Iyer",
        "mobile_number": "9345871620",
        "pan": "GHIUR7891M",
        "aadhaar": "8912-3456-7891",
        "email": "rohit.iyer@email.com",
        "age": 33,
        "city": "Chennai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 810,
            "annual_income": 1080000,
            "monthly_income": 90000,
            "employment_type": "Salaried",
            "company": "Google",
            "work_experience_years": 8,
            "existing_loans": [{"type": "Home Loan", "emi": 15000, "outstanding": 500000}],
            "total_monthly_debt": 15000,
            "debt_to_income_ratio": 0.167,
            "bank_balance": 600000,
            "preapproved_limit": 450000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C008 - Sneha Patil
    "9217640835": {
        "name": "Sneha Patil",
        "mobile_number": "9217640835",
        "pan": "HJPKL8912N",
        "aadhaar": "9123-4567-8912",
        "email": "sneha.patil@email.com",
        "age": 27,
        "city": "Pune",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 720,
            "annual_income": 576000,
            "monthly_income": 48000,
            "employment_type": "Salaried",
            "company": "Accenture",
            "work_experience_years": 4,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 200000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C009 - Varun Khanna
    "9876043819": {
        "name": "Varun Khanna",
        "mobile_number": "9876043819",
        "pan": "IKLPM9123B",
        "aadhaar": "1234-5678-9123",
        "email": "varun.khanna@email.com",
        "age": 36,
        "city": "Delhi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 830,
            "annual_income": 1140000,
            "monthly_income": 95000,
            "employment_type": "Salaried",
            "company": "Microsoft",
            "work_experience_years": 12,
            "existing_loans": [{"type": "Car Loan", "emi": 18000, "outstanding": 400000}],
            "total_monthly_debt": 18000,
            "debt_to_income_ratio": 0.189,
            "bank_balance": 700000,
            "preapproved_limit": 600000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C010 - Ananya Rao
    "9157396028": {
        "name": "Ananya Rao",
        "mobile_number": "9157396028",
        "pan": "JMKTR0123C",
        "aadhaar": "2345-6789-0123",
        "email": "ananya.rao@email.com",
        "age": 31,
        "city": "Hyderabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 740,
            "annual_income": 744000,
            "monthly_income": 62000,
            "employment_type": "Salaried",
            "company": "Deloitte",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Personal Loan", "emi": 7000, "outstanding": 80000}],
            "total_monthly_debt": 7000,
            "debt_to_income_ratio": 0.113,
            "bank_balance": 250000,
            "preapproved_limit": 250000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C011 - Vikram Joshi
    "9897624105": {
        "name": "Vikram Joshi",
        "mobile_number": "9897624105",
        "pan": "KPLMN2345D",
        "aadhaar": "3456-7801-2345",
        "email": "vikram.joshi@email.com",
        "age": 38,
        "city": "Mumbai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 710,
            "annual_income": 696000,
            "monthly_income": 58000,
            "employment_type": "Salaried",
            "company": "Cognizant",
            "work_experience_years": 13,
            "existing_loans": [{"type": "Home Loan", "emi": 6000, "outstanding": 200000}],
            "total_monthly_debt": 6000,
            "debt_to_income_ratio": 0.103,
            "bank_balance": 280000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C012 - Pooja Singh
    "9064157382": {
        "name": "Pooja Singh",
        "mobile_number": "9064157382",
        "pan": "LKJHG3456F",
        "aadhaar": "4567-8910-3456",
        "email": "pooja.singh@email.com",
        "age": 26,
        "city": "Jaipur",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 680,
            "annual_income": 504000,
            "monthly_income": 42000,
            "employment_type": "Salaried",
            "company": "Capgemini",
            "work_experience_years": 3,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 120000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C013 - Suresh Reddy
    "9845639172": {
        "name": "Suresh Reddy",
        "mobile_number": "9845639172",
        "pan": "MNBVC4567G",
        "aadhaar": "5678-9012-4567",
        "email": "suresh.reddy@email.com",
        "age": 37,
        "city": "Hyderabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 770,
            "annual_income": 840000,
            "monthly_income": 70000,
            "employment_type": "Salaried",
            "company": "IBM",
            "work_experience_years": 11,
            "existing_loans": [{"type": "Car Loan", "emi": 11000, "outstanding": 280000}],
            "total_monthly_debt": 11000,
            "debt_to_income_ratio": 0.157,
            "bank_balance": 400000,
            "preapproved_limit": 400000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C014 - Meera Iyer
    "9238701645": {
        "name": "Meera Iyer",
        "mobile_number": "9238701645",
        "pan": "NMASD5678H",
        "aadhaar": "6789-0123-5678",
        "email": "meera.iyer@email.com",
        "age": 29,
        "city": "Chennai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 760,
            "annual_income": 816000,
            "monthly_income": 68000,
            "employment_type": "Salaried",
            "company": "Oracle",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Personal Loan", "emi": 9000, "outstanding": 100000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.132,
            "bank_balance": 350000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C015 - Akash Gupta
    "9195627840": {
        "name": "Akash Gupta",
        "mobile_number": "9195627840",
        "pan": "OPQWE6789J",
        "aadhaar": "7890-1234-6789",
        "email": "akash.gupta@email.com",
        "age": 33,
        "city": "Delhi",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 690,
            "annual_income": 600000,
            "monthly_income": 50000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 8,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 180000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C016 - Ritika Malhotra
    "9823147069": {
        "name": "Ritika Malhotra",
        "mobile_number": "9823147069",
        "pan": "PLOKI7890K",
        "aadhaar": "8901-2345-7890",
        "email": "ritika.malhotra@email.com",
        "age": 28,
        "city": "Mumbai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 820,
            "annual_income": 1056000,
            "monthly_income": 88000,
            "employment_type": "Salaried",
            "company": "Goldman Sachs",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Credit Card", "emi": 14000, "outstanding": 180000}],
            "total_monthly_debt": 14000,
            "debt_to_income_ratio": 0.159,
            "bank_balance": 550000,
            "preapproved_limit": 550000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C017 - Nikhil Bansal
    "9017843625": {
        "name": "Nikhil Bansal",
        "mobile_number": "9017843625",
        "pan": "QAZWS8901L",
        "aadhaar": "9012-3456-8901",
        "email": "nikhil.bansal@email.com",
        "age": 34,
        "city": "Gurgaon",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 800,
            "annual_income": 900000,
            "monthly_income": 75000,
            "employment_type": "Salaried",
            "company": "Adobe",
            "work_experience_years": 9,
            "existing_loans": [{"type": "Home Loan", "emi": 10000, "outstanding": 350000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.133,
            "bank_balance": 450000,
            "preapproved_limit": 450000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C018 - Ayesha Khan
    "9341068572": {
        "name": "Ayesha Khan",
        "mobile_number": "9341068572",
        "pan": "WSXED9012M",
        "aadhaar": "0123-4567-9012",
        "email": "ayesha.khan@email.com",
        "age": 30,
        "city": "Lucknow",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 710,
            "annual_income": 624000,
            "monthly_income": 52000,
            "employment_type": "Salaried",
            "company": "HDFC Bank",
            "work_experience_years": 6,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 200000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C019 - Manoj Kumar
    "9170386249": {
        "name": "Manoj Kumar",
        "mobile_number": "9170386249",
        "pan": "EDCRF9013N",
        "aadhaar": "1234-5678-9013",
        "email": "manoj.kumar@email.com",
        "age": 39,
        "city": "Patna",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 680,
            "annual_income": 576000,
            "monthly_income": 48000,
            "employment_type": "Salaried",
            "company": "BSNL",
            "work_experience_years": 14,
            "existing_loans": [{"type": "Personal Loan", "emi": 4000, "outstanding": 50000}],
            "total_monthly_debt": 4000,
            "debt_to_income_ratio": 0.083,
            "bank_balance": 150000,
            "preapproved_limit": 200000,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 2,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C020 - Sakshi Joshi
    "9065724831": {
        "name": "Sakshi Joshi",
        "mobile_number": "9065724831",
        "pan": "RFVTG0124P",
        "aadhaar": "2345-6789-0124",
        "email": "sakshi.joshi@email.com",
        "age": 27,
        "city": "Bhopal",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 750,
            "annual_income": 720000,
            "monthly_income": 60000,
            "employment_type": "Salaried",
            "company": "Wipro",
            "work_experience_years": 4,
            "existing_loans": [{"type": "Two Wheeler Loan", "emi": 8000, "outstanding": 60000}],
            "total_monthly_debt": 8000,
            "debt_to_income_ratio": 0.133,
            "bank_balance": 280000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C021 - Ravi Shankar
    "9846157932": {
        "name": "Ravi Shankar",
        "mobile_number": "9846157932",
        "pan": "TGBNH1234Q",
        "aadhaar": "3456-7891-1234",
        "email": "ravi.shankar@email.com",
        "age": 36,
        "city": "Bangalore",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 830,
            "annual_income": 1104000,
            "monthly_income": 92000,
            "employment_type": "Salaried",
            "company": "Flipkart",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Home Loan", "emi": 16000, "outstanding": 600000}],
            "total_monthly_debt": 16000,
            "debt_to_income_ratio": 0.174,
            "bank_balance": 650000,
            "preapproved_limit": 500000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C022 - Divya Nair
    "9274018653": {
        "name": "Divya Nair",
        "mobile_number": "9274018653",
        "pan": "YHNJU2345R",
        "aadhaar": "4567-8912-2345",
        "email": "divya.nair@email.com",
        "age": 31,
        "city": "Kochi",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 720,
            "annual_income": 660000,
            "monthly_income": 55000,
            "employment_type": "Salaried",
            "company": "TCS",
            "work_experience_years": 7,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 220000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C023 - Karthik Menon
    "9125876340": {
        "name": "Karthik Menon",
        "mobile_number": "9125876340",
        "pan": "UIKLO3456S",
        "aadhaar": "5678-9123-3456",
        "email": "karthik.menon@email.com",
        "age": 29,
        "city": "Trivandrum",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 740,
            "annual_income": 756000,
            "monthly_income": 63000,
            "employment_type": "Salaried",
            "company": "UST Global",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Personal Loan", "emi": 7000, "outstanding": 90000}],
            "total_monthly_debt": 7000,
            "debt_to_income_ratio": 0.111,
            "bank_balance": 280000,
            "preapproved_limit": 280000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C024 - Shweta Kulkarni
    "9347052186": {
        "name": "Shweta Kulkarni",
        "mobile_number": "9347052186",
        "pan": "IOLKP4567T",
        "aadhaar": "6789-1234-4567",
        "email": "shweta.kulkarni@email.com",
        "age": 28,
        "city": "Nagpur",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 760,
            "annual_income": 804000,
            "monthly_income": 67000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Car Loan", "emi": 9000, "outstanding": 200000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.134,
            "bank_balance": 320000,
            "preapproved_limit": 320000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C025 - Aditya Birla
    "9817426095": {
        "name": "Aditya Birla",
        "mobile_number": "9817426095",
        "pan": "POIUY5678V",
        "aadhaar": "7891-2345-5678",
        "email": "aditya.birla@email.com",
        "age": 35,
        "city": "Jaipur",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 840,
            "annual_income": 1176000,
            "monthly_income": 98000,
            "employment_type": "Salaried",
            "company": "McKinsey",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Home Loan", "emi": 19000, "outstanding": 800000}],
            "total_monthly_debt": 19000,
            "debt_to_income_ratio": 0.194,
            "bank_balance": 750000,
            "preapproved_limit": 600000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C026 - Priyanshi Shah
    "9051867432": {
        "name": "Priyanshi Shah",
        "mobile_number": "9051867432",
        "pan": "LKJHG6789W",
        "aadhaar": "8912-3456-6789",
        "email": "priyanshi.shah@email.com",
        "age": 27,
        "city": "Ahmedabad",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 700,
            "annual_income": 600000,
            "monthly_income": 50000,
            "employment_type": "Salaried",
            "company": "ICICI Bank",
            "work_experience_years": 4,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 180000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C027 - Harsh Patel
    "9874501269": {
        "name": "Harsh Patel",
        "mobile_number": "9874501269",
        "pan": "MNBVC7890X",
        "aadhaar": "9123-4567-7890",
        "email": "harsh.patel@email.com",
        "age": 32,
        "city": "Surat",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 780,
            "annual_income": 816000,
            "monthly_income": 68000,
            "employment_type": "Salaried",
            "company": "Reliance",
            "work_experience_years": 8,
            "existing_loans": [{"type": "Personal Loan", "emi": 10000, "outstanding": 130000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.147,
            "bank_balance": 380000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C028 - Neeraj Yadav
    "9193740562": {
        "name": "Neeraj Yadav",
        "mobile_number": "9193740562",
        "pan": "ZXCVB9014Y",
        "aadhaar": "1234-5678-9014",
        "email": "neeraj.yadav@email.com",
        "age": 36,
        "city": "Gurgaon",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 790,
            "annual_income": 864000,
            "monthly_income": 72000,
            "employment_type": "Salaried",
            "company": "PayTM",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Car Loan", "emi": 11000, "outstanding": 250000}],
            "total_monthly_debt": 11000,
            "debt_to_income_ratio": 0.153,
            "bank_balance": 420000,
            "preapproved_limit": 400000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C029 - Kiran Rao
    "9847503162": {
        "name": "Kiran Rao",
        "mobile_number": "9847503162",
        "pan": "ASDFG0125Z",
        "aadhaar": "2345-6789-0125",
        "email": "kiran.rao@email.com",
        "age": 33,
        "city": "Hyderabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 750,
            "annual_income": 780000,
            "monthly_income": 65000,
            "employment_type": "Salaried",
            "company": "Tech Mahindra",
            "work_experience_years": 8,
            "existing_loans": [{"type": "Personal Loan", "emi": 9000, "outstanding": 110000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.138,
            "bank_balance": 320000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C030 - Ankit Jain
    "9126073458": {
        "name": "Ankit Jain",
        "mobile_number": "9126073458",
        "pan": "QWERT1235A",
        "aadhaar": "3456-7891-1235",
        "email": "ankit.jain@email.com",
        "age": 31,
        "city": "Delhi",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 690,
            "annual_income": 576000,
            "monthly_income": 48000,
            "employment_type": "Salaried",
            "company": "HCL",
            "work_experience_years": 6,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 160000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C031 - Pankaj Singh
    "9385174026": {
        "name": "Pankaj Singh",
        "mobile_number": "9385174026",
        "pan": "PLMOK2346B",
        "aadhaar": "4567-8912-2346",
        "email": "pankaj.singh@email.com",
        "age": 37,
        "city": "Lucknow",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 720,
            "annual_income": 720000,
            "monthly_income": 60000,
            "employment_type": "Salaried",
            "company": "State Bank",
            "work_experience_years": 12,
            "existing_loans": [{"type": "Home Loan", "emi": 8000, "outstanding": 300000}],
            "total_monthly_debt": 8000,
            "debt_to_income_ratio": 0.133,
            "bank_balance": 280000,
            "preapproved_limit": 250000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C032 - Riya Gupta
    "9016843759": {
        "name": "Riya Gupta",
        "mobile_number": "9016843759",
        "pan": "NJHBG3457C",
        "aadhaar": "5678-9123-3457",
        "email": "riya.gupta@email.com",
        "age": 28,
        "city": "Noida",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 760,
            "annual_income": 768000,
            "monthly_income": 64000,
            "employment_type": "Salaried",
            "company": "Genpact",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Two Wheeler Loan", "emi": 9000, "outstanding": 70000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.141,
            "bank_balance": 300000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C033 - Vishal Verma
    "9267501843": {
        "name": "Vishal Verma",
        "mobile_number": "9267501843",
        "pan": "BVCXZ4568D",
        "aadhaar": "6789-1234-4568",
        "email": "vishal.verma@email.com",
        "age": 34,
        "city": "Kanpur",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 670,
            "annual_income": 540000,
            "monthly_income": 45000,
            "employment_type": "Salaried",
            "company": "BHEL",
            "work_experience_years": 9,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 130000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 2,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C034 - Pallavi Joshi
    "9148637205": {
        "name": "Pallavi Joshi",
        "mobile_number": "9148637205",
        "pan": "CXZAQ5679E",
        "aadhaar": "7891-2345-5679",
        "email": "pallavi.joshi@email.com",
        "age": 30,
        "city": "Pune",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 740,
            "annual_income": 744000,
            "monthly_income": 62000,
            "employment_type": "Salaried",
            "company": "Persistent",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Personal Loan", "emi": 7000, "outstanding": 85000}],
            "total_monthly_debt": 7000,
            "debt_to_income_ratio": 0.113,
            "bank_balance": 280000,
            "preapproved_limit": 280000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C035 - Rakesh Kumar
    "9057146823": {
        "name": "Rakesh Kumar",
        "mobile_number": "9057146823",
        "pan": "ZAQWS6780F",
        "aadhaar": "8912-3456-6780",
        "email": "rakesh.kumar@email.com",
        "age": 39,
        "city": "Patna",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 660,
            "annual_income": 564000,
            "monthly_income": 47000,
            "employment_type": "Salaried",
            "company": "NTPC",
            "work_experience_years": 14,
            "existing_loans": [{"type": "Personal Loan", "emi": 4000, "outstanding": 45000}],
            "total_monthly_debt": 4000,
            "debt_to_income_ratio": 0.085,
            "bank_balance": 140000,
            "preapproved_limit": 200000,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 2,
            "fraud_alerts": 0,
            "bounced_cheques": 1,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C036 - Neha Singh
    "9876341508": {
        "name": "Neha Singh",
        "mobile_number": "9876341508",
        "pan": "XSWED7891G",
        "aadhaar": "9123-4567-7891",
        "email": "neha.singh@email.com",
        "age": 27,
        "city": "Delhi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 780,
            "annual_income": 816000,
            "monthly_income": 68000,
            "employment_type": "Salaried",
            "company": "Zomato",
            "work_experience_years": 4,
            "existing_loans": [{"type": "Credit Card", "emi": 10000, "outstanding": 120000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.147,
            "bank_balance": 350000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C037 - Sandeep Reddy
    "9846215073": {
        "name": "Sandeep Reddy",
        "mobile_number": "9846215073",
        "pan": "CDEFR9015H",
        "aadhaar": "1234-5678-9015",
        "email": "sandeep.reddy@email.com",
        "age": 36,
        "city": "Hyderabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 800,
            "annual_income": 900000,
            "monthly_income": 75000,
            "employment_type": "Salaried",
            "company": "Amazon",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Home Loan", "emi": 12000, "outstanding": 450000}],
            "total_monthly_debt": 12000,
            "debt_to_income_ratio": 0.16,
            "bank_balance": 480000,
            "preapproved_limit": 400000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C038 - Aditi Nair
    "9276051834": {
        "name": "Aditi Nair",
        "mobile_number": "9276051834",
        "pan": "VFRTG0126J",
        "aadhaar": "2345-6789-0126",
        "email": "aditi.nair@email.com",
        "age": 29,
        "city": "Kochi",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 710,
            "annual_income": 636000,
            "monthly_income": 53000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 5,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 200000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C039 - Rohit Kapoor
    "9827451630": {
        "name": "Rohit Kapoor",
        "mobile_number": "9827451630",
        "pan": "GBNHY1236K",
        "aadhaar": "3456-7891-1236",
        "email": "rohit.kapoor@email.com",
        "age": 33,
        "city": "Mumbai",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 830,
            "annual_income": 1080000,
            "monthly_income": 90000,
            "employment_type": "Salaried",
            "company": "JP Morgan",
            "work_experience_years": 9,
            "existing_loans": [{"type": "Car Loan", "emi": 15000, "outstanding": 350000}],
            "total_monthly_debt": 15000,
            "debt_to_income_ratio": 0.167,
            "bank_balance": 600000,
            "preapproved_limit": 550000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C040 - Sonal Patil
    "9138562074": {
        "name": "Sonal Patil",
        "mobile_number": "9138562074",
        "pan": "HNJMU2347L",
        "aadhaar": "4567-8912-2347",
        "email": "sonal.patil@email.com",
        "age": 28,
        "city": "Nashik",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 750,
            "annual_income": 780000,
            "monthly_income": 65000,
            "employment_type": "Salaried",
            "company": "L&T Infotech",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Two Wheeler Loan", "emi": 9000, "outstanding": 80000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.138,
            "bank_balance": 300000,
            "preapproved_limit": 320000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C041 - Deepak Yadav
    "9193846507": {
        "name": "Deepak Yadav",
        "mobile_number": "9193846507",
        "pan": "UJMKI3458M",
        "aadhaar": "5678-9123-3458",
        "email": "deepak.yadav@email.com",
        "age": 35,
        "city": "Gurgaon",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 810,
            "annual_income": 984000,
            "monthly_income": 82000,
            "employment_type": "Salaried",
            "company": "Google",
            "work_experience_years": 10,
            "existing_loans": [{"type": "Home Loan", "emi": 13000, "outstanding": 500000}],
            "total_monthly_debt": 13000,
            "debt_to_income_ratio": 0.159,
            "bank_balance": 520000,
            "preapproved_limit": 450000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C042 - Priya Nair
    "9276408519": {
        "name": "Priya Nair",
        "mobile_number": "9276408519",
        "pan": "IKLOP4569N",
        "aadhaar": "6789-1234-4569",
        "email": "priya.nair@email.com",
        "age": 31,
        "city": "Trivandrum",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 720,
            "annual_income": 672000,
            "monthly_income": 56000,
            "employment_type": "Salaried",
            "company": "TCS",
            "work_experience_years": 7,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 220000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C043 - Kunal Shah
    "9051827649": {
        "name": "Kunal Shah",
        "mobile_number": "9051827649",
        "pan": "OLPKM5670P",
        "aadhaar": "7891-2345-5670",
        "email": "kunal.shah@email.com",
        "age": 34,
        "city": "Ahmedabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 840,
            "annual_income": 1176000,
            "monthly_income": 98000,
            "employment_type": "Salaried",
            "company": "Cred",
            "work_experience_years": 9,
            "existing_loans": [{"type": "Home Loan", "emi": 18000, "outstanding": 700000}],
            "total_monthly_debt": 18000,
            "debt_to_income_ratio": 0.184,
            "bank_balance": 700000,
            "preapproved_limit": 600000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C044 - Bhavana Desai
    "9875162038": {
        "name": "Bhavana Desai",
        "mobile_number": "9875162038",
        "pan": "PKMLO6781Q",
        "aadhaar": "8912-3456-6781",
        "email": "bhavana.desai@email.com",
        "age": 29,
        "city": "Surat",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 770,
            "annual_income": 828000,
            "monthly_income": 69000,
            "employment_type": "Salaried",
            "company": "Tata Consultancy",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Car Loan", "emi": 10000, "outstanding": 230000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.145,
            "bank_balance": 350000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C045 - Amit Mishra
    "9146283750": {
        "name": "Amit Mishra",
        "mobile_number": "9146283750",
        "pan": "LPOKI7892R",
        "aadhaar": "9123-4567-7892",
        "email": "amit.mishra@email.com",
        "age": 38,
        "city": "Bhopal",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 730,
            "annual_income": 744000,
            "monthly_income": 62000,
            "employment_type": "Salaried",
            "company": "Coal India",
            "work_experience_years": 13,
            "existing_loans": [{"type": "Home Loan", "emi": 8000, "outstanding": 280000}],
            "total_monthly_debt": 8000,
            "debt_to_income_ratio": 0.129,
            "bank_balance": 280000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "NEAR_PRIME",
        },
        "application_history": [],
    },
    # C046 - Shalini Gupta
    "9061738452": {
        "name": "Shalini Gupta",
        "mobile_number": "9061738452",
        "pan": "MKOIJ9016S",
        "aadhaar": "1234-5678-9016",
        "email": "shalini.gupta@email.com",
        "age": 27,
        "city": "Jaipur",
        "existing_customer": False,
        "financial_data": {
            "credit_score": 690,
            "annual_income": 576000,
            "monthly_income": 48000,
            "employment_type": "Salaried",
            "company": "Infosys BPM",
            "work_experience_years": 4,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 150000,
            "preapproved_limit": 0,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUB_PRIME",
        },
        "application_history": [],
    },
    # C047 - Naveen Kumar
    "9845176309": {
        "name": "Naveen Kumar",
        "mobile_number": "9845176309",
        "pan": "NHYGT0127T",
        "aadhaar": "2345-6789-0127",
        "email": "naveen.kumar@email.com",
        "age": 36,
        "city": "Bangalore",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 820,
            "annual_income": 1056000,
            "monthly_income": 88000,
            "employment_type": "Salaried",
            "company": "SAP Labs",
            "work_experience_years": 11,
            "existing_loans": [{"type": "Home Loan", "emi": 15000, "outstanding": 580000}],
            "total_monthly_debt": 15000,
            "debt_to_income_ratio": 0.17,
            "bank_balance": 550000,
            "preapproved_limit": 500000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [],
    },
    # C048 - Pooja Reddy
    "9847310562": {
        "name": "Pooja Reddy",
        "mobile_number": "9847310562",
        "pan": "RFVDE1237V",
        "aadhaar": "3456-7891-1237",
        "email": "pooja.reddy@email.com",
        "age": 30,
        "city": "Hyderabad",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 760,
            "annual_income": 840000,
            "monthly_income": 70000,
            "employment_type": "Salaried",
            "company": "Qualcomm",
            "work_experience_years": 6,
            "existing_loans": [{"type": "Personal Loan", "emi": 10000, "outstanding": 130000}],
            "total_monthly_debt": 10000,
            "debt_to_income_ratio": 0.143,
            "bank_balance": 350000,
            "preapproved_limit": 350000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C049 - Varun Singh
    "9197465038": {
        "name": "Varun Singh",
        "mobile_number": "9197465038",
        "pan": "WSXED2348W",
        "aadhaar": "4567-8912-2348",
        "email": "varun.singh@email.com",
        "age": 33,
        "city": "Chandigarh",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 790,
            "annual_income": 888000,
            "monthly_income": 74000,
            "employment_type": "Salaried",
            "company": "Infosys",
            "work_experience_years": 8,
            "existing_loans": [{"type": "Car Loan", "emi": 11000, "outstanding": 260000}],
            "total_monthly_debt": 11000,
            "debt_to_income_ratio": 0.149,
            "bank_balance": 400000,
            "preapproved_limit": 400000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
    # C050 - Anjali Sharma
    "9817563402": {
        "name": "Anjali Sharma",
        "mobile_number": "9817563402",
        "pan": "QAZWS3459X",
        "aadhaar": "5678-9123-3459",
        "email": "anjali.sharma@email.com",
        "age": 29,
        "city": "Delhi",
        "existing_customer": True,
        "financial_data": {
            "credit_score": 750,
            "annual_income": 780000,
            "monthly_income": 65000,
            "employment_type": "Salaried",
            "company": "Wipro",
            "work_experience_years": 5,
            "existing_loans": [{"type": "Personal Loan", "emi": 9000, "outstanding": 110000}],
            "total_monthly_debt": 9000,
            "debt_to_income_ratio": 0.138,
            "bank_balance": 300000,
            "preapproved_limit": 300000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [],
    },
}


# ==================== MOCK DATA PROVIDER ====================
class MockDataProvider:
    """
    Simulates external data sources that would exist in a real NBFC system.
    Provides consistent, reproducible data for testing and demonstration.
    
    PRIMARY IDENTIFIER: mobile_number
    ---------------------------------
    All lookups use mobile_number as the primary key because:
    1. It's the unique identifier in Indian banking (linked to Aadhaar/KYC)
    2. OTP verification requires mobile_number
    3. All backend services use mobile_number for customer lookup
    
    OTP GATING REQUIREMENT:
    -----------------------
    CRM lookup should ONLY be called AFTER OTP verification.
    This is enforced by the stage router, not by this class.
    """

    @staticmethod
    def get_customer_by_mobile(mobile_number: str) -> Optional[Dict[str, Any]]:
        """
        Look up customer by mobile number.
        
        This is the PRIMARY lookup method used by all backend services.
        
        Args:
            mobile_number: 10-digit Indian mobile number
            
        Returns:
            Customer profile dict or None if not found
            
        IMPORTANT: This should only be called AFTER OTP verification.
        The stage router enforces this gate.
        """
        # Clean the mobile number (remove any formatting)
        clean_mobile = "".join(filter(str.isdigit, mobile_number))
        return CUSTOMER_PROFILES.get(clean_mobile)
    
    # DEPRECATED: Use get_customer_by_mobile instead
    @staticmethod
    def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: Use get_customer_by_mobile() instead.
        Kept for backward compatibility during migration.
        """
        return MockDataProvider.get_customer_by_mobile(phone)

    @staticmethod
    def get_customer_by_pan(pan: str) -> Optional[Dict[str, Any]]:
        """Look up customer by PAN number"""
        clean_pan = pan.upper().strip()
        for profile in CUSTOMER_PROFILES.values():
            if profile.get("pan") == clean_pan:
                return profile
        return None

    @staticmethod
    def verify_customer(mobile_number: str, pan: str) -> Dict[str, Any]:
        """
        Verify customer identity by matching mobile_number and PAN.
        
        IMPORTANT: This should only be called AFTER OTP verification.
        The mobile_number has been verified via OTP before this lookup.
        
        Args:
            mobile_number: OTP-verified 10-digit mobile number
            pan: Customer's PAN number (optional cross-check)
            
        Returns:
            Dict with verification status and profile if found
        """
        mobile_profile = MockDataProvider.get_customer_by_mobile(mobile_number)
        pan_profile = MockDataProvider.get_customer_by_pan(pan)

        if not mobile_profile and not pan_profile:
            return {
                "verified": False,
                "status": "NOT_FOUND",
                "message": "No customer record found",
                "profile": None,
            }

        if mobile_profile and pan_profile:
            if mobile_profile == pan_profile:
                return {
                    "verified": True,
                    "status": "VERIFIED",
                    "message": "Customer identity verified",
                    "profile": mobile_profile,
                }
            else:
                return {
                    "verified": False,
                    "status": "MISMATCH",
                    "message": "Mobile number and PAN do not match our records",
                    "profile": None,
                    "risk_flag": "IDENTITY_MISMATCH",
                }

        # Partial match - only one identifier found
        return {
            "verified": False,
            "status": "PARTIAL_MATCH",
            "message": "Incomplete information - please provide both mobile number and PAN",
            "profile": mobile_profile or pan_profile,
        }

    @staticmethod
    def create_lead(name: str, mobile_number: str, pan: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new lead for unknown customers.
        
        Args:
            name: Customer's name
            mobile_number: OTP-verified mobile number
            pan: Optional PAN number
            
        Returns:
            Dict with new lead information
        """
        return {
            "lead_id": f"LEAD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "mobile_number": mobile_number,
            "pan": pan,
            "status": "NEW_LEAD",
            "created_at": datetime.now().isoformat(),
            "message": "New lead created - will require document verification",
        }

    @staticmethod
    def get_all_customers() -> Dict[str, Dict[str, Any]]:
        """Return all customer profiles (for admin purposes)"""
        return CUSTOMER_PROFILES

    @staticmethod
    def _levenshtein_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein edit distance between two strings"""
        if len(s1) < len(s2):
            return MockDataProvider._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]

    @staticmethod
    def _similarity_score(s1: str, s2: str) -> float:
        """
        Calculate similarity score between two strings (0 to 1).
        Handles: case differences, minor typos, extra spaces.
        """
        # Normalize: lowercase, strip, collapse multiple spaces
        s1 = ' '.join(s1.lower().split())
        s2 = ' '.join(s2.lower().split())
        
        if s1 == s2:
            return 1.0
        
        if not s1 or not s2:
            return 0.0
        
        # Calculate Levenshtein-based similarity
        max_len = max(len(s1), len(s2))
        distance = MockDataProvider._levenshtein_distance(s1, s2)
        similarity = 1 - (distance / max_len)
        
        return similarity

    @staticmethod
    def fuzzy_match_by_name(name: str, threshold: float = 0.7) -> Dict[str, Any]:
        """
        Find customer by fuzzy name matching.
        Handles: case differences, minor typos (1-2 chars), extra spaces.
        Returns match info with safety checks for duplicate names.
        
        NOTE: This should only be used as a fallback lookup method.
        Primary lookup should always be via mobile_number after OTP verification.
        
        Args:
            name: The name to search for
            threshold: Minimum similarity score (0-1) to consider a match (0.7 = ~2 typos allowed)
            
        Returns:
            Dict with: matches (list), unique (bool), customer (profile or None)
        """
        if not name or len(name.strip()) < 2:
            return {"matches": [], "unique": False, "customer": None}
        
        name_normalized = ' '.join(name.lower().split())
        matches = []
        
        for mobile_number, profile in CUSTOMER_PROFILES.items():
            profile_name = profile.get("name", "")
            profile_name_normalized = ' '.join(profile_name.lower().split())
            
            # Calculate overall similarity
            full_score = MockDataProvider._similarity_score(name_normalized, profile_name_normalized)
            
            # Also check if input matches first name or last name specifically
            name_parts = profile_name_normalized.split()
            partial_scores = [MockDataProvider._similarity_score(name_normalized, part) for part in name_parts]
            best_partial = max(partial_scores) if partial_scores else 0
            
            # Use the better of full match or partial match (for "Priya" matching "Priya Sharma")
            score = max(full_score, best_partial * 0.95)  # Slight penalty for partial match
            
            if score >= threshold:
                matches.append({
                    "profile": profile,
                    "score": score,
                    "name": profile_name,
                    "match_type": "full" if full_score >= threshold else "partial"
                })
        
        # Sort by score descending
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # Return result with safety info
        if len(matches) == 1:
            return {
                "matches": matches,
                "unique": True,
                "customer": matches[0]["profile"]
            }
        elif len(matches) > 1:
            # Check if top match is significantly better than second
            if matches[0]["score"] - matches[1]["score"] > 0.2:
                # Clear winner - safe to use
                return {
                    "matches": matches,
                    "unique": True,
                    "customer": matches[0]["profile"],
                    "note": "Clear best match"
                }
            # Multiple close matches - not safe to auto-select
            return {
                "matches": matches,
                "unique": False,
                "customer": None,
                "names_found": [m["name"] for m in matches]
            }
        else:
            return {"matches": [], "unique": False, "customer": None}


# Helper function for quick testing
def demo_lookup():
    """Demo function to test the mock data provider"""
    print("=== TataSmartAgent Mock Data Demo ===\n")

    # Test 1: Prime Customer (Priya Sharma)
    print("1. Testing Prime Customer (Priya Sharma) by mobile_number:")
    result = MockDataProvider.verify_customer("9815467328", "BTXPS2345K")
    print(f"   Status: {result['status']}")
    if result['profile']:
        print(f"   Credit Score: {result['profile']['financial_data']['credit_score']}")
        print(f"   Risk Category: {result['profile']['behavioral_flags']['risk_category']}\n")

    # Test 2: Sub-Prime Customer (Amit Verma)
    print("2. Testing Sub-Prime Customer (Amit Verma):")
    result = MockDataProvider.verify_customer("9890347612", "CPRTV3456Z")
    print(f"   Status: {result['status']}")
    if result['profile']:
        print(f"   Credit Score: {result['profile']['financial_data']['credit_score']}")
        print(f"   Risk Category: {result['profile']['behavioral_flags']['risk_category']}\n")

    # Test 3: Unknown Customer
    print("3. Testing Unknown Customer:")
    result = MockDataProvider.verify_customer("9999999999", "UNKNOWN123")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}\n")

    # Test 4: All Customers Summary
    print("4. All Customers Summary (keyed by mobile_number):")
    for mobile_number, profile in CUSTOMER_PROFILES.items():
        print(f"   {profile['name']}: {mobile_number} | Score: {profile['financial_data']['credit_score']} | {profile['behavioral_flags']['risk_category']}")


if __name__ == "__main__":
    demo_lookup()
