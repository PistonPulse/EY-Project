import { MessageCircle, X, Send, Upload, Download, CheckCircle, RotateCcw, Clock, Eye } from 'lucide-react';
import { useState, useRef, useEffect, useCallback } from 'react';
import tataLogo from "../assets/Tata_Capital_Logo-01.jpg";
import jsPDF from 'jspdf';
import { SanctionLetter } from './SanctionLetter';

/**
 * ================================================================================
 * PHASE 10: VISUAL POLISH, TIMING REALISM & TONE CORRECTION
 * ================================================================================
 * 
 * PURPOSE:
 * --------
 * Make the chatbot feel like a real NBFC product, not a demo. This involves:
 * 
 * 1. TIMING REALISM: Adding deliberate delays (1-2s) for verification operations
 *    - WHY: Instant verification feels fake. Real banking systems take time.
 *    - Banks intentionally show "verifying" states to build trust and indicate
 *      that actual work is happening (even if technically faster).
 *    - This matches user expectations from mobile banking apps.
 * 
 * 2. LOADING STATES: Contextual loading messages that explain what's happening
 *    - WHY: "Processing..." is vague. "Verifying PAN with NSDL..." is trustworthy.
 *    - Users understand that real verification takes time and involves external systems.
 * 
 * 3. PROFESSIONAL TONE: Remove emojis after KYC, use banking language
 *    - WHY: Initial greeting can be friendly, but verification stages should be formal.
 *    - Real banks switch to formal tone when handling sensitive operations.
 * 
 * 4. INPUT DISABLING: Prevent user input during verification delays
 *    - WHY: Users shouldn't be able to interrupt mid-verification.
 *    - This prevents confusion and maintains conversation integrity.
 * 
 * 5. EDGE CASE HANDLING: Session persistence, idle states, graceful recovery
 *    - WHY: Real banking apps don't lose state on refresh or idle timeout.
 * 
 * ================================================================================
 * WHY TIMING DELAYS INCREASE TRUST IN BANKING UX:
 * ================================================================================
 * 
 * Research in banking UX shows that users DISTRUST instant verification:
 * - "That was too fast - did it really check anything?"
 * - "My bank takes 30 seconds, this took 0.5s - seems fake"
 * 
 * Optimal delays for perceived legitimacy (based on mobile banking UX studies):
 * - OTP sending: 1.5-2s (SMS gateway simulation)
 * - Identity verification: 1.5-2s (bureau API simulation)
 * - Credit check: 2-3s (CIBIL API simulation)
 * - Underwriting: 2-3s (complex calculation simulation)
 * 
 * These delays should feel deliberate, not laggy. Loading indicators must be
 * smooth and contextual to convey "working" not "broken".
 * 
 * ================================================================================
 */

// ================================================================================
// PHASE 10: TIMING CONFIGURATION - REALISTIC BANKING DELAYS
// ================================================================================
// These delays simulate real banking verification times to build user trust.
// Values are in milliseconds and calibrated based on mobile banking UX research.

interface VerificationDelay {
  duration: number;      // Delay in ms before showing response
  loadingText: string;   // What to show during the delay
  description: string;   // For documentation purposes
  steps?: string[];      // Multi-step loading messages
}

const VERIFICATION_DELAYS: Record<string, VerificationDelay> = {
  // ================================================================================
  // V4 16-STAGE FLOW DELAYS - DYNAMIC CREDIT SCORING EXPERIENCE
  // New stages: INCOME, EXISTING_EMI, DOB for user-provided financial data
  // ================================================================================

  // Stage 1: GREETING - Quick welcome
  GREETING: {
    duration: 1500,
    loadingText: 'Connecting to Tata Capital...',
    description: 'Quick connection, friendly start',
    steps: ['Establishing secure connection...', 'Initializing chat session...', 'Connected!']
  },

  // Stage 2: PURPOSE - Understanding needs
  PURPOSE: {
    duration: 1800,
    loadingText: 'Processing...',
    description: 'Analyzing loan purpose',
    steps: ['Recording your requirement...', 'Analyzing loan category...', 'Purpose noted!']
  },

  // Stage 3: AMOUNT - Loan amount collection
  AMOUNT: {
    duration: 1500,
    loadingText: 'Processing amount...',
    description: 'Recording loan amount',
    steps: ['Validating amount format...', 'Checking eligibility range...', 'Amount recorded!']
  },

  // Stage 4: CITY - Location collection
  CITY: {
    duration: 1800,
    loadingText: 'Verifying serviceability...',
    description: 'Recording city for serviceability',
    steps: ['Checking branch network...', 'Verifying service coverage...', 'Location verified!']
  },

  // Stage 5: EMPLOYMENT_TYPE - Employment verification
  EMPLOYMENT_TYPE: {
    duration: 1500,
    loadingText: 'Processing...',
    description: 'Recording employment type',
    steps: ['Recording employment details...', 'Updating customer profile...', 'Details saved!']
  },

  // Stage 6: NAME - Customer identification
  NAME: {
    duration: 1200,
    loadingText: 'Recording details...',
    description: 'Customer name collection',
    steps: ['Validating name format...', 'Saving to profile...']
  },

  // Stage 7: MOBILE - Phone number collection & OTP sending
  MOBILE: {
    duration: 4000,
    loadingText: 'Sending OTP...',
    description: 'Setting up mobile verification',
    steps: [
      'Validating mobile number...',
      'Connecting to SMS gateway...',
      'Generating secure OTP...',
      'Dispatching OTP to your mobile...',
      'OTP sent successfully!'
    ]
  },

  // Stage 8: OTP - OTP verification (key security step)
  OTP: {
    duration: 4500,
    loadingText: 'Verifying OTP...',
    description: 'Authenticating with telecom gateway',
    steps: [
      'Connecting to telecom provider...',
      'Validating OTP format...',
      'Verifying with authentication server...',
      'Cross-checking with records...',
      'OTP verified successfully!'
    ]
  },

  // Stage 9: INCOME - Monthly income collection (NEW)
  INCOME: {
    duration: 2000,
    loadingText: 'Processing income details...',
    description: 'Recording and validating monthly income',
    steps: [
      'Recording income amount...',
      'Validating income format...',
      'Updating financial profile...',
      'Income recorded!'
    ]
  },

  // Stage 10: EXISTING_EMI - Existing loan/EMI collection (NEW)
  EXISTING_EMI: {
    duration: 2500,
    loadingText: 'Analyzing debt profile...',
    description: 'Calculating debt-to-income ratio',
    steps: [
      'Recording existing EMI...',
      'Calculating DTI ratio...',
      'Analyzing repayment capacity...',
      'Debt profile updated!'
    ]
  },

  // Stage 11: DOB - Age/Date of Birth collection (NEW)
  DOB: {
    duration: 1500,
    loadingText: 'Verifying age...',
    description: 'Recording age for eligibility check',
    steps: [
      'Processing date of birth...',
      'Calculating age...',
      'Verifying eligibility criteria...',
      'Age verified!'
    ]
  },

  // Stage 12: KYC - PAN verification (important identity step)
  KYC: {
    duration: 6000,
    loadingText: 'Verifying PAN...',
    description: 'Identity verification via PAN',
    steps: [
      'Connecting to NSDL server...',
      'Fetching PAN details...',
      'Validating PAN format...',
      'Verifying identity with Income Tax database...',
      'Connecting to CRM server...',
      'Fetching customer profile...',
      'Identity verification complete!'
    ]
  },

  // Stage 13: OFFER_DISCUSSION - Pre-approved offer check (with credit score calculation)
  OFFER_DISCUSSION: {
    duration: 8000,
    loadingText: 'Calculating credit score...',
    description: 'Dynamic credit scoring and offer generation',
    steps: [
      'Analyzing financial profile...',
      'Calculating debt-to-income ratio...',
      'Evaluating income stability...',
      'Assessing age and employment factors...',
      'Computing credit score...',
      'Calculating maximum eligibility...',
      'Determining interest rate...',
      'Generating personalized offer...',
      'Offer ready!'
    ]
  },

  // Stage 11: TENURE_SELECTION - EMI calculation
  TENURE_SELECTION: {
    duration: 3500,
    loadingText: 'Calculating EMI...',
    description: 'Computing EMI for different tenures',
    steps: [
      'Fetching current interest rates...',
      'Calculating EMI for 12 months...',
      'Calculating EMI for 24 months...',
      'Calculating EMI for 36 months...',
      'Calculating EMI for 48 months...',
      'EMI options ready!'
    ]
  },

  // Stage 12: UNDERWRITING - Final decision (critical step)
  UNDERWRITING: {
    duration: 8000,
    loadingText: 'Processing application...',
    description: 'Risk assessment and eligibility calculation',
    steps: [
      'Initiating underwriting engine...',
      'Analyzing credit history...',
      'Verifying income details...',
      'Checking debt-to-income ratio...',
      'Verifying employment stability...',
      'Running fraud detection checks...',
      'Calculating risk score...',
      'Applying lending policies...',
      'Generating final decision...'
    ]
  },

  // Stage 13a: SANCTION - Loan approved
  SANCTION: {
    duration: 5000,
    loadingText: 'Generating sanction letter...',
    description: 'Document generation and digital signing',
    steps: [
      'Preparing loan agreement...',
      'Generating sanction letter...',
      'Adding terms and conditions...',
      'Applying digital signature...',
      'Encrypting document...',
      'Document ready for download!'
    ]
  },

  // Stage 13b: REJECTION - Loan declined
  REJECTION: {
    duration: 3000,
    loadingText: 'Processing...',
    description: 'Finalizing application status',
    steps: [
      'Finalizing decision...',
      'Recording rejection reason...',
      'Updating application status...'
    ]
  },

  // Legacy stage names for backwards compatibility
  NEEDS_ANALYSIS: {
    duration: 1000,
    loadingText: 'Understanding your requirements...',
    description: 'Analyzing loan needs'
  },
  KYC_COLLECTION: {
    duration: 1200,
    loadingText: 'Preparing verification...',
    description: 'Setting up identity verification'
  },
  KYC_VERIFICATION: {
    duration: 2500,
    loadingText: 'Verifying your identity...',
    description: 'OTP verification with telecom gateway'
  },
  OFFER_CHECK: {
    duration: 2000,
    loadingText: 'Checking pre-approved offers...',
    description: 'Querying offer management system'
  },
  CREDIT_CHECK: {
    duration: 2500,
    loadingText: 'Fetching credit score from bureau...',
    description: 'CIBIL/Experian API call simulation'
  },
  UNDERWRITING_DECISION: {
    duration: 3000,
    loadingText: 'Evaluating your application...',
    description: 'Risk assessment and eligibility calculation'
  }
};

// Helper function to get delay config for a stage
const getDelayConfig = (stage: string): VerificationDelay => {
  const config = VERIFICATION_DELAYS[stage];
  if (!config) {
    console.warn(`⚠️ No delay config found for stage: "${stage}", using fallback`);
    console.log('Available stages:', Object.keys(VERIFICATION_DELAYS));
  } else {
    console.log(`✅ Using delay config for stage: "${stage}" - ${config.loadingText}`);
  }
  return config || {
    duration: 800,
    loadingText: 'Processing...',
    description: 'Default processing'
  };
};

// ================================================================================
// PHASE 10: TONE MANAGEMENT
// ================================================================================
// After KYC verification begins, remove emojis and use formal banking language.
// Greeting and initial stages can be friendly; verification stages must be professional.

const FORMAL_STAGES = [
  'KYC_VERIFICATION',
  'OFFER_CHECK',
  'CREDIT_CHECK',
  'INCOME_DOC_UPLOAD',
  'UNDERWRITING_DECISION',
  'REJECTION'
];

// Remove emojis from text for formal stages
const sanitizeForFormalTone = (text: string, stage: string): string => {
  if (!FORMAL_STAGES.includes(stage)) {
    return text; // Keep emojis for early friendly stages
  }

  // Remove common emojis used in responses
  return text
    .replace(/[\u{1F600}-\u{1F64F}]/gu, '') // Emoticons
    .replace(/[\u{1F300}-\u{1F5FF}]/gu, '') // Misc symbols
    .replace(/[\u{1F680}-\u{1F6FF}]/gu, '') // Transport/map
    .replace(/[\u{1F1E0}-\u{1F1FF}]/gu, '') // Flags
    .replace(/[\u{2600}-\u{26FF}]/gu, '')   // Misc symbols
    .replace(/[\u{2700}-\u{27BF}]/gu, '')   // Dingbats
    .replace(/👋|🎉|😊|✅|❌|📄|📊|💰|🎯|⚠️|🔍|💼|🏦|📈|📉|🎊|✨|💳|📞|📧/g, '')
    .replace(/\s+/g, ' ')
    .trim();
};

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

// ================================================================================
// PHASE 8: CUSTOMER ACQUISITION SIMULATION
// ================================================================================
//
// PURPOSE:
// --------
// Simulates how customers arrive at an NBFC loan chatbot through digital marketing:
// - "AD" = Customer clicked a digital advertisement (Google/Facebook/Instagram ads)
// - "EMAIL" = Customer opened a pre-approved loan marketing email
//
// HOW THIS SIMULATES REAL NBFC DIGITAL FUNNEL:
// ---------------------------------------------
// In a real NBFC, customers arrive via:
// 1. Performance marketing ads (Google, Meta, YouTube)
// 2. Email campaigns to existing/prospect customers
// 3. SMS campaigns with loan offers
// 4. Partner affiliate websites
//
// The acquisition_source helps:
// - Personalize the greeting (ad clicker vs email recipient)
// - Track conversion funnel for marketing ROI
// - Adjust conversation tone (new prospect vs existing customer)
//
// WHY THIS SATISFIES "LANDING VIA DIGITAL ADS OR EMAILS":
// --------------------------------------------------------
// The landing page buttons simulate the exact user journey:
// - "Apply via Digital Ad" = User clicked loan ad on social media/search
// - "Apply via Marketing Email" = User clicked CTA in pre-approved email
//
// The chatbot then:
// 1. Auto-opens (simulating ad/email click behavior)
// 2. Shows contextual greeting based on how they arrived
// 3. Proceeds with normal loan journey from GREETING stage
//
// ================================================================================

// Type definition for acquisition source
export type AcquisitionSource = 'AD' | 'EMAIL' | null;

// Global state for acquisition source (set by landing page buttons)
let globalAcquisitionSource: AcquisitionSource = null;

// Helper function to open chat widget with optional acquisition source
export const openChatWidget = (source?: AcquisitionSource) => {
  // PHASE 8: Store acquisition source for greeting customization
  if (source) {
    globalAcquisitionSource = source;
    console.log(`📢 PHASE 8: Customer acquired via ${source}`);
  }

  const chatButton = document.querySelector('[data-chat-trigger]') as HTMLButtonElement;
  if (chatButton) {
    chatButton.click();
  }
};

// Helper to get contextual greeting based on acquisition source
// PHASE 10: Greetings are friendly but professional - no excessive emojis
const getContextualGreeting = (source: AcquisitionSource): string => {
  switch (source) {
    case 'AD':
      // Customer clicked a digital advertisement
      // Tone: Warm, professional, clear value proposition
      return `Hello! Thank you for your interest in Tata Capital Personal Loans.

I can help you check your eligibility in just a few minutes - it's quick and paperwork-free.

To get started, could you tell me:
1. How much loan amount you're looking for?
2. The purpose of your loan?`;

    case 'EMAIL':
      // Customer opened pre-approved loan marketing email
      // Tone: Personalized, acknowledge existing relationship
      return `Welcome to Tata Capital. We're glad you opened your pre-approved loan offer.

Based on your profile, you may already qualify for a special interest rate.

To check your pre-approved amount, please share your registered mobile number.`;

    default:
      // Direct website visitor (no specific acquisition source)
      // Tone: Warm, informative, professional
      return `Hello and welcome to Tata Capital.

I'm here to help you with your personal loan application. The process is quick and can be completed in just a few minutes.

How may I assist you today?`;
  }
};

export function ChatWidget() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState<string>('Processing...');
  const [sessionId, setSessionId] = useState<string>(() => `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);

  // ================================================================
  // PHASE 10: Processing state for realistic delays
  // ================================================================
  // isProcessing indicates that a verification delay is in progress.
  // During this time, the input should be disabled and a contextual
  // loading message should be displayed.
  const [isProcessing, setIsProcessing] = useState(false);

  // ================================================================
  // PHASE 10: Idle timeout tracking
  // ================================================================
  // Track when the user goes idle for too long
  const [isIdle, setIsIdle] = useState(false);
  const idleTimerRef = useRef<NodeJS.Timeout | null>(null);
  const IDLE_TIMEOUT = 5 * 60 * 1000; // 5 minutes

  // ================================================================
  // CRITICAL FIX: Stage-driven UI state
  // ================================================================
  // Previously: showUpload was a free-floating state that could be toggled
  // manually, causing it to reappear after verification.
  //
  // FIX: Track current_stage from backend and DERIVE showUpload from it.
  // Upload button appears ONLY when stage === INCOME_DOC_UPLOAD
  // Once stage advances, upload button cannot reappear.
  // ================================================================
  const [currentStage, setCurrentStage] = useState<string>('GREETING');

  // DERIVED: showUpload is now computed from currentStage, not independently set
  // This prevents the upload button from reappearing after stage advances
  const showUpload = currentStage === 'INCOME_DOC_UPLOAD';


  const [showLetterModal, setShowLetterModal] = useState(false);
  const [showSanctionLetter, setShowSanctionLetter] = useState(false);
  const [loanDetails, setLoanDetails] = useState<LoanDetails | null>(null);
  const [customerName, setCustomerName] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [waitingForDocs, setWaitingForDocs] = useState(false);
  const [currentScenario, setCurrentScenario] = useState<string | null>(null);
  const [pendingDecision, setPendingDecision] = useState<boolean>(false);
  const [decisionType, setDecisionType] = useState<'credit' | 'underwriting' | 'documents' | 'final' | null>(null);
  // PHASE 5: Session closure state
  const [sessionClosed, setSessionClosed] = useState(false);
  const [closureReason, setClosureReason] = useState<string | null>(null);

  // PHASE 8: Customer acquisition source tracking
  // Tracks how customer arrived: 'AD' (digital ad) or 'EMAIL' (marketing email)
  const [acquisitionSource, setAcquisitionSource] = useState<AcquisitionSource>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // ================================================================
  // PHASE 10: Idle timeout management
  // ================================================================
  // Reset idle timer on user activity
  const resetIdleTimer = useCallback(() => {
    if (idleTimerRef.current) {
      clearTimeout(idleTimerRef.current);
    }
    setIsIdle(false);

    // Only set idle timer if chat is open and not already closed
    if (isOpen && !sessionClosed) {
      idleTimerRef.current = setTimeout(() => {
        setIsIdle(true);
      }, IDLE_TIMEOUT);
    }
  }, [isOpen, sessionClosed]);

  // Reset idle timer on user interactions
  useEffect(() => {
    if (isOpen) {
      resetIdleTimer();
    }
    return () => {
      if (idleTimerRef.current) {
        clearTimeout(idleTimerRef.current);
      }
    };
  }, [isOpen, messages, inputValue, resetIdleTimer]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ================================================================
  // AUTO-FOCUS INPUT: Always keep cursor in input when chat is open
  // ================================================================
  useEffect(() => {
    if (isOpen && !sessionClosed && inputRef.current) {
      // Immediate focus
      inputRef.current.focus();

      // Also set up interval to keep focus (in case it's lost)
      const focusInterval = setInterval(() => {
        if (inputRef.current && document.activeElement !== inputRef.current && !isLoading && !sessionClosed) {
          inputRef.current.focus();
        }
      }, 500);

      return () => clearInterval(focusInterval);
    }
  }, [isOpen, sessionClosed]);

  // Re-focus after loading completes
  useEffect(() => {
    if (isOpen && !isLoading && !sessionClosed && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen, isLoading, sessionClosed, messages]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      // PHASE 8: Capture acquisition source when chat opens
      // This reads from the global variable set by landing page buttons
      const source = globalAcquisitionSource;
      setAcquisitionSource(source);

      // Clear global source after capturing (one-time use)
      globalAcquisitionSource = null;

      // PHASE 10: Show brief loading state before greeting (simulates connection)
      setIsLoading(true);
      setLoadingMessage('Connecting to Tata Capital...');

      setTimeout(() => {
        // PHASE 8: Contextual greeting based on acquisition source
        // Different greeting for ad clicks vs email opens vs direct visits
        const greetingContent = getContextualGreeting(source);

        const greeting: Message = {
          role: 'assistant',
          content: greetingContent,
          timestamp: new Date().toISOString()
        };
        setMessages([greeting]);
        setIsLoading(false);

        // Log acquisition for analytics
        if (source) {
          sendAdminEvent('ACQUISITION_SOURCE', { source, timestamp: new Date().toISOString() });
        }
      }, 800); // Brief delay to simulate connection
    }
  }, [isOpen]);

  // ================================================================
  // AUTO-ADVANCE FOR UNDERWRITING STAGE
  // ================================================================
  useEffect(() => {
    let timer: NodeJS.Timeout;

    // Only trigger if we are in UNDERWRITING stage and not currently processing an action
    // We check !isLoading to ensure we don't trigger while the previous response is still being handled
    if (currentStage === 'UNDERWRITING' && !isProcessing && !isLoading) {
      console.log('🔄 Auto-advance: Underwriting stage detected');

      // 1. Trigger the visual animation (8 seconds of steps)
      // We explicitly call this to show "Analyzing...", "Checking score..." etc.
      applyProcessingDelay('UNDERWRITING');

      // 2. Set timer to auto-advance AFTER the animation completes
      // The animation takes ~8s, so we trigger the backend call just after
      timer = setTimeout(() => {
        console.log('✅ Auto-advance: Sending [AUTO_PROCEED] trigger');
        sendMessage('[AUTO_PROCEED]', true); // true = hidden message
      }, 8500);
    }

    return () => {
      if (timer) clearTimeout(timer);
    };
  }, [currentStage]); // Dependency on currentStage ensures it runs when entering the stage

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
      }).catch(() => { }); // Silent fail if backend unavailable
    } catch (e) { }
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

  // PHASE 5: Handle restart after session closure
  const handleRestart = () => {
    // Generate new session ID
    const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);

    // Reset all state
    setMessages([]);
    setInputValue('');
    setIsLoading(false);
    setIsProcessing(false);
    setIsIdle(false);
    setLoadingMessage('Processing...');
    // CRITICAL FIX: Reset stage to GREETING (showUpload is derived from this)
    setCurrentStage('GREETING');
    setShowSanctionLetter(false);
    setLoanDetails(null);
    setCustomerName(null);
    setUploadedDocs([]);
    setWaitingForDocs(false);
    setCurrentScenario(null);
    setPendingDecision(false);
    setDecisionType(null);
    setSessionClosed(false);
    setClosureReason(null);

    // PHASE 8: Reset acquisition source on restart
    setAcquisitionSource(null);

    // PHASE 10: Show connecting state briefly, then greeting
    setIsLoading(true);
    setLoadingMessage('Starting new session...');

    setTimeout(() => {
      const greeting: Message = {
        role: 'assistant',
        content: 'Hello and welcome to Tata Capital.\n\nI\'m here to help you with your personal loan application. The process is quick and can be completed in just a few minutes.\n\nTo get started, please share:\n1. Your full name\n2. Your mobile number',
        timestamp: new Date().toISOString()
      };
      setMessages([greeting]);
      setIsLoading(false);
    }, 800);
  };

  // ================================================================
  // PHASE 10: Helper to apply realistic processing delay with multi-step messages
  // ================================================================
  // This function adds a delay before showing the response to simulate
  // real banking verification times. Shows multiple loading steps for realism.
  const applyProcessingDelay = async (stage: string): Promise<void> => {
    const config = getDelayConfig(stage);
    // Keep isLoading true so the loading indicator stays visible
    setIsLoading(true);
    setIsProcessing(true);

    // If we have multi-step messages, cycle through them
    if (config.steps && config.steps.length > 0) {
      const stepDuration = config.duration / config.steps.length;
      for (let i = 0; i < config.steps.length; i++) {
        setLoadingMessage(config.steps[i]);
        await new Promise(resolve => setTimeout(resolve, stepDuration));
      }
    } else {
      setLoadingMessage(config.loadingText);
      await new Promise(resolve => setTimeout(resolve, config.duration));
    }

    setIsProcessing(false);
    // Note: isLoading will be set to false by the caller after adding the message
  };

  // Helper to show multi-step loading for a given stage
  const showMultiStepLoading = async (stage: string): Promise<void> => {
    const config = getDelayConfig(stage);

    if (config.steps && config.steps.length > 0) {
      const stepDuration = config.duration / config.steps.length;
      for (let i = 0; i < config.steps.length; i++) {
        setLoadingMessage(config.steps[i]);
        await new Promise(resolve => setTimeout(resolve, stepDuration));
      }
    } else {
      setLoadingMessage(config.loadingText);
      await new Promise(resolve => setTimeout(resolve, config.duration));
    }
  };

  const sendMessage = async (textOverride?: string, isHidden: boolean = false) => {
    const textToSend = textOverride || inputValue;
    if (!textToSend.trim() || (isLoading && !isHidden) || (isProcessing && !isHidden)) return;

    // PHASE 10: Reset idle timer on user activity
    resetIdleTimer();

    if (!isHidden) {
      const userMessage: Message = {
        role: 'user',
        content: textToSend,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, userMessage]);
      setInputValue('');
    }

    setIsLoading(true);

    // PHASE 10: Set generic loading message initially
    // Stage-specific messages will be applied AFTER we know the stage from API response
    setLoadingMessage('Please wait...');

    try {
      // ========== HARD RESET: USE V3 DETERMINISTIC ENDPOINT ==========
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 60000); // 60 second timeout

      // HARD RESET: Use /api/v3/chat for deterministic flow
      const response = await fetch('http://localhost:8000/api/v3/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: textToSend,
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

      // ================================================================
      // PHASE 10: Apply realistic processing delay based on stage
      // ================================================================
      // Different stages require different "verification times" to feel real.
      // This delay is INTENTIONAL - instant responses feel fake in banking.
      const newStage = data.conversation_stage || data.admin_data?.stage || currentStage;

      console.log('🔍 Stage debugging:', {
        conversation_stage: data.conversation_stage,
        admin_stage: data.admin_data?.stage,
        currentStage: currentStage,
        newStage: newStage
      });

      // FIX: Use CURRENT stage for loading messages, not the new stage.
      // When the user enters their mobile number (MOBILE stage), we want to show
      // "Sending OTP..." (MOBILE loading), NOT "Verifying OTP..." (OTP loading).
      // The loading message should describe what's being DONE with the user's input.
      const delayStage = currentStage;

      console.log(`📋 Loading message for stage: "${delayStage}" (user was on this stage)`);

      // Apply the delay with contextual loading message for the CURRENT stage
      await applyProcessingDelay(delayStage);

      // Get response text from API
      const responseText = data.response || 'I received your message but got an empty response.';

      // ================================================================
      // PHASE 10: Clean and format response with tone adjustment
      // ================================================================
      // For formal stages (post-KYC), remove emojis and use banking language
      const cleanText = (text: string, stage: string): string => {
        let cleaned = text
          // Remove typing indicators
          .replace(/\*typing\*/g, '')
          // Remove loading indicators
          .replace(/⏳/g, '')
          // Clean up multiple newlines
          .replace(/\n\s*\n\s*\n/g, '\n\n')
          .trim();

        // PHASE 10: Remove emojis for formal stages
        cleaned = sanitizeForFormalTone(cleaned, stage);

        return cleaned;
      };

      // Clean response with stage-appropriate tone
      const cleanedResponse = cleanText(responseText, newStage);
      if (cleanedResponse) {
        const botMessage: Message = {
          role: 'assistant',
          content: cleanedResponse,
          timestamp: new Date().toISOString()
        };

        setMessages(prev => [...prev, botMessage]);
      }

      // ================================================================
      // CRITICAL FIX: Update currentStage from backend response
      // showUpload is DERIVED from currentStage, not set directly
      // Backend sends "conversation_stage", we store it as currentStage
      // ================================================================
      if (newStage) {
        setCurrentStage(newStage);
      }
      // Note: showUpload is now derived: showUpload = (currentStage === 'INCOME_DOC_UPLOAD')
      // No more setShowUpload(true/false) - it's automatic!

      if (data.show_sanction_letter) {
        setShowSanctionLetter(true);
        setLoanDetails(data.loan_details);
      }

      if (data.customer_name) {
        setCustomerName(data.customer_name);
      }

      // PHASE 5: Handle session closure
      if (data.session_closed) {
        setSessionClosed(true);
        setClosureReason(data.closure_reason || 'COMPLETED');
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
        
        setCurrentStage('INCOME_DOC_UPLOAD');  // CRITICAL FIX: stage-driven upload
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
        setCurrentStage('INCOME_DOC_UPLOAD');  // CRITICAL FIX: stage-driven upload
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

  // Note: handleRestart is defined earlier in the component (PHASE 5)

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // PHASE 10: Reset idle timer on file upload
    resetIdleTimer();

    // Add uploaded document to tracking
    const newDocs = [...uploadedDocs, file.name];
    setUploadedDocs(newDocs);

    // Show upload confirmation message (professional format, no emoji)
    const uploadMsg: Message = {
      role: 'user',
      content: `Document uploaded: ${file.name}`,
      timestamp: new Date().toISOString()
    };
    setMessages(prev => [...prev, uploadMsg]);

    setIsLoading(true);
    setLoadingMessage('Uploading document...');

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

      // ================================================================
      // CRITICAL FIX: Update stage from upload response
      // showUpload is DERIVED from currentStage, not manually toggled
      // ================================================================
      console.log('📤 Upload Response:', {
        current_stage: data.current_stage,
        show_upload: data.show_upload,
        show_sanction_letter: data.show_sanction_letter,
        document_verified: data.document_verified
      });

      if (data.current_stage) {
        console.log(`📍 STAGE UPDATE (upload): ${currentStage} → ${data.current_stage}`);
        setCurrentStage(data.current_stage);
        // showUpload is now automatically derived from currentStage
        // No need to manually toggle - once stage advances, upload disappears!
      }

      // Handle sanction letter display
      if (data.show_sanction_letter) {
        setShowSanctionLetter(true);
        setLoanDetails(data.loan_details);
      }

    } catch (error) {
      console.error('Upload error:', error);
      // PHASE 10: Professional error message without emoji
      const errorMsg: Message = {
        role: 'assistant',
        content: `Document ${newDocs.length} received: ${file.name}\n\nPlease upload the remaining documents.`,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMsg]);
      // On error, stay in INCOME_DOC_UPLOAD stage (don't change currentStage)
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

    // CRITICAL FIX: Set stage instead of manual toggle - showUpload derived from stage
    setCurrentStage('INCOME_DOC_UPLOAD');
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
    // CRITICAL FIX: Set stage instead of manual toggle - showUpload derived from stage
    setCurrentStage('INCOME_DOC_UPLOAD');
    setWaitingForDocs(true);
    setUploadedDocs([]);
    setIsLoading(false);
  };

  const handleResetChat = async () => {
    if (confirm('Start a new conversation? This will clear the current chat.')) {
      try {
        // HARD RESET: Use v3 reset endpoint
        await fetch('http://localhost:8000/api/v3/reset-session', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ session_id: sessionId })
        });
      } catch (error) {
        console.error('Reset error:', error);
      }

      // Reset frontend state
      const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      setMessages([]);
      setSessionId(newSessionId);
      // CRITICAL FIX: Reset stage instead of manual toggle - showUpload derived from stage
      setCurrentStage('GREETING');
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
    doc.text(`Rs. ${(loanDetails?.amount || 0).toLocaleString('en-IN')}`, pageWidth - 20, yPos, { align: 'right' });

    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Annual Interest Rate:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`${loanDetails?.interest_rate || 0}% per annum`, pageWidth - 20, yPos, { align: 'right' });

    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Loan Tenure:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`${loanDetails?.tenure_months || 0} months`, pageWidth - 20, yPos, { align: 'right' });

    yPos += 6;
    doc.setFont('helvetica', 'normal');
    doc.text(`Monthly EMI:`, 20, yPos);
    doc.setFont('helvetica', 'bold');
    doc.text(`Rs. ${(loanDetails?.monthly_emi || 0).toLocaleString('en-IN')}`, pageWidth - 20, yPos, { align: 'right' });

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
      {/* Floating Chat Button - Responsive */}
      {!isOpen && (
        <div className="fixed bottom-4 right-4 sm:bottom-6 sm:right-6 z-[9999]">
          <div className="relative">
            {/* Nudge Tooltip - Hidden on very small screens */}
            <div className="absolute bottom-full right-0 mb-3 sm:mb-4 bg-white px-4 sm:px-5 py-2 sm:py-3 rounded-xl shadow-2xl border-2 border-[#004589] w-44 sm:w-52 hidden xs:block">
              <p className="text-gray-800 text-sm sm:text-base font-semibold leading-snug">
                Need a loan?<br />
                Chat with us!
              </p>
            </div>

            {/* Chat Button - Responsive size */}
            <button
              data-chat-trigger
              onClick={() => setIsOpen(true)}
              className="bg-[#004589] text-white w-14 h-14 sm:w-16 sm:h-16 rounded-full shadow-2xl hover:bg-[#003366] transition-all flex items-center justify-center hover:scale-110 border-3 sm:border-4 border-yellow-400"
            >
              <MessageCircle className="w-6 h-6 sm:w-8 sm:h-8" />
            </button>
          </div>
        </div>
      )}

      {/* Chat Window - Fully Responsive Modal */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 bg-black/50 z-[99998]" onClick={() => setIsOpen(false)}></div>

          {/* Chat Window - Centered Modal */}
          <div
            className="bg-white rounded-2xl shadow-2xl border-2 border-gray-300 
                       flex flex-col fixed z-[99999] overflow-hidden"
            style={{
              width: 'min(450px, 90vw)',
              height: 'min(550px, 75vh)',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)'
            }}
          >
            {/* Header */}
            <div className="bg-gradient-to-r from-[#004589] to-[#0066cc] text-white p-3 rounded-t-2xl flex items-center justify-between flex-shrink-0">
              <div className="flex items-center gap-2 sm:gap-3">
                <img src={tataLogo} alt="Tata Capital" className="h-8 sm:h-10 object-contain" />
                <div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 sm:w-2.5 sm:h-2.5 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-base sm:text-lg font-semibold">Tata Capital Assistant</span>
                  </div>
                  <p className="text-xs sm:text-sm opacity-90">AI-Powered Underwriter</p>
                </div>
              </div>
              <div className="flex items-center gap-1 sm:gap-2">
                <button
                  onClick={handleResetChat}
                  className="p-1.5 sm:p-2 hover:bg-white/20 rounded-lg transition-colors"
                  title="Start New Chat"
                >
                  <RotateCcw className="w-4 h-4 sm:w-5 sm:h-5" />
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1.5 sm:p-2 hover:bg-white/20 rounded-lg transition-colors"
                >
                  <X className="w-5 h-5 sm:w-6 sm:h-6" />
                </button>
              </div>
            </div>

            {/* Chat Content - Responsive padding */}
            <div className="flex-1 p-3 sm:p-4 overflow-y-auto bg-gradient-to-b from-gray-50 to-gray-100 scroll-smooth" style={{ scrollBehavior: 'smooth' }}>
              <div className="space-y-4 sm:space-y-5">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex gap-2 sm:gap-3 ${message.role === 'user' ? 'flex-row-reverse' : ''}`}
                    style={{
                      animation: 'fadeSlideIn 0.3s ease-out forwards',
                      animationDelay: `${index === messages.length - 1 ? '0.05s' : '0s'}`
                    }}
                  >
                    {/* Avatar - Responsive */}
                    {message.role === 'assistant' && (
                      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden bg-white border-2 border-blue-500 shadow-md">
                        {/* Tata Capital Logo */}
                        <img
                          src={tataLogo}
                          alt="Tata Capital"
                          className="w-6 h-6 sm:w-8 sm:h-8 object-contain"
                          onError={(e) => {
                            e.currentTarget.style.display = 'none';
                          }}
                        />
                      </div>
                    )}
                    {message.role === 'user' && (
                      <div className="w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden bg-gradient-to-br from-blue-500 to-blue-600 shadow-md border-2 border-white">
                        {/* User Profile Icon */}
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="white" className="w-5 h-5 sm:w-6 sm:h-6">
                          <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM3.751 20.105a8.25 8.25 0 0116.498 0 .75.75 0 01-.437.695A18.683 18.683 0 0112 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 01-.437-.695z" clipRule="evenodd" />
                        </svg>
                      </div>
                    )}

                    {/* Message Bubble - Responsive */}
                    <div className={`max-w-[85%] sm:max-w-[75%] ${message.role === 'user'
                      ? 'bg-gradient-to-br from-blue-500 to-blue-600 text-white rounded-2xl rounded-tr-sm'
                      : 'bg-white border border-gray-100 rounded-2xl rounded-tl-sm'} p-3 sm:p-4 shadow-sm hover:shadow-md transition-shadow duration-200 break-words`}>

                      {/* Rich Text Formatting for Bot Messages */}
                      {message.role === 'assistant' ? (
                        <div className="text-sm leading-relaxed text-slate-700">
                          {message.content.replace(/\\n/g, '\n').split('\n').map((line, i) => {
                            // Empty lines are spacers
                            if (!line.trim()) return <div key={i} className="h-2" />;

                            // Check for list items (bullets, numbers, emojis)
                            const isList = /^[•\-*]|\d+\.|^📌|^✅|^📊|^💰|^📈|^💳/.test(line.trim());

                            // Check for headers (ends with colon or starts with #)
                            const isHeader = line.trim().endsWith(':') || line.trim().startsWith('#');

                            if (isList) {
                              return (
                                <div key={i} className="flex gap-2 ml-1 mb-1">
                                  <span className="flex-shrink-0 mt-0.5">{line.trim().substring(0, 2)}</span>
                                  <span>{line.trim().substring(2)}</span>
                                </div>
                              );
                            }

                            if (isHeader) {
                              return (
                                <p key={i} className="font-semibold text-slate-900 mt-2 mb-1">
                                  {line}
                                </p>
                              );
                            }

                            // Standard paragraph with simple bold formatting
                            return (
                              <p key={i} className="mb-1">
                                {line.split(/(\*\*.*?\*\*)/).map((part, j) =>
                                  part.startsWith('**') && part.endsWith('**') ?
                                    <strong key={j} className="font-semibold text-slate-900">{part.slice(2, -2)}</strong> :
                                    part
                                )}
                              </p>
                            );
                          })
                          }
                        </div>
                      ) : (
                        // User messages - simple text
                        <p className="text-sm leading-relaxed whitespace-pre-wrap text-white">
                          {message.content}
                        </p>
                      )}

                      {/* Message timestamp - subtle */}
                      <p className={`text-[9px] sm:text-[10px] mt-1 ${message.role === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}
                {/* PHASE 10: Sanction Letter Card - Professional styling, no emojis */}
                {showSanctionLetter && loanDetails && (
                  <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-500 rounded-lg p-3 sm:p-4 animate-fadeIn">
                    <div className="flex items-center gap-2 mb-2 sm:mb-3">
                      <CheckCircle className="w-5 h-5 sm:w-6 sm:h-6 text-green-600" />
                      <h4 className="text-green-900 font-semibold text-sm sm:text-base">Loan Approved</h4>
                    </div>
                    <div className="space-y-1.5 sm:space-y-2 text-xs sm:text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-700">Sanctioned Amount:</span>
                        <span className="text-gray-900">₹{(loanDetails.amount || 0).toLocaleString('en-IN')}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Interest Rate:</span>
                        <span className="text-gray-900">{loanDetails.interest_rate || 0}% p.a.</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Tenure:</span>
                        <span className="text-gray-900">{loanDetails.tenure_months || 0} months</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-700">Monthly EMI:</span>
                        <span className="text-gray-900">₹{(loanDetails.monthly_emi || 0).toLocaleString('en-IN')}</span>
                      </div>
                    </div>
                    <button
                      onClick={() => setShowLetterModal(true)}
                      className="mt-4 w-full bg-green-600 text-white py-2 rounded-lg flex items-center justify-center gap-2 hover:bg-green-700 transition-colors"
                    >
                      <Eye className="w-4 h-4" />
                      View Sanction Letter
                    </button>
                  </div>
                )}

                {/* PHASE 10: Decision Buttons - Professional styling */}
                {pendingDecision && !isLoading && (
                  <div className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-500 rounded-lg p-4 animate-fadeIn">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-3 h-3 bg-blue-600 rounded-full animate-pulse"></div>
                      <h4 className="text-blue-900 font-semibold">Manual Review Required</h4>
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
                        Accept
                      </button>
                      <button
                        onClick={() => handleDecision('decline')}
                        className="flex-1 bg-red-600 text-white py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-red-700 transition-colors font-medium"
                      >
                        Decline
                      </button>
                      <button
                        onClick={() => handleDecision('contact')}
                        className="flex-1 bg-amber-600 text-white py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-amber-700 transition-colors font-medium"
                      >
                        Contact
                      </button>
                    </div>
                  </div>
                )}

                {/* PHASE 10: Loading Indicator - Professional, smooth animation with contextual message */}
                {isLoading && (
                  <div className="flex gap-3">
                    <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 overflow-hidden bg-white border-2 border-blue-500 shadow-md">
                      <img
                        src={tataLogo}
                        alt="Tata Capital"
                        className="w-8 h-8 object-contain animate-pulse"
                        onError={(e) => {
                          e.currentTarget.style.display = 'none';
                        }}
                      />
                    </div>
                    <div className="bg-white p-3 rounded-xl shadow-md border border-gray-100">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                          <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                        </div>
                        <span className="text-sm text-slate-600 ml-2">{loadingMessage}</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            </div>

            {/* Input Area */}
            <div className="p-4 border-t border-gray-200 bg-white rounded-b-2xl flex-shrink-0">
              {/* PHASE 5 + PHASE 10: Show session closed message - Professional tone, no emojis */}
              {sessionClosed && (
                <div className="mb-3 p-3 bg-gray-100 rounded-lg text-center">
                  <p className="text-sm text-gray-600">
                    {closureReason === 'LOAN_SANCTIONED'
                      ? 'This loan application has been completed. Your sanction letter is ready for download.'
                      : closureReason === 'LOAN_REJECTED'
                        ? 'This loan application session has ended.'
                        : 'This session has been closed.'
                    }
                  </p>
                  <button
                    onClick={handleRestart}
                    className="mt-2 text-blue-600 hover:text-blue-800 text-xs sm:text-sm font-medium flex items-center justify-center gap-1 mx-auto"
                  >
                    <RotateCcw className="w-3 h-3 sm:w-4 sm:h-4" />
                    Start New Application
                  </button>
                </div>
              )}

              {/* HARD RESET: Upload button REMOVED - Income from database only */}

              <div className="flex gap-2">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder={sessionClosed ? "Session ended" : "Type your message..."}
                  disabled={isLoading || sessionClosed}
                  autoFocus
                  autoComplete="off"
                  className="flex-1 px-3 sm:px-4 py-2.5 sm:py-3 text-sm sm:text-base border-2 border-gray-200 rounded-xl focus:outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100 disabled:bg-gray-100 transition-all"
                  style={{ fontSize: '16px' }} /* Prevents iOS zoom */
                />
                <button
                  onClick={() => sendMessage()}
                  disabled={isLoading || !inputValue.trim() || sessionClosed}
                  className="bg-[#3B82F6] text-white p-2.5 sm:p-3 rounded-xl hover:bg-[#2563EB] transition-colors disabled:opacity-50 disabled:cursor-not-allowed min-w-[44px] min-h-[44px] flex items-center justify-center"
                >
                  <Send className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Sanction Letter Modal */}
      {showLetterModal && loanDetails && (
        <SanctionLetter
          customerName={customerName || 'Customer'}
          loanDetails={loanDetails}
          onClose={() => setShowLetterModal(false)}
        />
      )}
    </>
  );
}