# ADR 004: Why Vector Memory Abstraction

## Context & Problem
Decision Intelligence platforms rely on:
1. **Episodic Memory**: Storing structured decisions, feedback records, and audit history.
2. **Semantic Memory**: Querying unstructured playbooks, enterprise PDFs, and domain docs using semantic similarity.

Hardcoding direct connections (like SQLite for relational storage or Chroma for vector retrieval) creates tight coupling and makes shifting to production-ready enterprise systems (PostgreSQL, Qdrant, Pinecone) expensive.

## Decision
We implement a decoupled repository abstraction layer for storage. The core application calls generic storage interface functions (`add_documents`, `query`, `write_feedback`), which are mapped at startup via an abstract factory to the selected backend.

## Consequences & Rationale
* **Backend Swapping**: Switching vector engines is done via simple configurations (`VECTOR_DB=qdrant` vs `VECTOR_DB=chroma`).
* **Clean Code Boundary**: Agents and planner logic remain completely isolated from databases, schemas, or query constructs.
* **Testing Isolation**: Integrated pipeline tests can run instantly using local mock connections (SQLite + Chroma memory mode) without requiring docker instances.

## Alternatives Considered
* **Direct Vector API Calls**: Overly coupled. Swapping databases would require rewriting context retrieval across all agent code.
