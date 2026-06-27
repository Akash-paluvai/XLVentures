# Intelligent Next Best Action Platform

A reusable, agentic decision-intelligence platform that transforms customer interactions and enterprise knowledge into explainable, confidence-scored next best action recommendations — with human-in-the-loop approval and continuous learning from feedback.

Built for the XLVentures.AI Hackathon.

---

## Why this is a platform, not a chatbot

Most "next best action" demos are a single RAG call wearing a trench coat. This system is built around a **dynamic planner** that decides, per interaction, which specialized agents to invoke and in what order — and a **plug-and-play agent/tool registry** so new capabilities can be added via config, with no code changes. Every recommendation carries a structured evidence graph and a computed (not asserted) confidence score, and every human decision is written back into memory to improve future recommendations.

---

## Architecture overview

The platform is organized as a 12-stage pipeline, wrapped by cross-cutting registries and observability layers.

```
 1.  Customer interaction   → multi-source ingestion (notes, email, CRM, transcripts, chat)
 2.  Planner agent          → intent understanding, task decomposition, agent selection, plan + reasoning
 3.  Execution engine        → orchestrates agents/tools: parallel execution, retries, fallbacks, result aggregation
 4.  Parallel agents         → 4A episodic recall · 4B context retrieval (RAG) · 4C conflict detection
 5.  Risk & opportunity synthesis → risk analysis, opportunity detection, gap identification, signal extraction
 6.  Candidate generation    → multiple ranked next-best-action candidates
 7.  Arbiter agent           → scores and ranks candidates on business value, feasibility, confidence
 8.  Reflection & confidence check → validates evidence sufficiency; triggers a replan loop if insufficient
 9.  Explanation agent       → evidence graph, reasoning trace, source links, confidence score
10.  Human review & approval → approve / edit / request more info / reject, with feedback captured
11.  Memory writeback        → interaction memory, outcome memory, decision history, preference learning
12.  Workflow templates      → reusable, domain-agnostic workflows (Sales, Customer Success, HR, IT Support, Energy/Ops, ...)
```

### Cross-cutting layers

| Layer | Purpose |
|---|---|
| **Config & rule engine** | Business rules, personas/ICP, workflows, guardrails, model routing — all without code changes |
| **Agent registry** | Plug-and-play specialized agents (CRM, Email, Meeting, Knowledge, Search, Risk, Opportunity, Contract, ...) |
| **Tool registry** | Reusable tools shared across agents (vector search, SQL, web search, email/send, Slack, file system, code executor, ...) |
| **Observability & monitoring** | Agent tracing (execution graph), latency/performance, success/failure rates, token cost, cache hit rates, model usage, alerts, dashboards |
| **Cost & model optimization** | Cost-aware routing between cheap and powerful models per task complexity, with a cost estimator and budget guardrails |
| **Audit trail & replay** | Full transparency log of planner decisions, agent outputs, tool calls, results, and human feedback — with execution replay |

### Replan loop

If the reflection step determines evidence is insufficient, the system requests more information or invokes additional agents rather than forcing a low-confidence recommendation through. This loop is what separates "the model answered" from "the system knows it doesn't know yet."

### Learning loop

Every approval, edit, or rejection at the human review stage is captured and written back into interaction memory, outcome memory, decision history, and preference learning — closing the loop so the platform's recommendations improve over time rather than staying static.

---

## Key differentiators

- **Dynamic planning, not a fixed graph** — the planner agent constructs the execution path per interaction based on intent, not a hardcoded sequence.
- **Multi-tier memory** — episodic (past cases), semantic (org knowledge/RAG), and a learning loop that feeds outcomes back into future decisions.
- **Computed confidence, not asserted confidence** — confidence scores derive from evidence sufficiency, source agreement, and historical outcomes, surfaced via reflection and an explanation agent.
- **Conflict detection** — a dedicated agent flags contradictions across sources (e.g., CRM stage vs. meeting notes) before a recommendation is made.
- **Ranked alternatives, not a single guess** — candidate generation produces multiple options; the arbiter agent justifies the winner against the field.
- **True extensibility** — new agents, tools, and workflow templates are added through the registries and config layer, with no code changes required.
- **Full auditability** — every planner decision, agent output, tool call, and human action is logged and replayable.

---

## Tech stack

> _Fill in as decisions are finalized._

| Component | Choice |
|---|---|
| Orchestration | LangGraph |
| LLM(s) | |
| Vector store | |
| Memory / state store | |
| Backend | |
| Frontend | |
| Observability | |

---

## Repository structure

```
.
├── agents/              # Planner, episodic recall, context retrieval, conflict detection,
│                         # risk/opportunity synthesis, candidate generation, arbiter, explanation
├── tools/                # Reusable tool implementations (CRM, vector search, web search, etc.)
├── registry/             # Agent registry + tool registry configs (plug-and-play)
├── config/                # Business rules, personas/ICP, workflow templates, guardrails
├── memory/                 # Episodic, semantic, decision history, preference learning stores
├── workflows/               # Domain workflow templates (Sales, CS, HR, IT Support, Energy/Ops)
├── observability/             # Tracing, dashboards, cost/budget monitoring
├── ui/                          # Human review & approval interface
├── data/                         # Synthetic CRM records, transcripts, playbooks for the demo
├── docs/                          # Architecture diagrams and design notes
└── README.md
```

---

## Getting started

> _Fill in once the implementation is in progress._

```bash
git clone <repo-url>
cd <repo-name>

# install dependencies

# configure environment variables (API keys, model routing, etc.)

# run the platform
```

---

## Demo business use case

> _Describe the chosen B2B domain, customer journey, decision points, and success metrics here._

---

## Evaluation alignment

| Criteria | Weight | Where it shows up |
|---|---|---|
| Agentic AI architecture quality | 70% (platform) | Dynamic planner, execution engine, agent/tool registries |
| Reusability & extensibility | | Plug-and-play registries, config-driven workflow templates |
| Memory & orchestration design | | Episodic + semantic memory, reflection/replan loop, writeback |
| User experience | | Human review & approval interface |
| Business use case understanding & outcomes | 30% (business) | Domain definition, recommendation quality, measurable metrics |