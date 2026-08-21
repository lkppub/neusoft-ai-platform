**English** | [中文](README.md)

# Neusoft Smart Business AI Assistant Platform

A Python-based AI application development training project — an enterprise-grade AI assistant platform.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Vue3 + Vite + Pinia + Vue Router + Axios + Element Plus + ECharts |
| Backend | FastAPI + SQLAlchemy (async) + Pydantic v2 |
| Database | SQLite (development) / PostgreSQL (production) |
| Cache | Redis |
| AI Engine | DeepSeek API (recommended) / OpenAI-compatible interface |
| AI Framework | LangChain + LangGraph |
| Vector Database | Chroma (embedded) |
| Low-Code | Dify (optional) |
| Deployment | Docker Compose |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (optional, for containerized deployment)

### 1. Clone and Configure the Environment

```bash
# Copy the environment variable file (pre-configured, ready to use)
cp .env.example .env

# Edit .env and fill in your DeepSeek API Key (optional, Mock mode by default)
# AI_PROVIDER=mock  -> Uses a mock AI, no API Key required
# AI_PROVIDER=deepseek -> Uses the real DeepSeek API
```

### 2. Start the Backend

```bash
cd backend

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize the database and create seed data
python -m app.seed

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000/docs to view the Swagger API documentation.

### 3. Start the Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

Visit http://localhost:5173 to open the frontend interface.

### 4. One-Click Deployment with Docker Compose

```bash
docker compose up -d
```

Once the services are running, visit http://localhost.

## Demo Accounts

| Username | Password | Role | Description |
|----------|----------|------|-------------|
| `admin` | `123456` | Administrator | System & user management, AI configuration, viewing reports |
| `cs_staff` | `123456` | Customer Service | Ticket management, AI-assisted replies, FAQ maintenance |
| `enterprise` | `123456` | Enterprise User | AI chat, knowledge base Q&A, submitting tickets |
| `decision` | `123456` | Decision Maker | Data dashboard, statistical analysis |

## Feature Modules

### Enterprise User Side
- 🤖 **AI Intelligent Chat Assistant**: Multi-turn conversation, SSE streaming output, context memory, Markdown rendering
- 📚 **Knowledge Base Q&A**: RAG retrieval-augmented generation, document upload, Chroma vector storage, source citation
- 🎤 **Voice Interaction**: Speech-to-text, text-to-speech

### Customer Service Side
- 📋 **Intelligent Ticket Management**: AI auto-categorization, AI reply suggestions, ticket status tracking
- 📝 **FAQ Management**: Frequently asked questions maintenance, category management
- 📄 **Reply Templates**: Template creation, variable substitution, one-click usage

### Administrator Side
- 👥 **User Management**: User CRUD, role assignment, permission control
- 📁 **Knowledge Base Management**: Document upload, chunking configuration, index management
- ⚙️ **AI Configuration Management**: Model selection, prompt template editing, parameter tuning
- 📊 **Conversation Record Viewer**: Browse and stat all conversation records
- 📈 **Intelligent Analysis Report**: AI-generated operations analysis report

### Decision Maker Side (Data Dashboard)
- 📊 **KPI Overview Cards**: Consultation volume, ticket volume, resolution rate, satisfaction
- 🥧 **Category Distribution Pie Chart**: Issue type distribution
- 📈 **Trend Line Chart**: Satisfaction and consultation volume trends
- 💡 **AI Insight Cards**: AI auto-detects key trends
- 🔥 **Hot Topics**: High-frequency FAQ keywords

## AI Architecture

```
User Input → FastAPI → LangGraph Multi-Agent Collaboration
                     ├── Classifier Agent (intent recognition)
                     ├── Query Agent (knowledge base retrieval)
                     ├── Reply Agent (response generation)
                     └── Quality Check Agent (quality review)

RAG Pipeline: Document Upload → Text Splitting → Vector Embedding → Chroma Storage → Similarity Retrieval → AI Response Generation
```

## Project Structure

```
├── backend/           # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── core/              # Configuration, security, database
│   │   ├── models/            # SQLAlchemy data models
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── api/v1/            # REST API routes
│   │   ├── services/          # Business logic layer
│   │   │   ├── ai/            # AI Provider (DeepSeek/Mock)
│   │   │   ├── knowledge/     # RAG, vector store, document processing
│   │   │   ├── voice/         # Speech services
│   │   │   └── analytics/     # Statistical analysis
│   │   └── agents/            # LangGraph multi-agent
│   └── requirements.txt
├── frontend/          # Vue3 frontend
│   └── src/
│       ├── api/               # Axios API modules
│       ├── stores/            # Pinia state management
│       ├── router/            # Vue Router routes
│       ├── composables/       # Reusable composables
│       ├── layouts/           # Layout components
│       ├── views/             # Page views
│       └── components/        # UI components
├── docker/            # Docker configuration files
│   └── nginx/nginx.conf
├── docker-compose.yml # Docker Compose orchestration
└── .env               # Environment variables
```

## API Endpoint Overview

All APIs are under `/api/v1/`:

- **Auth**: `/auth` — register, login, token refresh, profile
- **Conversations**: `/conversations` — CRUD + SSE streaming messages
- **Knowledge Base**: `/knowledge` — document upload, RAG query, FAQ management
- **Tickets**: `/tickets` — ticket management, AI categorization, AI reply suggestions
- **Templates**: `/templates` — reply template CRUD
- **Admin**: `/admin` — user management, AI configuration, prompts, reports
- **Dashboard**: `/dashboard` — KPI overview, trend charts, insights
- **Voice**: `/voice` — speech recognition, speech synthesis
- **Agent**: `/agent` — single-agent chat, multi-agent analysis
- **Dify**: `/dify` — low-code AI platform integration (optional)

## Switching AI Modes

Modify in `.env`:

```env
# Mock mode (no API Key required, returns mock replies)
AI_PROVIDER=mock

# DeepSeek mode (API Key required)
AI_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-actual-key
```

## License

This training project is for educational purposes only.
