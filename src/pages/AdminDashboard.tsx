import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { StatusBar } from '../components/admin/StatusBar';
import { LiveChatMirror } from '../components/admin/LiveChatMirror';
import { AgentNetwork } from '../components/admin/AgentNetwork';
import { RiskMetrics } from '../components/admin/RiskMetrics';
import { ActivityLogs } from '../components/admin/ActivityLogs';
import { LogOut } from 'lucide-react';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";

interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
}

export function AdminDashboard() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [events, setEvents] = useState<WebSocketMessage[]>([]);
  const [activeAgent, setActiveAgent] = useState<string>('master');
  const [riskScore, setRiskScore] = useState<number>(0);
  const [customerProfile, setCustomerProfile] = useState<any>(null);
  const [activeSessions, setActiveSessions] = useState<number>(0);

  useEffect(() => {
    let websocket: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout;

    const connect = () => {
      // Connect to WebSocket for real-time monitoring
      websocket = new WebSocket('ws://localhost:8000/admin/stream');

      websocket.onopen = () => {
        console.log('✅ WebSocket CONNECTED to admin stream');
      };

      websocket.onmessage = (event) => {
        const message: WebSocketMessage = JSON.parse(event.data);
        console.log('📨 WebSocket Message:', message.type, message.data);
      
      setEvents(prev => [...prev, message].slice(-50)); // Keep last 50 events

      // Update dashboard based on event type
      switch (message.type) {
        case 'connected':
          setActiveSessions(message.data.active_sessions);
          break;
        case 'agent_active':
          setActiveAgent(message.data.agent);
          break;
        case 'risk_calculated':
          const newScore = message.data.risk_score;
          setRiskScore(newScore);
          console.log('Trust Score Updated:', newScore);
          break;
        case 'customer_identified':
          // Update customer profile with full data including behavioral_flags
          const fullProfile = message.data.customer;
          setCustomerProfile(fullProfile);
          console.log('Customer Profile Updated:', fullProfile);
          break;
        case 'bot_response':
          // Check if bot response contains admin_data with trust scores
          if (message.data && message.data.admin_data) {
            if (message.data.admin_data.trust_score !== undefined) {
              setRiskScore(message.data.admin_data.trust_score);
            }
            if (message.data.admin_data.customer_profile) {
              setCustomerProfile(message.data.admin_data.customer_profile);
            }
          }
          break;
        case 'log':
          if (message.data.agent) {
            // Normalize agent name to ID
            const agentName = message.data.agent.toLowerCase();
            if (agentName.includes('sales')) setActiveAgent('sales');
            else if (agentName.includes('verification')) setActiveAgent('verification');
            else if (agentName.includes('underwriting')) setActiveAgent('underwriting');
            else if (agentName.includes('trust') || agentName.includes('safety')) setActiveAgent('trust');
            else setActiveAgent('master');
          }
          // Extract trust_score from log if present
          if (message.data.trust_score !== undefined) {
            setRiskScore(message.data.trust_score);
          }
          break;
      }
    };

    websocket.onerror = (error) => {
      console.error('❌ WebSocket error:', error);
    };

    websocket.onclose = () => {
      console.log('🔌 WebSocket disconnected - reconnecting in 2s...');
      // Auto-reconnect after 2 seconds
      reconnectTimeout = setTimeout(() => {
        console.log('🔄 Attempting to reconnect...');
        connect();
      }, 2000);
    };

    setWs(websocket);
  };

  connect();

  return () => {
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    if (websocket) websocket.close();
  };
}, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-[#0F172A] text-white">
      {/* Header */}
      <header className="bg-[#1E293B] border-b border-cyan-500/20 sticky top-0 z-50 backdrop-blur-sm">
        <div className="px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3 sm:gap-4">
              <div className="bg-white rounded p-1.5 sm:p-2">
                <img src={tataLogo} alt="Tata Capital" className="h-6 sm:h-8 object-contain" />
              </div>
              <div className="border-l border-gray-600 pl-3 sm:pl-4">
                <h1 className="text-lg sm:text-xl font-semibold">Risk Control Unit (RCU) Console</h1>
                <p className="text-xs sm:text-sm text-gray-400 hidden sm:block">Tata Capital AI Underwriter - Live Monitoring</p>
              </div>
            </div>
            <div className="flex items-center gap-3 sm:gap-6">
              <div className="text-right hidden sm:block">
                <div className="text-sm text-gray-400">Senior Credit Officer</div>
                <div className="text-cyan-400 font-semibold">{user?.username}</div>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 border border-red-500/30 rounded-lg hover:bg-red-500/20 transition-colors text-red-400"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Status Bar */}
      <StatusBar 
        activeSessions={activeSessions}
        activeAgent={activeAgent}
        riskScore={riskScore}
      />

      {/* Main Dashboard Grid */}
      <div className="p-8 pt-24">
        <div className="grid grid-cols-12 gap-8 max-w-[1800px] mx-auto">
          {/* Left Column - Live Chat Mirror (25%) */}
          <div className="col-span-12 lg:col-span-3">
            <LiveChatMirror events={events} />
          </div>

          {/* Center Column - Agent Network (50%) */}
          <div className="col-span-12 lg:col-span-6">
            <AgentNetwork activeAgent={activeAgent} customerProfile={customerProfile} />
          </div>

          {/* Right Column - Risk Metrics (25%) */}
          <div className="col-span-12 lg:col-span-3">
            <RiskMetrics 
              riskScore={riskScore} 
              events={events}
              customerProfile={customerProfile}
            />
          </div>

          {/* Full Width Bottom - Activity Logs */}
          <div className="col-span-12 h-80">
            <ActivityLogs events={events} />
          </div>
        </div>
      </div>
    </div>
  );
}