"""
TataSmartAgent - FastAPI Main Application (CLEAN VERSION)

================================================================================
HARD RESET: DETERMINISTIC 13-STAGE FLOW
================================================================================

This is the CLEAN implementation with all legacy code removed.

FEATURES:
- Strict 16-stage linear flow (no skipping)
- No file upload (income from database only)
- EMI calculated AFTER tenure selection
- Interest rate as RANGE (10.5%-18%)
- Backend controls ALL decisions
- Admin dashboard shows exact backend state
- LLM NEVER hallucinates (backend controls logic)

STAGES:
1. GREETING → 2. PURPOSE → 3. AMOUNT → 4. CITY → 5. EMPLOYMENT_TYPE →
6. NAME → 7. MOBILE → 8. OTP → 9. KYC → 10. OFFER_DISCUSSION →
11. TENURE_SELECTION → 12. UNDERWRITING → 13. SANCTION/REJECTION

================================================================================
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import asyncio

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field

# PDF Generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
import tempfile

# Gemini AI Integration
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("⚠️ google-generativeai not installed. Using hardcoded responses only.")

# HARD RESET: Deterministic Flow Controller (ONLY source of truth)
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

from mock_data import MockDataProvider
from pdf_generator import generate_sanction_letter

# Load environment variables
load_dotenv()

# ==================== GEMINI AI CONFIGURATION ====================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"  # Disabled - using hardcoded responses

# Initialize Gemini model
gemini_model = None
if GEMINI_AVAILABLE and GEMINI_API_KEY and USE_GEMINI:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        print(f"✅ Gemini AI initialized (model: gemini-2.0-flash)")
        print(f"   API Key: {GEMINI_API_KEY[:20]}...")
    except Exception as e:
        print(f"⚠️ Gemini initialization failed: {e}")
        gemini_model = None
else:
    if not GEMINI_API_KEY:
        print("⚠️ GEMINI_API_KEY not set. Using hardcoded responses.")
    elif not USE_GEMINI:
        print("ℹ️ Gemini disabled via USE_GEMINI=false. Using hardcoded responses.")


# ==================== INDIAN CURRENCY FORMATTING ====================
def format_indian_currency(amount) -> str:
    """
    Format number in Indian currency style (lakhs/crores).
    
    Examples:
    - 500000 → 5,00,000
    - 1500000 → 15,00,000
    - 50000 → 50,000
    - 12345678 → 1,23,45,678
    
    Indian number system:
    - First comma after 3 digits from right
    - Then commas every 2 digits
    """
    amount = int(round(float(amount)))
    s = str(amount)
    
    if len(s) <= 3:
        return s
    
    # Split: last 3 digits + rest
    last_three = s[-3:]
    rest = s[:-3]
    
    # Add commas every 2 digits to the rest
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    
    return ','.join(parts) + ',' + last_three


# Active WebSocket connections for admin dashboard
admin_connections: List[WebSocket] = []

# Session storage (in production, use Redis/database)
sessions: Dict[str, Dict[str, Any]] = {}


# ==================== LIFESPAN ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown"""
    print("""
============================================================
🏦 TATA CAPITAL - DETERMINISTIC LOAN CHATBOT (V4)
============================================================
📍 Flow: 16-stage strict linear sequence
🔒 Backend controls ALL logic
📊 Admin dashboard shows exact state
💳 Dynamic Credit Scoring from user inputs
💵 EMI calculated AFTER tenure selection
🤖 Gemini AI for natural responses
============================================================
    """)
    
    # Initialize the deterministic flow controller
    controller = get_flow_controller()
    print("✅ Deterministic Flow Controller initialized")
    print(f"   - 16 stages enforced")
    print(f"   - Dynamic credit scoring enabled")
    print(f"   - State persistence enabled")
    
    yield
    
    print("🛑 Shutting down...")


# ==================== FASTAPI APP ====================
app = FastAPI(
    title="TataSmartAgent",
    description="Deterministic 16-Stage Loan Chatbot with Dynamic Credit Scoring",
    version="4.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== PYDANTIC MODELS ====================
class ChatRequest(BaseModel):
    """Request model for chat"""
    message: str = Field(..., description="User's message")
    session_id: Optional[str] = Field(None, description="Session ID")


class ChatResponse(BaseModel):
    """Response model for chat"""
    response: str
    session_id: str
    conversation_stage: str
    missing_info: List[str] = Field(default_factory=list)
    decision: Optional[str] = None
    show_upload: bool = False  # Always False (no uploads)
    show_sanction_letter: bool = False
    loan_details: Optional[Dict[str, Any]] = None
    customer_name: Optional[str] = None
    admin_data: Optional[Dict[str, Any]] = None
    session_closed: bool = False
    closure_reason: Optional[str] = None


# ==================== HELPERS ====================
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
    
    for conn in disconnected:
        if conn in admin_connections:
            admin_connections.remove(conn)


# ==================== GEMINI AI RESPONSE GENERATION ====================

# Stage-specific prompts for Gemini
STAGE_PROMPTS = {
    "GREETING": """You are a friendly loan assistant at Tata Capital. 
    Generate a warm, welcoming greeting for a new customer. 
    Mention that you help with personal loans. Ask if they're looking for a loan today.
    Use 1-2 emojis. Keep it 2-3 sentences max.""",
    
    "PURPOSE": """The customer wants a loan. Ask them what they need the loan for.
    Mention some common purposes: home renovation, education, medical expenses, wedding, travel.
    Be warm and helpful. Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "AMOUNT": """The customer told us their loan purpose is: {loan_purpose}
    Now ask how much they want to borrow.
    Give an example format (e.g., "5 lakhs" or "500000").
    Be encouraging. Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "CITY": """The customer wants to borrow ₹{loan_amount_formatted}.
    Acknowledge the amount positively and ask which city they live in.
    Mention it helps check branch availability.
    Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "EMPLOYMENT_TYPE": """The customer lives in {city}.
    Acknowledge the city positively and ask if they are salaried or self-employed.
    Mention this helps find the best rates.
    Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "NAME": """Now ask for the customer's full name as it appears on their PAN card.
    Mention this is important for verification.
    Be professional but friendly. Use 1 emoji. Keep it 2 sentences.""",
    
    "MOBILE": """The customer's name is {user_name}.
    Thank them and ask for their 10-digit mobile number.
    Mention we'll send an OTP for verification.
    Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "OTP": """We've sent an OTP to the customer's mobile.
    Ask them to enter the 6-digit verification code.
    Mention it should arrive within seconds.
    Use 1 emoji. Keep it 2 sentences.""",
    
    "INCOME": """The customer's mobile is now verified! 📱✅
    Now we need to understand their financial profile.
    Ask for their monthly income (salary or business income).
    Give examples like "50,000" or "50k" or "5 lakhs per year".
    Mention this helps us calculate the best loan offer.
    Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "EXISTING_EMI": """The customer earns ₹{monthly_income_formatted} per month.
    Now ask if they have any existing loans or EMIs they're paying.
    If yes, ask for the total monthly EMI amount.
    If no existing loans, they can say "0" or "none".
    This helps us understand their repayment capacity.
    Use 1-2 emojis. Keep it 2-3 sentences.""",
    
    "DOB": """We're building their financial profile!
    Now ask for their age or date of birth.
    They can provide just their age (e.g., "32") or full DOB (e.g., "15/06/1992").
    Mention age is required for loan eligibility criteria.
    Use 1 emoji. Keep it 2-3 sentences.""",
    
    "KYC": """The customer's financial profile is captured.
    Now ask for their 10-character PAN number (format: ABCDE1234F).
    Mention it's for identity verification and final eligibility check.
    Use 1 emoji. Keep it 2-3 sentences.""",
    
    "OFFER_DISCUSSION": """Great news! Based on the customer's profile:
    - Monthly Income: ₹{monthly_income_formatted}
    - Credit Score: {credit_score} (calculated from financial profile)
    - Pre-approved Limit: ₹{pre_approved_limit_formatted}
    - Interest Rate: {interest_min}% - {interest_max}% per annum
    
    Share this exciting news enthusiastically!
    DO NOT mention the exact credit score number to the customer.
    Ask if they want to proceed with the loan.
    Use 2-3 emojis to celebrate. Keep it 4-5 sentences.""",
    
    "TENURE_SELECTION": """The customer accepted the offer. Now present EMI options:
    {emi_options_text}
    Ask them to choose their preferred tenure (12, 24, 36, or 48 months).
    Be helpful and clear. Use 1-2 emojis. Keep it concise.""",
    
    "UNDERWRITING": """The customer's application is being processed by our underwriting team.
    Let them know to hang tight while we verify details (takes about 8-10 seconds).
    Do NOT ask them to type anything. Just say you are checking.
    Be reassuring. Use 1 emoji. Keep it 2 sentences.""",
    
    "SANCTION": """CONGRATULATIONS! The loan is APPROVED!
    Customer: {user_name}
    Loan Amount: ₹{loan_amount_formatted}
    Interest Rate: {interest_rate}% per annum
    Tenure: {tenure} months
    Monthly EMI: ₹{emi_formatted}
    
    Share this wonderful news with lots of enthusiasm!
    Mention the sanction letter is ready for download.
    Welcome them to Tata Capital family.
    Use 3-4 celebration emojis. Keep it 5-6 sentences.""",
    
    "REJECTION": """Unfortunately, we couldn't approve the loan for {user_name}.
    Express genuine empathy and apologize.
    Mention they can reapply after 6 months.
    Provide helpline number: 1800-XXX-XXXX.
    Be compassionate. Use 1 emoji (sad). Keep it 3-4 sentences."""
}


async def generate_gemini_response(stage: str, session_data: dict) -> Optional[str]:
    """
    Generate a dynamic response using Google Gemini AI.
    
    This function:
    1. Gets the stage-specific prompt template
    2. Fills in context data (names, amounts, etc.)
    3. Sends to Gemini for natural language generation
    4. Returns the AI-generated response
    
    Falls back to None if Gemini fails (hardcoded backup will be used).
    """
    global gemini_model
    
    if not gemini_model:
        return None
    
    try:
        # Get prompt template for this stage
        prompt_template = STAGE_PROMPTS.get(stage)
        if not prompt_template:
            return None
        
        # Build context for prompt
        context = {
            "user_name": session_data.get("user_name", ""),
            "loan_purpose": (session_data.get("loan_purpose") or "personal").replace('_', ' ').title(),
            "loan_amount": session_data.get("loan_amount") or 0,
            "loan_amount_formatted": format_indian_currency(session_data.get("loan_amount") or 0),
            "city": session_data.get("city") or "",
            "employment_type": session_data.get("employment_type") or "",
            "pre_approved_limit": session_data.get("pre_approved_limit") or 0,
            "pre_approved_limit_formatted": format_indian_currency(session_data.get("pre_approved_limit") or 0),
            "interest_min": session_data.get("interest_rate_min") or 10.5,
            "interest_max": session_data.get("interest_rate_max") or 18.0,
            "interest_rate": session_data.get("final_interest_rate") or 12.0,
            "tenure": session_data.get("selected_tenure") or 24,
            "emi": session_data.get("calculated_emi") or 0,
            "emi_formatted": format_indian_currency(session_data.get("calculated_emi") or 0),
        }
        
        # Build EMI options text for tenure selection
        emi_options = session_data.get("emi_options") or {}
        emi_text_parts = []
        for months in [12, 24, 36, 48]:
            option = emi_options.get(months, {})
            emi = option.get("emi", 0) if isinstance(option, dict) else 0
            if emi and emi > 0:
                emi_text_parts.append(f"{months} months: ₹{format_indian_currency(emi)}/month")
        context["emi_options_text"] = "\n".join(emi_text_parts) if emi_text_parts else "Multiple tenure options available"
        
        # Fill in the prompt template
        try:
            prompt = prompt_template.format(**context)
        except KeyError:
            # If any key is missing, use template as-is
            prompt = prompt_template
        
        # System instruction for consistent tone
        system_instruction = """You are a professional loan assistant at Tata Capital, India's leading NBFC.
        Your tone is: warm, helpful, professional, and slightly enthusiastic.
        You speak like a friendly bank officer who genuinely wants to help.
        Always use proper Indian English (e.g., "lakhs" not "lacs", "₹" for rupees).
        Never make up information - only use what's provided.
        Keep responses concise but warm."""
        
        # Generate response
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: gemini_model.generate_content(
                f"{system_instruction}\n\n{prompt}",
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=300,
                )
            )
        )
        
        if response and response.text:
            print(f"✨ Gemini generated response for stage: {stage}")
            return response.text.strip()
        
        return None
        
    except Exception as e:
        print(f"⚠️ Gemini generation failed for {stage}: {e}")
        return None


def generate_deterministic_response_hardcoded(stage: str, session_data: dict) -> str:
    """
    Generate bot response based on CURRENT STAGE.
    
    Uses LAZY EVALUATION to avoid format errors when values are None.
    Tone: Professional yet warm and personal - like a helpful bank officer.
    """
    user_name = session_data.get("user_name", "")
    name_part = f", {user_name}" if user_name else ""
    
    # Safe defaults
    loan_purpose = session_data.get("loan_purpose") or "personal"
    loan_amount = session_data.get("loan_amount") or 0
    city = session_data.get("city") or ""
    employment = session_data.get("employment_type") or ""
    
    if stage == "GREETING":
        return "Hi there! 👋 Welcome to Tata Capital.\n\nI'm here to help you get a personal loan quickly and hassle-free. Are you looking for a loan today?"
    
    elif stage == "PURPOSE":
        return "Wonderful! 😊 I'd love to help you out.\n\nCould you tell me what you need the loan for? It could be home renovation, education, medical expenses, a wedding, travel, or anything else!"
    
    elif stage == "AMOUNT":
        purpose_display = loan_purpose.replace('_', ' ').title()
        return f"Perfect choice - {purpose_display}! 👍\n\nHow much are you looking to borrow? Just give me an amount (e.g., 5 lakhs or 500000)."
    
    elif stage == "CITY":
        if loan_amount and loan_amount > 0:
            return f"Got it! ₹{format_indian_currency(loan_amount)} - I've noted that down ✅\n\nWhich city do you currently reside in? This helps us check branch availability near you."
        return "Which city do you currently live in?"
    
    elif stage == "EMPLOYMENT_TYPE":
        return f"Great, {city} is well-covered! 📍\n\nOne quick question - are you salaried or self-employed? This helps us find the best rates for you."
    
    elif stage == "NAME":
        return "Excellent! Now, may I have your full name exactly as it appears on your PAN card? This is important for verification. 📝"
    
    elif stage == "MOBILE":
        return f"Thank you{name_part}! 😊\n\nPlease share your 10-digit mobile number. We'll send a quick OTP to verify - takes just a few seconds!"
    
    elif stage == "OTP":
        return "📱 OTP sent to your mobile!\n\nPlease check your messages and enter the 6-digit verification code. It should arrive within a few seconds."
    
    elif stage == "INCOME":
        return f"Wonderful! Your mobile number is verified ✅\n\nNow, let's understand your financial profile. What is your monthly income (take-home salary or business income)?\n\nYou can type it as \"50000\" or \"50k\" or \"5 lakhs per year\" 💰"
    
    elif stage == "EXISTING_EMI":
        monthly_income = session_data.get("monthly_income") or 0
        return f"Got it! ₹{format_indian_currency(monthly_income)} per month ✅\n\nDo you have any existing loans or EMIs you're currently paying? If yes, please tell me the total monthly EMI amount.\n\nIf you don't have any existing loans, just type \"0\" or \"none\" 📊"
    
    elif stage == "DOB":
        return "Almost there! 🎂\n\nWhat is your age? You can simply type your age (e.g., \"32\") or your date of birth (e.g., \"15/06/1992\").\n\nThis helps us verify eligibility criteria."
    
    elif stage == "KYC":
        return f"Wonderful! Your financial profile is complete ✅\n\nNow I need your PAN number for identity verification. Please enter your 10-character PAN (e.g., ABCDE1234F)."
    
    elif stage == "OFFER_DISCUSSION":
        return _generate_offer_response(session_data)
    
    elif stage == "TENURE_SELECTION":
        return _generate_tenure_response(session_data)
    
    elif stage == "UNDERWRITING":
        return f"Your application is being processed... ⏳\n\nOur underwriting team is reviewing your profile. This usually takes just a moment - hang tight!"

    elif stage == "SANCTION":
        return _generate_sanction_response(session_data)
    
    elif stage == "REJECTION":
        return f"I'm really sorry{name_part} 😔\n\nUnfortunately, we couldn't approve your loan application at this time based on our eligibility criteria.\n\nYou're welcome to reapply after 6 months. If you have questions, please call us at 1800-XXX-XXXX - we're here to help!"
    else:
        return "Processing..."


def _generate_offer_response(session_data: dict) -> str:
    """Generate OFFER stage response with interest RANGE and credit assessment."""
    user_name = session_data.get("user_name", "")
    name_part = f", {user_name}" if user_name else ""
    
    pre_approved = session_data.get("pre_approved_limit") or 0
    interest_min = session_data.get("interest_rate_min") or 10.5
    interest_max = session_data.get("interest_rate_max") or 18.0
    credit_score = session_data.get("credit_score") or 0
    monthly_income = session_data.get("monthly_income") or 0
    
    # Determine credit rating description (never show actual score)
    if credit_score >= 800:
        credit_status = "Excellent credit profile! 🌟"
    elif credit_score >= 750:
        credit_status = "Very good credit profile! ✨"
    elif credit_score >= 700:
        credit_status = "Good credit profile! 👍"
    else:
        credit_status = "Your profile has been assessed."
    
    return f"""🎉 Fantastic news{name_part}!

Based on your financial profile:
📊 Monthly Income: ₹{format_indian_currency(monthly_income)}
✅ {credit_status}

You're pre-approved for up to ₹{format_indian_currency(pre_approved)}! 🎊

📈 Interest Rate Range: {interest_min}% - {interest_max}% per annum
(Final rate will be determined based on your complete profile)

Would you like to proceed with your application? Just say "yes" and we'll move to the next step!"""


def _generate_tenure_response(session_data: dict) -> str:
    """Generate TENURE selection response with EMI options."""
    emi_options = session_data.get("emi_options") or {}
    
    response = "Great! Now let's choose a repayment plan that works for you 📅\n\nHere are your EMI options:\n\n"
    for months in [12, 24, 36, 48]:
        option = emi_options.get(months, {}) if emi_options else {}
        emi = option.get("emi", 0) if isinstance(option, dict) else 0
        if emi and emi > 0:
            response += f"📌 {months} months → ₹{format_indian_currency(emi)}/month\n"
        else:
            response += f"📌 {months} months\n"
    
    response += "\nJust type your preferred tenure (e.g., \"24 months\") and we'll finalize your loan!"
    
    return response


def _generate_sanction_response(session_data: dict) -> str:
    """Generate SANCTION response with final loan details."""
    user_name = session_data.get("user_name", "")
    name_part = f", {user_name}" if user_name else ""
    
    amount = session_data.get("pre_approved_limit") or 0
    rate = session_data.get("final_interest_rate") or 12.0
    tenure = session_data.get("selected_tenure") or 24
    emi = session_data.get("calculated_emi") or 0
    
    return f"""🎊🎉 CONGRATULATIONS{name_part}! Your loan is APPROVED! 🎉🎊

Here are your final loan details:

💰 Loan Amount: ₹{format_indian_currency(amount)}
📈 Interest Rate: {rate}% per annum
📅 Tenure: {tenure} months
💳 Monthly EMI: ₹{format_indian_currency(emi)}

Your official sanction letter is ready for download below! 👇

Welcome to the Tata Capital family - we're honored to be part of your journey! 🙏"""


async def generate_deterministic_response(stage: str, session_data: dict) -> str:
    """
    MAIN RESPONSE GENERATOR - Tries Gemini first, falls back to hardcoded.
    
    Strategy:
    1. If Gemini is available and enabled → Generate dynamic AI response
    2. If Gemini fails or is disabled → Use hardcoded response (backup)
    
    This ensures:
    - Natural, varied responses when AI is available
    - Reliable fallback when AI is unavailable
    - No service interruption regardless of AI status
    """
    # Try Gemini first if available
    if gemini_model and USE_GEMINI:
        try:
            gemini_response = await generate_gemini_response(stage, session_data)
            if gemini_response:
                return gemini_response
        except Exception as e:
            print(f"⚠️ Gemini fallback triggered: {e}")
    
    # Fallback to hardcoded response
    return generate_deterministic_response_hardcoded(stage, session_data)


# ==================== MAIN ENDPOINTS ====================

@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "TataSmartAgent",
        "version": "3.0.0",
        "status": "online",
        "flow": "deterministic_13_stage",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "flow_controller": "deterministic_v4",
        "stages": 16,
        "features": ["dynamic_credit_scoring", "user_provided_income", "gemini_ai"],
        "admin_connections": len(admin_connections),
        "gemini_enabled": gemini_model is not None and USE_GEMINI,
        "gemini_model": "gemini-2.0-flash" if gemini_model else None,
        "timestamp": datetime.now().isoformat()
    }


# ==================== CHAT ENDPOINT (V3) ====================

@app.post("/api/v3/chat", response_model=ChatResponse)
async def deterministic_chat_endpoint(request: ChatRequest):
    """
    DETERMINISTIC 13-STAGE CHAT ENDPOINT
    
    Flow: GREETING → PURPOSE → AMOUNT → CITY → EMPLOYMENT_TYPE → NAME →
          MOBILE → OTP → KYC → OFFER_DISCUSSION → TENURE_SELECTION →
          UNDERWRITING → SANCTION/REJECTION
    
    Rules:
    - Stage advances ONLY when required data is collected
    - Out-of-order input is IGNORED
    - Credit score NEVER exposed
    - EMI calculated ONLY after tenure selection
    """
    try:
        # Process through deterministic flow
        result = deterministic_process_message(
            session_id=request.session_id,
            message=request.message
        )
        
        # Get admin state
        admin_state = get_admin_state(request.session_id)
        
        # Generate bot response (async - uses Gemini with hardcoded fallback)
        current_stage = result.get("current_stage", "GREETING")
        session_data = result.get("session", {})
        bot_response = await generate_deterministic_response(current_stage, session_data)
        
        # Broadcast to admin dashboard
        timestamp = datetime.now().isoformat()
        
        await broadcast_to_admin({
            "type": "user_message",
            "data": {"message": request.message},
            "session_id": request.session_id,
            "timestamp": timestamp
        })
        
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
        
        await broadcast_to_admin({
            "type": "bot_response",
            "data": {"response": bot_response, "stage": current_stage},
            "session_id": request.session_id,
            "timestamp": timestamp
        })
        
        if admin_state:
            await broadcast_to_admin({
                "type": "state_update",
                "data": admin_state,
                "session_id": request.session_id,
                "timestamp": timestamp
            })
        
        # Terminal stage check
        is_terminal = current_stage in ["SANCTION", "REJECTION"]
        
        # Loan details for sanction - match frontend LoanDetails interface
        loan_details = None
        if current_stage == "SANCTION":
            loan_details = {
                "amount": session_data.get("pre_approved_limit") or 0,
                "interest_rate": session_data.get("final_interest_rate") or 0,
                "tenure_months": session_data.get("selected_tenure") or 0,
                "monthly_emi": session_data.get("calculated_emi") or 0
            }
        
        return ChatResponse(
            response=bot_response,
            session_id=request.session_id,
            conversation_stage=current_stage,
            missing_info=[],
            decision=session_data.get("underwriting_result"),
            show_upload=False,  # NO file uploads
            show_sanction_letter=current_stage == "SANCTION",
            loan_details=loan_details,
            customer_name=session_data.get("user_name"),
            session_closed=is_terminal,
            closure_reason=session_data.get("underwriting_result") if is_terminal else None,
            admin_data=admin_state
        )
        
    except Exception as e:
        print(f"❌ Chat error: {e}")
        import traceback
        traceback.print_exc()
        
        await broadcast_to_admin({
            "type": "error",
            "data": {"error": str(e)},
            "session_id": request.session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/api/v3/reset-session")
async def reset_session(request: dict):
    """Reset a session"""
    session_id = request.get("session_id")
    if session_id:
        deterministic_reset_session(session_id)
        return {"status": "success", "message": "Session reset"}
    return {"status": "error", "message": "No session_id provided"}


# ==================== SANCTION LETTER DOWNLOAD ====================

@app.get("/api/download-sanction/{session_id}")
async def download_sanction_letter(session_id: str):
    """Download sanction letter PDF"""
    try:
        state = deterministic_get_session_state(session_id)
        
        if not state:
            raise HTTPException(status_code=404, detail="Session not found")
        
        customer_name = state.get("user_name", "Valued Customer")
        loan_amount = state.get("pre_approved_limit", 500000)
        interest_rate = state.get("final_interest_rate", 12.0)
        tenure = state.get("selected_tenure", 24)
        emi = state.get("calculated_emi", 15000)
        phone = state.get("mobile_number", "")
        pan = state.get("pan_number", "")
        
        pdf_path = generate_sanction_letter(
            customer_name=customer_name,
            loan_amount=int(loan_amount) if loan_amount else 500000,
            interest_rate=float(interest_rate) if interest_rate else 12.0,
            tenure=int(tenure) if tenure else 24,
            emi=int(emi) if emi else 15000,
            phone=phone or "",
            pan=pan or "",
            approval_type="Standard",
            session_id=session_id
        )
        
        filename = f"Tata_Capital_Sanction_Letter_{customer_name.replace(' ', '_')}.pdf"
        
        return FileResponse(
            pdf_path,
            media_type='application/pdf',
            filename=filename
        )
        
    except Exception as e:
        print(f"❌ PDF download error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== ADMIN ENDPOINTS ====================

@app.websocket("/admin/stream")
async def admin_websocket(websocket: WebSocket):
    """WebSocket for admin dashboard"""
    await websocket.accept()
    admin_connections.append(websocket)
    
    await websocket.send_json({
        "type": "connection",
        "message": "Connected to TataSmartAgent Admin Stream (V3)",
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            
            if data == "get_sessions":
                all_sessions = get_all_admin_sessions()
                await websocket.send_json({
                    "type": "sessions_list",
                    "sessions": all_sessions,
                    "count": len(all_sessions)
                })
                
    except WebSocketDisconnect:
        if websocket in admin_connections:
            admin_connections.remove(websocket)


@app.get("/admin/sessions")
async def get_admin_sessions():
    """Get all active sessions for admin dashboard"""
    all_sessions = get_all_admin_sessions()
    
    # Transform sessions to include 'state' wrapper for frontend compatibility
    transformed_sessions = []
    for session in all_sessions:
        transformed_sessions.append({
            "session_id": session.get("session_id"),
            "created_at": session.get("timestamps", {}).get("created_at"),
            "last_activity": session.get("timestamps", {}).get("last_updated"),
            "message_count": 0,  # Not tracking message count
            "state": session  # Wrap the full admin state under 'state' key
        })
    
    return {
        "active_sessions": len(transformed_sessions),
        "sessions": transformed_sessions,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/admin/session/{session_id}")
async def get_admin_session_detail(session_id: str):
    """Get detailed state for a specific session"""
    admin_state = get_admin_state(session_id)
    
    if not admin_state:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "state": admin_state
    }


@app.post("/api/admin-event")
async def receive_admin_event(request: Request):
    """Receive events from ChatWidget and broadcast to Admin"""
    try:
        event_data = await request.json()
        await broadcast_to_admin(event_data)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/admin/reset")
async def reset_all_sessions():
    """Clear all sessions"""
    # Reset the flow controller
    controller = get_flow_controller()
    controller.sessions.clear()
    
    await broadcast_to_admin({
        "type": "system_reset",
        "message": "All sessions cleared",
        "timestamp": datetime.now().isoformat()
    })
    
    return {"message": "All sessions reset", "timestamp": datetime.now().isoformat()}


# ==================== AUTH ====================

@app.post("/api/auth/login")
async def login(credentials: Dict):
    """Admin login"""
    if credentials.get("username") == "admin" and credentials.get("password") == "tata123":
        return {
            "success": True,
            "token": "mock_jwt_token_v3",
            "user": {"username": "admin", "role": "bank_officer", "name": "Admin User"}
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")


# ==================== TEST ENDPOINTS ====================

@app.get("/test/customer/{phone}")
async def test_get_customer(phone: str):
    """Test endpoint to get customer by phone"""
    customer = MockDataProvider.get_customer_by_phone(phone)
    if customer:
        return customer
    raise HTTPException(status_code=404, detail="Customer not found")


@app.get("/admin/customers")
async def get_all_customers():
    """Get all mock customer profiles"""
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


# ==================== ERROR HANDLER ====================

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


# ==================== MAIN ====================
if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║        TataSmartAgent - V3 Deterministic Flow             ║
    ║                                                            ║
    ║  🏦 16-Stage Strict Linear Sequence                       ║
    ║  🔒 Backend Controls ALL Logic                            ║
    ║  📊 Admin Dashboard = Exact Backend State                 ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
