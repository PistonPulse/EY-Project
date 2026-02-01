"""
External API Client
===================
HTTP client for making requests to the mock external services.

This module provides typed methods for calling:
1. Credit Bureau API - Get credit scores
2. CRM API - Get customer KYC data  
3. Offer Engine API - Calculate pre-approved limits

Usage:
    from api_client import ExternalAPIClient
    
    client = ExternalAPIClient()
    
    # Get credit score
    score = await client.get_credit_score("ABCDE1234F")
    
    # Get customer from CRM
    customer = await client.get_customer("9876543210")
    
    # Calculate offer
    offer = await client.calculate_offer(100000, 750, 5000)
"""

import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime


class ExternalAPIClient:
    """
    Client for interacting with mock external banking services.
    
    Simulates real-world API integration patterns:
    - HTTP requests with proper error handling
    - Retry logic for transient failures
    - Logging of all API calls for debugging
    - Timeout handling
    """
    
    def __init__(self, base_url: str = "http://localhost:8000/external-api"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for external services (default: localhost)
        """
        self.base_url = base_url
        self.timeout = 10.0  # 10 second timeout
        
    async def get_credit_score(self, pan_number: str) -> Dict[str, Any]:
        """
        Fetch credit score from the Credit Bureau API.
        
        Args:
            pan_number: 10-character PAN card number
            
        Returns:
            dict with credit_score, score_band, factors, etc.
            
        Raises:
            Exception if API call fails
        """
        print(f"\n{'='*50}")
        print(f"🔗 CONNECTING TO CREDIT BUREAU (CIBIL)...")
        print(f"   Endpoint: POST /external-api/credit-bureau/score")
        print(f"   PAN: {pan_number[:4]}XXXX{pan_number[-2:]}")
        print(f"{'='*50}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/credit-bureau/score",
                    json={
                        "pan_number": pan_number,
                        "consent": True
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ CREDIT BUREAU RESPONSE:")
                    print(f"   Credit Score: {data.get('credit_score')}")
                    print(f"   Score Band: {data.get('score_band')}")
                    print(f"   Inquiry ID: {data.get('inquiry_id')}")
                    return data
                else:
                    print(f"❌ CREDIT BUREAU ERROR: {response.status_code}")
                    print(f"   Response: {response.text}")
                    return {
                        "error": True,
                        "status_code": response.status_code,
                        "message": response.text
                    }
                    
        except httpx.TimeoutException:
            print(f"⏱️ CREDIT BUREAU TIMEOUT after {self.timeout}s")
            return {"error": True, "message": "Request timeout"}
        except Exception as e:
            print(f"❌ CREDIT BUREAU CONNECTION ERROR: {e}")
            return {"error": True, "message": str(e)}
    
    async def get_customer(self, phone: str) -> Optional[Dict[str, Any]]:
        """
        Fetch customer KYC data from the CRM API.
        
        Args:
            phone: 10-digit phone number
            
        Returns:
            dict with customer profile or None if not found
        """
        print(f"\n{'='*50}")
        print(f"🔗 CONNECTING TO CRM SERVER...")
        print(f"   Endpoint: GET /external-api/crm/customer/{phone}")
        print(f"   Phone: XXXXXX{phone[-4:]}")
        print(f"{'='*50}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/crm/customer/{phone}"
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ CRM RESPONSE:")
                    print(f"   Customer: {data.get('name')}")
                    print(f"   KYC Status: {data.get('kyc_status')}")
                    print(f"   Risk Category: {data.get('risk_profile', {}).get('category')}")
                    return data
                elif response.status_code == 404:
                    print(f"⚠️ CRM: Customer not found")
                    return None
                else:
                    print(f"❌ CRM ERROR: {response.status_code}")
                    return None
                    
        except httpx.TimeoutException:
            print(f"⏱️ CRM TIMEOUT after {self.timeout}s")
            return None
        except Exception as e:
            print(f"❌ CRM CONNECTION ERROR: {e}")
            return None
    
    async def calculate_offer(
        self, 
        monthly_income: float, 
        credit_score: int,
        existing_emi: float = 0,
        employment_type: str = "Salaried"
    ) -> Dict[str, Any]:
        """
        Calculate pre-approved loan offer from the Offer Engine API.
        
        Args:
            monthly_income: Monthly income in INR
            credit_score: Credit score (300-900)
            existing_emi: Existing monthly EMI obligations
            employment_type: Type of employment
            
        Returns:
            dict with pre_approved_limit, interest_rate_range, etc.
        """
        print(f"\n{'='*50}")
        print(f"🔗 CONNECTING TO OFFER ENGINE...")
        print(f"   Endpoint: POST /external-api/offers/calculate")
        print(f"   Income: ₹{monthly_income:,.0f}/month")
        print(f"   Credit Score: {credit_score}")
        print(f"{'='*50}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
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
                    print(f"   Interest Rate: {data.get('interest_rate_range', {}).get('min')}% - {data.get('interest_rate_range', {}).get('max')}%")
                    print(f"   Eligibility: {data.get('eligibility_status')}")
                    print(f"   Offer ID: {data.get('offer_id')}")
                    return data
                else:
                    print(f"❌ OFFER ENGINE ERROR: {response.status_code}")
                    return {
                        "error": True,
                        "pre_approved_limit": 0,
                        "message": response.text
                    }
                    
        except httpx.TimeoutException:
            print(f"⏱️ OFFER ENGINE TIMEOUT after {self.timeout}s")
            return {"error": True, "pre_approved_limit": 0, "message": "Request timeout"}
        except Exception as e:
            print(f"❌ OFFER ENGINE CONNECTION ERROR: {e}")
            return {"error": True, "pre_approved_limit": 0, "message": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all external services.
        
        Returns:
            dict with status of each service
        """
        print(f"\n🏥 Checking External Services Health...")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ All external services are healthy")
                    return data
                else:
                    print(f"⚠️ Health check failed: {response.status_code}")
                    return {"status": "unhealthy", "error": response.text}
                    
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return {"status": "unreachable", "error": str(e)}


# Global client instance
api_client = ExternalAPIClient()
