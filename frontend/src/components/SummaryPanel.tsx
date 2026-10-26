import { money } from "../api";
import type { Statement } from "../types";
import { Icon } from "./Icon";

export function SummaryPanel({
  statement,
  onReview,
}: {
  statement: Statement;
  onReview: () => void;
}) {
  const s = statement.summary;
  const format = (value: number) => money(value, statement.currency);
  const categories = [...s.categories]
    .filter((item) => item.count > 0)
    .sort((a, b) => b.net_minor - a.net_minor);
  const max = Math.max(
    1,
    ...categories.map((item) => Math.abs(item.net_minor)),
  );
  const completed = s.transaction_count - s.review_count;
  return (
    <>
      <div className="stat-grid">
        <article className="stat-card primary-stat">
          <span>
            Net business expenses <Icon name="grid" size={18} />
          </span>
          <strong>{format(s.net_expenses_minor)}</strong>
          <small>
            {format(s.spent_minor)} spent − {format(s.refund_minor)} refunded
          </small>
        </article>
        <article className="stat-card">
          <span>
            Needs your review{" "}
            <span className="tiny-amber">
              <Icon name="clock" size={16} />
            </span>
          </span>
          <strong>
            {s.review_count}
            <small>transactions</small>
          </strong>
          <small>
            {format(s.unresolved_out_minor)} out ·{" "}
            {format(s.unresolved_in_minor)} in withheld
          </small>
        </article>
        <article className="stat-card">
          <span>
            Refunds applied <Icon name="check" size={18} />
          </span>
          <strong>{format(s.refund_minor)}</strong>
          <small>Money back, reducing your expenses</small>
        </article>
      </div>
      <div className="overview-grid">
        <section
          className="panel category-panel"
          aria-labelledby="category-heading"
        >
          <div className="section-top">
            <h2 id="category-heading">Where your money went</h2>
            <span className="small muted">
              Net expenses · {statement.currency}
            </span>
          </div>
          {categories.length ? (
            <div className="category-bars">
              {categories.map((item, index) => (
                <div className="category-bar-row" key={item.category}>
                  <div>
                    <span className={`category-dot color-${index % 5}`} />
                    {item.category}
                    <span>{format(item.net_minor)}</span>
                  </div>
                  <div className="bar-track">
                    <div
                      className={`bar-fill color-${index % 5}`}
                      style={{
                        width: `${(Math.abs(item.net_minor) / max) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-category">
              <Icon name="grid" size={25} />
              <p>Accepted expenses will appear here.</p>
            </div>
          )}
          <p className="panel-note">
            Accepted rows only. Transfers, personal spending, and unresolved
            rows are excluded.
          </p>
        </section>
        <section className="panel progress-panel">
          <span className="eyebrow">YOUR REVIEW PROGRESS</span>
          <div className="progress-value">
            {completed}
            <span> / {s.transaction_count}</span>
          </div>
          <p>transactions have a decision</p>
          <div
            className="progress-track"
            role="progressbar"
            aria-label="Transactions with a decision"
            aria-valuenow={completed}
            aria-valuemin={0}
            aria-valuemax={s.transaction_count}
          >
            <div
              style={{
                width: `${(completed / Math.max(1, s.transaction_count)) * 100}%`,
              }}
            />
          </div>
          <dl className="progress-list">
            <div>
              <dt>
                <span className="status-dot green" />
                Auto-sorted
              </dt>
              <dd>{s.auto_count}</dd>
            </div>
            <div>
              <dt>
                <span className="status-dot blue" />
                Reviewed by you
              </dt>
              <dd>{s.reviewed_count}</dd>
            </div>
            <div>
              <dt>
                <span className="status-dot gray" />
                Excluded rows
              </dt>
              <dd>{s.excluded_count}</dd>
            </div>
          </dl>
          <button className="button primary full-width" onClick={onReview}>
            {s.review_count
              ? "Review remaining transactions"
              : "View completed transactions"}
            <Icon name="arrow" size={17} />
          </button>
          <p className="small muted">A wrong guess is worse than asking.</p>
        </section>
      </div>
      <details className="reconciliation">
        <summary>
          Statement reconciliation <span>Every row accounted for</span>
        </summary>
        <div className="reconciliation-grid">
          <div>
            <span>Raw statement net</span>
            <strong>{format(s.raw_net_minor)}</strong>
          </div>
          <div>
            <span>Accepted net</span>
            <strong>{format(s.accepted_net_minor)}</strong>
          </div>
          <div>
            <span>Unresolved net</span>
            <strong>{format(s.unresolved_net_minor)}</strong>
          </div>
          <div>
            <span>Excluded net</span>
            <strong>{format(s.excluded_net_minor)}</strong>
          </div>
        </div>
        <p className="small muted">
          Raw net = accepted + unresolved + excluded. Accepted net includes
          transfers and personal rows; business expenses above do not. Accepted
          income: {format(s.income_minor)}. Transfers:{" "}
          {format(s.transfer_out_minor)} out / {format(s.transfer_in_minor)} in.
        </p>
      </details>
    </>
  );
}
