import type {
  AccountType,
  Category,
  ErrorBody,
  MerchantRule,
  Statement,
  StatementDetail,
  Summary,
  Transaction,
  TransactionUpdateResult,
  TxnStatus,
  UploadResult,
} from './types'

const BASE = '/api'

/** A failed request, carrying the backend's own message (ErrorOut.detail). */
export class ApiError extends Error {
  readonly status: number
  readonly code?: string
  readonly statementId?: number

  constructor(status: number, body: Partial<ErrorBody>) {
    super(body.detail || `Request failed (${status})`)
    this.name = 'ApiError'
    this.status = status
    this.code = body.code
    this.statementId = body.statement_id
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(BASE + path, init)
  } catch {
    throw new ApiError(0, { detail: 'Cannot reach the server. Is the backend running?' })
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as Partial<ErrorBody>
    throw new ApiError(response.status, body)
  }
  return (response.status === 204 ? undefined : await response.json()) as T
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export interface UploadOptions {
  accountType: AccountType
  chargesPositive?: boolean | null
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  categories: () => request<Category[]>('/categories'),

  uploadStatement(file: File, { accountType, chargesPositive }: UploadOptions) {
    const form = new FormData()
    form.append('file', file)
    form.append('account_type', accountType)
    if (chargesPositive != null) form.append('charges_positive', String(chargesPositive))
    return request<UploadResult>('/statements', { method: 'POST', body: form })
  },
  listStatements: () => request<Statement[]>('/statements'),
  getStatement: (id: number) => request<StatementDetail>(`/statements/${id}`),
  deleteStatement: (id: number) => request<void>(`/statements/${id}`, { method: 'DELETE' }),
  listTransactions(id: number, status?: TxnStatus) {
    const query = status ? `?status=${status}` : ''
    return request<Transaction[]>(`/statements/${id}/transactions${query}`)
  },
  getSummary: (id: number) => request<Summary>(`/statements/${id}/summary`),
  exportUrl: (id: number) => `${BASE}/statements/${id}/export.csv`,

  updateTransaction: (id: number, categoryId: string, remember: boolean) =>
    request<TransactionUpdateResult>(
      `/transactions/${id}`,
      json('PATCH', { category_id: categoryId, remember }),
    ),

  listRules: () => request<MerchantRule[]>('/rules'),
  deleteRule: (id: number) => request<void>(`/rules/${id}`, { method: 'DELETE' }),

  async fetchSample(name: string): Promise<File> {
    const response = await fetch(`${BASE}/samples/${encodeURIComponent(name)}`)
    if (!response.ok) throw new ApiError(response.status, { detail: `Sample ${name} not found` })
    return new File([await response.blob()], name)
  },
}
