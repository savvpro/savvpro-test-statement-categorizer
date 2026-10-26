export function ReviewProgress({ total, pending }) {
  const done = total - pending;
  return (
    <div className={`alert ${pending ? "warn" : "ok"}`}>
      <div className="progress-text">
        {pending
          ? `${pending} of ${total} transactions need your review before totals are final.`
          : "All transactions are categorized. Your totals are ready to export."}
      </div>
      <div className="progress" role="progressbar" aria-valuenow={done} aria-valuemin={0} aria-valuemax={total}>
        <div style={{ width: `${total ? (done / total) * 100 : 0}%` }} />
      </div>
    </div>
  );
}
