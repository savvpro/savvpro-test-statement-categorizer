import type { LucideIcon } from "lucide-react";
import { AlertTriangle, XCircle } from "lucide-react";
import type { Status } from "@/lib/api";

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function Card({
  className,
  children,
  as: Tag = "section",
  ...rest
}: React.HTMLAttributes<HTMLElement> & { as?: "section" | "div" | "aside" }) {
  return (
    <Tag className={cx("rounded-xl border border-line bg-card", className)} {...rest}>
      {children}
    </Tag>
  );
}

export type Tone = "accent" | "amber" | "blue" | "red" | "green" | "grey";

const toneCircle: Record<Tone, string> = {
  accent: "bg-accent-soft text-accent",
  amber: "bg-amber-soft text-amber",
  blue: "bg-blue-soft text-blue",
  red: "bg-red-soft text-red",
  green: "bg-green-soft text-green",
  grey: "bg-grey-soft text-muted",
};

export function IconCircle({
  icon: Icon,
  tone = "accent",
  size = "md",
  square = false,
}: {
  icon: LucideIcon;
  tone?: Tone;
  size?: "sm" | "md" | "lg";
  square?: boolean;
}) {
  const box = size === "sm" ? "h-8 w-8" : size === "lg" ? "h-11 w-11" : "h-10 w-10";
  const icon = size === "sm" ? 16 : size === "lg" ? 22 : 20;
  return (
    <span
      aria-hidden="true"
      className={cx(
        "inline-flex shrink-0 items-center justify-center",
        square ? "rounded-lg" : "rounded-full",
        box,
        toneCircle[tone],
      )}
    >
      <Icon size={icon} strokeWidth={1.75} />
    </span>
  );
}

const statusStyle: Record<Status, { label: string; className: string }> = {
  auto: { label: "Auto", className: "bg-accent-soft text-accent" },
  needs_review: { label: "Needs Review", className: "bg-amber-soft text-amber" },
  learned: { label: "Learned", className: "bg-blue-soft text-blue" },
  user: { label: "Edited", className: "bg-blue-soft text-blue" },
  duplicate: { label: "Duplicate", className: "bg-red-soft text-red" },
  not_spending: { label: "Not spending", className: "bg-grey-soft text-muted" },
};

export const STATUS_LABEL: Record<Status, string> = Object.fromEntries(
  Object.entries(statusStyle).map(([k, v]) => [k, v.label]),
) as Record<Status, string>;

export function StatusPill({ status }: { status: Status }) {
  const s = statusStyle[status] ?? { label: status, className: "bg-grey-soft text-muted" };
  return (
    <span
      className={cx(
        "inline-flex items-center whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium",
        s.className,
      )}
    >
      {s.label}
    </span>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <span aria-hidden="true" className={cx("block animate-pulse rounded-md bg-grey-soft", className)} />;
}

export function Notice({
  tone = "amber",
  title,
  children,
  action,
}: {
  tone?: "amber" | "red";
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
}) {
  const Icon = tone === "red" ? XCircle : AlertTriangle;
  return (
    <div
      role={tone === "red" ? "alert" : "status"}
      className={cx(
        "flex items-start gap-3 rounded-xl border px-4 py-3 text-sm",
        tone === "red" ? "border-red/25 bg-red-soft" : "border-amber-line/40 bg-amber-soft",
      )}
    >
      <Icon
        size={18}
        strokeWidth={1.75}
        aria-hidden="true"
        className={cx("mt-0.5 shrink-0", tone === "red" ? "text-red" : "text-amber")}
      />
      <div className="min-w-0 flex-1">
        <p className={cx("font-medium", tone === "red" ? "text-red" : "text-amber")}>{title}</p>
        {children ? <div className="mt-1 text-ink/80">{children}</div> : null}
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export const buttonPrimary =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60";

export const buttonSecondary =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-line bg-card px-4 text-sm font-medium text-ink transition-colors hover:bg-page focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60";

export const fieldClass =
  "h-10 w-full rounded-lg border border-line bg-card px-3 text-sm text-ink placeholder:text-faint transition-colors hover:border-line-strong focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/15";
