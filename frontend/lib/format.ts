import type { CategoryTotal, Transaction } from "./api";

const pkr = new Intl.NumberFormat("en-PK", {
  style: "currency",
  currency: "PKR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
});

// Intl formats numeric strings exactly (no float round trip), so "1173930.50" stays precise.
export function formatPkr(amount: string): string {
  return pkr.format(amount as `${number}`);
}

const pkrSigned = new Intl.NumberFormat("en-PK", {
  style: "currency",
  currency: "PKR",
  minimumFractionDigits: 0,
  maximumFractionDigits: 2,
  signDisplay: "exceptZero",
});

export const formatSignedPkr = (amount: string): string => pkrSigned.format(amount as `${number}`);

const toCents = (s: string): bigint => {
  const t = s.trim();
  const [whole, frac = ""] = t.replace(/^[-+]/, "").split(".");
  const cents = BigInt(whole + (frac + "00").slice(0, 2));
  return t.startsWith("-") ? -cents : cents;
};

// Exact income minus spending (spending arrives positive). BigInt cents, no float.
export function netAmount(income: string, spending: string): string {
  const c = toCents(income) - toCents(spending);
  const digits = (c < BigInt(0) ? -c : c).toString().padStart(3, "0");
  return `${c < BigInt(0) ? "-" : ""}${digits.slice(0, -2)}.${digits.slice(-2)}`;
}

// ponytail: Number() is used only to order bars and size their width, never to display money.
export function categoryBars(categories: CategoryTotal[]): (CategoryTotal & { pct: number })[] {
  const size = (c: CategoryTotal) => Math.abs(Number(c.net));
  const sorted = [...categories].sort((a, b) => size(b) - size(a));
  const max = sorted.length ? size(sorted[0]) : 0;
  return sorted.map((c) => ({ ...c, pct: max ? (size(c) / max) * 100 : 0 }));
}

export const isDebit = (amount: string): boolean => amount.trim().startsWith("-");

export type Filter = "all" | "review" | "edited" | { category: string };

export function filterRows(rows: Transaction[], filter: Filter): Transaction[] {
  if (filter === "all") return rows;
  if (filter === "review") return rows.filter((t) => t.needs_review);
  if (filter === "edited") return rows.filter((t) => t.user_edited);
  return rows.filter((t) => t.category === filter.category);
}

export type Tab = "all" | "review" | "edited";

// Tab, category select and description search combine with AND. An empty category means any.
export function applyFilters(rows: Transaction[], tab: Tab, category: string, query: string): Transaction[] {
  const byTab = filterRows(rows, tab);
  const byCategory = category ? filterRows(byTab, { category }) : byTab;
  const q = query.trim().toLowerCase();
  return q ? byCategory.filter((t) => t.description.toLowerCase().includes(q)) : byCategory;
}

export const categoryClass = (category: string): string =>
  "cat-" + category.toLowerCase().replace(/[^a-z]+/g, "-").replace(/^-|-$/g, "");
