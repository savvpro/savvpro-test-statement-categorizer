import { cn } from "@/lib/format";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-[var(--radius-md)] bg-[var(--rule-line)]",
        className
      )}
      {...props}
    />
  );
}
