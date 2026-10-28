# 04 — Edge-Case Catalog & Fake Data

Every case has an ID, a fixture row, an expected outcome, and a test. IDs are referenced in test names (`test_EC_D03_refund_not_income`) and in DESIGN.md.

## 1. Catalog

### P — Parsing (ingest)
| ID | Case | Expected |
|---|---|---|
| P01 | UTF-8 BOM | parsed, no warning |
| P02 | cp1252 file with `é` / `’` | parsed, ENCODING_FALLBACK only if utf-8 fails |
| P03 | `;` delimiter, decimal comma | parsed, DECIMAL_COMMA warning |
| P04 | 3 preamble lines before header | PREAMBLE_SKIPPED |
| P05 | Footer "Ending Balance" row | SUMMARY_ROW_SKIPPED |
| P06 | Blank lines in middle | ignored |
| P07 | Quoted description with comma | single field |
| P08 | Separate Debit/Credit columns | signed correctly |
| P09 | `(45.00)`, `45.00 CR`, `$-45.00`, `1,234.56`, `−45` | correct cents |
| P10 | All dates ≤ 12th | AMBIGUOUS_DATE_ORDER, MDY |
| P11 | DMY with a 25th | DMY chosen, no warning |
| P12 | Credit card CSV, charges positive | inverted |
| P13 | Credit card CSV, charges negative | not inverted |
| P14 | Missing amount column | 422 listing missing |
| P15 | 3 malformed rows of 100 | warnings, 97 rows |
| P16 | 30% malformed | 422 |
| P17 | OFX 1.x SGML (no closing tags) | parsed |
| P18 | OFX 2.x XML | parsed |
| P19 | OFX duplicate FITID | second DUPLICATE |
| P20 | OFX without NAME (MEMO only) | memo used |
| P21 | `.csv` extension containing OFX | parsed as OFX, EXTENSION_MISMATCH |
| P22 | CRLF line endings | parsed |
| P23 | Pending + posted pair | pending DUPLICATE |
| P24 | Zero-amount authorization | NEEDS_REVIEW ZERO_AMOUNT |
| P25 | Future date | FUTURE_DATE warning |

### D — Domain (landlord brain)
| ID | Case | Expected category / status |
|---|---|---|
| D01 | Zelle from tenant, memo "rent march" | RENT / auto |
| D02 | Zelle from tenant, no memo, monthly x3 | RENT / auto (recurring) |
| D03 | Zelle from tenant, no memo, once | suggestion RENT / review |
| D04 | Zelle from tenant memo "security deposit" | SECURITY_DEPOSIT_RECEIVED / auto |
| D05 | Inflow ≈ 2× usual rent from same tenant | review (AMOUNT_OUTLIER) |
| D06 | Late fee payment | RENT / auto |
| D07 | Deposit returned to ex-tenant (memo) | SECURITY_DEPOSIT_RETURNED / auto |
| D08 | Returned item / NSF on tenant payment | RENT reversal (negative) / auto, RENT_REVERSAL |
| D09 | NSF fee charged by bank | OTHER_EXPENSE / auto |
| D10 | Home Depot $84.12 | REPAIRS / auto |
| D11 | Home Depot $3,412.00 | suggestion REPAIRS / review POSSIBLE_CAPITAL_IMPROVEMENT |
| D12 | Home Depot refund +$42.10 | REPAIRS, is_refund / auto (reduces repairs) |
| D13 | Amazon $56.20 | review MIXED_USE_MERCHANT |
| D14 | Walmart, Costco, Target | review MIXED_USE_MERCHANT |
| D15 | Mortgage payment to lender | suggestion MORTGAGE_INTEREST / review MORTGAGE_SPLIT_REQUIRED |
| D16 | County treasurer property tax | TAXES / auto |
| D17 | Landlord insurance premium | INSURANCE / auto |
| D18 | Water/sewer, trash, electric for vacant unit | UTILITIES / auto |
| D19 | HOA dues | OTHER_EXPENSE / auto |
| D20 | Property management fee | MANAGEMENT_FEES / auto |
| D21 | Listing site ad | ADVERTISING / auto |
| D22 | CPA / attorney | LEGAL_PROFESSIONAL / auto |
| D23 | Plumber business card payment | REPAIRS / auto |
| D24 | Zelle to individual, no memo | review PAYMENT_TO_INDIVIDUAL |
| D25 | Zelle to same individual totaling ≥ $600 | review + POSSIBLE_1099 |
| D26 | Check #1042 | review CHECK_NO_PAYEE |
| D27 | Transfer to savings | TRANSFER / auto (excluded) |
| D28 | Transfer from savings | TRANSFER / auto |
| D29 | Credit card autopay from checking | CARD_PAYMENT / auto |
| D30 | "PAYMENT THANK YOU" on card | CARD_PAYMENT / auto |
| D31 | Interest earned on checking | INTEREST_EARNED / auto |
| D32 | Monthly maintenance fee | OTHER_EXPENSE / auto |
| D33 | Gas station | review (AUTO_TRAVEL suggestion, low score) |
| D34 | Totally unknown merchant `JOES CAFE` | review UNKNOWN_MERCHANT |
| D35 | Typo merchant `HOEM DEPOT` | REPAIRS via fuzzy, auto if ≥ threshold else review |
| D36 | Inflow from utility without refund token | review DIRECTION_CONFLICT |
| D37 | Foreign transaction fee | OTHER_EXPENSE / auto |
| D38 | Owner contribution deposit | OWNER_CONTRIBUTION / auto |
| D39 | Same coffee twice same day same amount (genuine) | both kept, not duplicate |
| D40 | Same statement uploaded twice | 409 (identical file) |
| D41 | Overlapping second statement | overlapping rows DUPLICATE (cross-upload) |
| D42 | User marks JOES CAFE as PERSONAL + remember; new upload | PERSONAL / auto via memory |
| D43 | Description is `=HYPERLINK("http://x")` | treated as text; escaped in export |
| D44 | Description empty | review LOW_INFORMATION |

### S — Security / abuse (see 05-security)
S01 6 MB file → 413 · S02 `.exe` renamed `.csv` (MZ magic) → 415 · S03 PDF → 415 · S04 OFX with DOCTYPE/ENTITY (XXE) → 422 UNSAFE_XML · S05 billion-laughs → 422 · S06 25k rows → 422 · S07 path traversal filename `../../etc/passwd.csv` → stored as `passwd.csv` · S08 formula payloads in every cell → escaped on export · S09 very long description (10k chars) → truncated to 512 for storage, warning · S10 deeply nested OFX → 422.

## 2. Fake data (`scripts/generate_samples.py`)

Deterministic (`random.seed(2026)`, Faker seeded) so CI is stable. Fictional names only: banks "Evergreen Community Bank", "Summit Rewards Card"; lender "Granite Home Lending"; insurer "Hearthstone Mutual"; tenants generated by Faker (`en_US`), addresses fake. Public retailer names (Home Depot, Amazon…) used as merchants only.

Persona: **"Dana Reyes"** (fake), owns 2 rentals (12 Alder Ln Unit A/B — fake), tenants 3 (fake), Jan–Mar 2026.

Files (each with `*.expected.json` labels: `{row_index, category, status, flags_contains[]}`):
| File | Content | Covers |
|---|---|---|
| `checking_q1_2026.csv` | 3 months business checking, standard signed-amount layout | D01–D09, D16–D32, D37–D39 |
| `card_q1_2026.csv` | credit card, charges positive, Debit/Credit cols variant | P08, P12, D10–D14, D23, D30, D33–D36 |
| `checking_messy.csv` | BOM, preamble, footer, `;`, decimal comma, ambiguous dates, malformed rows | P01–P11, P15, P22, P24, P25 |
| `checking_q1_2026.ofx` | OFX 1.x SGML | P17, P19, P20 |
| `card_q1_2026_v2.ofx` | OFX 2.x XML | P18 |
| `checking_overlap_feb_apr.csv` | overlaps Q1 file | D41 |
| `malicious/*.ofx|csv` | S-cases (tests only, not shown in UI) | S01–S10 |
Generator also writes `samples/README.md` (what each file demonstrates). Labels are **hand-reviewed** by orchestrator — labels define truth, so they're not blindly generated.

The UI "Try a sample" button serves `checking_q1_2026.csv` and `card_q1_2026.csv` from `frontend/public/samples/` (copied at build).
