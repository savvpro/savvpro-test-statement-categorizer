import type { SkippedRow } from "../types";

export function Notices({ warnings, skipped }: { warnings: string[]; skipped: SkippedRow[] }) {
  if (warnings.length === 0 && skipped.length === 0) return null;
  return (
    <div className="notice" role="status">
      {warnings.map((w) => (
        <p key={w}>{w}</p>
      ))}
      {skipped.length > 0 && (
        <details>
          <summary>
            {skipped.length} line{skipped.length === 1 ? " was" : "s were"} not imported
          </summary>
          <ul>
            {skipped.map((s) => (
              <li key={s.line}>
                <strong>Line {s.line}:</strong> {s.reason}{" "}
                <code className="muted">{s.content}</code>
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
