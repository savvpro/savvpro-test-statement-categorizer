import {
  AlertCircle,
  CheckCheck,
  CircleHelp,
  Copy,
  Sparkles,
} from "lucide-react";
import type { ApiError } from "./api";
import type { Transaction } from "./types";
import { statusOf } from "./api";
export function ErrorNotice({ error }: { error: ApiError | Error }) {
  const issues = "issues" in error ? (error as ApiError).issues : [];
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={20} />
      <div>
        <strong>{error.message}</strong>
        {issues.length > 0 && (
          <>
            <ul>
              {issues.slice(0, 12).map((issue, i) => (
                <li key={i}>
                  {issue.row ? `Row ${issue.row}: ` : ""}
                  {issue.message}
                </li>
              ))}
            </ul>
            {issues.length > 12 && (
              <p>
                And {issues.length - 12} more errors. Fix the file and retry.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  );
}
export function StatusBadge({ row }: { row: Transaction }) {
  const status = statusOf(row);
  return (
    <span className={`badge ${status.toLowerCase().replace(" ", "-")}`}>
      {status === "Needs review" ? (
        <CircleHelp size={12} />
      ) : status === "Reviewed" ? (
        <CheckCheck size={12} />
      ) : status === "Excluded" ? (
        <Copy size={12} />
      ) : (
        <Sparkles size={12} />
      )}{" "}
      {status}
    </span>
  );
}
