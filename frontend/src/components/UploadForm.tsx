"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useRef, useState } from "react";
import { AppError, MAX_UPLOAD_BYTES } from "@/lib/api/client";
import { useUpload } from "@/lib/api/hooks";
import type { AccountType } from "@/lib/api/types";

const EXT = /\.(csv|ofx|qfx)$/i;

export function checkFile(file: File): string | null {
  if (!EXT.test(file.name))
    return "Only CSV, OFX or QFX files can be read. Export the statement in one of those formats.";
  if (file.size > MAX_UPLOAD_BYTES)
    return "The file is larger than 5 MB. Export a shorter date range and upload again.";
  if (file.size === 0) return "That file is empty. Export the statement again and choose the new file.";
  return null;
}

export function UploadForm() {
  const router = useRouter();
  const upload = useUpload();
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [accountType, setAccountType] = useState<AccountType>("checking");
  const [error, setError] = useState<AppError | string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function send(file: File, type: AccountType = accountType) {
    const problem = checkFile(file);
    if (problem) {
      setError(problem);
      return;
    }
    setError(null);
    try {
      const st = await upload.mutateAsync({ file, accountType: type });
      router.push(`/statements/${st.id}`);
    } catch (e) {
      setError(e instanceof AppError ? e : "Something went wrong. Try again in a moment.");
    }
  }

  async function loadSample(name: string, type: AccountType) {
    setAccountType(type);
    try {
      const res = await fetch(`/samples/${name}`);
      if (!res.ok) throw new Error("missing");
      const blob = await res.blob();
      await send(new File([blob], name, { type: "text/csv" }), type);
    } catch {
      setError("The sample file could not be loaded. Choose a file from your computer instead.");
    }
  }

  const busy = upload.isPending;
  const message = typeof error === "string" ? error : error?.message;

  return (
    <form onSubmit={(e) => e.preventDefault()} className="space-y-6">
      <fieldset>
        <legend className="mb-2 font-medium">Account</legend>
        <div className="flex gap-6">
          {(
            [
              ["checking", "Checking"],
              ["credit_card", "Credit card"],
            ] as const
          ).map(([v, label]) => (
            <label key={v} className="flex cursor-pointer items-center gap-2">
              <input
                type="radio"
                name="account_type"
                value={v}
                checked={accountType === v}
                onChange={() => setAccountType(v)}
                className="h-4 w-4 accent-ledger"
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept=".csv,.ofx,.qfx"
          className="peer sr-only"
          disabled={busy}
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void send(f);
            e.target.value = "";
          }}
        />
        <label
          htmlFor={inputId}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            const f = e.dataTransfer.files[0];
            if (f) void send(f);
          }}
          className={`block cursor-pointer rounded-md peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-ledger border border-dashed px-6 py-10 ${
            dragging ? "border-ledger bg-row" : "border-muted bg-row/60"
          }`}
        >
          <span className="block text-lg font-medium">
            {busy ? "Reading your statement..." : "Drop a CSV or OFX file here, or choose a file"}
          </span>
          <span className="mt-1 block text-muted">Up to 5 MB. Exports from most US banks work.</span>
        </label>
      </div>

      <div aria-live="polite" role="status">
        {busy && <p className="text-muted">Sorting every transaction. This takes a few seconds.</p>}
        {message && !busy && (
          <div role="alert" className="border-l-4 border-error bg-row px-4 py-3 text-error">
            <p>{message}</p>
            {error instanceof AppError && error.rowErrors.length > 0 && (
              <ul className="mt-2 list-disc pl-5 text-ink">
                {error.rowErrors.slice(0, 8).map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            )}
            {error instanceof AppError && error.existingId && (
              <p className="mt-2 text-ink">
                <Link href={`/statements/${error.existingId}`} className="font-medium text-ledger underline">
                  Open the existing statement
                </Link>
              </p>
            )}
          </div>
        )}
      </div>

      <p className="text-muted">
        No statement handy? Use a sample:{" "}
        <button type="button" className="text-ledger underline" onClick={() => void loadSample("checking_q1_2026.csv", "checking")}>
          Checking, Jan to Mar
        </button>
        ,{" "}
        <button type="button" className="text-ledger underline" onClick={() => void loadSample("card_q1_2026.csv", "credit_card")}>
          Credit card
        </button>
      </p>
    </form>
  );
}
