import { Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'bot';
  text: string;
  time: string;
}

interface LiveChatMirrorProps {
  events: any[];
}

export function LiveChatMirror({ events }: LiveChatMirrorProps) {
  // Extract chat messages from events
  const chatMessages: Message[] = events
    .filter(e => e.type === 'user_message' || e.type === 'bot_response')
    .map(e => ({
      role: e.type === 'user_message' ? 'user' : 'bot',
      text: e.type === 'user_message' ? e.data.message : e.data.response,
      time: new Date(e.timestamp).toLocaleTimeString('en-US', { hour12: false })
    }))
    .slice(-8); // Keep last 8 messages

  return (
    <div className="bg-gradient-to-br from-slate-800/40 to-slate-900/40 backdrop-blur-sm rounded-lg border border-cyan-500/30 p-4 h-[calc(100vh-120px)] flex flex-col">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-cyan-500/30">
        <div className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"></div>
        <h3 className="font-mono text-cyan-400">Live Customer Interaction</h3>
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 scrollbar-thin scrollbar-thumb-cyan-500/30">
        {chatMessages.length === 0 ? (
          <div className="text-gray-500 text-center mt-8">
            Waiting for customer to start chat...
          </div>
        ) : (
          chatMessages.map((message, index) => (
            <div key={index} className="animate-fadeIn">
              <div className="flex items-start gap-2 mb-1">
                {message.role === 'bot' ? (
                  <Bot className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-1" />
                ) : (
                  <User className="w-4 h-4 text-blue-400 flex-shrink-0 mt-1" />
                )}
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-xs font-mono ${message.role === 'bot' ? 'text-emerald-400' : 'text-blue-400'}`}>
                      {message.role === 'bot' ? 'AI Agent' : 'Customer'}
                    </span>
                    <span className="text-xs text-gray-500 font-mono">{message.time}</span>
                  </div>
                  <p className="text-sm text-gray-300 break-words">{message.text}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}