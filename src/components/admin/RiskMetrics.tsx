import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { Shield, Activity, Terminal } from 'lucide-react';
import { useState, useEffect } from 'react';

interface RiskMetricsProps {
  riskScore: number;
  events: any[];
  customerProfile: any;
}

export function RiskMetrics({ riskScore, events, customerProfile }: RiskMetricsProps) {
  const [behaviorData, setBehaviorData] = useState(
    Array.from({ length: 20 }, (_, i) => ({ value: Math.random() * 100 }))
  );

  useEffect(() => {
    const interval = setInterval(() => {
      // Update behavior waveform
      setBehaviorData(prev => [
        ...prev.slice(1),
        { value: 50 + Math.random() * 40 - 20 }
      ]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  // Extract log events
  const logEvents = events
    .filter(e => e.type === 'log' || e.type === 'agent_active' || e.type === 'risk_calculated')
    .slice(-6)
    .map(e => {
      if (e.type === 'log') {
        return {
          text: e.data.message,
          time: new Date(e.timestamp).toLocaleTimeString('en-US', { hour12: false }),
          level: e.data.level
        };
      } else if (e.type === 'agent_active') {
        return {
          text: `>> Agent Active: ${e.data.agent.toUpperCase()}`,
          time: new Date(e.timestamp).toLocaleTimeString('en-US', { hour12: false }),
          level: 'success'
        };
      } else if (e.type === 'risk_calculated') {
        return {
          text: `>> Risk Score: ${e.data.risk_score}/100`,
          time: new Date(e.timestamp).toLocaleTimeString('en-US', { hour12: false }),
          level: 'success'
        };
      }
      return null;
    })
    .filter(Boolean);

  const displayRiskScore = riskScore || 0;
  const riskStatus = displayRiskScore >= 75 ? 'VERIFIED' : displayRiskScore >= 50 ? 'MEDIUM' : displayRiskScore > 0 ? 'HIGH RISK' : 'PENDING';

  return (
    <div className="space-y-6 h-[calc(100vh-120px)] overflow-y-auto scrollbar-thin scrollbar-thumb-amber-500/30">
      {/* Trust Score */}
      <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-emerald-500/30 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-emerald-400" />
          <h3 className="font-mono text-emerald-400">Trust Score</h3>
        </div>

        {/* Speedometer */}
        <div className="relative w-full h-32 flex items-end justify-center">
          <svg viewBox="0 0 200 100" className="w-full">
            {/* Background Arc */}
            <path
              d="M 20 90 A 80 80 0 0 1 180 90"
              fill="none"
              stroke="#1e293b"
              strokeWidth="20"
              strokeLinecap="round"
            />
            
            {/* Colored Arc */}
            <path
              d="M 20 90 A 80 80 0 0 1 180 90"
              fill="none"
              stroke="url(#scoreGradient)"
              strokeWidth="20"
              strokeLinecap="round"
              strokeDasharray={`${displayRiskScore * 2.51} 251`}
              className="transition-all duration-1000"
            />

            {/* Gradient Definition */}
            <defs>
              <linearGradient id="scoreGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="#ef4444" />
                <stop offset="50%" stopColor="#f59e0b" />
                <stop offset="100%" stopColor="#10b981" />
              </linearGradient>
            </defs>
          </svg>
          
          {/* Score Display */}
          <div className="absolute inset-0 flex items-center justify-center mt-8">
            <div className="text-center">
              <div className="text-4xl text-emerald-400 font-mono">{Math.round(displayRiskScore)}</div>
              <div className="text-xs text-gray-400 font-mono">/100</div>
            </div>
          </div>
        </div>

        <div className="mt-4 text-center">
          <span className="text-xs font-mono text-gray-400">Status: </span>
          <span className={`text-xs font-mono ${
            riskStatus === 'VERIFIED' ? 'text-emerald-400' : 
            riskStatus === 'MEDIUM' ? 'text-amber-400' : 
            riskStatus === 'HIGH RISK' ? 'text-red-400' : 'text-gray-400'
          }`}>{riskStatus}</span>
        </div>

        {customerProfile && (
          <div className="mt-3 pt-3 border-t border-emerald-500/20 text-xs space-y-1">
            <div className="flex justify-between text-gray-400">
              <span>Credit Score:</span>
              <span className="text-cyan-400">{customerProfile.credit_score || 'N/A'}</span>
            </div>
            {customerProfile.behavioral_flags && (
              <>
                <div className="flex justify-between text-gray-400">
                  <span>Behavioral Score:</span>
                  <span className="text-emerald-400">{customerProfile.behavioral_flags.behavioral_score || 0}/100</span>
                </div>
                <div className="flex justify-between text-gray-400">
                  <span>Risk Category:</span>
                  <span className={`${
                    customerProfile.behavioral_flags.risk_category === 'LOW' ? 'text-green-400' :
                    customerProfile.behavioral_flags.risk_category === 'MEDIUM' ? 'text-amber-400' :
                    'text-red-400'
                  }`}>{customerProfile.behavioral_flags.risk_category}</span>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Behavioral Analysis */}
      <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-amber-500/30 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-amber-400" />
          <h3 className="font-mono text-amber-400">Behavioral Analysis</h3>
        </div>

        <div className="h-24 -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={behaviorData}>
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#f59e0b" 
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 flex items-center justify-between text-xs font-mono">
          <span className="text-gray-400">Stress Level:</span>
          <span className="text-amber-400">NORMAL</span>
        </div>

        {customerProfile && (
          <div className="mt-2 text-xs text-gray-400">
            Behavioral Score: <span className="text-amber-400">{customerProfile.behavioral_score}/100</span>
          </div>
        )}
      </div>

      {/* System Logs */}
      <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-green-500/30 p-6">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5 text-green-400" />
          <h3 className="font-mono text-green-400">System Logs</h3>
        </div>

        <div className="bg-black/60 rounded p-3 h-48 overflow-y-auto font-mono text-xs space-y-1 scrollbar-thin scrollbar-thumb-green-500/30">
          {logEvents.length === 0 ? (
            <div className="text-gray-500">Waiting for events...</div>
          ) : (
            logEvents.map((log: any, index) => (
              <div key={index} className="animate-fadeIn">
                <span className="text-gray-500">[{log.time}] </span>
                <span className={log.level === 'success' ? 'text-green-400' : 'text-amber-400'}>
                  {log.text}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}