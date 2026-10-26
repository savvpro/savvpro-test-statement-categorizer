"use client";

import { useState, useEffect } from "react";
import { useTheme } from "next-themes";
import { useMutation } from "@tanstack/react-query";
import { Sun, Moon, Monitor, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { toast } from "sonner";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const [confirmReset, setConfirmReset] = useState(false);

  const seed = useMutation({
    mutationFn: () => api.post("/demo/seed"),
    onSuccess: () => toast.success("Demo data seeded"),
    onError: (e: Error) => toast.error(e.message),
  });

  const reset = useMutation({
    mutationFn: () => api.post("/demo/reset"),
    onSuccess: () => {
      setConfirmReset(false);
      toast.success("All data reset");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const themes = [
    { value: "light", label: "Light", icon: Sun },
    { value: "dark", label: "Dark", icon: Moon },
    { value: "system", label: "System", icon: Monitor },
  ];

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Settings</h1>

      {/* Theme */}
      <Card>
        <CardHeader><CardTitle>Appearance</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-[var(--fg-muted)] mb-4">Choose your color theme</p>
          <div className="flex gap-3">
            {themes.map(({ value, label, icon: Icon }) => {
              const active = mounted && theme === value;
              return (
              <button
                key={value}
                onClick={() => setTheme(value)}
                className="flex-1 flex flex-col items-center gap-2 rounded-[var(--radius-lg)] border px-4 py-4 text-sm transition-all"
                style={{
                  borderColor: active ? "var(--accent)" : "var(--border)",
                  background: active ? "var(--accent-light)" : "var(--surface)",
                  color: active ? "var(--accent)" : "var(--fg-muted)",
                }}
              >
                <Icon size={20} />
                {label}
              </button>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* About */}
      <Card>
        <CardHeader><CardTitle>About Ledgerline</CardTitle></CardHeader>
        <CardContent className="space-y-2 text-sm text-[var(--fg-muted)]">
          <p>Ledgerline categorizes bank statement transactions to IRS Schedule C lines for US freelancers and sole proprietors.</p>
          <p>All categorization is done locally using deterministic rules. No AI or external APIs are called for any categorization decision.</p>
          <p className="text-xs" style={{ color: "var(--fg-faint)" }}>Version 0.1.0 · SAVV Pro Assessment</p>
        </CardContent>
      </Card>

      {/* Data management */}
      <Card>
        <CardHeader><CardTitle>Data Management</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-sm">Seed demo data</div>
              <div className="text-xs text-[var(--fg-muted)]">Load sample transactions from fictional banks</div>
            </div>
            <Button variant="outline" onClick={() => seed.mutate()} disabled={seed.isPending}>
              {seed.isPending ? "Seeding…" : "Seed demo data"}
            </Button>
          </div>
          <div className="h-px" style={{ background: "var(--border)" }} />
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium text-sm text-[var(--red-ink)]">Reset all data</div>
              <div className="text-xs text-[var(--fg-muted)]">Delete all accounts, statements, and transactions</div>
            </div>
            <Button variant="destructive" onClick={() => setConfirmReset(true)}>
              <AlertTriangle size={14} /> Reset
            </Button>
          </div>
        </CardContent>
      </Card>

      <Dialog open={confirmReset} onClose={() => setConfirmReset(false)} title="Reset all data?">
        <p className="text-sm text-[var(--fg-muted)] mb-6">
          This will permanently delete all accounts, statements, transactions, and rules. This action cannot be undone.
        </p>
        <div className="flex gap-2 justify-end">
          <Button variant="ghost" onClick={() => setConfirmReset(false)}>Cancel</Button>
          <Button variant="destructive" onClick={() => reset.mutate()} disabled={reset.isPending}>
            {reset.isPending ? "Resetting…" : "Yes, reset everything"}
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
