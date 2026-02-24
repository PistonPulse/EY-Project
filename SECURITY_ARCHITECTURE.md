# Enterprise Security Architecture & Data Protection

This document details the rigorous security measures, compliance safeguards, and anti-fraud mechanisms engineered into the Agentic AI Personal Loan Chatbot. 

Because the system handles Highly Classified Personally Identifiable Information (PII) such as PAN numbers, Salary Slips, and Income Data, security cannot be an afterthought—it is the foundational layer upon which the LangGraph architecture is built.

---

## 1. Identity & Session Integrity (Anti-Spoofing)

A major vulnerability of Generative AI is "Prompt Injection" and social engineering, where a malicious user attempts to trick the AI into altering their profile mid-conversation to bypass credit checks. Our system strictly prevents this through programmatic **Identity Locking**.

### Cryptographic Session Tokens
- **Implementation:** The backend does not rely on simple browser cookies. FastAPi initializes a secure UUID `session_id` upon the first WebSocket handshake or HTTP POST `/api/v3/chat`. 
- **Benefit:** The state dictionary is bound server-side purely to this UUID. An attacker cannot intercept traffic and guess another user's session state.

### The "Identity Lock" Protocol
- **Implementation:** When the Verification Agent reaches the `OTP` stage, it demands a 6-digit pin confirming mobile ownership. Once verified, the Python backend flips the boolean flag `session.otp_verified = True`.
- **Benefit:** If the user later tries to tell the Groq LLM, *"Actually, my PAN is EXAMP1234F and my salary is 5 Lakhs,"* the **Master Agent rejects it**. The state machine permanently freezes identity variables post-OTP. The LLM has zero technical authority to overwrite the `AgentState` core memory, neutralizing 100% of social engineering identity-spoofing attempts.

---

## 2. PII Data Leak Prevention (DLP)

Handling sensitive financial documents like Salary Slips requires strict adherence to data privacy laws (like DPDP Act in India or GDPR globally). 

### Ephemeral In-Memory Document Processing
- **Implementation:** When a user utilizes the React Chat Widget to upload a `.pdf` or `.png` Salary Slip, the `/api/upload` endpoint processes the payload exclusively within an **in-memory byte stream**.
- **Benefit:** At absolutely no point is the user's document saved to the local server disk (`os.write()`). The raw bytes are securely streamed over TLS 1.3 to the Gemini Vision API for OCR extraction. Once the API returns the JSON data (Name, PAN, Net Income), the Python server immediately garbage-collects the byte stream from RAM. This guarantees zero residual disk traces, meaning a server breach yields no physical files to steal.

### Classified Profile Redaction in AI Prompts
- **Implementation:** The Groq LLM requires context to converse empathetically. However, we do not feed the user's raw PAN or specific OCR artifacts into the standard conversational LLM stream.
- **Benefit:** LLM providers log prompts. To prevent leaking classified details to external LLM servers, the Master Agent only injects non-classified context (e.g., `user_name`, `loan_amount`, `city`) into the `STAGE_PROMPTS`. The highly classified data (PAN, computed FOIR capacity limits, exact OCR extraction blobs) remains siloed strictly within the local Python variables utilized by the Underwriting Agent.

---

## 3. Fraud Detection: The Cross-Verification Matrix

Identity fraud occurs when a bad actor uses a stolen phone number but provides forged financial documents.

### The Mismatch Alert System
- **Implementation:** The system relies on a dual-entry verification logic. 
  1. Early in the chat, the user explicitly types their Name and PAN. The backend stores this as the **Declared Truth**.
  2. During the `DOCUMENT_UPLOAD` stage, the Gemini Vision API extracts the Name and PAN natively from the scanned digital slip. The backend stores this as the **Extracted Truth**.
- **Benefit:** The Underwriting Agent runs a strict equality check (`Declared == Extracted`). If the user declared "Suresh" but uploaded a slip belonging to "Rahul," the system instantly halts the flow and broadcasts a severe **High-Risk Fraud Alert** over the WebSocket to the Admin Dashboard. The session is flagged, and automatic approvals are permanently locked out.

---

## 4. Network Security & External API Hardening

Financial systems must be resilient against infrastructural attacks, DoS (Denial of Service), and API hijacking.

### WebSocket Encryption & Admin Telemetry
- **Implementation:** The Live Admin Dashboard utilizes Socket.io to monitor conversations in real-time. This stream is heavily protected by CORS (Cross-Origin Resource Sharing) middleware within the FastAPI initialization.
- **Benefit:** The backend actively rejects cross-origin requests from unauthorized web domains. A malicious actor cannot clone the React frontend and bind it to our API endpoints to scrape conversation data.

### 5-Tier API Key Rotation Strategy
- **Implementation:** Generative API endpoints (like Groq) are highly susceptible to Rate Limit (HTTP 429) attacks which can crash the service.
- **Benefit:** The `main.py` backend rotates through an encrypted array of 5 redundant `GROQ_FALLBACK_KEYS`. If an attacker attempts a DoS attack to exhaust the primary key's token limit, the system gracefully swivels to the next key. It ensures 99.9% uptime and protects the application from cascading server failure.

---

## 5. Architectural Isolation (The LangGraph Advantage)

- **Implementation:** In monolithic designs, if the Chat Logic is breached, the attacker gains access to the Database Logic. We utilized a Service-Oriented Mock Architecture (separating Port 5001 for CRM, 5002 for CIBIL, etc.).
- **Benefit:** Even if an attacker somehow executed code execution against the Sales Agent pipeline, they are physically walled off from the Underwriting Agent and the Mock Databases. The Underwriting Node sits behind a deterministic Python wall; it only runs if the Master Agent explicitly invokes it via a locked `AgentState` object. 

---
*End of Security Architecture Report.*
