"use client";

import { forwardRef } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/format";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 font-medium rounded-[var(--radius-md)] transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 cursor-pointer",
  {
    variants: {
      variant: {
        default:
          "bg-[var(--accent)] text-[var(--accent-fg)] hover:opacity-90 shadow-[var(--shadow-sm)]",
        outline:
          "border border-[var(--border-strong)] bg-transparent text-[var(--fg)] hover:bg-[var(--surface-2)]",
        ghost:
          "bg-transparent text-[var(--fg-muted)] hover:bg-[var(--surface-2)] hover:text-[var(--fg)]",
        destructive:
          "bg-[var(--red-ink)] text-white hover:opacity-90 shadow-[var(--shadow-sm)]",
      },
      size: {
        sm: "h-8 px-3 text-sm",
        md: "h-10 px-4 text-sm",
        lg: "h-12 px-6 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
);
Button.displayName = "Button";
