# Reference samples

Files published by others, used to test the parsers against real-world formats. They are
unmodified copies. Sources and licences are in
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

| Folder | Nature of the data |
|---|---|
| `bankstatemently-benchmark/` | PDF statements for fictional banks with synthetic data. The project states "fictional banks with synthetic data. No real customer information." |
| `bank-statement-pdf-parser/` | PDF statements that print "SYNTHETIC ACCOUNT STATEMENT" and "synthetic demo data", with a ground-truth CSV for each |
| `ofxparse/` | Small OFX fixtures from an open-source library, with invented merchants and account numbers |
| `stockport-purchase-card/` | **Real** open data from a UK council, with no personal details. See its [README](stockport-purchase-card/README.md) for how it relates to the "fake data only" rule |

Names that appear inside the synthetic PDFs (an account holder, an address) are inventions of
their authors and do not refer to real people.
