# Third-party sample data

The files under `sample-data/reference/` are real-world and standards-based samples
used to check that the parsers cope with how banks actually format statements. Every
file below is either synthetic by its author's own description or published by a public
body as open data. None contains real customer details. They are unmodified copies.

| Folder | Source | Licence | Used for |
|---|---|---|---|
| `bankstatemently-benchmark/` | [bankstatemently/bank-statement-parsing-benchmark](https://github.com/bankstatemently/bank-statement-parsing-benchmark), statements `bsb-001` to `bsb-005` | MIT, Copyright (c) 2026 Bankstatemently (`LICENSE` in the folder) | PDF statements from Singapore, the US (credit card), the Netherlands, Hong Kong and French-speaking Canada, each with a `statement-info.json` describing its layout and true transaction count |
| `bank-statement-pdf-parser/` | [AyonPal/bank-statement-pdf-parser](https://github.com/AyonPal/bank-statement-pdf-parser), `samples/pdfs` and `samples/parsed` | MIT (`LICENSE` in the folder) | Synthetic Indian bank statement PDFs with a rotated watermark, plus the ground-truth CSV for each |
| `ofxparse/` | [jseutter/ofxparse](https://github.com/jseutter/ofxparse), `tests/fixtures` | MIT, Copyright (c) 2009 Jerry Seutter (`LICENSE` in the folder) | OFX 1.x (SGML) and 2.x (XML) bank and credit card exports |
| `stockport-purchase-card/` | [Stockport Metropolitan Borough Council, Purchase Card Transactions, August 2026](https://ckan.publishing.service.gov.uk/dataset/purchase-card-transactions) | [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) | **Real** public-body data (no personal details, see the note below). A card transaction export with a title line, a BOM, two date columns, currency symbols in the header and quoted thousands separators |

Contains public sector information licensed under the Open Government Licence v3.0.

## A note on the "fake data only" rule

The assessment asks for fake data only, with no real people's details and no real bank
statements. Everything here is either synthetic by its authors' own description (the PDFs and
OFX fixtures) or open data from a public body. The one exception to "fake" is the Stockport
purchase-card file, which is **real** council transaction data. It contains no personal
details (no cardholder names, card numbers, emails or phone numbers, checked by a scan) and
is licensed for reuse, but it is not invented. It was included on purpose to test against
real-world input. See [its README](sample-data/reference/stockport-purchase-card/README.md)
for what it contains and how to remove it (delete that folder and
`backend/tests/test_reference_csv.py`; nothing else depends on it).

## Standards sample files that are fetched, not stored

The official ISO 20022 `camt.053` and SWIFT `MT940` sample files published by PostFinance
are used by the tests for those two formats. The publisher does not state a licence, so
the files are not copied into this repository. Run
`python backend/scripts/fetch_reference_samples.py` to download them into
`backend/tests/reference_cache/` (ignored by git). The tests for them are skipped when the
files are absent.

- [PostFinance sample files](https://www.postfinance.ch/en/support/documents/sample-files-for-business-customers.html)

## Formats and specifications

- OFX: Open Financial Exchange specification, versions 1.x and 2.x
- ISO 20022 `camt.053.001.xx` bank-to-customer statement
- SWIFT MT940 customer statement message
- RFC 4180, the common CSV format, plus the many real-world departures from it that the
  CSV reader tolerates (semicolon and tab delimiters, BOMs, preamble lines, quoted
  thousands separators)
