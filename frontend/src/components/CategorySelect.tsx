import { kindLabel } from "../format";
import type { Category, CategoryKind } from "../types";

interface Props {
  id: string;
  categories: Category[];
  value: string;
  onChange: (categoryId: string) => void;
  disabled?: boolean;
}

// "review" is a placeholder bucket, not something a user can assign.
const KIND_ORDER: CategoryKind[] = ["expense", "non_spending", "income"];

export function CategorySelect({ id, categories, value, onChange, disabled }: Props) {
  return (
    <select
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled || categories.length === 0}
    >
      <option value="">Choose category…</option>
      {KIND_ORDER.map((kind) => {
        const group = categories.filter((c) => c.kind === kind);
        if (group.length === 0) return null;
        return (
          <optgroup key={kind} label={kindLabel(kind)}>
            {group.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </optgroup>
        );
      })}
    </select>
  );
}
