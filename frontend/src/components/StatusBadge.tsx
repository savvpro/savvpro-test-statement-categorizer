import type { TxnStatus } from "../types";

const LABELS: Record<TxnStatus, string> = {
  needs_review: "Needs review",
  categorized: "Categorized",
  excluded: "Excluded",
  user_corrected: "Corrected",
};

export function StatusBadge({ status }: { status: TxnStatus }) {
  return <span className={`badge badge-${status}`}>{LABELS[status] ?? status}</span>;
}
