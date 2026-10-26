import type { CategoryInfo, Txn } from "@/lib/types";
import { KIND_DOT, KIND_GROUPS } from "@/lib/ui";

interface Props {
  txn: Txn;
  categories: CategoryInfo[];
  disabled: boolean;
  onChange: (category: string) => void;
}

/** Native select (keyboard and screen-reader friendly), grouped by how the category is taxed. */
export function CategorySelect({ txn, categories, disabled, onChange }: Props) {
  const current = categories.find((c) => c.name === txn.category);
  const kind = current?.kind ?? "review";
  const needsReview = kind === "review";

  return (
    <span className="flex items-center gap-2">
      <span aria-hidden className={`size-2.5 shrink-0 rounded-full ${KIND_DOT[kind]}`} />
      <select
        aria-label={`Category for ${txn.description}`}
        className={`h-10 w-full min-w-0 rounded-md border bg-surface px-2.5 text-sm disabled:cursor-wait disabled:opacity-60 md:max-w-60 ${
          needsReview ? "border-review-edge font-medium" : "border-rule-strong"
        }`}
        value={needsReview ? "" : txn.category}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
      >
        {needsReview && (
          <option value="" disabled>
            Choose a category…
          </option>
        )}
        {KIND_GROUPS.map((group) => (
          <optgroup key={group.kind} label={group.label}>
            {categories
              .filter((c) => c.kind === group.kind)
              .map((c) => (
                <option key={c.name} value={c.name}>
                  {c.name}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </span>
  );
}
