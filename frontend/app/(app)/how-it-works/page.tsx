"use client";

import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";

const PIPELINE_STEPS = [
  {
    n: "1",
    title: "Normalize",
    description: 'Strip processor prefixes, store numbers, URLs, and trailing state codes from raw bank descriptions.',
    example: '"SQ *JOES CAFE 9921 BROOKLYN NY" → "JOES CAFE"',
    detail: 'Patterns stripped: SQ*, TST*, PAYPAL*, POS DEBIT, CHECKCARD, ACH, URL domains, phone numbers, store # codes, trailing 2-letter state codes.',
    color: "var(--accent)",
  },
  {
    n: "2",
    title: "Detect Kind",
    description: "Classify the transaction type before attempting category scoring.",
    example: '"IRS USATAXPYMT" → Tax Payment (kind: tax_payment)',
    detail: "Kinds: Credit-Card Payment, Transfer, Tax Payment, Owner Draw, Interest (income/expense), Fee, Refund, Income, Expense, Unknown.",
    color: "var(--accent)",
  },
  {
    n: "3",
    title: "Score Candidates",
    description: "Evidence-based scoring with fixed weights, no machine learning.",
    example: '"ADOBE CREATIVE CLOUD" → software (0.95 dict match)',
    detail: "User rule (0.99) > Merchant dict exact (0.95) > Strong keyword (0.85) > Weak keyword (0.65). Top score wins. Margin between top-2 checked for conflicts.",
    color: "var(--accent)",
  },
  {
    n: "4",
    title: "Assign Status",
    description: 'Auto if confident and unambiguous. "Needs Review" if any trigger fires.',
    example: '"AMAZON MARKETPLACE" → supplies (0.95), but Needs Review (mixed-use merchant)',
    detail: "Needs Review triggers: confidence < 0.75, top-2 margin < 0.15 (conflict), mixed-use merchant, equipment > $2,500, unknown inflow, owner draw.",
    color: "var(--highlight)",
  },
];

const REVIEW_TRIGGERS = [
  {
    trigger: "Confidence below threshold",
    example: 'A transaction with a new merchant matches only a weak keyword (0.65). Below the 0.75 default threshold.',
    fix: "Assign the correct category. Optionally create a rule to handle this merchant automatically next time.",
  },
  {
    trigger: "Top-2 conflict (small margin)",
    example: '"STUDIO RENTAL" scores 0.80 for rent_cowork and 0.70 for contract_labor. Margin = 0.10 < 0.15.',
    fix: "Pick the right category. The brain doesn\'t have enough signal to be sure. You do.",
  },
  {
    trigger: "Mixed-use merchant",
    example: '"AMAZON MARKETPLACE": Amazon sells office supplies AND personal items. No way to know without context.',
    fix: "Classify this purchase. If you always use Amazon for business, create a rule: Amazon → Supplies.",
  },
  {
    trigger: "Equipment over $2,500",
    example: '"B&H PHOTO VIDEO EQUIPMENT" for $3,200, above the de-minimis threshold where Section 179 election or depreciation may apply.',
    fix: "Confirm. Consult your tax advisor about whether to expense or depreciate the item.",
  },
];

const TAXONOMY_ROWS = [
  { slug: "client_income", name: "Client Income", line: "Line 1", pct: "n/a" },
  { slug: "other_income", name: "Other Income", line: "Line 6", pct: "n/a" },
  { slug: "advertising", name: "Advertising", line: "Line 8", pct: "100%" },
  { slug: "car_truck", name: "Car & Truck", line: "Line 9", pct: "100%" },
  { slug: "commissions", name: "Commissions & Fees", line: "Line 10", pct: "100%" },
  { slug: "contract_labor", name: "Contract Labor", line: "Line 11", pct: "100%" },
  { slug: "equipment", name: "Equipment", line: "Line 13", pct: "100%" },
  { slug: "insurance", name: "Insurance", line: "Line 15", pct: "100%" },
  { slug: "interest_expense", name: "Business Interest", line: "Line 16b", pct: "100%" },
  { slug: "legal_professional", name: "Legal & Professional", line: "Line 17", pct: "100%" },
  { slug: "office", name: "Office Expense", line: "Line 18", pct: "100%" },
  { slug: "rent_cowork", name: "Rent (Coworking)", line: "Line 20b", pct: "100%" },
  { slug: "repairs", name: "Repairs & Maintenance", line: "Line 21", pct: "100%" },
  { slug: "supplies", name: "Supplies", line: "Line 22", pct: "100%" },
  { slug: "taxes_licenses", name: "Taxes & Licenses", line: "Line 23", pct: "100%" },
  { slug: "travel", name: "Travel", line: "Line 24a", pct: "100%" },
  { slug: "meals", name: "Meals", line: "Line 24b", pct: "50%" },
  { slug: "utilities", name: "Utilities / Phone / Internet", line: "Line 25", pct: "100%" },
  { slug: "software", name: "Software & Subscriptions", line: "Line 27a Other", pct: "100%" },
  { slug: "education", name: "Education & Training", line: "Line 27a Other", pct: "100%" },
  { slug: "bank_fees", name: "Bank Fees", line: "Line 27a Other", pct: "100%" },
];

export default function HowItWorksPage() {
  return (
    <div className="p-6 max-w-3xl mx-auto space-y-10">
      <div>
        <h1 className="text-3xl font-bold" style={{ fontFamily: "var(--font-display)" }}>How Ledgerline Works</h1>
        <p className="text-[var(--fg-muted)] mt-2">
          The categorization brain is a deterministic pipeline. The same input always produces the same output, with a full reason trail explaining every decision.
        </p>
      </div>

      {/* Pipeline */}
      <section>
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "var(--font-display)" }}>The Brain Pipeline</h2>
        <div className="space-y-4">
          {PIPELINE_STEPS.map((step, i) => (
            <motion.div
              key={step.n}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.1 }}
            >
              <Card>
                <CardContent className="pt-5">
                  <div className="flex gap-4">
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                      style={{ background: "var(--accent-light)", color: "var(--accent)" }}
                    >
                      {step.n}
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold mb-1" style={{ fontFamily: "var(--font-display)" }}>{step.title}</div>
                      <p className="text-sm text-[var(--fg-muted)] mb-2">{step.description}</p>
                      <code
                        className="block text-xs px-3 py-2 rounded-[var(--radius-md)] mb-2"
                        style={{ background: "var(--surface-2)", color: "var(--accent)" }}
                      >
                        {step.example}
                      </code>
                      <p className="text-xs text-[var(--fg-faint)]">{step.detail}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
              {i < PIPELINE_STEPS.length - 1 && (
                <div className="flex justify-center py-1">
                  <ArrowRight size={16} style={{ color: "var(--fg-faint)", transform: "rotate(90deg)" }} />
                </div>
              )}
            </motion.div>
          ))}
        </div>
      </section>

      {/* Needs Review */}
      <section>
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "var(--font-display)" }}>What &ldquo;Needs Review&rdquo; Means</h2>
        <p className="text-sm text-[var(--fg-muted)] mb-4">
          A wrong guess is worse than asking. The brain flags any transaction where it&apos;s not confident, with a human-readable explanation.
        </p>
        <div className="space-y-3">
          {REVIEW_TRIGGERS.map((t) => (
            <Card key={t.trigger}>
              <CardContent className="pt-4">
                <div
                  className="inline-flex items-center gap-1.5 text-xs font-medium rounded-full px-2 py-0.5 mb-2"
                  style={{ background: "var(--highlight-bg)", color: "var(--highlight-fg)" }}
                >
                  ⚠ {t.trigger}
                </div>
                <p className="text-sm text-[var(--fg-muted)] mb-1"><em>{t.example}</em></p>
                <p className="text-xs text-[var(--fg-faint)]">Fix: {t.fix}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      {/* Schedule C taxonomy */}
      <section>
        <h2 className="text-xl font-bold mb-4" style={{ fontFamily: "var(--font-display)" }}>Schedule C Lines Covered</h2>
        <Card>
          <CardContent className="p-0">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: "1px solid var(--border)", background: "var(--surface-2)" }}>
                  <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Category</th>
                  <th className="px-4 py-3 text-left font-medium text-[var(--fg-muted)]">Sch C</th>
                  <th className="px-4 py-3 text-right font-medium text-[var(--fg-muted)]">Deductible</th>
                </tr>
              </thead>
              <tbody>
                {TAXONOMY_ROWS.map((row) => (
                  <tr key={row.slug} style={{ borderBottom: "1px solid var(--rule-line)" }}>
                    <td className="px-4 py-3">{row.name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[var(--fg-muted)]">{row.line}</td>
                    <td className="px-4 py-3 text-right text-[var(--fg-muted)]">{row.pct}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>
        <p className="text-xs text-[var(--fg-faint)] mt-3">
          Non-P&L movements (transfers, credit-card payments, owner draws, estimated tax payments) are tracked separately and excluded from Schedule C totals.
        </p>
      </section>
    </div>
  );
}
