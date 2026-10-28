"use client";
import { useId, useState } from "react";
import { CategorySelect, rankedCategories } from "./CategorySelect";
import { amount, confidenceWord, money, shortDate } from "@/lib/format";
import { categoryLabel, flagText, lineText, merchantName, STATUS_LABEL } from "@/lib/categories";
import type { CategoryOut, TransactionOut } from "@/lib/api/types";

export interface Draft {
  category: string;
  remember: boolean;
  similar: boolean;
}

export function DecisionPanel({
  tx,
  categories,
  draft,
  onDraft,
  onConfirm,
  onSkip,
  onRestore,
  busy,
  totalSoFar,
  similarRows,
}: {
  tx: TransactionOut;
  categories: CategoryOut[];
  draft: Draft;
  onDraft: (patch: Partial<Draft>) => void;
  onConfirm: () => void;
  onSkip: () => void;
  onRestore?: () => void;
  busy?: boolean;
  /** Cents already counted on the chosen category's Schedule E line. */
  totalSoFar?: number;
  /** The other rows "Also apply to N similar" would change, shown before applying. */
  similarRows?: TransactionOut[];
}) {
  const uid = useId();
  const [showWhy, setShowWhy] = useState(false);
  const suggested = tx.category ?? tx.brain_category;
  const picks = rankedCategories(categories, tx.direction, tx.is_refund, suggested).slice(0, 9);
  const reasons = [...tx.flags.map(flagText), ...tx.reasons];
  const shownReasons = showWhy ? reasons : reasons.slice(0, 2);
  const isDup = tx.status === "duplicate";
  const chosen = categories.find((c) => c.code === draft.category);

  return (
    <section aria-label="Decision" className="space-y-4 p-4">
      <header>
        <h2 tabIndex={-1} data-decision-heading className="text-lg font-semibold leading-snug outline-offset-2">
          {tx.description}
        </h2>
        <p className="num !text-left text-xl">
          {money(tx.amount_cents)} <span className="text-sm text-muted">{shortDate(tx.posted_date)}</span>
        </p>
        <p className="text-sm text-muted">
          {STATUS_LABEL[tx.status]}. Confidence {confidenceWord(tx.confidence)}.
        </p>
      </header>

      {reasons.length > 0 && (
        <div>
          <h3 className="font-medium">{tx.status === "needs_review" ? "Why we are asking" : "Why this category"}</h3>
          <ul className="mt-1 space-y-1 text-sm">
            {shownReasons.map((r) => (
              <li key={r}>{r}</li>
            ))}
          </ul>
          {reasons.length > 2 && (
            <button type="button" className="mt-1 text-sm text-ledger underline" onClick={() => setShowWhy((v) => !v)}>
              {showWhy ? "Show less" : `Show all ${reasons.length} reasons`}
            </button>
          )}
        </div>
      )}

      {isDup ? (
        <div>
          <p className="text-sm">This looks like a duplicate, so it is not counted. If it is a real transaction, restore it.</p>
          <button type="button" onClick={onRestore} className="mt-2 rounded-xs border border-ledger px-4 py-2 font-medium text-ledger">
            Restore as a real transaction
          </button>
        </div>
      ) : (
        <>
          <div>
            <h3 className="mb-1 font-medium" id={`${uid}-quick`}>
              Category
            </h3>
            <ul aria-labelledby={`${uid}-quick`} className="grid grid-cols-1 gap-1">
              {picks.map((c, i) => (
                <li key={c.code}>
                  <button
                    type="button"
                    aria-pressed={draft.category === c.code}
                    onClick={() => onDraft({ category: c.code })}
                    className={`flex w-full items-center gap-2 rounded-xs border px-2 py-1 text-left ${
                      draft.category === c.code ? "border-ledger bg-ledger/10 font-medium" : "border-muted bg-row"
                    }`}
                  >
                    <span className="w-4 text-muted" aria-hidden="true">
                      {i + 1}
                    </span>
                    <span className="flex-1">{c.label}</span>
                    {c.code === suggested && <span className="text-xs text-ledger">suggested</span>}
                  </button>
                </li>
              ))}
            </ul>
            <label htmlFor={`${uid}-all`} className="mb-1 mt-3 block text-sm text-muted">
              Or choose from all categories
            </label>
            <CategorySelect
              id={`${uid}-all`}
              categories={categories}
              direction={tx.direction}
              isRefund={tx.is_refund}
              value={draft.category}
              suggested={suggested}
              onChange={(code) => onDraft({ category: code })}
            />
          </div>

          <div className="space-y-1">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={draft.remember}
                onChange={(e) => onDraft({ remember: e.target.checked })}
                className="h-4 w-4 accent-ledger"
              />
              Remember for {merchantName(tx)}
            </label>
            {tx.similar_count > 0 && (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={draft.similar}
                  onChange={(e) => onDraft({ similar: e.target.checked })}
                  className="h-4 w-4 accent-ledger"
                />
                Also apply to {tx.similar_count} similar
              </label>
            )}
            {tx.similar_count > 0 && similarRows && similarRows.length > 0 && (
              <ul aria-label="Similar rows" className="ml-6 space-y-0.5 text-sm text-muted">
                {similarRows.slice(0, 5).map((r) => (
                  <li key={r.id} className="flex gap-2">
                    <span className="w-14 shrink-0">{shortDate(r.posted_date)}</span>
                    <span className="min-w-0 flex-1 truncate">{r.description}</span>
                    <span className="num shrink-0">{amount(r.amount_cents)}</span>
                  </li>
                ))}
                {similarRows.length > 5 && <li>and {similarRows.length - 5} more</li>}
              </ul>
            )}
          </div>

          <div className="flex items-center gap-4">
            <button
              type="button"
              disabled={!draft.category || busy}
              onClick={onConfirm}
              className="rounded-xs bg-ledger px-6 py-2 font-medium text-white disabled:opacity-50"
            >
              Confirm
            </button>
            <button type="button" onClick={onSkip} className="text-muted underline">
              Skip for now
            </button>
          </div>

          {chosen && (
            <p className="border-t border-rule pt-3 text-sm text-muted">
              Schedule E so far, {lineText(categories, draft.category)}:{" "}
              <span key={totalSoFar} className="total-flash num inline-block text-ink">
                {money(totalSoFar ?? 0)}
              </span>
              <br />
              Updates when you confirm.
            </p>
          )}
          {!chosen && draft.category === "" && <p className="text-sm text-muted">Pick a category to continue. Current: {categoryLabel(categories, tx.category)}.</p>}
        </>
      )}
    </section>
  );
}
