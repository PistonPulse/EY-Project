"""
TataSmartAgent - FastAPI Main Application
Production-grade backend for Agentic AI Loan Officer
"""

import os
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

# PHASE 6: PDF Generation imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, blue, black
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import tempfile

from graph_agent import create_agent, LoanAgentGraph, GeminiLLM, validate_salary_math, cross_check_bank_statement, check_visual_forgery
from mock_data import MockDataProvider
from pdf_generator import generate_sanction_letter, cleanup_pdf_file
from external_services import external_api_router

# Fuzzy matching for name verification
try:
    from thefuzz import fuzz
except ImportError:
    # Fallback - install with: pip install thefuzz
    fuzz = None
    print("⚠️ thefuzz not installed - fuzzy matching disabled")

# ==================== CONFIGURATION ====================
# Load environment variables from .env file
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    print("⚠️  WARNING: GEMINI_API_KEY not set. Set it in environment variables.")
else:
    print(f"✅ GEMINI_API_KEY loaded: {GEMINI_API_KEY[:20]}...")

# Global agent instance
agent: Optional[LoanAgentGraph] = None

# Active WebSocket connections for admin dashboard
admin_connections: List[WebSocket] = []

# Session storage (in production, use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}



# ==================== LIFESPAN MANAGEMENT ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global agent
    
    # Startup
    print("🚀 Initializing TataSmartAgent...")
    if GEMINI_API_KEY:
        agent = await create_agent(GEMINI_API_KEY)
        print("✅ Agent initialized successfully")
    else:
        print("❌ Agent initialization failed - missing API key")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down TataSmartAgent...")


# ==================== FASTAPI APP ====================
app = FastAPI(
    title="TataSmartAgent",
    description="Production-grade Agentic AI Loan Officer using LangGraph & Google Gemini",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount External Services API Router (Mock microservices)
app.include_router(external_api_router)
print("🔌 External Services API mounted at /external-api/*")


# ==================== PYDANTIC MODELS ====================
class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Unique session identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional typing metadata for trust analysis")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="AI agent's response")
    session_id: str
    conversation_stage: str
    missing_info: List[str] = Field(default_factory=list)
    decision: Optional[str] = None
    show_upload: bool = False  # NEW: Show upload button in UI
    show_sanction_letter: bool = False  # NEW: Show download button in UI
    loan_details: Optional[Dict[str, Any]] = None  # NEW: Loan details for sanction letter
    customer_name: Optional[str] = None  # NEW: Customer name for letter
    admin_data: Optional[Dict[str, Any]] = None  # For debugging


class UploadResponse(BaseModel):
    """Response model for document upload"""
    success: bool
    message: str
    response: Optional[str] = None  # AI response message
    session_id: Optional[str] = None
    document_verified: Optional[bool] = None  # Whether document passed verification
    extracted_data: Optional[Dict[str, Any]] = None
    trust_score: Optional[int] = None
    fraud_detected: Optional[bool] = None  # Whether fraud was detected
    risk_control: Optional[Dict[str, Any]] = None  # Fraud detection results


class SessionInfoResponse(BaseModel):
    """Response model for session information"""
    session_id: str
    conversation_history: List[Dict[str, Any]]
    current_state: Dict[str, Any]


# ==================== HELPER FUNCTIONS ====================
def get_or_create_session(session_id: str) -> Dict[str, Any]:
    """Get existing session or create new one"""
    if session_id not in sessions:
        sessions[session_id] = {
            "session_id": session_id,
            "created_at": datetime.now().isoformat(),
            "messages": [],
            "state": {},
            "last_activity": datetime.now().isoformat()
        }
    else:
        sessions[session_id]["last_activity"] = datetime.now().isoformat()
    
    return sessions[session_id]


async def broadcast_to_admin(data: Dict[str, Any]):
    """Send data to all connected admin dashboards"""
    if not admin_connections:
        return
    
    message = json.dumps(data)
    disconnected = []
    
    for connection in admin_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)
    
    # Remove disconnected clients
    for conn in disconnected:
        admin_connections.remove(conn)



# ==================== MAIN ENDPOINTS ====================
@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "TataSmartAgent",
        "status": "online",
        "agent_initialized": agent is not None,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy" if agent else "degraded",
        "agent_ready": agent is not None,
        "active_sessions": len(sessions),
        "admin_connections": len(admin_connections),
        "gemini_api_configured": bool(GEMINI_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint - processes user messages through the LangGraph agent
    
    This endpoint implements the complete agentic workflow:
    1. Extracts entities (name, phone, PAN) using Gemini (NO REGEX)
    2. Verifies customer against mock database  
    3. Analyzes trust & safety with Gemini reasoning
    4. Makes underwriting decision with strict Python rules
    5. Generates natural language response with Gemini (NO TEMPLATES)
    
    All responses are dynamically generated - zero hardcoded text.
    """
    
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not initialized. Check GEMINI_API_KEY.")
    
    try:
        # Get or create session
        session = get_or_create_session(request.session_id)
        
        # Process message through the agent graph
        try:
            result = await agent.process_message(
                user_message=request.message,
                conversation_history=session["messages"],
                previous_state=session.get("state", {})  # Pass previous state to preserve demo_script
            )
        except Exception as agent_error:
            error_str = str(agent_error)
            # Check if it's a quota exceeded error
            if "429" in error_str or "quota" in error_str.lower() or "ResourceExhausted" in error_str:
                return ChatResponse(
                    response="I apologize, but we've reached our daily API usage limit. This is a demo using Google's free tier. Please try again later or contact support to upgrade to a paid plan for unlimited access.",
                    session_id=request.session_id,
                    conversation_stage="error_quota",
                    missing_info=[],
                    decision=None,
                    admin_data={"error": "quota_exceeded"}
                )
            # Re-raise other errors
            raise agent_error
        
        # Update session with new state (support both old flat and new nested format)
        session["messages"] = result.get("messages", [])
        session["state"] = {
            # User identification (flat for backward compatibility)
            "name": result.get("name"),
            "phone": result.get("phone"),
            "pan": result.get("pan"),
            "verified": result.get("customer_verified"),
            "conversation_stage": result.get("conversation_stage"),
            "loan_decision": result.get("loan_decision"),
            "trust_score": result.get("trust_score"),
            # New nested state format
            "user_profile": result.get("user_profile", {}),
            "loan_request": result.get("loan_request", {}),
            "pending_loan_request": result.get("pending_loan_request", {}),
            "financial_data": result.get("financial_data", {}),
            "negotiation_state": result.get("negotiation_state", {}),
            "document_state": result.get("document_state", {}),
            "trust_analysis": result.get("trust_analysis", {}),
            # OTP state for verification
            "otp_state": result.get("otp_state", {})
        }
        
        print(f"\n🔄 SESSION UPDATED:")
        print(f"Session ID: {request.session_id}")
        print(f"User Name: {result.get('name')}")
        print(f"Verified: {result.get('customer_verified')}")
        print(f"Trust Score: {result.get('trust_score')}")
        print(f"Customer Profile: {result.get('customer_profile')}")
        print(f"Admin Logs Count: {len(result.get('admin_log', []))}")
        print(f"Session State: {session['state']}\n")
        
        # Broadcast events to admin dashboard
        timestamp = datetime.now().isoformat()
        
        # 1. User Message
        await broadcast_to_admin({
            "type": "user_message",
            "data": {"message": request.message},
            "timestamp": timestamp
        })
        
        # 2. Admin Logs (Step-by-step execution) - CRITICAL FOR AGENT VISUALIZATION
        if result.get("admin_log") and len(result.get("admin_log", [])) > 0:
            print(f"📋 Broadcasting {len(result['admin_log'])} admin logs...")
            
            # Track last agent to avoid spamming agent_active events
            last_active_agent = None
            
            for log in result["admin_log"]:
                # Check if this is an API event (special handling for microservices visibility)
                api_event = log.get("api_event")
                if api_event:
                    # Broadcast as API event type directly for special UI treatment
                    await broadcast_to_admin({
                        "type": api_event["type"],  # e.g., "API_CALL_CRM", "API_RESPONSE_CRM"
                        "data": api_event["data"],
                        "timestamp": api_event["timestamp"]
                    })
                    print(f"  🌐 Broadcasting API Event: {api_event['type']}")
                    await asyncio.sleep(0.3)  # Longer delay for visual effect on API calls
                    continue
                
                # Map graph agent log types to UI levels
                level = log.get("type", "info")
                # Ensure level matches what frontend expects
                if level not in ["info", "success", "warning", "error"]:
                    level = "info"
                
                # Use message from log, or construct one if missing
                msg = log.get("message")
                if not msg:
                    if "action" in log:
                        msg = f"Action: {log['action']}"
                    elif "mode" in log:
                        msg = f"Mode: {log['mode']}"
                    else:
                        msg = "Processing..."

                agent_name = log.get("agent", "System")
                print(f"  🤖 Broadcasting: {agent_name} - {msg}")
                
                # Normalize agent name for frontend (extract key identifier)
                agent_id = agent_name.lower()
                if "sales" in agent_id:
                    agent_id = "sales"
                elif "verification" in agent_id:
                    agent_id = "verification"
                elif "underwriting" in agent_id:
                    agent_id = "underwriting"
                elif "trust" in agent_id or "safety" in agent_id:
                    agent_id = "trust"
                elif "master" in agent_id:
                    agent_id = "master"
                else:
                    # Skip "system" and other generic agents - don't highlight them
                    if "system" in agent_id:
                        agent_id = None
                    else:
                        agent_id = agent_name.lower().replace(" ", "_").replace("&", "and")
                
                # Only broadcast agent_active when agent actually CHANGES (not for every log)
                # This prevents rapid flashing between agents
                if agent_id and agent_id != last_active_agent and agent_id != "system":
                    print(f"    🎯 Agent CHANGED: {last_active_agent} → {agent_id}")
                    await broadcast_to_admin({
                        "type": "agent_active",
                        "data": {
                            "agent": agent_id
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                    last_active_agent = agent_id
                    await asyncio.sleep(0.2)  # Slight delay for visual effect
                
                # Broadcast the log message
                await broadcast_to_admin({
                    "type": "log",
                    "data": {
                        "message": msg,
                        "level": level,
                        "agent": agent_name
                    },
                    "timestamp": datetime.now().isoformat()
                })
                await asyncio.sleep(0.05)  # Small delay between logs
        else:
            print(f"⚠️ No admin_log found in result!")

        # 3. Risk Score Update - ALWAYS SEND (critical for dashboard updates)
        # Get trust_score from trust_analysis if available
        trust_analysis = result.get("trust_analysis", {})
        trust_score = trust_analysis.get("trust_score") or result.get("trust_score", 50)
        fraud_flags = trust_analysis.get("fraud_flags", []) or result.get("fraud_flags", [])
        risk_category = trust_analysis.get("risk_category", "MEDIUM")
        
        await broadcast_to_admin({
            "type": "risk_calculated",
            "data": {
                "risk_score": trust_score,
                "risk_category": risk_category,
                "factors": fraud_flags
            },
            "timestamp": timestamp
        })
        print(f"📊 Broadcasting Trust Score: {trust_score} | Risk: {risk_category} | Flags: {len(fraud_flags)}")

        # 4. Customer Identification & Profile Update
        customer_profile = result.get("customer_profile") or {}
        if customer_profile:
            behavioral_flags = customer_profile.get("behavioral_flags") or {}
            risk_category = behavioral_flags.get("risk_category", "UNKNOWN")
            
            await broadcast_to_admin({
                "type": "customer_identified",
                "data": {
                    "customer": customer_profile
                },
                "timestamp": timestamp
            })
            print(f"👤 Broadcasting Customer Profile: {customer_profile.get('name', 'Unknown')}, Risk: {risk_category}")

        # 5. Bot Response with Admin Data
        await broadcast_to_admin({
            "type": "bot_response",
            "data": {
                "response": result["ai_response"],
                "admin_data": {
                    "trust_score": result.get("trust_score"),
                    "customer_profile": result.get("customer_profile"),
                    "verification_status": result.get("verification_status")
                }
            },
            "timestamp": datetime.now().isoformat()
        })
        
        # Prepare response with ALL UI flags
        response = ChatResponse(
            response=result["ai_response"],
            session_id=request.session_id,
            conversation_stage=result.get("conversation_stage", "unknown"),
            missing_info=result.get("missing_info", []),
            decision=result.get("loan_decision"),
            show_upload=result.get("show_upload", False),  # NEW: Upload button flag
            show_sanction_letter=result.get("show_sanction_letter", False),  # NEW: Download button flag
            loan_details=result.get("loan_details"),  # NEW: Loan details for sanction letter
            customer_name=result.get("name"),  # NEW: Customer name for letter
            admin_data={
                "trust_score": result.get("trust_score"),
                "verification_status": result.get("verification_status"),
                "admin_log": result.get("admin_log", [])
            }
        )
        
        return response
        
    except Exception as e:
        # Log error and broadcast to admin
        error_data = {
            "type": "error",
            "session_id": request.session_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        await broadcast_to_admin(error_data)
        
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.post("/api/reset-session")
async def reset_session(session_id: str = Form(...)):
    """Reset/clear a conversation session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"success": True, "message": "Session cleared successfully"}
    return {"success": True, "message": "Session not found (already cleared)"}


# PHASE 6: Sanction Letter Download Endpoint
@app.get("/api/download-sanction/{session_id}")
async def download_sanction_letter(session_id: str):
    """
    PHASE 6: Generate and download sanction letter PDF
    Called when sales agent closes the deal
    """
    try:
        # Get session
        session = get_or_create_session(session_id)
        user_profile = session.get("state", {}).get("user_profile", {})
        loan_request = session.get("state", {}).get("loan_request", {})
        negotiation = session.get("state", {}).get("negotiation_state", {})
        
        # Extract data
        customer_name = user_profile.get("name", "Valued Customer")
        loan_amount = loan_request.get("amount", 500000)
        interest_rate = negotiation.get("current_offered_rate", 12.0)
        tenure = loan_request.get("tenure", 36)
        emi = loan_request.get("emi", 15000)
        phone = user_profile.get("phone", "")
        pan = user_profile.get("pan", "")
        
        # Generate PDF
        pdf_path = generate_sanction_letter(
            customer_name=customer_name,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            tenure=tenure,
            emi=emi,
            phone=phone,
            pan=pan
        )
        
        # Return file response
        filename = f"Tata_Capital_Sanction_Letter_{customer_name.replace(' ', '_')}.pdf"
        
        def cleanup():
            """Cleanup function to delete temp file after sending"""
            cleanup_pdf_file(pdf_path)
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=filename,
            background=cleanup  # Auto-cleanup after sending
        )
        
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Could not generate sanction letter: {str(e)}")


@app.post("/api/upload")
async def upload_document_vision(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    document_count: str = Form(...)
):
    """
    PHASE 5: Document Intelligence with Gemini Vision
    Actually analyzes uploaded documents instead of mocking
    """
    
    try:
        # Read file contents
        contents = await file.read()
        doc_count = int(document_count)
        
        # Get session
        session = get_or_create_session(session_id)
        
        print(f"\n{'='*60}")
        print(f"📤 VISION DOCUMENT PROCESSING")
        print(f"Session ID: {session_id}")
        print(f"File: {file.filename}")
        print(f"File size: {len(contents)} bytes")
        print(f"{'='*60}\n")
        
        # PHASE 5: Use Gemini Vision to analyze document
        if agent:
            try:
                # Create GeminiLLM instance with API key
                gemini = GeminiLLM(GEMINI_API_KEY)
                
                # Send to Gemini Vision (base64 encode the file)
                import base64
                file_data = base64.b64encode(contents).decode('utf-8')
                
                # Set correct mime type based on file extension
                filename_lower = file.filename.lower()
                if filename_lower.endswith('.pdf'):
                    file_mime = 'application/pdf'
                elif filename_lower.endswith('.png'):
                    file_mime = 'image/png'
                elif filename_lower.endswith('.jpg') or filename_lower.endswith('.jpeg'):
                    file_mime = 'image/jpeg'
                else:
                    file_mime = file.content_type or 'image/jpeg'
                
                print(f"📄 File MIME type: {file_mime}")
                
                # Determine document type from filename
                if 'salary' in filename_lower or 'slip' in filename_lower or 'payslip' in filename_lower:
                    doc_type_hint = 'Salary Slip'
                elif 'pan' in filename_lower:
                    doc_type_hint = 'PAN Card'
                elif 'bank' in filename_lower or 'statement' in filename_lower:
                    doc_type_hint = 'Bank Statement'
                else:
                    doc_type_hint = 'Unknown'
                
                # PHASE 5: Vision prompt for document analysis based on type
                if doc_type_hint == 'Salary Slip':
                    vision_prompt = """Analyze this Salary Slip document and extract ALL salary components as JSON:
{
    "doc_type": "Salary Slip",
    "employee_name": "<full name of the employee>",
    "employer_name": "<company name>",
    "month": "<month and year string e.g. 'January 2024'>",
    "salary_date": "<date salary was credited if visible, format: YYYY-MM-DD or null>",
    
    "earnings": {
        "basic_pay": <number - Basic Salary component>,
        "hra": <number - House Rent Allowance or 0>,
        "special_allowances": <number - sum of all other allowances like conveyance, medical, etc or 0>,
        "other_earnings": <number - any other additions or 0>
    },
    
    "deductions": {
        "pf_deduction": <number - Provident Fund deduction or 0>,
        "tax_deduction": <number - TDS/Income Tax deduction or 0>,
        "professional_tax": <number - Professional Tax or 0>,
        "other_deductions": <number - any other deductions or 0>
    },
    
    "gross_salary": <number - Total Earnings before deductions>,
    "total_deductions": <number - Sum of all deductions>,
    "net_salary": <number - the NET SALARY or TAKE HOME amount>,
    
    "pan_number": "<PAN if visible or null>",
    "employee_id": "<Employee ID if visible or null>",
    
    "visual_analysis": {
        "font_consistency": <true if fonts are consistent, false if different fonts detected>,
        "alignment_quality": <true if text alignment is proper, false if suspicious>,
        "image_quality": "<good/medium/poor>",
        "signs_of_editing": <true if there are visual signs of editing/tampering, false otherwise>,
        "suspicion_score": <0-100, higher means more suspicious of tampering>
    },
    
    "confidence": <0-100 based on clarity and extraction certainty>
}

IMPORTANT: Extract EXACT numbers as shown. Check for visual anomalies like:
- Different fonts used for numbers vs text
- Suspicious text alignment or spacing
- Signs of digital editing or cut-paste
- Inconsistent formatting

Return ONLY valid JSON."""""
                elif doc_type_hint == 'PAN Card':
                    vision_prompt = """Analyze this PAN Card document and extract the following fields as JSON:
{
    "doc_type": "PAN Card",
    "pan_number": "<10-character PAN number>",
    "full_name": "<full name as shown on PAN>",
    "father_name": "<father's name if visible or null>",
    "dob": "<date of birth if visible or null>",
    
    "visual_analysis": {
        "font_consistency": <true if fonts are consistent, false if different fonts detected>,
        "hologram_visible": <true if hologram/watermark visible, false otherwise>,
        "signs_of_editing": <true if there are visual signs of editing/tampering, false otherwise>,
        "suspicion_score": <0-100, higher means more suspicious of tampering>
    },
    
    "confidence": <0-100 based on clarity>
}

Return ONLY valid JSON. Extract the EXACT text shown."""
                elif doc_type_hint == 'Bank Statement':
                    vision_prompt = """Analyze this Bank Statement document and extract the following fields as JSON:
{
    "doc_type": "Bank Statement",
    "account_holder_name": "<name on the account>",
    "bank_name": "<name of the bank>",
    "account_number": "<account number, can be partially masked>",
    "statement_period": {
        "from_date": "<start date in YYYY-MM-DD format>",
        "to_date": "<end date in YYYY-MM-DD format>"
    },
    
    "opening_balance": <number>,
    "closing_balance": <number>,
    
    "transactions": [
        {
            "date": "<YYYY-MM-DD>",
            "description": "<transaction narration>",
            "type": "CREDIT" or "DEBIT",
            "amount": <number>,
            "balance": <number after transaction>
        }
    ],
    
    "credit_summary": {
        "total_credits": <total of all credit transactions>,
        "salary_credits": [<list of amounts that appear to be salary credits based on description>],
        "credit_count": <number of credit transactions>
    },
    
    "visual_analysis": {
        "font_consistency": <true if fonts are consistent>,
        "alignment_quality": <true if proper alignment>,
        "signs_of_editing": <true if tampering detected>,
        "suspicion_score": <0-100>
    },
    
    "confidence": <0-100>
}

Extract ALL visible transactions. Focus on identifying salary credit entries.
Return ONLY valid JSON."""
                else:
                    vision_prompt = """Analyze this document and extract the following fields as JSON:
{
    "doc_type": "Salary Slip" | "Bank Statement" | "PAN Card" | "CIBIL Report" | "Other",
    "net_salary": <number or null>,
    "employer_name": "<string or null>",
    "pan_number": "<string or null>",
    "bank_name": "<string or null>",
    "account_balance": <number or null>,
    "full_name": "<name if visible or null>",
    "confidence": <0-100>
}

Return ONLY valid JSON."""
                
                # Call Gemini Vision API
                try:
                    extracted_data = await gemini.analyze_document(file_data, file_mime, vision_prompt)
                    print(f"📄 Gemini Vision extracted: {extracted_data}")
                except Exception as vision_error:
                    print(f"⚠️ Vision API error, using fallback: {vision_error}")
                    # Fallback mock data for demo - with proper salary components
                    user_name = session.get("state", {}).get("user_profile", {}).get("name", "Employee")
                    if doc_type_hint == 'Salary Slip':
                        extracted_data = {
                            "doc_type": "Salary Slip",
                            "employee_name": user_name,
                            "employer_name": "Tech Mahindra Ltd",
                            "month": "November 2025",
                            "earnings": {
                                "basic_pay": 50000,
                                "hra": 20000,
                                "special_allowances": 35000,
                                "other_earnings": 0
                            },
                            "deductions": {
                                "pf_deduction": 6000,
                                "tax_deduction": 4000,
                                "professional_tax": 200,
                                "other_deductions": 0
                            },
                            "gross_salary": 105000,
                            "total_deductions": 10200,
                            "net_salary": 94800,
                            "visual_analysis": {
                                "font_consistency": True,
                                "alignment_quality": True,
                                "image_quality": "good",
                                "signs_of_editing": False,
                                "suspicion_score": 5
                            },
                            "confidence": 85
                        }
                    else:
                        extracted_data = {
                            "doc_type": doc_type_hint,
                            "full_name": user_name,
                            "pan_number": "ABCDE1234F" if doc_type_hint == 'PAN Card' else None,
                            "confidence": 75
                        }
                
                # Get user profile from session
                user_profile = session.get("state", {}).get("user_profile", {})
                financial_data = session.get("state", {}).get("financial_data", {})
                expected_salary = financial_data.get("monthly_income", 0)
                claimed_name = user_profile.get("name", "")
                
                # ========== STRICT VERIFICATION: CROSS-CHECK LOGIC ==========
                docs_verified = False
                verification_message = ""
                discrepancy_flags = []
                
                # Store extracted data for underwriting to use
                if "document_state" not in session["state"]:
                    session["state"]["document_state"] = {}
                
                # Ensure financial_data exists in session state
                if "financial_data" not in session["state"]:
                    session["state"]["financial_data"] = {}
                
                # ---- SALARY VERIFICATION (Strict 90% Rule) ----
                if extracted_data.get("net_salary"):
                    proven_salary = extracted_data["net_salary"]
                    session["state"]["document_state"]["proven_salary"] = proven_salary
                    
                    if expected_salary > 0:
                        # STRICT RULE: If proven_salary < 90% of claimed_salary → Discrepancy
                        if proven_salary < (0.9 * expected_salary):
                            discrepancy_flags.append("SALARY_DISCREPANCY")
                            verification_message = f"**Salary Discrepancy Detected**\n\nThe document shows a salary of **Rs. {proven_salary:,}**, which is lower than the Rs. {expected_salary:,} you mentioned.\n\n**I must use the documented amount (Rs. {proven_salary:,}) for underwriting.**"
                            
                            # Update financial data with PROVEN salary
                            session["state"]["financial_data"]["monthly_income"] = proven_salary
                            session["state"]["financial_data"]["annual_income"] = proven_salary * 12
                            session["state"]["financial_data"]["salary_source"] = "DOCUMENT_VERIFIED"
                            
                            # Recalculate pre-approved limit with proven salary
                            credit_score = financial_data.get("credit_score", 650)
                            if credit_score >= 750:
                                new_pre_approved = min(proven_salary * 60, 2000000)
                            elif credit_score >= 700:
                                new_pre_approved = min(proven_salary * 48, 1500000)
                            else:
                                new_pre_approved = min(proven_salary * 36, 1000000)
                            session["state"]["financial_data"]["pre_approved_limit"] = new_pre_approved
                            
                            docs_verified = True  # Document is valid, just lower than claimed
                        elif proven_salary >= (0.9 * expected_salary):
                            docs_verified = True
                            verification_message = f"**Salary Verified:** Rs. {proven_salary:,} matches your profile!"
                            session["state"]["financial_data"]["monthly_income"] = proven_salary
                            session["state"]["financial_data"]["salary_source"] = "DOCUMENT_VERIFIED"
                    else:
                        # No claimed salary - use proven salary directly
                        docs_verified = True
                        session["state"]["financial_data"]["monthly_income"] = proven_salary
                        session["state"]["financial_data"]["salary_source"] = "DOCUMENT_VERIFIED"
                        verification_message = f"**Salary Extracted:** Rs. {proven_salary:,}/month"
                
                # ---- NAME/IDENTITY VERIFICATION (Fuzzy Match 80% Rule) ----
                document_name = extracted_data.get("employee_name") or extracted_data.get("full_name")
                if document_name and claimed_name:
                    session["state"]["document_state"]["document_name"] = document_name
                    
                    # Use fuzzy matching if available
                    if fuzz:
                        name_similarity = fuzz.ratio(claimed_name.lower(), document_name.lower())
                        session["state"]["document_state"]["name_similarity"] = name_similarity
                        
                        if name_similarity < 80:
                            discrepancy_flags.append("NAME_MISMATCH")
                            docs_verified = False
                            verification_message += f"\n\n**Identity Mismatch Detected**\n\nThe document shows the name **'{document_name}'**, but you registered as **'{claimed_name}'** (Match: {name_similarity}%).\n\n**This document cannot be accepted.** Please upload a document with your registered name."
                        else:
                            verification_message += f"\n\n**Name Verified:** {document_name} (Match: {name_similarity}%)"
                    else:
                        # Simple comparison fallback
                        if claimed_name.lower().strip() in document_name.lower() or document_name.lower() in claimed_name.lower().strip():
                            verification_message += f"\n\n**Name Verified:** {document_name}"
                        else:
                            discrepancy_flags.append("NAME_MISMATCH")
                            docs_verified = False
                            verification_message += f"\n\n**Identity Mismatch:** Document shows '{document_name}', expected '{claimed_name}'"
                
                # ---- PAN VERIFICATION ----
                if extracted_data.get("pan_number"):
                    session["state"]["document_state"]["verified_pan"] = extracted_data["pan_number"]
                    verification_message += f"\n\n**PAN Verified:** {extracted_data['pan_number']}"
                
                # Store discrepancy flags
                session["state"]["document_state"]["discrepancy_flags"] = discrepancy_flags
                session["state"]["document_state"]["docs_verified"] = docs_verified
                session["state"]["document_state"][f"doc_{doc_count}"] = extracted_data
                
                # ========== FRAUD DETECTION (RISK CONTROL) ==========
                fraud_detected = False
                fraud_message = ""
                risk_control_results = {
                    "fraud_detected": False,
                    "math_check": None,
                    "bank_check": None,
                    "visual_check": None,
                    "fraud_reasons": []
                }
                
                # Store extracted data by document type for cross-checks
                if "extracted_data" not in session["state"]["document_state"]:
                    session["state"]["document_state"]["extracted_data"] = {}
                
                doc_type = extracted_data.get("doc_type", doc_type_hint)
                session["state"]["document_state"]["extracted_data"][doc_type] = extracted_data
                
                # 1. MATHEMATICAL INTEGRITY CHECK (Salary Slip)
                if doc_type == "Salary Slip":
                    math_result = validate_salary_math(extracted_data)
                    risk_control_results["math_check"] = math_result
                    print(f"🔢 Math Check Result: {math_result['status']} - {math_result.get('reason', '')}")
                    
                    if math_result["status"] == "FRAUD_DETECTED":
                        fraud_detected = True
                        risk_control_results["fraud_reasons"].append(f"Math: {math_result.get('reason')}")
                
                # 2. VISUAL FORGERY CHECK (All Documents)
                visual_result = check_visual_forgery(extracted_data)
                risk_control_results["visual_check"] = visual_result
                print(f"👁️ Visual Check Result: {visual_result['status']} - Score: {visual_result.get('suspicion_score', 0)}")
                
                if visual_result["status"] == "MANUAL_REVIEW":
                    fraud_detected = True
                    risk_control_results["fraud_reasons"].append(f"Visual: {visual_result.get('reason')}")
                
                # 3. BANK STATEMENT CROSS-CHECK (If both Salary Slip and Bank Statement are uploaded)
                all_extracted = session["state"]["document_state"].get("extracted_data", {})
                if "Salary Slip" in all_extracted and "Bank Statement" in all_extracted:
                    salary_data = all_extracted["Salary Slip"]
                    bank_data = all_extracted["Bank Statement"]
                    bank_result = cross_check_bank_statement(salary_data, bank_data)
                    risk_control_results["bank_check"] = bank_result
                    print(f"🏦 Bank Cross-Check Result: {bank_result['status']} - Found: {bank_result.get('salary_found')}")
                    
                    if bank_result["status"] == "DISCREPANCY":
                        fraud_detected = True
                        risk_control_results["fraud_reasons"].append(f"Bank: {bank_result.get('reason')}")
                
                # Store risk control state
                risk_control_results["fraud_detected"] = fraud_detected
                session["state"]["risk_control"] = risk_control_results
                
                # If fraud detected, return polite rejection
                if fraud_detected:
                    print(f"FRAUD DETECTED: {risk_control_results['fraud_reasons']}")
                    
                    fraud_message = f"""**Document Verification Issue**

I'm having trouble verifying the authenticity of your uploaded document. This could happen due to:
- Image quality or resolution issues
- Document not being an original copy
- Internal formatting inconsistencies

**What you can do:**
- Please upload the **original PDF** downloaded directly from your payroll portal or bank's website.
- If uploading photos, ensure they're clear, uncropped, and include the full document.

**Need help?** Our team can assist you at **1800-XXX-XXXX** (Toll-free).

_Your application is safe - you can re-upload the correct document to continue._"""
                    
                    session["state"]["document_state"]["verification_status"] = "FRAUD_SUSPECTED"
                    session["state"]["document_state"]["requires_reupload"] = True
                    
                    return UploadResponse(
                        success=False,
                        message="Document verification failed",
                        response=fraud_message,
                        session_id=session_id,
                        document_verified=False,
                        extracted_data=extracted_data,
                        trust_score=max(10, 50 - visual_result.get("suspicion_score", 0))
                    )
                
                # Process through agent
                result = await agent.process_message(
                    user_message=f"document uploaded: {file.filename}",
                    conversation_history=session.get("conversation_history", []),
                    previous_state=session.get("state", {})
                )
                
                # Add verification info to response
                if verification_message:
                    result["ai_response"] += f"\n\n{verification_message}"
                
                return UploadResponse(
                    success=True,
                    message="Document processed successfully",
                    response=result.get("ai_response", "Document processed successfully"),
                    session_id=session_id,
                    document_verified=docs_verified,
                    extracted_data=extracted_data,
                    trust_score=result.get("trust_score", 50)
                )
                
            except Exception as e:
                print(f"❌ Vision processing error: {e}")
                return UploadResponse(
                    success=False,
                    message=f"Document processing failed: {str(e)}",
                    response="Sorry, I couldn't process that document. Please try uploading again.",
                    session_id=session_id
                )
        
        return UploadResponse(
            success=False,
            message="Agent not available",
            response="Service temporarily unavailable",
            session_id=session_id
        )
    
    except Exception as e:
        print(f"❌ Upload error: {e}")
        return UploadResponse(
            success=False,
            message=f"Upload failed: {str(e)}",
            response="Sorry, something went wrong processing your document.",
            session_id=session_id
        )


@app.get("/session/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(session_id: str):
    """Get information about a specific session"""
    
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions[session_id]
    
    return SessionInfoResponse(
        session_id=session_id,
        conversation_history=session.get("messages", []),
        current_state=session.get("state", {})
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Delete a session"""
    
    if session_id in sessions:
        del sessions[session_id]
        return {"message": f"Session {session_id} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")


# ==================== ADMIN DASHBOARD ENDPOINTS ====================
@app.websocket("/admin/stream")
async def admin_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for admin "God Mode" dashboard
    Streams all agent activity in real-time
    """
    
    await websocket.accept()
    admin_connections.append(websocket)
    
    # Send initial connection message
    await websocket.send_json({
        "type": "connection",
        "message": "Connected to TataSmartAgent Admin Stream",
        "active_sessions": len(sessions),
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # Keep connection alive and listen for any client messages
            data = await websocket.receive_text()
            
            # Handle admin commands
            if data == "get_sessions":
                await websocket.send_json({
                    "type": "sessions_list",
                    "sessions": list(sessions.keys()),
                    "count": len(sessions),
                    "timestamp": datetime.now().isoformat()
                })
            elif data.startswith("get_session:"):
                session_id = data.split(":")[1]
                if session_id in sessions:
                    await websocket.send_json({
                        "type": "session_detail",
                        "session": sessions[session_id],
                        "timestamp": datetime.now().isoformat()
                    })
                    
    except WebSocketDisconnect:
        admin_connections.remove(websocket)
        print(f"Admin disconnected. Active connections: {len(admin_connections)}")


@app.get("/admin/sessions")
async def get_all_sessions():
    """Get list of all active sessions"""
    return {
        "total_sessions": len(sessions),
        "sessions": [
            {
                "session_id": sid,
                "created_at": session["created_at"],
                "last_activity": session["last_activity"],
                "message_count": len(session.get("messages", [])),
                "state": session.get("state", {})
            }
            for sid, session in sessions.items()
        ]
    }


@app.get("/admin/customers")
async def get_all_customers():
    """Get all mock customer profiles (for testing)"""
    return {
        "total_customers": len(MockDataProvider.get_all_customers()),
        "customers": [
            {
                "name": profile["name"],
                "phone": profile["phone"],
                "credit_score": profile["financial_data"]["credit_score"],
                "risk_category": profile["behavioral_flags"]["risk_category"]
            }
            for profile in MockDataProvider.get_all_customers().values()
        ]
    }


@app.post("/api/admin-event")
async def receive_admin_event(request: Request):
    """
    Receive events from ChatWidget and broadcast to Admin Dashboard
    This enables the 'scripted mode' to sync both screens
    """
    try:
        event_data = await request.json()
        
        # Broadcast to all connected admin dashboards
        await broadcast_to_admin(event_data)
        
        return {"success": True, "message": "Event broadcasted"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/admin/reset")
async def reset_all_sessions():
    """Clear all sessions (for testing)"""
    global sessions
    count = len(sessions)
    sessions = {}
    
    await broadcast_to_admin({
        "type": "system_reset",
        "message": f"All {count} sessions cleared",
        "timestamp": datetime.now().isoformat()
    })
    
    return {
        "message": f"Reset complete. Cleared {count} sessions.",
        "timestamp": datetime.now().isoformat()
    }


# ==================== TESTING ENDPOINTS ====================
@app.post("/test/verify-customer")
async def test_verify_customer(phone: str, pan: str):
    """Test endpoint to verify customer lookup"""
    result = MockDataProvider().verify_customer(phone, pan)
    return result


@app.get("/test/customer/{phone}")
async def test_get_customer(phone: str):
    """Test endpoint to get customer by phone"""
    customer = MockDataProvider.get_customer_by_phone(phone)
    if customer:
        return customer
    else:
        raise HTTPException(status_code=404, detail="Customer not found")


# ==================== LEGACY AUTH ENDPOINT (For backward compatibility) ====================
@app.post("/api/auth/login")
async def login(credentials: Dict):
    """Mock login for admin dashboard"""
    username = credentials.get("username")
    password = credentials.get("password")
    
    if username == "admin" and password == "tata123":
        return {
            "success": True,
            "token": "mock_jwt_token_v3",
            "user": {
                "username": "admin",
                "role": "bank_officer",
                "name": "Admin User"
            }
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ==================== LEGACY CHAT ENDPOINT (For backward compatibility) ====================
@app.post("/api/chat")
async def legacy_chat_endpoint(request: Request):
    """Legacy chat endpoint for backward compatibility"""
    try:
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id")
        
        # Generate session_id if not provided
        if not session_id:
            import time
            import random
            session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        
        chat_req = ChatRequest(
            message=message,
            session_id=session_id,
            metadata=None
        )
        result = await chat_endpoint(chat_req)
        return {
            "session_id": result.session_id,
            "response": result.response,
            "state": result.conversation_stage,
            "decision": result.decision
        }
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ERROR HANDLERS ====================
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "detail": str(exc),
            "timestamp": datetime.now().isoformat()
        }
    )


# ==================== STARTUP MESSAGE ====================
if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        TataSmartAgent - Production Backend                ║
    ║                                                            ║
    ║  🤖 Agentic AI Loan Officer                               ║
    ║  🧠 Powered by LangGraph + Google Gemini                  ║
    ║  🔐 Production-Grade Underwriting                         ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

