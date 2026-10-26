import { REVIEW, money } from "../lib/format.js";

export function CategoryTotals({ totals, activeCategory, onSelect }) {
  return (
    <section className="totals" aria-label="Totals by category">
      {totals.map(({ category, total, count }) => (
        <button
          key={category}
          className={`card ${category === REVIEW ? "review" : ""} ${activeCategory === category ? "active" : ""}`}
          onClick={() => onSelect(activeCategory === category ? "" : category)}
          title="Filter the table by this category"
        >
          <span>{category}</span>
          <strong>{money(total)}</strong>
          <small>{count} transaction{count === 1 ? "" : "s"}</small>
        </button>
      ))}
    </section>
  );
}
