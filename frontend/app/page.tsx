"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { ArrowRight, FileCheck, BookOpen, Zap, Lightbulb, TrendingUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { api } from "@/lib/api";
import { toast } from "sonner";

const MOCK_ROWS = [
  { desc: "SQ *JOES CAFE", amount: "-$8.50", cat: "Meals (50%)", color: "#1D6B48" },
  { desc: "GOOGLE ADS", amount: "-$150.00", cat: "Advertising L8", color: "#1D6B48" },
  { desc: "AMAZON MARKETPLACE", amount: "-$45.99", cat: "Needs Review", color: "#F2C94C", review: true },
  { desc: "STRIPE TRANSFER", amount: "+$3,200.00", cat: "Client Income L1", color: "#1D6B48" },
  { desc: "ADOBE CREATIVE", amount: "-$54.99", cat: "Software L27a", color: "#1D6B48" },
];

const PIPELINE = [
  { step: "1", title: "Normalize", desc: 'Strip processor noise. "SQ *JOES CAFE 9921 BROOKLYN NY" → "JOES CAFE"', icon: "✦" },
  { step: "2", title: "Detect Kind", desc: "Is it income, expense, transfer, CC payment, refund, or owner draw?", icon: "⬡" },
  { step: "3", title: "Score Candidates", desc: "Match merchant dict (0.95) → keywords (0.85/0.65) → user rules (0.99)", icon: "◎" },
  { step: "4", title: "Assign Status", desc: "Auto if confident; Needs Review if uncertain, mixed-use, or over $2,500", icon: "◈" },
];

export default function LandingPage() {
  const router = useRouter();
  const [seeding, setSeeding] = useState(false);

  async function handleDemo() {
    setSeeding(true);
    try {
      await api.post("/demo/seed");
      router.push("/dashboard");
    } catch {
      toast.error("Failed to seed demo data");
      setSeeding(false);
    }
  }

  return (
    <div style={{ background: "var(--bg)", color: "var(--fg)", fontFamily: "var(--font-ui)" }}>
      {/* Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 h-16"
        style={{ background: "var(--bg)", borderBottom: "1px solid var(--border)" }}>
        <div className="flex items-center gap-2">
          <BookOpen size={20} style={{ color: "var(--accent)" }} />
          <span className="font-semibold text-lg" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
            Ledgerline
          </span>
        </div>
        <div className="flex items-center gap-3">
          <Link href="/how-it-works" className="text-sm text-[var(--fg-muted)] hover:text-[var(--fg)] transition-colors">
            How it works
          </Link>
          <ThemeToggle />
          <Button size="sm" onClick={handleDemo} disabled={seeding}>
            {seeding ? "Loading…" : "Try demo"}
          </Button>
        </div>
      </nav>

      {/* Hero */}
      <section className="min-h-screen flex flex-col items-center justify-center pt-16 px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="max-w-3xl mx-auto"
        >
          <div className="inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium mb-6"
            style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
            <Zap size={12} /> Schedule C tax categorizer
          </div>
          <h1
            className="text-5xl md:text-7xl font-bold leading-tight mb-6"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif", color: "var(--fg)" }}
          >
            Your bank statements.{" "}
            <span style={{ color: "var(--accent)" }}>Tax-ready.</span>
          </h1>
          <p className="text-xl text-[var(--fg-muted)] mb-10 max-w-xl mx-auto leading-relaxed">
            Ledgerline categorizes every transaction to the right Schedule C line, automatically.
            No LLM guesses. Pure rule-based logic you can inspect.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <Button size="lg" onClick={handleDemo} disabled={seeding}>
              {seeding ? "Loading demo…" : "Try with demo data"}
              <ArrowRight size={16} />
            </Button>
            <Button size="lg" variant="outline" onClick={() => router.push("/how-it-works")}>
              How it works
            </Button>
          </div>
        </motion.div>

        {/* Animated statement strip */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.3 }}
          className="mt-16 w-full max-w-2xl mx-auto rounded-[var(--radius-xl)] overflow-hidden shadow-[var(--shadow-lg)]"
          style={{ border: "1px solid var(--border)", background: "var(--surface)" }}
        >
          <div className="px-4 py-3 border-b text-xs font-medium text-[var(--fg-muted)]"
            style={{ borderColor: "var(--border)", background: "var(--surface-2)" }}>
            Northwind Bank · Business Checking ****4892
          </div>
          {MOCK_ROWS.map((row, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.5 + i * 0.12 }}
              className="flex items-center gap-4 px-4 py-3 border-b last:border-0"
              style={{
                borderColor: "var(--rule-line)",
                background: row.review ? "var(--highlight-bg)" : undefined,
              }}
            >
              <span className="flex-1 text-sm text-[var(--fg)] truncate">{row.desc}</span>
              <span className={`text-sm tabular font-medium ${row.amount.startsWith("+") ? "text-[var(--accent)]" : "text-[var(--red-ink)]"}`}>
                {row.amount}
              </span>
              <span className="text-xs font-medium px-2 py-1 rounded-full"
                style={{
                  background: row.review ? "var(--highlight-bg)" : "var(--accent-light)",
                  color: row.review ? "var(--highlight-fg)" : "var(--accent)",
                  border: row.review ? "1px solid var(--highlight)" : undefined,
                }}>
                {row.cat}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </section>

      {/* Features */}
      <section className="py-24 px-6">
        <div className="max-w-5xl mx-auto grid md:grid-cols-3 gap-6">
          {[
            { icon: FileCheck, title: "Messy files, handled", desc: "Any bank CSV layout, OFX/QFX, preamble rows, split debit/credit columns, ambiguous date formats, inverted signs, all auto-detected." },
            { icon: Lightbulb, title: "Explains every decision", desc: "Every categorization shows its full reason trail: normalized merchant, matched keyword, confidence score, and why it flagged Needs Review." },
            { icon: TrendingUp, title: "Tax-ready export", desc: "Schedule C summary by line, with deductible percentages applied. Export to CSV, print the report, or share the link." },
          ].map(({ icon: Icon, title, desc }) => (
            <motion.div
              key={title}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.4 }}
              className="rounded-[var(--radius-xl)] p-6"
              style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
            >
              <div className="w-10 h-10 rounded-[var(--radius-md)] flex items-center justify-center mb-4"
                style={{ background: "var(--accent-light)" }}>
                <Icon size={20} style={{ color: "var(--accent)" }} />
              </div>
              <h3 className="font-semibold text-[var(--fg)] mb-2">{title}</h3>
              <p className="text-sm text-[var(--fg-muted)] leading-relaxed">{desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pipeline */}
      <section className="py-24 px-6" style={{ background: "var(--surface)" }}>
        <div className="max-w-4xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-3"
            style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>
            How the brain works
          </h2>
          <p className="text-center text-[var(--fg-muted)] mb-12">Four deterministic steps. No LLM. Every decision is traceable.</p>
          <div className="grid md:grid-cols-4 gap-4">
            {PIPELINE.map((p, i) => (
              <motion.div
                key={p.step}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="rounded-[var(--radius-lg)] p-5 text-center"
                style={{ background: "var(--bg)", border: "1px solid var(--border)" }}
              >
                <div className="text-2xl mb-3">{p.icon}</div>
                <div className="text-xs font-medium text-[var(--fg-muted)] mb-1">Step {p.step}</div>
                <h3 className="font-semibold text-[var(--fg)] mb-2">{p.title}</h3>
                <p className="text-xs text-[var(--fg-muted)] leading-relaxed">{p.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 px-6 border-t text-center" style={{ borderColor: "var(--border)" }}>
        <div className="flex items-center justify-center gap-4 mb-4">
          <BookOpen size={18} style={{ color: "var(--accent)" }} />
          <span className="font-semibold" style={{ fontFamily: "var(--font-fraunces), Georgia, serif" }}>Ledgerline</span>
        </div>
        <p className="text-sm text-[var(--fg-muted)] mb-4">
          Schedule C lines: L1 Income · L8 Advertising · L9 Car & Truck · L11 Contract Labor · L13 Equipment · L15 Insurance · L17 Legal · L18 Office · L20b Rent · L24b Meals · L25 Utilities · L27a Other
        </p>
        <ThemeToggle className="mx-auto" />
      </footer>
    </div>
  );
}
