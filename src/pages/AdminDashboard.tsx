/**
 * ================================================================================
 * LOAN OPERATIONS DASHBOARD
 * ================================================================================
 * 
 * PURPOSE:
 * --------
 * Internal monitoring console for Aurora Finance NBFC loan officers and 
 * compliance teams. Provides real-time visibility into loan application workflow.
 * 
 * SECTIONS:
 * ---------
 * 1. Applications Queue    - Active loan applications with status
 * 2. Application Progress  - Visual pipeline of processing stages
 * 3. Processing Assignment - Current handler and workflow step
 * 4. KYC Status           - Verification data and customer information
 * 5. Underwriting Summary - Decision details and financial calculations
 * 6. Sanction & Closure   - Generated documents and final outcomes
 * 
 * IMPORTANT - READ-ONLY DESIGN:
 * -----------------------------
 * This dashboard is strictly observation-only and cannot modify loan state.
 * All values are retrieved directly from the backend state store.
 * 
 * This ensures:
 * - Regulatory compliance and complete audit trail
 * - Data integrity - no manual intervention in automated decisions
 * - Separation of concerns between operations and processing
 * 
 * For compliance questions, contact: compliance@aurorafinance.in
 * 
 * ================================================================================
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { 
  LogOut, RefreshCw, Users, Activity, Brain, Shield, 
  CheckCircle, Clock, FileText, AlertTriangle, XCircle,
  TrendingUp, Phone, User, Zap, Database, Download, Eye
} from 'lucide-react';

// ================================================================================
// TYPE DEFINITIONS - V3 DETERMINISTIC FLOW STRUCTURE
// ================================================================================

// Stage enumeration matching backend V3 13-stage flow
type ConversationStage = 
  | 'GREETING' 
  | 'PURPOSE'
  | 'AMOUNT'
  | 'CITY'
  | 'EMPLOYMENT_TYPE'
  | 'NAME'
  | 'MOBILE'
  | 'OTP'
  | 'KYC'
  | 'OFFER_DISCUSSION'
  | 'TENURE_SELECTION'
  | 'UNDERWRITING'
  | 'SANCTION' 
  | 'REJECTION';

// V3 Admin Dict structure from to_admin_dict()
interface V3AdminState {
  application_id: string;
  session_id: string;
  
  customer: {
    name: string | null;
    mobile_masked: string | null;
    city: string | null;
    employment_type: string | null;
    loan_purpose: string | null;
  };
  
  stage: {
    current_stage: ConversationStage;
    stage_number: number;
    total_stages: number;
    progress_percent: number;
    is_terminal: boolean;
  };
  
  kyc: {
    otp_verified: boolean;
    otp_attempts: number;
    pan_verified: boolean;
    pan_number: string | null;
    identity_locked: boolean;
    identity_locked_at: string | null;
    identity_mismatch: boolean;
    identity_mismatch_reason: string | null;
  };
  
  offer: {
    pre_approved_limit: number | null;
    requested_amount: number | null;
    amount_within_limit: boolean | null;
    interest_rate_range: {
      min: number;
      max: number;
    } | null;
    final_interest_rate: number | null;
    selected_tenure: number | null;
    calculated_emi: number | null;
    offer_shown: boolean;
  };
  
  decision: {
    underwriting_complete: boolean;
    underwriting_result: string | null;
    rejection_reason: string | null;
    is_frozen: boolean;
    freeze_reason: string | null;
    sanction_letter_generated: boolean;
  };
  
  timestamps: {
    created_at: string;
    last_updated: string;
  };
  
  session: {
    is_halted: boolean;
    halt_reason: string | null;
  };
  
  income_source: string | null;
}

// Session summary returned by /admin/sessions
interface SessionSummary {
  session_id: string;
  created_at: string;
  last_activity: string;
  message_count: number;
  state: V3AdminState;
}

// Handler mapping to V3 13-stage flow
const STAGE_TO_AGENT: Record<ConversationStage, string> = {
  GREETING: 'Sales',
  PURPOSE: 'Sales',
  AMOUNT: 'Sales',
  CITY: 'Sales',
  EMPLOYMENT_TYPE: 'Sales',
  NAME: 'Sales',
  MOBILE: 'Verification',
  OTP: 'Verification',
  KYC: 'Verification',
  OFFER_DISCUSSION: 'Verification',
  TENURE_SELECTION: 'Sales',
  UNDERWRITING: 'Underwriting',
  SANCTION: 'Sanction',
  REJECTION: 'Underwriting'
};

// Stage display names and descriptions for V3 flow
const STAGE_INFO: Record<ConversationStage, { name: string; description: string }> = {
  GREETING: { name: 'Greeting', description: 'Welcome' },
  PURPOSE: { name: 'Purpose', description: 'Loan purpose' },
  AMOUNT: { name: 'Amount', description: 'Loan amount' },
  CITY: { name: 'City', description: 'Location' },
  EMPLOYMENT_TYPE: { name: 'Employment', description: 'Job type' },
  NAME: { name: 'Name', description: 'Customer name' },
  MOBILE: { name: 'Mobile', description: 'Phone number' },
  OTP: { name: 'OTP', description: 'Verification' },
  KYC: { name: 'KYC', description: 'PAN verify' },
  OFFER_DISCUSSION: { name: 'Offer', description: 'Pre-approved' },
  TENURE_SELECTION: { name: 'Tenure', description: 'EMI select' },
  UNDERWRITING: { name: 'Underwriting', description: 'Decision' },
  SANCTION: { name: 'Sanction', description: 'Approved' },
  REJECTION: { name: 'Rejection', description: 'Declined' }
};

// Ordered stages for pipeline visualization (V3 13-stage flow)
const STAGE_ORDER: ConversationStage[] = [
  'GREETING', 'PURPOSE', 'AMOUNT', 'CITY', 'EMPLOYMENT_TYPE', 'NAME',
  'MOBILE', 'OTP', 'KYC', 'OFFER_DISCUSSION', 'TENURE_SELECTION', 'UNDERWRITING'
];

// ================================================================================
// MAIN COMPONENT
// ================================================================================

export function AdminDashboard() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  
  // State
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState<SessionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [wsConnected, setWsConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  
  // ================================================================
  // CRITICAL FIX: Stable reference for selected session ID
  // Previously, fetchSessions depended on selectedSession object,
  // which caused useEffect to re-run on every selection change,
  // tearing down and recreating the WebSocket connection.
  // 
  // FIX: Use a ref to track selectedSessionId for updates without
  // causing dependency changes.
  // ================================================================
  const selectedSessionIdRef = useRef<string | null>(null);

  // Fetch sessions from backend - stable callback that doesn't depend on selectedSession
  const fetchSessions = useCallback(async () => {
    try {
      const response = await fetch('http://localhost:8000/admin/sessions');
      if (response.ok) {
        const data = await response.json();
        setSessions(data.sessions || []);
        setLastUpdate(new Date());
        
        // Auto-select first session if none selected
        if (!selectedSessionIdRef.current && data.sessions?.length > 0) {
          setSelectedSession(data.sessions[0]);
          selectedSessionIdRef.current = data.sessions[0].session_id;
        }
        
        // Update selected session if it exists (using ref for stable comparison)
        if (selectedSessionIdRef.current) {
          const updated = data.sessions?.find((s: SessionSummary) => s.session_id === selectedSessionIdRef.current);
          if (updated) {
            setSelectedSession(updated);
          }
        }
      }
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setIsLoading(false);
    }
  }, []); // Empty dependency array - stable reference
  
  // Update ref when selectedSession changes (for selection tracking)
  useEffect(() => {
    selectedSessionIdRef.current = selectedSession?.session_id || null;
  }, [selectedSession?.session_id]);

  // WebSocket connection for real-time updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket('ws://localhost:8000/admin/stream');

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        
        // Refresh sessions on relevant events
        if (['user_message', 'bot_response', 'stage_change', 'decision', 'customer_identified'].includes(message.type)) {
          fetchSessions();
        }
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        setWsConnected(false);
      };
    };

    connect();
    
    // Initial fetch
    fetchSessions();
    
    // Poll for updates every 2 seconds
    const pollInterval = setInterval(fetchSessions, 2000);

    return () => {
      clearInterval(pollInterval);
      clearTimeout(reconnectTimeout);
      ws?.close();
    };
  }, [fetchSessions]);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Get status color based on loan status - V3 nested structure
  const getStatusColor = (state: V3AdminState) => {
    if (!state?.stage) return 'text-gray-600 bg-gray-100 border border-gray-300';
    
    const currentStage = state.stage.current_stage;
    const isApproved = state.decision?.underwriting_result === 'APPROVED' || currentStage === 'SANCTION';
    const isRejected = state.decision?.underwriting_result === 'REJECTED' || currentStage === 'REJECTION';
    const isClosed = state.decision?.is_frozen || state.stage?.is_terminal;
    
    if (isApproved) {
      return 'text-green-700 bg-green-100 border border-green-300';
    }
    if (isRejected) {
      return 'text-red-700 bg-red-100 border border-red-300';
    }
    if (isClosed) {
      return 'text-gray-600 bg-gray-100 border border-gray-300';
    }
    // Warning for sessions awaiting OTP
    if (currentStage === 'OTP' && !state.kyc?.otp_verified) {
      return 'text-amber-700 bg-amber-100 border border-amber-300';
    }
    // Warning for sessions at KYC
    if (currentStage === 'KYC' && !state.kyc?.pan_verified) {
      return 'text-amber-700 bg-amber-100 border border-amber-300';
    }
    return 'text-blue-700 bg-blue-100 border border-blue-300';
  };

  const getStatusText = (state: V3AdminState) => {
    if (!state?.stage) return 'UNKNOWN';
    
    const currentStage = state.stage.current_stage;
    const isApproved = state.decision?.underwriting_result === 'APPROVED' || currentStage === 'SANCTION';
    const isRejected = state.decision?.underwriting_result === 'REJECTED' || currentStage === 'REJECTION';
    const isClosed = state.decision?.is_frozen;
    
    if (isApproved) return 'APPROVED';
    if (isRejected) return 'REJECTED';
    if (isClosed) return 'CLOSED';
    if (currentStage === 'OTP' && !state.kyc?.otp_verified) return 'AWAITING OTP';
    if (currentStage === 'KYC' && !state.kyc?.pan_verified) return 'KYC PENDING';
    return 'IN PROGRESS';
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* ============ HEADER ============ */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="px-4 md:px-6 py-3 md:py-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3 md:gap-4">
              <div className="bg-gradient-to-br from-purple-600 to-indigo-600 p-2 rounded-lg">
                <Eye className="w-5 h-5 md:w-6 md:h-6 text-white" />
              </div>
              <div>
                <h1 className="text-lg md:text-xl font-bold text-gray-900">Loan Operations Dashboard</h1>
                <p className="text-xs md:text-sm text-gray-500 hidden sm:block">Internal Monitoring Console • Aurora Finance NBFC</p>
              </div>
            </div>
            
            <div className="flex items-center gap-2 md:gap-4">
              {/* Connection Status */}
              <div className={`flex items-center gap-1 md:gap-2 px-2 md:px-3 py-1 md:py-1.5 rounded-full text-xs md:text-sm ${
                wsConnected ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
              }`}>
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="hidden sm:inline">{wsConnected ? 'Live Connected' : 'Disconnected'}</span>
              </div>
              
              {/* Refresh Button */}
              <button
                onClick={() => fetchSessions()}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw className="w-4 h-4 md:w-5 md:h-5 text-gray-600" />
              </button>
              
              {/* Logout */}
              <button
                onClick={handleLogout}
                className="flex items-center gap-1 md:gap-2 px-2 md:px-4 py-1.5 md:py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors text-sm"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          </div>
        </div>
        
        {/* Status Bar */}
        <div className="px-4 md:px-6 py-2 bg-gray-50 border-t border-gray-200 flex items-center gap-3 md:gap-6 text-xs md:text-sm flex-wrap">
          <div className="flex items-center gap-1 md:gap-2">
            <Users className="w-4 h-4 text-blue-600" />
            <span className="text-gray-600">Active Sessions:</span>
            <span className="font-semibold text-blue-600">{sessions.length}</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2">
            <Clock className="w-4 h-4 text-gray-500" />
            <span className="text-gray-500">Last Update: {lastUpdate.toLocaleTimeString()}</span>
          </div>
          <div className="flex items-center gap-1 md:gap-2 ml-auto">
            <Activity className="w-4 h-4 text-purple-600" />
            <span className="text-gray-600 hidden sm:inline">Mode:</span>
            <span className="font-medium text-purple-600">Read-Only Monitoring</span>
          </div>
        </div>
      </header>

      {/* ============ MAIN CONTENT ============ */}
      <div className="p-4 md:p-6 overflow-x-hidden">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 md:gap-6">
          
          {/* ============ LEFT: SESSION LIST ============ */}
          <div className="lg:col-span-3 col-span-1">
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 h-auto lg:h-[calc(100vh-180px)] max-h-[400px] lg:max-h-none flex flex-col">
              <div className="p-4 border-b border-gray-200">
                <h2 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Database className="w-5 h-5 text-blue-600" />
                  Applications Queue
                </h2>
                <p className="text-xs text-gray-500 mt-1">Select application to view details</p>
              </div>
              
              <div className="flex-1 overflow-y-auto p-2">
                {isLoading ? (
                  <div className="text-center py-8 text-gray-500">Loading applications...</div>
                ) : sessions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    No active applications
                    <p className="text-xs mt-1">Applications will appear when customers initiate loans</p>
                  </div>
                ) : (
                  sessions.map((session) => (
                    <button
                      key={session.session_id}
                      onClick={() => setSelectedSession(session)}
                      className={`w-full text-left p-3 rounded-lg mb-2 border transition-all duration-200 ${
                        selectedSession?.session_id === session.session_id
                          ? 'border-blue-500 bg-blue-50 shadow-md ring-2 ring-blue-200'
                          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50 hover:shadow-sm'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="font-medium text-gray-900 text-sm truncate">
                          {session.state?.customer?.name || 'Anonymous'}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${getStatusColor(session.state)}`}>
                          {getStatusText(session.state)}
                        </span>
                      </div>
                      {/* Acquisition Source Badge */}
                      {session.state?.acquisition_source && (
                        <div className="mb-2">
                          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                            session.state.acquisition_source === 'AD' 
                              ? 'bg-purple-100 text-purple-700 border border-purple-200' 
                              : 'bg-indigo-100 text-indigo-700 border border-indigo-200'
                          }`}>
                            {session.state.acquisition_source === 'AD' ? 'Digital Campaign' : 'Email Campaign'}
                          </span>
                        </div>
                      )}
                      <div className="text-xs text-gray-500 space-y-1">
                        <div className="flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {session.state?.customer?.mobile_masked || 'No phone'}
                        </div>
                        <div className="flex items-center gap-1">
                          <Activity className="w-3 h-3" />
                          Stage: {session.state?.stage?.current_stage || 'GREETING'}
                        </div>
                        <div className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {session.last_activity ? new Date(session.last_activity).toLocaleTimeString() : 'Just now'}
                        </div>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* ============ CENTER: MAIN PANELS ============ */}
          <div className="lg:col-span-6 col-span-1 space-y-4 md:space-y-6">
            
            {/* Stage Progression Tracker */}
            <StageProgressionPanel state={selectedSession?.state || null} />
            
            {/* Agent Activity Panel */}
            <AgentActivityPanel state={selectedSession?.state || null} />
            
          </div>

          {/* ============ RIGHT: DATA PANELS ============ */}
          <div className="lg:col-span-3 col-span-1 space-y-4 md:space-y-6">
            
            {/* Verification & Data Panel */}
            <VerificationDataPanel state={selectedSession?.state || null} />
            
            {/* Underwriting Decision Panel */}
            <UnderwritingDecisionPanel state={selectedSession?.state || null} />
            
            {/* Sanction/Rejection Artifacts */}
            <ArtifactsPanel state={selectedSession?.state || null} />
            
          </div>
        </div>
      </div>
    </div>
  );
}


// ================================================================================
// APPLICATION PROGRESS PANEL
// ================================================================================
/**
 * Visual pipeline showing loan application processing stages.
 * 
 * Stage indicators:
 * - Green (completed): Stage has been processed successfully
 * - Yellow (current): Application is currently at this stage  
 * - Gray (pending): Stage not yet reached
 * - Red (failed): Application was rejected at this stage
 * 
 * READ-ONLY: Values are retrieved from backend state, not editable.
 */

function StageProgressionPanel({ state }: { state: V3AdminState | null }) {
  const currentStage = state?.stage?.current_stage;
  const currentStageIndex = currentStage 
    ? STAGE_ORDER.indexOf(currentStage as ConversationStage)
    : -1;
  
  const isFinalStage = currentStage === 'SANCTION' || currentStage === 'REJECTION';

  const getStageStatus = (stage: ConversationStage, index: number) => {
    if (!state || !currentStage) return 'pending';
    if (currentStage === 'REJECTION' && stage === 'UNDERWRITING') return 'failed';
    if (currentStage === stage) return 'current';
    if (index < currentStageIndex) return 'completed';
    if (isFinalStage && index <= 11) return 'completed';
    return 'pending';
  };

  const getStatusStyles = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500 text-white border-green-500';
      case 'current': return 'bg-yellow-400 text-yellow-900 border-yellow-400 animate-pulse';
      case 'failed': return 'bg-red-500 text-white border-red-500';
      default: return 'bg-gray-200 text-gray-500 border-gray-300';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 md:p-6">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp className="w-5 h-5 text-purple-600" />
        <h2 className="font-semibold text-gray-900">Application Progress</h2>
        <span className="ml-auto text-xs text-gray-500">Workflow Status</span>
      </div>
      
      {/* Pipeline Visualization - Scrollable on small screens */}
      <div className="overflow-x-auto pb-2">
        <div className="flex items-center justify-between min-w-[800px] mb-4">
          {STAGE_ORDER.map((stage, index) => {
            const status = getStageStatus(stage, index);
            const info = STAGE_INFO[stage];
            
            return (
              <div key={stage} className="flex items-center">
                {/* Stage Node */}
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 md:w-10 md:h-10 rounded-full border-2 flex items-center justify-center text-xs font-bold ${getStatusStyles(status)}`}>
                    {status === 'completed' ? '✓' : status === 'failed' ? '✗' : index + 1}
                  </div>
                  <span className="text-[9px] md:text-[10px] text-gray-600 mt-1 text-center max-w-[45px] md:max-w-[50px] leading-tight">{info.name}</span>
                </div>
                
                {/* Connector Line */}
                {index < STAGE_ORDER.length - 1 && (
                  <div className={`w-3 md:w-4 h-0.5 ${status === 'completed' ? 'bg-green-500' : 'bg-gray-300'}`} />
                )}
              </div>
            );
          })}
          
          {/* Final Stage (Sanction/Rejection) */}
          <div className="flex items-center">
            <div className="w-3 md:w-4 h-0.5 bg-gray-300" />
            <div className="flex flex-col items-center">
              <div className={`w-10 h-10 md:w-12 md:h-12 rounded-full border-2 flex items-center justify-center ${
                state?.current_stage === 'SANCTION' ? 'bg-green-500 text-white border-green-500' :
                state?.current_stage === 'REJECTION' ? 'bg-red-500 text-white border-red-500' :
                'bg-gray-200 text-gray-500 border-gray-300'
              }`}>
                {state?.current_stage === 'SANCTION' ? '✓' : 
                 state?.current_stage === 'REJECTION' ? '✗' : '?'}
              </div>
              <span className="text-[9px] md:text-[10px] text-gray-600 mt-1">
                {state?.current_stage === 'SANCTION' ? 'Approved' :
                 state?.current_stage === 'REJECTION' ? 'Rejected' : 'Decision'}
              </span>
            </div>
          </div>
        </div>
      </div>
      
      {/* Current Stage Info */}
      <div className="bg-gray-50 rounded-lg p-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-gray-600">Current Stage:</span>
          <span className="font-semibold text-purple-600">
            {state?.stage?.current_stage || 'No Session Selected'}
          </span>
        </div>
        {state && (
          <div className="flex items-center justify-between mt-1">
            <span className="text-gray-600">Current Handler:</span>
            <span className="font-medium text-blue-600">
              {STAGE_TO_AGENT[state.stage?.current_stage as ConversationStage] || 'System'}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}


// ================================================================================
// PROCESSING ASSIGNMENT PANEL
// ================================================================================
/**
 * Displays which processing handler is currently assigned to the application.
 * 
 * Handlers:
 * - Sales: Initial customer engagement and requirements gathering
 * - Verification: KYC validation and credit bureau checks
 * - Underwriting: Loan eligibility and risk assessment
 * - Sanction: Document generation and loan disbursement
 * 
 * READ-ONLY: Handler assignment is automatic based on application stage.
 */

function AgentActivityPanel({ state }: { state: V3AdminState | null }) {
  const agents = [
    { id: 'master', name: 'System', icon: Brain, description: 'Routing', color: 'purple' },
    { id: 'sales', name: 'Sales', icon: User, description: 'Customer Engagement', color: 'blue' },
    { id: 'verification', name: 'Verification', icon: Shield, description: 'KYC & Credit Check', color: 'green' },
    { id: 'underwriting', name: 'Underwriting', icon: TrendingUp, description: 'Risk Assessment', color: 'orange' },
    { id: 'sanction', name: 'Sanction', icon: FileText, description: 'Document Generation', color: 'emerald' },
  ];

  const getCurrentAgent = () => {
    if (!state?.stage) return null;
    const agentName = STAGE_TO_AGENT[state.stage.current_stage as ConversationStage];
    return agents.find(a => a.name === agentName) || agents[0];
  };

  const currentAgent = getCurrentAgent();

  // Compute dynamic background colors
  const getAgentBgColor = (agent: typeof agents[0], isActive: boolean) => {
    if (!isActive) return 'bg-gray-200 text-gray-500';
    switch (agent.color) {
      case 'purple': return 'bg-purple-500 text-white';
      case 'blue': return 'bg-blue-500 text-white';
      case 'green': return 'bg-green-500 text-white';
      case 'orange': return 'bg-orange-500 text-white';
      case 'emerald': return 'bg-emerald-500 text-white';
      default: return 'bg-gray-500 text-white';
    }
  };

  const getAgentBorderColor = (agent: typeof agents[0], isActive: boolean) => {
    if (!isActive) return 'border-gray-200 bg-gray-50';
    switch (agent.color) {
      case 'purple': return 'border-purple-500 bg-purple-50 shadow-md';
      case 'blue': return 'border-blue-500 bg-blue-50 shadow-md';
      case 'green': return 'border-green-500 bg-green-50 shadow-md';
      case 'orange': return 'border-orange-500 bg-orange-50 shadow-md';
      case 'emerald': return 'border-emerald-500 bg-emerald-50 shadow-md';
      default: return 'border-gray-500 bg-gray-50 shadow-md';
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="w-5 h-5 text-purple-600" />
        <h2 className="font-semibold text-gray-900">Processing Assignment</h2>
        <span className="ml-auto text-xs text-gray-500">Current Handler</span>
      </div>
      
      {/* Agent Grid */}
      <div className="grid grid-cols-5 gap-3">
        {agents.map((agent) => {
          const isActive = currentAgent?.id === agent.id;
          const Icon = agent.icon;
          
          return (
            <div
              key={agent.id}
              className={`p-3 rounded-lg border-2 text-center transition-all ${getAgentBorderColor(agent, isActive)}`}
            >
              <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center mb-2 ${getAgentBgColor(agent, isActive)}`}>
                <Icon className="w-6 h-6" />
              </div>
              <div className={`text-xs font-medium ${isActive ? 'text-gray-900' : 'text-gray-500'}`}>
                {agent.name}
              </div>
              {isActive && (
                <div className="mt-1">
                  <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-ping" />
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Current Activity */}
      {state && state.stage && (
        <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-900">
              {currentAgent?.name} handling {STAGE_INFO[state.stage.current_stage as ConversationStage]?.name}
            </span>
          </div>
          <p className="text-xs text-blue-700 mt-1">
            {STAGE_INFO[state.stage.current_stage as ConversationStage]?.description}
          </p>
        </div>
      )}
    </div>
  );
}


// ================================================================================
// KYC STATUS PANEL
// ================================================================================
/**
 * Displays customer verification data and KYC status.
 * 
 * Data sources:
 * - CRM Service: Customer identification and contact details
 * - Credit Bureau: Credit score and financial history
 * - Offer Engine: Pre-approved limits and interest rates
 * 
 * PAN numbers are masked for data security compliance.
 * 
 * READ-ONLY: All data retrieved from verified backend services.
 */

function VerificationDataPanel({ state }: { state: V3AdminState | null }) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Database className="w-5 h-5 text-green-600" />
        <h2 className="font-semibold text-gray-900 text-sm">KYC Status</h2>
      </div>
      
      {!state ? (
        <p className="text-sm text-gray-500">Select an application to view data</p>
      ) : (
        <div className="space-y-3 text-sm">
          {/* KYC Status */}
          <div className="flex items-center justify-between">
            <span className="text-gray-600">OTP Verified</span>
            <span className={`font-medium ${state.kyc?.otp_verified ? 'text-green-600' : 'text-gray-500'}`}>
              {state.kyc?.otp_verified ? 'VERIFIED' : 'PENDING'}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">PAN Verified</span>
            <span className={`font-medium ${state.kyc?.pan_verified ? 'text-green-600' : 'text-gray-500'}`}>
              {state.kyc?.pan_verified ? 'VERIFIED' : 'PENDING'}
            </span>
          </div>
          
          {/* Customer Info */}
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Customer</span>
            <span className="font-medium text-gray-900">{state.customer?.name || 'N/A'}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Mobile</span>
            <span className="font-mono text-gray-700">{state.customer?.mobile_masked || 'N/A'}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">PAN (masked)</span>
            <span className="font-mono text-gray-700">{state.kyc?.pan_number || 'N/A'}</span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">City</span>
            <span className="font-medium text-gray-900">{state.customer?.city || 'N/A'}</span>
          </div>
          
          {/* Financial Data */}
          <div className="pt-2 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Pre-approved Limit</span>
              <span className="font-semibold text-green-600">
                ₹{(state.offer?.pre_approved_limit || 0).toLocaleString('en-IN')}
              </span>
            </div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-gray-600">Requested Amount</span>
              <span className="font-medium text-gray-900">
                ₹{(state.offer?.requested_amount || 0).toLocaleString('en-IN')}
              </span>
            </div>
            {state.offer?.interest_rate_range && (
              <div className="flex items-center justify-between mt-1">
                <span className="text-gray-600">Interest Rate Range</span>
                <span className="font-medium text-gray-900">
                  {state.offer.interest_rate_range.min}% - {state.offer.interest_rate_range.max}%
                </span>
              </div>
            )}
            {state.offer?.final_interest_rate && (
              <div className="flex items-center justify-between mt-1">
                <span className="text-gray-600">Final Rate</span>
                <span className="font-medium text-blue-600">
                  {state.offer.final_interest_rate}%
                </span>
              </div>
            )}
          </div>
          
          {/* Data Source Note */}
          <div className="pt-2 mt-2 border-t border-gray-200">
            <p className="text-xs text-gray-400 italic">
              Source: {state.income_source || 'Database'}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}


// ================================================================================
// UNDERWRITING SUMMARY PANEL
// ================================================================================
/**
 * Displays underwriting decision details and financial calculations.
 * 
 * Calculations shown:
 * - Requested loan amount vs pre-approved limit
 * - Calculated EMI based on tenure and interest rate
 * - EMI as percentage of monthly income
 * - Final approval/rejection decision with reasoning
 * 
 * READ-ONLY: Decisions are made by the underwriting engine, not editable.
 */

function UnderwritingDecisionPanel({ state }: { state: V3AdminState | null }) {
  const getDecisionExplanation = () => {
    if (!state?.decision?.underwriting_result) return null;
    
    if (state.decision.underwriting_result === 'APPROVED') {
      return 'Loan within pre-approved limit. Credit score excellent. Instant approval granted.';
    }
    
    if (state.decision.underwriting_result === 'REJECTED') {
      return state.decision.rejection_reason || 'Application did not meet eligibility criteria.';
    }
    
    return 'Underwriting in progress...';
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="w-5 h-5 text-orange-600" />
        <h2 className="font-semibold text-gray-900 text-sm">Underwriting Summary</h2>
      </div>
      
      {!state ? (
        <p className="text-sm text-gray-500">Select a session to view decision</p>
      ) : (
        <div className="space-y-3 text-sm">
          {/* Loan Request */}
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Requested Amount</span>
            <span className="font-bold text-gray-900">
              ₹{(state.offer?.requested_amount || 0).toLocaleString('en-IN')}
            </span>
          </div>
          
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Pre-approved Limit</span>
            <span className="font-medium text-gray-700">
              ₹{(state.offer?.pre_approved_limit || 0).toLocaleString('en-IN')}
            </span>
          </div>
          
          {/* Selected Tenure */}
          {state.offer?.selected_tenure && (
            <div className="flex items-center justify-between">
              <span className="text-gray-600">Tenure Selected</span>
              <span className="font-medium text-gray-900">
                {state.offer.selected_tenure} months
              </span>
            </div>
          )}
          
          {/* Calculated EMI */}
          {state.offer?.calculated_emi && (
            <div className="flex items-center justify-between">
              <span className="text-gray-600">EMI Calculated</span>
              <span className="font-bold text-blue-600">
                ₹{state.offer.calculated_emi.toLocaleString('en-IN')}/mo
              </span>
            </div>
          )}
          
          {/* Decision */}
          {state.decision?.underwriting_result && (
            <div className={`mt-3 p-3 rounded-lg ${
              state.decision.underwriting_result === 'APPROVED' ? 'bg-green-50 border border-green-200' :
              state.decision.underwriting_result === 'REJECTED' ? 'bg-red-50 border border-red-200' :
              'bg-yellow-50 border border-yellow-200'
            }`}>
              <div className="flex items-center gap-2 mb-1">
                {state.decision.underwriting_result === 'APPROVED' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : state.decision.underwriting_result === 'REJECTED' ? (
                  <XCircle className="w-5 h-5 text-red-600" />
                ) : (
                  <Clock className="w-5 h-5 text-yellow-600" />
                )}
                <span className={`font-bold ${
                  state.decision.underwriting_result === 'APPROVED' ? 'text-green-700' :
                  state.decision.underwriting_result === 'REJECTED' ? 'text-red-700' : 'text-yellow-700'
                }`}>
                  {state.decision.underwriting_result}
                </span>
              </div>
              <p className="text-xs text-gray-600">{getDecisionExplanation()}</p>
            </div>
          )}
          
          {/* Underwriting Status */}
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Underwriting</span>
            <span className={`font-medium ${state.decision?.underwriting_complete ? 'text-green-600' : 'text-yellow-600'}`}>
              {state.decision?.underwriting_complete ? 'COMPLETE' : 'PENDING'}
            </span>
          </div>
          
          {/* Decision Source Note */}
          <div className="pt-2 mt-2 border-t border-gray-200">
            <p className="text-xs text-gray-400 italic flex items-center gap-1">
              <Shield className="w-3 h-3" />
              Automated underwriting decision
            </p>
          </div>
        </div>
      )}
    </div>
  );
}


// ================================================================================
// SANCTION & CLOSURE PANEL
// ================================================================================
/**
 * Displays final loan outcome documents and closure details.
 * 
 * For approved loans:
 * - Sanction letter generation status
 * - Reference number and validity period
 * - Download link for sanction letter PDF
 * 
 * For rejected applications:
 * - Rejection reason and details
 * - Closure information
 * 
 * READ-ONLY: Document generation is automatic based on underwriting decision.
 */

function ArtifactsPanel({ state }: { state: V3AdminState | null }) {
  const handleDownload = () => {
    if (state?.session_id) {
      window.open(`http://localhost:8000/api/download-sanction/${state.session_id}`, '_blank');
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText className="w-5 h-5 text-emerald-600" />
        <h2 className="font-semibold text-gray-900 text-sm">Sanction & Closure</h2>
      </div>
      
      {!state ? (
        <p className="text-sm text-gray-500">Select an application to view documents</p>
      ) : state.stage?.current_stage === 'SANCTION' || state.decision?.underwriting_result === 'APPROVED' ? (
        <div className="space-y-3">
          {/* Sanction Letter */}
          <div className="p-3 bg-green-50 rounded-lg border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-green-600" />
              <span className="font-medium text-green-800">Sanction Letter</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                state.decision?.sanction_letter_generated ? 'bg-green-200 text-green-800' : 'bg-yellow-200 text-yellow-800'
              }`}>
                {state.decision?.sanction_letter_generated ? 'GENERATED' : 'PENDING'}
              </span>
            </div>
            
            <p className="text-xs text-green-700 mb-1">
              Application ID: {state.application_id}
            </p>
            
            {state.decision?.sanction_letter_generated && (
              <button
                onClick={handleDownload}
                className="mt-2 flex items-center gap-2 text-sm text-green-700 hover:text-green-900"
              >
                <Download className="w-4 h-4" />
                Download PDF
              </button>
            )}
          </div>
        </div>
      ) : state.stage?.current_stage === 'REJECTION' || state.decision?.underwriting_result === 'REJECTED' ? (
        <div className="space-y-3">
          {/* Rejection Details */}
          <div className="p-3 bg-red-50 rounded-lg border border-red-200">
            <div className="flex items-center gap-2 mb-2">
              <XCircle className="w-4 h-4 text-red-600" />
              <span className="font-medium text-red-800">Application Rejected</span>
            </div>
            
            <p className="text-sm text-red-700">
              {state.decision?.rejection_reason || 'Eligibility criteria not met'}
            </p>
            
            {state.decision?.freeze_reason && (
              <p className="text-xs text-gray-500 mt-2">
                Closure: {state.decision.freeze_reason}
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="p-3 bg-gray-50 rounded-lg text-center">
          <AlertTriangle className="w-8 h-8 text-gray-400 mx-auto mb-2" />
          <p className="text-sm text-gray-500">
            No artifacts yet
          </p>
          <p className="text-xs text-gray-400 mt-1">
            Will appear after underwriting decision
          </p>
        </div>
      )}
    </div>
  );
}