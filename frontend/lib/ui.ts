import type { Kind } from "./types";

// Class names are written out in full so Tailwind can see them at build time.

const btn =
  "inline-flex h-10 items-center justify-center gap-2 whitespace-nowrap rounded-md px-3.5 text-sm font-medium transition-colors duration-150 disabled:cursor-not-allowed disabled:opacity-50";

export const btnPrimary = `${btn} bg-accent text-on-accent hover:bg-accent-hover active:bg-accent-active`;
export const btnSecondary = `${btn} border border-rule-strong bg-surface text-ink hover:bg-sunken active:bg-rule`;

export const KIND_DOT: Record<Kind, string> = {
  income: "bg-kind-income",
  deductible: "bg-kind-deductible",
  personal: "bg-kind-personal",
  excluded: "bg-kind-excluded",
  refund: "bg-kind-refund",
  review: "bg-kind-review",
};

/** Order and wording of the groups in the category menu. */
export const KIND_GROUPS: { kind: Kind; label: string }[] = [
  { kind: "income", label: "Income" },
  { kind: "deductible", label: "Business expense (deductible)" },
  { kind: "personal", label: "Personal (not deductible)" },
  { kind: "excluded", label: "Not spending" },
  { kind: "refund", label: "Refund" },
];
