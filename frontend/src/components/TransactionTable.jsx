const money = (n) => n.toLocaleString(undefined, { style: "currency", currency: "USD" });

export default function TransactionTable({ rows, categories, onChange }) {
  if (rows.length === 0) return <p className="empty">No rows to show here.</p>;
  return (
    <div className="table-wrap">
      <table className="transactions">
        <thead>
          <tr>
            <th>Date</th>
            <th>Description</th>
            <th className="num">Amount</th>
            <th>Category</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id} className={row.category === "Needs Review" ? "review" : ""}>
              <td>{row.date}</td>
              <td>
                {row.description}
                <small>{row.reason}</small>
                {row.possible_duplicate && <small className="dupe">Possible duplicate: same date, amount and merchant appear twice.</small>}
              </td>
              <td className="num">{money(row.amount)}</td>
              <td>
                <select
                  aria-label={`Category for ${row.description}`}
                  value={row.category}
                  onChange={(e) => onChange(row, e.target.value)}
                >
                  {categories.map((c) => <option key={c}>{c}</option>)}
                </select>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
