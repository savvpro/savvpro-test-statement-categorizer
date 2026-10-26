import type { Category, Rule } from "../types";

interface Props {
  rules: Rule[];
  categories: Map<string, Category>;
  onDelete: (rule: Rule) => void;
}

export function RulesPanel({ rules, categories, onDelete }: Props) {
  if (rules.length === 0) return null;
  return (
    <section className="panel" aria-labelledby="rules-title">
      <h2 id="rules-title">What I've learned from you</h2>
      <p className="muted small">These merchants are sorted your way in every future upload.</p>
      <ul className="rule-list">
        {rules.map((r) => (
          <li key={`${r.direction}:${r.merchant_key}`}>
            <div>
              <span className="rule-list__merchant">{r.merchant_key.toUpperCase()}</span>
              <span className="muted small">
                {r.direction === "in" ? "money in" : "money out"} →{" "}
                {categories.get(r.category)?.label ?? r.category}
              </span>
            </div>
            <button
              className="icon-btn"
              aria-label={`Forget rule for ${r.merchant_key}`}
              title="Forget this rule"
              onClick={() => onDelete(r)}
            >
              ×
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
