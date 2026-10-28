import { Reveal } from "@/components/ui/Reveal";
import { SectionTitle } from "./SectionTitle";

const steps = [
  {
    title: "Download from your bank",
    text: "In online banking open the account, choose Statements or Activity, then Download / Export and pick CSV (sometimes called Excel or Spreadsheet).",
  },
  {
    title: "Check the columns",
    text: "You need a date, a description and the amount. Extra columns are fine and ignored. You don't need to edit or clean the file.",
  },
  {
    title: "Upload and review",
    text: "Drop the file on the Sort a statement page. Most rows are sorted instantly; you only answer the ones marked Needs Review.",
  },
];

const columns = [
  { name: "Date", need: "Required", names: "Date, Transaction Date, Posted Date", ok: "2026-09-03 · 09/03/2026 · Sep 03, 2026" },
  { name: "Description", need: "Required", names: "Description, Memo, Payee, Merchant", ok: "UBER *PAYOUT · SHELL OIL 57444" },
  { name: "Amount", need: "Required*", names: "Amount, Transaction Amount", ok: "-48.20 · $1,284.50 · (12.34) · 99.00 CR" },
  { name: "Debit + Credit", need: "*or both", names: "Debit / Withdrawal, Credit / Deposit", ok: "Money out in one column, money in in the other" },
  { name: "Status", need: "Optional", names: "Status", ok: "Pending rows are flagged for review" },
];

const csv = [
  ["Date", "Description", "Amount", "Balance"],
  ["09/01/2026", "UBER *PAYOUT DRIVER WEEKLY", "1284.50", "2104.18"],
  ["09/02/2026", "SHELL OIL 57444 DALLAS TX", "-48.20", "2055.98"],
  ["09/03/2026", "DOORDASH*TACO SPOT", "-23.18", "2032.80"],
];
const colTone = ["text-accent-300", "text-brand-300", "text-emerald-300", "text-slate-500"];

const samples = ["checking_bank_style.csv", "credit_card_style.csv", "debit_credit_columns.csv"];

export function CsvGuide() {
  return (
    <section id="prepare" className="scroll-mt-20 bg-gradient-to-b from-white to-brand-50/60 py-24">
      <div className="container-page">
        <SectionTitle
          eyebrow="Before you upload"
          title="Prepare your CSV in three steps"
          text="Any normal bank or credit card export works. Here is what the app looks for."
        />

        <ol className="mt-14 grid gap-5 md:grid-cols-3">
          {steps.map((s, i) => (
            <Reveal key={s.title} delay={i * 120}>
              <li className="group h-full rounded-2xl bg-white p-6 shadow-card ring-1 ring-brand-100 transition hover:-translate-y-1 hover:shadow-glow">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-bold text-white shadow-md transition group-hover:scale-110">
                  {i + 1}
                </span>
                <h3 className="mt-5 text-lg font-semibold text-brand-950">{s.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{s.text}</p>
              </li>
            </Reveal>
          ))}
        </ol>

        <div className="mt-14 grid gap-6 lg:grid-cols-[1.15fr_1fr]">
          <Reveal className="overflow-hidden rounded-2xl bg-white shadow-card ring-1 ring-brand-100">
            <div className="border-b border-brand-100 bg-brand-50/60 px-6 py-4">
              <h3 className="font-semibold text-brand-950">Columns the app reads</h3>
              <p className="mt-0.5 text-xs text-slate-500">Matched by name, in any order, even after a few title lines at the top.</p>
            </div>
            <ul className="divide-y divide-slate-100">
              {columns.map((c) => (
                <li key={c.name} className="grid gap-1 px-6 py-4 sm:grid-cols-[150px_1fr]">
                  <div>
                    <p className="font-semibold text-brand-950">{c.name}</p>
                    <span
                      className={`mt-1 inline-block rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ${
                        c.need.startsWith("Required") ? "bg-brand-50 text-brand-700 ring-brand-200" : "bg-slate-50 text-slate-600 ring-slate-200"
                      }`}
                    >
                      {c.need}
                    </span>
                  </div>
                  <div className="text-sm">
                    <p className="text-slate-700">
                      <span className="text-slate-400">Called: </span>
                      {c.names}
                    </p>
                    <p className="mt-1 font-mono text-xs text-slate-500">{c.ok}</p>
                  </div>
                </li>
              ))}
            </ul>
            <p className="border-t border-slate-100 px-6 py-3 text-xs text-slate-500">
              * One <b>Amount</b> column, or separate <b>Debit</b> and <b>Credit</b> columns. Card files with purchases as positive numbers are
              detected automatically.
            </p>
          </Reveal>

          <Reveal delay={150} className="flex flex-col gap-6">
            <div className="overflow-hidden rounded-2xl bg-brand-950 shadow-glow ring-1 ring-brand-800">
              <div className="flex items-center gap-2 border-b border-white/10 px-5 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-red-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400/80" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400/80" />
                <span className="ml-2 font-mono text-xs text-brand-200">statement.csv</span>
              </div>
              <div className="overflow-x-auto p-5">
                <table className="font-mono text-xs">
                  <tbody>
                    {csv.map((row, r) => (
                      <tr key={r}>
                        {row.map((cell, c) => (
                          <td key={c} className={`whitespace-nowrap py-1 pr-5 ${r === 0 ? "font-bold" : ""} ${colTone[c]}`}>
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="flex flex-wrap gap-4 border-t border-white/10 px-5 py-3 text-[11px] text-brand-200">
                <span><b className="text-accent-300">■</b> date</span>
                <span><b className="text-brand-300">■</b> description</span>
                <span><b className="text-emerald-300">■</b> amount: minus = money out</span>
                <span><b className="text-slate-500">■</b> ignored</span>
              </div>
            </div>

            <div className="rounded-2xl bg-white p-6 shadow-card ring-1 ring-brand-100">
              <h3 className="font-semibold text-brand-950">No file yet? Download a fake sample</h3>
              <ul className="mt-4 space-y-2">
                {samples.map((name) => (
                  <li key={name}>
                    <a
                      href={`/samples/${name}`}
                      download
                      className="flex items-center justify-between rounded-lg px-3 py-2 text-sm text-brand-700 ring-1 ring-brand-100 transition hover:bg-brand-50"
                    >
                      <span className="font-mono">{name}</span>
                      <span aria-hidden>↓</span>
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  );
}
