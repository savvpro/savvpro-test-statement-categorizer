# AI Usage Disclosure

This file is a **template** to be completed honestly by the candidate. Do not invent usage numbers.

## AI tools used

| Tool | Purpose | How it helped | Where it got things wrong |
|------|---------|---------------|---------------------------|
| (e.g. Claude, Copilot, GPT) | (e.g. boilerplate, test scaffolding, debugging) | (e.g. saved time on FastAPI setup) | (e.g. suggested wrong import paths, hallucinated library APIs) |

## Token usage

| Tool | Approx. input tokens | Approx. output tokens | Notes |
|------|---------------------|----------------------|-------|
| | | | |
| | | | |

**Total tokens:** (fill in honestly)

## Categories of AI assistance

- **Code generation:** (e.g. initial FastAPI app skeleton, React component structure)
- **Debugging:** (e.g. fixing float comparison bug in ambiguity gap check)
- **Test writing:** (e.g. generating test cases for edge cases)
- **Documentation:** (e.g. drafting README sections)

## What I wrote myself

- The categorization brain logic (normalizer, classifier, structural rules)
- Merchant rules in `config/rules.yaml`
- All threshold/weight constants in `constants.py`
- Test assertions verifying no AI SDK is imported
- Integration of frontend with backend API

## Verification

- [ ] No OpenAI/Anthropic/Gemini/etc. API key or SDK is imported in the categorization brain
- [ ] `test_brain_imports_no_ai_sdk` passes
- [ ] All tests pass (`pytest -v`)
- [ ] Ruff reports no issues (`ruff check .`)
- [ ] Frontend TypeScript compiles (`npx tsc --noEmit`)
- [ ] Frontend builds (`npm run build`)