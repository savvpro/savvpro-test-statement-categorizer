# Design Decisions & Use Case

## Use Case: Freelance Web Developer
I chose to build a statement categorizer that is made for a Freelance Web Developer. Freelancer users have highly specific tax write-offs like (hosting, domains, software subscriptions, hardware) mixed with personal/generic expenses. 

- **Software & Tools**: Matches keywords like "aws", "github", "adobe".
- **Travel**: Matches keywords like "uber", "careem", "flight".
- **Hardware & Office**: Matches keywords like "dell", "amazon".
- **Income**: Matches "upwork", "fiverr", "wire transfer". 
- **Needs Review**: Any transaction that does not match known business keywords is flagged for manual user review in the UI.

## The "Brain" (Rule-Based Engine)
Per the project rules, no AI models were used to make categorization decisions. 
The core logic resides in `backend/categorizer/brain.py`. It utilizes a robust Dictionary of Regex patterns. 
1. The CSV is parsed into memory.
2. The description is converted to lowercase.
3. The engine iterates through the dictionary. If a regex match is found, the category is assigned.
4. Edge Case Handling: The engine checks the mathematical sign of the `Amount`. If an expense matches an "Income" keyword (e.g., a refund or fee), it ensures negative amounts are not incorrectly categorized as positive income.

## Frontend
Built with Next.js and Tailwind CSS for a clean, responsive, production-ready interface. Rows flagged as "Needs Review" render a `<select>` dropdown so the user can manually correct the unassigned transaction.