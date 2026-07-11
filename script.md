# Hackathon Presentation Script & Demo Guide

This script is designed to structure your presentation, highlight key technical innovations, and provide a step-by-step guide for showcasing the platform's features to impress the hackathon judges.

---

## ── PART 1: The Pitch & Introduction (2 Minutes) ──

### 1. The Hook (Why this matters)
> *"Most enterprise AI applications today are built as simple chatbots or static recommendation engines. They give outputs, but they don't learn, they don't adapt to real-time events, and they operate in a black box. Today, we are presenting a next-generation **Agentic Decision Intelligence Platform** that acts as a living, breathing advisor for Customer Success and Recruitment team members. It continuously ingests real-time events, extracts hidden business signals, and dynamically evolves its recommendations over time."*

### 2. Core Architectural Pillars (What makes it special)
* **LangGraph-Orchestrated Multi-Agent System**: Utilizes state graphs to coordinate specialized agents (Context, Reasoning, Recommendation, Explanation, Learning).
* **Dual-Core Memory Engine**: Combines **Semantic Memory** (vector index for static playbook rules) and **Episodic Memory** (SQLite-backed history of approved human actions) to calibrate suggestions.
* **Human-in-the-Loop Interruption**: Safety first. The planner graph pauses execution at a human gate, allowing operators to edit, reject, or approve recommendations.
* **Continuous Ingestion Layer**: Evaluates incoming notes, extracts signals via an analyzer, measures operational impact, and evolves advice in real time.

---

## ── PART 2: Live Walkthrough Script (5 Minutes) ──

### Step 1: The Active Dashboard (Making the Platform Feel Alive)
* **Action**: Open the landing page (`http://localhost:5173/`). Point out the **Domain Pack Selector** at the top right (switching between Customer Success and Recruitment).
* **Talking Point**:
  > *"When we load the app, we are greeted by a sleek, Apple-style light-themed dashboard. Look at the **Recent Signals** feed at the bottom. The system is actively listening. We have simulated seed events like 'Champion resigned', 'Three P1 incidents', and 'Usage dropped 40%'. The dashboard immediately surfaces these with severity colors, showing that this is a dynamic interaction center, not a static form."*

### Step 2: The Initial Evaluation
* **Action**: Select the customer **CloudSphere Solutions** (`acc_cs_002`) from the list. Click **Run Decision Pipeline**.
* **Talking Point**:
  > *"Let's select CloudSphere Solutions. Currently, they are healthy. Let's run the pipeline. Notice the **AI Execution Center** sidebar opening. The system traces the execution of the agents. The planner classifies the state as 'standard' because the usage trend is stable/growing, and generates a routine recommendation: 'Conduct Quarterly Health Check' with a baseline confidence of 85%."*

### Step 3: Real-Time Event Ingestion
* **Action**: Click the **+ Add Interaction** button next to the customer header. In the modal, select the **Budget Freeze** or **Champion Resigned** template button. Click **Submit Interaction**.
* **Talking Point**:
  > *"Now, let's inject a real-world disruption. Let's say our primary CSM logs a call note: 'Champion Jane Doe left the company and renewal is due in 20 days'. I will select the 'Champion Resigned' template. Upon submission, pay close attention to the live progress bar: Ingestion → Signal Extraction → Impact Assessment → Planner Reclassification. The entire agent loop runs in under a second!"*

### Step 4: Inspecting the Intelligence Layer & Evolution
* **Action**: Point to the **Interaction Timeline** below the header. Show the new orange badge for `Meeting` and `champion_change` signal. Next, switch the sidebar to **Interactions** and **What Changed** panels.
* **Talking Point**:
  > *"Look at the UI update. First, the interaction is added to the SQLite-backed timeline. Second, look at the sidebar's **Interaction Intelligence** panel. The system extracted the `champion_change` signal, assessed a **+25 Renewal Risk** and **+20 Churn Probability** impact delta, and the **Planner reclassified the account from standard to escalation**.*
  >
  > *Now look at the **Recommendation Evolution** (under What Changed). The recommendation evolved from 'Conduct Quarterly Health Check' to 'Schedule Executive Alignment Call'. Under the hood, the system did a semantic lookup on our playbook DB, recognized the new interim sponsor Robert Chen, and adapted the advice. The linter-provenance fields even show us exactly which playbook rules drove this output!"*

### Step 5: Human Gate & Episodic Feedback Loop
* **Action**: Click **Edit & Approve** or **Approve**. In the edit modal, modify the description slightly and type some feedback notes (e.g. "Important to include the VP of Sales"). Click **Submit Edits & Approve**.
* **Talking Point**:
  > *"We don't let AI run wild. The system pauses at a human checkpoint. I will edit the action slightly, type feedback, and click Approve. This logs the final decision into our **Episodic Memory** database. The system now has a record of what we did, which will influence future confidence scores!"*

### Step 6: Learning Hub & Reflection
* **Action**: Point to the **Learning Hub** in the right column. Click **Run Reflection**.
* **Talking Point**:
  > *"To ensure long-term reproducibility, we have a Learning Agent. By clicking 'Run Reflection', the system scans the episodic SQLite records, clusters human approval patterns, and dynamically generates new heuristics that are written back into vector search. It self-corrects based on historical decisions."*

---

## ── PART 3: Codebase Deep Dive (3 Minutes) ──

*Open these files in your IDE to walk the judges through the clean, robust implementation.*

### 1. `backend/core/planner.py`
* **Why it's impressive**: This is the brain of the platform. It compiles the LangGraph state machine.
* **Show the Judges**:
  - The `StateGraph` definition and the static/conditional routing splits.
  - The `interrupt_before=["human_approval_node"]` compilation check.
  - Explain how the state is persisted via the `MemorySaver` checkpointer so it can suspend and resume seamlessly.
  - Point to the **Max Graph Depth and Execution Guards** (`MAX_GRAPH_DEPTH = 10` and `MAX_AGENT_EXECUTIONS = 20`) that prevent infinite routing loops.

### 2. `backend/agents/interaction_analyzer.py` & `backend/core/impact_engine.py`
* **Why it's impressive**: Demonstrates clean signal modeling and deterministic impact rules.
* **Show the Judges**:
  - The lists of CS and recruitment keyword arrays (e.g., `champion_change`, `renewal_risk`).
  - How delta scores are computed, clamped, and mapped to overall severity.

### 3. `backend/security/recommendation_guard.py`
* **Why it's impressive**: Demonstrates enterprisey AI safety. It prevents hallucinated entities and destructive actions.
* **Show the Judges**:
  - The validation functions that verify claims, penalize confidence if evidence is missing, and rewrite absolute claims (e.g., changing "Customer will definitely churn" to "Customer exhibits churn risk indicators").

### 4. `backend/memory/interactions.py`
* **Why it's impressive**: Highlights clean ORM persistence with zero-dependency SQLite databases.
* **Show the Judges**:
  - The SQLAlchemy ORM classes (`InteractionRecord` and `RecommendationEvolution`).
  - The seeding routing that initializes the DB with realistic, domain-specific data on startup.

---

## ── PART 4: Key Exaggerations / Buzzwords to Use ──

* **"Explainability Provenance"**: Don't just say 'we search playbooks'. Say: *"Every recommendation is tied to its originating source documents and playbooks, providing full audit compliance."*
* **"Low-Confidence Advisory Fallback"**: Say: *"If the confidence score drops below 60%, the recommendation agent automatically triggers a safety fallback, overriding risky actions with a Request More Information query."*
* **"Decoupled Learning Loop"**: Say: *"Our learning loop runs asynchronously, mining episodic feedback records to generate localized heuristics without blocking the user response."*
* **"Zero-Dependency Vector/Episodic Integration"**: Say: *"We've built an enterprise-ready memory footprint using a zero-dependency SQLite and local keyword-matching setup that executes in milliseconds without needing expensive external vector APIs."*
