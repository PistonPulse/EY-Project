# 🏦 Tata Capital AI Loan Underwriter

**EY Techathon 2026** - Enterprise-grade AI-powered loan underwriting system with Hub-and-Spoke multi-agent orchestration, real-time fraud detection, and intelligent document verification.

<div align="center">

![Tata Capital](https://img.shields.io/badge/Tata_Capital-004589?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI_Powered-00D9FF?style=for-the-badge&logo=google&logoColor=black)
![LangGraph](https://img.shields.io/badge/LangGraph-121212?style=for-the-badge&logo=chainlink&logoColor=white)
![Gemini Vision](https://img.shields.io/badge/Gemini_Vision-4285F4?style=for-the-badge&logo=google&logoColor=white)
![Status](https://img.shields.io/badge/Status-Production_Ready-success?style=for-the-badge)

**Instant loan approvals in under 60 seconds with complete fraud detection and document intelligence**

</div>

---

## ✨ Key Highlights

| Feature | Description |
|---------|-------------|
| 🤖 **Hub-and-Spoke Architecture** | Master Agent orchestrates 6 specialized agents |
| 🔍 **AI Document Verification** | Gemini Vision extracts & validates documents |
| 🛡️ **Real-time Fraud Detection** | Mathematical integrity + visual forgery checks |
| 👥 **Dual User Flows** | Existing customers vs New prospects handling |
| 📊 **Live Admin Dashboard** | Real-time agent monitoring & trust scoring |
| 📄 **Instant Sanction Letters** | Auto-generated PDF with digital verification |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Google Gemini API Key (with Vision access)

### Environment Setup
```bash
# Create .env file in src/backend/
GEMINI_API_KEY=your_gemini_api_key_here
```

### Backend Setup
```bash
cd src/backend
pip install -r requirements.txt
pip install thefuzz python-Levenshtein reportlab  # Additional dependencies

# Start server
python main.py  # Runs on http://localhost:8000
```

### Frontend Setup
```bash
cd src/frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

### Demo Workflow
See **[DEMO_INPUTS.md](./DEMO_INPUTS.md)** for complete step-by-step guide with all scenarios.

---

## 📁 Project Structure

```
EY-Project/
├── README.md                        # Project documentation
├── DEMO_INPUTS.md                   # Demo workflow guide
├── demo_documents/                  # Sample PDFs for testing
│
├── src/
│   ├── backend/
│   │   ├── main.py                  # FastAPI server + Document upload + WebSocket
│   │   ├── graph_agent.py           # Hub-and-Spoke multi-agent LangGraph (~2100 lines)
│   │   ├── mock_data.py             # Static demo customer data
│   │   ├── mock_data_provider.py    # Dynamic data provider with lead creation
│   │   ├── pdf_generator.py         # Sanction letter PDF generation
│   │   ├── requirements.txt         # Python dependencies
│   │   ├── .env                     # API keys (gitignored)
│   │   └── start.sh                 # Backend startup script
│   │
│   └── frontend/
│       ├── src/
│       │   ├── components/          # React UI components
│       │   ├── pages/               # Landing, Dashboard, Admin pages
│       │   └── contexts/            # React context providers
│       └── package.json             # Node.js dependencies
│
└── package.json                     # Root package.json
```

---

## 🏗️ System Architecture

### Hub-and-Spoke Multi-Agent Design

```
                    ┌─────────────────────────────────────────┐
                    │           MASTER AGENT (HUB)            │
                    │      Intelligent Request Router         │
                    │   Analyzes intent & manages workflow    │
                    └─────────────────┬───────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  SALES AGENT  │           │ VERIFICATION  │           │ UNDERWRITING  │
│               │           │    AGENT      │           │    AGENT      │
│ • Loan inquiry│           │ • KYC check   │           │ • Risk rules  │
│ • Negotiation │           │ • Phone/Name  │           │ • Approval    │
│ • Product info│           │ • Lead create │           │ • EMI calc    │
└───────────────┘           └───────────────┘           └───────────────┘
        │                             │                             │
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌───────────────┐           ┌───────────────┐
│  TRUST AGENT  │           │   DOCUMENT    │           │  FRAUD CHECK  │
│               │           │    AGENT      │           │    AGENT      │
│ • Trust score │           │ • Doc guidance│           │ • Math verify │
│ • Behavior    │           │ • Upload flow │           │ • Visual check│
│ • Risk flags  │           │ • Status track│           │ • Bank cross  │
└───────────────┘           └───────────────┘           └───────────────┘
```

### Agent Responsibilities

| Agent | Role | Key Functions |
|-------|------|---------------|
| **Master Agent** | Hub/Orchestrator | Routes requests to appropriate spoke agents |
| **Sales Agent** | Product Specialist | Handles inquiries, negotiation, interest rates |
| **Verification Agent** | KYC Handler | Identity verification, lead creation for new users |
| **Underwriting Agent** | Risk Analyst | Loan approval, EMI calculations, limit decisions |
| **Trust & Safety Agent** | Risk Monitor | Real-time trust scoring, behavioral analysis |
| **Document Agent** | Doc Manager | Required docs list, upload guidance, status tracking |
| **Fraud Check Agent** | Fraud Detector | Mathematical integrity, visual forgery, bank cross-check |

---

## 👥 Dual User Flow

### Flow 1: Existing Customers (Marketing Emails)
```
User arrives → Provides phone/name → Verified against database → 
Pre-approved offer shown → Document upload → Instant approval
```

### Flow 2: New Prospects (Digital Ads)
```
User arrives → Provides phone/name → NOT found in database → 
Lead created → Collects income/employment → Risk assessment → 
Document upload → Conditional approval
```

---

## 🔐 Fraud Detection System

### Three-Layer Verification

#### 1️⃣ Mathematical Integrity Check
```python
# Validates salary slip arithmetic
(Basic Pay + HRA + Allowances) - (PF + Tax + Deductions) = Net Pay
# Tolerance: ±₹10 for rounding
# Status: FRAUD_DETECTED if mismatch > ₹10
```

#### 2️⃣ Bank Statement Cross-Check
```python
# Verifies salary credit in bank statement
# Checks: Amount within 5% tolerance
# Window: ±5 days from salary date
# Status: DISCREPANCY if not found
```

#### 3️⃣ Visual Forgery Detection (Gemini Vision)
```python
# AI analyzes document images for:
- Font consistency
- Alignment quality
- Signs of digital editing
- Suspicion score (0-100)
# Status: MANUAL_REVIEW if score > 70
```

### Fraud Response
When fraud is detected, the system responds politely:
> "I'm having trouble verifying the authenticity of your uploaded document. Please upload the original PDF downloaded directly from your payroll portal."

---

## 📄 Document Intelligence (Gemini Vision)

### Supported Documents

| Document | Extracted Fields | Verification |
|----------|------------------|--------------|
| **Salary Slip** | Basic, HRA, Allowances, Deductions, Net Pay, Employer | Math check + Visual |
| **PAN Card** | PAN Number, Full Name, DOB, Father's Name | Name match + Visual |
| **Bank Statement** | Transactions, Credits, Debits, Balance, Salary Credits | Cross-check + Visual |
| **CIBIL Report** | Credit Score, History, Defaults | Score validation |

### Strict Verification Rules

| Rule | Threshold | Action |
|------|-----------|--------|
| **Salary Match** | Document salary < 90% of claimed | Use documented amount |
| **Name Match** | Fuzzy match < 80% | Reject document |
| **Suspicion Score** | > 70 | Flag for manual review |

---

## 🧠 Underwriting Logic

### Rule-Based Decision Engine

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNDERWRITING DECISION TREE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Loan Amount ≤ Pre-approved Limit?                              │
│       │                                                          │
│       ├── YES → ✅ INSTANT APPROVAL                              │
│       │         • No documents needed (for 750+ credit)          │
│       │         • EMI auto-calculated                            │
│       │                                                          │
│       └── NO → Loan ≤ 2x Limit?                                 │
│                    │                                             │
│                    ├── YES → ⚠️ CONDITIONAL APPROVAL             │
│                    │         • Requires salary slip verification │
│                    │         • EMI must be ≤ 50% of income       │
│                    │                                             │
│                    └── NO → ❌ REJECT                            │
│                              • Exceeds risk threshold            │
│                              • Credit score < 700 = Reject       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Pre-Approved Limit Calculation

| Credit Score | Multiplier | Max Limit |
|--------------|------------|-----------|
| 750+ | 60x monthly salary | ₹20,00,000 |
| 700-749 | 48x monthly salary | ₹15,00,000 |
| Below 700 | 36x monthly salary | ₹10,00,000 |

### Interest Rate Negotiation
- **Base Rate**: 10.5% - 14.5% (based on credit score)
- **Negotiation**: Up to 5 rounds of rate reduction
- **Min Rate**: 9.5% (for excellent profiles)

---

## 📊 Admin Dashboard Features

### Real-Time Monitoring
- **Live Chat Feed**: See all customer conversations
- **Agent Activity**: Track which agent is handling each request
- **Trust Score Graph**: Real-time trust score evolution

### Metrics Tracked
| Metric | Description |
|--------|-------------|
| Trust Score | 0-100 composite score |
| Risk Category | LOW / MEDIUM / CRITICAL / FRAUD |
| Behavioral Flags | Urgency, Inconsistency, Aggression |
| Document Status | Uploaded / Verified / Rejected |
| Agent Routing | Visual graph of agent interactions |

---

## 🔑 API Endpoints

### Chat & Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/chat` | Send message, receive AI response |
| GET | `/session/{id}` | Get session information |
| WS | `/ws/{session_id}` | WebSocket for real-time chat |

### Documents
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload document for AI verification |
| GET | `/api/sanction-letter/{id}` | Download sanction letter PDF |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| WS | `/admin/stream` | Admin dashboard WebSocket |
| GET | `/admin/metrics` | Get aggregated metrics |

---

## 🛠️ Technology Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async web framework |
| **LangGraph** | Multi-agent orchestration & state management |
| **Google Gemini 2.0 Flash** | LLM for conversation & decisions |
| **Google Gemini 1.5 Flash** | Vision API for document analysis |
| **WebSocket** | Real-time bidirectional communication |
| **ReportLab** | PDF generation for sanction letters |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 18** | UI framework |
| **TypeScript** | Type-safe development |
| **Vite** | Fast build tool |
| **TailwindCSS** | Utility-first styling |
| **Framer Motion** | Animations |

### AI & ML
| Component | Model/Library |
|-----------|---------------|
| **Chat LLM** | Gemini 2.0 Flash |
| **Vision API** | Gemini 1.5 Flash |
| **Fuzzy Matching** | thefuzz (Levenshtein) |
| **Agent Framework** | LangGraph StateGraph |

---

## 🔐 Security Features

- ✅ **Document Authenticity**: AI-powered forgery detection
- ✅ **Identity Verification**: Fuzzy name matching across documents
- ✅ **Salary Verification**: Mathematical consistency checks
- ✅ **Bank Cross-Check**: Transaction verification
- ✅ **Session Management**: Secure session handling
- ✅ **API Key Protection**: Environment variable storage

---

## 📈 Performance

| Metric | Value |
|--------|-------|
| Average Response Time | < 2 seconds |
| Document Processing | < 5 seconds |
| Concurrent Sessions | 100+ |
| Loan Decision Time | < 60 seconds |

---

## 🧪 Testing the System

### Test Scenarios

#### Scenario 1: Instant Approval (Existing Customer)
```
Name: Priya Sharma
Phone: 9876543210
Loan: ₹5,00,000
Expected: ✅ Instant approval, trust score 65→90
```

#### Scenario 2: New Prospect Flow
```
Name: New User
Phone: 9999999999
Income: ₹75,000/month
Expected: Lead created, conditional approval after docs
```

#### Scenario 3: Fraud Detection Test
```
Upload: Tampered salary slip (mismatched numbers)
Expected: ⚠️ Document verification issue message
```

---

## 🔧 Configuration

### Environment Variables
```env
# src/backend/.env
GEMINI_API_KEY=your_api_key_here
```

### Key Settings (graph_agent.py)
```python
# Fraud Detection Thresholds
SALARY_MATH_TOLERANCE = 10          # ₹10 rounding tolerance
BANK_DATE_WINDOW = 5                # ±5 days for salary credit
VISUAL_SUSPICION_THRESHOLD = 70     # Trigger manual review

# Verification Rules
NAME_MATCH_THRESHOLD = 80           # 80% fuzzy match required
SALARY_MATCH_THRESHOLD = 0.90       # 90% of claimed salary
```

---

## 📝 Dependencies

### Python (requirements.txt)
```
fastapi==0.115.5
langgraph==2.55
langchain-google-genai==2.0.8
google-generativeai==0.8.3
python-multipart==0.0.12
websockets==14.1
thefuzz
python-Levenshtein
reportlab
python-dotenv
```

### Node.js (package.json)
```
react: ^18.x
typescript: ^5.x
vite: ^5.x
tailwindcss: ^3.x
framer-motion: ^11.x
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is developed for the **EY Techathon 2026** competition.

---

<div align="center">

### Built with ❤️ for EY Techathon 2026

**Tata Capital AI Loan Underwriter**

![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-121212?style=flat-square&logo=chainlink&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=flat-square&logo=google&logoColor=white)

**🏆 Intelligent. Secure. Instant.**

</div>
