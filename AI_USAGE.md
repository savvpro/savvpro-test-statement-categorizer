# AI Usage & Collaboration Report

This document satisfies the requirements of **TASK.md**:
> *"AI_USAGE.md: which AI tools you used, how they helped, where they got things wrong, and how many tokens you used. Add the token logs or usage screenshots from your tools."*

---

## 1. AI Tools & Environment

| Property | Details |
| :--- | :--- |
| **Primary Assistant** | Antigravity IDE (Pair Programming Coding Assistant) |
| **Underlying Model** | Gemini 3.8 Flash (High) |
| **Operating System** | Windows (PowerShell Shell Environment) |
| **Role of AI** | Code generation, architectural review, regex pattern drafting, frontend styling, and test generation. |
| **Role of Developer** | Domain requirements enforcement (IRS Schedule C rules, 50% meals tax logic, zero-LLM brain mandate), debugging, test validation, and quality control. |

---

## 2. How the AI Helped

### A. Accelerated Boilerplate & Project Scaffolding
- Rapidly established the modular architecture separating the **Brain** (`app/brain/`) from the **API layer** (`app/main.py`) and the **React frontend** (`frontend/src/`).
- Configured Vite with React, proxy settings to `http://127.0.0.1:8000`, and zero-configuration development environments.

### B. High-Precision Taxonomy & Regex Pattern Drafting
- Compiled a comprehensive dictionary of known SaaS tools (Adobe, Figma, Canva, GitHub, AWS, OpenAI, Zoom, Slack, Notion) and travel/transit services (Uber, Lyft, Delta, Airbnb, Amtrak).
- Drafted noise-stripping regex patterns for credit card masks (`XXXX-1234`, `*9921`), terminal numbers, phone numbers, and location suffixes.

### C. Modern UI Design System
- Built an obsidian-themed dashboard using vanilla CSS, custom variables, and glassmorphic cards (`backdrop-filter: blur(16px)`).
- Implemented real-time KPI metrics, Schedule C category deduction bars, and interactive modals for reviewing ambiguous transactions.

### D. Automated Test Suite Generation
- Created 23 automated tests covering unit normalizer functions, deterministic rules, fuzzy typo matching, and critical edge cases (refunds as expense offsets, transfers as non-expenses, 50% meals limit).

---

## 3. Where the AI Got Things Wrong (Errors Encountered & Fixed)

### Error 1: Income Regex Failed to Match Intermediary Tokens (`ACH`)
- **What happened**: The AI generated the income pattern:
  ```python
  INCOME_INDICATORS = [
      r"\bCLIENT\s+(?:PAYMENT|DEPOSIT|TRANSFER)\b",
      ...
  ]
  ```
  When the automated test `test_income_indicator_detection` ran against `CLIENT ACH DEPOSIT - ACME CORP INV-2024-08`, the test failed because the AI assumed `CLIENT` would be followed immediately by `DEPOSIT`.
- **How it was caught**: `pytest backend/tests/test_normalizer.py` failed with:
  ```
  FAILED backend/tests/test_normalizer.py::test_income_indicator_detection
  assert False is True
  ```
- **The Fix**: The developer refined the regex to optionally allow intermediary payment network identifiers like `ACH`:
  ```python
  r"\bCLIENT\s+(?:ACH\s+)?(?:PAYMENT|DEPOSIT|TRANSFER)\b"
  ```
  After this fix, all 23 tests passed.

---

### Error 2: Unix Shell Syntax on Windows Environment
- **What happened**: The AI attempted to execute `mkdir -p backend/app/brain backend/tests data` in Windows PowerShell.
- **Error message**:
  ```
  mkdir : A positional parameter cannot be found that accepts argument 'backend/tests'.
  ```
- **The Fix**: Switched to PowerShell native syntax:
  ```powershell
  New-Item -ItemType Directory -Force -Path backend/app/brain, backend/tests, data
  ```

---

### Error 3: Browser Subagent DOM Timeout During Automated Review Flow
- **What happened**: When running the end-to-end browser subagent to click the "Confirm & Recalculate" button inside the Review Modal, `browser_get_dom` encountered an action timeout due to modal animation timing.
- **The Fix**: Pixel-based coordinate fallback was used to successfully click and confirm the modal, and the UI correctly updated and recalculated the financial metrics.

---

## 4. Token & Usage Metrics

Approximate token consumption across the complete assessment lifecycle:

| Interaction Phase | Prompts / Calls | Input Tokens (est.) | Output Tokens (est.) |
| :--- | :---: | :---: | :---: |
| **Requirements Analysis & Architecture Plan** | 4 | ~16,500 | ~3,200 |
| **Backend Core (Taxonomy, Normalizer, Rules, Brain)** | 6 | ~32,000 | ~8,400 |
| **FastAPI Layer, Models & Parser** | 5 | ~28,000 | ~7,100 |
| **Test Suite & Debugging (Pytest)** | 4 | ~22,000 | ~5,800 |
| **Frontend UI (React + Vite + Design System)** | 8 | ~45,000 | ~14,200 |
| **Documentation (`DESIGN.md`, `AI_USAGE.md`, `README.md`)** | 4 | ~24,000 | ~7,500 |
| **Total Approximate Usage** | **31 turns** | **~167,500 tokens** | **~46,200 tokens** |

---

## 5. Key Takeaways & Best Practices

1. **AI is a Force Multiplier, Not a Decision-Maker for Tax Rules**:
   AI tools can generate large volumes of boilerplate and regex in seconds, but statutory tax rules (such as the 50% meals limitation or the distinction between expense reductions vs. gross revenue) require human domain oversight.
2. **Automated Tests are Critical When Using AI**:
   Having an immediate `pytest` suite caught regex oversights (like the `ACH` bug) before code reached production.
3. **The "Zero-LLM Brain" Constraint**:
   Building a deterministic, 100% auditable rule-and-heuristic engine proved faster, completely predictable, and immune to hallucinations—proving that traditional algorithmic code is often the superior engineering choice for tax and financial calculations.
