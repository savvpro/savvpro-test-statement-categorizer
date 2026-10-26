# AI Usage

## Tools Used

- **Claude (claude.ai chat)** by Anthropic: Used to understand the task, divide it into modules, generate test cases, and get UI design suggestions.

## Not Used

- No AI model is used inside the application. The categorizer uses plain Python rules in `backend/app/categorizer.py`.

## How AI Helped

- Helped me understand the project requirements and divide the task into smaller modules.
- I wrote the code components, implementing one module at a time.
- Helped generate test cases and provided UI design guidance.
- Helped me understand errors and improve the implementation.

## Where It Got Things Wrong

- The first sample CSV contained a valid date in a row expected to be skipped, so I corrected the sample data.
- A test incorrectly described `JOES CAFE` as an unknown transaction, although the rules categorized it as Meals. I corrected the test.
- AI-generated suggestions and test cases required review to ensure they matched the actual application logic.

## What I Changed Myself

- Wrote the application code myself, module by module.
- Reviewed the code and corrected test cases and sample data where needed.
- Learned how to structure a project, implement modules, test functionality, and design the UI.

## Token Usage

- AI was used for task understanding, planning, test-case generation, and UI design guidance.
- Token usage was not recorded.
  ![alt text](image.png)
