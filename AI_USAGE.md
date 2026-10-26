# AI usage disclosure

AI-assisted coding was used during development of this assessment. The assistant
helped plan the architecture, draft implementation code, write tests, improve
documentation and troubleshoot test feedback. All resulting code was reviewed,
run locally and verified with the project test/build commands before submission.

## Runtime AI usage

**None.** Ledgerly does not call an LLM, external categorization service or any
AI API at runtime. The categorization engine is deterministic Python code, so the
application works without API keys, credentials or network access after setup.

## Privacy and data handling

Only fictional sample data is included. The UI advises users to avoid real bank
data. Uploaded CSV bytes are processed locally and are not retained; validated
transactions and user reviews are stored only in the local SQLite database.

## Token record

The coding environment exposed a cumulative session counter of approximately
4.17 million tokens during final verification. This is an environment-wide number,
not a task-only measurement: it includes system context, tool output, prior
planning and generated code. No reliable task-only token counter was available,
so this disclosure avoids presenting the cumulative value as a precise per-file or
per-feature total.
