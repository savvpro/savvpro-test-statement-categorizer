import { money, percent } from "../lib/format.js";

export function TaxEstimatePanel({ estimate }) {
  if (!estimate) return null;
  const lines = [
    ["Business income", estimate.income],
    [`Deduction (${estimate.deduction_used})`, -estimate.deduction],
    ["Taxable profit", estimate.profit],
    ["Income tax", estimate.income_tax],
    ["Class 4 National Insurance", estimate.class4_nic],
  ];
  return (
    <section className="panel">
      <h2>Self Assessment estimate <small>{estimate.tax_year}</small></h2>
      <dl className="tax-grid">
        {lines.map(([label, value]) => (
          <div key={label}><dt>{label}</dt><dd>{money(value)}</dd></div>
        ))}
        <div className="total"><dt>Estimated tax to set aside</dt><dd>{money(estimate.total_due)}</dd></div>
      </dl>
      <p className="hint">That is about {percent(estimate.set_aside_rate)} of income in this statement.</p>
      <ul className="notes">{estimate.notes.map((n) => <li key={n}>{n}</li>)}</ul>
    </section>
  );
}
