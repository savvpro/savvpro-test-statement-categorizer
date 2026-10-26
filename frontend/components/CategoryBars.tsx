import type { CategoryTotal } from "@/lib/api";
import { categoryBars, categoryClass, formatSignedPkr } from "@/lib/format";

export function CategoryBars({ categories }: { categories: CategoryTotal[] }) {
  return (
    <section className="panel" aria-labelledby="bars-title">
      <h2 id="bars-title">Totals by category</h2>
      <ul className="bars">
        {categoryBars(categories).map((c) => (
          <li key={c.category} className={categoryClass(c.category)}>
            <span className="chip">{c.category}</span>
            <span className="bar-track" aria-hidden="true">
              <span className="bar-fill" style={{ width: `${c.pct}%` }} />
            </span>
            <span className="bar-amount num">{formatSignedPkr(c.net)}</span>
            <span className="bar-count muted">{c.count} {c.count === 1 ? "row" : "rows"}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
