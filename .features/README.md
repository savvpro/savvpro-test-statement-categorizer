# Feature Plan: Statement Categorizer

This project is divided into 7 sequential features. Each feature has its own spec file in this directory with complete instructions for an agent to build, test, and push.

## Build Order

| # | Feature | Spec File | Description |
|---|---------|-----------|-------------|
| 1 | Backend Models & Brain | `feature-1-backend-brain.md` | Pydantic models, sanitizer, direction detector, rules dict, classifier, categories, tax summary |
| 2 | CSV Parser & Sample Data | `feature-2-parser-and-data.md` | Multi-format CSV parser + fake sample statement with edge cases |
| 3 | FastAPI API Layer | `feature-3-api-endpoints.md` | REST endpoints: upload, recalculate, categories, sample |
| 4 | Backend Tests | `feature-4-backend-tests.md` | pytest suite covering all brain modules, parser, and API |
| 5 | Frontend Scaffold & Upload | `feature-5-frontend-upload.md` | Vite + React project, drag-and-drop upload, demo mode, API client |
| 6 | Dashboard & Review Table | `feature-6-frontend-dashboard.md` | Tax summary cards, category chart, interactive table, inline edit, export |
| 7 | Documentation & Final Push | `feature-7-documentation.md` | README.md, DESIGN.md, AI_USAGE.md, final commit and push |

## Agent Workflow Per Feature

```
1. Read the feature .md file
2. Build all files described
3. Run tests / verify it works
4. git add + commit with message from the spec
5. git push origin candidate-sikandarhussain6858
6. Move to next feature
```

## Key Constraint (from TASK.md)

> **The brain must be your own code.** No LLM (GPT, Claude, Gemini) calls for categorization decisions. The classification engine is 100% deterministic rule-based code.
