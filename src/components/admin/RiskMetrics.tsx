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
    <div className="space-y-4 h-[calc(100vh-120px)] overflow-y-auto">
      {/* Trust Score */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-[#3B82F6]" />
          <h3 className="font-semibold text-[#004589]">Trust Score</h3>
        </div>

        {/* Speedometer */}
        <div className="relative w-full h-32 flex items-end justify-center">
          <svg viewBox="0 0 200 100" className="w-full">
            {/* Background Arc */}
            <path
              d="M 20 90 A 80 80 0 0 1 180 90"
              fill="none"
              stroke="#E0E7FF"
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
              <div className="text-5xl text-[#004589] font-bold">{Math.round(displayRiskScore)}</div>
              <div className="text-sm text-gray-600 font-medium">/100</div>
            </div>
          </div>
        </div>

        <div className="mt-4 text-center">
          <span className="text-sm text-gray-700 font-medium">Status: </span>
          <span className={`text-sm font-bold ${
            riskStatus === 'VERIFIED' ? 'text-green-600' : 
            riskStatus === 'MEDIUM' ? 'text-amber-600' : 
            riskStatus === 'HIGH RISK' ? 'text-red-600' : 'text-gray-600'
          }`}>{riskStatus}</span>
        </div>

        {customerProfile && (
          <div className="mt-3 pt-3 border-t border-gray-200 text-sm space-y-2">
            <div className="flex justify-between text-gray-700">
              <span className="font-medium">Credit Score:</span>
              <span className="text-[#004589] font-bold">{customerProfile.credit_score || 'N/A'}</span>
            </div>
            {customerProfile.behavioral_flags && (
              <>
                <div className="flex justify-between text-gray-700">
                  <span className="font-medium">Behavioral Score:</span>
                  <span className="text-green-600 font-bold">{customerProfile.behavioral_flags.behavioral_score || 0}/100</span>
                </div>
                <div className="flex justify-between text-gray-700">
                  <span className="font-medium">Risk Category:</span>
                  <span className={`font-bold ${
                    customerProfile.behavioral_flags.risk_category === 'LOW' ? 'text-green-600' :
                    customerProfile.behavioral_flags.risk_category === 'MEDIUM' ? 'text-amber-600' :
                    customerProfile.behavioral_flags.risk_category === 'HIGH' ? 'text-red-600' :
                    customerProfile.behavioral_flags.risk_category === 'CRITICAL' ? 'text-red-700' :
                    customerProfile.behavioral_flags.risk_category === 'FRAUD_CONFIRMED' ? 'text-red-900' :
                    'text-gray-600'
                  }`}>{customerProfile.behavioral_flags.risk_category}</span>
                </div>
                <div className="flex justify-between text-gray-700">
                  <span className="font-medium">Doc Status:</span>
                  <span className={`font-bold ${
                    customerProfile.behavioral_flags.document_authenticity === 'VERIFIED' ? 'text-green-600' :
                    customerProfile.behavioral_flags.document_authenticity === 'UNDER_REVIEW' ? 'text-blue-600' :
                    customerProfile.behavioral_flags.document_authenticity === 'SUSPICIOUS' ? 'text-red-600' :
                    'text-gray-500'
                  }`}>{customerProfile.behavioral_flags.document_authenticity}</span>
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Behavioral Analysis */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-[#3B82F6]" />
          <h3 className="font-semibold text-[#004589]">Behavioral Analysis</h3>
        </div>

        <div className="h-24 -mx-2">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={behaviorData}>
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#3B82F6" 
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 flex items-center justify-between text-sm">
          <span className="text-gray-600">Conversation Quality:</span>
          <span className={`font-medium ${
            customerProfile?.behavioral_flags?.conversation_quality === 'EXCELLENT' ? 'text-green-600' :
            customerProfile?.behavioral_flags?.conversation_quality === 'GOOD' ? 'text-blue-600' :
            customerProfile?.behavioral_flags?.conversation_quality === 'POOR' ? 'text-red-600' :
            'text-gray-600'
          }`}>
            {customerProfile?.behavioral_flags?.conversation_quality || 'PENDING'}
          </span>
        </div>

        {customerProfile && customerProfile.behavioral_flags && (
          <div className="mt-2 text-sm text-gray-700">
            Behavioral Score: <span className="text-[#3B82F6] font-semibold">{customerProfile.behavioral_flags.behavioral_score}/100</span>
          </div>
        )}
      </div>

      {/* System Logs */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-4">
          <Terminal className="w-5 h-5 text-[#3B82F6]" />
          <h3 className="font-semibold text-[#004589]">Activity Logs</h3>
        </div>

        <div className="bg-gray-50 rounded p-3 h-48 overflow-y-auto text-sm space-y-1">
          {logEvents.length === 0 ? (
            <div className="text-gray-500">Waiting for customer activity...</div>
          ) : (
            logEvents.map((log: any, index) => (
              <div key={index} className="animate-fadeIn">
                <span className="text-gray-500">[{log.time}] </span>
                <span className={log.level === 'success' ? 'text-green-600' : 'text-blue-600'}>
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