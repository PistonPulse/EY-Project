"""
Mock Data Provider for TataSmartAgent v3.0
Contains 10 diverse customer profiles for testing the agentic workflow
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

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


# Mock Customer Database
CUSTOMER_PROFILES: Dict[str, Dict[str, Any]] = {
    "9876543210": {
        "name": "Priya Sharma",
        "phone": "9876543210",
        "pan": "ABCDE1234F",
        "email": "priya.sharma@email.com",
        "financial_data": {
            "credit_score": 780,
            "annual_income": 1200000,  # 12 LPA
            "monthly_income": 100000,
            "employment_type": "Salaried",
            "company": "Tech Mahindra",
            "work_experience_years": 5,
            "existing_loans": [
                {"type": "Credit Card", "emi": 5000, "outstanding": 50000}
            ],
            "total_monthly_debt": 5000,
            "debt_to_income_ratio": 0.05,
            "bank_balance": 250000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [
            {
                "date": "2023-06-15",
                "type": "Personal Loan",
                "amount": 300000,
                "status": "Closed - Fully Paid",
            }
        ],
    },
    "9123456789": {
        "name": "Rajesh Kumar",
        "phone": "9123456789",
        "pan": "FGHIJ5678K",
        "email": "rajesh.kumar@email.com",
        "financial_data": {
            "credit_score": 520,
            "annual_income": 480000,  # 4.8 LPA
            "monthly_income": 40000,
            "employment_type": "Salaried",
            "company": "Local Trading Co.",
            "work_experience_years": 2,
            "existing_loans": [
                {"type": "Personal Loan", "emi": 15000, "outstanding": 200000},
                {"type": "Credit Card", "emi": 8000, "outstanding": 95000},
            ],
            "total_monthly_debt": 23000,
            "debt_to_income_ratio": 0.575,  # 57.5% - Very High
            "bank_balance": 12000,
        },
        "behavioral_flags": {
            "loan_history": "Poor",
            "payment_delays": 12,
            "fraud_alerts": 2,
            "bounced_cheques": 3,
            "risk_category": "HIGH_RISK",
            "notes": "Multiple fraud alerts from previous lenders",
        },
        "application_history": [
            {
                "date": "2024-03-10",
                "type": "Personal Loan",
                "amount": 100000,
                "status": "Rejected - High Risk",
            }
        ],
    },
    "9988776655": {
        "name": "Amit Patel",
        "phone": "9988776655",
        "pan": "KLMNO9012P",
        "email": "amit.patel@email.com",
        "financial_data": {
            "credit_score": 650,
            "annual_income": 720000,  # 7.2 LPA
            "monthly_income": 60000,
            "employment_type": "Salaried",
            "company": "Infosys Ltd",
            "work_experience_years": 3,
            "existing_loans": [
                {"type": "Two Wheeler Loan", "emi": 4500, "outstanding": 45000},
                {"type": "Credit Card", "emi": 3000, "outstanding": 35000},
            ],
            "total_monthly_debt": 7500,
            "debt_to_income_ratio": 0.125,
            "bank_balance": 85000,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 3,
            "fraud_alerts": 0,
            "bounced_cheques": 1,
            "risk_category": "MEDIUM_RISK",
        },
        "application_history": [],
    },
    "9876001122": {
        "name": "Ananya Singh",
        "phone": "9876001122",
        "pan": "QRSTU3456V",
        "email": "ananya.singh@email.com",
        "financial_data": {
            "credit_score": 0,  # Thin file - No credit history
            "annual_income": 600000,  # 6 LPA
            "monthly_income": 50000,
            "employment_type": "Salaried",
            "company": "Wipro",
            "work_experience_years": 1,
            "existing_loans": [],
            "total_monthly_debt": 0,
            "debt_to_income_ratio": 0.0,
            "bank_balance": 120000,
        },
        "behavioral_flags": {
            "loan_history": "No History",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "THIN_FILE",
            "notes": "New to credit, no historical data",
        },
        "application_history": [],
    },
    "9445566778": {
        "name": "Vikram Reddy",
        "phone": "9445566778",
        "pan": "WXYZ7890A",
        "email": "vikram.reddy@email.com",
        "financial_data": {
            "credit_score": 620,
            "annual_income": 1500000,  # 15 LPA
            "monthly_income": 125000,
            "employment_type": "Salaried",
            "company": "Amazon India",
            "work_experience_years": 7,
            "existing_loans": [
                {"type": "Home Loan", "emi": 45000, "outstanding": 3500000},
                {"type": "Car Loan", "emi": 18000, "outstanding": 450000},
                {"type": "Personal Loan", "emi": 12000, "outstanding": 150000},
            ],
            "total_monthly_debt": 75000,
            "debt_to_income_ratio": 0.60,  # 60% - High leverage
            "bank_balance": 180000,
        },
        "behavioral_flags": {
            "loan_history": "Fair",
            "payment_delays": 2,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "HIGH_DEBT",
            "notes": "High debt burden despite good income",
        },
        "application_history": [
            {
                "date": "2022-11-20",
                "type": "Home Loan",
                "amount": 4000000,
                "status": "Active",
            }
        ],
    },
    "9334455667": {
        "name": "Sneha Desai",
        "phone": "9334455667",
        "pan": "BCDEF2345G",
        "email": "sneha.desai@email.com",
        "financial_data": {
            "credit_score": 810,
            "annual_income": 1800000,  # 18 LPA
            "monthly_income": 150000,
            "employment_type": "Salaried",
            "company": "Google India",
            "work_experience_years": 8,
            "existing_loans": [
                {"type": "Credit Card", "emi": 2000, "outstanding": 15000}
            ],
            "total_monthly_debt": 2000,
            "debt_to_income_ratio": 0.013,
            "bank_balance": 850000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "SUPER_PRIME",
        },
        "application_history": [
            {
                "date": "2021-08-10",
                "type": "Car Loan",
                "amount": 800000,
                "status": "Closed - Fully Paid",
            }
        ],
    },
    "9667788990": {
        "name": "Arjun Menon",
        "phone": "9667788990",
        "pan": "HIJKL6789M",
        "email": "arjun.menon@email.com",
        "financial_data": {
            "credit_score": 580,
            "annual_income": 540000,  # 5.4 LPA
            "monthly_income": 45000,
            "employment_type": "Contract",
            "company": "Freelance IT Consultant",
            "work_experience_years": 4,
            "existing_loans": [
                {"type": "Personal Loan", "emi": 9000, "outstanding": 120000},
                {"type": "Credit Card", "emi": 6000, "outstanding": 78000},
            ],
            "total_monthly_debt": 15000,
            "debt_to_income_ratio": 0.333,
            "bank_balance": 25000,
        },
        "behavioral_flags": {
            "loan_history": "Poor",
            "payment_delays": 8,
            "fraud_alerts": 0,
            "bounced_cheques": 2,
            "risk_category": "HIGH_RISK",
            "notes": "Irregular income due to contract work",
        },
        "application_history": [],
    },
    "9112233445": {
        "name": "Kavya Iyer",
        "phone": "9112233445",
        "pan": "NOPQR4567S",
        "email": "kavya.iyer@email.com",
        "financial_data": {
            "credit_score": 720,
            "annual_income": 960000,  # 9.6 LPA
            "monthly_income": 80000,
            "employment_type": "Salaried",
            "company": "HDFC Bank",
            "work_experience_years": 6,
            "existing_loans": [
                {"type": "Education Loan", "emi": 8000, "outstanding": 180000},
                {"type": "Credit Card", "emi": 3000, "outstanding": 25000},
            ],
            "total_monthly_debt": 11000,
            "debt_to_income_ratio": 0.1375,
            "bank_balance": 145000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 1,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "LOW_RISK",
        },
        "application_history": [
            {
                "date": "2020-05-15",
                "type": "Education Loan",
                "amount": 500000,
                "status": "Active",
            }
        ],
    },
    "9998887776": {
        "name": "Rohan Gupta",
        "phone": "9998887776",
        "pan": "TUVWX8901Y",
        "email": "rohan.gupta@email.com",
        "financial_data": {
            "credit_score": 695,
            "annual_income": 840000,  # 8.4 LPA
            "monthly_income": 70000,
            "employment_type": "Salaried",
            "company": "TCS",
            "work_experience_years": 4,
            "existing_loans": [
                {"type": "Car Loan", "emi": 12000, "outstanding": 280000},
                {"type": "Credit Card", "emi": 4000, "outstanding": 45000},
            ],
            "total_monthly_debt": 16000,
            "debt_to_income_ratio": 0.228,
            "bank_balance": 95000,
        },
        "behavioral_flags": {
            "loan_history": "Good",
            "payment_delays": 2,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "MEDIUM_RISK",
        },
        "application_history": [
            {
                "date": "2023-02-20",
                "type": "Car Loan",
                "amount": 500000,
                "status": "Active",
            }
        ],
    },
    "9223344556": {
        "name": "Deepa Nair",
        "phone": "9223344556",
        "pan": "ZABCD1234E",
        "email": "deepa.nair@email.com",
        "financial_data": {
            "credit_score": 760,
            "annual_income": 1080000,  # 10.8 LPA
            "monthly_income": 90000,
            "employment_type": "Salaried",
            "company": "Accenture",
            "work_experience_years": 5,
            "existing_loans": [
                {"type": "Credit Card", "emi": 4500, "outstanding": 48000}
            ],
            "total_monthly_debt": 4500,
            "debt_to_income_ratio": 0.05,
            "bank_balance": 320000,
        },
        "behavioral_flags": {
            "loan_history": "Excellent",
            "payment_delays": 0,
            "fraud_alerts": 0,
            "bounced_cheques": 0,
            "risk_category": "PRIME",
        },
        "application_history": [
            {
                "date": "2022-09-10",
                "type": "Personal Loan",
                "amount": 200000,
                "status": "Closed - Fully Paid",
            }
        ],
    },
}


class MockDataProvider:
    """Provides mock customer data for testing"""

    @staticmethod
    def get_customer_by_phone(phone: str) -> Optional[Dict[str, Any]]:
        """Retrieve customer profile by phone number"""
        # Clean phone number (remove spaces, dashes, etc.)
        clean_phone = "".join(filter(str.isdigit, phone))
        return CUSTOMER_PROFILES.get(clean_phone)

    @staticmethod
    def get_customer_by_pan(pan: str) -> Optional[Dict[str, Any]]:
        """Retrieve customer profile by PAN number"""
        pan_upper = pan.upper().strip()
        for profile in CUSTOMER_PROFILES.values():
            if profile["pan"] == pan_upper:
                return profile
        return None
    
    @staticmethod
    def get_customer_as_dataclass(phone: str) -> Optional[CustomerProfile]:
        """Retrieve customer as typed dataclass for better IDE support"""
        profile_dict = MockDataProvider.get_customer_by_phone(phone)
        if not profile_dict:
            return None
        
        # Convert nested dict to dataclass
        return CustomerProfile(
            id=f"CUST_{phone[-4:]}",
            name=profile_dict["name"],
            phone=profile_dict["phone"],
            pan=profile_dict["pan"],
            email=profile_dict["email"],
            credit_score=profile_dict["financial_data"]["credit_score"],
            monthly_income=profile_dict["financial_data"]["monthly_income"],
            annual_income=profile_dict["financial_data"]["annual_income"],
            total_debt=profile_dict["financial_data"]["total_monthly_debt"],
            debt_to_income_ratio=profile_dict["financial_data"]["debt_to_income_ratio"],
            risk_category=profile_dict["behavioral_flags"]["risk_category"],
            flags=profile_dict["behavioral_flags"].get("notes", "").split(", ") if "notes" in profile_dict["behavioral_flags"] else [],
            employment_type=profile_dict["financial_data"]["employment_type"],
            company=profile_dict["financial_data"]["company"],
            work_experience_years=profile_dict["financial_data"]["work_experience_years"],
            bank_balance=profile_dict["financial_data"]["bank_balance"],
            payment_delays=profile_dict["behavioral_flags"]["payment_delays"],
            fraud_alerts=profile_dict["behavioral_flags"]["fraud_alerts"],
            bounced_cheques=profile_dict["behavioral_flags"]["bounced_cheques"],
            loan_history=profile_dict["behavioral_flags"]["loan_history"]
        )

    @staticmethod
    def verify_customer(phone: str, pan: str) -> Dict[str, Any]:
        """
        Verify customer identity by matching phone and PAN
        Returns verification status and profile if found
        """
        phone_profile = MockDataProvider.get_customer_by_phone(phone)
        pan_profile = MockDataProvider.get_customer_by_pan(pan)

        if not phone_profile and not pan_profile:
            return {
                "verified": False,
                "status": "NOT_FOUND",
                "message": "No customer record found",
                "profile": None,
            }

        if phone_profile and pan_profile:
            if phone_profile == pan_profile:
                return {
                    "verified": True,
                    "status": "VERIFIED",
                    "message": "Customer identity verified",
                    "profile": phone_profile,
                }
            else:
                return {
                    "verified": False,
                    "status": "MISMATCH",
                    "message": "Phone and PAN do not match our records",
                    "profile": None,
                    "risk_flag": "IDENTITY_MISMATCH",
                }

        # Partial match - only one identifier found
        return {
            "verified": False,
            "status": "PARTIAL_MATCH",
            "message": "Incomplete information - please provide both phone and PAN",
            "profile": phone_profile or pan_profile,
        }

    @staticmethod
    def create_lead(name: str, phone: str, pan: Optional[str] = None) -> Dict[str, Any]:
        """Create a new lead for unknown customers"""
        return {
            "lead_id": f"LEAD_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "name": name,
            "phone": phone,
            "pan": pan,
            "status": "NEW_LEAD",
            "created_at": datetime.now().isoformat(),
            "message": "New lead created - will require document verification",
        }

    @staticmethod
    def get_all_customers() -> Dict[str, Dict[str, Any]]:
        """Return all customer profiles (for admin purposes)"""
        return CUSTOMER_PROFILES


# Helper function for quick testing
def demo_lookup():
    """Demo function to test the mock data provider"""
    print("=== TataSmartAgent Mock Data Demo ===\n")

    # Test 1: Prime Customer
    print("1. Testing Prime Customer (Priya):")
    result = MockDataProvider.verify_customer("9876543210", "ABCDE1234F")
    print(f"   Status: {result['status']}")
    print(f"   Credit Score: {result['profile']['financial_data']['credit_score']}")
    print(f"   Risk Category: {result['profile']['behavioral_flags']['risk_category']}\n")

    # Test 2: High Risk Customer
    print("2. Testing High Risk Customer (Rajesh):")
    result = MockDataProvider.verify_customer("9123456789", "FGHIJ5678K")
    print(f"   Status: {result['status']}")
    print(f"   Credit Score: {result['profile']['financial_data']['credit_score']}")
    print(f"   Fraud Alerts: {result['profile']['behavioral_flags']['fraud_alerts']}\n")

    # Test 3: Unknown Customer
    print("3. Testing Unknown Customer:")
    result = MockDataProvider.verify_customer("9999999999", "UNKNOWN123")
    print(f"   Status: {result['status']}")
    print(f"   Message: {result['message']}\n")


if __name__ == "__main__":
    demo_lookup()
