import type { AmountConvention, CategoryKind, Flag, SourceFormat } from "./types";

export function formatCurrency(value: number, currency = "USD"): string {
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(value);
  } catch {
    // Unknown currency code: fall back to a plain number with the code.
    return `${value.toFixed(2)} ${currency}`;
  }
}

export function formatDate(iso: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!match) return iso;
  const [, y, m, d] = match;
  // Build in UTC so the displayed day never shifts with the local timezone.
  const date = new Date(Date.UTC(Number(y), Number(m) - 1, Number(d)));
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(date);
}

export function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

const FLAG_LABELS: Record<Flag, string> = {
  refund: "Refund",
  possible_duplicate: "Possible duplicate",
  foreign_currency: "Foreign currency",
  large_amount: "Large amount",
  ambiguous_merchant: "Ambiguous merchant",
  unmatched_refund: "Unmatched refund",
};

export function flagLabel(flag: Flag): string {
  return FLAG_LABELS[flag] ?? flag.replace(/_/g, " ");
}

const CONVENTION_LABELS: Record<AmountConvention, string> = {
  auto: "Auto-detect",
  negative_is_spending: "Negative amounts are spending",
  positive_is_spending: "Positive amounts are spending",
};

export function conventionLabel(convention: AmountConvention): string {
  return CONVENTION_LABELS[convention] ?? convention;
}

const KIND_LABELS: Record<CategoryKind, string> = {
  expense: "Expenses",
  non_spending: "Non-spending (excluded)",
  income: "Income",
  review: "Needs review",
};

export function kindLabel(kind: CategoryKind): string {
  return KIND_LABELS[kind] ?? kind;
}

export function pluralize(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}

export function savedMessage(updatedCount: number, applyToSimilar: boolean): string {
  if (applyToSimilar && updatedCount > 0) {
    return `Saved. ${pluralize(updatedCount, "similar transaction")} updated.`;
  }
  return "Saved.";
}

const FORMAT_GROUPS: { label: string; exts: string[] }[] = [
  { label: "CSV", exts: [".csv", ".tsv", ".txt"] },
  { label: "Excel", exts: [".xlsx", ".xls"] },
  { label: "PDF", exts: [".pdf"] },
  { label: "OFX", exts: [".ofx", ".qfx"] },
  { label: "ISO 20022 XML", exts: [".xml"] },
  { label: "SWIFT MT940", exts: [".sta", ".mt940", ".940", ".dat"] },
];

/** Friendly names for the accepted extensions, one entry per format family. */
export function acceptedFormatsLabel(extensions: string[]): string {
  const labels = FORMAT_GROUPS.filter((g) => g.exts.some((e) => extensions.includes(e))).map(
    (g) => g.label,
  );
  const known = new Set(FORMAT_GROUPS.flatMap((g) => g.exts));
  const others = extensions.filter((e) => !known.has(e)).map((e) => e.slice(1).toUpperCase());
  return [...labels, ...others].join(", ");
}

const SOURCE_LABELS: Record<SourceFormat, string> = {
  csv: "CSV",
  xlsx: "Excel",
  pdf: "PDF",
  ofx: "OFX",
  camt053: "ISO 20022 camt.053",
  mt940: "SWIFT MT940",
};

export function sourceFormatLabel(format: SourceFormat): string {
  return SOURCE_LABELS[format] ?? String(format).toUpperCase();
}

export function formatMb(mb: number): string {
  return Number.isInteger(mb) ? String(mb) : mb.toFixed(1);
}

/** Returns a friendly message if the file would be rejected, otherwise null. */
export function checkFile(
  file: { name: string; size: number },
  config: { max_upload_mb: number; accepted_extensions: string[] },
): string | null {
  const dot = file.name.lastIndexOf(".");
  const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : "";
  if (!config.accepted_extensions.includes(ext)) {
    return `"${file.name}" is not a supported file type. Accepted: ${acceptedFormatsLabel(config.accepted_extensions)}.`;
  }
  if (file.size === 0) {
    return `"${file.name}" is empty.`;
  }
  if (file.size > config.max_upload_mb * 1024 * 1024) {
    return `"${file.name}" is ${(file.size / (1024 * 1024)).toFixed(1)} MB. The limit is ${formatMb(config.max_upload_mb)} MB.`;
  }
  return null;
}
