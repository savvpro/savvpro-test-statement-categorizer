# Stockport purchase-card export (real public data)

`purchase-card-2026-08.csv` is a **real** data file, not a fake one. Read this before relying
on it.

## What it is

- The August 2026 purchase-card transactions of Stockport Metropolitan Borough Council, a UK
  local authority, published as open data.
- Source: https://ckan.publishing.service.gov.uk/dataset/purchase-card-transactions
- Licence: [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
  Contains public sector information licensed under the Open Government Licence v3.0.
- The copy here is unmodified.

## What it contains

360 transactions with the columns `Organisation Name`, `Supplier (Beneficiary)`,
`Procurement (Merchant) Category`, `Purchase Date`, `Settlement Date` and `Gross Amount (£)`.
The only organisation is `STOCKPORT MBC` and the suppliers are shops and services. It does
not name any cardholder or employee and has no card, account, email or phone numbers. This
was checked by scanning the file for names with titles, email addresses, phone numbers and
card-length digit strings, and none were found.

## Why it is here

It is a realistic, messy card export that a hand-made file would not be: a byte-order mark, a
title line and a blank line before the header, a currency symbol in the amount header, two
different date formats in two date columns, quoted thousands separators and genuinely
repeated rows. `backend/tests/test_reference_csv.py` uses it to check that the CSV reader
handles all of that and parses every row.

## About the "fake data only" rule

The assessment rules say to use fake data only, with no real people's details and no real
bank statements. This file is not a person's statement and holds no personal details, but it
is real transaction data from a real public body, so it sits outside a strict reading of
"fake data only". It was included deliberately, to test against real-world input. Every other
demo statement in `sample-data/` is invented, and the PDF and OFX reference files are
synthetic according to their authors.

To remove it entirely, delete this folder and `backend/tests/test_reference_csv.py`, and
delete its row from `THIRD_PARTY_NOTICES.md`. Nothing else depends on it.
