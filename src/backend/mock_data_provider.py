"""
Mock Data Provider for Tata Capital Demo
Contains 10 profiles covering all demo scenarios
"""

from typing import Dict, Optional
from datetime import datetime, timedelta

class MockDataProvider:
    def __init__(self):
        self.customers = {
            # 1. PRIME Customer - Instant Approval
            "9876543210": {
                "name": "Priya Sharma",
                "phone": "9876543210",
                "pan": "ABCDE1234F",
                "email": "priya.sharma@email.com",
                "age": 32,
                "employment_type": "Salaried",
                "employer": "Tata Consultancy Services",
                "monthly_income": 125000,
                "credit_score": 785,
                "existing_loans": 1,
                "total_debt": 350000,
                "loan_history": "Excellent",
                "address": "Mumbai, Maharashtra",
                "kyc_status": "Verified",
                "risk_category": "PRIME",
                "fraud_flags": [],
                "behavioral_score": 95,
                "max_eligible_amount": 2000000,
                "interest_rate": 10.5,
                "tenure_months": 60,
                "approval_probability": 98
            },
            
            # 2. FRAUD - Fake PAN, Hard Reject
            "9988776655": {
                "name": "Rajesh Kumar",
                "phone": "9988776655",
                "pan": "ZZZZZ9999Z",
                "email": "rajesh.kumar@email.com",
                "age": 28,
                "employment_type": "Salaried",
                "employer": "Unknown Pvt Ltd",
                "monthly_income": 45000,
                "credit_score": None,  # PAN doesn't exist
                "existing_loans": 0,
                "total_debt": 0,
                "loan_history": "No History",
                "address": "Delhi",
                "kyc_status": "Failed",
                "risk_category": "FRAUD",
                "fraud_flags": ["INVALID_PAN", "SUSPICIOUS_PROFILE", "POTENTIAL_IDENTITY_THEFT"],
                "behavioral_score": 15,
                "max_eligible_amount": 0,
                "interest_rate": None,
                "tenure_months": 0,
                "approval_probability": 0
            },
            
            # 3. HIGH RISK - Yellow Flag, Conditional Offer
            "9123456789": {
                "name": "Amit Patel",
                "phone": "9123456789",
                "pan": "CDEFG5678H",
                "email": "amit.patel@email.com",
                "age": 35,
                "employment_type": "Salaried",
                "employer": "Small IT Firm",
                "monthly_income": 55000,
                "credit_score": 640,
                "existing_loans": 3,
                "total_debt": 850000,
                "loan_history": "Average - 2 Late Payments",
                "address": "Ahmedabad, Gujarat",
                "kyc_status": "Verified",
                "risk_category": "HIGH_RISK",
                "fraud_flags": ["HIGH_DEBT_TO_INCOME", "RECENT_CREDIT_INQUIRIES"],
                "behavioral_score": 62,
                "max_eligible_amount": 300000,
                "interest_rate": 14.5,
                "tenure_months": 36,
                "approval_probability": 65,
                "requires_documents": ["salary_slip", "bank_statement"]
            },
            
            # 4. THIN FILE - Standard Approval
            "9000011111": {
                "name": "Ananya Desai",
                "phone": "9000011111",
                "pan": "FGHIJ1234K",
                "email": "ananya.desai@email.com",
                "age": 26,
                "employment_type": "Salaried",
                "employer": "Infosys Limited",
                "monthly_income": 65000,
                "credit_score": 710,
                "existing_loans": 1,
                "total_debt": 120000,
                "loan_history": "Limited - Only Credit Card",
                "address": "Bangalore, Karnataka",
                "kyc_status": "Verified",
                "risk_category": "THIN_FILE",
                "fraud_flags": [],
                "behavioral_score": 78,
                "max_eligible_amount": 500000,
                "interest_rate": 12.5,
                "tenure_months": 48,
                "approval_probability": 82
            },
            
            # 5. HIGH DEBT - Reduced Amount
            "9898989898": {
                "name": "Vikram Malhotra",
                "phone": "9898989898",
                "pan": "JKLMN5678O",
                "email": "vikram.malhotra@email.com",
                "age": 40,
                "employment_type": "Salaried",
                "employer": "HDFC Bank",
                "monthly_income": 95000,
                "credit_score": 680,
                "existing_loans": 4,
                "total_debt": 1500000,
                "loan_history": "Good - High Utilization",
                "address": "Pune, Maharashtra",
                "kyc_status": "Verified",
                "risk_category": "HIGH_DEBT",
                "fraud_flags": ["HIGH_EMI_BURDEN"],
                "behavioral_score": 70,
                "max_eligible_amount": 250000,
                "interest_rate": 13.5,
                "tenure_months": 36,
                "approval_probability": 70
            },
            
            # 6. GIG WORKER - High Interest Rate
            "7777766666": {
                "name": "Rahul Verma",
                "phone": "7777766666",
                "pan": "MNOPQ9012R",
                "email": "rahul.verma@email.com",
                "age": 30,
                "employment_type": "Self-Employed",
                "employer": "Freelance Consultant",
                "monthly_income": 75000,
                "credit_score": 695,
                "existing_loans": 2,
                "total_debt": 300000,
                "loan_history": "Good - Variable Income",
                "address": "Gurgaon, Haryana",
                "kyc_status": "Verified",
                "risk_category": "GIG_WORKER",
                "fraud_flags": ["INCOME_VOLATILITY"],
                "behavioral_score": 72,
                "max_eligible_amount": 600000,
                "interest_rate": 15.5,
                "tenure_months": 48,
                "approval_probability": 68
            },
            
            # 7. MISMATCH - Manual Review Required
            "8888811111": {
                "name": "Sneha Reddy",
                "phone": "8888811111",
                "pan": "PQRST3456U",
                "email": "sneha.reddy@email.com",
                "age": 29,
                "employment_type": "Salaried",
                "employer": "Tech Startup",
                "monthly_income": 70000,
                "credit_score": 720,
                "existing_loans": 2,
                "total_debt": 400000,
                "loan_history": "Good",
                "address": "Hyderabad, Telangana",
                "kyc_status": "Pending",
                "risk_category": "MISMATCH",
                "fraud_flags": ["ADDRESS_MISMATCH", "EMPLOYMENT_VERIFICATION_PENDING"],
                "behavioral_score": 75,
                "max_eligible_amount": 0,
                "interest_rate": None,
                "tenure_months": 0,
                "approval_probability": 50,
                "requires_manual_review": True
            },
            
            # 8. RETIRED - Prime Approval
            "9988776644": {
                "name": "Col. Nair",
                "phone": "9988776644",
                "pan": "STUVW6789X",
                "email": "col.nair@email.com",
                "age": 62,
                "employment_type": "Retired",
                "employer": "Indian Army (Retired)",
                "monthly_income": 85000,  # Pension
                "credit_score": 800,
                "existing_loans": 0,
                "total_debt": 0,
                "loan_history": "Excellent - 30 Years",
                "address": "Kochi, Kerala",
                "kyc_status": "Verified",
                "risk_category": "PRIME",
                "fraud_flags": [],
                "behavioral_score": 98,
                "max_eligible_amount": 1000000,
                "interest_rate": 10.0,
                "tenure_months": 36,
                "approval_probability": 99
            },
            
            # 9. BLACKLIST - Policy Reject
            "6666655555": {
                "name": "Karan Mehra",
                "phone": "6666655555",
                "pan": "VWXYZ0123A",
                "email": "karan.mehra@email.com",
                "age": 33,
                "employment_type": "Salaried",
                "employer": "ABC Corporation",
                "monthly_income": 60000,
                "credit_score": 520,
                "existing_loans": 5,
                "total_debt": 2000000,
                "loan_history": "Poor - Multiple Defaults",
                "address": "Noida, UP",
                "kyc_status": "Verified",
                "risk_category": "BLACKLIST",
                "fraud_flags": ["WRITEOFF_HISTORY", "LEGAL_PROCEEDINGS", "NPA_ACCOUNT"],
                "behavioral_score": 25,
                "max_eligible_amount": 0,
                "interest_rate": None,
                "tenure_months": 0,
                "approval_probability": 0
            },
            
            # 10. HNI - Pre-Approved High Value
            "9119119111": {
                "name": "Dr. Aditi",
                "phone": "9119119111",
                "pan": "BCDEF4567G",
                "email": "dr.aditi@email.com",
                "age": 38,
                "employment_type": "Self-Employed",
                "employer": "Senior Cardiologist",
                "monthly_income": 450000,
                "credit_score": 820,
                "existing_loans": 1,
                "total_debt": 500000,  # Home Loan
                "loan_history": "Excellent",
                "address": "South Delhi, Delhi",
                "kyc_status": "Verified",
                "risk_category": "HNI",
                "fraud_flags": [],
                "behavioral_score": 99,
                "max_eligible_amount": 1500000,
                "interest_rate": 9.5,
                "tenure_months": 60,
                "approval_probability": 99,
                "pre_approved": True
            }
        }
    
    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Retrieve customer profile by phone number"""
        return self.customers.get(phone)
    
    def get_customer_by_pan(self, pan: str) -> Optional[Dict]:
        """Retrieve customer profile by PAN"""
        for customer in self.customers.values():
            if customer["pan"] == pan:
                return customer
        return None
    
    def verify_pan(self, pan: str) -> Dict:
        """Simulate PAN verification with NSDL"""
        customer = self.get_customer_by_pan(pan)
        if not customer:
            return {
                "status": "INVALID",
                "message": "PAN not found in records",
                "verified": False
            }
        
        if customer["risk_category"] == "FRAUD":
            return {
                "status": "INVALID",
                "message": "Invalid PAN - Potential fraud detected",
                "verified": False
            }
        
        return {
            "status": "VALID",
            "message": f"PAN verified for {customer['name']}",
            "verified": True,
            "name": customer["name"]
        }
    
    def get_credit_score(self, pan: str) -> Optional[int]:
        """Simulate credit bureau check"""
        customer = self.get_customer_by_pan(pan)
        return customer["credit_score"] if customer else None
    
    def calculate_risk_score(self, phone: str) -> Dict:
        """Calculate comprehensive risk score"""
        customer = self.get_customer_by_phone(phone)
        if not customer:
            return {"risk_score": 0, "category": "UNKNOWN"}
        
        risk_factors = {
            "credit_score_weight": 0.3,
            "debt_to_income_weight": 0.25,
            "loan_history_weight": 0.2,
            "behavioral_weight": 0.15,
            "fraud_flags_weight": 0.1
        }
        
        # Calculate normalized risk score (0-100)
        credit_component = (customer["credit_score"] or 0) / 850 * 100 * risk_factors["credit_score_weight"]
        
        dti_ratio = customer["total_debt"] / (customer["monthly_income"] * 12) if customer["monthly_income"] > 0 else 1
        dti_component = max(0, (1 - dti_ratio) * 100) * risk_factors["debt_to_income_weight"]
        
        behavioral_component = customer["behavioral_score"] * risk_factors["behavioral_weight"]
        
        fraud_penalty = len(customer["fraud_flags"]) * 15
        
        total_risk_score = credit_component + dti_component + behavioral_component - fraud_penalty
        total_risk_score = max(0, min(100, total_risk_score))
        
        return {
            "risk_score": round(total_risk_score, 2),
            "category": customer["risk_category"],
            "fraud_flags": customer["fraud_flags"],
            "approval_probability": customer["approval_probability"]
        }

# Global instance
mock_data = MockDataProvider()
