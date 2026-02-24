import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import multiprocessing
import time

# Import the mock data dictionary
from mock_data import CUSTOMER_PROFILES

# ---------------------------------------------------------
# SERVER 1: CRM API (Port 5001)
# Hosts Dummy Customer KYC Data
# ---------------------------------------------------------
crm_app = FastAPI(title="🏦 Mock CRM API (KYC Data)")
crm_app.add_middleware(CORSMiddleware, allow_origins=["*"])

@crm_app.get("/api/crm/customer/{mobile_number}")
async def get_customer_kyc(mobile_number: str):
    user = CUSTOMER_PROFILES.get(mobile_number)
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found in CRM")
    
    # Return ONLY KYC data
    return {
        "status": "success",
        "data": {
            "name": user["name"],
            "mobile_number": user["mobile_number"],
            "pan": user["pan"],
            "aadhaar": user["aadhaar"],
            "age": user["age"],
            "city": user["city"],
            "existing_customer": user["existing_customer"]
        }
    }


# ---------------------------------------------------------
# SERVER 2: Credit Bureau API (Port 5002)
# Hosts Mock Credit Scores
# ---------------------------------------------------------
credit_app = FastAPI(title="📊 Mock Credit Bureau API")
credit_app.add_middleware(CORSMiddleware, allow_origins=["*"])

@credit_app.get("/api/credit/score/{pan}")
async def get_credit_score(pan: str):
    # Find user by PAN
    for mobile, user in CUSTOMER_PROFILES.items():
        if user["pan"].upper() == pan.upper():
            return {
                "status": "success",
                "data": {
                    "pan": pan,
                    "credit_score": user["financial_data"]["credit_score"],
                    "risk_category": user["behavioral_flags"]["risk_category"],
                    "payment_delays": user["behavioral_flags"]["payment_delays"],
                    "fraud_alerts": user["behavioral_flags"]["fraud_alerts"]
                }
            }
    
    raise HTTPException(status_code=404, detail="PAN not found in Credit Bureau")


# ---------------------------------------------------------
# SERVER 3: Offer Mart API (Port 5003)
# Hosts Pre-approved Loan Offers
# ---------------------------------------------------------
offer_app = FastAPI(title="🎁 Mock Offer Mart API")
offer_app.add_middleware(CORSMiddleware, allow_origins=["*"])

@offer_app.get("/api/offers/{mobile_number}")
async def get_offers(mobile_number: str):
    user = CUSTOMER_PROFILES.get(mobile_number)
    if not user:
        raise HTTPException(status_code=404, detail="No offers found for this mobile number")
    
    return {
        "status": "success",
        "data": {
            "preapproved_limit": user["financial_data"]["preapproved_limit"],
            "existing_loans": user["financial_data"]["existing_loans"],
            "bank_balance": user["financial_data"]["bank_balance"],
            "total_monthly_debt": user["financial_data"]["total_monthly_debt"],
            "monthly_income": user["financial_data"]["monthly_income"],
            "annual_income": user["financial_data"]["annual_income"],
            "debt_to_income_ratio": user["financial_data"]["debt_to_income_ratio"]
        }
    }


# ---------------------------------------------------------
# MULTIPROCESSING RUNNER
# ---------------------------------------------------------

def run_crm():
    uvicorn.run(crm_app, host="0.0.0.0", port=5001, log_level="error")

def run_credit():
    uvicorn.run(credit_app, host="0.0.0.0", port=5002, log_level="error")

def run_offer():
    uvicorn.run(offer_app, host="0.0.0.0", port=5003, log_level="error")

if __name__ == "__main__":
    print("="*60)
    print("🚀 STARTING ISOLATED MOCK API SERVERS...")
    print("="*60)
    print("📡 [Server 1] CRM API            --> http://localhost:5001")
    print("📡 [Server 2] Credit Bureau API  --> http://localhost:5002")
    print("📡 [Server 3] Offer Mart API     --> http://localhost:5003")
    print("="*60)
    print("Leave this terminal running in the background for demonstrations.\n")
    
    p1 = multiprocessing.Process(target=run_crm)
    p2 = multiprocessing.Process(target=run_credit)
    p3 = multiprocessing.Process(target=run_offer)
    
    p1.start()
    p2.start()
    p3.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down mock servers...")
        p1.terminate()
        p2.terminate()
        p3.terminate()
        p1.join()
        p2.join()
        p3.join()
        print("✅ Servers stopped.")
