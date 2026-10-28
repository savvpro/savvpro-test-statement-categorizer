# 02 — The Brain (categorization engine)

Hard rule: **no LLM / ML model decides anything.** Pure Python, deterministic: same input + same rules ⇒ same output. Written by the orchestrator (Opus), not delegated.

## 1. Contract

```python
def categorize(txns: Sequence[Transaction], ctx: BrainContext) -> list[Decision]
@dataclass(frozen=True)
class BrainContext:
    rules: RuleSet                       # from YAML
    memory: Mapping[str, Category]       # merchant_key → category (user corrections)
    prior_fingerprints: Mapping[str, str]# fingerprint → existing transaction id (other statements)
    ytd_by_counterparty: Mapping[str, int] # cents paid to individuals in prior statements (1099)
    settings: BrainSettings              # thresholds
```
No I/O inside. Services build the context.

## 2. Pipeline

```
for each txn:
   candidates = []
   S1 structural      (may short-circuit)
   S2 direction/channel
   S3 user memory
   S4 exact merchant
   S5 keyword/regex
   S6 fuzzy merchant
   flags = S7 policy(txn, candidates)
   decision = resolve(txn, candidates, flags)
cross-row passes (after all rows):
   X1 duplicates   X2 recurring boost   X3 1099 aggregate   X4 refund linking
   re-resolve rows whose candidates/flags changed
```

### S1 — Structural / non-P&L (patterns.yaml `structural`)
| rule_id | Match (on normalized description) | Direction | → Category | score |
|---|---|---|---|---|
| st.transfer | `\b(ONLINE )?TRANSFER (TO|FROM)\b`, `\bXFER\b`, `\bTO (SAVINGS|CHECKING)\b` | any | TRANSFER | 0.99 |
| st.card_payment.checking | `(CREDIT CARD|CARD) (PAYMENT|AUTOPAY)`, `\bAUTOPAY\b.*CARD` | outflow, checking | CARD_PAYMENT | 0.99 |
| st.card_payment.card | `PAYMENT (THANK YOU|RECEIVED)`, `AUTOPAY PAYMENT` | inflow, credit_card | CARD_PAYMENT | 0.99 |
| st.owner_contribution | `OWNER (CONTRIBUTION|DEPOSIT)` | inflow | OWNER_CONTRIBUTION | 0.97 |
| st.interest_earned | `INTEREST (PAID|EARNED|PAYMENT)` | inflow, checking | INTEREST_EARNED | 0.97 |
| st.nsf_return | `(RETURNED ITEM|NSF|RETURN(ED)? DEPOSIT|CHARGEBACK)` | outflow | RENT (reversal) + flag RENT_REVERSAL | 0.92 |
| st.bank_fee | `(SERVICE|MAINTENANCE|NSF|OVERDRAFT|WIRE) FEE`, `MONTHLY FEE` | outflow | OTHER_EXPENSE | 0.93 |
Short-circuit when score ≥ 0.97 (skip S3–S6, still run S7 + cross-row).

### S2 — Direction & channel
Uses `channel` (ZELLE/VENMO/ACH/CHECK/CARD/CASH_APP/WIRE) and `counterparty` from normalizer.
- Inflow + person-like counterparty (channel ∈ P2P/ACH credit, no business token like LLC/INC/CO) + memo/description has `RENT` → RENT 0.92.
- Same but memo has `DEPOSIT|SECURITY|SEC DEP` → SECURITY_DEPOSIT_RECEIVED 0.92 (and RENT 0.30 as second).
- Same without memo → RENT 0.70 (below threshold alone; recurring boost X2 can lift it).
- Inflow + memo `LATE FEE|PET (FEE|RENT)` → RENT 0.90.
- Outflow + P2P to person + memo `DEPOSIT (RETURN|REFUND)` → SECURITY_DEPOSIT_RETURNED 0.90.
- Outflow + P2P to person, no memo → no category candidate; flag PAYMENT_TO_INDIVIDUAL (→ review).
- Outflow `CHECK #\d+` → no candidate; flag CHECK_NO_PAYEE (→ review, cannot know payee).
- **Refund rule:** inflow on credit card or checking where merchant matches an *expense* rule in S4–S6 ⇒ keep that expense category, set `is_refund=True`, reason "Money returned by merchant — reduces <Category>, not income". Also triggered by tokens `REFUND|RETURN|CREDIT ADJ|REVERSAL` on inflow.

### S3 — User memory
`ctx.memory[merchant_key]` → candidate score 0.98, source `memory`, reason "You categorized <merchant> as X before". Direction compatibility still checked (memory for an outflow merchant doesn't apply to an inflow — becomes refund logic instead).

### S4 — Exact merchant dictionary (`merchants.yaml`)
Match if any alias is a whole-token prefix/substring of `merchant_key`.
```yaml
- id: m.insurance.fake_mutual
  aliases: ["HEARTHSTONE MUTUAL INS", "HEARTHSTONE INS"]
  category: INSURANCE
  score: 0.95
- id: m.mortgage.lender
  aliases: ["GRANITE HOME LENDING", "GRANITE MTG"]
  category: MORTGAGE_INTEREST
  score: 0.95
  flags: [MORTGAGE_SPLIT_REQUIRED]
```
Seed list (~60 entries, fictional or generic-public names): county treasurer/tax collector, water/sewer/trash utility, electric/gas utility, HOA management, landlord software (rent collection apps), listing sites (ADVERTISING), property managers (MANAGEMENT_FEES), law/CPA firms (LEGAL_PROFESSIONAL), hardware stores (REPAIRS score 0.80 — repairs vs supplies ambiguity handled by keyword + amount), cleaning services, pest control, locksmith, plumbing/HVAC/electrician businesses, gas stations (AUTO_TRAVEL 0.60 → review unless recurring), insurers, lenders.
Real big-brand merchant names are allowed as merchant strings in fake data (e.g. "HOME DEPOT", "AMAZON") — they are public businesses, not personal data.

### S5 — Keyword/regex (`keywords.yaml`)
```yaml
- id: kw.plumbing
  pattern: '\bPLUMB(ING|ER|ERS)?\b'
  category: REPAIRS
  weight: 0.80
  directions: [outflow]
```
~40 rules: PLUMB, HVAC, ROOF, ELECTRIC(IAN), PAINT, LOCKSMITH, PEST, LANDSCAP, LAWN, CLEANING, MAID, JANITOR, APPLIANCE, HOA, ASSOC, PROPERTY TAX, TREASURER, INSURANCE/INS, MORTGAGE/MTG/LOAN PMT, WATER, SEWER, TRASH, WASTE, ELECTRIC CO, GAS CO, POWER, UTIL, LEGAL, ATTORNEY, LAW, CPA, ACCOUNTING, TAX PREP, ADVERTIS, LISTING, PROPERTY MGMT, MGMT FEE, COMMISSION, LEASING FEE, FUEL, PARKING, TOLL, MILEAGE.
Multiple keyword hits for the same category combine by noisy-OR.

### S6 — Fuzzy merchant
`rapidfuzz.fuzz.token_set_ratio(merchant_key, alias)`; best alias ≥ `FUZZY_MIN_RATIO` (88) ⇒ score = rule.score × (ratio/100) × 0.92. Only runs if S4 had no hit. Reason includes the matched alias and ratio.

### S7 — Policy / blocking flags (force NEEDS_REVIEW)
| Flag | Condition | Why |
|---|---|---|
| MIXED_USE_MERCHANT | merchant_key matches `mixed_use.yaml` (AMAZON, WALMART, COSTCO, TARGET, PAYPAL generic, VENMO generic) and not in user memory | could be personal or business |
| POSSIBLE_CAPITAL_IMPROVEMENT | top category ∈ {REPAIRS, SUPPLIES, CLEANING_MAINTENANCE} and abs(amount) ≥ DE_MINIMIS (250000) | IRS de-minimis safe harbor: bigger may be an improvement |
| MORTGAGE_SPLIT_REQUIRED | merchant rule flag | statement can't show interest vs principal |
| PAYMENT_TO_INDIVIDUAL | S2 | contractor? personal? |
| CHECK_NO_PAYEE | S2 | |
| DIRECTION_CONFLICT | top category not allowed for direction and not a refund | e.g. inflow matched to UTILITIES without refund tokens |
| AMOUNT_OUTLIER | abs(amount) > 5 × median for that merchant_key in this statement (n ≥ 3) | unusual charge |
| UNKNOWN_MERCHANT | no candidates at all | |
| LOW_INFORMATION | description < 3 meaningful chars | |
| RENT_REVERSAL | S1 nsf | informational, not blocking |
| POSSIBLE_1099 | X3 | informational, not blocking |
| RECURRING | X2 | informational |
Blocking set: everything except RENT_REVERSAL, POSSIBLE_1099, RECURRING. Memory hits clear MIXED_USE_MERCHANT and PAYMENT_TO_INDIVIDUAL (user already decided that merchant/person).

### Resolver
1. Drop candidates whose category is not allowed for the txn direction, unless it's a refund (expense category on inflow with refund evidence) or RENT_REVERSAL.
2. Aggregate per category with **noisy-OR**: `p = 1 − Π(1 − s_i)`, capped 0.99. (Independent evidence agreeing raises confidence; one weak hit stays weak.)
3. `top`, `second` by p. `margin = top.p − second.p` (second.p=0 if none).
4. Status:
   - no candidates → NEEDS_REVIEW, category None, flag UNKNOWN_MERCHANT, confidence 0.
   - `top.p ≥ AUTO_THRESHOLD and margin ≥ MARGIN_THRESHOLD and no blocking flags` → AUTO, category=top.
   - else NEEDS_REVIEW, `suggestion=top.category`, `category=None` (excluded from totals until confirmed).
5. `confidence = round(top.p, 2)`; reasons = top candidate reasons + one line per flag (`explain.py` templates).

### Cross-row passes
- **X1 Duplicates**
  - OFX: same FITID within file → later one DUPLICATE.
  - Pending/posted: row with `is_pending` and a posted row with same amount & merchant_key within ±5 days → pending row DUPLICATE (`duplicate_of_row`).
  - Cross-upload: fingerprint ∈ `prior_fingerprints` → DUPLICATE (user can restore).
  - Fingerprint = sha256(`account_type|posted_date|amount_cents|merchant_key|occurrence_n`) where occurrence_n counts identical tuples in the same file ⇒ two genuine identical coffees in one file are NOT merged.
- **X2 Recurring** — group by (merchant_key or counterparty), ≥ 2 occurrences in distinct months with amounts within ±10% ⇒ add `+0.20` candidate (noisy-OR) to the group's current top category and flag RECURRING. Main purpose: monthly tenant Zelle without memo (0.70 → ≥0.85 ⇒ AUTO).
- **X3 1099** — sum outflows per counterparty (this statement + ctx.ytd) ≥ 60000 ⇒ POSSIBLE_1099 on those rows.
- **X4 Refund linking** — refund row linked to most recent prior outflow with same merchant_key (reason text "refund of <date> purchase").

## 3. Direction compatibility table (taxonomy)
| Kind / category | inflow | outflow |
|---|---|---|
| RENT | ✓ | only as RENT_REVERSAL |
| Expenses | only as refund | ✓ |
| SECURITY_DEPOSIT_RECEIVED | ✓ | ✗ |
| SECURITY_DEPOSIT_RETURNED | ✗ | ✓ |
| TRANSFER, CARD_PAYMENT | ✓ | ✓ |
| OWNER_CONTRIBUTION | ✓ | ✗ |
| OWNER_DRAW, PERSONAL, LOAN_PRINCIPAL, CAPITAL_IMPROVEMENT | ✗ (PERSONAL refund ✓) | ✓ |
| INTEREST_EARNED | ✓ | ✗ |

## 4. Rule file validation (fail fast at startup + unit test)
Pydantic models per file: unique ids, category ∈ enum, 0 < score ≤ 0.99, regex compiles, directions valid, no alias duplicated across categories (a duplicate alias is a config bug). Test `test_rules_integrity.py` loads the real files.

## 5. Explainability templates (`explain.py`)
- `merchant`: "Matched known merchant '{alias}' → {label}."
- `keyword`: "Description contains '{token}' → {label}."
- `fuzzy`: "Looks like '{alias}' ({ratio}% similar) → {label}."
- `memory`: "You previously marked '{merchant}' as {label}."
- flags: MIXED_USE → "Store sells both business and personal items — please confirm." CAPITAL → "Over ${limit}: may be a capital improvement (depreciated), not a repair." MORTGAGE → "Mortgage payments mix interest (deductible) and principal (not). Enter the split or confirm." etc.

## 6. Evaluation (`scripts/evaluate_brain.py`)
- For each `samples/*.{csv,ofx}` with sibling `*.expected.json` (`[{row_index, category|null, status}]`), run full ingest→brain (no DB).
- Metrics:
  - **auto_precision** = correct AUTO / total AUTO (gate: **1.00**).
  - **review_recall** = rows labeled must-review that got NEEDS_REVIEW (gate: **1.00**).
  - **coverage** = AUTO / non-duplicate rows (report; target ≥ 0.70).
  - suggestion accuracy on NEEDS_REVIEW rows (report).
  - confusion matrix (markdown).
- Output: markdown table to stdout and `--json` for CI; exit 1 on gate failure. Results pasted into DESIGN.md.

## 7. Tuning loop (during P3/P4)
Run evaluator → for each miss decide: rule bug, missing rule, or genuinely ambiguous (→ should be review, fix label rationale). Never tune thresholds to make a specific row pass; record each change in `docs/ai-log/phases.md`.

## 8. Known limits (documented in DESIGN.md)
No per-property allocation (P2), no mileage, no depreciation schedules, US Schedule E only, English descriptions, single currency per statement (foreign fee rows detected by `FOREIGN TRANSACTION FEE` → OTHER_EXPENSE).
