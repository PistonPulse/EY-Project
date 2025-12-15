import React from 'react';
import { Activity, CheckCircle, XCircle, AlertCircle, Phone } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'decision';
  message: string;
  agent?: string;
}

interface ActivityLogsProps {
  events: any[];
}

export function ActivityLogs({ events }: ActivityLogsProps) {
  // Convert events to log entries
  const logs: LogEntry[] = events.map(event => {
    let type: LogEntry['type'] = 'info';
    let message = '';
    
    switch (event.type) {
      case 'VERIFICATION_INITIATED':
        type = 'info';
        message = `Verification started for ${event.data.phone}`;
        break;
      case 'CRM_LOOKUP_SUCCESS':
        type = 'success';
        message = `Customer profile found: ${event.data.name}`;
        break;
      case 'CRM_NO_MATCH':
        type = 'warning';
        message = `No existing profile for ${event.data.phone}`;
        break;
      case 'CREDIT_SCORE_RETRIEVED':
        type = event.data.score >= 700 ? 'success' : 'warning';
        message = `Credit score: ${event.data.score} (${event.data.category})`;
        break;
      case 'UNDERWRITING_APPROVED':
        type = 'success';
        message = `Loan approved: ₹${(event.data.amount / 100000).toFixed(1)}L`;
        break;
      case 'UNDERWRITING_CONDITIONAL':
        type = 'warning';
        message = `Conditional approval - Document verification required`;
        break;
      case 'DOCUMENTS_UPLOADED':
        type = 'info';
        message = `${event.data.count} documents uploaded by ${event.data.customer}`;
        break;
      case 'DOCUMENT_VERIFIED':
        type = 'success';
        message = `Income verified: ₹${(event.data.salary / 1000).toFixed(0)}K/month`;
        break;
      case 'LOAN_APPROVED':
        type = 'success';
        message = `Final approval: ₹${(event.data.amount / 100000).toFixed(1)}L for ${event.data.customer}`;
        break;
      case 'FRAUD_DETECTED':
        type = 'error';
        message = `FRAUD ALERT: ${event.data.reason}`;
        break;
      case 'APPLICATION_REJECTED':
        type = 'error';
        message = `Application rejected: ${event.data.reason}`;
        break;
      case 'MANUAL_DECISION':
        type = 'decision';
        if (event.data.decision === 'accept') {
          message = `✓ ACCEPTED by underwriter (${event.data.type} review)`;
        } else if (event.data.decision === 'decline') {
          message = `✗ DECLINED by underwriter (${event.data.type} review)`;
        } else {
          message = `📞 CONTACT flagged by underwriter (${event.data.type} review)`;
        }
        break;
      case 'log':
        type = event.data.level || 'info';
        message = event.data.message;
        break;
      default:
        message = event.type;
    }
    
    return {
      timestamp: event.timestamp,
      type,
      message,
      agent: event.data?.agent
    };
  });

  const getIcon = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-400" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case 'decision':
        return <Phone className="w-4 h-4 text-blue-400" />;
      default:
        return <Activity className="w-4 h-4 text-gray-400" />;
    }
  };

  const getTextColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return 'text-green-300';
      case 'error':
        return 'text-red-300';
      case 'warning':
        return 'text-yellow-300';
      case 'decision':
        return 'text-blue-300';
      default:
        return 'text-gray-300';
    }
  };

  return (
    <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-emerald-500/30 p-6 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-emerald-400" />
        <h3 className="font-mono text-emerald-400 text-lg font-semibold">Activity Logs</h3>
        <span className="ml-auto text-xs text-gray-500">{logs.length} events</span>
      </div>
      
      <div className="bg-black/60 rounded p-3 h-[calc(100%-3rem)] overflow-y-auto space-y-2 scrollbar-thin scrollbar-thumb-emerald-500/30">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-sm text-center py-4">
            No activity yet... Waiting for customer interactions
          </div>
        ) : (
          logs.slice().reverse().map((log, index) => (
            <div
              key={index}
              className="flex items-start gap-2 p-2 hover:bg-slate-800/50 rounded transition-colors"
            >
              <div className="mt-0.5">{getIcon(log.type)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-500">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  {log.agent && (
                    <span className="text-xs text-purple-400 bg-purple-500/10 px-1.5 py-0.5 rounded">
                      {log.agent}
                    </span>
                  )}
                </div>
                <p className={`text-sm ${getTextColor(log.type)} leading-snug`}>
                  {log.message}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
