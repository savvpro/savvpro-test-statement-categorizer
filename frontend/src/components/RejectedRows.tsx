import type { RejectedRow } from "../types";

export function RejectedRows({ rows }: { rows: RejectedRow[] }) {
  return (
    <details className="card rejected">
      <summary>
        <h2>Rejected rows ({rows.length})</h2>
      </summary>
      {rows.length === 0 ? (
        <p className="empty">Every line in the file was parsed.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <caption className="sr-only">Lines that could not be parsed</caption>
            <thead>
              <tr>
                <th scope="col">Line</th>
                <th scope="col">Raw text</th>
                <th scope="col">Reason</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.line}>
                  <td>{row.line}</td>
                  <td>
                    <code>{row.raw}</code>
                  </td>
                  <td>{row.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </details>
  );
}
