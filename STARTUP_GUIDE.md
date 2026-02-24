# TataSmartAgent v4.0 - Explicit Startup Guide

Welcome to the **TataSmartAgent** project! Because this codebase simulates a true Enterprise architecture (decoupled frontend, backend orchestrator, and multiple isolated microservices), you must explicitly start **three** separate processes in **three separate terminal windows**.

---

### Terminal 1: The Mock Microservices (CRM, Bureau, Offer Mart)
This terminal runs three independent FastAPI servers in the background concurrently on Ports 5001, 5002, and 5003.

```bash
# 1. Open Terminal 1
# 2. Ensure you are in the project root: `cd "EY PROJECT - TANISHA FINAL"`
# 3. Run the following command:
python3 src/backend/mock_servers.py
```
*(Leave this terminal open and running. Do not close it or the "Digital Ad" and "Marketing Email" flows will break because they rely on these disconnected databases).*

<br>

### Terminal 2: The Main Backend Orchestrator (Port 8000)
This terminal runs the primary FastAPI application containing the Master Agent, the 16-Stage Deterministic Flow, and the WebSocket connection for the Admin Dashboard.

```bash
# 1. Open Terminal 2
# 2. Ensure you are in the project root: `cd "EY PROJECT - TANISHA FINAL"`
# 3. Run the Uvicorn ASGI server as a module:
python3 -m uvicorn src.backend.main:app --reload --port 8000
```
*(Leave this terminal open. If this stops, the chatbot will stop responding entirely).*

<br>

### Terminal 3: The React Frontend (Vite)
This terminal runs the user interface where you can see the landing page, the chatbot widget, and the senior loan officer admin dashboard.

```bash
# 1. Open Terminal 3
# 2. Ensure you are in the project root: `cd "EY PROJECT - TANISHA FINAL"`
# 3. Start the Vite development server:
npm run dev
```

---

### Accessing the Application

Once all three terminals are running without errors, open your web browser:
- **Landing Page & Chatbot:** [http://localhost:5173](http://localhost:5173)
- **Admin Dashboard:** [http://localhost:5173/admin](http://localhost:5173/admin) (Password: `admin` / `tata123`)

**To stop the servers**, return to each terminal and press `Ctrl + C`.
