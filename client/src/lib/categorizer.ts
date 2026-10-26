export const CATEGORIES = [
  "Software",
  "Travel",
  "Meals",
  "Office supplies",
  "Equipment",
  "Advertising",
  "Bank fees",
  "Refund",
  "Income",
  "Transfer / non-spend",
  "Needs review",
] as const;

export type Category = (typeof CATEGORIES)[number];
export type RawRow = Record<string, string>;
export type DecisionStatus = "categorized" | "needs_review" | "reviewed";

export type Decision = {
  category: Category;
  status: DecisionStatus;
  confidence: "high" | "medium" | "review";
  ruleId: string;
  ruleLabel: string;
  reviewReason?: string;
};

export type Transaction = Decision & {
  id: string;
  date: string;
  description: string;
  amount: number | null;
  direction: string;
  raw: RawRow;
};

export function normalizeDescription(value: string) {
  return value.trim().toUpperCase().replace(/\s+/g, " ");
}

export function parseAmount(value: string | undefined, direction = "") {
  if (!value?.trim()) return null;
  let cleaned = value.trim().toUpperCase().replaceAll("$", "").replaceAll(",", "");
  const parenthesized = cleaned.startsWith("(") && cleaned.endsWith(")");
  cleaned = cleaned.replace(/^\(|\)$/g, "");
  const parsed = Number(cleaned);
  if (!Number.isFinite(parsed)) return null;
  const normalizedDirection = direction.trim().toLowerCase();
  let amount = parsed;
  if (["debit", "expense", "withdrawal", "outflow"].includes(normalizedDirection)) amount = -Math.abs(amount);
  if (["credit", "income", "deposit", "inflow"].includes(normalizedDirection)) amount = Math.abs(amount);
  if (parenthesized) amount = -Math.abs(amount);
  return Math.round(amount * 100) / 100;
}

function findTerm(text: string, terms: string[]) {
  return terms.find((term) => text.includes(term));
}

export function classify(description: string, amount: number | null, direction: string, dataIssue?: string): Decision {
  const text = normalizeDescription(description);
  if (dataIssue || amount === null || !text) {
    const reason = dataIssue ?? "Missing description or amount.";
    return { category: "Needs review", status: "needs_review", confidence: "review", ruleId: "data-quality", ruleLabel: reason, reviewReason: reason };
  }

  const transfer = findTerm(text, ["TRANSFER", "AUTOPAY", "AUTO PAY", "CARD PAYMENT", "PAYMENT TO", "CASH ADVANCE", "SAVINGS"]);
  if (transfer) return { category: "Transfer / non-spend", status: "categorized", confidence: "high", ruleId: "transfer", ruleLabel: `Merchant text contains “${transfer}”` };

  const refund = findTerm(text, ["REFUND", "RETURN", "REVERSAL", "CREDIT MEMO", "CHARGEBACK"]);
  if (refund) return { category: "Refund", status: "categorized", confidence: "high", ruleId: "refund", ruleLabel: `Merchant text contains “${refund}”` };

  const income = findTerm(text, ["CLIENT PAYMENT", "INVOICE", "PAYOUT", "PROJECT DEPOSIT", "CONTRACTOR PAYMENT"]);
  if (income && amount > 0) return { category: "Income", status: "categorized", confidence: "high", ruleId: "income", ruleLabel: `Direction is credit and description contains “${income}”` };

  const fee = findTerm(text, ["BANK FEE", "SERVICE FEE", "OVERDRAFT", "FOREIGN TRANSACTION FEE", "MONTHLY FEE"]);
  if (fee) return { category: "Bank fees", status: "categorized", confidence: "high", ruleId: "fees", ruleLabel: `Merchant text contains “${fee}”` };

  const ruleGroups: Array<[string, Category, string[], "high" | "medium"]> = [
    ["software", "Software", ["ADOBE", "FIGMA", "GITHUB", "NOTION", "DROPBOX", "GOOGLE WORKSPACE", "AIRTABLE"], "high"],
    ["travel", "Travel", ["UBER", "LYFT", "AIRBNB", "DELTA", "SOUTHWEST", "UNITED AIR", "AMTRAK", "HOTEL", "PARKING", "RIDESHARE"], "high"],
    ["meals", "Meals", ["STARBUCKS", "DOORDASH", "UBER EATS", "GRUBHUB", "COFFEE", "RESTAURANT", "CATERING"], "medium"],
    ["office-supplies", "Office supplies", ["STAPLES", "OFFICE DEPOT", "PRINTER", "PAPER", "DESK SUPPLIES"], "high"],
    ["equipment", "Equipment", ["B&H", "BEST BUY", "APPLE STORE", "DELL", "LOGITECH", "CAMERA", "MONITOR", "KEYBOARD"], "high"],
    ["advertising", "Advertising", ["META ADS", "GOOGLE ADS", "CAMPAIGN", "SPONSORED", "PROMOTED"], "high"],
  ];
  for (const [ruleId, category, terms, confidence] of ruleGroups) {
    const match = findTerm(text, terms);
    if (match) return { category, status: "categorized", confidence, ruleId, ruleLabel: `Merchant text contains “${match}”` };
  }

  if (amount > 0) {
    const reason = "Positive inflow without a recognized income or refund rule.";
    return { category: "Needs review", status: "needs_review", confidence: "review", ruleId: "unmatched-credit", ruleLabel: reason, reviewReason: reason };
  }
  const reason = "No specific merchant rule matched this transaction.";
  return { category: "Needs review", status: "needs_review", confidence: "review", ruleId: "unmatched", ruleLabel: reason, reviewReason: reason };
}

export function categorizeRows(rows: RawRow[], mappedColumns: Record<string, string>): Transaction[] {
  const seen = new Map<string, number>();
  const normalized = rows.map((row, index) => {
    const date = (row[mappedColumns.date] ?? "").trim();
    const description = (row[mappedColumns.description] ?? "").trim();
    const direction = (row[mappedColumns.type] ?? "").trim();
    const amount = parseAmount(row[mappedColumns.amount], direction);
    let issue: string | undefined;
    if (!date) issue = "Missing date.";
    else if (!description) issue = "Missing description.";
    else if (amount === null) issue = "Amount is missing or not numeric.";
    const fingerprint = `${date}|${normalizeDescription(description)}|${amount ?? ""}`;
    if (!issue && seen.has(fingerprint)) issue = `Exact duplicate of row ${(seen.get(fingerprint) ?? 0) + 1}.`;
    else if (!issue) seen.set(fingerprint, index);
    return { row, date, description, direction: direction || (amount !== null && amount > 0 ? "Credit" : "Debit"), amount, issue };
  });

  return normalized.map(({ row, date, description, direction, amount, issue }, index) => ({
    id: `txn-${index + 1}`,
    date,
    description,
    amount,
    direction,
    raw: row,
    ...classify(description, amount, direction, issue),
  }));
}
