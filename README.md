# Statement Categorizer
Next.js 14 + TypeScript + Tailwind frontend. `npm install`, `npm run dev`, `npm test`, `npm run build`.
**Demo mode** (default, `NEXT_PUBLIC_API_BASE_URL` empty): uploads are not read; synthetic sample data is loaded. **Real mode**: set the variable to the FastAPI URL; `lib/api.ts` is the only place that calls the backend, and failures surface as errors. Categorization will be rule-based Python code.
