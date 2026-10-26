"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Upload, FileText, CheckCircle, AlertTriangle } from "lucide-react";
import { api } from "@/lib/api";
import { qk } from "@/lib/query-keys";
import type { Account, ImportDraft } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";

type Step = "drop" | "preview";

export default function UploadPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [step, setStep] = useState<Step>("drop");
  const [draft, setDraft] = useState<ImportDraft | null>(null);
  const [accountId, setAccountId] = useState("");
  const [newAccountName, setNewAccountName] = useState("");
  const [newAccountType, setNewAccountType] = useState<"checking" | "credit_card">("checking");
  const [invertSign, setInvertSign] = useState(false);
  const [preferMdy, setPreferMdy] = useState(true);

  const { data: accounts = [] } = useQuery({
    queryKey: qk.accounts(),
    queryFn: () => api.get("/accounts") as Promise<Account[]>,
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.postForm("/imports", fd) as Promise<ImportDraft>;
    },
    onSuccess: (d) => {
      setDraft(d);
      // the preview is already flipped when the backend detected inverted signs
      setInvertSign(d.warnings.some((w) => w.toLowerCase().includes("inverted")));
      setStep("preview");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const commitMutation = useMutation({
    mutationFn: async () => {
      if (!draft) return;
      let aid = accountId;
      if (aid === "__new__") {
        if (!newAccountName.trim()) throw new Error("Enter a name for the new account");
        aid = "";
      }
      if (!aid && newAccountName) {
        const acc = await api.post("/accounts", {
          name: newAccountName.trim(), type: newAccountType, institution: "", mask: ""
        }) as Account;
        aid = acc.id;
      }
      if (!aid) throw new Error("Please select or create an account");
      const fd = new FormData();
      fd.append("account_id", aid);
      fd.append("invert_sign", String(invertSign));
      fd.append("prefer_mdy", String(preferMdy));
      return api.postForm(`/imports/${draft.draft_id}/commit`, fd) as Promise<{ statement_id: string }>;
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: qk.statements() });
      qc.invalidateQueries({ queryKey: qk.dashboard() });
      toast.success("Import complete!");
      router.push(`/statements/${(res as { statement_id: string }).statement_id}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const onDrop = useCallback((accepted: File[]) => {
    if (accepted[0]) uploadMutation.mutate(accepted[0]);
  }, [uploadMutation]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "text/csv": [".csv"], "application/x-ofx": [".ofx", ".qfx"] },
    maxSize: 5 * 1024 * 1024,
    multiple: false,
  });

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6" style={{ fontFamily: "var(--font-fraunces), Georgia, serif", color: "var(--fg)" }}>
        Upload Statement
      </h1>

      <AnimatePresence mode="wait">
        {step === "drop" && (
          <motion.div
            key="drop"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
          >
            <Card>
              <CardContent className="pt-6 space-y-6">
                {/* Dropzone */}
                <div
                  {...getRootProps()}
                  className="border-2 border-dashed rounded-[var(--radius-lg)] p-12 text-center cursor-pointer transition-colors"
                  style={{
                    borderColor: isDragActive ? "var(--accent)" : "var(--border-strong)",
                    background: isDragActive ? "var(--accent-light)" : "var(--surface-2)",
                  }}
                >
                  <input {...getInputProps()} />
                  {uploadMutation.isPending ? (
                    <div className="flex flex-col items-center gap-3">
                      <div className="w-10 h-10 border-2 rounded-full animate-spin" style={{ borderColor: "var(--accent)", borderTopColor: "transparent" }} />
                      <p className="text-sm text-[var(--fg-muted)]">Analyzing file…</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-3">
                      <Upload size={32} style={{ color: "var(--fg-faint)" }} />
                      <div>
                        <p className="font-medium text-[var(--fg)]">Drop your bank statement here</p>
                        <p className="text-sm text-[var(--fg-muted)] mt-1">CSV, OFX, or QFX · max 5 MB</p>
                      </div>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}

        {step === "preview" && draft && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="space-y-4"
          >
            {/* File info */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText size={16} style={{ color: "var(--accent)" }} />
                  {draft.filename}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {draft.warnings.length > 0 && (
                  <div className="rounded-[var(--radius-md)] p-3 flex gap-2 text-sm"
                    style={{ background: "var(--highlight-bg)", color: "var(--highlight-fg)" }}>
                    <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                    <ul className="space-y-1">
                      {draft.warnings.map((w, i) => <li key={i}>{w}</li>)}
                    </ul>
                  </div>
                )}

                {/* Account selection */}
                <div className="space-y-3">
                  <Select
                    label="Account"
                    id="account"
                    value={accountId}
                    onChange={(e) => setAccountId(e.target.value)}
                    options={[
                      { value: "", label: "Select account" },
                      ...accounts.map((a) => ({ value: a.id, label: `${a.name} (${a.type})` })),
                      { value: "__new__", label: "+ Create new account" },
                    ]}
                  />
                  {accountId === "__new__" && (
                    <input
                      className="h-10 w-full rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface)] px-3 text-sm text-[var(--fg)] focus:outline-none focus:border-[var(--accent)]"
                      placeholder="Account name (e.g. Business Checking)"
                      value={newAccountName}
                      onChange={(e) => setNewAccountName(e.target.value)}
                    />
                  )}
                  {accountId === "__new__" && (
                    <Select
                      label="New account type"
                      id="new-account-type"
                      value={newAccountType}
                      onChange={(e) => setNewAccountType(e.target.value as "checking" | "credit_card")}
                      options={[
                        { value: "checking", label: "Checking" },
                        { value: "credit_card", label: "Credit card" },
                      ]}
                    />
                  )}
                </div>

                {/* Detected mapping */}
                <div>
                  <p className="text-sm font-medium text-[var(--fg-muted)] mb-2">Detected columns</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(draft.detected_mapping).map(([role, idx]) => (
                      <div key={role} className="flex items-center gap-2 text-xs rounded-[var(--radius-sm)] px-2 py-1"
                        style={{ background: "var(--surface-2)" }}>
                        <CheckCircle size={12} style={{ color: "var(--accent)" }} />
                        <span className="text-[var(--fg-muted)]">{role}</span>
                        <span className="text-[var(--fg)] font-medium ml-auto">col {idx}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Toggles */}
                <div className="flex gap-4 flex-wrap">
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" checked={invertSign} onChange={(e) => setInvertSign(e.target.checked)} className="accent-[var(--accent)]" />
                    <span className="text-[var(--fg-muted)]">Invert signs (CC export)</span>
                  </label>
                  <label className="flex items-center gap-2 text-sm cursor-pointer">
                    <input type="checkbox" checked={preferMdy} onChange={(e) => setPreferMdy(e.target.checked)} className="accent-[var(--accent)]" />
                    <span className="text-[var(--fg-muted)]">Dates are MM/DD (US format)</span>
                  </label>
                </div>

                {/* Preview rows */}
                {draft.preview_rows.length > 0 && (
                  <div>
                    <p className="text-sm font-medium text-[var(--fg-muted)] mb-2">Preview (first 10 rows)</p>
                    <div className="overflow-x-auto rounded-[var(--radius-md)] border" style={{ borderColor: "var(--border)" }}>
                      <table className="w-full text-xs">
                        <thead style={{ background: "var(--surface-2)" }}>
                          <tr>
                            <th className="px-3 py-2 text-left text-[var(--fg-muted)] font-medium">Date</th>
                            <th className="px-3 py-2 text-left text-[var(--fg-muted)] font-medium">Description</th>
                            <th className="px-3 py-2 text-right text-[var(--fg-muted)] font-medium">Amount</th>
                          </tr>
                        </thead>
                        <tbody>
                          {draft.preview_rows.map((row, i) => (
                            <tr key={i} className="border-t" style={{ borderColor: "var(--rule-line)" }}>
                              <td className="px-3 py-2 text-[var(--fg-muted)]">{String(row.posted_date ?? "")}</td>
                              <td className="px-3 py-2 text-[var(--fg)] truncate max-w-[200px]">{String(row.description_raw ?? "")}</td>
                              <td className="px-3 py-2 text-right tabular font-medium"
                                style={{ color: Number(row.amount_cents) < 0 ? "var(--red-ink)" : "var(--accent)" }}>
                                {(Number(row.amount_cents) / 100).toFixed(2)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setStep("drop")}>Back</Button>
              <Button
                className="flex-1"
                onClick={() => commitMutation.mutate()}
                disabled={commitMutation.isPending}
              >
                {commitMutation.isPending ? "Importing…" : "Import statement"}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
