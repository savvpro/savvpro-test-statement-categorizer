import { flagLabel } from "../format";
import type { Flag } from "../types";

export function FlagPills({ flags }: { flags: Flag[] }) {
  if (flags.length === 0) return null;
  return (
    <ul className="pills" aria-label="Flags">
      {flags.map((flag) => (
        <li key={flag} className={`pill pill-${flag}`}>
          {flagLabel(flag)}
        </li>
      ))}
    </ul>
  );
}
