"use client";
import { useEffect, useState } from "react";

export interface ToastState {
  id: number;
  message: string;
  undo?: () => void;
  /** Errors stay until dismissed and are announced assertively. */
  error?: boolean;
}

/** Time an Undo stays available. Hover or keyboard focus pauses the countdown. */
export const UNDO_MS = 15000;
const PLAIN_MS = 8000;

/**
 * Polite live region; the toast itself is the only floating element besides the decision panel.
 * Below 900px the decision panel is a bottom sheet (44vh), so the toast sits above it.
 */
export function Toast({ toast, onDismiss }: { toast: ToastState | null; onDismiss: () => void }) {
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (!toast || toast.error || paused) return;
    const t = setTimeout(onDismiss, toast.undo ? UNDO_MS : PLAIN_MS);
    return () => clearTimeout(t);
  }, [toast, paused, onDismiss]);

  return (
    <div
      aria-live="polite"
      role="status"
      className="pointer-events-none fixed inset-x-0 bottom-[calc(44vh+1rem)] z-30 flex justify-center px-4 min-[900px]:bottom-4"
    >
      {toast && (
        <div
          role={toast.error ? "alert" : undefined}
          onMouseEnter={() => setPaused(true)}
          onMouseLeave={() => setPaused(false)}
          onFocus={() => setPaused(true)}
          onBlur={() => setPaused(false)}
          className="panel-shadow pointer-events-auto flex items-center gap-4 rounded-md bg-ink px-4 py-2 text-white"
        >
          <span>{toast.message}</span>
          {toast.undo && (
            <button
              type="button"
              onClick={() => {
                toast.undo?.();
                onDismiss();
              }}
              className="rounded-xs px-2 font-medium text-white underline"
            >
              Undo
            </button>
          )}
          {toast.error && (
            <button type="button" onClick={onDismiss} className="rounded-xs px-2 font-medium text-white underline">
              Dismiss
            </button>
          )}
        </div>
      )}
    </div>
  );
}
