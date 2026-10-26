import type { ParseErrorItem } from '../api/client'

interface Props {
  errors: ParseErrorItem[]
  skippedCount: number
}

export function ParseErrorsPanel({ errors, skippedCount }: Props) {
  return (
    <section className="panel" aria-labelledby="errors-heading">
      <h2 id="errors-heading">Lines that could not be read</h2>
      {errors.length === 0 ? (
        <p className="muted">Every line was read.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <caption className="visually-hidden">Parse errors</caption>
            <thead>
              <tr>
                <th scope="col">Row</th>
                <th scope="col">Line</th>
                <th scope="col">Why</th>
              </tr>
            </thead>
            <tbody>
              {errors.map((error) => (
                <tr key={error.row_number}>
                  <td>{error.row_number}</td>
                  <td>
                    <code className="raw-line">{error.raw_line}</code>
                  </td>
                  <td>{error.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {skippedCount > 0 && (
        <p className="muted">
          {skippedCount} blank {skippedCount === 1 ? 'line was' : 'lines were'} ignored.
        </p>
      )}
    </section>
  )
}
