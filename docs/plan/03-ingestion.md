# 03 — Ingestion & Normalization

## 1. Format detection (`ingest/detect.py`)
Order:
1. Reject if empty, or > MAX_UPLOAD_BYTES (already enforced while streaming).
2. Extension allowlist: `.csv`, `.txt` (csv), `.ofx`, `.qfx`. Anything else → 415.
3. Content sniff on first 4 KB:
   - Contains NUL bytes or known binary magic (PK, %PDF, MZ, \x89PNG) → 415.
   - Starts with `OFXHEADER:` or contains `<OFX>` (case-insensitive) → OFX.
   - Else must decode as text (see §2) → CSV.
4. Extension/content disagreement (e.g. `.csv` but OFX content) → trust content, add warning `EXTENSION_MISMATCH`.

## 2. Decoding
Try in order: `utf-8-sig` (strips BOM) → `utf-8` → `cp1252` → `latin-1` (always succeeds; add warning `ENCODING_FALLBACK`). Normalize newlines (`\r\n`, `\r` → `\n`). Unicode NFKC.

## 3. CSV reader (`ingest/csv_reader.py`)
1. **Delimiter**: `csv.Sniffer().sniff(sample, delimiters=",;\t|")`; fallback by counting candidates in the first 10 non-empty lines (most consistent count wins).
2. **Header row**: scan first 25 rows; header = first row with ≥ 2 cells matching synonyms below (case/space/punct-insensitive). Rows before it = preamble (ignored, warning `PREAMBLE_SKIPPED`). No header found → 422 `NO_HEADER` with hint listing expected names.
3. **Column mapping** (synonyms):
   - date: date, posted date, posting date, transaction date, trans date, post date, value date
   - description: description, payee, merchant, name, details, transaction description, narrative
   - memo: memo, notes, reference, additional info
   - amount: amount, transaction amount, amount (usd), value
   - debit: debit, withdrawal, withdrawals, money out, paid out, charges
   - credit: credit, deposit, deposits, money in, paid in, payments
   - type: type, transaction type, dr/cr, debit/credit
   - status: status (values containing PENDING → is_pending)
   Required: date + description + (amount OR debit/credit). Missing → 422 with which ones.
   If both `date` synonyms appear (posted + transaction date), prefer posted.
4. **Rows**: skip blank rows; skip footer/summary rows (description matches `^(TOTAL|ENDING BALANCE|BEGINNING BALANCE|OPENING BALANCE|CLOSING BALANCE)` or date cell empty and amount present) → warning `SUMMARY_ROW_SKIPPED`. Row with wrong cell count → keep if required cells present, else warning `MALFORMED_ROW` (row skipped, row_index reported). > MAX_ROWS → 422.
5. Every row becomes `RawTransaction` with `row_index` = 1-based data row number in the original file (so users can find it).
6. Partial failure policy: if ≤ 5% rows fail to parse → continue with warnings; > 5% → 422 listing first 20 row errors (better to refuse than half-import silently).

## 4. Amount parsing (`ingest/amounts.py`) → Decimal → cents
Accept: `1234.56`, `1,234.56`, `-45.00`, `(45.00)`, `$45.00`, `-$45.00`, `$-45.00`, `45.00-`, `45.00 CR`, `45.00 DR`, `USD 45.00`, unicode minus `−`, spaces/nbsp as thousands separators.
- European `1.234,56` only if the whole column consistently uses comma decimals (column-level detection) → warning `DECIMAL_COMMA`.
- Debit/credit columns: amount = credit − debit (both may be empty → row error; both non-zero → error `BOTH_DEBIT_CREDIT`).
- Type column `DR/DEBIT` forces negative, `CR/CREDIT` positive (when amount unsigned).
- Quantize to 0.01 with ROUND_HALF_EVEN; >2 decimals → warning.
- Zero amount → kept, flagged by brain as LOW_INFORMATION? No — zero-amount rows (authorization holds) → excluded as DUPLICATE-like status? Decision: keep, status NEEDS_REVIEW with flag `ZERO_AMOUNT` (cheap, honest).

## 5. Date parsing (`ingest/dates.py`) — column-level inference
Candidate formats: `%m/%d/%Y %m/%d/%y %d/%m/%Y %d/%m/%y %Y-%m-%d %Y/%m/%d %d-%b-%Y %b %d, %Y %d %b %Y %m-%d-%Y %Y%m%d`.
Pick the format that parses **every** non-empty date in the column. If both MDY and DMY parse all rows (all days ≤ 12) → choose MDY (US landlord), statement warning `AMBIGUOUS_DATE_ORDER`. If none parses all → choose the one parsing most, failing rows become row errors.
Sanity: date > today + 7 days → warning `FUTURE_DATE` on that row; year < 2000 → row error.
OFX dates: `YYYYMMDD[HHMMSS[.XXX]][[+-]TZ[:name]]` → take date part.

## 6. OFX reader (`ingest/ofx_reader.py`) — own, minimal, safe
- **v2 (XML)**: header `<?xml` / `<?OFX` → parse with `defusedxml.ElementTree.fromstring` (forbids DTD, entities, external refs). Any `DTDForbidden/EntitiesForbidden` → 422 `UNSAFE_XML`.
- **v1 (SGML)**: strip header lines until `<OFX>`; tokenizer regex `<(/?)([A-Z0-9.]+)>([^<]*)` builds a tree; leaf elements have no close tag (value = text until next tag). No entity expansion at all (only `&amp; &lt; &gt;` literal replace).
- Extract: `ACCTTYPE` (CHECKING/SAVINGS/CREDITLINE; CREDITCARDMSGSRSV1 ⇒ credit card) → compared with user's `account_type` (mismatch ⇒ warning, user choice wins), `CURDEF`, each `STMTTRN`: TRNTYPE, DTPOSTED, TRNAMT, FITID, NAME, MEMO, CHECKNUM, PAYEE/NAME.
- OFX `TRNAMT` sign is already from account holder perspective for bank; for credit cards negative = charge ⇒ consistent with our convention (+inflow/−outflow). No inversion.
- NAME missing → use MEMO; both missing → TRNTYPE as description + LOW_INFORMATION.
- Limits: max 20k STMTTRN, max depth 32, max token count.

## 7. Normalization (`normalize/normalizer.py`)
1. **Sign convention** → `amount_cents` signed + inflow / − outflow.
   - Checking: as parsed.
   - Credit card CSV: detect convention: if ≥ 60% of non-payment rows are positive and rows matching card-payment patterns are negative → "charges positive" ⇒ invert all. Ambiguous ⇒ assume charges positive for credit_card (most common) + warning `CARD_SIGN_ASSUMED`.
2. `direction` from sign.
3. `description` = cleaned original (whitespace collapsed, kept for display); `memo` likewise.
4. `merchant_key`, `channel`, `counterparty` via `normalize/merchant.py` (§8).
5. `is_pending` from status column or `PENDING` token.
6. `fingerprint` (see 02-brain X1).

## 8. Merchant cleaning (`normalize/merchant.py`) — ordered, each step unit-tested
1. Uppercase, NFKC, replace `’'"` → removed, `&` → ` AND `, other punctuation → space (keep `*`, `#` until steps below).
2. **Channel extraction** (before stripping):
   - `ZELLE (PAYMENT )?(FROM|TO) (?P<cp>.+?)( CONF.*| REF.*| ID.*)?$` → channel ZELLE, counterparty.
   - `VENMO`, `CASH APP|SQC\*CASH APP`, `PAYPAL \*(?P<cp>\w+)` similar.
   - `ACH (DEBIT|CREDIT)`, `DIRECT DEP(OSIT)?`, `CHECK #?\d+` → CHECK, `WIRE (IN|OUT)`.
   - `POS (DEBIT|PURCHASE)`, `DEBIT CARD PURCHASE`, `CHECKCARD \d{4}`, `PURCHASE AUTHORIZED ON \d\d/\d\d` → CARD.
3. **Prefix strip**: `^(SQ|TST|SP|PY|PP|IN|DD|BT|EB|FS|PAYPAL|GOOGLE|APL\*?|AMZN MKTP)\s*\*\s*` and channel phrases above.
4. **Noise strip**: card masks `X{2,}\d{2,4}`, `\*\d{4}`; reference ids `(REF|CONF|ID|TRACE|AUTH)[#:]?\s*\w+`; store numbers `#\s*\d+` and standalone tokens with ≥ 4 digits; phone numbers; URLs/domains (`\w+\.(COM|NET|ORG)`); dates `\d\d/\d\d`.
5. **Location strip**: trailing `(\s[A-Z]{2})$` if it's a US state code, plus the preceding single city token if the remaining key is ≥ 2 tokens.
6. Collapse spaces, trim, cap 128 chars. Empty → `UNKNOWN`.
7. Person-like counterparty check: 2–3 alpha tokens, none in business-token list (LLC INC CO CORP LTD SERVICES PLUMBING …).
Examples (become tests):
| raw | merchant_key | channel | counterparty |
|---|---|---|---|
| `SQ *JOES CAFE 9921 SEATTLE WA` | `JOES CAFE` | CARD | – |
| `ZELLE FROM MARIA K LOPEZ CONF# 88H2` | `ZELLE MARIA K LOPEZ` | ZELLE | `MARIA K LOPEZ` |
| `POS DEBIT HOME DEPOT #4410 TACOMA WA` | `HOME DEPOT` | CARD | – |
| `AMZN MKTP US*2K4T81` | `AMAZON` (alias map AMZN→AMAZON) | CARD | – |
| `CHECK #1042` | `CHECK` | CHECK | – |
A small alias map (`AMZN→AMAZON`, `WM SUPERCENTER→WALMART`, `THE HOME DEPOT→HOME DEPOT`, `LOWES #→LOWES`) lives in `patterns.yaml`.

## 9. Output guarantees (property-tested)
- `normalize` is total: never raises for any RawTransaction that passed parsing.
- `merchant_key` idempotent: `clean(clean(x)) == clean(x)`.
- Sum of `amount_cents` equals sum of parsed Decimal × 100 (no money lost).
