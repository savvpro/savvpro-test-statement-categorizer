# AI Usage Disclosure

## AI Tools Used

OpenAI ChatGPT was used as a development assistant.

## How AI Helped

- Planning the FastAPI backend architecture
- Drafting and reviewing Python categorization logic
- Developing API endpoints and validation
- Writing and improving automated tests
- Developing the React frontend
- Troubleshooting npm and Windows development issues
- Drafting documentation
- Guiding Git and GitHub submission steps

## Human Verification

The application was tested locally.

Backend: 71 pytest tests passed (latest verified run).

Frontend: Vite production build passed.

ESLint: 0 errors and 1 non-blocking warning in the latest run.

Manual integration testing covered statement upload, category correction, duplicate handling and summary updates.

## Mistakes and Limitations

AI-generated suggestions required local verification and integration.

An attempted npm ci operation initially failed with an EPERM file-lock error on Windows. Closing Node processes and reinstalling dependencies resolved it.

The frontend lint check reported a React useMemo dependency warning.

Docker Engine was unavailable during local checks, so Docker runtime verification was not completed.

## AI Runtime Independence

No external generative AI model is used to decide transaction categories.

All transaction classification decisions are performed by application code and explicit user corrections.

## Token Usage

An approximate token count was calculated using OpenAI's
`tiktoken` Python library with the `o200k_base` encoding.

- Collected transcript size: 62,973 characters
- Approximate token count: **16,716 tokens**
- Method: Tokenization of the collected ChatGPT conversation text
  containing prompts and responses.
- Scope: This figure represents the collected transcript, not
  necessarily every AI interaction during development.
- Limitation: Hidden reasoning and other unrecorded token usage
  are not included.

The estimate is based on collected conversation text rather than
an invented usage figure.

## Logs and Screenshots

Development conversation history is available in ChatGPT.

Supporting screenshots or exported usage records should be attached to the repository if available.

## Responsibility

AI-assisted code and documentation were reviewed through local testing. Final implementation and submission remain the candidate's responsibility.

## Supporting AI Conversation Evidence

The following original screenshots document AI-assisted development activities:

1. [Testing and verification conversation](docs/ai-evidence/01-real-testing-conversation.png)
2. [Documentation assistance conversation](docs/ai-evidence/02-real-documentation-conversation.png)

These are excerpts of actual ChatGPT conversations, not token-usage reports. An approximate count of 16,716 tokens was calculated from the collected conversation transcript using tiktoken.
