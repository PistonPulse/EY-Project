# 🏦 TATA CAPITAL LOAN CHATBOT - COMPLETE SYSTEM DOCUMENTATION

> **Version:** 4.0.0  
> **Last Updated:** February 2026  
> **Status:** Production Ready

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Technology Stack](#technology-stack)
4. [Application Flow](#application-flow)
5. [AI Integration (Gemini)](#ai-integration-gemini)
6. [Dynamic Credit Scoring](#dynamic-credit-scoring)
7. [Backend Components](#backend-components)
8. [Frontend Components](#frontend-components)
9. [Admin Dashboard](#admin-dashboard)
10. [PDF Generation](#pdf-generation)
11. [Testing & Demo Data](#testing--demo-data)
12. [Configuration & Environment](#configuration--environment)
13. [Running the Application](#running-the-application)

---

## 🎯 EXECUTIVE SUMMARY

The **Tata Capital Loan Chatbot** is an AI-powered conversational interface that guides customers through a personal loan application process. The system combines:

- **Google Gemini AI** for natural, human-like responses
- **Deterministic 16-stage flow** for reliable loan processing (NEW!)
- **Dynamic Credit Scoring** based on user-provided financial data (NEW!)
- **Real-time admin dashboard** for monitoring applications
- **Automated underwriting** with calculated credit scores
- **Professional PDF sanction letters** with Tata Capital branding

### Key Features
| Feature | Description |
|---------|-------------|
| 🤖 AI-Powered Chat | Gemini 2.0 Flash generates dynamic, context-aware responses |
| 📊 16-Stage Flow | Strict linear progression ensures data collection compliance |
| 💳 Dynamic Credit Score | Real-time credit scoring from user inputs (income, EMIs, age) |
| 👨‍💼 Admin Dashboard | Real-time monitoring of all active sessions |
| 📄 PDF Generation | Professional sanction letters with Tata branding |
| 🔒 Secure Validation | PAN, mobile, OTP verification patterns |
| 💰 EMI Calculator | Dynamic EMI calculation based on tenure selection |

### NEW in v4.0.0 - Dynamic Credit Scoring
- **No database dependency**: Any user can apply (no pre-existing profiles needed)
- **User-provided inputs**: Income, existing EMIs, and age collected during flow
- **Real-time scoring**: Credit score calculated from financial inputs
- **Transparent factors**: DTI ratio, income level, employment type, age factor

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │ Landing Page │  │ Chat Widget  │  │   Admin Dashboard    │   │
│  │  (Products)  │  │  (Customer)  │  │  (Live Monitoring)   │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                    │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   API Layer (main.py)                      │  │
│  │  • POST /api/v3/chat - Main chat endpoint                 │  │
│  │  • GET /api/admin/* - Admin dashboard APIs                │  │
│  │  • WebSocket /ws/admin - Real-time updates                │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│        ┌─────────────────────┼─────────────────────┐            │
│        ▼                     ▼                     ▼            │
│  ┌───────────┐    ┌──────────────────┐    ┌─────────────┐      │
│  │  GEMINI   │    │  DETERMINISTIC   │    │    MOCK     │      │
│  │    AI     │    │  FLOW CONTROL    │    │    DATA     │      │
│  │           │    │                  │    │             │      │
│  │ Dynamic   │    │ 13-Stage State   │    │ Customer    │      │
│  │ Response  │    │ Machine with     │    │ Profiles    │      │
│  │ Generator │    │ Validation       │    │ (3 Types)   │      │
│  └───────────┘    └──────────────────┘    └─────────────┘      │
│        │                     │                     │            │
│        └─────────────────────┴─────────────────────┘            │
│                              │                                   │
│                              ▼                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  SERVICES LAYER                            │  │
│  │  • Underwriting Engine - Credit scoring & decisioning     │  │
│  │  • PDF Generator - Tata Capital sanction letters          │  │
│  │  • Mock Data Provider - Test customer profiles            │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 TECHNOLOGY STACK

### Frontend
| Technology | Purpose | Version |
|------------|---------|---------|
| React | UI Framework | 18.x |
| TypeScript | Type Safety | 5.x |
| Vite | Build Tool | 6.x |
| Tailwind CSS | Styling | 3.x |
| Shadcn/UI | Component Library | Latest |
| Lucide React | Icons | Latest |

### Backend
| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Language | 3.11+ |
| FastAPI | API Framework | 0.100+ |
| Uvicorn | ASGI Server | 0.23+ |
| Google Generative AI | LLM (Gemini) | Latest |
| ReportLab | PDF Generation | 4.x |
| Pydantic | Data Validation | 2.x |

### AI/ML
| Technology | Purpose | Model |
|------------|---------|-------|
| Google Gemini | Response Generation | gemini-2.0-flash |
| LangChain (optional) | LLM Orchestration | N/A |

---

## 🔄 APPLICATION FLOW

### The 16-Stage Loan Journey (v4.0)

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│GREETING │ → │PURPOSE  │ → │ AMOUNT  │ → │  CITY   │
│ Stage 1 │    │ Stage 2 │    │ Stage 3 │    │ Stage 4 │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                  │
     ┌────────────────────────────────────────────┘
     ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│EMPLOY-  │ → │  NAME   │ → │ MOBILE  │ → │   OTP   │
│  MENT   │    │ Stage 6 │    │ Stage 7 │    │ Stage 8 │
│ Stage 5 │    └─────────┘    └─────────┘    └─────────┘
└─────────┘                                       │
     ┌────────────────────────────────────────────┘
     ▼
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ INCOME  │ → │EXISTING │ → │   DOB   │ → │   KYC   │
│ Stage 9 │    │  EMI    │    │Stage 11 │    │Stage 12 │
│  (NEW)  │    │Stage 10 │    │  (NEW)  │    └─────────┘
└─────────┘    │  (NEW)  │    └─────────┘         │
               └─────────┘                        │
     ┌────────────────────────────────────────────┘
     ▼
┌─────────┐    ┌─────────┐    ┌─────────┐
│ OFFER   │ → │ TENURE  │ → │UNDER-   │
│DISCUSS- │    │SELECTION│    │WRITING  │
│  ION    │    │Stage 14 │    │Stage 15 │
│Stage 13 │    └─────────┘    └─────────┘
└─────────┘                        │
                                   ▼
                    ┌────────────────────────────┐
                    │      FINAL DECISION        │
                    │  ┌─────────┐  ┌─────────┐ │
                    │  │SANCTION │  │REJECTION│ │
                    │  │Stage 16a│  │Stage 16b│ │
                    │  └─────────┘  └─────────┘ │
                    └────────────────────────────┘
```

### Stage Details

| Stage | Name | Data Collected | Validation |
|-------|------|----------------|------------|
| 1 | GREETING | None | "yes/hi/loan" triggers |
| 2 | PURPOSE | Loan purpose | Keywords: renovation, education, medical, etc. |
| 3 | AMOUNT | Loan amount | ₹50K - ₹50L range |
| 4 | CITY | City name | Indian city names |
| 5 | EMPLOYMENT_TYPE | Salaried/Self-employed | Keywords |
| 6 | NAME | Full name | 2+ words |
| 7 | MOBILE | Phone number | 10-digit starting with 6-9 |
| 8 | OTP | OTP code | 6-digit number |
| 9 | **INCOME** ⭐ | Monthly income | "50k", "50000", "5 lakh per year" |
| 10 | **EXISTING_EMI** ⭐ | Current EMIs | "0", "none", or amount |
| 11 | **DOB** ⭐ | Age/Date of birth | "25", "25 years", "15/06/1992" |
| 12 | KYC | PAN number | Format: ABCDE1234F |
| 13 | OFFER_DISCUSSION | Acceptance | "yes/proceed/accept" |
| 14 | TENURE_SELECTION | Tenure | 12/24/36/48 months |
| 15 | UNDERWRITING | None (auto) | Credit score ≥ 700 |
| 16 | SANCTION/REJECTION | Final decision | Based on credit score |

⭐ = **NEW stages for dynamic credit scoring**

---

## 💳 DYNAMIC CREDIT SCORING (NEW in v4.0!)

### Overview

The system now calculates credit scores in **real-time** based on user-provided financial data. No database lookups or pre-existing profiles required!

### Credit Score Calculation (Max 900 points)

```
┌─────────────────────────────────────────────────────────────┐
│                 CREDIT SCORE COMPONENTS                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   1. DTI Ratio Score           (max 300 points)             │
│      └── Debt-to-Income = Existing EMI / Monthly Income     │
│                                                              │
│   2. Income Level Score        (max 200 points)             │
│      └── Based on monthly income bracket                    │
│                                                              │
│   3. Employment Score          (max 150 points)             │
│      └── Salaried vs Self-employed                          │
│                                                              │
│   4. Age Factor Score          (max 100 points)             │
│      └── Prime age range: 25-45 years                       │
│                                                              │
│   5. Loan-to-Income Ratio      (max 150 points)             │
│      └── Requested Amount / Monthly Income                  │
│                                                              │
│   TOTAL = Sum of all components (max 900)                   │
│   THRESHOLD: ≥ 700 = APPROVED, < 700 = REJECTED            │
└─────────────────────────────────────────────────────────────┘
```

### Scoring Breakdown

| Component | Points | Criteria |
|-----------|--------|----------|
| **DTI Ratio** | 300 | < 20% |
| | 200 | 20% - 35% |
| | 100 | 35% - 50% |
| | 50 | > 50% |
| **Income** | 200 | > ₹1,00,000/month |
| | 175 | ₹75,000 - ₹1,00,000 |
| | 150 | ₹50,000 - ₹75,000 |
| | 100 | ₹30,000 - ₹50,000 |
| | 50 | < ₹30,000 |
| **Employment** | 150 | Salaried |
| | 120 | Self-employed |
| **Age** | 100 | 25-45 years (prime) |
| | 75 | 21-24 or 46-55 years |
| | 50 | 18-20 or 56-60 years |
| | 30 | Other |
| **Loan Ratio** | 150 | < 3x monthly income |
| | 100 | 3x - 6x income |
| | 50 | 6x - 12x income |
| | 25 | > 12x income |

### Interest Rate by Credit Score

| Score Range | Interest Rate |
|-------------|---------------|
| 850 - 900 | 10.5% p.a. |
| 800 - 849 | 11.0% p.a. |
| 750 - 799 | 12.5% p.a. |
| 700 - 749 | 14.5% p.a. |
| < 700 | **REJECTED** |

### Example: Approval Scenario

```
User Input:
  - Monthly Income: ₹80,000
  - Existing EMI: ₹8,000
  - Age: 32 years
  - Employment: Salaried
  - Loan Amount: ₹4,00,000

Calculation:
  DTI = 8,000 / 80,000 = 10% → Score: 300
  Income: ₹80,000 (75k-1L range) → Score: 175  
  Employment: Salaried → Score: 150
  Age: 32 (25-45 prime) → Score: 100
  Loan Ratio: 4L / 80k = 5x → Score: 100

  TOTAL = 300 + 175 + 150 + 100 + 100 = 825 ✅
  
Result: APPROVED at 11.0% interest rate
```

---

## 🤖 AI INTEGRATION (GEMINI)

### How Gemini AI is Used

The system uses **Google Gemini 2.0 Flash** for generating natural, conversational responses while maintaining deterministic flow control.

```
┌─────────────────────────────────────────────────────────────┐
│                 RESPONSE GENERATION FLOW                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   User Message                                               │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────────────┐                                   │
│   │ Deterministic Flow  │ ← Stage validation                │
│   │ Controller          │ ← Data extraction                 │
│   │ (deterministic_     │ ← State management                │
│   │  flow.py)           │                                   │
│   └─────────────────────┘                                   │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────────────┐     ┌─────────────────────────┐  │
│   │ generate_           │     │ Stage-specific prompt   │  │
│   │ deterministic_      │────▶│ with context data       │  │
│   │ response()          │     │ (names, amounts, etc.)  │  │
│   └─────────────────────┘     └─────────────────────────┘  │
│        │                                                     │
│        ▼                                                     │
│   ┌─────────────────────┐                                   │
│   │ Is Gemini           │                                   │
│   │ Available?          │                                   │
│   └─────────────────────┘                                   │
│     │YES            │NO                                      │
│     ▼               ▼                                        │
│ ┌───────────┐  ┌───────────────┐                            │
│ │ GEMINI AI │  │ HARDCODED     │                            │
│ │ Response  │  │ FALLBACK      │                            │
│ │ (Dynamic) │  │ (Deterministic)│                           │
│ └───────────┘  └───────────────┘                            │
│     │               │                                        │
│     └───────┬───────┘                                        │
│             ▼                                                │
│        Bot Response                                          │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Gemini Configuration

```python
# Location: src/backend/main.py

# Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")  # Required
USE_GEMINI = os.getenv("USE_GEMINI", "true")   # Enable/disable

# Model Configuration
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel('gemini-2.0-flash')

# Generation Settings
generation_config = {
    "temperature": 0.7,      # Creativity level
    "max_output_tokens": 300  # Response length limit
}
```

### Stage-Specific Prompts

Each stage has a customized prompt template:

```python
STAGE_PROMPTS = {
    "GREETING": """You are a friendly loan assistant at Tata Capital. 
    Generate a warm, welcoming greeting...""",
    
    "PURPOSE": """The customer wants a loan. Ask them what they need 
    the loan for...""",
    
    "OFFER_DISCUSSION": """Great news! The customer is pre-approved 
    for up to ₹{pre_approved_limit_formatted}!...""",
    
    # ... more stages
}
```

### Fallback Mechanism

If Gemini fails or is disabled, hardcoded responses are used:

```python
async def generate_deterministic_response(stage, session_data):
    # Try Gemini first
    if gemini_model and USE_GEMINI:
        try:
            response = await generate_gemini_response(stage, session_data)
            if response:
                return response
        except Exception:
            pass  # Fall through to hardcoded
    
    # Fallback to hardcoded
    return generate_deterministic_response_hardcoded(stage, session_data)
```

---

## ⚙️ BACKEND COMPONENTS

### 1. Main Application (`main.py`)

**Purpose:** FastAPI application with all endpoints and response generation.

**Key Functions:**
| Function | Purpose |
|----------|---------|
| `generate_deterministic_response()` | Main response generator (Gemini + fallback) |
| `generate_gemini_response()` | AI response generation |
| `generate_deterministic_response_hardcoded()` | Backup responses |
| `deterministic_chat_endpoint()` | Main chat API |
| `broadcast_to_admin()` | WebSocket notifications |

### 2. Deterministic Flow (`deterministic_flow.py`)

**Purpose:** State machine controlling the 13-stage flow.

**Key Features:**
- Strict linear progression
- Input validation per stage
- State persistence
- Session management

```python
class FlowStage(Enum):
    GREETING = "GREETING"
    PURPOSE = "PURPOSE"
    AMOUNT = "AMOUNT"
    CITY = "CITY"
    EMPLOYMENT_TYPE = "EMPLOYMENT_TYPE"
    NAME = "NAME"
    MOBILE = "MOBILE"
    OTP = "OTP"
    KYC = "KYC"
    OFFER_DISCUSSION = "OFFER_DISCUSSION"
    TENURE_SELECTION = "TENURE_SELECTION"
    UNDERWRITING = "UNDERWRITING"
    SANCTION = "SANCTION"
    REJECTION = "REJECTION"
```

### 3. Underwriting Engine (`underwriting_engine.py`)

**Purpose:** Credit decisioning based on mock credit scores.

**Logic:**
```
Credit Score ≥ 750  → APPROVED (Lower interest rate)
Credit Score 650-749 → CONDITIONAL APPROVAL
Credit Score < 650   → REJECTED
```

### 4. Mock Data Provider (`mock_data.py`)

**Purpose:** Provides test customer profiles for demos.

**Test Profiles:**
| PAN | Name | Scenario |
|-----|------|----------|
| ABCDE1234F | Rahul Sharma | ✅ Approved (Score: 780) |
| FGHIJ5678K | Priya Patel | ⚠️ Conditional (Score: 680) |
| KLMNO9012P | Amit Singh | ❌ Rejected (Score: 520) |

### 5. PDF Generator (`pdf_generator.py`)

**Purpose:** Creates professional Tata Capital sanction letters.

**Features:**
- Tata Capital branding (#004589 blue)
- Professional header with logo area
- Loan details table
- Terms & conditions
- Digital signature note
- Footer with contact info

---

## 🎨 FRONTEND COMPONENTS

### 1. Chat Widget (`ChatWidget.tsx`)

**Purpose:** Main chat interface for customers.

**Features:**
- Message bubbles (user/bot)
- Loading indicators with stage-specific messages
- EMI option cards
- Sanction letter download button
- Auto-scroll to latest message

### 2. Admin Dashboard (`AdminDashboard.tsx`)

**Purpose:** Real-time monitoring interface.

**Components:**
- `LiveChatMirror` - Live view of conversations
- `StatusBar` - Current stage progress
- `RiskMetrics` - Credit score (admin only)
- `ActivityLogs` - Session activity log
- `AgentNetwork` - Visual agent status

### 3. Landing Page (`LandingPage.tsx`)

**Purpose:** Marketing page with product showcase.

### 4. Other Pages
- `PersonalLoans.tsx` - Personal loan info
- `HomeLoans.tsx` - Home loan info
- `BusinessLoans.tsx` - Business loan info
- `EMICalculator.tsx` - EMI calculation tool
- `FAQs.tsx` - Frequently asked questions

---

## 👨‍💼 ADMIN DASHBOARD

### Real-Time Features

The admin dashboard provides live monitoring via WebSocket:

```
┌─────────────────────────────────────────────────────────────┐
│                    ADMIN DASHBOARD                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  SESSION LIST   │  │      LIVE CHAT MIRROR           │   │
│  │                 │  │                                  │   │
│  │  • Session 1 ●  │  │  User: Hi, I need a loan        │   │
│  │  • Session 2 ○  │  │  Bot: Welcome to Tata Capital!  │   │
│  │  • Session 3 ●  │  │  User: 500000                   │   │
│  │                 │  │  Bot: Great! ₹5,00,000 noted... │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              STAGE PROGRESS BAR                      │    │
│  │  [✓][✓][✓][✓][●][ ][ ][ ][ ][ ][ ][ ][ ]           │    │
│  │   1  2  3  4  5  6  7  8  9 10 11 12 13             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────────┐  ┌──────────────────────────────┐    │
│  │  RISK METRICS    │  │      ACTIVITY LOGS           │    │
│  │                  │  │                               │    │
│  │  Credit: 780     │  │  10:01 - Stage: GREETING     │    │
│  │  Risk: LOW       │  │  10:02 - Stage: PURPOSE      │    │
│  │  Status: GOOD    │  │  10:03 - Stage: AMOUNT       │    │
│  └──────────────────┘  └──────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### WebSocket Events

| Event Type | Data | Purpose |
|------------|------|---------|
| `user_message` | Message text | Show user input |
| `bot_response` | Response text | Show bot reply |
| `stage_transition` | Stage info | Update progress |
| `state_update` | Full state | Sync dashboard |

---

## 📄 PDF GENERATION

### Sanction Letter Format

```
┌─────────────────────────────────────────────────────────────┐
│  [TATA BLUE HEADER BAR]                                      │
│  TATA CAPITAL                                                │
│  "We only do what's right for you"                          │
│                                        CIN: U65990MH...      │
│                                        www.tatacapital.com   │
└─────────────────────────────────────────────────────────────┘

           PERSONAL LOAN SANCTION LETTER
           ══════════════════════════════

Date: 02 February 2026          Reference No: TC/PL/20260202/...
Valid Until: 04 March 2026

To,
Mr./Ms. Rahul Sharma
Mobile: 9876543210
PAN: ABCDE1234F

Dear Mr./Ms. Rahul Sharma,

We are delighted to inform you that your application has been
APPROVED by Tata Capital Financial Services Limited.

┌─────────────────────────────────────────────────────────────┐
│                      LOAN DETAILS                            │
├─────────────────────────────────────────────────────────────┤
│  Sanctioned Loan Amount      │      ₹ 5,00,000              │
│  Interest Rate (Fixed)       │      12.5% per annum         │
│  Loan Tenure                 │      24 months               │
│  Monthly EMI                 │      ₹ 23,536                │
│  Total Interest Payable      │      ₹ 64,864                │
│  Total Amount Payable        │      ₹ 5,64,864              │
│  Processing Fee              │      ₹ 10,000 + GST          │
│  EMI Start Date              │      04 March 2026           │
└─────────────────────────────────────────────────────────────┘

Terms & Conditions:
1. This sanction letter is valid for 30 days...
2. Loan disbursement is subject to documentation...
...

[Digital Signature]
Authorized Signatory
Tata Capital Financial Services Limited

┌─────────────────────────────────────────────────────────────┐
│  [TATA BLUE FOOTER BAR]                                      │
│  Tata Capital Financial Services Limited                     │
│  Peninsula Business Park, Lower Parel, Mumbai - 400013       │
│  Helpline: 1860-267-6060 | customercare@tatacapital.com     │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 TESTING & DEMO DATA

### Test Customer Profiles

#### 1. Rahul Sharma (APPROVAL)
```
PAN: ABCDE1234F
Mobile: 9876543210
Credit Score: 780
Result: ✅ APPROVED
Interest Rate: 12.5%
```

#### 2. Priya Patel (CONDITIONAL)
```
PAN: FGHIJ5678K
Mobile: 9123456780
Credit Score: 680
Result: ⚠️ CONDITIONAL
Note: Requires income proof
```

#### 3. Amit Singh (REJECTION)
```
PAN: KLMNO9012P
Mobile: 9988776655
Credit Score: 520
Result: ❌ REJECTED
Reason: Low credit score
```

### Test Flow (Happy Path)

```
User: hi
Bot: [GREETING message]

User: yes, I need a loan
Bot: [PURPOSE message]

User: home renovation
Bot: [AMOUNT message]

User: 5 lakhs
Bot: [CITY message]

User: Mumbai
Bot: [EMPLOYMENT message]

User: salaried
Bot: [NAME message]

User: Rahul Sharma
Bot: [MOBILE message]

User: 9876543210
Bot: [OTP message]

User: 123456
Bot: [KYC message]

User: ABCDE1234F
Bot: [OFFER message with pre-approval]

User: yes
Bot: [TENURE options]

User: 24 months
Bot: [UNDERWRITING processing]

Bot: [SANCTION - Congratulations!]
```

---

## ⚙️ CONFIGURATION & ENVIRONMENT

### Environment Variables

Create `.env` file in `src/backend/`:

```bash
# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key_here

# Enable/Disable Gemini (set to "false" to use hardcoded only)
USE_GEMINI=true

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

### Feature Flags

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_GEMINI` | `true` | Enable AI responses |
| `GEMINI_API_KEY` | Required | Google API key |

---

## 🚀 RUNNING THE APPLICATION

### Prerequisites

- Python 3.11+
- Node.js 18+
- npm or yarn

### Installation

```bash
# Clone repository
git clone https://github.com/your-repo/EY-Tata-Chatbot.git
cd EY-Tata-Chatbot

# Backend setup
cd src/backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Frontend setup
cd ../..
npm install
```

### Starting Servers

```bash
# Terminal 1: Backend
cd src/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
npm run dev
```

### Access URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Admin Dashboard | http://localhost:5173/admin |

### Health Check

```bash
curl http://localhost:8000/health

# Response:
{
  "status": "healthy",
  "gemini_enabled": true,
  "gemini_model": "gemini-2.0-flash",
  "stages": 13
}
```

---

## 📁 PROJECT STRUCTURE

```
EY-Tata-Chatbot/
├── src/
│   ├── backend/
│   │   ├── main.py                 # FastAPI app + Gemini integration
│   │   ├── deterministic_flow.py   # 13-stage state machine
│   │   ├── underwriting_engine.py  # Credit decisioning
│   │   ├── mock_data.py            # Test customer profiles
│   │   ├── pdf_generator.py        # Tata Capital PDFs
│   │   ├── graph_agent.py          # LangGraph agent (optional)
│   │   ├── requirements.txt        # Python dependencies
│   │   └── .env                    # Environment config
│   │
│   ├── components/
│   │   ├── ChatWidget.tsx          # Main chat UI
│   │   ├── Navbar.tsx              # Navigation
│   │   ├── Footer.tsx              # Footer
│   │   └── admin/                  # Admin components
│   │       ├── LiveChatMirror.tsx
│   │       ├── StatusBar.tsx
│   │       ├── RiskMetrics.tsx
│   │       └── ActivityLogs.tsx
│   │
│   ├── pages/
│   │   ├── LandingPage.tsx
│   │   ├── AdminDashboard.tsx
│   │   ├── PersonalLoans.tsx
│   │   └── ...
│   │
│   └── contexts/
│       └── AuthContext.tsx         # Admin authentication
│
├── package.json
├── vite.config.ts
├── tailwind.config.js
├── COMPLETE_SYSTEM_DOCUMENTATION.md  # This file
├── DEMO_INPUTS.md                    # Demo test cases
└── README.md                         # Quick start guide
```

---

## 🔐 SECURITY NOTES

1. **API Key Protection**: Never commit `.env` with real API keys
2. **PAN Validation**: Server-side validation only (no client exposure)
3. **Credit Score**: Never exposed to customer (admin only)
4. **Session Data**: In-memory only (use Redis/DB for production)
5. **CORS**: Currently allows all origins (restrict in production)

---

## 📞 SUPPORT

For issues or questions:
- Check `DEMO_INPUTS.md` for test scenarios
- Review API docs at `/docs`
- Contact: [Your team contact info]

---

**© 2026 Tata Capital | EY Project Team**
