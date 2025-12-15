import { Bot, Sparkles, MessageCircle } from 'lucide-react';

export function AIChatBanner() {
  const handleChatClick = () => {
    // This will trigger the chat widget to open
    const chatButton = document.querySelector('[data-chat-trigger]') as HTMLButtonElement;
    if (chatButton) {
      chatButton.click();
    }
  };

  return (
    <div className="bg-gradient-to-r from-[#004589] via-[#0066cc] to-[#3B82F6] py-3 sm:py-4 px-4 sm:px-6 sticky top-[65px] sm:top-[73px] z-40 shadow-lg">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 sm:gap-4">
          <div className="flex items-center gap-3 sm:gap-4 w-full sm:w-auto">
            <div className="relative flex-shrink-0">
              <div className="absolute inset-0 bg-yellow-400 rounded-full blur-lg opacity-50 animate-pulse"></div>
              <div className="relative bg-white rounded-full p-2 sm:p-3">
                <Bot className="w-5 h-5 sm:w-6 sm:h-6 text-[#004589]" />
              </div>
            </div>
            <div className="text-white flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-base sm:text-lg font-semibold">Get Instant Loan Approval with AI</h3>
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 text-yellow-400 animate-pulse" />
              </div>
              <p className="text-xs sm:text-sm text-blue-100">
                Our AI Agent approves loans in 5 minutes - 100% paperless & instant disbursal
              </p>
            </div>
          </div>
          <button
            onClick={handleChatClick}
            className="bg-yellow-400 text-[#004589] px-6 sm:px-8 py-2.5 sm:py-3 rounded-lg hover:bg-yellow-300 transition-all flex items-center gap-2 shadow-xl hover:shadow-2xl transform hover:scale-105 whitespace-nowrap text-sm sm:text-base font-semibold w-full sm:w-auto justify-center"
          >
            <MessageCircle className="w-4 h-4 sm:w-5 sm:h-5" />
            <span>Chat with AI Now</span>
          </button>
        </div>
      </div>
    </div>
  );
}
