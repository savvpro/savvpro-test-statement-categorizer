# Design

## Use case

**A freelance designer sorting a business credit card or bank statement for tax time.**
They pay for software (Adobe, Figma), hosting, travel, coworking and the odd client lunch,
and their personal spending sometimes lands on the same card. At the end of the year they
need a total per tax category, and they need to trust it. A wrong total is worse than a
total with a list of "please check these" rows, so the design principle is:

> **Decide only when there is evidence. Otherwise say so and ask.**

The categories (`backend/app/brain/categories.py`) carry a *kind*, which is what the rest
of the system relies on:

| Kind | Examples | Counts as spending? |
|---|---|---|
| `expense` | Software, Hosting, Travel, Meals (partly deductible), Office, Marketing, Professional services, Phone, Education, Rent and coworking, Insurance, Taxes and licences, Bank fees, Personal (not deductible) | Yes |
| `non_spending` | Transfer between own accounts, Card payment | No |
| `income` | Client income | No |
| `review` | Needs Review | Not decided |

## Pipeline

```
file -> detect real format -> reader -> raw rows -> sign convention -> brain -> transactions
                                                                       |
                                  refund matching, duplicate flags, thresholds, summary
```

Everything after "reader" is format independent. Each reader (CSV, Excel, PDF, OFX,
ISO 20022 camt.053, SWIFT MT940) returns the same `ParsedStatement`: rows with a date,
description and either a signed amount or explicit debit and credit, plus rejected lines
with reasons and warnings. Adding a format means adding one reader.

## The brain

The brain is `backend/app/brain/` and it is ordinary code. No AI model decides anything.
For one transaction `Classifier.classify` works down this list and stops at the first
level that has evidence:

| # | Evidence | Result |
|---|---|---|
| 1 | A rule the user saved by correcting an earlier row (same merchant key) | That category, confidence 1.0 |
| 2 | Structure of the line: card payment, transfer between own accounts, fee or interest, client payout or invoice | `non_spending`, `income` or `Bank fees`, confidence 0.85 to 0.95 |
| 3 | A known merchant phrase (`ADOBE`, `UBER EATS`, `AMAZON WEB SERVICES`...). The **longest matching phrase wins**, so `UBER EATS` beats `UBER` and `AWS` beats the ambiguous `AMAZON` | That category, confidence from the rule (0.85 to 0.96) |
| 4 | An ambiguous merchant (Amazon, PayPal, Zelle, fuel stations, ATM, Apple, Google, IRS...) | **Needs Review**, with the plausible categories offered as suggestions |
| 5 | A weak keyword (`CAFE`, `HOTEL`, `PRINTING`...) | **Needs Review** with one suggestion, confidence about 0.55 |
| 6 | Nothing | **Needs Review**, "merchant is not recognised" |

Rules live in `backend/app/brain/data/merchants.json` (brands, ambiguous merchants,
keywords). They are data, validated on load against the category list, and extending
them needs no code change. Descriptions are first normalized (`normalize.py`): processor
prefixes like `SQ *` and `PAYPAL *` are dropped, reference numbers, store numbers and
masked card numbers removed, accents folded, trailing city and state codes trimmed. So
`SQ *JOES CAFE 9921 SAN JOSE CA` and `JOES CAFE #0042` share the merchant key
`JOES CAFE`, which is also what refund matching and learning use.

**Confidence and the threshold.** Every decision has a confidence and a list of
human-readable reasons. Anything below `SC_REVIEW_THRESHOLD` (0.75) is not decided: it is
shown as Needs Review and keeps its best guess as a suggestion. The user always sees why:
"Known merchant 'ADOBE': Software & Subscriptions", or "'AMZN MKTP' is ambiguous: could be
Office Supplies or Personal or Software. Amazon sells everything, so the category depends on
what was bought."

**Determinism.** The same file always produces the same output. There is no randomness,
no network call and no learned model in the decision path, so a result can be explained and
tested line by line.

## Messy real-world cases

| Case | What the app does |
|---|---|
| Refund | Money back is **not income**. It is matched to the earlier purchase from the same merchant (equal or larger amount, not dated before it, exact amount preferred), inherits that category and reduces its total. Partial refunds work. If the purchase is not in the file but the merchant is known, the merchant's category is used with confidence capped at 0.8 and an `unmatched_refund` flag. If the merchant is unknown it goes to review. |
| Unknown money in | Never labelled income without evidence (invoice, payout, client). A bare `DEPOSIT` asks. |
| Card payment and transfers | `ONLINE PAYMENT - THANK YOU` and `TRANSFER TO SAVINGS` are excluded from spending. `TRANSFER TO JOHN SMITH` is not assumed to be an own-account transfer, so it asks. |
| Ambiguous merchants | Always ask, with suggestions. Income-tax payments (IRS) are flagged as not a business expense. |
| Which sign is spending? | Banks disagree. For a single signed column the app looks at payment, refund and deposit lines (their sign is the inflow sign), then at the majority sign, and warns when it had to guess. The user can override it. Debit/credit columns, `CR`/`DR` suffixes, OFX, camt.053, MT940 and verified running balances state direction explicitly and skip the guess. |
| Duplicates | Same date, merchant and amount more than once: flagged `possible_duplicate`, not dropped (two coffees are legitimate). |
| Foreign currency | A row in another currency than the statement is never totalled blindly. It goes to review with a note that it was not converted. |
| Large amounts | Flagged for a second look but still categorized. |
| Bad lines | Unreadable dates or amounts, zero amounts, balance and total lines are rejected individually with a reason and shown to the user. One bad line never loses the file. |
| Ambiguous dates | `03/04/2026` is resolved from the whole column (any value above 12 settles it) and a warning is shown when nothing can. |

## Learning from corrections

When the user fixes a row they can tick "apply to similar transactions". All rows in the
statement with the same merchant key are updated and the rule is saved (`var/user_rules.json`),
so the next statement already knows it. Rule priority is highest in the brain, and saved
rules naming a category that no longer exists are ignored. A refund follows the purchase it
reverses when that purchase is corrected.

## Input handling and limits

- **Detection by content**, not name: PDF, Excel (and a zip that is not a workbook), OFX,
  camt.053 and MT940 are recognised from their bytes. A misnamed file is read correctly with
  a warning, an unsupported or binary file is refused with a clear message.
- **CSV tolerance:** BOM, UTF-8, UTF-16 and Windows-1252, delimiter sniffing, preamble
  lines, `sep=` hints, quoted fields, localised headers (English, German, French, Spanish,
  Dutch), thousands and decimal separators in both styles, `(12.50)` and `12.50-` negatives.
- **PDF:** tables are read when the statement has them, otherwise lines are rebuilt from
  word positions. Rotated watermark text is filtered out, wrapped descriptions are merged
  into one row, and a running balance, when present, is used to decide whether each amount
  is money in or out. A PDF with no text layer (a scan) is rejected with advice to export a
  CSV, because OCR is out of scope.
- **Caps:** upload size (5 MB), rows (5000), PDF pages (40), all configurable. Oversized
  bodies are refused before they are buffered. Excel files that expand beyond 60 MB are
  refused as zip bombs. XML with a `DOCTYPE` or entity declaration is refused before parsing.
- **Rate limiting:** a per-client sliding window, tight for uploads (10 per minute) and
  looser for everything else (120 per minute), answering HTTP 429 with `Retry-After`. The
  client address can be taken from `X-Forwarded-For` only when explicitly configured.
- **Errors** are always `{"detail": {"code", "message"}}` with a stable code per problem
  (`file_too_large`, `pdf_encrypted`, `pdf_no_text`, `missing_columns`, `rate_limited`...),
  so the UI can show a precise message.
- **Export safety:** cells that start with `=`, `+`, `-` or `@` are prefixed so a spreadsheet
  cannot run them.
- **Privacy:** parsed statements are held in memory only (bounded, oldest evicted) and the
  app never writes them to disk or logs their contents. The only thing saved to disk is
  the small file of merchant rules the user taught it. (The web framework may spool a large
  upload to a temporary file while the request is being received.)

## Structure

```
api/        thin FastAPI routes and pydantic response models
services/   upload and correction use-cases (the only place that knows the whole flow)
parsing/    one reader per format, shared tabular, date and amount logic
brain/      categories, normalizer, rules, classifier, direction, pipeline (refunds, duplicates)
storage/    StatementRepository protocol with an in-memory implementation, UserRuleStore
middleware  body limit, rate limit, security headers
```

Money is `Decimal` internally and rounded to cents. Domain objects are frozen dataclasses,
the API layer maps them to pydantic models, and settings come from environment variables.

## Testing

- Unit tests for amounts, dates, normalization, the classifier (including every ambiguous
  and edge case above), refunds, conventions, duplicates, thresholds and storage.
- Reader tests for each format, including every kind of broken file.
- API tests for each format end to end, every error code, caps, rate limits, CORS,
  corrections, rule persistence across a restart and export injection.
- **Real-world data:** the parsers are run against files published by others (all synthetic apart from one real council open-data CSV, explained in its README), listed in
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md): a council purchase-card export,
  OFX fixtures from an open-source library, eight synthetic multi-country bank statement PDFs
  with known transaction counts, and the official ISO 20022 and MT940 samples from a
  bank (balance reconciliation is asserted exactly).

## Known limits and what comes next

- Merchant rules cover common services, not every merchant. Unknown ones are asked about
  rather than guessed, and the saved rules make the second statement better than the first.
- The rule set is built for one persona. Another persona (a rideshare driver, an online
  seller) is a new category list and rule file.
- No OCR for scanned statements, no currency conversion, no multi-user accounts. Statements
  are in memory, behind an interface that a database can implement.
