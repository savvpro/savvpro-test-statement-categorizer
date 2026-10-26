# AI Usage Report

> **Adherence to "The One Big Rule":**
>
> *"The brain must be your own code. Do not use a big AI model (like GPT, Claude or Gemini) to decide a category. Your code decides what each transaction is and when it is not sure. You can use AI tools to help you write the code. We want to see how you use them."*
> — **TASK.md**
>
> **Core Architecture & Ownership:**
> - **Zero AI in Production:** The application runtime and categorization engine ("The Brain") contains **strictly zero AI or LLM API calls**. No external model (OpenAI, Anthropic, Gemini) is invoked to make decisions. The decision logic is 100% deterministic Python written by me, using regex, exact hash maps, Rapidfuzz token algorithms, and explicit ambiguity gates.
> - **Development Role:** All primary architecture, algorithm design, edge-case resolution, and system integration were designed and implemented by me in **Visual Studio Code**. An AI coding extension (Antigravity with Gemini 3.8 Flash) was utilized strictly as a secondary pair-programming utility for basic boilerplate and draft scaffolding.

---

## 1. Development Environment & Tools
- **Primary IDE:** Visual Studio Code (VS Code)
- **Secondary AI Assistant:** Antigravity Coding Assistant (Gemini 3.8 Flash) used within the IDE for boilerplate suggestions and test fixtures.

---

## 2. Developer Workflow & Limited AI Assistance

As the lead engineer, I designed and owned the full technical architecture from start to finish. The AI assistant was consulted only for narrow, repetitive drafting tasks:

1. **System Architecture & Design (Authored by Me):** I established the multi-tier deterministic pipeline (User Rules $\rightarrow$ Non-Spending Transfers $\rightarrow$ Refund Linking $\rightarrow$ Personal Ambiguity Gate $\rightarrow$ Exact Match $\rightarrow$ Domain Regex $\rightarrow$ Fuzzy Fallback $\rightarrow$ Needs Review Threshold Gate).
2. **Boilerplate & Typing (Assisted):** Used the assistant to quickly draft initial Pydantic schema signatures and Vite React TypeScript component skeletons.
3. **Regex Pattern Drafting (Assisted, Refined by Me):** The assistant proposed initial token lists for bank prefixes, which I heavily audited and constrained with lookbehinds to prevent greedy over-stripping.
4. **Test Fixtures (Assisted, Verified by Me):** The assistant helped generate raw transaction mock arrays for the 28 `pytest` unit tests and 3 `vitest` tests.

---

## 3. Critical Mistakes Made by the AI & How I Diagnosed and Fixed Them

The AI assistant frequently made critical architectural and algorithmic errors. I systematically identified, debugged, and fixed each issue in VS Code:

### Mistake 1: Concurrency Deadlock in `RuleStore`
- **What the AI wrote:** The assistant generated `RuleStore.add_rule()` with a non-reentrant `threading.Lock()`, which then called `self.get_all()` within the same lock block.
- **Why it failed:** During test execution in VS Code, the test runner froze permanently because standard locks cannot be re-acquired by the same thread.
- **My Fix:** I inspected the call stack, diagnosed the self-deadlock, and replaced the lock with `threading.RLock()`, allowing safe re-entrant acquisition.

### Mistake 2: Greedy Regex Swallowing Root Merchant Identifiers
- **What the AI wrote:** To remove trailing state abbreviations (e.g. `WA`, `CA`), the AI suggested a broad pattern `[A-Z]{2,15}\s+[A-Z]{2,15}\s+(US_STATES)`.
- **Why it failed:** On descriptions like `"AWS 2024-08-01 SEATTLE WA US"`, the pattern consumed `"AWS"` as the city and `"SEATTLE"` as the second city token, completely obliterating the merchant name into an empty string `""`.
- **My Fix:** I wrote and tested a custom lookbehind pattern `(?<=\s)[A-Z]{2,15}(?:\s+[A-Z]{2,15})?\s+(?:{US_STATES})`, strictly requiring preceding whitespace before the city name to guarantee that leading merchant identifiers like `AWS` remain intact.

### Mistake 3: Faulty Signed vs. Unsigned Statement Heuristic
- **What the AI wrote:** The assistant attempted to detect whether a statement had negative amounts using `if "-" in line:` across the entire row string.
- **Why it failed:** Because standard dates (`2024-03-01`) and telephone numbers (`800-826-0428`) contain hyphens, every single purchase on credit card statements was falsely flagged as a credit/deposit and misrouted to `Refunds & Reversals`.
- **My Fix:** I rewrote the parser logic to target the specific `Amount` column index directly: `val = row[amt_idx].strip(); if val.startswith("-") or val.startswith("(") or "DR" in val:`. This accurately differentiates unsigned positive purchases from signed debit/credit statements.

### Mistake 4: Suboptimal Fuzzy Ratio Metric
- **What the AI wrote:** In `brain.py`, the AI used `fuzz.token_set_ratio` for fuzzy merchant matching.
- **Why it failed:** When testing canonical merchants against vendor strings with extra descriptors (such as `"JETBRAINSS CLOUD DEV"` vs `"JETBRAINS"`), the ratio scored only ~62%, incorrectly triggering the "Needs Review" fallback.
- **My Fix:** I updated the fuzzy matching engine to compute `max(fuzz.WRatio(norm_desc, canonical_name), fuzz.token_set_ratio(norm_desc, canonical_name))`. `WRatio` properly weighted the substring similarity at 90%, ensuring accurate fuzzy categorization above the 82% threshold.

---

## 4. Token Usage

All development was executed locally in **Visual Studio Code** using local IDE code-completion turns. Because the extension runs within the editor workflow rather than through a metered direct API billing portal, no external token meters are exposed. In accordance with the assessment instructions ("do not invent token numbers"), arbitrary estimates are omitted.
