"use client";

import { useRef, useState } from "react";
import { Button } from "@/components/ui/Button";

const SAMPLES = [
  { file: "checking_bank_style.csv", label: "Checking account (bank layout)" },
  { file: "credit_card_style.csv", label: "Credit card (card layout, pending row)" },
  { file: "debit_credit_columns.csv", label: "Debit / Credit columns" },
];

type Sign = "auto" | "bank" | "card";

export function UploadPanel({ busy, error, onUpload }: { busy: boolean; error: string | null; onUpload: (file: File, sign: Sign) => void }) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [sign, setSign] = useState<Sign>("auto");

  const pick = (files: FileList | null) => {
    const file = files?.[0];
    if (file) onUpload(file, sign);
  };

  const loadSample = async (name: string) => {
    const blob = await (await fetch(`/samples/${name}`)).blob();
    onUpload(new File([blob], name, { type: "text/csv" }), sign);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          pick(e.dataTransfer.files);
        }}
        className={`flex flex-col items-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition ${
          dragging ? "border-brand-500 bg-brand-50" : "border-brand-200 bg-white"
        }`}
      >
        <span className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-50 text-brand-600">
          <svg viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 16V4m0 0-4 4m4-4 4 4M4 20h16" />
          </svg>
        </span>
        <h2 className="mt-4 text-lg font-semibold text-brand-900">Drop your statement CSV here</h2>
        <p className="mt-1 text-sm text-slate-500">Bank or credit card export, up to 5 MB.</p>
        <input ref={input} type="file" accept=".csv,text/csv" className="hidden" onChange={(e) => pick(e.target.files)} />
        <Button className="mt-6" disabled={busy} onClick={() => input.current?.click()}>
          {busy ? "Sorting your statement…" : "Choose a file"}
        </Button>
        <label className="mt-5 flex items-center gap-2 text-sm text-slate-600">
          Amount signs
          <select
            value={sign}
            onChange={(e) => setSign(e.target.value as Sign)}
            className="rounded-md border border-brand-200 bg-white px-2 py-1 text-sm"
          >
            <option value="auto">Detect automatically</option>
            <option value="bank">Bank (money out is negative)</option>
            <option value="card">Card (purchases are positive)</option>
          </select>
        </label>
      </div>

      {error && (
        <p role="alert" className="mt-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
          {error}
        </p>
      )}

      <div className="mt-8 rounded-2xl bg-brand-50 p-6">
        <p className="text-sm font-semibold text-brand-900">No statement handy? Try a fake sample:</p>
        <div className="mt-3 flex flex-wrap gap-2">
          {SAMPLES.map((s) => (
            <Button key={s.file} variant="secondary" disabled={busy} onClick={() => loadSample(s.file)}>
              {s.label}
            </Button>
          ))}
        </div>
      </div>
    </div>
  );
}
