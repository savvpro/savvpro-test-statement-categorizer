import {
  ArrowDownLeft,
  ArrowUpRight,
  CircleHelp,
  ReceiptText,
} from "lucide-react";
import { money } from "../api";
import type { Statement } from "../types";

export function SummaryCards({ statement }: { statement: Statement }) {
  const s = statement.summary;
  const items = [
    {
      label: "Net business expenses",
      value: money(s.net_expenses_cents, statement.currency),
      hint: `${money(s.refunds_cents, statement.currency)} in refunds accounted for`,
      icon: ArrowUpRight,
    },
    {
      label: "Client income",
      value: money(s.income_cents, statement.currency),
      hint: "Confirmed incoming payments",
      icon: ArrowDownLeft,
    },
    {
      label: "Needs your review",
      value: String(s.needs_review).padStart(2, "0"),
      hint: s.needs_review
        ? "Kept out of totals until confirmed"
        : "Everything has a category",
      icon: CircleHelp,
    },
    {
      label: "Transactions",
      value: String(s.transaction_count),
      hint: `${s.excluded_count} transfers, personal or excluded`,
      icon: ReceiptText,
    },
  ];
  return (
    <div className="stats-grid">
      {items.map((item, index) => (
        <section
          className={`stat-card ${index === 2 && s.needs_review ? "stat-review" : ""}`}
          key={item.label}
        >
          <div className="stat-label">
            <span>{item.label}</span>
            <item.icon size={18} />
          </div>
          <div className="stat-value">{item.value}</div>
          <p>{item.hint}</p>
        </section>
      ))}
    </div>
  );
}
