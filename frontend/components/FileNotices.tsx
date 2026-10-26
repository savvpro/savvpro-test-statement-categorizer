import { plural } from "@/lib/format";
import type { RowIssue } from "@/lib/types";

function Notice({ title, issues }: { title: string; issues: RowIssue[] }) {
  if (issues.length === 0) return null;
  return (
    <details className="rounded-md border border-rule-strong bg-surface px-4 py-3 text-sm">
      <summary className="cursor-pointer font-medium">{title}</summary>
      <ul className="mt-2 space-y-1 text-ink-2">
        {issues.map((issue) => (
          <li key={`${issue.row}-${issue.message}`}>
            <span className="num font-medium text-ink">Row {issue.row}:</span> {issue.message}
          </li>
        ))}
      </ul>
    </details>
  );
}

/** Rows the parser could not read, and rows it read but wants a second look at. */
export function FileNotices({ skipped, warnings }: { skipped: RowIssue[]; warnings: RowIssue[] }) {
  if (skipped.length === 0 && warnings.length === 0) return null;
  return (
    <div className="space-y-2">
      <Notice
        title={`${plural(skipped.length, "row")} in your file could not be read and ${
          skipped.length === 1 ? "was" : "were"
        } skipped`}
        issues={skipped}
      />
      <Notice title={`Worth a second look (${warnings.length})`} issues={warnings} />
    </div>
  );
}
