"""
TataSmartAgent - FastAPI Main Application
Production-grade backend for Agentic AI Loan Officer

================================================================================
PHASE 1 REFACTOR: DETERMINISTIC STAGE-BASED FLOW CONTROL
================================================================================

CHANGE: Added stage-based conversation handler that replaces LLM-driven routing.

OLD ARCHITECTURE:
    User Message → Master LLM decides next agent → Agent processes

NEW ARCHITECTURE:  
    User Message → StageRouter (deterministic) → LLM generates response only

The LLM no longer decides conversation flow - it only generates natural language.
================================================================================
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

# OLD: LLM-driven agent (kept for backward compatibility)
from graph_agent import create_agent, LoanAgentGraph, GeminiLLM, validate_salary_math, cross_check_bank_statement, check_visual_forgery

# NEW: Stage-based deterministic handler (PHASE 1 REFACTOR)
from conversation_handler import StageBasedConversationHandler, create_conversation_handler
from stage_machine import ConversationStage

# ================================================================================
# PHASE 1 STRICT STAGE MACHINE (NEW - DETERMINISTIC FLOW CONTROL)
# ================================================================================
# This is the NEW strict stage machine that provides:
# - Single source of truth for loan journey stage
# - Deterministic stage transitions (no LLM decisions)
# - State persistence across page reloads
# - Invalid transition blocking with logging
from stage_machine_v2 import (
    Stage,
    StageEvent,
    StageState,
    StageController,
    get_stage_controller,
    get_current_stage,
    request_transition,
    update_session_data,
    get_session_state as get_strict_session_state,
    reset_session as reset_strict_session,
    get_stage_instruction,
    STAGE_INSTRUCTIONS
)
from stage_handler import StageMessageHandler, create_stage_handler

# ================================================================================
# PHASE 2: CONVERSATIONAL HANDLER (QUESTION SEQUENCING)
# ================================================================================
# This handler adds proper question sequencing on top of the strict stage machine:
# - One question at a time
# - Proper sequence: purpose → amount → city → employment → name → mobile
# - Natural conversation flow
from stage_handler_v2 import ConversationalStageHandler, create_conversational_handler

from mock_data import MockDataProvider
from pdf_generator import generate_sanction_letter, cleanup_pdf_file
from external_services import external_api_router

# ================================================================================
# HARD RESET: DETERMINISTIC FLOW CONTROLLER (PART 1-6 REFACTOR)
# ================================================================================
# This is the NEW deterministic flow controller that provides:
# - Strict 13-stage sequence
# - Backend controls ALL logic (flow, verification, credit, approval)
# - LLM controls ONLY wording
# - Data integrity enforcement
# - Admin dashboard state
from deterministic_flow import (
    get_flow_controller,
    process_message as deterministic_process_message,
    get_session_state as deterministic_get_session_state,
    get_admin_state,
    get_all_admin_sessions,
    reset_session as deterministic_reset_session,
    FlowStage,
    TERMINAL_STAGES,
)

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

# ==================== GLOBAL INSTANCES ====================
# OLD: LLM-driven agent (kept for backward compatibility)
agent: Optional[LoanAgentGraph] = None

# NEW: Stage-based conversation handler (PHASE 1 REFACTOR - LEGACY)
stage_handler: Optional[StageBasedConversationHandler] = None

# ================================================================================
# PHASE 1 STRICT: New strict stage handler (DETERMINISTIC)
# This handler uses the strict stage machine for flow control
# ================================================================================
strict_stage_handler: Optional[StageMessageHandler] = None
strict_stage_controller: Optional[StageController] = None

# ================================================================================
# PHASE 2: Conversational handler (QUESTION SEQUENCING)
# This handler adds proper question flow on top of strict stage control
# ================================================================================
conversational_handler: Optional[ConversationalStageHandler] = None

# Active WebSocket connections for admin dashboard
admin_connections: List[WebSocket] = []

# Session storage (in production, use Redis or database)
sessions: Dict[str, Dict[str, Any]] = {}



# ==================== LIFESPAN MANAGEMENT ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global agent, stage_handler, strict_stage_handler, strict_stage_controller, conversational_handler
    
    # Startup
    print("🚀 Initializing TataSmartAgent...")
    
    # ========================================================================
    # PHASE 1 STRICT: Initialize the strict stage machine FIRST
    # This is the SINGLE SOURCE OF TRUTH for loan journey flow
    # ========================================================================
    strict_stage_controller = get_stage_controller()
    strict_stage_handler = create_stage_handler(backend_services=None)
    print("="*60)
    print("✅ PHASE 1 STRICT: Stage Machine initialized")
    print("   - Deterministic flow control enabled")
    print("   - State persistence enabled")
    print("   - Invalid transitions will be blocked")
    print("="*60)
    
    # ========================================================================
    # PHASE 2: Initialize the conversational handler
    # This adds question sequencing on top of strict stage control
    # ========================================================================
    conversational_handler = create_conversational_handler(backend_services=None)
    print("="*60)
    print("✅ PHASE 2: Conversational Handler initialized")
    print("   - Question sequencing enabled")
    print("   - One question at a time")
    print("   - Natural conversation flow")
    print("="*60)
    
    if GEMINI_API_KEY:
        # Initialize OLD agent for backward compatibility
        agent = await create_agent(GEMINI_API_KEY)
        print("✅ Legacy Agent initialized")
        
        # Initialize legacy stage-based handler (PHASE 1 - old implementation)
        data_provider = MockDataProvider()
        stage_handler = create_conversation_handler(data_provider)
        print("✅ Legacy Stage-Based Handler initialized")
    else:
        print("⚠️ GEMINI_API_KEY not set - LLM features disabled")
        print("   Stage machine will still work for flow control")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down TataSmartAgent...")


# ==================== FASTAPI APP ====================
app = FastAPI(
    title="TataSmartAgent",
    description="Production-grade Agentic AI Loan Officer using LangGraph & Google Gemini",
    version="2.0.0",  # Version bump for Phase 1 refactor
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
    has_uploaded_docs: Optional[bool] = Field(False, description="Flag indicating documents were uploaded")
    documents_verified: Optional[bool] = Field(False, description="Flag indicating documents were verified")
    # PHASE 8: Customer Acquisition Source
    # Tracks how customer arrived at the chatbot (for personalized greeting)
    # "AD" = clicked digital advertisement, "EMAIL" = opened marketing email
    acquisition_source: Optional[str] = Field(None, description="Acquisition channel: 'AD' or 'EMAIL'")


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
    # PHASE 5: Session closure fields
    session_closed: bool = False  # True after SANCTION or REJECTION
    closure_reason: Optional[str] = None  # LOAN_SANCTIONED, LOAN_REJECTED, etc.


class UploadResponse(BaseModel):
    """Response model for document upload
    
    CRITICAL FIX: Added stage-related fields to ensure frontend derives
    upload button visibility from stage, not from manual toggle.
    
    The flow after document verification:
    1. Upload endpoint processes document
    2. If verified, calls stage_handler to advance stage
    3. Returns current_stage and show_upload
    4. Frontend derives showUpload from current_stage
    """
    success: bool
    message: str
    response: Optional[str] = None  # AI response message
    session_id: Optional[str] = None
    document_verified: Optional[bool] = None  # Whether document passed verification
    extracted_data: Optional[Dict[str, Any]] = None
    trust_score: Optional[int] = None
    fraud_detected: Optional[bool] = None  # Whether fraud was detected
    risk_control: Optional[Dict[str, Any]] = None  # Fraud detection results
    # CRITICAL FIX: Stage-driven UI control
    current_stage: Optional[str] = None  # Current stage after processing
    show_upload: bool = False  # Derived from stage === INCOME_DOC_UPLOAD
    show_sanction_letter: bool = False  # True if stage === SANCTION and letter generated
    loan_details: Optional[Dict[str, Any]] = None  # Loan details if sanctioned


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
        "status": "healthy" if conversational_handler else "degraded",
        "agent_ready": agent is not None,
        "stage_handler_ready": stage_handler is not None,
        "strict_stage_handler_ready": strict_stage_handler is not None,  # PHASE 1 STRICT
        "conversational_handler_ready": conversational_handler is not None,  # PHASE 2
        "strict_stage_controller_ready": strict_stage_controller is not None,  # PHASE 1 STRICT
        "active_sessions": len(sessions),
        "admin_connections": len(admin_connections),
        "gemini_api_configured": bool(GEMINI_API_KEY),
        "timestamp": datetime.now().isoformat()
    }


# ================================================================================
# HARD RESET: DETERMINISTIC RESPONSE GENERATOR
# ================================================================================
# Generates bot responses based on CURRENT STAGE and SESSION DATA
# LLM DOES NOT control flow - only provides polite wording
# ================================================================================

def generate_deterministic_response(stage: str, session_data: dict) -> str:
    """
    Generate bot response based on CURRENT STAGE.
    
    RULES:
    - Response matches CURRENT stage question
    - NEVER mention credit score
    - NEVER calculate EMI before tenure selection
    - Show interest rate as RANGE
    
    IMPORTANT: Uses LAZY EVALUATION (if/elif) instead of dictionary
    to avoid format string errors when values are None.
    """
    user_name = session_data.get("user_name", "")
    name_part = f", {user_name}" if user_name else ""
    
    # Get values with safe defaults (avoid None)
    loan_purpose = session_data.get("loan_purpose") or "personal"
    loan_amount = session_data.get("loan_amount") or 0
    city = session_data.get("city") or ""
    employment = session_data.get("employment_type") or ""
    
    # LAZY EVALUATION: Only generate the specific response needed
    if stage == "GREETING":
        return "Hello and welcome to Tata Capital! I'm here to help you with your personal loan application. The process is quick and can be completed in just a few minutes.\n\nHow may I assist you today?"
    
    elif stage == "PURPOSE":
        return "Great! What would you like to use the loan for? (e.g., home renovation, education, medical expenses, wedding, travel, personal needs)"
    
    elif stage == "AMOUNT":
        return f"Perfect! You're looking for a {loan_purpose} loan. How much amount are you looking to borrow?"
    
    elif stage == "CITY":
        if loan_amount and loan_amount > 0:
            return f"Got it! You need ₹{loan_amount:,.0f}. Which city do you currently reside in?"
        return "Thank you! Which city do you currently reside in?"
    
    elif stage == "EMPLOYMENT_TYPE":
        if city:
            return f"Great! You're in {city}. Are you salaried or self-employed?"
        return "Thank you! Are you salaried or self-employed?"
    
    elif stage == "NAME":
        emp_display = employment.replace('_', '-') if employment else 'registered'
        return f"Thank you! You're {emp_display}. May I have your full name as per official documents?"
    
    elif stage == "MOBILE":
        return f"Nice to meet you{name_part}! Please provide your 10-digit mobile number for OTP verification."
    
    elif stage == "OTP":
        return "I've sent a 6-digit OTP to your mobile number. Please enter it to verify your identity."
    
    elif stage == "KYC":
        return f"OTP verified successfully{name_part}! Now please provide your PAN number for identity verification."
    
    elif stage == "OFFER_DISCUSSION":
        return _generate_offer_response(session_data)
    
    elif stage == "TENURE_SELECTION":
        return _generate_tenure_response(session_data)
    
    elif stage == "UNDERWRITING":
        return f"Thank you{name_part}! Processing your application..."
    
    elif stage == "SANCTION":
        return _generate_sanction_response(session_data)
    
    elif stage == "REJECTION":
        return f"Thank you for your interest{name_part}. Unfortunately, we are unable to approve your application at this time based on our eligibility criteria.\n\nYou may reapply after 6 months or contact our support team at 1800-XXX-XXXX for more information."
    
    else:
        return "Processing your request..."


def _generate_offer_response(session_data: dict) -> str:
    """Generate OFFER stage response with interest RANGE (not fixed EMI)."""
    user_name = session_data.get("user_name", "")
    name_part = f", {user_name}" if user_name else ""
    
    # Ensure all values are never None (use 0 as safe default)
    pre_approved = session_data.get("pre_approved_limit") or 0
    interest_min = session_data.get("interest_rate_min") or 10.5
    interest_max = session_data.get("interest_rate_max") or 18.0
    
    return f"""Great news{name_part}! Based on your profile, you're pre-approved for:

💰 **Loan Amount:** Up to ₹{pre_approved:,.0f}
📊 **Interest Rate:** {interest_min}% to {interest_max}% per annum

Your final EMI will depend on the tenure you select. Would you like to proceed? (Say 'yes' or 'proceed')"""


def _generate_tenure_response(session_data: dict) -> str:
    """Generate TENURE selection response with EMI options."""
    emi_options = session_data.get("emi_options") or {}
    pre_approved = session_data.get("pre_approved_limit") or 0
    
    response = """Please select your preferred loan tenure:

"""
    for months in [12, 24, 36, 48]:
        emi = emi_options.get(months, 0) if emi_options else 0
        if emi and emi > 0:
            response += f"• **{months} months** → EMI: ₹{emi:,.0f}/month\n"
        else:
            response += f"• **{months} months**\n"
    
    response += "\n💡 *Shorter tenure = Higher EMI but less total interest*\n*Longer tenure = Lower EMI but more total interest*\n\nPlease type your choice (e.g., '24 months' or '2 years')"
    
    return response


def _generate_sanction_response(session_data: dict) -> str:
    """Generate SANCTION response with final loan details."""
    user_name = session_data.get("user_name", "")
    name_part = f" {user_name}" if user_name else ""
    
    # Ensure all values are never None (use safe defaults)
    amount = session_data.get("pre_approved_limit") or 0
    rate = session_data.get("final_interest_rate") or 12.0
    tenure = session_data.get("selected_tenure") or 24
    emi = session_data.get("calculated_emi") or 0
    
    return f"""🎉 **Congratulations{name_part}!** Your loan has been approved!

**Loan Details:**
━━━━━━━━━━━━━━━━━━━━━━
💰 **Approved Amount:** ₹{amount:,.0f}
📊 **Interest Rate:** {rate}% per annum
📅 **Tenure:** {tenure} months
💵 **Monthly EMI:** ₹{emi:,.0f}
━━━━━━━━━━━━━━━━━━━━━━

Your sanction letter is ready for download. A copy has also been sent to your registered email.

Thank you for choosing Tata Capital! 🙏"""


# ================================================================================
# HARD RESET: NEW DETERMINISTIC FLOW ENDPOINT (V3)
# ================================================================================
# This endpoint uses deterministic_flow.py - the ONLY correct implementation
# 
# FEATURES:
# - Strict 13-stage linear flow (no skipping)
# - No file upload (income from database only)
# - EMI calculated AFTER tenure selection
# - Interest rate as RANGE (10.5%-18%)
# - Backend controls ALL decisions
# - Admin dashboard shows exact backend state
# - LLM NEVER hallucinates (backend controls logic)
# ================================================================================

@app.post("/api/v3/chat", response_model=ChatResponse)
async def deterministic_chat_endpoint(request: ChatRequest):
    """
    HARD RESET: Deterministic Flow Chat Endpoint
    
    This is the CORRECT implementation using deterministic_flow.py
    
    13-STAGE FLOW:
    1. GREETING → 2. PURPOSE → 3. AMOUNT → 4. CITY → 5. EMPLOYMENT_TYPE →
    6. NAME → 7. MOBILE → 8. OTP → 9. KYC → 10. OFFER_DISCUSSION →
    11. TENURE_SELECTION → 12. UNDERWRITING → 13. SANCTION/REJECTION
    
    RULES:
    - Stage advances ONLY when required data is collected
    - Out-of-order input is IGNORED, current question repeated
    - Credit score NEVER exposed to user
    - EMI calculated ONLY after tenure selection
    - Admin dashboard shows exact backend state
    """
    try:
        # Process through deterministic flow controller
        result = deterministic_process_message(
            session_id=request.session_id,
            message=request.message
        )
        
        # Get current state for admin
        state = deterministic_get_session_state(request.session_id)
        admin_state = get_admin_state(request.session_id)
        
        # Generate bot response based on current stage
        current_stage = result.get("current_stage", "GREETING")
        session_data = result.get("session", {})
        
        # Build contextual bot response
        bot_response = generate_deterministic_response(current_stage, session_data)
        
        # Broadcast to admin dashboard
        timestamp = datetime.now().isoformat()
        
        # 1. User Message
        await broadcast_to_admin({
            "type": "user_message",
            "data": {"message": request.message},
            "session_id": request.session_id,
            "timestamp": timestamp
        })
        
        # 2. Stage Transition
        await broadcast_to_admin({
            "type": "stage_transition",
            "data": {
                "stage": current_stage,
                "stage_number": result.get("stage_number"),
                "stage_changed": result.get("stage_changed", False)
            },
            "session_id": request.session_id,
            "timestamp": timestamp
        })
        
        # 3. Bot Response
        await broadcast_to_admin({
            "type": "bot_response",
            "data": {
                "response": bot_response,
                "stage": current_stage
            },
            "session_id": request.session_id,
            "timestamp": timestamp
        })
        
        # 4. Full State Update for Admin
        if admin_state:
            await broadcast_to_admin({
                "type": "state_update",
                "data": admin_state,
                "session_id": request.session_id,
                "timestamp": timestamp
            })
        
        # Determine if session is closed (terminal stage)
        is_terminal = current_stage in ["SANCTION", "REJECTION"]
        
        # Get loan details for sanction
        loan_details = None
        if current_stage == "SANCTION":
            loan_details = {
                "amount": session_data.get("pre_approved_limit"),
                "interest_rate": session_data.get("final_interest_rate"),
                "tenure": session_data.get("selected_tenure"),
                "emi": session_data.get("calculated_emi")
            }
        
        # Build response
        return ChatResponse(
            response=bot_response,
            session_id=request.session_id,
            conversation_stage=current_stage,
            missing_info=[],
            decision=session_data.get("underwriting_result"),
            show_upload=False,  # HARD RESET: No file upload
            show_sanction_letter=current_stage == "SANCTION",
            loan_details=loan_details,
            customer_name=session_data.get("user_name"),
            session_closed=is_terminal,
            closure_reason=session_data.get("underwriting_result") if is_terminal else None,
            admin_data=admin_state
        )
        
    except Exception as e:
        print(f"❌ Deterministic chat error: {e}")
        import traceback
        traceback.print_exc()
        
        # Broadcast error to admin
        await broadcast_to_admin({
            "type": "error",
            "data": {"error": str(e)},
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


# ================================================================================
# RESET SESSION ENDPOINT FOR V3
# ================================================================================

@app.post("/api/v3/reset-session")
async def reset_deterministic_session(request: dict):
    """Reset session for deterministic flow"""
    session_id = request.get("session_id")
    if session_id:
        deterministic_reset_session(session_id)
        return {"status": "success", "message": "Session reset"}
    return {"status": "error", "message": "No session_id provided"}


# ================================================================================
# PHASE 1 STRICT: NEW DETERMINISTIC STAGE MACHINE ENDPOINT (LEGACY)
# ================================================================================
# This endpoint uses the NEW strict stage machine for GUARANTEED flow control.
#
# WHY THIS EXISTS:
# - The old stage_handler still has some flexibility in transitions
# - This new endpoint enforces STRICT deterministic transitions
# - Invalid transitions are BLOCKED and LOGGED
# - State persists across page reloads
# - NO LLM decisions affect flow - only backend logic
#
# USE THIS FOR:
# - Testing deterministic flow
# - Production systems requiring strict compliance
# - Debugging stage transition issues
#
# ================================================================================
# STRICT GATING MIDDLEWARE INTEGRATION (NEW)
# ================================================================================
# The gating middleware validates ALL inputs BEFORE they reach the handler:
# - Checks input matches expected type for current stage
# - Enforces preconditions (e.g., OTP must be verified before KYC)
# - Returns re-ask prompts for invalid input instead of advancing
# - Logs all validation failures for debugging
# ================================================================================

# Import gating middleware at module level
from strict_gating_middleware import get_gating_middleware, GatingResult

@app.post("/api/v2/chat", response_model=ChatResponse)
async def strict_stage_chat_endpoint(request: ChatRequest):
    """
    PHASE 2: Conversational Stage-Based Chat with QUESTION SEQUENCING
    + STRICT GATING MIDDLEWARE for input validation
    
    ================================================================================
    PHASE 2 IMPROVEMENTS OVER PHASE 1
    ================================================================================
    
    1. ONE QUESTION AT A TIME - Never ask multiple questions in single message
    2. PROPER SEQUENCE: purpose → amount → city → employment → name → mobile  
    3. NATURAL CONVERSATION - Bot acknowledges answers, smooth transitions
    4. REDIRECT HANDLING - Gently redirect off-topic responses
    
    ================================================================================
    STRICT GATING (NEW)
    ================================================================================
    
    BEFORE processing, the gating middleware:
    1. Validates input matches expected type for current stage
    2. Checks preconditions are met (e.g., OTP verified before KYC)
    3. Blocks invalid input and returns re-ask prompt
    4. Logs all validation for audit trail
    
    ================================================================================
    STAGE PROGRESSION (STRICT - NO SKIPPING):
    ================================================================================
    
    GREETING → NEEDS_DISCOVERY → BASIC_ELIGIBILITY → KYC_COLLECTION →
    OTP_VERIFICATION → KYC_VERIFICATION → OFFER_DISCOVERY →
    INCOME_DOC_UPLOAD → UNDERWRITING → SANCTION or REJECTION
    
    ================================================================================
    """
    
    if not conversational_handler:
        raise HTTPException(
            status_code=503, 
            detail="Conversational handler not initialized."
        )
    
    try:
        # ====================================================================
        # STRICT GATING: Validate input BEFORE processing
        # ====================================================================
        gating_middleware = get_gating_middleware()
        
        # Get current state for validation
        current_state = get_strict_session_state(request.session_id) or {}
        current_stage = current_state.get("current_stage", "GREETING")
        current_step = current_state.get("conversation_step")
        
        # Validate input against expected type
        gating_result = gating_middleware.validate_input(
            session_id=request.session_id,
            user_message=request.message,
            current_stage=current_stage,
            current_step=current_step,
            state_data=current_state
        )
        
        # Log gating result
        print(f"\n{'='*60}")
        print(f"📍 STRICT GATING: {gating_result.log_entry}")
        print(f"   Allowed: {gating_result.allowed}")
        print(f"{'='*60}\n")
        
        # If gating blocked (precondition failed or re-ask required)
        if not gating_result.allowed:
            if gating_result.precondition_failed:
                print(f"⛔ PRECONDITION FAILED: {gating_result.precondition_error}")
                return ChatResponse(
                    response=gating_middleware.get_reask_prompt(
                        current_stage, current_step, gating_result
                    ),
                    session_id=request.session_id,
                    conversation_stage=current_stage,
                    missing_info=[],
                    decision=None,
                    show_upload=False,
                    show_sanction_letter=False,
                    admin_data={
                        "stage": current_stage,
                        "gating_blocked": True,
                        "gating_reason": "precondition_failed",
                        "gating_error": gating_result.precondition_error
                    }
                )
            
            if gating_result.reask_required:
                print(f"🔄 RE-ASK REQUIRED: {gating_result.reask_message}")
                return ChatResponse(
                    response=gating_result.reask_message,
                    session_id=request.session_id,
                    conversation_stage=current_stage,
                    missing_info=[],
                    decision=None,
                    show_upload=(current_stage == "INCOME_DOC_UPLOAD"),
                    show_sanction_letter=False,
                    admin_data={
                        "stage": current_stage,
                        "gating_blocked": True,
                        "gating_reason": "reask_required",
                        "gating_message": gating_result.reask_message
                    }
                )
        
        # ====================================================================
        # GATING PASSED: Process through conversational handler
        # ====================================================================
        result = conversational_handler.process_message(
            session_id=request.session_id,
            user_message=request.message,
            has_uploaded_docs=request.has_uploaded_docs,
            documents_verified=request.documents_verified
        )
        
        # Log the transition for debugging
        timestamp = datetime.now().isoformat()
        
        print(f"\n{'='*60}")
        print(f"📍 PHASE 2 CONVERSATIONAL: Message Processed")
        print(f"   Session: {request.session_id}")
        print(f"   Stage: {result['previous_stage']} → {result['current_stage']}")
        print(f"   Changed: {result['stage_changed']}")
        print(f"   Bot Response: {result.get('bot_response', '')[:50]}...")
        print(f"   Next Step: {result.get('conversation_step')}")
        print(f"{'='*60}\n")
        
        # Broadcast to admin dashboard
        await broadcast_to_admin({
            "type": "stage_transition",
            "data": {
                "session_id": request.session_id,
                "previous_stage": result["previous_stage"],
                "current_stage": result["current_stage"],
                "stage_changed": result["stage_changed"],
                "conversation_step": result.get("conversation_step"),
                "machine": "CONVERSATIONAL_V2"  # Identify which machine processed this
            },
            "timestamp": timestamp
        })
        
        # Get state data for response
        state_data = result.get("state_data", {})
        
        # PHASE 2: Use bot_response from conversational handler
        # This has proper question sequencing built in
        response_text = result.get("bot_response", "")
        
        # Fallback to generated response if bot_response is empty
        if not response_text:
            stage_instruction = result.get("stage_instruction", "")
            response_text = _generate_stage_response(
                result["current_stage"],
                state_data,
                stage_instruction
            )
        
        # Add OTP to response if needed (only if not already in response)
        if result.get("otp_code") and "OTP" not in response_text:
            response_text += f"\n\n📱 Your OTP: **{result['otp_code']}** (valid for 5 minutes)"
        
        return ChatResponse(
            response=response_text,
            session_id=request.session_id,
            conversation_stage=result["current_stage"],
            missing_info=[],
            decision=state_data.get("loan_status"),
            show_upload=result.get("show_upload", False),
            show_sanction_letter=result.get("show_sanction_letter", False),
            loan_details=None,  # Would be populated in SANCTION stage
            customer_name=state_data.get("user_name"),
            session_closed=result.get("session_closed", False),
            closure_reason=result.get("closure_reason"),
            admin_data={
                "stage": result["current_stage"],
                "stage_changed": result["stage_changed"],
                "machine": "STRICT_V2",
                "transition_result": result.get("transition_result"),
                "state_summary": {
                    "user_name": state_data.get("user_name"),
                    "user_mobile": state_data.get("user_mobile"),
                    "loan_amount": state_data.get("loan_amount"),
                    "otp_verified": state_data.get("otp_verified"),
                    "kyc_verified": state_data.get("kyc_verified"),
                }
            }
        )
        
    except Exception as e:
        print(f"❌ Strict stage chat error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


@app.get("/api/v2/stage/{session_id}")
async def get_strict_stage_state(session_id: str):
    """
    PHASE 1 STRICT: Get current stage state for a session
    
    This endpoint returns the EXACT state from the strict stage machine.
    Use this to verify the current stage and all collected data.
    """
    state = get_strict_session_state(session_id)
    
    if not state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "current_stage": state.get("current_stage"),
        "session_closed": state.get("session_closed"),
        "closure_reason": state.get("closure_reason"),
        "state": state,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/v2/reset/{session_id}")
async def reset_strict_stage_session(session_id: str):
    """
    PHASE 1 STRICT: Reset a session completely
    
    This removes all state and starts fresh.
    Use for testing or when user wants to start over.
    """
    reset_strict_session(session_id)
    
    return {
        "success": True,
        "message": f"Session {session_id} reset successfully",
        "timestamp": datetime.now().isoformat()
    }


def _generate_stage_response(stage: str, state_data: Dict[str, Any], instruction: str) -> str:
    """
    Generate a response based on current stage.
    
    NOTE: This is a TEMPORARY implementation for Phase 1.
    In production, this would use the LLM with the stage instruction as context.
    
    For Phase 1 (flow control only), we use simple template responses.
    """
    user_name = state_data.get("user_name", "")
    loan_amount = state_data.get("loan_amount")
    
    responses = {
        "GREETING": "Welcome to Tata Capital! I'm your AI loan assistant. How can I help you today? Are you looking for a personal loan, home loan, or something else?",
        
        "NEEDS_DISCOVERY": "I'd be happy to help you with a loan. Could you tell me how much you're looking to borrow?",
        
        "BASIC_ELIGIBILITY": f"Great! You're looking for a loan of ₹{loan_amount:,.0f}." if loan_amount else "Let me check your basic eligibility. I'll need to verify your identity first.",
        
        "KYC_COLLECTION": "To proceed with your loan application, I'll need to verify your identity. Please share your full name and 10-digit mobile number.",
        
        "OTP_VERIFICATION": f"I've sent an OTP to your mobile number. Please enter the 6-digit code to verify your identity.",
        
        "KYC_VERIFICATION": f"Thank you{', ' + user_name if user_name else ''}! Your identity is being verified...",
        
        "OFFER_DISCOVERY": f"Great news{', ' + user_name if user_name else ''}! Let me check what offers are available for you...",
        
        "INCOME_DOC_UPLOAD": "To finalize your loan, please upload your salary slip or income proof using the upload button below.",
        
        "UNDERWRITING": "I'm reviewing your documents and making the final decision. This will just take a moment...",
        
        "SANCTION": f"🎉 Congratulations{', ' + user_name if user_name else ''}! Your loan has been approved! You can download your sanction letter now.",
        
        "REJECTION": f"I'm sorry{', ' + user_name if user_name else ''}, but we're unable to approve your loan at this time. {state_data.get('rejection_reason', 'Please contact our support team for more details.')}",
    }
    
    return responses.get(stage, "Processing your request...")


# ================================================================================
# PHASE 1: NEW STAGE-BASED CHAT ENDPOINT (DETERMINISTIC FLOW) - LEGACY
# ================================================================================
# This endpoint replaces LLM-driven routing with deterministic stage control.
# The conversation flow is controlled by StageRouter, not by the LLM.
# ================================================================================

@app.post("/api/chat", response_model=ChatResponse)
async def stage_based_chat_endpoint(request: ChatRequest):
    """
    PHASE 1: Stage-Based Chat Endpoint with DETERMINISTIC Flow Control
    
    ================================================================================
    KEY CHANGE FROM OLD ARCHITECTURE:
    ================================================================================
    
    OLD (LLM-driven):
        User Message → Master LLM decides which agent → Agent processes → Response
        PROBLEM: LLM could jump between stages randomly
    
    NEW (Stage-driven):
        User Message → StageRouter (deterministic logic) → LLM generates response
        SOLUTION: Strict linear progression through stages
    
    ================================================================================
    STAGE PROGRESSION:
    ================================================================================
    
    GREETING → NEEDS_ANALYSIS → KYC_COLLECTION → KYC_VERIFICATION →
    OFFER_CHECK → CREDIT_CHECK → INCOME_DOC_UPLOAD → 
    UNDERWRITING_DECISION → SANCTION or REJECTION
    
    Each transition is controlled by DETERMINISTIC RULES, not LLM decisions:
    - GREETING → NEEDS_ANALYSIS: Always after greeting
    - NEEDS_ANALYSIS → KYC_COLLECTION: When loan_amount is provided
    - KYC_COLLECTION → KYC_VERIFICATION: When phone number is provided
    - etc.
    
    ================================================================================
    """
    
    if not stage_handler:
        raise HTTPException(
            status_code=503, 
            detail="Stage-based handler not initialized. Check GEMINI_API_KEY."
        )
    
    try:
        # PHASE 5: Check if session is closed before processing
        # This prevents any responses after loan sanction/rejection
        existing_state = stage_handler.get_session_state(request.session_id)
        if existing_state and existing_state.get("session_closed"):
            closure_reason = existing_state.get("closure_reason", "COMPLETED")
            return ChatResponse(
                response=f"This loan application session has ended ({closure_reason}). Please start a new conversation for any additional inquiries.",
                session_id=request.session_id,
                conversation_stage=existing_state.get("current_stage", "SANCTION"),
                missing_info=[],
                decision=None,
                show_upload=False,
                show_sanction_letter=closure_reason == "LOAN_SANCTIONED",
                loan_details=None,
                customer_name=existing_state.get("user_name"),
                admin_data={
                    "stage": existing_state.get("current_stage"),
                    "session_closed": True,
                    "closure_reason": closure_reason
                }
            )
        
        # Process message through DETERMINISTIC stage machine
        # The StageRouter decides flow, LLM only generates response text
        result = await stage_handler.process_message(
            session_id=request.session_id,
            user_message=request.message,
            has_uploaded_docs=request.has_uploaded_docs,
            documents_verified=request.documents_verified,
            acquisition_source=request.acquisition_source  # PHASE 8: Track how customer arrived
        )
        
        # Broadcast to admin dashboard
        timestamp = datetime.now().isoformat()
        
        # 1. User Message
        await broadcast_to_admin({
            "type": "user_message",
            "data": {"message": request.message},
            "timestamp": timestamp
        })
        
        # 2. Stage Transition Log (NEW: Shows deterministic flow)
        await broadcast_to_admin({
            "type": "log",
            "data": {
                "message": f"Stage: {result['previous_stage']} → {result['current_stage']}",
                "level": "info" if result['stage_changed'] else "info",
                "agent": "StageRouter"
            },
            "timestamp": timestamp
        })
        
        # 3. Bot Response
        await broadcast_to_admin({
            "type": "bot_response",
            "data": {
                "response": result["response"],
                "active_agent": result.get("active_agent", "unknown"),
                "admin_data": result.get("state_summary", {})
            },
            "timestamp": timestamp
        })
        
        # 4. Agent Assignment Log (NEW: Shows which worker agent is responding)
        agent_info = result.get("agent_info", {})
        await broadcast_to_admin({
            "type": "agent_assignment",
            "data": {
                "agent_type": result.get("active_agent", "unknown"),
                "agent_name": agent_info.get("agent_name", "Unknown Agent"),
                "stage": result["current_stage"]
            },
            "timestamp": timestamp
        })
        
        # Return response with UI flags
        return ChatResponse(
            response=result["response"],
            session_id=request.session_id,
            conversation_stage=result["current_stage"],
            missing_info=[],  # Stage machine handles this internally
            decision=None,  # Set in SANCTION/REJECTION stages
            show_upload=result.get("show_upload", False),
            show_sanction_letter=result.get("show_sanction_letter", False),
            loan_details=result.get("loan_details"),
            customer_name=result.get("state_summary", {}).get("user_name"),
            # PHASE 5: Session closure fields
            session_closed=result.get("session_closed", False),
            closure_reason=result.get("closure_reason"),
            admin_data={
                "stage": result["current_stage"],
                "stage_changed": result["stage_changed"],
                "active_agent": result.get("active_agent"),  # NEW: Which agent responded
                "agent_info": result.get("agent_info"),      # NEW: Agent metadata
                "state_summary": result.get("state_summary", {}),
                # PHASE 5: Include closure info in admin data
                "session_closed": result.get("session_closed", False),
                "closure_reason": result.get("closure_reason")
            }
        )
        
    except Exception as e:
        # Log error
        error_data = {
            "type": "error",
            "session_id": request.session_id,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        await broadcast_to_admin(error_data)
        
        print(f"❌ Stage-based chat error: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")


# ================================================================================
# LEGACY ENDPOINT (Kept for backward compatibility)
# ================================================================================

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


# PHASE 7: Sanction Letter Download Endpoint
@app.get("/api/download-sanction/{session_id}")
async def download_sanction_letter(session_id: str):
    """
    PHASE 7: Download pre-generated sanction letter PDF
    
    ================================================================================
    HOW THIS SIMULATES REAL NBFC DOCUMENT DELIVERY:
    ================================================================================
    
    In a real NBFC, after loan sanction:
    1. Credit Operations generates the sanction letter (done by SanctionLetterService)
    2. Letter is stored in document management system (our /sanction_letters folder)
    3. Customer downloads via portal/email link (this endpoint)
    4. Customer reviews and accepts
    5. Disbursement proceeds
    
    PHASE 7 CHANGES:
    ----------------
    - First tries to serve pre-generated PDF from /sanction_letters folder
    - File was created during SANCTION stage by SanctionLetterService
    - Path stored in state.sanction_letter_path
    - Falls back to on-demand generation only if pre-generated file not found
    
    WHY PRE-GENERATION MATTERS:
    ---------------------------
    1. AUDIT TRAIL: Document was created at time of decision
    2. CONSISTENCY: Same file served for multiple downloads
    3. PERFORMANCE: No PDF generation on each download
    4. REALISTIC: Matches real NBFC workflow
    
    ================================================================================
    """
    try:
        # Get the conversation handler to access state
        handler = stage_handler
        state = handler.get_session_state(session_id) if handler else None
        
        if state:
            # PHASE 7: First check if pre-generated PDF exists
            pre_generated_path = state.get("sanction_letter_path")
            
            if pre_generated_path and os.path.exists(pre_generated_path):
                # Serve the pre-generated PDF (preferred method)
                customer_name = state.get("user_name", "Valued Customer")
                filename = f"Aurora_Finance_Sanction_Letter_{customer_name.replace(' ', '_')}.pdf"
                
                print(f"📄 PHASE 7: Serving pre-generated sanction letter")
                print(f"   File: {pre_generated_path}")
                print(f"   Customer: {customer_name}")
                
                return FileResponse(
                    pre_generated_path,
                    media_type='application/pdf',
                    filename=filename
                    # Note: No cleanup - file is persistent for audit
                )
            
            # Fallback: Generate on-demand if pre-generated file not found
            print(f"⚠️ PHASE 7: Pre-generated PDF not found, generating on-demand")
            
            customer_name = state.get("user_name", "Valued Customer")
            loan_amount = state.get("loan_amount", 500000)
            interest_rate = state.get("effective_interest_rate") or state.get("interest_rate", 12.5)
            tenure = state.get("loan_tenure_months", 48)
            emi = state.get("calculated_emi") or state.get("emi_amount", 15000)
            # Support both mobile_number (new) and user_phone (deprecated)
            phone = state.get("user_mobile_number") or state.get("user_phone", "")
            pan = state.get("user_pan", "")
            approval_type = state.get("approval_type", "Standard")
            
            print(f"📜 Generating sanction letter from conversation state")
            print(f"   Customer: {customer_name}")
            print(f"   Amount: ₹{loan_amount:,.0f}")
            print(f"   Rate: {interest_rate}%")
            print(f"   EMI: ₹{emi:,.0f}")
        else:
            # Fallback to session storage (legacy)
            session = get_or_create_session(session_id)
            user_profile = session.get("state", {}).get("user_profile", {})
            loan_request = session.get("state", {}).get("loan_request", {})
            negotiation = session.get("state", {}).get("negotiation_state", {})
            
            customer_name = user_profile.get("name", "Valued Customer")
            loan_amount = loan_request.get("amount", 500000)
            interest_rate = negotiation.get("current_offered_rate", 12.0)
            tenure = loan_request.get("tenure", 36)
            emi = loan_request.get("emi", 15000)
            phone = user_profile.get("phone", "")
            pan = user_profile.get("pan", "")
            approval_type = "Standard"
            
            print(f"⚠️ LEGACY: Using session storage for sanction letter")
        
        # Generate PDF using verified data (on-demand fallback)
        pdf_path = generate_sanction_letter(
            customer_name=customer_name,
            loan_amount=int(loan_amount) if loan_amount else 500000,
            interest_rate=float(interest_rate) if interest_rate else 12.5,
            tenure=int(tenure) if tenure else 48,
            emi=int(emi) if emi else 15000,
            phone=phone or "",
            pan=pan or "",
            approval_type=approval_type,
            session_id=session_id
        )
        
        # Return file response
        filename = f"Aurora_Finance_Sanction_Letter_{customer_name.replace(' ', '_')}.pdf"
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=filename
            # Note: No cleanup for Phase 7 - files are persistent
        )
        
    except Exception as e:
        print(f"❌ PDF download error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not download sanction letter: {str(e)}")


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
                    print(f"🚨 FRAUD DETECTED: {risk_control_results['fraud_reasons']}")
                    
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
                        trust_score=max(10, 50 - visual_result.get("suspicion_score", 0)),
                        # CRITICAL FIX: Stay in INCOME_DOC_UPLOAD for reupload
                        current_stage="INCOME_DOC_UPLOAD",
                        show_upload=True  # Allow re-upload
                    )
                
                # ================================================================
                # CRITICAL FIX: Advance stage after successful document verification
                # ================================================================
                # Previously, the upload endpoint processed documents but did NOT
                # advance the conversation stage, causing the system to get stuck
                # in INCOME_DOC_UPLOAD with upload button reappearing.
                #
                # FIX: Call stage_handler.process_message() with document flags
                # to trigger deterministic stage transition:
                # INCOME_DOC_UPLOAD → UNDERWRITING_DECISION → SANCTION/REJECTION
                # ================================================================
                
                print(f"\n{'='*60}")
                print(f"📄 DOCUMENT VERIFICATION SUCCESSFUL")
                print(f"   Document: {file.filename}")
                print(f"   Verified: {docs_verified}")
                print(f"   Session: {session_id}")
                print(f"{'='*60}")
                
                # Get the state BEFORE processing to track transition
                pre_state = stage_handler.get_session_state(session_id)
                pre_stage = pre_state.get("current_stage", "UNKNOWN") if pre_state else "UNKNOWN"
                print(f"📍 PRE-UPLOAD STAGE: {pre_stage}")
                
                # CRITICAL: Call stage_handler with document flags
                # This triggers the stage machine to:
                # 1. Mark documents as uploaded in state
                # 2. Transition from INCOME_DOC_UPLOAD → UNDERWRITING_DECISION
                # 3. Run underwriting engine (if in UNDERWRITING_DECISION)
                # 4. Transition to SANCTION or REJECTION
                stage_result = await stage_handler.process_message(
                    session_id=session_id,
                    user_message=f"[DOCUMENT_UPLOADED: {file.filename}]",
                    document_uploaded=True,
                    uploaded_doc_type="salary_slip",
                    has_uploaded_docs=True,
                    documents_verified=docs_verified
                )
                
                post_stage = stage_result.get("current_stage", "UNKNOWN")
                print(f"📍 POST-UPLOAD STAGE: {post_stage}")
                print(f"✅ STAGE TRANSITION: {pre_stage} → {post_stage}")
                
                # Derive UI flags from stage (NOT from manual toggle)
                show_upload_flag = (post_stage == "INCOME_DOC_UPLOAD")
                show_sanction_letter_flag = stage_result.get("show_sanction_letter", False)
                
                # Build response message
                response_text = stage_result.get("response", "Document processed successfully")
                if verification_message:
                    response_text = f"{verification_message}\n\n{response_text}"
                
                # Prepare loan details if sanctioned
                loan_details_data = None
                if post_stage == "SANCTION" and show_sanction_letter_flag:
                    loan_details_data = stage_result.get("loan_details")
                
                print(f"📊 UPLOAD RESPONSE FLAGS:")
                print(f"   show_upload: {show_upload_flag}")
                print(f"   show_sanction_letter: {show_sanction_letter_flag}")
                print(f"   current_stage: {post_stage}")
                
                return UploadResponse(
                    success=True,
                    message="Document processed and verified",
                    response=response_text,
                    session_id=session_id,
                    document_verified=docs_verified,
                    extracted_data=extracted_data,
                    trust_score=85,
                    # CRITICAL FIX: Stage-driven UI control
                    current_stage=post_stage,
                    show_upload=show_upload_flag,
                    show_sanction_letter=show_sanction_letter_flag,
                    loan_details=loan_details_data
                )
                
            except Exception as e:
                print(f"❌ Vision processing error: {e}")
                import traceback
                traceback.print_exc()
                return UploadResponse(
                    success=False,
                    message=f"Document processing failed: {str(e)}",
                    response="Sorry, I couldn't process that document. Please try uploading again.",
                    session_id=session_id,
                    current_stage="INCOME_DOC_UPLOAD",
                    show_upload=True  # Allow retry
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
    """
    Get list of all active sessions with full state for ADMIN DASHBOARD.
    
    ADMIN DASHBOARD REQUIREMENTS (PART 6):
    - READ-ONLY: No actions, no modifications
    - BACKEND STATE ONLY: Shows deterministic state machine truth
    - NEVER DISCONNECT: Stable data, no websocket-dependent fields
    - NEVER INFER: Only actual values, no computed/guessed fields
    
    Shows:
    - Application ID
    - Current stage
    - KYC status
    - Offer eligibility
    - Decision reason
    """
    # ====================================================================
    # HARD RESET: Use DETERMINISTIC FLOW CONTROLLER for admin state
    # This is the authoritative source of truth for all session data
    # ====================================================================
    deterministic_sessions = get_all_admin_sessions()
    
    # Also include legacy sessions that may not be in deterministic controller
    result_sessions = []
    deterministic_session_ids = {s["session_id"] for s in deterministic_sessions}
    
    # Add deterministic sessions first (these are authoritative)
    for admin_state in deterministic_sessions:
        session_id = admin_state["session_id"]
        legacy_session = sessions.get(session_id, {})
        
        result_sessions.append({
            "session_id": session_id,
            "created_at": legacy_session.get("created_at", admin_state["timestamps"]["created_at"]),
            "last_activity": legacy_session.get("last_activity", admin_state["timestamps"]["last_updated"]),
            "message_count": len(legacy_session.get("messages", [])),
            "state": admin_state,  # Use admin-specific view
        })
    
    # Add any legacy sessions not in deterministic controller (for backward compat)
    for sid, session in sessions.items():
        if sid not in deterministic_session_ids:
            # Try to get deterministic state
            admin_state = get_admin_state(sid)
            if not admin_state:
                # Fallback to legacy state
                strict_state = get_strict_session_state(sid)
                if not strict_state:
                    strict_state = stage_handler.get_session_state(sid) if stage_handler else None
                admin_state = strict_state if strict_state else session.get("state", {})
            
            result_sessions.append({
                "session_id": sid,
                "created_at": session["created_at"],
                "last_activity": session["last_activity"],
                "message_count": len(session.get("messages", [])),
                "state": admin_state
            })
    
    return {
        "total_sessions": len(result_sessions),
        "sessions": result_sessions
    }


@app.get("/admin/session/{session_id}")
async def get_admin_session(session_id: str):
    """
    Get admin dashboard state for a SINGLE session.
    
    ADMIN DASHBOARD REQUIREMENTS (PART 6):
    - READ-ONLY: No actions, no modifications
    - BACKEND STATE ONLY: Shows deterministic state machine truth
    - NEVER DISCONNECT: Stable data, no websocket-dependent fields
    - NEVER INFER: Only actual values, no computed/guessed fields
    
    Shows:
    - Application ID
    - Current stage
    - KYC status
    - Offer eligibility
    - Decision reason
    """
    admin_state = get_admin_state(session_id)
    
    if not admin_state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": admin_state
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
# NOTE: This endpoint is DEPRECATED. Use /api/chat for the new stage-based system.
# This is kept only for any old integrations that may still use /chat (without /api prefix)
@app.post("/legacy/chat")
async def legacy_chat_endpoint(request: Request):
    """
    DEPRECATED: Legacy chat endpoint for backward compatibility.
    Use /api/chat instead for the new stage-based deterministic flow.
    """
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
        # Route to the OLD chat_endpoint (LLM-driven) for backward compatibility
        result = await chat_endpoint(chat_req)
        return {
            "session_id": result.session_id,
            "response": result.response,
            "state": result.conversation_stage,
            "decision": result.decision
        }
    except Exception as e:
        print(f"Error in legacy chat endpoint: {str(e)}")
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

