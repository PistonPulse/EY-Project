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
    if (agent.id === activeAgent) return 'border-emerald-400 bg-emerald-400/20 shadow-emerald-400/50';
    if (agent.id === 'master') return 'border-cyan-400 bg-cyan-400/20 shadow-cyan-400/50';
    return 'border-gray-500 bg-gray-500/10 shadow-gray-500/30';
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-purple-500/30 p-6 h-[calc(100vh-120px)] flex flex-col">
      <div className="flex items-center gap-2 mb-6 pb-3 border-b border-purple-500/30">
        <Brain className="w-5 h-5 text-purple-400" />
        <h3 className="font-mono text-purple-400">Agent Neural Network</h3>
        {customerProfile && (
          <div className="ml-auto text-sm">
            <span className="text-gray-400">Customer: </span>
            <span className="text-cyan-400">{customerProfile.name}</span>
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
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.8" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.8" />
            </linearGradient>
            <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#10b981" stopOpacity="1" />
              <stop offset="100%" stopColor="#3b82f6" stopOpacity="1" />
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
                <div className="text-white">
                  {agent.icon}
                </div>
              </div>
              
              {/* Label */}
              <div className="font-mono text-xs text-center whitespace-nowrap bg-black/60 px-2 py-1 rounded">
                {agent.name}
              </div>

              {/* Active Indicator */}
              {agent.id === activeAgent && (
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-emerald-400 rounded-full animate-ping"></div>
              )}
            </div>
          </div>
        ))}

        {/* Current Activity Display */}
        <div className="absolute bottom-0 left-0 right-0 bg-black/60 backdrop-blur-sm rounded-lg p-4 border border-emerald-500/30">
          <div className="font-mono text-sm">
            <span className="text-gray-400">Current Activity: </span>
            <span className="text-emerald-400">
              {agents.find(a => a.id === activeAgent)?.name || 'Master'} Agent Processing...
            </span>
          </div>
          {customerProfile && (
            <div className="font-mono text-xs mt-2">
              <span className="text-gray-400">Risk Category: </span>
              <span className={`${
                customerProfile.risk_category === 'PRIME' || customerProfile.risk_category === 'HNI' 
                  ? 'text-green-400' 
                  : customerProfile.risk_category === 'FRAUD' || customerProfile.risk_category === 'BLACKLIST'
                  ? 'text-red-400'
                  : 'text-amber-400'
              }`}>
                {customerProfile.risk_category}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}