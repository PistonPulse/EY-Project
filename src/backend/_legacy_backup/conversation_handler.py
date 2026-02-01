"""
================================================================================
PHASE 1 + PHASE 2: STAGE-BASED CONVERSATION HANDLER WITH MASTER AGENT
================================================================================

This module handles the conversation flow using:
- Phase 1: Deterministic stage machine (StageRouter)
- Phase 2: Master Agent with specialized Worker Agents

ARCHITECTURE:
============

    ┌─────────────────────────────────────────────────────────────┐
    │                     USER MESSAGE                            │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              STAGE ROUTER (Phase 1)                         │
    │  • Updates current_stage DETERMINISTICALLY                  │
    │  • Extracts data from message (mobile_number, name, amount, OTP)│
    │  • NO LLM involved in routing decisions                     │
    └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
    ┌─────────────────────────────────────────────────────────────┐
    │              MASTER AGENT (Phase 2)                         │
    │  • Reads current_stage (set by StageRouter)                 │
    │  • Maps stage → Worker Agent (DETERMINISTIC)                │
    │  • Delegates response generation to Worker Agent            │
    │  • DOES NOT change current_stage                            │
    └─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
    ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
    │ SALES AGENT │   │ VERIFY AGENT│   │ UW AGENT    │
    │  Friendly   │   │  Formal     │   │ Analytical  │
    └─────────────┘   └─────────────┘   └─────────────┘

WHY THIS ARCHITECTURE:
- Stage transitions are DETERMINISTIC (StageRouter)
- Agent selection is DETERMINISTIC (Master Agent mapping)
- Only response PHRASING uses LLM (Worker Agents)
- Each stage gets a specialized agent with appropriate personality

================================================================================
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from stage_machine import (
    ConversationStage,
    ConversationState,
    StageRouter,
    STAGE_INSTRUCTIONS,
    create_stage_router
)
from backend_services import BackendServices
from master_agent import (
    MasterAgent,
    create_master_agent,
    get_agent_info,
    WorkerAgentType,
    STAGE_TO_AGENT_MAP
)
from agent_prompts import format_indian_currency


# ================================================================================
# LLM RESPONSE GENERATOR
# ================================================================================
# The LLM is ONLY used for generating natural language responses.
# It does NOT decide conversation flow - that's handled by StageRouter.

class ResponseGenerator:
    """
    Generates human-like responses using LLM.
    
    KEY PRINCIPLE: The LLM receives:
    1. The current stage
    2. An instruction describing what to communicate
    3. Context about the customer/conversation
    
    The LLM does NOT:
    - Decide the next stage
    - Perform eligibility logic
    - Modify conversation state
    """
    
    def __init__(self, api_key: str):
        """Initialize the LLM for response generation."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.7,
            convert_system_message_to_human=True
        )
    
    async def generate_response(
        self,
        state: ConversationState,
        stage_instruction: str,
        user_message: str
    ) -> str:
        """
        Generate a natural language response for the current stage.
        
        The LLM is given:
        - The stage instruction (what to communicate)
        - Context about the customer
        - The user's message
        
        It returns ONLY a phrased response, not a flow decision.
        
        Args:
            state: Current conversation state (read-only for LLM)
            stage_instruction: What the LLM should communicate
            user_message: The user's message to respond to
            
        Returns:
            Generated response string
        """
        # Build the system prompt
        system_prompt = f"""You are a friendly and professional loan assistant for Tata Capital.

CURRENT STAGE: {state.current_stage.value}

YOUR TASK:
{stage_instruction}

IMPORTANT RULES:
1. Keep responses conversational and brief (2-4 sentences typically)
2. Be warm and professional - like a helpful bank employee
3. Use Indian English naturally (lakhs, crores, etc.)
4. Address the customer by name if known
5. Do NOT ask for information already collected
6. Do NOT make promises about approval
7. Do NOT decide what happens next - just respond to this stage

CUSTOMER CONTEXT:
- Name: {state.user_name or 'Unknown'}
- Mobile Number: {'XXXXXX' + state.user_mobile_number[-4:] if state.user_mobile_number else 'Not provided'}
- Loan Amount: {format_indian_currency(state.loan_amount) if state.loan_amount else 'Not specified'}
- Credit Score: {state.credit_score or 'Not checked yet'}
- Interest Rate: {str(state.interest_rate) + '% p.a.' if state.interest_rate else 'Not calculated'}
- Monthly EMI: {format_indian_currency(state.emi_amount) if state.emi_amount else 'Not calculated'}
- OTP Status: {'Verified ✓' if state.otp_verified else ('Sent, awaiting verification' if state.otp_sent else 'Not sent')}
- Customer Type: {'Existing Customer' if state.is_existing_customer else 'New Customer'}

Generate a natural, helpful response for this stage."""

        # Include conversation history for context
        messages = [SystemMessage(content=system_prompt)]
        
        # Add recent conversation history (last 3 exchanges)
        for msg in state.conversation_history[-6:]:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg["content"]))
        
        # Add current user message
        messages.append(HumanMessage(content=user_message))
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            print(f"❌ LLM Error: {e}")
            # Return a fallback response based on stage
            return self._get_fallback_response(state)
    
    def _get_fallback_response(self, state: ConversationState) -> str:
        """
        Get a fallback response if LLM fails.
        These are simple, safe responses for each stage.
        """
        fallbacks = {
            ConversationStage.GREETING: "Welcome to Tata Capital! I'm here to help you with your loan needs. How can I assist you today?",
            
            ConversationStage.NEEDS_ANALYSIS: "I'd be happy to help you with a loan. Could you tell me how much you're looking to borrow?",
            
            ConversationStage.KYC_COLLECTION: "Great! To check your eligibility, I'll need your mobile number for verification. Could you please share your 10-digit mobile number?",
            
            ConversationStage.KYC_VERIFICATION: f"I've sent an OTP to your mobile number. Please enter the 6-digit code to verify. (For testing, OTP is: {state.otp_code})" if state.otp_code else "Please enter the OTP sent to your mobile number.",
            
            ConversationStage.OFFER_CHECK: "Let me check what offers are available for you...",
            
            ConversationStage.CREDIT_CHECK: f"Based on your profile, you qualify for a loan at {state.interest_rate}% p.a. with an EMI of {format_indian_currency(state.emi_amount)}. Would you like to proceed?" if state.interest_rate else "Let me calculate your loan offer...",
            
            ConversationStage.INCOME_DOC_UPLOAD: "To finalize your loan, please upload your salary slip or income proof using the upload button below.",
            
            ConversationStage.UNDERWRITING_DECISION: "I'm reviewing your documents. This will just take a moment...",
            
            ConversationStage.SANCTION: f"Congratulations! Your loan of {format_indian_currency(state.loan_amount)} has been approved! You can download your sanction letter now.",
            
            ConversationStage.REJECTION: f"I'm sorry, but we're unable to approve your loan at this time. {state.rejection_reason or 'Please contact our support team for more details.'}",
        }
        
        return fallbacks.get(state.current_stage, "I'm here to help. How can I assist you?")


# ================================================================================
# MAIN CONVERSATION HANDLER (PHASE 1 + PHASE 2)
# ================================================================================
# This is the entry point for processing user messages.
# It combines:
# - Phase 1: Deterministic stage routing (StageRouter)
# - Phase 2: Specialized agent responses (Master Agent + Worker Agents)

class StageBasedConversationHandler:
    """
    Main handler that orchestrates stage routing and Master Agent responses.
    
    FLOW FOR EVERY MESSAGE:
    ========================
    1. StageRouter.route() - Updates state DETERMINISTICALLY (Phase 1)
    2. MasterAgent.orchestrate() - Selects Worker Agent and generates response (Phase 2)
    3. Return response and updated state
    
    WHY THIS SEPARATION:
    ====================
    - StageRouter: Controls WHAT HAPPENS (flow control) - DETERMINISTIC
    - MasterAgent: Controls WHO RESPONDS (agent selection) - DETERMINISTIC
    - WorkerAgent: Controls HOW IT'S SAID (phrasing) - LLM-POWERED
    
    This ensures:
    - No LLM-based flow decisions
    - Predictable conversation progression
    - Natural, personality-driven responses
    """
    
    def __init__(self, gemini_api_key: str, data_provider=None):
        """
        Initialize the conversation handler with Phase 1 + Phase 2 + Phase 3 components.
        
        Args:
            gemini_api_key: API key for Gemini LLM
            data_provider: Optional provider for customer data lookups (legacy)
            
        PHASE 3 INTEGRATION:
        - BackendServices initialized for real dataset lookups
        - All customer data comes from CUSTOMER_PROFILES, NOT LLM invention
        """
        # Phase 3: Backend Services for real dataset lookups
        self.backend_services = BackendServices()
        
        # Phase 1: Deterministic Stage Router (with Phase 3 backend services)
        self.router = create_stage_router(data_provider, self.backend_services)
        
        # Phase 2: Master Agent with Worker Agents
        self.master_agent = create_master_agent()
        
        # Legacy: Keep response generator for backward compatibility
        self.response_generator = ResponseGenerator(gemini_api_key)
        
        self.data_provider = data_provider
        
        # Session storage (in production, use Redis or database)
        self.sessions: Dict[str, ConversationState] = {}
        
        print("\n" + "="*60)
        print("🏦 TATA CAPITAL - CONVERSATION SYSTEM (Phase 1 + 2 + 3)")
        print("="*60)
        print("📍 Phase 1: Deterministic Stage Control (StageRouter)")
        print("🎯 Phase 2: Master Agent Orchestration")
        print("👥 Worker Agents: Sales, Verification, Underwriting, Sanction")
        print("🔗 Phase 3: Backend Services (CRM, Offers, Credit Bureau)")
        print("="*60 + "\n")
    
    def get_or_create_session(self, session_id: str) -> ConversationState:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            ConversationState for the session
        """
        if session_id not in self.sessions:
            state = ConversationState()
            state.session_id = session_id  # PHASE 7: Store session ID for file naming
            self.sessions[session_id] = state
            print(f"📝 New session created: {session_id}")
        return self.sessions[session_id]
    
    def save_session(self, session_id: str, state: ConversationState):
        """Save session state."""
        self.sessions[session_id] = state
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        document_uploaded: bool = False,
        uploaded_doc_type: Optional[str] = None,
        has_uploaded_docs: bool = False,
        documents_verified: bool = False,
        acquisition_source: Optional[str] = None  # PHASE 8: "AD" or "EMAIL"
    ) -> Dict[str, Any]:
        """
        Process a user message through the stage machine.
        
        This is the MAIN ENTRY POINT for handling user messages.
        
        Steps:
        1. Get/create session state
        2. Handle document upload if applicable
        3. Route through stage machine (DETERMINISTIC)
        4. Generate LLM response (PHRASING ONLY)
        5. Update state with response
        6. Return response with UI flags
        
        Args:
            session_id: Session identifier
            user_message: User's message
            document_uploaded: Whether a document was just uploaded (legacy)
            uploaded_doc_type: Type of document uploaded
            has_uploaded_docs: Whether documents were uploaded (new flag from chat)
            documents_verified: Whether documents were verified
            acquisition_source: PHASE 8 - How customer arrived ("AD", "EMAIL", or None)
            
        Returns:
            Dict with response, state, and UI control flags
        """
        # Step 1: Get session state
        state = self.get_or_create_session(session_id)
        previous_stage = state.current_stage
        
        # PHASE 8: Store acquisition source if provided (only on first message)
        if acquisition_source and not state.acquisition_source:
            state.acquisition_source = acquisition_source
            print(f"📢 PHASE 8: Acquisition source set to '{acquisition_source}'")
        
        print(f"\n{'='*60}")
        print(f"🚀 PROCESSING MESSAGE")
        print(f"   Session: {session_id}")
        print(f"   Stage: {state.current_stage.value}")
        print(f"   Acquisition: {state.acquisition_source or 'DIRECT'}")
        print(f"   Message: {user_message[:50]}...")
        print(f"{'='*60}")
        
        # Step 2: Handle document upload flags
        if document_uploaded or has_uploaded_docs:
            state.documents_uploaded.append(uploaded_doc_type or "salary_slip")
            print(f"📄 Document uploaded: {uploaded_doc_type or 'salary_slip'}")
        
        if documents_verified:
            state.documents_verified = True
            print(f"✅ Documents verified")
        
        # ================================================================
        # PHASE 1: Route through stage machine (DETERMINISTIC)
        # ================================================================
        # This is where flow control happens - NO LLM INVOLVED
        # The StageRouter:
        # - Reads the user message
        # - Extracts relevant data (mobile_number, name, loan amount, OTP)
        # - Updates current_stage based on DETERMINISTIC rules
        # ================================================================
        state = self.router.route(state, user_message)
        
        new_stage = state.current_stage
        stage_changed = previous_stage != new_stage
        
        if stage_changed:
            print(f"✅ STAGE CHANGED: {previous_stage.value} → {new_stage.value}")
        else:
            print(f"⏸️ STAGE UNCHANGED: {new_stage.value}")
        
        # ================================================================
        # PHASE 2: Master Agent orchestration
        # ================================================================
        # The Master Agent:
        # 1. Reads current_stage (set by StageRouter above)
        # 2. Maps stage → Worker Agent (DETERMINISTIC)
        # 3. Delegates response generation to Worker Agent
        # 
        # CRITICAL: Master Agent NEVER changes current_stage
        # ================================================================
        
        # Get agent info for logging/admin
        agent_info = get_agent_info(new_stage)
        print(f"🎯 Delegating to: {agent_info['agent_name']}")
        
        # Master Agent orchestrates the response
        orchestration_result = await self.master_agent.orchestrate(
            state=state,
            user_message=user_message
        )
        
        response = orchestration_result["response"]
        active_agent = orchestration_result["agent_type"]
        
        # Add OTP to response if in verification stage and OTP just sent
        if state.current_stage == ConversationStage.KYC_VERIFICATION and state.otp_sent and not state.otp_verified:
            if state.otp_code and state.otp_code not in response:
                # Append OTP for demo purposes
                response += f"\n\n📱 Your OTP: **{state.otp_code}** (valid for 5 minutes)"
        
        # Step 6: Add response to conversation history
        state.conversation_history.append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "agent": active_agent  # Track which agent responded
        })
        
        # Step 7: Save session
        self.save_session(session_id, state)
        
        # Step 8: Prepare UI control flags
        show_upload = state.current_stage == ConversationStage.INCOME_DOC_UPLOAD
        
        # PHASE 5: Show sanction letter download button only if approved and letter generated
        show_sanction_letter = (
            state.current_stage == ConversationStage.SANCTION and 
            state.sanction_letter_generated
        )
        
        # Prepare loan details if sanctioned (PHASE 5: Use calculated values)
        loan_details = None
        if state.current_stage == ConversationStage.SANCTION:
            loan_details = {
                "amount": state.loan_amount,
                "interest_rate": state.effective_interest_rate or state.interest_rate,
                "emi": state.calculated_emi or state.emi_amount,
                "tenure_months": state.loan_tenure_months,
                "customer_name": state.user_name,
                "approval_type": state.approval_type,
                "reference_number": state.sanction_reference_number,
                "validity_date": state.sanction_validity_date,
            }
        
        # PHASE 5: Include session closure status
        session_closed = state.session_closed
        closure_reason = state.closure_reason
        
        return {
            "response": response,
            "current_stage": state.current_stage.value,
            "previous_stage": previous_stage.value,
            "stage_changed": stage_changed,
            "active_agent": active_agent,  # NEW: Which worker agent responded
            "agent_info": agent_info,       # NEW: Agent metadata for admin
            "show_upload": show_upload,
            "show_sanction_letter": show_sanction_letter,
            "loan_details": loan_details,
            # PHASE 5: Session closure
            "session_closed": session_closed,
            "closure_reason": closure_reason,
            "state_summary": {
                "user_name": state.user_name,
                "user_mobile_number": state.user_mobile_number[-4:] if state.user_mobile_number else None,
                "user_phone": state.user_mobile_number[-4:] if state.user_mobile_number else None,  # DEPRECATED alias
                "loan_amount": state.loan_amount,
                "otp_verified": state.otp_verified,
                "otp_verification_timestamp": state.otp_verification_timestamp,  # Admin visibility
                "credit_score": state.credit_score,
                "interest_rate": state.effective_interest_rate or state.interest_rate,
                "emi_amount": state.calculated_emi or state.emi_amount,
                # PHASE 5: Decision status
                "loan_status": state.loan_status,
                "approval_type": state.approval_type,
                "rejection_reason": state.rejection_reason,
                # PHASE 8: Acquisition source for admin dashboard
                "acquisition_source": state.acquisition_source,
            }
        }
    
    def mark_documents_verified(self, session_id: str, verified: bool = True):
        """
        Mark documents as verified (called after document processing).
        
        Args:
            session_id: Session identifier
            verified: Whether documents are verified
        """
        if session_id in self.sessions:
            self.sessions[session_id].documents_verified = verified
            print(f"📄 Documents marked as {'verified' if verified else 'not verified'}")
    
    def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current session state for debugging/admin.
        
        Args:
            session_id: Session identifier
            
        Returns:
            State dictionary or None if not found
        """
        if session_id in self.sessions:
            return self.sessions[session_id].to_dict()
        return None
    
    def reset_session(self, session_id: str):
        """
        Reset a session to start over.
        
        Args:
            session_id: Session identifier
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"🔄 Session reset: {session_id}")


# ================================================================================
# FACTORY FUNCTION
# ================================================================================

def create_conversation_handler(data_provider=None) -> StageBasedConversationHandler:
    """
    Create a stage-based conversation handler.
    
    Args:
        data_provider: Optional data provider for customer lookups
        
    Returns:
        Configured StageBasedConversationHandler
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    
    return StageBasedConversationHandler(api_key, data_provider)


# ================================================================================
# TESTING
# ================================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_conversation():
        """Test the stage-based conversation flow."""
        handler = create_conversation_handler()
        session_id = "test_session_001"
        
        # Simulate a conversation
        messages = [
            "Hi there!",
            "I need a loan of 5 lakhs",
            "My name is Rahul and mobile number is 9876543210",
            "123456",  # OTP
            "Yes, proceed",
        ]
        
        for msg in messages:
            print(f"\n{'='*60}")
            print(f"👤 USER: {msg}")
            print(f"{'='*60}")
            
            result = await handler.process_message(session_id, msg)
            
            print(f"\n🤖 BOT: {result['response']}")
            print(f"\n📊 Stage: {result['previous_stage']} → {result['current_stage']}")
            print(f"   Changed: {result['stage_changed']}")
    
    # Run test
    asyncio.run(test_conversation())
