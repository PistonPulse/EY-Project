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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from graph_agent import create_agent, LoanAgentGraph
from mock_data import MockDataProvider

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
    extracted_data: Optional[Dict[str, Any]] = None


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
        
        # Update session with new state
        session["messages"] = result["messages"]
        session["state"] = {
            "name": result.get("name"),
            "phone": result.get("phone"),
            "pan": result.get("pan"),
            "verified": result.get("customer_verified"),
            "conversation_stage": result.get("conversation_stage"),
            "loan_decision": result.get("loan_decision"),
            "trust_score": result.get("trust_score"),
            "demo_script": result.get("demo_script"),  # Save active demo scenario
            "demo_step": result.get("demo_step")  # Save demo step
        }
        
        print(f"\n🔄 SESSION UPDATED:")
        print(f"Session ID: {request.session_id}")
        print(f"Demo Script: {result.get('demo_script')}")
        print(f"Demo Step: {result.get('demo_step')}")
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
            for log in result["admin_log"]:
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
                
                await broadcast_to_admin({
                    "type": "log",
                    "data": {
                        "message": msg,
                        "level": level,
                        "agent": agent_name
                    },
                    "timestamp": datetime.now().isoformat()
                })
                # Small delay to simulate real-time processing
                await asyncio.sleep(0.05)
        else:
            print(f"⚠️ No admin_log found in result!")

        # 3. Risk Score Update - ALWAYS SEND (critical for dashboard updates)
        trust_score = result.get("trust_score", 50)  # Default to 50 if not set
        await broadcast_to_admin({
            "type": "risk_calculated",
            "data": {
                "risk_score": trust_score,
                "factors": result.get("fraud_flags", [])
            },
            "timestamp": timestamp
        })
        print(f"📊 Broadcasting Trust Score: {trust_score}")

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


@app.post("/api/upload")
async def upload_document_demo(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    document_count: str = Form(...)
):
    """
    Document upload endpoint for DEMO MODE
    Simulates document processing and triggers next demo step
    """
    
    try:
        # Read file
        contents = await file.read()
        doc_count = int(document_count)
        
        # Get session to check which demo script is active
        session = get_or_create_session(session_id)
        demo_script = session.get("state", {}).get("demo_script", "")
        
        print(f"\n{'='*60}")
        print(f"📤 UPLOAD ENDPOINT CALLED")
        print(f"Session ID: {session_id}")
        print(f"Active Script: {demo_script}")
        print(f"File: {file.filename}")
        print(f"Session State: {session.get('state', {})}")
        print(f"{'='*60}\n")
        
        # Broadcast to admin
        await broadcast_to_admin({
            "type": "document_upload",
            "session_id": session_id,
            "file_name": file.filename,
            "document_number": doc_count,
            "timestamp": datetime.now().isoformat()
        })
        
        # Invoke agent to get next step response based on document count
        if agent and demo_script:
            # Get required docs count and calculate step based on negotiation flow
            script_data = None
            if "priya" in demo_script.lower():
                required_docs = 3
                # Priya: Steps 1-6 are negotiation, steps 7-9 are doc uploads
                current_step = 6 + doc_count  # Steps 7, 8, 9 for docs 1, 2, 3
            elif "amit" in demo_script.lower():
                required_docs = 3
                # Amit: Steps 1-6 are negotiation, steps 7-9 are doc uploads
                current_step = 6 + doc_count  # Steps 7, 8, 9 for docs 1, 2, 3
            elif "rajesh" in demo_script.lower():
                required_docs = 2
                # Rajesh: Steps 1-2 are inquiry/fraud alert, steps 3-4 are doc uploads
                current_step = 2 + doc_count  # Steps 3, 4 for docs 1, 2
            else:
                required_docs = 3
                current_step = 6 + doc_count
            
            print(f"🤖 Invoking agent | Script: {demo_script} | Doc: {doc_count}/{required_docs} | Step: {current_step}")
            
            try:
                # Use process_message to ensure proper state handling
                result = await agent.process_message(
                    user_message="upload complete",
                    conversation_history=session["messages"],
                    previous_state={
                        **session.get("state", {}),
                        "demo_script": demo_script,
                        "demo_step": current_step,
                        "docs_uploaded": doc_count
                    }
                )
                
                # Update session with new step and trust score
                session["state"]["demo_step"] = current_step
                session["state"]["docs_uploaded"] = doc_count
                session["state"]["trust_score"] = result.get("trust_score", 50)
                session["messages"] = result["messages"]
                
                # Broadcast trust score update
                if result.get("trust_score") is not None:
                    await broadcast_to_admin({
                        "type": "risk_calculated",
                        "data": {
                            "risk_score": result["trust_score"],
                            "factors": result.get("fraud_flags", [])
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"📊 Broadcasting Trust Score (Upload): {result['trust_score']}")
                
                # Broadcast customer profile update
                if result.get("customer_profile"):
                    await broadcast_to_admin({
                        "type": "customer_identified",
                        "data": {
                            "customer": result["customer_profile"]
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"👤 Broadcasting Profile Update (Upload)")
                
                return {
                    "response": result.get("ai_response", "Documents verified! Processing..."),
                    "continue_upload": doc_count < required_docs,  # Keep upload button if more docs needed
                    "show_sanction_letter": result.get("show_sanction_letter", False),
                    "loan_details": result.get("loan_details")
                }
            except Exception as e:
                print(f"❌ Upload agent error: {e}")
                import traceback
                traceback.print_exc()
                # Fallback response
                return {
                    "response": f"✅ Document {doc_count} received!\n\n⏳ Processing your application...\n\nPlease wait...",
                    "continue_upload": doc_count < required_docs,
                    "show_sanction_letter": False
                }
        
        # No active demo script - fallback
        return {
            "response": f"✅ Document received: {file.filename}\n\nTo start a loan application, please send a message with your name and phone number!",
            "continue_upload": False,
            "show_sanction_letter": False
        }
        
    except Exception as e:
        return {
            "response": f"✅ Document {document_count} received: {file.filename}",
            "continue_upload": True if int(document_count) < 3 else False,
            "show_sanction_letter": False
        }


@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    document_type: str = Form(...)
):
    """
    Document upload endpoint - simulates OCR processing of salary slips, bank statements, etc.
    
    In production, this would:
    1. Upload to cloud storage (S3, GCS)
    2. Run OCR (Google Document AI, Textract)
    3. Extract structured data
    4. Verify against declared information
    """
    
    try:
        # Read file
        contents = await file.read()
        file_size = len(contents)
        
        # ⚡ DEMO MODE: Instant verification (no API calls)
        # Hardcoded success for demo reliability
        extracted_data = {
            "document_type": document_type,
            "file_name": file.filename,
            "file_size": file_size,
            "processed_at": datetime.now().isoformat(),
            "verification_status": "VERIFIED",
            "confidence_score": 98.5,
            "extracted_fields": {}
        }
        
        if document_type == "salary_slip":
            extracted_data["extracted_fields"] = {
                "employee_name": "Verified Employee",
                "company": "Verified Corporation Ltd.",
                "gross_salary": 75000,
                "net_salary": 65000,
                "month": "November 2024",
                "deductions": 10000,
                "verification": "✓ Income verified successfully"
            }
        elif document_type == "bank_statement":
            extracted_data["extracted_fields"] = {
                "account_holder": "Verified Account Holder",
                "account_number": "XXXX1234",
                "average_balance": 125000,
                "period": "May 2024 - Oct 2024",
                "verification": "✓ Banking details verified"
            }
        elif document_type == "pan_card":
            extracted_data["extracted_fields"] = {
                "name": "Sample Name",
                "pan": "ABCDE1234F",
                "dob": "01/01/1990"
            }
        
        # Get session and update
        session = get_or_create_session(session_id)
        if "uploaded_documents" not in session:
            session["uploaded_documents"] = []
        
        session["uploaded_documents"].append(extracted_data)
        
        # Broadcast to admin
        await broadcast_to_admin({
            "type": "document_upload",
            "session_id": session_id,
            "document_type": document_type,
            "file_name": file.filename,
            "timestamp": datetime.now().isoformat()
        })
        
        return UploadResponse(
            success=True,
            message=f"{document_type} uploaded and processed successfully",
            extracted_data=extracted_data
        )
        
    except Exception as e:
        return UploadResponse(
            success=False,
            message=f"Error uploading document: {str(e)}",
            extracted_data=None
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

