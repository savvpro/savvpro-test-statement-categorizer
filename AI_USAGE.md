# AI Usage Log & Disclosure

## 1. AI Tools & Models Used

- **Primary Tool:** Google Antigravity Agentic Coding Assistant
- **Model:** Gemini 3.8 Flash (Medium)
- **Role:** Pair-programming, code scaffolding, test generation, and architectural design assistance.

---

## 2. Tasks Assisted by AI

1. **Architecture & Schema Planning:**
   - Designed normalized transaction data structures and canonical U.S. Schedule C category mappings for independent creative freelancers.
   - Designed layered deterministic categorization hierarchy to ensure 100% adherence to the mandatory rule: **No LLM or remote AI calls at runtime**.

2. **Deterministic Rules Engine & Pattern Identification:**
   - Compiled vendor regex and lookup tables for common creative freelancer SaaS tools (Adobe, Figma, GitHub, Canva, JetBrains), transit providers (Uber, Lyft, Amtrak), dining (Starbucks, Blue Bottle), and telecommunications (Comcast, Verizon).
   - Formulated heuristics for processor-mangled descriptors (`SQ *`, `TST* `) and ambiguous merchants (`JOES CAFE 9921`, `AMAZON.COM`).

3. **Automated Testing Suite:**
   - Scaffolded 39 unit and integration tests covering parser edge cases (parentheses negative amounts, `DR`/`CR` notation, trailing minuses, CSV formats A & B), categorization precedence, duplicate charge detection, Decimal arithmetic precision, and FastAPI HTTP endpoints.

4. **Frontend UI Scaffolding:**
   - Scaffolded React 18 + Vite + TypeScript single-page application components (`Header`, `UploadDropzone`, `SummaryCards`, `CategoryBreakdown`, `TransactionTable`, `ExplainModal`).
   - Implemented sleek dark/slate CSS design tokens, micro-interactions, responsive table layout, and inline category editor with real-time recalculation.

---

## 3. Where the Initial AI Attempt Was Wrong & Corrected

During the development cycle, several edge cases and environment challenges were detected and actively corrected:

### 1. `DR`/`CR` Amount Parsing Order Bug
- **Initial Attempt:** In `backend/app/parsing.py`, the initial implementation stripped whitespace and currency symbols before evaluating the trailing `\bDR\b` / `\bCR\b` regex. This compressed `"45.00 DR"` into `"45.00DR"`, causing regex boundary failures and returning `None`.
- **How It Was Caught:** Backend unit test `tests/test_parsing.py::test_parse_decimal_amount_formats` immediately caught the failure during `pytest` execution.
- **Correction:** Refactored `parse_decimal_amount` to extract and strip `\b(DR|CR)\b` case-insensitively *prior* to whitespace and currency symbol removal. The test subsequently passed.

### 2. Windows Installer Privileges (Exit Code 50)
- **Initial Attempt:** Attempted to install Python 3.11 via `winget install Python.Python.3.11`, which triggered an MSI Burn installer exit code 50 due to standard user elevation restrictions.
- **Correction:** Pivoted to Astral's standalone `uv` package manager (`uv python install 3.11`), successfully installing portable CPython 3.11.17 into the user profile without requiring administrator privileges.

### 3. Playwright Browser Driver Network Constraint
- **Initial Attempt:** Invoked browser subagent to execute automated Playwright UI tests against `http://localhost:5173/`. The agent encountered a `404 Not Found` when attempting to fetch external Playwright browser driver binaries from `azureedge.net` due to sandbox network restrictions.
- **Correction:** Recognized the environment constraint; validated end-to-end frontend-backend communication directly via the Vite reverse proxy (`http://localhost:5173/api/health`, `/api/statements/demo`, `/api/summary`) and curl HTTP requests.

---

## 4. Token Usage & Session Metrics

- **Session Context:** Advanced Agentic Pair Programming session in Antigravity IDE.
- **Model:** Gemini 3.8 Flash (Medium).
- **Estimated Token Volume:**
  - Prompt Tokens: ~45,000 tokens
  - Completion Tokens: ~12,000 tokens
- **Runtime Statement Brain:** **0 Tokens (Deterministic Python Code Only)**.

> **Candidate Note:** If submitting for assessment review, verify whether your Antigravity IDE dashboard or workspace logs expose exact token metrics or billing screenshots, and append any exported screenshots into the repository or PR description.

---

## 5. Certification of Deterministic Execution

I hereby certify that:
1. No OpenAI, Anthropic, Google Gemini, or other Large Language Model API is called during transaction categorization or runtime operation.
2. All category assignments, confidence scores, duplicate flags, and financial summaries are computed strictly through local deterministic Python code (`backend/app/categorizer.py`, `backend/app/parsing.py`, `backend/app/summaries.py`).
