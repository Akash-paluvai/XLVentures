# System Architecture

The Decision Intelligence Platform is structured as a decoupled, configuration-driven multi-agent system. It segregates logic between:
1. **Frontend Dashboard (React + Vite)**: A dynamic interface to review, approve, and audit recommendations.
2. **Web API Layer (FastAPI)**: Coordinates requests, manages request tracing, and handles lifespan startup checks.
3. **Planner Agent (LangGraph)**: Compiles the state graph, manages interrupts, and coordinates agent handoffs.
4. **Memory Layer Abstraction**: Manages relational (SQLite/PostgreSQL) and semantic vector (Chroma/Qdrant) data.

---

## High-Level Architecture Block Diagram

```mermaid
graph TD
    Client[React Client SPA] <-->|HTTP API / JSON| API[FastAPI Web Service]
    API <-->|State Execution| Graph[LangGraph State Machine]

    subgraph Agents [The 5 Agents]
        Graph -->|1. Ingest| Agent1[Context Agent]
        Graph -->|2. Analyze| Agent2[Reasoning Agent]
        Graph -->|3. Propose| Agent3[Recommendation Agent]
        Graph -->|4. Explain| Agent4[Explanation Agent]
        Graph -->|5. Learn| Agent5[Learning Agent]
    end

    subgraph Storage [Decoupled Storage Layer]
        Agent1 -.->|Semantic Search| Vec[Vector Store Chroma/Qdrant]
        Agent5 -.->|Write Heuristics| Vec
        Graph -.->|Audit Logs / Feedback| DB[Relational DB SQLite/Postgres]
    end
```

---

## Global Execution Handoff Sequence

The diagram below details the handoff flow from the initial user event to the final feedback and learning loops.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as User / Decider
    participant Client as React Dashboard
    participant API as FastAPI Backend
    participant Graph as LangGraph Planner
    participant Context as Context Agent
    participant Explain as Explanation Agent
    participant Learning as Learning Agent
    participant Storage as Storage Repositories

    Admin->>Client: Select Domain & Input Event
    Client->>API: POST /api/v1/recommend (Payload)
    API->>Graph: Compile & Execute Graph (Thread ID)
    Graph->>Context: Retrieve Playbooks & Past Cases
    Context->>Storage: Vector Similarity Match
    Storage-->>Context: Return Documents & Weights
    Graph->>Explain: Reason, Score & Generate Recommendation
    Graph->>API: Interrupt / Pause Graph (human_review)
    API-->>Client: Return JSON Recommendation + Explanations
    Client-->>Admin: Render Action Card & Evidence Accordion

    Admin->>Client: Click Approve / Edit Action
    Client->>API: POST /api/v1/approve (Outcome Feedback)
    API->>Graph: Resume Graph from Checkpoint
    Graph->>Learning: Log Action Outcome & Trigger Reflection
    Learning->>Storage: Save Relational Feedback & Update Heuristics Document
    Storage-->>Graph: Success ACK
    Graph-->>API: Graph Complete (END)
    API-->>Client: Update UI State (Success)
```
