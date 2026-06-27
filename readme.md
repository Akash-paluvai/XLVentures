# Intelligent Next Best Action Platform

A reusable, configuration-driven **Decision Intelligence Platform** that turns customer interactions and enterprise knowledge into explainable, confidence-scored next best action recommendations — with human-in-the-loop approval and continuous learning from feedback.

Built for the XLVentures.AI Hackathon.

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

| Agent | Responsibilities |
|---|---|
| **Context** | Ingest interactions (notes, email, CRM, transcripts); retrieve enterprise knowledge; gather historical context |
| **Reasoning** | Identify risks, opportunities, and missing information; prioritize signals |
| **Recommendation** | Generate candidate next actions; rank them |
| **Explanation** | Produce evidence, confidence score, and reasoning trace |
| **Learning** | Memory writeback; incorporate human feedback into future scoring |

The planner decides at runtime which of these to invoke and in what order, based on the interaction it's classifying — that dynamic routing, not the agent count, is what's being graded under "quality of agentic AI architecture."

### Configuration Hub

Everything that changes between business domains lives here, not in code: domain packs, business rules, workflow templates, personas, policies, KPIs. Switching domains is a configuration swap, not a redeploy.

---

## Key differentiator: domain packs, not more agents

The single most convincing proof that this is a *platform* rather than a use-case demo: run the same five agents and the same planner against a second domain pack, live, with no code change. A single-domain demo reads as "they built a Customer Success app." Two domains on the same platform reads as "they built a platform" — that distinction is the whole point of this section.

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

**Sample outputs, same architecture:**

```
Customer Success → Risk: renewal probability low. Next action: schedule executive call. Confidence: 91%.
Recruitment      → Risk: candidate may decline offer. Next action: fast-track offer + schedule hiring manager call. Confidence: 88%.
```

The Recruitment pack is intentionally minimal: config + 2-3 sample records + one workflow (Screening → Offer) + one clean end-to-end recommendation. It exists to prove extensibility, not to be judged on business depth — that's what the Customer Success pack is for.

If this swap works cleanly live in the demo, it's a stronger signal of "real platform" than any number of additional agents would be.

---

## Rubric alignment

| Requirement | How it's satisfied |
|---|---|
| Dynamic planner orchestration | Planner Agent + Execution Engine, runtime agent selection |
| Reusable agents and tools | Agent Registry + Tool Registry |
| Shared memory | Memory Layer (semantic + episodic) |
| Multi-source retrieval | Context Agent |
| Explainable recommendations | Explanation Agent (evidence + confidence + reasoning trace) |
| Configurable workflows | Configuration Hub |
| Extensible framework | Domain Packs + Registries — proven via the two-domain-pack demo |
| Human-in-the-loop | Human Approval stage |
| Learning from interactions | Learning Agent + Memory Writeback |

---

## Tech stack

| Component | Choice |
|---|---|
| Orchestration | LangGraph |
| LLMs | Claude (Sonnet for reasoning/recommendation/explanation, Haiku for classification/routing — cost-aware routing) |
| Vector store | ChromaDB (local, embedded) |
| Memory / state store | SQLite (episodic memory, decision history) |
| Backend | FastAPI (Python end-to-end) |
| Frontend | Streamlit |
| Observability | LangSmith |

---

## Repository structure

```
.
├── agents/              # context, reasoning, recommendation, explanation, learning
├── tools/                # reusable tool implementations (CRM, vector search, web search, etc.)
├── registry/             # agent registry + tool registry configs (plug-and-play)
├── config/                 # domain packs, business rules, workflow templates, personas, policies, KPIs
├── memory/                  # semantic, episodic, decision history stores
├── ui/                        # frontend (Streamlit): config hub, recommendation view, approval, dashboard
├── data/                        # synthetic CRM records, transcripts, playbooks for each domain pack
├── docs/                          # architecture diagrams and design notes
└── README.md
```

---

## Getting started

```bash
git clone <repo-url>
cd <repo-name>

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# configure environment variables: ANTHROPIC_API_KEY, LANGSMITH_API_KEY, etc.
cp .env.example .env

# run the platform
streamlit run app.py
```

---

## Demo business use case

**Primary domain pack: B2B SaaS Customer Success — Renewal Risk & Expansion Intelligence**

**Decision points:**
- Renewal at risk (usage drop, sentiment decline, support tickets up)
- Expansion/upsell opportunity (positive sentiment + usage near plan limits)
- Escalation needing CSM follow-up (unresolved negative support interaction)
- Champion/stakeholder change risk (key contact gone quiet or left)

**Success metrics:**
- Recommendation acceptance rate (approve / edit / reject ratio)
- Risk-catch lead time (days before renewal flagged vs. human baseline)
- Simulated NRR impact (accepted upsell recs × assumed expansion value)

**Second domain pack (lightweight extensibility proof):** Staffing/Recruitment — Screening → Offer workflow only, 2-3 synthetic candidate/job records, not built to the same depth as Customer Success. See "Key differentiator" section above for the entity mapping.

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