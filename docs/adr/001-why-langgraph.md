# ADR 001: Why LangGraph

## Context & Problem
Decision Intelligence platforms require state orchestration across multiple independent LLM agents. Traditional linear pipelines fail when:
1. Loops are required (e.g., re-running reasoning or reflection based on feedback).
2. Human-in-the-loop validation is needed to interrupt execution before finalizing actions.
3. State preservation is needed to inspect traces and rollback execution steps.

## Decision
We choose **LangGraph** (built on top of LangChain) as our core orchestration framework.

## Consequences & Rationale
* **Graph-Based Cycles**: Allows modeling loops natively. We can easily transition back to context retrieval, reasoning updates, or learning reflections based on feedback.
* **First-Class Persistence**: Built-in checkpointers (like `MemorySaver`) save state at every step. This makes debugging, tracing, and multi-turn state recovery out-of-the-box features.
* **Human-in-the-loop Interrupts**: LangGraph supports thread interrupts. When transitioning to human validation, the graph automatically pauses execution, saves progress, and resumes state from the last compiled checkpoint when the user acts.
* **Thread Isolation**: Supports thread IDs, allowing multiple parallel customer sessions to execute concurrently without mixing memory states.

## Alternatives Considered
* **Vanilla Linear Chains**: Simple but completely lacks loop support and human interrupt capability.
* **Custom State Engines**: Building state-machines manually with database tables is error-prone, hard to scale, and lacks integration with LangChain's ecosystem.
