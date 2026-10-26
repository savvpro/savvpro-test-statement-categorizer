import { useState } from "react";

const EMPTY = { principal: "", rate: "", term: "", first: "" };

/** Turn the form text into the JSON the API expects, or throw a readable error. */
export function buildLoan(fields) {
  const { principal, rate, term, first } = fields;
  if (!principal || !rate || !term || !first) {
    throw new Error("Please fill in all four loan fields.");
  }
  return {
    original_principal: principal,
    annual_rate_percent: rate,
    term_months: Number(term),
    first_payment_date: first,
  };
}

/** Controlled loan form. The parent owns the state so it can read it on submit. */
export function useLoanFields() {
  return useState(EMPTY);
}

export default function LoanFields({ fields, onChange }) {
  const set = (key) => (e) => onChange({ ...fields, [key]: e.target.value });
  return (
    <div className="loan-grid">
      <label>
        Original loan amount
        <input type="number" min="1" step="any" placeholder="200000"
               value={fields.principal} onChange={set("principal")} />
      </label>
      <label>
        Annual rate (%)
        <input type="number" min="0" max="50" step="any" placeholder="6"
               value={fields.rate} onChange={set("rate")} />
      </label>
      <label>
        Term (months)
        <input type="number" min="1" max="600" placeholder="360"
               value={fields.term} onChange={set("term")} />
      </label>
      <label>
        First payment date
        <input type="date" value={fields.first} onChange={set("first")} />
      </label>
    </div>
  );
}