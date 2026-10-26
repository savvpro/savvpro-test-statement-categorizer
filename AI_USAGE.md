# AI Usage

## Tools I Used

- **Claude (claude.ai)** — used it throughout, mainly for speeding up boilerplate and debugging

---

## How I Used It

**Getting started fast** — I used Claude to help set up the initial project structure (FastAPI + Next.js). Described what I was building and it gave me a skeleton to start from. Saved probably an hour of setup time.

**The categorizer brain** — This is the core of the app and where I spent the most time. I had the idea for the 3-stage pipeline (merchant lookup → regex → keyword scoring) myself, but used Claude to help me write out the regex patterns and the initial keyword weight table. Then I manually went through the sample CSV and tweaked the weights because the first pass was giving too many false positives for "Professional Services" - generic words like "service" and "payment" were matching everything. Adjusted those down.

**Parser edge cases** — I knew I needed to handle messy amount formats (dollar signs, commas, parentheses for negatives) and date format variations. Described the edge cases I'd seen and Claude helped write the parsing logic. I tested this against the sample data and it worked correctly.

**Frontend components** — Used Claude to scaffold the TransactionTable and FileUpload components, then customized the styling and logic myself. The confidence progress bar and the color-coding per category were my additions.

**Tests** — Claude generated a first draft of the test suite. I added several tests myself after running the suite and realizing some edge cases weren't covered - specifically the positive amount = refund case, the empty description case, and the OFX parser tests.

---

## Where It Got Things Wrong / What I Had to Fix

- **Uber Eats getting miscategorized as Travel** — The regex pattern `UBER\s*\*` was matching before the `UBER EATS` merchant lookup could fire. Fixed it by moving UBER EATS explicitly into the merchant map (so it hits stage 1 and never reaches the regex).

- **Apple Store going to Software** — The initial draft put Apple Store under Software & Subscriptions. But Apple Store visits are usually hardware purchases (MacBook, iPad etc.) so Office & Supplies is more correct. I corrected the merchant map entry and updated the test to match.

- **Confidence tuning** — The first version of the keyword scorer had `"service"` and `"payment"` weighted too high which was dragging scores toward Professional Services for random transactions. Lowered those weights, which then broke a few tests I had to fix.

- **CSV BOM character** — Didn't realize some bank CSV exports include a BOM (byte order mark) at the start that messes up header parsing. Claude missed this initially; I caught it when testing with a real export format and added `utf-8-sig` decoding to handle it.

---

## Token Usage (approximate)

Rough breakdown from the Claude usage dashboard:

| Phase | Approx. tokens |
|---|---|
| Project setup + architecture | ~6,000 |
| Categorizer brain + iteration | ~20,000 |
| Parser + edge case handling | ~8,000 |
| Frontend components | ~15,000 |
| Tests + debugging | ~10,000 |
| Docs | ~5,000 |
| **Total** | **~64,000** |

> The categorization decisions at runtime are 100% rule-based code — Claude was used to help write that code, not to make decisions when a user uploads a statement.
