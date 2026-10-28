"use client";
import { allowedFor, GROUPS } from "@/lib/categories";
import type { CategoryOut, Direction } from "@/lib/api/types";

const COMMON = [
  "RENT",
  "REPAIRS",
  "CLEANING_MAINTENANCE",
  "UTILITIES",
  "SUPPLIES",
  "MORTGAGE_INTEREST",
  "INSURANCE",
  "TAXES",
  "PERSONAL",
  "TRANSFER",
];

/** Categories valid for this money direction, suggestion first, then the usual picks. */
export function rankedCategories(
  cats: CategoryOut[],
  direction: Direction,
  isRefund: boolean,
  suggested: string | null,
): CategoryOut[] {
  const ok = cats.filter((c) => allowedFor(c, direction, isRefund));
  const rank = (c: CategoryOut) => {
    if (c.code === suggested) return -1;
    const i = COMMON.indexOf(c.code);
    return i === -1 ? 100 : i;
  };
  return [...ok].sort((a, b) => rank(a) - rank(b));
}

export function CategorySelect({
  id,
  categories,
  direction,
  isRefund = false,
  value,
  suggested,
  onChange,
}: {
  id: string;
  categories: CategoryOut[];
  direction: Direction;
  isRefund?: boolean;
  value: string;
  suggested: string | null;
  onChange: (code: string) => void;
}) {
  const allowed = categories.filter((c) => allowedFor(c, direction, isRefund));
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xs border border-muted bg-row px-2 py-2"
    >
      {!value && <option value="">Choose a category</option>}
      {GROUPS.map((g) => {
        const items = allowed.filter((c) => c.kind === g.kind);
        if (items.length === 0) return null;
        return (
          <optgroup key={g.kind} label={g.label}>
            {items.map((c) => (
              <option key={c.code} value={c.code}>
                {c.label}
                {c.schedule_e_line ? ` (line ${c.schedule_e_line})` : ""}
                {c.code === suggested ? " - suggested" : ""}
              </option>
            ))}
          </optgroup>
        );
      })}
    </select>
  );
}
