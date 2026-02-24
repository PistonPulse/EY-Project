# 🏦 Tata Capital - AI-Driven Agentic Loan Application System

> **Agentic AI Personal Loan Underwriting System via LangGraph & Gemini Vision**  
> Version 5.0 | Enterprise Edition

An advanced, production-grade conversational AI platform designed to completely eradicate "Form Fatigue" and automate the highly-complex personal loan underwriting process.

This system replaces static legacy forms with a dynamic **LangGraph-inspired State Machine**, handling realtime KYC verification, biometric document scanning (via Gemini OCR), Fixed Obligations to Income Ratio (FOIR) calculations, and Live Security Fraud Tracking without any human intervention.

---

## 🏗️ The Agentic Architecture 

Unlike simple generative chatbots that hallucinate financial data, this system utilizes a strict Master/Worker Agent orchestration model to ensure 100% RBI mathematical compliance.

- **The Master Agent (Deterministic Flow Controller):** Written in FastAPI Python. Controls the 16 stages of the Directed Acyclic Graph. Generative AI is forbidden from changing the core state; only the Master Agent can transition nodes.
- **The Sales Agent:** Powered by **Groq (Llama-3.1-8b-instant)**. Empathizes with the customer and dynamically injects `STAGE_PROMPTS` constraints (e.g., City, Income, Purpose) to persuade the customer down the funnel.
- **The Verification Agent:** Natively manages OTP handshakes. Initiates the **"Identity Lock"** protocol, cryptographically freezing the session state so an attacker cannot alter their PAN or Mobile post-verification.
- **The Underwriting Agent:** A purely mathematical Python node. Strips the LLM of authority. Calculates the **900-Point Dynamic Credit Algorithm**, generates precise DTI (Debt-to-Income) ceilings, and computes compound amortized EMIs (`[P*R*(1+R)^N]/[(1+R)^N-1]`) in under 20 milliseconds.

---

## 🚀 Key Feature Implementations

| Feature | Technical Implementation |
|---------|--------------------------|
| 👁️ **Multimodal OCR KYC** | Streams raw PDF/JPG byte data securely over TLS to **Google Gemini 2.0 Flash Vision** to extract Salary, PAN, and identity. Bytes are strictly maintained in-memory and instantly garbage-collected to prevent PII data leaks. |
| �️ **Identity Spoof Detection** | Backend explicitly compares the *Declared PAN/Name* typed by the user against the *Extracted PAN/Name* off the uploaded Salary Slip. Any mismatch instantly halts the graph and pushes a WebSocket fraud alert. |
| 👨‍💼 **Live WebSocket Admin Dashboard** | Built with **Socket.io + React**. Allows bank supervisors a "God-View" to watch active concurrent conversations and live state transitions in real-time without refreshing the page. |
| � **High Availability Fail-Safes** | Implements a 5-Key continuous rotation for the Groq API to prevent Rate-Limiting DoS attacks. If the cloud drops entirely, the OCR and Chat cascade down into local regex Mock Simulators to guarantee the demo never crashes. |
| ⚡ **Vite + Tailwind Frontend** | A heavily psychometric UI intended to lower financial anxiety. Features drag-and-drop document uploads, simulated typing indicators, and immediate quick-reply chips. |

---

## 🌐 The Synthetic Microservice Ecosystem

Real applications don't query flat files. We engineered a massive synthetic backend architecture simulating an entire corporate Kubernetes topography across multiple localhost ports:

- **Port 5001 (CRM Master):** Returns localized JSON profiles identifying "existing prime customers".
- **Port 5002 (CIBIL Simulator):** Simulates a secure live fetch to a Credit Bureau database based on dynamic PAN requests.
- **Port 5003 (Offer Mart):** Generates specialized "Pre-Approved" JSON payloads for custom marketing funnels.

> **Newly Added: Custom Acquisition Flows (Ads & Email)**
> Direct marketing links bypass the GREETING stage, seamlessly merging the user directly into the soft-credit checks and triggering the React `DOCUMENT_UPLOAD` component seamlessly!

---

## ⚙️ Quick Start Installation

### Prerequisites
- Python 3.11+
- Node.js 18+
- Active API Keys for Groq & Google Gemini

### 1. Repository Setup
```bash
git clone https://github.com/tanishamukherjee/EY-Tata-Chatbot.git
cd EY-Tata-Chatbot
```

### 2. Backend Initialization (FastAPI)
```bash
cd src/backend
pip install -r requirements.txt
cp .env.example .env
# IMPORTANT: Insert GEMINI_API_KEY and GROQ_API_KEY into .env
```

### 3. Frontend Initialization (React + Vite)
```bash
cd ../..
npm install
```

---

## � Running The Project

Because of the decoupled Kubernetes-style architecture, you must run three distinct terminal environments.

**Terminal 1: The React Frontend**
```bash
npm run dev
# Starts on http://localhost:5173
```

**Terminal 2: The Main FastAPI Server**
```bash
cd src/backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# Starts the Master Agent on Port 8000
```

**Terminal 3: The Mock Microservices**
```bash
cd src/backend
python3 mock_servers.py
# Bootstraps Port 5001, 5002, and 5003 simultaneously
```

---

## 👥 Team & Co-Authorship

This project is a collaborative effort engineered by:

- **Tanish Gupta** ([@PistonPulse](https://github.com/PistonPulse)) - *System Architecture, State Machine & Deterministic Engine*
- **Tanisha Mukherjee** ([@tanishamukherjee](https://github.com/tanishamukherjee)) - *RiskControlAgent, Multi-Layer Fraud Detection & Document Intelligence*

---

## 📚 Deep Dive Technical Documentation

For an absolutely exhaustive breakdown of the architectural code, the risk math, and the compliance mechanisms, please refer to the dedicated whitepapers located in the project root:

1. **[COMPLETE_SYSTEM_DOCUMENTATION.md](COMPLETE_SYSTEM_DOCUMENTATION.md)** — The 10,000-foot view of the entire workflow.
2. **[DEMO_INPUTS.md](DEMO_INPUTS.md)** — Demo test scenarios and synthetic input data.

---
*Developed for the EY-Tata Capital Challenge 2026*
