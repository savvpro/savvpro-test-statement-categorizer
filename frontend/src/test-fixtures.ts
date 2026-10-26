import type { Category, Transaction } from "./types";

export const categories: Category[] = [
  { id: "platform_income", label: "Gig Platform Income", kind: "income", schedule_c_line: "Line 1", description: "" },
  { id: "fuel", label: "Fuel & EV Charging", kind: "expense", schedule_c_line: "Line 9", description: "" },
  { id: "personal", label: "Personal (not deductible)", kind: "personal", schedule_c_line: null, description: "" },
  { id: "transfer", label: "Transfers & Card Payments", kind: "transfer", schedule_c_line: null, description: "" },
];

export const categoryMap = new Map(categories.map((c) => [c.id, c]));

let nextId = 1;

export function tx(overrides: Partial<Transaction> = {}): Transaction {
  return {
    id: nextId++,
    line: 2,
    date: "2026-01-03",
    description: "POS PURCHASE SHELL OIL 57444",
    merchant: "SHELL OIL",
    amount_cents: -4520,
    direction: "out",
    bank_category: null,
    category: "fuel",
    status: "auto",
    confidence: 0.92,
    source: "knowledge_base",
    reasons: ["Recognised: SHELL."],
    suggestions: [],
    flags: [],
    engine_category: "fuel",
    ...overrides,
  };
}
