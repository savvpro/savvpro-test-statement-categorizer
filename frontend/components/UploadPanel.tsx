"use client";

import { useState } from "react";
import { KIND_DOT, btnSecondary } from "@/lib/ui";
import type { Kind } from "@/lib/types";

interface Props {
  busy: boolean;
  onUpload: (file: File, purchasesPositive: boolean) => void;
  onSample: (purchasesPositive: boolean) => void;
}

const TREATMENT: { kind: Kind; title: string; text: string }[] = [
  {
    kind: "income",
    title: "Income",
    text: "Platform payouts from Uber, Careem, Foodpanda and similar.",
  },
  {
    kind: "deductible",
    title: "Business expenses",
    text: "Fuel, car maintenance, tolls and parking, phone and internet, platform fees.",
  },
  {
    kind: "personal",
    title: "Personal",
    text: "Everyday spending that is not deductible.",
  },
  {
    kind: "excluded",
    title: "Not spending",
    text: "Transfers between your accounts and credit card payments are left out of the totals.",
  },
  {
    kind: "refund",
    title: "Refunds",
    text: "Money back. It reduces the expense it reverses and is never counted as income.",
  },
  {
    kind: "review",
    title: "Needs review",
    text: "Cash withdrawals, unknown merchants, anything the app is not sure about. It asks instead of guessing.",
  },
];

export function UploadPanel({ busy, onUpload, onSample }: Props) {
  const [dragging, setDragging] = useState(false);
  const [purchasesPositive, setPurchasesPositive] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  function pick(file: File | undefined) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv")) {
      setProblem("That is not a .csv file. Export your statement from your bank as CSV.");
      return;
    }
    setProblem(null);
    onUpload(file, purchasesPositive);
  }

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] lg:gap-16">
      <section aria-labelledby="upload-heading">
        <h1
          id="upload-heading"
          className="text-3xl font-semibold tracking-tight text-balance sm:text-4xl"
        >
          Sort your bank statement for tax time
        </h1>
        <p className="mt-4 max-w-xl text-base leading-relaxed text-ink-2">
          Upload a CSV from your bank. Every transaction gets a category and a plain-language
          reason. Anything the app is not sure about is flagged for you, never guessed.
        </p>

        <div className="mt-8">
          <input
            id="statement-file"
            type="file"
            accept=".csv,text/csv"
            className="peer sr-only"
            disabled={busy}
            onChange={(e) => {
              pick(e.target.files?.[0]);
              e.target.value = ""; // allow choosing the same file again
            }}
          />
          <label
            htmlFor="statement-file"
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              if (!busy) pick(e.dataTransfer.files?.[0]);
            }}
            className={`flex min-h-44 cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 text-center transition-colors duration-150 peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-focus ${
              dragging ? "border-accent bg-sunken" : "border-rule-strong bg-surface hover:bg-sunken"
            } ${busy ? "cursor-progress opacity-70" : ""}`}
          >
            {busy ? (
              <span className="flex items-center gap-3 text-base font-medium" role="status">
                <span
                  aria-hidden
                  className="size-4 rounded-full border-2 border-rule-strong border-t-accent motion-safe:animate-spin"
                />
                Reading your statement…
              </span>
            ) : (
              <>
                <span className="text-base font-medium">Choose a CSV file</span>
                <span className="text-sm text-ink-2">or drop it here</span>
              </>
            )}
          </label>

          {problem && (
            <p role="alert" className="mt-3 text-sm text-neg">
              {problem}
            </p>
          )}

          <label className="mt-5 flex items-start gap-3 text-sm">
            <input
              type="checkbox"
              className="mt-0.5 size-4 accent-accent"
              checked={purchasesPositive}
              onChange={(e) => setPurchasesPositive(e.target.checked)}
            />
            <span>
              <span className="font-medium">Purchases show as positive numbers</span>
              <span className="block text-ink-2">
                Typical for credit card exports with a single Amount column. Leave this off for
                bank accounts.
              </span>
            </span>
          </label>

          <div className="mt-6 flex flex-wrap items-center gap-3 text-sm text-ink-2">
            <span>No statement handy?</span>
            <button
              type="button"
              className={btnSecondary}
              disabled={busy}
              onClick={() => onSample(purchasesPositive)}
            >
              Try the sample statement
            </button>
          </div>
        </div>
      </section>

      <aside aria-labelledby="treatment-heading">
        <h2 id="treatment-heading" className="text-sm font-semibold uppercase tracking-wide text-ink-2">
          How each row is treated
        </h2>
        <dl className="mt-4 divide-y divide-rule border-y border-rule">
          {TREATMENT.map((item) => (
            <div key={item.title} className="py-3">
              <dt className="flex items-center gap-2 text-sm font-medium">
                <span aria-hidden className={`size-2.5 rounded-full ${KIND_DOT[item.kind]}`} />
                {item.title}
              </dt>
              <dd className="mt-1 pl-[1.125rem] text-sm leading-relaxed text-ink-2">{item.text}</dd>
            </div>
          ))}
        </dl>
      </aside>
    </div>
  );
}
