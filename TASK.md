# Build a Statement Categorizer

Pick a type of customer whose bank or credit card statements need to be sorted for tax time. Build an app that reads their statements and sorts every transaction for them.

## 1. How it works

The user uploads a statement. The app reads each transaction, decides its category, and shows the result.

```
Upload statement → Read transactions → The brain → Category for each row → User reviews the result
```

This repeats for every row in the statement.

> **The one big rule:** the brain must be your own code. Do not use a big AI model (like GPT, Claude or Gemini) to decide a category. Your code decides what each transaction is and when it is not sure.

You can use AI tools to help you write the code. We want to see how you use them.

## 2. Pick a use case

You can pick anything. The app should do a real job from start to end, not just show a table.

> **Example:** a freelance designer. The app reads their business credit card statement. `ADOBE CREATIVE CLOUD` becomes "Software", `UBER *TRIP` becomes "Travel", `TRANSFER TO SAVINGS` is not spending, and `JOES CAFE 9921` is unknown, so it goes to **Needs Review**. At the end, the user sees a total for each category and fixes the rows that need review.

If the app is not sure, it must say so. A wrong guess is worse than asking.

Real statements are messy. Think about what can go wrong in your use case and make your app handle it. For example, a refund is money back, not income. Finding these cases is part of the task.

## 3. Tech

- Backend: Python.
- Frontend: React or Next.js. A simple page where someone can upload a statement, see how each row was categorized, and fix the rows that need review.
- Everything else is up to you. Use any framework, library, API or service you want, for reading files, data, testing, or anything else. This does not include the brain: no big AI model for decisions (see the big rule above).

## 4. Your repo should include

- `README.md`: how to set it up and run it.
- `DESIGN.md`: your use case and how your brain makes decisions.
- `AI_USAGE.md`: which AI tools you used, how they helped, where they got things wrong, and how many tokens you used. Add the token logs or usage screenshots from your tools.

When you are done, open a pull request with your work.

## 5. Codebase rules

- Do not commit keys, passwords or tokens.
- Use fake data only. No real people's details and no real bank statements.
- Add tests.

**Nice to have:** build it like a real production product. A clean project structure and the good practices you would use in a live product will earn extra points.

Good luck, and have fun with it.
