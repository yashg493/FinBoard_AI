# FinBoard_AI 🏛

**Autonomous Multi-Agent Financial Governance System**

> Brings billionaire-grade family office intelligence to retail users via real-time multi-agent AI debate.

---

## Architecture

```
Sentinel Agent (macro monitor)
    ↓
ParallelAgent(InvestmentAgent, RiskAgent, TaxAgent)   ← asyncio.gather()
    ↓
Debate Loop (conflict detection)
    ↓
OrchestratorAgent (consensus + governance decision)
    ↓
WebSocket stream → Live Boardroom UI
    ↓
MongoDB Atlas (persistent memory)
```

---

## Quick Start

### Option A — Docker Compose (recommended)

```bash
git clone <repo>
cd boardroom-ai

# 1. Copy env file and fill in your keys
cp .env.example .env

# 2. Add GCP service account key
mkdir credentials
cp ~/Downloads/gcp-key.json credentials/gcp-key.json

# 3. Start everything
docker compose up --build

# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
# Arize:    http://localhost:6006
```

### Option B — Local dev

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env  # fill in values
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev   # http://localhost:3000
```

---

## Required Credentials

| Service          | Where to get                              | Used for                  |
|------------------|-------------------------------------------|---------------------------|
| Vertex AI (GCP)  | console.cloud.google.com → IAM            | Gemini 1.5 Pro inference  |
| MongoDB Atlas    | mongodb.com/atlas (free M0 cluster)       | Persistent agent memory   |
| Firebase         | console.firebase.google.com               | User authentication       |
| Arize Phoenix    | app.arize.com (optional)                  | Agent observability        |

---

## Project Structure

```
finBoard-ai/
├── backend/
│   ├── main.py                    # FastAPI + WebSocket server
│   ├── agents/
│   │   ├── base_agent.py          # Vertex AI Gemini base class
│   │   ├── sentinel.py            # Macro monitor
│   │   ├── investment_agent.py    # Portfolio optimizer
│   │   ├── risk_agent.py          # Risk & emergency analysis
│   │   ├── tax_agent.py           # Tax efficiency (India)
│   │   └── orchestrator.py        # Board chair, consensus engine
│   ├── memory/
│   │   └── mongodb.py             # Async MongoDB via motor
│   ├── routers/
│   │   ├── portfolio.py           # User profile endpoints
│   │   ├── simulation.py          # HTTP simulation endpoint
│   │   └── history.py             # Meeting history endpoints
│   └── utils/
│       ├── connection_manager.py  # WebSocket session manager
│       └── observability.py       # Arize Phoenix tracing
├── frontend/
│   ├── pages/
│   │   ├── boardroom.tsx          # Main board UI
│   │   └── index.tsx              # Redirect to /boardroom
│   └── components/
│       ├── BoardEvent.tsx         # Live agent message renderer
│       ├── AgentCard.tsx          # Sidebar agent status
│       ├── ConsensusPanel.tsx     # Right panel: verdict + actions
│       ├── MacroDashboard.tsx     # Macro indicator snapshot
│       ├── SimulationPanel.tsx    # Scenario runner
│       └── HistoryPanel.tsx       # Past meeting history
├── docker-compose.yml
└── .env.example
```

---

## Governance Modes

| Mode       | Description                                              |
|------------|----------------------------------------------------------|
| ADVISORY   | Agents recommend; user decides                           |
| COPILOT    | Agents recommend and pre-fill actions; user confirms     |
| AUTONOMOUS | Agents execute decisions automatically (future feature)  |

---

## Adding a New Agent

1. Create `backend/agents/your_agent.py` extending `BaseAgent`
2. Override `build_prompt()` and `parse_output()`
3. Add it to `OrchestratorAgent.__init__()` and the `run_board_meeting()` parallel block
4. Add a card to `AGENTS` array in `pages/boardroom.tsx`

---

## Deploy to GCP Cloud Run

```bash
# Build and push backend image
gcloud builds submit backend/ --tag gcr.io/PROJECT_ID/boardroom-ai-backend

# Deploy to Cloud Run
gcloud run deploy boardroom-ai-backend \
  --image gcr.io/PROJECT_ID/boardroom-ai-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars MONGODB_URI=... \
  --allow-unauthenticated

# Deploy frontend to Vercel
cd frontend && vercel --prod
```
