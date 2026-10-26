import { formatCents } from "@/lib/format";
import { cn } from "@/lib/format";

interface AmountProps {
  cents: number;
  className?: string;
  showSign?: boolean;
  absolute?: boolean;
}

export function Amount({ cents, className, showSign, absolute }: AmountProps) {
  const isNeg = cents < 0;
  return (
    <span
      className={cn(
        "tabular font-medium",
        isNeg ? "text-[var(--red-ink)]" : "text-[var(--accent)]",
        className
      )}
    >
      {formatCents(cents, { showSign, absolute })}
    </span>
  );
}
