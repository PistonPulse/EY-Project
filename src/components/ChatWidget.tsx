import { MessageCircle, X, Send, Upload, Download, CheckCircle, RotateCcw } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";
import jsPDF from 'jspdf';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}

interface LoanDetails {
  amount: number;
  interest_rate: number;
  tenure_months: number;
  monthly_emi: number;
}

// Helper function to open chat widget
export const openChatWidget = () => {
  const chatButton = document.querySelector('[data-chat-trigger]') as HTMLButtonElement;
  if (chatButton) {
    chatButton.click();
  }
};

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const [showUpload, setShowUpload] = useState(false);
  const [showSanctionLetter, setShowSanctionLetter] = useState(false);
  const [loanDetails, setLoanDetails] = useState<LoanDetails | null>(null);
  const [customerName, setCustomerName] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [waitingForDocs, setWaitingForDocs] = useState(false);
  const [currentScenario, setCurrentScenario] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<boolean>(false);
  const [decisionType, setDecisionType] = useState<'credit' | 'underwriting' | 'documents' | 'final' | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      // Initial greeting - conversational and warm
      const greeting: Message = {
        role: 'assistant',
        content: 'Hello! Welcome to Tata Capital 😊\n\nI\'m your AI Loan Assistant, and I\'m here to help you get instant pre-approval for a personal loan - the entire process takes less than a minute!\n\n**To get started, please provide:**\n1. Your full name\n2. Your mobile number',
        timestamp: new Date().toISOString()
      };
      setMessages([greeting]);
    }
  }, [isOpen]);

  // Helper function to send WebSocket event to admin dashboard
  const sendAdminEvent = (eventType: string, eventData: any) => {
    try {
      fetch('http://localhost:8000/api/admin-event', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: eventType,
          data: eventData,
          timestamp: new Date().toISOString()
        })
      }).catch(() => {}); // Silent fail if backend unavailable
    } catch (e) {}
  };

  // Helper to add bot message with typing delay
  const addBotMessage = async (content: string, delay: number = 2500) => {
    await new Promise(resolve => setTimeout(resolve, delay));
    const botMessage: Message = {
      role: 'assistant',
      content,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, botMessage]);
  };

  // Handle manual decision (Accept/Decline/Contact)
  const handleDecision = async (decision: 'accept' | 'decline' | 'contact') => {
    setPendingDecision(false);
    setIsLoading(true);
    
    sendAdminEvent('MANUAL_DECISION', { decision, type: decisionType, customer: customerName });
    
    if (decision === 'accept') {
      await addBotMessage(`✅ Decision recorded: ACCEPTED by underwriter\n\nProceeding to next step...`, 1500);
      // Continue with the flow based on decision type
      if (decisionType === 'credit') {
        await continueAfterCreditDecision(true);
      } else if (decisionType === 'documents') {
        await continueAfterDocumentDecision(true);
      } else if (decisionType === 'final') {
        await continueAfterFinalDecision(true);
      }
    } else if (decision === 'decline') {
      await addBotMessage(`❌ Decision recorded: DECLINED by underwriter\n\nApplication cannot proceed.`, 1500);
      await addBotMessage(`💼 Sales Agent: Thank you for your interest, ${customerName || 'valued customer'}.\n\nUnfortunately, we are unable to process your loan application at this time due to risk assessment results.\n\nYou may reapply after 3 months or contact our support team at 1800-209-0088 for personalized assistance.`, 2500);
      setIsLoading(false);
    } else if (decision === 'contact') {
      await addBotMessage(`📞 Decision recorded: CONTACT CUSTOMER for clarification\n\nMarked for manual review...`, 1500);
      await addBotMessage(`💼 Sales Agent: Thank you, ${customerName || 'valued customer'}!\n\nYour application requires additional verification. Our relationship manager will contact you within 24 hours at your registered mobile number.\n\nApplication ID: TC${Date.now().toString().slice(-8)}\nStatus: PENDING MANUAL REVIEW`, 2500);
      setIsLoading(false);
    }
  };

  // Continue functions after decisions
  const continueAfterCreditDecision = async (approved: boolean) => {
    if (!approved) return;
    
    // Step 7: Master Agent → Underwriting Agent
    await addBotMessage('🔄 Master Agent: Handing over to Underwriting Agent for eligibility assessment...', 1500);
    sendAdminEvent('UNDERWRITING_INITIATED', { customer: customerName, amount: 500000 });
    
    // Step 8: Underwriting Agent - Risk Assessment
    await addBotMessage('📊 Underwriting Agent: Loading risk assessment model...', 1800);
    await addBotMessage('📊 Underwriting Agent: Calculating debt-to-income ratio...', 2000);
    await addBotMessage('📊 Underwriting Agent:\n\n🔸 Requested Amount: ₹5,00,000\n🔸 Pre-approved Limit: ₹20,00,000\n🔸 Credit Score: 785 (Threshold: 700) ✓\n🔸 Monthly Income: ₹1,25,000\n🔸 Existing EMI: ₹18,500\n🔸 Proposed EMI: ₹16,134\n🔸 Total EMI: ₹34,634 (27.7% of income) ✓', 2500);
    await addBotMessage('✅ Underwriting Agent: **RULE A APPLIED**\n\nLoan amount ≤ Pre-approved limit\nCredit score ≥ 700\nEMI ratio < 50%\n\n**RESULT: INSTANT APPROVAL** ✓', 1500);
    sendAdminEvent('UNDERWRITING_APPROVED', { rule: 'A', amount: 500000, limit: 2000000 });
    
    // DECISION POINT 2: Final Approval
    await addBotMessage('⚖️ System: Risk assessment complete. Awaiting final approval...', 1500);
    setDecisionType('final');
    setPendingDecision(true);
    setIsLoading(false);
  };

  const continueAfterDocumentDecision = async (approved: boolean) => {
    if (!approved) return;
    // Add logic to continue after document verification approval
    setIsLoading(false);
  };

  const continueAfterFinalDecision = async (approved: boolean) => {
    if (!approved) return;
    
    // Step 9: Master Agent → Sanction Letter Generator
    await addBotMessage('🔄 Master Agent: Approval confirmed! Triggering Sanction Letter Generator...', 900);
    sendAdminEvent('SANCTION_LETTER_GENERATION', { customer: customerName, amount: 500000 });
    
    // Step 10: Sanction Letter Generator
    await addBotMessage('📄 Sanction Letter Generator: Initializing document template...', 1500);
    await addBotMessage('📄 Sanction Letter Generator: Calculating EMI schedule and interest breakdown...', 2000);
    await addBotMessage('📄 Sanction Letter Generator: Adding terms, conditions, and legal clauses...', 1800);
    await addBotMessage('📄 Sanction Letter Generator: Applying digital signature and encryption...', 1500);
    await addBotMessage('✅ Sanction Letter Generator: Document ready for download!', 1200);
    sendAdminEvent('LOAN_APPROVED', { amount: 500000, customer: customerName });
    
    // Step 11: Sales Agent - Final Message
    setLoanDetails({
      amount: 500000,
      interest_rate: 10.5,
      tenure_months: 36,
      monthly_emi: 16134
    });
    setShowSanctionLetter(true);
    await addBotMessage(`🎉 Sales Agent: Congratulations, ${customerName}! 🎊\n\nYour Personal Loan has been **APPROVED**!\n\n💰 Loan Amount: ₹5,00,000\n📈 Interest Rate: 10.5% per annum\n📅 Tenure: 36 months\n💳 Monthly EMI: ₹16,134\n📄 Processing Fee: 2% + GST\n⚡ Disbursal: Within 24 hours\n\nYour official sanction letter is ready below. It's valid for 30 days.\n\nWelcome to the Tata Capital family! We're honored to support your home renovation journey. 🏡✨`, 2000);
    
    setIsLoading(false);
  };

  const sendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputValue,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    const currentInput = inputValue;
    setInputValue('');
    setIsLoading(true);

    try {
      // ========== BACKEND API CALL - LET BACKEND HANDLE DEMO MODE ==========
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout
      
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: currentInput,
          session_id: sessionId
        }),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.session_id) {
        setSessionId(data.session_id);
      }

      // Get response text from API
      const responseText = data.response || 'I received your message but got an empty response.';

      // Clean and format the response text
      const cleanText = (text: string): string => {
        return text
          // Remove bold markers
          .replace(/\*\*/g, '')
          // Remove emoji and special characters but keep basic punctuation
          .replace(/[👋🎉🌟💰📈⏰💳📊💵⬇️😊😄⚠️🤔💪✅🎯😅🚀📄📎✋💬]/g, '')
          // Remove bullet points and replace with clean format
          .replace(/•/g, '')
          // Remove typing indicators
          .replace(/\*typing\*/g, '')
          // Remove loading indicators
          .replace(/⏳/g, '')
          // Clean up multiple spaces
          .replace(/\s+/g, ' ')
          // Clean up multiple newlines
          .replace(/\n\s*\n\s*\n/g, '\n\n')
          .trim();
      };

      // PHASE 7: Display the response directly
      const cleanedResponse = cleanText(responseText);
      if (cleanedResponse) {
        const botMessage: Message = {
          role: 'assistant',
          content: cleanedResponse,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, botMessage]);
      }
      
      // Debug: Log the response data
      console.log('📊 API Response:', {
        show_upload: data.show_upload,
        show_sanction_letter: data.show_sanction_letter,
        decision: data.decision
      });
      
      if (data.show_upload) {
        console.log('✅ Setting showUpload to TRUE');
        setShowUpload(true);
      } else {
        console.log('❌ show_upload is FALSE or undefined');
      }
      
      if (data.show_sanction_letter) {
        setShowSanctionLetter(true);
        setLoanDetails(data.loan_details);
      }
      
      if (data.customer_name) {
        setCustomerName(data.customer_name);
      }

      // OLD FRONTEND SCRIPTED DEMO CODE - COMMENTED OUT SINCE BACKEND HANDLES THIS
      /*
      // Handle second input (loan details) for existing scenarios
      if (currentScenario === 'priya' && !currentInput.includes('9876543210')) {
        // Continue Priya's flow with loan details
        await handlePriyaLoanDetails(currentInput);
        return;
      }
      
      if (currentScenario === 'amit' && !currentInput.includes('9123456789')) {
        // Continue Amit's flow with loan details
        await handleAmitLoanDetails(currentInput);
        return;
      }
      
      if (currentScenario === 'rajesh' && !currentInput.includes('9988776655')) {
        // Continue Rajesh's flow with loan details
        await handleRajeshLoanDetails(currentInput);
        return;
      }
      
      // SCENARIO A: Prime Customer (Priya) - 9876543210
      // Requires: Name, Phone, Loan Amount, Purpose, Employment confirmation
      if (false && currentInput.includes('9876543210')) {
        // Extract name from user input
        const nameMatch = currentInput.match(/(?:I am|I'm|my name is|this is)\s+([A-Za-z]+)/i);
        const name = nameMatch ? nameMatch[1] + ' Sharma' : 'Priya Sharma';
        setCustomerName(name);
        setCurrentScenario('priya');

        // Step 1: Sales Agent - Welcome with name confirmation
        await addBotMessage(`💼 Sales Agent: Thank you for contacting Tata Capital, ${name}! I see you're calling from 9876543210. Let me pull up your details...`, 2000);
        
        // Step 2: Master Agent hands to Verification Agent
        await addBotMessage('🔄 Master Agent: Routing to Verification Agent for KYC check...', 1500);
        sendAdminEvent('VERIFICATION_INITIATED', { phone: '9876543210', name });
        
        // Step 3: Verification Agent - CRM Lookup
        await addBotMessage('🔍 Verification Agent: Connecting to CRM database...', 2500);
        await addBotMessage('🔍 Verification Agent: Retrieving customer profile from Tata Capital records...', 2000);
        await addBotMessage(`✅ Verification Agent: Profile found!\n\n👤 Name: ${name}\n📍 Location: Mumbai, Maharashtra\n🏢 Employer: Tata Consultancy Services\n💼 Designation: Senior Software Engineer\n📧 Email: priya.sharma@email.com\n✓ KYC Status: VERIFIED`, 3000);
        sendAdminEvent('CRM_LOOKUP_SUCCESS', { phone: '9876543210', name, risk: 'LOW' });
        
        // Step 4: Sales Agent - Loan Discussion - WAIT FOR USER INPUT
        await addBotMessage(`💼 Sales Agent: Great to have you back, ${name}! 😊\n\nI can see you have an excellent relationship with us. Based on your profile, you're eligible for a personal loan.\n\nPlease type your response with:\n1. Loan amount you're looking for\n2. Purpose of this loan\n3. Preferred tenure (months)\n\nExample: "I need 5 lakhs for home renovation, 36 months"`, 3000);
        
        setIsLoading(false);
        return; // Wait for actual user input
        
        // Step 5: Master Agent → Credit Bureau Check
        await addBotMessage('🔄 Master Agent: Initiating credit bureau verification...', 900);
        sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: name });
        
        // Step 6: Verification Agent - Credit Score Fetch
        await addBotMessage('🔍 Verification Agent: Querying CIBIL TransUnion database...', 1200);
        await addBotMessage('🔍 Verification Agent: Retrieving credit history...', 1000);
        await addBotMessage('✅ Verification Agent: Credit report received!\n\n📊 Credit Score: 785/900 (EXCELLENT)\n✓ No defaults or late payments\n✓ Credit utilization: 28% (Healthy)\n✓ Active loans: 1 (Car Loan)\n✓ Payment history: 100% on-time', 1800);
        sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 785, category: 'EXCELLENT' });
        
        // Step 7: Master Agent → Underwriting Agent
        await addBotMessage('🔄 Master Agent: Handing over to Underwriting Agent for eligibility assessment...', 900);
        sendAdminEvent('UNDERWRITING_INITIATED', { customer: name, amount: 500000 });
        
        // Step 8: Underwriting Agent - Risk Assessment
        await addBotMessage('📊 Underwriting Agent: Analyzing application parameters...', 1200);
        await addBotMessage('📊 Underwriting Agent:\n\n🔸 Requested Amount: ₹5,00,000\n🔸 Pre-approved Limit: ₹20,00,000\n🔸 Credit Score: 785 (Threshold: 700) ✓\n🔸 Monthly Income: ₹1,25,000\n🔸 Existing EMI: ₹18,500\n🔸 Proposed EMI: ₹16,134\n🔸 Total EMI: ₹34,634 (27.7% of income) ✓', 2000);
        await addBotMessage('✅ Underwriting Agent: **RULE A APPLIED**\n\nLoan amount ≤ Pre-approved limit\nCredit score ≥ 700\nEMI ratio < 50%\n\n**RESULT: INSTANT APPROVAL** ✓', 1500);
        sendAdminEvent('UNDERWRITING_APPROVED', { rule: 'A', amount: 500000, limit: 2000000 });
        
        // Step 9: Master Agent → Sanction Letter Generator
        await addBotMessage('🔄 Master Agent: Approval confirmed! Triggering Sanction Letter Generator...', 900);
        sendAdminEvent('SANCTION_LETTER_GENERATION', { customer: name, amount: 500000 });
        
        // Step 10: Sanction Letter Generator
        await addBotMessage('📄 Sanction Letter Generator: Generating official document...', 1200);
        await addBotMessage('📄 Sanction Letter Generator: Calculating EMI schedule...', 1000);
        await addBotMessage('📄 Sanction Letter Generator: Adding terms and conditions...', 1000);
        await addBotMessage('📄 Sanction Letter Generator: Applying digital signature...', 1000);
        await addBotMessage('✅ Sanction Letter Generator: Document ready for download!', 800);
        sendAdminEvent('LOAN_APPROVED', { amount: 500000, customer: name });
        
        // Step 11: Sales Agent - Final Message
        setLoanDetails({
          amount: 500000,
          interest_rate: 10.5,
          tenure_months: 36,
          monthly_emi: 16134
        });
        setShowSanctionLetter(true);
        await addBotMessage(`🎉 Sales Agent: Congratulations, ${name}! 🎊\n\nYour Personal Loan has been **APPROVED**!\n\n💰 Loan Amount: ₹5,00,000\n📈 Interest Rate: 10.5% per annum\n📅 Tenure: 36 months\n💳 Monthly EMI: ₹16,134\n📄 Processing Fee: 2% + GST\n⚡ Disbursal: Within 24 hours\n\nYour official sanction letter is ready below. It's valid for 30 days.\n\nWelcome to the Tata Capital family! We're honored to support your home renovation journey. 🏡✨`, 2000);

        setIsLoading(false);
        return;
      }

      // SCENARIO B: Conditional Approval Customer (Amit) - 9123456789
      // Requires: Multi-step verification, document upload, income verification
      if (false && currentInput.includes('9123456789')) {
        // Extract name from user input
        const nameMatch = currentInput.match(/(?:I am|I'm|my name is|this is)\s+([A-Za-z]+)/i);
        const name = nameMatch ? nameMatch[1] + ' Patel' : 'Amit Patel';
        setCustomerName(name);
        setCurrentScenario('amit');

        // Step 1: Sales Agent - Initial Contact with name confirmation
        await addBotMessage(`💼 Sales Agent: Good day, ${name}! Thank you for reaching out to Tata Capital. I can see you're calling from 9123456789.`, 2000);
        
        // Step 2: Master Agent → Verification
        await addBotMessage('🔄 Master Agent: Initiating customer verification process...', 1500);
        sendAdminEvent('VERIFICATION_INITIATED', { phone: '9123456789', name });
        
        // Step 3: Verification Agent - CRM Check
        await addBotMessage('🔍 Verification Agent: Searching customer database...', 2500);
        await addBotMessage('🔍 Verification Agent: Fetching profile from CRM...', 2000);
        await addBotMessage(`✅ Verification Agent: Customer profile retrieved!\n\n👤 Name: ${name}\n📍 Location: Ahmedabad, Gujarat\n🏢 Employer: TechLogix Solutions Pvt Ltd\n💼 Designation: Software Developer\n📧 Email: amit.patel@email.com\n⚠️ KYC Status: VERIFIED (Last updated 6 months ago)`, 3000);
        sendAdminEvent('CRM_LOOKUP_SUCCESS', { phone: '9123456789', name, risk: 'MEDIUM' });
        
        // Step 4: Sales Agent - Loan Inquiry - WAIT FOR USER INPUT
        await addBotMessage(`💼 Sales Agent: Welcome, ${name}! 👋\n\nI see you're working with TechLogix Solutions. How can we assist you today?\n\nPlease type your response with:\n1. Desired loan amount?\n2. Purpose (business, wedding, education, medical, home)?\n3. Preferred tenure?\n\nExample: "I need 8 lakhs for my wedding expenses. 48 months tenure"`, 3000);
        
        setIsLoading(false);
        return; // Wait for actual user input
        
        // Step 5: Master Agent → Credit Check
        await addBotMessage('🔄 Master Agent: Proceeding with credit bureau verification...', 900);
        sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: name });
        
        // Step 6: Verification Agent - Credit Report
        await addBotMessage('🔍 Verification Agent: Connecting to CIBIL database...', 1200);
        await addBotMessage('🔍 Verification Agent: Pulling credit report...', 1000);
        await addBotMessage('⚠️ Verification Agent: Credit report received\n\n📊 Credit Score: 680/900 (FAIR)\n⚠️ Active loans: 3 (Personal + Credit Card + Two-Wheeler)\n⚠️ Credit utilization: 78% (High)\n⚠️ Recent inquiries: 2 in last 3 months\n✓ Payment history: 95% on-time (1 late payment)', 1800);
        sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 680, category: 'FAIR' });
        
        // Step 7: Master Agent → Underwriting
        await addBotMessage('🔄 Master Agent: Routing to Underwriting Agent for risk assessment...', 900);
        sendAdminEvent('UNDERWRITING_INITIATED', { customer: name, amount: 800000 });
        
        // Step 8: Underwriting Agent - Initial Assessment
        await addBotMessage('📊 Underwriting Agent: Analyzing application parameters...', 1200);
        await addBotMessage('📊 Underwriting Agent:\n\n🔸 Requested Amount: ₹8,00,000\n🔸 Pre-approved Limit: ₹5,00,000\n🔸 Ratio: 160% of limit (>100% but <200%)\n🔸 Credit Score: 680 (Threshold: 700) ⚠️\n🔸 Monthly Income: ₹55,000 (stated)\n🔸 Existing EMI burden: HIGH', 1800);
        await addBotMessage('⚠️ Underwriting Agent: **RULE B TRIGGERED**\n\nAmount exceeds pre-approved limit but within 2x threshold.\nCredit score below 700.\n\n**DECISION: DOCUMENT VERIFICATION MANDATORY**', 1500);
        sendAdminEvent('UNDERWRITING_CONDITIONAL', { rule: 'B', amount: 800000, limit: 500000 });
        
        // Step 9: Master Agent → Verification (Document Request)
        await addBotMessage('🔄 Master Agent: Requesting Verification Agent to collect income documents...', 900);
        
        // Step 10: Document Request - WAIT FOR ACTUAL UPLOADS
        await addBotMessage(`📄 Verification Agent: ${name}, to process your application for ₹8 lakhs, we need to verify your income.\n\nPlease upload ALL 3 documents:\n1️⃣ Latest Salary Slip (November 2025)\n2️⃣ Bank Statement (Last 6 months)\n3️⃣ PAN Card copy\n\nClick the upload button below to select each document.`, 3000);
        
        setShowUpload(true);
        setWaitingForDocs(true);
        setUploadedDocs([]);
        setIsLoading(false);
        return; // Wait for user to upload 3 documents
      }
      
      // AMIT SCENARIO - Continue after 3 documents uploaded
      if (currentScenario === 'amit' && uploadedDocs.length === 3 && currentInput.includes('continue_amit_docs')) {
        setIsLoading(true);
        setWaitingForDocs(false);
        
        // Step 11: Master Agent → Back to Verification
        await addBotMessage('🔄 Master Agent: All 3 documents received. Initiating verification scan...', 1800);
        sendAdminEvent('DOCUMENTS_UPLOADED', { count: 3, customer: customerName });
        
        // Step 12: Verification Agent - Document Analysis
        await addBotMessage('🔍 Verification Agent: Extracting data from salary slip...', 2500);
        await addBotMessage('🔍 Verification Agent: Parsing bank statement transactions...', 1200);
        await addBotMessage('🔍 Verification Agent: Validating PAN card details...', 1000);
        await addBotMessage('✅ Verification Agent: Document verification complete!\n\n💰 Gross Salary: ₹55,000/month\n💰 Net Salary: ₹47,850/month\n🏦 Average Bank Balance: ₹45,000\n✓ Salary credits: Regular (TechLogix)\n✓ PAN: CDEFG5678H (Valid)\n✓ No bounced transactions', 2000);
        sendAdminEvent('DOCUMENT_VERIFIED', { salary: 55000, net: 47850, pan: 'CDEFG5678H' });
        
        // Step 13: Master Agent → Back to Underwriting
        await addBotMessage('🔄 Master Agent: Income verified. Resuming underwriting analysis...', 900);
        
        // Step 14: Underwriting Agent - EMI Affordability Check
        await addBotMessage('📊 Underwriting Agent: Calculating EMI affordability...', 1200);
        await addBotMessage('📊 Underwriting Agent:\n\n🔸 Net Monthly Income: ₹47,850\n🔸 Existing EMIs: ₹12,000\n🔸 Proposed EMI: ₹25,868\n🔸 Total EMI: ₹37,868\n🔸 EMI Ratio: 79.1% of net income\n\n⚠️ **ALERT: Exceeds 50% threshold!**', 1800);
        await addBotMessage('📊 Underwriting Agent: Adjusting loan parameters...', 1200);
        await addBotMessage('📊 Underwriting Agent:\n\n🔄 Revised Offer:\n🔸 Approved Amount: ₹6,50,000 (reduced from ₹8L)\n🔸 Tenure: 48 months\n🔸 Interest Rate: 12.5% (higher risk)\n🔸 Monthly EMI: ₹21,017\n🔸 Total EMI: ₹33,017 (69% of income)\n\n✅ Manageable EMI burden achieved!', 2000);
        await addBotMessage('✅ Underwriting Agent: **CONDITIONAL APPROVAL GRANTED**\n\nAmount adjusted for affordability.\nDocument verification successful.\n\n**RESULT: APPROVED ₹6.5L** ✓', 1500);
        sendAdminEvent('UNDERWRITING_APPROVED', { rule: 'B', amount: 650000, conditions: 'Reduced Amount' });
        
        // Step 15: Master Agent → Sanction Letter
        await addBotMessage('🔄 Master Agent: Approval confirmed! Triggering Sanction Letter Generator...', 900);
        sendAdminEvent('SANCTION_LETTER_GENERATION', { customer: name, amount: 650000 });
        
        // Step 16: Sanction Letter Generator
        await addBotMessage('📄 Sanction Letter Generator: Preparing official document...', 1200);
        await addBotMessage('📄 Sanction Letter Generator: Computing amortization schedule...', 1000);
        await addBotMessage('📄 Sanction Letter Generator: Embedding terms and conditions...', 1000);
        await addBotMessage('📄 Sanction Letter Generator: Applying authorization seal...', 1000);
        await addBotMessage('✅ Sanction Letter Generator: Letter generated successfully!', 800);
        sendAdminEvent('LOAN_APPROVED', { amount: 650000, customer: name });
        
        // Step 17: Sales Agent - Final Offer
        setLoanDetails({
          amount: 650000,
          interest_rate: 12.5,
          tenure_months: 48,
          monthly_emi: 21017
        });
        setShowSanctionLetter(true);
        await addBotMessage(`✅ Sales Agent: Congratulations, ${name}! 🎊\n\nAfter careful evaluation, we're pleased to offer you a Personal Loan!\n\n💰 Approved Amount: ₹6,50,000\n📈 Interest Rate: 12.5% per annum\n📅 Tenure: 48 months\n💳 Monthly EMI: ₹21,017\n📄 Processing Fee: 2.5% + GST\n⚡ Disbursal: 48 hours\n\n📌 Note: Amount adjusted from ₹8L to ₹6.5L to ensure comfortable EMI management.\n\nYour sanction letter is ready below. Wishing you a wonderful wedding! 💒✨`, 2500);

        setIsLoading(false);
        return;
      }

      // SCENARIO C: Fraud Detection (Rajesh) - 9988776655
      // Requires: Multi-step fraud detection, PAN validation, NPCI alert, rejection with empathy
      if (false && currentInput.includes('9988776655')) {
        const nameMatch = currentInput.match(/(?:I am|I'm|my name is|this is)\s+([A-Za-z]+)/i);
        const name = nameMatch ? nameMatch[1] + ' Kumar' : 'Rajesh Kumar';
        setCustomerName(name);
        setCurrentScenario('rajesh');

        // Step 1: Sales Agent - Initial Welcome
        await addBotMessage(`💼 Sales Agent: Thank you for contacting Tata Capital, ${name}! I can see you're calling from 9988776655.`, 2000);
        
        // Step 2: Master Agent → Verification
        await addBotMessage('🔄 Master Agent: Initiating customer verification protocol...', 1500);
        sendAdminEvent('VERIFICATION_INITIATED', { phone: '9988776655', name });
        
        // Step 3: Verification Agent - CRM Search
        await addBotMessage('🔍 Verification Agent: Searching customer records...', 2500);
        await addBotMessage('🔍 Verification Agent: Querying CRM database...', 2000);
        await addBotMessage('⚠️ Verification Agent: **ALERT: No existing customer profile found**\n\nPhone number: 9988776655\nPrevious applications: None\nKYC status: NOT VERIFIED', 3000);
        sendAdminEvent('CRM_NO_MATCH', { phone: '9988776655', name });
        
        // Step 4: Sales Agent - Basic Information Request - WAIT FOR USER INPUT
        await addBotMessage(`💼 Sales Agent: Welcome, ${name}! 👋\n\nI see this is your first application with us. That's great!\n\nTo get started, please type your response with:\n1. What loan amount do you need?\n2. Purpose of the loan?\n3. Your current employer name?\n4. Monthly income?\n\nExample: "I need 15 lakhs urgently for business. I earn 2.5 lakhs per month. Self-employed"`, 3000);
        
        setIsLoading(false);
        return; // Wait for actual user input
        
        // Step 5: Master Agent → Credit Bureau Check
        await addBotMessage('🔄 Master Agent: High loan amount detected. Initiating credit bureau verification...', 1800);
        sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: name, amount: 1500000 });
        
        // Step 6: Verification Agent - Credit Report Retrieval
        await addBotMessage('🔍 Verification Agent: Connecting to CIBIL database...', 2500);
        await addBotMessage('🔍 Verification Agent: Fetching credit history...', 2500);
        await addBotMessage('🚨 Verification Agent: **CRITICAL ALERT - CREDIT REPORT**\n\n📊 Credit Score: 350/900 (VERY POOR)\n🚨 CIBIL Status: HIGH RISK\n❌ Writeoff Accounts: 2\n❌ Settled Accounts: 3\n❌ Active NPA: 1 account\n❌ Legal Proceedings: Pending\n⚠️ Total Outstanding Debt: ₹18,50,000', 3500);
        sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 350, category: 'VERY_POOR', risk: 'HIGH' });
        
        // Step 6.5: Request Documents for High-Risk Case
        await addBotMessage(`💼 Sales Agent: ${name}, due to the concerns in your credit report, we need to verify your documents before proceeding.\n\n📎 Please upload 2 documents:\n1. PAN Card\n2. Latest CIBIL Report\n\nUse the upload button below. ⬇️`, 2500);
        setShowUpload(true);
        setWaitingForDocs(true);
        setUploadedDocs([]);
        setIsLoading(false);
        return; // Wait for document uploads - fraud detection continues in handleRajeshDocumentsContinue()
      }

      */
      // END OF OLD FRONTEND DEMO CODE

    } catch (error: any) {
      console.error('Chat error:', error);
      let errorContent = 'I apologize, but I\'m having trouble connecting to the server. Please try again in a moment.';
      
      if (error.name === 'AbortError') {
        errorContent = 'The request took too long. The AI is processing - please wait a moment and try again.';
      } else if (error.message?.includes('Failed to fetch')) {
        errorContent = 'Cannot connect to the server. Please make sure the backend is running on http://localhost:8000';
      }
      
      const errorMessage: Message = {
        role: 'assistant',
        content: errorContent,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Add uploaded document to tracking
    const newDocs = [...uploadedDocs, file.name];
    setUploadedDocs(newDocs);
    
    // Show upload confirmation message
    const uploadMsg: Message = {
      role: 'user',
      content: `📎 Uploaded: ${file.name}`,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, uploadMsg]);
    
    setIsLoading(true);
    
    try {
      // Send file to backend
      const formData = new FormData();
      formData.append('file', file);
      formData.append('session_id', sessionId);
      formData.append('document_count', newDocs.length.toString());
      
      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      });
      
      const data = await response.json();
      
      // Clean and format the response text
      const cleanText = (text: string): string => {
        return text
          .replace(/\*\*/g, '')
          .replace(/[👋🎉🌟💰📈⏰💳📊💵⬇️😊😄⚠️🤔💪✅🎯😅🚀📄📎✋💬🥳]/g, '')
          .replace(/•/g, '')
          .replace(/\*typing\*/g, '')
          .replace(/⏳/g, '')
          .replace(/\s+/g, ' ')
          .replace(/\n\s*\n\s*\n/g, '\n\n')
          .trim();
      };

      // Split response into parts for gradual display
      const responseParts = data.response.split('\n\n').filter((part: string) => part.trim());
      
      // Display messages gradually
      for (let i = 0; i < responseParts.length; i++) {
        const cleanedPart = cleanText(responseParts[i]);
        if (!cleanedPart) continue;
        
        await new Promise(resolve => setTimeout(resolve, i === 0 ? 500 : 1200));
        
        const botMessage: Message = {
          role: 'assistant',
          content: cleanedPart,
          timestamp: new Date().toISOString()
        };
        
        setMessages(prev => [...prev, botMessage]);
      }
      
      // Check if we need to continue showing upload or proceed
      if (data.continue_upload) {
        setShowUpload(true);
      } else {
        setShowUpload(false);
        
        // If final response, show sanction letter
        if (data.show_sanction_letter) {
          setShowSanctionLetter(true);
          setLoanDetails(data.loan_details);
        }
      }
      
    } catch (error) {
      console.error('Upload error:', error);
      const errorMsg: Message = {
        role: 'assistant',
        content: `✅ Document ${newDocs.length} received: ${file.name}\n\nPlease upload the remaining documents.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
    }
    
    setIsLoading(false);
    
    // Reset file input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };
  
  const handleAmitDocumentsContinue = async () => {
    if (currentScenario !== 'amit' || uploadedDocs.length !== 3) return;
    
    setIsLoading(true);
    setWaitingForDocs(false);
    
    try {
      // Step 11: Master Agent → Back to Verification
      await addBotMessage('🔄 Master Agent: All 3 documents received. Initiating verification scan...', 1800);
      sendAdminEvent('DOCUMENTS_UPLOADED', { count: 3, customer: customerName });
      
      // Step 12: Verification Agent - Document Analysis
      await addBotMessage('🔍 Verification Agent: Extracting data from salary slip...', 2500);
      await addBotMessage('🔍 Verification Agent: Parsing bank statement transactions...', 2500);
      await addBotMessage('🔍 Verification Agent: Validating PAN card details...', 2000);
      await addBotMessage('✅ Verification Agent: Document verification complete!\n\n💰 Gross Salary: ₹55,000/month\n💰 Net Salary: ₹47,850/month\n🏦 Average Bank Balance: ₹45,000\n✓ Salary credits: Regular (TechLogix)\n✓ PAN: CDEFG5678H (Valid)\n✓ No bounced transactions', 3000);
      sendAdminEvent('DOCUMENT_VERIFIED', { salary: 55000, net: 47850, pan: 'CDEFG5678H' });
      
      // Step 13: Master Agent → Back to Underwriting
      await addBotMessage('🔄 Master Agent: Income verified. Resuming underwriting analysis...', 1800);
      
      // Step 14: Underwriting Agent - EMI Affordability Check
      await addBotMessage('📊 Underwriting Agent: Calculating EMI affordability...', 2500);
      await addBotMessage('📊 Underwriting Agent:\n\n🔸 Net Monthly Income: ₹47,850\n🔸 Existing EMIs: ₹12,000\n🔸 Proposed EMI: ₹25,868\n🔸 Total EMI: ₹37,868\n🔸 EMI Ratio: 79.1% of net income\n\n⚠️ **ALERT: Exceeds 50% threshold!**', 3000);
      await addBotMessage('⚠️ Underwriting Agent: **Cannot approve at current amount**\n\nOur bank representative will call you within 24 hours to discuss:\n• Possible loan amount adjustment\n• Alternative tenure options\n• Co-applicant possibilities\n\nApplication Status: **PENDING MANUAL REVIEW**', 3000);
      sendAdminEvent('UNDERWRITING_MANUAL_REVIEW', { rule: 'B', amount: 800000, reason: 'EMI exceeds threshold' });
      
      await addBotMessage(`💼 Sales Agent: Thank you for your patience, ${customerName}.\n\nYour application is under review due to high EMI burden. Our relationship manager will contact you at 9123456789 within 24 hours to find the best solution.\n\nReference Number: TCPL${Date.now()}\n\nWe appreciate your interest in Tata Capital! 🙏`, 2500);
      
      setIsLoading(false);
    } catch (error) {
      console.error('Error in document continuation:', error);
      setIsLoading(false);
    }
  };

  const handleRajeshDocumentsContinue = async () => {
    if (currentScenario !== 'rajesh' || uploadedDocs.length !== 2) return;
    
    setIsLoading(true);
    setWaitingForDocs(false);
    
    try {
      // Step 7: Verification Agent - Document Analysis
      await addBotMessage('🔄 Master Agent: Both documents received. Initiating verification...', 1800);
      sendAdminEvent('DOCUMENTS_UPLOADED', { count: 2, customer: customerName });
      
      await addBotMessage('🔍 Verification Agent: Validating PAN card details...', 2500);
      await addBotMessage('🔍 Verification Agent: Cross-checking with Income Tax database...', 2500);
      await addBotMessage('🚨 Verification Agent: **PAN VALIDATION FAILED**\n\n❌ PAN: ZZZZZ9999Z (INVALID FORMAT)\n❌ Income Tax records: NO MATCH\n❌ PAN-Aadhaar link: NOT FOUND\n🚨 Possible fraudulent document detected', 3500);
      sendAdminEvent('PAN_VALIDATION_FAILED', { pan: 'ZZZZZ9999Z', status: 'INVALID' });
      
      // Step 8: Verification Agent - NPCI Fraud Check
      await addBotMessage('🔍 Verification Agent: Checking NPCI fraud database...', 2500);
      await addBotMessage('🚨 Verification Agent: **NPCI FRAUD ALERT**\n\n⚠️ Phone 9988776655: FLAGGED\n❌ Multiple loan applications across 8 NBFCs in last 30 days\n❌ Identity theft reports: 2 cases\n❌ Suspicious transaction patterns detected\n❌ Linked to known fraud network\n🚨 **RECOMMENDATION: IMMEDIATE REJECTION**', 3500);
      sendAdminEvent('NPCI_FRAUD_ALERT', { phone: '9988776655', fraud_score: 95, networks: 8 });
      
      // Step 9: Master Agent → Underwriting Agent (Escalation)
      await addBotMessage('🔄 Master Agent: **FRAUD DETECTED** - Escalating to Underwriting Agent for final decision...', 1800);
      sendAdminEvent('UNDERWRITING_INITIATED', { customer: customerName, amount: 1500000, risk: 'CRITICAL' });
      
      // Step 10: Underwriting Agent - Risk Assessment
      await addBotMessage('📊 Underwriting Agent: Analyzing risk parameters...', 2500);
      await addBotMessage('📊 Underwriting Agent:\n\n🔸 Requested Amount: ₹15,00,000\n🔸 Credit Score: 350 (Threshold: 700) ❌\n🔸 PAN Status: INVALID ❌\n🔸 NPCI Status: FRAUD FLAGGED ❌\n🔸 Debt History: Multiple defaults ❌\n🔸 Identity Verification: FAILED ❌', 3000);
      await addBotMessage('❌ Underwriting Agent: **RULE C TRIGGERED**\n\nCredit score significantly below 700.\nIdentity verification failed.\nFraud indicators present.\nExisting debt obligations unpaid.\n\n**DECISION: APPLICATION REJECTED**', 3000);
      sendAdminEvent('UNDERWRITING_REJECTED', { rule: 'C', reason: 'Fraud + Credit Score', score: 350 });
      
      // Step 11: Master Agent → Compliance Notification
      await addBotMessage('🔄 Master Agent: Notifying compliance team for regulatory reporting...', 1800);
      sendAdminEvent('FRAUD_DETECTED', { phone: '9988776655', name: customerName, risk: 'HIGH', reason: 'Multiple fraud indicators', rule: 'C' });
      
      // Step 12: Sales Agent - Empathetic Rejection
      await addBotMessage(`I sincerely apologize, ${customerName}, but I'm unable to proceed with your loan application at this time.\n\nOur system has identified some concerns that require further review:\n\n• Credit history concerns\n• Identity verification issues\n• Multiple recent loan applications\n\nFor your security and protection, we recommend:\n\n1. Check your credit report at CIBIL.com\n2. Verify your PAN-Aadhaar linking status\n3. Contact our fraud prevention team if you believe this is an error\n\n📞 Customer Support: 1800-209-4477\n🏢 Visit nearest Tata Capital branch for manual verification\n\nWe take financial security very seriously and appreciate your understanding. 🙏`, 4000);

      setIsLoading(false);
    } catch (error) {
      console.error('Error in Rajesh document continuation:', error);
      setIsLoading(false);
    }
  };

  const handlePriyaLoanDetails = async (input: string) => {
    // Step 5: Master Agent → Credit Bureau Check
    await addBotMessage('🔄 Master Agent: Initiating credit bureau verification...', 1500);
    sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: customerName });
    
    // Step 6: Verification Agent - Credit Score Fetch
    await addBotMessage('🔍 Verification Agent: Connecting to CIBIL TransUnion API...', 2000);
    await addBotMessage('🔍 Verification Agent: Authenticating secure connection...', 1800);
    await addBotMessage('🔍 Verification Agent: Querying credit history database...', 2200);
    await addBotMessage('✅ Verification Agent: Credit report received!\n\n📊 Credit Score: 785/900 (EXCELLENT)\n✓ No defaults or late payments\n✓ Credit utilization: 28% (Healthy)\n✓ Active loans: 1 (Car Loan)\n✓ Payment history: 100% on-time', 2500);
    sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 785, category: 'EXCELLENT' });
    
    // DECISION POINT 1: Credit Check Review
    await addBotMessage('⚖️ System: Credit verification complete. Awaiting underwriter review...', 1500);
    setDecisionType('credit');
    setPendingDecision(true);
    setIsLoading(false);
  };

  const handleAmitLoanDetails = async (input: string) => {
    // Step 5: Master Agent → Credit Check
    await addBotMessage('🔄 Master Agent: Proceeding with credit bureau verification...', 1500);
    sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: customerName });
    
    // Step 6: Verification Agent - Credit Report
    await addBotMessage('🔍 Verification Agent: Establishing secure connection to CIBIL...', 2000);
    await addBotMessage('🔍 Verification Agent: Fetching comprehensive credit history...', 2200);
    await addBotMessage('🔍 Verification Agent: Analyzing payment patterns across accounts...', 1800);
    await addBotMessage('⚠️ Verification Agent: Credit report received\n\n📊 Credit Score: 680/900 (FAIR)\n⚠️ Active loans: 3 (Personal + Credit Card + Two-Wheeler)\n⚠️ Credit utilization: 78% (High)\n⚠️ Recent inquiries: 2 in last 3 months\n✓ Payment history: 95% on-time (1 late payment)', 1800);
    sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 680, category: 'FAIR' });
    
    // Step 7: Master Agent → Underwriting
    await addBotMessage('🔄 Master Agent: Routing to Underwriting Agent for risk assessment...', 900);
    sendAdminEvent('UNDERWRITING_INITIATED', { customer: customerName, amount: 800000 });
    
    // Step 8: Underwriting Agent - Initial Assessment
    await addBotMessage('📊 Underwriting Agent: Analyzing loan application...', 1200);
    await addBotMessage('📊 Underwriting Agent:\n\n🔸 Requested Amount: ₹8,00,000\n🔸 Credit Score: 680 (Threshold: 700) ⚠️\n🔸 Credit utilization: 78% (High) ⚠️\n🔸 Multiple active loans detected\n🔸 Score below excellent range', 1800);
    await addBotMessage('⚠️ Underwriting Agent: **RULE B TRIGGERED**\n\nCredit score below 700 but above 650.\nHigh credit utilization detected.\nHigh loan amount relative to income.\n\n**ACTION REQUIRED:** Income document verification needed', 1800);
    sendAdminEvent('UNDERWRITING_CONDITIONAL', { rule: 'B', reason: 'Income verification required', amount: 800000 });
    
    // Step 9: Master Agent → Back to Verification (Document Request)
    await addBotMessage('🔄 Master Agent: Requesting income verification documents...', 900);
    sendAdminEvent('DOCUMENT_REQUEST_INITIATED', { customer: customerName, type: 'income_proof' });
    
    // Step 10: Verification Agent - Document Request
    await addBotMessage(`📄 Verification Agent: ${customerName}, to proceed with your application for ₹8,00,000, we need to verify your income.\n\nPlease upload the following 3 documents:\n1. Latest salary slip\n2. Last 3 months bank statement\n3. CIBIL report\n\nUse the upload button below to submit each document. ⬇️`, 2500);
    
    setShowUpload(true);
    setWaitingForDocs(true);
    setUploadedDocs([]);
    setIsLoading(false);
  };

  const handleRajeshLoanDetails = async (input: string) => {
    // Step 5: Master Agent → Credit Bureau Check
    await addBotMessage('🔄 Master Agent: High loan amount detected. Initiating enhanced verification...', 2000);
    sendAdminEvent('CREDIT_CHECK_INITIATED', { customer: customerName, amount: 1500000 });
    
    // Step 6: Verification Agent - Credit Report Retrieval
    await addBotMessage('🔍 Verification Agent: Connecting to CIBIL database...', 2200);
    await addBotMessage('🔍 Verification Agent: Running comprehensive background check...', 2500);
    await addBotMessage('🔍 Verification Agent: Cross-checking multiple credit bureaus...', 2000);
    await addBotMessage('🚨 Verification Agent: **CRITICAL ALERT - CREDIT REPORT**\n\n📊 Credit Score: 350/900 (VERY POOR)\n🚨 CIBIL Status: HIGH RISK\n❌ Writeoff Accounts: 2\n❌ Settled Accounts: 3\n❌ Active NPA: 1 account\n❌ Legal Proceedings: Pending\n⚠️ Total Outstanding Debt: ₹18,50,000', 3500);
    sendAdminEvent('CREDIT_SCORE_RETRIEVED', { score: 350, category: 'VERY_POOR', risk: 'HIGH' });
    
    // Step 6.5: Request Documents for High-Risk Case
    await addBotMessage(`💼 Sales Agent: ${customerName}, due to the concerns in your credit report, we need to verify your documents before proceeding.\n\n📎 Please upload 2 documents:\n1. PAN Card\n2. Latest CIBIL Report\n\nUse the upload button below. ⬇️`, 2500);
    setShowUpload(true);
    setWaitingForDocs(true);
    setUploadedDocs([]);
    setIsLoading(false);
  };

  const handleResetChat = async () => {
    if (confirm('Start a new conversation? This will clear the current chat.')) {
      try {
        // Call backend to reset session
        const formData = new URLSearchParams();
        formData.append('session_id', sessionId);
        
        await fetch('http://localhost:8000/api/reset-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: formData
        });
      } catch (error) {
        console.error('Reset error:', error);
      }
      
      // Reset frontend state
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setMessages([]);
      setSessionId(newSessionId);
      setShowUpload(false);
      setShowSanctionLetter(false);
      setLoanDetails(null);
      setCustomerName(null);
    }
  };

  const downloadSanctionLetter = () => {
    const today = new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    const validUntil = new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    const refNo = `TC/${Math.random().toString(36).substr(2, 9).toUpperCase()}`;

    // Create PDF document
    const doc = new jsPDF();
    const pageWidth = doc.internal.pageSize.getWidth();
    let yPos = 20;

    // Header with border
    doc.setDrawColor(0, 69, 137);
    doc.setLineWidth(0.5);
    doc.rect(10, 10, pageWidth - 20, 25);
    
    // Company name
    doc.setFontSize(16);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 69, 137);
    doc.text('TATA CAPITAL LIMITED', pageWidth / 2, 20, { align: 'center' });
    
    doc.setFontSize(9);
    doc.setFont('helvetica', 'normal');
    doc.text('Corporate Office: One World Centre, Mumbai', pageWidth / 2, 27, { align: 'center' });
    doc.text('CIN: U65990MH2007PLC164987', pageWidth / 2, 32, { align: 'center' });

    yPos = 50;

    // Title
    doc.setFontSize(14);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 0, 0);
    doc.text('LOAN SANCTION LETTER', pageWidth / 2, yPos, { align: 'center' });
    yPos += 15;

    // Reference details
    doc.setFontSize(10);
    doc.setFont('helvetica', 'normal');
    doc.text(`Reference No: ${refNo}`, 15, yPos);
    doc.text(`Date: ${today}`, pageWidth - 15, yPos, { align: 'right' });
    yPos += 15;

    // Addressee
    doc.text(`To,`, 15, yPos);
    yPos += 5;
    doc.setFont('helvetica', 'bold');
    doc.text(`${customerName || 'Valued Customer'}`, 15, yPos);
    yPos += 10;

    doc.setFont('helvetica', 'normal');
    doc.text(`Dear ${customerName || 'Customer'},`, 15, yPos);
    yPos += 10;

    // Subject
    doc.setFont('helvetica', 'bold');
    doc.text('Subject: APPROVAL OF PERSONAL LOAN APPLICATION', 15, yPos);
    yPos += 10;

    // Body text
    doc.setFont('helvetica', 'normal');
    const bodyText = 'We are pleased to inform you that your Personal Loan application has been APPROVED by our AI-Powered Underwriting System after thorough evaluation of your credit profile, income verification, and risk assessment.';
    const splitBody = doc.splitTextToSize(bodyText, pageWidth - 30);
    doc.text(splitBody, 15, yPos);
    yPos += splitBody.length * 5 + 10;

    // Loan Details Box
    doc.setDrawColor(0, 128, 0);
    doc.setLineWidth(0.3);
    doc.rect(15, yPos, pageWidth - 30, 45);
    
    doc.setFontSize(11);
    doc.setFont('helvetica', 'bold');
    doc.setTextColor(0, 100, 0);
    doc.text('SANCTIONED LOAN DETAILS', pageWidth / 2, yPos + 7, { align: 'center' });
    
    yPos += 15;
    doc.setFontSize(10);
    doc.setTextColor(0, 0, 0);
    doc.setFont('helvetica', 'normal');
    doc.text(`Loan Amount Sanctioned:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`Rs. ${loanDetails?.amount.toLocaleString('en-IN')}`, pageWidth - 20, yPos, { align: 'right' });
    
    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Annual Interest Rate:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`${loanDetails?.interest_rate}% per annum`, pageWidth - 20, yPos, { align: 'right' });
    
    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Loan Tenure:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`${loanDetails?.tenure_months} months`, pageWidth - 20, yPos, { align: 'right' });
    
    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Monthly EMI:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`Rs. ${loanDetails?.monthly_emi.toLocaleString('en-IN')}`, pageWidth - 20, yPos, { align: 'right' });
    
    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Processing Fee:`, 20, yPos);
    doc.text(`2% + GST`, pageWidth - 20, yPos, { align: 'right' });

    yPos += 15;

    // Terms & Conditions
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text('TERMS & CONDITIONS', 15, yPos);
    yPos += 7;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    const terms = [
      `1. This sanction is valid until ${validUntil} (30 days from issue date).`,
      '2. Disbursement subject to verification of original documents.',
      '3. EMI repayment to commence from next month via auto-debit.',
      '4. Late payment charges: 2% per month on overdue amount.',
      '5. Loan covered under Credit Life Insurance (optional).'
    ];
    
    terms.forEach(term => {
      const splitTerm = doc.splitTextToSize(term, pageWidth - 30);
      doc.text(splitTerm, 15, yPos);
      yPos += splitTerm.length * 4 + 2;
    });

    yPos += 8;

    // Next Steps
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(11);
    doc.text('NEXT STEPS', 15, yPos);
    yPos += 7;

    doc.setFont('helvetica', 'normal');
    doc.setFontSize(9);
    doc.text('• Submit original KYC documents at nearest Tata Capital branch', 15, yPos);
    yPos += 5;
    doc.text('• Sign loan agreement and provide cancelled cheque', 15, yPos);
    yPos += 5;
    doc.text('• Loan will be disbursed within 24 hours of documentation', 15, yPos);
    yPos += 12;

    // Contact Info
    doc.setFont('helvetica', 'bold');
    doc.text('For any queries, contact us:', 15, yPos);
    yPos += 5;
    doc.setFont('helvetica', 'normal');
    doc.text('Customer Care: 1800-209-4477 | Email: customercare@tatacapital.com', 15, yPos);
    yPos += 5;
    doc.text('Website: www.tatacapital.com', 15, yPos);
    yPos += 15;

    // Footer signature
    doc.text('Thank you for choosing Tata Capital. We look forward to serving you.', 15, yPos);
    yPos += 10;
    doc.text('Yours faithfully,', 15, yPos);
    yPos += 15;
    doc.setFont('helvetica', 'bold');
    doc.text('Authorized Signatory', 15, yPos);
    doc.setFont('helvetica', 'normal');
    yPos += 4;
    doc.text('Tata Capital Limited', 15, yPos);

    // Bottom note
    yPos = doc.internal.pageSize.getHeight() - 15;
    doc.setFontSize(8);
    doc.setTextColor(100, 100, 100);
    doc.text('** This is a system-generated document **', pageWidth / 2, yPos, { align: 'center' });
    doc.text('Generated by: TataSmartAgent AI Underwriter v3.0', pageWidth / 2, yPos + 4, { align: 'center' });

    // Save PDF
    doc.save(`Tata_Capital_Sanction_Letter_${customerName || 'Customer'}_${Date.now()}.pdf`);
  };

  return (
    <>
      {/* Floating Chat Button */}
      {!isOpen && (
        <div className="fixed bottom-6 right-6 z-[9999]">
          <div className="relative">
            {/* Nudge Tooltip - Horizontal 2-line layout */}
            <div className="absolute bottom-full right-0 mb-4 bg-white px-5 py-3 rounded-xl shadow-2xl border-2 border-[#004589] w-52">
              <p className="text-gray-800 text-base font-semibold leading-snug">
                Need a loan?<br />
                Chat with us!
              </p>
            </div>
            
            {/* Chat Button */}
            <button
              data-chat-trigger
              onClick={() => setIsOpen(true)}
              className="bg-[#004589] text-white w-16 h-16 rounded-full shadow-2xl hover:bg-[#003366] transition-all flex items-center justify-center hover:scale-110 border-4 border-yellow-400"
            >
              <MessageCircle className="w-8 h-8" />
            </button>
          </div>
        </div>
      )}

      {/* Chat Window - Centered Modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black/50 z-[99998]" onClick={() => setIsOpen(false)}></div>
          
          {/* Centered Chat Window */}
          <div 
            className="bg-white rounded-2xl shadow-2xl border-2 border-gray-300 w-[600px] h-[650px] flex flex-col fixed z-[99999]"
            style={{
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              maxHeight: '90vh'
            }}
          >
              {/* Header */}
              <div className="bg-gradient-to-r from-[#004589] to-[#0066cc] text-white p-4 rounded-t-2xl flex items-center justify-between">
              <div className="flex items-center gap-3">
                <img src={tataLogo} alt="Tata Capital" className="h-10 object-contain" />
                <div>
                  <div className="flex items-center gap-2">
                    <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-lg font-semibold">Tata Capital Assistant</span>
                  </div>
                  <p className="text-sm opacity-90">AI-Powered Underwriter</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleResetChat}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                  title="Start New Chat"
                >
                  <RotateCcw className="w-5 h-5" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
            </div>

            {/* Chat Content */}
            <div className="flex-1 p-4 overflow-y-auto bg-gray-50 scroll-smooth" style={{ scrollBehavior: 'smooth' }}>
              <div className="space-y-4">
                {messages.map((message, index) => (
                  <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}>
                    {/* Avatar */}
                    {message.role === 'assistant' && (
                      <div className="w-8 h-8 bg-[#3B82F6] rounded-full flex items-center justify-center text-white flex-shrink-0">
                        AI
                      </div>
                    )}
                    {message.role === 'user' && (
                      <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center text-white flex-shrink-0">
                        U
                      </div>
                    )}
                    
                    {/* Message Bubble */}
                    <div className={`max-w-[70%] ${message.role === 'user' ? 'bg-[#3B82F6] text-white' : 'bg-white'} p-4 rounded-xl shadow-md break-words`}>
                      <p className={`text-sm leading-relaxed font-normal whitespace-pre-wrap ${message.role === 'user' ? 'text-white' : 'text-slate-700'}`}>
                        {message.content}
                      </p>
                    </div>
                  </div>
                ))}

                {/* Sanction Letter Card */}
                {showSanctionLetter && loanDetails && (
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-500 rounded-lg p-4 animate-fadeIn">
                    <div className="flex items-center gap-2 mb-3">
                      <CheckCircle className="w-6 h-6 text-green-600" />
                      <h4 className="text-green-900">Loan Approved! 🎉</h4>
                    </div>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-700">Sanctioned Amount:</span>
                        <span className="text-gray-900">₹{loanDetails.amount.toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Interest Rate:</span>
                        <span className="text-gray-900">{loanDetails.interest_rate}% p.a.</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Tenure:</span>
                        <span className="text-gray-900">{loanDetails.tenure_months} months</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Monthly EMI:</span>
                        <span className="text-gray-900">₹{loanDetails.monthly_emi.toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                    <button
                      onClick={downloadSanctionLetter}
                      className="mt-4 w-full bg-green-600 text-white py-2 rounded-lg flex items-center justify-center gap-2 hover:bg-green-700 transition-colors"
                    >
                      <Download className="w-4 h-4" />
                      Download Sanction Letter
                    </button>
                  </div>
                )}

                {/* Decision Buttons */}
                {pendingDecision && !isLoading && (
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-500 rounded-lg p-4 animate-fadeIn">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-3 h-3 bg-blue-600 rounded-full animate-pulse"></div>
                      <h4 className="text-blue-900 font-semibold">⚖️ Manual Review Required</h4>
                    </div>
                    <p className="text-sm text-gray-700 mb-4">
                      {decisionType === 'credit' && 'Credit report retrieved. Please review credit score and history.'}
                      {decisionType === 'underwriting' && 'Risk assessment complete. Review loan parameters and affordability.'}
                      {decisionType === 'documents' && 'Documents uploaded and verified. Review income details.'}
                      {decisionType === 'final' && 'All checks complete. Make final decision on application.'}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleDecision('accept')}
                        className="flex-1 bg-green-600 text-white py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-green-700 transition-colors font-medium"
                      >
                        ✓ Accept
                      </button>
                      <button
                        onClick={() => handleDecision('decline')}
                        className="flex-1 bg-red-600 text-white py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-red-700 transition-colors font-medium"
                      >
                        ✗ Decline
                      </button>
                      <button
                        onClick={() => handleDecision('contact')}
                        className="flex-1 bg-amber-600 text-white py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-amber-700 transition-colors font-medium"
                      >
                        📞 Contact
                      </button>
                    </div>
                  </div>
                )}

                {/* Loading Indicator */}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 bg-[#3B82F6] rounded-full flex items-center justify-center text-white flex-shrink-0">
                      AI
                    </div>
                    <div className="bg-white p-3 rounded-lg shadow-sm">
                      <div className="flex gap-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200 bg-white rounded-b-2xl flex-shrink-0">
              <div className="mb-3 space-y-2">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf,.jpg,.jpeg,.png"
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isLoading}
                  className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg flex items-center justify-center gap-2 hover:bg-blue-700 transition-colors disabled:opacity-50 font-semibold shadow-md"
                >
                  <Upload className="w-5 h-5" />
                  📎 Upload Document
                </button>
              </div>
              
              <div className="flex gap-2">
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Type your message..."
                  disabled={isLoading}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:border-[#3B82F6] disabled:bg-gray-100"
                />
                <button
                  onClick={sendMessage}
                  disabled={isLoading || !inputValue.trim()}
                  className="bg-[#3B82F6] text-white p-2 rounded-lg hover:bg-[#2563EB] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}