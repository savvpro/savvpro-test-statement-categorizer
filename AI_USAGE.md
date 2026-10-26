# AI Usage & Collaboration Report

This document records the AI tools, methodologies, failure points, and token metrics utilized during the design and development of **LedgerLens**.

---

## 1. AI Tools Used

- **Primary AI Assistant:** Google Antigravity (Advanced Agentic Pair Programming Assistant powered by Gemini 3.8 Flash)
- **Role:** Architectural advisor, code scaffolding partner, automated test author, and refactoring agent.
- **Rule Adherence Check:** In compliance with **The One Big Rule**, no LLMs, generative APIs, or cloud model inferences are present in the runtime codebase. The application decision engine ("The Brain") is 100% deterministic Python heuristics.

---

## 2. How AI Helped

1. **Requirements Auditing & Gap Identification:**
   - Evaluated the cloned workspace against the task specification.
   - Identified critical omissions (missing `.gitignore`, missing frontend, unconfigured pytest paths).

2. **Deterministic Brain Engineering:**
   - Designed a multi-stage pipeline handling normalization, internal transfer filtering, refund/reversal credit allocation, and Schedule C tax category classification.
   - Implemented flexible header resolution to parse CSVs containing split `Debit`/`Credit` columns or varied naming schemes (`Date`, `Transaction Date`, `Description`, `Merchant`, `Amount`).

3. **Frontend Implementation:**
   - Converted a bare Vite starter into a fully featured React dashboard.
   - Built interactive components: drag-and-drop CSV upload, 1-click sample statement loader, real-time Schedule C deduction cards, live row editing with backend recalculation, and CSV report export.

4. **Comprehensive Test Suite:**
   - Authored 23 test cases spanning heuristic classifications, edge cases, financial math, and API endpoints.

---

## 3. Where AI Got Things Wrong & How It Was Corrected

### Incident 1: Over-Matching on Generic Merchant Tokens
- **What happened:** During the initial expansion of the `Meals (50% Deductible)` lexicon, the token `"CAFE"` was included. When evaluating `JOES CAFE 9921`, the brain classified it with high confidence as a deductible meal instead of flagging it for review.
- **Why it was wrong:** The prompt explicitly stated:
  > *"JOES CAFE 9921 is unknown, so it goes to Needs Review. If the app is not sure, it must say so. A wrong guess is worse than asking."*
- **Correction:** Automated pytest test `test_unknown_merchant_needs_review` caught the assertion failure. Generic nouns (`CAFE`, `COFFEE`, `RESTAURANT`) were purged from the automatic lexicon. Local and ambiguous establishments now correctly default to **Needs Review**.

### Incident 2: Python Decimal vs Float Type Mismatch
- **What happened:** In `test_categorizer.py`, the test asserted `parse_amount("(49.99)") == -49.99`.
- **Why it was wrong:** `parse_amount` returns a `Decimal` instance for monetary accuracy without floating-point drift. Python does not equate `Decimal("-49.99")` to `float(-49.99)`.
- **Correction:** Updated test assertions to check against explicit `Decimal("-49.99")`.

### Incident 3: Async Event Loop Deadlock in Tests
- **What happened:** Testing `categorize_csv` with `asyncio.run()` hung during `await file.read()` because Starlette `UploadFile` uses `anyio.to_thread.run_sync` which conflicted with the test runner's event loop.
- **Correction:** Refactored the core CSV parsing logic into a clean, synchronous helper `process_statement_bytes(content: bytes, filename: str)`. This decoupled the business logic from HTTP transport, making tests execute in under 4 seconds without async threading locks.

### Incident 4: TypeScript Side-Effect CSS Import Error
- **What happened:** Running `pnpm --dir frontend run build` threw `error TS2882: Cannot find module or type declarations for side-effect import of './index.css'`.
- **Correction:** Added `frontend/src/vite-env.d.ts` with `<reference types="vite/client" />` and CSS module declarations, enabling clean compilation.

### Incident 5: Overly Clichéd "AI Template" UI Aesthetics
- **What happened:** Initial UI pass included generic AI tropes (sparkles icons, glowing multi-color cards, rainbow badges) that felt like an AI template rather than an authentic financial tool.
- **Correction:** Redesigned the interface into a professional fintech design system inspired by Mercury and Ramp: deep neutral obsidian/slate surfaces, tabular monospace figures (`font-variant-numeric: tabular-nums`), clean reconciliation progress indicator, custom-styled category dropdowns, and restrained status pills.

---

## 4. Token & Session Metrics

### Estimated Usage Summary

| Activity | Input Tokens | Output Tokens | Total Tokens |
| :--- | :--- | :--- | :--- |
| Initial Assessment & Codebase Audit | ~28,000 | ~2,500 | ~30,500 |
| Backend Engine Refactoring & Tests | ~34,000 | ~4,200 | ~38,200 |
| React UI Development & Styling | ~42,000 | ~6,800 | ~48,800 |
| Build Fixes, Debugging & Test Runs | ~22,000 | ~2,100 | ~24,100 |
| Documentation (`DESIGN.md`, `AI_USAGE.md`, `README.md`) | ~18,000 | ~3,400 | ~21,400 |
| Enterprise UI Refinement (Fintech Theme & Polish) | ~20,000 | ~2,800 | ~22,800 |
| **Total Estimated Token Usage** | **~164,000** | **~21,800** | **~185,800** |

*Model: Gemini 3.8 Flash (High)*
