# TODO.md — shift-based build plan (2 people, alternating, 1-2hr shifts)

Deadline: Mon June 29 EOD. Today: Sat June 27. Budget: 9 shifts, alternating Person A / Person B.
**Rule: never start a shift until the previous one ends in a working, committed state.** Each shift below ends with a "Definition of done" — if you can't check every box, do not hand off; finish or explicitly descope before committing.

**Git rule for vibe-coded handoffs:** commit + push at the end of every shift, no exceptions, even if incomplete-but-working. Next person always starts by pulling and running the app once before touching anything, to confirm the handoff state actually works on their machine.

---

## Shift 1 (Person A) — Scaffolding, contracts, synthetic data skeleton

**Goal:** repo exists, runs, has the shape everything else slots into.

- [ ] Init repo structure per `README.md` (`agents/`, `tools/`, `registry/`, `config/`, `memory/`, `ui/`, `data/`, `docs/`)
- [ ] `requirements.txt`: langgraph, langchain, anthropic, chromadb, streamlit, langsmith, python-dotenv
- [ ] `.env.example` with `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`, `LANGCHAIN_TRACING_V2=true`
- [ ] Create `core/schemas.py` implementing every data contract from `description.md` §4 (`DomainPack`, `DecisionPoint`, `AgentSpec`, `Recommendation`, `CandidateAction`, `ComputedConfidence`, `EvidenceNode`, `MemoryWrite`) as Pydantic models
- [ ] Create `config/domain_packs/customer_success.json` — stub with the 4 decision points from `description.md` §1, empty prompt_overrides for now
- [ ] Write 5-6 synthetic CS accounts in `data/customer_success/accounts.json`: each with company name, plan tier, usage trend, last 2-3 interaction notes (mix of renewal-risk, upsell, escalation, champion-change signals across the set so later agents have variety to react to)
- [ ] Trivial `app.py` Streamlit entrypoint that just loads and prints the domain pack + account count, to confirm the scaffolding wires together

**Definition of done:** `streamlit run app.py` runs with no errors and shows "Loaded N accounts for customer_success pack." Commit + push.

---

## Shift 2 (Person B) — Memory layer + Tool registry skeleton

**Goal:** the data plumbing every agent will call into.

- [ ] `memory/episodic.py`: SQLite setup (SQLAlchemy), table matching `Recommendation` + `MemoryWrite` schemas, tagged with `domain_pack_id`. Functions: `write_recommendation()`, `write_feedback()`, `get_similar_past_cases(domain_pack_id, query)` (stub similarity for now — can be naive keyword match, replace later if time)
- [ ] `memory/semantic.py`: ChromaDB local client, one collection per domain pack. Function `add_documents(domain_pack_id, docs)`, `query(domain_pack_id, query, k)`
- [ ] Seed semantic memory: write 4-5 short CS playbook snippets into `data/customer_success/playbooks/` (plain text — e.g. "renewal risk playbook," "upsell qualification criteria") and a script `scripts/seed_memory.py` that loads them into Chroma on first run
- [ ] `registry/tool_registry.py`: simple dict-based registry (`register_tool(name, fn)`, `get_tool(name)`), pre-register a `search_accounts` tool and a `query_playbooks` tool wrapping the memory functions above
- [ ] Quick test script `scripts/test_memory.py` proving a write + read round-trip on both stores

**Definition of done:** running `scripts/seed_memory.py` then `scripts/test_memory.py` prints retrieved playbook snippets and a sample episodic write/read. Commit + push.

---

## Shift 3 (Person A) — Context Agent

**Goal:** first real agent, working end to end against memory from Shift 2.

- [ ] `agents/context_agent.py`: implements `AgentSpec`. Input: an account interaction. Output: retrieved playbook snippets (semantic), similar past cases (episodic), and the raw interaction data — bundled per the `EvidenceNode`-compatible shape
- [ ] Wrap a single Claude call (Haiku) that the agent uses only if synthesis of retrieved snippets is needed — keep this agent retrieval-heavy, not reasoning-heavy (see `description.md` §3 scope table)
- [ ] `registry/agent_registry.py`: same pattern as tool registry, register the Context Agent
- [ ] Test script `scripts/test_context_agent.py` running it against 2 different synthetic accounts, printing what it retrieved for each — confirm the outputs are visibly different per account (this is your first proof the system isn't hardcoded)

**Definition of done:** test script shows two distinct retrieval outputs for two different accounts, no errors. Commit + push.

---

## Shift 4 (Person B) — Reasoning Agent + Recommendation Agent

**Goal:** the two middle agents, working standalone against Context Agent's output.

- [ ] `agents/reasoning_agent.py`: takes Context Agent output, calls Claude (Sonnet) to identify risks/opportunities/missing info/conflicts. Output matches the risk/opportunity/conflict portion of the pipeline — keep output as structured JSON (risks: [], opportunities: [], conflicts: [], missing_info: [])
- [ ] `agents/recommendation_agent.py`: takes Reasoning Agent output, generates 3 `CandidateAction`s (Claude Sonnet, structured output), ranks them, fills `rejected_reason` for the 2 not chosen
- [ ] Register both in `agent_registry.py`
- [ ] Test script `scripts/test_pipeline_partial.py` chaining Context → Reasoning → Recommendation manually (no planner yet) for one synthetic account, printing the final 3 ranked candidates with reasons

**Definition of done:** test script prints 3 ranked candidates with rejection reasons for at least one account, end to end. Commit + push.

---

## Shift 5 (Person A) — Explanation Agent + Learning Agent + computed confidence

**Goal:** close the loop on explainability and memory writeback (no planner/UI yet).

- [ ] `agents/explanation_agent.py`: takes the chosen `CandidateAction` + the evidence gathered upstream, builds `EvidenceNode[]` and `reasoning_trace`, and **computes** `ComputedConfidence` per `description.md` §2 rule 4 — i.e. write an actual function combining evidence_count, source_agreement (can be a simple heuristic: agreement = 1 - conflict_count/evidence_count), and historical_acceptance_rate pulled from episodic memory (default to a neutral prior like 0.5 if no history exists yet)
- [ ] `agents/learning_agent.py`: `write_outcome(recommendation, human_decision, feedback_text)` → writes to episodic memory via Shift 2's functions. Also implement `run_reflection(domain_pack_id)`: pulls recent episodic entries, asks Claude to summarize 1-2 patterns, writes them as new documents into semantic memory. This will be wired to a manual UI button later — for now just make it callable.
- [ ] Register both agents
- [ ] Extend `scripts/test_pipeline_partial.py` to run all 5 agents manually in sequence (still no planner) and print the full `Recommendation` object including computed confidence

**Definition of done:** full 5-agent manual chain prints a complete `Recommendation` with a computed (not LLM-stated) confidence score. Commit + push.

---

## Shift 6 (Person B) — Planner Agent + LangGraph wiring (critical integration shift)

**Goal:** replace the manual chain with real dynamic orchestration. This is the most important shift in the whole plan — protect the time for it.

- [ ] `core/planner.py`: LangGraph `StateGraph`. Define `AgentState` (interaction in, all 5 agents' outputs accumulating)
- [ ] Planner node: one Claude (Haiku) call that classifies the incoming interaction against the domain pack's `decision_points` and decides agent sequence (for v1 this can mean: always run Context → Reasoning → Recommendation → Explanation, but the *decision point classification* must be visibly different per input — that's the dynamic part graded)
- [ ] Conditional edges based on the classification — at minimum, show one branch difference (e.g. if `champion_change_risk` is detected, the graph also re-invokes Context Agent for an extra contact-history lookup before Reasoning)
- [ ] Wire `interrupt()` before "execute"/finalize, to pause for human approval (approval handling itself comes in Shift 7 — for now just confirm the graph pauses)
- [ ] Add LangSmith tracing (env vars only, per `description.md` §6)
- [ ] Test script `scripts/test_planner.py` running 2 different synthetic accounts through the full graph, confirming the classification and routing differ between them, and that the graph pauses at the interrupt point

**Definition of done:** two different accounts visibly produce two different planner classifications/paths in the LangSmith trace or printed logs, and the graph correctly pauses before finalizing. This satisfies the most important checklist item in `description.md` §8. Commit + push.

---

## Shift 7 (Person A) — Streamlit UI: recommendation view + HITL approval

**Goal:** make Shift 6's pipeline visible and operable by a human.

- [ ] `ui/pages/recommend.py` (or section in `app.py`): account selector → triggers the planner graph → displays ranked candidates (`st.columns`, non-chosen showing `rejected_reason` muted) → evidence list as `st.expander` per `EvidenceNode` (per `description.md` §6 Streamlit guidance — no graph viz)
- [ ] Approve / Edit / Request more info / Reject buttons, using `st.session_state` to hold the paused graph state (per the session-state warning in `description.md` §6 — test that clicking a button doesn't silently re-run the planner from scratch)
- [ ] Wire button actions to `interrupt()` resume + `learning_agent.write_outcome(...)`
- [ ] Manual confirmation: approve one, edit one, reject one across different test accounts and confirm all three show up in episodic memory (query it directly to check)

**Definition of done:** full click-through demo works in the browser: pick account → see recommendation → approve/edit/reject → confirm memory updated. Commit + push.

---

## Shift 8 (Person B) — Configuration Hub UI + second domain pack (Staffing/Recruitment, lightweight)

**Goal:** the headline differentiator — live domain-pack switch, no code change. Keep this pack deliberately thin (see scope list below) — depth belongs in the CS pack, not here.

- [ ] `config/domain_packs/recruitment.json`: entities (`Candidate`, `Job`, `Interview`), workflows (`Screening`, `Offer` — only these two), tools (`ATS`, `Resume Parser`, `Email`), one business rule (e.g. candidate fit score > 85% → fast-track), success_metrics (`time_to_hire`), decision points mapped from CS per the README mapping table (e.g. `candidate_dropoff_risk`, `fast_track_opportunity`), prompt_overrides per agent
- [ ] `data/recruitment/`: **2-3** synthetic candidate/job records only (not 5-6 like CS) + interview transcript notes
- [ ] `data/recruitment/playbooks/`: 2-3 short screening/offer playbook snippets, seeded into a separate Chroma collection
- [ ] `ui/`: domain pack selector (dropdown) in the Configuration Hub section — switching it must reload the agents' prompt overrides and point retrieval at the correct domain pack's memory collections, with zero code changes (this is the test — if you find yourself editing an agent file to make recruitment work, something is wired wrong per `description.md` §7)
- [ ] Run **one** recruitment candidate through the full pipeline end to end and confirm a coherent recruitment-specific recommendation comes out (target output shape: "Risk: candidate may decline offer. Next action: fast-track offer + schedule hiring manager call. Confidence: ~88%")
- [ ] Simple observability/metrics panel: acceptance rate, risk-catch lead time, simulated NRR impact for CS — for recruitment, just show time-to-hire if trivial, otherwise skip (don't spend extra time here)
- [ ] **Stop here for the recruitment pack.** Do not build a second playbook depth pass, a second confidence calibration, or any agent-level branch for it — if it's tempting, that effort goes back into the CS pack instead

**Definition of done:** in the running app, switching the domain pack dropdown from "Customer Success" to "Recruitment" and running a recommendation produces a coherent recruitment-specific output, with no code edited to make it happen. Commit + push.

---

## Shift 9 (Person A) — Buffer: polish, reflection button, README/demo prep

**Goal:** everything that makes the demo land, not new features. Skip any unchecked item if out of time — this entire shift is the cut-first buffer.

- [ ] Wire the "Run reflection" manual button (Learning Agent's `run_reflection`) into the UI, confirm it visibly adds a new doc to semantic memory when clicked
- [ ] Fix any rough edges found while rehearsing the demo flow once, start to finish, out loud
- [ ] Finalize `README.md`: fill in any remaining `<TODO>` (team names, license), confirm getting-started commands actually work from a clean clone
- [ ] Write a rough demo script/runbook in `docs/demo_script.md`: exact click order, which 2 accounts to use, what to say at the domain-pack-switch moment (your strongest beat — don't ad-lib it)
- [ ] Record the 5-min demo video + 5-min architecture walkthrough
- [ ] Final commit + push, tag the submission commit

**Definition of done:** demo runs clean once, start to finish, without intervention. Videos recorded. Repo pushed.

---

## If you're running behind (cut in this order)

1. Drop the conditional-branch nuance in Shift 6 (keep planner classification visible, but the agent sequence can stay fixed) — the classification alone still proves dynamism for the demo narrative.
2. Drop the metrics dashboard panel in Shift 8 — mention the metrics verbally in the demo instead of showing a live panel.
3. Drop the reflection button wiring in Shift 9 — describe it in the architecture walkthrough as implemented-but-not-demoed-live, and show the code.
4. Never cut: the domain-pack switch (Shift 8 core) and the HITL approve/edit/reject memory writeback (Shift 7) — these are your two strongest, most differentiated demo beats.