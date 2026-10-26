import { ArrowUpRight, ChartNoAxesCombined } from "lucide-react";
import { money } from "../api";
import type { Statement } from "../types";

export function CategoryBreakdown({
  statement,
  onCategory,
}: {
  statement: Statement;
  onCategory: (category: string) => void;
}) {
  const entries = Object.entries(statement.summary.categories).sort(
    (a, b) => b[1] - a[1],
  );
  const max = Math.max(...entries.map(([, amount]) => Math.abs(amount)), 1);
  return (
    <section className="panel breakdown">
      <div className="panel-title">
        <div>
          <h2>Where it all goes</h2>
          <p>Net expenses by category</p>
        </div>
        <ChartNoAxesCombined size={20} />
      </div>
      {entries.length ? (
        <div className="category-bars">
          {entries.map(([category, value], i) => (
            <button
              className="category-bar"
              aria-label={`View ${category} transactions`}
              key={category}
              onClick={() => onCategory(category)}
            >
              <div>
                <span>
                  <i className={`category-dot tone-${i % 6}`} />
                  {category}
                </span>
                <strong>
                  {money(value, statement.currency)}
                  <ArrowUpRight size={13} />
                </strong>
              </div>
              <div className="bar-track">
                <div
                  className={`bar-fill tone-${i % 6}`}
                  style={{
                    width: `${Math.max(2, (Math.abs(value) / max) * 100)}%`,
                  }}
                />
              </div>
            </button>
          ))}
        </div>
      ) : (
        <div className="small-empty">
          Your category totals will appear as you review transactions.
        </div>
      )}
      <p className="subtle-note">
        Refunds reduce their category. Pending rows and transfers are excluded.
      </p>
    </section>
  );
}
