# ONGC IntelliAssist

ONGC IntelliAssist is a secure, hybrid Retrieval-Augmented Generation (RAG) assistant for ONGC and enterprise knowledge workflows.

## Main features

- JWT-authenticated, role-aware access with backend validation, protected routes, server-side logout revocation, and user-isolated state.
- Hybrid RAG routing: a user's uploaded documents, the ONGC Knowledge Base, the enterprise multi-domain knowledge base, then a general AI fallback.
- Document upload and retrieval for PDF, DOCX, and TXT files; each user's uploaded library is isolated from other users.
- ONGC and enterprise knowledge coverage including operations, exploration, HSE, HR, finance, procurement, governance, sustainability, IT, and cybersecurity.
- Chat history, citations, feedback, and per-user analytics.
- ONGC-branded React interface with responsive chat, document focus mode, and dark mode.

## Architecture

The FastAPI backend authenticates each request and persists chats, messages, feedback, audit logs, and document ownership in SQLite. The routing service classifies a question, retrieves user-owned uploaded content where applicable, searches the built-in ONGC/enterprise knowledge base, or uses Ollama as the general AI fallback. The Vite/React client validates the session with the backend before rendering protected interfaces.

## Technology stack

- Frontend: React, Vite, Tailwind CSS, React Router, Lucide
- Backend: FastAPI, SQLAlchemy, Pydantic, JWT
- Retrieval: local embeddings, document chunking, hybrid knowledge routing
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
