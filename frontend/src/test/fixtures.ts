import type { Transaction } from "../types";

export const row: Transaction = {
  id: "fake-transaction",
  source_row: 2,
  date: "2026-04-02",
  description: "JOES CAFE 9921",
  amount_minor: -1840,
  currency: "USD",
  category: "Needs Review",
  kind: "unknown",
  confidence: 0,
  rule_id: "review.unknown",
  reason: "No sufficiently specific rule matched.",
  status: "needs_review",
  review_flags: [],
  duplicate_of: null,
  excluded: false,
  version: 1,
  note: "",
  original_decision: {
    category: "Needs Review",
    kind: "unknown",
    confidence: 0,
    rule_id: "review.unknown",
    reason: "Unknown merchant.",
    engine_version: "1.0.0",
  },
};
