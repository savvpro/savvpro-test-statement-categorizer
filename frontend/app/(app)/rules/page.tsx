"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Plus, Trash2, ToggleLeft, ToggleRight } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Rule, Category } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Dialog } from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

type RuleForm = {
  match_type: string;
  pattern: string;
  category_id: string;
  priority: number;
};

const EMPTY_FORM: RuleForm = { match_type: "merchant_exact", pattern: "", category_id: "", priority: 0 };

export default function RulesPage() {
  const qc = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState<RuleForm>(EMPTY_FORM);
  const [previewCount, setPreviewCount] = useState<number | null>(null);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: qk.rules(),
    queryFn: () => api.get("/rules") as Promise<Rule[]>,
  });

  const { data: categories = [] } = useQuery({
    queryKey: qk.categories(),
    queryFn: () => api.get("/categories") as Promise<Category[]>,
  });

  const createRule = useMutation({
    mutationFn: () => api.post("/rules", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.rules() });
      setDialogOpen(false);
      setForm(EMPTY_FORM);
      setPreviewCount(null);
      toast.success("Rule created");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const deleteRule = useMutation({
    mutationFn: (id: string) => api.del(`/rules/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.rules() });
      toast.success("Rule deleted");
    },
  });

  const toggleRule = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      api.patch(`/rules/${id}`, { enabled }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.rules() }),
  });

  async function handlePreview() {
    try {
      const result = await api.post("/rules/preview", form) as { match_count: number };
      setPreviewCount(result.match_count);
    } catch {
      setPreviewCount(null);
    }
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" style={{ fontFamily: "var(--font-display)" }}>Rules</h1>
          <p className="text-sm text-[var(--fg-muted)]">Custom categorization overrides, applied before the built-in brain</p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus size={16} /> New Rule
        </Button>
      </div>

      {/* Rules list */}
      <Card>
        <CardHeader>
          <CardTitle>Your Rules ({rules.length})</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4 space-y-3">
              {Array(3).fill(0).map((_, i) => <Skeleton key={i} className="h-12" />)}
            </div>
          ) : rules.length === 0 ? (
            <div className="py-12 text-center text-sm text-[var(--fg-muted)]">
              No rules yet. Create one to override the brain&apos;s default categorization.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}>
                  <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Pattern</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Type</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Category</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--fg-muted)]">Hits</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--fg-muted)]">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((rule) => (
                  <motion.tr
                    key={rule.id}
                    layout
                    style={{ borderBottom: "1px solid var(--rule-line)", opacity: rule.enabled ? 1 : 0.5 }}
                  >
                    <td className="px-4 py-3 font-mono text-xs">{rule.pattern}</td>
                    <td className="px-4 py-3">
                      <Badge variant="default">{rule.match_type.replace("_", " ")}</Badge>
                    </td>
                    <td className="px-4 py-3 text-[var(--fg-muted)]">
                      {categories.find((c) => c.id === rule.category_id)?.name ?? rule.category_id ?? "-"}
                    </td>
                    <td className="px-4 py-3 text-right tabular text-[var(--fg-muted)]">{rule.hit_count}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => toggleRule.mutate({ id: rule.id, enabled: !rule.enabled })}
                          aria-label={rule.enabled ? "Disable rule" : "Enable rule"}
                          title={rule.enabled ? "Disable rule" : "Enable rule"}
                          className="text-[var(--fg-muted)] hover:text-[var(--fg)]"
                        >
                          {rule.enabled ? <ToggleRight size={18} style={{ color: "var(--accent)" }} /> : <ToggleLeft size={18} />}
                        </button>
                        <button
                          onClick={() => deleteRule.mutate(rule.id)}
                          aria-label="Delete rule"
                          title="Delete rule"
                          className="text-[var(--fg-muted)] hover:text-[var(--red-ink)]"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>

      {/* Create rule dialog */}
      <Dialog open={dialogOpen} onClose={() => { setDialogOpen(false); setForm(EMPTY_FORM); setPreviewCount(null); }}
        title="New Rule">
        <div className="space-y-4">
          <div>
            <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Match type</label>
            <select
              value={form.match_type}
              onChange={(e) => setForm((f) => ({ ...f, match_type: e.target.value }))}
              className="w-full rounded-[var(--radius-md)] border px-3 py-2 text-sm"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
            >
              <option value="merchant_exact">Merchant exact (normalized name)</option>
              <option value="contains">Contains text</option>
              <option value="regex">Regex pattern</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Pattern</label>
            <Input
              value={form.pattern}
              onChange={(e) => { setForm((f) => ({ ...f, pattern: e.target.value })); setPreviewCount(null); }}
              placeholder={form.match_type === "merchant_exact" ? "STARBUCKS STORE" : "adobe|figma"}
            />
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Category</label>
            <select
              value={form.category_id}
              onChange={(e) => setForm((f) => ({ ...f, category_id: e.target.value }))}
              className="w-full rounded-[var(--radius-md)] border px-3 py-2 text-sm"
              style={{ background: "var(--surface)", borderColor: "var(--border)", color: "var(--fg)" }}
            >
              <option value="">Select category</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-[var(--fg-muted)] block mb-1">Priority (higher wins)</label>
            <Input
              type="number"
              value={form.priority}
              onChange={(e) => setForm((f) => ({ ...f, priority: parseInt(e.target.value) || 0 }))}
            />
          </div>

          {previewCount !== null && (
            <div className="rounded-[var(--radius-md)] px-3 py-2 text-sm"
              style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
              Matches {previewCount} existing transaction{previewCount !== 1 ? "s" : ""}
            </div>
          )}

          <div className="flex gap-2 pt-2">
            <Button variant="outline" size="sm" onClick={handlePreview}>Preview matches</Button>
            <div className="flex-1" />
            <Button variant="ghost" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={() => createRule.mutate()} disabled={!form.pattern || !form.category_id || createRule.isPending}>
              Create Rule
            </Button>
          </div>
        </div>
      </Dialog>
    </div>
  );
}
