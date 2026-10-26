import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/format";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
  {
    variants: {
      variant: {
        auto: "bg-[var(--accent-light)] text-[var(--accent)]",
        review: "bg-[var(--highlight-bg)] text-[var(--highlight-fg)]",
        confirmed: "bg-[var(--accent-light)] text-[var(--accent)]",
        income: "bg-[var(--accent-light)] text-[var(--accent)]",
        expense: "bg-[var(--red-bg)] text-[var(--red-ink)]",
        default: "bg-[var(--surface-2)] text-[var(--fg-muted)]",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
