# ONGC IntelliAssist

ONGC IntelliAssist is a secure, pure Retrieval-Augmented Generation (RAG) assistant for ONGC and enterprise knowledge workflows.

## Main features

- JWT-authenticated, role-aware access with backend validation, protected routes, server-side logout revocation, and user-isolated state.
- Pure RAG answering from user-uploaded documents and the ONGC multi-domain knowledge base, with no general AI fallback.
- Document upload and retrieval for PDF, DOCX, and TXT files; each user's uploaded library is isolated from other users.
- ONGC and enterprise knowledge coverage including operations, exploration, HSE, HR, finance, procurement, governance, sustainability, IT, and cybersecurity.
- Chat history, citations, feedback, and per-user analytics.
- ONGC-branded React interface with responsive chat, document focus mode, and dark mode.

## Architecture

The FastAPI backend authenticates each request and persists chats, messages, feedback, audit logs, and document ownership in SQLite. The retrieval service searches user-owned uploaded content where applicable and the built-in ONGC/enterprise knowledge base. Ollama is used only to generate grounded answers from retrieved context. If relevant context is unavailable, the backend returns a controlled information-not-found response instead of answering from general model knowledge. The Vite/React client validates the session with the backend before rendering protected interfaces.

## Technology stack

- Frontend: React, Vite, Tailwind CSS, React Router, Lucide
- Backend: FastAPI, SQLAlchemy, Pydantic, JWT
- Retrieval: local embeddings, document chunking, pure RAG knowledge retrieval
- Model runtime: Ollama (default model: `llama3.2`)
- Persistence: SQLite (local development)

## Local setup

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Configure production settings through environment variables or a local `.env` file; never commit secrets, database credentials, or JWT keys.

At minimum, set `SECRET_KEY` to a long random value. To create an initial admin only on a fresh database, set `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD` locally; these values are never stored in source control.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The application starts on the Login page. Accounts are authenticated by the backend before the dashboard is shown.

### Ollama

Install Ollama, then run:

```powershell
ollama pull llama3.2
ollama serve
```

## Folder structure

```text
backend/
  app/                 # API routes, models, security, and RAG services
  knowledge_base/      # ONGC and enterprise markdown knowledge sources
  requirements.txt
frontend/
  src/                 # React application and styles
  package.json
storage/uploads/       # Local runtime uploads (ignored by Git)
docker-compose.yml
```

## Security notes

Runtime databases, user uploads, generated indexes, virtual environments, Node dependencies, logs, and `.env` files are excluded from Git. Set a strong, unique JWT secret for any non-development deployment.

## How to Run the Project

### Prerequisites
1. **Python Version Required**: Python 3.10 to 3.14 (tested on 3.14.2)
2. **Node.js Version Required**: Node.js v18+ or v20+

### Step 1: Ollama Setup (Local LLM Support)
1. **Ollama Installation**: Download and install Ollama from [ollama.com](https://ollama.com).
2. **Download Model**: Run the download command:
   ```bash
   ollama pull llama3.2
   ```
3. Start the Ollama service (usually runs automatically after installation, or run `ollama serve`).

### Step 2: Backend Setup
1. Open a terminal and navigate to the backend directory:
   ```bash
   cd backend
   ```
2. **Virtual Environment Creation**:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - On Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
   - On Windows (CMD): `.\venv\Scripts\activate.bat`
   - On Linux/macOS: `source venv/bin/activate`
4. **Package Installation**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Environment Variables**: Configure the `.env` file in the `backend/` directory. Required variables:
   - `SECRET_KEY`: A long, unique random string for JWT signatures.
   - `BOOTSTRAP_ADMIN_EMAIL`: Initial admin username (defaults to `admin@ongc.com`).
   - `BOOTSTRAP_ADMIN_PASSWORD`: Initial admin password (defaults to `Admin@12345`).
   - `GROQ_API_KEY`: Groq API Key (for high-speed, high-accuracy synthesis and web fallbacks).

### Step 3: Start the Backend
1. **Backend Run Command**: Start the server using the conflict-resolving script:
   ```bash
   python start_server.py --port 8000
   ```
2. **How to Verify Backend is Running**:
   - Access the health endpoint: `http://localhost:8000/api/health`
   - Expected JSON response: `{"status": "ok", "app": "ONGC IntelliAssist"}`

### Step 4: Frontend Setup & Run
1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. **Package Installation**:
   ```bash
   npm install
   ```
3. **Frontend Run Command**:
   ```bash
   npm run dev
   ```
4. **How to Verify Frontend is Running**:
   - Open your browser and navigate to `http://localhost:5173`.
   - The login page should load. You can log in using the bootstrapped administrator credentials (e.g. `admin@ongc.com` / `Admin@12345`).

### Step 5: Populate and Query the Knowledge Base
1. **How to Upload Knowledge Base PDFs**:
   - Log in as the administrator.
   - Navigate to the **Knowledge Base** management tab.
   - Drag & drop or browse to select your annual reports (e.g., `annualreport22-23rev.pdf`, `ar2023-24.pdf`, `ar2024-25.pdf`).
   - The backend will automatically extract text, generate chunks, compute embeddings, and index them in the FAISS vector database.
2. **How to Ask Questions**:
   - Type your query into the main chat window.
   - For multi-year comparison queries (e.g., *"What is the profit in the last three years?"*), the backend automatically isolates, queries, and pulls chunks from each registered annual report individually, generating a consolidated markdown table and trend analysis.

### Troubleshooting
- **WinError 10013 (Port Conflict)**: The `start_server.py` script automatically detects stale uvicorn processes on port 8000, terminates them, and falls back to port 8001/8002 if the port remains blocked.
- **Index Missing at Startup**: The backend automatically recovers and rebuilds the FAISS vector store at startup if SQLite contains chunks but the vector files are missing on disk.
- **High Latency / Connection Refused on Ollama**: The RAG pipeline automatically prioritizes Groq API if the `GROQ_API_KEY` is configured (responses in ~2 seconds), falling back to local Ollama only if Groq is unavailable.

