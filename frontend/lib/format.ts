import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatCents(
  cents: number,
  opts?: { showSign?: boolean; absolute?: boolean }
): string {
  const value = opts?.absolute ? Math.abs(cents) : cents;
  const dollars = Math.abs(value) / 100;
  const formatted = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(dollars);
  if (opts?.showSign) {
    return value >= 0 ? `+${formatted}` : `-${formatted}`;
  }
  return value < 0 ? `-${formatted}` : formatted;
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr + (dateStr.length === 10 ? "T00:00:00" : ""));
  return d.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatConfidence(conf: number): string {
  return `${Math.round(conf * 100)}%`;
}
