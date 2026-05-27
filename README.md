# AI Project Assistant

A robust backend-first AI assistant designed to manage projects using Claude (for reasoning/chat), Gemini (for vision), and a persistent dual-layer memory system.

---

##  Quick Start

Get the assistant running locally:

1. **Setup**: `python -m venv .venv` and `pip install -r requirements.txt`.
2. **Environment**: Copy `.env.example` to `.env` and add your API keys.
3. **Database**: The assistant **automatically syncs** your schema on startup using the `DATABASE_URL`.
4. **Launch**: `uvicorn app.main:app --reload --port 8000`.
*The UI is available at [http://localhost:8000](http://localhost:8000)*

---

##  Environment Variables

| Variable | Description | Required | Default |
| :--- | :--- | :---: | :--- |
| `GROQ_API_KEY` | API Key for Groq (Llama) Models | **Yes** | - |
| `GROQ_CHAT_MODEL` | Model for user-facing chat | No | `llama-3.3-70b-versatile` |
| `GROQ_AGENT_MODEL` | Model for background organizer agent | No | `llama-3.1-8b-instant` |
| `LLM_MAX_TOKENS` | Max token limit for LLM responses | No | `2048` |
| `GEMINI_API_KEY` | API Key for Gemini Vision | **Yes** | - |
| `GEMINI_MODEL` | Gemini model for image analysis | No | `gemini-2.5-flash-lite` |
| `GEMINI_MAX_TOKENS` | Max tokens for vision responses | No | `512` |
| `SUPABASE_URL` | Your Supabase Project URL | **Yes** | - |
| `SUPABASE_KEY` | Your **Service Role Key** (Not Anon) | **Yes** | - |
| `DATABASE_URL` | Postgres URI for **Automated Migrations** | **Yes** | - |
| `MOCK_AI` | Short-circuit AI calls for UI testing | No | `false` |
| `IMAGE_PROVIDER` | Generation service (`mock`, `stability`) | No | `mock` |

---

## Key Features

- **Brain Tiering**: Uses **Llama 3.3 70B** (via Groq) for high-quality user chat and **Llama 3.1 8B** for cost-efficient background organization.
- **Agentic Tool Loop**: The LLM can autonomously generate images, search project briefs, and update project memory in a single chat turn via Groq's OpenAI-compatible function-calling API.
- **Persistence**: Full PostgreSQL history (Supabase) for projects, conversations, and agent runs.
- **Project Memory**: Scopes knowledge storage that persists across sessions, stored both in the database (for indexing) and as structured JSON files (for model context).
- **Background Organizer**: A dedicated sub-agent that periodically summarizes project data into structured durable memory.

---

##  Frontend UI

The application features a modern, **glassmorphic SPA** designed for a "Chat-First" workflow.

- **2-Column Layout**: Projects Sidebar on the left, high-velocity Chat Console on the right.
- **Inline Vision**: Upload images with optional custom prompts directly into the chat flow for instant Gemini-powered analysis (works in both project and general chat modes).
- **Visual Feedback**: AI-generated images are rendered directly in the conversation history.

---

## 📂 Project Structure

A clean, layered architecture designed for maintainability and scalability:

```text
.
├── app/
│   ├── agents/       # Specialist sub-agents (e.g. Organizer)
│   ├── ai/           # Direct LLM clients (Groq/Llama, Gemini Vision)
│   ├── db/           # Connection logic & Automated Migrator
│   ├── repositories/ # Data access layer (PostgreSQL / Supabase)
│   ├── routers/      # API endpoints (FastAPI)
│   ├── schemas/      # Pydantic data models
│   └── services/     # Business logic layer (Storage, Analysis)
├── sql/              # Automated schema migrations
├── static/           # Glassmorphic Chat-First UI
├── tests/            # Backend unit & integration tests
└── .env              # Global environment configuration
```

---

## Schema Design Decisions

The database is designed with high normalization to ensure data integrity and ease of indexing.

### 1. Projects & Briefs (`sql/001-002`)
- **Projects**: The root entity.
- **Briefs**: Instead of a single Markdown blob, the brief is broken into distinct fields (`goals`, `constraints`, `target_audience`, etc.). This allows the AI to perform "surgical" updates to specific project aspects rather than rewriting the entire document.

### 2. Conversations & Messages (`sql/003-004`)
- Supports infinite history per project.
- **Tool Interactions**: Stores `tool_use` and `tool_result` roles as first-class message types, allowing the AI to "remember" its own actions across page reloads.

### 3. Memory Entries (`sql/006`)
- Categorized into `context`, `decision`, `entity`, and `constraint`.
- This categorization helps the AI filter information (e.g., "Tell me all technical decisions made so far").

### 4. Agent Runs (`sql/007`)
- Implements a state-machine pattern (`pending` → `running` → `completed`/`failed`).
- Stores the final `output` (entry counts) or `error` messages for easy debugging.

---

## The Agent System

### Chat Orchestrator
The `ChatOrchestrator` manages the interaction loop. When a user sends a message:
1. It loads all relevant project memory.
2. It injects memory into a system prompt.
3. It enters a loop (max 8 rounds) where the LLM (Llama 70B via Groq) can call tools, see results, and refine its answer.

### Background Organizer Agent
The **Organizer Agent** is a "single-pass" specialist. 
- **Trigger**: `POST /projects/{id}/agent-runs`
- **Action**: It reads the project brief and the last 100 messages, then extracts "durable knowledge" into structured JSON files.
- **Outcome**: This prevents the project memory from becoming "stale" or cluttered with conversational noise.

---

## 📡 API Endpoints (Core)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| **GET** | `/projects` | List all active projects. |
| **POST** | `/projects/{id}/chat` | Main AI interaction loop. |
| **POST** | `/projects/{id}/images/upload` | Upload an image for processing. |
| **POST** | `/projects/{id}/images/{image_id}/analyze` | Analyze a project image with optional prompt. |
| **POST** | `/projects/{id}/agent-runs` | Trigger the Background Organizer. |
| **POST** | `/general-chat` | General assistant chat (Llama 70B). |
| **POST** | `/general-chat/analyze-image` | Stateless image analysis for general chat. |

---

## 📬 Sample API Interaction

### 1. Create a Project
`POST /projects`
```json
{
  "name": "Smart City App",
  "description": "An IoT dashboard for urban monitoring."
}
```
**Response**: `201 Created`
```json
{
  "id": "62d11c8e-a8a8-4ae5-a28f-435f0da52b85",
  "name": "Smart City App",
  "created_at": "2026-04-02T15:45:00Z"
}
```

### 2. Chat with AI (Vision + Tools)
`POST /projects/{id}/chat`
```json
{ "message": "Analyze my uploaded image and brainstorm three design iterations." }
```
**Response**: `200 OK`
```json
{
  "text": "Based on the wireframe you uploaded, I suggest...",
  "images": [
    {
      "url": "https://.../project-images/wireframe.jpg",
      "analysis": "A high-fidelity wireframe showing a dashboard with line charts..."
    }
  ],
  "tool_calls": ["analyze_image", "brainstorm_logic"]
}
```

---

##  Testing
Run backend validation via Pytest:
```bash
pytest tests/ -v
```

---

## 🧠 Assumptions & Tradeoffs
- **Automated Schema Sync**: On every startup, the app executes all `sql/` files. This ensures your project structure is always "self-healing."
- **Security-First Storage**: The system uses a **Private Bucket** for images. Access is restricted to the backend via the **Service Role Key**.
- **No-Auth Pattern**: Designed as a project-internal tool; assumes auth is handled by a reverse proxy.

---

## 🛠️ Limitations & Future Improvements

While this version is a fully functional AI assistant, the following features would be added for a production-ready rollout:

- **Identity & Access Management (IAM)**: Full user authentication (OAuth2/Supabase Auth) with per-user project scoping.
- **Background Task Queues**: Moving long-running Agent Runs and image generation to a worker (e.g., Celery or Redis) to free up the API workers.
- **Advanced Retries**: Implementing exponential backoff for LLM API calls to handle rate limits and transient failures gracefully.
- **Enhanced Observability**: Integrating structured logging (ELK) and tracing (OpenTelemetry) to monitor complex multi-agent reasoning loops.
- **Cypress/Playwright Tests**: Adding end-to-end browser tests to automate UI validation across all features.

---

## 💰 Cost Optimizations
- **Model Tiering**: Claude 3.5 Sonnet for reasoning, Haiku for organization.
- **Prompt Caching**: Uses `cache_control` on large context blocks to reduce repetitive costs.
- **Gemini Flash**: Efficient vision processing at scale.
- **Mock Mode**: Prevents cost spikes during frontend development.

---

## Technology Stack
- **Backend Framework**: FastAPI (Python 3.12+)
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, CSS3 (Glassmorphism)
- **Database**: Supabase (PostgreSQL)
- **AI Models**: Anthropic Claude & Google Gemini Flash
- **Memory**: Local File System + Database (Dual-Writer)
