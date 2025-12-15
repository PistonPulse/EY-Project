import { Activity, Wifi } from 'lucide-react';

interface StatusBarProps {
  activeSessions: number;
}

export function StatusBar({ activeSessions }: StatusBarProps) {
  return (
    <div className="bg-black/50 backdrop-blur-sm border-b border-emerald-500/30">
      <div className="px-6 py-3 flex items-center justify-between">
        {/* Left Side */}
        <div className="flex items-center gap-4">
          <Activity className="w-5 h-5 text-emerald-400 animate-pulse" />
          <span className="font-mono text-emerald-400 font-semibold">
            Tata Capital AI Underwriter // SYSTEM ONLINE
          </span>
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-6 font-mono text-sm">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse"></div>
            <span className="text-gray-300">Active Agents: <span className="text-emerald-400">5</span></span>
          </div>
          <div className="text-gray-300">
            Live Sessions: <span className="text-amber-400">{activeSessions}</span>
          </div>
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-emerald-400" />
            <span className="text-emerald-400">WebSocket: Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}