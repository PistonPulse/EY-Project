# 🏦 Tata Capital - AI Loan Chatbot

> **AI-Powered Personal Loan Application System with Google Gemini**  
> Version 4.0 | February 2026

> [!IMPORTANT]
> **Active Backend Entry Point:** `src/backend/main.py`  
> Do **not** use `backend/main.py` — that module contains the production-architecture scaffolding (agents, orchestration) and is not yet wired to serve traffic.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API Key

### Installation

```bash
# Clone repository
git clone https://github.com/tanishamukherjee/EY-Tata-Chatbot.git
cd EY-Tata-Chatbot

# Backend setup
cd src/backend
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Frontend setup
cd ../..
npm install
```

### Running

```bash
# Terminal 1: Backend
cd src/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Frontend
npm run dev
```

### Access
| Service | URL |
|---------|-----|
| 🌐 Frontend | http://localhost:5173 |
| ⚙️ Backend API | http://localhost:8000 |
| 📚 API Docs | http://localhost:8000/docs |
| 👨‍💼 Admin Dashboard | http://localhost:5173/admin |

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🤖 **Gemini AI + Groq Fallback** | Dynamic responses via Gemini 2.0 Flash → Groq LLaMA 3.1 → Static |
| 📊 **16-Stage Flow** | Deterministic loan application journey |
| 👨‍💼 **Admin Dashboard** | Real-time monitoring via WebSocket |
| 📄 **PDF Generation** | Professional Tata Capital sanction letters |
| 🔒 **Secure Validation** | PAN, mobile, OTP verification |
| 💰 **EMI Calculator** | Dynamic tenure-based calculations |
| 🛡️ **AI Guardrails** | Financial data never sent to LLM; sanitizer strips leaked numbers |

---

## 🧪 Test Profiles

| PAN | Name | Result |
|-----|------|--------|
| `ABCDE1234F` | Rahul Sharma | ✅ Approved |
| `FGHIJ5678K` | Priya Patel | ⚠️ Conditional |
| `KLMNO9012P` | Amit Singh | ❌ Rejected |

---

## 📚 Documentation

For complete system documentation, see:
- **[COMPLETE_SYSTEM_DOCUMENTATION.md](COMPLETE_SYSTEM_DOCUMENTATION.md)** - Full technical docs
- **[DEMO_INPUTS.md](DEMO_INPUTS.md)** - Demo test scenarios
- **[TEST_INPUTS.md](TEST_INPUTS.md)** - Test input reference

---

## 🏗️ Architecture

```
Frontend (React + Vite)       →     Backend (FastAPI + Python)
        ↓                                     ↓
    Chat Widget                    Deterministic 16-Stage Flow
        ↓                                     ↓
  Admin Dashboard              Gemini → Groq → Static Fallback
  (WebSocket live)                        ↓
                                PDF Generator + Mock Services
```

### AI Fallback Chain
```
Gemini API ──fail──→ Groq API ──fail──→ Static Response
     ↓                    ↓                     ↓
  sanitize()          sanitize()         FALLBACK_RESPONSES
```

---

## 📁 Project Structure

```
EY-Tata-Chatbot/
├── src/
│   ├── backend/
│   │   ├── main.py                 # FastAPI + Gemini integration
│   │   ├── deterministic_flow.py   # 13-stage state machine
│   │   ├── pdf_generator.py        # Tata Capital PDFs
│   │   └── mock_data.py            # Test profiles
│   ├── components/
│   │   ├── ChatWidget.tsx          # Chat interface
│   │   └── admin/                  # Admin components
│   └── pages/
│       └── AdminDashboard.tsx      # Admin panel
├── COMPLETE_SYSTEM_DOCUMENTATION.md
└── README.md
```

---

## 🔐 Environment Variables

```bash
# src/backend/.env (or project-root .env)
GEMINI_API_KEY=your_api_key_here
USE_GEMINI=true            # Set to "false" for hardcoded-only mode
GROQ_API_KEY=your_groq_key # Fallback LLM (optional)
GROQ_MODEL_NAME=llama-3.1-8b-instant
```

> ⚠️ **Never commit `.env` to version control.** It is already in `.gitignore`.

---
