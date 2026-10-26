# AI Usage Log — Statement Categorizer

> **Project:** Bank Statement Categorizer for Freelance Tech Consultants  
> **Candidate Branch:** `candidate-sikandarhussain6858`  
> **Evaluation Compliance:** Documents AI tools used, specific assistance provided, technical challenges/corrections encountered, and token usage estimates.

---

## 1. Compliance with the Core Assessment Rule

> **The One Big Rule:** *"The brain must be your own code. Do not use a big AI model (like GPT, Claude or Gemini) to decide a category. Your code decides what each transaction is and when it is not sure."*

### Affirmation of Compliance
- **Zero Runtime LLM Calls:** The classification engine in `backend/app/brain/` contains **no calls** to OpenAI, Anthropic, Gemini, or any other external AI model or LLM API.
- **Deterministic Python Execution:** All classification decisions, merchant string sanitization, direction analysis, and IRS Schedule C calculations run exclusively through deterministic Python rules (`rules.py`, `sanitizer.py`, `direction.py`, `classifier.py`, `tax_summary.py`).
- **Reproducible & Auditable:** Any statement uploaded produces identical, repeatable results with a traceable decision audit trail.

---

## 2. AI Tools Used

| Tool | Version / Model | Primary Purpose |
|---|---|---|
| **Google Antigravity** | Gemini 2.5 Pro / Flash | Architecture planning, feature decomposition, test suite generation, and React UI implementation |

---

## 3. How AI Assisted the Development Process

### 1. Architecture Planning & Feature Breakdown
- Decomposed the overall project into 7 modular, testable feature specifications stored in `.features/`:
  - Feature 1: Backend Domain Models & Brain Engine
  - Feature 2: Multi-Format CSV Parser & Sample Data
  - Feature 3: FastAPI REST Endpoints
  - Feature 4: Automated Pytest Suite (52 tests)
  - Feature 5: Frontend Scaffold & File Upload
  - Feature 6: Frosted Glass Dashboard, Review Table & Export
  - Feature 7: Documentation & Submission Readiness

### 2. Boilerplate & Rapid Prototyping
- Generated Pydantic v2 domain schemas (`Transaction`, `TaxSummary`, `RecalculateRequest`, `CategoryBreakdown`).
- Scaffolded FastAPI endpoints with multipart file upload and error handling.
- Wrote initial regex patterns for POS merchant prefix sanitization.

### 3. Comprehensive Test Generation
- Assisted in generating 52 unit and integration tests across 6 test modules (`test_sanitizer.py`, `test_direction.py`, `test_classifier.py`, `test_tax_summary.py`, `test_parser.py`, `test_api.py`), ensuring complete coverage of edge cases.

### 4. Custom Frosted Glass CSS System
- Created a bespoke frosted acrylic glassmorphism UI system in `index.css` (`backdrop-filter: blur(25px)`, radial ethereal gradient canvas, custom SVG arc gauge) matching the executive dashboard reference.

---

## 4. Where AI Got Things Wrong & How It Was Corrected

Honest technical documentation of mistakes, misunderstandings, and runtime errors encountered during pairing:

### 1. Windows PowerShell Command Chaining (`&&`)
- **What went wrong:** AI attempted to run commands chaining with bash-style `&&` (e.g., `cd backend && python -m uvicorn app.main:app`). In older Windows PowerShell environments, `&&` is not supported and threw parsing errors.
- **Correction:** Rewrote commands to use PowerShell-compatible syntax (semicolons or running in appropriate working directories).

### 2. Windows CP1252 Unicode Encoding Error
- **What went wrong:** When creating a Python test runner script to output test results, the script printed UTF-8 unicode checkmarks (`✓`). On Windows running with code page 1252, this caused `UnicodeEncodeError: 'charmap' codec can't encode character '\u2713'`.
- **Correction:** Replaced unicode checkmarks with standard ASCII tags `[PASS]` and `[FAIL]`, ensuring compatibility across all Windows terminal environments.

### 3. POS Sanitizer Regex Edge Cases
- **What went wrong:**
  1. The initial regex failed to strip airline ticket numbers (8 to 18 digits, e.g., `DELTA AIR 006245892184 ATLANTA GA`), leaving raw numbers in the sanitized merchant name.
  2. Passing an empty string or whitespace-only description resulted in an empty string `""` rather than a safe fallback key.
- **Correction:**
  - Added regex `\b\d{8,18}\b` to the noise removal pipeline.
  - Added explicit validation to return `"UNKNOWN"` whenever a sanitized merchant string is empty.

### 4. Unstyled Category Filter Tabs
- **What went wrong:** During initial implementation of the transaction table filters in `CategoryFilter.jsx`, CSS classes (`.filter-pill`, `.glass-filter-pill`) were referenced in JSX but omitted from `index.css`, resulting in raw unstyled HTML buttons.
- **Correction:** Redesigned the filter bar into frosted pill tabs with active indicator counts and a rounded category dropdown selector.

### 5. Upload Dropzone Card Alignment
- **What went wrong:** An early iteration of `FileUpload.jsx` used unstyled flex containers, which caused the upload icon to stretch into a horizontal purple bar and left-aligned the action buttons awkwardly.
- **Correction:** Re-engineered `.dropzone-container` with a floating circular icon badge, symmetric divider lines, and responsive center-aligned layout.

---

## 5. Estimated Token & Session Metrics

| Metric | Estimate |
|---|---|
| **Total Prompt Turns** | ~14 interactive turns |
| **Input Tokens (Context, Files, Specs)** | ~185,000 tokens |
| **Output Tokens (Code, Tests, Documentation)** | ~38,000 tokens |
| **Total Estimated Tokens** | ~223,000 tokens |
| **Runtime AI Calls During Statement Categorization** | **0 tokens (100% Deterministic Python)** |

---

## 6. Development Workflow Summary

```
1. Feature Spec (.features/) 
   └── Reviewed & Confirmed Requirements
2. Deterministic Brain Implementation 
   └── Built Pydantic models, rules engine, direction analyzer
3. Test-Driven Verification 
   └── Ran 52 pytest test cases (100% passing)
4. Interactive Frosted UI 
   └── Built React + Vite dashboard with real-time recalculation
5. End-to-End Validation 
   └── Verified sample statement (33 txns) and split columns (10 txns)
6. Comprehensive Documentation
   └── README.md, DESIGN.md, AI_USAGE.md
```
