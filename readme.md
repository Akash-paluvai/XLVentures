# Intelligent Next Best Action Platform

A reusable, configuration-driven **Decision Intelligence Platform** that turns customer interactions and enterprise knowledge into explainable, confidence-scored next best action recommendations — with human-in-the-loop approval and continuous learning from feedback.

Built for the XLVentures.AI Hackathon.

---

## Current Status

| Shift | Description | Status |
|---|---|---|
| **Shift 1** | Project Scaffolding & Data Contracts | ✅ Complete |
| **Shift 2** | Memory Layer & Tool Registry | ✅ Complete |
| **Shift 3** | Context Agent | ✅ Complete |
| Shift 4 | Reasoning Agent + Recommendation Agent | ⬜ Pending |
| Shift 5 | Explanation Agent + Learning Agent | ⬜ Pending |
| Shift 6 | Planner Agent + LangGraph Wiring | ⬜ Pending |
| Shift 7 | React UI: Recommendation View + HITL | ⬜ Pending |
| Shift 8 | Configuration Hub UI + Domain Pack Switch | ⬜ Pending |
| Shift 9 | Polish, Reflection, Demo Prep | ⬜ Pending |

See [PROGRESS.md](PROGRESS.md) for detailed change log.

---

## Core idea

This is a **platform**, not an autonomous AI employee and not a chatbot. The pipeline is intentionally simple:

```
Input data → Understand context → Reason about the business situation →
Generate options → Recommend next action → Explain why → Human approval → Learn
```

The differentiator isn't agent count — the brief asks for a planner that *dynamically orchestrates specialized agents*, not a fixed roster of twenty. We deliberately use **five** specialized agents behind a dynamic planner, and prove extensibility by running the same platform across **two domain packs** (no code changes) rather than by stacking more agents.

---

## Architecture

```
                       Frontend
                          │
                          ▼
                 Configuration Hub
   (Domain Packs · Business Rules · Workflow Templates ·
    Personas · Policies · KPIs)
                          │
                          ▼
                   Planner Agent
                          │
                          ▼
                  Execution Engine
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
  Agent Registry     Tool Registry      Memory Layer
        │
        ▼
┌───────────┬────────────┬────────────────┬─────────────┬────────────┐
│  Context  │ Reasoning  │ Recommendation │ Explanation │  Learning  │
│   Agent   │   Agent    │     Agent      │    Agent    │   Agent    │
└───────────┴────────────┴────────────────┴─────────────┴────────────┘
                          │
                          ▼
                  Human Approval
                          │
                          ▼
                  Memory Writeback
```

Observability and an audit trail wrap the whole pipeline (every planner decision, agent call, and human action is traced and logged).

### The five agents

| Agent | Responsibilities | Status |
|---|---|---|
| **Context** | Ingest interactions; retrieve enterprise knowledge; gather historical context | ✅ Implemented |
| **Reasoning** | Identify risks, opportunities, and missing information; prioritize signals | ⬜ Pending |
| **Recommendation** | Generate candidate next actions; rank them | ⬜ Pending |
| **Explanation** | Produce evidence, confidence score, and reasoning trace | ⬜ Pending |
| **Learning** | Memory writeback; incorporate human feedback into future scoring | ⬜ Pending |

The planner decides at runtime which of these to invoke and in what order, based on the interaction it's classifying — that dynamic routing, not the agent count, is what's being graded under "quality of agentic AI architecture."

### Configuration Hub

Everything that changes between business domains lives here, not in code: domain packs, business rules, workflow templates, personas, policies, KPIs. Switching domains is a configuration swap, not a redeploy.

---

## Key differentiator: domain packs, not more agents

The single most convincing proof that this is a *platform* rather than a use-case demo: run the same five agents and the same planner against a second domain pack, live, with no code change.

- **Primary domain pack (fully implemented):** Customer Success — renewal risk / expansion intelligence.
- **Second domain pack (lightweight, extensibility proof only):** Staffing/Recruitment.

The two packs are structurally identical; only configuration differs:

| Customer Success | Recruitment |
|---|---|
| Customer | Candidate |
| Meeting transcript | Interview transcript |
| CRM | ATS |
| Churn risk | Candidate drop-off risk |
| Upsell opportunity | Fast-track opportunity |
| Executive meeting | Hiring manager call |
| Renewal | Hiring decision |

Both domain packs already have:
- ✅ Domain configuration JSONs
- ✅ Synthetic data records
- ✅ Playbooks seeded into ChromaDB
- ✅ Dynamic retrieval proven via Context Agent

---

## Tech stack

| Component | Choice | Status |
|---|---|---|
| Orchestration | LangGraph | ⬜ Not yet wired |
| LLMs | OpenRouter (Gemma 3 27B free tier) | ✅ Optional synthesis ready |
| Vector store | ChromaDB (local, embedded, all-MiniLM-L6-v2) | ✅ Operational |
| Memory / state store | SQLite (SQLAlchemy ORM) | ✅ Operational |
| Backend | FastAPI (Python) | ✅ Running |
| Frontend | React (Vite) | ✅ Running |
| Observability | LangSmith | ⬜ Not yet wired |

---

## Repository structure

```
.
├── backend/
│   ├── agents/                # Agent implementations
│   │   ├── context_agent.py   # ✅ Context retrieval agent
│   │   └── query_builder.py   # ✅ Query construction module
│   ├── api/
│   │   └── main.py            # ✅ FastAPI entrypoint + routes
│   ├── config/
│   │   └── domain_packs/
│   │       ├── customer_success.json   # ✅ CS domain config
│   │       └── recruitment.json        # ✅ Recruitment domain config
│   ├── core/
│   │   ├── schemas.py         # ✅ All Pydantic data contracts
│   │   ├── settings.py        # ✅ Platform settings (DB paths, etc.)
│   │   ├── state.py           # ✅ PlatformState TypedDict
│   │   └── config_loader.py   # ✅ Domain-agnostic data loader
│   ├── data/
│   │   ├── customer_success/
│   │   │   ├── accounts.json  # ✅ 5 synthetic CS accounts
│   │   │   └── playbooks/     # ✅ 5 playbook MDs
│   │   └── recruitment/
│   │       ├── candidates.json # ✅ 3 synthetic candidates
│   │       └── playbooks/      # ✅ 3 playbook MDs
│   ├── memory/
│   │   ├── episodic.py        # ✅ SQLite-backed recommendation/feedback store
│   │   ├── semantic.py        # ✅ ChromaDB vector store for playbooks
│   │   └── manager.py         # ✅ Unified MemoryManager interface
│   ├── registry/
│   │   ├── agent_registry.py  # ✅ Agent registration + bootstrap
│   │   └── tool_registry.py   # ✅ Tool registration + bootstrap
│   ├── scripts/
│   │   ├── seed_memory.py     # ✅ Domain-agnostic playbook seeder
│   │   ├── test_memory.py     # ✅ 9 memory integration tests
│   │   └── test_context_agent.py  # ✅ Context agent dynamic test
│   └── docs/
├── frontend/                  # Vite React dashboard
│   ├── src/
│   │   ├── components/        # Domain selector, account cards, etc.
│   │   ├── pages/             # Page components
│   │   ├── services/          # API service layer
│   │   └── App.jsx            # Main application
│   └── package.json
├── PROGRESS.md                # Detailed implementation log
├── readme.md                  # This file
├── todo.md                    # Shift-based build plan
└── requirements.txt
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+

### Backend Setup
```bash
# Initialize and activate virtual environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env

# Seed memory (first run downloads ~80MB embedding model)
PYTHONPATH=. python backend/scripts/seed_memory.py

# Run memory tests (optional verification)
PYTHONPATH=. python backend/scripts/test_memory.py

# Run context agent tests (optional verification)
PYTHONPATH=. python backend/scripts/test_context_agent.py

# Start the backend FastAPI server
PYTHONPATH=. uvicorn backend.api.main:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Optional | Enables LLM synthesis in Context Agent |
| `ENABLE_CONTEXT_SYNTHESIS` | Optional | Set to `true` to activate LLM synthesis (default: `false`) |
| `LANGSMITH_API_KEY` | Optional | Enables LangSmith tracing |
| `LANGCHAIN_TRACING_V2` | Optional | Set to `true` for tracing |
| `LANGCHAIN_PROJECT` | Optional | LangSmith project name |

---

## Demo business use case

**Primary domain pack: B2B SaaS Customer Success — Renewal Risk & Expansion Intelligence**

**Decision points:**
- Renewal at risk (usage drop, sentiment decline, support tickets up)
- Expansion/upsell opportunity (positive sentiment + usage near plan limits)
- Escalation needing CSM follow-up (unresolved negative support interaction)
- Champion/stakeholder change risk (key contact gone quiet or left)

**Second domain pack (lightweight extensibility proof):** Staffing/Recruitment — Screening → Offer workflow only, 3 synthetic candidate records + 3 playbooks, proving the platform is domain-agnostic.

---

## Evaluation alignment

| Criteria | Weight | Where it shows up |
|---|---|---|
| Agentic AI architecture quality | 70% (platform) | Dynamic planner, execution engine, five-agent registry |
| Reusability & extensibility | | Domain packs (two domains, no code change), config hub |
| Memory & orchestration design | | Memory layer, learning agent, writeback loop |
| User experience | | Human approval interface, observability dashboard |
| Business use case understanding & outcomes | 30% (business) | CS domain definition, recommendation quality, measurable metrics |

---

## Team

> _Names / roles here._

## License

> _TBD._