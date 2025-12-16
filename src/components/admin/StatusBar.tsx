import { Activity, Wifi } from 'lucide-react';

interface StatusBarProps {
  activeSessions: number;
}

export function StatusBar({ activeSessions }: StatusBarProps) {
  return (
    <div className="bg-white border-b border-gray-200 shadow-sm">
      <div className="px-6 py-3 flex items-center justify-between">
        {/* Left Side */}
        <div className="flex items-center gap-4">
          <Activity className="w-5 h-5 text-[#3B82F6] animate-pulse" />
          <span className="text-[#004589] font-semibold">
            Tata Capital AI Underwriter - System Active
          </span>
        </div>

        {/* Right Side */}
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-gray-700">Active Agents: <span className="text-[#3B82F6] font-semibold">5</span></span>
          </div>
          <div className="text-gray-700">
            Live Sessions: <span className="text-[#004589] font-semibold">{activeSessions}</span>
          </div>
          <div className="flex items-center gap-2">
            <Wifi className="w-4 h-4 text-green-500" />
            <span className="text-green-600 font-medium">Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}