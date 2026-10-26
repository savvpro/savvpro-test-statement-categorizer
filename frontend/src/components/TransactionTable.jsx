import { money, percent } from "../format";

export default function TransactionTable({ transactions }) {
  return (
    <section className="card">
      <h2>All transactions</h2>
      <div className="scroll">
        <table>
          <thead>
            <tr>
              <th>Date</th><th>Description</th><th className="num">Amount</th>
              <th>Category</th><th className="num">Conf.</th><th>Why</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id} className={t.needs_review ? "row-review" : ""}>
                <td>{t.date}</td>
                <td>
                  {t.description}
                  {t.is_duplicate && <span className="badge">duplicate?</span>}
                </td>
                <td className={`num ${Number(t.amount) < 0 ? "neg" : "pos"}`}>{money(t.amount)}</td>
                <td>
                  {t.category}
                  {t.splits.map((s, i) => (
                    <div className="split" key={i}>↳ {s.category}: {money(s.amount)}</div>
                  ))}
                </td>
                <td className="num">{percent(t.confidence)}</td>
                <td className="why">{t.explanation}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}