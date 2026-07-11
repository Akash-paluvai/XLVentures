# ADR 003: Why React

## Context & Problem
We require a highly interactive, responsive dashboard for decision-makers to inspect multi-agent reasoning paths, review confidence factors, edit actions, and trigger reflections. We need a framework that:
1. Provides structured UI updates based on backend API state changes.
2. Supports rich components (graphs, timelines, accordion lists).
3. Has lightweight state management for domain swap context.

## Decision
We choose **React** with **Vite** (bundler) and **Zustand** (state management) as our frontend client stack.

## Consequences & Rationale
* **Component-Driven UI**: React's modular structure allows isolating visual blocks (e.g., the Evidence Accordion, Timeline items, Trace canvas) into reusable components.
* **Fast State Re-rendering**: Zustand handles active domain packs and execution context states simply and with minimum boilerplates.
* **Vite Development Loop**: Vite provides instantaneous Hot Module Replacement (HMR) and extremely fast production bundle compilation.
* **Ecosystem Diversity**: Standard, beautiful elements can be easily built using Vanilla CSS for full control over modern visual designs.

## Alternatives Considered
* **Vanilla JS**: Hard to scale, error-prone when syncing visual state changes with complex JSON APIs.
* **Next.js**: Excellent, but introduces unnecessary server-side rendering complexity for a client-only single-page admin portal.
