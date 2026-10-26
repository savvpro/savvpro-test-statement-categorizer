import type {
  Category,
  Rule,
  Sample,
  SignConvention,
  Statement,
  StatementListItem,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?", 0);
  }
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* keep the generic message */
    }
    throw new ApiError(message, res.status);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  categories: () => request<Category[]>("/api/categories"),
  statements: () => request<StatementListItem[]>("/api/statements"),
  statement: (id: number) => request<Statement>(`/api/statements/${id}`),
  samples: () => request<Sample[]>("/api/samples"),
  rules: () => request<Rule[]>("/api/rules"),

  upload(file: File, signConvention: SignConvention) {
    const form = new FormData();
    form.append("file", file);
    form.append("sign_convention", signConvention);
    return request<Statement>("/api/statements", { method: "POST", body: form });
  },

  importSample: (name: string) =>
    request<Statement>(`/api/samples/${encodeURIComponent(name)}`, { method: "POST" }),

  deleteStatement: (id: number) =>
    request<void>(`/api/statements/${id}`, { method: "DELETE" }),

  updateTransaction: (
    statementId: number,
    txId: number,
    category: string | null,
    remember: boolean,
  ) =>
    request<Statement>(`/api/statements/${statementId}/transactions/${txId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, remember }),
    }),

  deleteRule: (rule: Rule) =>
    request<void>(
      `/api/rules/${rule.direction}/${encodeURIComponent(rule.merchant_key)}`,
      { method: "DELETE" },
    ),

  exportUrl: (statementId: number) => `${BASE}/api/statements/${statementId}/export.csv`,
};
