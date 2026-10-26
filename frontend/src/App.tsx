import { exportUrl } from "./api/client";
import { AlertIcon, CheckIcon } from "./components/Icons";
import { RejectedRows } from "./components/RejectedRows";
import { ReviewQueue } from "./components/ReviewQueue";
import { SummaryPanel } from "./components/SummaryPanel";
import { TransactionTable } from "./components/TransactionTable";
import { UploadPanel } from "./components/UploadPanel";
import { conventionLabel, formatDateTime, sourceFormatLabel } from "./format";
import { useStatement } from "./hooks/useStatement";

export default function App() {
  const {
    statement,
    categories,
    categoriesError,
    config,
    uploading,
    uploadError,
    retryUntil,
    savingId,
    notice,
    upload,
    save,
  } = useStatement();

  return (
    <div className="page">
      <header className="app-header">
        <h1>Statement Categorizer</h1>
        <p className="muted">
          Upload a business credit-card statement and get it sorted into tax categories. Anything
          uncertain is flagged for you to confirm.
        </p>
      </header>

      <main>
        <UploadPanel
          onUpload={upload}
          loading={uploading}
          error={uploadError}
          config={config}
          retryUntil={retryUntil}
        />

        <div className="live" aria-live="polite">
          {notice && (
            <p className={`alert ${notice.kind === "success" ? "success" : "error"}`}>
              {notice.kind === "success" ? <CheckIcon /> : <AlertIcon />}
              <span>{notice.text}</span>
            </p>
          )}
        </div>

        {categoriesError && (
          <p className="alert error" role="alert">
            <AlertIcon />
            <span>
              Could not load categories, so corrections are unavailable. {categoriesError}
            </span>
          </p>
        )}

        {uploading && !statement && (
          <p className="card empty" role="status">
            Reading your statement…
          </p>
        )}

        {!statement && !uploading && (
          <p className="card empty">No statement yet. Upload a file above to see results.</p>
        )}

        {statement && (
          <>
            <section className="card result-header" aria-label="Statement details">
              <div>
                <p className="filename">
                  <strong>{statement.filename}</strong>
                  <span className="pill pill-format">{sourceFormatLabel(statement.source_format)}</span>
                </p>
                <p className="muted">
                  {conventionLabel(statement.convention)} · {statement.currency} ·{" "}
                  {statement.summary.transaction_count} transactions · uploaded{" "}
                  {formatDateTime(statement.created_at)}
                </p>
              </div>
              <a className="button" href={exportUrl(statement.id)}>
                Export CSV
              </a>
            </section>

            {statement.warnings.length > 0 && (
              <section className="notice" aria-labelledby="notes-heading">
                <h2 id="notes-heading" className="notice-title">
                  <AlertIcon /> Notes about this file
                </h2>
                <ul>
                  {statement.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </section>
            )}

            <SummaryPanel summary={statement.summary} currency={statement.currency} />

            <ReviewQueue
              transactions={statement.transactions}
              categories={categories}
              currency={statement.currency}
              savingId={savingId}
              onSave={save}
            />

            <TransactionTable
              transactions={statement.transactions}
              categories={categories}
              currency={statement.currency}
              savingId={savingId}
              onSave={save}
            />

            <RejectedRows rows={statement.rejected_rows} />
          </>
        )}
      </main>
    </div>
  );
}
