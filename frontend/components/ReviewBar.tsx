import { plural } from "@/lib/format";

interface Props {
  total: number;
  needsReview: number;
  onlyReview: boolean;
  onFilter: (onlyReview: boolean) => void;
}

export function ReviewBar({ total, needsReview, onlyReview, onFilter }: Props) {
  const done = total - needsReview;
  const pct = total === 0 ? 100 : Math.round((done / total) * 100);

  const tab = (active: boolean) =>
    `h-9 rounded px-3 text-sm font-medium transition-colors duration-150 ${
      active ? "bg-ink text-paper" : "text-ink-2 hover:bg-sunken"
    }`;

  return (
    <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
      <div className="min-w-0 flex-1 basis-64">
        <h2 id="transactions-heading" className="text-lg font-semibold">
          {needsReview === 0
            ? "Every transaction is categorized"
            : `${plural(needsReview, "transaction")} need${needsReview === 1 ? "s" : ""} your review`}
        </h2>
        <div className="mt-3 flex items-center gap-3">
          <div
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={total}
            aria-valuenow={done}
            aria-label="Rows categorized"
            className="h-1.5 max-w-xs flex-1 overflow-hidden rounded-full bg-rule"
          >
            <div
              className="h-full rounded-full bg-accent transition-[width] duration-300"
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="num text-sm text-ink-2">
            {done} of {total} categorized
          </span>
        </div>
      </div>

      <div
        role="group"
        aria-label="Which rows to show"
        className="flex gap-1 rounded-md border border-rule-strong bg-surface p-0.5"
      >
        <button type="button" aria-pressed={!onlyReview} className={tab(!onlyReview)} onClick={() => onFilter(false)}>
          All <span className="num">{total}</span>
        </button>
        <button type="button" aria-pressed={onlyReview} className={tab(onlyReview)} onClick={() => onFilter(true)}>
          Needs review <span className="num">{needsReview}</span>
        </button>
      </div>
    </div>
  );
}
