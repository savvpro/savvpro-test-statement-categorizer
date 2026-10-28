import type { CategoryOut, Direction, Status, TransactionOut } from "./api/types";

export const STATUS_LABEL: Record<Status, string> = {
  auto: "Sorted",
  user_confirmed: "Confirmed by you",
  needs_review: "Needs your review",
  duplicate: "Duplicate (skipped)",
};

export const FLAG_TEXT: Record<string, string> = {
  MIXED_USE_MERCHANT: "This merchant is used for both rental and personal spending.",
  POSSIBLE_CAPITAL_IMPROVEMENT:
    "Over $2,500, so this may be an improvement (depreciated) rather than a repair.",
  MORTGAGE_SPLIT_REQUIRED:
    "A mortgage payment mixes interest and principal. Only the interest counts.",
  PAYMENT_TO_INDIVIDUAL: "Paid to a person. Check what the payment was for.",
  CHECK_NO_PAYEE: "A check with no payee name.",
  DIRECTION_CONFLICT: "The money direction does not match the usual category.",
  AMOUNT_OUTLIER: "The amount is unusual for this merchant.",
  UNKNOWN_MERCHANT: "We have not seen this merchant before.",
  LOW_INFORMATION: "The description has too little detail to sort with confidence.",
  ZERO_AMOUNT: "The amount is zero.",
  AMBIGUOUS_MATCH: "More than one category fits equally well.",
  RENT_REVERSAL: "A returned rent payment.",
  POSSIBLE_1099: "Paid over $600 to one payee. You may need to file a 1099.",
  RECURRING: "Repeats on a regular schedule.",
  DUPLICATE_PENDING: "Matches a pending charge.",
  DUPLICATE_FITID: "The bank listed this transaction twice.",
  DUPLICATE_PRIOR_UPLOAD: "Already in a statement you uploaded earlier.",
};

export function flagText(flag: string): string {
  return FLAG_TEXT[flag] ?? flag.toLowerCase().replace(/_/g, " ");
}

export function allowedFor(cat: CategoryOut, direction: Direction, isRefund: boolean): boolean {
  if (cat.allowed_directions.includes(direction)) return true;
  if (isRefund && cat.kind === "expense" && direction === "inflow") return true;
  return isRefund && cat.code === "RENT" && direction === "outflow";
}

export const GROUPS: { kind: CategoryOut["kind"]; label: string }[] = [
  { kind: "income", label: "Income" },
  { kind: "expense", label: "Schedule E expenses" },
  { kind: "non_pnl", label: "Not counted on Schedule E" },
];

export function categoryLabel(cats: CategoryOut[] | undefined, code: string | null): string {
  if (!code) return "Uncategorized";
  return cats?.find((c) => c.code === code)?.label ?? code;
}

export function lineText(cats: CategoryOut[] | undefined, code: string | null): string {
  const c = cats?.find((x) => x.code === code);
  const label = categoryLabel(cats, code);
  return c?.schedule_e_line ? `${label} (line ${c.schedule_e_line})` : label;
}

/** Readable merchant name for "Remember for ..." copy. */
export function merchantName(tx: TransactionOut): string {
  const k = tx.merchant_key || tx.description;
  return k.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}
