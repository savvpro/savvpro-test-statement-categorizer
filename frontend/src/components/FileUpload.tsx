"use client";

import { useRef, useState, DragEvent, ChangeEvent } from "react";
import clsx from "clsx";

interface FileUploadProps {
  onUpload: (file: File) => void;
  loading: boolean;
}

export default function FileUpload({ onUpload, loading }: FileUploadProps) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) onUpload(file);
  }

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  }

  return (
    <div
      onClick={() => !loading && inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      className={clsx(
        "relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-8 py-16 text-center transition-colors cursor-pointer select-none",
        dragging
          ? "border-brand-500 bg-brand-50"
          : "border-gray-300 bg-white hover:border-brand-500 hover:bg-brand-50",
        loading && "pointer-events-none opacity-60"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.ofx,.qfx"
        className="sr-only"
        onChange={handleChange}
        disabled={loading}
      />

      {/* Icon */}
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-brand-100">
        <svg
          className="h-7 w-7 text-brand-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      <div>
        <p className="text-sm font-semibold text-gray-700">
          {loading ? "Processing…" : "Drop your statement here"}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          CSV, OFX or QFX · max 10 MB
        </p>
      </div>

      {!loading && (
        <span className="rounded-full border border-gray-300 px-4 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
          Browse files
        </span>
      )}
    </div>
  );
}
