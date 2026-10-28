// API types, derived from the generated OpenAPI schema (src/lib/api/schema.d.ts).
// Regenerate with `npm run gen:api`; never edit schema.d.ts by hand.
import type { components } from "./schema";

type Schemas = components["schemas"];

export type AccountType = Schemas["AccountType"];
export type Direction = Schemas["Direction"];
export type Status = Schemas["Status"];
export type CategoryKind = Schemas["CategoryKind"];
export type CategoryCode = Schemas["Category"];
export type StatementCounts = Schemas["StatementCounts"];
export type ParseWarning = Schemas["ParseWarningOut"];
export type StatementOut = Schemas["StatementOut"];
export type TransactionOut = Schemas["TransactionOut"];
export type TransactionPage = Schemas["TransactionListOut"];
// remember / apply_to_similar have server-side defaults, so they are optional for callers.
export type CorrectionIn = Omit<Schemas["TransactionPatch"], "remember" | "apply_to_similar"> &
  Partial<Pick<Schemas["TransactionPatch"], "remember" | "apply_to_similar">>;
export type CorrectionOut = Schemas["PatchResult"];
export type CategoryOut = Schemas["CategoryOut"];
export type ScheduleELine = Schemas["ScheduleELine"];
export type SummaryOut = Schemas["SummaryOut"];
export type ProblemJson = Schemas["ProblemDetail"];
