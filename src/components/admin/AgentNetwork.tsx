import { Brain, ShoppingCart, Shield, CheckCircle, TrendingUp } from 'lucide-react';

interface Agent {
  id: string;
  name: string;
  icon: React.ReactNode;
  x: number;
  y: number;
}

interface AgentNetworkProps {
  activeAgent: string;
  customerProfile: any;
}

export function AgentNetwork({ activeAgent, customerProfile }: AgentNetworkProps) {
  const agents: Agent[] = [
    { 
      id: 'master', 
      name: 'Master Agent', 
      icon: <Brain className="w-6 h-6" />,
      x: 50, 
      y: 15
    },
    { 
      id: 'sales', 
      name: 'Sales', 
      icon: <ShoppingCart className="w-5 h-5" />,
      x: 15, 
      y: 45
    },
    { 
      id: 'verification', 
      name: 'Verification', 
      icon: <CheckCircle className="w-5 h-5" />,
      x: 50, 
      y: 50
    },
    { 
      id: 'trust', 
      name: 'Trust & Safety', 
      icon: <Shield className="w-5 h-5" />,
      x: 85, 
      y: 45
    },
    { 
      id: 'underwriting', 
      name: 'Underwriting', 
      icon: <TrendingUp className="w-5 h-5" />,
      x: 50, 
      y: 75
    },
  ];

  const getStatusColor = (agent: Agent) => {
    if (agent.id === activeAgent) return 'border-[#3B82F6] bg-blue-100 shadow-lg shadow-blue-200';
    if (agent.id === 'master') return 'border-[#004589] bg-blue-50 shadow-md shadow-blue-100';
    return 'border-gray-300 bg-white shadow-sm';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 h-[calc(100vh-120px)] flex flex-col">
      <div className="flex items-center gap-2 mb-6 pb-3 border-b border-gray-200">
        <Brain className="w-5 h-5 text-[#3B82F6]" />
        <h3 className="font-semibold text-[#004589]">Agent Network</h3>
        {customerProfile && (
          <div className="ml-auto text-sm">
            <span className="text-gray-600">Customer: </span>
            <span className="text-[#004589] font-semibold">{customerProfile.name}</span>
          </div>
        )}
      </div>

      {/* Neural Network Visualization */}
      <div className="flex-1 relative">
        <svg className="absolute inset-0 w-full h-full" style={{ zIndex: 0 }}>
          {/* Connection Lines */}
          {/* Master to all others */}
          <line x1="50%" y1="15%" x2="15%" y2="45%" stroke="url(#grad1)" strokeWidth="2" opacity="0.4" />
          <line x1="50%" y1="15%" x2="50%" y2="50%" stroke="url(#grad2)" strokeWidth="3" opacity="0.8" />
          <line x1="50%" y1="15%" x2="85%" y2="45%" stroke="url(#grad1)" strokeWidth="2" opacity="0.4" />
          
          {/* Verification to Underwriting */}
          <line x1="50%" y1="50%" x2="50%" y2="75%" stroke="url(#grad2)" strokeWidth="2" opacity="0.6" />
          
          {/* Gradients */}
          <defs>
            <linearGradient id="grad1" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.6" />
              <stop offset="100%" stopColor="#004589" stopOpacity="0.6" />
            </linearGradient>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#004589" stopOpacity="0.8" />
            </linearGradient>
          </defs>
        </svg>

        {/* Agent Nodes */}
        {agents.map((agent) => (
          <div
            key={agent.id}
            className="absolute transform -translate-x-1/2 -translate-y-1/2 transition-all duration-500"
            style={{ left: `${agent.x}%`, top: `${agent.y}%`, zIndex: 10 }}
          >
            <div className={`relative flex flex-col items-center gap-2`}>
              {/* Node Circle */}
              <div className={`w-20 h-20 rounded-full border-2 flex items-center justify-center shadow-lg transition-all duration-500 ${getStatusColor(agent)} ${agent.id === activeAgent ? 'animate-pulse scale-110' : ''}`}>
                <div className={agent.id === activeAgent ? 'text-[#3B82F6]' : 'text-[#004589]'}>
                  {agent.icon}
                </div>
              </div>
              
              {/* Label */}
              <div className="text-xs text-center whitespace-nowrap bg-gray-100 px-2 py-1 rounded border border-gray-300 font-medium text-gray-700">
                {agent.name}
              </div>

              {/* Active Indicator */}
              {agent.id === activeAgent && (
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-green-500 rounded-full animate-ping"></div>
              )}
            </div>
          </div>
        ))}

        {/* Current Activity Display */}
        <div className="absolute bottom-0 left-0 right-0 bg-blue-50 rounded-lg p-4 border border-blue-200">
          <div className="text-sm">
            <span className="text-gray-700 font-medium">Current Activity: </span>
            <span className="text-[#3B82F6] font-semibold">
              {agents.find(a => a.id === activeAgent)?.name || 'Master'} Agent Processing...
            </span>
          </div>
          {customerProfile && customerProfile.behavioral_flags && (
            <div className="text-xs mt-2">
              <span className="text-gray-700 font-medium">Risk Category: </span>
              <span className={`font-bold ${
                customerProfile.behavioral_flags.risk_category === 'LOW' 
                  ? 'text-green-600' 
                  : customerProfile.behavioral_flags.risk_category === 'MEDIUM'
                  ? 'text-amber-600'
                  : customerProfile.behavioral_flags.risk_category === 'HIGH' || 
                    customerProfile.behavioral_flags.risk_category === 'CRITICAL' ||
                    customerProfile.behavioral_flags.risk_category === 'FRAUD_CONFIRMED'
                  ? 'text-red-600'
                  : 'text-gray-600'
              }`}>
                {customerProfile.behavioral_flags.risk_category}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}