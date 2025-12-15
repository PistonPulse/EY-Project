# 🏦 Tata Capital AI Loan Underwriter

**EY Project Demo** - AI-powered loan underwriting system with multi-agent orchestration, real-time risk assessment, and dynamic decision-making.

<div align="center">

![Tata Capital](https://img.shields.io/badge/Tata_Capital-004589?style=for-the-badge)
![AI Powered](https://img.shields.io/badge/AI_Powered-00D9FF?style=for-the-badge&logo=openai&logoColor=black)
![LangGraph](https://img.shields.io/badge/LangGraph-121212?style=for-the-badge&logo=chainlink&logoColor=white)
![Status](https://img.shields.io/badge/Status-Ready-success?style=for-the-badge)

**Instant loan approvals in under 60 seconds with complete agent orchestration**

</div>

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Google Gemini API Key

### Backend Setup
```bash
cd "src/backend"
pip3 install -r requirements.txt
./start.sh  # or: python3 -m uvicorn main:app --host localhost --port 8000 --reload
```

### Frontend Setup
```bash
npm install
npm run dev  # Runs on http://localhost:5173
```

### Demo Workflow
See **[DEMO_INPUTS.md](./DEMO_INPUTS.md)** for complete step-by-step guide with all 3 scenarios.

---

## 📁 Project Structure

```
/EY Project/
├── README.md                    # Project overview
├── DEMO_INPUTS.md              # Complete demo workflow guide
├── demo_documents/             # Sample PDFs for testing
├── src/
│   ├── backend/
│   │   ├── main.py            # FastAPI server + WebSocket
│   │   ├── graph_agent.py     # Multi-agent LangGraph logic
│   │   ├── mock_data.py       # Demo customer data
│   │   ├── requirements.txt   # Python dependencies
│   │   └── start.sh          # Backend startup script
│   ├── components/            # React UI components
│   ├── pages/                 # React pages (Landing, Dashboard, etc.)
│   └── contexts/              # React context providers
└── package.json               # Node.js dependencies
```

---

## 🎯 Features

### Customer-Facing
- ✅ Real-time AI chat with loan negotiation
- ✅ Dynamic interest rate adjustment (5 rounds)
- ✅ Document upload with instant verification
- ✅ Sanction letter generation & download
- ✅ Three demo scenarios (Approval, Conditional, Fraud)

### Admin Dashboard
- ✅ Live chat monitoring
- ✅ Real-time trust score updates (0-100)
- ✅ Agent neural network visualization
- ✅ Behavioral analysis metrics
- ✅ Risk category tracking (LOW/MEDIUM/CRITICAL/FRAUD)
- ✅ Activity logs with agent orchestration

### Technical
- ✅ Multi-agent architecture (Master, Sales, Verification, Underwriting, Trust & Safety)
- ✅ WebSocket for real-time updates
- ✅ Demo mode (zero API costs, scripted responses)
- ✅ Production mode (full Gemini AI integration)

---

## 🎬 Demo Scenarios

See [DEMO_INPUTS.md](DEMO_INPUTS.md) for complete workflow guide.

| Customer | Credit | Outcome | Trust Score Journey |
|----------|--------|---------|---------------------|
| **Priya Sharma** | 785 (Excellent) | ✅ Instant Approval | 65 → 90 |
| **Amit Patel** | 680 (Fair) | ⚠️ Conditional Approval | 55 → 75 |
| **Rajesh Kumar** | 350 (Poor) | ❌ Fraud Rejection | 35 → 10 |

---

## 🤖 Multi-Agent Architecture

```
Master Agent (Orchestrator)
    ├── Sales Agent (Negotiation + Info Collection)
    ├── Verification Agent (KYC + Document Check)
    ├── Underwriting Agent (Risk Rules + Approval Decision)
    └── Trust & Safety Agent (Fraud Detection)
```

---

## 🧠 Underwriting Logic

### **Rule A**: Loan ≤ Pre-approved Limit → ✅ **INSTANT APPROVAL**
### **Rule B**: Loan ≤ 2x Limit → ⚠️ **CONDITIONAL** (Request salary slip, verify EMI ≤ 50% income)
### **Rule C**: Loan > 2x Limit OR Credit Score < 700 → ❌ **REJECT**

---

## 🔐 Login Credentials

**Admin Dashboard**: `admin` / `admin123`

---

## 📊 Tech Stack

- **Backend**: FastAPI, Python 3.9, LangGraph, Google Gemini
- **Frontend**: React, TypeScript, Vite, TailwindCSS
- **Real-time**: WebSocket
- **AI**: Google Gemini 1.5 Pro

---

## 🔐 Demo vs Production Mode

### **Demo Mode** (Current)
```python
# In src/backend/graph_agent.py, line 18:
DEMO_MODE = True  # Uses scripted flows, zero API calls
```

### **Production Mode** (Real AI)
```python
# In src/backend/graph_agent.py, line 18:
DEMO_MODE = False  # Uses Gemini API for real conversations
```

---

## 🛠️ Development

Both servers auto-reload on file changes:
- Backend: `--reload` flag on uvicorn
- Frontend: Vite HMR

---

## 📝 Notes

- Demo mode is enabled by default (DEMO_MODE = True in graph_agent.py)
- All three scenarios use scripted responses for consistent demos
- Trust scores and behavioral metrics update dynamically
- WebSocket auto-reconnects if connection drops

---

<div align="center">

**Built for EY Project | Tata Capital AI Underwriter Demo**

![React](https://img.shields.io/badge/React-61DAFB?style=flat-square&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-121212?style=flat-square&logo=chainlink&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_AI-4285F4?style=flat-square&logo=google&logoColor=white)

</div>
