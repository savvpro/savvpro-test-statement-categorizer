// Amounts arrive from the API as strings to keep cents exact.
// We only convert for display; all totals are computed by the backend.
const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export const money = (value) => usd.format(Number(value));
export const percent = (value) => `${Math.round(value * 100)}%`;

// Categories a person may pick by hand (mirrors NOT_MANUAL in api.py).
export const MANUAL_CATEGORIES = [
  "Rental Income",
  "Security Deposit",
  "Transfer",
  "Property Tax",
  "Insurance",
  "Repairs & Maintenance",
  "Utilities",
  "HOA Fees",
  "Bank Fees",
];