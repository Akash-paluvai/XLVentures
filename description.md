# description.md — project context for coding agents

This file is the single source of truth for what this project is and how it's built. Read this before writing code. If something here conflicts with code you find, the code is probably stale — flag it, don't silently follow it.

---

## 1. What this is

A reusable **Agentic Decision Intelligence Platform** for B2B businesses. It ingests customer interactions (notes, emails, CRM updates, transcripts, chat), combines them with enterprise knowledge (playbooks, docs, history), and produces explainable, confidence-scored **next best action** recommendations for a human to approve. It is a platform (pluggable agents/tools/workflows), not a single fixed chatbot pipeline.

Built for a hackathon evaluated 70% on platform/architecture quality, 30% on business use case quality. Optimize accordingly: the orchestration, memory, and extensibility mechanisms must be *visibly* real, not hardcoded to look agentic.

**Business domain:** B2B SaaS Customer Success — Renewal Risk & Expansion Intelligence.
Chosen because judges already understand SaaS CS without explanation (demo time goes to the agentic reasoning, not domain teaching), and LLM-generated synthetic CRM/transcript data is most believable in this domain.

**Decision points** (exactly these four — enough variety without diluting build time):
1. **Renewal at risk** — usage drop, sentiment decline in notes, support tickets up
2. **Expansion/upsell opportunity** — positive sentiment + usage near plan limits
3. **Escalation needing CSM follow-up** — negative support interaction left unresolved
4. **Champion/stakeholder change risk** — key contact gone quiet or left; only catchable by cross-referencing CRM + email metadata — good showcase for conflict/gap detection (stage 4C)

**Success metrics** (all computable from our own synthetic data — build a small dashboard for these):
- Recommendation acceptance rate (approve / edit / reject ratio across the replayed interaction set)
- Risk-catch lead time (days before renewal date the system flagged risk vs. when a human would likely notice)
- Simulated NRR impact (accepted upsell recommendations × assumed average expansion value)

---

## 2. Non-negotiable design principles

1. **The planner must actually be dynamic.** Don't hardcode a linear sequence and call it agentic. The planner agent classifies the input and decides at runtime which agents to invoke and in what order. Two different inputs should be able to take two different paths — this must be demonstrable, not just claimed.
2. **Confidence is computed, never asserted by the LLM.** Confidence scores come from evidence count, source agreement/conflict, and historical acceptance rate from episodic memory — not "the model said 85%."
3. **Extensibility means config, not code.** New agents/tools are added via a registry entry (schema below), not by editing orchestration code.
4. **Every recommendation must be explainable.** Structured evidence graph (source, recency, reliability) + reasoning trace, not a paragraph of prose justification.
5. **Human-in-the-loop is a real gate.** No recommendation is "executed" without passing through approve/edit/request-info/reject. All four outcomes are first-class, not just approve/reject.
6. **Everything writes back to memory.** Approvals, edits, and rejections feed episodic memory and influence future scoring. If a feature doesn't close this loop, it's incomplete.

---

## 3. Pipeline (12 stages — see `/docs` for the diagram)

```
1.  Ingestion        — multi-source: notes, email, CRM, transcripts, chat
2.  Planner agent     — classify intent → decompose tasks → select agents → emit plan
3.  Execution engine   — orchestrates agents/tools: parallel exec, retries, fallback, aggregation
4.  Parallel agents:
    4A. Episodic recall      — similar past situations from episodic memory
    4B. Context retrieval     — RAG over org knowledge (semantic memory)
    4C. Conflict detection     — flags contradictions across sources
5.  Risk & opportunity synthesis — combines 4A-4C into risks/opportunities/gaps/signals
6.  Candidate generation     — fan-out: generate N (e.g. 3) ranked candidate actions
7.  Arbiter agent              — scores candidates (business value, feasibility, confidence), picks winner
8.  Reflection & confidence check — if evidence insufficient → REPLAN (loop back to step 3/4, don't force a low-confidence answer)
9.  Explanation agent            — evidence graph + reasoning trace + source links + confidence score
10. Human review                  — approve / edit / request more info / reject
11. Memory writeback                — interaction memory, outcome memory, decision history, preference learning
12. Workflow templates                — the above is parameterized per domain (Sales, CS, HR, IT, Energy/Ops, ...)
```

**Cross-cutting (apply to every stage, not separate features):**
- **Config & rule engine** — business rules, personas/ICP, workflows, guardrails, model routing. No-code changes for config updates.
- **Agent registry** — plug-and-play agent specs (schema below).
- **Tool registry** — reusable tools shared across agents (vector search, SQL, web search, email/send, Slack, file system, code exec, ...).
- **Observability** — trace every planner decision and agent call (execution graph), latency, success/failure, token cost, cache hits, model routing decisions.
- **Cost/model routing** — cheap model (e.g. gpt-4o-mini) for simple classification/retrieval tasks, powerful model (e.g. Claude/GPT-5-class) for synthesis/arbitration/explanation. Route by task complexity, not uniformly.
- **Audit trail & replay** — log planner decisions, agent outputs, tool calls, results, human feedback. Must support replaying a past execution.

---

## 4. Core data contracts

Keep these shapes stable — most agents read/write them. Update this section if you change them.

```ts
AgentSpec {
  name: string
  description: string          // used by planner for routing decisions
  trigger_condition: string     // when planner should consider this agent
  tools: string[]                // tool names from Tool Registry
  prompt_template: string
  input_schema: object
  output_schema: object
}

Recommendation {
  id: string
  candidate_actions: CandidateAction[]   // ranked, not just one
  chosen_action_id: string
  confidence: ComputedConfidence
  evidence_graph: EvidenceNode[]
  reasoning_trace: string[]
  status: "pending" | "approved" | "edited" | "rejected" | "needs_info"
}

CandidateAction {
  id: string
  description: string
  business_value_score: number
  feasibility_score: number
  rejected_reason?: string      // why the arbiter didn't pick this one — must be filled if not chosen
}

ComputedConfidence {
  score: number                  // 0-1, computed not LLM-asserted
  evidence_count: number
  source_agreement: number        // 0-1
  historical_acceptance_rate: number  // from episodic memory of similar past recs
}

EvidenceNode {
  source: string
  excerpt: string
  recency: string
  reliability_score: number
}

MemoryWrite {
  interaction_id: string
  recommendation_id: string
  human_decision: "approved" | "edited" | "rejected" | "needs_info"
  feedback_text?: string
  timestamp: string
}
```

---

## 5. Memory model (3 tiers — don't collapse into one vector store)

| Tier | Contains | Used by |
|---|---|---|
| **Semantic memory** | Org docs, playbooks, product knowledge (vector store) | Context retrieval agent (4B) |
| **Episodic memory** | Past interactions + recommendations + human decisions | Episodic recall (4A), confidence computation, arbiter |
| **Reflective layer** | Periodic job that mines episodic memory for patterns (e.g. "pricing objections + case study = higher acceptance") and writes summarized heuristics back into semantic memory | Runs on a schedule / after N interactions — not synchronous with the main pipeline |

The reflective layer is the part most likely to get skipped under time pressure — it's also the single highest-leverage differentiator (see README "Key differentiators"). Don't cut it; simplify it if needed (e.g. a simple aggregation + LLM summarization job is enough).

---

## 6. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Orchestration | LangGraph (Python) | Use `interrupt()` for HITL pause/resume; use a `checkpointer` for persistence across the approval gate |
| Planner routing | Conditional edges driven by an LLM classification node, not if/else keyword matching | |
| LLMs | Claude — Sonnet for synthesis/arbitration/explanation, Haiku for classification/routing | Cost-aware routing is a scored differentiator — log which model handled which call and surface it in observability |
| Vector store | ChromaDB, local, embedded (no server) | Zero infra setup, no risk of a hosted dependency failing mid-demo |
| Episodic memory | SQLite | Zero setup, vibe-codes reliably via SQLAlchemy, can show judges raw rows directly if asked |
| Backend | FastAPI (or call agents directly from Streamlit if FastAPI adds no value) | Keep it Python end-to-end |
| Frontend | **Streamlit** | Chosen to stay single-language (Python) across the whole stack for faster, more reliable vibe-coding. See §7 for the specific risks this introduces and how to handle them. |
| Observability | **LangSmith** | Near-zero setup with LangGraph (env vars only) — gives a real execution trace viewer for free. Don't hand-build a trace UI; spend the saved time on the reflective memory layer instead. |
| Deployment | Local only, run live during the demo | A flawless local run beats a flaky hosted one |

### Streamlit-specific risks (read before building the UI)

- **Rerun-on-every-interaction model fights long-running pipelines.** Every click reruns the whole script top to bottom. Use `st.session_state` to hold pipeline/interrupt state — do NOT let a button click re-trigger the planner from scratch. Build and test this against a trivial dummy LangGraph pipeline on day 1, before wiring up real agents, so the pattern is solid before complexity is added on top.
- **Evidence graph display**: don't build an interactive node-graph visualization (high effort, fragile). Render it as a clean expandable list — source → excerpt → recency → reliability score, one `st.expander` per evidence node. Equally legible to a judge in a 5-minute demo, a fraction of the build time.
- **Ranked candidates panel**: use `st.columns` for side-by-side candidates, with the non-chosen ones showing their `rejected_reason` in muted/secondary text.
- **Demo-critical actions should be manual, not automatic**: give the reflective memory layer a literal "Run reflection" button rather than a background schedule, and make the "add new agent via config" extensibility proof a deliberate rehearsed click. Automatic background jobs risk firing at the wrong moment (or not at all) during a live 5-minute demo.

---

## 7. Conventions

- **Naming**: agent files `agents/<name>_agent.py` (or `.ts`), one agent per file, must export an `AgentSpec`-conforming object.
- **No agent calls another agent directly.** All inter-agent flow goes through the planner/execution engine so the execution graph stays traceable. If agent A needs agent B's output, that's a planner routing decision, not a function call.
- **All LLM calls go through a single wrapped client** that handles model routing (cheap/powerful) and cost logging — don't call provider SDKs directly from agent code.
- **Every new agent or tool must be registrable via config**, not by editing the planner. If you find yourself adding an `if agent_name == "x"` branch in core orchestration code, stop — that belongs in the registry.
- **Synthetic data lives in `/data`**, written by hand or generated once and committed — don't regenerate randomly per run, demo must be reproducible.

---

## 8. What "done" looks like for the demo

- [ ] Two different sample interactions visibly take two different planner paths
- [ ] At least one recommendation shows multiple ranked candidates with rejection reasons
- [ ] Confidence score is traceably computed (can point to the inputs that produced the number)
- [ ] At least one conflict-detection catch shown live
- [ ] One full HITL cycle: approve, one edit, one reject — all three write back to memory visibly
- [ ] Reflective layer runs at least once and visibly updates semantic memory or a heuristic
- [ ] A new agent is added via config/registry live in the demo, with no code change, and the planner routes to it
- [ ] Outcome simulator/dashboard shows aggregate metrics over replayed synthetic interactions

---

## 9. Open decisions (fill in as resolved — don't let these drift silently)

- ~~Business domain, ICP, personas~~ — **locked**: B2B SaaS Customer Success, see §1
- ~~Final tech stack choices~~ — **locked**: see §6
- Number of candidate actions generated per recommendation (default assumption: 3): `<TODO>`
- Reflective layer trigger — **locked for demo**: manual button, not scheduled (see §6 Streamlit risks). Document scheduled/event-driven trigger as the intended production design in code comments.
- Personas/ICP specifics (company size, industry vertical for synthetic accounts): `<TODO>`
- Team role split across the 3 members: `<TODO>`