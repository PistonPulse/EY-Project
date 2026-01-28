import React from 'react';
import { Activity, CheckCircle, XCircle, AlertCircle, Phone, Server, Database, CreditCard, Zap } from 'lucide-react';

interface LogEntry {
  timestamp: string;
  type: 'info' | 'success' | 'warning' | 'error' | 'decision' | 'api_call' | 'api_response';
  message: string;
  agent?: string;
  service?: string;
}

interface ActivityLogsProps {
  events: any[];
}

export function ActivityLogs({ events }: ActivityLogsProps) {
  // Convert events to log entries with better categorization
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
      // ====== NEW: External API Call Events ======
      case 'API_CALL_CRM':
        type = 'api_call';
        message = `🔗 Connecting to CRM Server... (${event.data.endpoint || '/crm/customer'})`;
        break;
      case 'API_RESPONSE_CRM':
        type = 'api_response';
        message = event.data.found 
          ? `✅ CRM: Found customer "${event.data.name}" (KYC: ${event.data.kyc_status})`
          : `⚠️ CRM: Customer not found`;
        break;
      case 'API_CALL_CREDIT_BUREAU':
        type = 'api_call';
        message = `🔗 Connecting to CIBIL Credit Bureau... (PAN: ${event.data.pan || 'XXXX'})`;
        break;
      case 'API_RESPONSE_CREDIT_BUREAU':
        type = 'api_response';
        const score = event.data.credit_score;
        const band = event.data.score_band;
        message = `✅ CIBIL: Credit Score ${score} (${band})`;
        break;
      case 'API_CALL_OFFER_ENGINE':
        type = 'api_call';
        message = `🔗 Connecting to Offer Engine... (Income: ₹${(event.data.income/1000).toFixed(0)}K)`;
        break;
      case 'API_RESPONSE_OFFER_ENGINE':
        type = 'api_response';
        const limit = event.data.pre_approved_limit;
        message = `✅ Offer Engine: Pre-approved ₹${(limit/100000).toFixed(1)}L`;
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
      agent: event.data?.agent,
      service: event.data?.service
    };
  });

  const getIcon = (type: LogEntry['type'], service?: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'error':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-amber-600" />;
      case 'decision':
        return <Phone className="w-4 h-4 text-blue-600" />;
      case 'api_call':
        return <Server className="w-4 h-4 text-purple-600 animate-pulse" />;
      case 'api_response':
        return <Zap className="w-4 h-4 text-cyan-600" />;
      default:
        return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  const getTextColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'warning':
        return 'text-amber-600';
      case 'decision':
        return 'text-blue-600';
      case 'api_call':
        return 'text-purple-600 font-medium';
      case 'api_response':
        return 'text-cyan-700';
      default:
        return 'text-gray-700';
    }
  };

  const getBgColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'api_call':
        return 'bg-purple-50 border-l-2 border-purple-400';
      case 'api_response':
        return 'bg-cyan-50 border-l-2 border-cyan-400';
      default:
        return 'hover:bg-white';
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-6 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Activity className="w-5 h-5 text-[#3B82F6]" />
        <h3 className="font-semibold text-[#004589] text-lg">Activity Timeline</h3>
        <span className="ml-auto text-xs text-gray-500">{logs.length} events</span>
      </div>
      
      <div className="bg-gray-50 rounded p-3 h-[calc(100%-3rem)] overflow-y-auto space-y-2">
        {logs.length === 0 ? (
          <div className="text-gray-500 text-sm text-center py-4">
            No activity yet... Waiting for customer interactions
          </div>
        ) : (
          logs.slice().reverse().map((log, index) => (
            <div
              key={index}
              className={`flex items-start gap-2 p-2 rounded transition-colors ${getBgColor(log.type)}`}
            >
              <div className="mt-0.5">{getIcon(log.type, log.service)}</div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs text-gray-500">
                    {new Date(log.timestamp).toLocaleTimeString()}
                  </span>
                  {log.agent && (
                    <span className="text-xs text-[#3B82F6] bg-blue-50 px-1.5 py-0.5 rounded">
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
