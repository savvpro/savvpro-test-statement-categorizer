import { formatCurrency, kindLabel } from "../format";
import type { Summary } from "../types";

interface Props {
  summary: Summary;
  currency: string;
}

export function SummaryPanel({ summary, currency }: Props) {
  const money = (n: number) => formatCurrency(n, currency);
  const maxAbs = Math.max(0, ...summary.totals.map((t) => Math.abs(t.total)));

  const stats: { label: string; value: string; tone?: string }[] = [
    { label: "Total spending", value: money(summary.total_spending) },
    { label: "Refunds", value: money(summary.total_refunds) },
    { label: "Net spending", value: money(summary.net_spending), tone: "strong" },
    {
      label: "Needs review",
      value: String(summary.needs_review_count),
      tone: summary.needs_review_count > 0 ? "warn" : undefined,
    },
    { label: "Excluded (non-spending)", value: money(summary.excluded_total) },
  ];

  return (
    <section className="card" aria-labelledby="summary-heading">
      <h2 id="summary-heading">Summary</h2>
      <dl className="stats">
        {stats.map((s) => (
          <div key={s.label} className={`stat ${s.tone ?? ""}`}>
            <dt>{s.label}</dt>
            <dd>{s.value}</dd>
          </div>
        ))}
      </dl>

      {summary.totals.length === 0 ? (
        <p className="empty">No categories to show yet.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Totals per category</caption>
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col" className="num">
                  Count
                </th>
                <th scope="col" className="num">
                  Total
                </th>
                <th scope="col" className="bar-col">
                  <span className="sr-only">Share of largest category</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {summary.totals.map((t) => {
                const pct = maxAbs > 0 ? (Math.abs(t.total) / maxAbs) * 100 : 0;
                return (
                  <tr key={t.category_id}>
                    <th scope="row">
                      {t.category_name}
                      <span className="muted kind"> {kindLabel(t.kind)}</span>
                    </th>
                    <td className="num">{t.count}</td>
                    <td className={`num ${t.total < 0 ? "credit" : ""}`}>{money(t.total)}</td>
                    <td className="bar-col" aria-hidden="true">
                      <div className="bar-track">
                        <div className={`bar bar-${t.kind}`} style={{ width: `${pct}%` }} />
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
