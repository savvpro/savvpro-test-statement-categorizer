# Design Decisions

## Architecture

The application follows a simple client-server architecture.

React Frontend
↓
FastAPI REST API
↓
CSV Parser
↓
Rule-Based Categorization Engine

## Categorization Engine

The categorization logic is implemented in Python without relying on an LLM.

Each category contains a list of known merchant keywords.

Example:

Software:
ADOBE
CANVA
MICROSOFT
FIGMA

Travel:
UBER
CAREEM
LYFT

If a transaction matches a keyword, the application assigns the corresponding category.

## Uncertainty Handling

Transactions that cannot be confidently categorized are not guessed.

Instead, they are assigned:

Needs Review

with:

confidence = 0

This makes the system safer and allows users to manually correct uncertain results.

## Manual Corrections

The frontend provides a dropdown for every transaction.

Users can change an assigned category.

When a category is changed, summary totals are recalculated immediately.

## Transfers and Refunds

Transfers are separated from business expenses.

Example:

TRANSFER TO SAVINGS

is categorized as:

Transfer / Not Expense

Refund transactions are categorized separately as Refund.

## Technology Choices

### FastAPI

FastAPI was selected because it provides:

- simple REST API development
- automatic API documentation
- good Python type support
- lightweight architecture

### React

React provides an interactive UI for:

- file uploads
- transaction tables
- category corrections
- live summary calculations

## Future Improvements

Possible improvements include:

- PDF statement support
- configurable user-created rules
- persistent database storage
- merchant history
- improved confidence scoring
- fuzzy merchant matching
- export corrected CSV