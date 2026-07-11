# Technical Debt & Maintainability Review

This document summarizes known technical debt, formatting items, and typing improvements identified for the Decision Intelligence Platform.

---

## 1. Identified Technical Debt & Polish Items

### A. Python Static Typing Mismatches
* **Status**: Moderate Debt.
* **Analysis**: Several helper methods use generic dictionaries (`Dict[str, Any]`) instead of concrete Pydantic schemas.
* **Remediation**: Transition dynamic dictionary variables in `planner.py` to structured TypedDict and Pydantic models to catch schema issues during compilation.

### B. React Client State Coupling
* **Status**: Low Debt.
* **Analysis**: The global Zustand store holds both domain pack configuration data and execution histories.
* **Remediation**: Split the store into separate hooks (`useConfigStore`, `useHistoryStore`) to improve modular code encapsulation.

---

## 2. Standardized Naming Conventions
* **API Endpoints**: Use lower-kebab-case prefixes (`/api/v1/recent-interactions`).
* **Python Modules**: Use snake_case for all module files (`episodic.py`, `factory.py`).
* **React Components**: Use PascalCase for components (`Navbar.jsx`, `EvidenceAccordion.jsx`).

---

## 3. Code Optimization Summary
* **Unused Variables**: Successfully ran Ruff lint check to purge dead variables (`safe_interaction`, `pack_data`, etc.).
* **Magic Constants**: Replaced magic values in `explanation_agent.py` and `input_guard.py` with centralized definitions imported from `backend/core/constants.py`.
