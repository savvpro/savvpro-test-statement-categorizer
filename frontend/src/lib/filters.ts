import type { Category, Kind, Transaction } from "../types";

export type FilterId = "review" | "all" | Kind;

export const FILTERS: { id: FilterId; label: string }[] = [
  { id: "review", label: "Needs review" },
  { id: "all", label: "All" },
  { id: "income", label: "Income" },
  { id: "expense", label: "Deductible" },
  { id: "personal", label: "Personal" },
  { id: "transfer", label: "Transfers" },
];

export function kindOf(tx: Transaction, categories: Map<string, Category>): Kind | null {
  return tx.category ? (categories.get(tx.category)?.kind ?? null) : null;
}

export function filterTransactions(
  transactions: Transaction[],
  filter: FilterId,
  query: string,
  categories: Map<string, Category>,
): Transaction[] {
  const q = query.trim().toLowerCase();
  return transactions.filter((tx) => {
    if (filter === "review" && tx.status !== "needs_review") return false;
    if (filter !== "review" && filter !== "all" && kindOf(tx, categories) !== filter) return false;
    if (!q) return true;
    const label = tx.category ? (categories.get(tx.category)?.label ?? "") : "";
    return (
      tx.description.toLowerCase().includes(q) ||
      tx.merchant.toLowerCase().includes(q) ||
      label.toLowerCase().includes(q)
    );
  });
}

export function countByFilter(
  transactions: Transaction[],
  categories: Map<string, Category>,
): Record<FilterId, number> {
  const counts: Record<FilterId, number> = {
    review: 0,
    all: transactions.length,
    income: 0,
    expense: 0,
    personal: 0,
    transfer: 0,
  };
  for (const tx of transactions) {
    if (tx.status === "needs_review") counts.review += 1;
    const kind = kindOf(tx, categories);
    if (kind) counts[kind] += 1;
  }
  return counts;
}
