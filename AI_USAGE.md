# AI Usage Log

**Tool Used:** Google Gemini

**How it helped:**
- Used as a pair-programmer to quickly scaffold the Django REST Framework boilerplate.
- Provided the Tailwind CSS class structures for the Next.js frontend table to ensure a clean, modern UI.
- Helped generate dummy CSV data (`test.csv`) for testing the API endpoint.

**Where it got things wrong:**
- Initially generated Django URL routes with a `categorizer/` prefix that threw a 404 error during testing. I used Gemini to debug this by passing the traceback, which resulted in quickly updating `config/urls.py` to correctly map the API endpoint.

**Token Usage:**
- Used approximately 4,000 - 5,000 context tokens during the scaffolding conversation.

**Compliance Note:** AI was explicitly **NOT** used for the decision-making logic of the transactions. The actual sorting "brain" is a strictly rule-based Python dictionary built manually in `brain.py`.